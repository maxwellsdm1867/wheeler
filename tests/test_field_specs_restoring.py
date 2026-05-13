"""Tests for ``_field_specs.validate_and_normalize`` ``_restoring`` flag.

The flag flips strict required-field and required-path checks from errors
to warnings so that ``restore_fresh`` and ``restore_merge`` can replay
historical archive content without aborting on validation that tightened
after the archive was packed.
"""

from __future__ import annotations

from wheeler.tools.graph_tools._field_specs import validate_and_normalize


class TestRestoringDowngradesRequiredFields:
    """When ``_restoring=True``, empty or missing required fields become
    warnings instead of errors.  Restore must preserve archive content
    faithfully even when the source predates current validation.
    """

    def test_empty_description_errors_without_restoring(self) -> None:
        """Baseline: empty required field hard-fails by default."""
        args = {"kind": "discuss", "description": ""}
        errors, warnings = validate_and_normalize("add_execution", args)
        assert "description" in errors
        assert errors["description"]["error"].startswith("required")

    def test_empty_description_warns_with_restoring(self) -> None:
        """``_restoring=True`` downgrades an empty required field."""
        args = {"kind": "discuss", "description": "", "_restoring": True}
        errors, warnings = validate_and_normalize("add_execution", args)
        assert errors == {}, f"unexpected errors: {errors}"
        assert "description" in warnings
        assert "restored from archive" in warnings["description"]

    def test_missing_description_warns_with_restoring(self) -> None:
        """A missing required field becomes a warning under ``_restoring``."""
        args = {"kind": "discuss", "_restoring": True}
        errors, warnings = validate_and_normalize("add_execution", args)
        assert errors == {}, f"unexpected errors: {errors}"
        assert "description" in warnings

    def test_missing_description_errors_without_restoring(self) -> None:
        """Baseline: missing required field hard-fails by default."""
        args = {"kind": "discuss"}
        errors, warnings = validate_and_normalize("add_execution", args)
        assert "description" in errors
        assert errors["description"]["value"] is None

    def test_restoring_flag_is_popped(self) -> None:
        """``_restoring`` is consumed and never leaks to backend writes."""
        args = {"kind": "discuss", "description": "x", "_restoring": True}
        validate_and_normalize("add_execution", args)
        assert "_restoring" not in args

    def test_restoring_flag_popped_even_when_errors(self) -> None:
        """The flag is popped even if validation otherwise errors out, so
        the caller cannot accidentally re-submit with the flag still set.
        """
        args = {"_restoring": True}  # missing kind AND description
        errors, _ = validate_and_normalize("add_execution", args)
        assert "_restoring" not in args
        # Required fields are downgraded under _restoring, so no errors here.
        assert errors == {}

    def test_finding_empty_description_warns_with_restoring(self) -> None:
        """The downgrade applies to every tool's required fields, not just
        ``add_execution``.  Verified on ``add_finding(description)``.
        """
        args = {"description": "", "_restoring": True}
        errors, warnings = validate_and_normalize("add_finding", args)
        assert errors == {}
        assert "description" in warnings


class TestRestoringDowngradesPathChecks:
    """Existing behavior (already in place before this change): with
    ``_restoring=True``, ``_PATH_MUST_EXIST`` tools downgrade a missing
    file to a warning rather than refusing the write.  These tests pin
    that behavior so the recent refactor (popping the flag once at the
    top of ``validate_and_normalize``) does not regress it.
    """

    def test_dataset_missing_path_warns_with_restoring(self, tmp_path) -> None:
        nonexistent = tmp_path / "missing.csv"
        args = {
            "path": str(nonexistent),
            "type": "csv",
            "description": "fixture",
            "_restoring": True,
        }
        errors, warnings = validate_and_normalize("add_dataset", args)
        assert "path" not in errors
        # Either a warning or no warning, but never an error.
        # (The exact text is not asserted: the point is no abort.)

    def test_dataset_missing_path_errors_without_restoring(self, tmp_path) -> None:
        nonexistent = tmp_path / "missing.csv"
        args = {
            "path": str(nonexistent),
            "type": "csv",
            "description": "fixture",
        }
        errors, warnings = validate_and_normalize("add_dataset", args)
        assert "path" in errors
