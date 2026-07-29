"""Shared isolation for the LLM-SR tests.

The metric and optimizer registries are process-wide and open: `load_user_*()`
imports whatever `$WHEELER_LLMSR_METRICS` / `$WHEELER_LLMSR_OPTIMIZERS` or
`.wheeler/llmsr/{metrics,optimizers}.py` points at and registers it for the rest
of the process. Several of these tests write their own metric or optimizer into a
scratch project on purpose, so without a snapshot the first such test would leak
its registration into every test that ran after it, and the order tests happen to
run in would decide whether they pass.

Every test in this directory therefore runs in its own scratch cwd (run dirs and
`.wheeler/` are created relative to it) and leaves both registries exactly as it
found them.
"""

from __future__ import annotations

import pytest

from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr import optimizers as optimizers_mod


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    """Run in a scratch project and leave the process-wide registries as found."""
    monkeypatch.chdir(tmp_path)
    registries = [
        (metrics_mod.METRICS, dict(metrics_mod.METRICS),
         metrics_mod._loaded_sources, set(metrics_mod._loaded_sources)),
        (optimizers_mod.OPTIMIZERS, dict(optimizers_mod.OPTIMIZERS),
         optimizers_mod._loaded_sources, set(optimizers_mod._loaded_sources)),
    ]
    monkeypatch.delenv(metrics_mod._USER_METRICS_ENV, raising=False)
    monkeypatch.delenv(optimizers_mod._USER_OPTIMIZERS_ENV, raising=False)
    yield
    for live, snapshot, loaded, loaded_snapshot in registries:
        live.clear()
        live.update(snapshot)
        loaded.clear()
        loaded.update(loaded_snapshot)
