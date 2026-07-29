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
     "metrics_refit": {"mse_test_ood": 0.04},
     "optimizer": {"requested": "auto", "used": "bfgs"},
     "selection": {"mode": "parsimony", ...}, "n_samples": N, "n_valid": M,
     # GROUPED runs only (`params` is empty for them, by construction):
     "group_by": "cell_id", "params_per_group": {"c01": [...], ...},
     "value_per_group": {"c01": 0.02, ...},
     # MULTI-DATASET runs only (`params` is empty for them too):
     "datasets": {"seed_from": "A", "score_on": ["B"], "entries": [
         {"name": "B", "path": "...", "seed": false, "regime": "scored",
          "value": 0.02, "keys": ["B"], "value_per_key": {"B": 0.02},
          "params_per_key": {"B": [...]}}, ...]}}

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
  - **A multi-unit run's answer is the TABLE.** Whenever a run has more than one
    fittable unit, whether that is several GROUPS in one table or several
    DATASETS or both, each unit refits its own constants under the one shared
    form and the flat ``params`` is empty by construction. The Script records the
    per-unit table (``params_per_group`` for a grouped single table,
    ``params_per_key`` for anything spanning datasets); recording the empty flat
    list would land the discovery in the graph with no constants at all.
  - **One Dataset node per scored dataset.** A multi-dataset run fitted constants
    on several tables, and each is an input the run genuinely USED. They are
    inputs, so they are never ``WAS_GENERATED_BY`` the Execution: they land as
    ``Execution -[USED]-> Dataset``, each carrying its own regime label.
  - **Every metric Finding is LABELLED by regime, by claim, and by what MEASURED
    it.** ``scored`` means the search optimized against that data, so the number
    is a fit quality and NOT a generalization claim; ``held_out`` means it did
    not; ``held_out_form`` means the constants were REFITTED on the split being
    reported, so it is held out for the FORM only; ``unknown`` means the artifact
    does not record enough to tell. Forty rounds of search against a split makes
    that split's error a training number however good it looks, and the graph must
    never present one as the other. Under ``--use-spec-evaluate`` the split
    numbers were computed by Wheeler's own fit seam under the run's DECLARED
    metric rather than by the spec's ``@evaluate.run`` that scored the search, and
    the Finding says so instead of presenting a second opinion as the run's own
    objective.
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
#
# ``REGIME_HELD_OUT_FORM`` is the fourth and it is NOT a synonym for the third. A
# refit fits its constants on the very split it reports, so the split is held out
# for the FORM and never for the CONSTANTS. Calling it plain ``held_out`` would
# claim more than the measurement supports, which is the failure these labels
# exist to prevent. ``transfer.py`` labels its own refit block identically.
REGIME_SCORED = "scored"
REGIME_HELD_OUT = "held_out"
REGIME_HELD_OUT_FORM = "held_out_form"
REGIME_UNKNOWN = "unknown"
_REGIMES = (REGIME_SCORED, REGIME_HELD_OUT, REGIME_HELD_OUT_FORM, REGIME_UNKNOWN)

# What a number is a claim ABOUT, matching ``transfer.py``'s vocabulary. Applying
# the winner's own constants asks whether the CONSTANTS transfer; refitting them
# under the same form asks whether the FORM does. Neither ever stands in for the
# other, so both travel labelled.
CLAIM_CONSTANTS = "constants"
CLAIM_FORM = "form"

# What machinery produced a number. Under ``--use-spec-evaluate`` the SEARCH was
# scored by the spec's own ``@evaluate.run`` (``best.json``'s
# ``optimizer.scored_by``), while the held-out splits still run through
# ``fit.py`` + ``metrics.py`` under the run's DECLARED metric. Those numbers are a
# second opinion computed by different machinery, not the run's own objective
# measured again, and a Finding that did not say so would assert the stronger
# thing. The literal matches ``spec_eval.SPEC_EVALUATE``, duplicated rather than
# imported for the same reason ``transfer.py`` duplicates the regimes: this module
# is the graph writer and must not pull in a scoring door to read one string.
MEASURED_BY_FIT = "wheeler-fit"
SCORED_BY_SPEC_EVALUATE = "spec-evaluate"
_SECOND_OPINION_NOTE = (
    "Measured by Wheeler's own fit seam under the run's DECLARED metric, not by "
    "the spec's @evaluate.run that scored the search, so it is a second opinion "
    "computed by different machinery and not this run's own objective measured "
    "again."
)
# The caveat on the OTHER side of the same seam, and the one that was missing.
# A number the spec's own `@evaluate.run` produced is the SPEC'S objective: the
# spec owns its loss and never reports what it computed, and nothing checks that
# it equals the run's declared metric (a stock recipe minimizing MSE under a run
# declaring nmse returns an MSE). So it never travels under the declared metric's
# name, and it says why. This used to be omitted on the grounds that a number the
# search itself produced is "the run's own objective with no caveat", which is
# true of the OBJECTIVE and false of its NAME.
_SPEC_OBJECTIVE_NOTE = (
    "Measured by the spec's own @evaluate.run, which scored this search and owns "
    "its loss. The spec does not report what it computed and nothing checks that "
    "it equals the run's declared metric, so this number is named after the spec "
    "rather than after the declared metric. The declared metric appears only "
    "where Wheeler's fit seam computed it."
)


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


