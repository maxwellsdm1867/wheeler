"""Tests for Neo4j fulltext index integration (RRF channel 4)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.config import WheelerConfig
from wheeler.graph.schema import INDEXES


class TestFulltextIndexInSchema:
    def test_fulltext_index_in_indexes_list(self):
        """The fulltext index CREATE statement must be in the INDEXES list."""
        fulltext_stmts = [
            stmt for stmt in INDEXES if "FULLTEXT" in stmt and "wheeler_fulltext" in stmt
        ]
        assert len(fulltext_stmts) == 1, (
            f"Expected exactly 1 fulltext index statement, found {len(fulltext_stmts)}"
        )

    def test_fulltext_index_covers_expected_labels(self):
        """The fulltext index must cover Finding, Hypothesis, OpenQuestion, Paper, Document, ResearchNote."""
        fulltext_stmt = next(s for s in INDEXES if "wheeler_fulltext" in s)
        for label in ("Finding", "Hypothesis", "OpenQuestion", "Paper", "Document", "ResearchNote"):
            assert label in fulltext_stmt, f"Fulltext index missing label: {label}"

    def test_fulltext_index_uses_search_text_property(self):
        """The fulltext index must index the _search_text property."""
        fulltext_stmt = next(s for s in INDEXES if "wheeler_fulltext" in s)
        assert "_search_text" in fulltext_stmt


class TestFulltextChannelReturnsResults:
    @pytest.mark.asyncio
    async def test_fulltext_channel_returns_node_ids(self):
        """_fulltext_channel should return node IDs from Cypher results."""
        from wheeler.search.retrieval import _fulltext_channel

        config = WheelerConfig()
        mock_backend = AsyncMock()
        mock_backend.run_cypher.return_value = [
            {"id": "F-aaa11111", "type": "Finding", "score": 2.5},
            {"id": "H-bbb22222", "type": "Hypothesis", "score": 1.8},
        ]

        with patch("wheeler.tools.graph_tools._get_backend", return_value=mock_backend):
            result = await _fulltext_channel("spike generation", config, 10, "")

        assert result == ["F-aaa11111", "H-bbb22222"]

    @pytest.mark.asyncio
    async def test_fulltext_channel_filters_empty_ids(self):
        """Nodes with empty or missing IDs should be excluded."""
        from wheeler.search.retrieval import _fulltext_channel

        config = WheelerConfig()
        mock_backend = AsyncMock()
        mock_backend.run_cypher.return_value = [
            {"id": "F-aaa11111", "type": "Finding", "score": 2.5},
            {"id": "", "type": "Finding", "score": 1.0},
            {"type": "Finding", "score": 0.5},
        ]

        with patch("wheeler.tools.graph_tools._get_backend", return_value=mock_backend):
            result = await _fulltext_channel("test query", config, 10, "")

        assert result == ["F-aaa11111"]


class TestFulltextChannelWithNamespaceFilter:
    @pytest.mark.asyncio
    async def test_project_tag_adds_where_clause(self):
        """When project_tag is set, the Cypher must filter by _wheeler_project."""
        from wheeler.search.retrieval import _fulltext_channel

        config = WheelerConfig()
        config.neo4j.project_tag = "my-project"

        mock_backend = AsyncMock()
        mock_backend.run_cypher.return_value = []

        with patch("wheeler.tools.graph_tools._get_backend", return_value=mock_backend):
            await _fulltext_channel("test query", config, 10, "")

        # Inspect the Cypher query passed to run_cypher
        call_args = mock_backend.run_cypher.call_args
        cypher_query = call_args[0][0]
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})

        assert "_wheeler_project" in cypher_query
        assert "$ptag" in cypher_query
        assert params.get("ptag") == "my-project"

    @pytest.mark.asyncio
    async def test_label_filter_adds_label_check(self):
        """When label is specified, the Cypher must include a label filter."""
        from wheeler.search.retrieval import _fulltext_channel

        config = WheelerConfig()
        mock_backend = AsyncMock()
        mock_backend.run_cypher.return_value = []

        with patch("wheeler.tools.graph_tools._get_backend", return_value=mock_backend):
            await _fulltext_channel("test query", config, 10, "Finding")

        call_args = mock_backend.run_cypher.call_args
        cypher_query = call_args[0][0]
        assert "'Finding' IN labels(node)" in cypher_query

    @pytest.mark.asyncio
    async def test_no_project_tag_omits_namespace_filter(self):
        """Without project_tag, the Cypher should NOT include _wheeler_project."""
        from wheeler.search.retrieval import _fulltext_channel

        config = WheelerConfig()
        config.neo4j.project_tag = ""

        mock_backend = AsyncMock()
        mock_backend.run_cypher.return_value = []

        with patch("wheeler.tools.graph_tools._get_backend", return_value=mock_backend):
            await _fulltext_channel("test query", config, 10, "")

        call_args = mock_backend.run_cypher.call_args
        cypher_query = call_args[0][0]
        assert "_wheeler_project" not in cypher_query


class TestFulltextChannelGracefulDegradation:
    @pytest.mark.asyncio
    async def test_backend_error_returns_empty_list(self):
        """If the fulltext index does not exist, the channel returns []."""
        from wheeler.search.retrieval import _fulltext_channel

        config = WheelerConfig()
        mock_backend = AsyncMock()
        mock_backend.run_cypher.side_effect = Exception(
            "There is no fulltext index called 'wheeler_fulltext'"
        )

        with patch("wheeler.tools.graph_tools._get_backend", return_value=mock_backend):
            result = await _fulltext_channel("test query", config, 10, "")

        assert result == []

    @pytest.mark.asyncio
    async def test_backend_unavailable_returns_empty_list(self):
        """If the backend cannot be reached, the channel returns []."""
        from wheeler.search.retrieval import _fulltext_channel

        config = WheelerConfig()

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            side_effect=ConnectionError("Neo4j unavailable"),
        ):
            result = await _fulltext_channel("test query", config, 10, "")

        assert result == []


class TestSearchTextInExecuteTool:
    """Verify _search_text is set on mutation tools in execute_tool."""

    @pytest.mark.asyncio
    async def test_search_text_set_after_mutation(self):
        """execute_tool should call update_node with _search_text after add_finding."""
        from wheeler.tools.graph_tools import execute_tool

        config = WheelerConfig()
        config.knowledge_path = "/tmp/test-knowledge-nonexistent"

        mock_backend = AsyncMock()
        mock_backend.create_node = AsyncMock()
        # Simulate the add_finding handler returning a result
        finding_result = json.dumps({
            "status": "created",
            "node_id": "F-test1234",
            "label": "Finding",
        })

        # Patch the handler to return known result, and _get_backend to return our mock
        with patch("wheeler.tools.graph_tools._get_backend", return_value=mock_backend):
            with patch(
                "wheeler.tools.graph_tools._TOOL_REGISTRY",
                {"add_finding": AsyncMock(return_value=finding_result)},
            ):
                with patch("wheeler.tools.graph_tools._write_knowledge_file", return_value=(True, True)):
                    await execute_tool(
                        "add_finding",
                        {"description": "spike frequency doubles at 22C", "confidence": 0.85},
                        config,
                    )

        # Check that update_node was called with _search_text
        update_calls = [
            c for c in mock_backend.update_node.call_args_list
            if "_search_text" in (c[0][2] if len(c[0]) > 2 else c[1].get("properties", {}))
        ]
        assert len(update_calls) == 1
        props = update_calls[0][0][2]
        assert props["_search_text"] == "spike frequency doubles at 22C"


class TestMultiSearchIncludesFulltext:
    """Verify fulltext mode is wired into multi_search."""

    @pytest.mark.asyncio
    async def test_fulltext_mode_standalone(self):
        """mode='fulltext' should only run the fulltext channel."""
        from wheeler.search.retrieval import multi_search

        config = WheelerConfig()

        with patch(
            "wheeler.search.retrieval._fulltext_channel",
            new_callable=AsyncMock,
            return_value=["F-aaa11111"],
        ) as mock_ft:
            with patch(
                "wheeler.search.retrieval._semantic_channel",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_sem:
                with patch(
                    "wheeler.search.retrieval._keyword_channel",
                    new_callable=AsyncMock,
                    return_value=[],
                ) as mock_kw:
                    with patch(
                        "wheeler.search.retrieval._temporal_channel",
                        new_callable=AsyncMock,
                        return_value=[],
                    ) as mock_tmp:
                        results = await multi_search(
                            "test", config, limit=5, mode="fulltext",
                        )

        # Fulltext called, others not
        mock_ft.assert_called_once()
        mock_sem.assert_not_called()
        mock_kw.assert_not_called()
        mock_tmp.assert_not_called()
        assert len(results) == 1
        assert results[0]["id"] == "F-aaa11111"
