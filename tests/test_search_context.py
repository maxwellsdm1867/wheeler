"""Tests for graph-expanded local search (expand_search_results).

All tests mock the graph backend so they run without a live Neo4j
database. The FakeBackend pattern returns known Cypher results for
predictable assertions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.search.retrieval import expand_search_results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_seed(node_id: str, node_type: str = "Finding", score: float = 0.01) -> dict:
    """Create a minimal seed dict matching multi_search output."""
    return {"id": node_id, "type": node_type, "rrf_score": score}


def _mock_backend(hop1_results: list[dict] | None = None,
                  hop2_results: list[dict] | None = None,
                  hop1_error: Exception | None = None) -> AsyncMock:
    """Build a mock backend whose run_cypher returns controlled results.

    hop1_results: returned for 1-hop queries (those without USED|WAS_GENERATED_BY).
    hop2_results: returned for 2-hop provenance queries.
    hop1_error: if set, 1-hop queries raise this exception.
    """
    backend = AsyncMock()

    async def _cypher_dispatch(query: str, params: dict | None = None):
        if hop1_error and "USED|WAS_GENERATED_BY" not in query:
            raise hop1_error
        if "USED|WAS_GENERATED_BY" in query and "h2" in query:
            # 2-hop provenance query
            return hop2_results or []
        # 1-hop query
        if hop1_error:
            raise hop1_error
        return hop1_results or []

    backend.run_cypher = AsyncMock(side_effect=_cypher_dispatch)
    return backend


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExpandEmptySeeds:
    """Empty seed list returns empty expansion."""

    @pytest.mark.asyncio
    async def test_empty_seeds(self) -> None:
        config = MagicMock()
        backend = _mock_backend()

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result = await expand_search_results([], config)

        assert result["seed_nodes"] == []
        assert result["related_nodes"] == []
        assert result["relationships"] == []
        assert result["total_related"] == 0


class TestExpandSingleSeedOneHop:
    """One seed with one neighbor returns it."""

    @pytest.mark.asyncio
    async def test_single_neighbor(self) -> None:
        config = MagicMock()
        hop1 = [
            {"nid": "H-001", "nlabel": "Hypothesis", "rel": "SUPPORTS", "dir": "out"},
        ]
        backend = _mock_backend(hop1_results=hop1)

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result = await expand_search_results(
                [_make_seed("F-001")], config,
            )

        assert result["total_related"] == 1
        related = result["related_nodes"]
        assert len(related) == 1
        assert related[0]["id"] == "H-001"
        assert related[0]["type"] == "Hypothesis"
        assert related[0]["relationship"] == "SUPPORTS"

        # Should have one relationship edge
        rels = result["relationships"]
        assert len(rels) == 1
        assert rels[0]["source"] == "F-001"
        assert rels[0]["target"] == "H-001"
        assert rels[0]["relationship"] == "SUPPORTS"


class TestExpandDeduplicatesRelated:
    """Same node found from two seeds is deduplicated, keeping closest hop."""

    @pytest.mark.asyncio
    async def test_dedup_keeps_closest(self) -> None:
        config = MagicMock()
        # Both seeds find the same neighbor H-001
        hop1 = [
            {"nid": "H-001", "nlabel": "Hypothesis", "rel": "SUPPORTS", "dir": "out"},
        ]
        backend = _mock_backend(hop1_results=hop1)

        seeds = [_make_seed("F-001"), _make_seed("F-002")]

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result = await expand_search_results(seeds, config)

        # H-001 should appear only once
        related_ids = [r["id"] for r in result["related_nodes"]]
        assert related_ids.count("H-001") == 1
        assert result["total_related"] == 1


class TestExpandExcludesSeedsFromRelated:
    """Seed nodes don't appear in related_nodes."""

    @pytest.mark.asyncio
    async def test_seed_excluded(self) -> None:
        config = MagicMock()
        # F-002 is a neighbor of F-001, but also a seed
        hop1 = [
            {"nid": "F-002", "nlabel": "Finding", "rel": "WAS_DERIVED_FROM", "dir": "out"},
            {"nid": "H-001", "nlabel": "Hypothesis", "rel": "SUPPORTS", "dir": "out"},
        ]
        backend = _mock_backend(hop1_results=hop1)

        seeds = [_make_seed("F-001"), _make_seed("F-002")]

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result = await expand_search_results(seeds, config)

        related_ids = [r["id"] for r in result["related_nodes"]]
        assert "F-001" not in related_ids
        assert "F-002" not in related_ids
        assert "H-001" in related_ids