def _finding_id(
    run_id: str, metric: str, split: str = "train", claim: str = CLAIM_CONSTANTS
) -> str:
    """Deterministic Finding id so a re-ingest dedupes instead of duplicating.

    The SPLIT is part of the key, so a train number and a held-out number from
    one run are distinct nodes. ``train`` is the historic default, so ids minted
    before per-split Findings existed still resolve to the same node.

    The CLAIM is part of it too, and appended only when it is not the historic
    one: a fixed-theta number and a refit number on the SAME split are two
    different measurements of two different things, so they must be two nodes,
    while every id minted before the refit numbers were ingested still resolves.
    """
    key = f"{_SERVICE_TAG}:{run_id}:{metric}:{split or 'unlabeled'}"
    if claim and claim != CLAIM_CONSTANTS:
        key += f":{claim}"
    return "F-" + hashlib.sha256(key.encode()).hexdigest()[:8]


def _scored_metric(doc: dict[str, Any], declared: str) -> str:
    """The name of the quantity the SEARCH's own numbers are in. Never guessed.

    ``best.json`` carries a ``scored_metric`` block exactly when that is not the
    declared metric, which is the spec door (``runs.scored_metric_report``). The
    name is read out of the artifact rather than reconstructed here, for the same
    reason the regimes are: only the RUN knows how it was scored, and a
    reconstruction would drift.

    An artifact written before the block existed, or one whose block is
    shape-drifted, falls back to the declared metric. That is the pre-spec-door
    answer and it is right for every default-door run, which is all an older
    artifact could be that this module can tell apart.
    """
    block = doc.get("scored_metric")
    if isinstance(block, dict):
        name = _as_str(block.get("name"))
        if name:
            return name
    return declared


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


def _refit_regime(regime: str, reason: str) -> tuple[str, str]:
    """The regime of a REFIT number, which is never simply the data's regime.

    A refit fits its constants on the very split it reports, so the number is
    held out for the FORM and not for the CONSTANTS. Reporting it as plain
    ``held_out`` would claim more than the measurement supports, which is exactly
    what these labels exist to prevent, and it is why S3 refused to smuggle the
    refit numbers into ``metrics`` under a suffix where this labeller would have
    called them clean held-out numbers.

    A SCORED split stays scored: refitting on data the search already optimized
    against does not turn it into a holdout of any kind. Same rule, same wording,
    as ``transfer._refit_regime``.
    """
    if regime == REGIME_HELD_OUT:
        return REGIME_HELD_OUT_FORM, (
            reason + ", but the constants WERE refitted on it, so this number is "
            "held out for the FORM only, never for the constants"
        )
    return regime, reason


@dataclass
class _RunContext:
    """What the whole run says about how any one of its numbers was earned.

    Read once off ``best.json`` and passed down, so every split entry is labelled
    from the same facts rather than from whatever was in scope where it was built.
    """

    select_mode: str = ""
    n_valid: int | None = None
    # `best.json["optimizer"]["scored_by"]`, present only when the run took the
    # spec's own @evaluate.run door. Empty means Wheeler's fit seam scored it.
    scored_by: str = ""

    def note_for(self, measured_by: str) -> str:
        """What produced this number, whenever that is worth saying. BOTH sides.

        A run that took the spec door has its numbers split across two pieces of
        machinery, and neither of them is "the run's declared metric measured by
        the thing that scored the search":

        - Wheeler's fit seam computed the held-out splits under the DECLARED
          metric, so those are a second opinion (``_SECOND_OPINION_NOTE``).
        - the spec's own ``@evaluate.run`` computed everything the SEARCH ranked,
          under a loss the spec owns and never names, so those are the spec's
          objective and not the declared metric (``_SPEC_OBJECTIVE_NOTE``).

        The second used to return ``""`` on the reasoning that a number the
        search itself produced is the run's own objective needing no caveat. That
        holds for the QUANTITY and fails for its NAME, which is how the spec's
        MSE reached the graph labelled ``nmse``. A default-door run has one piece
        of machinery and still gets no note at all.
        """
        if self.scored_by != SCORED_BY_SPEC_EVALUATE:
            return ""
        return (
            _SPEC_OBJECTIVE_NOTE
            if measured_by == self.scored_by
            else _SECOND_OPINION_NOTE
        )


