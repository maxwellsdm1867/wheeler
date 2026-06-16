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
    """Outcome of one ingest run.

    ``failed`` / ``job_state`` carry the external-job lifecycle outcome: an
    ingest only fabricates output nodes when the job VERIFIABLY succeeded. A
    failed or incomplete job still leaves a (failed) Execution so the attempt is
    visible (``failed=True``, ``job_state`` = the job's own state), but no
    fabricated Findings/Hypotheses/Papers, so a failed run never masquerades as a
    clean completed one.
    """

    created: int = 0
    deduped: int = 0
    linked: int = 0
    skipped: int = 0
    used: int = 0
    plan_linked: int = 0
    execution_id: str = ""
    artifact: str = ""
    paper_ids: list[str] = field(default_factory=list)
    failed: bool = False
    job_state: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "deduped": self.deduped,
            "linked": self.linked,
            "skipped": self.skipped,
            "used": self.used,
            "plan_linked": self.plan_linked,
            "execution_id": self.execution_id,
            "artifact": self.artifact,
            "paper_ids": list(self.paper_ids),
            "failed": self.failed,
            "job_state": self.job_state,
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


# ---------------------------------------------------------------------------
# Input-side provenance: Execution -[USED]-> the marshalled-in graph nodes
# ---------------------------------------------------------------------------


async def _node_exists(backend, config: WheelerConfig, node_id: str) -> bool:
    """Return True if a node with this id (any label) lives in the graph.

    The generic, label-agnostic sibling of ``_paper_exists``: a marshalled-in
    USED input can be any node type (an OpenQuestion, a Finding, a Plan, a
    Dataset), so the guard matches on id alone rather than a fixed label. Keyed
    on the globally-unique id, project-aware (scoped to ``project_tag`` when
    Community Edition isolation is on, mirroring the read scoping in the query
    handlers). Used to existence-guard every USED edge so the run never
    fabricates an input it cannot find: a missing id is skipped, never created.
    """
    if not node_id:
        return False
    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        query = (
            "MATCH (n {id: $id}) "
            "WHERE n._wheeler_project = $ptag RETURN n.id AS id LIMIT 1"
        )
        params = {"id": node_id, "ptag": ptag}
    else:
        query = "MATCH (n {id: $id}) RETURN n.id AS id LIMIT 1"
        params = {"id": node_id}
    rows = await backend.run_cypher(query, params)
    return bool(rows)


async def _link_execution_to_plan(
    backend, config: WheelerConfig, exec_id: str, link_to: str | None,
) -> bool:
    """Anchor the run Execution to a Plan: ``Execution -[AROSE_FROM]-> Plan``.

    Plan/session lifecycle integration. When the marshal-in ``link_to`` is a Plan
    id (``PL-`` prefix), the Asta run is a step OF that plan, so the run Execution
    -[AROSE_FROM]-> the Plan: the run AROSE FROM the plan that motivated it. This
    puts the Execution itself into the plan's provenance chain, on top of the
    results that link RELEVANT_TO the Plan as today. With this edge a Plan, its
    Asta Executions, and their outputs form one chain (see /wh:plan, /wh:execute,
    /wh:close).

    Direction rationale: ``AROSE_FROM`` reads as "the run arose from the plan",
    matching the proven model already used by the Theorizer adapter (a generated
    parent Finding -[AROSE_FROM]-> its ``link_to`` Plan/Question). ``CONTAINS``
    (Plan CONTAINS the step) was considered but rejected: CONTAINS is the
    structural parent/child edge (e.g. a theory Finding CONTAINS its law
    Hypotheses); AROSE_FROM is the discovery/derivation edge, which is exactly
    what an Asta run is relative to the plan that prompted it. Keeping the same
    relationship the Theorizer already uses also makes the plan-side query
    uniform across adapters.

    No-op (returns False) for a non-Plan ``link_to`` (anything not ``PL-``),
    a blank id, or a Plan id not in the graph (existence-guarded with
    ``_node_exists``, so a stale/missing id is skipped, never fabricated).
    Idempotent via ``_link_once``, so re-ingest does not duplicate the edge.
    Returns True only when a NEW edge was created.
    """
    if not exec_id or not link_to:
        return False
    plan_id = link_to.strip()
    if not plan_id.upper().startswith("PL-"):
        return False
    if plan_id == exec_id:
        return False
    if not await _node_exists(backend, config, plan_id):
        logger.warning(
            "link_execution_to_plan: skipping missing Plan id %r (not in graph)",
            plan_id,
        )
        return False
    return await _link_once(backend, config, exec_id, "AROSE_FROM", plan_id)


