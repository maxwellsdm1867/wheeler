"""Tests for backfill_embeddings."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from wheeler.search.backfill import TEXT_FIELDS, backfill_embeddings
from wheeler.search.embeddings import EmbeddingStore


def _make_deterministic_embedding(text: str, dim: int = 384) -> np.ndarray:
    rng = np.random.RandomState(hash(text) % (2**31))
    vec = rng.randn(dim).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec


def _mock_embed(texts: list[str]) -> list[np.ndarray]:
    return [_make_deterministic_embedding(t) for t in texts]


def _patched_store(tmp_path: Path) -> EmbeddingStore:
    store = EmbeddingStore(store_path=str(tmp_path / "embeddings"))
    mock_model = MagicMock()
    mock_model.embed = _mock_embed
    store._model = mock_model
    return store


class TestBackfill:
    """Tests for backfill_embeddings function."""

    @pytest.mark.asyncio
    async def test_backfill_basic(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        nodes_by_label = {
            "Finding": [
                {"id": "F-001", "description": "Calcium signaling"},
                {"id": "F-002", "description": "Neural oscillations"},
            ],
            "Hypothesis": [
                {"id": "H-001", "statement": "Astrocytes modulate synapses"},
            ],
        }
        added = await backfill_embeddings(nodes_by_label, store)
        assert added == 3
        assert store.count == 3

    @pytest.mark.asyncio
    async def test_backfill_skips_existing(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        store.add("F-001", "Finding", "Already exists")
        nodes_by_label = {
            "Finding": [
                {"id": "F-001", "description": "Calcium signaling"},
                {"id": "F-002", "description": "Neural oscillations"},
            ],
        }
        added = await backfill_embeddings(nodes_by_label, store)
        assert added == 1  # only F-002 is new
        assert store.count == 2

    @pytest.mark.asyncio
    async def test_backfill_skips_empty_text(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        nodes_by_label = {
            "Finding": [
                {"id": "F-001", "description": ""},
                {"id": "F-002", "description": "Valid text"},
            ],
        }
        added = await backfill_embeddings(nodes_by_label, store)
        assert added == 1

    @pytest.mark.asyncio
    async def test_backfill_skips_missing_id(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        nodes_by_label = {
            "Finding": [
                {"description": "No ID field"},
            ],
        }
        added = await backfill_embeddings(nodes_by_label, store)
        assert added == 0

    @pytest.mark.asyncio
    async def test_backfill_skips_unknown_labels(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        nodes_by_label = {
            "UnknownType": [
                {"id": "X-001", "data": "some text"},
            ],
        }
        added = await backfill_embeddings(nodes_by_label, store)
        assert added == 0

    @pytest.mark.asyncio
    async def test_backfill_all_labels(self, tmp_path: Path) -> None:
        """Test that all known labels are handled."""
        store = _patched_store(tmp_path)
        nodes_by_label = {
            "Finding": [{"id": "F-001", "description": "A finding"}],
            "Hypothesis": [{"id": "H-001", "statement": "A hypothesis"}],
            "OpenQuestion": [{"id": "Q-001", "question": "A question?"}],
            "Paper": [{"id": "P-001", "title": "A paper title"}],
            "Dataset": [{"id": "D-001", "description": "Dataset desc"}],
            "Document": [{"id": "DOC-001", "title": "Doc title"}],
        }
        added = await backfill_embeddings(nodes_by_label, store)
        assert added == 6
        assert store.count == 6

    @pytest.mark.asyncio
    async def test_backfill_empty_input(self, tmp_path: Path) -> None:
        store = _patched_store(tmp_path)
        added = await backfill_embeddings({}, store)
        assert added == 0

    def test_text_fields_mapping(self) -> None:
        """Verify TEXT_FIELDS covers all expected node types."""
        expected = {"Finding", "Hypothesis", "OpenQuestion", "Paper", "Dataset", "Document", "ResearchNote"}
        assert set(TEXT_FIELDS.keys()) == expected
