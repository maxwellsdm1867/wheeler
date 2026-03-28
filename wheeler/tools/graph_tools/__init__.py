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
    "add_analysis",
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
    "add_analysis": mutations.add_analysis,
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
    "query_analyses": queries.query_analyses,
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
            "analyses, hypotheses without supporting findings, stale analyses. "
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
        "name": "query_analyses",
        "description": "Search Analysis nodes in the knowledge graph by script path, description, or language.",
        "parameters": {
            "keyword": {"type": "string", "description": "Optional keyword to filter by", "default": ""},
            "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
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

    except Exception:
        logger.error(
            "Dual-write tier update failed for %s (best-effort, continuing)",
            args.get("node_id", "?"),
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

    Uses the configured backend (Neo4j, Kuzu, etc.) — selected by
    ``config.graph.backend``.

    For mutation tools (add_*), a best-effort dual-write persists the new
    node as a JSON file under ``config.knowledge_path``.  For ``set_tier``,
    the existing JSON file (if any) is updated.
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

        # Dual-write: persist node as JSON file
        if tool_name in _MUTATION_TOOLS:
            _write_knowledge_file(tool_name, args, result, config)
        elif tool_name == "set_tier":
            _update_knowledge_tier(args, result, config)

        logger.debug("execute_tool: %s completed", tool_name)
        return result
    except Exception as exc:
        logger.error("execute_tool %s failed: %s", tool_name, exc, exc_info=True)
        return json.dumps({"error": f"{tool_name} failed: {exc}"})
