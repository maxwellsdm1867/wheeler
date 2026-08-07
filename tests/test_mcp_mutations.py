"""Tests for wheeler.mcp_mutations module.

Ported from the deleted test_mcp_server.py: the monolith carried private copies
of these helpers, the split servers are now the only home.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

class TestGraphToolWrappers:
    """Graph tools delegate to graph_tools.execute_tool — mock that."""

    @pytest.mark.asyncio
    async def test_add_finding_delegates(self):
        mock_result = json.dumps({"node_id": "F-test1234", "label": "Finding", "status": "created"})
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result) as mock_exec:
            from wheeler.mcp_mutations import add_finding
            result = await add_finding("test finding", 0.9)
        assert result["node_id"] == "F-test1234"
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        assert call_args[0][0] == "add_finding"
        assert call_args[0][1]["description"] == "test finding"
        assert call_args[0][1]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_add_finding_includes_session_id(self):
        from wheeler.mcp_mutations import _SESSION_ID
        mock_result = json.dumps({"node_id": "F-sid01234", "label": "Finding", "status": "created"})
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result) as mock_exec:
            from wheeler.mcp_mutations import add_finding
            await add_finding("session test", 0.7)
        args_dict = mock_exec.call_args[0][1]
        assert args_dict["session_id"] == _SESSION_ID

    @pytest.mark.asyncio
    async def test_mutation_tools_include_session_id(self):
        """All mutation MCP handlers should pass session_id in their args."""
        from wheeler.mcp_mutations import _SESSION_ID
        from wheeler.mcp_mutations import (
            add_finding, add_hypothesis, add_question, add_note,
            add_dataset, add_paper, add_document,
        )

        async def _check(coro_fn, mock_result):
            with patch("wheeler.mcp_mutations.graph_tools.execute_tool",
                       new_callable=AsyncMock, return_value=mock_result) as mock_exec:
                await coro_fn()
            args_dict = mock_exec.call_args[0][1]
            tool_name = mock_exec.call_args[0][0]
            assert "session_id" in args_dict, f"Missing session_id for {tool_name}"
            assert args_dict["session_id"] == _SESSION_ID, f"Wrong session_id for {tool_name}"

        await _check(
            lambda: add_finding("test", 0.5),
            json.dumps({"node_id": "F-sid00001", "label": "Finding", "status": "created"}),
        )
        await _check(
            lambda: add_hypothesis("test"),
            json.dumps({"node_id": "H-sid00002", "label": "Hypothesis", "status": "created"}),
        )
        await _check(
            lambda: add_question("test?"),
            json.dumps({"node_id": "Q-sid00003", "label": "OpenQuestion", "status": "created"}),
        )
        await _check(
            lambda: add_note("test note"),
            json.dumps({"node_id": "N-sid00004", "label": "ResearchNote", "status": "created"}),
        )
        await _check(
            lambda: add_dataset("/data", "csv", "test"),
            json.dumps({"node_id": "D-sid00005", "label": "Dataset", "status": "created"}),
        )
        await _check(
            lambda: add_paper("test paper"),
            json.dumps({"node_id": "P-sid00006", "label": "Paper", "status": "created"}),
        )
        await _check(
            lambda: add_document("test doc", "/doc.md"),
            json.dumps({"node_id": "W-sid00007", "label": "Document", "status": "created"}),
        )

    @pytest.mark.asyncio
    async def test_add_hypothesis_delegates(self):
        mock_result = json.dumps({"node_id": "H-test1234", "label": "Hypothesis", "status": "created"})
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_mutations import add_hypothesis
            result = await add_hypothesis("test hypothesis")
        assert result["node_id"] == "H-test1234"


class TestUnlinkNodesMCP:
    """unlink_nodes MCP wrapper delegates to graph_tools.execute_tool."""

    @pytest.mark.asyncio
    async def test_unlink_delegates(self):
        mock_result = json.dumps({"status": "unlinked", "source": "F-abc12345", "target": "H-def67890", "relationship": "SUPPORTS"})
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result) as mock_exec:
            from wheeler.mcp_mutations import unlink_nodes
            result = await unlink_nodes("F-abc12345", "H-def67890", "SUPPORTS")
        assert result["status"] == "unlinked"
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        assert call_args[0][0] == "unlink_nodes"
        assert call_args[0][1]["source_id"] == "F-abc12345"
        assert call_args[0][1]["target_id"] == "H-def67890"
        assert call_args[0][1]["relationship"] == "SUPPORTS"

class TestDeleteNodeMCP:
    """delete_node MCP wrapper delegates to graph_tools.execute_tool."""

    @pytest.mark.asyncio
    async def test_delete_delegates(self):
        mock_result = json.dumps({"status": "deleted", "node_id": "F-abc12345", "label": "Finding"})
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result) as mock_exec:
            from wheeler.mcp_mutations import delete_node
            result = await delete_node("F-abc12345")
        assert result["status"] == "deleted"
        assert result["node_id"] == "F-abc12345"
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        assert call_args[0][0] == "delete_node"
        assert call_args[0][1]["node_id"] == "F-abc12345"
