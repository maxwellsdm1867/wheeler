"""Wheeler MCP Server — exposes knowledge graph, citations, workspace, and provenance.

DEPRECATED: This monolithic server is kept for backward compatibility.
Prefer the split servers: mcp_core, mcp_query, mcp_mutations, mcp_ops.
See .plans/MCP-SERVER-SPLIT.md for rationale.

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
from typing import Literal

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
    instructions="Wheeler research knowledge graph tools. Use only for research graph operations (querying nodes, adding findings/hypotheses/papers, citation validation, research asset discovery). Not for general file browsing, document editing, or non-research tasks.",
)


def _logged(func):
    """Wrap an MCP tool handler with request logging."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        trace_id = f"t-{secrets.token_hex(6)}"
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
                trace_id=trace_id,
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
                trace_id=trace_id,
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


# --- Node read (filesystem) ---


@mcp.tool()
@_logged
async def show_node(node_id: str) -> dict:
    """Read the full content of a Wheeler knowledge graph node from its JSON file.

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


# --- Entity resolution ---


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


@mcp.tool()
@_logged
async def execute_merge(keep_id: str, merge_from_id: str) -> dict:
    """Merge two duplicate nodes: redirect relationships, merge metadata, delete duplicate.

    Two-phase commit: prepares merged state in temp files, then commits
    graph changes and atomic file renames. If the graph operation fails,
    temp files are discarded and no changes are made.

    Always call propose_merge first to preview what will happen.
    """
    from wheeler.merge import execute_merge as _execute
    return await _execute(_config, keep_id, merge_from_id)


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
    """Add a Finding to the Wheeler knowledge graph. Returns the new node ID.

    A finding can be a number, a figure, a table, or any result worth
    recording.

    Field constraints (enforced, invalid values are rejected):
      confidence: float 0.0-1.0 (required). 0.3 = exploratory, 0.7 = solid.
      description: non-empty string (required).
      path: absolute file path if provided. Verify the file exists first.
      artifact_type: figure, number, table, plot, text, or code.
      tier: 'generated' (default) or 'reference'.

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
    """Add a Hypothesis to the Wheeler knowledge graph. Returns the new node ID.

    Field constraints (enforced):
      statement: non-empty string (required).
      status: 'open' (default), 'supported', or 'rejected'. Other values rejected.
      tier: 'generated' (default) or 'reference'.

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
    """Add an OpenQuestion to the Wheeler knowledge graph. Returns the new node ID.

    Field constraints (enforced):
      question: non-empty string (required).
      priority: integer 1-10, where 10 is highest (default 5). Out-of-range rejected.

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
async def ensure_artifact(
    path: str,
    description: str = "",
    artifact_type: str = "",
    language: str = "",
    data_type: str = "",
    title: str = "",
    confidence: float = 0.0,
    status: str = "",
) -> dict:
    """Register a file in the Wheeler knowledge graph, or update its hash if already registered.

    PREFERRED way to track any artifact (script, dataset, figure, plan, document).
    Call this after writing, reading, or modifying a file. Safe to call
    repeatedly: it is idempotent on unchanged files.

    Auto-detects node type from extension:
      .py .m .r .jl .sh         -> Script
      .mat .h5 .hdf5 .csv .npy  -> Dataset
      .md .tex .pdf             -> Document  (or Plan if path is under .plans/)
      .png .jpg .svg .tif       -> Finding (artifact_type=figure)
      Unknown extension          -> Document

    Returns: {node_id, label, action, path, hash, ...}
      action = "created"   -> new node created, use node_id for link_nodes
      action = "unchanged" -> file hash matches stored hash, no write
      action = "updated"   -> file changed on disk; hash updated and
                              downstream dependents marked stale.
                              Includes previous_hash and stale_downstream count.

    Use instead of add_script, add_dataset, add_document, add_plan, or the
    three-step "hash_file + query_* + add_*" pattern.
    """
    ea_args: dict = {
        "path": path,
        "session_id": _SESSION_ID,
    }
    if description:
        ea_args["description"] = description
    if artifact_type:
        ea_args["artifact_type"] = artifact_type
    if language:
        ea_args["language"] = language
    if data_type:
        ea_args["data_type"] = data_type
    if title:
        ea_args["title"] = title
    if confidence != 0.0:
        ea_args["confidence"] = confidence
    if status:
        ea_args["status"] = status

    result = await graph_tools.execute_tool("ensure_artifact", ea_args, _config)
    return json.loads(result)


