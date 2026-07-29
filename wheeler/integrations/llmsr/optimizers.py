"""Pluggable optimizers for the constant fit, with detect-and-escalate.

Which optimizer fits a candidate's free constants is a SCIENTIFIC choice, not an
implementation detail, because a fit that fails is indistinguishable from a form
that is WRONG. Under ``--group-by`` one failed group invalidates the whole
candidate (``fit.evaluate_body_grouped``, strict validity), so an optimizer that
cannot see a single cell's objective silently rejects a correct law.

That is not hypothetical. BFGS steers by a numerical gradient, and on a
piecewise-constant objective that gradient is identically zero: every start
returns exactly where it began and the reported best is merely whichever init
happened to sit lowest. Measured on a quantized objective, no BFGS start moved
off its ``x0`` and it reported a best of 1.0 where Nelder-Mead reached 0.0.

Hence ``auto``, the default: run BFGS from every start, and if NO start moved off
its init, rerun Nelder-Mead FROM THE SAME STARTS. That is detection, not a guess
from the declared data shape, so it repairs any non-smooth objective rather than
the hardcoded list of ones we happened to think of. The CONCRETE optimizer behind
the winning constants is recorded on the ``FitResult`` and lands in ``best.json``:
a number whose provenance is "we quietly fell back" is exactly what this project
exists to prevent.

An optimizer is ``(loss, x0) -> (x, fun)``, or ``None`` for "this start produced
nothing usable", which the caller skips exactly as it skips a start whose
optimizer raised. The multi-start loop itself is NOT here: it lives in
``fit._fit_one_group``, which owns the inits, the escalation decision, and the
selection rule.

``bfgs``, ``nelder-mead`` and ``powell`` ship built in. Any other optimizer is the
scientist's own and does NOT require editing the installed package: write an
``Optimizer`` in your own module, call ``register_optimizer`` on it, and point
Wheeler at that module through ``$WHEELER_LLMSR_OPTIMIZERS`` or by putting it at
``.wheeler/llmsr/optimizers.py`` in the project. ``load_user_optimizers()``
imports those sources before the CLI resolves an optimizer name::

    # .wheeler/llmsr/optimizers.py
    from scipy.optimize import differential_evolution
    from wheeler.integrations.llmsr.optimizers import Optimizer, register_optimizer

    def de(loss, x0):
        res = differential_evolution(loss, [(-20, 20)] * len(x0), seed=0)
        return res.x, res.fun

    register_optimizer(Optimizer(key="de", label="differential evolution", minimize=de))
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
from typing import Any, Callable

logger = logging.getLogger(__name__)

# (loss, x0) -> (x, fun) | None. `x` is the parameter vector the caller will read
# constants out of; `fun` is the objective there, which the caller compares across
# starts. Returning None means this start produced nothing usable.
Minimizer = Callable[..., Any]

# The default choice, and the reason this module exists. Not a registered
# optimizer: it is a STRATEGY over two of them, resolved by `resolve`.
AUTO = "auto"
AUTO_PRIMARY = "bfgs"
AUTO_ESCALATION = "nelder-mead"


@dataclass(frozen=True)
class Optimizer:
    """A named way to minimize one loss from one start.

    ``minimize(loss, x0)`` returns ``(x, fun)``, or ``None`` when this start
    produced nothing usable. It may also simply raise: the caller treats a raise
    and a ``None`` identically, by skipping that start, so an optimizer never has
    to defend itself against a pathological candidate body.

    ``escalates_to`` names an optimizer to retry FROM THE SAME STARTS when no
    start moved off its init. Escalation is one hop, never a chain: the fallback's
    own ``escalates_to`` is not followed, because a second failure to move is
    information about the objective, not an invitation to keep guessing.
    """

    key: str
    label: str
    minimize: Minimizer
    escalates_to: str = ""


def _bfgs(loss, x0):
    """scipy BFGS, called exactly as the fit has always called it.

    Bit-for-bit identical to the ``opt.minimize(loss, x0, method="BFGS")`` this
    replaced: same defaults, same result fields, no re-wrapping of either.
    """
    # Local import, in both senses: it keeps scipy out of the parent process's
    # import graph (the fit runs in a forked child), and it keeps this module
    # importable by the `optimizers` listing verb on an install without the extra.
    import scipy.optimize as opt

    res = opt.minimize(loss, x0, method="BFGS")
    return res.x, res.fun


def _nelder_mead(loss, x0):
    """scipy Nelder-Mead: derivative-free, so a flat gradient does not blind it."""
    import scipy.optimize as opt

    res = opt.minimize(loss, x0, method="Nelder-Mead")
    return res.x, res.fun


def _powell(loss, x0):
    """scipy Powell: derivative-free line searches along conjugate directions."""
    import scipy.optimize as opt

    res = opt.minimize(loss, x0, method="Powell")
    return res.x, res.fun


BFGS = Optimizer(
    key="bfgs",
    label="BFGS (quasi-Newton, numerical gradient)",
    minimize=_bfgs,
)

NELDER_MEAD = Optimizer(
    key="nelder-mead",
    label="Nelder-Mead (derivative-free simplex)",
    minimize=_nelder_mead,
)

POWELL = Optimizer(
    key="powell",
    label="Powell (derivative-free conjugate directions)",
    minimize=_powell,
)


# The three optimizers Wheeler ships. Never mutated: it is what `builtin` reports
# against, so a scientist can always tell their own optimizer from ours.
BUILTIN_OPTIMIZERS: dict[str, Optimizer] = {
    BFGS.key: BFGS,
    NELDER_MEAD.key: NELDER_MEAD,
    POWELL.key: POWELL,
}

# The live registry: the built-ins plus whatever `register_optimizer` has added.
OPTIMIZERS: dict[str, Optimizer] = dict(BUILTIN_OPTIMIZERS)

_REQUIRED_ATTRS = ("key", "label", "minimize")
_USER_OPTIMIZERS_ENV = "WHEELER_LLMSR_OPTIMIZERS"
_PROJECT_OPTIMIZERS_FILE = Path(".wheeler/llmsr/optimizers.py")


@dataclass(frozen=True)
class OptimizerSourceError:
    """A user optimizer module that failed to import, and why."""

    source: str
    error: str


_loaded_sources: set[str] = set()


def _normalize_key(key: object) -> str:
    return key.strip().lower() if isinstance(key, str) else ""


def register_optimizer(optimizer: Optimizer, *, replace: bool = False) -> Optimizer:
    """Register a scientist-supplied optimizer under its key and return it.

    Everything the fit path will touch is checked HERE, naming what is missing, so
    a half-built optimizer fails at declaration rather than as an AttributeError
    inside a fit worker an hour into a search.
    """
    missing = [attr for attr in _REQUIRED_ATTRS if not hasattr(optimizer, attr)]
    if missing:
        raise TypeError(
            f"invalid optimizer ({type(optimizer).__name__}): missing required "
            f"attribute(s) {', '.join(missing)}. An optimizer must declare "
            f"{', '.join(_REQUIRED_ATTRS)}."
        )
    key = _normalize_key(getattr(optimizer, "key", None))
    if not key:
        raise ValueError("invalid optimizer: 'key' must be a non-empty string")
    if not isinstance(optimizer, Optimizer):
        raise TypeError(
            f"invalid optimizer {key!r}: build it with "
            "wheeler.integrations.llmsr.optimizers.Optimizer, which the fit path "
            "reads the escalation rule off"
        )
    if key == AUTO:
        raise ValueError(
            f"{AUTO!r} is the escalation STRATEGY over "
            f"{AUTO_PRIMARY!r} and {AUTO_ESCALATION!r}, not an optimizer; "
            "register yours under its own name"
        )
    if not callable(optimizer.minimize):
        raise TypeError(f"invalid optimizer {key!r}: 'minimize' must be callable")
    if _normalize_key(optimizer.escalates_to) == key:
        raise ValueError(f"optimizer {key!r} escalates to itself")
    if key in OPTIMIZERS and not replace:
        origin = "built in" if key in BUILTIN_OPTIMIZERS else "already registered"
        raise ValueError(
            f"optimizer {key!r} is {origin}; pass replace=True to override it"
        )
    OPTIMIZERS[key] = optimizer
    logger.debug("registered optimizer %r (%s)", key, optimizer.label)
    return optimizer


def user_optimizer_sources() -> list[str]:
    """Where to look for the scientist's optimizer modules, in order."""
    raw = os.environ.get(_USER_OPTIMIZERS_ENV, "")
    sources = [
        part.strip()
        for chunk in raw.split(os.pathsep)
        for part in chunk.split(",")
        if part.strip()
    ]
    if _PROJECT_OPTIMIZERS_FILE.exists():
        sources.append(str(_PROJECT_OPTIMIZERS_FILE.resolve()))
    return sources


