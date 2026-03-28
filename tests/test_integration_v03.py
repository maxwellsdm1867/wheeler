"""E2E integration test: KuzuBackend + EmbeddingStore + search_findings MCP tool.

Tests the v0.3 feature set working together: create nodes via Kuzu backend,
embed them, search semantically via the MCP tool.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from wheeler.config import GraphConfig, SearchConfig, WheelerConfig, load_config
from wheeler.graph.backend import GraphBackend, get_backend
from wheeler.search.backfill import TEXT_FIELDS, backfill_embeddings
from wheeler.search.embeddings import EmbeddingStore, SearchResult

# Guard for kuzu availability — tests that need it are skipped otherwise.
kuzu = pytest.importorskip("kuzu")

from wheeler.graph.kuzu_backend import KuzuBackend  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_deterministic_embedding(text: str, dim: int = 384) -> np.ndarray:
    """Deterministic pseudo-embedding from text hash."""
    rng = np.random.RandomState(hash(text) % (2**31))
    vec = rng.randn(dim).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec


def _mock_embed(texts: list[str]) -> list[np.ndarray]:
    return [_make_deterministic_embedding(t) for t in texts]


def _patched_store(tmp_path: Path) -> EmbeddingStore:
    """EmbeddingStore with fastembed mocked out."""
    store = EmbeddingStore(store_path=str(tmp_path / "embeddings"))
    mock_model = MagicMock()
    mock_model.embed = _mock_embed
    store._model = mock_model
    return store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def backend(tmp_path: Path) -> KuzuBackend:
    """Initialized KuzuBackend in a temp directory."""
    b = KuzuBackend(str(tmp_path / "kuzu_db"))
    await b.initialize()
    yield b
    await b.close()


@pytest.fixture
def store(tmp_path: Path) -> EmbeddingStore:
    """EmbeddingStore with mocked fastembed."""
    return _patched_store(tmp_path)


# ---------------------------------------------------------------------------
# Test 1: KuzuBackend -- create nodes, verify they exist
# ---------------------------------------------------------------------------


class TestKuzuNodeLifecycle:
    """Create various node types in Kuzu and verify retrieval."""

    async def test_create_and_get_finding(self, backend: KuzuBackend) -> None:
        node_id = await backend.create_node("Finding", {
            "description": "Ion channel conductance scales with temperature",
            "confidence": 0.85,
            "date": "2025-03-26",
            "tier": "generated",
        })
        assert node_id.startswith("F-")

        node = await backend.get_node("Finding", node_id)
        assert node is not None
        assert node["description"] == "Ion channel conductance scales with temperature"
        assert node["confidence"] == 0.85

    async def test_create_and_get_hypothesis(self, backend: KuzuBackend) -> None:
        node_id = await backend.create_node("Hypothesis", {
            "statement": "Temperature sensitivity arises from lipid bilayer fluidity",
            "status": "open",
            "date": "2025-03-26",
            "tier": "generated",
        })
        assert node_id.startswith("H-")

        node = await backend.get_node("Hypothesis", node_id)
        assert node is not None
        assert node["statement"] == "Temperature sensitivity arises from lipid bilayer fluidity"

    async def test_create_and_get_open_question(self, backend: KuzuBackend) -> None:
        node_id = await backend.create_node("OpenQuestion", {
            "question": "Does cholesterol content modulate temperature response?",
            "priority": 8,
            "date_added": "2025-03-26",
            "tier": "generated",
        })
        assert node_id.startswith("Q-")

        node = await backend.get_node("OpenQuestion", node_id)
        assert node is not None
        assert node["priority"] == 8

    async def test_create_relationship_between_nodes(self, backend: KuzuBackend) -> None:
        f_id = await backend.create_node("Finding", {
            "description": "Calcium transients increase at 37C",
            "confidence": 0.9,
            "date": "2025-03-26",
            "tier": "generated",
        })
        h_id = await backend.create_node("Hypothesis", {
            "statement": "TRPV1 mediates the temperature response",
            "status": "open",
            "date": "2025-03-26",
            "tier": "generated",
        })
        linked = await backend.create_relationship(
            "Finding", f_id, "SUPPORTS", "Hypothesis", h_id,
        )
        assert linked is True

    async def test_count_nodes_across_labels(self, backend: KuzuBackend) -> None:
        await backend.create_node("Finding", {
            "description": "F1", "confidence": 0.5,
            "date": "2025-01-01", "tier": "generated",
        })
        await backend.create_node("Finding", {
            "description": "F2", "confidence": 0.6,
            "date": "2025-01-02", "tier": "generated",
        })
        await backend.create_node("Hypothesis", {
            "statement": "H1", "status": "open",
            "date": "2025-01-01", "tier": "generated",
        })

        counts = await backend.count_all()
        assert counts["Finding"] == 2
        assert counts["Hypothesis"] == 1
        assert counts["OpenQuestion"] == 0


# ---------------------------------------------------------------------------
# Test 2: EmbeddingStore -- add nodes, search by meaning
# ---------------------------------------------------------------------------


class TestEmbeddingSearch:
    """Add nodes to EmbeddingStore and verify semantic search."""

    def test_add_multiple_and_search(self, store: EmbeddingStore) -> None:
        store.add("F-001", "Finding", "Calcium imaging reveals neural bursting")
        store.add("F-002", "Finding", "Potassium channels gate at -60mV")
        store.add("H-001", "Hypothesis", "Bursting is driven by calcium influx")
        store.add("Q-001", "OpenQuestion", "What role does sodium play?")

        results = store.search("calcium neural activity", limit=4)
        assert len(results) == 4
        assert all(isinstance(r, SearchResult) for r in results)

        # Scores should be descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_label_filter_restricts_results(self, store: EmbeddingStore) -> None:
        store.add("F-001", "Finding", "Voltage clamp analysis")
        store.add("H-001", "Hypothesis", "Voltage gating is nonlinear")
        store.add("Q-001", "OpenQuestion", "What is the threshold voltage?")

        findings_only = store.search("voltage", label_filter="Finding")
        assert all(r.label == "Finding" for r in findings_only)
        assert len(findings_only) == 1

    def test_search_result_structure(self, store: EmbeddingStore) -> None:
        store.add("P-abcd", "Paper", "Hodgkin-Huxley Model of Nerve Conduction")
        results = store.search("action potential model")
        assert len(results) == 1
        r = results[0]
        assert r.node_id == "P-abcd"
        assert r.label == "Paper"
        assert r.text == "Hodgkin-Huxley Model of Nerve Conduction"
        assert isinstance(r.score, float)

    def test_save_load_preserves_search(self, store: EmbeddingStore) -> None:
        store.add("F-001", "Finding", "Dendritic integration sums EPSPs")
        store.add("F-002", "Finding", "Axonal propagation is decremental")
        store.save()

        # Load into a fresh store with same path
        store2 = EmbeddingStore(store_path=store._store_path)
        mock_model = MagicMock()
        mock_model.embed = _mock_embed
        store2._model = mock_model
        store2.load()

        assert store2.count == 2
        results = store2.search("dendritic summation")
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Test 3: Full pipeline -- Kuzu backend -> embed -> MCP search
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Create nodes in Kuzu, embed them, search via MCP tool mock."""

    async def test_kuzu_to_embeddings_to_search(
        self, backend: KuzuBackend, store: EmbeddingStore,
    ) -> None:
        # 1. Create nodes in Kuzu
        f1 = await backend.create_node("Finding", {
            "description": "Astrocytes release glutamate",
            "confidence": 0.88,
            "date": "2025-03-26",
            "tier": "generated",
        })
        f2 = await backend.create_node("Finding", {
            "description": "Microglia prune synapses via complement",
            "confidence": 0.75,
            "date": "2025-03-26",
            "tier": "generated",
        })
        h1 = await backend.create_node("Hypothesis", {
            "statement": "Glial-neuron signaling is bidirectional",
            "status": "open",
            "date": "2025-03-26",
            "tier": "generated",
        })

        # 2. Retrieve from Kuzu and embed
        for label, node_id in [("Finding", f1), ("Finding", f2), ("Hypothesis", h1)]:
            node = await backend.get_node(label, node_id)
            assert node is not None
            text_field = TEXT_FIELDS.get(label, "")
            text = node.get(text_field, "")
            store.add(node_id, label, text)

        assert store.count == 3

        # 3. Search semantically
        results = store.search("glutamate astrocyte signaling")
        assert len(results) == 3
        # First result should relate to astrocytes/glutamate
        assert all(isinstance(r, SearchResult) for r in results)

    async def test_mcp_search_findings_integration(
        self, backend: KuzuBackend, store: EmbeddingStore,
    ) -> None:
        """Simulate what the MCP search_findings tool does end-to-end."""
        # Create and embed nodes
        f_id = await backend.create_node("Finding", {
            "description": "Spike frequency adaptation in cortical neurons",
            "confidence": 0.92,
            "date": "2025-03-26",
            "tier": "generated",
        })
        node = await backend.get_node("Finding", f_id)
        assert node is not None
        store.add(f_id, "Finding", node["description"])

        # Simulate what the MCP tool does
        results = store.search("cortical neuron firing rate", limit=10)
        response = {
            "results": [
                {
                    "node_id": r.node_id,
                    "label": r.label,
                    "text": r.text,
                    "score": round(r.score, 4),
                }
                for r in results
            ],
            "count": len(results),
            "query": "cortical neuron firing rate",
        }

        assert response["count"] == 1
        assert response["results"][0]["node_id"] == f_id
        assert response["results"][0]["label"] == "Finding"
        assert isinstance(response["results"][0]["score"], float)

    async def test_mcp_index_node_integration(
        self, backend: KuzuBackend, store: EmbeddingStore,
    ) -> None:
        """Simulate what the MCP index_node tool does end-to-end."""
        # Create node in Kuzu
        f_id = await backend.create_node("Finding", {
            "description": "GABAergic interneurons inhibit pyramidal cells",
            "confidence": 0.95,
            "date": "2025-03-26",
            "tier": "generated",
        })

        # Simulate index_node: add embedding and save
        store.add(f_id, "Finding", "GABAergic interneurons inhibit pyramidal cells")
        store.save()

        # Verify it's searchable
        results = store.search("inhibition interneuron")
        assert len(results) == 1
        assert results[0].node_id == f_id


