"""Fit an equation body's free constants and report the chosen metric.

This is the seam that makes the metric pluggable and extracts the fitted
constants the plan requires on the winning program. Given the full program
(spec preface + a concrete ``equation`` body), it execs the program, reads the
``equation`` callable, and fits ``params`` by minimizing ``metric.loss`` with
scipy BFGS (the same optimizer the upstream spec uses). The input-column calling
convention is derived from the ``equation`` signature (every parameter except the
trailing ``params``), so no per-spec coupling is needed.

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

from .metrics import Metric
from .vendor.evaluator import _MP_CONTEXT

logger = logging.getLogger(__name__)

_DEFAULT_MAX_NPARAMS = 10
_DEFAULT_TIMEOUT = 30
_N_RESTARTS = 6  # extra BFGS starts beyond all-ones, to escape flat/local regions


@dataclass
class FitResult:
    valid: bool
    score: float | None = None  # maximize-me buffer score (= metric.score_from_value)
    value: float | None = None  # reported metric value
    params: list[float] = field(default_factory=list)
    error: str = ""


def _worker(program_str, function_to_evolve, X, y, metric: Metric, max_nparams, q):
    try:
        import scipy.optimize as opt  # local: only needed in the child

        namespace: dict = {}
        exec(program_str, namespace)  # noqa: S102 - sandboxed, model-generated body
        equation = namespace.get(function_to_evolve)
        if not callable(equation):
            q.put({"valid": False, "error": f"no callable {function_to_evolve!r}"})
            return

        # input columns = every equation arg except the trailing `params`
        n_inputs = len(inspect.signature(equation).parameters) - 1
        if n_inputs < 1 or n_inputs > X.shape[1]:
            q.put({"valid": False, "error": f"arity {n_inputs} vs {X.shape[1]} cols"})
            return
        cols = [np.asarray(X[:, i], dtype=float) for i in range(n_inputs)]
        y_true = np.asarray(y, dtype=float).reshape(-1)

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
                q.put({"valid": False, "error": "no successful fit from any start"})
                return
            params = np.asarray(best.x, dtype=float)
            y_pred = equation(*cols, params)
            value = float(metric.report(y_pred, y_true))

        if not np.isfinite(value):
            q.put({"valid": False, "error": "non-finite metric value"})
            return
        q.put({
            "valid": True,
            "value": value,
            "score": metric.score_from_value(value),
            "params": params.tolist(),
        })
    except Exception as exc:  # any failure in untrusted body -> invalid, never raise
        q.put({"valid": False, "error": f"{type(exc).__name__}: {exc}"})


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
        namespace: dict = {}
        exec(program_str, namespace)  # noqa: S102 - already-validated winner
        equation = namespace.get(function_to_evolve)
        if not callable(equation):
            return None
        n_inputs = len(inspect.signature(equation).parameters) - 1
        if n_inputs < 1 or n_inputs > X.shape[1]:
            return None
        cols = [np.asarray(X[:, i], dtype=float) for i in range(n_inputs)]
        y_true = np.asarray(y, dtype=float).reshape(-1)
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
    non-finite result, or timeout.
    """
    queue = _MP_CONTEXT.Queue()
    proc = _MP_CONTEXT.Process(
        target=_worker,
        args=(program_str, function_to_evolve, X, y, metric, max_nparams, queue),
    )
    proc.start()
    proc.join(timeout=timeout_seconds)
    if proc.is_alive():
        proc.terminate()
        proc.join()
        return FitResult(valid=False, error=f"timeout after {timeout_seconds}s")

    if queue.empty():
        return FitResult(valid=False, error="worker produced no result")
    out = queue.get_nowait()
    if not out.get("valid"):
        return FitResult(valid=False, error=out.get("error", "invalid"))
    return FitResult(
        valid=True,
        score=out["score"],
        value=out["value"],
        params=out["params"],
    )
