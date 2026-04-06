"""Wheeler MCP Server — exposes knowledge graph, citations, workspace, and provenance.

Thin wrapper over existing Wheeler modules. Each tool loads config once at startup,
calls the same functions the CLI and engine use, and returns JSON-serializable results.

Run: python -m wheeler.mcp_server
"""

from __future__ import annotations

import functools
import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

from wheeler.config import configure_logging, load_config, WheelerConfig
from wheeler.graph import context, schema
from wheeler.graph import provenance
from wheeler.request_log import RequestLog, RequestLogger
from wheeler.tools import graph_tools
from wheeler.validation import citations
from wheeler import workspace

# Configure logging and load config once at startup
configure_logging()
_config: WheelerConfig = load_config()

# Unique session ID generated once per MCP server process
_SESSION_ID: str = f"session-{secrets.token_hex(4)}"

# Request logger — append-only JSONL in .wheeler/
_request_logger = RequestLogger(Path(".wheeler"))

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


def _logged(func):
    """Wrap an MCP tool handler with request logging."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        tool_name = func.__name__
        try:
            result = await func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            node_id = ""
            label = ""
            if isinstance(result, dict):
                node_id = result.get("node_id", "") or ""
                label = result.get("label", "") or ""
            _request_logger.log(RequestLog(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_name=tool_name,
                latency_ms=round(elapsed, 1),
                status="ok",
                session_id=_SESSION_ID,
                node_id=str(node_id),
                label=str(label),
                error="",
            ))
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            _request_logger.log(RequestLog(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_name=tool_name,
                latency_ms=round(elapsed, 1),
                status="error",
                session_id=_SESSION_ID,
                node_id="",
                label="",
                error=str(exc),
            ))
            raise

    return wrapper


def _check_similar_nodes(text: str, label: str, exclude_id: str | None = None) -> list[dict]:
    """Check for similar existing nodes. Returns matches or empty list.

    Fails silently if embeddings aren't available — this is purely advisory.
    """
    try:
        store = _get_embedding_store()
        matches = store.check_similar(text, threshold=0.85, label_filter=label, exclude_id=exclude_id)
        return [
            {"node_id": m.node_id, "text": m.text, "similarity": round(m.score, 4)}
            for m in matches[:3]
        ]
    except (ImportError, Exception):
        return []


# --- Graph health & status ---


@mcp.tool()
@_logged
async def graph_health() -> dict:
    """Check graph database connectivity and report diagnostics.

    Returns backend type, connection status, database name, node counts,
    and any errors. Use this to verify the graph is working before
    starting work that depends on it.
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
        total = sum(counts.values())
        result["status"] = "connected"
        result["node_count"] = total
        result["node_counts"] = counts
    except Exception as exc:
        result["status"] = "offline"
        result["error"] = str(exc)

    # Check knowledge/ directory
    from pathlib import Path
    knowledge_path = Path(_config.knowledge_path)
    if knowledge_path.exists():
        json_files = list(knowledge_path.glob("*.json"))
        result["knowledge_files"] = len(json_files)
    else:
        result["knowledge_files"] = 0
        if result["status"] == "connected":
            result["warnings"] = ["knowledge/ directory does not exist — run /wh:init"]

    return result


@mcp.tool()
@_logged
async def graph_status() -> dict:
    """Return node counts per label in the knowledge graph."""
    return await schema.get_status(_config)


@mcp.tool()
@_logged
async def graph_context() -> str:
    """Fetch size-limited graph context (recent findings, open questions, hypotheses)."""
    return await context.fetch_context(_config)


# --- Node read (filesystem) ---


@mcp.tool()
@_logged
async def show_node(node_id: str) -> dict:
    """Read the full content of a knowledge node from its JSON file.

    Returns the complete node data including all fields. Use this to
    read findings, hypotheses, questions, papers, etc. without needing
    a graph query.
    """
    from pathlib import Path
    from wheeler.knowledge import store

    knowledge_path = Path(_config.knowledge_path)
    try:
        model = store.read_node(knowledge_path, node_id)
        return model.model_dump()
    except FileNotFoundError:
        return {"error": f"Node {node_id} not found"}


