"""Shared isolation for the LLM-SR tests.

The metric registry is process-wide and open: `load_user_metrics()` imports
whatever `$WHEELER_LLMSR_METRICS` or `.wheeler/llmsr/metrics.py` points at and
registers it for the rest of the process. Several of these tests write their own
metric into a scratch project on purpose, so without a snapshot the first such
test would leak its metric into every test that ran after it, and the order tests
happen to run in would decide whether they pass.

Every test in this directory therefore runs in its own scratch cwd (run dirs and
`.wheeler/` are created relative to it) and leaves the registry exactly as it
found it.
"""

from __future__ import annotations

import pytest

from wheeler.integrations.llmsr import metrics as metrics_mod


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    """Run in a scratch project and leave the process-wide registry as found."""
    monkeypatch.chdir(tmp_path)
    registry = dict(metrics_mod.METRICS)
    loaded = set(metrics_mod._loaded_sources)
    monkeypatch.delenv(metrics_mod._USER_METRICS_ENV, raising=False)
    yield
    metrics_mod.METRICS.clear()
    metrics_mod.METRICS.update(registry)
    metrics_mod._loaded_sources.clear()
    metrics_mod._loaded_sources.update(loaded)
