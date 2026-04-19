"""Tests for ensure_artifact tool and _detect_artifact_type helper."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.tools.graph_tools.mutations import (
    _detect_artifact_type,
    _build_delegated_args,
    _EXT_TO_TYPE,
    ensure_artifact,
)
from wheeler.tools.graph_tools._field_specs import validate_and_normalize


# ---------------------------------------------------------------------------
# _detect_artifact_type
# ---------------------------------------------------------------------------


class TestDetectArtifactType:
    def test_python_script(self):
        label, secondary = _detect_artifact_type("/tmp/foo.py", "")
        assert label == "Script"
        assert secondary == "python"

    def test_matlab_script(self):
        label, secondary = _detect_artifact_type("/tmp/foo.m", "")
        assert label == "Script"
        assert secondary == "matlab"

    def test_csv_dataset(self):
        label, secondary = _detect_artifact_type("/data/results.csv", "")
        assert label == "Dataset"
        assert secondary == "csv"

    def test_mat_dataset(self):
        label, secondary = _detect_artifact_type("/data/neurons.mat", "")
        assert label == "Dataset"
        assert secondary == "mat"

    def test_markdown_document(self):
        label, secondary = _detect_artifact_type("/docs/readme.md", "")
        assert label == "Document"
        assert secondary == "markdown"

    def test_plans_md_routes_to_plan(self):
        label, secondary = _detect_artifact_type("/project/.plans/inv-001.md", "")
        assert label == "Plan"
        assert secondary == "markdown"

    def test_png_figure(self):
        label, secondary = _detect_artifact_type("/results/fig1.png", "")
        assert label == "Finding"
        assert secondary == "figure"

    def test_svg_figure(self):
        label, secondary = _detect_artifact_type("/figs/plot.svg", "")
        assert label == "Finding"
        assert secondary == "figure"

    def test_unknown_extension_defaults_to_document(self):
        label, secondary = _detect_artifact_type("/data/file.xyz", "")
        assert label == "Document"
        assert secondary == ""

    def test_override_wins(self):
        # .py normally maps to Script, but override says dataset
        label, secondary = _detect_artifact_type("/tmp/foo.py", "dataset")
        assert label == "Dataset"
        assert secondary == "python"  # secondary from extension

    def test_override_plan(self):
        label, secondary = _detect_artifact_type("/docs/plan.md", "plan")
        assert label == "Plan"

    def test_override_finding(self):
        label, secondary = _detect_artifact_type("/results/data.csv", "finding")
        assert label == "Finding"

    def test_all_extensions_covered(self):
        """Every entry in _EXT_TO_TYPE should produce a valid label."""
        valid_labels = {"Script", "Dataset", "Document", "Finding"}
        for ext, (label, secondary) in _EXT_TO_TYPE.items():
            assert label in valid_labels, f"Extension {ext} maps to unknown label {label}"
            assert secondary, f"Extension {ext} has empty secondary"

    def test_r_uppercase(self):
        label, _ = _detect_artifact_type("/code/analysis.R", "")
        assert label == "Script"


# ---------------------------------------------------------------------------
# _build_delegated_args
# ---------------------------------------------------------------------------


class TestBuildDelegatedArgs:
    def test_script_defaults_language(self):
        tool, args = _build_delegated_args(
            "Script", "python", "/tmp/foo.py", {}, "abc123",
        )
        assert tool == "add_script"
        assert args["language"] == "python"
        assert "language" in args.pop("_defaulted")

    def test_dataset_translates_data_type_to_type(self):
        """Adversarial review issue #1: add_dataset expects 'type' not 'data_type'."""
        tool, args = _build_delegated_args(
            "Dataset", "csv", "/data/results.csv", {}, "abc123",
        )
        assert tool == "add_dataset"
        assert "type" in args
        assert args["type"] == "csv"
        assert "data_type" not in args

    def test_dataset_defaults_description(self):
        tool, args = _build_delegated_args(
            "Dataset", "csv", "/data/results.csv", {}, "abc123",
        )
        assert args["description"] == "results.csv"
        assert "description" in args.pop("_defaulted")

    def test_plan_defaults(self):
        tool, args = _build_delegated_args(
            "Plan", "markdown", "/project/.plans/inv.md", {}, "abc",
        )
        assert tool == "add_plan"
        assert args["title"] == "inv"
        assert args["status"] == "draft"
        defaulted = args.pop("_defaulted")
        assert "title" in defaulted
        assert "status" in defaulted

    def test_finding_defaults(self):
        tool, args = _build_delegated_args(
            "Finding", "figure", "/results/fig.png", {}, "abc",
        )
        assert tool == "add_finding"
        assert args["confidence"] == 0.5
        assert args["description"] == "fig.png"
        assert args["artifact_type"] == "figure"

    def test_document_defaults(self):
        tool, args = _build_delegated_args(
            "Document", "markdown", "/docs/methods.md", {}, "abc",
        )
        assert tool == "add_document"
        assert args["title"] == "methods"

    def test_explicit_args_override_defaults(self):
        tool, args = _build_delegated_args(
            "Script", "python", "/tmp/foo.py",
            {"language": "cython"},
            "abc123",
        )
        assert args["language"] == "cython"
        assert "language" not in args.pop("_defaulted")

    def test_dataset_explicit_description(self):
        tool, args = _build_delegated_args(
            "Dataset", "csv", "/data/results.csv",
            {"description": "Spike timing data"},
            "abc123",
        )
        assert args["description"] == "Spike timing data"
        assert "description" not in args.pop("_defaulted")


