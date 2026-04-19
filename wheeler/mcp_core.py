"""Wheeler Core MCP Server: graph health, status, context, gaps, node reads, cypher, schema, search.

10 tools for reading and querying the knowledge graph.
Run: python -m wheeler.mcp_core
"""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP

from wheeler.config import WheelerConfig
from wheeler.graph import context, schema
from wheeler.tools import graph_tools
from wheeler.mcp_shared import (
    _config,
    _logged,
    _get_embedding_store,
    _extract_display_text,
    _request_logger,
    _verify_backend,
)

mcp = FastMCP(
    "wheeler_core",
    instructions="Wheeler core graph tools: health checks, status, context, gaps, node reads, raw cypher, schema init, semantic search. Use for reading and querying the research knowledge graph.",
)


def _diagnose_health_error(error_msg: str) -> dict:
    """Return structured diagnosis for common Neo4j connection errors.

    Always includes 'remediation' as a string (backward-compatible).
    Adds 'diagnosis', 'cause', and 'fix' fields for richer LLM context.
    """
    msg = error_msg.lower()
    if "unauthorized" in msg or "authentication" in msg:
        return {
            "diagnosis": "Neo4j authentication failed",
            "cause": "The password in wheeler.yaml does not match the Neo4j database password.",
            "remediation": (
                "Open wheeler.yaml and check the neo4j.password field matches "
                "what you set in Neo4j Desktop. Wheeler's default password is "
                "'research-graph'. If you forgot the password, delete the DBMS "
                "in Neo4j Desktop and create a new one."
            ),
            "fix": [
                "Open wheeler.yaml and check the neo4j.password field matches what you set in Neo4j Desktop.",
                "Wheeler's default password is 'research-graph'.",
                "If you forgot the password: delete the DBMS in Neo4j Desktop and create a new one.",
            ],
        }
    if "refused" in msg or "unavailable" in msg or "connection" in msg or "failed to establish" in msg:
        return {
            "diagnosis": "Cannot connect to Neo4j",
            "cause": "Neo4j is not running, or another process is using port 7687.",
            "remediation": (
                "Open Neo4j Desktop and click Start on your database (look for "
                "the green Running indicator), or run: docker start wheeler-neo4j. "
                "Check for port conflicts: lsof -i :7687"
            ),
            "fix": [
                "Open Neo4j Desktop and click Start on your database (look for the green Running indicator).",
                "If using Docker: docker start wheeler-neo4j",
                "If using Homebrew: brew services start neo4j",
                "Check for port conflicts: lsof -i :7687",
            ],
        }
    return {
        "remediation": (
            "Open Neo4j Desktop and start the database, "
            "or run: docker start wheeler-neo4j"
        ),
    }


# --- Graph health & status ---


@mcp.tool()
@_logged
async def graph_health() -> dict:
    """Check Wheeler knowledge graph database connectivity and report diagnostics.

    Returns backend type, connection status, database name, node counts,
    and any errors. Use this to verify the graph is working before
    starting research work that depends on it.
    """
    result: dict = {
        "backend": _config.graph.backend,
        "database": _config.neo4j.database,
        "status": "unknown",
        "node_count": 0,
        "error": None,
    }
    try:
        counts = await schema.get_status(_config)
        if counts.get("_status") == "offline":
            result["status"] = "offline"
            result["error"] = counts.get("_error", "Unknown error")
            result["blocking"] = True
            result.update(_diagnose_health_error(counts.get("_error", "")))
        else:
            node_counts = {k: v for k, v in counts.items()
                          if not k.startswith("_")}
            total = sum(node_counts.values())
            result["status"] = "connected"
            result["node_count"] = total
            result["node_counts"] = node_counts
    except Exception as exc:
        result["status"] = "offline"
        result["error"] = str(exc)
        result["blocking"] = True
        result.update(_diagnose_health_error(str(exc)))

    # Check knowledge/ directory
    knowledge_path = Path(_config.knowledge_path)
    if knowledge_path.exists():
        json_files = list(knowledge_path.glob("*.json"))
        result["knowledge_files"] = len(json_files)
    else:
        result["knowledge_files"] = 0
        if result["status"] == "connected":
            result["warnings"] = ["knowledge/ directory does not exist -- run /wh:init"]

    return result


