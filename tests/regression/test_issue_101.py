"""Regression test for issue #101: cannot clear a string field.

https://github.com/maxwellsdm/wheeler/issues/101

The bug: update_node treats empty string as "field not supplied", so
passing path="" returns "No fields to update" instead of clearing the field.

This test verifies that:
1. A string field can be cleared via update_node by passing an empty string
2. The response reports the change (not "No fields to update")
3. The change is recorded in the node's change_log
4. Omitting a parameter still means "leave unchanged"
"""

import asyncio
import json
from pathlib import Path

import pytest

from wheeler.config import load_config
from wheeler.graph.backend import get_backend
from wheeler.graph.schema import generate_node_id, PREFIX_TO_LABEL
from wheeler.tools.graph_tools import mutations


@pytest.fixture
async def backend_and_config():
    """Set up backend for test."""
    config = load_config()
    backend = get_backend(config)
    yield backend, config
    # No cleanup needed: tests manage their own node cleanup


class TestUpdateNodeClearString:
    """Test clearing string fields via update_node."""

    @pytest.mark.asyncio
    async def test_clear_path_field(self, backend_and_config):
        """Test that path field can be cleared with empty string."""
        backend, config = backend_and_config

        # Create a Plan node with a path
        node_id = generate_node_id("PL")
        original_path = "/tmp/test_plan_issue101.md"

        await backend.create_node("Plan", {
            "id": node_id,
            "title": "Test Plan for Issue 101",
            "path": original_path,
            "status": "draft",
            "date": "2024-07-28T00:00:00Z",
            "tier": "generated",
            "stability": 0.5,
            "session_id": "test_issue_101",
            "display_name": "Test Plan",
            "e2e_tag": f"test-101-{node_id}",  # Marker for cleanup
        })

        try:
            # Verify node was created with the path
            node = await backend.get_node("Plan", node_id)
            assert node is not None, f"Node {node_id} not found after creation"
            assert node.get("path") == original_path, "Path not set on creation"

            # Attempt to clear the path field
            update_args = {
                "node_id": node_id,
                "path": "",  # Explicit empty string to clear
                "session_id": "test_issue_101"
            }

            result_json = await mutations.update_node(backend, update_args)
            result = json.loads(result_json)

            # Check: should NOT return "No fields to update"
            assert result.get("error") != "No fields to update", (
                f"update_node returned 'No fields to update' when clearing path. "
                f"Full response: {result}"
            )

            # Check: should return success status
            assert result.get("status") == "updated", (
                f"Expected status='updated' but got {result.get('status')}. "
                f"Response: {result}"
            )

            # Check: should report path as updated field
            assert "path" in result.get("updated_fields", []), (
                f"Expected path in updated_fields but got {result.get('updated_fields')}. "
                f"Response: {result}"
            )

            # Check: should show the change
            changes = result.get("changes", {})
            assert "path" in changes, (
                f"Expected path in changes but got {list(changes.keys())}. "
                f"Response: {result}"
            )
            assert changes["path"]["old"] == original_path, (
                f"Expected old value to be {original_path} but got {changes['path']['old']}"
            )
            assert changes["path"]["new"] == "", (
                f"Expected new value to be empty string but got {repr(changes['path']['new'])}"
            )

            # Verify the field was actually cleared in the graph
            updated_node = await backend.get_node("Plan", node_id)
            assert updated_node is not None
            assert updated_node.get("path") == "", (
                f"Path was not cleared in graph. Got {repr(updated_node.get('path'))}"
            )

        finally:
            # Clean up the test node
            try:
                await backend.delete_node("Plan", node_id)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_omit_field_means_no_change(self, backend_and_config):
        """Test that omitting a parameter leaves the field unchanged."""
        backend, config = backend_and_config

        # Create a Finding node with a description
        node_id = generate_node_id("F")
        original_description = "Original description"

        await backend.create_node("Finding", {
            "id": node_id,
            "description": original_description,
            "confidence": 0.7,
            "date": "2024-07-28T00:00:00Z",
            "tier": "generated",
            "stability": 0.7,
            "session_id": "test_issue_101",
            "display_name": "Test Finding",
            "e2e_tag": f"test-101-{node_id}",
        })

        try:
            # Update only confidence, omit description
            update_args = {
                "node_id": node_id,
                "confidence": 0.9,
                # description is NOT included, should remain unchanged
                "session_id": "test_issue_101"
            }

            result_json = await mutations.update_node(backend, update_args)
            result = json.loads(result_json)

            assert result.get("status") == "updated"
            assert "confidence" in result.get("updated_fields", [])
            assert "description" not in result.get("updated_fields", [])

            # Verify description was not changed
            updated_node = await backend.get_node("Finding", node_id)
            assert updated_node is not None
            assert updated_node.get("description") == original_description

        finally:
            try:
                await backend.delete_node("Finding", node_id)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_clear_title_field(self, backend_and_config):
        """Test clearing title field on a Hypothesis node."""
        backend, config = backend_and_config

        # Create a Hypothesis with a statement
        node_id = generate_node_id("H")
        original_statement = "Original hypothesis"

        await backend.create_node("Hypothesis", {
            "id": node_id,
            "statement": original_statement,
            "date": "2024-07-28T00:00:00Z",
            "tier": "generated",
            "stability": 0.5,
            "session_id": "test_issue_101",
            "display_name": "Test Hyp",
            "e2e_tag": f"test-101-{node_id}",
        })

        try:
            # Try to clear the statement (primary content field)
            update_args = {
                "node_id": node_id,
                "statement": "",  # Clear the statement
                "session_id": "test_issue_101"
            }

            result_json = await mutations.update_node(backend, update_args)
            result = json.loads(result_json)

            # Should succeed (not return "No fields to update")
            assert result.get("status") == "updated", (
                f"Failed to clear statement. Response: {result}"
            )

            # Verify the statement was cleared
            updated_node = await backend.get_node("Hypothesis", node_id)
            assert updated_node is not None
            assert updated_node.get("statement") == "", (
                f"Statement was not cleared. Got {repr(updated_node.get('statement'))}"
            )

        finally:
            try:
                await backend.delete_node("Hypothesis", node_id)
            except Exception:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
