"""The other scoring door: call the spec's own ``@evaluate.run``.

A spec declares an ``@evaluate.run`` function that fits a candidate's free
constants and returns its score, and upstream's loop calls it
(``vendor/evaluator.py::LocalSandbox._compile_and_run_function`` execs the
program and then calls ``function_to_run(dataset)``). Wheeler's default does not:
it parses the name into ``meta["function_to_run"]`` and scores through ``fit.py``
+ ``metrics.py`` instead, which is what makes the metric pluggable, the constants
recoverable for ``best.json``, and per-unit refitting possible.

That substitution stays the DEFAULT. This module makes it a CHOICE: a run created
with ``wheeler llmsr init --use-spec-evaluate`` scores every candidate by calling
the spec's own ``evaluate`` instead.

How wide the door is, in upstream's own terms: their
``specification_oscillator2_torch.txt`` defines a ``torch.nn.Module``, an Adam
optimizer, and a 10,000-step gradient loop INSIDE the spec file, and the
unmodified package runs it, because it never looks inside ``evaluate``. Wheeler's
default cannot: it calls ``equation(*cols, params)`` under its own numpy
convention and fits the constants itself. Through this door the spec's arbitrary
Python runs, whatever it imports and whatever it optimizes with.

Three rules the door does not bend on:

**Opt-in by FLAG, never by sniffing.** Nothing here inspects the body of
``evaluate`` to guess whether it looks stock. Detection would silently change how
a run is scored when somebody edits a comment, and a scoring change nobody asked
for is the exact failure this whole issue exists to remove.

**One call per UNIT.** A run's fittable unit is a (dataset, group) pair, and the
spec's ``evaluate`` is called once per unit with that unit's rows. Calling it once
for the whole candidate would throw away the per-unit refit, which is the point of
the per-group protocol: a form that governs 40 cells with 40 constant sets must
not be charged for variation that belongs to the PARAMETERS.

**The score KEYS are the run's, never the spec's.** Keys come from
``data.score_key`` and are fixed at ``init``, because the vendored buffer clusters
candidates on the sorted score signature. A spec that could name its own keys
would silently invalidate the buffer state of every run on disk. A returned
``per_group`` that names anything other than the unit the call covered is
therefore an error, and a loud one.

The return contract is additive over upstream's:

``float`` (or ``int``)
    Exactly upstream's contract (``isinstance(results, (int, float))`` in
    ``vendor/evaluator.py``): the number is the MAXIMIZE-ME score, which is why
    every upstream spec ends ``return -loss``. Wheeler orients it the way the
    run's metric is oriented and reports it as the SPEC'S own objective, under
    the spec's own name (see ``_value_from_score`` and ``runs.scored_metric``):
    the spec owns its loss and never says what it computed, so this number is
    not the declared metric and is never labelled as it. There are no constants
    either, because upstream's contract has nowhere to put them.
``dict``
    ``{"score": float, "params": [...], "per_group": {...}}``, carrying what
    Wheeler needs and upstream throws away: every upstream spec computes
    ``optimized_params = result.x`` and then discards it. ``score`` is the same
    maximize-me number; ``params`` are that unit's fitted constants; ``per_group``
    may name the unit this call covered and supply its score, and nothing else.

Anything else (``None``, a string, an array, a dict with no score, a non-finite
number) makes the candidate INVALID with a truthful error. Upstream returns
``None`` for a non-finite loss and drops the candidate; here that becomes a
recorded invalid candidate, never a fabricated score.

Both doors normalize into the same ``fit.FitResult``, so ``submit``, ``best``,
``transfer``, selection and ``discover.py`` are unchanged downstream.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .fit import UNGROUPED, FitResult, _emit_progress, _run_sandboxed
from .metrics import Metric

logger = logging.getLogger(__name__)

# What ``FitResult.optimizer`` reports for a candidate the spec scored. The run's
# own optimizer knobs (``--optimizer``, ``--restarts``, ``--seed``) are not
# consulted at all on this path, so naming one of them here would attribute a
# number to machinery that never touched it.
SPEC_EVALUATE = "spec-evaluate"

# The keys a returned dict may carry. Anything else is a spec talking to a
# contract that does not exist, and is reported rather than ignored.
_RESULT_KEYS = frozenset({"score", "params", "per_group"})


def _as_float(value: Any) -> float | None:
    """A finite Python float, or ``None``. Rejects bools, arrays, and strings.

    ``bool`` is an ``int`` in Python, so upstream's ``isinstance(results, (int,
    float))`` would read ``True`` as the score ``1``. A spec returning a truth
    value has not computed a score, so that is refused here.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, np.floating, np.integer)):
        return None
    out = float(value)
    return out if np.isfinite(out) else None


def _as_params(value: Any) -> tuple[list[float] | None, str]:
    """A returned ``params`` as a flat list of floats, or ``(None, why)``."""
    if value is None:
        return [], ""
    try:
        arr = np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        return None, f"'params' is not a numeric sequence ({exc})"
    if not np.all(np.isfinite(arr)):
        return None, "'params' holds a non-finite value"
    return [float(v) for v in arr], ""


