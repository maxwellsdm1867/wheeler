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
            "graph_status",
            "graph_context",
            "add_finding",
            "add_hypothesis",
            "add_question",
            "link_nodes",
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
            "detect_stale",
            "hash_file",
            "init_schema",
            "query_papers",
            "query_documents",
            "search_findings",
            "index_node",
        }
        assert expected == tool_names

    @pytest.mark.asyncio
    async def test_tool_count(self):
        tools = await mcp.list_tools()
        assert len(tools) == 25

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
    async def test_graph_gaps_delegates(self):
        mock_result = json.dumps({"total_gaps": 0, "unlinked_questions": [], "unsupported_hypotheses": [], "analyses_without_findings": []})
        with patch("wheeler.mcp_server.graph_tools.execute_tool", new_callable=AsyncMock, return_value=mock_result):
            from wheeler.mcp_server import graph_gaps
            result = await graph_gaps()
        assert result["total_gaps"] == 0


class TestGraphStatus:
    @pytest.mark.asyncio
    async def test_graph_status_delegates(self):
        mock_counts = {"Finding": 3, "Hypothesis": 1}
        with patch("wheeler.mcp_server.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            from wheeler.mcp_server import graph_status
            result = await graph_status()
        assert result == {"Finding": 3, "Hypothesis": 1}


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
    """search_findings delegates to EmbeddingStore — mock it."""

    @pytest.mark.asyncio
    async def test_search_returns_structure(self):
        @dataclass
        class FakeResult:
            node_id: str
            label: str
            text: str
            score: float

        mock_results = [
            FakeResult(node_id="F-test1234", label="Finding", text="test finding", score=0.95),
        ]
        mock_store = MagicMock()
        mock_store.search.return_value = mock_results
        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import search_findings

            result = await search_findings("test query", limit=5)
        assert result["count"] == 1
        assert result["results"][0]["node_id"] == "F-test1234"
        assert result["results"][0]["score"] == 0.95
        assert result["query"] == "test query"

    @pytest.mark.asyncio
    async def test_search_handles_import_error(self):
        with patch("wheeler.mcp_server._get_embedding_store", side_effect=ImportError("no fastembed")):
            from wheeler.mcp_server import search_findings

            result = await search_findings("test")
        assert "error" in result
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_search_passes_label_filter(self):
        mock_store = MagicMock()
        mock_store.search.return_value = []
        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import search_findings

            await search_findings("test", label="Finding")
        mock_store.search.assert_called_once_with("test", limit=10, label_filter="Finding")

    @pytest.mark.asyncio
    async def test_search_empty_label_passes_none(self):
        mock_store = MagicMock()
        mock_store.search.return_value = []
        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import search_findings

            await search_findings("test", label="")
        mock_store.search.assert_called_once_with("test", limit=10, label_filter=None)


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