def _split_record(
    split: str,
    metric: str,
    value: float | None,
    values: dict[str, float],
    ctx: _RunContext,
    *,
    claim: str = CLAIM_CONSTANTS,
    measured_by: str = MEASURED_BY_FIT,
) -> dict[str, Any]:
    """One labelled split entry: what number, on what data, earned how, by what.

    ``claim`` says WHAT the number is about (do the CONSTANTS transfer, or does
    the FORM), and ``measured_by`` says WHICH machinery produced it. Both ride
    onto the Finding, because a run scored through the spec's own evaluate has
    held-out numbers computed by a different door than the one that ranked its
    candidates.
    """
    regime, reason = _split_regime(split, ctx.select_mode, ctx.n_valid)
    if claim == CLAIM_FORM:
        regime, reason = _refit_regime(regime, reason)
    return {
        "split": split,
        "metric": metric,
        "value": value,
        # the same split under the run's other reported metric (mse next to nmse)
        "others": {k: v for k, v in values.items() if k != metric},
        "regime": regime,
        "regime_reason": reason,
        "claim": claim,
        "measured_by": measured_by,
        "measurement_note": ctx.note_for(measured_by),
    }


def _bucket_by_split(metrics: Any) -> dict[str, dict[str, float]]:
    """Bucket a ``<metric>_<split>`` dict by the split each number was measured on."""
    by_split: dict[str, dict[str, float]] = {}
    if not isinstance(metrics, dict):
        return by_split
    for raw_key, raw_val in metrics.items():
        val = _as_float(raw_val)
        if val is None:
            continue
        mkey, split = _split_key(str(raw_key))
        by_split.setdefault(split, {})[mkey] = val
    return by_split


