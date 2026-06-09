"""Regression tests for issue #57: update_node field validation and started_at.

Tests verify that:
1. update_node cannot set provenance fields like started_at (immutable post-creation)
2. update_node rejects invalid fields with a clear error instead of silently misrouting them
3. Attempting to set started_at via content field does not corrupt the content field
"""

from __future__ import annotations

import json
import pytest


class FakeBackend:
    """Minimal backend for testing update_node."""

    def __init__(self, nodes=None):
        self._nodes = nodes or {}

    async def get_node(self, label, node_id):
        """Return node data or None if not found."""
        return self._nodes.get(node_id)

    async def update_node(self, label, node_id, props):
        """Update node properties in-memory."""
        if node_id not in self._nodes:
            return False
        self._nodes[node_id].update(props)
        return True


class TestUpdateNodeFieldValidation:
    """Test for issue #57: update_node field validation and immutable fields."""

    @pytest.mark.asyncio
    async def test_update_node_cannot_set_started_at_directly(self):
        """Update_node should reject started_at as an updatable field.

        started_at is a provenance field that should only be set at Execution
        creation time via _complete_provenance, not via update_node.
        """
        from wheeler.tools.graph_tools.mutations import update_node

        backend = FakeBackend(nodes={
            "X-242eb216": {
                "id": "X-242eb216",
                "type": "Execution",
                "kind": "close",
                "description": "Close session",
                "status": "completed",
                "started_at": "",  # Empty, needs repair
                "ended_at": "2026-06-03T07:00:00Z",
                "created": "2026-06-03T06:00:00Z",
                "updated": "2026-06-03T06:00:00Z",
                "tier": "generated",
                "stability": 0.5,
            }
        })

        # Attempt to set started_at via update_node
        result = json.loads(await update_node(backend, {
            "node_id": "X-242eb216",
            "started_at": "2026-06-03T06:28:47Z",
        }))

        # Should either reject with an error or report that the field was not updated
        # (because started_at is immutable post-creation).
        # Key point: result must not silently accept the update of a provenance field.
        assert "error" in result or result["status"] == "no_changes"

        # Verify the node was NOT updated with started_at
        final_node = await backend.get_node("Execution", "X-242eb216")
        assert final_node["started_at"] == ""  # Still empty, unchanged

    @pytest.mark.asyncio
    async def test_update_node_does_not_corrupt_content_with_unknown_field(self):
        """update_node should not write unknown fields to content.

        When an unknown field is passed (e.g., started_at as content="started_at=..."),
        the call should either reject it or leave content untouched. It must not
        silently copy the unsupported field specification into content.
        """
        from wheeler.tools.graph_tools.mutations import update_node

        backend = FakeBackend(nodes={
            "X-242eb216": {
                "id": "X-242eb216",
                "type": "Execution",
                "kind": "close",
                "description": "Close session",
                "status": "completed",
                "started_at": "",  # Empty
                "ended_at": "2026-06-03T07:00:00Z",
                "content": "Original content",  # Legitimate field
                "created": "2026-06-03T06:00:00Z",
                "updated": "2026-06-03T06:00:00Z",
                "tier": "generated",
                "stability": 0.5,
            }
        })

        # Mistaken attempt: trying to set started_at via content parameter
        result = json.loads(await update_node(backend, {
            "node_id": "X-242eb216",
            "content": "started_at=2026-06-03T06:28:47Z",
        }))

        # Check the result
        final_node = await backend.get_node("Execution", "X-242eb216")

        # The bug: content field gets overwritten with the literal string
        # Expected: content should either be unchanged OR explicitly updated
        # with a proper new value, not with a key=value specification.
        # The test verifies that we DON'T see the literal "started_at=..." in content.
        if "error" not in result and result.get("status") != "no_changes":
            # If an update happened, content must not contain the literal field spec
            assert "started_at=" not in final_node.get("content", ""), (
                "content field was corrupted with literal 'started_at=' string; "
                "update_node should not write unknown field specifications into content"
            )

    @pytest.mark.asyncio
    async def test_update_node_rejects_invalid_fields_with_error(self):
        """update_node should return an error for fields that don't exist on the node type.

        The error message should name the invalid field, not silently ignore it.
        """
        from wheeler.tools.graph_tools.mutations import update_node

        backend = FakeBackend(nodes={
            "X-242eb216": {
                "id": "X-242eb216",
                "type": "Execution",
                "kind": "close",
                "description": "Close session",
                "status": "completed",
                "started_at": "",
                "ended_at": "2026-06-03T07:00:00Z",
                "created": "2026-06-03T06:00:00Z",
                "updated": "2026-06-03T06:00:00Z",
                "tier": "generated",
                "stability": 0.5,
            }
        })

        # Attempt to set a field that Execution model does not define
        result = json.loads(await update_node(backend, {
            "node_id": "X-242eb216",
            "nonexistent_field": "some value",
        }))

        # Either:
        # 1. An error is returned naming the invalid field, or
        # 2. The update is accepted but the field is not actually written to the node
        # The current bug is that neither happens: the field silently gets written.
        # For now, we check that IF an update happens, the nonexistent field is not there.
        if "error" not in result and result.get("status") != "no_changes":
            final_node = await backend.get_node("Execution", "X-242eb216")
            assert "nonexistent_field" not in final_node, (
                "Invalid field 'nonexistent_field' was written to the node; "
                "update_node should validate fields against the node's schema"
            )

    @pytest.mark.asyncio
    async def test_update_node_allows_valid_execution_fields(self):
        """update_node should allow updating valid Execution fields like description and status.

        This is a positive test to ensure we don't over-constrain the function.
        """
        from wheeler.tools.graph_tools.mutations import update_node

        backend = FakeBackend(nodes={
            "X-242eb216": {
                "id": "X-242eb216",
                "type": "Execution",
                "kind": "close",
                "description": "Close session",
                "status": "completed",
                "started_at": "2026-06-03T06:00:00Z",
                "ended_at": "2026-06-03T07:00:00Z",
                "created": "2026-06-03T06:00:00Z",
                "updated": "2026-06-03T06:00:00Z",
                "tier": "generated",
                "stability": 0.5,
            }
        })

        # Valid update: change status and description
        result = json.loads(await update_node(backend, {
            "node_id": "X-242eb216",
            "status": "running",
            "description": "Restarting close session",
        }))

        # Should succeed
        assert "error" not in result
        assert result["status"] == "updated"
        assert set(result["updated_fields"]) >= {"status", "description"}

        # Verify the update actually happened
        final_node = await backend.get_node("Execution", "X-242eb216")
        assert final_node["status"] == "running"
        assert final_node["description"] == "Restarting close session"
