"""Fit an equation body's free constants and report the chosen metric.

This is the seam that makes the metric pluggable and extracts the fitted
constants the plan requires on the winning program. Given the full program
(spec preface + a concrete ``equation`` body), it execs the program, reads the
``equation`` callable, and fits ``params`` by minimizing ``metric.loss`` from
several starts. The input-column calling convention is derived from the
``equation`` signature (every parameter except the trailing ``params``), so no
per-spec coupling is needed.

WHICH optimizer runs is declarable (``optimizers.py``) and defaults to ``auto``:
BFGS from every start, escalating to Nelder-Mead FROM THE SAME STARTS when no
start moved off its init. That signature means the optimizer could not see the
objective at all (BFGS's numerical gradient is identically zero on a
piecewise-constant loss), and it matters here more than anywhere: under
``--group-by`` one failed group invalidates the whole candidate, so an optimizer
blind to a single cell rejects a CORRECT form. This is a deliberate behaviour
change from the BFGS-only fit. Where BFGS moved, every number is bit-for-bit what
it was; where BFGS did not move, the result changes, for the better. The concrete
optimizer behind the winning constants is recorded on the ``FitResult`` and
surfaced in ``best.json``, because a number whose provenance is a silent fallback
is exactly what this project exists to prevent.

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

Execution runs in a forked, timeout-bounded child process (``_run_sandboxed``,
reusing the vendored sandbox's fork context) because the equation body is
model-generated code: a pathological body cannot hang or crash the parent.

This is the DEFAULT scoring door, not the only one. A run created with
``--use-spec-evaluate`` scores through the spec's own ``@evaluate.run`` instead
(``spec_eval.py``), which is what upstream does; it shares ``_run_sandboxed`` and
returns the same ``FitResult``, so nothing downstream branches on which door ran.

The vertical slice uses this at ``best`` time on the single winning body to
extract ``params`` for ``best.json``. It generalizes to per-sample search scoring
for non-MSE metrics (deferred breadth).
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .metrics import REGRESSION, Metric
from .optimizers import AUTO, Optimizer, resolve
from .vendor.evaluator import _MP_CONTEXT

logger = logging.getLogger(__name__)

_DEFAULT_MAX_NPARAMS = 10
_DEFAULT_TIMEOUT = 30

# Extra starts beyond all-ones, to escape flat/local regions, and the seed that
# draws them. Public and reachable (``wheeler llmsr init --restarts/--seed``): a
# constant nobody can change is a constant nobody can rule out. The values are
# the ones the fit has always used, so a run that names neither replays exactly.
DEFAULT_RESTARTS = 6
DEFAULT_SEED = 0

# The group label for an ungrouped run. Matches the key Wheeler has always passed
# to the vendored buffer, so submissions written before grouping replay unchanged.
UNGROUPED = "data"

# What ``FitResult.optimizer`` says when a grouped fit escalated for some groups
# and not others. Escalation is decided per group because it is a property of
# THAT group's objective; claiming one name for a candidate whose groups disagree
# would be a claim the fit never made. ``optimizer_per_group`` always resolves it.
MIXED = "mixed"


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
    # The CONCRETE optimizer that produced the reported constants, never the
    # strategy that chose it: `auto` reports `bfgs` or `nelder-mead`, so the
    # winner says which optimizer is behind its numbers. `MIXED` when a grouped
    # fit escalated for some groups only. Empty when nothing was fitted.
    optimizer: str = ""
    optimizer_per_group: dict[str, str] = field(default_factory=dict)


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


def _run_starts(minimize, loss, inits) -> tuple[tuple | None, bool]:
    """Run ONE optimizer from every start. Returns ``(best, moved)``.

    ``best`` is the ``(x, fun)`` with the lowest finite objective, selected
    exactly as the single-optimizer loop always selected it: strict ``<``, so the
    FIRST start to reach a value keeps it. A start whose optimizer raises or
    returns ``None`` is skipped, which is what ``except Exception: continue`` did.
    ``None`` when no start produced a finite objective.

    ``moved`` is False when NOT ONE usable start ended anywhere other than where
    it began. That is the fingerprint of an optimizer that cannot see this
    objective at all, and it is what ``_fit_one_group`` escalates on. It is
    measured rather than predicted from the data shape, so it catches any
    non-smooth objective and not merely the ones we anticipated. Only starts that
    produced a finite objective are asked whether they moved: a start that came
    back NaN did not explore anywhere, it failed, and counting it as movement
    would suppress the escalation exactly where it is most needed.
    """
    best = None
    moved = False
    for x0 in inits:
        try:
            out = minimize(loss, x0)
        except Exception:
            continue
        if out is None:
            continue
        x, fun = out
        if np.isfinite(fun):
            if not np.allclose(x, x0):
                moved = True
            if best is None or fun < best[1]:
                best = (x, fun)
    return best, moved


def _fit_one_group(
    equation,
    metric: Metric,
    X,
    y,
    max_nparams,
    primary: Optimizer,
    escalation: Optimizer | None = None,
    restarts: int = DEFAULT_RESTARTS,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Fit this group's OWN constants and score it. One group, one theta.

    Pulled out of ``_worker`` so that the single-group case stays numerically
    identical: the restart RNG is seeded per group, so group 1 of a grouped run
    draws exactly the inits an ungrouped run drew.

    The escalation decision is per group, and deliberately so: whether an
    optimizer can see the objective is a property of THIS group's data, and under
    strict validity one blind group throws away the whole candidate.
    """
    cols, y_true, bind_error = _bind_inputs(metric, equation, X, y)
    if bind_error:
        return {"valid": False, "error": bind_error, "rejection_reason": "numeric"}

    with np.errstate(all="ignore"):
        def loss(p):
            y_pred = equation(*cols, np.asarray(p, dtype=float))
            return metric.loss(y_pred, y_true)

        # Multi-start: a single all-ones init leaves forms whose constants live
        # far from 1 (a temperature optimum, a saturation constant) stuck in a
        # flat region and mis-scored, so the search would reject a CORRECT form.
        # Deterministic restarts (fixed seed) keep the fit reproducible.
        restart_rng = np.random.default_rng(seed)
        inits = [np.ones(max_nparams)]
        inits += [
            restart_rng.uniform(-12.0, 12.0, max_nparams) for _ in range(restarts)
        ]
        best, moved = _run_starts(primary.minimize, loss, inits)
        used = primary.key
        if escalation is not None and not moved:
            # Nothing moved, so the primary optimizer never saw a slope: its
            # "best" is just whichever init sat lowest, and a correct form would
            # be rejected on that alone. Rerun from the SAME starts, and keep the
            # escalated answer only if it actually improved on that init.
            alt, _alt_moved = _run_starts(escalation.minimize, loss, inits)
            if alt is not None and (best is None or alt[1] < best[1]):
                best, used = alt, escalation.key
        if best is None:
            return {
                "valid": False,
                "error": "no successful fit from any start",
                "rejection_reason": "numeric",
            }
        params = np.asarray(best[0], dtype=float)
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
            "optimizer": used,
        }
    return {
        "valid": True,
        "value": value,
        "score": metric.score_from_value(value),
        "params": params.tolist(),
        "optimizer": used,
    }


