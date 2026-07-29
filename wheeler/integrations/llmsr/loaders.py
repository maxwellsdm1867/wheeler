"""Pluggable data loaders: how a run's rows become the groups that get fitted.

The fit is per group and its validity is STRICT: a candidate is valid only if
EVERY group fitted (see ``fit.evaluate_body_grouped``). That is the right rule
for comparing FORMS, and it has a sharp consequence: one dead cell in a recording
rejects a correct law. So the question "which rows are even admissible" has to be
answerable BEFORE the fit sees them, and it is not a question Wheeler can answer.
Whether a cell is unhealthy, whether a trial was aborted, whether a sweep drifted,
is the scientist's call about their own data.

A loader is where that call lives. It reads whatever the recording actually is
(a CSV, a ``.mat`` file, a query against an epoch database) and returns the list
of ``Group`` the search will fit. Excluding a bad group is simply not returning
it, and adding a new file format is simply a new loader: neither requires editing
the installed package.

``csv`` ships built in and is the tabular LLM-SR convention, unchanged: the last
column is the target, the leading columns are the inputs, and ``--group-by`` names
a label column that is read separately and excluded from the inputs. It wraps
``data.py`` rather than restating those rules, so it cannot drift from them.

Any other loader is the scientist's own. Write it in your own module, call
``register_loader``, and point Wheeler at that module through
``$WHEELER_LLMSR_LOADERS`` or by putting it at ``.wheeler/llmsr/loaders.py`` in
the project: the same convention metrics use (see ``_userland``)::

    # .wheeler/llmsr/loaders.py
    import numpy as np
    from wheeler.integrations.llmsr.loaders import Loader, get_loader, register_loader

    def healthy_cells(request):
        # Start from the tabular convention, then drop the cells that failed QC.
        groups = get_loader("csv").load(request)
        return [g for g in groups if np.std(np.asarray(g.y, dtype=float)) > 1e-9]

    register_loader(Loader(
        key="healthy-cells",
        label="CSV, excluding flat cells",
        load=healthy_cells,
    ))

An excluded group is EXCLUDED, not marked: it never reaches the buffer, so the
per-group score vectors of two candidates stay comparable (the vendored island
model clusters forms by that vector, and it is only meaningful if every candidate
was scored on the same group set).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import numpy as np

from . import _userland

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Group:
    """One fittable unit: the rows that share a single set of fitted constants.

    ``name`` is the group label (a cell id, a trial id). It keys the per-group
    score vector, so it must be stable across candidates within a run. An
    ungrouped run is the one-group case and uses ``fit.UNGROUPED``.

    ``X`` is the input matrix, one row per observation and one column per input,
    in the order the equation's signature expects. ``cols`` names those columns
    in the same order, which is what lets a loader be checked against a spec and
    what a report needs to say which variable is which. It may be empty when the
    source has no column names to give.

    ``y`` is the target, and its shape is the metric's business: one value per row
    of ``X`` for ``regression``, a variable-length sequence of recorded event
    times for a simulator shape like ``spike_train``. The loader hands it over as
    the metric declared it; nothing here reinterprets it.

    ``meta`` is free-form provenance about this group: where it came from, what
    was dropped and why. Nothing in the fit path reads it. It exists so that a
    loader which EXCLUDES data can say so somewhere the scientist will find it,
    rather than silently returning a shorter list.
    """

    name: str
    X: np.ndarray
    y: Any
    cols: tuple[str, ...] = ()
    meta: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LoadRequest:
    """What a loader is asked for: the source, and how to read it.

    A single object rather than a positional signature, so a later slice can add
    a field (a second dataset, a split role) without breaking every loader a
    scientist has already written.

    ``metric`` is passed because the target's SHAPE is the metric's declaration:
    a ``regression`` metric wants one ``y`` per row, a ``spike_train`` metric
    wants recorded event times. ``options`` carries loader-specific knobs the
    engine knows nothing about.
    """

    path: str
    metric: Any
    group_by: str = ""
    options: Mapping[str, Any] = field(default_factory=dict)


LoaderFn = Callable[[LoadRequest], "list[Group]"]


@dataclass(frozen=True)
class Loader:
    """A named way of turning a source into groups.

    ``load(request) -> list[Group]``. Returning fewer groups than the source
    contains is the supported way to exclude bad data. Returning zero groups is
    an error the caller reports, not something to fit.
    """

    key: str
    label: str
    load: LoaderFn


# ------------------------------------------------------------------ built-ins

def _load_csv(request: LoadRequest) -> list[Group]:
    """The tabular LLM-SR convention, delegated to ``data.py`` so it cannot drift.

    Imported inside the function because ``data`` pulls in ``fit`` and ``metrics``:
    the registry itself stays importable by anything.
    """
    from . import data as data_mod

    X, y, labels = data_mod._load_data(request.path, request.metric, request.group_by)
    cols = data_mod.input_columns(request.path, request.group_by)
    return [
        Group(
            name=name,
            X=group_x,
            y=group_y,
            cols=cols,
            meta={"loader": "csv", "path": request.path, "group_by": request.group_by},
        )
        for name, group_x, group_y in data_mod._as_groups(X, y, labels)
    ]


CSV = Loader(
    key="csv",
    label="tabular CSV (last column is the target)",
    load=_load_csv,
)


# The loaders Wheeler ships. Never mutated: it is what `builtin` reports against,
# so a scientist can always tell their own loader from ours.
BUILTIN_LOADERS: dict[str, Loader] = {CSV.key: CSV}

# The live registry: the built-ins plus whatever `register_loader` has added.
LOADERS: dict[str, Loader] = dict(BUILTIN_LOADERS)

DEFAULT_LOADER = CSV.key

_REQUIRED_ATTRS = ("key", "label", "load")
_KIND = "loaders"
_USER_LOADERS_ENV = _userland.env_var(_KIND)
_PROJECT_LOADERS_FILE = _userland.project_file(_KIND)
LoaderSourceError = _userland.SourceError


def _normalize_key(key: object) -> str:
    return key.strip().lower() if isinstance(key, str) else ""


def register_loader(loader: Loader, *, replace: bool = False) -> Loader:
    """Register a scientist-supplied loader under its key and return it.

    Checked HERE, naming what is missing, so a half-built loader fails at
    declaration rather than at ``init`` time with an AttributeError.
    """
    missing = [attr for attr in _REQUIRED_ATTRS if not hasattr(loader, attr)]
    if missing:
        raise TypeError(
            f"invalid loader ({type(loader).__name__}): missing required "
            f"attribute(s) {', '.join(missing)}. A loader must declare "
            f"{', '.join(_REQUIRED_ATTRS)}."
        )
    key = _normalize_key(getattr(loader, "key", None))
    if not key:
        raise ValueError("invalid loader: 'key' must be a non-empty string")
    if not isinstance(loader, Loader):
        raise TypeError(
            f"invalid loader {key!r}: build it with "
            "wheeler.integrations.llmsr.loaders.Loader, so the engine can rely "
            "on the load(request) -> list[Group] contract"
        )
    if not callable(loader.load):
        raise TypeError(f"invalid loader {key!r}: 'load' must be callable")
    if key in LOADERS and not replace:
        origin = "built in" if key in BUILTIN_LOADERS else "already registered"
        raise ValueError(
            f"loader {key!r} is {origin}; pass replace=True to override it"
        )
    LOADERS[key] = loader
    logger.debug("registered loader %r (%s)", key, loader.label)
    return loader


def user_loader_sources() -> list[str]:
    """Where to look for the scientist's loader modules, in order."""
    return _userland.sources(_KIND)


