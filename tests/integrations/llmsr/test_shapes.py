"""A non-regression data shape runs end to end through the CLI verbs.

The candidate is a SIMULATOR: it returns a variable-length sequence of event
times, scored against a recorded sequence of a different length. No live model
and no Neo4j: the metric is the scientist's own, loaded from the project the way
a real one would be.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr.cli import _load_data, llmsr_app

runner = CliRunner()

_SPIKE_METRIC_SOURCE = '''
from wheeler.integrations.llmsr.metrics import Metric, register_metric


def spike_count_distance(y_pred, y_true):
    """A stand-in for a real spike distance: both sides stay variable length."""
    if not isinstance(y_pred, (list, tuple)):
        raise TypeError(f"expected a sequence of event times, got {type(y_pred).__name__}")
    if not isinstance(y_true, (list, tuple)):
        raise TypeError(f"expected recorded event times, got {type(y_true).__name__}")
    return float(abs(len(y_pred) - len(y_true)))


register_metric(Metric(
    key="spike_count",
    label="spike count distance",
    data_shape="spike_train",
    lower_is_better=True,
    loss=spike_count_distance,
    report=spike_count_distance,
))
'''

_SPIKE_SPEC = '''"""Spike times produced by an injected current."""
import numpy as np

MAX_NPARAMS = 2


@evaluate.run
def evaluate(data: dict) -> float:
    return 0.0


@equation.evolve
def equation(stim: np.ndarray, params: np.ndarray):
    """Simulate the spike times the injected current produces."""
    return [float(i) * params[0] for i, s in enumerate(stim) if s > params[1]]
'''

# 5 stimulus samples, 2 recorded events: the sequences are NOT the same length
_SPIKE_DATA = "stim,events\n0.0,0.2\n1.0,0.35\n2.0,\n3.0,\n4.0,\n"


@pytest.fixture(autouse=True)
def _project(tmp_path, monkeypatch):
    """A scratch project carrying the scientist's metric; registry left as found."""
    monkeypatch.chdir(tmp_path)
    registry = dict(metrics_mod.METRICS)
    loaded = set(metrics_mod._loaded_sources)
    monkeypatch.delenv(metrics_mod._USER_METRICS_ENV, raising=False)
    Path(".wheeler/llmsr").mkdir(parents=True)
    Path(".wheeler/llmsr/metrics.py").write_text(_SPIKE_METRIC_SOURCE)
    Path("spec.txt").write_text(_SPIKE_SPEC)
    Path("train.csv").write_text(_SPIKE_DATA)
    yield
    metrics_mod.METRICS.clear()
    metrics_mod.METRICS.update(registry)
    metrics_mod._loaded_sources.clear()
    metrics_mod._loaded_sources.update(loaded)


def _out(result) -> dict:
    assert result.exit_code == 0, result.output
    return json.loads(result.output.strip().splitlines()[-1])


class TestSpikeTrainLoading:
    def test_event_column_is_read_as_padded(self):
        metrics_mod.load_user_metrics()
        metric = metrics_mod.get_metric("spike_count")
        X, y, _ = _load_data("train.csv", metric)
        assert X.shape == (5, 1)
        assert y == [0.2, 0.35]  # shorter than the stimulus, and a plain sequence

    def test_regression_loading_is_untouched(self):
        X, y, _ = _load_data("train.csv", metrics_mod.MSE)
        assert X.shape == (5, 1)
        assert isinstance(y, np.ndarray) and len(y) == 5


class TestSpikeTrainRun:
    def test_simulator_run_end_to_end(self):
        m = _out(runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv",
            "--metric", "spike_count", "--run-id", "s",
        ]))
        assert m["metric"] == "spike_count"
        assert m["seed_valid"] is True
        assert isinstance(m["seed_value"], float)

        rd = ".wheeler/llmsr/runs/s"
        p = _out(runner.invoke(llmsr_app, ["prompt", "--run", rd]))

        # a candidate emitting the right number of events scores 0
        Path("good.py").write_text("    return [params[0], params[1]]")
        good = _out(runner.invoke(llmsr_app, [
            "submit", "--run", rd, "--body-file", "good.py",
            "--island-id", str(p["island_id"]),
            "--version-generated", str(p["version_generated"]),
        ]))
        assert good["valid"] is True
        assert good["value"] == 0.0

        # one emitting too many scores worse, and is not the winner
        Path("long.py").write_text("    return [params[0], params[1], 9.0]")
        worse = _out(runner.invoke(llmsr_app, [
            "submit", "--run", rd, "--body-file", "long.py",
            "--island-id", str(p["island_id"]),
            "--version-generated", str(p["version_generated"]),
        ]))
        assert worse["valid"] is True
        assert worse["value"] == 1.0

        _out(runner.invoke(llmsr_app, ["best", "--run", rd]))
        best = json.loads(Path(rd, "best.json").read_text())
        assert best["status"] == "completed"
        assert best["metric"] == "spike_count"
        assert best["equation"].strip() == "return [params[0], params[1]]"
        assert len(best["params"]) == 2
        # the run's own metric is reported, not mse/nmse (meaningless here)
        assert best["metrics"]["spike_count_train"] == 0.0
        assert not any(k.startswith(("mse_", "nmse_")) for k in best["metrics"])
        assert "n_events" in best["program"]

    def test_simulator_ignoring_the_stimulus_is_still_fittable(self):
        """A free-running generator declares no stimulus input at all, which the
        tabular arity rule would have rejected outright."""
        Path("spec.txt").write_text(_SPIKE_SPEC.replace(
            "def equation(stim: np.ndarray, params: np.ndarray):",
            "def equation(params: np.ndarray):",
        ).replace(
            "return [float(i) * params[0] for i, s in enumerate(stim) if s > params[1]]",
            "return [params[0], params[1]]",
        ))
        m = _out(runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv",
            "--metric", "spike_count", "--run-id", "free",
        ]))
        assert m["seed_valid"] is True
        assert m["seed_value"] == 0.0