# ---------------------------------------------------------------------------
# validate_and_normalize for ensure_artifact
# ---------------------------------------------------------------------------


class TestEnsureArtifactValidation:
    def test_path_required(self):
        errors, _ = validate_and_normalize("ensure_artifact", {})
        assert "path" in errors

    def test_path_must_exist(self, tmp_path):
        args = {"path": str(tmp_path / "nonexistent.py")}
        errors, _ = validate_and_normalize("ensure_artifact", args)
        assert "path" in errors
        assert "does not exist" in errors["path"]["error"]

    def test_existing_path_ok(self, tmp_path):
        f = tmp_path / "script.py"
        f.write_text("x = 1")
        args = {"path": str(f)}
        errors, warnings = validate_and_normalize("ensure_artifact", args)
        assert not errors
        # Path should be resolved to absolute
        assert args["path"] == str(f.resolve())


# ---------------------------------------------------------------------------
# ensure_artifact: integration with FakeBackend
# ---------------------------------------------------------------------------


class FakeBackend:
    """Minimal backend for ensure_artifact tests."""

    def __init__(self):
        self.nodes: dict[str, list[dict]] = {}
        self.cypher_results: list[list[dict]] = []

    async def create_node(self, label: str, props: dict) -> str:
        self.nodes.setdefault(label, []).append(props)
        return props.get("id", "")

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        if self.cypher_results:
            return self.cypher_results.pop(0)
        return []

    async def get_node(self, label: str, node_id: str) -> dict | None:
        for props in self.nodes.get(label, []):
            if props.get("id") == node_id:
                return props
        return None

    async def update_node(self, label: str, node_id: str, updates: dict) -> bool:
        return True

    async def count_all(self) -> dict:
        return {}


