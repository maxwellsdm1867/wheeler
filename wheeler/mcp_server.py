"""Wheeler MCP Server — exposes knowledge graph, citations, workspace, and provenance.

Thin wrapper over existing Wheeler modules. Each tool loads config once at startup,
calls the same functions the CLI and engine use, and returns JSON-serializable results.

Run: python -m wheeler.mcp_server
"""

from __future__ import annotations

import asyncio
import json
import sys

from fastmcp import FastMCP

from wheeler.config import load_config, WheelerConfig
from wheeler.graph import context, schema
from wheeler.graph import provenance
from wheeler.tools import graph_tools
from wheeler.validation import citations
from wheeler import workspace

# Load config once at startup
_config: WheelerConfig = load_config()

mcp = FastMCP(
    "wheeler",
    instructions="Wheeler knowledge graph, citation validation, and workspace tools",
)


# --- Graph status & context ---


@mcp.tool()
async def graph_status() -> dict:
    """Return node counts per label in the knowledge graph."""
    return await schema.get_status(_config)


@mcp.tool()
async def graph_context() -> str:
    """Fetch size-limited graph context (recent findings, open questions, hypotheses)."""
    return await context.fetch_context(_config)


# --- Graph mutations ---


@mcp.tool()
async def add_finding(description: str, confidence: float) -> dict:
    """Add a Finding to the knowledge graph. Returns the new node ID."""
    result = await graph_tools.execute_tool(
        "add_finding", {"description": description, "confidence": confidence}, _config
    )
    return json.loads(result)


@mcp.tool()
async def add_hypothesis(statement: str, status: str = "open") -> dict:
    """Add a Hypothesis to the knowledge graph. Returns the new node ID."""
    result = await graph_tools.execute_tool(
        "add_hypothesis", {"statement": statement, "status": status}, _config
    )
    return json.loads(result)


@mcp.tool()
async def add_question(question: str, priority: int = 5) -> dict:
    """Add an OpenQuestion to the knowledge graph. Returns the new node ID."""
    result = await graph_tools.execute_tool(
        "add_question", {"question": question, "priority": priority}, _config
    )
    return json.loads(result)


@mcp.tool()
async def link_nodes(source_id: str, target_id: str, relationship: str) -> dict:
    """Create a relationship between two graph nodes."""
    result = await graph_tools.execute_tool(
        "link_nodes",
        {"source_id": source_id, "target_id": target_id, "relationship": relationship},
        _config,
    )
    return json.loads(result)


@mcp.tool()
async def add_dataset(path: str, type: str, description: str) -> dict:
    """Add a Dataset node to the knowledge graph. Returns the new node ID."""
    result = await graph_tools.execute_tool(
        "add_dataset", {"path": path, "type": type, "description": description}, _config
    )
    return json.loads(result)


# --- Graph queries ---


@mcp.tool()
async def query_findings(keyword: str = "", limit: int = 10) -> dict:
    """Search findings in the knowledge graph, optionally filtered by keyword."""
    result = await graph_tools.execute_tool(
        "query_findings", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
async def query_hypotheses(status: str = "all", limit: int = 10) -> dict:
    """List hypotheses, optionally filtered by status (open/supported/rejected/all)."""
    result = await graph_tools.execute_tool(
        "query_hypotheses", {"status": status, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
async def query_open_questions(limit: int = 10) -> dict:
    """List open questions from the knowledge graph, sorted by priority."""
    result = await graph_tools.execute_tool(
        "query_open_questions", {"limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
async def query_datasets(keyword: str = "", limit: int = 10) -> dict:
    """Search Dataset nodes in the knowledge graph."""
    result = await graph_tools.execute_tool(
        "query_datasets", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
async def graph_gaps() -> dict:
    """Find knowledge gaps: unlinked questions, unsupported hypotheses, stale analyses."""
    result = await graph_tools.execute_tool("graph_gaps", {}, _config)
    return json.loads(result)


# --- Citation validation ---


@mcp.tool()
async def extract_citations(text: str) -> list[str]:
    """Extract all node ID citations ([F-3a2b] format) from text using regex."""
    return citations.extract_citations(text)


@mcp.tool()
async def validate_citations(text: str) -> dict:
    """Validate all citations in text against Neo4j. Checks existence and provenance."""
    results = await citations.validate_citations(text, _config)
    valid = sum(1 for r in results if r.status == citations.CitationStatus.VALID)
    return {
        "total": len(results),
        "valid": valid,
        "results": [
            {
                "node_id": r.node_id,
                "status": r.status.value,
                "label": r.label,
                "details": r.details,
            }
            for r in results
        ],
    }


# --- Workspace ---


@mcp.tool()
async def scan_workspace() -> dict:
    """Scan the project directory for scripts and data files."""
    summary = workspace.scan_workspace(_config.workspace)
    return {
        "project_dir": summary.project_dir,
        "total_files": summary.total_files,
        "scripts": [
            {"path": f.path, "extension": f.extension, "size_bytes": f.size_bytes}
            for f in summary.scripts
        ],
        "data_files": [
            {"path": f.path, "extension": f.extension, "size_bytes": f.size_bytes}
            for f in summary.data_files
        ],
    }


# --- Provenance ---


@mcp.tool()
async def detect_stale() -> list[dict]:
    """Find Analysis nodes whose script has been modified since execution."""
    stale = await provenance.detect_stale_analyses(_config)
    return [
        {
            "node_id": s.node_id,
            "script_path": s.script_path,
            "stored_hash": s.stored_hash,
            "current_hash": s.current_hash,
            "executed_at": s.executed_at,
        }
        for s in stale
    ]


@mcp.tool()
async def hash_file(path: str) -> dict:
    """Compute SHA-256 hash of a file for provenance tracking."""
    sha = provenance.hash_file(path)
    return {"path": path, "sha256": sha}


# --- Schema ---


@mcp.tool()
async def init_schema() -> dict:
    """Apply all constraints and indexes to Neo4j. Returns count of applied statements."""
    applied = await schema.init_schema(_config)
    return {"applied": len(applied)}


# --- Entry point ---


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