# --- Graph mutations ---


@mcp.tool()
@_logged
async def add_finding(
    description: str,
    confidence: float,
    path: str = "",
    artifact_type: str = "",
    source: str = "",
    execution_kind: str = "",
    used_entities: str = "",
    execution_description: str = "",
) -> dict:
    """Add a Finding to the knowledge graph. Returns the new node ID.

    A finding can be a number, a figure, a table, or any result worth
    recording. Set artifact_type (e.g. "figure", "number", "table") and
    path to link to the actual file. Set source for external findings
    (e.g. a collaborator's name or paper ID).

    Provenance-completing: set execution_kind (e.g. "script", "discuss")
    to auto-create an Execution activity and link provenance.  Pass
    used_entities as comma-separated node IDs (e.g. "D-abc,S-def") to
    link what the execution consumed.
    """
    result = await graph_tools.execute_tool(
        "add_finding",
        {"description": description, "confidence": confidence,
         "path": path, "artifact_type": artifact_type, "source": source,
         "session_id": _SESSION_ID,
         "execution_kind": execution_kind,
         "used_entities": used_entities,
         "execution_description": execution_description},
        _config,
    )
    parsed = json.loads(result)
    similar = _check_similar_nodes(description, "Finding", exclude_id=parsed.get("node_id"))
    if similar:
        parsed["similar_existing"] = similar
    return parsed


@mcp.tool()
@_logged
async def add_hypothesis(
    statement: str,
    status: str = "open",
    execution_kind: str = "",
    used_entities: str = "",
    execution_description: str = "",
) -> dict:
    """Add a Hypothesis to the knowledge graph. Returns the new node ID.

    Provenance-completing: set execution_kind to auto-create an Execution
    and link provenance. Pass used_entities as comma-separated node IDs.
    """
    result = await graph_tools.execute_tool(
        "add_hypothesis",
        {"statement": statement, "status": status, "session_id": _SESSION_ID,
         "execution_kind": execution_kind,
         "used_entities": used_entities,
         "execution_description": execution_description},
        _config,
    )
    parsed = json.loads(result)
    similar = _check_similar_nodes(statement, "Hypothesis", exclude_id=parsed.get("node_id"))
    if similar:
        parsed["similar_existing"] = similar
    return parsed


@mcp.tool()
@_logged
async def add_question(
    question: str,
    priority: int = 5,
    execution_kind: str = "",
    used_entities: str = "",
    execution_description: str = "",
) -> dict:
    """Add an OpenQuestion to the knowledge graph. Returns the new node ID.

    Provenance-completing: set execution_kind to auto-create an Execution
    and link provenance. Pass used_entities as comma-separated node IDs.
    """
    result = await graph_tools.execute_tool(
        "add_question",
        {"question": question, "priority": priority, "session_id": _SESSION_ID,
         "execution_kind": execution_kind,
         "used_entities": used_entities,
         "execution_description": execution_description},
        _config,
    )
    parsed = json.loads(result)
    similar = _check_similar_nodes(question, "OpenQuestion", exclude_id=parsed.get("node_id"))
    if similar:
        parsed["similar_existing"] = similar
    return parsed


