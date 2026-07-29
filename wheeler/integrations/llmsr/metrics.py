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

A metric also declares the data shape it expects (``regression`` for tabular
``(X, y)``); spike-train metrics such as Victor-Purpura will declare
``spike_train`` and carry their own loader, which is deferred breadth (see the
package plan).
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)

Scorer = Callable[[np.ndarray, np.ndarray], float]


@dataclass(frozen=True)
class Metric:
    """A named scoring metric.

    ``loss`` is minimized during the constant fit (lower is a better fit).
    ``report`` is the human-facing value stored on the Finding. For MSE the two
    coincide; for a metric like R2 they differ (fit may minimize ``-R2`` while the
    report is ``R2``). ``lower_is_better`` lets the driver turn ``report`` into a
    buffer score where higher is always better (the island model maximizes).
    """

    key: str
    label: str
    data_shape: str  # "regression" (tabular X, y). "spike_train" reserved.
    lower_is_better: bool
    loss: Scorer
    report: Scorer

    def score_from_value(self, value: float) -> float:
        """Convert a reported value into a maximize-me buffer score."""
        return -value if self.lower_is_better else value


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
_USER_METRICS_ENV = "WHEELER_LLMSR_METRICS"
_PROJECT_METRICS_FILE = Path(".wheeler/llmsr/metrics.py")


@dataclass(frozen=True)
class MetricSourceError:
    """A user metric module that failed to import, and why."""

    source: str
    error: str


_loaded_sources: set[str] = set()


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
    raw = os.environ.get(_USER_METRICS_ENV, "")
    sources = [
        part.strip()
        for chunk in raw.split(os.pathsep)
        for part in chunk.split(",")
        if part.strip()
    ]
    if _PROJECT_METRICS_FILE.exists():
        sources.append(str(_PROJECT_METRICS_FILE.resolve()))
    return sources


def _import_source(source: str) -> None:
    """Import one metric source: a .py path, or an importable module path."""
    if not source.endswith(".py"):
        importlib.import_module(source)
        return
    path = Path(source).resolve()
    if not path.exists():
        raise FileNotFoundError(f"no such metrics file: {path}")
    name = "wheeler_llmsr_user_metrics_" + hashlib.sha256(
        str(path).encode()
    ).hexdigest()[:8]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load metrics from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # so the module behaves like any other import
    spec.loader.exec_module(module)


def load_user_metrics() -> list[MetricSourceError]:
    """Import the scientist's metric modules so their registrations take effect.

    Sources, in order: every entry of ``$WHEELER_LLMSR_METRICS`` (separated by
    the path separator or by commas, each either an importable module path or a
    path to a .py file), then ``.wheeler/llmsr/metrics.py`` under the project.
    Each source is imported at most once per process. A source that raises is
    REPORTED, not raised: one broken file must not take down every verb.
    """
    failures: list[MetricSourceError] = []
    for source in user_metric_sources():
        if source in _loaded_sources:
            continue
        _loaded_sources.add(source)
        try:
            _import_source(source)
        except Exception as exc:
            logger.error("could not load metrics from %s: %s", source, exc)
            failures.append(
                MetricSourceError(source=source, error=f"{type(exc).__name__}: {exc}")
            )
    return failures


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
    """Return the sorted keys of registered metrics (what the act may offer)."""
    return sorted(METRICS)