def _emit_progress(
    progress_path: str | Path | None,
    dataset: str | None,
    group: str | None,
    done: int,
    total: int,
) -> None:
    """Write one during-the-fit ping so a long run can be asked where it is.

    Telemetry, never numerics. Every failure is swallowed, because the fit is the
    product and progress is only the commentary: a full disk or a run dir deleted
    under us must not invalidate a candidate. Nothing here touches the queue
    protocol or what ``_fit_one_group`` returns, and the per-group calls happen
    OUTSIDE the ``np.errstate`` block, so the numerics cannot see it either.

    ``dataset`` and ``group`` together name the unit in flight, so a run scoring
    one form against several tables can be asked WHICH table it is on, not just
    which group. Both are ``None`` on the ping written before the fork, which is
    the honest reading of it: a fit has started and no unit has begun.

    A ``progress_path`` of ``None`` makes this a no-op, which is the parity
    property: a caller that passes no path behaves exactly as it did before this
    channel existed.
    """
    if progress_path is None:
        return
    try:
        # Local import: `runs` imports `fit`, so the dependency only runs one way
        # at module level. Same lazy-to-break-a-cycle pattern as elsewhere.
        from .runs import _write_json_atomic

        _write_json_atomic(Path(progress_path), {
            "phase": "fit",
            "dataset": dataset,
            "group": group,
            "done": done,
            "total": total,
            "at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass


def _run_sandboxed(target, args: tuple, timeout_seconds: int) -> dict:
    """Run ``target(*args, queue)`` in a forked child and return its one payload.

    The ONE sandbox both scoring doors share (this fit, and ``spec_eval.py``
    calling the spec's own ``@evaluate.run``). Untrusted code runs in a child
    process under a wall-clock bound, so a pathological body cannot hang or crash
    the parent, and the child's single queued dict is the whole result.

    Never raises: a timeout or a child that died without queuing anything comes
    back as ``{"error": ...}``, which is exactly what both callers turn into an
    invalid candidate. The two messages are the ones this path has always
    produced, because they reach ``best.json`` and ``submissions.jsonl``.
    """
    queue = _MP_CONTEXT.Queue()
    proc = _MP_CONTEXT.Process(target=target, args=(*args, queue))
    proc.start()
    proc.join(timeout=timeout_seconds)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return {"error": f"timeout after {timeout_seconds}s"}
    if queue.empty():
        return {"error": "worker produced no result"}
    return queue.get_nowait()


def _worker(program_str, function_to_evolve, groups, metric: Metric, max_nparams,
            progress_path, primary, escalation, restarts, seed, dataset_of, q):
    """Fit one candidate FORM against every group, each with its own constants.

    ``groups`` is a list of ``(label, X, y)``. The form is shared; theta is not.
    Compiling the program is done once, then each group refits independently.

    ``dataset_of`` maps a label to the dataset it came from, for the progress
    ping alone. Absent, every label reports ``UNGROUPED``, which is both what this
    channel has always said and, for a run with one default-named dataset, true.

    Runs in the forked child, which is also where the per-group progress pings
    are written: the parent is blocked in ``proc.join`` and so cannot report
    anything until the whole candidate is done.
    """
    try:
        # Local, and deliberately here rather than inside the optimizer: an
        # ImportError raised per start would be swallowed by the skip-this-start
        # rule and reported as "no successful fit from any start". A missing extra
        # has to name itself.
        import scipy.optimize  # noqa: F401

        # `np` is pre-bound because a candidate body is written against the numpy
        # calling convention but need not carry its own import; a spec preface
        # that imports numpy rebinds the same module.
        namespace: dict = {"np": np}
        exec(program_str, namespace)  # noqa: S102 - sandboxed, model-generated body
        equation = namespace.get(function_to_evolve)
        if not callable(equation):
            q.put({"error": f"no callable {function_to_evolve!r}"})
            return

        # An explicit loop rather than a dict comprehension so a group can be
        # counted as it lands. Iteration order and the resulting dict are
        # identical to the comprehension this replaced.
        total = len(groups)
        fitted: dict[str, dict] = {}
        for done, (label, gX, gy) in enumerate(groups, start=1):
            fitted[label] = _fit_one_group(
                equation, metric, gX, gy, max_nparams,
                primary, escalation, restarts, seed,
            )
            _emit_progress(
                progress_path, (dataset_of or {}).get(label, UNGROUPED),
                label, done, total,
            )
        q.put({"groups": fitted})
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
    sets. That generalization step is WHEELER'S addition, not upstream's: LLM-SR
    ships the test splits with its datasets, but its own ``main.py`` loads only
    ``train.csv`` and never scores against them. In-process (the winner already
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
    optimizer: str = AUTO,
    restarts: int = DEFAULT_RESTARTS,
    seed: int = DEFAULT_SEED,
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
        optimizer=optimizer,
        restarts=restarts,
        seed=seed,
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
    progress_path: str | Path | None = None,
    optimizer: str = AUTO,
    restarts: int = DEFAULT_RESTARTS,
    seed: int = DEFAULT_SEED,
    dataset_of: dict[str, str] | None = None,
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

    ``progress_path``, when given, names a file this refreshes as each group
    lands, so a submit that refits forty groups can be asked where it is instead
    of being silent for minutes. It is pure telemetry: passing ``None`` (the
    default) leaves every byte of the result and every number in it unchanged.

    ``optimizer`` names a declared choice (``optimizers.resolve``), ``restarts``
    and ``seed`` control the multi-start inits. The defaults are what the fit has
    always used, except that ``auto`` will escalate off a flat gradient where
    plain BFGS could only report the init it never left.

    ``dataset_of`` labels each group with the dataset it came from, which a run
    scoring several tables needs so the progress ping can say WHICH table is
    under the needle. It is telemetry only: nothing in the fit reads it.
    """
    try:
        primary, escalation = resolve(optimizer)
    except KeyError as exc:
        # A configuration error, not a bad candidate. Reported rather than raised,
        # because this function's contract is that it never raises, and named
        # loudly on every candidate rather than quietly turning a whole search
        # invalid.
        return FitResult(
            valid=False, error=str(exc).strip("'"), rejection_reason="numeric"
        )
    # Ping before forking, so that a fit which wedges on its FIRST group is still
    # visibly a fit in flight rather than an idle run. Done in the parent because
    # by definition the child has not started yet.
    _emit_progress(progress_path, None, None, 0, len(groups))
    out = _run_sandboxed(
        _worker,
        (program_str, function_to_evolve, groups, metric, max_nparams,
         progress_path, primary, escalation, restarts, seed, dataset_of),
        timeout_seconds * max(1, len(groups)),
    )
    # A timeout or a silent child lands here too: neither produced groups, and
    # both are the same thing to a candidate, an invalid one with a named reason.
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
            optimizer=first.get("optimizer", ""),
            optimizer_per_group={
                label: r["optimizer"] for label, r in per.items() if r.get("optimizer")
            },
        )

    per_group = {label: r["score"] for label, r in per.items()}
    per_group_value = {label: r["value"] for label, r in per.items()}
    params_per_group = {label: r["params"] for label, r in per.items()}
    optimizer_per_group = {label: r["optimizer"] for label, r in per.items()}
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
        optimizer=_common_optimizer(optimizer_per_group),
        optimizer_per_group=optimizer_per_group,
    )


def _common_optimizer(per_group: dict[str, str]) -> str:
    """The one optimizer behind every group, or ``MIXED`` when they disagree."""
    names = set(per_group.values())
    if not names:
        return ""
    return next(iter(names)) if len(names) == 1 else MIXED
