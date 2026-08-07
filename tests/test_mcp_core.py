"""Tests for wheeler.mcp_core module.

Ported from the deleted test_mcp_server.py: the monolith carried private copies
of these helpers, the split servers are now the only home.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGraphStatus:
    @pytest.mark.asyncio
    async def test_graph_status_delegates(self):
        mock_counts = {"Finding": 3, "Hypothesis": 1}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_core import graph_status
            result = await graph_status()
        assert result == {"Finding": 3, "Hypothesis": 1}

    @pytest.mark.asyncio
    async def test_graph_status_offline_returns_remediation(self):
        """When get_status returns _status=offline, graph_status surfaces it clearly."""
        mock_counts = {"Finding": 0, "Hypothesis": 0, "_status": "offline", "_error": "Connection refused"}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_core import graph_status
            result = await graph_status()
        assert result["status"] == "offline"
        assert result["blocking"] is True
        assert "remediation" in result
        assert "Connection refused" in result["error"]
        # The node_counts should not include _status or _error
        assert "_status" not in result["node_counts"]
        assert "_error" not in result["node_counts"]

class TestGetStatusOffline:
    """Test that schema.get_status marks offline state instead of silently returning zeros."""

    @pytest.mark.asyncio
    async def test_get_status_offline_includes_status_key(self):
        """When Neo4j is unreachable, get_status returns _status=offline and _error."""
        from wheeler.graph.schema import get_status
        from wheeler.config import load_config
        config = load_config()
        # Force a bad URI to guarantee connection failure
        config.neo4j.uri = "bolt://localhost:1"
        result = await get_status(config)
        assert result.get("_status") == "offline"
        assert "_error" in result
        assert isinstance(result["_error"], str)
        assert len(result["_error"]) > 0

    @pytest.mark.asyncio
    async def test_get_status_offline_still_has_zeroed_counts(self):
        """Offline result still contains zeroed counts for backward compatibility."""
        from wheeler.graph.schema import get_status
        from wheeler.models import NODE_LABELS
        from wheeler.config import load_config
        config = load_config()
        config.neo4j.uri = "bolt://localhost:1"
        result = await get_status(config)
        for label in NODE_LABELS:
            assert label in result
            assert result[label] == 0

class TestGraphHealth:
    @pytest.mark.asyncio
    async def test_graph_health_connected(self):
        mock_counts = {"Finding": 3, "Hypothesis": 1}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_core import graph_health
            result = await graph_health()
        assert result["status"] == "connected"
        assert result["node_count"] == 4
        assert "blocking" not in result

    @pytest.mark.asyncio
    async def test_graph_health_offline_via_status_key(self):
        """When get_status returns _status=offline, graph_health includes remediation."""
        mock_counts = {"Finding": 0, "_status": "offline", "_error": "Connection refused"}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_core import graph_health
            result = await graph_health()
        assert result["status"] == "offline"
        assert result["blocking"] is True
        assert "remediation" in result
        assert "Neo4j Desktop" in result["remediation"]
        assert "docker start" in result["remediation"]
        assert "Connection refused" in result["error"]

    @pytest.mark.asyncio
    async def test_graph_health_offline_via_exception(self):
        """Fallback: if get_status raises, graph_health still includes remediation."""
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, side_effect=RuntimeError("driver crashed")):
            from wheeler.mcp_core import graph_health
            result = await graph_health()
        assert result["status"] == "offline"
        assert result["blocking"] is True
        assert "remediation" in result
        assert "driver crashed" in result["error"]

    @pytest.mark.asyncio
    async def test_graph_health_auth_error_diagnosis(self):
        """Auth errors get a specific diagnosis with password fix instructions."""
        mock_counts = {"_status": "offline", "_error": "authentication failure. Unauthorized"}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_core import graph_health
            result = await graph_health()
        assert result["diagnosis"] == "Neo4j authentication failed"
        assert "wheeler.yaml" in result["remediation"]
        assert "research-graph" in result["remediation"]
        assert isinstance(result["fix"], list)

    @pytest.mark.asyncio
    async def test_graph_health_connection_error_diagnosis(self):
        """Connection refused errors get a specific diagnosis with start instructions."""
        mock_counts = {"_status": "offline", "_error": "Connection refused"}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_core import graph_health
            result = await graph_health()
        assert result["diagnosis"] == "Cannot connect to Neo4j"
        assert "Neo4j Desktop" in result["remediation"]
        assert isinstance(result["fix"], list)

class TestErrorDiagnosis:
    """Test that execute_tool returns helpful error messages for Neo4j failures."""

    @pytest.mark.asyncio
    async def test_auth_error_includes_diagnosis(self):
        """Auth errors from execute_tool include password fix instructions."""
        from wheeler.tools.graph_tools import _diagnose_neo4j_error

        # Simulate a Neo4j auth error via string matching fallback
        class FakeAuthError(Exception):
            pass

        exc = FakeAuthError("authentication failure. Unauthorized")
        result = _diagnose_neo4j_error(exc)
        assert result["diagnosis"] == "Neo4j authentication failed"
        assert "wheeler.yaml" in result["cause"]

    @pytest.mark.asyncio
    async def test_connection_error_includes_diagnosis(self):
        """Connection errors from execute_tool include start instructions."""
        from wheeler.tools.graph_tools import _diagnose_neo4j_error

        exc = ConnectionError("Connection refused to localhost:7687")
        result = _diagnose_neo4j_error(exc)
        assert result["diagnosis"] == "Cannot connect to Neo4j"

    @pytest.mark.asyncio
    async def test_unknown_error_returns_empty(self):
        """Unrecognized errors return empty dict (no misleading diagnosis)."""
        from wheeler.tools.graph_tools import _diagnose_neo4j_error

        exc = ValueError("something weird")
        result = _diagnose_neo4j_error(exc)
        assert result == {}

class TestInitSchema:
    @pytest.mark.asyncio
    async def test_init_schema_returns_count(self):
        with patch("wheeler.mcp_core.schema.init_schema", new_callable=AsyncMock, return_value=["stmt1", "stmt2", "stmt3"]):
            from wheeler.mcp_core import init_schema
            result = await init_schema()
        assert result == {"applied": 3}

class TestSearchFindings:
    """search_findings delegates to multi_search — mock it."""

    @pytest.mark.asyncio
    async def test_search_returns_structure(self):
        mock_results = [
            {"id": "F-test1234", "type": "Finding", "description": "test finding", "rrf_score": 0.95},
        ]
        with patch(
            "wheeler.search.retrieval.multi_search",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            from wheeler.mcp_core import search_findings

            result = await search_findings("test query", limit=5)
        assert result["count"] == 1
        assert result["results"][0]["node_id"] == "F-test1234"
        assert result["results"][0]["score"] == 0.95
        assert result["query"] == "test query"
        assert result["mode"] == "multi"

    @pytest.mark.asyncio
    async def test_search_handles_import_error(self):
        with patch(
            "wheeler.search.retrieval.multi_search",
            new_callable=AsyncMock,
            side_effect=ImportError("no fastembed"),
        ):
            from wheeler.mcp_core import search_findings

            result = await search_findings("test")
        assert "error" in result
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_search_passes_label_filter(self):
        with patch(
            "wheeler.search.retrieval.multi_search",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_multi:
            from wheeler.mcp_core import search_findings

            await search_findings("test", label="Finding")
        mock_multi.assert_awaited_once()
        call_kwargs = mock_multi.call_args
        assert call_kwargs[1]["label"] == "Finding"

    @pytest.mark.asyncio
    async def test_search_empty_label_passes_none(self):
        with patch(
            "wheeler.search.retrieval.multi_search",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_multi:
            from wheeler.mcp_core import search_findings

            await search_findings("test", label="")
        mock_multi.assert_awaited_once()
        call_kwargs = mock_multi.call_args
        assert call_kwargs[1]["label"] == ""

class TestIndexNode:
    """index_node delegates to EmbeddingStore — mock it."""

    @pytest.mark.asyncio
    async def test_index_node_delegates(self):
        mock_store = MagicMock()
        with patch("wheeler.mcp_core._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_core import index_node

            result = await index_node("F-test1234", "Finding", "test text")
        assert result["status"] == "indexed"
        assert result["node_id"] == "F-test1234"
        mock_store.add.assert_called_once_with("F-test1234", "Finding", "test text")
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_handles_import_error(self):
        with patch("wheeler.mcp_core._get_embedding_store", side_effect=ImportError("no fastembed")):
            from wheeler.mcp_core import index_node

            result = await index_node("F-test1234", "Finding", "test text")
        assert "error" in result


class TestGraphGaps:
    """graph_gaps is a read-only core tool that delegates to execute_tool."""

    @pytest.mark.asyncio
    async def test_graph_gaps_delegates(self):
        mock_result = json.dumps({"total_gaps": 0, "unlinked_questions": [], "unsupported_hypotheses": [], "analyses_without_findings": []})
        with patch("wheeler.mcp_core.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_core import graph_gaps
            result = await graph_gaps()
        assert result["total_gaps"] == 0


class TestActTools:
    """list_acts / get_act read the packaged act corpus, never the graph.

    Full coverage of the corpus itself lives in test_acts.py. These check the
    wiring: core serves acts, and it does it without touching the backend.
    """

    @pytest.mark.asyncio
    async def test_list_acts_delegates_to_corpus(self):
        from wheeler import acts
        from wheeler.mcp_core import list_acts

        result = await list_acts()
        assert result["count"] == len(acts.load_acts())
        assert result["acts"][0]["act_id"] in acts.act_ids()

    @pytest.mark.asyncio
    async def test_get_act_returns_body_and_note(self):
        from wheeler.mcp_core import get_act

        result = await get_act("execute")
        assert result["name"] == "wh:execute"
        assert result["body"]
        assert result["orchestration_note"]

    @pytest.mark.asyncio
    async def test_get_act_unknown_name_is_an_error_dict(self):
        from wheeler.mcp_core import get_act

        result = await get_act("no-such-act")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_act_tools_do_not_touch_the_backend(self):
        """Reads of packaged files must not open a graph connection."""
        from wheeler.mcp_core import get_act, list_acts

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            side_effect=AssertionError("act tools must not use the graph backend"),
        ):
            await list_acts()
            await get_act("chat")
