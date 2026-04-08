"""Tests for wheeler.communities module."""

import pytest
from wheeler.communities import connected_components, find_communities


class TestConnectedComponents:
    def test_empty_edges(self):
        assert connected_components([]) == []

    def test_single_edge(self):
        result = connected_components([("A", "B")])
        assert len(result) == 1
        assert result[0] == {"A", "B"}

    def test_two_components(self):
        edges = [("A", "B"), ("B", "C"), ("D", "E")]
        result = connected_components(edges)
        assert len(result) == 2
        assert result[0] == {"A", "B", "C"}  # larger first
        assert result[1] == {"D", "E"}

    def test_triangle(self):
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        result = connected_components(edges)
        assert len(result) == 1
        assert result[0] == {"A", "B", "C"}

    def test_sorted_by_size(self):
        edges = [("A", "B"), ("C", "D"), ("C", "E"), ("C", "F")]
        result = connected_components(edges)
        assert len(result) == 2
        assert len(result[0]) == 4  # C-D-E-F
        assert len(result[1]) == 2  # A-B

    def test_chain(self):
        edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")]
        result = connected_components(edges)
        assert len(result) == 1
        assert result[0] == {"A", "B", "C", "D", "E"}

    def test_self_loop(self):
        edges = [("A", "A"), ("A", "B")]
        result = connected_components(edges)
        assert len(result) == 1
        assert result[0] == {"A", "B"}

    def test_isolated_nodes_not_found(self):
        # Nodes only appear if they're in edges
        edges = [("A", "B")]
        result = connected_components(edges)
        assert len(result) == 1
        assert "C" not in result[0]


class TestFindCommunities:
    @pytest.mark.asyncio
    async def test_find_communities_with_min_size(self):
        """Communities smaller than min_size are filtered out."""
        from unittest.mock import patch, AsyncMock
        from wheeler.config import load_config

        config = load_config()

        # 3 edges: one component of 3, one of 2
        mock_backend = AsyncMock()
        mock_backend.run_cypher = AsyncMock(return_value=[
            {"source": "F-aaa", "target": "F-bbb", "rel_type": "SUPPORTS"},
            {"source": "F-bbb", "target": "F-ccc", "rel_type": "SUPPORTS"},
            {"source": "F-ddd", "target": "F-eee", "rel_type": "SUPPORTS"},
        ])

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=mock_backend):
            with patch("wheeler.knowledge.store.read_node", side_effect=FileNotFoundError):
                result = await find_communities(config, min_size=3)

        assert result["total_communities"] == 1
        assert result["communities"][0]["size"] == 3
        assert result["filtered_below_min_size"] == 1

    @pytest.mark.asyncio
    async def test_find_communities_empty_graph(self):
        """Empty graph returns empty communities."""
        from unittest.mock import patch, AsyncMock
        from wheeler.config import load_config

        config = load_config()
        mock_backend = AsyncMock()
        mock_backend.run_cypher = AsyncMock(return_value=[])

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=mock_backend):
            result = await find_communities(config, min_size=3)

        assert result["total_communities"] == 0
        assert result["communities"] == []

    @pytest.mark.asyncio
    async def test_find_communities_handles_graph_error(self):
        """Graph error returns empty result, doesn't crash."""
        from unittest.mock import patch, AsyncMock
        from wheeler.config import load_config

        config = load_config()
        mock_backend = AsyncMock()
        mock_backend.run_cypher = AsyncMock(side_effect=Exception("Neo4j down"))

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=mock_backend):
            result = await find_communities(config, min_size=3)

        assert result["total_communities"] == 0

    @pytest.mark.asyncio
    async def test_community_has_label_counts(self):
        """Each community includes label distribution."""
        from unittest.mock import patch, AsyncMock
        from wheeler.config import load_config

        config = load_config()
        mock_backend = AsyncMock()
        mock_backend.run_cypher = AsyncMock(return_value=[
            {"source": "F-aaa", "target": "H-bbb", "rel_type": "SUPPORTS"},
            {"source": "F-ccc", "target": "H-bbb", "rel_type": "SUPPORTS"},
        ])

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=mock_backend):
            with patch("wheeler.knowledge.store.read_node", side_effect=FileNotFoundError):
                result = await find_communities(config, min_size=3)

        assert result["total_communities"] == 1
        labels = result["communities"][0]["labels"]
        assert labels["Finding"] == 2
        assert labels["Hypothesis"] == 1
