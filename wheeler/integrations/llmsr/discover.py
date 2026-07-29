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
     "metrics": {"mse_train": 0.0167, "nmse_test_ood": 0.31},
     "selection": {"mode": "parsimony", ...}, "n_samples": N, "n_valid": M,
     # GROUPED runs only (`params` is empty for them, by construction):
     "group_by": "cell_id", "params_per_group": {"c01": [...], ...},
     "value_per_group": {"c01": 0.02, ...}}

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
  - **A grouped run's answer is the TABLE.** Each group refits its own constants
    under one shared form, so there is no single parameter vector and the flat
    ``params`` is empty. The Script records ``params_per_group`` plus the group
    coverage; recording the empty flat list would land the discovery in the graph
    with no constants at all.
  - **Every metric Finding is LABELLED by regime.** ``scored`` means the search
    optimized against that data, so the number is a fit quality and NOT a
    generalization claim; ``held_out`` means it did not; ``unknown`` means the
    artifact does not record enough to tell. Forty rounds of search against a
    split makes that split's error a training number however good it looks, and
    the graph must never present one as the other. (Full multi-dataset scoring is
    issue #107 slices S2/S3; this establishes the LABEL.)
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

# The splits `cli.py::best` can report, in the order a Finding should read them.
_SPLITS = ("train", "test_id", "test_ood")

# Regime: did the search optimize against this data? The label rides on every
# metric Finding, because a number the search was steered by is a fit quality and
# presenting it as a generalization claim is false.
REGIME_SCORED = "scored"
REGIME_HELD_OUT = "held_out"
REGIME_UNKNOWN = "unknown"


@dataclass
class RunMeta:
    run_id: str = ""
    generator: str = ""
    duration_seconds: float | None = None
    # candidates a hard constraint threw out. Carried onto the Execution only
    # when non-zero, so a run that declared no constraints lands exactly as before
    n_constraint_rejected: int = 0

    def custom_bag(self) -> dict[str, Any]:
        bag: dict[str, Any] = {"service": _SERVICE_TAG}
        if self.run_id:
            bag["run_id"] = self.run_id
        if self.generator:
            bag["generator"] = self.generator
        if self.duration_seconds is not None:
            bag["duration_seconds"] = self.duration_seconds
        if self.n_constraint_rejected:
            bag["n_constraint_rejected"] = self.n_constraint_rejected
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


def _finding_id(run_id: str, metric: str, split: str = "train") -> str:
    """Deterministic Finding id so a re-ingest dedupes instead of duplicating.

    The SPLIT is part of the key, so a train number and a held-out number from
    one run are distinct nodes. ``train`` is the historic default, so ids minted
    before per-split Findings existed still resolve to the same node.
    """
    key = f"{_SERVICE_TAG}:{run_id}:{metric}:{split or 'unlabeled'}"
    return "F-" + hashlib.sha256(key.encode()).hexdigest()[:8]


def _split_key(key: str) -> tuple[str, str]:
    """Split a ``<metric>_<split>`` metrics key into ``(metric, split)``.

    A key naming no split Wheeler knows about returns ``(key, "")``, which the
    regime labeller reports as ``unknown`` rather than guessing which regime a
    number it cannot place belongs to.
    """
    for split in _SPLITS:
        suffix = "_" + split
        if key.endswith(suffix) and len(key) > len(suffix):
            return key[: -len(suffix)], split
    return key, ""


def _split_regime(
    split: str, select_mode: str, n_valid: int | None
) -> tuple[str, str]:
    """Label one split by REGIME, with the reason, never guessing.

    Two things count as the search optimizing against data: FITTING the constants
    and CHOOSING THE WINNER. Train is both. ``--select ood`` ranks candidates by
    their error on ``test_ood``, so under that mode the OOD split is a selection
    set and its number is not a clean generalization claim either. Everything
    else the run merely reported on is held out.
    """
    if split == "train":
        return (
            REGIME_SCORED,
            "the search fitted the constants and ranked every candidate on this split",
        )
    if not split:
        return (
            REGIME_UNKNOWN,
            "the run did not record which split this number came from",
        )
    if split == "test_ood":
        if not select_mode:
            return (
                REGIME_UNKNOWN,
                "the run recorded no selection mode, so whether this split chose "
                "the winner cannot be determined",
            )
        if select_mode == "ood" and (n_valid is None or n_valid > 1):
            return (
                REGIME_SCORED,
                "--select ood chose the winning form by its error on this split",
            )
    return (
        REGIME_HELD_OUT,
        "the search neither fitted constants nor selected the winner on this split",
    )


def _split_record(
    split: str,
    metric: str,
    value: float | None,
    values: dict[str, float],
    select_mode: str,
    n_valid: int | None,
) -> dict[str, Any]:
    """One regime-labelled split entry: what number, on what data, earned how."""
    regime, reason = _split_regime(split, select_mode, n_valid)
    return {
        "split": split,
        "metric": metric,
        "value": value,
        # the same split under the run's other reported metric (mse next to nmse)
        "others": {k: v for k, v in values.items() if k != metric},
        "regime": regime,
        "regime_reason": reason,
    }


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

    rejected = _as_float(doc.get("n_constraint_rejected"))
    meta = RunMeta(
        run_id=_as_str(doc.get("run_id")),
        generator=_as_str(doc.get("generator")),
        n_constraint_rejected=int(rejected) if rejected else 0,
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
    params_raw = doc.get("params")
    params = params_raw if isinstance(params_raw, list) else []

    # How the winner was chosen, and out of how many. Both feed the regime label:
    # `--select ood` means the OOD split picked the winner (so it was optimized
    # against), unless there was only one valid candidate to pick from.
    selection_raw = doc.get("selection")
    select_mode = (
        _as_str(selection_raw.get("mode")).lower()
        if isinstance(selection_raw, dict)
        else ""
    )
    n_valid_raw = _as_float(doc.get("n_valid"))
    n_valid = int(n_valid_raw) if n_valid_raw is not None else None

    group_by, params_per_group, value_per_group = _parse_groups(doc)

    # Bucket the reported metrics by the split they were measured on.
    by_split: dict[str, dict[str, float]] = {}
    for raw_key, raw_val in metrics.items():
        val = _as_float(raw_val)
        if val is None:
            continue
        mkey, split = _split_key(str(raw_key))
        by_split.setdefault(split, {})[mkey] = val

    # The headline number is the TRAIN one, and only the train one: a held-out
    # number stands in for it nowhere, which is the whole point of the labels.
    train_values = by_split.pop("train", {})
    value = train_values.get(metric)
    if value is None and train_values:
        value = train_values[sorted(train_values)[0]]
    value_is_group_mean = False
    if value is None and value_per_group:
        # A grouped run reports no scalar (held-out scoring is skipped for it),
        # but every group reported its own value. The mean over groups is exactly
        # the scalar `fit.py` aggregates to, so it is DERIVED, not invented, and
        # it travels labelled as a mean so nothing reads it as a pooled fit.
        value = sum(value_per_group.values()) / len(value_per_group)
        value_is_group_mean = True

    # Train first (always present, even when the run reported no number, so the
    # discovery still lands), then any held-out splits the run scored.
    splits = [
        _split_record("train", metric, value, train_values, select_mode, n_valid)
    ]
    ordered = [s for s in _SPLITS if s in by_split]
    ordered += sorted(s for s in by_split if s not in _SPLITS)
    for split in ordered:
        values = by_split[split]
        headline = metric if metric in values else sorted(values)[0]
        splits.append(
            _split_record(
                split, headline, values[headline], values, select_mode, n_valid
            )
        )

    record = {
        "equation": equation,
        "program": program,
        "params": params,
        "metric": metric,
        "value": value,
        "value_is_group_mean": value_is_group_mean,
        "group_by": group_by,
        "params_per_group": params_per_group,
        "value_per_group": value_per_group,
        "select_mode": select_mode,
        "splits": splits,
        "data_path": _as_str(doc.get("data_path")),
        "spec_path": _as_str(doc.get("spec_path")),
    }
    return [record], meta


def _parse_groups(
    doc: dict[str, Any],
) -> tuple[str, dict[str, list[float]], dict[str, float]]:
    """Lift a grouped run's per-group constant table and per-group values.

    Returns ``("", {}, {})`` for an ungrouped run, and tolerates a partial table
    (a group whose entry is not a list of numbers is skipped, not fatal).
    """
    group_by = _as_str(doc.get("group_by"))
    raw_params = doc.get("params_per_group")
    params_per_group: dict[str, list[float]] = {}
    if isinstance(raw_params, dict):
        for label, vals in raw_params.items():
            if not isinstance(vals, list):
                continue
            floats = [f for f in (_as_float(v) for v in vals) if f is not None]
            if floats:
                params_per_group[str(label)] = floats
    raw_values = doc.get("value_per_group")
    value_per_group: dict[str, float] = {}
    if isinstance(raw_values, dict):
        for label, val in raw_values.items():
            fval = _as_float(val)
            if fval is not None:
                value_per_group[str(label)] = fval
    return group_by, params_per_group, value_per_group


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
        if run_meta.n_constraint_rejected:
            run_custom["n_constraint_rejected"] = run_meta.n_constraint_rejected
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
    """Create the Script (full program + constants) + one Finding per split."""
    metric = record["metric"]
    value = record["value"]
    grouped = bool(record["group_by"] and record["params_per_group"])

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
                custom: dict[str, Any] = {
                    "equation": record["equation"],
                    "metric": metric,
                    "value": value,
                    "run_dir": f".wheeler/llmsr/runs/{run_meta.run_id}",
                    "generator": run_meta.generator,
                }
                if grouped:
                    # The TABLE is the answer for a grouped run: one constant
                    # vector per group under one shared form. The flat `params`
                    # is empty by construction, so recording it would land the
                    # discovery in the graph with no constants at all.
                    custom.update(
                        {
                            "group_by": record["group_by"],
                            "n_groups": len(record["params_per_group"]),
                            "groups": json.dumps(sorted(record["params_per_group"])),
                            "params_per_group": json.dumps(record["params_per_group"]),
                            "value_per_group": json.dumps(record["value_per_group"]),
                            "value_is_group_mean": record["value_is_group_mean"],
                        }
                    )
                else:
                    custom["params"] = json.dumps(record["params"])
                await execute_tool(
                    "update_node",
                    {"node_id": script_id, "custom": custom},
                    config,
                )
                if link_to and await _link_once(
                    backend, config, script_id, "RELEVANT_TO", link_to
                ):
                    report.linked += 1

    # 2. One Finding per scored split, each LABELLED by regime.
    for entry in record["splits"]:
        await _record_split_finding(
            entry, record, run_meta, session_id, link_to,
            backend, config, execute_tool, report, produced_ids,
        )


async def _record_split_finding(
    entry: dict[str, Any],
    record: dict[str, Any],
    run_meta: RunMeta,
    session_id: str,
    link_to: str | None,
    backend,
    config: WheelerConfig,
    execute_tool,
    report: ImportReport,
    produced_ids: list[str],
) -> None:
    """One Finding for one split, carrying the REGIME that earned its number.

    The label is the guardrail. A number the search optimized against is a fit
    quality, and the graph must never offer it as a generalization claim; a
    held-out number may be read that way; and where the artifact does not say,
    the Finding says ``unknown`` instead of picking the flattering answer.
    """
    metric = entry["metric"]
    split = entry["split"]
    value = entry["value"]
    regime = entry["regime"]
    reason = entry["regime_reason"]
    grouped = bool(record["group_by"] and record["params_per_group"])

    finding_id = _finding_id(run_meta.run_id, metric, split)
    dataset_name = _dataset_label(record["data_path"])
    val_str = f"{value:.4g}" if isinstance(value, float) else _as_str(value)
    where = f"on {dataset_name} ({split or 'unlabelled split'})"
    mean_note = ""
    if split == "train" and record["value_is_group_mean"]:
        mean_note = (
            f" (mean over {len(record['value_per_group'])} "
            f"{record['group_by']!r} groups, each refitting its own constants)"
        )
    if value is None:
        headline = f"LLM-SR run reported no {metric} value {where}"
    else:
        headline = (
            f"LLM-SR discovered equation attains {metric} = {val_str}{mean_note} {where}"
        )
    if regime == REGIME_SCORED:
        caveat = (
            f"SCORED, not held out: {reason}, so this is fit quality and not a "
            "generalization claim."
        )
    elif regime == REGIME_HELD_OUT:
        caveat = f"Held out: {reason}."
    else:
        caveat = f"Regime unknown: {reason}."

    if await _node_exists(backend, config, finding_id):
        report.deduped += 1
    else:
        created = json.loads(
            await execute_tool(
                "add_finding",
                {
                    "id": finding_id,
                    "description": f"{headline}. {caveat}",
                    "confidence": _FINDING_CONFIDENCE,
                    "artifact_type": "number",
                    "title": f"{metric}_{split}" if split else metric,
                    "service": _SERVICE_TAG,
                    "session_id": session_id,
                },
                config,
            )
        )
        finding_id = created.get("node_id", finding_id)
        report.created += 1
    produced_ids.append(finding_id)

    custom: dict[str, Any] = {
        "metric": metric,
        "value": value,
        "equation": record["equation"],
        "run_id": run_meta.run_id,
        "split": split,
        "regime": regime,
        "regime_reason": reason,
    }
    # the same split under the run's other reported metric (nmse beside mse)
    for other_key, other_val in entry["others"].items():
        custom[f"value_{other_key}"] = other_val
    if split == "train" and grouped:
        custom.update(
            {
                "group_by": record["group_by"],
                "n_groups": len(record["params_per_group"]),
                "value_per_group": json.dumps(record["value_per_group"]),
                "value_is_group_mean": record["value_is_group_mean"],
            }
        )
    await execute_tool(
        "update_node", {"node_id": finding_id, "custom": custom}, config
    )
    if link_to and await _link_once(backend, config, finding_id, "RELEVANT_TO", link_to):
        report.linked += 1


def _dataset_label(data_path: str) -> str:
    if not data_path:
        return "the dataset"
    p = Path(data_path)
    return p.parent.name or p.stem or "the dataset"