@mcp.tool()
@_logged
async def link_nodes(source_id: str, target_id: str, relationship: str) -> dict:
    """Create a relationship between two graph nodes."""
    result = await graph_tools.execute_tool(
        "link_nodes",
        {"source_id": source_id, "target_id": target_id, "relationship": relationship,
         "session_id": _SESSION_ID},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def add_dataset(path: str, type: str, description: str) -> dict:
    """Add a Dataset node to the knowledge graph. Returns the new node ID."""
    result = await graph_tools.execute_tool(
        "add_dataset",
        {"path": path, "type": type, "description": description, "session_id": _SESSION_ID},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def add_analysis(
    script_path: str,
    language: str,
    script_hash: str = "",
    language_version: str = "",
    parameters: str = "",
    output_path: str = "",
    output_hash: str = "",
) -> dict:
    """Add a Script node to track a code file with provenance (legacy alias).

    If script_hash is empty, Wheeler will compute it from the file.
    Use this when registering scripts or during /wh:ingest.

    Args:
        script_path: Path to the script file
        language: Programming language (matlab, python, r, julia, etc.)
        script_hash: SHA-256 hash (auto-computed if empty and file exists)
        language_version: Language version (e.g., "3.14", "R2022a")
        parameters: Unused (kept for backward compatibility)
        output_path: Unused (kept for backward compatibility)
        output_hash: Unused (kept for backward compatibility)
    """
    # Auto-compute hash if not provided
    if not script_hash:
        from pathlib import Path as P
        p = P(script_path)
        if p.exists():
            script_hash = provenance.hash_file(p)

    result = await graph_tools.execute_tool(
        "add_script",
        {
            "path": script_path,
            "hash": script_hash,
            "language": language,
            "version": language_version,
            "session_id": _SESSION_ID,
        },
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def set_tier(node_id: str, tier: str) -> dict:
    """Set context tier of a node to 'reference' (established) or 'generated' (new work)."""
    result = await graph_tools.execute_tool(
        "set_tier", {"node_id": node_id, "tier": tier, "session_id": _SESSION_ID}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def add_paper(title: str, authors: str = "", doi: str = "", year: int = 0) -> dict:
    """Add a Paper to the knowledge graph for literature provenance. Returns the new node ID."""
    result = await graph_tools.execute_tool(
        "add_paper",
        {"title": title, "authors": authors, "doi": doi, "year": year,
         "session_id": _SESSION_ID},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def add_document(
    title: str,
    path: str,
    section: str = "",
    status: str = "draft",
    execution_kind: str = "",
    used_entities: str = "",
    execution_description: str = "",
) -> dict:
    """Add a Document to the knowledge graph. Returns the new node ID.

    Provenance-completing: set execution_kind (e.g. "write") to auto-create
    an Execution and link provenance. Pass used_entities as comma-separated
    node IDs of findings and papers cited.
    """
    result = await graph_tools.execute_tool(
        "add_document",
        {"title": title, "path": path, "section": section, "status": status,
         "session_id": _SESSION_ID,
         "execution_kind": execution_kind,
         "used_entities": used_entities,
         "execution_description": execution_description},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def add_note(
    content: str,
    title: str = "",
    context: str = "",
    execution_kind: str = "",
    used_entities: str = "",
    execution_description: str = "",
) -> dict:
    """Add a ResearchNote to capture an insight or idea. Returns the new node ID.

    Provenance-completing: set execution_kind to auto-create an Execution
    and link provenance. Pass used_entities as comma-separated node IDs.
    """
    result = await graph_tools.execute_tool(
        "add_note",
        {"content": content, "title": title, "context": context,
         "session_id": _SESSION_ID,
         "execution_kind": execution_kind,
         "used_entities": used_entities,
         "execution_description": execution_description},
        _config,
    )
    return json.loads(result)


# --- Graph queries ---


@mcp.tool()
@_logged
async def query_findings(keyword: str = "", limit: int = 10) -> dict:
    """Search findings in the knowledge graph, optionally filtered by keyword."""
    result = await graph_tools.execute_tool(
        "query_findings", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_hypotheses(status: str = "all", limit: int = 10) -> dict:
    """List hypotheses, optionally filtered by status (open/supported/rejected/all)."""
    result = await graph_tools.execute_tool(
        "query_hypotheses", {"status": status, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_open_questions(limit: int = 10) -> dict:
    """List open questions from the knowledge graph, sorted by priority."""
    result = await graph_tools.execute_tool(
        "query_open_questions", {"limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_datasets(keyword: str = "", limit: int = 10) -> dict:
    """Search Dataset nodes in the knowledge graph."""
    result = await graph_tools.execute_tool(
        "query_datasets", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_papers(keyword: str = "", limit: int = 10) -> dict:
    """Search Paper nodes in the knowledge graph by title or authors."""
    result = await graph_tools.execute_tool(
        "query_papers", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_notes(keyword: str = "", limit: int = 10) -> dict:
    """Search research notes in the knowledge graph."""
    result = await graph_tools.execute_tool(
        "query_notes", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_documents(keyword: str = "", status: str = "", limit: int = 10) -> dict:
    """Search Document nodes in the knowledge graph."""
    result = await graph_tools.execute_tool(
        "query_documents", {"keyword": keyword, "status": status, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def query_analyses(keyword: str = "", limit: int = 20) -> dict:
    """Search Script nodes in the knowledge graph by path or language (legacy alias for query_scripts)."""
    result = await graph_tools.execute_tool(
        "query_scripts", {"keyword": keyword, "limit": limit}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def graph_gaps() -> dict:
    """Find knowledge gaps: unlinked questions, unsupported hypotheses, stale analyses, near-duplicates."""
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
        # Embeddings not available — skip duplicate detection silently
        pass

    return gaps


# --- Semantic search ---


@mcp.tool()
@_logged
async def search_findings(
    query: str,
    limit: int = 10,
    label: str = "",
    mode: str = "multi",
) -> dict:
    """Search across knowledge graph nodes using multi-channel retrieval.

    Combines semantic (embedding similarity), keyword (graph queries), and
    temporal (recency) channels via Reciprocal Rank Fusion for better recall
    than any single channel alone.

    Args:
        query: Natural language search query
        limit: Maximum results (default 10)
        label: Optional filter by node type (Finding, Hypothesis, OpenQuestion, Paper, Dataset, Document)
        mode: Retrieval mode — "multi" (default, all channels), "semantic" (embeddings only),
              "keyword" (graph keyword only), "temporal" (most recent only)
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


def _extract_display_text(node: dict) -> str:
    """Extract the best display text from a node dict.

    Tries common text fields in priority order.
    """
    for field in ("description", "statement", "question", "title", "content"):
        val = node.get(field)
        if val:
            return val
    return ""


@mcp.tool()
@_logged
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
@_logged
async def extract_citations(text: str) -> list[str]:
    """Extract all node ID citations ([F-3a2b] format) from text using regex."""
    return citations.extract_citations(text)


@mcp.tool()
@_logged
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
@_logged
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
@_logged
async def detect_stale() -> list[dict]:
    """Find Script nodes whose file has been modified since last recorded hash."""
    stale = await provenance.detect_stale_scripts(_config)
    return [
        {
            "node_id": s.node_id,
            "path": s.path,
            "stored_hash": s.stored_hash,
            "current_hash": s.current_hash,
        }
        for s in stale
    ]


@mcp.tool()
@_logged
async def hash_file(path: str) -> dict:
    """Compute SHA-256 hash of a file for provenance tracking."""
    sha = provenance.hash_file(path)
    return {"path": path, "sha256": sha}


@mcp.tool()
@_logged
async def scan_dependencies(script_path: str, link_to_graph: bool = False) -> dict:
    """Scan a Python script for imports, data file references, and function calls.

    Uses AST parsing (no execution) to extract:
    - imports: all imported modules
    - data_files: file paths found in string literals and data-loading calls
      (pd.read_csv, np.load, scipy.io.loadmat, etc.)
    - function_calls: unique function/method calls

    When link_to_graph is True and the script has a matching Analysis node,
    creates DEPENDS_ON edges to any Dataset nodes whose paths match
    detected data files.

    Args:
        script_path: Path to a .py file
        link_to_graph: If True, create graph edges for discovered dependencies
    """
    from wheeler.depscanner import scan_script

    try:
        dep_map = scan_script(script_path)
    except FileNotFoundError:
        return {"error": f"Script not found: {script_path}"}
    except SyntaxError as exc:
        return {"error": f"Parse error: {exc}"}

    result = dep_map.to_dict()

    if link_to_graph and dep_map.data_files:
        edges = await _link_dependencies(script_path, dep_map.data_files)
        result["edges_created"] = edges

    return result


async def _link_dependencies(
    script_path: str, data_files: list[dict[str, str]]
) -> list[dict]:
    """Best-effort: find Analysis node for this script and link to matching Datasets."""
    edges: list[dict] = []
    try:
        backend = await graph_tools._get_backend(_config)

        # Find Analysis node by script_path
        analyses = await backend.run_cypher(
            "MATCH (a:Analysis) WHERE a.script_path CONTAINS $path "
            "RETURN a.id AS id ORDER BY a.date DESC LIMIT 1",
            parameters={"path": script_path},
        )
        if not analyses:
            return [{"note": f"No Analysis node found for {script_path}"}]

        analysis_id = analyses[0]["id"]

        # Find Dataset nodes matching any of the detected data file paths
        for df in data_files:
            datasets = await backend.run_cypher(
                "MATCH (d:Dataset) WHERE d.path CONTAINS $path "
                "RETURN d.id AS id",
                parameters={"path": df["path"]},
            )
            for ds in datasets:
                link_result = await graph_tools.execute_tool(
                    "link_nodes",
                    {
                        "source_id": analysis_id,
                        "target_id": ds["id"],
                        "relationship": "USED_DATA",
                    },
                    _config,
                )
                edges.append(json.loads(link_result))
    except Exception as exc:
        edges.append({"error": f"Graph linking failed: {exc}"})
    return edges


# --- Raw Cypher ---


@mcp.tool()
@_logged
async def run_cypher(query: str) -> dict:
    """Run a read-only Cypher query against the graph database.

    Use for ad-hoc graph exploration: relationship traversal, path queries,
    aggregations, or anything the higher-level tools don't cover.

    Examples:
        "MATCH (f:Finding)-[:SUPPORTS]->(h:Hypothesis) RETURN f.id, h.statement"
        "MATCH p=(a:Analysis)-[:GENERATED]->(f:Finding) RETURN p"
        "MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count ORDER BY count DESC"

    Args:
        query: Cypher query string (read-only — no CREATE/DELETE/SET)
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
    """Apply all constraints and indexes to Neo4j. Returns count of applied statements."""
    applied = await schema.init_schema(_config)
    return {"applied": len(applied)}


# --- Request log ---


@mcp.tool()
async def request_log_summary() -> dict:
    """Return summary stats of recent MCP tool calls (latency, error rate, call counts)."""
    return _request_logger.summary()


# --- Startup health check ---


async def _verify_backend() -> None:
    """Verify the graph backend initializes and can run a basic query.

    Logs a clear error if the database is unreachable so the user knows
    writes will fail silently.
    """
    import logging as _logging

    _log = _logging.getLogger("wheeler.health")
    try:
        backend = await graph_tools._get_backend(_config)
        counts = await backend.count_all()
        total = sum(counts.values())
        _log.info(
            "Graph backend OK (%s, %d nodes)",
            _config.graph.backend,
            total,
        )
    except Exception as exc:
        _log.error(
            "GRAPH BACKEND FAILED (%s): %s — "
            "graph operations will not work until this is fixed. "
            "Ensure Neo4j is running (Desktop or Docker).",
            _config.graph.backend,
            exc,
        )


# --- Entry point ---


def main():
    import asyncio

    asyncio.run(_verify_backend())
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