class TestExpandRanksProvHigher:
    """PROV relationships are ordered before semantic ones."""

    @pytest.mark.asyncio
    async def test_prov_outranks_semantic(self) -> None:
        config = MagicMock()
        hop1 = [
            {"nid": "H-001", "nlabel": "Hypothesis", "rel": "SUPPORTS", "dir": "out"},
            {"nid": "X-001", "nlabel": "Execution", "rel": "WAS_GENERATED_BY", "dir": "in"},
            {"nid": "N-001", "nlabel": "ResearchNote", "rel": "RELEVANT_TO", "dir": "out"},
        ]
        backend = _mock_backend(hop1_results=hop1)

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result = await expand_search_results(
                [_make_seed("F-001")], config,
            )

        related = result["related_nodes"]
        assert len(related) == 3

        # PROV (WAS_GENERATED_BY) should be first, semantic (SUPPORTS) second,
        # other (RELEVANT_TO) third
        assert related[0]["id"] == "X-001"
        assert related[1]["id"] == "H-001"
        assert related[2]["id"] == "N-001"


class TestExpandTwoHopProv:
    """2-hop provenance chain is found and included."""

    @pytest.mark.asyncio
    async def test_two_hop_provenance(self) -> None:
        config = MagicMock()
        hop1 = [
            {"nid": "X-001", "nlabel": "Execution", "rel": "WAS_GENERATED_BY", "dir": "in"},
        ]
        hop2 = [
            {"nid": "S-001", "nlabel": "Script", "rel": "USED", "via": "X-001"},
        ]
        backend = _mock_backend(hop1_results=hop1, hop2_results=hop2)

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result = await expand_search_results(
                [_make_seed("F-001")], config, max_hops_prov=2,
            )

        related = result["related_nodes"]
        related_ids = [r["id"] for r in related]
        assert "X-001" in related_ids
        assert "S-001" in related_ids

        # Both should have their relationship preserved
        s_node = next(r for r in related if r["id"] == "S-001")
        assert s_node["relationship"] == "USED"


class TestExpandHandlesBackendError:
    """Backend failure returns empty expansion, doesn't crash."""

    @pytest.mark.asyncio
    async def test_backend_error_graceful(self) -> None:
        config = MagicMock()
        # Backend raises on all queries
        backend = AsyncMock()
        backend.run_cypher = AsyncMock(side_effect=RuntimeError("connection lost"))

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result = await expand_search_results(
                [_make_seed("F-001")], config,
            )

        # Should not crash, seed passed through with summary fallback
        assert len(result["seed_nodes"]) == 1
        assert result["seed_nodes"][0]["id"] == "F-001"
        assert result["seed_nodes"][0]["score"] == 0.01
        assert result["related_nodes"] == []
        assert result["relationships"] == []
        assert result["total_related"] == 0


class TestExpandSkipsInvalidIds:
    """Seeds with unrecognized prefixes are skipped without error."""

    @pytest.mark.asyncio
    async def test_bad_prefix_skipped(self) -> None:
        config = MagicMock()
        backend = _mock_backend(hop1_results=[
            {"nid": "H-001", "nlabel": "Hypothesis", "rel": "SUPPORTS", "dir": "out"},
        ])

        seeds = [
            {"id": "ZZ-bad", "type": "Unknown", "rrf_score": 0.01},
            _make_seed("F-001"),
        ]

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result = await expand_search_results(seeds, config)

        # Only F-001 should have been expanded (ZZ prefix is unknown)
        assert result["total_related"] == 1
        assert result["related_nodes"][0]["id"] == "H-001"