def _score_from_per_group(
    per_group: Any, key: str, group: str
) -> tuple[float | None, str]:
    """Read a returned ``per_group``, which may name ONLY the unit just scored.

    One call covers exactly one unit, so a ``per_group`` with any other key is a
    spec trying to name the score keys. It cannot: the keys are fixed at ``init``
    (``data.key_scheme``) and the vendored buffer clusters candidates on the
    sorted key signature, so a candidate that invented its own keys would be
    incomparable with every other candidate in the run, silently.
    """
    if per_group is None:
        return None, ""
    if not isinstance(per_group, Mapping):
        return None, "'per_group' is not a mapping"
    allowed = {key, group}
    stray = sorted(str(k) for k in per_group if str(k) not in allowed)
    if stray:
        return None, (
            f"'per_group' names {stray}, but this call scored only the unit "
            f"{key!r}. The score keys belong to the run (they are fixed at init "
            "and the buffer clusters candidates on them), so a spec may report "
            "per_group only for the unit it was handed."
        )
    for name in (key, group):
        if name in per_group:
            value = _as_float(per_group[name])
            if value is None:
                return None, f"'per_group[{name!r}]' is not a finite number"
            return value, ""
    return None, ""


def _normalize(raw: Any, key: str, group: str) -> dict:
    """Turn one ``evaluate`` return into the per-unit dict the parent assembles.

    Mirrors ``fit._fit_one_group``'s shape exactly (``valid``, ``score``,
    ``value`` is derived by the parent, ``params``, ``error``,
    ``rejection_reason``) so both doors converge on the same ``FitResult``.
    """
    score = _as_float(raw)
    if score is not None:
        # Upstream's contract, unchanged: a bare number IS the maximize-me score,
        # and there is nowhere in it to return the constants.
        return {"valid": True, "score": score, "params": []}

    if not isinstance(raw, Mapping):
        return {
            "valid": False,
            "rejection_reason": "numeric",
            "error": (
                f"@evaluate.run returned {type(raw).__name__}, which is neither a "
                "finite int/float score (upstream's contract) nor a dict carrying "
                "'score'"
            ),
        }

    stray = sorted(str(k) for k in raw if str(k) not in _RESULT_KEYS)
    if stray:
        return {
            "valid": False,
            "rejection_reason": "numeric",
            "error": (
                f"@evaluate.run returned unknown key(s) {stray}; the dict contract "
                f"is {sorted(_RESULT_KEYS)}"
            ),
        }

    from_per_group, why = _score_from_per_group(raw.get("per_group"), key, group)
    if why:
        return {"valid": False, "rejection_reason": "numeric", "error": why}

    score = _as_float(raw.get("score")) if "score" in raw else from_per_group
    if score is None:
        detail = (
            "'score' is not a finite number" if "score" in raw
            else "no 'score' (nor a 'per_group' entry for this unit)"
        )
        return {
            "valid": False,
            "rejection_reason": "numeric",
            "error": f"@evaluate.run returned a dict with {detail}",
        }

    params, why = _as_params(raw.get("params"))
    if params is None:
        return {
            "valid": False,
            "rejection_reason": "numeric",
            "error": f"@evaluate.run returned a dict where {why}",
        }
    return {"valid": True, "score": score, "params": params}


def _data_for(X, y, group: str, grouped: bool) -> dict:
    """The ``data`` dict handed to the spec's ``evaluate``, in UPSTREAM'S shape.

    ``data['inputs']`` and ``data['outputs']`` are what every upstream spec reads
    (``inputs, outputs = data['inputs'], data['outputs']``), so an upstream spec
    runs here unmodified.

    ``data['groups']`` is Wheeler's one addition and appears only when the run
    declared ``--group-by``. It lines up row-for-row with the other two, like they
    do with each other, and is constant within a call BY CONSTRUCTION: one call is
    one unit, because the per-unit refit is the whole point of grouping. It is
    there so a spec can know WHICH cell it is fitting, not so it can partition
    anything.
    """
    data: dict[str, Any] = {"inputs": X, "outputs": y}
    if grouped:
        data["groups"] = np.full(np.asarray(X).shape[0], group)
    return data


def _spec_worker(program_str, function_to_run, units, grouped, progress_path,
                 dataset_of, q):
    """Exec the program once, then call the spec's ``evaluate`` per unit.

    Runs in the forked child (``fit._run_sandboxed``), which is also where the
    per-unit progress pings are written: the parent is blocked in ``proc.join``
    and cannot report anything until the whole candidate is done.

    The namespace is the spec's own. ``exec`` runs the spec preface, so whatever
    it imports (numpy, torch, anything) is bound before ``evaluate`` is called,
    and ``np`` is pre-bound only so a body written against the numpy convention
    without its own import still resolves. Nothing constrains what ``evaluate``
    then does: that is the door.
    """
    try:
        namespace: dict = {"np": np}
        exec(program_str, namespace)  # noqa: S102 - sandboxed, model-generated body
        run = namespace.get(function_to_run)
        if not callable(run):
            q.put({"error": f"no callable {function_to_run!r}"})
            return

        total = len(units)
        scored: dict[str, dict] = {}
        for done, (key, group, X, y) in enumerate(units, start=1):
            try:
                raw = run(_data_for(X, y, group, grouped))
            except Exception as exc:
                # The spec's own code failed on this unit. Named, never smoothed
                # into "no fit": a spec author has to see their own traceback line.
                scored[key] = {
                    "valid": False,
                    "rejection_reason": "numeric",
                    "error": f"@evaluate.run raised {type(exc).__name__}: {exc}",
                }
            else:
                scored[key] = _normalize(raw, key, group)
            _emit_progress(
                progress_path, (dataset_of or {}).get(key, UNGROUPED),
                key, done, total,
            )
        q.put({"units": scored})
    except Exception as exc:  # any failure in untrusted code -> invalid, never raise
        q.put({"error": f"{type(exc).__name__}: {exc}"})


