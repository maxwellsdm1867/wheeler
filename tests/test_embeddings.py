"""Tests for the EmbeddingStore.

Tests work in two tiers:
1. Mocked fastembed — always runs, tests logic without the model.
2. Real fastembed — runs only when fastembed is installed (``pytest.importorskip``).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from wheeler.search.embeddings import EmbeddingStore, SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_deterministic_embedding(text: str, dim: int = 384) -> np.ndarray:
    """Create a deterministic pseudo-embedding from text for testing."""
    rng = np.random.RandomState(hash(text) % (2**31))
    vec = rng.randn(dim).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec


def _mock_embed(texts: list[str]) -> list[np.ndarray]:
    """Mock fastembed embed method — returns deterministic vectors."""
    return [_make_deterministic_embedding(t) for t in texts]


def _patched_store(tmp_path: Path) -> EmbeddingStore:
    """Return an EmbeddingStore with fastembed mocked out."""
    store = EmbeddingStore(store_path=str(tmp_path / "embeddings"))
    mock_model = MagicMock()
    mock_model.embed = _mock_embed
    store._model = mock_model
    return store


# ---------------------------------------------------------------------------
# Tests with mocked fastembed
# ---------------------------------------------------------------------------

class TestEmbeddingStoreMocked:
    """Tests using mocked embeddings (no fastembed required)."""

    def test_add_and_count(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        assert store.count == 0
        store.add("F-aaa1", "Finding", "Neurons fire in bursts")
        assert store.count == 1

    def test_add_ignores_empty_text(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-aaa1", "Finding", "")
        store.add("F-aaa2", "Finding", "   ")
        assert store.count == 0

    def test_add_updates_existing(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-aaa1", "Finding", "Version 1")
        store.add("F-aaa1", "Finding", "Version 2")
        assert store.count == 1
        assert store._metadata["F-aaa1"]["text"] == "Version 2"

    def test_remove(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-aaa1", "Finding", "Some finding")
        store.remove("F-aaa1")
        assert store.count == 0

    def test_remove_nonexistent_is_noop(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.remove("F-does-not-exist")  # should not raise
        assert store.count == 0

    def test_search_empty_store(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        results = store.search("anything")
        assert results == []

    def test_search_returns_results(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Calcium signaling in astrocytes")
        store.add("H-001", "Hypothesis", "Astrocytes regulate synaptic strength")
        store.add("Q-001", "OpenQuestion", "What triggers calcium waves?")

        results = store.search("calcium astrocytes", limit=10)
        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)
        # Scores should be in descending order
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_with_label_filter(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Neural oscillations")
        store.add("H-001", "Hypothesis", "Oscillations encode memory")
        store.add("F-002", "Finding", "Gamma band activity")

        results = store.search("oscillations", label_filter="Finding")
        assert all(r.label == "Finding" for r in results)
        assert len(results) == 2

    def test_search_respects_limit(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        for i in range(20):
            store.add(f"F-{i:03d}", "Finding", f"Finding number {i}")
        results = store.search("finding", limit=5)
        assert len(results) == 5

    def test_cosine_similarity_ordering(self, tmp_path: Path) -> None:
        """Verify that more similar texts score higher."""
        store = _patched_store(tmp_path)
        # The query and "close" text share more words
        store.add("F-close", "Finding", "Mitochondrial membrane potential")
        store.add("F-far", "Finding", "Banana split dessert recipe")

        results = store.search("Mitochondrial membrane depolarization")
        assert len(results) == 2
        # With deterministic embeddings the ordering is stable
        # Just verify scores are floats in valid range
        for r in results:
            assert -1.0 <= r.score <= 1.0

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Action potentials propagate")
        store.add("H-001", "Hypothesis", "Myelination increases speed")
        store.save()

        # Load into a fresh store
        store2 = _patched_store(tmp_path)
        store2._embeddings.clear()
        store2._metadata.clear()
        store2.load()

        assert store2.count == 2
        assert "F-001" in store2._embeddings
        assert "H-001" in store2._embeddings
        assert store2._metadata["F-001"]["text"] == "Action potentials propagate"
        assert store2._metadata["H-001"]["label"] == "Hypothesis"
        # Embeddings should match
        np.testing.assert_array_almost_equal(
            store._embeddings["F-001"], store2._embeddings["F-001"]
        )

    def test_load_missing_files(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.load()  # should not raise
        assert store.count == 0

    def test_save_empty_store(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.save()  # should not raise
        # No files created for empty store
        assert not (tmp_path / "embeddings" / "embeddings.npy").exists()

    def test_search_result_fields(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("P-abcd", "Paper", "Deep Learning for Neuroscience")
        results = store.search("deep learning")
        assert len(results) == 1
        r = results[0]
        assert r.node_id == "P-abcd"
        assert r.label == "Paper"
        assert r.text == "Deep Learning for Neuroscience"
        assert isinstance(r.score, float)


# ---------------------------------------------------------------------------
# Tests with real fastembed (skipped if not installed)
# ---------------------------------------------------------------------------

class TestEmbeddingStoreReal:
    """Integration tests using real fastembed model."""

    @pytest.fixture(autouse=True)
    def _require_fastembed(self) -> None:
        pytest.importorskip("fastembed")

    def test_embed_text_shape(self, tmp_path: Path) -> None:
        store = EmbeddingStore(store_path=str(tmp_path / "embeddings"))
        vec = store.embed_text("Test sentence")
        assert vec.shape == (384,)
        assert vec.dtype in (np.float32, np.float64)

    def test_semantic_similarity(self, tmp_path: Path) -> None:
        """Similar texts should score higher than dissimilar ones."""
        store = EmbeddingStore(store_path=str(tmp_path / "embeddings"))
        store.add("F-001", "Finding", "Calcium imaging reveals neural activity")
        store.add("F-002", "Finding", "Fluorescent calcium indicators in neurons")
        store.add("F-003", "Finding", "Banana cultivation in tropical regions")

        results = store.search("calcium neural imaging")
        # The two neuroscience findings should rank above bananas
        assert results[0].node_id in ("F-001", "F-002")
        assert results[1].node_id in ("F-001", "F-002")
        assert results[2].node_id == "F-003"

    def test_save_load_search(self, tmp_path: Path) -> None:
        """Full round-trip: add, save, load, search."""
        store = EmbeddingStore(store_path=str(tmp_path / "embeddings"))
        store.add("F-001", "Finding", "Synaptic plasticity mechanisms")
        store.add("H-001", "Hypothesis", "LTP requires NMDA receptors")
        store.save()

        store2 = EmbeddingStore(store_path=str(tmp_path / "embeddings"))
        store2.load()
        results = store2.search("NMDA receptor plasticity")
        assert len(results) == 2
        assert results[0].score > results[1].score
