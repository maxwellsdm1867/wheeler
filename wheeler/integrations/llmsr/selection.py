"""Pick the winning candidate and report how well it generalizes.

Three selection modes, because the best FITTER is not always the true LAW:
``fit`` takes the lowest training error, ``ood`` takes the best extrapolation onto
a held-out out-of-domain split, and ``parsimony`` takes the simplest form among
those that fit comparably well (Occam). The same held-out machinery scores the
winner on train / test_id / test_ood for ``best.json``, and the runnable footer
turns the winning program into a .py that reproduces the answer.

Held-out scoring reports TWO quantities, and they answer different questions:

``fixed-theta``
    the winner's own constants applied unchanged. This asks whether the
    CONSTANTS transfer.
``refit``
    the constants fitted from scratch on the held-out data, under the same form.
    This asks whether the FORM transfers, which is the question symbolic
    regression is actually asking.

They travel in separate, labelled dicts (``metrics`` and ``metrics_refit`` in
``best.json``) precisely so neither can stand in for the other. The on-demand
version of the same comparison, against an arbitrary file, is ``transfer.py``.

Split out of ``cli.py`` so the verbs stay readable.
"""

from __future__ import annotations

import ast
from pathlib import Path

from . import fit as fit_mod
from . import metrics as metrics_mod
from .data import _as_groups, _load_data

_SELECT_MODES = ("fit", "ood", "parsimony")
_PARSIMONY_TOL = 10.0  # a candidate within this factor of the best error is "as good"

# The held-out splits `best` scores, as `<split>: <sibling filename>`.
_SIBLING_SPLITS = (("test_id", "test_id.csv"), ("test_ood", "test_ood.csv"))


def _grouped_footer(
    group_by: str,
    params_per_group: dict,
    value_per_group: dict,
    metric_key: str,
    value,
    data_path: str,
    fte: str,
) -> str:
    """The footer for a GROUPED run: the per-group constant table + a main that
    applies each group's own constants to that group's own rows.

    A grouped run has no single parameter vector, and that is the point: every
    group refits its OWN constants under one shared form. Writing the flat
    ``FITTED_PARAMS`` here would write ``[]`` and a file that calls the equation
    with an empty array, so the artifact Wheeler advertises as durable and
    re-runnable would be neither.

    The row filter mirrors ``data.py::_load_xy`` exactly: the group column
    identifies who a row belongs to and is EXCLUDED from the inputs, and the
    labels are read as text, because a label like ``c01`` is not a float and
    would come back NaN through the numeric read.
    """
    table = {
        str(label): [float(v) for v in vals]
        for label, vals in params_per_group.items()
    }
    per_group_value = {
        str(label): float(v) for label, v in (value_per_group or {}).items()
    }
    return (
        "\n\n# --- Fitted result (discovered by LLM-SR via Wheeler) ---\n"
        "# GROUPED run: each group refit its OWN constants under this one shared\n"
        "# form, so there is no single parameter vector. Each entry below is one\n"
        "# group's answer, and METRIC['value'] is the mean over them.\n"
        f"GROUP_BY = {group_by!r}\n"
        f"FITTED_PARAMS_PER_GROUP = {table!r}\n"
        f"METRIC = {{'name': {metric_key!r}, 'value': {value!r}, "
        f"'per_group': {per_group_value!r}}}\n\n"
        "if __name__ == '__main__':\n"
        "    import numpy as _np\n"
        f"    _path = r{data_path!r}\n"
        "    with open(_path) as _fh:\n"
        "        _header = [_c.strip() for _c in _fh.readline().strip().split(',')]\n"
        "    _d = _np.genfromtxt(_path, delimiter=',', skip_header=1)\n"
        "    if _d.ndim == 1:\n"
        "        _d = _d.reshape(1, -1)\n"
        "    _gi = _header.index(GROUP_BY)\n"
        "    _labels = _np.atleast_1d(_np.genfromtxt(\n"
        "        _path, delimiter=',', skip_header=1, usecols=[_gi], dtype=str))\n"
        "    _keep = [_i for _i in range(_d.shape[1] - 1) if _i != _gi]\n"
        "    _X, _y = _d[:, _keep], _d[:, -1].reshape(-1)\n"
        f"    _n = {fte}.__code__.co_argcount - 1\n"
        "    print('metric', METRIC)\n"
        "    for _g in sorted(FITTED_PARAMS_PER_GROUP):\n"
        "        _mask = _np.asarray([str(_v) == _g for _v in _labels.tolist()])\n"
        "        _gX = _X[_mask]\n"
        f"        _pred = {fte}(*[_gX[:, _i] for _i in range(_n)],\n"
        "                      _np.array(FITTED_PARAMS_PER_GROUP[_g]))\n"
        "        print('group', _g, 'n_rows', int(_mask.sum()),\n"
        "              'prediction[:5]', _np.asarray(_pred).reshape(-1)[:5])\n"
    )


