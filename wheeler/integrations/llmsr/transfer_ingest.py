"""Marshal-out (deterministic): ingest an LLM-SR transfer result.

Reads a ``transfer.json`` produced by ``wheeler llmsr transfer`` and lands it in
the graph. ``transfer`` answers the question the whole per-group protocol exists
for, **does the FORM generalize**, by refitting the discovered form's constants
from scratch on data the search never saw, and it reports that number BESIDE the
one you get by applying the source constants unchanged. Two numbers, two
questions, and until this module existed neither of them reached the graph.

REAL output shape (transfer.json), produced by ``cli.py::transfer``::

    {"status": "completed"|"failed", "run_id": "...", "metric": "mse",
     "data_path": "/abs/held_out.csv", "source_data_path": "/abs/train.csv",
     "group_by": "cell_id", "groups": ["c02", "c03"],
     "candidate": {"sample_order": 2, "selected_by": "fit",
                   "equation": "<body>", "complexity": 7},
     "refit": {"claim": "form", "label": "...", "valid": true, "value": 2.6e-16,
               "value_per_group": {...}, "params_per_group": {...},
               "optimizer": "bfgs", "regime": "held_out_form",
               "regime_reason": "...", "error": ""},
     "fixed_theta": {"claim": "constants", "label": "...", "value": 134.35,
                     "value_per_group": {...}, "params_per_group": {...},
                     "source_per_group": {...}, "regime": "held_out",
                     "regime_reason": "...", "error": ""},
     "comparison": {"metric": "mse", "refit_value": ..., "fixed_theta_value": ...,
                    "refit_over_fixed": 1.9e-18, "note": "..."},
     "optimizer": {...},
     # SPEC-DOOR source runs only (`--use-spec-evaluate`):
     "scored_metric": {"name": "spec:evaluate", "declared": "mse", ...},
     "written": "..."}

Provenance is TWO-SIDED off ONE Execution, exactly as in ``discover.py``:
``output -[WAS_GENERATED_BY]-> Execution -[USED]-> input``. The inputs are the
three things a transfer genuinely read: the table the form was transferred ONTO,
the source run's discovered Script (so the chain back to the discovery is real
and not merely narrated), and the source run's own training table (whose fitted
constants are what the fixed-theta number applies). The outputs are the two
Findings and ``transfer.json`` itself.

Why this lives beside ``transfer.py`` rather than inside it: ``transfer.py``
imports the scoring machinery (``fit``, ``runs``, ``selection``) and says in its
own header that it duplicates the regime literals because it is NOT the graph
writer. That separation is worth keeping, so the graph writer is its own module
and sits at the same layer as ``discover.py`` (config + ``asta/_marshal.py``
only), importing the labelling vocabulary FROM ``discover.py`` rather than
restating it. A parallel vocabulary is exactly what these labels exist to
prevent.

Invariants (kept true):
  - Defensive: every step tolerates missing pieces, counts and skips, never
    raises. A partial or shape-drifted artifact never aborts ingest.
  - Sequential writes only. Never ``asyncio.gather``.
  - link_once: every edge is existence-guarded (bare CREATE duplicates on re-run).
  - One Execution per TRANSFER, tagged service ``llmsr:transfer``. The
    ``session_id`` is the source run PLUS what the transfer was actually about
    (the target table and the candidate), because one run can be transferred onto
    many tables and each is a separate measurement. It can never collide with the
    discovery run's Execution, which is keyed on the bare run id under a
    different service tag.
  - **The external-call failsafe.** A ``transfer.json`` whose status is not
    ``completed`` records a FAILED Execution plus the raw artifact and fabricates
    NO Findings. A failed transfer still carries partial per-group fixed-theta
    numbers (the two sides are measured independently), and promoting those to
    Findings would present a run that could not refit as though it had answered
    the question it was asked.
  - **TWO Findings, in DIFFERENT regimes, and they must never collapse into
    one.** The refit number is ``held_out_form``: a refit fits its constants on
    the very split it reports, so the data is held out for the FORM and never for
    the CONSTANTS. The fixed-theta number is ``held_out`` proper. Each Finding
    also carries the OTHER number and the labelled ratio, so a reader who lands
    on one cannot mistake it for the answer to both questions.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
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

# The labelling vocabulary and the id scheme are DISCOVER'S, imported rather than
# restated. Two modules writing metric Findings under two spellings of
# "held out" is the exact failure the labels exist to prevent, and
# `_finding_id` already takes the CLAIM that keeps the two numbers on one piece
# of data from colliding into one node.
from wheeler.integrations.llmsr.discover import (
    _DISCOVERIES_DIR,
    _FINDING_CONFIDENCE,
    _REGIMES,
    _SECOND_OPINION_NOTE,
    CLAIM_CONSTANTS,
    CLAIM_FORM,
    MEASURED_BY_FIT,
    REGIME_SCORED,
    REGIME_UNKNOWN,
    _as_float,
    _as_str,
    _finding_id,
    _float_map,
    _record_generated,
    _refit_regime,
)

logger = logging.getLogger(__name__)

_SERVICE_TAG = "llmsr:transfer"
_EXECUTION_KIND = "equation-transfer"
_RAW_NODE_TYPE = "document"  # transfer.json is a synthesized run report (W-)

# The two blocks, in the order a reader should meet them. The refit comes first
# because it answers the question symbolic regression is actually asking.
_BLOCKS = (("refit", CLAIM_FORM), ("fixed_theta", CLAIM_CONSTANTS))


@dataclass
class TransferMeta:
    """What the whole transfer was, read once off the artifact.

    ``session_id`` and ``split_token`` are derived here so the Execution key and
    both Finding ids come from one place and are deterministic in the artifact
    alone: re-ingesting the same file always lands on the same nodes.
    """

    run_id: str = ""
    metric: str = ""
    data_path: str = ""
    source_data_path: str = ""
    group_by: str = ""
    groups: list[str] = field(default_factory=list)
    sample_order: Any = None
    selected_by: str = ""
    equation: str = ""
    complexity: float | None = None
    # `spec:<evaluate>` when the SOURCE run was scored through the spec door,
    # else empty. It never names THIS verb's numbers, which `fit.py` computed
    # under the declared metric whatever scored the search.
    scored_metric: str = ""
    session_id: str = ""
    split_token: str = ""

    def custom_bag(self) -> dict[str, Any]:
        """Run metadata for the Execution. Deliberately carries NO measurement.

        Both numbers already live, labelled and paired, on both Findings. A third
        copy here would put the same values in the graph under a node type that
        does not carry their regime, which is how a generalization claim loses
        the caveat that qualifies it.
        """
        bag: dict[str, Any] = {"service": _SERVICE_TAG}
        if self.run_id:
            bag["run_id"] = self.run_id
        if self.metric:
            bag["metric"] = self.metric
        if self.data_path:
            bag["transfer_data"] = self.data_path
        if self.source_data_path:
            bag["source_data"] = self.source_data_path
        if self.group_by:
            bag["group_by"] = self.group_by
        if self.groups:
            bag["n_groups"] = len(self.groups)
            bag["groups"] = json.dumps(self.groups)
        if self.sample_order is not None:
            bag["candidate_sample_order"] = self.sample_order
        if self.selected_by:
            bag["selected_by"] = self.selected_by
        if self.scored_metric:
            bag["source_scored_metric"] = self.scored_metric
        return bag


def _transfer_key(run_id: str, data_path: str, sample_order: Any) -> str:
    """The stable digest of WHAT this transfer measured. Never re-derived.

    Three things make one transfer distinct from another: the source RUN, the
    table it was transferred ONTO, and WHICH candidate was transferred. Keying on
    the run alone would make a second transfer of the same run silently overwrite
    the first's numbers under its Finding ids, which is worse than a duplicate
    because it looks like an update.

    ``data_path`` is used EXACTLY as the artifact recorded it and is never
    re-resolved here: resolving a relative path at ingest time would key on the
    ingesting process's cwd, and the same file would then produce two different
    Executions from two different directories.
    """
    key = f"{run_id}|{data_path}|{sample_order}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _label(data_path: str) -> str:
    """A short human name for the transfer table, for ids and titles."""
    if not data_path:
        return "unknown"
    p = Path(data_path)
    return p.stem or p.name or "unknown"


def _claim_regime(block: dict[str, Any], claim: str) -> tuple[str, str]:
    """The regime of one block, read off the artifact and never softened.

    The run is the only thing that knows whether it fitted or selected on this
    data, so the label is READ rather than recomputed. A label this version does
    not recognize reports ``unknown`` with the reason rather than being coerced
    into the flattering answer: the vocabulary is closed on purpose.

    ``discover._refit_regime`` is then applied to the FORM claim, which is a
    no-op on an artifact ``transfer.py`` already labelled (it applies the same
    rule before writing) and REPAIRS one written by any version that did not:
    a refit reported as plain ``held_out`` claims the constants transferred too.
    """
    regime = _as_str(block.get("regime"))
    reason = _as_str(block.get("regime_reason"))
    if regime not in _REGIMES:
        regime, reason = REGIME_UNKNOWN, (
            "the transfer report did not label this number with a regime this "
            f"version knows ({regime or 'none recorded'})"
        )
    if claim == CLAIM_FORM:
        regime, reason = _refit_regime(regime, reason)
    return regime, reason


def _params_map(value: Any) -> dict[str, list[float]]:
    """A ``group -> constants`` table, dropping whatever is not one. Never raises."""
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[float]] = {}
    for key, raw in value.items():
        if not isinstance(raw, list):
            continue
        floats = [f for f in (_as_float(v) for v in raw) if f is not None]
        if floats:
            out[str(key)] = floats
    return out


def _str_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(k): _as_str(v) for k, v in value.items()}


def parse_transfer(doc: Any) -> tuple[list[dict[str, Any]], TransferMeta]:
    """Parse transfer.json into one record PER CLAIM + transfer metadata.

    Two records, never one: the refit number and the fixed-theta number are
    measurements of two different things on the same data, and a single record
    would force a caller to pick which question the transfer answered.

    A non-dict, a non-completed status, or a report with neither block yields
    ``([], meta)``: the gate in ``ingest_transfer`` records the failed/empty
    transfer and fabricates nothing. Never raises.
    """
    if not isinstance(doc, dict):
        logger.warning("parse_transfer: doc is not a dict, got %s", type(doc).__name__)
        return [], TransferMeta()

    cand = doc.get("candidate")
    cand = cand if isinstance(cand, dict) else {}
    scored_block = doc.get("scored_metric")
    meta = TransferMeta(
        run_id=_as_str(doc.get("run_id")),
        metric=_as_str(doc.get("metric")) or "score",
        data_path=_as_str(doc.get("data_path")),
        source_data_path=_as_str(doc.get("source_data_path")),
        group_by=_as_str(doc.get("group_by")),
        groups=[_as_str(g) for g in (doc.get("groups") or []) if _as_str(g)],
        sample_order=cand.get("sample_order"),
        selected_by=_as_str(cand.get("selected_by")),
        equation=_as_str(cand.get("equation")),
        complexity=_as_float(cand.get("complexity")),
        scored_metric=(
            _as_str(scored_block.get("name"))
            if isinstance(scored_block, dict)
            else ""
        ),
    )
    digest = _transfer_key(meta.run_id, meta.data_path, meta.sample_order)
    meta.session_id = f"{meta.run_id or 'unknown-run'}:{_label(meta.data_path)}:{digest}"
    # Can never be one of `discover._SPLITS` (train / test_id / test_ood) nor the
    # unlabelled empty string, so a transfer Finding can never collide with a
    # discovery Finding from the same run under the same metric.
    meta.split_token = f"transfer:{digest}"

    if _as_str(doc.get("status")).lower() != "completed":
        return [], meta

    # The SOURCE run's door, applied to numbers THIS verb computed. `transfer`
    # always refits through `fit.py` under the run's DECLARED metric, so on a
    # spec-door run these are a second opinion measured by different machinery
    # than the search used, exactly as `best.json`'s held-out splits are. A
    # default-door run has one piece of machinery and gets no note at all.
    note = _SECOND_OPINION_NOTE if meta.scored_metric else ""

    records: list[dict[str, Any]] = []
    for block_key, claim in _BLOCKS:
        block = doc.get(block_key)
        if not isinstance(block, dict):
            logger.warning(
                "parse_transfer: %r block is missing or not a dict; skipped",
                block_key,
            )
            continue
        regime, reason = _claim_regime(block, claim)
        records.append({
            "block": block_key,
            "claim": claim,
            "label": _as_str(block.get("label")),
            "value": _as_float(block.get("value")),
            "value_per_group": _float_map(block.get("value_per_group")),
            "params_per_group": _params_map(block.get("params_per_group")),
            # WHY a group has (or has not) a source constant vector. Present on
            # the fixed-theta side only, and it is what turns a withheld number
            # from a hole into a recorded fact.
            "source_per_group": _str_map(block.get("source_per_group")),
            "regime": regime,
            "regime_reason": reason,
            "error": _as_str(block.get("error")),
            "measured_by": MEASURED_BY_FIT,
            "measurement_note": note,
        })
    if not records:
        return [], meta

    # The labelled comparison, carried onto BOTH Findings so whichever one a
    # reader lands on shows the other beside it. Read off the artifact rather
    # than recomputed: `transfer._comparison` withholds the ratio when either
    # number is missing or the divisor is zero, and re-deriving it here would
    # reintroduce exactly the guesses it declines to make.
    comparison = doc.get("comparison")
    comparison = comparison if isinstance(comparison, dict) else {}
    pair = {
        "refit_value": _as_float(comparison.get("refit_value")),
        "fixed_theta_value": _as_float(comparison.get("fixed_theta_value")),
        "refit_over_fixed": _as_float(comparison.get("refit_over_fixed")),
        "comparison_note": _as_str(comparison.get("note")),
    }
    for record in records:
        record.update(pair)
    return records, meta


async def ingest_transfer(
    doc: dict[str, Any],
    *,
    link_to: str | None = None,
    config: WheelerConfig,
    artifact_path: str | None = None,
    used_inputs: list[str] | None = None,
) -> ImportReport:
    """Ingest an LLM-SR ``transfer.json`` into the knowledge graph.

    Args:
        doc: the parsed transfer.json dict.
        link_to: optional Question/Plan id the produced Findings relate to.
        config: active Wheeler config.
        artifact_path: path to transfer.json; registered as a Document generated
            by the transfer.
        used_inputs: graph node ids the request was built from (the held-out
            Dataset, the link target); the Execution -[USED]-> each existing one.
    """
    from wheeler.tools.graph_tools import _get_backend, execute_tool

    report = ImportReport()
    records, meta = parse_transfer(doc)

    # FAILSAFE gate. `transfer.json` reports its own status, and a candidate that
    # could not refit on the held-out table is a truthful failure of the question
    # that was asked. Gate on it: a not-ok transfer records a FAILED Execution
    # and fabricates no Finding, even though its fixed-theta side may carry real
    # per-group numbers. Reporting those alone would answer the CONSTANTS
    # question while silently dropping the FORM one the transfer was run for.
    outcome = job_outcome(doc)
    status = _as_str(doc.get("status")).lower() if isinstance(doc, dict) else ""
    if status != "completed":
        detail = ""
        if isinstance(doc, dict):
            refit = doc.get("refit")
            detail = _as_str(refit.get("error")) if isinstance(refit, dict) else ""
            detail = detail or _as_str(doc.get("error"))
        outcome = JobOutcome(ok=False, state=status or "failed", detail=detail)

    backend = await _get_backend(config)

    session_id = meta.session_id or "llmsr-transfer-unknown"
    exec_id = await _find_execution(
        backend, config, service=_SERVICE_TAG, session_id=session_id
    )
    reused = bool(exec_id)
    if not exec_id:
        exec_result = json.loads(
            await execute_tool(
                "add_execution",
                {
                    "kind": _EXECUTION_KIND,
                    "description": (
                        f"LLM-SR form transfer: {meta.run_id or 'unknown run'} "
                        f"onto {_label(meta.data_path)}"
                    ),
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

    # Plan anchor + the input ids the act marshalled in.
    if exec_id and await _link_execution_to_plan(backend, config, exec_id, link_to):
        report.plan_linked += 1
    if exec_id and used_inputs:
        report.used += await _record_used(backend, config, exec_id, used_inputs)

    # Register transfer.json as the durable raw Document (WAS_GENERATED_BY the
    # transfer). The durable-store key is the SESSION id, not the bare run id:
    # two transfers of one run onto two tables are two artifacts, and keying on
    # the run would path-dedupe the second onto the first and keep the first's
    # content. The benchmark bag still carries the true `run_id`.
    try:
        from wheeler.integrations.asta.artifacts import register_output_artifact

        artifact_id = await register_output_artifact(
            artifact_path,
            execution_id=exec_id,
            service=_SERVICE_TAG,
            config=config,
            node_type=_RAW_NODE_TYPE,
            run_id=session_id,
            benchmark=meta.custom_bag(),
            description=(
                f"{_SERVICE_TAG} report ({meta.run_id} onto {_label(meta.data_path)})"
            ),
        )
        if artifact_id:
            report.artifact = artifact_id
    except Exception:
        logger.warning(
            "ingest_transfer: artifact registration raised (best-effort)",
            exc_info=True,
        )

    # FAILSAFE: not-ok transfer stops here. Execution (failed) + raw artifact are
    # visible; no Findings fabricated.
    if not outcome.ok:
        await mark_execution_failed(config, exec_id, outcome)
        report.failed = True
        report.job_state = outcome.state
        logger.warning(
            "ingest_transfer: transfer not completed (state=%s): %s",
            outcome.state,
            outcome.detail,
        )
        return report
    if not records:
        # A "completed" transfer with neither block parseable is not a clean
        # empty result: mark it failed so the graph never asserts a completed
        # transfer with zero measurements.
        await mark_execution_failed(
            config,
            exec_id,
            JobOutcome(
                ok=False,
                state="no-output",
                detail="completed transfer reported no refit or fixed-theta block",
            ),
        )
        report.failed = True
        report.job_state = "no-output"
        logger.warning(
            "ingest_transfer: completed artifact had no parseable claim; marked failed"
        )
        return report
    if reused:
        await mark_execution_completed(config, exec_id)

    try:
        produced_ids: list[str] = []
        # 1. INPUT side: everything the transfer genuinely read.
        await _record_inputs(
            records, meta, exec_id, backend, config, execute_tool, report
        )
        # 2. OUTPUT side: one Finding per claim, each labelled by regime.
        for record in records:
            await _record_claim_finding(
                record, meta, session_id, link_to,
                backend, config, execute_tool, report, produced_ids,
            )
        run_custom = meta.custom_bag()
        run_custom.pop("service", None)
        if run_custom:
            await execute_tool(
                "update_node", {"node_id": exec_id, "custom": run_custom}, config
            )
        await _record_generated(backend, config, exec_id, produced_ids, report)
    except Exception:
        logger.error(
            "ingest_transfer: output bucketing raised partway; marking transfer failed",
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
        "ingest_transfer: created=%d deduped=%d linked=%d used=%d (exec=%s)",
        report.created,
        report.deduped,
        report.linked,
        report.used,
        exec_id,
    )
    return report


async def _record_inputs(
    records: list[dict[str, Any]],
    meta: TransferMeta,
    exec_id: str,
    backend,
    config: WheelerConfig,
    execute_tool,
    report: ImportReport,
) -> None:
    """The three things a transfer READ, each ``USED`` by its Execution.

    These are INPUTS, so they are deliberately absent from ``produced_ids``: a
    table the transfer read and a Script it re-ran are never
    ``WAS_GENERATED_BY`` it, on the same rule that keeps reference-entity Papers
    off that edge in the Asta adapters.

    1. The table the form was transferred ONTO. It carries the regime the RUN
       assigned it (which is the fixed-theta block's, the regime of the DATA
       rather than of a refit), so the graph can answer "which tables was this
       form never fitted on" without re-reading the report.
    2. The source run's discovered Script. ``discover.py`` writes the winning
       program to ``.wheeler/llmsr/discoveries/<run_id>.py`` and registers it,
       so ``ensure_artifact`` on that path resolves to the SAME node and the
       chain from a transfer number back to the discovery that produced the form
       is a real edge rather than a shared ``custom_run_id``. Absent when the
       discovery was never ingested: counted, logged, never fatal.
    3. The source run's own training table, whose fitted constants are exactly
       what the fixed-theta number applies. Without it, half the transfer's
       inputs would be invisible.

    Defensive throughout: a path that has moved since the run cannot be hashed,
    so it is counted and skipped rather than aborting an ingest.
    """
    if not exec_id:
        return
    # The DATA's own regime is the fixed-theta claim's (the refit's is a
    # statement about the number, not about the table).
    data_regime, data_reason = REGIME_UNKNOWN, "no claim recorded a regime"
    for record in records:
        if record["claim"] == CLAIM_CONSTANTS:
            data_regime, data_reason = record["regime"], record["regime_reason"]
            break

    await _record_input_artifact(
        meta.data_path, "dataset", exec_id, backend, config, execute_tool, report,
        description=(
            f"LLM-SR transfer target {_label(meta.data_path)!r} ({meta.run_id})"
        ),
        custom={
            "run_id": meta.run_id,
            "regime": data_regime,
            "regime_reason": data_reason,
            "transferred_onto": True,
            **({"group_by": meta.group_by} if meta.group_by else {}),
        },
    )

    if meta.run_id:
        script_path = _DISCOVERIES_DIR / f"{meta.run_id}.py"
        await _record_input_artifact(
            str(script_path), "script", exec_id, backend, config, execute_tool,
            report,
            description=f"LLM-SR discovered equation ({meta.run_id})",
            custom={"run_id": meta.run_id},
            language="python",
            optional=True,
        )

    # Skipped when the transfer targeted the run's OWN training table (a
    # legitimate control). It is then ONE input, not two, and registering it
    # twice would overwrite the regime reason the target write just recorded with
    # this more general one.
    if _same_file(meta.source_data_path, meta.data_path):
        return
    await _record_input_artifact(
        meta.source_data_path, "dataset", exec_id, backend, config, execute_tool,
        report,
        description=(
            f"LLM-SR source training table {_label(meta.source_data_path)!r} "
            f"({meta.run_id})"
        ),
        custom={
            "run_id": meta.run_id,
            "regime": REGIME_SCORED,
            "regime_reason": (
                "the source search fitted the transferred form's constants on "
                "this table"
            ),
        },
    )


def _same_file(a: str, b: str) -> bool:
    """Do two recorded paths name the same file? Never raises."""
    if not a or not b:
        return False
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return a == b


async def _record_input_artifact(
    path: str,
    artifact_type: str,
    exec_id: str,
    backend,
    config: WheelerConfig,
    execute_tool,
    report: ImportReport,
    *,
    description: str,
    custom: dict[str, Any],
    language: str = "",
    optional: bool = False,
) -> None:
    """Register one input file and link ``Execution -[USED]-> it``. Never raises.

    ``optional=True`` marks an input whose absence is an ordinary state rather
    than a defect: the source Script exists only once the DISCOVERY has been
    ingested, and a transfer ingested first is a legitimate order of operations,
    not a broken one. It is still logged, so the missing edge is never silent.
    """
    if not path:
        return
    if not Path(path).exists():
        report.skipped += 1
        logger.log(
            logging.INFO if optional else logging.WARNING,
            "ingest_transfer: input %s is not on disk; USED edge skipped",
            path,
        )
        return
    args: dict[str, Any] = {
        "path": str(Path(path).resolve()),
        "artifact_type": artifact_type,
        "service": _SERVICE_TAG,
        "description": description,
    }
    if language:
        args["language"] = language
    try:
        result = json.loads(await execute_tool("ensure_artifact", args, config))
    except Exception:
        report.skipped += 1
        logger.warning(
            "ingest_transfer: registering input %s raised; skipped", path,
            exc_info=True,
        )
        return
    node_id = result.get("node_id")
    if not node_id:
        report.skipped += 1
        logger.warning(
            "ingest_transfer: registering input %s returned no node (%s)",
            path, result.get("error", "no error reported"),
        )
        return
    if result.get("action") == "created":
        report.created += 1
    else:
        report.deduped += 1
    if custom:
        await execute_tool(
            "update_node", {"node_id": node_id, "custom": custom}, config
        )
    if await _link_once(backend, config, exec_id, "USED", node_id):
        report.used += 1


async def _record_claim_finding(
    record: dict[str, Any],
    meta: TransferMeta,
    session_id: str,
    link_to: str | None,
    backend,
    config: WheelerConfig,
    execute_tool,
    report: ImportReport,
    produced_ids: list[str],
) -> None:
    """One Finding for one CLAIM, carrying everything that earned its number.

    The two Findings from one transfer are the scientific core of the verb and
    they must stay two nodes. They are the same metric on the same table and they
    are NOT two measurements of one thing:

    - the FORM claim refitted the constants HERE, so its regime is
      ``held_out_form``: held out for the form, never for the constants.
    - the CONSTANTS claim applied the source run's own vector unchanged, so its
      regime is the data's, ``held_out`` for a table the search never touched.

    ``discover._finding_id`` keys on the claim, so the two ids differ by
    construction; the split token names this transfer, so neither can collide
    with a Finding from the discovery run it came from.

    A withheld fixed-theta number (``value`` is None) still gets its Finding.
    "No number, and here is which group had no legitimate source vector" is a
    fact the graph should carry; leaving it out would make an unanswerable
    question look like one nobody asked.
    """
    claim = record["claim"]
    refit = claim == CLAIM_FORM
    metric = meta.metric
    value = record["value"]
    regime = record["regime"]
    reason = record["regime_reason"]

    finding_id = _finding_id(meta.run_id, metric, meta.split_token, claim)
    where = f"on {_label(meta.data_path)}"
    val_str = f"{value:.4g}" if isinstance(value, float) else _as_str(value)
    group_note = ""
    if meta.group_by and record["value_per_group"]:
        group_note = (
            f" (mean over {len(record['value_per_group'])} {meta.group_by!r} "
            "groups)"
        )
    if refit:
        how = " with its constants REFITTED there from scratch"
        question = (
            "This asks whether the FORM transfers, which is what symbolic "
            "regression is looking for: a law that governs new data with "
            "different constants is the same law."
        )
    else:
        how = " with the source run's own constants applied unchanged"
        question = (
            "This asks whether the CONSTANTS transfer, which is a different and "
            "weaker question than whether the form does."
        )
    if value is None:
        headline = (
            f"LLM-SR transfer reported no {metric} value {where}{how}"
        )
    else:
        headline = (
            f"LLM-SR transferred form attains {metric} = {val_str}{group_note}"
            f" {where}{how}"
        )

    if regime == REGIME_SCORED:
        caveat = (
            f"SCORED, not held out: {reason}, so this is fit quality and not a "
            "generalization claim."
        )
    elif refit:
        caveat = (
            f"Held out for the FORM only: {reason}. It says nothing about "
            "whether the source constants transfer."
        )
    elif regime == REGIME_UNKNOWN:
        caveat = f"Regime unknown: {reason}."
    else:
        caveat = f"Held out: {reason}."
    caveat += " " + question
    if record["error"]:
        caveat += f" No number was reported here: {record['error']}"
    if record["measurement_note"]:
        caveat += " " + record["measurement_note"]
    # BOTH numbers on BOTH Findings, so a reader who lands on one is told the
    # other exists rather than taking this one for the answer to both questions.
    other = record["fixed_theta_value"] if refit else record["refit_value"]
    if other is not None:
        other_name = "fixed-theta" if refit else "refit"
        caveat += (
            f" The {other_name} number on the same data is {other:.4g}; neither "
            "substitutes for the other."
        )

    title = f"{metric}_transfer_{_label(meta.data_path)}"
    if refit:
        title += "_refit"

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
                    "title": title,
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
        "equation": meta.equation,
        "run_id": meta.run_id,
        # The "split" this number was measured on is a whole TABLE, named by its
        # path, not one of the run's sibling splits. It carries the same key name
        # as a discovery Finding so one query shape reads both.
        "split": meta.split_token,
        "transfer_data": meta.data_path,
        "source_data": meta.source_data_path,
        "regime": regime,
        "regime_reason": reason,
        "claim": claim,
        "measured_by": record["measured_by"],
        "candidate_sample_order": meta.sample_order,
        "selected_by": meta.selected_by,
        # The pair, labelled, on every Finding.
        "refit_value": record["refit_value"],
        "fixed_theta_value": record["fixed_theta_value"],
        "comparison_note": record["comparison_note"],
    }
    if record["refit_over_fixed"] is not None:
        custom["refit_over_fixed"] = record["refit_over_fixed"]
    if record["measurement_note"]:
        custom["measurement_note"] = record["measurement_note"]
    if meta.scored_metric:
        # The quantity the SOURCE SEARCH was scored on, which is NOT this number
        # (this one came from `fit.py` under the declared metric). Named so a
        # reader does not compare it against the run's headline as though the
        # two were the same measurement.
        custom["source_scored_metric"] = meta.scored_metric
    if record["error"]:
        custom["error"] = record["error"]
    if meta.complexity is not None:
        custom["complexity"] = meta.complexity
    if meta.group_by:
        custom["group_by"] = meta.group_by
    if record["value_per_group"]:
        custom["n_groups"] = len(record["value_per_group"])
        custom["value_per_group"] = json.dumps(record["value_per_group"])
    if record["params_per_group"]:
        custom["params_per_group"] = json.dumps(record["params_per_group"])
    if record["source_per_group"]:
        # Which group's constants came from where, and why a group has none.
        custom["source_per_group"] = json.dumps(record["source_per_group"])
    await execute_tool(
        "update_node", {"node_id": finding_id, "custom": custom}, config
    )
    if link_to and await _link_once(
        backend, config, finding_id, "RELEVANT_TO", link_to
    ):
        report.linked += 1