class TestEnsureArtifactCreate:
    @pytest.fixture
    def backend(self):
        return FakeBackend()

    @pytest.fixture
    def script_file(self, tmp_path):
        f = tmp_path / "analysis.py"
        f.write_text("import numpy as np\nprint('hello')")
        return f

    @pytest.fixture
    def csv_file(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("a,b,c\n1,2,3")
        return f

    @pytest.fixture
    def plan_file(self, tmp_path):
        d = tmp_path / ".plans"
        d.mkdir()
        f = d / "inv-001.md"
        f.write_text("# Investigation\nSome plan")
        return f

    @pytest.fixture
    def png_file(self, tmp_path):
        f = tmp_path / "figure.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        return f

    @pytest.mark.asyncio
    async def test_create_script(self, backend, script_file):
        """New script file should be created with action='created'."""
        # Mock execute_tool to return a proper result
        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "abc123hash"
            with patch("wheeler.tools.graph_tools.execute_tool") as mock_exec:
                mock_exec.return_value = json.dumps({
                    "node_id": "S-test1234",
                    "label": "Script",
                    "status": "created",
                })
                result_str = await ensure_artifact(backend, {
                    "path": str(script_file),
                    "_config": None,
                })
        result = json.loads(result_str)
        assert result["action"] == "created"
        assert result["label"] == "Script"
        assert result["hash"] == "abc123hash"
        assert result["path"] == str(script_file)

    @pytest.mark.asyncio
    async def test_unchanged_returns_no_write(self, backend, script_file):
        """File with matching hash should return action='unchanged'."""
        backend.cypher_results = [
            [{"id": "S-existing", "label": "Script", "hash": "samehash"}],
        ]
        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "samehash"
            result_str = await ensure_artifact(backend, {
                "path": str(script_file),
            })
        result = json.loads(result_str)
        assert result["action"] == "unchanged"
        assert result["node_id"] == "S-existing"

    @pytest.mark.asyncio
    async def test_updated_triggers_propagation(self, backend, script_file):
        """Changed hash should update and propagate invalidation."""
        backend.cypher_results = [
            [{"id": "S-existing", "label": "Script", "hash": "oldhash"}],
        ]
        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "newhash"
            with patch("wheeler.tools.graph_tools.execute_tool") as mock_exec:
                mock_exec.return_value = json.dumps({
                    "node_id": "S-existing",
                    "label": "Script",
                    "updated_fields": ["hash"],
                    "changes": {"hash": {"old": "oldhash", "new": "newhash"}},
                    "status": "updated",
                })
                with patch("wheeler.provenance.propagate_invalidation", new_callable=AsyncMock) as mock_prop:
                    mock_prop.return_value = [{"node_id": "F-downstream"}]
                    result_str = await ensure_artifact(backend, {
                        "path": str(script_file),
                        "_config": None,
                    })
        result = json.loads(result_str)
        assert result["action"] == "updated"
        assert result["previous_hash"] == "oldhash"
        assert result["hash"] == "newhash"
        assert result["stale_downstream"] == 1

    @pytest.mark.asyncio
    async def test_label_mismatch_error(self, backend, script_file):
        """Finding at a .py path should return label_mismatch."""
        backend.cypher_results = [
            [{"id": "F-wrong", "label": "Finding", "hash": "abc"}],
        ]
        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "abc"
            result_str = await ensure_artifact(backend, {
                "path": str(script_file),
            })
        result = json.loads(result_str)
        assert result["error"] == "label_mismatch"
        assert result["existing_label"] == "Finding"
        assert result["detected_label"] == "Script"

    @pytest.mark.asyncio
    async def test_plan_detection(self, backend, plan_file):
        """Files under .plans/ with .md extension route to Plan."""
        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "planhash"
            with patch("wheeler.tools.graph_tools.execute_tool") as mock_exec:
                mock_exec.return_value = json.dumps({
                    "node_id": "PL-test1234",
                    "label": "Plan",
                    "status": "created",
                })
                result_str = await ensure_artifact(backend, {
                    "path": str(plan_file),
                    "_config": None,
                })
        result = json.loads(result_str)
        assert result["action"] == "created"
        assert result["label"] == "Plan"

    @pytest.mark.asyncio
    async def test_defaulted_fields_reported(self, backend, script_file):
        """Created nodes should report which fields were defaulted."""
        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "hash123"
            with patch("wheeler.tools.graph_tools.execute_tool") as mock_exec:
                mock_exec.return_value = json.dumps({
                    "node_id": "S-new123",
                    "label": "Script",
                    "status": "created",
                })
                result_str = await ensure_artifact(backend, {
                    "path": str(script_file),
                    "_config": None,
                })
        result = json.loads(result_str)
        assert "defaulted_fields" in result
        assert "language" in result["defaulted_fields"]


# ---------------------------------------------------------------------------
# Meta-test: delegated args pass validation for all extension types
# ---------------------------------------------------------------------------


class TestDelegatedArgsValidation:
    """Adversarial review #3: ensure defaulted args pass validation."""

    def test_all_extensions_produce_valid_args(self, tmp_path):
        """For every extension in _EXT_TO_TYPE, defaulted args must pass
        validate_and_normalize for the delegated tool."""
        for ext, (label, secondary) in _EXT_TO_TYPE.items():
            # Create a temp file
            f = tmp_path / f"testfile{ext}"
            f.write_text("test content")
            path = str(f.resolve())

            tool_name, args = _build_delegated_args(
                label, secondary, path, {}, "fakehash",
            )
            args.pop("_defaulted", None)

            errors, _ = validate_and_normalize(tool_name, args)
            assert not errors, (
                f"Extension {ext} -> {tool_name}: validation failed: {errors}"
            )