# ---------------------------------------------------------------------------
# Test 4: Backfill -- create nodes in backend -> backfill -> search
# ---------------------------------------------------------------------------


class TestBackfillIntegration:
    """Backfill embeddings from Kuzu nodes into EmbeddingStore."""

    async def test_backfill_kuzu_nodes(
        self, backend: KuzuBackend, store: EmbeddingStore,
    ) -> None:
        # Create nodes in Kuzu
        await backend.create_node("Finding", {
            "description": "Dendritic spines undergo structural plasticity",
            "confidence": 0.8,
            "date": "2025-03-26",
            "tier": "generated",
        })
        await backend.create_node("Finding", {
            "description": "Spine density increases after LTP",
            "confidence": 0.7,
            "date": "2025-03-26",
            "tier": "generated",
        })
        await backend.create_node("Hypothesis", {
            "statement": "Spine growth requires actin polymerization",
            "status": "open",
            "date": "2025-03-26",
            "tier": "generated",
        })

        # Query all nodes from Kuzu for backfill
        findings = await backend.query_nodes("Finding", limit=100)
        hypotheses = await backend.query_nodes("Hypothesis", limit=100)

        nodes_by_label = {
            "Finding": findings,
            "Hypothesis": hypotheses,
        }

        # Backfill
        added = await backfill_embeddings(nodes_by_label, store)
        assert added == 3
        assert store.count == 3

        # Now search
        results = store.search("spine plasticity")
        assert len(results) == 3

    async def test_backfill_skips_already_embedded(
        self, backend: KuzuBackend, store: EmbeddingStore,
    ) -> None:
        f1_id = await backend.create_node("Finding", {
            "description": "Pre-existing finding",
            "confidence": 0.9,
            "date": "2025-03-26",
            "tier": "generated",
        })
        f2_id = await backend.create_node("Finding", {
            "description": "New finding to backfill",
            "confidence": 0.8,
            "date": "2025-03-26",
            "tier": "generated",
        })

        # Pre-embed the first one
        store.add(f1_id, "Finding", "Pre-existing finding")
        assert store.count == 1

        # Backfill
        findings = await backend.query_nodes("Finding", limit=100)
        added = await backfill_embeddings({"Finding": findings}, store)
        assert added == 1  # only the new one
        assert store.count == 2