def _ordered_splits(by_split: dict[str, dict[str, float]]) -> list[str]:
    """Wheeler's split order first, then anything else, sorted, so it is stable."""
    ordered = [s for s in _SPLITS if s in by_split]
    return ordered + sorted(s for s in by_split if s not in _SPLITS)


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
    params_raw = doc.get("params")
    params = params_raw if isinstance(params_raw, list) else []

    # How the winner was chosen, out of how many, and through which scoring door.
    # The first two feed the regime label (`--select ood` means the OOD split
    # picked the winner, so it was optimized against, unless there was only one
    # valid candidate to pick from). The third says whether a held-out number was
    # computed by the same machinery that scored the search.
    selection_raw = doc.get("selection")
    select_mode = (
        _as_str(selection_raw.get("mode")).lower()
        if isinstance(selection_raw, dict)
        else ""
    )
    n_valid_raw = _as_float(doc.get("n_valid"))
    optimizer_raw = doc.get("optimizer")
    ctx = _RunContext(
        select_mode=select_mode,
        n_valid=int(n_valid_raw) if n_valid_raw is not None else None,
        scored_by=(
            _as_str(optimizer_raw.get("scored_by"))
            if isinstance(optimizer_raw, dict)
            else ""
        ),
    )

    group_by, params_per_group, value_per_group = _parse_groups(doc)
    dataset_report = _parse_dataset_report(doc)
    params_per_key, value_per_key = _scored_units(dataset_report)

    by_split = _bucket_by_split(doc.get("metrics"))
    refit_by_split = _bucket_by_split(doc.get("metrics_refit"))

    # What the SEARCH'S own per-unit numbers are in, which is the declared metric
    # on the default door and the SPEC'S objective through the spec door. Every
    # number derived from `value_per_group` / `value_per_key` is labelled with
    # this, never with the declared metric, because through that door the spec
    # owns the loss and nothing checks the two are the same quantity.
    scored_name = _scored_metric(doc, metric)

    # The headline number is the TRAIN one, and only the train one: a held-out
    # number stands in for it nowhere, which is the whole point of the labels.
    train_values = by_split.pop("train", {})
    # `metrics` is computed by `fit.py` on both doors, so a number read out of it
    # is a Wheeler-fit number under the DECLARED metric, whatever scored the search.
    train_measured_by = MEASURED_BY_FIT
    value_metric = metric
    value = train_values.get(metric)
    if value is None and train_values:
        value = train_values[sorted(train_values)[0]]
        value_metric = sorted(train_values)[0]
    value_is_group_mean = False
    value_is_unit_mean = False
    if value is None and value_per_key:
        # A MULTI-DATASET run reports no scalar in `metrics`: the flat `params`
        # is empty, so `evaluate_fixed` has no vector to apply and `_split_metrics`
        # returns nothing for it. Every scored UNIT reported its own value, and
        # the mean over them is exactly the scalar `fit.py` aggregates to
        # (`sum(per_group_value) / len(per_group_value)`), so it is DERIVED, not
        # invented, and it travels labelled so nothing reads it as a pooled fit.
        value = sum(value_per_key.values()) / len(value_per_key)
        value_is_unit_mean = True
        train_measured_by = ctx.scored_by or MEASURED_BY_FIT
        # Derived from the numbers the SEARCH produced, so it is in the quantity
        # the search was scored on, whatever that is. This is the path every
        # grouped and every multi-dataset run takes, which is precisely the shape
        # the per-group protocol exists for, so getting the name right here is
        # not an edge case.
        value_metric = scored_name
    elif value is None and value_per_group:
        # The same derivation one level down: a grouped single-table run.
        value = sum(value_per_group.values()) / len(value_per_group)
        value_is_group_mean = True
        train_measured_by = ctx.scored_by or MEASURED_BY_FIT
        value_metric = scored_name

    # Train first (always present, even when the run reported no number, so the
    # discovery still lands), then any held-out splits the run scored. The train
    # entry is labelled with what PRODUCED its number (`value_metric`), which is
    # the declared metric wherever `fit.py` computed it and the spec's own
    # objective wherever the search's per-unit table was averaged.
    splits = [
        _split_record(
            "train", value_metric, value, train_values, ctx,
            measured_by=train_measured_by,
        )
    ]
    for split in _ordered_splits(by_split):
        values = by_split[split]
        headline = metric if metric in values else sorted(values)[0]
        splits.append(
            _split_record(split, headline, values[headline], values, ctx)
        )

    # The REFIT numbers, which answer the other half of "does it generalize":
    # the constants were fitted from scratch on the split being reported, so each
    # is a claim about the FORM alone. Kept in their own list rather than folded
    # in beside the fixed-theta ones, because a split now carries two numbers that
    # are not interchangeable and must never collide into one Finding.
    refit_splits = []
    for split in _ordered_splits(refit_by_split):
        values = refit_by_split[split]
        headline = metric if metric in values else sorted(values)[0]
        refit_splits.append(
            _split_record(
                split, headline, values[headline], values, ctx, claim=CLAIM_FORM,
            )
        )

    record = {
        "equation": equation,
        "program": program,
        "params": params,
        # Three metric names, because a run can genuinely hold three answers to
        # "which quantity is this". `metric` is what the run DECLARED (and what
        # `metrics` / `metrics_refit` are in, on both doors). `scored_metric` is
        # what the SEARCH'S own per-unit numbers are in. `value_metric` is what
        # the headline `value` below is in, which is one or the other depending
        # on where it came from. They coincide on every default-door run.
        "metric": metric,
        "scored_metric": scored_name,
        "value_metric": value_metric,
        "value": value,
        "value_is_group_mean": value_is_group_mean,
        "value_is_unit_mean": value_is_unit_mean,
        "group_by": group_by,
        "params_per_group": params_per_group,
        "value_per_group": value_per_group,
        "datasets": dataset_report,
        "params_per_key": params_per_key,
        "value_per_key": value_per_key,
        "select_mode": select_mode,
        "scored_by": ctx.scored_by,
        "splits": splits,
        "refit_splits": refit_splits,
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


def _float_list(value: Any) -> list[float]:
    """A list of numbers, dropping whatever is not one. Never raises."""
    if not isinstance(value, list):
        return []
    return [f for f in (_as_float(v) for v in value) if f is not None]


def _float_map(value: Any) -> dict[str, float]:
    """A ``key -> number`` map, dropping whatever is not one. Never raises."""
    if not isinstance(value, dict):
        return {}
    out: dict[str, float] = {}
    for key, raw in value.items():
        val = _as_float(raw)
        if val is not None:
            out[str(key)] = val
    return out


def _parse_dataset_report(doc: dict[str, Any]) -> dict[str, Any]:
    """Lift a MULTI-DATASET run's per-dataset breakdown, or ``{}`` for any other.

    ``best.json["datasets"]`` is absent on a single-default-dataset run, which is
    exactly the run an older Wheeler could have created, so a caller sees the
    empty dict and takes the path it always took.

    Each entry keeps the regime ``cli.py::_dataset_report`` assigned it, because
    only the RUN knows which tables entered its objective. A regime this module
    does not recognize is reported ``unknown`` rather than being coerced into the
    flattering answer: the vocabulary is closed on purpose.
    """
    raw = doc.get("datasets")
    if not isinstance(raw, dict):
        return {}
    entries: list[dict[str, Any]] = []
    for item in raw.get("entries") or []:
        if not isinstance(item, dict) or not _as_str(item.get("name")):
            continue
        regime = _as_str(item.get("regime"))
        reason = _as_str(item.get("regime_reason"))
        if regime not in _REGIMES:
            regime, reason = REGIME_UNKNOWN, (
                "the run report did not label this dataset with a regime this "
                f"version knows ({regime or 'none recorded'})"
            )
        params_per_key: dict[str, list[float]] = {}
        raw_params = item.get("params_per_key")
        if isinstance(raw_params, dict):
            for key, vals in raw_params.items():
                floats = _float_list(vals)
                if floats:
                    params_per_key[str(key)] = floats
        entries.append({
            "name": _as_str(item.get("name")),
            "path": _as_str(item.get("path")),
            "seed": bool(item.get("seed")),
            "regime": regime,
            "regime_reason": reason,
            "value": _as_float(item.get("value")),
            "keys": [_as_str(k) for k in (item.get("keys") or []) if _as_str(k)],
            "value_per_key": _float_map(item.get("value_per_key")),
            "params_per_key": params_per_key,
        })
    if not entries:
        return {}
    return {
        "seed_from": _as_str(raw.get("seed_from")),
        "score_on": [_as_str(n) for n in (raw.get("score_on") or []) if _as_str(n)],
        "score_key_scheme": _as_str(raw.get("score_key_scheme")),
        "entries": entries,
    }


def _scored_units(
    report: dict[str, Any],
) -> tuple[dict[str, list[float]], dict[str, float]]:
    """The constants and values of every SCORED unit, merged across datasets.

    Scored only, and this is the whole discipline of the function: a held-out
    entry carries no value BECAUSE the run never computed one for it, so folding
    it in would either invent a number or silently shrink the denominator of the
    mean derived from these. Keys are ``dataset`` or ``dataset:group``.
    """
    params: dict[str, list[float]] = {}
    values: dict[str, float] = {}
    for entry in report.get("entries", []):
        if entry.get("regime") != REGIME_SCORED:
            continue
        params.update(entry.get("params_per_key") or {})
        values.update(entry.get("value_per_key") or {})
    return params, values


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
    """Create the Script (program + constants), the input Datasets, the Findings."""
    value = record["value"]
    multi = _is_multi(record)
    grouped = _is_grouped(record)

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
                    # `metric` sits next to `value`, so it names what produced
                    # `value`, not what the run declared. The two differ only
                    # through the spec door, and then the declared one rides
                    # alongside under its own name rather than over this number.
                    "metric": record["value_metric"],
                    "value": value,
                    "run_dir": f".wheeler/llmsr/runs/{run_meta.run_id}",
                    "generator": run_meta.generator,
                }
                custom.update(_declared_metric_custom(record, record["value_metric"]))
                if multi:
                    # The TABLE is the answer, keyed by UNIT: a run that spans
                    # datasets fitted one constant vector per (dataset, group)
                    # pair under one shared form. The flat `params` is empty by
                    # construction for it, exactly as for a grouped run, so
                    # recording it would land the discovery with no constants.
                    custom.update(_unit_table_custom(record))
                elif grouped:
                    # The same, one level down: a grouped single-table run keys
                    # its table by group label.
                    # The units are the GROUPS, and they are named off whichever
                    # per-group table the run actually reported. A bare-float
                    # spec run has values and no constants, and a three-group
                    # discovery must not land as a one-unit run because of it.
                    labels = sorted(
                        record["params_per_group"] or record["value_per_group"]
                    )
                    custom.update(
                        {
                            "group_by": record["group_by"],
                            "n_groups": len(labels),
                            "groups": json.dumps(labels),
                            "value_per_group": json.dumps(record["value_per_group"]),
                            "value_is_group_mean": record["value_is_group_mean"],
                        }
                    )
                    if record["params_per_group"]:
                        custom["params_per_group"] = json.dumps(
                            record["params_per_group"]
                        )
                elif record["params"]:
                    custom["params"] = json.dumps(record["params"])
                # No constants of ANY shape, which only upstream's bare-float
                # return can produce. Said outright rather than left as an empty
                # list: `params "[]"` reads as "it fitted nothing", and what
                # happened is that the spec never handed them back.
                if _no_constants(record):
                    custom["no_constants"] = True
                    custom["no_constants_reason"] = _NO_CONSTANTS_NOTE
                await execute_tool(
                    "update_node",
                    {"node_id": script_id, "custom": custom},
                    config,
                )
                if link_to and await _link_once(
                    backend, config, script_id, "RELEVANT_TO", link_to
                ):
                    report.linked += 1

    # 2. One Dataset per declared table, on the INPUT side of the Execution.
    await _record_datasets(
        record, run_meta, exec_id, backend, config, execute_tool, report
    )

    # 3. One Finding per scored split, each LABELLED by regime, then the same
    # splits again with the constants REFITTED. The two are separate nodes on
    # purpose: one asks whether the CONSTANTS transfer and the other whether the
    # FORM does, and a reader who saw only one number would take it for both.
    for entry in record["splits"] + record["refit_splits"]:
        await _record_split_finding(
            entry, record, run_meta, session_id, link_to,
            backend, config, execute_tool, report, produced_ids,
        )


