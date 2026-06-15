"""Marshal-out (deterministic): ingest an Asta Semantic Scholar artifact.

The third adapter (after Paper Finder and Theorizer). It is mechanical: it
reuses the Paper bucketing, the shared corpus_id index, and every read/write
helper in ``ingest.py`` plus ``register_output_artifact`` in ``artifacts.py``.
No generic engine is extracted yet (that is a later phase).

A marshal-out module, mirroring ``ingest.py`` / ``theorizer.py``: it imports
``execute_tool`` lazily (function-local), so every graph write routes through
the triple-write + write-receipt + trace-id + embedding wiring. Reads (paper
dedupe by corpus_id, edge existence for ``link_once``, execution dedupe) reuse
the same cached backend the dispatch path uses, and reuse the shared helpers in
``_marshal.py`` (``_link_once`` / ``_edge_exists`` / ``_find_paper_by_corpus_id``
/ ``_paper_exists`` / ``_find_execution`` + the persisted corpus_id index) plus
the corpus_id normalization in ``schemas.py``.

REAL Semantic Scholar REST output shapes (not A2A), captured live. The parser
AUTO-DETECTS the sub-kind by keys, since all four are distinguishable:

  - ``get``: a single paper dict ``{paperId, title, venue, year, citationCount,
    url, openAccessPdf, publicationDate, authors:[{name, authorId}], abstract}``.
    Detected by a top-level ``paperId``. IMPORTANT: ``corpusId`` is NOT in the
    default field set; the CLI must request ``--fields corpusId,externalIds`` so
    it is present (it then appears as a top-level ``corpusId`` and/or under
    ``externalIds.CorpusId``). Without it, dedupe falls back to the s2 paperId or
    DOI, which will NOT match a Paper Finder / Theorizer corpus_id.
  - ``search``: ``{total, offset, next, data:[paper...]}`` (same paper dict
    shape). Detected by ``total`` present alongside a ``data`` list.
  - ``citations``: ``{offset, next, data:[{citingPaper:{...}}]}``. Detected by
    ``data[].citingPaper``. CRITICAL: the TARGET paper being cited is NOT in the
    output (it is the CLI argument); the ingest receives it via ``target`` (a
    corpus_id or a P-id) to create the CITES edges.
  - ``snippet``: ``{data:[{paper:{corpusId, title, ...}, score, snippet:{text,
    snippetKind, ...}}], retrievalVersion}``. Detected by ``data[].snippet`` and
    a top-level ``retrievalVersion``. snippet-search DOES carry ``paper.corpusId``.

MAPPING (service = ``asta:semantic-scholar``):
  - get / search -> Paper nodes (dedupe by corpus_id when present, else a stable
    fallback key from s2 paperId or DOI; the s2 paperId / DOI / openAccessPdf are
    parked in the custom bag). Reuses Paper bucketing + the shared corpus_id index.
  - citations(target T) -> each citingPaper -> Paper node (dedupe); citingPaper
    -[CITES]-> T. T is resolved from the passed ``target`` (a corpus_id digit
    string mapped to its Paper, or a P-id used directly). This BUILDS the
    citation graph. CRITICAL: a citing paper is NOT relevant to the question, so
    it links via CITES + WAS_DERIVED_FROM the raw node ONLY, NEVER RELEVANT_TO.
    Papers are reference entities, not produced by Wheeler, so they carry NO
    WAS_GENERATED_BY (per /wh:close and /wh:graph-link: "Papers are never
    orphans. They are reference entities, not produced by Wheeler"). ``link_to``
    is therefore NOT applied to the citations sub-kind (it is applied to get /
    search / snippet, whose results ARE relevant to the question).
  - snippet -> a Finding(artifact_type="snippet", description=snippet.text,
    confidence=score, title=short) -[APPEARS_IN]-> its Paper; the paper -> Paper
    node (corpusId present). Snippet Findings dedupe on a content hash so
    re-ingest is a no-op.
  - raw output -> a Dataset node (structured reference records: data-ish is a
    Dataset, unlike Theorizer synthesis = Document), service-tagged, saved
    durably to ``.wheeler/asta/raw/asta-semantic-scholar/<sha>.json``. S2 has no
    run_id, so the durable key is a content sha. No cost/time benchmark fields.
  - One Execution per RUN (service ``asta:semantic-scholar``, kind by sub-shape,
    e.g. ``s2-citations``); the run Execution is WAS_GENERATED_BY the
    Wheeler-PRODUCED nodes only (the raw Dataset node + each snippet Finding).
    Papers are reference entities and carry NO WAS_GENERATED_BY. If ``link_to``
    is given, RELEVANT_TO links the question to results that are actually
    relevant (get / search / snippet), but NOT to citing papers (see citations).

Invariants:
  - Defensive: every step tolerates missing fields, counts and skips, never
    raises. A partial or shape-drifted artifact never aborts ingest.
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses
    one cached backend singleton and Neo4j forbids concurrent queries.
  - link_once on every edge (incl. CITES, APPEARS_IN). Papers dedupe on
    corpus_id (graph-existence-guarded), snippet Findings on a content hash, the
    Execution on (service, session_id), the raw Dataset on path.
  - One Execution per RUN, tagged service ``asta:semantic-scholar``.
  - No LLM-provider SDK.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.integrations.asta._marshal import (
    ImportReport,
    _find_execution,
    _find_paper_by_corpus_id,
    _link_once,
    _load_index,
    _paper_exists,
    _record_used,
    _save_index,
)
from wheeler.integrations.asta.schemas import _normalize_corpus_id

logger = logging.getLogger(__name__)

_SERVICE_TAG = "asta:semantic-scholar"

# Persisted (content-hash -> Wheeler F-id) map so re-ingest of the same snippet
# reuses the existing Finding instead of creating a duplicate. Kept separate
# from the shared corpus_id paper index (paper_finder_index.json), which we
# reuse for cross-tool paper dedupe.
_SNIPPET_INDEX_REL_PATH = ".wheeler/integrations/semantic_scholar_snippet_index.json"

# Persisted (fallback-key -> Wheeler P-id) map for papers that arrive WITHOUT a
# corpus_id (the DEFAULT S2 field set omits corpusId, so a get/search run that
# does not request it has only the s2 paperId / DOI as a stable key). Kept
# SEPARATE from the shared corpus_id index (paper_finder_index.json), which is
# keyed strictly on corpus_id so it stays compatible with Paper Finder /
# Theorizer. The fallback key is namespaced (``s2:<paperId>`` / ``doi:<doi>``)
# so a paperId and a DOI can never collide. Re-ingesting a corpus-id-less paper
# reuses its P-id instead of forking a duplicate. The s2 paperId / DOI are also
# parked on the node (``custom_s2_paper_id`` / ``custom_doi``) so the dedupe has
# a graph fallback when the index file is absent.
_FALLBACK_INDEX_REL_PATH = ".wheeler/integrations/semantic_scholar_fallback_index.json"


# ---------------------------------------------------------------------------
# Normalized records (intermediate, shape-drift tolerant)
# ---------------------------------------------------------------------------


@dataclass
class S2Paper:
    """One Semantic Scholar paper normalized for ingest.

    ``corpus_id`` is the preferred dedupe key (a digit string, "" if absent).
    ``fallback_key`` is a stable secondary key (the s2 paperId, else a DOI) used
    only when corpus_id is absent so cross-shape dedupe within a run still works.
    """

    corpus_id: str
    title: str
    authors: str
    year: int
    custom: dict[str, Any] = field(default_factory=dict)
    fallback_key: str = ""


@dataclass
class S2Snippet:
    """One snippet-search hit (becomes a Finding -[APPEARS_IN]-> its Paper)."""

    text: str
    score: float
    kind: str
    paper: S2Paper


@dataclass
class S2Citation:
    """One citing paper (becomes a Paper -[CITES]-> the target)."""

    citing: S2Paper


@dataclass
class S2Parsed:
    """The auto-detected, normalized result of parsing one S2 artifact.

    ``sub_kind`` is one of get | search | citations | snippet | unknown.
    Exactly one of the record lists is populated per sub_kind.
    """

    sub_kind: str
    papers: list[S2Paper] = field(default_factory=list)
    citations: list[S2Citation] = field(default_factory=list)
    snippets: list[S2Snippet] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Small coercion helpers (defensive)
# ---------------------------------------------------------------------------


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _coerce_year(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coerce_score(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return 0.0
    return 0.0


def _scalar_or_none(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    return None


def _join_authors(value: Any) -> str:
    """Render the authors list (dicts ``{name, authorId}`` or bare strings)."""
    if not isinstance(value, list):
        return _as_str(value)
    names: list[str] = []
    for author in value:
        if isinstance(author, dict):
            name = author.get("name", "")
            if name:
                names.append(str(name))
        elif isinstance(author, str):
            if author:
                names.append(author)
    return ", ".join(names)


def _doi_from_external_ids(paper: dict[str, Any]) -> str:
    """Pull a DOI out of ``externalIds`` (a defensive fallback dedupe key)."""
    ext = paper.get("externalIds")
    if isinstance(ext, dict):
        for key in ("DOI", "doi"):
            doi = ext.get(key)
            if doi:
                return _as_str(doi)
    return ""


def _corpus_id_from_paper(paper: dict[str, Any]) -> str:
    """Resolve a corpus_id from a paper dict, trying both shapes.

    Direct ``corpusId`` (snippet-search and any get/search run with
    ``--fields corpusId``) is preferred; ``externalIds.CorpusId`` is the second
    place S2 returns it (``--fields externalIds``). Returns "" when neither is
    present (the default S2 field set omits corpusId entirely).
    """
    cid = _normalize_corpus_id(paper.get("corpusId"))
    if cid:
        return cid
    ext = paper.get("externalIds")
    if isinstance(ext, dict):
        for key in ("CorpusId", "corpusId", "corpusid"):
            cid = _normalize_corpus_id(ext.get(key))
            if cid:
                return cid
    return ""


# Scalar long-tail fields parked into the custom bag. Each maps an S2 paper key
# to the custom_<key> name the backend stores. Only scalar values are kept.
_CUSTOM_SCALAR_KEYS: tuple[tuple[str, str], ...] = (
    ("venue", "venue"),
    ("url", "url"),
    ("citationCount", "citation_count"),
    ("abstract", "abstract"),
    ("publicationDate", "publication_date"),
)


def _parse_paper(paper: Any) -> S2Paper | None:
    """Parse one S2 paper dict into an S2Paper, or None if unusable.

    Drops a paper with no corpus_id AND no title AND no fallback key (paperId /
    DOI), so a malformed entry never creates a junk node.
    """
    if not isinstance(paper, dict):
        logger.warning("parse_semantic_scholar: skipping non-dict paper entry")
        return None

    corpus_id = _corpus_id_from_paper(paper)
    title = _as_str(paper.get("title"))
    s2_paper_id = _as_str(paper.get("paperId"))
    doi = _doi_from_external_ids(paper)
    fallback_key = s2_paper_id or doi

    if not corpus_id and not title and not fallback_key:
        logger.warning(
            "parse_semantic_scholar: skipping paper with no corpus_id, title, "
            "or fallback key"
        )
        return None

    custom: dict[str, Any] = {}
    for src_key, dst_key in _CUSTOM_SCALAR_KEYS:
        val = _scalar_or_none(paper.get(src_key))
        if val is not None and val != "":
            custom[dst_key] = val
    # Park the s2 identifiers so a corpus-id-less paper stays joinable later.
    if s2_paper_id:
        custom["s2_paper_id"] = s2_paper_id
    if doi:
        custom["doi"] = doi
    # openAccessPdf is a nested dict; lift its url (a scalar) into the bag.
    oa = paper.get("openAccessPdf")
    if isinstance(oa, dict):
        oa_url = _scalar_or_none(oa.get("url"))
        if oa_url:
            custom["open_access_pdf"] = oa_url
    # snippet-search carries openAccessInfo (no pdf url, a status) instead.
    oai = paper.get("openAccessInfo")
    if isinstance(oai, dict):
        oa_status = _scalar_or_none(oai.get("status"))
        if oa_status:
            custom["open_access_status"] = oa_status

    return S2Paper(
        corpus_id=corpus_id,
        title=title,
        authors=_join_authors(paper.get("authors")),
        year=_coerce_year(paper.get("year")),
        custom=custom,
        fallback_key=fallback_key,
    )


# ---------------------------------------------------------------------------
# Auto-detect the sub-kind
# ---------------------------------------------------------------------------


def _detect_sub_kind(doc: dict[str, Any]) -> str:
    """Classify an S2 REST doc into get | search | citations | snippet.

    The four sub-shapes are distinguishable by keys:
      - snippet:   ``retrievalVersion`` present, or ANY ``data[i].snippet``.
      - citations: ANY ``data[i]`` is a dict carrying a ``citingPaper`` KEY
                   (whether its value is a dict, ``null``, or absent-but-present).
      - search:    ``total`` present alongside a ``data`` list (and not the two
                   above, which also carry a ``data`` list).
      - get:       a top-level ``paperId`` (a single paper dict).
    Order matters: snippet and citations are checked before the generic
    ``data``-list shapes so they are not misread as a search.

    Detection SCANS the whole ``data`` list rather than trusting ``data[0]``: a
    citations response whose FIRST entry has ``citingPaper: null`` (a real S2
    shape when a citing record is withheld) would otherwise be misread as a
    plain search and the ENTIRE citation graph silently dropped. So citations is
    detected when any entry carries the ``citingPaper`` key (presence, not
    value), and snippet likewise when any entry carries a ``snippet`` dict.
    """
    data = doc.get("data")
    entries = [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []

    if "retrievalVersion" in doc or any(
        isinstance(e.get("snippet"), dict) for e in entries
    ):
        return "snippet"
    if any("citingPaper" in e for e in entries):
        return "citations"
    if "total" in doc and isinstance(data, list):
        return "search"
    if "paperId" in doc:
        return "get"
    # A bare ``data`` list of papers with no ``total`` is still a search-like
    # listing; treat it as search rather than dropping it.
    if isinstance(data, list):
        return "search"
    return "unknown"


def parse_semantic_scholar(doc: Any) -> S2Parsed:
    """Parse an Asta Semantic Scholar REST artifact, auto-detecting the sub-kind.

    Defensive throughout: a non-dict doc, or an unrecognized shape, yields an
    ``S2Parsed(sub_kind="unknown")`` with empty record lists rather than raising,
    so a partial artifact never aborts ingest.
    """
    if not isinstance(doc, dict):
        logger.warning(
            "parse_semantic_scholar: doc is not a dict, got %s",
            type(doc).__name__,
        )
        return S2Parsed(sub_kind="unknown")

    sub_kind = _detect_sub_kind(doc)

    if sub_kind == "get":
        record = _parse_paper(doc)
        return S2Parsed(sub_kind="get", papers=[record] if record else [])

    if sub_kind == "search":
        papers: list[S2Paper] = []
        data = doc.get("data")
        if isinstance(data, list):
            for entry in data:
                record = _parse_paper(entry)
                if record is not None:
                    papers.append(record)
        return S2Parsed(sub_kind="search", papers=papers)

    if sub_kind == "citations":
        citations: list[S2Citation] = []
        data = doc.get("data")
        if isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                citing = _parse_paper(entry.get("citingPaper"))
                if citing is not None:
                    citations.append(S2Citation(citing=citing))
        return S2Parsed(sub_kind="citations", citations=citations)

    if sub_kind == "snippet":
        snippets: list[S2Snippet] = []
        data = doc.get("data")
        if isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                snip = entry.get("snippet")
                text = ""
                kind = ""
                if isinstance(snip, dict):
                    text = _as_str(snip.get("text"))
                    kind = _as_str(snip.get("snippetKind"))
                paper = _parse_paper(entry.get("paper"))
                if not text or paper is None:
                    # A snippet with no text or no resolvable paper is unusable.
                    continue
                snippets.append(
                    S2Snippet(
                        text=text,
                        score=_coerce_score(entry.get("score")),
                        kind=kind,
                        paper=paper,
                    )
                )
        return S2Parsed(sub_kind="snippet", snippets=snippets)

    logger.warning("parse_semantic_scholar: unrecognized S2 shape, nothing to ingest")
    return S2Parsed(sub_kind="unknown")


# ---------------------------------------------------------------------------
# Snippet content-hash dedupe index (snippets have no external id)
# ---------------------------------------------------------------------------


def _snippet_index_path():
    from pathlib import Path

    return Path(_SNIPPET_INDEX_REL_PATH)


def _load_snippet_index() -> dict[str, str]:
    path = _snippet_index_path()
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "semantic_scholar: could not read snippet index %s, starting fresh",
            path,
        )
    return {}


def _save_snippet_index(index: dict[str, str]) -> None:
    path = _snippet_index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
        tmp.replace(path)
    except OSError:
        logger.error(
            "semantic_scholar: could not persist snippet index %s (best-effort)",
            path,
            exc_info=True,
        )


def _snippet_key(corpus_id: str, text: str) -> str:
    """Stable content hash for a snippet (the Finding dedupe key)."""
    digest = hashlib.sha256(f"{corpus_id}\x00{text}".encode()).hexdigest()
    return digest[:16]


# ---------------------------------------------------------------------------
# Corpus-id-less paper fallback index (s2 paperId / DOI, namespaced)
# ---------------------------------------------------------------------------


def _fallback_index_path():
    from pathlib import Path

    return Path(_FALLBACK_INDEX_REL_PATH)


def _load_fallback_index() -> dict[str, str]:
    path = _fallback_index_path()
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "semantic_scholar: could not read fallback index %s, starting fresh",
            path,
        )
    return {}


def _save_fallback_index(index: dict[str, str]) -> None:
    path = _fallback_index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
        tmp.replace(path)
    except OSError:
        logger.error(
            "semantic_scholar: could not persist fallback index %s (best-effort)",
            path,
            exc_info=True,
        )


def _fallback_keys(record: S2Paper) -> list[str]:
    """Namespaced persisted keys for a corpus-id-less paper (s2 paperId / DOI).

    Both are returned (a paper may carry both) so either re-ingest path resolves
    the same node. Namespacing (``s2:`` / ``doi:``) prevents a paperId from
    colliding with a DOI.
    """
    keys: list[str] = []
    s2_id = str(record.custom.get("s2_paper_id", "")).strip()
    doi = str(record.custom.get("doi", "")).strip()
    if s2_id:
        keys.append(f"s2:{s2_id}")
    if doi:
        keys.append(f"doi:{doi}")
    return keys


async def _find_paper_by_fallback(
    backend, config: WheelerConfig, record: S2Paper
) -> str | None:
    """Resolve a corpus-id-less Paper via a graph read on s2 paperId / DOI.

    The graph fallback so dedupe still works when the persisted fallback index
    file is absent (a fresh checkout, a cleared sandbox). Reads the parked
    ``custom_s2_paper_id`` / ``custom_doi`` props. Project-aware, mirroring the
    other adapter reads.
    """
    s2_id = str(record.custom.get("s2_paper_id", "")).strip()
    doi = str(record.custom.get("doi", "")).strip()
    if not s2_id and not doi:
        return None
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    clauses: list[str] = []
    params: dict[str, Any] = {}
    if s2_id:
        clauses.append("p.custom_s2_paper_id = $s2")
        params["s2"] = s2_id
    if doi:
        clauses.append("p.custom_doi = $doi")
        params["doi"] = doi
    where = "(" + " OR ".join(clauses) + ")"
    if ptag:
        where += " AND p._wheeler_project = $ptag"
        params["ptag"] = ptag
    query = f"MATCH (p:Paper) WHERE {where} RETURN p.id AS id LIMIT 1"
    rows = await backend.run_cypher(query, params)
    if rows:
        return rows[0].get("id")
    return None


async def _finding_exists(backend, config: WheelerConfig, finding_id: str) -> bool:
    """Return True if a Finding with this id still lives in the graph.

    Guards the persisted snippet index against staleness (a deleted node would
    otherwise leave a dangling id that re-ingest would link to). Project-aware,
    mirroring the read scoping in the query handlers and the other adapters.
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


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def _kind_for_sub(sub_kind: str) -> str:
    """Map a parsed sub-kind to the Execution ``kind`` (e.g. ``s2-citations``)."""
    return f"s2-{sub_kind}" if sub_kind and sub_kind != "unknown" else "s2-query"


