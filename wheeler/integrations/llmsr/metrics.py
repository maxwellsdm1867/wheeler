"""Pluggable scoring metrics for LLM-SR equation discovery.

The metric is chosen once per run (``wheeler llmsr init --metric``), bound into
the run, and used both to FIT the free constants (minimize ``loss``) and to REPORT
the result (``report``). The scientist picks it in the act; nothing is defaulted
silently.

``mse`` and ``nmse`` ship built in. Any other objective is the scientist's own and
does NOT require editing the installed package: write a ``Metric`` in your own
module, call ``register_metric`` on it, and point Wheeler at that module through
``$WHEELER_LLMSR_METRICS`` or by putting it at ``.wheeler/llmsr/metrics.py`` in
the project. ``load_user_metrics()`` imports those sources before the CLI resolves
a metric name, so an upgrade never drops the objective::

    # .wheeler/llmsr/metrics.py
    import numpy as np
    from wheeler.integrations.llmsr.metrics import Metric, register_metric

    def huber(y_pred, y_true, delta=1.0):
        r = np.abs(np.asarray(y_pred).reshape(-1) - np.asarray(y_true).reshape(-1))
        return float(np.mean(np.where(r <= delta, 0.5 * r**2, delta * (r - 0.5 * delta))))

    register_metric(Metric(
        key="huber", label="Huber loss", data_shape="regression",
        lower_is_better=True, loss=huber, report=huber,
    ))

A metric also declares the DATA SHAPE it expects, and the fit path dispatches on
it. ``regression`` is the tabular case: one column of ``X`` per input, and the
prediction lines up row-for-row with ``y``. ``spike_train`` is the simulator
case: the candidate returns a variable-length sequence of event times, scored
against a recorded sequence of a different length, so nothing lines up row-wise
and the metric owns the comparison (a Victor-Purpura distance, for instance).
An unsupported shape is rejected when the metric is declared, not at scoring time.

A metric may also declare HARD CONSTRAINTS through ``guard``: accept/reject checks
evaluated per candidate, separately from the scalar loss, so a candidate that
violates one is rejected whatever it scored (see ``Constraint``).
"""

from __future__ import annotations

import logging
from dataclasses import InitVar, dataclass, field
from typing import Any, Callable

import numpy as np

from . import _userland

logger = logging.getLogger(__name__)

Scorer = Callable[[Any, Any], float]

REGRESSION = "regression"  # tabular (X, y): prediction lines up row-for-row
SPIKE_TRAIN = "spike_train"  # simulator: variable-length event times vs recorded
DATA_SHAPES = (REGRESSION, SPIKE_TRAIN)


@dataclass(frozen=True)
class Constraint:
    """A hard accept/reject check on a fitted candidate.

    ``check(y_pred, y_true, params) -> bool``, where True means admissible. This
    is NOT a weighted penalty in the loss: a candidate that fails a constraint is
    rejected whatever it scored, so it cannot buy a large gain on the primary
    objective by paying a small penalty on a secondary one.
    """

    name: str
    check: Callable[[Any, Any, np.ndarray], bool]

    def holds(self, y_pred: Any, y_true: Any, params: np.ndarray) -> bool:
        return bool(self.check(y_pred, y_true, params))


def _as_constraints(guard: Any, key: str) -> tuple[Constraint, ...]:
    """Normalize a declared guard into constraints. One callable, or several."""
    if guard is None:
        return ()
    items = list(guard) if isinstance(guard, (list, tuple)) else [guard]
    out: list[Constraint] = []
    for i, item in enumerate(items):
        if isinstance(item, Constraint):
            out.append(item)
        elif callable(item):
            out.append(
                Constraint(name=getattr(item, "__name__", "") or f"constraint_{i}", check=item)
            )
        else:
            raise TypeError(
                f"metric {key!r}: guard entry {item!r} is neither a Constraint nor "
                "a callable taking (y_pred, y_true, params)"
            )
    return tuple(out)


