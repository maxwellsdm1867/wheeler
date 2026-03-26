"""Wheeler MCP Server — exposes knowledge graph, citations, workspace, and provenance.

Thin wrapper over existing Wheeler modules. Each tool loads config once at startup,
calls the same functions the CLI and engine use, and returns JSON-serializable results.

Run: python -m wheeler.mcp_server
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from wheeler.config import configure_logging, load_config, WheelerConfig
from wheeler.graph import context, schema
from wheeler.graph import provenance
from wheeler.tools import graph_tools
from wheeler.validation import citations
from wheeler import workspace

# Configure logging and load config once at startup
configure_logging()
_config: WheelerConfig = load_config()

# Lazy-loaded singleton for semantic search
_embedding_store: object | None = None


def _get_embedding_store():
    """Return the singleton EmbeddingStore, creating it on first call."""
    global _embedding_store
    if _embedding_store is None:
        from wheeler.search.embeddings import EmbeddingStore

        store_path = _config.search.store_path
        _embedding_store = EmbeddingStore(store_path)
        _embedding_store.load()
    return _embedding_store


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


@mcp.tool()
async def set_tier(node_id: str, tier: str) -> dict:
    """Set context tier of a node to 'reference' (established) or 'generated' (new work)."""
    result = await graph_tools.execute_tool(
        "set_tier", {"node_id": node_id, "tier": tier}, _config
    )
    return json.loads(result)


@mcp.tool()
async def add_paper(title: str, authors: str = "", doi: str = "", year: int = 0) -> dict:
    """Add a Paper to the knowledge graph for literature provenance. Returns the new node ID."""
    result = await graph_tools.execute_tool(
        "add_paper",
        {"title": title, "authors": authors, "doi": doi, "year": year},
        _config,
    )
    return json.loads(result)


@mcp.tool()
async def add_document(title: str, path: str, section: str = "", status: str = "draft") -> dict:
    """Add a Document to the knowledge graph to track written output. Returns the new node ID."""
    result = await graph_tools.execute_tool(
        "add_document",
        {"title": title, "path": path, "section": section, "status": status},
        _config,
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
async def query_papers(keyword: str = "", limit: int = 10) -> dict:
    """Search Paper nodes in the knowledge graph by title or authors."""
    result = await graph_tools.execute_tool(
        "query_papers", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
async def query_documents(keyword: str = "", status: str = "", limit: int = 10) -> dict:
    """Search Document nodes in the knowledge graph."""
    result = await graph_tools.execute_tool(
        "query_documents", {"keyword": keyword, "status": status, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
async def graph_gaps() -> dict:
    """Find knowledge gaps: unlinked questions, unsupported hypotheses, stale analyses."""
    result = await graph_tools.execute_tool("graph_gaps", {}, _config)
    return json.loads(result)


# --- Semantic search ---


@mcp.tool()
async def search_findings(query: str, limit: int = 10, label: str = "") -> dict:
    """Semantic search across knowledge graph nodes by meaning, not just keywords.

    Uses embeddings to find findings, hypotheses, questions, and other nodes
    that are semantically similar to the query text. Much more powerful than
    keyword search — finds conceptually related results even with different wording.

    Args:
        query: Natural language search query
        limit: Maximum results (default 10)
        label: Optional filter by node type (Finding, Hypothesis, OpenQuestion, Paper, Dataset, Document)
    """
    try:
        store = _get_embedding_store()
        results = store.search(query, limit=limit, label_filter=label or None)
        return {
            "results": [
                {
                    "node_id": r.node_id,
                    "label": r.label,
                    "text": r.text,
                    "score": round(r.score, 4),
                }
                for r in results
            ],
            "count": len(results),
            "query": query,
        }
    except ImportError:
        return {
            "error": "Semantic search not available. Install with: pip install wheeler[search]",
            "results": [],
            "count": 0,
        }
    except Exception as exc:
        return {
            "error": f"Search failed: {exc}",
            "results": [],
            "count": 0,
        }


@mcp.tool()
async def index_node(node_id: str, label: str, text: str) -> dict:
    """Add or update a node's semantic embedding for search.

    Call this after creating or updating a node to make it searchable.
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
    summary = workspace.scan_workspace(_config.workspace, _config.paths)
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
