"""Tests for wheeler.mcp_query module.

Ported from the deleted test_mcp_server.py. These lived in the monolith's
TestGraphToolWrappers, which spanned three servers; the read-only query_* wrappers
belong here.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest


class TestQueryToolWrappers:
    """query_* tools delegate to graph_tools.execute_tool."""

    @pytest.mark.asyncio
    async def test_query_findings_delegates(self):
        mock_result = json.dumps({"findings": [], "count": 0})
        with patch("wheeler.mcp_query.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_query import query_findings
            result = await query_findings(keyword="test", limit=5)
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_query_analyses_delegates(self):
        mock_result = json.dumps({"analyses": [], "count": 0})
        with patch("wheeler.mcp_query.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_query import query_analyses
            result = await query_analyses(keyword="matlab", limit=5)
        assert result["count"] == 0
