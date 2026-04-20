"""Wheeler Mutations MCP Server: all graph write operations.

12 tools for creating, modifying, and deleting graph nodes and relationships.
Run: python -m wheeler.mcp_mutations
"""

from __future__ import annotations

import json
from typing import Literal

from fastmcp import FastMCP

from wheeler.graph import provenance
from wheeler.tools import graph_tools
from wheeler.mcp_shared import (
    _config,
    _SESSION_ID,
    _logged,
    _check_similar_nodes,
    _verify_backend,
)

mcp = FastMCP(
    "wheeler_mutations",
    instructions="Create, update, link, unlink, and delete graph nodes: add_finding, add_hypothesis, add_question, add_dataset, add_paper, add_document, add_note, add_plan, add_execution, ensure_artifact, link_nodes, unlink_nodes, update_node, set_tier, delete_node. Prefer ensure_artifact for registering any file artifact (script/dataset/figure/plan/document); it hashes and creates-or-updates in one call.",
)


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
      status: 'draft' (default), 'approved', 'in-progress', or 'completed'.

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

    Label-collision: if a node already exists at this path under a different
    label, returns {"error": "label_mismatch", "node_id", "existing_label"}
    without mutating. Use update_node or delete_node to reconcile.

    Field constraints (enforced):
      path: file path (required). File MUST exist on disk. Relative paths
        are resolved to absolute.
      artifact_type: override auto-detection. One of 'script', 'dataset',
        'document', 'plan', 'finding'.
      description / title: optional. If omitted, defaults to filename.
      language: for Script only. Defaults to extension-derived value.
      data_type: for Dataset only. Defaults to extension.
      confidence: for Finding only. 0.0-1.0, default 0.5.
      status: for Plan/Document only. 'draft' (default) or 'final'.

    Use instead of add_script, add_dataset, add_document, add_plan, or the
    three-step "hash_file + query_* + add_*" pattern. Those remain available
    for cases that need explicit create-only semantics.

    For find-or-create by path, prefer ensure_artifact.
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
async def execute_merge(keep_id: str, merge_from_id: str) -> dict:
    """Merge two duplicate nodes: redirect relationships, merge metadata, delete duplicate.

    Two-phase commit: prepares merged state in temp files, then commits
    graph changes and atomic file renames. If the graph operation fails,
    temp files are discarded and no changes are made.

    Always call propose_merge first to preview what will happen.
    """
    from wheeler.merge import execute_merge as _execute
    return await _execute(_config, keep_id, merge_from_id)


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


# --- Entry point ---


def main():
    import asyncio

    from wheeler.graph.driver import invalidate_async_driver

    asyncio.run(_verify_backend())
    invalidate_async_driver()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
