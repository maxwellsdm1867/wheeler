"""One importer for every open registry in the LLM-SR engine.

Metrics, loaders and optimizers are all OPEN: the scientist's own objective, own
way of reading a recording, own minimizer, must be selectable by name without
editing the installed package. That needs exactly one mechanism, not one per
registry, so this module owns it and each registry is a thin caller.

The convention, for a registry of kind ``k``:

* ``$WHEELER_LLMSR_<K>`` names sources to import, separated by the path separator
  or by commas. Each entry is either an importable module path or a path to a
  ``.py`` file.
* ``.wheeler/llmsr/<k>.py`` under the project is imported after those, if present.

So ``$WHEELER_LLMSR_METRICS`` + ``.wheeler/llmsr/metrics.py`` for metrics (the
convention that already shipped, unchanged), ``$WHEELER_LLMSR_LOADERS`` +
``.wheeler/llmsr/loaders.py`` for loaders, and so on. A scientist who learns it
once knows it everywhere.

Importing is what makes a registration take effect: the module body calls
``register_metric`` / ``register_loader`` at import time. Two rules follow.
A source is imported at most ONCE per process, tracked in ``_loaded_sources``,
so naming the same file from two registries runs it once and both registrations
land. And a source that raises is REPORTED, not raised: one broken file must not
take down every verb, so ``load()`` returns the failures and the caller decides
how loudly to say so.
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

logger = logging.getLogger(__name__)

ENV_PREFIX = "WHEELER_LLMSR_"
PROJECT_DIR = Path(".wheeler/llmsr")


@dataclass(frozen=True)
class SourceError:
    """A user module that failed to import, and why."""

    source: str
    error: str


# Every source imported so far, across every registry. Shared on purpose: the
# unit is "this file has been executed", which is a property of the process, not
# of the registry that asked for it.
#
# Registries alias this set by name (``metrics._loaded_sources`` is this object),
# and the test fixture snapshots it through those aliases. Mutate it in place;
# never rebind it, or the aliases go stale.
_loaded_sources: set[str] = set()


def env_var(kind: str) -> str:
    """The environment variable naming user sources for a registry kind."""
    return ENV_PREFIX + kind.upper()


def project_file(kind: str) -> Path:
    """The in-project file imported for a registry kind, if it exists."""
    return PROJECT_DIR / f"{kind}.py"


def sources(kind: str) -> list[str]:
    """Where to look for the scientist's modules of this kind, in order."""
    raw = os.environ.get(env_var(kind), "")
    found = [
        part.strip()
        for chunk in raw.split(os.pathsep)
        for part in chunk.split(",")
        if part.strip()
    ]
    path = project_file(kind)
    if path.exists():
        found.append(str(path.resolve()))
    return found


def _import_source(source: str) -> None:
    """Import one source: a .py path, or an importable module path."""
    if not source.endswith(".py"):
        importlib.import_module(source)
        return
    path = Path(source).resolve()
    if not path.exists():
        raise FileNotFoundError(f"no such file: {path}")
    name = "wheeler_llmsr_user_" + hashlib.sha256(str(path).encode()).hexdigest()[:8]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # so the module behaves like any other import
    spec.loader.exec_module(module)


def load(kind: str) -> list[SourceError]:
    """Import the scientist's modules of this kind so registrations take effect.

    Called before a name is resolved, so an upgrade never drops the scientist's
    own metric, loader or optimizer. Returns the sources that failed, in order.
    """
    failures: list[SourceError] = []
    for source in sources(kind):
        if source in _loaded_sources:
            continue
        _loaded_sources.add(source)
        try:
            _import_source(source)
        except Exception as exc:
            logger.error("could not load %s from %s: %s", kind, source, exc)
            failures.append(
                SourceError(source=source, error=f"{type(exc).__name__}: {exc}")
            )
    return failures