async def _record_used(
    backend, config: WheelerConfig, exec_id: str, used_inputs: list[str],
) -> int:
    """Record Execution -[USED]-> each existing marshalled-in graph node.

    Input-side provenance: the marshal-in synthesized the tool payload FROM
    these graph nodes (the question, the Findings seeded into extraction, the
    gap that shaped the query), so the run USED them. The chain is then
    transitive without per-output edges:
    ``output -[WAS_GENERATED_BY]-> Execution -[USED]-> input``.

    Each id is existence-guarded with ``_node_exists`` (a missing id is skipped
    and logged, never fabricated) and linked with ``_link_once`` (so re-ingest
    dedupes the edge and a USED already recorded by another path, e.g. the
    Theorizer evidence-paper USED, is not duplicated). Self-edges (an id equal to
    the Execution) and blanks are skipped. Returns the count of USED edges newly
    created this call.
    """
    if not exec_id or not used_inputs:
        return 0
    linked = 0
    seen: set[str] = set()
    for raw_id in used_inputs:
        node_id = (raw_id or "").strip()
        if not node_id or node_id == exec_id or node_id in seen:
            continue
        seen.add(node_id)
        if not await _node_exists(backend, config, node_id):
            logger.warning(
                "record_used: skipping missing input id %r (not in graph)",
                node_id,
            )
            continue
        if await _link_once(backend, config, exec_id, "USED", node_id):
            linked += 1
    return linked


# ---------------------------------------------------------------------------
# External-job lifecycle: did the job actually run, and the Execution status
# ---------------------------------------------------------------------------


# A2A Task.status.state values that mean the job did NOT finish successfully.
# Anything other than "completed" means the outputs (if any) are partial or
# absent, so we must not ingest them as if real. "completed" is the only success.
_A2A_TERMINAL_OK = "completed"


@dataclass
class JobOutcome:
    """Whether an external-service job VERIFIABLY produced a usable artifact.

    ``ok`` gates whether the ingest fabricates output nodes. ``state`` is the
    job's own reported state (an A2A Task ``status.state``, or a synthetic token
    for non-Task shapes), surfaced onto the Execution so a failed run is visible
    and queryable. ``detail`` is a short human reason for a failure.
    """

    ok: bool
    state: str
    detail: str = ""


def _a2a_status_message(doc: dict[str, Any]) -> str:
    """Best-effort human text from an A2A Task status.message.parts[0].text."""
    status = doc.get("status")
    if not isinstance(status, dict):
        return ""
    msg = status.get("message")
    if not isinstance(msg, dict):
        return ""
    parts = msg.get("parts")
    if isinstance(parts, list) and parts and isinstance(parts[0], dict):
        text = parts[0].get("text")
        if isinstance(text, str):
            return text.strip()[:300]
    return ""


def job_outcome(doc: Any) -> JobOutcome:
    """Decide whether an external job's artifact represents a SUCCESSFUL run.

    The failsafe gate before any output is ingested. We do NOT trust the mere
    presence of an artifact: an A2A Task can come back ``status.state="failed"``
    (or canceled / rejected / input-required / working) with a partial or empty
    artifacts list, and ingesting that as if real would forge a record. So:

      - ``None`` (the transport returned nothing: non-zero exit, timeout, missing
        / empty / unparseable artifact) -> NOT ok, state "missing".
      - a non-dict -> NOT ok, state "invalid".
      - an A2A Task (has a ``status`` dict with a ``state``): ok IFF
        ``state == "completed"``; otherwise NOT ok, state = the reported state.
      - any other dict (a LiteratureSearchResult, a report envelope: no A2A
        status block): ok (the transport already rejected the empty / unparseable
        cases, so a present dict is a usable artifact). state "completed".

    Defensive: never raises.
    """
    if doc is None:
        return JobOutcome(ok=False, state="missing", detail="no artifact returned")
    if not isinstance(doc, dict):
        return JobOutcome(
            ok=False, state="invalid", detail=f"artifact is {type(doc).__name__}, not an object"
        )
    status = doc.get("status")
    if isinstance(status, dict) and status.get("state") is not None:
        state = str(status.get("state")).strip().lower()
        if state == _A2A_TERMINAL_OK:
            return JobOutcome(ok=True, state=state)
        return JobOutcome(
            ok=False,
            state=state or "unknown",
            detail=_a2a_status_message(doc) or f"job state was {state!r}, not completed",
        )
    # No A2A status block: a plain result dict. The transport already guarantees
    # it is a non-empty parseable object, so the job produced a usable artifact.
    return JobOutcome(ok=True, state="completed")