def _import_source(source: str) -> None:
    """Import one optimizer source: a .py path, or an importable module path."""
    # TODO(S5): delegate to the shared `_userland` importer once it lands; this is
    # deliberately the same shape as `metrics._import_source` so the two collapse
    # into one call with no behaviour change.
    if not source.endswith(".py"):
        importlib.import_module(source)
        return
    path = Path(source).resolve()
    if not path.exists():
        raise FileNotFoundError(f"no such optimizers file: {path}")
    name = "wheeler_llmsr_user_optimizers_" + hashlib.sha256(
        str(path).encode()
    ).hexdigest()[:8]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load optimizers from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # so the module behaves like any other import
    spec.loader.exec_module(module)


def load_user_optimizers() -> list[OptimizerSourceError]:
    """Import the scientist's optimizer modules so their registrations take effect.

    Sources, in order: every entry of ``$WHEELER_LLMSR_OPTIMIZERS`` (separated by
    the path separator or by commas, each either an importable module path or a
    path to a .py file), then ``.wheeler/llmsr/optimizers.py`` under the project.
    Each source is imported at most once per process. A source that raises is
    REPORTED, not raised: one broken file must not take down every verb.
    """
    failures: list[OptimizerSourceError] = []
    for source in user_optimizer_sources():
        if source in _loaded_sources:
            continue
        _loaded_sources.add(source)
        try:
            _import_source(source)
        except Exception as exc:
            logger.error("could not load optimizers from %s: %s", source, exc)
            failures.append(
                OptimizerSourceError(source=source, error=f"{type(exc).__name__}: {exc}")
            )
    return failures