@mcp.tool()
@_logged
async def graph_status() -> dict:
    """Return node counts per label in the Wheeler knowledge graph."""
    counts = await schema.get_status(_config)
    if counts.get("_status") == "offline":
        return {
            "status": "offline",
            "error": counts.get("_error", "Unknown error"),
            "blocking": True,
            "remediation": (
                "Open Neo4j Desktop and start the database, "
                "or run: docker start wheeler-neo4j"
            ),
            "node_counts": {k: v for k, v in counts.items()
                           if not k.startswith("_")},
        }
    return counts


@mcp.tool()
@_logged
async def graph_context(topic: str = "") -> str:
    """Fetch size-limited context from the Wheeler knowledge graph (recent findings, open questions, hypotheses).

    When topic is provided, filters results to those matching the topic
    (case-insensitive substring match on descriptions/statements).
    Leave empty to get all recent context.
    """
    return await context.fetch_context(_config, topic=topic)


@mcp.tool()
@_logged
async def graph_gaps() -> dict:
    """Find gaps in the Wheeler knowledge graph: unlinked questions, unsupported hypotheses, stale analyses, near-duplicates."""
    result = await graph_tools.execute_tool("graph_gaps", {}, _config)
    gaps = json.loads(result)

    # Enrich with near-duplicate detection from embeddings (if available)
    try:
        store = _get_embedding_store()
        pairs = store.find_similar_pairs(threshold=0.85)
        gaps["potential_duplicates"] = [
            {
                "node_a": {"id": a.node_id, "label": a.label, "text": a.text},
                "node_b": {"id": b.node_id, "label": b.label, "text": b.text},
                "similarity": round(score, 4),
            }
            for a, b, score in pairs[:10]  # cap at 10 pairs
        ]
        gaps["total_gaps"] = gaps.get("total_gaps", 0) + len(gaps["potential_duplicates"])
    except (ImportError, Exception):
        # Embeddings not available: skip duplicate detection silently
        pass

    return gaps


# --- Node read (filesystem) ---


@mcp.tool()
@_logged
async def show_node(node_id: str) -> dict:
    """Read the full content of a Wheeler knowledge graph node from its JSON file.

    Returns the complete node data including all fields. Use this to
    read findings, hypotheses, questions, papers, etc. without needing
    a graph query.
    """
    from wheeler.knowledge import store

    knowledge_path = Path(_config.knowledge_path)
    try:
        model = store.read_node(knowledge_path, node_id)
        return model.model_dump()
    except FileNotFoundError:
        return {"error": f"Node {node_id} not found"}


# --- Entity resolution (read-only) ---


@mcp.tool()
@_logged
async def propose_merge(node_id_a: str, node_id_b: str) -> dict:
    """Compare two knowledge graph nodes and propose a merge.

    Returns which node to keep (more relationships), field conflicts,
    and relationships that would be redirected. Read-only, no changes made.
    Use before execute_merge to preview the operation.
    """
    from wheeler.merge import propose_merge as _propose
    return await _propose(_config, node_id_a, node_id_b)


# --- Raw Cypher ---


@mcp.tool()
@_logged
async def run_cypher(query: str) -> dict:
    """Run a read-only Cypher query against the Wheeler knowledge graph database.

    Use for ad-hoc research graph exploration: relationship traversal, path queries,
    aggregations, or anything the higher-level tools don't cover.

    Examples:
        "MATCH (f:Finding)-[:SUPPORTS]->(h:Hypothesis) RETURN f.id, h.statement"
        "MATCH p=(a:Analysis)-[:GENERATED]->(f:Finding) RETURN p"
        "MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count ORDER BY count DESC"

    Args:
        query: Cypher query string (read-only: no CREATE/DELETE/SET)
    """
    # Block write operations
    upper = query.strip().upper()
    for keyword in ("CREATE ", "DELETE ", "DETACH ", "SET ", "REMOVE ", "MERGE ", "DROP "):
        if keyword in upper:
            return {"error": f"Write operations not allowed via run_cypher. Use Wheeler's mutation tools (add_finding, link_nodes, etc.) instead."}

    try:
        backend = await graph_tools._get_backend(_config)
        records = await backend.run_cypher(query)
        return {"results": records, "count": len(records)}
    except Exception as exc:
        return {"error": str(exc), "results": [], "count": 0}