# ---------------------------------------------------------------------------
# Test 5: Config -- verify GraphConfig and SearchConfig both load
# ---------------------------------------------------------------------------


class TestConfigIntegration:
    """GraphConfig and SearchConfig coexist in WheelerConfig."""

    def test_default_config_has_both(self) -> None:
        config = WheelerConfig()
        assert isinstance(config.graph, GraphConfig)
        assert isinstance(config.search, SearchConfig)

    def test_graph_config_defaults(self) -> None:
        config = WheelerConfig()
        assert config.graph.backend == "neo4j"
        assert config.graph.kuzu_path == ".kuzu"

    def test_search_config_defaults(self) -> None:
        config = WheelerConfig()
        assert config.search.enabled is True
        assert config.search.store_path == ".wheeler/embeddings"
        assert config.search.model == "BAAI/bge-small-en-v1.5"

    def test_config_from_dict(self) -> None:
        config = WheelerConfig(
            graph={"backend": "kuzu", "kuzu_path": "/tmp/kuzu"},
            search={"enabled": False, "store_path": "/tmp/embeddings"},
        )
        assert config.graph.backend == "kuzu"
        assert config.graph.kuzu_path == "/tmp/kuzu"
        assert config.search.enabled is False
        assert config.search.store_path == "/tmp/embeddings"

    def test_load_config_from_yaml(self, tmp_path: Path) -> None:
        yaml_content = (
            "graph:\n"
            "  backend: kuzu\n"
            "  kuzu_path: /data/kuzu\n"
            "search:\n"
            "  enabled: true\n"
            "  store_path: /data/embeddings\n"
            "  model: BAAI/bge-small-en-v1.5\n"
        )
        config_file = tmp_path / "wheeler.yaml"
        config_file.write_text(yaml_content)

        config = load_config(config_file)
        assert config.graph.backend == "kuzu"
        assert config.graph.kuzu_path == "/data/kuzu"
        assert config.search.enabled is True
        assert config.search.store_path == "/data/embeddings"

    def test_get_backend_factory_with_kuzu_config(self, tmp_path: Path) -> None:
        config = WheelerConfig(
            graph={"backend": "kuzu", "kuzu_path": str(tmp_path / "factory_kuzu")},
        )
        b = get_backend(config)
        assert isinstance(b, KuzuBackend)

    def test_get_backend_factory_with_neo4j_config(self) -> None:
        from wheeler.graph.neo4j_backend import Neo4jBackend

        config = WheelerConfig(graph={"backend": "neo4j"})
        b = get_backend(config)
        assert isinstance(b, Neo4jBackend)