@dataclass(frozen=True)
class Metric:
    """A named scoring metric.

    ``loss`` is minimized during the constant fit (lower is a better fit).
    ``report`` is the human-facing value stored on the Finding. For MSE the two
    coincide; for a metric like R2 they differ (fit may minimize ``-R2`` while the
    report is ``R2``). ``lower_is_better`` lets the driver turn ``report`` into a
    buffer score where higher is always better (the island model maximizes).

    ``data_shape`` is one of ``DATA_SHAPES``. It decides how the fit path calls
    the candidate and what it hands the metric, so an unknown shape is a hard
    error here rather than a silent no-op at scoring time.

    ``guard`` declares hard constraints: one ``Constraint`` or callable, or a
    sequence of them. They are normalized into ``hard_constraints`` and evaluated
    per candidate AFTER the fit, separately from the scalar loss.
    """

    key: str
    label: str
    data_shape: str
    lower_is_better: bool
    loss: Scorer
    report: Scorer
    guard: InitVar[Any] = None
    hard_constraints: tuple[Constraint, ...] = field(init=False, default=())

    def __post_init__(self, guard: Any) -> None:
        if self.data_shape not in DATA_SHAPES:
            raise ValueError(
                f"metric {self.key!r} declares data_shape {self.data_shape!r}, "
                f"which the fit path cannot dispatch; supported: {list(DATA_SHAPES)}"
            )
        object.__setattr__(self, "hard_constraints", _as_constraints(guard, self.key))

    def score_from_value(self, value: float) -> float:
        """Convert a reported value into a maximize-me buffer score."""
        return -value if self.lower_is_better else value


# ``guard`` is consumed by __post_init__, so no instance ever stores it. Dropping
# the class-level default the dataclass leaves behind keeps that honest: reading
# ``metric.guard`` raises instead of answering None for a metric that does carry
# constraints. ``metric.hard_constraints`` is the one place they live.
delattr(Metric, "guard")


def _as_arrays(y_pred, y_true) -> tuple[np.ndarray, np.ndarray]:
    yp = np.asarray(y_pred, dtype=float).reshape(-1)
    yt = np.asarray(y_true, dtype=float).reshape(-1)
    return yp, yt


def _mse(y_pred, y_true) -> float:
    yp, yt = _as_arrays(y_pred, y_true)
    diff = yp - yt
    return float(np.mean(diff * diff))


def _nmse(y_pred, y_true) -> float:
    """MSE normalized by the variance of the targets: the LLM-SR paper's metric.

    NMSE = mean((y - yhat)^2) / mean((y - mean(y))^2). A perfect fit -> 0, the
    mean predictor -> 1. Minimizing NMSE is equivalent to minimizing MSE (the
    denominator is constant in the params), so it drives the same fit.
    """
    yp, yt = _as_arrays(y_pred, y_true)
    denom = float(np.mean((yt - yt.mean()) ** 2))
    mse = float(np.mean((yp - yt) ** 2))
    if denom == 0.0:  # constant targets: fall back to raw MSE
        return mse
    return mse / denom


MSE = Metric(
    key="mse",
    label="mean squared error",
    data_shape="regression",
    lower_is_better=True,
    loss=_mse,
    report=_mse,
)

NMSE = Metric(
    key="nmse",
    label="normalized mean squared error",
    data_shape="regression",
    lower_is_better=True,
    loss=_nmse,
    report=_nmse,
)


# The two metrics Wheeler ships. Never mutated: it is what `builtin` reports
# against, so a scientist can always tell their own objective from ours.
BUILTIN_METRICS: dict[str, Metric] = {MSE.key: MSE, NMSE.key: NMSE}

# The live registry: the built-ins plus whatever `register_metric` has added.
METRICS: dict[str, Metric] = dict(BUILTIN_METRICS)

_REQUIRED_ATTRS = ("key", "label", "data_shape", "lower_is_better", "loss", "report")