def _multidata_footer(
    report: dict,
    metric_key: str,
    value,
    group_by: str,
    fte: str,
    data_shape: str = metrics_mod.REGRESSION,
) -> str:
    """The footer for a MULTI-DATASET run: the constants, and a runner that loops.

    Neither other footer can address this shape. The flat one applies a single
    parameter vector to one ``data_path``; the grouped one filters that one file's
    rows by a group column. A multi-dataset run has neither a single vector nor a
    single file: its units are (dataset, group) pairs spanning several tables, so
    the flat branch would write ``FITTED_PARAMS = []`` and raise, and the grouped
    branch would match keys like ``A:c01`` against one file's cell labels and
    report zero rows for every group WITHOUT failing.

    That second failure is what this footer is written against. It loops the
    SCORED datasets, and the groups within each one, and applies each unit's OWN
    constants to that unit's OWN rows, so the key that names a fit and the rows
    that fit it can never come apart. The row filter and the group-column
    exclusion mirror ``_grouped_footer``, which mirrors ``data.py::_load_xy``.

    Two mismatches are possible once the file on disk and the run's key set can
    disagree, and BOTH are reported and both exit non-zero:

    ``missing``
        a unit in the file that the run has no constants for (the table gained a
        group after the search ran). Applying a neighbouring group's theta would
        answer a different question dressed as this one.
    ``unused``
        a key in the table that no row in any file matched (the file lost a group,
        or was replaced). The number in ``METRIC`` then describes rows this run
        can no longer show you.

    Silence on either would be the exact outcome the per-group protocol exists to
    prevent: a plausible-looking printout computed over the wrong rows.

    HELD-OUT datasets are listed and deliberately NOT run: the search fitted no
    constants on them, so there is nothing to apply. Refitting the form on one is
    ``wheeler llmsr transfer``, a separate act with its own provenance.
    """
    entries = [e for e in report.get("entries", []) if isinstance(e, dict)]
    scored = [e for e in entries if e.get("regime") == "scored"]
    held_out = [e for e in entries if e.get("regime") != "scored"]
    params_per_key: dict[str, list[float]] = {}
    value_per_key: dict[str, float] = {}
    for entry in scored:
        for key, vals in (entry.get("params_per_key") or {}).items():
            params_per_key[str(key)] = [float(v) for v in vals]
        for key, val in (entry.get("value_per_key") or {}).items():
            value_per_key[str(key)] = float(val)
    scored_paths = {str(e.get("name", "")): str(e.get("path", "")) for e in scored}
    held_out_paths = {str(e.get("name", "")): str(e.get("path", "")) for e in held_out}
    if data_shape == metrics_mod.REGRESSION:
        bind = f"            _n = {fte}.__code__.co_argcount - 1\n"
        show = (
            "                  'prediction[:5]',\n"
            "                  _np.asarray(_pred).reshape(-1)[:5])\n"
        )
    else:
        # A simulator takes the stimulus columns it declares and returns however
        # many events it returns: neither count is fixed by the table.
        bind = (
            f"            _n = min({fte}.__code__.co_argcount - 1, _gX.shape[1])\n"
        )
        show = "                  'n_events', len(list(_pred)))\n"
    return (
        "\n\n# --- Fitted result (discovered by LLM-SR via Wheeler) ---\n"
        "# MULTI-DATASET run: this one shared form was refitted, with its OWN\n"
        "# constants, on every unit the search scored. A unit is a (dataset,\n"
        "# group) pair, so there is no single parameter vector and no single\n"
        "# input file. Keys below are 'dataset' or 'dataset:group', and the\n"
        "# runner walks them: each unit's rows are fitted by that unit's own\n"
        "# constants, never by a neighbour's. The labelled breakdown, including\n"
        "# which datasets were only declared, is best.json['datasets'].\n"
        "# HELD-OUT datasets are listed but NOT run: the search fitted no\n"
        "# constants on them, so there is nothing here to apply to them.\n"
        f"SCORED_DATASETS = {scored_paths!r}\n"
        f"HELD_OUT_DATASETS = {held_out_paths!r}\n"
        f"GROUP_BY = {group_by!r}\n"
        f"FITTED_PARAMS_PER_KEY = {params_per_key!r}\n"
        f"METRIC = {{'name': {metric_key!r}, 'value': {value!r}, "
        f"'per_key': {value_per_key!r}}}\n\n"
        "if __name__ == '__main__':\n"
        "    import numpy as _np\n"
        "    print('metric', METRIC)\n"
        "    _missing, _unused = [], set(FITTED_PARAMS_PER_KEY)\n"
        "    for _name in sorted(SCORED_DATASETS):\n"
        "        _path = SCORED_DATASETS[_name]\n"
        "        with open(_path) as _fh:\n"
        "            _header = [_c.strip() for _c in _fh.readline().strip().split(',')]\n"
        "        _d = _np.genfromtxt(_path, delimiter=',', skip_header=1)\n"
        "        if _d.ndim == 1:\n"
        "            _d = _d.reshape(1, -1)\n"
        "        if GROUP_BY and GROUP_BY in _header:\n"
        "            _gi = _header.index(GROUP_BY)\n"
        "            _labels = [str(_v) for _v in _np.atleast_1d(_np.genfromtxt(\n"
        "                _path, delimiter=',', skip_header=1, usecols=[_gi],\n"
        "                dtype=str)).tolist()]\n"
        "            _keep = [_i for _i in range(_d.shape[1] - 1) if _i != _gi]\n"
        "            _units = [(_g, _np.asarray([_v == _g for _v in _labels]))\n"
        "                      for _g in sorted(set(_labels))]\n"
        "        else:\n"
        "            _keep = list(range(_d.shape[1] - 1))\n"
        "            _units = [('', _np.ones(_d.shape[0], dtype=bool))]\n"
        "        _X = _d[:, _keep]\n"
        "        for _g, _mask in _units:\n"
        "            _key = _name + ':' + _g if _g else _name\n"
        "            if _key not in FITTED_PARAMS_PER_KEY:\n"
        "                _missing.append(_key)\n"
        "                print('dataset', _name, 'group', _g or '-', 'key', _key,\n"
        "                      'n_rows', int(_mask.sum()), 'NO CONSTANTS')\n"
        "                continue\n"
        "            _unused.discard(_key)\n"
        "            _gX = _X[_mask]\n"
        + bind
        + f"            _pred = {fte}(*[_gX[:, _i] for _i in range(_n)],\n"
        "                          _np.array(FITTED_PARAMS_PER_KEY[_key]))\n"
        "            print('dataset', _name, 'group', _g or '-', 'key', _key,\n"
        "                  'n_rows', int(_mask.sum()),\n"
        + show
        + "    for _name in sorted(HELD_OUT_DATASETS):\n"
        "        print('dataset', _name, 'HELD OUT: the search fitted no constants\\n'\n"
        "              '  here, so there are none to apply. `wheeler llmsr transfer\\n'\n"
        "              '  --run <run> --data <file>` refits the form on it.')\n"
        "    if _missing or _unused:\n"
        "        raise SystemExit(\n"
        "            'This run and the files on disk no longer describe the same units.\\n'\n"
        "            'units in the data with no constants here: ' + repr(sorted(_missing)) + '\\n'\n"
        "            'constants here matched by no row: ' + repr(sorted(_unused)) + '\\n'\n"
        "            'Nothing was guessed: a unit with no constants of its own was\\n'\n"
        "            'skipped rather than fitted with a neighbour\\'s. Re-run the\\n'\n"
        "            'search against the current files, or restore the ones it scored.'\n"
        "        )\n"
    )


