"""Marshal-out (deterministic): ingest an Asta Theorizer artifact.

A marshal-out module, mirroring ``ingest.py`` and ``artifacts.py``: it imports
``execute_tool`` lazily (function-local), so every graph write routes through
the triple-write + write-receipt + trace-id + embedding wiring. Reads (paper
dedupe by corpus_id, edge existence for ``link_once``) reuse the same cached
backend the dispatch path uses, and reuse the shared helpers in ``ingest.py``
(``_link_once`` / ``_edge_exists`` / ``_find_paper_by_corpus_id`` and the
persisted corpus_id index).

The Theorizer output shape is NOT in the agent card or ``describe`` (both are
input-only, confirmed), so the parser is DEFENSIVE: multi-key ``.get``
fallbacks, count-and-skip unknowns, never raise. The best-effort assumed shape
(documented on ``parse_theorizer``) is tolerated with drift.

Bucketing (each theory becomes a small provenance subgraph):
  - One Execution per RUN (kind ``theory-generation``, service ``asta:theorizer``).
  - Per theory: a PARENT Finding (``artifact_type="theory"``, low confidence).
  - Per law/statement: a Hypothesis linked parent -[CONTAINS]-> Hypothesis. The
    novelty verdict (established/derivable/new) is parked in the custom bag as
    ``custom_novelty`` via a follow-up update_node, NEVER in Hypothesis.status
    (acts rely on its open/supported/rejected enum).
  - supporting papers -> add_paper (dedupe by corpus_id), Paper -[SUPPORTS]->
    Hypothesis. contradicting papers -> Paper -[CONTRADICTS]-> Hypothesis.
  - Provenance: parent + hypotheses + papers WAS_GENERATED_BY the Execution.
    If ``link_to`` is given, parent -[AROSE_FROM]-> link_to. If ``artifact_path``
    is given, the raw output registers as a Dataset and each generated node
    links WAS_DERIVED_FROM it (best-effort).

Invariants:
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses
    one cached backend singleton and Neo4j forbids concurrent queries.
  - link_once. Every edge is guarded by an existence check because the
    backend's ``create_relationship`` is a bare CREATE that would duplicate on
    re-run. Hypotheses dedupe on a content hash so re-ingest is a no-op.
  - One Execution per RUN, tagged service ``asta:theorizer``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.integrations.asta.ingest import (
    ImportReport,
    _find_paper_by_corpus_id,
    _link_once,
    _load_index,
    _save_index,
)
from wheeler.integrations.asta.schemas import _normalize_corpus_id

logger = logging.getLogger(__name__)

_SERVICE_TAG = "asta:theorizer"

# Persisted (content-hash -> Wheeler H-id) map so re-ingest of the same theory
# law reuses the existing Hypothesis instead of creating a duplicate. Kept
# separate from the shared corpus_id paper index (paper_finder_index.json),
# which we reuse for cross-tool paper dedupe.
_HYP_INDEX_REL_PATH = ".wheeler/integrations/theorizer_hyp_index.json"

# Persisted (content-hash -> Wheeler F-id) map for the per-theory parent
# Finding. A theory has no external id, so it dedupes on a content hash of its
# identity (name + summary), mirroring the Hypothesis dedupe. Re-ingest of the
# same artifact reuses the existing parent Finding instead of creating a duplicate.
_THEORY_INDEX_REL_PATH = ".wheeler/integrations/theorizer_theory_index.json"

# Valid novelty verdicts. Anything else is normalized to "" (unknown) and not
# written, so the custom bag only ever holds a known verdict.
_NOVELTY_VERDICTS = {"established", "derivable", "new"}


# ---------------------------------------------------------------------------
# Defensive parse (shape-drift tolerant, never raises)
# ---------------------------------------------------------------------------


@dataclass
class PaperRef:
    """A supporting or contradicting paper reference inside a theory."""

    corpus_id: str
    title: str
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class LawRecord:
    """One law/statement inside a theory (becomes a Hypothesis)."""

    text: str
    novelty: str = ""
    supporting: list[PaperRef] = field(default_factory=list)
    contradicting: list[PaperRef] = field(default_factory=list)


@dataclass
class TheoryRecord:
    """One theory (becomes a parent Finding with artifact_type=theory)."""

    name: str
    summary: str
    laws: list[LawRecord] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)


def _first(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present, non-None value among ``keys`` in ``d``."""
    for key in keys:
        if key in d and d[key] is not None:
            return d[key]
    return default


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _normalize_novelty(value: Any) -> str:
    """Coerce a novelty verdict to a known token, or "" if unrecognized."""
    s = _as_str(value).lower()
    return s if s in _NOVELTY_VERDICTS else ""


