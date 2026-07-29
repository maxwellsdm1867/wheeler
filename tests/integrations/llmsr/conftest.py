"""Shared isolation for the LLM-SR tests.

The registries are process-wide and open: `load_user_metrics()` /
`load_user_loaders()` import whatever `$WHEELER_LLMSR_METRICS` /
`$WHEELER_LLMSR_LOADERS` or `.wheeler/llmsr/{metrics,loaders}.py` point at, and
register it for the rest of the process. Several of these tests write their own
metric or loader into a scratch project on purpose, so without a snapshot the
first such test would leak its registration into every test that ran after it,
and the order tests happen to run in would decide whether they pass.

Every test in this directory therefore runs in its own scratch cwd (run dirs and
`.wheeler/` are created relative to it) and leaves every registry exactly as it
found it.

`_userland._loaded_sources` is one set shared by all the registries: it records
which FILES have been executed, which is a property of the process rather than of
the registry that asked. Restoring it is what lets two tests point at the same
scratch path and both see their module actually imported.
"""

from __future__ import annotations

import pytest

from wheeler.integrations.llmsr import _userland
from wheeler.integrations.llmsr import loaders as loaders_mod
from wheeler.integrations.llmsr import metrics as metrics_mod

# Every open registry: (the live dict, the env var that feeds it).
_REGISTRIES = (
    (metrics_mod.METRICS, metrics_mod._USER_METRICS_ENV),
    (loaders_mod.LOADERS, loaders_mod._USER_LOADERS_ENV),
)


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    """Run in a scratch project and leave the process-wide registries as found."""
    monkeypatch.chdir(tmp_path)
    snapshots = [(live, dict(live)) for live, _env in _REGISTRIES]
    for _live, env in _REGISTRIES:
        monkeypatch.delenv(env, raising=False)
    loaded = set(_userland._loaded_sources)
    yield
    for live, before in snapshots:
        live.clear()
        live.update(before)
    _userland._loaded_sources.clear()
    _userland._loaded_sources.update(loaded)
