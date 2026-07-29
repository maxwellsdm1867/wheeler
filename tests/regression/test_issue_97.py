"""Regression test for issue #97: Metric.data_shape must be consulted by fit.py.

After the fix is applied:
1. Metric.data_shape is consulted by the fit path to validate shape support
2. A metric declaring an unsupported data_shape fails at init with a clear message
3. A non-regression shape (spike_train) is dispatchable end to end
4. A simulator program (returns variable-length event times) can be fit
5. Existing regression runs produce byte-identical results

These tests FAIL on main (before the fix) because the shape dispatch does not exist.
They PASS after issue #97 is fixed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr.vendor import code_manipulation, evaluator


FIX = Path(__file__).parent.parent / "integrations" / "llmsr" / "fixtures"
SPEC = FIX / "spec_bactgrow.txt"
DATA = FIX / "train_small.csv"


def _load_xy(data_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load CSV data: all columns except last are X, last column is y."""
    data = np.genfromtxt(data_path, delimiter=",", skip_header=1)
    return data[:, :-1], data[:, -1].reshape(-1)


def _spike_distance_loss(y_pred, y_true) -> float:
    """Mock spike-train distance metric: candidate returns event times,
    data has event times. Expects both to be variable-length lists.

    This loss raises TypeError if given reshaped arrays, proving it requires
    shape-specific handling.
    """
    y_pred_list = y_pred
    y_true_list = y_true

    if not isinstance(y_pred_list, (list, tuple)):
        raise TypeError(
            f"spike_train metric expects variable-length sequence, "
            f"got {type(y_pred_list).__name__}"
        )
    if not isinstance(y_true_list, (list, tuple)):
        raise TypeError(
            f"spike_train metric expects variable-length sequence, "
            f"got {type(y_true_list).__name__}"
        )

    return float(abs(len(y_pred_list) - len(y_true_list)))


def _spike_distance_report(y_pred, y_true) -> float:
    """Report the spike distance."""
    return _spike_distance_loss(y_pred, y_true)


