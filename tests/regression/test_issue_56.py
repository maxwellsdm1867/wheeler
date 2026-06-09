"""Regression test for issue #56: mcp/show_node import error.

Issue: show_node MCP tool fails with "No module named 'wheeler.knowledge'"
when called, even though the module exists and can be imported directly.

This test verifies that:
1. The show_node function can be imported from mcp_core
2. The lazy import of wheeler.knowledge.store inside show_node succeeds
3. show_node can read actual node data from the knowledge store
4. The import does NOT fail at runtime (the actual bug scenario)
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

from wheeler.mcp_core import show_node
from wheeler.models import FindingModel


@pytest.fixture
def temp_knowledge_dir():
    """Create a temporary knowledge directory with a test node."""
    with tempfile.TemporaryDirectory() as tmpdir:
        knowledge_path = Path(tmpdir)

        # Create a test finding node
        finding = FindingModel(
            id="F-test-issue56",
            title="Test Finding for Issue 56",
            statement="This is a test finding to verify show_node works",
            type="Finding",
        )

        # Write it as JSON
        target = knowledge_path / finding.file_name
        data = finding.model_dump_json(indent=2)
        target.write_text(data, encoding="utf-8")

        yield knowledge_path, finding


@pytest.mark.asyncio
async def test_show_node_can_import_store():
    """Test that show_node's lazy import of wheeler.knowledge.store succeeds."""
    # This should not raise ImportError
    try:
        from wheeler.knowledge import store
        assert hasattr(store, 'read_node'), "store module should have read_node function"
    except ImportError as e:
        pytest.fail(f"Failed to import wheeler.knowledge.store: {e}")


@pytest.mark.asyncio
async def test_show_node_with_existing_node(temp_knowledge_dir, monkeypatch):
    """Test that show_node can read an actual node from the knowledge store."""
    knowledge_path, finding = temp_knowledge_dir

    # Patch the _config in mcp_shared that show_node uses
    import wheeler.mcp_shared as mcp_shared
    original_knowledge_path = mcp_shared._config.knowledge_path
    monkeypatch.setattr(mcp_shared._config, "knowledge_path", str(knowledge_path))

    try:
        # Call show_node with the test finding ID
        result = await show_node(node_id="F-test-issue56")

        # Should succeed and return the node data
        assert "error" not in result or result.get("error") is None, (
            f"show_node should not error, but got: {result.get('error')}"
        )
        assert result.get("id") == "F-test-issue56", (
            f"Expected node id F-test-issue56, got {result.get('id')}"
        )
        assert result.get("title") == "Test Finding for Issue 56", (
            f"Expected correct title, got {result.get('title')}"
        )
    finally:
        monkeypatch.setattr(mcp_shared._config, "knowledge_path", original_knowledge_path)


@pytest.mark.asyncio
async def test_show_node_missing_node():
    """Test that show_node gracefully handles missing nodes."""
    # Call show_node with a non-existent node ID
    result = await show_node(node_id="F-nonexistent-issue56")

    # Should return error dict, not raise ImportError
    assert isinstance(result, dict), "show_node should always return a dict"
    assert "error" in result, "show_node should indicate node not found"