# --- Schema ---


@mcp.tool()
@_logged
async def init_schema() -> dict:
    """Apply Wheeler knowledge graph constraints and indexes to Neo4j. Returns count of applied statements."""
    applied = await schema.init_schema(_config)
    return {"applied": len(applied)}


# --- Semantic search ---


@mcp.tool()
@_logged
async def search_findings(
    query: str,
    limit: int = 10,
    label: str = "",
    mode: str = "multi",
) -> dict:
    """Search across Wheeler knowledge graph nodes for research context retrieval.

    Combines semantic (embedding similarity), keyword (graph queries),
    temporal (recency), and fulltext (Neo4j index) channels via Reciprocal
    Rank Fusion for better recall than any single channel alone. Use for
    finding related research nodes when linking new entries or exploring
    existing knowledge.

    Args:
        query: Natural language search query
        limit: Maximum results (default 10)
        label: Optional filter by node type (Finding, Hypothesis, OpenQuestion, Paper, Dataset, Document)
        mode: Retrieval mode -- "multi" (default, all channels), "semantic" (embeddings only),
              "keyword" (graph keyword only), "temporal" (most recent only), "fulltext" (Neo4j fulltext index only)
    """
    try:
        from wheeler.search.retrieval import multi_search

        results = await multi_search(
            query, _config, limit=limit, label=label, mode=mode,
        )
        return {
            "results": [
                {
                    "node_id": r.get("id", ""),
                    "label": r.get("type", ""),
                    "text": _extract_display_text(r),
                    "score": r.get("rrf_score", 0.0),
                }
                for r in results
            ],
            "count": len(results),
            "query": query,
            "mode": mode,
        }
    except Exception as exc:
        return {
            "error": f"Search failed: {exc}",
            "results": [],
            "count": 0,
        }


@mcp.tool()
@_logged
async def search_context(
    query: str,
    limit: int = 5,
    hops: int = 2,
    label: str = "",
) -> dict:
    """Search the knowledge graph and expand results via graph traversal.

    Returns seed nodes from search plus their graph neighborhood:
    provenance chains (2 hops via USED/WAS_GENERATED_BY/WAS_DERIVED_FROM),
    semantic links (1 hop via SUPPORTS/CONTRADICTS), and other relationships.

    Use this instead of search_findings when you need the full experimental
    context around results, not just the results themselves. Especially
    useful for "why" and "how" questions that need provenance chains.

    Args:
        query: Natural language search query
        limit: Maximum seed results (default 5)
        hops: Maximum provenance chain depth (default 2)
        label: Optional filter by node type
    """
    from wheeler.search.retrieval import multi_search, expand_search_results

    try:
        seeds = await multi_search(query, _config, limit=limit, label=label)
        expanded = await expand_search_results(
            seeds, _config, max_hops_prov=hops,
        )
        return expanded
    except Exception as exc:
        return {
            "error": f"Search context failed: {exc}",
            "seed_nodes": [],
            "related_nodes": [],
        }


@mcp.tool()
@_logged
async def index_node(node_id: str, label: str, text: str) -> dict:
    """Add or update a Wheeler knowledge graph node's semantic embedding for search.

    Call this after creating or updating a research node to make it searchable.
    The embedding is generated from the text content using a local model.

    Args:
        node_id: The node ID (e.g., F-3a2b)
        label: Node type (Finding, Hypothesis, etc.)
        text: The text content to embed
    """
    try:
        store = _get_embedding_store()
        store.add(node_id, label, text)
        store.save()
        return {"status": "indexed", "node_id": node_id, "label": label}
    except ImportError:
        return {"error": "Semantic search not available. Install with: pip install wheeler[search]"}
    except Exception as exc:
        return {"error": f"Indexing failed: {exc}"}


# --- Request log ---


@mcp.tool()
async def request_log_summary() -> dict:
    """Return summary stats of recent Wheeler MCP tool calls (latency, error rate, call counts)."""
    return _request_logger.summary()


# --- Entry point ---


def main():
    import asyncio

    from wheeler.graph.driver import invalidate_async_driver

    asyncio.run(_verify_backend())
    invalidate_async_driver()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
