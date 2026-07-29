"""Pick the winning candidate and report how well it generalizes.

Three selection modes, because the best FITTER is not always the true LAW:
``fit`` takes the lowest training error, ``ood`` takes the best extrapolation onto
a held-out out-of-domain split, and ``parsimony`` takes the simplest form among
those that fit comparably well (Occam). The same held-out machinery scores the
winner on train / test_id / test_ood for ``best.json``, and the runnable footer
turns the winning program into a .py that reproduces the answer.

Split out of ``cli.py`` so the verbs stay readable; the rules themselves are
unchanged.
"""

from __future__ import annotations

import ast
from pathlib import Path

from . import fit as fit_mod
from . import metrics as metrics_mod
from .data import _load_data

_SELECT_MODES = ("fit", "ood", "parsimony")
_PARSIMONY_TOL = 10.0  # a candidate within this factor of the best error is "as good"


def _runnable_program(
    program: str, params, metric_key: str, value, data_path: str, fte: str,
    data_shape: str = metrics_mod.REGRESSION,
) -> str:
    """Append fitted constants + a runnable main so the .py reproduces the answer."""
    if data_shape == metrics_mod.REGRESSION:
        bind = f"    _n = {fte}.__code__.co_argcount - 1\n"
        show = "    print('prediction[:5]', _np.asarray(_pred).reshape(-1)[:5])\n"
    else:
        # A simulator takes the stimulus columns it declares and returns however
        # many events it returns: neither count is fixed by the table.
        bind = f"    _n = min({fte}.__code__.co_argcount - 1, _X.shape[1])\n"
        show = (
            "    _ev = list(_pred)\n"
            "    print('n_events', len(_ev), 'events[:5]', _ev[:5])\n"
        )
    footer = (
        "\n\n# --- Fitted result (discovered by LLM-SR via Wheeler) ---\n"
        f"FITTED_PARAMS = {list(params)!r}\n"
        f"METRIC = {{'name': {metric_key!r}, 'value': {value!r}}}\n\n"
        "if __name__ == '__main__':\n"
        "    import numpy as _np\n"
        f"    _d = _np.genfromtxt(r{data_path!r}, delimiter=',', skip_header=1)\n"
        "    _X, _y = _d[:, :-1], _d[:, -1].reshape(-1)\n"
        + bind
        + "    _cols = [_X[:, i] for i in range(_n)]\n"
        + f"    _pred = {fte}(*_cols, _np.array(FITTED_PARAMS))\n"
        + "    print('metric', METRIC)\n"
        + show
    )
    return program + footer


def _equation_complexity(body: str) -> int:
    """Structural complexity of an equation body: the count of operations (BinOp,
    UnaryOp, Call, Attribute, Compare). A compact law scores low; a many-term
    polynomial or a NN-like blob scores high. Drives parsimony selection: among
    forms that fit comparably, the SIMPLEST is the more likely true law (Occam).
    """
    try:
        tree = ast.parse("def _f():\n" + body)
    except SyntaxError:
        return 10**6
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Call, ast.Attribute, ast.Compare))
    )


def _candidate_ood(meta: dict, cand: dict) -> float | None:
    """Held-out out-of-domain error of a candidate (train-fitted, applied to
    test_ood). None when no OOD set exists. This is the extrapolation signal: the
    true law generalizes here, an overfit form does not."""
    # Lazy: cli imports this module, so resolving the metric at module level would
    # close the cycle.
    from .cli import _metric_for

    sibling = Path(str(meta["data_path"])).parent / "test_ood.csv"
    if not sibling.exists():
        return None
    metric = _metric_for(meta["metric"])
    # NMSE is the scale-free comparison for a regression run. For any other shape
    # it is meaningless (it assumes a row-for-row prediction), so the run's own
    # metric is the only one that can rank extrapolation.
    ood_metric = (
        metrics_mod.get_metric("nmse")
        if metric.data_shape == metrics_mod.REGRESSION
        else metric
    )
    try:
        X, y, _ = _load_data(str(sibling), metric)
    except OSError:
        return None
    return fit_mod.evaluate_fixed(
        cand["program"], meta["function_to_evolve"], X, y,
        cand["params"], ood_metric,
    )


def _select_winner(valid: list[dict], meta: dict, mode: str) -> dict:
    """Choose the winning candidate. `fit` = lowest training error (best FITTER,
    the default, back-compatible). `ood` = best extrapolation (the discovery
    signal). `parsimony` = the SIMPLEST form among those that fit comparably well
    (Occam). The last two target the true LAW rather than the best fit."""
    if mode == "fit" or len(valid) == 1:
        return max(valid, key=lambda s: s["score"])

    for c in valid:
        c["_complexity"] = _equation_complexity(c["body"])
        c["_ood"] = _candidate_ood(meta, c)

    if mode == "ood":
        with_ood = [c for c in valid if c.get("_ood") is not None]
        if with_ood:
            return min(with_ood, key=lambda c: c["_ood"])
        return max(valid, key=lambda s: s["score"])  # no OOD set: fall back to fit

    # parsimony: among candidates whose training error is within a factor of the
    # best, pick the fewest operations (tie-break toward the better fit).
    best_err = min(-c["score"] for c in valid)
    threshold = max(best_err * _PARSIMONY_TOL, best_err + 1e-12)
    good = [c for c in valid if (-c["score"]) <= threshold] or valid
    return min(good, key=lambda c: (c["_complexity"], -c["score"]))


def _split_metrics(meta: dict, winner: dict) -> dict[str, float]:
    """Score the train-fitted winner on train + sibling test_id / test_ood sets.

    Both MSE and NMSE per split for a regression run (the paper's protocol). For
    any other data shape those two are meaningless, so the run's own metric is
    reported instead. The LLM-SR datasets store
    ``<problem>/{train,test_id,test_ood}.csv``, so the test splits are siblings of
    the training file. Applies the fitted constants without re-fitting.
    """
    # Lazy: cli imports this module, so resolving the metric at module level would
    # close the cycle.
    from .cli import _metric_for

    out: dict[str, float] = {}
    if meta.get("group_by"):
        # Held-out scoring applies FIXED constants, and a grouped run has no single
        # constant vector to apply: each group kept its own. Scoring held-out data
        # per group needs a policy for groups absent from the held-out file, which
        # is deferred with the rest of the Objective work (see issue #107). Returning
        # empty is honest; applying an arbitrary group's constants would not be.
        return out
    fte = meta["function_to_evolve"]
    program = winner["program"]
    params = winner["params"]
    metric = _metric_for(meta["metric"])
    report_keys = (
        ("mse", "nmse") if metric.data_shape == metrics_mod.REGRESSION else (metric.key,)
    )
    train_path = str(meta["data_path"])
    splits = {"train": train_path}
    for name, fname in (("test_id", "test_id.csv"), ("test_ood", "test_ood.csv")):
        sibling = Path(train_path).parent / fname
        if sibling.exists():
            splits[name] = str(sibling)
    for split, path in splits.items():
        try:
            X, y, _ = _load_data(path, metric)
        except OSError:
            continue
        for mkey in report_keys:
            val = fit_mod.evaluate_fixed(
                program, fte, X, y, params, metrics_mod.get_metric(mkey)
            )
            if val is not None:
                out[f"{mkey}_{split}"] = val
    return out
