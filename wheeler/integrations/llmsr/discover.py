"""Marshal-out (deterministic): ingest an LLM-SR equation-discovery result.

Reads a ``best.json`` produced by ``wheeler llmsr best`` and lands it in the
graph: the full generated program becomes a hashed Script (durable, re-runnable),
the fit metric becomes a Finding, both WAS_GENERATED_BY one run Execution that
USED the input Dataset. Mirrors the Asta adapters: ``execute_tool`` is imported
lazily (function-local) so every write routes through the triple-write, and the
shared marshal helpers live in ``wheeler/integrations/asta/_marshal.py``.

REAL output shape (best.json), produced by ``cli.py::best``::

    {"status": "completed"|"failed", "run_id": "...", "spec_path": "...",
     "data_path": "...", "metric": "mse", "generator": "claude",
     "equation": "<body>", "params": [...], "program": "<full runnable .py>",
     "metrics": {"mse_train": 0.0167}, "history": [...],
     "n_samples": N, "n_valid": M}

Provenance is TWO-SIDED off ONE Execution:
``output -[WAS_GENERATED_BY]-> Execution -[USED]-> input``. The produced Script
and Finding are Wheeler-generated, so they DO carry WAS_GENERATED_BY (unlike
reference-entity Papers, which this adapter never creates).

Invariants (kept true):
  - Defensive: every step tolerates missing pieces, counts and skips, never
    raises. A partial or shape-drifted artifact never aborts ingest.
  - Sequential writes only. Never ``asyncio.gather``.
  - link_once: every edge is existence-guarded (bare CREATE duplicates on re-run).
  - One Execution per RUN, tagged service ``llmsr:discover``. Idempotent:
    Execution dedupes on session_id, Script on file hash (ensure_artifact),
    Finding on a deterministic id, edges via link_once.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.integrations.asta._marshal import (
    ImportReport,
    JobOutcome,
    _find_execution,
    _link_execution_to_plan,
    _link_once,
    _node_exists,
    _record_used,
    job_outcome,
    mark_execution_completed,
    mark_execution_failed,
)

logger = logging.getLogger(__name__)

_SERVICE_TAG = "llmsr:discover"
_RAW_NODE_TYPE = "document"  # best.json is a synthesized run report (W-)
_FINDING_CONFIDENCE = 0.7  # a fitted, measured result: moderate, not speculative
_DISCOVERIES_DIR = Path(".wheeler/llmsr/discoveries")


@dataclass
class RunMeta:
    run_id: str = ""
    generator: str = ""
    duration_seconds: float | None = None

    def custom_bag(self) -> dict[str, Any]:
        bag: dict[str, Any] = {"service": _SERVICE_TAG}
        if self.run_id:
            bag["run_id"] = self.run_id
        if self.generator:
            bag["generator"] = self.generator
        if self.duration_seconds is not None:
            bag["duration_seconds"] = self.duration_seconds
        return bag


# --- defensive coercion helpers ---


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _finding_id(run_id: str, metric: str) -> str:
    """Deterministic Finding id so a re-ingest dedupes instead of duplicating."""
    key = f"{_SERVICE_TAG}:{run_id}:{metric}:train"
    return "F-" + hashlib.sha256(key.encode()).hexdigest()[:8]


async def _record_generated(
    backend,
    config: WheelerConfig,
    exec_id: str,
    produced_ids: list[str],
    report: ImportReport,
) -> None:
    """OUTPUT side: each produced node -[WAS_GENERATED_BY]-> Execution (link_once)."""
    if not exec_id or not produced_ids:
        return
    seen: set[str] = set()
    for raw_id in produced_ids:
        node_id = (raw_id or "").strip()
        if not node_id or node_id == exec_id or node_id in seen:
            continue
        seen.add(node_id)
        if await _link_once(backend, config, node_id, "WAS_GENERATED_BY", exec_id):
            report.linked += 1


def parse_discover(doc: Any) -> tuple[list[dict[str, Any]], RunMeta]:
    """Parse best.json into a single result record + run metadata. Never raises.

    A non-dict, a non-completed status, or a missing equation/program yields
    ``([], meta)``: the gate in ``ingest_discover`` records the failed/empty run
    and fabricates nothing.
    """
    if not isinstance(doc, dict):
        logger.warning("parse_discover: doc is not a dict, got %s", type(doc).__name__)
        return [], RunMeta()

    meta = RunMeta(
        run_id=_as_str(doc.get("run_id")),
        generator=_as_str(doc.get("generator")),
    )
    timing = doc.get("timing")
    if isinstance(timing, dict):
        meta.duration_seconds = _as_float(timing.get("duration_seconds"))
    if _as_str(doc.get("status")).lower() != "completed":
        return [], meta

    equation = _as_str(doc.get("equation"))
    program = _as_str(doc.get("program"))
    if not equation or not program:
        return [], meta

    metric = _as_str(doc.get("metric")) or "score"
    metrics_raw = doc.get("metrics")
    metrics = metrics_raw if isinstance(metrics_raw, dict) else {}
    value = _as_float(metrics.get(f"{metric}_train"))
    if value is None:  # fall back to any numeric metric present
        value = next(
            (v for v in (_as_float(x) for x in metrics.values()) if v is not None),
            None,
        )
    params_raw = doc.get("params")
    params = params_raw if isinstance(params_raw, list) else []

    record = {
        "equation": equation,
        "program": program,
        "params": params,
        "metric": metric,
        "value": value,
        "data_path": _as_str(doc.get("data_path")),
        "spec_path": _as_str(doc.get("spec_path")),
    }
    return [record], meta


async def ingest_discover(
    doc: dict[str, Any],
    *,
    link_to: str | None = None,
    config: WheelerConfig,
    artifact_path: str | None = None,
    used_inputs: list[str] | None = None,
) -> ImportReport:
    """Ingest an LLM-SR ``best.json`` into the knowledge graph.

    Args:
        doc: the parsed best.json dict.
        link_to: optional Question/Plan id the produced nodes relate to.
        config: active Wheeler config.
        artifact_path: path to best.json; registered as a Document generated by
            the run.
        used_inputs: graph node ids the request was built from (the Dataset, the
            link target); the run Execution -[USED]-> each existing one.
    """
    from wheeler.tools.graph_tools import _get_backend, execute_tool

    report = ImportReport()
    records, run_meta = parse_discover(doc)

    # FAILSAFE gate. best.json is a plain dict, so job_outcome() is ok by default;
    # LLM-SR reports its own status, so a search that found no valid equation is a
    # truthful failure. Gate on it: a not-ok run records a FAILED Execution and
    # fabricates no Script/Finding.
    outcome = job_outcome(doc)
    status = _as_str(doc.get("status")).lower() if isinstance(doc, dict) else ""
    if status != "completed":
        outcome = JobOutcome(
            ok=False,
            state=status or "failed",
            detail=_as_str(doc.get("error")) if isinstance(doc, dict) else "",
        )

    backend = await _get_backend(config)

    session_id = run_meta.run_id or "llmsr-discover-unknown-run"
    exec_id = await _find_execution(
        backend, config, service=_SERVICE_TAG, session_id=session_id
    )
    reused = bool(exec_id)
    if not exec_id:
        exec_result = json.loads(
            await execute_tool(
                "add_execution",
                {
                    "kind": "equation-discovery",
                    "description": f"LLM-SR equation discovery: {run_meta.run_id}",
                    "agent_id": "llmsr",
                    "status": "completed" if outcome.ok else "failed",
                    "session_id": session_id,
                    "service": _SERVICE_TAG,
                },
                config,
            )
        )
        exec_id = exec_result.get("node_id", "")
    report.execution_id = exec_id

    # Plan anchor + input-side provenance.
    if exec_id and await _link_execution_to_plan(backend, config, exec_id, link_to):
        report.plan_linked += 1
    if exec_id and used_inputs:
        report.used += await _record_used(backend, config, exec_id, used_inputs)

    # Register best.json as the durable raw Document (WAS_GENERATED_BY the run).
    try:
        from wheeler.integrations.asta.artifacts import register_output_artifact

        artifact_id = await register_output_artifact(
            artifact_path,
            execution_id=exec_id,
            service=_SERVICE_TAG,
            config=config,
            node_type=_RAW_NODE_TYPE,
            run_id=run_meta.run_id,
            benchmark=run_meta.custom_bag(),
            description=f"{_SERVICE_TAG} run report ({run_meta.run_id})",
        )
        if artifact_id:
            report.artifact = artifact_id
    except Exception:
        logger.warning(
            "ingest_discover: artifact registration raised (best-effort)",
            exc_info=True,
        )

    # FAILSAFE: not-ok job stops here. Execution (failed) + raw artifact are
    # visible; no outputs fabricated.
    if not outcome.ok:
        await mark_execution_failed(config, exec_id, outcome)
        report.failed = True
        report.job_state = outcome.state
        logger.warning(
            "ingest_discover: run not completed (state=%s): %s",
            outcome.state,
            outcome.detail,
        )
        return report
    if not records:
        # A "completed" run that produced no parseable equation is not a clean
        # empty result: mark it failed so the graph never asserts a completed run
        # with zero outputs.
        await mark_execution_failed(
            config,
            exec_id,
            JobOutcome(ok=False, state="no-output", detail="completed run produced no equation"),
        )
        report.failed = True
        report.job_state = "no-output"
        logger.warning("ingest_discover: completed artifact had no parseable equation; marked failed")
        return report
    if reused:
        await mark_execution_completed(config, exec_id)

    try:
        produced_ids: list[str] = []
        for record in records:
            await _bucket_result(
                record, run_meta, exec_id, session_id, link_to,
                backend, config, execute_tool, report, produced_ids,
            )
        # stamp run metadata on the Execution: which generator (claude / codex)
        # proposed the winner, and how long the search took (queryable in the graph)
        run_custom: dict[str, Any] = {}
        if run_meta.generator:
            run_custom["generator"] = run_meta.generator
        if run_meta.duration_seconds is not None:
            run_custom["duration_seconds"] = run_meta.duration_seconds
        if run_custom:
            await execute_tool(
                "update_node", {"node_id": exec_id, "custom": run_custom}, config
            )
        await _record_generated(backend, config, exec_id, produced_ids, report)
    except Exception:
        logger.error(
            "ingest_discover: output bucketing raised partway; marking run failed",
            exc_info=True,
        )
        await mark_execution_failed(
            config,
            exec_id,
            JobOutcome(ok=False, state="ingest-error", detail="output bucketing raised"),
        )
        report.failed = True
        report.job_state = "ingest-error"
        return report

    logger.info(
        "ingest_discover: created=%d deduped=%d linked=%d used=%d (exec=%s)",
        report.created,
        report.deduped,
        report.linked,
        report.used,
        exec_id,
    )
    return report


async def _bucket_result(
    record: dict[str, Any],
    run_meta: RunMeta,
    exec_id: str,
    session_id: str,
    link_to: str | None,
    backend,
    config: WheelerConfig,
    execute_tool,
    report: ImportReport,
    produced_ids: list[str],
) -> None:
    """Create the Script (full program) + Finding (metric) for one result."""
    metric = record["metric"]
    value = record["value"]

    # 1. The full generated program -> a durable .py -> a hashed Script.
    program = record["program"]
    if program:
        _DISCOVERIES_DIR.mkdir(parents=True, exist_ok=True)
        py_path = _DISCOVERIES_DIR / f"{run_meta.run_id or 'discovery'}.py"
        try:
            py_path.write_text(program)
        except OSError:
            logger.warning("ingest_discover: could not write %s", py_path, exc_info=True)
            py_path = None  # type: ignore[assignment]
        if py_path is not None and py_path.exists():
            result = json.loads(
                await execute_tool(
                    "ensure_artifact",
                    {
                        "path": str(py_path.resolve()),
                        "artifact_type": "script",
                        "language": "python",
                        "service": _SERVICE_TAG,
                        "description": f"LLM-SR discovered equation ({run_meta.run_id})",
                    },
                    config,
                )
            )
            script_id = result.get("node_id")
            if script_id:
                if result.get("action") == "created":
                    report.created += 1
                else:
                    report.deduped += 1
                produced_ids.append(script_id)
                await execute_tool(
                    "update_node",
                    {
                        "node_id": script_id,
                        "custom": {
                            "equation": record["equation"],
                            "params": json.dumps(record["params"]),
                            "metric": metric,
                            "value": value,
                            "run_dir": f".wheeler/llmsr/runs/{run_meta.run_id}",
                            "generator": run_meta.generator,
                        },
                    },
                    config,
                )
                if link_to and await _link_once(
                    backend, config, script_id, "RELEVANT_TO", link_to
                ):
                    report.linked += 1

    # 2. The fit metric -> a Finding (deterministic id so re-ingest dedupes).
    finding_id = _finding_id(run_meta.run_id, metric)
    dataset_name = _dataset_label(record["data_path"])
    val_str = f"{value:.4g}" if isinstance(value, float) else _as_str(value)
    if await _node_exists(backend, config, finding_id):
        report.deduped += 1
    else:
        created = json.loads(
            await execute_tool(
                "add_finding",
                {
                    "id": finding_id,
                    "description": (
                        f"LLM-SR discovered equation attains {metric} = {val_str} "
                        f"on {dataset_name} (train)."
                    ),
                    "confidence": _FINDING_CONFIDENCE,
                    "artifact_type": "number",
                    "title": f"{metric}_train",
                    "service": _SERVICE_TAG,
                    "session_id": session_id,
                },
                config,
            )
        )
        finding_id = created.get("node_id", finding_id)
        report.created += 1
    produced_ids.append(finding_id)
    await execute_tool(
        "update_node",
        {
            "node_id": finding_id,
            "custom": {
                "metric": metric,
                "value": value,
                "equation": record["equation"],
                "run_id": run_meta.run_id,
            },
        },
        config,
    )
    if link_to and await _link_once(backend, config, finding_id, "RELEVANT_TO", link_to):
        report.linked += 1


def _dataset_label(data_path: str) -> str:
    if not data_path:
        return "the dataset"
    p = Path(data_path)
    return p.parent.name or p.stem or "the dataset"