def load_user_loaders() -> list[LoaderSourceError]:
    """Import the scientist's loader modules so their registrations take effect.

    Sources, in order: every entry of ``$WHEELER_LLMSR_LOADERS`` (separated by
    the path separator or by commas, each either an importable module path or a
    path to a .py file), then ``.wheeler/llmsr/loaders.py`` under the project.
    Each source is imported at most once per process. A source that raises is
    REPORTED, not raised: one broken file must not take down every verb.
    """
    return _userland.load(_KIND)


def get_loader(key: str) -> Loader:
    """Return the registered loader for ``key`` or raise with the available list."""
    normalized = _normalize_key(key)
    if normalized not in LOADERS:
        raise KeyError(
            f"unknown loader {key!r}; registered loaders: {sorted(LOADERS)}. "
            f"Register your own with loaders.register_loader() from a module "
            f"named in ${_USER_LOADERS_ENV} or from {_PROJECT_LOADERS_FILE}."
        )
    return LOADERS[normalized]


def available() -> list[str]:
    """Return the sorted keys of registered loaders (what the act may offer)."""
    return sorted(LOADERS)


def load_groups(
    path: str,
    metric: Any,
    *,
    group_by: str = "",
    loader: str = DEFAULT_LOADER,
    options: Mapping[str, Any] | None = None,
) -> list[Group]:
    """Resolve a loader by name and run it. The one call site the verbs need."""
    chosen = get_loader(loader)
    request = LoadRequest(
        path=path,
        metric=metric,
        group_by=group_by,
        options=dict(options or {}),
    )
    groups = chosen.load(request)
    if not groups:
        raise ValueError(
            f"loader {chosen.key!r} returned no groups for {path!r}; there is "
            "nothing to fit. If it excludes groups, every one was excluded."
        )
    return groups