def _scalar_or_none(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    return None


def _parse_paper_ref(entry: Any) -> PaperRef | None:
    """Parse one supporting/contradicting paper entry, or None if unusable."""
    if not isinstance(entry, dict):
        return None
    corpus_id = _normalize_corpus_id(_first(entry, "corpusId", "corpus_id"))
    title = _as_str(_first(entry, "title", "name", default=""))
    if not corpus_id and not title:
        return None
    custom: dict[str, Any] = {}
    for src_key, dst_key in (
        ("venue", "venue"),
        ("year", "year"),
        ("url", "url"),
        ("relevanceScore", "relevance_score"),
    ):
        val = _scalar_or_none(entry.get(src_key))
        if val is not None and val != "":
            custom[dst_key] = val
    return PaperRef(corpus_id=corpus_id, title=title, custom=custom)


def _parse_paper_list(value: Any) -> list[PaperRef]:
    if not isinstance(value, list):
        return []
    refs: list[PaperRef] = []
    for entry in value:
        ref = _parse_paper_ref(entry)
        if ref is not None:
            refs.append(ref)
    return refs


def _parse_law(entry: Any) -> LawRecord | None:
    """Parse one law/statement entry, or None if there is no usable text."""
    if not isinstance(entry, dict):
        # Tolerate a bare string law.
        if isinstance(entry, str) and entry.strip():
            return LawRecord(text=entry.strip())
        return None
    text = _as_str(_first(entry, "text", "statement", "law", "claim", default=""))
    if not text:
        return None
    return LawRecord(
        text=text,
        novelty=_normalize_novelty(_first(entry, "novelty", "verdict", "status")),
        supporting=_parse_paper_list(
            _first(entry, "supporting_papers", "supporting", "support", default=[])
        ),
        contradicting=_parse_paper_list(
            _first(
                entry,
                "contradicting_papers",
                "contradicting",
                "conflicting",
                "contradicts",
                default=[],
            )
        ),
    )


def _parse_theory(entry: Any) -> TheoryRecord | None:
    """Parse one theory entry into a TheoryRecord, or None if unusable."""
    if not isinstance(entry, dict):
        logger.warning("parse_theorizer: skipping non-dict theory entry")
        return None
    name = _as_str(_first(entry, "name", "title", "id", default=""))
    summary = _as_str(
        _first(entry, "summary", "description", "abstract", default="")
    )
    raw_laws = _first(entry, "statements", "laws", "claims", "hypotheses", default=[])
    laws: list[LawRecord] = []
    if isinstance(raw_laws, list):
        for law_entry in raw_laws:
            law = _parse_law(law_entry)
            if law is not None:
                laws.append(law)
    if not name and not laws:
        logger.warning("parse_theorizer: skipping theory with no name and no laws")
        return None
    if not name:
        name = summary[:60] or "Untitled theory"

    custom: dict[str, Any] = {}
    novelty_counts: dict[str, int] = {}
    for law in laws:
        if law.novelty:
            novelty_counts[law.novelty] = novelty_counts.get(law.novelty, 0) + 1
    if laws:
        custom["law_count"] = len(laws)
    for verdict, count in novelty_counts.items():
        custom[f"novelty_{verdict}_count"] = count

    return TheoryRecord(name=name, summary=summary, laws=laws, custom=custom)


def parse_theorizer(doc: Any) -> list[TheoryRecord]:
    """Parse an Asta Theorizer artifact into TheoryRecords (defensive).

    The output shape is unverified (not in the agent card or describe), so this
    is tolerant of drift and never raises. Best-effort assumed shape:

        {"theories": [...]}  OR  {"results": [...]}  OR  a bare list

    where each theory is roughly::

        {
          "id"|"name"|"title": str,
          "statements"|"laws": [
            {"text"|"statement": str,
             "novelty": "established"|"derivable"|"new",
             "supporting_papers"|"supporting": [{"corpusId"|"corpus_id", "title"}],
             "contradicting_papers"|"conflicting": [ same ]}
          ]
        }

    Unknown or malformed entries are counted-and-skipped, not raised. A doc that
    is neither a dict nor a list, or that has no parseable theories, yields an
    empty list so a partial artifact never aborts ingest.
    """
    theories_raw: Any
    if isinstance(doc, list):
        theories_raw = doc
    elif isinstance(doc, dict):
        theories_raw = _first(
            doc, "theories", "results", "items", "output", default=None
        )
        if theories_raw is None:
            logger.warning(
                "parse_theorizer: no 'theories'/'results' list in doc keys=%s",
                sorted(doc.keys()),
            )
            return []
    else:
        logger.warning(
            "parse_theorizer: doc is neither dict nor list, got %s",
            type(doc).__name__,
        )
        return []

    if not isinstance(theories_raw, list):
        logger.warning("parse_theorizer: theories container is not a list")
        return []

    records: list[TheoryRecord] = []
    skipped = 0
    for entry in theories_raw:
        record = _parse_theory(entry)
        if record is None:
            skipped += 1
            continue
        records.append(record)
    if skipped:
        logger.info("parse_theorizer: skipped %d unparseable theory entries", skipped)
    return records


# ---------------------------------------------------------------------------
# Hypothesis content-hash dedupe (no external id, so key on the law text)
# ---------------------------------------------------------------------------


def _hyp_index_path() -> Path:
    return Path(_HYP_INDEX_REL_PATH)


def _load_hyp_index() -> dict[str, str]:
    path = _hyp_index_path()
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        logger.warning("theorizer: could not read hyp index %s, starting fresh", path)
    return {}


def _save_hyp_index(index: dict[str, str]) -> None:
    path = _hyp_index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
        tmp.replace(path)
    except OSError:
        logger.error(
            "theorizer: could not persist hyp index %s (best-effort)",
            path,
            exc_info=True,
        )


def _hyp_key(theory_name: str, law_text: str) -> str:
    """Stable content hash for a (theory, law) pair (the Hypothesis dedupe key)."""
    digest = hashlib.sha256(f"{theory_name}\x00{law_text}".encode()).hexdigest()
    return digest[:16]


def _theory_index_path() -> Path:
    return Path(_THEORY_INDEX_REL_PATH)


def _load_theory_index() -> dict[str, str]:
    path = _theory_index_path()
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "theorizer: could not read theory index %s, starting fresh", path
        )
    return {}