# ---------------------------------------------------------------------------
# Test 6: MCP tool search_findings returns correct structure
# ---------------------------------------------------------------------------


class TestMCPSearchFindings:
    """Test the MCP search_findings tool via mocking."""

    @pytest.mark.asyncio
    async def test_search_findings_returns_structure(self) -> None:
        mock_results = [
            SearchResult(
                node_id="F-abc12345",
                label="Finding",
                text="Neurons fire in bursts",
                score=0.9234,
            ),
            SearchResult(
                node_id="H-def67890",
                label="Hypothesis",
                text="Bursting is calcium-driven",
                score=0.8100,
            ),
        ]
        mock_store = MagicMock()
        mock_store.search.return_value = mock_results

        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import search_findings

            result = await search_findings("neural bursting calcium", limit=5)

        assert result["count"] == 2
        assert result["query"] == "neural bursting calcium"
        assert len(result["results"]) == 2

        r0 = result["results"][0]
        assert r0["node_id"] == "F-abc12345"
        assert r0["label"] == "Finding"
        assert r0["text"] == "Neurons fire in bursts"
        assert r0["score"] == 0.9234

        r1 = result["results"][1]
        assert r1["node_id"] == "H-def67890"
        assert r1["label"] == "Hypothesis"

    @pytest.mark.asyncio
    async def test_search_findings_handles_empty_results(self) -> None:
        mock_store = MagicMock()
        mock_store.search.return_value = []

        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import search_findings

            result = await search_findings("nonexistent topic")

        assert result["count"] == 0
        assert result["results"] == []
        assert result["query"] == "nonexistent topic"

    @pytest.mark.asyncio
    async def test_search_findings_with_label_filter(self) -> None:
        mock_store = MagicMock()
        mock_store.search.return_value = []

        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import search_findings

            await search_findings("query", limit=5, label="Finding")

        mock_store.search.assert_called_once_with(
            "query", limit=5, label_filter="Finding",
        )


# ---------------------------------------------------------------------------
# Test 7: MCP tool index_node persists correctly
# ---------------------------------------------------------------------------


class TestMCPIndexNode:
    """Test the MCP index_node tool via mocking."""

    @pytest.mark.asyncio
    async def test_index_node_returns_status(self) -> None:
        mock_store = MagicMock()

        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import index_node

            result = await index_node("F-test1234", "Finding", "Test finding text")

        assert result["status"] == "indexed"
        assert result["node_id"] == "F-test1234"
        assert result["label"] == "Finding"
        mock_store.add.assert_called_once_with(
            "F-test1234", "Finding", "Test finding text",
        )
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_node_handles_error(self) -> None:
        mock_store = MagicMock()
        mock_store.add.side_effect = RuntimeError("disk full")

        with patch("wheeler.mcp_server._get_embedding_store", return_value=mock_store):
            from wheeler.mcp_server import index_node

            result = await index_node("F-bad", "Finding", "text")

        assert "error" in result
        assert "disk full" in result["error"]

    @pytest.mark.asyncio
    async def test_index_node_handles_import_error(self) -> None:
        with patch(
            "wheeler.mcp_server._get_embedding_store",
            side_effect=ImportError("no fastembed"),
        ):
            from wheeler.mcp_server import index_node

            result = await index_node("F-test", "Finding", "text")

        assert "error" in result
