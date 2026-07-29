"""The metric registry is open: a scientist's own objective, from outside the
installed package, is selectable by name.

No live model and no Neo4j: the user metric is written to a file in a tmp project
and picked up the way a real one would be.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr.cli import llmsr_app

FIX = Path(__file__).parent / "fixtures"
SPEC = FIX / "spec_bactgrow.txt"
DATA = FIX / "train_small.csv"

runner = CliRunner()

_HUBER_SOURCE = '''
import numpy as np

from wheeler.integrations.llmsr.metrics import Metric, register_metric


def huber(y_pred, y_true, delta=1.0):
    r = np.abs(np.asarray(y_pred, dtype=float).reshape(-1)
               - np.asarray(y_true, dtype=float).reshape(-1))
    return float(np.mean(np.where(r <= delta, 0.5 * r ** 2, delta * (r - 0.5 * delta))))


register_metric(Metric(
    key="huber",
    label="Huber loss (robust regression)",
    data_shape="regression",
    lower_is_better=True,
    loss=huber,
    report=huber,
))
'''


def _write_project_metrics(text: str = _HUBER_SOURCE) -> Path:
    path = Path(".wheeler/llmsr/metrics.py")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestProjectMetricsFile:
    def test_project_file_metric_is_listed_and_runnable(self):
        _write_project_metrics()

        res = runner.invoke(llmsr_app, ["metrics"])
        assert res.exit_code == 0, res.output
        listing = json.loads(res.output)
        by_key = {m["key"]: m for m in listing["metrics"]}
        assert by_key["huber"]["builtin"] is False
        assert by_key["mse"]["builtin"] is True
        assert listing["errors"] == []

        res = runner.invoke(llmsr_app, [
            "init", "--spec", str(SPEC), "--data", str(DATA),
            "--metric", "huber", "--run-id", "h",
        ])
        assert res.exit_code == 0, res.output
        out = json.loads(res.output.strip().splitlines()[-1])
        assert out["metric"] == "huber"
        assert out["seed_valid"] is True
        assert isinstance(out["seed_value"], float)

    def test_env_var_source_is_loaded(self, monkeypatch):
        path = Path("my_metrics.py").resolve()
        path.write_text(_HUBER_SOURCE)
        monkeypatch.setenv(metrics_mod._USER_METRICS_ENV, str(path))

        metrics_mod.load_user_metrics()
        assert metrics_mod.get_metric("huber").lower_is_better is True
        assert "huber" in metrics_mod.available()

    def test_broken_source_is_reported_not_raised(self):
        _write_project_metrics("raise RuntimeError('boom')\n")

        failures = metrics_mod.load_user_metrics()
        assert len(failures) == 1
        assert "boom" in failures[0].error

        res = runner.invoke(llmsr_app, ["metrics"])
        assert res.exit_code == 0, res.output
        # already imported once in this process, so the listing reports no new
        # failure; the built-ins are still intact and every verb still works
        assert {m["key"] for m in json.loads(res.output)["metrics"]} == {"mse", "nmse"}


class TestRegistration:
    def test_builtin_is_not_silently_shadowed(self):
        clone = metrics_mod.Metric(
            key="mse", label="not the real mse", data_shape="regression",
            lower_is_better=True, loss=metrics_mod._mse, report=metrics_mod._mse,
        )
        with pytest.raises(ValueError, match="built in"):
            metrics_mod.register_metric(clone)
        assert metrics_mod.get_metric("mse") is metrics_mod.MSE
        metrics_mod.register_metric(clone, replace=True)
        assert metrics_mod.get_metric("mse") is clone

    def test_uncallable_loss_is_rejected_at_registration(self):
        broken = metrics_mod.Metric(
            key="broken", label="broken", data_shape="regression",
            lower_is_better=True, loss="not a function", report=metrics_mod._mse,
        )
        with pytest.raises(TypeError, match="loss"):
            metrics_mod.register_metric(broken)
        assert "broken" not in metrics_mod.available()
