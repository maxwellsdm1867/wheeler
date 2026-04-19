"""Wheeler Query MCP Server: read-only graph queries by node type.

8 tools for querying findings, hypotheses, questions, datasets, papers,
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
    instructions="Wheeler query tools: search and list knowledge graph nodes by type (findings, hypotheses, questions, datasets, papers, documents, notes, analyses). Read-only graph queries for research exploration.",
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


# --- Entry point ---


def main():
    import asyncio

    from wheeler.graph.driver import invalidate_async_driver

    asyncio.run(_verify_backend())
    invalidate_async_driver()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
