"""Shared marshal-out helpers for the Asta adapters.

This module holds the genuinely-shared marshal-out helpers used by more than
one adapter (``ingest.py`` = Paper Finder, ``theorizer.py``,
``semantic_scholar.py``, ``artifacts.py``). It is a neutral home so the adapters
import these helpers from one place instead of reaching into the Paper Finder
module.

The helpers are:
  - ``ImportReport``: the outcome dataclass of one ingest run.
  - the persisted corpus_id -> node-id index load/save helpers.
  - the project-aware read helpers (dedupe by corpus_id, Execution lookup,
    Paper existence guard).
  - the edge-existence / ``link_once`` write helpers.

Like the adapters, every graph WRITE here routes through ``execute_tool``,
imported lazily (function-local) so it stays a chokepoint and ``graph_tools/``
stays asta-free (mirrors ``wheeler/validation/ledger.py``). Reads go through the
same cached backend the dispatch path uses, and are project-aware (Community
Edition namespacing).

Invariants:
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses
    one cached backend singleton and Neo4j forbids concurrent queries.
  - Idempotent. Edges are guarded by ``link_once`` because the backend's
    ``create_relationship`` is a bare CREATE that would duplicate on re-run.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)

# Persisted (corpus_id -> Wheeler P-id) map so re-ingest across runs is a no-op.
_INDEX_REL_PATH = ".wheeler/integrations/paper_finder_index.json"


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


async def _find_execution(
    backend, config: WheelerConfig, *, service: str, session_id: str
) -> str | None:
    """Return an existing Execution id for this (service, session_id), or None.

    Makes the run Execution itself idempotent: re-ingesting the same artifact
    reuses the existing Execution (keyed on its stable run id = session_id)
    instead of creating a duplicate node and stale WAS_GENERATED_BY edges. Both
    fields are needed because session_id alone is not unique across services.
    Project-aware, mirroring the read scoping in the query handlers.
    """
    if not service or not session_id:
        return None
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (x:Execution {service: $svc, session_id: $sid}) "
            "WHERE x._wheeler_project = $ptag RETURN x.id AS id LIMIT 1"
        )
        params = {"svc": service, "sid": session_id, "ptag": ptag}
    else:
        query = (
            "MATCH (x:Execution {service: $svc, session_id: $sid}) "
            "RETURN x.id AS id LIMIT 1"
        )
        params = {"svc": service, "sid": session_id}
    rows = await backend.run_cypher(query, params)
    if rows:
        return rows[0].get("id")
    return None


async def _paper_exists(backend, config: WheelerConfig, paper_id: str) -> bool:
    """Return True if a Paper with this id still lives in the graph.

    Guards the persisted corpus_id index against staleness. A node deleted by a
    prior teardown (or a pruned graph) leaves a dangling P-id in the on-disk
    index; trusting it would make a later ``link_once`` target a dead node, and
    the backend's link would fail and SILENTLY DROP the SUPPORTS/CONTRADICTS
    edge, losing provenance. Mirrors the Finding/Hypothesis existence guards.
    Project-aware, matching the read scoping in the query handlers.
    """
    if not paper_id:
        return False
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (p:Paper {id: $id}) "
            "WHERE p._wheeler_project = $ptag RETURN p.id AS id LIMIT 1"
        )
        params = {"id": paper_id, "ptag": ptag}
    else:
        query = "MATCH (p:Paper {id: $id}) RETURN p.id AS id LIMIT 1"
        params = {"id": paper_id}
    rows = await backend.run_cypher(query, params)
    return bool(rows)


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
