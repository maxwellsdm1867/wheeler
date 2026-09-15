"""Wheeler Mutations MCP Server: all graph write operations.

19 tools for creating, modifying, and deleting graph nodes and relationships.
Run: python -m wheeler.mcp_mutations

register_batch is the bulk path: a whole execution's provenance (nodes, files,
edges) in one call. It was chosen over split batch tools and a manifest CLI by
measurement (evals/batch_registration/REPORT.md, issues #116 and #117).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

from wheeler.graph import provenance
from wheeler.tools import graph_tools
from wheeler.mcp_shared import (
    _config,
    _SESSION_ID,
    _logged,
    _check_similar_nodes,
    _compact_write_result,
    _verify_backend,
)

mcp = FastMCP(
    "wheeler_mutations",
    instructions="Create, update, link, unlink, and delete graph nodes: add_finding, add_hypothesis, add_question, add_dataset, add_paper, add_document, add_note, add_plan, add_execution, ensure_artifact, link_nodes, unlink_nodes, update_node, set_tier, delete_node, register_batch. Prefer ensure_artifact for registering any file artifact (script/dataset/figure/plan/document); it hashes and creates-or-updates in one call. To register a whole execution (its Execution, findings, files and all their edges) use register_batch: one call instead of one per item.",
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
    return _compact_write_result(parsed)


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
    return _compact_write_result(parsed)


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
    return _compact_write_result(parsed)


@mcp.tool()
@_logged
async def add_dataset(
    path: str,
    type: str,
    description: str,
    schema: str = "",
    source: str = "",
    parent_dataset: str = "",
    size: str = "",
    format_details: str = "",
) -> dict:
    """Add a Dataset node to the Wheeler knowledge graph. Returns the new node ID. For find-or-create by path, prefer ensure_artifact.

    Field constraints (enforced):
      path: file path (required). File MUST exist on disk.
        Verify with ls or Read before calling. Relative paths are resolved to absolute.
      type: dataset format, e.g. 'mat', 'h5', 'csv' (required).
      description: what the dataset contains (required, non-empty).

    Optional structured metadata (issue #17):
      schema: structured schema description, e.g. column listing or HDF5 group layout.
      source: where the data came from (instrument, pipeline, collaborator).
      parent_dataset: ID of a Dataset this was derived from. When set to a
        valid 'D-xxxxxxxx' ID, automatically creates a WAS_DERIVED_FROM
        edge from the new dataset to the parent. Invalid or missing parents
        produce a warning in the result instead of failing the call.
      size: file size or row count (free-form string, e.g. '124MB' or '52000 rows').
      format_details: encoding, compression, version (e.g. 'utf-8, gzip-9, HDF5 1.10').
    """
    result = await graph_tools.execute_tool(
        "add_dataset",
        {
            "path": path,
            "type": type,
            "description": description,
            "schema": schema,
            "source": source,
            "parent_dataset": parent_dataset,
            "size": size,
            "format_details": format_details,
            "session_id": _SESSION_ID,
        },
        _config,
    )
    return _compact_write_result(json.loads(result))


@mcp.tool()
@_logged
async def add_paper(
    title: str,
    authors: str = "",
    doi: str = "",
    year: int = 0,
    corpus_id: str = "",
) -> dict:
    """Add a Paper to the Wheeler knowledge graph for literature provenance. Returns the new node ID.

    Field constraints (enforced):
      title: non-empty string (required).
      year: integer publication year. 0 means unknown (triggers warning).
      corpus_id: Semantic Scholar / Asta corpus id. Indexed, and the dedupe key
        the Asta adapters match on. Supply it when known: a Paper added without
        one is invisible to corpus_id dedupe and is recoverable only through the
        normalized-title fallback.
    """
    result = await graph_tools.execute_tool(
        "add_paper",
        {"title": title, "authors": authors, "doi": doi, "year": year,
         "corpus_id": corpus_id, "session_id": _SESSION_ID},
        _config,
    )
    return _compact_write_result(json.loads(result))


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
    return _compact_write_result(json.loads(result))


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
    return _compact_write_result(json.loads(result))


async def _add_script_impl(
    script_path: str,
    language: str,
    script_hash: str = "",
    language_version: str = "",
) -> dict:
    """Shared implementation for add_script and add_analysis."""
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
    return _compact_write_result(json.loads(result))


@mcp.tool()
@_logged
async def add_script(
    script_path: str,
    language: str,
    script_hash: str = "",
    language_version: str = "",
) -> dict:
    """Register a code/script file in the Wheeler knowledge graph. Creates an S- (Script) node with language and hash metadata. For find-or-create by path, prefer ensure_artifact.

    Field constraints (enforced):
      script_path: absolute file path (required). File MUST exist on disk.
        Verify with ls or Read before calling.
      language: programming language, e.g. 'python', 'matlab', 'r', 'julia', 'bash' (required).

    If script_hash is empty, Wheeler will compute it from the file.
    Use this when registering scripts or during /wh:ingest.
    """
    return await _add_script_impl(script_path, language, script_hash, language_version)


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
    """Register a code/script file (backward-compatible alias for add_script). Creates an S- (Script) node. Prefer add_script or ensure_artifact for new code.

    Field constraints (enforced):
      script_path: absolute file path (required). File MUST exist on disk.
      language: programming language, e.g. 'python', 'matlab' (required).
    """
    return await _add_script_impl(script_path, language, script_hash, language_version)


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
    return _compact_write_result(json.loads(result))


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
    return _compact_write_result(json.loads(result))


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
    execution_kind: str = "",
    used_entities: str = "",
    execution_description: str = "",
    verbose: bool = False,
) -> dict:
    """Register a file in the Wheeler knowledge graph, or update its hash if already registered.

    PREFERRED way to track any artifact (script, dataset, figure, plan,
    document). Idempotent on unchanged files. To register many files and their
    edges at once use register_batch instead of calling this in a loop.

    Type is auto-detected from the extension (.py/.m/.r/.jl/.sh Script;
    .mat/.h5/.csv/.npy/.parquet/.db Dataset; .md/.tex/.pdf Document, or Plan
    under .plans/; .png/.jpg/.svg/.tif Finding figure; else Document) or
    forced with artifact_type (script|dataset|document|plan|finding).

    Returns {node_id, label, action} where action is created, unchanged, or
    updated (file changed on disk: hash updated, downstream marked stale,
    stale_downstream reports how many). {"error": "label_mismatch", ...} when
    a node at this path has a different label; reconcile with update_node or
    delete_node. Pass verbose=true to also get path, stored_path and hashes.

    Fields: path (required, must exist; relative resolves to absolute),
    description (defaults to filename), title (defaults to stem), language
    (Script), data_type (Dataset), confidence 0.0-1.0 (Finding, default 0.5),
    status draft|final (Plan/Document). Provenance-completing: execution_kind
    (e.g. "script", "write") creates an Execution and links the node
    WAS_GENERATED_BY it; used_entities "F-abc,D-def" adds USED edges from that
    Execution, so the artifact is not born an orphan.
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
    if execution_kind:
        ea_args["execution_kind"] = execution_kind
    if used_entities:
        ea_args["used_entities"] = used_entities
    if execution_description:
        ea_args["execution_description"] = execution_description

    result = await graph_tools.execute_tool("ensure_artifact", ea_args, _config)
    parsed = json.loads(result)
    return parsed if verbose else _diet_ensure(parsed)


# Keys ensure_artifact echoes back that the caller already knows (it passed the
# path) or never acts on (hashes). Together they were 89 percent of the bytes of
# 524 real results; see docs/mcp-token-audit.md.
_ENSURE_ECHO_KEYS = ("path", "stored_path", "hash", "previous_hash", "path_upgraded")


def _diet_ensure(parsed: dict) -> dict:
    if "error" in parsed:
        return parsed
    out = {k: v for k, v in parsed.items() if k not in _ENSURE_ECHO_KEYS}
    if not out.get("stale_downstream"):
        out.pop("stale_downstream", None)
    return _compact_write_result(out)


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
    description: str | None = None,
    confidence: float | None = None,
    statement: str | None = None,
    status: str | None = None,
    title: str | None = None,
    content: str | None = None,
    question: str | None = None,
    priority: int | None = None,
    path: str | None = None,
    tier: str | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
    allow_provenance: bool = False,
    verbose: bool = False,
) -> dict:
    """Update fields on an existing Wheeler knowledge graph node. Omitted fields are left unchanged.

    Omitting an argument (or passing null) leaves the field alone. An empty
    string is a real value that CLEARS the field (path="" resets a dangling
    path). Fields are validated against the node type's schema; an unknown
    field is rejected by name, never silently written elsewhere.

    Constraints: confidence 0.0-1.0; priority 1-10 (10 highest); tier
    generated|reference; path resolved to absolute. Execution timestamps
    (started_at, ended_at) are immutable unless allow_provenance=true.

    Returns {node_id, label, status, updated_fields}. The old and new values
    are recorded in the node's change_log; pass verbose=true to get them back
    in the result as well.
    """
    update_args: dict = {"node_id": node_id, "session_id": _SESSION_ID}
    for field, val in [
        ("description", description), ("confidence", confidence),
        ("statement", statement), ("status", status), ("title", title),
        ("content", content), ("question", question), ("priority", priority),
        ("path", path), ("tier", tier),
        ("started_at", started_at), ("ended_at", ended_at),
    ]:
        if val is not None:
            update_args[field] = val
    if allow_provenance:
        update_args["allow_provenance"] = True

    result = await graph_tools.execute_tool("update_node", update_args, _config)
    parsed = json.loads(result)
    if not verbose:
        # 96 percent of a real update_node result was this echo of text the
        # caller had just written (docs/mcp-token-audit.md).
        parsed.pop("changes", None)
    return parsed


