"""Read a run's training table in the shape its metric declares.

The tabular convention is the LLM-SR one: the last column is the target and the
leading columns are the inputs. What varies is (a) whether a column names the
GROUP each row belongs to (a cell, a trial, a subject), which is read separately
and excluded from the inputs, and (b) whether the target is one value per row
(``regression``) or a padded column of recorded event times (any other shape).

Split out of ``cli.py`` so the verbs stay readable; the loading rules themselves
are unchanged.
"""

from __future__ import annotations

import numpy as np
import typer

from . import fit as fit_mod
from . import metrics as metrics_mod


def _header(data_path: str) -> list[str]:
    with open(data_path) as fh:
        return [c.strip() for c in fh.readline().strip().split(",")]


def _load_xy(data_path: str, group_by: str = "") -> tuple[np.ndarray, np.ndarray, object]:
    """Load (X, y, labels). ``labels`` is None unless ``group_by`` names a column.

    The group column is EXCLUDED from X: it identifies who the row belongs to, it
    is not an input to the equation. It is read separately as text, because a
    label like ``c01`` is not a float and would otherwise come back as NaN.
    """
    data = np.genfromtxt(data_path, delimiter=",", skip_header=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if not group_by:
        return data[:, :-1], data[:, -1].reshape(-1), None

    header = _header(data_path)
    if group_by not in header:
        raise typer.BadParameter(
            f"--group-by {group_by!r} is not a column in {data_path}; columns: {header}"
        )
    gi = header.index(group_by)
    if gi == len(header) - 1:
        raise typer.BadParameter(
            f"--group-by {group_by!r} is the target column (the last one); "
            "group by an identifier column instead"
        )
    labels = np.atleast_1d(
        np.genfromtxt(data_path, delimiter=",", skip_header=1, usecols=[gi], dtype=str)
    )
    keep = [i for i in range(data.shape[1] - 1) if i != gi]
    return data[:, keep], data[:, -1].reshape(-1), labels


def _load_data(data_path: str, metric: metrics_mod.Metric, group_by: str = ""):
    """Load a run's data in the shape its metric declares.

    ``regression``: the tabular convention, last column is the target, one value
    per row. ``spike_train``: the leading columns are the stimulus and the last
    column holds the RECORDED EVENT TIMES, which in general are fewer than the
    stimulus samples, so that column is read as padded (blank cells dropped)
    rather than as one value per sample.
    """
    X, y, labels = _load_xy(data_path, group_by)
    if metric.data_shape == metrics_mod.REGRESSION:
        return X, y, labels
    if group_by:
        # Event times do not line up with stimulus rows, so a row mask cannot
        # partition them. Refusing beats silently grouping the wrong axis.
        raise typer.BadParameter(
            f"--group-by is not supported for data_shape {metric.data_shape!r}: "
            "recorded events do not correspond row-for-row with stimulus samples, "
            "so a per-row group column cannot partition them. Use one run per group."
        )
    events = np.asarray(y, dtype=float)
    return X, [float(v) for v in events[~np.isnan(events)]], None


def _as_groups(X, y, labels) -> list[tuple[str, np.ndarray, object]]:
    """Partition into (label, X_i, y_i). Ungrouped is the single-group case.

    Sorted by label so the group ORDER is deterministic across candidates. The
    vendored buffer keys its clusters on the score signature, so two candidates
    must present their groups identically or the signatures are incomparable.
    """
    if labels is None:
        return [(fit_mod.UNGROUPED, X, y)]
    y_arr = np.asarray(y)
    out = []
    for label in sorted({str(v) for v in labels.tolist()}):
        mask = np.asarray([str(v) == label for v in labels.tolist()])
        out.append((label, X[mask], y_arr[mask]))
    return out
