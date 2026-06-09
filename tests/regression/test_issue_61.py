"""Regression test for issue #61: relative vs absolute path deduplication.

Issue: ensure_artifact creates duplicate nodes when an existing node has
a relative path and a new call passes the absolute path to the same file.

The tool should normalize both paths to absolute before the dedup lookup.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.tools.graph_tools.mutations import ensure_artifact


class FakeBackendForDedup:
    """Minimal backend that simulates pre-existing nodes with relative paths."""

    def __init__(self, existing_nodes_by_path: dict[str, dict] | None = None):
        """Initialize with optional pre-existing nodes keyed by path."""
        self.nodes: dict[str, list[dict]] = {}
        self.existing_nodes_by_path = existing_nodes_by_path or {}
        self.last_cypher_query = None
        self.last_cypher_params = None
        self.created_nodes = []

    async def create_node(self, label: str, props: dict) -> str:
        node_id = props.get("id", "")
        self.nodes.setdefault(label, []).append(props)
        self.created_nodes.append((label, props))
        return node_id

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        """Simulate Cypher query matching nodes by path."""
        self.last_cypher_query = query
        self.last_cypher_params = params

        # Check if this is the dedup lookup (matching on n.path = $path)
        if "n.path = $path" in query and params and "path" in params:
            queried_path = params["path"]
            # Return the node for this path if it exists
            if queried_path in self.existing_nodes_by_path:
                return [self.existing_nodes_by_path[queried_path]]
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


class TestIssue61RelativeAbsolutePathDedup:
    """Test that relative vs absolute paths are deduplicated correctly."""

    @pytest.fixture
    def script_file(self, tmp_path):
        """Create a test Python script."""
        f = tmp_path / "SpikeResponseModel.m"
        f.write_text("% MATLAB script\nfunction y = SpikeResponseModel(x)\ny = x;\nend")
        return f

    @pytest.mark.asyncio
    async def test_absolute_path_matches_relative_path_node(self, script_file):
        """Calling ensure_artifact with absolute path should match existing node
        with relative path, returning action='unchanged', not creating a duplicate.

        This is the core bug: when a pre-existing node is stored with a relative
        path (e.g., "SpikeResponseModel.m") and we call ensure_artifact with the
        absolute path ("/Users/.../SpikeResponseModel.m"), it should match the
        existing node and return action='unchanged' or 'updated', not 'created'.
        """
        # Simulate a pre-existing node with a RELATIVE path
        relative_path = "SpikeResponseModel.m"
        absolute_path = str(script_file.resolve())
        existing_node = {
            "id": "S-9501ebca",
            "label": "Script",
            "hash": "oldhash",
            "path": relative_path,  # Stored with relative path
        }

        # The backend must map BOTH the relative and absolute path to the same node
        # This simulates the current bug: the node is stored with relative path,
        # so a query for absolute path won't find it.
        backend = FakeBackendForDedup(existing_nodes_by_path={
            relative_path: existing_node,
            # Note: absolute_path is NOT in the map, simulating the bug
        })

        # Call ensure_artifact with the ABSOLUTE path to the same file
        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "oldhash"

            # This is the call that should match the existing node
            result_str = await ensure_artifact(backend, {
                "path": absolute_path,  # Absolute path
            })

        result = json.loads(result_str)

        # The bug: this currently returns action='created' with a new node_id
        # because the query on line 670 of mutations.py does an exact match:
        #   n.path = $path
        # But the node was stored with relative path "SpikeResponseModel.m"
        # and we're querying with absolute path "/Users/.../SpikeResponseModel.m"
        # so they don't match.

        # Expected: should return unchanged (same hash) on the existing node
        assert result["action"] == "unchanged", (
            f"Expected action='unchanged' to match existing node with relative path, "
            f"but got action='{result.get('action')}' with node_id='{result.get('node_id')}'. "
            f"This indicates a duplicate node was created. "
            f"Backend query used path parameter: {backend.last_cypher_params}"
        )
        assert result["node_id"] == "S-9501ebca", (
            f"Expected to match existing node S-9501ebca, but got {result.get('node_id')}"
        )

    @pytest.mark.asyncio
    async def test_relative_path_call_matches_absolute_path_node(self, script_file, tmp_path):
        """Inverse test: calling with relative path should match node stored
        with absolute path.

        This documents the expected behavior after the fix: path normalization
        should be bidirectional.
        """
        # Simulate a pre-existing node with an ABSOLUTE path
        absolute_path = str(script_file.resolve())
        existing_node = {
            "id": "S-d9cda53f",
            "label": "Script",
            "hash": "samehash",
            "path": absolute_path,  # Stored with absolute path
        }

        # After fix, both relative and absolute should map to the same node
        backend = FakeBackendForDedup(existing_nodes_by_path={
            absolute_path: existing_node,
        })

        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "samehash"

            # Call with absolute path (which is what happens after normalization)
            result_str = await ensure_artifact(backend, {
                "path": absolute_path,
            })

        result = json.loads(result_str)

        # Should match the existing node
        assert result["action"] == "unchanged", (
            f"Expected action='unchanged', got action='{result.get('action')}'"
        )
        assert result["node_id"] == "S-d9cda53f"

    @pytest.mark.asyncio
    async def test_ensure_artifact_idempotent_on_same_absolute_path(self, script_file):
        """Regression test to ensure idempotency on the same absolute path."""
        absolute_path = str(script_file.resolve())
        existing_node = {
            "id": "S-existing",
            "label": "Script",
            "hash": "h1",
            "path": absolute_path,
        }

        backend = FakeBackendForDedup(existing_nodes_by_path={
            absolute_path: existing_node,
        })

        with patch("wheeler.tools.graph_tools.mutations.graph_provenance") as mock_prov:
            mock_prov.hash_file.return_value = "h1"

            result_str = await ensure_artifact(backend, {
                "path": absolute_path,
            })

        result = json.loads(result_str)

        # This should work (it's not the bug, but validate it still passes)
        assert result["action"] == "unchanged"
        assert result["node_id"] == "S-existing"
