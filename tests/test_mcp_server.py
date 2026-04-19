"""Tests for wheeler.mcp_server module."""

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.mcp_server import mcp


class TestToolRegistration:
    """Verify all expected tools are registered with FastMCP."""

    @pytest.mark.asyncio
    async def test_all_expected_tools_registered(self):
        tools = await mcp.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "graph_health",
            "graph_status",
            "run_cypher",
            "add_analysis",
            "graph_context",
            "add_finding",
            "add_hypothesis",
            "add_question",
            "link_nodes",
            "unlink_nodes",
            "delete_node",
            "query_findings",
            "query_hypotheses",
            "query_open_questions",
            "query_datasets",
            "graph_gaps",
            "add_dataset",
            "add_paper",
            "add_document",
            "set_tier",
            "extract_citations",
            "validate_citations",
            "scan_workspace",
            "scan_dependencies",
            "detect_stale",
            "hash_file",
            "init_schema",
            "query_papers",
            "query_documents",
            "search_findings",
            "index_node",
            "show_node",
            "add_note",
            "query_notes",
            "query_analyses",
            "query_executions",
            "add_execution",
            "request_log_summary",
            "graph_consistency_check",
            "validate_task_contract",
            "search_context",
            "compute_retrieval_quality",
            "detect_communities",
            "propose_merge",
            "execute_merge",
            "update_node",
        }
        assert expected == tool_names

    @pytest.mark.asyncio
    async def test_tool_count(self):
        tools = await mcp.list_tools()
        assert len(tools) == 46

    @pytest.mark.asyncio
    async def test_all_tools_have_descriptions(self):
        tools = await mcp.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} has no description"


class TestExtractCitations:
    """extract_citations is pure regex — no mocking needed."""

    @pytest.mark.asyncio
    async def test_extract_finds_citations(self):
        from wheeler.mcp_server import extract_citations
        result = await extract_citations("See [F-3a2b] and [H-0012abcd]")
        assert result == ["F-3a2b", "H-0012abcd"]

    @pytest.mark.asyncio
    async def test_extract_empty_text(self):
        from wheeler.mcp_server import extract_citations
        result = await extract_citations("No citations here")
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_deduplicates(self):
        from wheeler.mcp_server import extract_citations
        result = await extract_citations("[F-3a2b] repeated [F-3a2b]")
        assert result == ["F-3a2b"]


class TestScanWorkspace:
    """scan_workspace uses filesystem — mock at the workspace module level."""

    @pytest.mark.asyncio
    async def test_scan_returns_structure(self):
        from wheeler.workspace import WorkspaceSummary, FileInfo
        mock_summary = WorkspaceSummary(
            project_dir="/tmp/test",
            scripts=[FileInfo(path="analysis.py", category="script", extension=".py", size_bytes=1024)],
            data_files=[FileInfo(path="data.mat", category="data", extension=".mat", size_bytes=2048)],
            total_files=2,
        )
        with patch("wheeler.mcp_server.workspace.scan_workspace", return_value=mock_summary):
            from wheeler.mcp_server import scan_workspace
            result = await scan_workspace()
        assert result["project_dir"] == "/tmp/test"
        assert result["total_files"] == 2
        assert len(result["scripts"]) == 1
        assert result["scripts"][0]["path"] == "analysis.py"
        assert len(result["data_files"]) == 1


class TestHashFile:
    @pytest.mark.asyncio
    async def test_hash_returns_dict(self):
        with patch("wheeler.mcp_server.provenance.hash_file", return_value="abc123"):
            from wheeler.mcp_server import hash_file
            result = await hash_file("/tmp/test.py")
        assert result == {"path": "/tmp/test.py", "sha256": "abc123"}


class TestSessionId:
    """Verify that _SESSION_ID is generated at module level and has the right format."""

    def test_session_id_format(self):
        from wheeler.mcp_server import _SESSION_ID
        assert _SESSION_ID.startswith("session-")
        hex_part = _SESSION_ID.removeprefix("session-")
        assert len(hex_part) == 8  # token_hex(4) -> 8 hex chars
        int(hex_part, 16)  # should not raise — valid hex

    def test_session_id_is_stable_within_import(self):
        from wheeler.mcp_server import _SESSION_ID as sid1
        from wheeler.mcp_server import _SESSION_ID as sid2
        assert sid1 == sid2  # same module, same value


