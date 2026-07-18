"""Pluggable scoring metrics for LLM-SR equation discovery.

The metric is chosen once per run (``wheeler llmsr init --metric``), bound into
the run, and used both to FIT the free constants (minimize ``loss``) and to REPORT
the result (``report``). The scientist picks it in the act; nothing is defaulted
silently.

The vertical slice wires ``mse`` only. Adding a metric is: define a ``Metric`` and
register it here. A metric also declares the data shape it expects
(``regression`` for tabular ``(X, y)``); spike-train metrics such as
Victor-Purpura will declare ``spike_train`` and carry their own loader, which is
deferred breadth (see the package plan).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
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


# The registry. Only wired metrics appear; the act offers exactly these.
METRICS: dict[str, Metric] = {MSE.key: MSE, NMSE.key: NMSE}


def get_metric(key: str) -> Metric:
    """Return the wired metric for ``key`` or raise with the available list."""
    normalized = (key or "").strip().lower()
    if normalized not in METRICS:
        raise KeyError(
            f"unknown metric {key!r}; wired metrics: {sorted(METRICS)}"
        )
    return METRICS[normalized]


def available() -> list[str]:
    """Return the sorted keys of wired metrics (what the act may offer)."""
    return sorted(METRICS)
