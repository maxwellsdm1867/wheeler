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


async def _fulltext_channel(
    query: str,
    config: WheelerConfig,
    limit: int,
    label: str,
) -> list[str]:
    """Retrieve node IDs via Neo4j fulltext index search (RRF channel 4)."""
    from wheeler.tools.graph_tools import _get_backend

    try:
        backend = await _get_backend(config)

        # Build query with optional namespace filter
        cypher = (
            "CALL db.index.fulltext.queryNodes('wheeler_fulltext', $query) "
            "YIELD node, score "
            "WHERE node.id IS NOT NULL"
        )
        params: dict = {"query": query}

        if config.neo4j.project_tag:
            cypher += " AND node._wheeler_project = $ptag"
            params["ptag"] = config.neo4j.project_tag

        if label:
            cypher += f" AND '{label}' IN labels(node)"

        cypher += (
            " RETURN node.id AS id, labels(node)[0] AS type, score"
            " ORDER BY score DESC LIMIT $limit"
        )
        params["limit"] = limit

        records = await backend.run_cypher(cypher, params)
        return [rec.get("id", "") for rec in records if rec.get("id")]
    except Exception:
        logger.debug("Fulltext channel failed", exc_info=True)
        return []  # graceful degradation if fulltext index doesn't exist yet


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


def _summarize_node(node_id: str, knowledge_path: Path) -> dict:
    """Load a short summary of a node for glanceable related-node context.

    Returns ``id``, ``type``, ``tier``, ``tags``, ``stale``, plus the
    type-specific gist fields (e.g. ``description`` for Finding,
    ``title`` for Paper).  Falls back to ``{"id": node_id}`` on error.
    """
    try:
        from wheeler.knowledge.store import read_node

        model = read_node(knowledge_path, node_id)
        data = model.model_dump()
    except Exception:
        return {"id": node_id}

    summary: dict = {
        "id": data["id"],
        "type": data.get("type", ""),
        "tier": data.get("tier", ""),
    }
    if data.get("tags"):
        summary["tags"] = data["tags"]
    if data.get("stale"):
        summary["stale"] = True

    # One-sentence human-readable summary for LLM context
    summary["summary"] = _one_line_summary(data)

    return summary


