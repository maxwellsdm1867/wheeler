"""Wheeler Query MCP Server: read-only graph queries by node type.

11 tools for querying findings, hypotheses, questions, datasets, papers,
documents, notes, and analyses.
Run: python -m wheeler.mcp_query
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from wheeler.tools import graph_tools
from wheeler.mcp_shared import (
    _config,
    _logged,
    _verify_backend,
)

mcp = FastMCP(
    "wheeler_query",
    instructions="Typed read-only listings with keyword filters: query_findings, query_hypotheses, query_open_questions, query_datasets, query_papers, query_documents, query_plans, query_notes, query_scripts, query_executions. Returns lists of one node type. query_review_queue is the exception: it lists nodes of ANY type left awaiting human review by a batch ingest. For meaning-based search across all types, use wheeler_core.search_findings or search_context.",
)


# --- Graph queries ---


@mcp.tool()
@_logged
async def query_findings(keyword: str = "", limit: int = 10) -> dict:
    """Search Finding nodes in the Wheeler knowledge graph, optionally filtered by keyword."""
    result = await graph_tools.execute_tool(
        "query_findings", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_hypotheses(status: str = "all", limit: int = 10) -> dict:
    """List Hypothesis nodes in the Wheeler knowledge graph, optionally filtered by status (open/supported/rejected/all)."""
    result = await graph_tools.execute_tool(
        "query_hypotheses", {"status": status, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_open_questions(limit: int = 10) -> dict:
    """List OpenQuestion nodes in the Wheeler knowledge graph, sorted by priority."""
    result = await graph_tools.execute_tool(
        "query_open_questions", {"limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_datasets(keyword: str = "", limit: int = 10) -> dict:
    """Search Dataset nodes in the Wheeler knowledge graph."""
    result = await graph_tools.execute_tool(
        "query_datasets", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_papers(keyword: str = "", limit: int = 10) -> dict:
    """Search Paper nodes in the Wheeler knowledge graph by title or authors."""
    result = await graph_tools.execute_tool(
        "query_papers", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_documents(keyword: str = "", status: str = "", limit: int = 10) -> dict:
    """Search Document nodes in the Wheeler knowledge graph.

    Returns documents registered as graph nodes (research drafts, synthesis
    docs), not arbitrary files. Use standard Read/Glob tools for general file
    operations.
    """
    result = await graph_tools.execute_tool(
        "query_documents", {"keyword": keyword, "status": status, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_plans(keyword: str = "", status: str = "", limit: int = 10) -> dict:
    """Search Plan nodes in the Wheeler knowledge graph by keyword and/or status.

    Returns plans registered as graph nodes (research investigations).
    Filter by status: draft, approved, in-progress, completed, or empty for all.
    """
    result = await graph_tools.execute_tool(
        "query_plans", {"keyword": keyword, "status": status, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_notes(keyword: str = "", limit: int = 10) -> dict:
    """Search ResearchNote nodes in the Wheeler knowledge graph."""
    result = await graph_tools.execute_tool(
        "query_notes", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_analyses(keyword: str = "", limit: int = 20) -> dict:
    """Search Script nodes in the Wheeler knowledge graph by path or language (legacy alias for query_scripts)."""
    result = await graph_tools.execute_tool(
        "query_scripts", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_executions(keyword: str = "", kind: str = "", limit: int = 10) -> dict:
    """Search Execution nodes in the Wheeler knowledge graph by kind or keyword."""
    result = await graph_tools.execute_tool(
        "query_executions",
        {"keyword": keyword, "kind": kind, "limit": limit},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_review_queue(
    batch: str = "", state: str = "undiscussed", limit: int = 20
) -> dict:
    """List Wheeler knowledge graph nodes awaiting human review after a batch ingest.

    A service harvest (for example an Asta Research Assistant mission) can land
    many nodes at once, more than a scientist can rule on in one sitting. Those
    nodes are stamped `custom_review_state="undiscussed"` and `custom_batch=<run
    key>`; this lists them so a review pass can walk the backlog and know what is
    left. Label-agnostic: the queue spans whatever node types the batch produced.

    Args:
        batch: Restrict to one batch key (default: every batch).
        state: Review state to list, `undiscussed` or `discussed`.
        limit: Max items returned. The `batches` roll-up is uncapped.
    """
    result = await graph_tools.execute_tool(
        "query_review_queue",
        {"batch": batch, "state": state, "limit": limit},
        _config,
    )
    return json.loads(result)


# --- Entry point ---


def main():
    import asyncio

    from wheeler.graph.driver import invalidate_async_driver

    asyncio.run(_verify_backend())
    invalidate_async_driver()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