def get_optimizer(key: str) -> Optimizer:
    """Return the registered optimizer for ``key`` or raise with the valid list.

    ``auto`` is NOT resolvable here: it is a strategy over two optimizers and has
    no per-start ``minimize`` of its own. ``resolve`` is what accepts it.
    """
    normalized = _normalize_key(key)
    if normalized not in OPTIMIZERS:
        raise KeyError(
            f"unknown optimizer {key!r}; valid choices: {list(choices())}. "
            f"Register your own with optimizers.register_optimizer() from a module "
            f"named in ${_USER_OPTIMIZERS_ENV} or from {_PROJECT_OPTIMIZERS_FILE}."
        )
    return OPTIMIZERS[normalized]


def resolve(key: str) -> tuple[Optimizer, Optimizer | None]:
    """Resolve a declared choice into ``(primary, escalation)``.

    The escalation is the optimizer to rerun from the SAME starts when no start
    moved off its init, or ``None`` when the choice declares no fallback. ``auto``
    is the one choice that is not itself an optimizer: it resolves to BFGS with
    Nelder-Mead behind it, which is why a run that escalates reports the concrete
    ``nelder-mead`` rather than the strategy that picked it.
    """
    if _normalize_key(key) == AUTO:
        return get_optimizer(AUTO_PRIMARY), get_optimizer(AUTO_ESCALATION)
    primary = get_optimizer(key)
    if not primary.escalates_to:
        return primary, None
    return primary, get_optimizer(primary.escalates_to)


def canonical(key: str) -> str:
    """The canonical form of a declared choice, having checked it resolves."""
    resolve(key)
    return _normalize_key(key)


def available() -> list[str]:
    """Return the sorted keys of registered optimizers (concrete ones only)."""
    return sorted(OPTIMIZERS)


def choices() -> list[str]:
    """Every value ``--optimizer`` accepts: the strategy plus the registered ones."""
    return [AUTO, *available()]
