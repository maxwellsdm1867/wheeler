"""Marshal-out (deterministic): ingest an Asta Paper Finder artifact.

This is the ONLY module that imports ``execute_tool``, and it imports it
lazily (function-local), mirroring ``wheeler/validation/ledger.py``. Every
graph write routes through ``execute_tool`` so the triple-write, write
receipt, trace id, and embedding wiring all fire. Reads (dedupe by corpus_id,
edge existence for ``link_once``) go through the same cached backend the
dispatch path uses, and are project-aware (Community Edition namespacing).

Invariants:
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses
    one cached backend singleton and Neo4j forbids concurrent queries.
  - Idempotent. Papers dedupe on ``corpus_id``; re-ingest reuses the existing
    ``P-`` id. Edges are guarded by ``link_once`` because the backend's
    ``create_relationship`` is a bare CREATE that would duplicate on re-run.
  - One Execution per RUN (not per paper), tagged service ``asta:paper-finder``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig

from .schemas import PaperRecord, parse_paper_finder

logger = logging.getLogger(__name__)

# Persisted (corpus_id -> Wheeler P-id) map so re-ingest across runs is a no-op.
_INDEX_REL_PATH = ".wheeler/integrations/paper_finder_index.json"

_SERVICE_TAG = "asta:paper-finder"


@dataclass
class ImportReport:
    """Outcome of one ingest run."""

    created: int = 0
    deduped: int = 0
    linked: int = 0
    skipped: int = 0
    execution_id: str = ""
    artifact: str = ""
    paper_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "deduped": self.deduped,
            "linked": self.linked,
            "skipped": self.skipped,
            "execution_id": self.execution_id,
            "artifact": self.artifact,
            "paper_ids": list(self.paper_ids),
        }


# ---------------------------------------------------------------------------
# On-disk corpus_id -> node-id index
# ---------------------------------------------------------------------------


def _index_path() -> Path:
    return Path(_INDEX_REL_PATH)


def _load_index() -> dict[str, str]:
    path = _index_path()
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        logger.warning("ingest: could not read index %s, starting fresh", path)
    return {}


def _save_index(index: dict[str, str]) -> None:
    path = _index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True))
        tmp.replace(path)
    except OSError:
        logger.error("ingest: could not persist index %s (best-effort)", path, exc_info=True)


# ---------------------------------------------------------------------------
# Project-aware reads (dedupe + link_once)
# ---------------------------------------------------------------------------


async def _find_paper_by_corpus_id(backend, config: WheelerConfig, corpus_id: str) -> str | None:
    """Return an existing Paper id for this corpus_id, or None.

    Project-aware: scoped to ``config.neo4j.project_tag`` when isolation is on,
    mirroring the read scoping in the query handlers.
    """
    if not corpus_id:
        return None
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (p:Paper {corpus_id: $cid}) "
            "WHERE p._wheeler_project = $ptag RETURN p.id AS id LIMIT 1"
        )
        params = {"cid": corpus_id, "ptag": ptag}
    else:
        query = "MATCH (p:Paper {corpus_id: $cid}) RETURN p.id AS id LIMIT 1"
        params = {"cid": corpus_id}
    rows = await backend.run_cypher(query, params)
    if rows:
        return rows[0].get("id")
    return None


async def _edge_exists(backend, src_id: str, rel: str, tgt_id: str) -> bool:
    """Return True if a src -[rel]-> tgt edge already exists (link_once guard).

    Keyed on node ids only (ids are globally unique), so no project clause is
    needed: a matching id pair already lives in the active namespace.
    """
    rows = await backend.run_cypher(
        "MATCH (a {id: $src})-[r]->(b {id: $tgt}) "
        "WHERE type(r) = $rel RETURN count(r) AS c",
        {"src": src_id, "tgt": tgt_id, "rel": rel},
    )
    return bool(rows and rows[0].get("c", 0) > 0)


async def _link_once(
    backend, config: WheelerConfig, src_id: str, rel: str, tgt_id: str,
) -> bool:
    """Create src -[rel]-> tgt only if it does not already exist.

    Returns True if a new edge was created, False if it already existed or
    the link failed. Writes route through execute_tool for triple-write.
    """
    from wheeler.tools.graph_tools import execute_tool

    if await _edge_exists(backend, src_id, rel, tgt_id):
        return False
    result_str = await execute_tool(
        "link_nodes",
        {"source_id": src_id, "target_id": tgt_id, "relationship": rel},
        config,
    )
    result = json.loads(result_str)
    return result.get("status") == "linked"


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


async def ingest_paper_finder(
    doc: dict[str, Any],
    *,
    link_to: str | None,
    config: WheelerConfig,
    artifact_path: str | None = None,
) -> ImportReport:
    """Ingest a parsed Asta Paper Finder artifact into the knowledge graph.

    Args:
        doc: The LiteratureSearchResult dict (from transport.run_asta).
        link_to: Optional node id (Plan/Question) every paper is linked to
            via RELEVANT_TO.
        config: Active Wheeler config.
        artifact_path: Optional path to the raw ``-o`` output file. When given,
            it is registered as a Dataset node (every service output is an
            artifact), linked WAS_GENERATED_BY the run Execution, and every
            Paper is linked WAS_DERIVED_FROM it. Best-effort: an artifact
            failure never breaks paper ingest.

    Returns:
        An ImportReport with created / deduped / linked / skipped counts.
    """
    from wheeler.tools.graph_tools import execute_tool
    from wheeler.tools.graph_tools import _get_backend

    report = ImportReport()
    records: list[PaperRecord] = parse_paper_finder(doc)
    if not records:
        logger.warning("ingest_paper_finder: no parseable papers in artifact")
        return report

    backend = await _get_backend(config)
    index = _load_index()

    # One Execution per RUN, tagged with the service. session_id correlates
    # every node written this turn (validate_contract audits on session_id).
    query_text = str(doc.get("query", ""))[:80]
    session_id = str(doc.get("thread_id") or "") or f"asta-pf-{abs(hash(query_text)) & 0xffffffff:08x}"
    exec_result_str = await execute_tool(
        "add_execution",
        {
            "kind": "paper-search",
            "description": f"Asta Paper Finder: {query_text}",
            "agent_id": "asta",
            "status": "completed",
            "session_id": session_id,
            "service": _SERVICE_TAG,
        },
        config,
    )
    exec_result = json.loads(exec_result_str)
    exec_id = exec_result.get("node_id", "")
    report.execution_id = exec_id

    # Every service output is an artifact: register the raw -o JSON dump as a
    # Dataset node, linked WAS_GENERATED_BY the run Execution. Best-effort:
    # register_output_artifact returns None on any failure and never raises, so
    # an artifact problem cannot break paper ingest.
    from .artifacts import register_output_artifact

    artifact_id = await register_output_artifact(
        artifact_path,
        execution_id=exec_id,
        service=_SERVICE_TAG,
        config=config,
        description=f"{_SERVICE_TAG} raw output",
    )
    if artifact_id:
        report.artifact = artifact_id

    # corpus_id -> P-id for papers seen this run (so a citing paper can be
    # linked to a cited paper that was just created in the same run).
    seen_this_run: dict[str, str] = {}

    for record in records:
        paper_id = await _ingest_one_paper(
            backend, execute_tool, config, record, index, session_id, exec_id, report,
        )
        if paper_id is None:
            report.skipped += 1
            continue
        if record.corpus_id:
            seen_this_run[record.corpus_id] = paper_id

        # Paper WAS_DERIVED_FROM the raw output artifact (link_once-guarded),
        # so every paper chains back through the artifact to the service run.
        if artifact_id:
            if await _link_once(
                backend, config, paper_id, "WAS_DERIVED_FROM", artifact_id,
            ):
                report.linked += 1

        # Paper RELEVANT_TO the link target (e.g. the Question/Plan that
        # prompted the search).
        if link_to:
            if await _link_once(backend, config, paper_id, "RELEVANT_TO", link_to):
                report.linked += 1

    # Second pass: citation contexts -> CITES edges. Done after all papers
    # exist so a cited corpus_id created this run is resolvable.
    for record in records:
        if not record.cited_corpus_ids:
            continue
        src_paper_id = seen_this_run.get(record.corpus_id) or index.get(record.corpus_id)
        if not src_paper_id:
            continue
        for cited_corpus in record.cited_corpus_ids:
            tgt_paper_id = seen_this_run.get(cited_corpus) or index.get(cited_corpus)
            if not tgt_paper_id:
                # Cited paper not in our graph; skip (no orphan stub creation).
                continue
            if await _link_once(backend, config, src_paper_id, "CITES", tgt_paper_id):
                report.linked += 1

    _save_index(index)
    logger.info(
        "ingest_paper_finder: created=%d deduped=%d linked=%d skipped=%d (exec=%s)",
        report.created, report.deduped, report.linked, report.skipped, exec_id,
    )
    return report


async def _ingest_one_paper(
    backend,
    execute_tool,
    config: WheelerConfig,
    record: PaperRecord,
    index: dict[str, str],
    session_id: str,
    exec_id: str,
    report: ImportReport,
) -> str | None:
    """Dedupe-or-create one paper. Returns its node id, or None on failure."""
    # Dedupe: prefer the persisted index, then a project-aware graph read.
    existing = index.get(record.corpus_id) if record.corpus_id else None
    if not existing and record.corpus_id:
        existing = await _find_paper_by_corpus_id(backend, config, record.corpus_id)

    if existing:
        report.deduped += 1
        report.paper_ids.append(existing)
        if record.corpus_id:
            index[record.corpus_id] = existing
        return existing

    add_args: dict[str, Any] = {
        "title": record.title or f"Paper {record.corpus_id}",
        "authors": record.authors,
        "year": record.year,
        "corpus_id": record.corpus_id,
        "custom": record.custom,
        "session_id": session_id,
        "service": _SERVICE_TAG,
    }
    result_str = await execute_tool("add_paper", add_args, config)
    result = json.loads(result_str)
    paper_id = result.get("node_id")
    if not paper_id or "error" in result:
        logger.warning("ingest: add_paper failed for corpus_id=%s: %s", record.corpus_id, result)
        return None

    report.created += 1
    report.paper_ids.append(paper_id)
    if record.corpus_id:
        index[record.corpus_id] = paper_id

    # Provenance: Paper WAS_GENERATED_BY the run Execution (link_once-guarded).
    if exec_id:
        if await _link_once(backend, config, paper_id, "WAS_GENERATED_BY", exec_id):
            report.linked += 1

    return paper_id