class TestGraphToolWrappers:
    """Graph tools delegate to graph_tools.execute_tool — mock that."""

    @pytest.mark.asyncio
    async def test_add_finding_delegates(self):
        mock_result = json.dumps({"node_id": "F-test1234", "label": "Finding", "status": "created"})
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result) as mock_exec:
            from wheeler.mcp_server import add_finding
            result = await add_finding("test finding", 0.9)
        assert result["node_id"] == "F-test1234"
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        assert call_args[0][0] == "add_finding"
        assert call_args[0][1]["description"] == "test finding"
        assert call_args[0][1]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_add_finding_includes_session_id(self):
        from wheeler.mcp_server import _SESSION_ID
        mock_result = json.dumps({"node_id": "F-sid01234", "label": "Finding", "status": "created"})
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result) as mock_exec:
            from wheeler.mcp_server import add_finding
            await add_finding("session test", 0.7)
        args_dict = mock_exec.call_args[0][1]
        assert args_dict["session_id"] == _SESSION_ID

    @pytest.mark.asyncio
    async def test_mutation_tools_include_session_id(self):
        """All mutation MCP handlers should pass session_id in their args."""
        from wheeler.mcp_server import _SESSION_ID
        from wheeler.mcp_server import (
            add_finding, add_hypothesis, add_question, add_note,
            add_dataset, add_paper, add_document,
        )

        async def _check(coro_fn, mock_result):
            with patch("wheeler.mcp_server.graph_tools.execute_tool",
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
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_server import add_hypothesis
            result = await add_hypothesis("test hypothesis")
        assert result["node_id"] == "H-test1234"

    @pytest.mark.asyncio
    async def test_query_findings_delegates(self):
        mock_result = json.dumps({"findings": [], "count": 0})
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_server import query_findings
            result = await query_findings(keyword="test", limit=5)
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_query_analyses_delegates(self):
        mock_result = json.dumps({"analyses": [], "count": 0})
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_server import query_analyses
            result = await query_analyses(keyword="matlab", limit=5)
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_graph_gaps_delegates(self):
        mock_result = json.dumps({"total_gaps": 0, "unlinked_questions": [], "unsupported_hypotheses": [], "analyses_without_findings": []})
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_server import graph_gaps
            result = await graph_gaps()
        assert result["total_gaps"] == 0


class TestUnlinkNodesMCP:
    """unlink_nodes MCP wrapper delegates to graph_tools.execute_tool."""

    @pytest.mark.asyncio
    async def test_unlink_delegates(self):
        mock_result = json.dumps({"status": "unlinked", "source": "F-abc12345", "target": "H-def67890", "relationship": "SUPPORTS"})
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result) as mock_exec:
            from wheeler.mcp_server import unlink_nodes
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
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result) as mock_exec:
            from wheeler.mcp_server import delete_node
            result = await delete_node("F-abc12345")
        assert result["status"] == "deleted"
        assert result["node_id"] == "F-abc12345"
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        assert call_args[0][0] == "delete_node"
        assert call_args[0][1]["node_id"] == "F-abc12345"


