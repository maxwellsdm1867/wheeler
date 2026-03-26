"""Graph tools package: mutations and queries for the Wheeler knowledge graph.

Public API (backward-compatible with the old graph_tools.py module):
  - TOOL_DEFINITIONS: list of tool specs for CLI and MCP registration
  - execute_tool(name, args, config): dispatch a tool by name
"""

from __future__ import annotations

import json
import logging

from wheeler.config import WheelerConfig
from wheeler.graph.schema import ALLOWED_RELATIONSHIPS

from . import mutations, queries

logger = logging.getLogger(__name__)

# --- Tool registry: maps tool names to handler functions ---

_TOOL_REGISTRY: dict[str, object] = {
    # Mutations
    "add_finding": mutations.add_finding,
    "add_hypothesis": mutations.add_hypothesis,
    "add_question": mutations.add_question,
    "add_dataset": mutations.add_dataset,
    "add_paper": mutations.add_paper,
    "add_document": mutations.add_document,
    "link_nodes": mutations.link_nodes,
    "set_tier": mutations.set_tier,
    # Queries
    "query_findings": queries.query_findings,
    "query_open_questions": queries.query_open_questions,
    "query_hypotheses": queries.query_hypotheses,
    "query_datasets": queries.query_datasets,
    "query_papers": queries.query_papers,
    "query_documents": queries.query_documents,
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


# --- Dispatch ---


async def execute_tool(
    tool_name: str, args: dict, config: WheelerConfig
) -> str:
    """Execute a graph tool by name and return a JSON string result.

    Each call gets its own session — failures in one tool call don't
    affect subsequent calls. The driver is a singleton with a connection
    pool, so session creation is cheap.
    """
    handler = _TOOL_REGISTRY.get(tool_name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        logger.debug("execute_tool: %s", tool_name)
        from wheeler.graph.driver import get_async_driver
        driver = get_async_driver(config)
        async with driver.session(database=config.neo4j.database) as session:
            if tool_name == "graph_gaps":
                result = await handler(session)
            else:
                result = await handler(session, args)
        logger.debug("execute_tool: %s completed", tool_name)
        return result
    except Exception as exc:
        logger.error("execute_tool %s failed: %s", tool_name, exc, exc_info=True)
        return json.dumps({"error": f"{tool_name} failed: {exc}"})
