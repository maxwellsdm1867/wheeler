"""The conftest fixture is load-bearing: prove it, do not assert it.

`metrics.METRICS` and `loaders.LOADERS` are process-wide, and several tests here
register into them on purpose. If the fixture stopped restoring them, the suite
would not go red at the fixture: it would go red somewhere else, later, in a test
that depends on what ran before it. That is the failure this file rules out, and
the extraction of the importer into `_userland` is exactly the kind of change
that could break it silently (the registries now share one `_loaded_sources` set
that `metrics` only aliases).

So this is a CONTROL EXPERIMENT, not an assertion. It runs the same two-test
scenario twice in a subprocess: once with the real fixture, once with the
registry snapshot removed and everything else identical. The real fixture must
pass and the control must FAIL. A fixture that has quietly stopped working fails
the first run; a scenario that never leaked in the first place (and so proves
nothing) fails the second.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REAL_CONFTEST = (Path(__file__).parent / "conftest.py").read_text()

# The control: same scratch cwd, no registry snapshot. Everything else identical.
CONTROL_CONFTEST = '''
import pytest


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield
'''

# Runs FIRST (files are collected in sorted order): registers "leaky" into both
# registries from a project file, the way a scientist's own module would.
REGISTERS = '''
from pathlib import Path

from wheeler.integrations.llmsr import loaders as loaders_mod
from wheeler.integrations.llmsr import metrics as metrics_mod

SOURCE = """
from wheeler.integrations.llmsr.loaders import Loader, register_loader
from wheeler.integrations.llmsr.metrics import Metric, register_metric

register_metric(Metric(key="leaky", label="leaky", data_shape="regression",
                       lower_is_better=True, loss=lambda p, t: 0.0,
                       report=lambda p, t: 0.0))
register_loader(Loader(key="leaky", label="leaky", load=lambda request: []))
"""


def test_a_registers_a_user_metric_and_loader():
    Path(".wheeler/llmsr").mkdir(parents=True)
    Path(".wheeler/llmsr/metrics.py").write_text(SOURCE)
    assert metrics_mod.load_user_metrics() == []
    assert "leaky" in metrics_mod.available()
    assert "leaky" in loaders_mod.available()
'''

# Runs SECOND, in its own scratch cwd with no project file of its own. Under the
# real fixture it sees the built-ins only.
EXPECTS_CLEAN = '''
from wheeler.integrations.llmsr import loaders as loaders_mod
from wheeler.integrations.llmsr import metrics as metrics_mod


def test_b_sees_no_registration_from_the_previous_test():
    assert "leaky" not in metrics_mod.available()
    assert "leaky" not in loaders_mod.available()
'''


def _run_scenario(where: Path, conftest: str) -> subprocess.CompletedProcess:
    root = where.resolve()
    root.mkdir(parents=True)
    (root / "conftest.py").write_text(conftest)
    (root / "test_a_registers.py").write_text(REGISTERS)
    (root / "test_b_expects_clean.py").write_text(EXPECTS_CLEAN)
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(root), "-q", "-p", "no:cacheprovider"],
        cwd=str(root),
        capture_output=True,
        text=True,
        # The worktree, not the installed package: the fixture under test is the
        # one in this branch.
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )


class TestFixtureIsolatesTheRegistries:
    def test_with_the_real_fixture_nothing_leaks(self):
        result = _run_scenario(Path("isolated"), REAL_CONFTEST)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "2 passed" in result.stdout

    def test_control_without_the_snapshot_the_registration_leaks(self):
        """Removing only the snapshot must break it, or the test above proves nothing."""
        result = _run_scenario(Path("control"), CONTROL_CONFTEST)
        assert result.returncode != 0, result.stdout + result.stderr
        assert "test_b_sees_no_registration_from_the_previous_test" in result.stdout
