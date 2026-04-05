"""Graph tools package: mutations and queries for the Wheeler knowledge graph.

Public API (backward-compatible with the old graph_tools.py module):
  - TOOL_DEFINITIONS: list of tool specs for CLI and MCP registration
  - execute_tool(name, args, config): dispatch a tool by name
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from wheeler.config import WheelerConfig
from wheeler.graph.schema import ALLOWED_RELATIONSHIPS

from . import mutations, queries
from ._common import _now

logger = logging.getLogger(__name__)

# Tools that create graph nodes and should be dual-written to knowledge/ files
_MUTATION_TOOLS = frozenset({
    "add_finding",
    "add_hypothesis",
    "add_question",
    "add_dataset",
    "add_paper",
    "add_document",
    "add_note",
    "add_script",
    "add_execution",
    "add_ledger",
})

# --- Tool registry: maps tool names to handler functions ---

_TOOL_REGISTRY: dict[str, object] = {
    # Mutations
    "add_finding": mutations.add_finding,
    "add_hypothesis": mutations.add_hypothesis,
    "add_question": mutations.add_question,
    "add_dataset": mutations.add_dataset,
    "add_paper": mutations.add_paper,
    "add_document": mutations.add_document,
    "add_note": mutations.add_note,
    "add_script": mutations.add_script,
    "add_execution": mutations.add_execution,
    "add_ledger": mutations.add_ledger,
    "link_nodes": mutations.link_nodes,
    "set_tier": mutations.set_tier,
    # Queries
    "query_findings": queries.query_findings,
    "query_open_questions": queries.query_open_questions,
    "query_hypotheses": queries.query_hypotheses,
    "query_datasets": queries.query_datasets,
    "query_papers": queries.query_papers,
    "query_documents": queries.query_documents,
    "query_notes": queries.query_notes,
    "query_scripts": queries.query_scripts,
    "query_executions": queries.query_executions,
    "graph_gaps": queries.graph_gaps,
}


# --- Tool definitions (JSON schema for CLI/MCP) ---

TOOL_DEFINITIONS = [
    {
        "name": "add_finding",
        "description": (
            "Add a Finding to the knowledge graph. Use when an analysis "
            "produces a result worth recording. Returns the new node ID."
        ),
        "parameters": {
            "description": {"type": "string", "description": "What was found"},
            "confidence": {"type": "number", "description": "Confidence 0.0-1.0"},
        },
        "required": ["description", "confidence"],
    },
    {
        "name": "add_hypothesis",
        "description": (
            "Add a Hypothesis to the knowledge graph. Use when proposing "
            "an explanation that needs testing. Returns the new node ID."
        ),
        "parameters": {
            "statement": {"type": "string", "description": "The hypothesis statement"},
            "status": {"type": "string", "description": "open, supported, or rejected", "default": "open"},
        },
        "required": ["statement"],
    },
    {
        "name": "add_question",
        "description": (
            "Add an OpenQuestion to the knowledge graph. Use when identifying "
            "a gap in knowledge. Returns the new node ID."
        ),
        "parameters": {
            "question": {"type": "string", "description": "The open question"},
            "priority": {"type": "integer", "description": "Priority 1-10 (10=highest)", "default": 5},
        },
        "required": ["question"],
    },
    {
        "name": "link_nodes",
        "description": (
            "Create a relationship between two graph nodes. "
            f"Allowed types: {', '.join(ALLOWED_RELATIONSHIPS)}"
        ),
        "parameters": {
            "source_id": {"type": "string", "description": "Source node ID (e.g., F-3a2b)"},
            "target_id": {"type": "string", "description": "Target node ID"},
            "relationship": {"type": "string", "description": f"One of: {', '.join(ALLOWED_RELATIONSHIPS)}"},
        },
        "required": ["source_id", "target_id", "relationship"],
    },
    {
        "name": "query_findings",
        "description": "Search findings in the knowledge graph. Returns recent findings optionally filtered by keyword.",
        "parameters": {
            "keyword": {"type": "string", "description": "Optional keyword to filter by", "default": ""},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "query_open_questions",
        "description": "List open questions from the knowledge graph, sorted by priority.",
        "parameters": {
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "query_hypotheses",
        "description": "List hypotheses, optionally filtered by status.",
        "parameters": {
            "status": {"type": "string", "description": "Filter: open, supported, rejected, or all", "default": "all"},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "graph_gaps",
        "description": (
            "Find gaps in the knowledge graph: open questions without linked "
            "executions, hypotheses without supporting findings, idle executions. "
            "Use in planning mode to propose next investigations."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "add_dataset",
        "description": (
            "Add a Dataset node to the knowledge graph. Use when registering "
            "a data file for provenance tracking. Returns the new node ID."
        ),
        "parameters": {
            "path": {"type": "string", "description": "File path to the dataset"},
            "type": {"type": "string", "description": "Dataset type (e.g., mat, h5, csv)"},
            "description": {"type": "string", "description": "What the dataset contains"},
        },
        "required": ["path", "type", "description"],
    },
    {
        "name": "query_datasets",
        "description": "Search Dataset nodes in the knowledge graph.",
        "parameters": {
            "keyword": {"type": "string", "description": "Optional keyword to filter by", "default": ""},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "add_paper",
        "description": (
            "Add a Paper to the knowledge graph. Use when registering "
            "a literature reference for provenance tracking. Returns the new node ID."
        ),
        "parameters": {
            "title": {"type": "string", "description": "Paper title"},
            "authors": {"type": "string", "description": "Author names (comma-separated)", "default": ""},
            "doi": {"type": "string", "description": "DOI if available", "default": ""},
            "year": {"type": "integer", "description": "Publication year", "default": 0},
        },
        "required": ["title"],
    },
    {
        "name": "query_papers",
        "description": "Search Paper nodes in the knowledge graph by title or authors.",
        "parameters": {
            "keyword": {"type": "string", "description": "Optional keyword to filter by", "default": ""},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "add_note",
        "description": (
            "Add a ResearchNote to the knowledge graph. Use when the scientist "
            "shares an insight, observation, or idea worth preserving. Returns the new node ID."
        ),
        "parameters": {
            "title": {"type": "string", "description": "Short title for the note", "default": ""},
            "content": {"type": "string", "description": "The note content"},
            "context": {"type": "string", "description": "What prompted this note (optional)", "default": ""},
        },
        "required": ["content"],
    },
    {
        "name": "add_document",
        "description": (
            "Add a Document to the knowledge graph. Use when /wh:write produces "
            "a draft to track which findings and papers it cites. Returns the new node ID."
        ),
        "parameters": {
            "title": {"type": "string", "description": "Document title (e.g., 'Results: Spike Generation')"},
            "path": {"type": "string", "description": "File path to the document"},
            "section": {"type": "string", "description": "Section type: results, methods, discussion, abstract, or full", "default": ""},
            "status": {"type": "string", "description": "Document status: draft, revision, or final", "default": "draft"},
        },
        "required": ["title", "path"],
    },
    {
        "name": "set_tier",
        "description": (
            "Set the context tier of a graph node to 'reference' or 'generated'. "
            "Use 'reference' for established knowledge (verified findings, published papers, "
            "confirmed analyses). Use 'generated' for new/in-progress work. "
            "Downstream agents use this to distinguish what's established from what's new."
        ),
        "parameters": {
            "node_id": {"type": "string", "description": "Node ID (e.g., F-3a2b)"},
            "tier": {"type": "string", "description": "reference or generated"},
        },
        "required": ["node_id", "tier"],
    },
    {
        "name": "query_notes",
        "description": "Search ResearchNote nodes in the knowledge graph by keyword.",
        "parameters": {
            "keyword": {"type": "string", "description": "Optional keyword to filter by", "default": ""},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "query_documents",
        "description": "Search Document nodes in the knowledge graph.",
        "parameters": {
            "keyword": {"type": "string", "description": "Optional keyword to filter by", "default": ""},
            "status": {"type": "string", "description": "Filter by status (draft, revision, final), or empty for all", "default": ""},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "add_script",
        "description": (
            "Add a Script node to the knowledge graph. Use when registering "
            "a code file for provenance tracking. Returns the new node ID."
        ),
        "parameters": {
            "path": {"type": "string", "description": "File path to the script"},
            "language": {"type": "string", "description": "Programming language (e.g., python, matlab)"},
            "hash": {"type": "string", "description": "Content hash of the script file", "default": ""},
            "version": {"type": "string", "description": "Version tag or commit hash", "default": ""},
        },
        "required": ["path", "language"],
    },
    {
        "name": "add_execution",
        "description": (
            "Add an Execution node to the knowledge graph. Use when recording "
            "a run of a script, pipeline, or agent task. Returns the new node ID."
        ),
        "parameters": {
            "kind": {"type": "string", "description": "Execution type (e.g., script_run, pipeline, agent_task)"},
            "description": {"type": "string", "description": "What the execution did"},
            "agent_id": {"type": "string", "description": "Agent or user who ran it", "default": "wheeler"},
            "status": {"type": "string", "description": "completed, failed, or running", "default": "completed"},
            "session_id": {"type": "string", "description": "Session or job ID", "default": ""},
            "started_at": {"type": "string", "description": "ISO timestamp when execution started", "default": ""},
            "ended_at": {"type": "string", "description": "ISO timestamp when execution ended", "default": ""},
        },
        "required": ["kind", "description"],
    },
    {
        "name": "query_scripts",
        "description": "Search Script nodes in the knowledge graph by path or language.",
        "parameters": {
            "keyword": {"type": "string", "description": "Optional keyword to filter by", "default": ""},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "query_executions",
        "description": "Search Execution nodes in the knowledge graph by kind or description.",
        "parameters": {
            "keyword": {"type": "string", "description": "Optional keyword to filter by", "default": ""},
            "kind": {"type": "string", "description": "Filter by execution kind", "default": ""},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": [],
    },
    {
        "name": "search_findings",
        "description": (
            "Semantic search across knowledge graph nodes by meaning. "
            "Finds conceptually related results even with different wording."
        ),
        "parameters": {
            "query": {"type": "string", "description": "Natural language search query"},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            "label": {"type": "string", "description": "Filter by node type (Finding, Hypothesis, etc.)", "default": ""},
        },
        "required": ["query"],
    },
    {
        "name": "index_node",
        "description": (
            "Add or update a node's semantic embedding for search. "
            "Call after creating or updating a node."
        ),
        "parameters": {
            "node_id": {"type": "string", "description": "Node ID (e.g., F-3a2b)"},
            "label": {"type": "string", "description": "Node type (Finding, Hypothesis, etc.)"},
            "text": {"type": "string", "description": "Text content to embed"},
        },
        "required": ["node_id", "label", "text"],
    },
]


# --- Dual-write helpers ---


def _write_knowledge_file(
    tool_name: str, args: dict, result_str: str, config: WheelerConfig
) -> None:
    """Best-effort dual-write: persist a new graph node as a JSON file.

    Uses the label from the result to look up the Pydantic model class,
    then builds it from the tool args. Any errors are logged but never
    propagated — the graph write has already succeeded.
    """
    try:
        parsed = json.loads(result_str)
        node_id: str | None = parsed.get("node_id")
        label: str | None = parsed.get("label")
        if not node_id or not label:
            logger.warning("_write_knowledge_file: missing node_id/label for %s", tool_name)
            return

        from wheeler.models import model_for_label
        from wheeler.knowledge.store import write_node

        now = _now()

        # Build kwargs from args, renaming graph field names to model field names
        kwargs: dict = {"id": node_id, "type": label, "created": now, "updated": now}

        # Tier: papers are always reference, everything else from args
        kwargs["tier"] = "reference" if label == "Paper" else args.get("tier", "generated")

        # Assign default stability based on node type and tier
        from wheeler.provenance import default_stability
        kwargs["stability"] = default_stability(label, kwargs["tier"])

        # Dataset has "type" in args but "data_type" in model
        if label == "Dataset" and "type" in args:
            kwargs["data_type"] = args["type"]

        # Ledger list fields are passed as JSON strings from ledger.py
        if label == "Ledger":
            for list_field in ("citations_found", "citations_valid", "citations_invalid",
                               "citations_missing_provenance", "citations_stale"):
                val = args.get(list_field)
                if isinstance(val, str):
                    kwargs[list_field] = json.loads(val)

        # Copy remaining args (skip internal keys)
        for key, val in args.items():
            if key.startswith("_") or key == "type" or key in kwargs:
                continue
            kwargs[key] = val

        model_cls = model_for_label(label)
        model = model_cls.model_validate(kwargs)

        write_node(Path(config.knowledge_path), model)
        logger.info("Dual-write: %s -> %s/%s.json", tool_name, config.knowledge_path, node_id)

        # Triple-write: synthesis markdown
        _write_synthesis_file(node_id, model, config)

    except Exception:
        logger.error(
            "Dual-write failed for %s (best-effort, continuing)",
            tool_name,
            exc_info=True,
        )


def _update_knowledge_tier(
    args: dict, result_str: str, config: WheelerConfig
) -> None:
    """Best-effort tier update: if a JSON file exists for the node, update its tier."""
    try:
        parsed = json.loads(result_str)
        if "error" in parsed:
            return

        node_id: str = args["node_id"]
        new_tier: str = args["tier"]

        from wheeler.knowledge.store import read_node, write_node

        knowledge_dir = Path(config.knowledge_path)

        try:
            node = read_node(knowledge_dir, node_id)
        except FileNotFoundError:
            logger.debug("set_tier: no knowledge file for %s, skipping", node_id)
            return

        node.tier = new_tier
        node.updated = _now()
        write_node(knowledge_dir, node)
        logger.info("Dual-write tier update: %s -> %s", node_id, new_tier)

        # Update synthesis file too
        _write_synthesis_file(node_id, node, config)

    except Exception:
        logger.error(
            "Dual-write tier update failed for %s (best-effort, continuing)",
            args.get("node_id", "?"),
            exc_info=True,
        )


# --- Synthesis write ---


def _write_synthesis_file(
    node_id: str,
    model: "NodeBase",
    config: WheelerConfig,
    relationships: list[dict] | None = None,
) -> None:
    """Best-effort synthesis markdown write."""
    try:
        from wheeler.knowledge.render import render_synthesis
        from wheeler.knowledge.store import write_synthesis

        markdown = render_synthesis(model, relationships=relationships)
        write_synthesis(Path(config.synthesis_path), node_id, markdown)
    except Exception:
        logger.error(
            "Synthesis write failed for %s (best-effort, continuing)",
            node_id,
            exc_info=True,
        )


async def _update_synthesis_for_link(
    backend, args: dict, config: WheelerConfig
) -> None:
    """Update synthesis files for both endpoints of a new relationship.

    Queries all relationships for each node and re-renders their
    synthesis files with a Relationships section.
    """
    try:
        from wheeler.knowledge.store import read_node
        from wheeler.models import PREFIX_TO_LABEL, title_for_node

        knowledge_dir = Path(config.knowledge_path)
        src_id: str = args["source_id"]
        tgt_id: str = args["target_id"]
        rel_type: str = args["relationship"]

        for node_id in (src_id, tgt_id):
            try:
                model = read_node(knowledge_dir, node_id)
            except FileNotFoundError:
                continue

            # Query all relationships for this node
            rels = []
            try:
                prefix = node_id.split("-", 1)[0]
                label = PREFIX_TO_LABEL.get(prefix, "")
                # Outgoing relationships
                out_records = await backend.run_cypher(
                    f"MATCH (n:{label} {{id: $nid}})-[r]->(m) "
                    "RETURN type(r) AS rel, m.id AS tid, labels(m)[0] AS tlabel",
                    {"nid": node_id},
                )
                for rec in out_records:
                    tid = rec.get("tid", "")
                    title = ""
                    try:
                        tmodel = read_node(knowledge_dir, tid)
                        title = title_for_node(tmodel)
                    except (FileNotFoundError, Exception):
                        pass
                    rels.append({
                        "target_id": tid,
                        "relationship": rec.get("rel", ""),
                        "target_title": title,
                        "direction": "outgoing",
                    })
                # Incoming relationships
                in_records = await backend.run_cypher(
                    f"MATCH (m)-[r]->(n:{label} {{id: $nid}}) "
                    "RETURN type(r) AS rel, m.id AS sid, labels(m)[0] AS slabel",
                    {"nid": node_id},
                )
                for rec in in_records:
                    sid = rec.get("sid", "")
                    title = ""
                    try:
                        smodel = read_node(knowledge_dir, sid)
                        title = title_for_node(smodel)
                    except (FileNotFoundError, Exception):
                        pass
                    rels.append({
                        "source_id": sid,
                        "relationship": rec.get("rel", ""),
                        "target_title": title,
                        "direction": "incoming",
                    })
            except Exception:
                logger.debug("Could not query relationships for %s", node_id)

            _write_synthesis_file(node_id, model, config, relationships=rels or None)

    except Exception:
        logger.error(
            "Synthesis link update failed (best-effort, continuing)",
            exc_info=True,
        )


# --- Dispatch ---


_backend_instance = None


async def _get_backend(config: WheelerConfig):
    """Return a cached, initialized backend instance."""
    global _backend_instance
    if _backend_instance is None:
        from wheeler.graph.backend import get_backend

        _backend_instance = get_backend(config)
        await _backend_instance.initialize()
    return _backend_instance


async def execute_tool(
    tool_name: str, args: dict, config: WheelerConfig
) -> str:
    """Execute a graph tool by name and return a JSON string result.

    Uses the configured backend (Neo4j, Kuzu, etc.) -- selected by
    ``config.graph.backend``.

    Triple-write: mutation tools (add_*) persist each new node as:
    1. Graph node (Neo4j)
    2. JSON file (knowledge/{node_id}.json)
    3. Synthesis markdown (synthesis/{node_id}.md)

    For ``set_tier``, updates both JSON and synthesis files.
    For ``link_nodes``, re-renders synthesis files for both endpoints.
    """
    handler = _TOOL_REGISTRY.get(tool_name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        logger.debug("execute_tool: %s", tool_name)
        backend = await _get_backend(config)

        # Inject config for query tools so they can read knowledge files
        if tool_name.startswith("query_") or tool_name == "graph_gaps":
            args["_config"] = config

        result = await handler(backend, args)

        # Dual-write: persist node as JSON file + synthesis markdown
        if tool_name in _MUTATION_TOOLS:
            _write_knowledge_file(tool_name, args, result, config)
        elif tool_name == "set_tier":
            _update_knowledge_tier(args, result, config)
        elif tool_name == "link_nodes":
            parsed = json.loads(result)
            if parsed.get("status") == "linked":
                await _update_synthesis_for_link(backend, args, config)

        logger.debug("execute_tool: %s completed", tool_name)
        return result
    except Exception as exc:
        logger.error("execute_tool %s failed: %s", tool_name, exc, exc_info=True)
        return json.dumps({"error": f"{tool_name} failed: {exc}"})
