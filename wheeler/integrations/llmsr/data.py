"""Read a run's training tables in the shape its metric declares, and name them.

The tabular convention is the LLM-SR one: the last column is the target and the
leading columns are the inputs. What varies is (a) whether a column names the
GROUP each row belongs to (a cell, a trial, a subject), which is read separately
and excluded from the inputs, and (b) whether the target is one value per row
(``regression``) or a padded column of recorded event times (any other shape).

A run may bind SEVERAL datasets (``--data A=a.csv --data B=b.csv``), which is
upstream's shape: ``vendor/evaluator.py`` loops its inputs and builds one score
per named input. Wheeler had collapsed that to a single hardcoded key. Reopening
it is what lets a form be extracted from one cell and JUDGED on cells it never
saw, refitting its constants each time, which is a test of the FORM rather than
of the parameterization.

The unit of fitting is therefore a (dataset, group) pair: one shared form, one
theta per pair. ``score_key`` names those pairs, and its scheme is fixed at
``init`` and recorded in ``meta.json``, because the vendored buffer clusters
candidates on the score SIGNATURE and two candidates in one run must present
identical keys or the signatures are incomparable.

Split out of ``cli.py`` so the verbs stay readable; the loading rules themselves
are unchanged.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import typer

from . import fit as fit_mod
from . import metrics as metrics_mod


def _header(data_path: str) -> list[str]:
    with open(data_path) as fh:
        return [c.strip() for c in fh.readline().strip().split(",")]


def input_columns(data_path: str, group_by: str = "") -> tuple[str, ...]:
    """Name the columns of ``X``, in order, for the same file ``_load_xy`` reads.

    Derived from the same header and the same two exclusions (the trailing target
    column, and the group column when one is named), so the names line up with
    the array positions by construction rather than by a second convention.
    """
    header = _header(data_path)
    if not group_by or group_by not in header:
        return tuple(header[:-1])
    # By INDEX, not by name, so this drops exactly the column `_load_xy` drops
    # even when a header repeats a name.
    gi = header.index(group_by)
    return tuple(c for i, c in enumerate(header[:-1]) if i != gi)


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


# ------------------------------------------------------------------- datasets

# What separates a dataset from a group inside one score key. Excluded from a
# dataset NAME so a key can always be read back apart.
KEY_SEP = ":"

# How a run names the units it scores. Fixed at ``init``, recorded in
# ``meta.json``, and never renegotiated mid-run.
#
# ``SCHEME_GROUP``
#     The key is the group label alone: ``data`` for an ungrouped run, ``c01``
#     for a grouped one. This is what Wheeler has always written, and it is used
#     for exactly one shape: a single scored dataset carrying the default name.
#     Reproducing it verbatim is not politeness, it is correctness. The vendored
#     buffer clusters candidates on the sorted score signature and ranks islands
#     on a mean taken in key-insertion order, so a changed key SET would silently
#     invalidate the buffer state of every run already on disk.
# ``SCHEME_DATASET``
#     The key names the dataset (``A``), and the group too when the run is
#     grouped (``A:c01``). Used the moment a run declares a dataset by name or
#     scores more than one.
SCHEME_GROUP = "group"
SCHEME_DATASET = "dataset"

# A dataset name is a label a human types and a key a machine splits, so it may
# not carry the separator, whitespace, or a path separator.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]*$")


@dataclass(frozen=True)
class DatasetSpec:
    """One declared ``--data``: what it is called and where it lives."""

    name: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "path": self.path}


@dataclass(frozen=True)
class Unit:
    """One fittable unit: the rows that share a single set of fitted constants.

    A unit is a (dataset, group) pair. ``key`` is what the score vector calls it
    and therefore what reaches the vendored buffer; ``dataset`` and ``group`` are
    kept alongside so a reader (progress ping, ``best.json`` breakdown) never has
    to parse the key back apart.
    """

    key: str
    dataset: str
    group: str
    X: np.ndarray
    y: Any


def _split_named(value: str) -> tuple[str, str]:
    """Read one ``--data`` value as ``(name, path)``; an empty name means unnamed.

    A value is ``NAME=PATH`` when it contains ``=`` and the text before the FIRST
    ``=`` holds no path separator. So ``--data cell4=rec.csv`` names it ``cell4``,
    while ``--data ./runs=2024/rec.csv`` is a path with an ``=`` in it. Splitting
    on the first ``=`` (not the last) leaves a path free to contain more of them.
    """
    head, sep, tail = value.partition("=")
    if not sep or not tail.strip() or "/" in head or "\\" in head:
        return "", value.strip()
    return head.strip(), tail.strip()


def _check_name(name: str, value: str) -> str:
    if not _NAME_RE.match(name):
        raise typer.BadParameter(
            f"dataset name {name!r} (from --data {value!r}) is not usable: a name "
            "must start with a letter or digit and hold only letters, digits, "
            f"'_', '.', '+' or '-'. In particular {KEY_SEP!r} is reserved, because "
            "a score key for a grouped run reads 'dataset" + KEY_SEP + "group'."
        )
    return name


def parse_datasets(values: Sequence[str]) -> list[DatasetSpec]:
    """Resolve the repeated ``--data`` values into named, existing datasets.

    Naming, in order of preference: what the scientist wrote (``NAME=path``),
    then the file stem when a run declares several. A SINGLE unnamed ``--data``
    keeps ``fit.UNGROUPED`` verbatim, which is the whole backward-compatibility
    hinge: that run's score keys, and therefore its buffer state, are exactly
    what they were before a dataset could be named at all.

    Everything that could make two units collide is refused here rather than
    surfacing later as a mis-clustered island: a duplicate name, a name that
    cannot be a key, a stem that repeats.
    """
    raw = [v for v in (value.strip() for value in values) if v]
    if not raw:
        raise typer.BadParameter("--data is required: give at least one dataset")

    parsed = [_split_named(v) for v in raw]
    single_unnamed = len(parsed) == 1 and not parsed[0][0]

    out: list[DatasetSpec] = []
    seen: dict[str, str] = {}
    for value, (name, path) in zip(raw, parsed):
        resolved = Path(path).expanduser()
        if not resolved.is_file():
            raise typer.BadParameter(f"--data {value!r}: no readable file at {path!r}")
        if name:
            _check_name(name, value)
        elif single_unnamed:
            # The historic shape. Its key must stay `data`, verbatim.
            name = fit_mod.UNGROUPED
        else:
            name = _check_name(resolved.stem, value)
        if name in seen:
            raise typer.BadParameter(
                f"dataset name {name!r} is declared twice (--data {seen[name]!r} and "
                f"--data {value!r}). Name them apart: --data A={path}"
            )
        seen[name] = value
        out.append(DatasetSpec(name=name, path=str(resolved.resolve())))
    return out


def _select(datasets: Sequence[DatasetSpec], names: Sequence[str], flag: str) -> list[DatasetSpec]:
    """Pick the named datasets, in DECLARATION order, refusing an unknown name.

    Declaration order rather than the order the names were typed, so the key set
    a run presents to the buffer depends on the run, not on how the command line
    happened to be written.
    """
    known = {d.name: d for d in datasets}
    wanted = set()
    for name in names:
        if name not in known:
            raise typer.BadParameter(
                f"{flag} {name!r} is not a declared dataset; declared: "
                f"{sorted(known)}. Name one with --data {name}=<path>."
            )
        wanted.add(name)
    return [d for d in datasets if d.name in wanted]


def resolve_score_on(
    datasets: Sequence[DatasetSpec], score_on: Sequence[str]
) -> list[DatasetSpec]:
    """Which datasets enter the objective. Default: every one of them.

    Defaulting to all is what makes a single-dataset run behave exactly as it did:
    it names its one dataset and scores against it.
    """
    names = _split_names(score_on)
    if not names:
        return list(datasets)
    return _select(datasets, names, "--score-on")


def resolve_seed_from(
    datasets: Sequence[DatasetSpec], seed_from: str
) -> DatasetSpec:
    """Which dataset shapes the prompt. Default: the first ``--data``.

    Deliberately a separate role from ``--score-on``. The dataset the generator
    is shown is where the FORM comes from; the datasets in the objective are what
    the form is judged on. Keeping them apart is what lets a form be extracted
    from one cell and tested on cells it never saw.
    """
    name = seed_from.strip()
    if not name:
        return datasets[0]
    return _select(datasets, [name], "--seed-from")[0]


def _split_names(values: Sequence[str]) -> list[str]:
    """Flatten repeated and comma-separated name lists, keeping first-seen order."""
    out: list[str] = []
    for value in values or ():
        for name in str(value).split(","):
            name = name.strip()
            if name and name not in out:
                out.append(name)
    return out


def key_scheme(scored: Sequence[DatasetSpec]) -> str:
    """The score-key scheme this run is bound to, decided once at ``init``.

    ``SCHEME_GROUP`` exactly when the run scores one dataset carrying the default
    name, which is precisely the run an older Wheeler could have created. Every
    other shape qualifies its keys by dataset, because otherwise two datasets
    sharing a group label would collide into one key and silently average.
    """
    if len(scored) == 1 and scored[0].name == fit_mod.UNGROUPED:
        return SCHEME_GROUP
    return SCHEME_DATASET


def score_key(dataset: str, group: str, scheme: str) -> str:
    """Name one (dataset, group) unit in the score vector."""
    if scheme == SCHEME_GROUP:
        return group
    return dataset if group == fit_mod.UNGROUPED else f"{dataset}{KEY_SEP}{group}"


def keys_for(dataset: str, keys: Sequence[str], scheme: str) -> list[str]:
    """The score keys belonging to ``dataset``, in the order they were fitted.

    Reads the key set back apart rather than recomputing it from the data, so a
    breakdown reports what the fit ACTUALLY produced. Under ``SCHEME_GROUP`` there
    is only one dataset, so every key is its own.
    """
    if scheme == SCHEME_GROUP:
        return list(keys)
    prefix = f"{dataset}{KEY_SEP}"
    return [k for k in keys if k == dataset or k.startswith(prefix)]


def datasets_from_meta(meta: Mapping[str, Any]) -> list[DatasetSpec]:
    """The datasets a run is bound to, tolerating a run dir written before S2.

    An older ``meta.json`` records a single ``data_path`` and no names at all.
    Reading it back as one dataset called ``fit.UNGROUPED`` reproduces its key
    scheme exactly, so an existing run keeps replaying through ``prompt`` /
    ``submit`` / ``best`` with the buffer state it already has.
    """
    declared = meta.get("datasets")
    if isinstance(declared, list) and declared:
        out = []
        for entry in declared:
            if isinstance(entry, Mapping) and entry.get("path"):
                out.append(DatasetSpec(
                    name=str(entry.get("name") or fit_mod.UNGROUPED),
                    path=str(entry["path"]),
                ))
        if out:
            return out
    return [DatasetSpec(name=fit_mod.UNGROUPED, path=str(meta.get("data_path", "")))]


def scored_from_meta(meta: Mapping[str, Any]) -> list[DatasetSpec]:
    """The datasets a run's objective is taken over, per its own ``meta.json``."""
    datasets = datasets_from_meta(meta)
    names = [str(n) for n in (meta.get("score_on") or [])]
    if not names:
        return datasets
    by_name = {d.name: d for d in datasets}
    scored = [by_name[n] for n in names if n in by_name]
    return scored or datasets


