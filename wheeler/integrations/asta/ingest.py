"""Marshal-out (deterministic): ingest an Asta Paper Finder artifact.

A marshal-out module: it imports ``execute_tool`` lazily (function-local),
mirroring ``wheeler/validation/ledger.py``. Every graph write routes through
``execute_tool`` so the triple-write, write receipt, trace id, and embedding
wiring all fire. The shared read/link/dedupe helpers (``_link_once`` /
``_edge_exists`` / ``_find_paper_by_corpus_id`` / ``_paper_exists`` /
``_find_execution`` + the persisted corpus_id index + ``ImportReport``) live in
``_marshal.py``; this module imports them and keeps only Paper-Finder-specific
logic (``ingest_paper_finder`` and ``_ingest_one_paper``). Reads (dedupe by
corpus_id, edge existence for ``link_once``) go through the same cached backend
the dispatch path uses, and are project-aware (Community Edition namespacing).

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
from typing import Any

from wheeler.config import WheelerConfig

from ._marshal import (
    ImportReport,
    _find_execution,
    _find_paper_by_corpus_id,
    _link_once,
    _load_index,
    _paper_exists,
    _save_index,
)
from .schemas import PaperRecord, parse_paper_finder

logger = logging.getLogger(__name__)

_SERVICE_TAG = "asta:paper-finder"


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
    # The Execution is itself idempotent: re-ingesting the same artifact reuses
    # the existing Execution (keyed on service + session_id) instead of creating
    # a duplicate node and stale WAS_GENERATED_BY edges.
    query_text = str(doc.get("query", ""))[:80]
    pf_run_id = str(doc.get("thread_id") or "")
    session_id = pf_run_id or f"asta-pf-{abs(hash(query_text)) & 0xffffffff:08x}"
    exec_id = await _find_execution(
        backend, config, service=_SERVICE_TAG, session_id=session_id
    )
    if not exec_id:
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
        # Stamp the run id onto the Execution custom bag so paper-finder runs are
        # benchmarkable by the same query shape as theorizer (custom_run_id).
        if exec_id and pf_run_id:
            update_result_str = await execute_tool(
                "update_node",
                {"node_id": exec_id, "custom": {"run_id": pf_run_id}},
                config,
            )
            update_result = json.loads(update_result_str)
            if "error" in update_result:
                logger.warning(
                    "ingest_paper_finder: run_id stamp failed for %s: %s",
                    exec_id, update_result,
                )
    report.execution_id = exec_id

    # Every service output is an artifact: register the raw -o JSON dump as a
    # Dataset node, linked WAS_GENERATED_BY the run Execution. Best-effort:
    # register_output_artifact returns None on any failure and never raises, so
    # an artifact problem cannot break paper ingest.
    from .artifacts import register_output_artifact

    # Paper Finder output is structured reference records, so its raw node is a
    # Dataset (D-). run_id is the thread_id when present (its closest stable run
    # key, computed above), else the durable store falls back to a content sha.
    artifact_id = await register_output_artifact(
        artifact_path,
        execution_id=exec_id,
        service=_SERVICE_TAG,
        config=config,
        node_type="dataset",
        run_id=pf_run_id,
        benchmark={"service": _SERVICE_TAG, "run_id": pf_run_id} if pf_run_id else None,
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
    # Dedupe: prefer the persisted index, then a project-aware graph read. The
    # persisted index hit is only trusted if the node still lives in the graph;
    # a stale id (deleted/pruned node) is dropped so we fall through to a fresh
    # corpus_id read or create. Trusting a dead id would make link_once target a
    # missing node and silently drop the resulting edge.
    existing = index.get(record.corpus_id) if record.corpus_id else None
    if existing and not await _paper_exists(backend, config, existing):
        existing = None
        if record.corpus_id:
            index.pop(record.corpus_id, None)
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