def _no_constants_footer(metric_key: str, value, value_per_key: dict | None) -> str:
    """The footer for a winner that has NO constants: the score, and no runner.

    Reachable only through the spec's own ``@evaluate.run`` (``spec_eval.py``),
    and only when it returned upstream's bare float. Upstream's contract has
    nowhere to put the fitted constants: every upstream spec computes
    ``optimized_params = result.x`` inside ``evaluate`` and then discards it,
    returning the score alone. So the run genuinely has no constants to write.

    The flat footer below would then emit ``FITTED_PARAMS = []`` and a ``__main__``
    that calls the equation with an empty array, which raises at the reader's
    feet with an IndexError that explains nothing. This says the true thing
    instead, and exits non-zero, on the same rule as ``_multidata_footer``: no
    answer beats a wrong one, and an exit 0 printing nothing reads as success.
    """
    per_key = {str(k): float(v) for k, v in (value_per_key or {}).items()}
    return (
        "\n\n# --- Result (discovered by LLM-SR via Wheeler) ---\n"
        "# This run scored through the SPEC'S OWN @evaluate.run, which returned\n"
        "# upstream's bare score and no constants: upstream's contract has\n"
        "# nowhere to put them (their specs fit `result.x` inside evaluate and\n"
        "# then discard it). So the form below is the discovery and the score is\n"
        "# its number, but the constants that produced it were never returned.\n"
        "# To recover them, have the spec's evaluate return\n"
        "#     {'score': <float>, 'params': [...]}\n"
        "# or drop --use-spec-evaluate and let Wheeler's fit seam fit them.\n"
        "FITTED_PARAMS = None\n"
        f"METRIC = {{'name': {metric_key!r}, 'value': {value!r}, "
        f"'per_key': {per_key!r}}}\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(\n"
        "        'No runner is emitted: this run scored through the spec\\'s own\\n'\n"
        "        '@evaluate.run, which returned a score and no fitted constants,\\n'\n"
        "        'so the equation above cannot be applied to data from this file.\\n'\n"
        "        'See the comment above METRIC for the two ways to get them.'\n"
        "    )\n"
    )


