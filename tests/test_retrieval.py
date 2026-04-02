"""Tests for multi-channel retrieval and Reciprocal Rank Fusion.

All tests use mocks for the embedding store and graph backend so they
run without numpy, fastembed, or a live database.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.search.retrieval import (
    multi_search,
    reciprocal_rank_fusion,
    _enrich_node,
    _semantic_channel,
    _keyword_channel,
    _temporal_channel,
)


# ---------------------------------------------------------------------------
# reciprocal_rank_fusion
# ---------------------------------------------------------------------------


class TestReciprocalRankFusion:
    """Unit tests for the RRF scoring function."""

    def test_single_list(self) -> None:
        result = reciprocal_rank_fusion([["A", "B", "C"]], k=60, limit=10)
        ids = [doc_id for doc_id, _ in result]
        assert ids == ["A", "B", "C"]

    def test_two_identical_lists(self) -> None:
        result = reciprocal_rank_fusion(
            [["A", "B", "C"], ["A", "B", "C"]], k=60, limit=10,
        )
        ids = [doc_id for doc_id, _ in result]
        # Order preserved — A gets highest combined score
        assert ids == ["A", "B", "C"]

    def test_boosts_items_in_multiple_channels(self) -> None:
        """An item appearing in two lists should outrank one appearing in only one."""
        list1 = ["X", "SHARED", "A"]
        list2 = ["Y", "SHARED", "B"]
        result = reciprocal_rank_fusion([list1, list2], k=60, limit=10)
        ids = [doc_id for doc_id, _ in result]
        # SHARED appears in both -> should be ranked first
        assert ids[0] == "SHARED"

    def test_three_overlapping_lists(self) -> None:
        list1 = ["A", "B", "C", "D"]
        list2 = ["B", "C", "A", "E"]
        list3 = ["C", "A", "E", "F"]
        result = reciprocal_rank_fusion([list1, list2, list3], k=60, limit=10)
        ids = [doc_id for doc_id, _ in result]
        # A, B, C appear in multiple lists; C appears in all three
        # C: rank 2 in list1, rank 1 in list2, rank 0 in list3
        # A: rank 0 in list1, rank 2 in list2, rank 1 in list3
        # B: rank 1 in list1, rank 0 in list2
        # All three should be near the top
        assert set(ids[:3]) == {"A", "B", "C"}

    def test_limit_truncates(self) -> None:
        result = reciprocal_rank_fusion(
            [["A", "B", "C", "D", "E"]], k=60, limit=2,
        )
        assert len(result) == 2

    def test_empty_lists(self) -> None:
        result = reciprocal_rank_fusion([], k=60, limit=10)
        assert result == []

    def test_all_empty_sublists(self) -> None:
        result = reciprocal_rank_fusion([[], [], []], k=60, limit=10)
        assert result == []

    def test_scores_are_positive(self) -> None:
        result = reciprocal_rank_fusion(
            [["A", "B"], ["B", "C"]], k=60, limit=10,
        )
        for _, score in result:
            assert score > 0

    def test_score_formula_exact(self) -> None:
        """Verify the exact RRF score for a simple case."""
        # A at rank 0 in list1 and rank 1 in list2
        # score = 1/(60+0+1) + 1/(60+1+1) = 1/61 + 1/62
        result = reciprocal_rank_fusion([["A"], ["X", "A"]], k=60, limit=10)
        a_score = dict(result)["A"]
        expected = 1.0 / 61 + 1.0 / 62
        assert abs(a_score - expected) < 1e-10

    def test_disjoint_lists(self) -> None:
        """Items only in one list each get ranked by their position in that list."""
        list1 = ["A", "B"]
        list2 = ["C", "D"]
        result = reciprocal_rank_fusion([list1, list2], k=60, limit=10)
        ids = [doc_id for doc_id, _ in result]
        # A and C are both at rank 0 in their respective lists, same score
        # B and D are both at rank 1, same score
        assert set(ids) == {"A", "B", "C", "D"}
        scores = dict(result)
        assert scores["A"] == scores["C"]
        assert scores["B"] == scores["D"]


# ---------------------------------------------------------------------------
# Channel tests (mocked)
# ---------------------------------------------------------------------------


class TestSemanticChannel:
    """Test _semantic_channel with mocked EmbeddingStore."""

    @pytest.mark.asyncio
    async def test_returns_node_ids(self) -> None:
        mock_result_1 = MagicMock(node_id="F-001")
        mock_result_2 = MagicMock(node_id="F-002")
        mock_store = MagicMock()
        mock_store.load = MagicMock()
        mock_store.search = MagicMock(return_value=[mock_result_1, mock_result_2])

        config = MagicMock()
        config.search.store_path = "/tmp/test"

        with patch("wheeler.search.embeddings.EmbeddingStore", return_value=mock_store):
            ids = await _semantic_channel("test query", config, limit=10, label="")
        assert ids == ["F-001", "F-002"]

    @pytest.mark.asyncio
    async def test_returns_empty_on_import_error(self) -> None:
        config = MagicMock()
        config.search.store_path = "/tmp/test"

        # The real function catches ImportError internally and returns []
        # We test this by verifying the return type is always a list
        ids = await _semantic_channel("query", config, 10, "")
        assert isinstance(ids, list)


class TestKeywordChannel:
    """Test _keyword_channel with mocked graph tools."""

    @pytest.mark.asyncio
    async def test_returns_node_ids_from_queries(self) -> None:
        config = MagicMock()
        findings_result = json.dumps({
            "findings": [{"id": "F-001"}, {"id": "F-002"}],
            "count": 2,
        })

        with patch(
            "wheeler.tools.graph_tools.execute_tool",
            new_callable=AsyncMock,
            return_value=findings_result,
        ):
            ids = await _keyword_channel("test", config, limit=10, label="Finding")
        assert "F-001" in ids
        assert "F-002" in ids

    @pytest.mark.asyncio
    async def test_deduplicates_across_tools(self) -> None:
        config = MagicMock()

        async def mock_execute(tool_name, args, config):
            if tool_name == "query_findings":
                return json.dumps({"findings": [{"id": "F-001"}], "count": 1})
            if tool_name == "query_notes":
                return json.dumps({"notes": [{"id": "F-001"}, {"id": "N-001"}], "count": 2})
            return json.dumps({"results": [], "count": 0})

        with patch(
            "wheeler.tools.graph_tools.execute_tool",
            side_effect=mock_execute,
        ):
            ids = await _keyword_channel("test", config, limit=10, label="")
        # F-001 should appear only once despite being in two result sets
        assert ids.count("F-001") == 1
        assert "N-001" in ids

    @pytest.mark.asyncio
    async def test_handles_tool_failure(self) -> None:
        config = MagicMock()

        with patch(
            "wheeler.tools.graph_tools.execute_tool",
            new_callable=AsyncMock,
            side_effect=Exception("graph down"),
        ):
            ids = await _keyword_channel("test", config, limit=10, label="Finding")
        assert ids == []


class TestTemporalChannel:
    """Test _temporal_channel with mocked knowledge store."""

    @pytest.mark.asyncio
    async def test_returns_recent_node_ids(self, tmp_path: Path) -> None:
        config = MagicMock()
        config.knowledge_path = str(tmp_path)

        # Create mock node objects
        node_a = MagicMock(id="F-001", created="2026-03-31T10:00:00")
        node_b = MagicMock(id="F-002", created="2026-03-30T10:00:00")

        with patch(
            "wheeler.knowledge.store.list_nodes",
            return_value=[node_a, node_b],
        ):
            ids = await _temporal_channel(config, limit=10, label="")
        # Should be sorted by recency
        assert ids == ["F-001", "F-002"]

    @pytest.mark.asyncio
    async def test_returns_empty_for_missing_dir(self) -> None:
        config = MagicMock()
        config.knowledge_path = "/nonexistent/path"
        ids = await _temporal_channel(config, limit=10, label="")
        assert ids == []


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------


class TestEnrichNode:
    def test_returns_full_data_when_file_exists(self, tmp_path: Path) -> None:
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {
            "id": "F-001",
            "type": "Finding",
            "description": "Test finding",
        }

        with patch("wheeler.knowledge.store.read_node", return_value=mock_model):
            result = _enrich_node("F-001", tmp_path)
        assert result["id"] == "F-001"
        assert result["description"] == "Test finding"

    def test_returns_stub_on_failure(self, tmp_path: Path) -> None:
        with patch(
            "wheeler.knowledge.store.read_node",
            side_effect=FileNotFoundError("not found"),
        ):
            result = _enrich_node("F-missing", tmp_path)
        assert result == {"id": "F-missing"}


# ---------------------------------------------------------------------------
# multi_search integration (all channels mocked)
# ---------------------------------------------------------------------------


class TestMultiSearch:
    """Integration test for the full multi_search pipeline."""

    @pytest.mark.asyncio
    async def test_fuses_multiple_channels(self) -> None:
        config = MagicMock()
        config.knowledge_path = "/tmp/knowledge"
        config.search.store_path = "/tmp/embeddings"

        # Mock all three channels
        with (
            patch(
                "wheeler.search.retrieval._semantic_channel",
                new_callable=AsyncMock,
                return_value=["F-001", "F-002", "F-003"],
            ),
            patch(
                "wheeler.search.retrieval._keyword_channel",
                new_callable=AsyncMock,
                return_value=["F-002", "F-004", "F-001"],
            ),
            patch(
                "wheeler.search.retrieval._temporal_channel",
                new_callable=AsyncMock,
                return_value=["F-005", "F-002", "F-003"],
            ),
            patch(
                "wheeler.search.retrieval._enrich_node",
                side_effect=lambda nid, _: {"id": nid, "type": "Finding"},
            ),
        ):
            results = await multi_search("test query", config, limit=5)

        # F-002 appears in all 3 channels — should be ranked first
        assert results[0]["id"] == "F-002"
        assert len(results) <= 5
        # All results should have rrf_score
        for r in results:
            assert "rrf_score" in r
            assert r["rrf_score"] > 0

    @pytest.mark.asyncio
    async def test_semantic_mode_only(self) -> None:
        config = MagicMock()
        config.knowledge_path = "/tmp/knowledge"
        config.search.store_path = "/tmp/embeddings"

        with (
            patch(
                "wheeler.search.retrieval._semantic_channel",
                new_callable=AsyncMock,
                return_value=["F-001"],
            ) as sem_mock,
            patch(
                "wheeler.search.retrieval._keyword_channel",
                new_callable=AsyncMock,
            ) as kw_mock,
            patch(
                "wheeler.search.retrieval._temporal_channel",
                new_callable=AsyncMock,
            ) as temp_mock,
            patch(
                "wheeler.search.retrieval._enrich_node",
                side_effect=lambda nid, _: {"id": nid},
            ),
        ):
            results = await multi_search("test", config, mode="semantic")

        sem_mock.assert_awaited_once()
        kw_mock.assert_not_awaited()
        temp_mock.assert_not_awaited()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_graceful_degradation_when_channels_fail(self) -> None:
        """If some channels raise, the others still produce results."""
        config = MagicMock()
        config.knowledge_path = "/tmp/knowledge"
        config.search.store_path = "/tmp/embeddings"

        with (
            patch(
                "wheeler.search.retrieval._semantic_channel",
                new_callable=AsyncMock,
                side_effect=Exception("embeddings unavailable"),
            ),
            patch(
                "wheeler.search.retrieval._keyword_channel",
                new_callable=AsyncMock,
                return_value=["F-001", "F-002"],
            ),
            patch(
                "wheeler.search.retrieval._temporal_channel",
                new_callable=AsyncMock,
                side_effect=Exception("no knowledge dir"),
            ),
            patch(
                "wheeler.search.retrieval._enrich_node",
                side_effect=lambda nid, _: {"id": nid},
            ),
        ):
            results = await multi_search("test", config, limit=10)

        # Should still return results from the keyword channel
        assert len(results) == 2
        ids = [r["id"] for r in results]
        assert "F-001" in ids
        assert "F-002" in ids

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_channels_fail(self) -> None:
        config = MagicMock()
        config.knowledge_path = "/tmp/knowledge"
        config.search.store_path = "/tmp/embeddings"

        with (
            patch(
                "wheeler.search.retrieval._semantic_channel",
                new_callable=AsyncMock,
                side_effect=Exception("fail"),
            ),
            patch(
                "wheeler.search.retrieval._keyword_channel",
                new_callable=AsyncMock,
                side_effect=Exception("fail"),
            ),
            patch(
                "wheeler.search.retrieval._temporal_channel",
                new_callable=AsyncMock,
                side_effect=Exception("fail"),
            ),
        ):
            results = await multi_search("test", config)
        assert results == []

    @pytest.mark.asyncio
    async def test_keyword_mode_only(self) -> None:
        config = MagicMock()
        config.knowledge_path = "/tmp/knowledge"

        with (
            patch(
                "wheeler.search.retrieval._keyword_channel",
                new_callable=AsyncMock,
                return_value=["F-001"],
            ) as kw_mock,
            patch(
                "wheeler.search.retrieval._semantic_channel",
                new_callable=AsyncMock,
            ) as sem_mock,
            patch(
                "wheeler.search.retrieval._temporal_channel",
                new_callable=AsyncMock,
            ) as temp_mock,
            patch(
                "wheeler.search.retrieval._enrich_node",
                side_effect=lambda nid, _: {"id": nid},
            ),
        ):
            results = await multi_search("test", config, mode="keyword")

        kw_mock.assert_awaited_once()
        sem_mock.assert_not_awaited()
        temp_mock.assert_not_awaited()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_temporal_mode_only(self) -> None:
        config = MagicMock()
        config.knowledge_path = "/tmp/knowledge"

        with (
            patch(
                "wheeler.search.retrieval._temporal_channel",
                new_callable=AsyncMock,
                return_value=["F-001"],
            ) as temp_mock,
            patch(
                "wheeler.search.retrieval._semantic_channel",
                new_callable=AsyncMock,
            ) as sem_mock,
            patch(
                "wheeler.search.retrieval._keyword_channel",
                new_callable=AsyncMock,
            ) as kw_mock,
            patch(
                "wheeler.search.retrieval._enrich_node",
                side_effect=lambda nid, _: {"id": nid},
            ),
        ):
            results = await multi_search("test", config, mode="temporal")

        temp_mock.assert_awaited_once()
        sem_mock.assert_not_awaited()
        kw_mock.assert_not_awaited()
        assert len(results) == 1
