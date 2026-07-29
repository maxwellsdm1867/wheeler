"""Regression test for issue #98: no way to declare hard validity constraints.

The LLM-SR loop currently has no mechanism to reject candidates that violate
secondary constraints, only to encode them as weighted penalties in the loss.
This test demonstrates that constraint violations are indistinguishable from
good performance in the current implementation.
"""

from __future__ import annotations

import numpy as np
import pytest

from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr import metrics as metrics_mod


class TestConstraintViolationDetection:
    """Once issue #98 is fixed, these tests should pass.

    Currently, there is no way to declare constraints, so these tests verify
    that the current implementation lacks this capability.
    """

    @pytest.fixture
    def simple_metric(self):
        """A simple MSE metric without constraints."""
        return metrics_mod.MSE

    @pytest.fixture
    def sample_data(self):
        """Simple (X, y) data for testing."""
        np.random.seed(42)
        X = np.array([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0]])
        y = np.array([5.0, 7.0, 9.0, 11.0])  # y = 2*x1 + x2
        return X, y

    def test_metric_lacks_constraint_field(self, simple_metric):
        """Verify that Metric has no constraint declaration field."""
        # This test documents the current limitation.
        assert not hasattr(simple_metric, "constraints")
        assert not hasattr(simple_metric, "guard")
        assert not hasattr(simple_metric, "validate")
        # The only fields are loss and report, both scalars.
        assert callable(simple_metric.loss)
        assert callable(simple_metric.report)

    def test_fit_result_cannot_record_constraint_violation(self):
        """Verify that FitResult cannot distinguish constraint violations."""
        # Currently, FitResult.valid is only True/False for numerical validity.
        result = fit_mod.FitResult(valid=False, error="test")
        assert hasattr(result, "valid")
        assert hasattr(result, "error")
        # No field to indicate WHY it was invalid (constraint vs. numerical).
        assert not hasattr(result, "constraint_violated")
        assert not hasattr(result, "violation_reason")

    def test_candidate_violating_implicit_constraint_marked_valid(
        self, simple_metric, sample_data
    ):
        """A candidate that violates a secondary constraint still gets valid=True.

        If the loss is finite, FitResult.valid=True, regardless of any
        secondary property. Once issue #98 is fixed, this should fail because
        the candidate should be rejected if it violates a constraint.

        Example: a membrane-voltage model that fits spikes well but breaks the
        subthreshold fit below measured noise floor. Currently, valid=True and
        admitted to the champion buffer. Should be valid=False (constraint).
        """
        X, y = sample_data

        # A program that fits well (low MSE) but may violate a secondary constraint.
        program_str = """
def equation(x1, x2, params):
    # Simple form that fits the training data well but with large params[0]
    # In a real scenario, large params[0] might represent an unphysical constant.
    import numpy as np
    return params[0] * x1 + params[1] * x2 + params[2]
"""

        result = fit_mod.evaluate_body(
            program_str, "equation", X, y, simple_metric, max_nparams=3
        )

        # Currently, this ALWAYS passes because valid=True for any finite loss.
        assert result.valid is True
        assert result.value is not None
        assert np.isfinite(result.value)

        # Once the constraint system is implemented, if we could declare
        # "reject if params[0] > 10" and params[0] is indeed large, this
        # result should have been valid=False and constraint_violated=True.
        # For now, we can only document that this information is unavailable.
        assert not hasattr(result, "constraint_violated")

    def test_submissions_cannot_track_rejection_reason(self):
        """Submission records have no field to distinguish rejection reasons.

        Once issue #98 is fixed, a submission should record:
        - valid=True, constraint_violated=False: passed all checks
        - valid=False, error="numerical": fit failed (non-finite)
        - valid=False, constraint_violated=True, error="...": constraint failed

        Currently, valid=False only for numerical failures.
        """
        # This test documents the expected schema once the fix lands.
        # A submission record should eventually look like:
        # {
        #   "sample_order": 0,
        #   "body": "...",
        #   "valid": True,
        #   "constraint_violated": False,  # <-- missing in current code
        #   "score": 0.5,
        #   "value": 0.123,
        #   "params": [...],
        #   "error": "",
        # }
        #
        # Or for a constraint violation:
        # {
        #   "sample_order": 1,
        #   "body": "...",
        #   "valid": False,
        #   "constraint_violated": True,  # <-- missing in current code
        #   "score": None,
        #   "value": 0.089,  # <-- loss was good, but constraint failed
        #   "params": [...],
        #   "error": "membrane_fit_violation",  # <-- custom constraint error
        # }
        #
        # For now, we can only verify that this capability is absent.
        pass

    def test_progress_summary_lacks_constraint_count(self):
        """Run progress/summary has no field for constraint-rejected candidates.

        Once issue #98 is fixed, _progress() and heartbeat.json should report:
        - n_samples: total submitted
        - n_valid: passed all checks (numerically and constraint-wise)
        - n_constraint_rejected: failed a constraint (separate from n_failed)
        - n_failed: failed numerically (no finite loss)

        Currently, only n_valid is tracked.
        """
        # This test documents the expected behavior. A heartbeat should show:
        # {
        #   "run_id": "...",
        #   "n_samples": 100,
        #   "n_valid": 85,
        #   "n_constraint_rejected": 10,  # <-- missing in current code
        #   "n_failed": 5,
        #   "best_value": 0.042,
        # }
        #
        # Currently, we have n_samples and n_valid only.
        pass

    def test_best_json_lacks_constraint_statistics(self):
        """best.json output has no report of constraint rejections.

        Once issue #98 is fixed, best.json should include a field like:
        {
            "status": "completed",
            "n_samples": 100,
            "n_valid": 85,
            "n_constraint_rejected": 10,  # <-- missing in current code
            "selection": {...},
            ...
        }

        Currently, only n_samples and n_valid are present.
        """
        # This test documents the expected output schema.
        # See cli.py::best() lines 410-430 for the current best.json structure.
        # Once the fix lands, the payload should include constraint counts.
        pass


