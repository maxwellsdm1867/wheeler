"""Community detection for Wheeler knowledge graphs.

Uses connected components (BFS) to find clusters of related research
nodes. Pure Python, no external dependencies.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)


def connected_components(edges: list[tuple[str, str]]) -> list[set[str]]:
    """Find connected components via BFS on an undirected edge list.

    Returns list of sets, each set containing node IDs in one component.
    Sorted by size (largest first).
    """
    # Build adjacency list (undirected)
    adj: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    visited: set[str] = set()
    components: list[set[str]] = []

    for node in adj:
        if node in visited:
            continue
        # BFS from this node
        component: set[str] = set()
        queue = deque([node])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adj[current]:
                if neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)

    # Sort by size (largest first)
    components.sort(key=len, reverse=True)
    return components


async def find_communities(
    config: WheelerConfig,
    min_size: int = 3,
) -> dict:
    """Detect communities in the knowledge graph.

    Extracts edges via Cypher (directed to avoid duplicates),
    runs connected components, and enriches each community with
    node metadata from knowledge files.

    Returns dict with communities list and summary stats.
    """
    from wheeler.tools.graph_tools import _get_backend
    from wheeler.knowledge.store import read_node
    from wheeler.models import title_for_node, PREFIX_TO_LABEL
    from pathlib import Path

    backend = await _get_backend(config)
    knowledge_dir = Path(config.knowledge_path)

    # Extract edges (directed -> to avoid duplicates)
    try:
        records = await backend.run_cypher(
            "MATCH (a)-[r]->(b) "
            "WHERE a.id IS NOT NULL AND b.id IS NOT NULL "
            "RETURN a.id AS source, b.id AS target, type(r) AS rel_type"
        )
    except Exception as exc:
        logger.warning("Cannot query graph for community detection: %s", exc)
        return {"communities": [], "total_nodes": 0, "total_communities": 0}

    edges = [(r["source"], r["target"]) for r in records]

    if not edges:
        return {"communities": [], "total_nodes": 0, "total_communities": 0}

    # Find connected components
    components = connected_components(edges)

    # Filter by min_size and enrich with metadata
    communities = []
    for i, component in enumerate(components):
        if len(component) < min_size:
            continue

        members = []
        for node_id in sorted(component):
            prefix = node_id.split("-", 1)[0] if "-" in node_id else ""
            label = PREFIX_TO_LABEL.get(prefix, "Unknown")
            title = ""
            try:
                model = read_node(knowledge_dir, node_id)
                title = title_for_node(model)
            except (FileNotFoundError, Exception):
                pass
            members.append({
                "node_id": node_id,
                "label": label,
                "title": title,
            })

        communities.append({
            "community_id": i,
            "size": len(component),
            "members": members,
            "labels": dict(_count_labels(members)),
        })

    total_nodes = sum(c["size"] for c in communities)

    return {
        "communities": communities,
        "total_nodes": total_nodes,
        "total_communities": len(communities),
        "filtered_below_min_size": sum(1 for c in components if len(c) < min_size),
    }


def _count_labels(members: list[dict]) -> list[tuple[str, int]]:
    """Count node labels in a community. Returns sorted (label, count) pairs."""
    counts: dict[str, int] = defaultdict(int)
    for m in members:
        counts[m["label"]] += 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)