@mcp.tool()
@_logged
async def link_nodes(
    source_id: str,
    target_id: str,
    relationship: Literal[
        "USED", "WAS_GENERATED_BY", "WAS_DERIVED_FROM", "WAS_INFORMED_BY",
        "WAS_ATTRIBUTED_TO", "WAS_ASSOCIATED_WITH",
        "SUPPORTS", "CONTRADICTS", "CITES", "APPEARS_IN",
        "RELEVANT_TO", "AROSE_FROM", "DEPENDS_ON", "CONTAINS",
    ],
) -> dict:
    """Create a relationship between two Wheeler knowledge graph nodes.

    Args:
      source_id: ID of the source node (e.g. 'F-3a2b')
      target_id: ID of the target node (e.g. 'D-1c4f')
      relationship: the relationship type (NOT 'relation'). See valid types below.

    Valid relationship types (exactly one of):
      PROV: USED, WAS_GENERATED_BY, WAS_DERIVED_FROM, WAS_INFORMED_BY,
            WAS_ATTRIBUTED_TO, WAS_ASSOCIATED_WITH
      Semantic: SUPPORTS, CONTRADICTS, CITES, APPEARS_IN, RELEVANT_TO,
                AROSE_FROM, DEPENDS_ON, CONTAINS

    Common aliases are auto-mapped (e.g. USES -> USED, DERIVED_FROM ->
    WAS_DERIVED_FROM). Any other value returns an error with the full
    list of allowed types.
    """
    result = await graph_tools.execute_tool(
        "link_nodes",
        {"source_id": source_id, "target_id": target_id, "relationship": relationship,
         "session_id": _SESSION_ID},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def unlink_nodes(
    source_id: str,
    target_id: str,
    relationship: Literal[
        "USED", "WAS_GENERATED_BY", "WAS_DERIVED_FROM", "WAS_INFORMED_BY",
        "WAS_ATTRIBUTED_TO", "WAS_ASSOCIATED_WITH",
        "SUPPORTS", "CONTRADICTS", "CITES", "APPEARS_IN",
        "RELEVANT_TO", "AROSE_FROM", "DEPENDS_ON", "CONTAINS",
    ],
) -> dict:
    """Remove a specific relationship between two Wheeler knowledge graph nodes. Use for correcting
    wrong links created during ingest.

    Args:
      source_id: ID of the source node (e.g. 'F-3a2b')
      target_id: ID of the target node (e.g. 'D-1c4f')
      relationship: the relationship type (NOT 'relation'). See valid types below.

    This is a destructive operation: the relationship is permanently deleted.
    Both nodes remain in the graph. To re-render synthesis files for the
    affected nodes, both endpoints are automatically updated.

    Valid relationship types (same as link_nodes):
      PROV: USED, WAS_GENERATED_BY, WAS_DERIVED_FROM, WAS_INFORMED_BY,
            WAS_ATTRIBUTED_TO, WAS_ASSOCIATED_WITH
      Semantic: SUPPORTS, CONTRADICTS, CITES, APPEARS_IN, RELEVANT_TO,
                AROSE_FROM, DEPENDS_ON, CONTAINS

    Common aliases are auto-mapped (e.g. USES -> USED).
    """
    result = await graph_tools.execute_tool(
        "unlink_nodes",
        {"source_id": source_id, "target_id": target_id, "relationship": relationship,
         "session_id": _SESSION_ID},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def delete_node(node_id: str) -> dict:
    """Permanently delete a Wheeler knowledge graph node, its knowledge file, synthesis file, all
    relationships, and embedding. This is irreversible. Use for removing
    incorrect or duplicate research nodes.

    The node is identified by its ID prefix (e.g. F- for Finding, H- for
    Hypothesis). All relationships connected to the node are also removed
    (DETACH DELETE). The knowledge JSON file and synthesis markdown file
    are deleted from disk. The embedding is removed from the search index.
    """
    result = await graph_tools.execute_tool(
        "delete_node",
        {"node_id": node_id, "session_id": _SESSION_ID},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def add_dataset(path: str, type: str, description: str) -> dict:
    """Add a Dataset node to the Wheeler knowledge graph. Returns the new node ID. For find-or-create by path, prefer ensure_artifact.

    Field constraints (enforced):
      path: file path (required). File MUST exist on disk.
        Verify with ls or Read before calling. Relative paths are resolved to absolute.
      type: dataset format, e.g. 'mat', 'h5', 'csv' (required).
      description: what the dataset contains (required, non-empty).
    """
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
    """Add a Script node to the Wheeler knowledge graph to track a code file with provenance (legacy alias). For find-or-create by path, prefer ensure_artifact.

    Field constraints (enforced):
      script_path: absolute file path (required). File MUST exist on disk.
        Verify with ls or Read before calling.
      language: programming language, e.g. 'python', 'matlab' (required).

    If script_hash is empty, Wheeler will compute it from the file.
    Use this when registering scripts or during /wh:ingest.
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
    """Set context tier of a Wheeler knowledge graph node to 'reference' (established) or 'generated' (new work)."""
    result = await graph_tools.execute_tool(
        "set_tier", {"node_id": node_id, "tier": tier, "session_id": _SESSION_ID}, _config
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def update_node(
    node_id: str,
    description: str = "",
    confidence: float | None = None,
    statement: str = "",
    status: str = "",
    title: str = "",
    content: str = "",
    question: str = "",
    priority: int | None = None,
    path: str = "",
    tier: str = "",
) -> dict:
    """Update fields on an existing Wheeler knowledge graph node. Only non-empty fields are applied.

    Field constraints (enforced, same as creation):
      confidence: float 0.0-1.0
      priority: integer 1-10, where 10 is highest
      tier: 'generated' or 'reference'
      path: resolved to absolute if relative

    Returns the node_id, updated fields, and a changes dict showing old vs new values.
    Use for correcting descriptions, changing status, adjusting confidence,
    or updating any node field after creation.
    """
    update_args: dict = {"node_id": node_id, "session_id": _SESSION_ID}
    for field, val in [
        ("description", description), ("confidence", confidence),
        ("statement", statement), ("status", status), ("title", title),
        ("content", content), ("question", question), ("priority", priority),
        ("path", path), ("tier", tier),
    ]:
        if val is not None and val != "":
            update_args[field] = val

    result = await graph_tools.execute_tool("update_node", update_args, _config)
    return json.loads(result)


@mcp.tool()
@_logged
async def add_paper(title: str, authors: str = "", doi: str = "", year: int = 0) -> dict:
    """Add a Paper to the Wheeler knowledge graph for literature provenance. Returns the new node ID.

    Field constraints (enforced):
      title: non-empty string (required).
      year: integer publication year. 0 means unknown (triggers warning).
    """
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
    """Add a Document to the Wheeler knowledge graph. Returns the new node ID. For find-or-create by path, prefer ensure_artifact.

    Field constraints (enforced):
      title: non-empty string (required).
      path: absolute file path (required). Use the full path to the document.
      status: 'draft' (default), 'revision', or 'final'. Other values rejected.

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
    """Add a ResearchNote to the Wheeler knowledge graph to capture an insight or idea. Returns the new node ID.

    Field constraints (enforced):
      content: non-empty string (required). The note body, insight, or observation.
      title: optional short title (defaults to auto-generated from content).
      context: optional string describing where/why this note was captured.

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


@mcp.tool()
@_logged
async def add_plan(
    title: str,
    path: str = "",
    status: str = "draft",
    execution_kind: str = "",
    used_entities: str = "",
    execution_description: str = "",
) -> dict:
    """Add a Plan node to the Wheeler knowledge graph. Returns the new node ID.

    Field constraints (enforced):
      title: non-empty string (required).
      path: file path to the plan document (optional).
      status: 'draft' (default) or 'final'. Other values rejected.

    Provenance-completing: set execution_kind to auto-create an Execution
    and link provenance. Pass used_entities as comma-separated node IDs.
    """
    result = await graph_tools.execute_tool(
        "add_plan",
        {"title": title, "path": path, "status": status,
         "session_id": _SESSION_ID,
         "execution_kind": execution_kind,
         "used_entities": used_entities,
         "execution_description": execution_description},
        _config,
    )
    return json.loads(result)


@mcp.tool()
@_logged
async def add_execution(
    kind: str,
    description: str,
    agent_id: str = "wheeler",
    status: str = "completed",
    session_id: str = "",
    started_at: str = "",
    ended_at: str = "",
) -> dict:
    """Add an Execution node to the Wheeler knowledge graph to record a run of a script, pipeline, or research activity.

    Field constraints (enforced):
      kind: execution type, e.g. 'script_run', 'discuss', 'write', 'pipeline' (required).
      description: what the execution did (required).
      status: 'completed', 'failed', or 'running' (default 'completed').

    Use this to record provenance for research activities. Link inputs with
    USED and outputs with WAS_GENERATED_BY.
    """
    result = await graph_tools.execute_tool(
        "add_execution",
        {
            "kind": kind,
            "description": description,
            "agent_id": agent_id,
            "status": status,
            "session_id": session_id or _SESSION_ID,
            "started_at": started_at,
            "ended_at": ended_at,
        },
        _config,
    )
    return json.loads(result)


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
async def query_notes(keyword: str = "", limit: int = 10) -> dict:
    """Search ResearchNote nodes in the Wheeler knowledge graph."""
    result = await graph_tools.execute_tool(
        "query_notes", {"keyword": keyword, "limit": limit}, _config
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
    """Search across Wheeler knowledge graph nodes for research context retrieval.

    Combines semantic (embedding similarity), keyword (graph queries), and
    temporal (recency) channels via Reciprocal Rank Fusion for better recall
    than any single channel alone. Use for finding related research nodes
    when linking new entries or exploring existing knowledge.

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


# --- Citation validation ---


@mcp.tool()
@_logged
async def extract_citations(text: str) -> list[str]:
    """Extract all Wheeler knowledge graph node ID citations ([F-3a2b] format) from text using regex."""
    return citations.extract_citations(text)


@mcp.tool()
@_logged
async def validate_citations(text: str) -> dict:
    """Validate all Wheeler knowledge graph citations in text against Neo4j. Checks existence and provenance."""
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


# --- Retrieval quality ---


@mcp.tool()
@_logged
async def compute_retrieval_quality(
    output_text: str,
    retrieved_node_ids: str = "",
) -> dict:
    """Compute retrieval quality metrics for generated text.

    Measures how effectively the knowledge graph was used:
    - context_precision: fraction of retrieved nodes actually cited
    - coverage_gaps: terms in output not backed by any graph node

    Args:
        output_text: The generated text to evaluate
        retrieved_node_ids: Comma-separated node IDs that were retrieved as context
    """
    from wheeler.validation.ledger import compute_retrieval_metrics
    from wheeler.knowledge.store import list_nodes

    retrieved = (
        [r.strip() for r in retrieved_node_ids.split(",") if r.strip()]
        if retrieved_node_ids
        else []
    )

    # Build node text corpus from knowledge files
    knowledge_dir = Path(_config.knowledge_path)
    node_texts: dict[str, str] = {}
    try:
        from wheeler.models import title_for_node

        nodes = list_nodes(knowledge_dir)
        for node in nodes:
            node_texts[node.id] = title_for_node(node)
    except Exception:
        pass  # if knowledge dir doesn't exist, corpus is empty

    metrics = compute_retrieval_metrics(output_text, retrieved, node_texts)
    return metrics


# --- Contract validation ---


@mcp.tool()
@_logged
async def validate_task_contract(
    session_id: str,
    required_finding_count: int = 0,
    confidence_min: float = 0.0,
    required_hypothesis_count: int = 0,
    require_provenance: bool = True,
    must_reference: str = "",
) -> dict:
    """Validate task output against a contract.

    Check that a task session produced the expected graph nodes,
    provenance links, and references. Use during /wh:reconvene to
    verify independent tasks met their goals.

    Args:
        session_id: The session ID of the task to validate
        required_finding_count: Minimum Finding nodes expected (0 = skip check)
        confidence_min: Minimum confidence for findings (0.0 = skip check)
        required_hypothesis_count: Minimum Hypothesis nodes expected (0 = skip check)
        require_provenance: Check that findings have WAS_GENERATED_BY links
        must_reference: Comma-separated node IDs that must be referenced by task output
    """
    from wheeler.contracts import (
        TaskContract, NodeRequirement, LinkRequirement, validate_contract,
    )

    reqs: list[NodeRequirement] = []
    if required_finding_count > 0:
        reqs.append(NodeRequirement(
            type="Finding", min_count=required_finding_count,
            confidence_min=confidence_min,
        ))
    if required_hypothesis_count > 0:
        reqs.append(NodeRequirement(
            type="Hypothesis", min_count=required_hypothesis_count,
        ))

    links: list[LinkRequirement] = []
    if require_provenance and required_finding_count > 0:
        links.append(LinkRequirement(
            from_type="Finding",
            relationship="WAS_GENERATED_BY",
            to_type="Execution",
        ))

    refs = [r.strip() for r in must_reference.split(",") if r.strip()] if must_reference else []

    contract = TaskContract(
        task_id=f"validate-{session_id}",
        required_nodes=reqs,
        required_links=links,
        must_reference=refs,
    )

    result = await validate_contract(_config, contract, session_id)
    return {
        "passed": result.passed,
        "violations": result.violations,
        "checks_run": result.checks_run,
        "summary": result.summary,
    }


# --- Workspace ---


@mcp.tool()
@_logged
async def scan_workspace() -> dict:
    """Scan research workspace paths defined in wheeler.yaml to discover data files and scripts for knowledge graph indexing.

    Only use for research asset discovery when building or updating the Wheeler
    knowledge graph (e.g. during /wh:ingest), not for general file browsing or
    non-research tasks. For general file operations use Read/Glob tools instead.
    """
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
    """Find Wheeler knowledge graph Script nodes whose file has been modified since last recorded hash."""
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
    """Compute SHA-256 hash of a file for Wheeler research provenance tracking. Most callers should use ensure_artifact instead, which hashes + registers in one call."""
    sha = provenance.hash_file(path)
    return {"path": path, "sha256": sha}


@mcp.tool()
@_logged
async def scan_dependencies(script_path: str, link_to_graph: bool = False) -> dict:
    """Scan a Python script for imports and data file references for Wheeler research provenance.

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
                        "relationship": "DEPENDS_ON",
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
    """Run a read-only Cypher query against the Wheeler knowledge graph database.

    Use for ad-hoc research graph exploration: relationship traversal, path queries,
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
async def graph_consistency_check(repair: bool = False) -> dict:
    """Check consistency across graph, JSON, and synthesis layers.

    Compares node inventories in Neo4j, knowledge/*.json, and synthesis/*.md.
    Reports nodes that exist in one layer but not others.

    Set repair=True to fix detected drift:
    - Regenerate missing synthesis files from JSON
    - Delete orphaned synthesis files with no backing JSON
    - Warn about graph/JSON mismatches (manual intervention needed)

    Use during /wh:dream consolidation or /wh:close end-of-session sweep.
    """
    from dataclasses import asdict
    from wheeler.consistency import check_consistency, repair_consistency

    report = await check_consistency(_config)
    result = asdict(report)

    if repair:
        repair_log = await repair_consistency(_config, report, dry_run=False)
        result["repairs"] = repair_log
    else:
        result["repairs"] = await repair_consistency(_config, report, dry_run=True)

    return result


@mcp.tool()
@_logged
async def detect_communities(min_size: int = 3) -> dict:
    """Detect research theme clusters in the Wheeler knowledge graph.

    Uses connected components to find groups of related nodes.
    Returns communities with member details, label distributions,
    and summary statistics.

    Use during /wh:dream consolidation to surface emergent research themes.
    Communities with 3+ nodes are returned by default.

    Args:
        min_size: Minimum community size to include (default 3)
    """
    from wheeler.communities import find_communities
    return await find_communities(_config, min_size=min_size)


@mcp.tool()
@_logged
async def init_schema() -> dict:
    """Apply Wheeler knowledge graph constraints and indexes to Neo4j. Returns count of applied statements."""
    applied = await schema.init_schema(_config)
    return {"applied": len(applied)}


# --- Request log ---


@mcp.tool()
async def request_log_summary() -> dict:
    """Return summary stats of recent Wheeler MCP tool calls (latency, error rate, call counts)."""
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

    from wheeler.graph.driver import invalidate_async_driver

    asyncio.run(_verify_backend())
    invalidate_async_driver()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
