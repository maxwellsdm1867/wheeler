"""Semantic embedding and search using fastembed.

Uses BAAI/bge-small-en-v1.5 (33MB, no PyTorch dependency).
Embeddings stored in a local numpy file alongside the graph data.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result with similarity score."""

    node_id: str
    label: str
    text: str
    score: float  # cosine similarity, 0-1


class EmbeddingStore:
    """Manages embeddings for graph nodes.

    Uses fastembed (optional dependency) for embedding generation and numpy
    for storage. The store is file-based and does not require a running
    database.
    """

    def __init__(self, store_path: str = ".wheeler/embeddings") -> None:
        """Initialize the embedding store.

        Args:
            store_path: Directory to store embedding data.

        Raises:
            ImportError: If numpy is not installed.
        """
        if np is None:
            raise ImportError(
                "numpy is required for semantic search. "
                "Install with: pip install 'wheeler[search]'"
            )
        self._store_path = Path(store_path)
        self._model: object | None = None  # lazy-loaded TextEmbedding
        self._embeddings: dict[str, np.ndarray] = {}  # node_id -> embedding
        self._metadata: dict[str, dict[str, str]] = {}  # node_id -> {label, text}
        self._dimension: int = 384  # bge-small-en-v1.5 dimension

    def _ensure_model(self) -> None:
        """Lazy-load the fastembed model.

        Raises:
            ImportError: If fastembed is not installed.
        """
        if self._model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError:
                raise ImportError(
                    "fastembed is required for semantic search. "
                    "Install with: pip install 'wheeler[search]'"
                )
            self._model = TextEmbedding("BAAI/bge-small-en-v1.5")
            logger.info("Loaded fastembed model BAAI/bge-small-en-v1.5")

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as numpy array of shape (384,).
        """
        self._ensure_model()
        # fastembed returns a generator of numpy arrays
        embeddings = list(self._model.embed([text]))  # type: ignore[union-attr]
        return embeddings[0]

    def add(self, node_id: str, label: str, text: str) -> None:
        """Add or update embedding for a node.

        Args:
            node_id: Graph node ID (e.g., "F-3a2b1c4d").
            label: Node label (e.g., "Finding").
            text: Text content to embed.
        """
        if not text or not text.strip():
            return
        embedding = self.embed_text(text)
        self._embeddings[node_id] = embedding
        self._metadata[node_id] = {"label": label, "text": text}

    def has(self, node_id: str) -> bool:
        """Check whether an embedding exists for *node_id*."""
        return node_id in self._embeddings

    def remove(self, node_id: str) -> None:
        """Remove embedding for a node.

        Args:
            node_id: Graph node ID to remove.
        """
        self._embeddings.pop(node_id, None)
        self._metadata.pop(node_id, None)

    def search(
        self,
        query: str,
        limit: int = 10,
        label_filter: str | None = None,
    ) -> list[SearchResult]:
        """Search for similar nodes by text.

        Args:
            query: Search query text.
            limit: Maximum number of results to return.
            label_filter: Optional label to filter by (e.g., "Finding").

        Returns:
            List of SearchResult sorted by similarity (highest first).
        """
        if not self._embeddings:
            return []

        query_embedding = self.embed_text(query)

        results: list[tuple[str, float]] = []
        for node_id, embedding in self._embeddings.items():
            if label_filter and self._metadata[node_id]["label"] != label_filter:
                continue
            # Cosine similarity
            norm_product = np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            if norm_product == 0:
                score = 0.0
            else:
                score = float(
                    np.dot(query_embedding, embedding) / norm_product
                )
            results.append((node_id, score))

        results.sort(key=lambda x: x[1], reverse=True)

        return [
            SearchResult(
                node_id=node_id,
                label=self._metadata[node_id]["label"],
                text=self._metadata[node_id]["text"],
                score=score,
            )
            for node_id, score in results[:limit]
        ]

    def save(self) -> None:
        """Persist embeddings to disk.

        Creates the store directory if it doesn't exist. Saves embeddings
        as a numpy .npy file and metadata as JSON.
        """
        self._store_path.mkdir(parents=True, exist_ok=True)
        emb_path = self._store_path / "embeddings.npy"
        meta_path = self._store_path / "metadata.json"
        if self._embeddings:
            ids = list(self._embeddings.keys())
            matrix = np.stack([self._embeddings[i] for i in ids])
            np.save(emb_path, matrix)

            meta: dict[str, object] = {
                node_id: self._metadata[node_id] for node_id in ids
            }
            meta["__ids__"] = ids  # type: ignore[assignment]
            with open(meta_path, "w") as f:
                json.dump(meta, f)
        else:
            # Remove stale files when the store is empty
            if emb_path.exists():
                emb_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
        logger.info(
            "Saved %d embeddings to %s", len(self._embeddings), self._store_path
        )

    def load(self) -> None:
        """Load embeddings from disk.

        Silently returns if no saved data exists.
        """
        emb_path = self._store_path / "embeddings.npy"
        meta_path = self._store_path / "metadata.json"
        if not emb_path.exists() or not meta_path.exists():
            logger.info("No saved embeddings found at %s", self._store_path)
            return

        matrix = np.load(emb_path)
        with open(meta_path) as f:
            meta = json.load(f)

        ids: list[str] = meta.pop("__ids__")
        for i, node_id in enumerate(ids):
            self._embeddings[node_id] = matrix[i]
            self._metadata[node_id] = meta[node_id]
        logger.info(
            "Loaded %d embeddings from %s", len(self._embeddings), self._store_path
        )

    def find_similar_pairs(
        self,
        threshold: float = 0.85,
        label_filter: str | None = None,
    ) -> list[tuple[SearchResult, SearchResult, float]]:
        """Find pairs of nodes whose embeddings are above a similarity threshold.

        Useful for detecting near-duplicate nodes in the knowledge graph.

        Args:
            threshold: Minimum cosine similarity to report (default 0.85).
            label_filter: Optional label to restrict comparison (e.g., "Finding").

        Returns:
            List of (node_a, node_b, score) tuples, sorted by score descending.
        """
        if not self._embeddings:
            return []

        # Filter to relevant nodes
        ids = [
            nid
            for nid in self._embeddings
            if not label_filter or self._metadata[nid]["label"] == label_filter
        ]
        if len(ids) < 2:
            return []

        # Build matrix and compute pairwise cosine similarity
        matrix = np.stack([self._embeddings[nid] for nid in ids])
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # avoid division by zero
        normed = matrix / norms
        sim_matrix = normed @ normed.T

        # Extract above-threshold pairs (upper triangle only)
        pairs: list[tuple[SearchResult, SearchResult, float]] = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                score = float(sim_matrix[i, j])
                if score >= threshold:
                    a = SearchResult(
                        node_id=ids[i],
                        label=self._metadata[ids[i]]["label"],
                        text=self._metadata[ids[i]]["text"],
                        score=score,
                    )
                    b = SearchResult(
                        node_id=ids[j],
                        label=self._metadata[ids[j]]["label"],
                        text=self._metadata[ids[j]]["text"],
                        score=score,
                    )
                    pairs.append((a, b, score))

        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs

    def check_similar(
        self,
        text: str,
        threshold: float = 0.85,
        label_filter: str | None = None,
        exclude_id: str | None = None,
    ) -> list[SearchResult]:
        """Check if text is similar to any existing node above threshold.

        Like search(), but only returns results above the threshold — designed
        for pre-creation duplicate checks.

        Args:
            text: Text to check against existing nodes.
            threshold: Minimum similarity to report.
            label_filter: Optional label filter.
            exclude_id: Node ID to skip (useful when updating an existing node).

        Returns:
            Matching nodes above threshold, sorted by score descending.
        """
        if not self._embeddings or not text or not text.strip():
            return []

        query_embedding = self.embed_text(text)
        results: list[SearchResult] = []

        for node_id, embedding in self._embeddings.items():
            if node_id == exclude_id:
                continue
            if label_filter and self._metadata[node_id]["label"] != label_filter:
                continue
            norm_product = np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            if norm_product == 0:
                continue
            score = float(np.dot(query_embedding, embedding) / norm_product)
            if score >= threshold:
                results.append(SearchResult(
                    node_id=node_id,
                    label=self._metadata[node_id]["label"],
                    text=self._metadata[node_id]["text"],
                    score=score,
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    @property
    def count(self) -> int:
        """Number of embeddings in the store."""
        return len(self._embeddings)