def _runnable_program(
    program: str, params, metric_key: str, value, data_path: str, fte: str,
    data_shape: str = metrics_mod.REGRESSION,
    *,
    group_by: str = "",
    params_per_group: dict | None = None,
    value_per_group: dict | None = None,
    dataset_report: dict | None = None,
    no_constants: bool = False,
) -> str:
    """Append fitted constants + a runnable main so the .py reproduces the answer.

    A grouped run takes the per-group branch: its constants are a TABLE, not a
    vector. Grouping is only reachable for the regression shape (``data.py``
    refuses ``--group-by`` for any other, since recorded events do not line up
    row-for-row with stimulus samples), so the grouped footer is written against
    the tabular convention.

    ``no_constants`` is checked FIRST and is passed only when the winner has no
    fitted constants at all, which only the spec-evaluate door can produce. Every
    footer below writes constants; with none to write, the flat one would emit a
    runner that raises. See ``_no_constants_footer``.

    ``dataset_report`` is passed only when the run's score keys span more than one
    file, and it is checked next: both footers below address a single table, so
    a caller that passes neither reaches exactly the branch it always reached,
    byte for byte. See ``_multidata_footer``.
    """
    if no_constants:
        return program + _no_constants_footer(metric_key, value, value_per_group)
    if dataset_report:
        return program + _multidata_footer(
            dataset_report, metric_key, value, group_by, fte, data_shape
        )
    if group_by and params_per_group:
        return program + _grouped_footer(
            group_by, params_per_group, value_per_group or {}, metric_key, value,
            data_path, fte,
        )
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


def _source_theta(source: dict, label: str) -> tuple[list[float] | None, str]:
    """The source constants that legitimately apply to group ``label``, and why.

    Never an arbitrary pick. There are exactly two cases where a fixed-theta
    number is defined: the source fitted THIS group (so it has that group's own
    constants), or the source has a single constant vector, which is what an
    ungrouped run's constants are and what "apply the source's constants" means
    for it. A source that fitted per-group constants and has none for this group
    gets ``None``: substituting some other group's theta would answer a question
    nobody asked, dressed as this one.
    """
    per_group = source.get("params_per_group") or {}
    own = per_group.get(label)
    if own:
        return [float(v) for v in own], "the source fitted this same group"
    vectors = [v for v in per_group.values() if v]
    if len(vectors) == 1:
        return [float(v) for v in vectors[0]], "the source has a single constant vector"
    flat = source.get("params") or []
    if flat and not vectors:
        return [float(v) for v in flat], "the source has a single constant vector"
    return None, (
        "the source fitted its constants per group and none of them belongs to "
        "this group"
    )