async def mark_execution_failed(
    config: WheelerConfig, exec_id: str, outcome: JobOutcome
) -> None:
    """Mark a run Execution as failed and stamp the job-failure diagnostic.

    The failsafe write: set ``status="failed"`` (so nothing downstream reads the
    run as clean) and park the job's own state + reason in the queryable custom
    bag (``custom_job_state`` / ``custom_error``). Best-effort: a failure here
    never raises, so the surrounding ingest's early-return is unaffected.
    """
    if not exec_id:
        return
    from wheeler.tools.graph_tools import execute_tool

    custom: dict[str, Any] = {"job_state": outcome.state}
    if outcome.detail:
        custom["error"] = outcome.detail
    try:
        await execute_tool(
            "update_node",
            {"node_id": exec_id, "status": "failed", "custom": custom},
            config,
        )
    except Exception:
        logger.warning(
            "mark_execution_failed: could not mark %s failed (best-effort)",
            exec_id,
            exc_info=True,
        )


async def mark_execution_completed(config: WheelerConfig, exec_id: str) -> None:
    """Reset a REUSED Execution to completed, clearing any prior failure marks.

    The mirror of ``mark_execution_failed``. The run Execution dedupes on
    (service, session_id), so a retry REUSES the node a prior attempt created. If
    that prior attempt left it ``status="failed"`` (a failed remote job, or a
    partial-ingest error), a now-SUCCESSFUL retry must not inherit the stale
    "failed" status, or the graph would lie that a successful run failed. Sets
    ``status="completed"`` and clears ``custom_job_state`` / ``custom_error``.
    Only call on the success path for a REUSED Execution (a freshly created one is
    already stamped with the right status). Best-effort: never raises.
    """
    if not exec_id:
        return
    from wheeler.tools.graph_tools import execute_tool

    try:
        await execute_tool(
            "update_node",
            {
                "node_id": exec_id,
                "status": "completed",
                "custom": {"job_state": "completed", "error": ""},
            },
            config,
        )
    except Exception:
        logger.warning(
            "mark_execution_completed: could not reset %s to completed "
            "(best-effort)",
            exec_id,
            exc_info=True,
        )


async def record_failed_execution(
    backend,
    config: WheelerConfig,
    *,
    service: str,
    session_id: str,
    kind: str,
    description: str,
    reason: str,
    link_to: str | None = None,
    used_inputs: list[str] | None = None,
) -> ImportReport:
    """Create (or reuse) a FAILED Execution for a job that produced no artifact.

    The visibility half of the failsafe: when the external CLI exits non-zero or
    returns no usable artifact, the transport returns None and the ingest is never
    called, so without this the attempt would leave NO trace ("you would not know
    it ran"). The marshal-in act calls this on a non-zero exit so the failed
    attempt is a queryable Execution (``status="failed"``, service-tagged, with
    the reason in ``custom_error``), wired to its inputs (USED) and Plan
    (AROSE_FROM) just like a successful run. Idempotent on (service, session_id).
    """
    from wheeler.tools.graph_tools import execute_tool

    report = ImportReport(failed=True, job_state="missing")
    exec_id = await _find_execution(
        backend, config, service=service, session_id=session_id
    )
    if not exec_id:
        result = json.loads(
            await execute_tool(
                "add_execution",
                {
                    "kind": kind,
                    "description": description[:200],
                    "agent_id": service.split(":", 1)[0] if service else "",
                    "status": "failed",
                    "session_id": session_id,
                    "service": service,
                },
                config,
            )
        )
        exec_id = result.get("node_id", "")
    report.execution_id = exec_id
    if exec_id:
        await mark_execution_failed(
            config, exec_id, JobOutcome(ok=False, state="missing", detail=reason)
        )
        if await _link_execution_to_plan(backend, config, exec_id, link_to):
            report.plan_linked += 1
        if used_inputs:
            report.used += await _record_used(backend, config, exec_id, used_inputs)
    return report