def _is_multi(record: dict[str, Any]) -> bool:
    """Do this run's units span several DATASETS? Asked of the units, not the constants.

    A unit exists because the run FITTED it, and it reported a value for it; the
    constants are what the fit chose to hand back, and upstream's bare-float
    contract hands back none (``spec_eval``, ``selection._no_constants_footer``).
    Reading the shape off the constants alone therefore misfiled every
    bare-float run as a one-unit run, and the graph then presented a
    many-unit discovery as a single flat fit.
    """
    return bool(record["params_per_key"] or record["value_per_key"])


def _is_grouped(record: dict[str, Any]) -> bool:
    """Is this run a GROUPED single table? Same rule, one level down.

    A run that declared ``--group-by`` and refitted every group is grouped
    whether or not the constants survived the return trip. ``value_per_group``
    is the run's per-group answer and it is present either way, so it is what the
    question is asked of.
    """
    return bool(
        record["group_by"]
        and (record["params_per_group"] or record["value_per_group"])
    )


def _no_constants(record: dict[str, Any]) -> bool:
    """Did this run report units but NO constants for any of them?

    True only for upstream's bare-float return through the spec door, where the
    contract has nowhere to put the fitted constants: every upstream spec
    computes ``optimized_params = result.x`` inside ``evaluate`` and discards it.
    Recorded on the node rather than left to be inferred from an absent field,
    because "no constants were returned" and "the constants are missing from the
    graph" look identical to a reader and are not the same fact.
    """
    return not (
        record["params"] or record["params_per_group"] or record["params_per_key"]
    )


