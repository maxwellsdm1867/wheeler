"""Regression test for issue #101: cannot clear a string field.

https://github.com/maxwellsdm/wheeler/issues/101

The bug: update_node treats empty string as "field not supplied", so
passing path="" returns "No fields to update" instead of clearing the field.

This test verifies that:
1. A string field can be cleared via update_node by passing an empty string
2. The response reports the change (not "No fields to update")
3. The change is recorded in the node's change_log
4. Omitting a parameter still means "leave unchanged"
5. The clear propagates through execute_tool to all three triple-write
   layers (Neo4j, knowledge/{id}.json, synthesis/{id}.md)
"""

import json
import re
import uuid
from pathlib import Path

import pytest

from wheeler.config import load_config, project_knowledge_dir, project_synthesis_dir
from wheeler.graph.backend import get_backend
from wheeler.graph.schema import generate_node_id
from wheeler.tools.graph_tools import execute_tool, mutations

# render.py emits "**Path**: <value>" only when the model's path is truthy,
# and joins it with the other metadata using " | ". Matching the live entry
# specifically matters: a cleared path can still appear elsewhere in the
# file as audit history, so scanning for the raw string would be wrong.
_LIVE_PATH_RE = re.compile(r"\*\*Path\*\*:\s*([^|\n]*)")


def _live_path(markdown: str) -> str | None:
    """Return the live Path value rendered in synthesis markdown, or None."""
    match = _LIVE_PATH_RE.search(markdown)
    return match.group(1).strip() if match else None


@pytest.fixture
async def backend_and_config(e2e_config):
    """Set up backend for test.

    Takes `e2e_config` rather than calling `load_config()`: the suite walls unit
    tests off from the keychain, so a bare `load_config()` here resolves to
    localhost while this directory's availability probe checks the graph the
    project actually uses. The two disagreeing turned a stopped local instance
    into failures instead of skips.
    """
    config = e2e_config
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


class TestClearPropagatesThroughTripleWrite:
    """Clearing a field must reach all three triple-write layers.

    The tests above call the mutation handler directly, which skips both
    validate_and_normalize and the triple-write in execute_tool. That
    leaves JSON and synthesis propagation unguarded, so this routes
    through execute_tool and reads every layer back off disk.
    """

    @pytest.mark.asyncio
    async def test_clear_path_reaches_graph_json_and_synthesis(
        self, backend_and_config, tmp_path,
    ):
        backend, config = backend_and_config

        marker = f"issue101-triplewrite-{uuid.uuid4().hex[:8]}"
        artifact = tmp_path / "issue101_artifact.md"
        artifact.write_text("placeholder artifact\n")
        # execute_tool normalizes path to absolute, so compare against the
        # resolved form (on macOS tmp_path is a symlink into /private).
        resolved = str(artifact.resolve())

        created = json.loads(await execute_tool(
            "add_document",
            {
                "title": "Issue 101 triple-write guard",
                "path": str(artifact),
                "status": "draft",
                "session_id": marker,
            },
            config,
        ))
        node_id = created.get("node_id")
        assert node_id, f"add_document did not create a node: {created}"

        knowledge_file = project_knowledge_dir(config) / f"{node_id}.json"
        synthesis_file = project_synthesis_dir(config) / f"{node_id}.md"

        try:
            # All three layers carry the path before the clear.
            graph_before = await backend.get_node("Document", node_id)
            assert graph_before is not None
            assert graph_before.get("path") == resolved

            assert knowledge_file.exists(), f"no knowledge file at {knowledge_file}"
            json_before = json.loads(knowledge_file.read_text())
            assert json_before.get("path") == resolved

            assert synthesis_file.exists(), f"no synthesis file at {synthesis_file}"
            assert _live_path(synthesis_file.read_text()) == resolved

            # Clear it through the dispatch path, not the handler.
            result = json.loads(await execute_tool(
                "update_node",
                {"node_id": node_id, "path": "", "session_id": marker},
                config,
            ))
            assert result.get("status") == "updated", (
                f"clearing path through execute_tool failed: {result}"
            )
            assert result.get("changes", {}).get("path") == {
                "old": resolved, "new": "",
            }, f"unexpected changes payload: {result.get('changes')}"

            # Layer 1: Neo4j.
            graph_after = await backend.get_node("Document", node_id)
            assert graph_after is not None
            assert graph_after.get("path") == "", (
                f"graph path not cleared: {repr(graph_after.get('path'))}"
            )

            # Layer 2: knowledge JSON, re-read off disk.
            json_after = json.loads(knowledge_file.read_text())
            assert json_after.get("path") == "", (
                f"knowledge JSON path not cleared (layer drift): "
                f"{repr(json_after.get('path'))}"
            )

            # The clear is recorded in change_log as old -> new.
            path_entries = [
                entry for entry in json_after.get("change_log", [])
                if "path" in entry.get("changes", {})
            ]
            assert path_entries, (
                f"no change_log entry for the cleared path: "
                f"{json_after.get('change_log')}"
            )
            assert path_entries[-1]["changes"]["path"] == [resolved, ""]

            # Layer 3: synthesis no longer renders a live Path entry. The old
            # value may survive as audit history, which is by design, so this
            # asserts on the live entry rather than on the raw string.
            assert _live_path(synthesis_file.read_text()) is None, (
                "synthesis still renders a live Path entry after the clear"
            )

            # _field_specs._check_path short-circuits on the empty string. If
            # that guard regresses, the path is resolved against the process
            # cwd instead of staying cleared.
            for layer, value in (
                ("graph", graph_after.get("path")),
                ("knowledge JSON", json_after.get("path")),
            ):
                assert value != str(Path.cwd()), (
                    f"{layer} path was resolved to the cwd instead of cleared"
                )
        finally:
            await execute_tool(
                "delete_node", {"node_id": node_id, "session_id": marker}, config,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
