"""Multi-channel retrieval with Reciprocal Rank Fusion.

Combines up to three retrieval channels — semantic (embeddings), keyword
(graph queries), and temporal (recency) — and fuses their ranked results
using RRF.  Gracefully degrades when individual channels are unavailable.

Reference: Cormack, Clarke & Buettcher (2009) — Reciprocal Rank Fusion.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)

# Maps node labels to the text field used by the keyword channel.
# Must stay in sync with backfill.TEXT_FIELDS.
_LABEL_TEXT_FIELDS: dict[str, str] = {
    "Finding": "description",
    "Hypothesis": "statement",
    "OpenQuestion": "question",
    "Paper": "title",
    "Dataset": "description",
    "Document": "title",
    "ResearchNote": "content",
}


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = 60,
    limit: int = 10,
) -> list[tuple[str, float]]:
    """Combine multiple ranked lists using Reciprocal Rank Fusion.

    Each input list contains node IDs ordered from most to least relevant.
    The fused score for a document is::

        score(doc) = sum(1 / (k + rank_in_list + 1))  for each list containing doc

    Args:
        ranked_lists: Ordered lists of node IDs from each retrieval channel.
        k: RRF constant (default 60, per the original paper).
        limit: Maximum number of results to return.

    Returns:
        ``(node_id, score)`` tuples sorted by fused score descending.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])[:limit]


# ---------------------------------------------------------------------------
# Individual retrieval channels
# ---------------------------------------------------------------------------


async def _semantic_channel(
    query: str,
    config: WheelerConfig,
    limit: int,
    label: str,
) -> list[str]:
    """Retrieve node IDs via cosine-similarity search over embeddings."""
    try:
        from wheeler.search.embeddings import EmbeddingStore
    except ImportError:
        logger.debug("Semantic channel unavailable: wheeler[search] not installed")
        return []

    store = EmbeddingStore(config.search.store_path)
    store.load()
    results = store.search(query, limit=limit, label_filter=label or None)
    return [r.node_id for r in results]


async def _keyword_channel(
    query: str,
    config: WheelerConfig,
    limit: int,
    label: str,
) -> list[str]:
    """Retrieve node IDs via keyword-filtered graph queries."""
    from wheeler.tools import graph_tools

    # Determine which query tools to run based on label filter
    if label:
        targets = _label_to_query_targets(label)
    else:
        # Query the broad set: findings, hypotheses, questions, notes, papers
        targets = [
            ("query_findings", "keyword"),
            ("query_hypotheses", None),  # hypotheses has no keyword param
            ("query_open_questions", None),
            ("query_notes", "keyword"),
            ("query_papers", "keyword"),
        ]

    node_ids: list[str] = []
    for tool_name, kw_param in targets:
        try:
            args: dict = {"limit": limit}
            if kw_param:
                args[kw_param] = query
            result_str = await graph_tools.execute_tool(tool_name, args, config)
            parsed = json.loads(result_str)
            # All query tools return a dict with a list keyed by plural label
            for key, val in parsed.items():
                if isinstance(val, list):
                    for item in val:
                        nid = item.get("id", "")
                        if nid and nid not in node_ids:
                            node_ids.append(nid)
        except Exception:
            logger.debug("Keyword channel %s failed", tool_name, exc_info=True)

    return node_ids[:limit]


async def _temporal_channel(
    config: WheelerConfig,
    limit: int,
    label: str,
) -> list[str]:
    """Retrieve the most recently created node IDs."""
    knowledge_path = Path(config.knowledge_path)
    if not knowledge_path.is_dir():
        return []

    try:
        from wheeler.knowledge.store import list_nodes

        nodes = list_nodes(knowledge_path, type_filter=label or None)

        # Sort by created timestamp descending (most recent first)
        def _sort_key(n):
            return getattr(n, "created", "") or ""

        nodes.sort(key=_sort_key, reverse=True)
        return [n.id for n in nodes[:limit]]
    except Exception:
        logger.debug("Temporal channel failed", exc_info=True)
        return []


def _label_to_query_targets(label: str) -> list[tuple[str, str | None]]:
    """Map a node label to the (tool_name, keyword_param) pairs to query."""
    mapping: dict[str, tuple[str, str | None]] = {
        "Finding": ("query_findings", "keyword"),
        "Hypothesis": ("query_hypotheses", None),
        "OpenQuestion": ("query_open_questions", None),
        "Paper": ("query_papers", "keyword"),
        "Dataset": ("query_datasets", "keyword"),
        "Document": ("query_documents", "keyword"),
        "ResearchNote": ("query_notes", "keyword"),
    }
    target = mapping.get(label)
    return [target] if target else []


# ---------------------------------------------------------------------------
# Node enrichment
# ---------------------------------------------------------------------------


def _enrich_node(node_id: str, knowledge_path: Path) -> dict:
    """Load full node data from the knowledge JSON file.

    Returns a dict with at least ``{"id": node_id}``.  On failure, returns
    a minimal stub so that results are never dropped.
    """
    try:
        from wheeler.knowledge.store import read_node

        model = read_node(knowledge_path, node_id)
        return model.model_dump()
    except Exception:
        return {"id": node_id}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def multi_search(
    query: str,
    config: WheelerConfig,
    limit: int = 10,
    label: str = "",
    mode: str = "multi",
) -> list[dict]:
    """Run multi-channel retrieval and fuse results with RRF.

    Runs up to three channels (semantic, keyword, temporal) in parallel,
    fuses their ranked ID lists with Reciprocal Rank Fusion, then enriches
    the top results from knowledge JSON files.

    Args:
        query: Natural language search query.
        config: Wheeler configuration.
        limit: Maximum results to return.
        label: Optional node-type filter (e.g. ``"Finding"``).
        mode: Retrieval mode — ``"multi"`` (default), ``"semantic"``,
              ``"keyword"``, or ``"temporal"``.

    Returns:
        List of enriched node dicts, each with at least ``id`` and
        ``rrf_score`` keys.
    """
    # Fetch a wider candidate pool per channel so RRF has material to work with
    per_channel = max(limit * 3, 30)

    if mode == "semantic":
        ranked_lists = [await _semantic_channel(query, config, per_channel, label)]
    elif mode == "keyword":
        ranked_lists = [await _keyword_channel(query, config, per_channel, label)]
    elif mode == "temporal":
        ranked_lists = [await _temporal_channel(config, per_channel, label)]
    else:
        # Multi: run all channels concurrently
        results = await asyncio.gather(
            _semantic_channel(query, config, per_channel, label),
            _keyword_channel(query, config, per_channel, label),
            _temporal_channel(config, per_channel, label),
            return_exceptions=True,
        )
        ranked_lists = []
        for i, r in enumerate(results):
            channel_name = ["semantic", "keyword", "temporal"][i]
            if isinstance(r, BaseException):
                logger.warning("Channel %s raised: %s", channel_name, r)
            elif r:
                ranked_lists.append(r)

    if not ranked_lists:
        return []

    fused = reciprocal_rank_fusion(ranked_lists, limit=limit)

    # Enrich each result with full node data
    knowledge_path = Path(config.knowledge_path)
    enriched: list[dict] = []
    for node_id, score in fused:
        node_data = _enrich_node(node_id, knowledge_path)
        node_data["rrf_score"] = round(score, 6)
        enriched.append(node_data)

    return enriched
