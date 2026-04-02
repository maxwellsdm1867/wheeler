"""Semantic search module for Wheeler knowledge graph."""

from wheeler.search.retrieval import multi_search, reciprocal_rank_fusion

try:
    from wheeler.search.embeddings import EmbeddingStore, SearchResult

    __all__ = ["EmbeddingStore", "SearchResult", "multi_search", "reciprocal_rank_fusion"]
except ImportError:
    # numpy not installed — embedding-based search is unavailable
    __all__: list[str] = ["multi_search", "reciprocal_rank_fusion"]  # type: ignore[no-redef]