class TestGraphStatus:
    @pytest.mark.asyncio
    async def test_graph_status_delegates(self):
        mock_counts = {"Finding": 3, "Hypothesis": 1}
        with patch("wheeler.mcp_server.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_server import graph_status
            result = await graph_status()
        assert result == {"Finding": 3, "Hypothesis": 1}

    @pytest.mark.asyncio
    async def test_graph_status_offline_returns_remediation(self):
        """When get_status returns _status=offline, graph_status surfaces it clearly."""
        mock_counts = {"Finding": 0, "Hypothesis": 0, "_status": "offline", "_error": "Connection refused"}
        with patch("wheeler.mcp_server.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_server import graph_status
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
        with patch("wheeler.mcp_server.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_server import graph_health
            result = await graph_health()
        assert result["status"] == "connected"
        assert result["node_count"] == 4
        assert "blocking" not in result

    @pytest.mark.asyncio
    async def test_graph_health_offline_via_status_key(self):
        """When get_status returns _status=offline, graph_health includes remediation."""
        mock_counts = {"Finding": 0, "_status": "offline", "_error": "Connection refused"}
        with patch("wheeler.mcp_server.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_server import graph_health
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
        with patch("wheeler.mcp_server.schema.get_status", new_callable=AsyncMock, side_effect=RuntimeError("driver crashed")):
            from wheeler.mcp_server import graph_health
            result = await graph_health()
        assert result["status"] == "offline"
        assert result["blocking"] is True
        assert "remediation" in result
        assert "driver crashed" in result["error"]

    @pytest.mark.asyncio
    async def test_graph_health_auth_error_diagnosis(self):
        """Auth errors get a specific diagnosis with password fix instructions."""
        mock_counts = {"_status": "offline", "_error": "authentication failure. Unauthorized"}
        with patch("wheeler.mcp_server.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_server import graph_health
            result = await graph_health()
        assert result["diagnosis"] == "Neo4j authentication failed"
        assert "wheeler.yaml" in result["remediation"]
        assert "research-graph" in result["remediation"]
        assert isinstance(result["fix"], list)

    @pytest.mark.asyncio
    async def test_graph_health_connection_error_diagnosis(self):
        """Connection refused errors get a specific diagnosis with start instructions."""
        mock_counts = {"_status": "offline", "_error": "Connection refused"}
        with patch("wheeler.mcp_server.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_server import graph_health
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
        with patch("wheeler.mcp_server.schema.init_schema", new_callable=AsyncMock, return_value=["stmt1", "stmt2", "stmt3"]):
            from wheeler.mcp_server import init_schema
            result = await init_schema()
        assert result == {"applied": 3}


class TestValidateCitations:
    @pytest.mark.asyncio
    async def test_validate_returns_structure(self):
        from wheeler.validation.citations import CitationResult, CitationStatus
        mock_results = [
            CitationResult(node_id="F-3a2b", status=CitationStatus.VALID, label="Finding"),
            CitationResult(node_id="H-0000", status=CitationStatus.NOT_FOUND, label="Hypothesis", details="not found"),
        ]
        with patch("wheeler.mcp_server.citations.validate_citations", new_callable=AsyncMock, return_value=mock_results):
            from wheeler.mcp_server import validate_citations
            result = await validate_citations("See [F-3a2b] and [H-0000]")
        assert result["total"] == 2
        assert result["valid"] == 1
        assert result["results"][0]["status"] == "valid"
        assert result["results"][1]["status"] == "not_found"


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
            from wheeler.mcp_server import search_findings

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
            from wheeler.mcp_server import search_findings

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
            from wheeler.mcp_server import search_findings

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
            from wheeler.mcp_server import search_findings

            await search_findings("test", label="")
        mock_multi.assert_awaited_once()
        call_kwargs = mock_multi.call_args
        assert call_kwargs[1]["label"] == ""


class TestIndexNode:
    """index_node delegates to EmbeddingStore — mock it."""

    @pytest.mark.asyncio
    async def test_index_node_delegates(self):
        mock_store = MagicMock()
        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import index_node

            result = await index_node("F-test1234", "Finding", "test text")
        assert result["status"] == "indexed"
        assert result["node_id"] == "F-test1234"
        mock_store.add.assert_called_once_with("F-test1234", "Finding", "test text")
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_handles_import_error(self):
        with patch("wheeler.mcp_server._get_embedding_store", side_effect=ImportError("no fastembed")):
            from wheeler.mcp_server import index_node

            result = await index_node("F-test1234", "Finding", "test text")
        assert "error" in result


class TestScanDependencies:
    """scan_dependencies delegates to depscanner — test MCP wrapper."""

    @pytest.mark.asyncio
    async def test_scan_returns_structure(self, tmp_path):
        script = tmp_path / "test_script.py"
        script.write_text("import numpy as np\ndf = np.load('data.npy')\n")

        from wheeler.mcp_server import scan_dependencies
        result = await scan_dependencies(str(script))

        assert "imports" in result
        assert "data_files" in result
        assert "function_calls" in result
        assert "numpy" in result["imports"]
        assert any(d["path"] == "data.npy" for d in result["data_files"])

    @pytest.mark.asyncio
    async def test_scan_file_not_found(self):
        from wheeler.mcp_server import scan_dependencies
        result = await scan_dependencies("/nonexistent/path.py")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_scan_syntax_error(self, tmp_path):
        script = tmp_path / "bad.py"
        script.write_text("def broken(\n")

        from wheeler.mcp_server import scan_dependencies
        result = await scan_dependencies(str(script))
        assert "error" in result