# --- Bulk registration ---


@mcp.tool()
@_logged
async def register_batch(
    nodes: list[dict] | None = None,
    artifacts: list[dict] | None = None,
    edges: list | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Register a whole execution's provenance in ONE call: nodes, files and edges.

    Use this instead of a run of ensure_artifact / add_* / link_nodes calls.
    Items may carry an alias ("@fig1") and edges may reference aliases or
    existing node ids, so you never have to wait for an id to come back.

    Args:
      nodes: non-file nodes. Each {"alias": "@x", "type": one of
        execution|finding|hypothesis|question|note, ...fields of the matching
        add_* tool}. Example execution: {"alias": "@exec", "type": "execution",
        "kind": "script_run", "description": "..."}. Example finding:
        {"alias": "@f1", "type": "finding", "description": "...", "confidence": 0.7}.
      artifacts: files on disk, one {"alias": "@fig1", "path": "...", "title": "...",
        "description": "...", "artifact_type": optional} each. Same fields as
        ensure_artifact. Relative paths resolve against the project root.
      edges: [{"source": "@fig1", "relationship": "WAS_GENERATED_BY", "target": "@exec"}]
        or the short form ["@fig1", "WAS_GENERATED_BY", "@exec"]. Endpoints are
        aliases defined above or literal node ids ("Q-1a2b3c4d").
      dry_run: validate only (structure, files exist, relationship names,
        literal ids exist in the graph). Nothing is written.
      verbose: include a row for every successful item too. Default returns
        counts, the alias -> id map, node_ids per section in input order, and
        only the rows that failed.

    One bad item never aborts the rest; the top-level status is ok, partial or
    failed, and "ids" maps every alias to its node id.
    """
    from wheeler.tools.graph_tools.batch import register_batch as _register

    manifest = {"nodes": nodes or [], "artifacts": artifacts or [], "edges": edges or []}
    result = await _register(
        manifest, _config, session_id=_SESSION_ID, dry_run=dry_run,
        base_dir=Path(_config.project_root),
    )
    return result if (verbose or dry_run) else _compact(result)


_OK_STATUSES = {"created", "unchanged", "updated", "linked"}


def _compact(result: dict) -> dict:
    """Drop the rows that succeeded; keep ids (in input order) and failures.

    ``ids`` covers aliased items only, so ``node_ids`` lists every created or
    matched node id per section in input order (None where the item failed).
    Without it a caller registering artifacts without aliases would have no way
    to learn their ids short of a second call.
    """
    out = {k: v for k, v in result.items() if k not in ("nodes", "artifacts", "edges")}
    if "nodes" in result or "artifacts" in result:
        out["node_ids"] = {
            section: [row.get("node_id") for row in result.get(section, [])]
            for section in ("nodes", "artifacts")
            if result.get(section)
        }
        # Only when something is not at version 1, which is the case a caller
        # has to act on (an artifact that already existed and was updated).
        moved = {
            section: [row.get("content_version") for row in result.get(section, [])]
            for section in ("nodes", "artifacts")
            if any((row.get("content_version") or 1) != 1 for row in result.get(section, []))
        }
        if moved:
            out["content_versions"] = moved
    problems = [
        {"section": section, **row}
        for section in ("nodes", "artifacts", "edges")
        for row in result.get(section, [])
        if row.get("status") not in _OK_STATUSES
    ]
    if problems:
        out["problems"] = problems
    return out


# --- Entry point ---


def main():
    import asyncio

    from wheeler.graph.driver import invalidate_async_driver

    asyncio.run(_verify_backend())
    invalidate_async_driver()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