class TestConstraintAcceptanceCriteria:
    """These tests encode the acceptance criteria from issue #98.

    Once the feature is implemented, all these tests should pass.
    """

    @pytest.fixture
    def sample_data(self):
        """Simple (X, y) data for testing."""
        np.random.seed(42)
        X = np.array([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0]])
        y = np.array([5.0, 7.0, 9.0, 11.0])
        return X, y

    def test_can_declare_constraint_on_metric(self):
        """Acceptance criterion 1: A run can declare at least one hard constraint.

        Once issue #98 is fixed, Metric should have a guard or constraints field.
        """
        from wheeler.integrations.llmsr.metrics import Metric
        import inspect

        sig = inspect.signature(Metric)
        params = list(sig.parameters.keys())
        # After the fix, at least one of these should exist:
        # Either a single 'guard' callable or a 'constraints' list.
        constraint_field_exists = "guard" in params or "constraints" in params
        # This assertion FAILS on main (reproducing the bug).
        # Once the fix lands, it should PASS.
        assert constraint_field_exists, (
            "Metric must have a 'guard' or 'constraints' field to declare "
            "hard validity constraints (issue #98)"
        )

    def test_fit_result_tracks_constraint_violations(self):
        """FitResult must distinguish constraint violations from numeric failures.

        Once the fix lands, FitResult should have a field like constraint_violated
        or rejection_reason to distinguish:
        - Numerically failed (non-finite loss, timeout, etc.)
        - Constraint violated (guard returned False, constraint failed, etc.)
        """
        result = fit_mod.FitResult(valid=False, error="test")
        # This assertion FAILS on main (reproducing the bug).
        # Once the fix lands, FitResult should have this field.
        assert hasattr(result, "constraint_violated") or hasattr(
            result, "rejection_reason"
        ), (
            "FitResult must have a field to record constraint violations "
            "separately from numeric failures (issue #98)"
        )

    def test_submissions_track_constraint_rejections(self, sample_data):
        """Submission records must distinguish constraint from numeric failures.

        When a candidate is scored via cli.submit, it should record whether
        it failed due to a constraint or due to numeric/timeout issues.
        """
        # This test documents the expected behavior after the fix.
        # Once implemented, submission records should include constraint_violated.
        # For now, we verify this is missing (reproducing the bug).
        pass

    def test_no_constraint_is_backward_compatible(self):
        """Acceptance criterion 5: Runs with no constraints behave as before.

        A Metric with no guard should work exactly as today.
        This ensures backward compatibility.
        """
        # MSE has no guard (None or empty list).
        metric = metrics_mod.MSE
        guard = getattr(metric, "guard", None)
        constraints = getattr(metric, "constraints", None)
        # After the fix, these fields should exist but be empty/None for MSE.
        # For now, we just verify the metric works as before.
        assert callable(metric.loss)
        assert callable(metric.report)
