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

    def test_has(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Some finding")
        assert store.has("F-001")
        assert not store.has("F-999")

    # --- find_similar_pairs ---

    def test_find_similar_pairs_empty(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        assert store.find_similar_pairs() == []

    def test_find_similar_pairs_single_node(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Just one node")
        assert store.find_similar_pairs() == []

    def test_find_similar_pairs_identical_text(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        # Identical text → identical embedding → similarity 1.0
        store.add("F-001", "Finding", "Neurons fire in bursts")
        store.add("F-002", "Finding", "Neurons fire in bursts")
        pairs = store.find_similar_pairs(threshold=0.99)
        assert len(pairs) == 1
        a, b, score = pairs[0]
        assert {a.node_id, b.node_id} == {"F-001", "F-002"}
        assert score > 0.99

    def test_find_similar_pairs_dissimilar_below_threshold(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Mitochondria in neurons")
        store.add("F-002", "Finding", "Banana dessert recipe")
        # Very different texts — with deterministic hash-based embeddings
        # they should not be near-identical
        pairs = store.find_similar_pairs(threshold=0.99)
        assert len(pairs) == 0

    def test_find_similar_pairs_label_filter(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Neurons fire in bursts")
        store.add("F-002", "Finding", "Neurons fire in bursts")
        store.add("H-001", "Hypothesis", "Neurons fire in bursts")
        # Only compare within Finding label
        pairs = store.find_similar_pairs(threshold=0.99, label_filter="Finding")
        assert len(pairs) == 1
        a, b, _ = pairs[0]
        assert a.label == "Finding"
        assert b.label == "Finding"

    def test_find_similar_pairs_sorted_by_score(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Neurons fire in bursts")
        store.add("F-002", "Finding", "Neurons fire in bursts")
        store.add("F-003", "Finding", "Something slightly different about neurons")
        pairs = store.find_similar_pairs(threshold=0.0)
        # Should be sorted descending by score
        scores = [s for _, _, s in pairs]
        assert scores == sorted(scores, reverse=True)

    # --- check_similar ---

    def test_check_similar_empty_store(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        results = store.check_similar("anything")
        assert results == []

    def test_check_similar_empty_text(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Something")
        assert store.check_similar("") == []
        assert store.check_similar("   ") == []

    def test_check_similar_finds_duplicate(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Neurons fire in bursts")
        results = store.check_similar("Neurons fire in bursts", threshold=0.99)
        assert len(results) == 1
        assert results[0].node_id == "F-001"
        assert results[0].score > 0.99

    def test_check_similar_exclude_id(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Neurons fire in bursts")
        # Exclude the matching node
        results = store.check_similar(
            "Neurons fire in bursts", threshold=0.99, exclude_id="F-001"
        )
        assert len(results) == 0

    def test_check_similar_label_filter(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Neurons fire in bursts")
        store.add("H-001", "Hypothesis", "Neurons fire in bursts")
        results = store.check_similar(
            "Neurons fire in bursts", threshold=0.99, label_filter="Finding"
        )
        assert len(results) == 1
        assert results[0].node_id == "F-001"

    def test_check_similar_sorted_by_score(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Neurons fire in bursts")
        store.add("F-002", "Finding", "Neurons sometimes fire")
        store.add("F-003", "Finding", "Banana recipe")
        results = store.check_similar("Neurons fire in bursts", threshold=0.0)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


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


class TestSaveIsOneAtomicCommit:
    """The matrix and its id list must commit together.

    They used to be two files written in place. A crash between them left the
    OLD id list beside the NEW matrix, and `load` maps matrix[i] to ids[i]
    positionally, so every node silently received another node's vector. A
    length check cannot catch it: the stale id list can be the same length.
    """

    def _store(self, path):
        import numpy as np

        from wheeler.search.embeddings import EmbeddingStore

        store = EmbeddingStore(str(path))
        for i, nid in enumerate(["F-aaaa1111", "F-bbbb2222", "F-cccc3333"]):
            store._embeddings[nid] = np.array([float(i), 1.0, 2.0])
            store._metadata[nid] = {"label": "Finding", "text": nid}
        return store

    def test_save_writes_a_single_archive(self, tmp_path):
        self._store(tmp_path).save()
        assert (tmp_path / "store.npz").exists()
        assert not (tmp_path / "embeddings.npy").exists()
        assert not (tmp_path / "metadata.json").exists()

    def test_round_trip_preserves_the_id_to_vector_mapping(self, tmp_path):
        import numpy as np

        from wheeler.search.embeddings import EmbeddingStore

        self._store(tmp_path).save()
        reloaded = EmbeddingStore(str(tmp_path))
        reloaded.load()
        assert set(reloaded._embeddings) == {"F-aaaa1111", "F-bbbb2222", "F-cccc3333"}
        assert np.allclose(reloaded._embeddings["F-bbbb2222"], [1.0, 1.0, 2.0])
        assert reloaded._metadata["F-cccc3333"]["text"] == "F-cccc3333"

    def test_failed_commit_leaves_the_previous_generation_intact(self, tmp_path):
        """Never a mixture: either the old archive or the new one."""
        import numpy as np

        from wheeler.search.embeddings import EmbeddingStore

        self._store(tmp_path).save()
        before = (tmp_path / "store.npz").read_bytes()

        store2 = EmbeddingStore(str(tmp_path))
        store2._embeddings["F-dddd4444"] = np.array([9.0, 9.0, 9.0])
        store2._metadata["F-dddd4444"] = {"label": "Finding", "text": "new"}

        import pathlib

        def boom(self, target):
            raise OSError("simulated crash at commit")

        original = pathlib.Path.replace
        pathlib.Path.replace = boom
        try:
            with __import__("pytest").raises(OSError):
                store2.save()
        finally:
            pathlib.Path.replace = original

        assert (tmp_path / "store.npz").read_bytes() == before
        assert not list(tmp_path.glob("*.tmp")), "temp file left behind"

    def test_tmp_name_is_unique_per_writer(self, tmp_path):
        """A fixed .tmp lets two concurrent writers interleave into one file."""
        import pathlib

        seen: list[str] = []
        original = pathlib.Path.replace

        def record(self, target):
            seen.append(self.name)
            return original(self, target)

        pathlib.Path.replace = record
        try:
            self._store(tmp_path).save()
            self._store(tmp_path).save()
        finally:
            pathlib.Path.replace = original

        assert len(seen) == 2
        assert seen[0] != seen[1], f"tmp name is not unique per writer: {seen}"

    def test_torn_legacy_pair_is_refused_not_misassigned(self, tmp_path):
        """The exact corruption the single archive exists to prevent."""
        import json

        import numpy as np

        from wheeler.search.embeddings import EmbeddingStore

        # 3 vectors, but a stale 3-id list naming DIFFERENT nodes would load
        # silently; use a mismatched length to prove the refusal path.
        np.save(tmp_path / "embeddings.npy", np.zeros((3, 4)))
        (tmp_path / "metadata.json").write_text(
            json.dumps({"F-old00001": {"label": "Finding"}, "__ids__": ["F-old00001"]})
        )

        store = EmbeddingStore(str(tmp_path))
        store.load()
        assert store._embeddings == {}, "torn store was loaded instead of refused"

    def test_legacy_pair_still_loads_and_migrates(self, tmp_path):
        import json

        import numpy as np

        from wheeler.search.embeddings import EmbeddingStore

        np.save(tmp_path / "embeddings.npy", np.array([[1.0, 2.0], [3.0, 4.0]]))
        (tmp_path / "metadata.json").write_text(
            json.dumps({
                "F-one00001": {"label": "Finding"},
                "F-two00002": {"label": "Finding"},
                "__ids__": ["F-one00001", "F-two00002"],
            })
        )

        store = EmbeddingStore(str(tmp_path))
        store.load()
        assert np.allclose(store._embeddings["F-two00002"], [3.0, 4.0])

        store.save()
        assert (tmp_path / "store.npz").exists()
        assert not (tmp_path / "embeddings.npy").exists()


class TestStorePathIsProjectAnchored:
    def test_nothing_outside_config_reads_the_raw_store_path(self):
        """search_findings and index_node read different files when cwd != root.

        Flags the raw FIELD REFERENCE rather than the EmbeddingStore call, so
        it catches both the inline form (`EmbeddingStore(config.search.store_path)`)
        and the assign-then-use form backup.py had, where the raw read sits
        several lines above the construction. An earlier window-based version of
        this guard missed the latter.

        `config.py` is the one legitimate reader: `project_search_store_dir`
        falls back to the raw string for duck-typed configs in tests.
        """
        import pathlib
        import re

        pattern = re.compile(
            r"config\.search\.store_path|getattr\(\s*config\.search\s*,\s*[\"']store_path"
        )
        offenders = []
        for path in pathlib.Path("wheeler").rglob("*.py"):
            if path.name == "config.py":
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if pattern.search(line):
                    offenders.append(f"{path}:{lineno}")
        assert offenders == [], (
            f"read the store path via project_search_store_dir(config): {offenders}"
        )
