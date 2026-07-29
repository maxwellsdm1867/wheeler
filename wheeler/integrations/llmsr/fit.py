"""Fit an equation body's free constants and report the chosen metric.

This is the seam that makes the metric pluggable and extracts the fitted
constants the plan requires on the winning program. Given the full program
(spec preface + a concrete ``equation`` body), it execs the program, reads the
``equation`` callable, and fits ``params`` by minimizing ``metric.loss`` with
scipy BFGS (the same optimizer the upstream spec uses). The input-column calling
convention is derived from the ``equation`` signature (every parameter except the
trailing ``params``), so no per-spec coupling is needed.

``metric.data_shape`` decides how the candidate is called and what the metric is
handed (see ``_bind_inputs``). The optimizer is the same either way: what changes
is whether the prediction has to line up row-for-row with the data.

Fitting is PER GROUP (``evaluate_body_grouped``). A run may declare a column
naming who each row belongs to (a cell, a trial, a subject), and then every group
refits its OWN constants under the SAME form. This matters because symbolic
regression is looking for the functional FORM: if one law governs 40 cells with
40 different constant sets, a single pooled fit charges the FORM for variation
that belongs to the PARAMETERS and rejects a correct law. The result carries the
per-group score VECTOR, which is what reaches the vendored buffer, where
``_reduce_score`` supplies island ranking and ``_get_signature`` clusters forms by
their per-group profile. An ungrouped run is the one-group case and is bit-for-bit
unchanged. See docs/llmsr-objective-formulation.md.

Execution runs in a forked, timeout-bounded child process (reusing the vendored
sandbox's fork context) because the equation body is model-generated code: a
pathological body cannot hang or crash the parent.

The vertical slice uses this at ``best`` time on the single winning body to
extract ``params`` for ``best.json``. It generalizes to per-sample search scoring
for non-MSE metrics (deferred breadth).
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field

import numpy as np

from .metrics import REGRESSION, Metric
from .vendor.evaluator import _MP_CONTEXT

logger = logging.getLogger(__name__)

_DEFAULT_MAX_NPARAMS = 10
_DEFAULT_TIMEOUT = 30
_N_RESTARTS = 6  # extra BFGS starts beyond all-ones, to escape flat/local regions

# The group label for an ungrouped run. Matches the key Wheeler has always passed
# to the vendored buffer, so submissions written before grouping replay unchanged.
UNGROUPED = "data"


@dataclass
class FitResult:
    valid: bool
    score: float | None = None  # maximize-me buffer score (= metric.score_from_value)
    value: float | None = None  # reported metric value
    params: list[float] = field(default_factory=list)
    error: str = ""
    # why an invalid candidate was rejected: "constraint" (a hard constraint said
    # no, whatever it scored) or "numeric" (no finite metric value was produced).
    # Empty on a valid fit. Conflating the two hides a truncated frontier.
    rejection_reason: str = ""
    # Per-group results, keyed by group label. `score`/`value` above are the mean
    # over these. The VECTOR is the primary object: it is what reaches the
    # vendored buffer as `scores_per_test`, where `_reduce_score` supplies island
    # ranking and `_get_signature` clusters forms by their per-group profile.
    # Each group refits its OWN constants, so params_per_group has one entry per
    # group and the flat `params` is meaningful only for an ungrouped run.
    per_group: dict[str, float] = field(default_factory=dict)
    per_group_value: dict[str, float] = field(default_factory=dict)
    params_per_group: dict[str, list[float]] = field(default_factory=dict)


def _first_violation(metric: Metric, y_pred, y_true, params) -> str:
    """Name of the first hard constraint the fitted candidate fails, else ''.

    A constraint that raises counts as failed: an inconclusive check cannot admit
    a candidate.
    """
    for constraint in metric.hard_constraints:
        try:
            holds = constraint.holds(y_pred, y_true, params)
        except Exception as exc:
            logger.warning("constraint %r raised, rejecting: %s", constraint.name, exc)
            return constraint.name
        if not holds:
            return constraint.name
    return ""


def _bind_inputs(metric: Metric, equation, X, y) -> tuple[list, object, str]:
    """Bind the candidate's call arguments and the recorded data, per data shape.

    Returns ``(cols, y_true, error)``; a non-empty ``error`` means the candidate
    cannot be called against this data at all.
    """
    # inputs = every equation arg except the trailing `params`
    n_inputs = len(inspect.signature(equation).parameters) - 1
    if metric.data_shape == REGRESSION:
        # Tabular: every declared input is a column, and the prediction has to
        # line up row-for-row with the target.
        if n_inputs < 1 or n_inputs > X.shape[1]:
            return [], None, f"arity {n_inputs} vs {X.shape[1]} cols"
        cols = [np.asarray(X[:, i], dtype=float) for i in range(n_inputs)]
        return cols, np.asarray(y, dtype=float).reshape(-1), ""
    # The candidate is a SIMULATOR: it returns however many events it returns, so
    # the tabular arity rule does not apply. It gets the stimulus columns it
    # declares (zero is legal, a free-running generator), and the recorded data
    # goes to the metric UNTOUCHED, whatever its length: the metric owns the
    # comparison. A declared input the stimulus cannot supply surfaces as the
    # real TypeError from calling it, not as a tabular rule it never agreed to.
    n_cols = min(max(n_inputs, 0), X.shape[1])
    return [np.asarray(X[:, i], dtype=float) for i in range(n_cols)], y, ""


def _fit_one_group(opt, equation, metric: Metric, X, y, max_nparams) -> dict:
    """Fit this group's OWN constants and score it. One group, one theta.

    Pulled out of ``_worker`` unchanged so that the single-group case stays
    numerically identical: the restart RNG is seeded per group, so group 1 of a
    grouped run draws exactly the inits an ungrouped run drew.
    """
    cols, y_true, bind_error = _bind_inputs(metric, equation, X, y)
    if bind_error:
        return {"valid": False, "error": bind_error, "rejection_reason": "numeric"}

    with np.errstate(all="ignore"):
        def loss(p):
            y_pred = equation(*cols, np.asarray(p, dtype=float))
            return metric.loss(y_pred, y_true)

        # Multi-start BFGS: a single all-ones init leaves forms whose constants
        # live far from 1 (a temperature optimum, a saturation constant) stuck in
        # a flat region and mis-scored, so the search would reject a CORRECT form.
        # Deterministic restarts (fixed seed) keep the fit reproducible.
        restart_rng = np.random.default_rng(0)
        inits = [np.ones(max_nparams)]
        inits += [
            restart_rng.uniform(-12.0, 12.0, max_nparams) for _ in range(_N_RESTARTS)
        ]
        best = None
        for x0 in inits:
            try:
                res = opt.minimize(loss, x0, method="BFGS")
            except Exception:
                continue
            if np.isfinite(res.fun) and (best is None or res.fun < best.fun):
                best = res
        if best is None:
            return {
                "valid": False,
                "error": "no successful fit from any start",
                "rejection_reason": "numeric",
            }
        params = np.asarray(best.x, dtype=float)
        y_pred = equation(*cols, params)
        value = float(metric.report(y_pred, y_true))
        violated = _first_violation(metric, y_pred, y_true, params) if np.isfinite(value) else ""

    if not np.isfinite(value):
        return {
            "valid": False,
            "error": "non-finite metric value",
            "rejection_reason": "numeric",
        }
    if violated:
        # Keep the value and the constants: a candidate the guard rejected
        # often scored WELL, and hiding that hides why it was thrown out.
        return {
            "valid": False,
            "rejection_reason": "constraint",
            "error": f"rejected by hard constraint {violated!r}",
            "value": value,
            "params": params.tolist(),
        }
    return {
        "valid": True,
        "value": value,
        "score": metric.score_from_value(value),
        "params": params.tolist(),
    }


def _worker(program_str, function_to_evolve, groups, metric: Metric, max_nparams, q):
    """Fit one candidate FORM against every group, each with its own constants.

    ``groups`` is a list of ``(label, X, y)``. The form is shared; theta is not.
    Compiling the program is done once, then each group refits independently.
    """
    try:
        import scipy.optimize as opt  # local: only needed in the child

        # `np` is pre-bound because a candidate body is written against the numpy
        # calling convention but need not carry its own import; a spec preface
        # that imports numpy rebinds the same module.
        namespace: dict = {"np": np}
        exec(program_str, namespace)  # noqa: S102 - sandboxed, model-generated body
        equation = namespace.get(function_to_evolve)
        if not callable(equation):
            q.put({"error": f"no callable {function_to_evolve!r}"})
            return

        q.put({
            "groups": {
                label: _fit_one_group(opt, equation, metric, gX, gy, max_nparams)
                for label, gX, gy in groups
            }
        })
    except Exception as exc:  # any failure in untrusted body -> invalid, never raise
        q.put({"error": f"{type(exc).__name__}: {exc}"})


def evaluate_fixed(
    program_str: str,
    function_to_evolve: str,
    X: np.ndarray,
    y: np.ndarray,
    params: list[float],
    metric: Metric,
) -> float | None:
    """Apply an equation with FIXED (already-fitted) params and report the metric.

    No fitting: used to score a train-fitted equation on held-out ID/OOD test
    sets (the paper's generalization protocol). In-process (the winner already
    passed the sandbox); defensive, returns None on any failure.
    """
    try:
        namespace: dict = {"np": np}
        exec(program_str, namespace)  # noqa: S102 - already-validated winner
        equation = namespace.get(function_to_evolve)
        if not callable(equation):
            return None
        cols, y_true, bind_error = _bind_inputs(metric, equation, X, y)
        if bind_error:
            return None
        with np.errstate(all="ignore"):
            y_pred = equation(*cols, np.asarray(params, dtype=float))
            value = float(metric.report(y_pred, y_true))
        return value if np.isfinite(value) else None
    except Exception:
        return None


def evaluate_body(
    program_str: str,
    function_to_evolve: str,
    X: np.ndarray,
    y: np.ndarray,
    metric: Metric,
    *,
    max_nparams: int = _DEFAULT_MAX_NPARAMS,
    timeout_seconds: int = _DEFAULT_TIMEOUT,
) -> FitResult:
    """Fit ``program_str``'s constants under ``metric``; never raises.

    Returns a ``FitResult``: ``valid`` false on compile error, wrong arity,
    non-finite result, or timeout (``rejection_reason`` ``numeric``), and also
    when a hard constraint rejected the fitted candidate (``constraint``).
    """
    result = evaluate_body_grouped(
        program_str,
        function_to_evolve,
        [(UNGROUPED, X, y)],
        metric,
        max_nparams=max_nparams,
        timeout_seconds=timeout_seconds,
    )
    # One group, so the aggregate IS that group and `params` is already flat.
    # sum([v]) / 1 is exact in IEEE, so this stays bit-for-bit identical to the
    # pre-grouping implementation.
    return result


def evaluate_body_grouped(
    program_str: str,
    function_to_evolve: str,
    groups: list[tuple[str, np.ndarray, object]],
    metric: Metric,
    *,
    max_nparams: int = _DEFAULT_MAX_NPARAMS,
    timeout_seconds: int = _DEFAULT_TIMEOUT,
) -> FitResult:
    """Fit one FORM against every group, each refitting its own constants.

    This is the per-group protocol: the equation body is shared across groups,
    theta is not. A form that governs 40 cells with 40 different constant sets
    scores well here, where a single pooled fit would charge the FORM for a
    mismatch that belongs to the PARAMETERS.

    Validity is STRICT: a candidate is valid only if EVERY group fitted and
    passed its constraints. Two reasons, one practical and one structural. The
    practical one is that this reproduces the ungrouped semantics exactly. The
    structural one is that the vendored island model keys its clusters on the
    score signature, so every candidate must be scored on the SAME group set or
    the signatures are not comparable. A per-group failure policy (accept a form
    that fails k of n groups) is a scientific call and is deferred; see
    docs/llmsr-objective-formulation.md.

    The timeout scales with the group count: it bounds one fit, and there are
    now ``len(groups)`` of them behind one fork.
    """
    queue = _MP_CONTEXT.Queue()
    proc = _MP_CONTEXT.Process(
        target=_worker,
        args=(program_str, function_to_evolve, groups, metric, max_nparams, queue),
    )
    proc.start()
    proc.join(timeout=timeout_seconds * max(1, len(groups)))
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return FitResult(
            valid=False,
            error=f"timeout after {timeout_seconds * max(1, len(groups))}s",
            rejection_reason="numeric",
        )

    if queue.empty():
        return FitResult(
            valid=False, error="worker produced no result", rejection_reason="numeric"
        )
    out = queue.get_nowait()
    if "groups" not in out:  # compile error or no such callable: applies to every group
        return FitResult(
            valid=False,
            error=out.get("error", "invalid"),
            rejection_reason="numeric",
        )

    per = out["groups"]
    failed = [(label, r) for label, r in per.items() if not r.get("valid")]
    if failed:
        label, first = sorted(failed, key=lambda kv: kv[0])[0]
        detail = first.get("error", "invalid")
        # Name the group only when there IS one. An ungrouped run has no group to
        # blame, and prefixing its sole pseudo-group would change every existing
        # error message for no gain.
        if not (len(per) == 1 and label == UNGROUPED):
            detail = f"group {label!r}: {detail}"
            if len(failed) > 1:
                detail += f" ({len(failed)} of {len(per)} groups failed)"
        return FitResult(
            valid=False,
            error=detail,
            rejection_reason=first.get("rejection_reason", "numeric"),
            value=first.get("value"),
            params=first.get("params", []),
            per_group_value={
                label: r["value"] for label, r in per.items() if r.get("value") is not None
            },
        )

    per_group = {label: r["score"] for label, r in per.items()}
    per_group_value = {label: r["value"] for label, r in per.items()}
    params_per_group = {label: r["params"] for label, r in per.items()}
    # With a single group there IS one parameter vector, so publish it flat: every
    # existing caller (best.json, OOD scoring via evaluate_fixed) reads `params`,
    # and an ungrouped run must keep behaving exactly as it did.
    flat_params = next(iter(params_per_group.values())) if len(params_per_group) == 1 else []
    return FitResult(
        valid=True,
        # The scalar is the mean over groups, matching the vendored
        # `_reduce_score`, and is what selection and reporting use. The VECTOR is
        # the primary object and is what reaches the buffer.
        score=sum(per_group.values()) / len(per_group),
        value=sum(per_group_value.values()) / len(per_group_value),
        params=flat_params,
        per_group=per_group,
        per_group_value=per_group_value,
        params_per_group=params_per_group,
    )
