"""Marshal-out (deterministic): ingest an Asta Literature Report.

A marshal-out module mirroring ``theorizer.py``: it imports ``execute_tool``
lazily (function-local), so every graph write routes through the triple-write +
write-receipt + trace-id + embedding wiring, and reuses the shared helpers in
``_marshal.py`` (``_link_once`` / ``_find_paper_by_corpus_id`` / ``_paper_exists``
/ ``_find_execution`` / ``_record_used`` + the persisted corpus_id index) plus
``register_output_artifact`` in ``artifacts.py``.

REAL output shape: UNLIKE the other three Asta adapters (each one A2A call that
dumps a single JSON ``-o`` artifact), the Asta Literature Report deliverable is a
MARKDOWN document. The ``literature-report`` skill orchestrates ``asta literature
find`` + ``asta papers`` lookups and Claude SYNTHESIZES a written review at
``.asta/literature/report/<topic>.md``. So this ingest takes the report MARKDOWN
(primary) plus the optional underlying ``LiteratureSearchResult`` JSON for paper
metadata enrichment, not a single service JSON.

The report uses the skill's citation convention, which carries the machine-
readable parts the parser keys on:

    Inline:      This was demonstrated by [[Maes2020]].
    References:  - [[Maes2020]] Maes, E., et al. (2020). Causal evidence ... Nature Neuroscience.
    Link defs:   [Maes2020]: https://semanticscholar.org/p/91676903

The link definition's URL carries the Semantic Scholar corpus id (``/p/<id>`` or
``CorpusId:<id>``), the stable dedupe key. The parser pairs each reference entry
(``[[Key]]``) with its link definition (``[Key]: <url>``) by citation key, lifts
the corpus id from the url, and enriches title/authors/year/venue from the
optional find-results JSON by a corpus_id join (text fallback when absent).

Bucketing (the report becomes a small synthesis subgraph):
  - One Execution per RUN (kind ``literature-report``, service
    ``asta:scholar-qa``), keyed on the report path so re-ingest is idempotent.
  - The report MARKDOWN is saved durably (see artifacts.py, extension-preserving)
    and registered as a Document (``W-``) node: a literature review is
    synthesized WRITING, not data. The Document is the run's primary produced
    node, ``WAS_GENERATED_BY`` the Execution.
  - Each cited paper -> add_paper (dedupe by corpus_id). The report Document
    ``-[CITES]-> Paper`` (the bibliographic edge), and the run Execution
    ``-[USED]-> Paper`` (the report was DERIVED from it, so the paper is a
    genuine INPUT, mirroring Theorizer evidence). Papers are REFERENCE ENTITIES
    (NO ``WAS_GENERATED_BY``; NOT ``WAS_DERIVED_FROM`` the report either, since a
    cited paper predates the review that cites it).
  - If ``link_to`` is given, the report Document ``-[AROSE_FROM]-> link_to`` and,
    when ``link_to`` is a Plan, the Execution ``-[AROSE_FROM]-> Plan``.

Semantic wiring to the EXISTING graph (the report's claims SUPPORTS/CONTRADICTS
prior Hypotheses, RELEVANT_TO open Questions) is JUDGMENT, so it lives in the
``/wh:asta-report`` act post-ingest, NOT in this parser (see the three-part model
in docs/asta-engine-spec.md).

Invariants:
  - Defensive: every step tolerates missing pieces, counts and skips, never
    raises. A malformed or reference-less report never aborts ingest.
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses
    one cached backend singleton and Neo4j forbids concurrent queries.
  - link_once: every edge is existence-guarded because the backend's
    ``create_relationship`` is a bare CREATE that duplicates on re-run.
  - One Execution per RUN, tagged service ``asta:scholar-qa``.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.integrations.asta._marshal import (
    ImportReport,
    _find_execution,
    _find_paper_by_corpus_id,
    _link_execution_to_plan,
    _link_once,
    _load_index,
    _paper_exists,
    _record_used,
    _save_index,
)
from wheeler.integrations.asta.schemas import (
    _normalize_corpus_id,
    parse_paper_finder,
)

logger = logging.getLogger(__name__)

_SERVICE_TAG = "asta:scholar-qa"

# A literature review is synthesized WRITING, so its raw node is a Document (W-),
# NOT a Dataset. Reserve Dataset for genuine data.
_RAW_NODE_TYPE = "document"

# Citation-key reference entry: a line carrying ``[[Key]]`` (the skill's
# double-bracket inline/reference form) followed by the citation text.
_REF_ENTRY_RE = re.compile(r"\[\[([^\]\[]+)\]\]\s*(.*)")

# Link definition: ``[Key]: <url>`` at the start of a line (single brackets, NOT
# followed by another ``[`` so a ``[[Key]]`` reference entry is not mistaken for
# a link def). The url runs to end-of-line / whitespace.
_LINK_DEF_RE = re.compile(r"^\[([^\]\[]+)\]:\s*(\S+)", re.MULTILINE)

# Corpus id inside a Semantic Scholar url: ``/p/<digits>`` or ``CorpusId:<digits>``
# (case-insensitive on the CorpusId token; the real find urls use both shapes).
_CORPUS_ID_RE = re.compile(r"(?:/p/|corpusid:)(\d+)", re.IGNORECASE)

# Year inside a citation text, e.g. ``(2020)``.
_YEAR_RE = re.compile(r"\((\d{4})\)")


# ---------------------------------------------------------------------------
# Parse records (intermediate, shape-drift tolerant, never raises)
# ---------------------------------------------------------------------------


@dataclass
class CitedPaper:
    """One paper cited by the report (becomes a Paper node, CITES from the doc)."""

    corpus_id: str
    title: str
    authors: str = ""
    year: int = 0
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportRecord:
    """A parsed literature report: its identity + the papers it cites."""

    title: str
    query: str
    papers: list[CitedPaper] = field(default_factory=list)


@dataclass
class RunMeta:
    """Benchmark fields for the run.

    A report has no service run_id (Claude synthesizes it), so these are usually
    empty; kept for shape-parity with the other adapters and future enrichment.
    """

    run_id: str = ""
    cost: float | None = None
    time: float | None = None
    model: str = ""

    def custom_bag(self) -> dict[str, Any]:
        bag: dict[str, Any] = {"service": _SERVICE_TAG}
        if self.run_id:
            bag["run_id"] = self.run_id
        if self.cost is not None:
            bag["cost"] = self.cost
        if self.time is not None:
            bag["time"] = self.time
        if self.model:
            bag["model"] = self.model
        return bag


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _corpus_id_from_url(url: str) -> str:
    """Lift a corpus id from a Semantic Scholar url, normalized, or ""."""
    match = _CORPUS_ID_RE.search(url or "")
    return _normalize_corpus_id(match.group(1)) if match else ""


def _report_title(markdown: str) -> str:
    """First level-1 ATX heading (``# ...``) as the report title, or ""."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _link_defs(markdown: str) -> dict[str, str]:
    """Map citation key -> corpus_id from every ``[Key]: <url>`` link def.

    A key with no extractable corpus id is kept with "" so the reference entry
    is still recognized (its metadata then comes from the text / find-results).
    """
    out: dict[str, str] = {}
    for key, url in _LINK_DEF_RE.findall(markdown):
        ckey = key.strip()
        if ckey and ckey not in out:
            out[ckey] = _corpus_id_from_url(url)
    return out


def _ref_entries(markdown: str) -> dict[str, str]:
    """Map citation key -> citation text from every ``[[Key]] <text>`` entry.

    Inline mentions and the References list both use ``[[Key]]``; the References
    entry carries the fuller text (authors, year, title), so prefer the LONGEST
    text seen for a key. This is the set of papers the report actually cites.
    """
    out: dict[str, str] = {}
    for raw_line in markdown.splitlines():
        match = _REF_ENTRY_RE.search(raw_line)
        if not match:
            continue
        key = match.group(1).strip()
        text = match.group(2).strip()
        if not key:
            continue
        if key not in out or len(text) > len(out[key]):
            out[key] = text
    return out


def _title_from_citation(text: str) -> str:
    """Best-effort title from a citation text ``Authors (Year). Title. Venue.``

    Take the clause after the ``(Year).`` marker up to the next sentence period.
    Falls back to the whole text when no year marker is present. Defensive: never
    raises, returns "" only for empty input.
    """
    text = text.strip()
    if not text:
        return ""
    match = _YEAR_RE.search(text)
    after = text[match.end() :].strip(" .") if match else text
    # Title is the first sentence after the year; venues follow another period.
    title = after.split(". ", 1)[0].strip(" .")
    return title or after or text


def _find_results_index(find_results: dict[str, Any] | None) -> dict[str, Any]:
    """Build a corpus_id -> PaperRecord map from a LiteratureSearchResult.

    Reuses the battle-tested ``parse_paper_finder`` (same shape) so enrichment
    metadata (clean title, authors, year, venue, url, abstract) is lifted by a
    deterministic corpus_id join. Defensive: a missing / malformed doc yields {}.
    """
    if not isinstance(find_results, dict):
        return {}
    index: dict[str, Any] = {}
    for record in parse_paper_finder(find_results):
        if record.corpus_id:
            index[record.corpus_id] = record
    return index


def parse_scholar_qa(
    report_markdown: Any, find_results: dict[str, Any] | None = None
) -> tuple[ReportRecord | None, RunMeta]:
    """Parse an Asta Literature Report markdown into a ReportRecord + run meta.

    Pairs each ``[[Key]]`` reference entry with its ``[Key]: <url>`` link
    definition by citation key, lifts the corpus id from the url, and enriches
    title/authors/year/venue from the optional find-results JSON (corpus_id
    join, text fallback). Defensive throughout: a non-string, empty, or
    reference-less report yields ``(None, RunMeta())`` so a partial artifact
    never aborts ingest.
    """
    if not isinstance(report_markdown, str) or not report_markdown.strip():
        logger.warning(
            "parse_scholar_qa: report is not a non-empty string, got %s",
            type(report_markdown).__name__,
        )
        return None, RunMeta()

    title = _report_title(report_markdown)
    link_defs = _link_defs(report_markdown)
    ref_entries = _ref_entries(report_markdown)
    enrich = _find_results_index(find_results)

    papers: list[CitedPaper] = []
    seen: set[str] = set()
    for key, text in ref_entries.items():
        corpus_id = link_defs.get(key, "")
        record = enrich.get(corpus_id) if corpus_id else None

        if record is not None:
            paper_title = record.title or _title_from_citation(text)
            authors = record.authors
            year = record.year
            custom = dict(record.custom)
        else:
            paper_title = _title_from_citation(text)
            authors = ""
            year_match = _YEAR_RE.search(text)
            year = int(year_match.group(1)) if year_match else 0
            custom = {}

        if not corpus_id and not paper_title:
            # Nothing to dedupe or name this reference by: skip it.
            continue
        # Dedupe within one report: a key cited inline and in References resolves
        # once; corpus-id-less refs dedupe on title.
        dedupe_key = corpus_id or f"title:{paper_title.lower()}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        custom["citation_key"] = key
        papers.append(
            CitedPaper(
                corpus_id=corpus_id,
                title=paper_title,
                authors=authors,
                year=year,
                custom=custom,
            )
        )

    query = _as_str((find_results or {}).get("query")) if find_results else ""
    record = ReportRecord(title=title, query=query, papers=papers)
    return record, RunMeta()


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


async def ingest_scholar_qa(
    report_markdown: str,
    *,
    report_path: str | None = None,
    find_results: dict[str, Any] | None = None,
    link_to: str | None = None,
    config: WheelerConfig,
    used_inputs: list[str] | None = None,
) -> ImportReport:
    """Ingest an Asta Literature Report into the knowledge graph.

    Args:
        report_markdown: The report's markdown text (the deliverable).
        report_path: Optional path to the report file. Registered as the Document
            (raw node, synthesized writing) WAS_GENERATED_BY the run Execution,
            and the stable run key so re-ingest is idempotent. The durable
            raw-store snapshot is first-write-wins: re-ingesting an EDITED report
            at the same path reuses the one Document node (correct provenance
            identity) but does NOT re-copy the new bytes into the store, so the
            snapshot keeps the first-seen version.
        find_results: Optional underlying ``LiteratureSearchResult`` dict, used to
            enrich each cited paper's metadata by a corpus_id join (best-effort).
        link_to: Optional node id (Question/Plan) the report Document AROSE_FROM.
        config: Active Wheeler config.
        used_inputs: Optional graph node ids the marshal-in consumed to build the
            request (the link target plus any seeded source ids). The run
            Execution -[USED]-> each one that exists (input-side provenance,
            existence-guarded, link_once, never fabricated).

    Returns:
        An ImportReport with created / deduped / linked / skipped / used counts.
        ``artifact`` is the report Document id; ``paper_ids`` the cited papers.
    """
    from wheeler.tools.graph_tools import _get_backend, execute_tool

    report = ImportReport()
    record, run_meta = parse_scholar_qa(report_markdown, find_results)
    if record is None:
        logger.warning("ingest_scholar_qa: report not parseable")
        return report

    backend = await _get_backend(config)
    paper_index = _load_index()

    # One stable run key from the report's IDENTITY (its path), used for BOTH the
    # Execution session_id AND the durable raw-store key, so the two dedupe on the
    # SAME identity. A literature report has no service run_id (Claude synthesizes
    # it), so without this coupling the Execution would key on the path (stable)
    # while the Document keyed on a content sha (changes on every edit): re-running
    # the act at the same path with re-synthesized text would then accrue a SECOND
    # Document to the same run. Coupling to the path makes one report path = one
    # run = one Document, even across edits. Falls back to a content hash when no
    # path is given (a directly-passed string has no stable identity).
    run_key = run_meta.run_id or (
        "sqa-" + hashlib.sha256(
            (report_path or report_markdown[:512]).encode()
        ).hexdigest()[:16]
    )
    session_id = run_key
    exec_id = await _find_execution(
        backend, config, service=_SERVICE_TAG, session_id=session_id
    )
    if not exec_id:
        import json

        exec_result = json.loads(
            await execute_tool(
                "add_execution",
                {
                    "kind": "literature-report",
                    "description": (
                        f"Asta Literature Report: {record.title or record.query}"
                    )[:200],
                    "agent_id": "asta",
                    "status": "completed",
                    "session_id": session_id,
                    "service": _SERVICE_TAG,
                },
                config,
            )
        )
        exec_id = exec_result.get("node_id", "")
    report.execution_id = exec_id

    # Plan lifecycle: anchor the run Execution to its Plan (Execution -[AROSE_FROM]
    # -> Plan) when link_to is a PL- id. No-op otherwise; link_once.
    if exec_id and await _link_execution_to_plan(backend, config, exec_id, link_to):
        report.plan_linked += 1

    # Input-side provenance: the marshal-in built the request FROM graph nodes, so
    # the run USED them. Existence-guarded, never fabricated, re-ingest dedupes.
    if exec_id and used_inputs:
        report.used += await _record_used(backend, config, exec_id, used_inputs)

    # The report markdown is synthesized WRITING, so it registers as a Document
    # (W-) node, the run's PRIMARY produced node, WAS_GENERATED_BY the Execution.
    # Best-effort: returns None on any failure and never raises.
    doc_id: str | None = None
    try:
        from wheeler.integrations.asta.artifacts import register_output_artifact

        doc_id = await register_output_artifact(
            report_path,
            execution_id=exec_id,
            service=_SERVICE_TAG,
            config=config,
            node_type=_RAW_NODE_TYPE,
            # Key the durable store on the SAME run_key as the Execution (above),
            # not a content sha, so one report path resolves to one Document.
            run_id=run_key,
            benchmark=run_meta.custom_bag(),
            description=(
                f"Literature report: {record.title or record.query}"
            )[:200],
        )
    except Exception:
        logger.warning(
            "ingest_scholar_qa: artifact registration raised (best-effort)",
            exc_info=True,
        )
    if doc_id:
        report.artifact = doc_id
        # The report Document AROSE_FROM its link target (the Question/Plan that
        # prompted it), mirroring a Theorizer theory parent.
        if link_to and await _link_once(
            backend, config, doc_id, "AROSE_FROM", link_to
        ):
            report.linked += 1

    # corpus_id -> P-id for papers touched this run (a paper cited by two keys is
    # resolved once).
    seen_papers: dict[str, str] = {}
    for paper in record.papers:
        await _ingest_cited_paper(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            paper=paper,
            doc_id=doc_id,
            exec_id=exec_id,
            session_id=session_id,
            paper_index=paper_index,
            seen_papers=seen_papers,
            report=report,
        )

    _save_index(paper_index)
    logger.info(
        "ingest_scholar_qa: created=%d deduped=%d linked=%d skipped=%d "
        "used=%d plan_linked=%d (exec=%s)",
        report.created,
        report.deduped,
        report.linked,
        report.skipped,
        report.used,
        report.plan_linked,
        exec_id,
    )
    return report


async def _ingest_cited_paper(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    paper: CitedPaper,
    doc_id: str | None,
    exec_id: str,
    session_id: str,
    paper_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> None:
    """Dedupe-or-create one cited paper, then wire its edges.

    The report Document -[CITES]-> the paper (bibliographic edge), and the run
    Execution -[USED]-> the paper: the review was DERIVED from the paper, so it is
    a genuine INPUT (mirroring Theorizer evidence). Papers are reference entities
    (NO WAS_GENERATED_BY; NOT WAS_DERIVED_FROM the report, since a cited paper
    predates the review). Both edges link_once-guarded.
    """
    paper_id = await _resolve_paper(
        backend=backend,
        execute_tool=execute_tool,
        config=config,
        paper=paper,
        session_id=session_id,
        paper_index=paper_index,
        seen_papers=seen_papers,
        report=report,
    )
    if paper_id is None:
        return
    # The report Document CITES the paper (bibliographic edge).
    if doc_id and await _link_once(backend, config, doc_id, "CITES", paper_id):
        report.linked += 1
    # Execution -[USED]-> the cited paper: the report was derived from it.
    if exec_id and await _link_once(backend, config, exec_id, "USED", paper_id):
        report.linked += 1


async def _resolve_paper(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    paper: CitedPaper,
    session_id: str,
    paper_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> str | None:
    """Return a Paper node id for ``paper``, deduping by corpus_id where possible."""
    cid = paper.corpus_id
    # 1. Already created this run.
    if cid and cid in seen_papers:
        return seen_papers[cid]
    # 2. Persisted cross-tool corpus_id index. Only trust the hit if the node
    # still lives in the graph; a stale id would make link_once target a missing
    # node and silently drop the CITES edge. Drop the dead entry and fall through.
    existing = paper_index.get(cid) if cid else None
    if existing and not await _paper_exists(backend, config, existing):
        existing = None
        if cid:
            paper_index.pop(cid, None)
    # 3. Project-aware graph read.
    if not existing and cid:
        existing = await _find_paper_by_corpus_id(backend, config, cid)
    if existing:
        report.deduped += 1
        if existing not in report.paper_ids:
            report.paper_ids.append(existing)
        if cid:
            paper_index[cid] = existing
            seen_papers[cid] = existing
        return existing

    # 4. Create. A paper with no corpus_id and no title was dropped at parse time,
    # so title is guaranteed here when corpus_id is absent.
    import json

    add_args: dict[str, Any] = {
        "title": paper.title or f"Paper {cid}",
        "corpus_id": cid,
        "authors": paper.authors,
        "year": paper.year,
        "custom": paper.custom,
        "session_id": session_id,
        "service": _SERVICE_TAG,
    }
    result = json.loads(await execute_tool("add_paper", add_args, config))
    paper_id = result.get("node_id")
    if not paper_id or "error" in result:
        logger.warning("ingest_scholar_qa: add_paper failed for corpus_id=%s", cid)
        report.skipped += 1
        return None
    report.created += 1
    report.paper_ids.append(paper_id)
    if cid:
        paper_index[cid] = paper_id
        seen_papers[cid] = paper_id
    # Papers are REFERENCE ENTITIES (per /wh:close, /wh:graph-link): no
    # WAS_GENERATED_BY. The semantic edges (CITES from the doc, USED by the run)
    # are added by the caller.
    return paper_id