def _fixed_theta_per_group(
    program: str, fte: str, groups: list, source: dict, metric: metrics_mod.Metric
) -> tuple[dict[str, float | None], dict[str, list[float]], dict[str, str]]:
    """Score every group with the SOURCE constants, refitting nothing.

    Returns ``(value_per_group, theta_per_group, reason_per_group)``. A group with
    no defensible source vector, or whose evaluation failed, gets ``None``, and
    the reason says which.
    """
    values: dict[str, float | None] = {}
    thetas: dict[str, list[float]] = {}
    reasons: dict[str, str] = {}
    for label, gX, gy in groups:
        theta, why = _source_theta(source, label)
        reasons[label] = why
        if theta is None:
            values[label] = None
            continue
        thetas[label] = theta
        value = fit_mod.evaluate_fixed(program, fte, gX, gy, theta, metric)
        values[label] = value
        if value is None:
            reasons[label] = (
                why + ", but the equation produced no finite value under them"
            )
    return values, thetas, reasons


def _strict_mean(values: dict[str, float | None]) -> float | None:
    """The mean over groups, or ``None`` when ANY group is missing a number.

    Strict for the reason ``evaluate_body_grouped`` is strict: a mean over the
    subset that happened to work is not the number a reader would take it for,
    and it silently flatters a form that failed somewhere.
    """
    present = [v for v in values.values() if v is not None]
    if not values or len(present) != len(values):
        return None
    return sum(present) / len(present)


def _load_groups(path: str, metric: metrics_mod.Metric, group_by: str) -> list | None:
    """Load one file and partition it, or ``None`` if it cannot be read that way.

    Broad by intent: this is a REPORTING path, and a sibling split that is
    missing, malformed, or lacks the run's group column must leave that number
    unreported rather than abort the verb that was asked for a different one.
    """
    try:
        X, y, labels = _load_data(path, metric, group_by)
    except Exception:
        return None
    return _as_groups(X, y, labels)


def _candidate_ood(meta: dict, cand: dict) -> float | None:
    """Held-out out-of-domain error of a candidate, under THE RUN'S OWN metric.

    None when no OOD set exists, or when it cannot be scored (a grouped run whose
    OOD file does not carry the group column has no constants that belong to its
    groups). This is the extrapolation signal: the true law generalizes here, an
    overfit form does not.

    The metric is the run's, always. It used to be hardcoded to NMSE for any
    regression run on the grounds that NMSE is the scale-free comparison, which
    quietly ranked a run whose declared objective was a registered custom metric
    on a quantity it never chose. The run's objective is the run's objective.

    FIXED-THETA by design, and this is not the same deferral as the one
    ``_split_metrics`` used to carry. Refitting on the OOD split before ranking
    would reward flexibility, which is exactly what OOD selection exists to
    punish: a nine-term polynomial refitted on the extrapolation region fits it,
    while the whole signal here is that its TRAIN-fitted constants diverge there.
    The refit number for the winner is reported next to this one by
    ``_split_metrics``, so both are visible; only this one ranks.
    """
    # Lazy: cli imports this module, so resolving the metric at module level would
    # close the cycle.
    from .cli import _metric_for

    sibling = Path(str(meta["data_path"])).parent / "test_ood.csv"
    if not sibling.exists():
        return None
    metric = _metric_for(meta["metric"])
    groups = _load_groups(
        str(sibling), metric, str(meta.get("group_by", "") or "")
    )
    if groups is None:
        return None
    values, _thetas, _reasons = _fixed_theta_per_group(
        cand["program"], meta["function_to_evolve"], groups, cand, metric
    )
    return _strict_mean(values)


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
            # Ranked through `score_from_value`, the same maximize-me convention
            # the buffer uses, so a metric that declares `lower_is_better=False`
            # is not ranked backwards. Lower error stays better for MSE/NMSE.
            from .cli import _metric_for

            ood_metric = _metric_for(meta["metric"])
            return max(with_ood, key=lambda c: ood_metric.score_from_value(c["_ood"]))
        return max(valid, key=lambda s: s["score"])  # no OOD set: fall back to fit

    # parsimony: among candidates whose training error is within a factor of the
    # best, pick the fewest operations (tie-break toward the better fit).
    best_err = min(-c["score"] for c in valid)
    threshold = max(best_err * _PARSIMONY_TOL, best_err + 1e-12)
    good = [c for c in valid if (-c["score"]) <= threshold] or valid
    return min(good, key=lambda c: (c["_complexity"], -c["score"]))