# What a node says when the run genuinely had no constants to record. Named here
# so the Script node and `selection._no_constants_footer` say the same thing.
_NO_CONSTANTS_NOTE = (
    "The spec's own @evaluate.run returned upstream's bare score and no fitted "
    "constants (upstream's contract has nowhere to put them), so this run has "
    "none to record. The form and its per-unit values are the discovery. To "
    "recover the constants, have the spec's evaluate return {'score': ..., "
    "'params': [...]}, or drop --use-spec-evaluate."
)


def _declared_metric_custom(
    record: dict[str, Any], label: str, *, with_note: bool = True
) -> dict[str, Any]:
    """Name the run's DECLARED metric beside a number that is not in it.

    Empty whenever the number IS in the declared metric, which is every
    default-door run: a node that gained a ``declared_metric`` equal to its own
    ``metric`` would invite a reader to look for a distinction that is not there.

    ``with_note=False`` for a Finding, which carries its own per-split
    ``measurement_note`` from ``_RunContext.note_for`` and must not have it
    overwritten by this more general one.
    """
    if label == record["metric"]:
        return {}
    out: dict[str, Any] = {"declared_metric": record["metric"]}
    if with_note:
        out["measurement_note"] = _SPEC_OBJECTIVE_NOTE
    return out


def _unit_table_custom(record: dict[str, Any]) -> dict[str, Any]:
    """The per-unit constant table plus the dataset roles, for the Script node.

    Keys are ``dataset`` or ``dataset:group``, matching the score keys the search
    itself used, so a Script property and a ``best.json`` score key name the same
    thing. The scored / held-out split is carried too, because "which tables was
    this form actually fitted on" is not answerable from the constants alone.
    """
    report = record["datasets"]
    entries = report.get("entries", [])
    scored = sorted(e["name"] for e in entries if e["regime"] == REGIME_SCORED)
    held_out = sorted(e["name"] for e in entries if e["regime"] != REGIME_SCORED)
    # The units are named off whichever per-key table the run reported. A
    # bare-float spec run has values and no constants, and the unit COUNT is a
    # property of the run either way.
    keys = sorted(record["params_per_key"] or record["value_per_key"])
    custom: dict[str, Any] = {
        "n_keys": len(keys),
        "keys": json.dumps(keys),
        **(
            {"params_per_key": json.dumps(record["params_per_key"])}
            if record["params_per_key"]
            else {}
        ),
        "value_per_key": json.dumps(record["value_per_key"]),
        "value_is_unit_mean": record["value_is_unit_mean"],
        "n_datasets_scored": len(scored),
        "datasets_scored": json.dumps(scored),
        "datasets_held_out": json.dumps(held_out),
        "seed_from": report.get("seed_from", ""),
        "score_key_scheme": report.get("score_key_scheme", ""),
    }
    if record["group_by"]:
        custom["group_by"] = record["group_by"]
    return custom