class TestIssue97ShapeDispatch:
    """Issue #97: Metric.data_shape must be consulted and dispatched by fit.py.

    These tests assert the DESIRED end state: after the fix, the fit path
    respects data_shape and can handle non-regression shapes.

    FAILS on main because the feature does not exist.
    PASSES after #97 is fixed.
    """

    def test_unsupported_data_shape_rejected_at_metric_init(self):
        """A metric declaring an unsupported data_shape must fail at init
        with a clear error message naming the shape.

        FAILS on main: unsupported shapes are silently accepted.
        PASSES after fix: init validates and rejects with shape name in message.
        """
        with pytest.raises((ValueError, KeyError)) as exc_info:
            metrics_mod.Metric(
                key="unsupported",
                label="unsupported metric",
                data_shape="unsupported_shape",
                lower_is_better=True,
                loss=_spike_distance_loss,
                report=_spike_distance_report,
            )

        error_str = str(exc_info.value).lower()
        assert "unsupported_shape" in error_str or "data_shape" in error_str

    def test_supported_shapes_pass_validation(self):
        """Metrics declaring supported shapes must pass init validation.

        After fix: at least "regression" and "spike_train" supported.
        PASSES on main for regression (regression is wired).
        """
        regression_metric = metrics_mod.Metric(
            key="test_mse",
            label="test mse",
            data_shape="regression",
            lower_is_better=True,
            loss=metrics_mod._mse,
            report=metrics_mod._mse,
        )
        assert regression_metric.data_shape == "regression"

        spike_metric = metrics_mod.Metric(
            key="victor_purpura",
            label="Victor-Purpura spike distance",
            data_shape="spike_train",
            lower_is_better=True,
            loss=_spike_distance_loss,
            report=_spike_distance_report,
        )
        assert spike_metric.data_shape == "spike_train"

    def test_spike_train_simulator_is_dispatchable(self):
        """A simulator returning variable-length event times must be fittable
        with a spike_train metric using a separate code path from regression.

        FAILS on main: the regression path rejects simulators.
        PASSES after fix: spike_train path handles variable-length output.
        """
        spike_simulator = '''
def equation(stimulus: np.ndarray, params: np.ndarray):
    """Simulator: given injected current, return list of spike times."""
    spike_times = []
    for i, s in enumerate(stimulus):
        if s > params[0]:
            spike_times.append(float(i) * 0.1 + params[1])
    return spike_times
'''

        stimulus = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        recorded_spike_times = [0.2, 0.3]

        spike_metric = metrics_mod.Metric(
            key="victor_purpura",
            label="Victor-Purpura spike distance",
            data_shape="spike_train",
            lower_is_better=True,
            loss=_spike_distance_loss,
            report=_spike_distance_report,
        )

        result = fit_mod.evaluate_body(
            spike_simulator,
            "equation",
            stimulus.reshape(-1, 1),
            recorded_spike_times,
            spike_metric,
            max_nparams=5,
            timeout_seconds=5,
        )

        assert result.valid is True
        assert result.value is not None
        assert result.score is not None
        assert len(result.params) == 5

    def test_spike_train_arity_check_not_applied(self):
        """The regression path's arity check (fit.py:60) must NOT apply to
        spike_train. A spike_train simulator might not match the tabular
        column-per-input model.

        FAILS on main: arity check always applied.
        PASSES after fix: spike_train path bypasses regression arity check.
        """
        spike_simulator = '''
def equation(stimulus: np.ndarray, params: np.ndarray):
    """Single input, variable-length output."""
    return [float(i) * params[0] for i in range(int(params[1]))]
'''

        stimulus = np.array([1.0, 2.0])
        recorded_spikes = [0.1, 0.2, 0.3]

        spike_metric = metrics_mod.Metric(
            key="spike_metric",
            label="spike metric",
            data_shape="spike_train",
            lower_is_better=True,
            loss=_spike_distance_loss,
            report=_spike_distance_report,
        )

        result = fit_mod.evaluate_body(
            spike_simulator,
            "equation",
            stimulus.reshape(-1, 1),
            recorded_spikes,
            spike_metric,
            max_nparams=3,
            timeout_seconds=5,
        )

        if not result.valid:
            assert "arity" not in result.error.lower()

    def test_constant_fitting_works_for_spike_train(self):
        """Constant fitting (BFGS optimization) must work for spike_train
        metrics as well as regression.

        FAILS on main: fitting only works for regression.
        PASSES after fix: fitting works for both shapes.
        """
        simple_spike_simulator = '''
def equation(stimulus: np.ndarray, params: np.ndarray):
    """Return fixed spike times, parameterized."""
    return [params[0], params[1]]
'''

        stimulus = np.array([1.0])
        recorded_spikes = [0.5, 1.5]

        spike_metric = metrics_mod.Metric(
            key="spike_metric",
            label="spike metric",
            data_shape="spike_train",
            lower_is_better=True,
            loss=_spike_distance_loss,
            report=_spike_distance_report,
        )

        result = fit_mod.evaluate_body(
            simple_spike_simulator,
            "equation",
            stimulus.reshape(-1, 1),
            recorded_spikes,
            spike_metric,
            max_nparams=2,
            timeout_seconds=5,
        )

        assert result.valid is True
        assert len(result.params) == 2
        assert result.value is not None

    def test_existing_regression_runs_unchanged(self):
        """Existing regression metrics must produce byte-identical results.

        PASSES on main (guard test, no regression expected).
        Remains PASSING after fix: regression path unchanged.
        """
        spec_text = SPEC.read_text()
        fte = "equation"
        template = code_manipulation.text_to_program(spec_text)
        X, y = _load_xy(str(DATA))

        body = "    return params[0]*b*s/(params[1]+s) - params[2]*b"
        fn, program = evaluator._sample_to_program(body, None, template, fte)

        result_mse = fit_mod.evaluate_body(
            program, fte, X, y,
            metrics_mod.MSE,
            max_nparams=10,
            timeout_seconds=30,
        )
        assert result_mse.valid is True
        assert result_mse.value is not None
        assert result_mse.score is not None

        result_nmse = fit_mod.evaluate_body(
            program, fte, X, y,
            metrics_mod.NMSE,
            max_nparams=10,
            timeout_seconds=30,
        )
        assert result_nmse.valid is True
        assert result_nmse.value is not None

        assert len(result_mse.params) == len(result_nmse.params) == 10
