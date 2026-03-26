"""Semantic search module for Wheeler knowledge graph."""

try:
    from wheeler.search.embeddings import EmbeddingStore, SearchResult

    __all__ = ["EmbeddingStore", "SearchResult"]
except ImportError:
    # numpy not installed — search is unavailable
    __all__: list[str] = []  # type: ignore[no-redef]