def _session_id_for(doc: dict[str, Any], sub_kind: str) -> str:
    """Build a stable session id for this run (S2 has no run_id).

    Keyed on the sub-kind plus a content sha of the doc, so re-ingesting the
    same artifact reuses the same Execution (the dedupe is on service +
    session_id), while a different artifact gets a distinct session.
    """
    try:
        blob = json.dumps(doc, sort_keys=True, default=str)
    except (TypeError, ValueError):
        blob = repr(doc)
    sha = hashlib.sha256(blob.encode()).hexdigest()[:12]
    return f"asta-s2-{sub_kind}-{sha}"


async def ingest_semantic_scholar(
    doc: dict[str, Any],
    *,
    link_to: str | None = None,
    target: str | None = None,
    config: WheelerConfig,
    artifact_path: str | None = None,
    used_inputs: list[str] | None = None,
) -> ImportReport:
    """Ingest a parsed Asta Semantic Scholar REST artifact into the graph.

    Args:
        doc: The S2 REST artifact dict (auto-detected: get / search / citations /
            snippet).
        link_to: Optional node id (Plan/Question) that relevant results link to
            via RELEVANT_TO. Applied to get / search / snippet results (those ARE
            relevant to the question). NOT applied to the ``citations`` sub-kind:
            citing papers are NOT relevant to the question. A citation links via
            ``citingPaper -[CITES]-> target`` plus ``WAS_DERIVED_FROM`` the raw
            node, never RELEVANT_TO and never WAS_GENERATED_BY (papers are
            reference entities, not produced by Wheeler; the CITES + lineage edge
            is their linkage, per /wh:close, /wh:graph-link).
        target: For a ``citations`` artifact, the paper being cited (the CLI
            argument, NOT in the output). Either a corpus_id (digit string,
            resolved to its Paper) or a P-id (used directly). Each citing paper
            links ``-[CITES]-> target``. Ignored for the other sub-kinds.
        config: Active Wheeler config.
        artifact_path: Optional path to the raw ``-o`` output file. When given it
            is saved durably and registered as a Dataset node (S2 output is
            structured reference records), linked WAS_GENERATED_BY the run
            Execution (the Dataset is Wheeler-produced), and every generated node
            (papers, snippet Findings) links WAS_DERIVED_FROM it. Best-effort: an
            artifact failure never breaks ingest.
        used_inputs: Optional graph node ids the marshal-in consumed to build
            the request (at minimum the link target that motivated the query).
            The run Execution -[USED]-> each one that exists in the graph
            (existence-guarded, link_once): input-side provenance. A missing id
            is skipped and logged, never fabricated.

    Returns:
        An ImportReport with created / deduped / linked / skipped / used counts.
    """
    from wheeler.tools.graph_tools import _get_backend, execute_tool

    report = ImportReport()
    parsed = parse_semantic_scholar(doc)
    if parsed.sub_kind == "unknown" or not (
        parsed.papers or parsed.citations or parsed.snippets
    ):
        logger.warning(
            "ingest_semantic_scholar: nothing parseable (sub_kind=%s)",
            parsed.sub_kind,
        )
        return report

    backend = await _get_backend(config)
    paper_index = _load_index()
    snippet_index = _load_snippet_index()
    fallback_index = _load_fallback_index()

    # One Execution per RUN. S2 has no run_id, so session_id is a content-sha of
    # the doc keyed by sub-kind; the Execution dedupes on (service, session_id)
    # so re-ingesting the same artifact reuses it rather than duplicating.
    session_id = _session_id_for(doc, parsed.sub_kind)
    exec_id = await _find_execution(
        backend, config, service=_SERVICE_TAG, session_id=session_id
    )
    if not exec_id:
        exec_result = json.loads(
            await execute_tool(
                "add_execution",
                {
                    "kind": _kind_for_sub(parsed.sub_kind),
                    "description": f"Asta Semantic Scholar: {parsed.sub_kind}",
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

    # Input-side provenance: the marshal-in built this request FROM graph nodes
    # (at minimum the link target that motivated the query), so the run USED
    # them. Existence-guarded + link_once, so re-ingest dedupes and a missing id
    # is skipped, never fabricated.
    if exec_id and used_inputs:
        report.used += await _record_used(backend, config, exec_id, used_inputs)

    # Every service output is an artifact: the raw S2 dump registers as a Dataset
    # (D-) node (structured reference records, NOT synthesized writing). S2 has no
    # run_id, so register_output_artifact keys the durable store on a content sha.
    # Best-effort: returns None on any failure and never raises.
    artifact_id: str | None = None
    if artifact_path:
        try:
            from wheeler.integrations.asta.artifacts import register_output_artifact

            artifact_id = await register_output_artifact(
                artifact_path,
                execution_id=exec_id,
                service=_SERVICE_TAG,
                config=config,
                node_type="dataset",
                run_id="",  # S2 has no run_id; durable store falls back to a sha
                benchmark=None,  # S2 provides no cost/time benchmark fields
                description=f"{_SERVICE_TAG} raw output ({parsed.sub_kind})",
            )
        except Exception:
            logger.warning(
                "ingest_semantic_scholar: artifact registration raised (best-effort)",
                exc_info=True,
            )
    if artifact_id:
        report.artifact = artifact_id

    # corpus_id (or fallback key) -> P-id for papers touched this run, so the
    # same paper appearing twice in one artifact is created once.
    seen_papers: dict[str, str] = {}

    if parsed.sub_kind in ("get", "search"):
        for record in parsed.papers:
            await _ingest_paper(
                backend=backend,
                execute_tool=execute_tool,
                config=config,
                record=record,
                session_id=session_id,
                artifact_id=artifact_id,
                link_to=link_to,
                paper_index=paper_index,
                fallback_index=fallback_index,
                seen_papers=seen_papers,
                report=report,
            )

    elif parsed.sub_kind == "citations":
        # Resolve the cited target (the CLI argument, NOT in the artifact). A
        # P-id is used directly; a corpus_id (digit string) is mapped to its
        # Paper. If the target cannot be resolved, the papers are still created
        # but no CITES edge is built (counted via report; logged once).
        target_id = await _resolve_target(backend, config, target)
        if target is not None and target_id is None:
            logger.warning(
                "ingest_semantic_scholar: citation target %r did not resolve to a "
                "node; citing papers will be created without CITES edges",
                target,
            )
        for citation in parsed.citations:
            # CRITICAL: citing papers are NOT relevant to the question. A citation
            # links via citingPaper -[CITES]-> target plus WAS_DERIVED_FROM the
            # raw node; it is never RELEVANT_TO the question and never
            # WAS_GENERATED_BY (papers are reference entities, not produced by
            # Wheeler). So link_to is forced to None here. See /wh:close and
            # /wh:graph-link: "Papers are never orphans. They are reference
            # entities, not produced by Wheeler."
            paper_id = await _ingest_paper(
                backend=backend,
                execute_tool=execute_tool,
                config=config,
                record=citation.citing,
                session_id=session_id,
                artifact_id=artifact_id,
                link_to=None,
                paper_index=paper_index,
                fallback_index=fallback_index,
                seen_papers=seen_papers,
                report=report,
            )
            # citingPaper -[CITES]-> target (the cited paper). Builds the
            # citation graph. link_once-guarded so re-ingest never duplicates.
            if paper_id and target_id:
                if await _link_once(backend, config, paper_id, "CITES", target_id):
                    report.linked += 1

    elif parsed.sub_kind == "snippet":
        for snippet in parsed.snippets:
            await _ingest_snippet(
                backend=backend,
                execute_tool=execute_tool,
                config=config,
                snippet=snippet,
                session_id=session_id,
                exec_id=exec_id,
                artifact_id=artifact_id,
                link_to=link_to,
                paper_index=paper_index,
                fallback_index=fallback_index,
                snippet_index=snippet_index,
                seen_papers=seen_papers,
                report=report,
            )

    _save_index(paper_index)
    _save_snippet_index(snippet_index)
    _save_fallback_index(fallback_index)
    logger.info(
        "ingest_semantic_scholar: sub_kind=%s created=%d deduped=%d linked=%d "
        "skipped=%d used=%d (exec=%s)",
        parsed.sub_kind,
        report.created,
        report.deduped,
        report.linked,
        report.skipped,
        report.used,
        exec_id,
    )
    return report


async def _resolve_target(
    backend, config: WheelerConfig, target: str | None
) -> str | None:
    """Resolve a citation target to a Paper node id, or None.

    A ``P-`` prefixed string is treated as a node id and verified to exist. Any
    other non-empty string is treated as a corpus_id (normalized to a digit
    string) and resolved to its Paper via the shared lookup. Returns None when
    the target is absent, unresolvable, or points at a missing node.
    """
    if not target:
        return None
    t = target.strip()
    if t.upper().startswith("P-"):
        # A Wheeler Paper id passed directly; only use it if the node exists.
        if await _paper_exists(backend, config, t):
            return t
        return None
    cid = _normalize_corpus_id(t)
    if not cid:
        return None
    return await _find_paper_by_corpus_id(backend, config, cid)


async def _ingest_paper(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    record: S2Paper,
    session_id: str,
    artifact_id: str | None,
    link_to: str | None,
    paper_index: dict[str, str],
    fallback_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> str | None:
    """Dedupe-or-create one Paper, wire provenance, return its node id.

    Dedupe prefers ``corpus_id`` (the cross-tool key, persisted to the shared
    corpus_id index). When the paper carries NO corpus_id (the default S2 field
    set omits it), it falls back to the s2 paperId / DOI, which IS persisted (to
    a SEPARATE fallback index, plus a graph read on the parked
    ``custom_s2_paper_id`` / ``custom_doi`` props), so a corpus-id-less paper
    re-ingested across runs reuses its node instead of forking a duplicate. The
    fallback key is kept out of the shared corpus_id index so that index stays
    keyed strictly on corpus_id and compatible with Paper Finder / Theorizer.
    """
    cid = record.corpus_id
    run_key = cid or record.fallback_key
    existing: str | None = None

    # 1. Already created/resolved this run (by corpus_id or fallback key). This
    # is an in-run cache hit, NOT a graph dedupe, so it does NOT increment
    # report.deduped: the same paper appearing twice in one artifact (e.g. two
    # snippet hits on one corpus_id) is a single create, with no extra dedupe
    # count. Otherwise created/deduped would be asymmetric on re-ingest (an
    # in-run repeat would count as deduped on re-run but not as created on the
    # first run). The paper_id is still recorded once.
    if run_key and run_key in seen_papers:
        existing = seen_papers[run_key]
        if existing not in report.paper_ids:
            report.paper_ids.append(existing)
        return existing

    # 2. Persisted cross-tool corpus_id index. Only trust the hit if the node
    # still lives in the graph: a stale id (deleted/pruned node) would make
    # link_once target a missing node and silently drop the CITES/APPEARS_IN
    # edge. Drop the dead entry and fall through to a fresh corpus_id read.
    existing = paper_index.get(cid) if cid else None
    if existing and not await _paper_exists(backend, config, existing):
        existing = None
        if cid:
            paper_index.pop(cid, None)
    # 3. Project-aware graph read on corpus_id.
    if not existing and cid:
        existing = await _find_paper_by_corpus_id(backend, config, cid)

    # 4. Corpus-id-less papers: resolve via the persisted fallback index (s2
    # paperId / DOI), stale-guarded like the corpus_id index, then a graph read
    # on the parked custom_s2_paper_id / custom_doi props. This is the cross-run
    # dedupe path the default S2 field set (no corpusId) depends on.
    fb_keys = _fallback_keys(record) if not cid else []
    if not existing and fb_keys:
        for fb_key in fb_keys:
            candidate = fallback_index.get(fb_key)
            if candidate and not await _paper_exists(backend, config, candidate):
                fallback_index.pop(fb_key, None)
                candidate = None
            if candidate:
                existing = candidate
                break
        if not existing:
            existing = await _find_paper_by_fallback(backend, config, record)

    if existing:
        report.deduped += 1
        if existing not in report.paper_ids:
            report.paper_ids.append(existing)
        if cid:
            paper_index[cid] = existing
        for fb_key in fb_keys:
            fallback_index[fb_key] = existing
        if run_key:
            seen_papers[run_key] = existing
        return existing

    # 4. Create. A record with no corpus_id, title, and fallback was dropped at
    # parse time, so a usable title (or a synthesized one) is available here.
    add_args: dict[str, Any] = {
        "title": record.title or f"Paper {cid or record.fallback_key}",
        "authors": record.authors,
        "year": record.year,
        "corpus_id": cid,
        "custom": record.custom,
        "session_id": session_id,
        "service": _SERVICE_TAG,
    }
    result = json.loads(await execute_tool("add_paper", add_args, config))
    paper_id = result.get("node_id")
    if not paper_id or "error" in result:
        logger.warning(
            "ingest_semantic_scholar: add_paper failed for corpus_id=%s key=%s: %s",
            cid,
            record.fallback_key,
            result,
        )
        report.skipped += 1
        return None
    report.created += 1
    report.paper_ids.append(paper_id)
    if cid:
        paper_index[cid] = paper_id
    for fb_key in fb_keys:
        fallback_index[fb_key] = paper_id
    if run_key:
        seen_papers[run_key] = paper_id

    # Papers are REFERENCE ENTITIES, not produced by Wheeler (per /wh:close and
    # /wh:graph-link: "Papers are never orphans. They are reference entities,
    # not produced by Wheeler"). A Semantic Scholar result (get / search /
    # snippet / citing paper) is part of the result set, not a node the run
    # produced, so it carries NO WAS_GENERATED_BY edge. Its lineage is
    # WAS_DERIVED_FROM the raw output artifact; its semantic edges (RELEVANT_TO,
    # CITES, APPEARS_IN) are added by the caller.
    if artifact_id and await _link_once(
        backend, config, paper_id, "WAS_DERIVED_FROM", artifact_id
    ):
        report.linked += 1
    # Paper RELEVANT_TO the link target (the Question/Plan that prompted it).
    if link_to and await _link_once(backend, config, paper_id, "RELEVANT_TO", link_to):
        report.linked += 1
    return paper_id


async def _ingest_snippet(
    *,
    backend,
    execute_tool,
    config: WheelerConfig,
    snippet: S2Snippet,
    session_id: str,
    exec_id: str,
    artifact_id: str | None,
    link_to: str | None,
    paper_index: dict[str, str],
    fallback_index: dict[str, str],
    snippet_index: dict[str, str],
    seen_papers: dict[str, str],
    report: ImportReport,
) -> None:
    """Bucket one snippet into a Finding -[APPEARS_IN]-> its Paper.

    The snippet's paper is deduped-or-created first (so APPEARS_IN targets a real
    node), then the Finding is created (or reused via the content-hash index) and
    linked. The snippet text is the Finding description, the score its confidence,
    a short prefix the title.
    """
    # 1. Resolve the paper the snippet appears in (corpusId is present in
    # snippet-search output, so corpus_id dedupe works).
    paper_id = await _ingest_paper(
        backend=backend,
        execute_tool=execute_tool,
        config=config,
        record=snippet.paper,
        session_id=session_id,
        artifact_id=artifact_id,
        link_to=link_to,
        paper_index=paper_index,
        fallback_index=fallback_index,
        seen_papers=seen_papers,
        report=report,
    )
    if paper_id is None:
        # Could not create the paper; the snippet Finding would be an orphan.
        return

    # 2. Dedupe-or-create the snippet Finding on a content hash (snippets have no
    # external id). A stale index hit (deleted node) is dropped so we recreate.
    key = _snippet_key(snippet.paper.corpus_id, snippet.text)
    finding_id = snippet_index.get(key)
    if finding_id and not await _finding_exists(backend, config, finding_id):
        finding_id = None
        snippet_index.pop(key, None)

    if finding_id:
        report.deduped += 1
    else:
        # confidence is the S2 relevance score, clamped to [0, 1] for the model.
        confidence = snippet.score
        if confidence < 0.0:
            confidence = 0.0
        elif confidence > 1.0:
            confidence = 1.0
        title = snippet.text[:80]
        finding_custom: dict[str, Any] = {}
        if snippet.kind:
            finding_custom["snippet_kind"] = snippet.kind
        if snippet.paper.corpus_id:
            finding_custom["paper_corpus_id"] = snippet.paper.corpus_id
        finding_result = json.loads(
            await execute_tool(
                "add_finding",
                {
                    "description": snippet.text,
                    "title": title,
                    "confidence": confidence,
                    "artifact_type": "snippet",
                    "session_id": session_id,
                    "service": _SERVICE_TAG,
                },
                config,
            )
        )
        finding_id = finding_result.get("node_id")
        if not finding_id or "error" in finding_result:
            logger.warning(
                "ingest_semantic_scholar: add_finding failed for snippet on "
                "corpus_id=%s",
                snippet.paper.corpus_id,
            )
            report.skipped += 1
            return
        report.created += 1
        snippet_index[key] = finding_id

        # Park snippet kind + paper corpus_id so they are queryable.
        if finding_custom:
            await _stamp_custom(execute_tool, config, finding_id, finding_custom)

        # Provenance for the freshly created Finding.
        if exec_id and await _link_once(
            backend, config, finding_id, "WAS_GENERATED_BY", exec_id
        ):
            report.linked += 1
        if artifact_id and await _link_once(
            backend, config, finding_id, "WAS_DERIVED_FROM", artifact_id
        ):
            report.linked += 1
        if link_to and await _link_once(
            backend, config, finding_id, "RELEVANT_TO", link_to
        ):
            report.linked += 1

    # 3. Finding -[APPEARS_IN]-> its Paper (link_once-guarded on every run).
    if await _link_once(backend, config, finding_id, "APPEARS_IN", paper_id):
        report.linked += 1


async def _stamp_custom(
    execute_tool, config: WheelerConfig, node_id: str, custom: dict[str, Any]
) -> None:
    """Stamp custom-bag scalars onto an existing node via update_node.

    add_finding does not forward ``custom`` into create_node, so the bag is
    applied with a follow-up update_node (``custom`` is a first-class NodeBase
    field; the backend flattens it to discrete ``custom_<key>`` props, so
    ``custom_snippet_kind`` / ``custom_paper_corpus_id`` are queryable).
    Best-effort: a failure here never breaks ingest.
    """
    if not custom:
        return
    try:
        result = json.loads(
            await execute_tool(
                "update_node", {"node_id": node_id, "custom": dict(custom)}, config
            )
        )
        if "error" in result:
            logger.warning(
                "ingest_semantic_scholar: custom-bag update failed for %s: %s",
                node_id,
                result,
            )
    except Exception:
        logger.warning(
            "ingest_semantic_scholar: custom-bag update raised for %s (best-effort)",
            node_id,
            exc_info=True,
        )