def _report_keys(metric: metrics_mod.Metric) -> tuple[str, ...]:
    """Which metrics to report a split under: MSE and NMSE for a regression run,
    the run's own metric for any other shape (where those two are meaningless)."""
    if metric.data_shape == metrics_mod.REGRESSION:
        return ("mse", "nmse")
    return (metric.key,)


def _split_metrics(meta: dict, winner: dict) -> tuple[dict[str, float], dict[str, float]]:
    """Score the winner on train + sibling test_id / test_ood sets, BOTH ways.

    Returns ``(fixed_theta, refit)``, two separately labelled dicts keyed
    ``<metric>_<split>``:

    ``fixed_theta``
        the winner's own constants applied unchanged. Does the CONSTANTS
        transfer? This is the historic ``metrics`` dict, unchanged for an
        ungrouped run, key for key and number for number.
    ``refit``
        the constants refitted from scratch on that split, under the same form
        and the run's own fit knobs. Does the FORM transfer? This is the
        question symbolic regression is asking, and it used to go unasked.

    Both are per group when the run declared ``--group-by``: each group refits
    its own constants, and the fixed-theta side applies the source constants that
    belong to that group (``_source_theta``), reporting nothing at all where none
    does rather than substituting another group's. That policy is what used to be
    deferred, and it is why this returned ``{}`` for any grouped run.

    TRAIN is deliberately fixed-theta only, and omitted entirely for a grouped
    run. On train the two quantities are the same measurement: that is where the
    constants were fitted. A grouped run's train answer is its per-group value
    TABLE, which ``best.json`` already carries as ``value_per_group``, and whose
    mean the ingest derives and stamps as a mean. Writing a pooled ``<metric>_train``
    next to it would put an unlabelled duplicate where the labelled one is.

    The held-out scoring is WHEELER'S, not upstream's. The LLM-SR datasets store
    ``<problem>/{train,test_id,test_ood}.csv``, so the test splits are siblings of
    the training file, but upstream's own ``main.py`` loads only ``train.csv`` and
    nothing in its pipeline opens the test splits. The splits are theirs; scoring
    against them is ours.
    """
    # Lazy: cli imports this module, so resolving these at module level would
    # close the cycle.
    from .cli import _fit_knobs, _metric_for

    fixed: dict[str, float] = {}
    refit: dict[str, float] = {}
    fte = meta["function_to_evolve"]
    program = winner["program"]
    metric = _metric_for(meta["metric"])
    group_by = str(meta.get("group_by", "") or "")
    keys = _report_keys(metric)
    train_path = str(meta["data_path"])

    splits: dict[str, str] = {} if group_by else {"train": train_path}
    for name, fname in _SIBLING_SPLITS:
        sibling = Path(train_path).parent / fname
        if sibling.exists():
            splits[name] = str(sibling)

    for split, path in splits.items():
        groups = _load_groups(path, metric, group_by)
        if groups is None:
            continue
        for mkey in keys:
            values, _thetas, _reasons = _fixed_theta_per_group(
                program, fte, groups, winner, metrics_mod.get_metric(mkey)
            )
            val = _strict_mean(values)
            if val is not None:
                fixed[f"{mkey}_{split}"] = val
        if split == "train":
            # The constants were fitted here. Refitting reports the same number
            # under a second name, which is noise, not a second quantity.
            continue
        # ONE refit per split, under the run's own objective (what the search
        # fitted against), then every reported key is read off those constants.
        # Refitting once per report key would fit three different objectives and
        # call the results comparable.
        result = fit_mod.evaluate_body_grouped(
            program, fte, groups, metric,
            max_nparams=int(meta.get("max_nparams") or 10),
            timeout_seconds=int(meta.get("timeout") or 30),
            **_fit_knobs(meta),
        )
        if not result.valid:
            continue
        for mkey in keys:
            values = {
                label: fit_mod.evaluate_fixed(
                    program, fte, gX, gy,
                    result.params_per_group[label],
                    metrics_mod.get_metric(mkey),
                )
                for label, gX, gy in groups
            }
            val = _strict_mean(values)
            if val is not None:
                refit[f"{mkey}_{split}"] = val
    return fixed, refit