# The user-module convention lives in `_userland`, shared with the other open
# registries. These are the metric-flavoured names for it, kept because they are
# what callers and tests already say. `_loaded_sources` is an ALIAS for the one
# process-wide set: mutate it in place, never rebind it.
_KIND = "metrics"
_USER_METRICS_ENV = _userland.env_var(_KIND)
_PROJECT_METRICS_FILE = _userland.project_file(_KIND)
MetricSourceError = _userland.SourceError
_loaded_sources = _userland._loaded_sources


def _normalize_key(key: object) -> str:
    return key.strip().lower() if isinstance(key, str) else ""


def register_metric(metric: Metric, *, replace: bool = False) -> Metric:
    """Register a scientist-supplied metric under its key and return it.

    Everything the fit path will touch is checked HERE, naming what is missing,
    so a half-built metric fails at declaration rather than as an AttributeError
    inside a fit worker an hour into a search.
    """
    missing = [attr for attr in _REQUIRED_ATTRS if not hasattr(metric, attr)]
    if missing:
        raise TypeError(
            f"invalid metric ({type(metric).__name__}): missing required "
            f"attribute(s) {', '.join(missing)}. A metric must declare "
            f"{', '.join(_REQUIRED_ATTRS)}."
        )
    key = _normalize_key(getattr(metric, "key", None))
    if not key:
        raise ValueError("invalid metric: 'key' must be a non-empty string")
    if not isinstance(metric, Metric):
        raise TypeError(
            f"invalid metric {key!r}: build it with "
            "wheeler.integrations.llmsr.metrics.Metric, which validates the "
            "declared data shape and derives the selection score"
        )
    for attr in ("loss", "report"):
        if not callable(getattr(metric, attr)):
            raise TypeError(f"invalid metric {key!r}: '{attr}' must be callable")
    if not isinstance(metric.lower_is_better, bool):
        raise TypeError(f"invalid metric {key!r}: 'lower_is_better' must be a bool")
    if key in METRICS and not replace:
        origin = "built in" if key in BUILTIN_METRICS else "already registered"
        raise ValueError(
            f"metric {key!r} is {origin}; pass replace=True to override it"
        )
    METRICS[key] = metric
    logger.debug("registered metric %r (%s)", key, metric.label)
    return metric


def user_metric_sources() -> list[str]:
    """Where to look for the scientist's metric modules, in order."""
    return _userland.sources(_KIND)


def load_user_metrics() -> list[MetricSourceError]:
    """Import the scientist's metric modules so their registrations take effect.

    Sources, in order: every entry of ``$WHEELER_LLMSR_METRICS`` (separated by
    the path separator or by commas, each either an importable module path or a
    path to a .py file), then ``.wheeler/llmsr/metrics.py`` under the project.
    Each source is imported at most once per process. A source that raises is
    REPORTED, not raised: one broken file must not take down every verb.
    """
    return _userland.load(_KIND)


def get_metric(key: str) -> Metric:
    """Return the registered metric for ``key`` or raise with the available list."""
    normalized = _normalize_key(key)
    if normalized not in METRICS:
        raise KeyError(
            f"unknown metric {key!r}; registered metrics: {sorted(METRICS)}. "
            f"Register your own with metrics.register_metric() from a module "
            f"named in ${_USER_METRICS_ENV} or from {_PROJECT_METRICS_FILE}."
        )
    return METRICS[normalized]


def available() -> list[str]:
    """Return the sorted keys of registered metrics (what the act may offer).

    Imports the scientist's metric modules FIRST, because this is the callable
    the `llmsr-discover` contract points its `metric` port at via `options_from`.
    A listing that reported only the built-ins would leave a registered metric
    unofferable by the interview, which is the exact invisibility the registry
    exists to remove.

    A failed source is swallowed here, not raised: `load_user_metrics()` is the
    call that REPORTS failures, and one broken file must not take down the whole
    interview.
    """
    try:
        load_user_metrics()
    except Exception:  # a listing must never raise
        logger.debug("could not load user metrics while listing", exc_info=True)
    return sorted(METRICS)
