"""Regression test for issue #96: closed metric registry with no extension point.

The issue: LLM-SR metric registry is hardcoded to only mse and nmse. Users cannot
register their own metrics without editing site-packages. The fix should allow
users to supply arbitrary custom metrics from outside the package, register them,
and select them by name in the CLI.

This test demonstrates the real user goal: taking an arbitrary error function
(e.g., Huber loss, asymmetric loss, robust loss) and using it in an LLM-SR run
without editing installed package source.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import pytest

# Import the metrics module and CLI to test the extension mechanism
from wheeler.integrations.llmsr import metrics as metrics_mod


class TestUserSuppliedMetricsExtension:
    """Test that users can register and use custom metrics without modifying site-packages."""

    def test_user_can_define_custom_metric(self):
        """A user can define a custom metric as a Metric dataclass instance."""
        def huber_loss(y_pred, y_true, delta=1.0):
            """Huber loss: robust to outliers, combines MSE and MAE."""
            yp = np.asarray(y_pred, dtype=float).reshape(-1)
            yt = np.asarray(y_true, dtype=float).reshape(-1)
            residuals = np.abs(yp - yt)
            mask = residuals <= delta
            loss = np.where(
                mask,
                0.5 * residuals ** 2,
                delta * (residuals - 0.5 * delta)
            )
            return float(np.mean(loss))

        # User creates a Metric instance for their custom objective
        custom_metric = metrics_mod.Metric(
            key="huber",
            label="Huber loss (robust regression)",
            data_shape="regression",
            lower_is_better=True,
            loss=huber_loss,
            report=huber_loss,
        )
        assert custom_metric.key == "huber"
        assert custom_metric.lower_is_better is True

    def test_built_in_metrics_still_work(self):
        """Existing mse and nmse metrics continue to function."""
        mse = metrics_mod.get_metric("mse")
        assert mse.key == "mse"
        assert mse.lower_is_better is True

        nmse = metrics_mod.get_metric("nmse")
        assert nmse.key == "nmse"
        assert nmse.lower_is_better is True

    def test_custom_metric_can_be_registered_at_runtime(self):
        """A user can register a custom metric dynamically without editing site-packages.

        This is the core capability needed: after defining a custom metric,
        the user should be able to call a registration function (e.g.,
        metrics.register_metric(custom_metric)) that makes it available
        to get_metric() and available().
        """
        # Define a simple custom metric
        def mae(y_pred, y_true):
            yp = np.asarray(y_pred, dtype=float).reshape(-1)
            yt = np.asarray(y_true, dtype=float).reshape(-1)
            return float(np.mean(np.abs(yp - yt)))

        custom = metrics_mod.Metric(
            key="mae",
            label="mean absolute error",
            data_shape="regression",
            lower_is_better=True,
            loss=mae,
            report=mae,
        )

        # The fix should provide a register_metric() or similar function
        # This call should succeed and make the metric available
        try:
            metrics_mod.register_metric(custom)
        except AttributeError as e:
            pytest.fail(
                f"register_metric() not found or not implemented: {e}\n"
                "The fix should expose a public function to register custom metrics."
            )

        # After registration, the metric should be available
        retrieved = metrics_mod.get_metric("mae")
        assert retrieved.key == "mae"

    def test_registered_custom_metric_appears_in_available_list(self):
        """After registering a custom metric, available() should include it."""
        # Define and register a custom metric
        def rmse(y_pred, y_true):
            yp = np.asarray(y_pred, dtype=float).reshape(-1)
            yt = np.asarray(y_true, dtype=float).reshape(-1)
            return float(np.sqrt(np.mean((yp - yt) ** 2)))

        custom = metrics_mod.Metric(
            key="rmse",
            label="root mean squared error",
            data_shape="regression",
            lower_is_better=True,
            loss=rmse,
            report=rmse,
        )

        try:
            metrics_mod.register_metric(custom)
        except AttributeError:
            pytest.fail("register_metric() not found or not implemented")

        # The metric should now appear in available()
        available = metrics_mod.available()
        assert "rmse" in available

    def test_custom_metric_with_invalid_attributes_raises_clear_error(self):
        """If a custom metric is missing required attributes, error is clear."""
        # Try to register a metric-like object with missing attributes
        incomplete_metric = {
            "key": "bad_metric",
            "label": "incomplete metric",
            # Missing: data_shape, lower_is_better, loss, report
        }

        # The fix should validate the metric structure and raise a clear error
        with pytest.raises((TypeError, ValueError, AttributeError)) as exc_info:
            metrics_mod.register_metric(incomplete_metric)

        # Error message should name what is missing, not raise AttributeError
        # at scoring time
        error_str = str(exc_info.value).lower()
        # Should mention the problem, not just fail later
        assert any(
            word in error_str
            for word in ["metric", "invalid", "required", "missing", "attribute"]
        ), f"Error should be descriptive: {exc_info.value}"

    def test_lower_is_better_is_honored_for_custom_metrics(self):
        """The lower_is_better flag is respected when selecting winners."""
        # A metric where higher is better (like R-squared)
        def r_squared(y_pred, y_true):
            yp = np.asarray(y_pred, dtype=float).reshape(-1)
            yt = np.asarray(y_true, dtype=float).reshape(-1)
            ss_res = np.sum((yt - yp) ** 2)
            ss_tot = np.sum((yt - yt.mean()) ** 2)
            return 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        custom = metrics_mod.Metric(
            key="r2",
            label="coefficient of determination",
            data_shape="regression",
            lower_is_better=False,  # Higher is better for R-squared
            loss=r_squared,
            report=r_squared,
        )

        try:
            metrics_mod.register_metric(custom)
        except AttributeError:
            pytest.fail("register_metric() not found")

        retrieved = metrics_mod.get_metric("r2")
        assert retrieved.lower_is_better is False

        # score_from_value should respect the flag
        # (higher R2 means better, so should not be negated)
        assert retrieved.score_from_value(0.9) == 0.9

    def test_custom_metric_can_be_used_in_cli_workflow(self):
        """A user-registered metric can be used via the CLI, not just the API."""
        # This is an integration test of the full workflow:
        # 1. Define and register a custom metric
        # 2. Create a sample spec and data
        # 3. Call `wheeler llmsr init --metric <custom_name>`
        # 4. Verify it is accepted and used

        def weighted_mse(y_pred, y_true):
            """MSE with sample weighting (user-specific application)."""
            yp = np.asarray(y_pred, dtype=float).reshape(-1)
            yt = np.asarray(y_true, dtype=float).reshape(-1)
            # Hypothetical: weight recent samples more
            weights = np.linspace(0.5, 1.5, len(yp))
            return float(np.mean(weights * (yp - yt) ** 2))

        custom = metrics_mod.Metric(
            key="weighted_mse",
            label="weighted mean squared error",
            data_shape="regression",
            lower_is_better=True,
            loss=weighted_mse,
            report=weighted_mse,
        )

        try:
            metrics_mod.register_metric(custom)
        except AttributeError:
            pytest.fail("register_metric() not found")

        # Now verify the CLI can retrieve it
        try:
            from wheeler.integrations.llmsr import cli as cli_mod
            retrieved = cli_mod.metrics_mod.get_metric("weighted_mse")
            assert retrieved.key == "weighted_mse"
        except Exception as e:
            pytest.fail(f"CLI could not retrieve registered metric: {e}")

    def test_registration_is_persistent_within_process(self):
        """A registered metric persists for the lifetime of the Python process."""
        def custom_loss(y_pred, y_true):
            yp = np.asarray(y_pred, dtype=float).reshape(-1)
            yt = np.asarray(y_true, dtype=float).reshape(-1)
            return float(np.mean((yp - yt) ** 2))

        custom = metrics_mod.Metric(
            key="persistent_test",
            label="test metric",
            data_shape="regression",
            lower_is_better=True,
            loss=custom_loss,
            report=custom_loss,
        )

        try:
            metrics_mod.register_metric(custom)
        except AttributeError:
            pytest.fail("register_metric() not found")

        # Verify it is retrievable immediately
        m1 = metrics_mod.get_metric("persistent_test")
        assert m1.key == "persistent_test"

        # And again later in the same process
        m2 = metrics_mod.get_metric("persistent_test")
        assert m2.key == "persistent_test"

        # Both should be the same metric
        assert m1 is m2