def _one_line_summary(data: dict) -> str:
    """Build a one-sentence summary from type-specific fields."""
    t = data.get("type", "")
    if t == "Finding":
        desc = data.get("description", "")
        conf = data.get("confidence", 0)
        if desc:
            s = desc[:200]
            return f"{s} (confidence: {conf})" if conf else s
    elif t == "Hypothesis":
        stmt = data.get("statement", "")
        status = data.get("status", "open")
        if stmt:
            return f"{stmt[:200]} [{status}]"
    elif t == "OpenQuestion":
        q = data.get("question", "")
        if q:
            return q[:200]
    elif t == "Paper":
        title = data.get("title", "")
        authors = data.get("authors", "")
        year = data.get("year", 0)
        parts = [p for p in [title, authors, str(year) if year else ""] if p]
        if parts:
            return ", ".join(parts)
    elif t == "Dataset":
        desc = data.get("description", "")
        path = data.get("path", "")
        return desc[:200] if desc else path
    elif t == "Script":
        path = data.get("path", "")
        lang = data.get("language", "")
        return f"{path} ({lang})" if lang else path
    elif t == "Execution":
        desc = data.get("description", "")
        kind = data.get("kind", "")
        return desc[:200] if desc else kind
    elif t == "Document":
        title = data.get("title", "")
        return title[:200] if title else data.get("path", "")
    elif t == "ResearchNote":
        title = data.get("title", "")
        return title[:200] if title else ""
    return data.get("id", "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Graph expansion
# ---------------------------------------------------------------------------


async def expand_search_results(
    seeds: list[dict],
    config: WheelerConfig,
    max_hops_prov: int = 2,
    max_hops_semantic: int = 1,
) -> dict:
    """Expand search seeds via graph traversal, returning provenance chains.

    Starting from the seed nodes returned by ``multi_search``, traverses the
    graph to collect:

    - 1-hop neighbors via any relationship type
    - 2-hop neighbors via PROV relationships only (provenance chains)

    Results are deduplicated, scored by relationship type and distance,
    and returned alongside the relationship edges found.

    Args:
        seeds: List of enriched node dicts from ``multi_search`` (must have
               ``id`` and ``type`` keys).
        config: Wheeler configuration.
        max_hops_prov: Maximum depth for provenance chain traversal (default 2).
        max_hops_semantic: Maximum depth for semantic link traversal (default 1).

    Returns:
        Dict with ``seed_nodes``, ``related_nodes``, ``relationships``,
        and ``total_related``.
    """
    from wheeler.tools.graph_tools import _get_backend
    from wheeler.models import PREFIX_TO_LABEL

    backend = await _get_backend(config)
    all_related: list[dict] = []
    all_relationships: list[dict] = []

    for seed in seeds:
        node_id = seed.get("id", "")
        prefix = node_id.split("-", 1)[0] if "-" in node_id else ""
        label = PREFIX_TO_LABEL.get(prefix, "")
        if not label or not node_id:
            continue

        # 1-hop: all relationship types
        try:
            hop1 = await backend.run_cypher(
                f"MATCH (seed:{label} {{id: $id}})-[r]-(n) "
                "RETURN n.id AS nid, labels(n)[0] AS nlabel, "
                "type(r) AS rel, "
                "CASE WHEN startNode(r).id = $id THEN 'out' ELSE 'in' END AS dir",
                {"id": node_id},
            )
            for rec in hop1:
                all_related.append({
                    "node_id": rec["nid"],
                    "label": rec["nlabel"],
                    "relationship": rec["rel"],
                    "direction": rec["dir"],
                    "from_seed": node_id,
                    "hops": 1,
                })
                all_relationships.append({
                    "source": node_id if rec["dir"] == "out" else rec["nid"],
                    "target": rec["nid"] if rec["dir"] == "out" else node_id,
                    "relationship": rec["rel"],
                })
        except Exception:
            logger.debug("1-hop expansion failed for %s", node_id, exc_info=True)

        # 2-hop: PROV relationships only (provenance chains)
        if max_hops_prov >= 2:
            try:
                hop2 = await backend.run_cypher(
                    f"MATCH (seed:{label} {{id: $id}})"
                    "-[:USED|WAS_GENERATED_BY|WAS_DERIVED_FROM|WAS_INFORMED_BY]-(h1)"
                    "-[r2:USED|WAS_GENERATED_BY|WAS_DERIVED_FROM|WAS_INFORMED_BY]-(h2) "
                    "WHERE h2.id <> $id "
                    "RETURN DISTINCT h2.id AS nid, labels(h2)[0] AS nlabel, "
                    "type(r2) AS rel, h1.id AS via",
                    {"id": node_id},
                )
                for rec in hop2:
                    all_related.append({
                        "node_id": rec["nid"],
                        "label": rec["nlabel"],
                        "relationship": rec["rel"],
                        "from_seed": node_id,
                        "via": rec["via"],
                        "hops": 2,
                    })
            except Exception:
                logger.debug(
                    "2-hop prov expansion failed for %s", node_id, exc_info=True,
                )

    # Deduplicate related nodes (keep closest hop)
    seen: dict[str, dict] = {}
    for rel in all_related:
        nid = rel["node_id"]
        if nid not in seen or rel["hops"] < seen[nid]["hops"]:
            seen[nid] = rel
    # Remove seeds from related
    seed_ids = {s.get("id") for s in seeds}
    unique_related = [v for k, v in sorted(seen.items()) if k not in seed_ids]

    # Rank: PROV relationships score higher than semantic
    prov_rels = {"USED", "WAS_GENERATED_BY", "WAS_DERIVED_FROM", "WAS_INFORMED_BY"}
    semantic_rels = {"SUPPORTS", "CONTRADICTS"}
    for node in unique_related:
        rel = node.get("relationship", "")
        hops = node.get("hops", 1)
        if rel in prov_rels:
            node["relevance_score"] = 1.0 / hops
        elif rel in semantic_rels:
            node["relevance_score"] = 0.8 / hops
        else:
            node["relevance_score"] = 0.5 / hops
    unique_related.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    # Enrich related nodes with glanceable summary from knowledge JSON
    knowledge_path = Path(config.knowledge_path)
    clean_related: list[dict] = []
    for node in unique_related:
        summary = _summarize_node(node["node_id"], knowledge_path)
        entry: dict = {
            "id": node["node_id"],
            "type": summary.get("type", node.get("label", "")),
            "relationship": node["relationship"],
            "summary": summary.get("summary", ""),
        }
        if summary.get("tier"):
            entry["tier"] = summary["tier"]
        if summary.get("tags"):
            entry["tags"] = summary["tags"]
        if summary.get("stale"):
            entry["stale"] = True
        clean_related.append(entry)

    # Deduplicate relationships
    unique_rels: list[dict] = []
    rel_seen: set[tuple[str, str, str]] = set()
    for r in all_relationships:
        key = (r["source"], r["target"], r["relationship"])
        if key not in rel_seen:
            rel_seen.add(key)
            unique_rels.append(r)

    # Build clean seed nodes: summary + score, no internal fields
    clean_seeds: list[dict] = []
    for s in seeds:
        node_id = s.get("id", "")
        seed_summary = _summarize_node(node_id, knowledge_path)
        entry = {**seed_summary, "score": s.get("rrf_score", 0)}
        clean_seeds.append(entry)

    return {
        "seed_nodes": clean_seeds,
        "related_nodes": clean_related,
        "relationships": unique_rels,
        "total_related": len(clean_related),
    }


async def multi_search(
    query: str,
    config: WheelerConfig,
    limit: int = 10,
    label: str = "",
    mode: str = "multi",
) -> list[dict]:
    """Run multi-channel retrieval and fuse results with RRF.

    Runs up to four channels (semantic, keyword, temporal, fulltext) in
    parallel, fuses their ranked ID lists with Reciprocal Rank Fusion,
    then enriches the top results from knowledge JSON files.

    Args:
        query: Natural language search query.
        config: Wheeler configuration.
        limit: Maximum results to return.
        label: Optional node-type filter (e.g. ``"Finding"``).
        mode: Retrieval mode: ``"multi"`` (default, all channels),
              ``"semantic"`` (embeddings only), ``"keyword"``
              (graph keyword only), ``"temporal"`` (most recent only),
              ``"fulltext"`` (Neo4j fulltext index only).

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
    elif mode == "fulltext":
        ranked_lists = [await _fulltext_channel(query, config, per_channel, label)]
    else:
        # Multi: run all channels concurrently
        results = await asyncio.gather(
            _semantic_channel(query, config, per_channel, label),
            _keyword_channel(query, config, per_channel, label),
            _temporal_channel(config, per_channel, label),
            _fulltext_channel(query, config, per_channel, label),
            return_exceptions=True,
        )
        ranked_lists = []
        for i, r in enumerate(results):
            channel_name = ["semantic", "keyword", "temporal", "fulltext"][i]
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