def scheme_from_meta(meta: Mapping[str, Any]) -> str:
    """The run's recorded key scheme, derived for a run dir written before S2."""
    recorded = str(meta.get("score_key_scheme") or "")
    if recorded in (SCHEME_GROUP, SCHEME_DATASET):
        return recorded
    return key_scheme(scored_from_meta(meta))


def load_units(
    scored: Sequence[DatasetSpec],
    metric: metrics_mod.Metric,
    *,
    group_by: str = "",
    scheme: str = SCHEME_GROUP,
    loader: str = "",
) -> list[Unit]:
    """Load every scored dataset into the units the fit will refit one by one.

    Routed through the loader registry rather than around it, so the run's choice
    of how to READ a recording composes with its choice of WHICH recordings to
    score. The built-in ``csv`` loader delegates straight back to ``_load_data``
    and ``_as_groups``, so a run that names no loader loads exactly as before.

    Dataset order is declaration order and group order is sorted, so the key
    sequence is a property of the run and not of when a file happened to be read.
    """
    # Local: `loaders` imports `data` back (inside its csv loader), and the
    # registry has to be importable by anything.
    from . import loaders as loaders_mod

    loaders_mod.load_user_loaders()
    key = (loader or "").strip() or loaders_mod.DEFAULT_LOADER
    units: list[Unit] = []
    for spec in scored:
        try:
            groups = loaders_mod.load_groups(
                spec.path, metric, group_by=group_by, loader=key
            )
        except (KeyError, ValueError) as exc:
            raise typer.BadParameter(
                f"dataset {spec.name!r} ({spec.path}): {str(exc).strip()}"
            ) from exc
        for group in groups:
            units.append(Unit(
                key=score_key(spec.name, group.name, scheme),
                dataset=spec.name,
                group=group.name,
                X=group.X,
                y=group.y,
            ))
    # Names are checked unique and group labels come back sorted-unique from the
    # built-in loader, so this can only fire for a loader that returned two groups
    # under one name. Checked anyway: the failure it prevents is silent (the
    # buffer would average two units into one key) rather than loud.
    duplicates = sorted(k for k, n in Counter(u.key for u in units).items() if n > 1)
    if duplicates:
        raise typer.BadParameter(
            f"two units resolved to the same score key {duplicates!r}; the buffer "
            "would average them into one. Name the datasets apart with --data NAME=path, "
            "or return distinct group names from the loader."
        )
    return units


def as_groups(units: Sequence[Unit]) -> list[tuple[str, np.ndarray, object]]:
    """The ``(label, X, y)`` triples ``fit.evaluate_body_grouped`` takes."""
    return [(u.key, u.X, u.y) for u in units]


def as_spec_units(units: Sequence[Unit]) -> list[tuple[str, str, np.ndarray, Any]]:
    """The ``(key, group, X, y)`` tuples ``spec_eval.evaluate_spec_grouped`` takes.

    The group travels beside the key rather than being parsed out of it, because
    the spec is handed the label the scientist's own group column carries while
    the key is Wheeler's (``A:c01`` versus ``c01``).
    """
    return [(u.key, u.group, u.X, u.y) for u in units]


def dataset_of(units: Sequence[Unit]) -> dict[str, str]:
    """key -> dataset name, so a progress ping can say which table it is on."""
    return {u.key: u.dataset for u in units}