def _save_theory_index(index: dict[str, str]) -> None:
    path = _theory_index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
        tmp.replace(path)
    except OSError:
        logger.error(
            "theorizer: could not persist theory index %s (best-effort)",
            path,
            exc_info=True,
        )


def _theory_key(theory_name: str, summary: str) -> str:
    """Stable content hash for a theory (the parent Finding dedupe key)."""
    digest = hashlib.sha256(f"{theory_name}\x00{summary}".encode()).hexdigest()
    return digest[:16]


async def _finding_exists(backend, config: WheelerConfig, finding_id: str) -> bool:
    """Return True if a Finding with this id still lives in the graph.

    Guards the persisted theory index against staleness (a deleted node would
    otherwise leave a dangling id that re-ingest would link to). Project-aware,
    mirroring the read scoping in the query handlers.
    """
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (f:Finding {id: $id}) "
            "WHERE f._wheeler_project = $ptag RETURN f.id AS id LIMIT 1"
        )
        params = {"id": finding_id, "ptag": ptag}
    else:
        query = "MATCH (f:Finding {id: $id}) RETURN f.id AS id LIMIT 1"
        params = {"id": finding_id}
    rows = await backend.run_cypher(query, params)
    return bool(rows)


async def _hypothesis_exists(backend, config: WheelerConfig, hyp_id: str) -> bool:
    """Return True if a Hypothesis with this id still lives in the graph.

    Guards the persisted hyp index against staleness (a deleted node would
    otherwise leave a dangling id that re-ingest would link to). Project-aware,
    mirroring the read scoping in the query handlers.
    """
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (h:Hypothesis {id: $id}) "
            "WHERE h._wheeler_project = $ptag RETURN h.id AS id LIMIT 1"
        )
        params = {"id": hyp_id, "ptag": ptag}
    else:
        query = "MATCH (h:Hypothesis {id: $id}) RETURN h.id AS id LIMIT 1"
        params = {"id": hyp_id}
    rows = await backend.run_cypher(query, params)
    return bool(rows)


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


