"""Regression test for issue #62: ensure_artifact Dataset data_type defaults.

Issue: ensure_artifact(path="*.db", artifact_type="dataset") fails validation
when data_type is not explicitly provided, even though the tool description
claims "data_type defaults to extension."

Expected: data_type should be derived from file extension (e.g. .db -> db).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.tools.graph_tools.mutations import (
    _build_delegated_args,
    _detect_artifact_type,
    ensure_artifact,
)
from wheeler.tools.graph_tools._field_specs import validate_and_normalize


class TestIssue62DataTypeDefaults:
    """Test that ensure_artifact defaults Dataset data_type from extension."""

    @pytest.fixture
    def db_file(self, tmp_path):
        """Create a temporary .db file."""
        f = tmp_path / "results.db"
        f.write_text("sqlite database")
        return f

    @pytest.fixture
    def mat_file(self, tmp_path):
        """Create a temporary .mat file."""
        f = tmp_path / "data.mat"
        f.write_text("matlab matrix")
        return f

    def test_db_extension_with_artifact_type_dataset(self, db_file):
        """When artifact_type='dataset' is passed for .db file, secondary
        should be derived from extension even if not explicitly in _EXT_TO_TYPE."""
        label, secondary = _detect_artifact_type(str(db_file), "dataset")
        assert label == "Dataset"
        # The bug: secondary is empty string because .db is not in _EXT_TO_TYPE
        # After fix, it should be 'db' (or similar)
        assert secondary != "", f"Got empty secondary for .db file; expected a non-empty type"

    def test_mat_extension_with_artifact_type_dataset(self, mat_file):
        """Existing .mat support should still work."""
        label, secondary = _detect_artifact_type(str(mat_file), "dataset")
        assert label == "Dataset"
        assert secondary == "mat"

    def test_db_delegated_args_type_field_not_empty(self, db_file):
        """_build_delegated_args for .db Dataset should produce non-empty type."""
        label, secondary = _detect_artifact_type(str(db_file), "dataset")
        tool_name, args = _build_delegated_args(
            label, secondary, str(db_file), {}, "fakehash"
        )
        assert tool_name == "add_dataset"
        assert args["type"] != "", (
            f"Got empty type for .db file; expected a derived type like 'db'"
        )

    def test_db_delegated_args_pass_validation(self, db_file):
        """Delegated args for .db Dataset must pass add_dataset validation."""
        label, secondary = _detect_artifact_type(str(db_file), "dataset")
        tool_name, args = _build_delegated_args(
            label, secondary, str(db_file), {}, "fakehash"
        )
        args_copy = args.copy()
        args_copy.pop("_defaulted", None)
        errors, _ = validate_and_normalize(tool_name, args_copy)
        assert not errors, (
            f"Delegated args for .db file failed validation: {errors}"
        )

    def test_common_dataset_extensions_with_artifact_type(self, tmp_path):
        """Test that common dataset extensions work with artifact_type override."""
        extensions = [".db", ".csv", ".mat", ".h5", ".hdf5", ".npy"]
        for ext in extensions:
            f = tmp_path / f"test{ext}"
            f.write_text("test")

            label, secondary = _detect_artifact_type(str(f), "dataset")
            assert label == "Dataset"
            assert secondary != "", (
                f"Extension {ext} should produce a non-empty secondary type"
            )

            tool_name, args = _build_delegated_args(
                label, secondary, str(f), {}, "fakehash"
            )
            assert args["type"] != "", (
                f"Extension {ext} should produce a non-empty type field"
            )

            args_copy = args.copy()
            args_copy.pop("_defaulted", None)
            errors, _ = validate_and_normalize(tool_name, args_copy)
            assert not errors, (
                f"Extension {ext} failed validation: {errors}"
            )

    @pytest.mark.asyncio
    async def test_ensure_artifact_db_without_data_type(self, db_file):
        """Full integration: ensure_artifact(path="*.db", artifact_type="dataset")
        without data_type should succeed, deriving type from extension."""

        class FakeBackend:
            async def create_node(self, label: str, props: dict) -> str:
                return props.get("id", "")

            async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
                return []

        backend = FakeBackend()

        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "abc123hash"
            with patch("wheeler.tools.graph_tools.execute_tool") as mock_exec:
                # Should not raise validation error
                mock_exec.return_value = json.dumps({
                    "node_id": "D-testdb01",
                    "label": "Dataset",
                    "status": "created",
                })
                result_str = await ensure_artifact(backend, {
                    "path": str(db_file),
                    "artifact_type": "dataset",
                    "_config": None,
                })

        result = json.loads(result_str)
        assert "error" not in result, (
            f"ensure_artifact failed for .db file: {result.get('error', result.get('message'))}"
        )
        assert result["action"] == "created"
        assert result["label"] == "Dataset"