def _value_from_score(metric: Metric, score: float) -> float:
    """Orient the spec's maximize-me score the way the run's metric is oriented.

    The exact inverse of ``metric.score_from_value``: negate when lower is
    better, identity otherwise. Orienting is ALL it does. The spec owns its loss
    and never says what it computed, so the number that comes out is the SPEC'S
    objective, not the run's declared metric, and nothing anywhere checks that
    the two are the same quantity (every bundled recipe minimizes mean squared
    error whatever ``--metric`` says).

    Which is why the value that leaves here does not travel under the declared
    metric's name. ``runs.scored_metric`` names it ``spec:<function_to_run>``,
    and ``best.json``, the emitted ``.py``, ``status`` and the graph Finding all
    use that name; ``optimizer.scored_by`` says which door, which is a different
    question and was never enough on its own. The declared metric labels only
    what ``fit.py`` computed.

    The orientation itself is load bearing and stays: ``selection`` ranks through
    ``metric.score_from_value``, so a value that did not round-trip would rank a
    ``lower_is_better=False`` metric backwards.
    """
    return -score if metric.lower_is_better else score


def evaluate_spec_grouped(
    program_str: str,
    function_to_run: str,
    units: Sequence[tuple[str, str, np.ndarray, Any]],
    metric: Metric,
    *,
    timeout_seconds: int = 30,
    progress_path: str | Path | None = None,
    dataset_of: dict[str, str] | None = None,
    grouped: bool = False,
) -> FitResult:
    """Score one candidate by calling the SPEC's ``evaluate``, once per unit.

    ``units`` are ``(key, group, X, y)``: the key is the run's own score key
    (``data.score_key``) and the group is the label the scientist's group column
    carries. Never raises; a failure of any kind comes back as an invalid
    ``FitResult`` with a named reason.

    Validity is STRICT, matching ``fit.evaluate_body_grouped``: a candidate is
    valid only if EVERY unit scored. The vendored island model keys its clusters
    on the score signature, so every candidate must present the same key set or
    the signatures are incomparable.

    The timeout scales with the unit count for the same reason the fit's does: it
    bounds one evaluation, and there are ``len(units)`` of them behind one fork.
    """
    _emit_progress(progress_path, None, None, 0, len(units))
    out = _run_sandboxed(
        _spec_worker,
        (program_str, function_to_run, list(units), grouped, progress_path,
         dataset_of),
        timeout_seconds * max(1, len(units)),
    )
    if "units" not in out:  # compile error, no such callable, timeout, dead child
        return FitResult(
            valid=False,
            error=out.get("error", "invalid"),
            rejection_reason="numeric",
        )

    per = out["units"]
    failed = [(key, r) for key, r in per.items() if not r.get("valid")]
    if failed:
        key, first = sorted(failed, key=lambda kv: kv[0])[0]
        detail = first.get("error", "invalid")
        # Name the unit only when there IS one to name, matching the fit's rule:
        # an ungrouped single-dataset run has no unit to blame.
        if not (len(per) == 1 and key == UNGROUPED):
            detail = f"unit {key!r}: {detail}"
            if len(failed) > 1:
                detail += f" ({len(failed)} of {len(per)} units failed)"
        return FitResult(
            valid=False, error=detail, rejection_reason="numeric",
            optimizer=SPEC_EVALUATE,
        )

    per_group = {key: float(r["score"]) for key, r in per.items()}
    per_group_value = {
        key: _value_from_score(metric, score) for key, score in per_group.items()
    }
    # A spec that returned bare floats has no constants to record, and an empty
    # entry is dropped rather than written as [], so `params_per_group` answers
    # "which units reported constants" truthfully instead of claiming every unit
    # fitted an empty vector.
    params_per_group = {
        key: r["params"] for key, r in per.items() if r.get("params")
    }
    flat_params = (
        next(iter(params_per_group.values()))
        if len(per) == 1 and len(params_per_group) == 1
        else []
    )
    return FitResult(
        valid=True,
        score=sum(per_group.values()) / len(per_group),
        value=sum(per_group_value.values()) / len(per_group_value),
        params=flat_params,
        per_group=per_group,
        per_group_value=per_group_value,
        params_per_group=params_per_group,
        optimizer=SPEC_EVALUATE,
        optimizer_per_group={key: SPEC_EVALUATE for key in per_group},
    )