async def ingest_theorizer(
    doc: dict[str, Any],
    *,
    link_to: str | None = None,
    config: WheelerConfig,
    artifact_path: str | None = None,
) -> ImportReport:
    """Ingest a parsed Asta Theorizer artifact into the knowledge graph.

    Args:
        doc: The Theorizer output dict (or bare list), from transport.run_asta.
        link_to: Optional node id (Question/Plan) every theory parent is linked
            to via AROSE_FROM.
        config: Active Wheeler config.
        artifact_path: Optional path to the raw ``-o`` output file. When given,
            it is registered as a Dataset node (every service output is an
            artifact), linked WAS_GENERATED_BY the run Execution, and every
            generated node is linked WAS_DERIVED_FROM it. Best-effort: an
            artifact failure never breaks theory ingest.

    Returns:
        An ImportReport with created / deduped / linked / skipped counts.
        ``paper_ids`` collects every Paper touched (created or deduped).
    """
    from wheeler.tools.graph_tools import _get_backend, execute_tool

    report = ImportReport()
    theories = parse_theorizer(doc)
    if not theories:
        logger.warning("ingest_theorizer: no parseable theories in artifact")
        return report

    backend = await _get_backend(config)
    paper_index = _load_index()
    hyp_index = _load_hyp_index()
    theory_index = _load_theory_index()

    # One Execution per RUN, tagged with the service. session_id correlates
    # every node written this turn (validate_contract audits on session_id).
    question_text = str(_first(doc, "question", "query", default="") or "")[:80]
    session_id = (
        str(_first(doc, "thread_id", "session_id", default="") or "")
        or f"asta-th-{abs(hash(question_text)) & 0xffffffff:08x}"
    )
    exec_result = json.loads(
        await execute_tool(
            "add_execution",
            {
                "kind": "theory-generation",
                "description": f"Asta Theorizer: {question_text}",
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

    # Every service output is an artifact: register the raw -o JSON dump as a
    # Dataset node, linked WAS_GENERATED_BY the run Execution. Best-effort:
    # register_output_artifact returns None on any failure and never raises, so
    # an artifact problem cannot break theory ingest.
    artifact_id: str | None = None
    try:
        from wheeler.integrations.asta.artifacts import register_output_artifact

        artifact_id = await register_output_artifact(
            artifact_path,
            execution_id=exec_id,
            service=_SERVICE_TAG,
            config=config,
            description=f"{_SERVICE_TAG} raw output",
        )
    except Exception:
        logger.warning(
            "ingest_theorizer: artifact registration raised (best-effort)",
            exc_info=True,
        )
    if artifact_id:
        report.artifact = artifact_id

    # corpus_id -> P-id for papers touched this run, so a paper cited by two
    # laws is created once and reused across both.
    seen_papers: dict[str, str] = {}

    for theory in theories:
        await _ingest_one_theory(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            theory=theory,
            link_to=link_to,
            session_id=session_id,
            exec_id=exec_id,
            artifact_id=artifact_id,
            paper_index=paper_index,
            hyp_index=hyp_index,
            theory_index=theory_index,
            seen_papers=seen_papers,
            report=report,
        )

    _save_index(paper_index)
    _save_hyp_index(hyp_index)
    _save_theory_index(theory_index)
    logger.info(
        "ingest_theorizer: created=%d deduped=%d linked=%d skipped=%d (exec=%s)",
        report.created,
        report.deduped,
        report.linked,
        report.skipped,
        exec_id,
    )
    return report


async def _ingest_one_theory(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    theory: TheoryRecord,
    link_to: str | None,
    session_id: str,
    exec_id: str,
    artifact_id: str | None,
    paper_index: dict[str, str],
    hyp_index: dict[str, str],
    theory_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> None:
    """Bucket one theory into a parent Finding + law Hypotheses + paper edges."""
    # PARENT = a Finding with artifact_type="theory", low confidence (generated,
    # not yet evidence-grounded). A theory has no external id, so it dedupes on a
    # content hash of (name, summary): re-ingest of the same artifact reuses the
    # existing parent instead of creating a duplicate.
    theory_key = _theory_key(theory.name, theory.summary)
    parent_id = theory_index.get(theory_key)
    if parent_id and not await _finding_exists(backend, config, parent_id):
        # Stale index entry (the node was deleted); drop it and recreate.
        parent_id = None

    if parent_id:
        report.deduped += 1
    else:
        parent_args: dict[str, Any] = {
            "description": theory.summary or theory.name,
            "title": theory.name[:100],
            "confidence": 0.3,
            "artifact_type": "theory",
            "session_id": session_id,
            "service": _SERVICE_TAG,
        }
        parent_result = json.loads(
            await execute_tool("add_finding", parent_args, config)
        )
        parent_id = parent_result.get("node_id")
        if not parent_id or "error" in parent_result:
            logger.warning(
                "ingest_theorizer: add_finding failed for theory %r", theory.name
            )
            report.skipped += 1
            return
        report.created += 1
        theory_index[theory_key] = parent_id

        # Park the theory-level custom scalars (law_count, novelty_*_count) so
        # they are queryable. add_finding does not forward custom into create_node,
        # so stamp it via update_node (custom is a first-class NodeBase field, so
        # the update allow-list accepts it; the backend flattens it to custom_<key>).
        if theory.custom:
            await _stamp_custom(execute_tool, config, parent_id, theory.custom)

    # Provenance: parent WAS_GENERATED_BY the run Execution.
    if exec_id and await _link_once(
        backend, config, parent_id, "WAS_GENERATED_BY", exec_id
    ):
        report.linked += 1
    # parent WAS_DERIVED_FROM the raw output artifact.
    if artifact_id and await _link_once(
        backend, config, parent_id, "WAS_DERIVED_FROM", artifact_id
    ):
        report.linked += 1
    # parent AROSE_FROM the link target (the Question/Plan that prompted it).
    if link_to and await _link_once(backend, config, parent_id, "AROSE_FROM", link_to):
        report.linked += 1

    for law in theory.laws:
        await _ingest_one_law(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            theory_name=theory.name,
            law=law,
            parent_id=parent_id,
            session_id=session_id,
            exec_id=exec_id,
            artifact_id=artifact_id,
            paper_index=paper_index,
            hyp_index=hyp_index,
            seen_papers=seen_papers,
            report=report,
        )


async def _ingest_one_law(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    theory_name: str,
    law: LawRecord,
    parent_id: str,
    session_id: str,
    exec_id: str,
    artifact_id: str | None,
    paper_index: dict[str, str],
    hyp_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> None:
    """Bucket one law into a Hypothesis with supporting/contradicting papers."""
    key = _hyp_key(theory_name, law.text)
    hyp_id = hyp_index.get(key)
    if hyp_id and not await _hypothesis_exists(backend, config, hyp_id):
        # Stale index entry (the node was deleted); drop it and recreate.
        hyp_id = None

    if hyp_id:
        report.deduped += 1
    else:
        hyp_result = json.loads(
            await execute_tool(
                "add_hypothesis",
                {
                    "statement": law.text,
                    "session_id": session_id,
                    "service": _SERVICE_TAG,
                },
                config,
            )
        )
        hyp_id = hyp_result.get("node_id")
        if not hyp_id or "error" in hyp_result:
            logger.warning("ingest_theorizer: add_hypothesis failed for law %r", law.text[:60])
            report.skipped += 1
            return
        report.created += 1
        hyp_index[key] = hyp_id

        # Novelty verdict goes in the custom bag (custom_novelty), NEVER in
        # Hypothesis.status (acts rely on open/supported/rejected). add_hypothesis
        # does not forward custom into create_node, so stamp it via update_node.
        if law.novelty:
            await _stamp_custom(execute_tool, config, hyp_id, {"novelty": law.novelty})

        # Provenance for the freshly created Hypothesis.
        if exec_id and await _link_once(
            backend, config, hyp_id, "WAS_GENERATED_BY", exec_id
        ):
            report.linked += 1
        if artifact_id and await _link_once(
            backend, config, hyp_id, "WAS_DERIVED_FROM", artifact_id
        ):
            report.linked += 1

    # parent -[CONTAINS]-> Hypothesis (link_once-guarded on every run).
    if await _link_once(backend, config, parent_id, "CONTAINS", hyp_id):
        report.linked += 1

    # supporting papers -[SUPPORTS]-> Hypothesis.
    for ref in law.supporting:
        await _ingest_paper_edge(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            ref=ref,
            hyp_id=hyp_id,
            rel="SUPPORTS",
            session_id=session_id,
            exec_id=exec_id,
            artifact_id=artifact_id,
            paper_index=paper_index,
            seen_papers=seen_papers,
            report=report,
        )
    # contradicting papers -[CONTRADICTS]-> Hypothesis.
    for ref in law.contradicting:
        await _ingest_paper_edge(
            backend=backend,
            execute_tool=execute_tool,
            config=config,
            ref=ref,
            hyp_id=hyp_id,
            rel="CONTRADICTS",
            session_id=session_id,
            exec_id=exec_id,
            artifact_id=artifact_id,
            paper_index=paper_index,
            seen_papers=seen_papers,
            report=report,
        )


async def _ingest_paper_edge(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    ref: PaperRef,
    hyp_id: str,
    rel: str,
    session_id: str,
    exec_id: str,
    artifact_id: str | None,
    paper_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> None:
    """Dedupe-or-create one paper, then link it to the Hypothesis via ``rel``."""
    paper_id = await _resolve_paper(
        backend=backend,
        execute_tool=execute_tool,
        config=config,
        ref=ref,
        session_id=session_id,
        exec_id=exec_id,
        artifact_id=artifact_id,
        paper_index=paper_index,
        seen_papers=seen_papers,
        report=report,
    )
    if paper_id is None:
        return
    if await _link_once(backend, config, paper_id, rel, hyp_id):
        report.linked += 1


async def _resolve_paper(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    ref: PaperRef,
    session_id: str,
    exec_id: str,
    artifact_id: str | None,
    paper_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> str | None:
    """Return a Paper node id for ``ref``, deduping by corpus_id where possible."""
    cid = ref.corpus_id
    # 1. Already created this run.
    if cid and cid in seen_papers:
        return seen_papers[cid]
    # 2. Persisted cross-tool corpus_id index.
    existing = paper_index.get(cid) if cid else None
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

    # 4. Create. A ref with no corpus_id and no title was dropped at parse time,
    # so title is guaranteed here when corpus_id is absent.
    add_args: dict[str, Any] = {
        "title": ref.title or f"Paper {cid}",
        "corpus_id": cid,
        "custom": ref.custom,
        "session_id": session_id,
        "service": _SERVICE_TAG,
    }
    result = json.loads(await execute_tool("add_paper", add_args, config))
    paper_id = result.get("node_id")
    if not paper_id or "error" in result:
        logger.warning("ingest_theorizer: add_paper failed for corpus_id=%s", cid)
        return None
    report.created += 1
    report.paper_ids.append(paper_id)
    if cid:
        paper_index[cid] = paper_id
        seen_papers[cid] = paper_id

    # Provenance: Paper WAS_GENERATED_BY the run Execution and WAS_DERIVED_FROM
    # the raw output artifact (link_once-guarded).
    if exec_id and await _link_once(
        backend, config, paper_id, "WAS_GENERATED_BY", exec_id
    ):
        report.linked += 1
    if artifact_id and await _link_once(
        backend, config, paper_id, "WAS_DERIVED_FROM", artifact_id
    ):
        report.linked += 1
    return paper_id


async def _stamp_custom(
    execute_tool, config: WheelerConfig, node_id: str, custom: dict[str, Any]
) -> None:
    """Stamp custom-bag scalars onto an existing node via update_node.

    add_finding / add_hypothesis do not forward ``custom`` into create_node, so
    the bag must be applied with a follow-up update_node. ``custom`` is a
    first-class NodeBase field (update_node's model-derived allow-list accepts
    it) and the backend flattens it to discrete ``custom_<key>`` props on write,
    so ``custom_novelty`` is queryable. Best-effort: a failure here never breaks
    ingest.
    """
    if not custom:
        return
    try:
        result = json.loads(
            await execute_tool(
                "update_node", {"node_id": node_id, "custom": custom}, config
            )
        )
        if "error" in result:
            logger.warning(
                "ingest_theorizer: custom-bag update failed for %s: %s",
                node_id,
                result,
            )
    except Exception:
        logger.warning(
            "ingest_theorizer: custom-bag update raised for %s (best-effort)",
            node_id,
            exc_info=True,
        )
