"""Hard constraints are accept/reject, evaluated apart from the scalar loss.

The candidate that scores BEST here is the one the guard throws out, which is the
whole point: a constraint is not a penalty term a good fit can pay its way past.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr.cli import llmsr_app

runner = CliRunner()

# A stand-in for the real thing: a candidate must not fit BELOW the measured
# noise floor, because a fit better than the noise is fitting the noise.
_NOISE_FLOOR = 0.5

_METRIC_SOURCE = f'''
import numpy as np

from wheeler.integrations.llmsr.metrics import Metric, register_metric, _mse


def above_noise_floor(y_pred, y_true, params):
    return _mse(y_pred, y_true) >= {_NOISE_FLOOR}


register_metric(Metric(
    key="mse_floor",
    label="mean squared error, floored",
    data_shape="regression",
    lower_is_better=True,
    loss=_mse,
    report=_mse,
    guard=above_noise_floor,
))
'''

# seed body is a constant model: it cannot reach the floor, so it is admissible
_SPEC = '''"""a linear law"""
import numpy as np

MAX_NPARAMS = 2


@evaluate.run
def evaluate(data: dict) -> float:
    return 0.0


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    """Predict y from x."""
    return params[0] + 0.0 * x
'''

# y = 3x exactly: the constant model scores 11.25, the true form scores 0
_DATA = "x,y\n1.0,3.0\n2.0,6.0\n3.0,9.0\n4.0,12.0\n"
_PERFECT = "    return params[0] * x"
_CONSTANT_MSE = 11.25


@pytest.fixture(autouse=True)
def _project(_isolated_registry):
    """The scratch project this file's tests run against. The temp cwd and the
    registry snapshot come from conftest; only the contents are local."""
    Path(".wheeler/llmsr").mkdir(parents=True)
    Path(".wheeler/llmsr/metrics.py").write_text(_METRIC_SOURCE)
    Path("spec.txt").write_text(_SPEC)
    Path("train.csv").write_text(_DATA)


def _out(result) -> dict:
    assert result.exit_code == 0, result.output
    return json.loads(result.output.strip().splitlines()[-1])


class TestGuardDeclaration:
    def test_callable_list_and_constraint_are_all_accepted(self):
        def ok(y_pred, y_true, params):
            return True

        named = metrics_mod.Constraint(name="named", check=ok)
        one = metrics_mod.Metric(
            key="one", label="one", data_shape="regression", lower_is_better=True,
            loss=metrics_mod._mse, report=metrics_mod._mse, guard=ok,
        )
        many = metrics_mod.Metric(
            key="many", label="many", data_shape="regression", lower_is_better=True,
            loss=metrics_mod._mse, report=metrics_mod._mse, guard=[ok, named],
        )
        assert [c.name for c in one.hard_constraints] == ["ok"]
        assert [c.name for c in many.hard_constraints] == ["ok", "named"]

    def test_non_callable_guard_is_rejected_at_declaration(self):
        with pytest.raises(TypeError, match="guard"):
            metrics_mod.Metric(
                key="bad", label="bad", data_shape="regression", lower_is_better=True,
                loss=metrics_mod._mse, report=metrics_mod._mse, guard="please reject me",
            )

    def test_no_guard_leaves_no_constraints(self):
        assert metrics_mod.MSE.hard_constraints == ()


class TestFitRejection:
    def _metric(self, check):
        return metrics_mod.Metric(
            key="guarded", label="guarded", data_shape="regression",
            lower_is_better=True, loss=metrics_mod._mse, report=metrics_mod._mse,
            guard=metrics_mod.Constraint(name="guard_under_test", check=check),
        )

    def _fit(self, metric):
        X = np.array([[1.0], [2.0], [3.0], [4.0]])
        y = np.array([3.0, 6.0, 9.0, 12.0])
        return fit_mod.evaluate_body(
            "def equation(x, params):\n    return params[0] * x\n",
            "equation", X, y, metric, max_nparams=1,
        )

    def test_violating_candidate_is_rejected_with_its_score_intact(self):
        result = self._fit(self._metric(lambda y_pred, y_true, params: False))
        assert result.valid is False
        assert result.rejection_reason == "constraint"
        assert "guard_under_test" in result.error
        # the value it scored is kept: the candidate fit WELL and was still refused
        assert result.value == pytest.approx(0.0, abs=1e-8)
        assert len(result.params) == 1

    def test_satisfying_candidate_is_untouched(self):
        result = self._fit(self._metric(lambda y_pred, y_true, params: True))
        assert result.valid is True
        assert result.rejection_reason == ""
        assert result.value == pytest.approx(0.0, abs=1e-8)

    def test_raising_constraint_rejects_rather_than_admits(self):
        def explodes(y_pred, y_true, params):
            raise RuntimeError("cannot decide")

        result = self._fit(self._metric(explodes))
        assert result.valid is False
        assert result.rejection_reason == "constraint"

    def test_numeric_failure_is_not_reported_as_a_constraint(self):
        result = fit_mod.evaluate_body(
            "def equation(x, params):\n    return nope * x\n",
            "equation", np.array([[1.0]]), np.array([3.0]), metrics_mod.MSE,
            max_nparams=1,
        )
        assert result.valid is False
        assert result.rejection_reason == "numeric"


class TestRunSummary:
    def _run(self, metric: str, run_id: str) -> str:
        _out(runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv",
            "--metric", metric, "--run-id", run_id,
        ]))
        rd = f".wheeler/llmsr/runs/{run_id}"
        p = _out(runner.invoke(llmsr_app, ["prompt", "--run", rd]))
        for name, body in (("perfect.py", _PERFECT), ("broken.py", "    return nope * x")):
            Path(name).write_text(body)
            self.last = _out(runner.invoke(llmsr_app, [
                "submit", "--run", rd, "--body-file", name,
                "--island-id", str(p["island_id"]),
                "--version-generated", str(p["version_generated"]),
            ]))
            if name == "perfect.py":
                self.perfect = self.last
        return rd

    def test_guarded_run_rejects_the_best_scoring_candidate(self):
        rd = self._run("mse_floor", "guarded")

        # the perfect fit was refused, and says so as a CONSTRAINT rejection
        assert self.perfect["valid"] is False
        assert self.perfect["rejection_reason"] == "constraint"
        assert self.perfect["value"] == pytest.approx(0.0, abs=1e-8)
        # the broken candidate is a different kind of failure
        assert self.last["rejection_reason"] == "numeric"

        summary = _out(runner.invoke(llmsr_app, ["best", "--run", rd]))
        assert summary["n_constraint_rejected"] == 1
        best = json.loads(Path(rd, "best.json").read_text())
        # the winner is the admissible constant model, NOT the perfect fit
        assert summary["value"] == pytest.approx(_CONSTANT_MSE)
        assert best["metrics"]["mse_train"] == pytest.approx(_CONSTANT_MSE)
        assert best["equation"].strip() == "return params[0] + 0.0 * x"
        assert best["n_valid"] == 1
        assert best["n_samples"] == 3
        assert best["n_constraint_rejected"] == 1

        heartbeat = json.loads(Path(rd, "heartbeat.json").read_text())
        assert heartbeat["n_constraint_rejected"] == 1
        assert heartbeat["n_failed"] == 1

    def test_run_without_constraints_is_unchanged(self):
        rd = self._run("mse", "plain")

        assert self.perfect["valid"] is True
        assert self.perfect["rejection_reason"] == ""

        summary = _out(runner.invoke(llmsr_app, ["best", "--run", rd]))
        assert summary["n_constraint_rejected"] == 0
        best = json.loads(Path(rd, "best.json").read_text())
        # with no guard the perfect fit wins, exactly as before
        assert summary["value"] == pytest.approx(0.0, abs=1e-8)
        assert best["metrics"]["mse_train"] == pytest.approx(0.0, abs=1e-8)
        assert best["equation"].strip() == _PERFECT.strip()
        assert best["n_constraint_rejected"] == 0