async def _record_datasets(
    record: dict[str, Any],
    run_meta: RunMeta,
    exec_id: str,
    backend,
    config: WheelerConfig,
    execute_tool,
    report: ImportReport,
) -> None:
    """One Dataset node per declared table, each ``USED`` by the run Execution.

    These are INPUTS, so they are deliberately absent from ``produced_ids``: a
    Dataset the run read is never ``WAS_GENERATED_BY`` it, on the same rule that
    keeps reference-entity Papers off that edge in the Asta adapters.

    Every declared table lands, not only the scored ones, and each carries the
    regime the RUN assigned it. A held-out table is still an input (the seed one
    shaped the prompt, so the generator did see it) and recording only the scored
    ones would leave the graph unable to answer which tables a form was NOT
    fitted on, which is the more interesting half of the question.

    Defensive throughout, like the rest of this module: a table whose file has
    moved since the run cannot be hashed, so it is counted and skipped rather
    than aborting an ingest that has already written the answer.
    """
    entries = record["datasets"].get("entries", []) if record["datasets"] else []
    if not entries or not exec_id:
        return
    for entry in entries:
        path = entry["path"]
        if not path or not Path(path).exists():
            report.skipped += 1
            logger.warning(
                "ingest_discover: dataset %r is not on disk at %s; skipped",
                entry["name"], path or "<no path recorded>",
            )
            continue
        try:
            result = json.loads(
                await execute_tool(
                    "ensure_artifact",
                    {
                        "path": str(Path(path).resolve()),
                        "artifact_type": "dataset",
                        "service": _SERVICE_TAG,
                        "description": (
                            f"LLM-SR {entry['regime']} input {entry['name']!r} "
                            f"({run_meta.run_id})"
                        ),
                    },
                    config,
                )
            )
        except Exception:
            report.skipped += 1
            logger.warning(
                "ingest_discover: registering dataset %r raised; skipped",
                entry["name"], exc_info=True,
            )
            continue
        ds_id = result.get("node_id")
        if not ds_id:
            report.skipped += 1
            logger.warning(
                "ingest_discover: registering dataset %r returned no node (%s)",
                entry["name"], result.get("error", "no error reported"),
            )
            continue
        if result.get("action") == "created":
            report.created += 1
        else:
            report.deduped += 1
        custom: dict[str, Any] = {
            "run_id": run_meta.run_id,
            "dataset_name": entry["name"],
            "regime": entry["regime"],
            "regime_reason": entry["regime_reason"],
            "seeded_the_prompt": entry["seed"],
            # `value` / `value_per_key` below are the numbers the SEARCH produced
            # on this table, so they carry the search's own metric name, which is
            # the spec's objective through the spec door.
            "metric": record["scored_metric"],
            "score_keys": json.dumps(entry["keys"]),
            **_declared_metric_custom(record, record["scored_metric"]),
        }
        if entry["value"] is not None:
            custom["value"] = entry["value"]
        if entry["value_per_key"]:
            custom["value_per_key"] = json.dumps(entry["value_per_key"])
        if entry["params_per_key"]:
            custom["params_per_key"] = json.dumps(entry["params_per_key"])
        await execute_tool(
            "update_node", {"node_id": ds_id, "custom": custom}, config
        )
        if await _link_once(backend, config, exec_id, "USED", ds_id):
            report.used += 1


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
    """One Finding for one split, carrying everything that earned its number.

    The labels are the guardrail, and there are three of them. REGIME: a number
    the search optimized against is a fit quality, and the graph must never offer
    it as a generalization claim. CLAIM: applying the winner's own constants asks
    whether the CONSTANTS transfer, refitting them asks whether the FORM does,
    and neither answers the other. MEASURED_BY: under ``--use-spec-evaluate`` the
    split numbers come from Wheeler's fit seam rather than from the door that
    scored the search, so they are a second opinion and say so. Where the
    artifact does not record enough, the Finding says ``unknown`` instead of
    picking the flattering answer.
    """
    metric = entry["metric"]
    split = entry["split"]
    value = entry["value"]
    regime = entry["regime"]
    reason = entry["regime_reason"]
    claim = entry["claim"]
    refit = claim == CLAIM_FORM
    multi = _is_multi(record)
    grouped = _is_grouped(record)

    finding_id = _finding_id(run_meta.run_id, metric, split, claim)
    dataset_name = _dataset_label(record["data_path"])
    val_str = f"{value:.4g}" if isinstance(value, float) else _as_str(value)
    where = f"on {dataset_name} ({split or 'unlabelled split'})"
    mean_note = ""
    if split == "train" and record["value_is_unit_mean"]:
        mean_note = (
            f" (mean over {len(record['value_per_key'])} scored (dataset, group) "
            "units, each refitting its own constants)"
        )
    elif split == "train" and record["value_is_group_mean"]:
        mean_note = (
            f" (mean over {len(record['value_per_group'])} "
            f"{record['group_by']!r} groups, each refitting its own constants)"
        )
    how = " with its constants REFITTED here" if refit else ""
    if value is None:
        headline = f"LLM-SR run reported no {metric} value {where}"
    else:
        headline = (
            f"LLM-SR discovered equation attains {metric} = {val_str}"
            f"{mean_note}{how} {where}"
        )
    if regime == REGIME_SCORED:
        caveat = (
            f"SCORED, not held out: {reason}, so this is fit quality and not a "
            "generalization claim."
        )
    elif regime == REGIME_HELD_OUT_FORM:
        caveat = (
            f"Held out for the FORM only: {reason}. It says nothing about whether "
            "the source constants transfer."
        )
    elif regime == REGIME_HELD_OUT:
        caveat = f"Held out: {reason}."
    else:
        caveat = f"Regime unknown: {reason}."
    if entry["measurement_note"]:
        caveat += " " + entry["measurement_note"]

    title = f"{metric}_{split}" if split else metric
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
        "equation": record["equation"],
        "run_id": run_meta.run_id,
        "split": split,
        "regime": regime,
        "regime_reason": reason,
        "claim": claim,
        "measured_by": entry["measured_by"],
    }
    if entry["measurement_note"]:
        custom["measurement_note"] = entry["measurement_note"]
    # A Finding whose number is not in the run's declared metric names that
    # metric too, so a reader who came looking for `nmse` finds out here that
    # this number is a different quantity rather than concluding it is a bad one.
    custom.update(_declared_metric_custom(record, metric, with_note=False))
    # the same split under the run's other reported metric (nmse beside mse)
    for other_key, other_val in entry["others"].items():
        custom[f"value_{other_key}"] = other_val
    if split == "train" and not refit and multi:
        custom.update(
            {
                "n_keys": len(record["value_per_key"]),
                "value_per_key": json.dumps(record["value_per_key"]),
                "value_is_unit_mean": record["value_is_unit_mean"],
                "n_datasets_scored": len(
                    [
                        e for e in record["datasets"].get("entries", [])
                        if e["regime"] == REGIME_SCORED
                    ]
                ),
            }
        )
        if record["group_by"]:
            custom["group_by"] = record["group_by"]
    elif split == "train" and not refit and grouped:
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
