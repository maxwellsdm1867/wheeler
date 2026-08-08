"""Semantic embedding and search using fastembed.

Uses BAAI/bge-small-en-v1.5 (33MB, no PyTorch dependency).
Embeddings stored in a local numpy file alongside the graph data.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

# Single-file store: the matrix and its id list must commit together.
_ARCHIVE_NAME = "store.npz"

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
        """Persist embeddings to disk as ONE atomically-renamed archive.

        The matrix and its id list must commit together. They used to be two
        files (``embeddings.npy`` + ``metadata.json``) written in place, which
        is two commit points: a crash between them left the OLD id list beside
        the NEW matrix, and ``load`` maps ``matrix[i]`` to ``ids[i]``
        positionally, so every node silently received another node's vector.
        A length check cannot catch that -- the stale id list can be the same
        length. Hence a single ``store.npz`` plus tmp+rename.

        The tmp name is unique per writer: a fixed ``.tmp`` would let two
        concurrent writers interleave into one file and both rename it,
        defeating the very atomicity the rename is there to provide.
        """
        self._store_path.mkdir(parents=True, exist_ok=True)
        archive = self._store_path / _ARCHIVE_NAME
        legacy_emb = self._store_path / "embeddings.npy"
        legacy_meta = self._store_path / "metadata.json"

        if self._embeddings:
            ids = list(self._embeddings.keys())
            matrix = np.stack([self._embeddings[i] for i in ids])
            meta = {node_id: self._metadata[node_id] for node_id in ids}

            tmp = self._store_path / f"{_ARCHIVE_NAME}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
            try:
                with open(tmp, "wb") as fh:
                    np.savez(fh, matrix=matrix, ids=np.array(ids, dtype=object),
                             meta=np.array(json.dumps(meta), dtype=object))
                tmp.replace(archive)
            finally:
                tmp.unlink(missing_ok=True)
        else:
            archive.unlink(missing_ok=True)

        # Either way the legacy pair is now superseded; drop it so a later load
        # cannot resurrect a stale generation.
        legacy_emb.unlink(missing_ok=True)
        legacy_meta.unlink(missing_ok=True)

        logger.info(
            "Saved %d embeddings to %s", len(self._embeddings), self._store_path
        )

    def load(self) -> None:
        """Load embeddings from disk.

        Reads the single-file archive when present, else falls back to the
        legacy two-file pair so existing stores keep working; the next `save`
        migrates them. Silently returns if no saved data exists.
        """
        archive = self._store_path / _ARCHIVE_NAME
        if archive.exists():
            with np.load(archive, allow_pickle=True) as data:
                matrix = data["matrix"]
                ids = [str(i) for i in data["ids"]]
                meta = json.loads(str(data["meta"].item()))
        else:
            emb_path = self._store_path / "embeddings.npy"
            meta_path = self._store_path / "metadata.json"
            if not emb_path.exists() or not meta_path.exists():
                logger.info("No saved embeddings found at %s", self._store_path)
                return

            matrix = np.load(emb_path)
            with open(meta_path) as f:
                meta = json.load(f)
            ids = meta.pop("__ids__")

            # A torn legacy pair assigns every node the wrong vector. Refuse it
            # rather than load a silently-corrupt store.
            if len(ids) != len(matrix):
                logger.error(
                    "Refusing torn embedding store at %s: %d ids vs %d vectors. "
                    "Delete the directory and re-run backfill.",
                    self._store_path, len(ids), len(matrix),
                )
                return

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
