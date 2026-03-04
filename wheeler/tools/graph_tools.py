"""In-process MCP tools for science-friendly graph operations.

These tools are registered with the Agent SDK so Claude can manipulate
the knowledge graph during conversations without writing raw Cypher.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from wheeler.config import WheelerConfig
from wheeler.graph.schema import ALLOWED_RELATIONSHIPS, PREFIX_TO_LABEL


def _generate_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_session(config: WheelerConfig):
    from wheeler.graph.context import _get_driver
    driver = _get_driver(config)
    return driver, driver.session(database=config.neo4j.database)


# --- Tool definitions ---
# Each returns a dict suitable for MCP tool response.


TOOL_DEFINITIONS = [
    {
        "name": "add_finding",
        "description": (
            "Add a Finding to the knowledge graph. Use when an analysis "
            "produces a result worth recording. Returns the new node ID."
        ),
        "parameters": {
            "description": {"type": "string", "description": "What was found"},
            "confidence": {
                "type": "number",
                "description": "Confidence 0.0-1.0",
            },
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
            "status": {
                "type": "string",
                "description": "open, supported, or rejected",
                "default": "open",
            },
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
            "priority": {
                "type": "integer",
                "description": "Priority 1-10 (10=highest)",
                "default": 5,
            },
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
            "relationship": {
                "type": "string",
                "description": f"One of: {', '.join(ALLOWED_RELATIONSHIPS)}",
            },
        },
        "required": ["source_id", "target_id", "relationship"],
    },
    {
        "name": "query_findings",
        "description": (
            "Search findings in the knowledge graph. Returns recent findings "
            "optionally filtered by keyword."
        ),
        "parameters": {
            "keyword": {
                "type": "string",
                "description": "Optional keyword to filter by",
                "default": "",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 10)",
                "default": 10,
            },
        },
        "required": [],
    },
    {
        "name": "query_open_questions",
        "description": "List open questions from the knowledge graph, sorted by priority.",
        "parameters": {
            "limit": {
                "type": "integer",
                "description": "Max results (default 10)",
                "default": 10,
            },
        },
        "required": [],
    },
    {
        "name": "query_hypotheses",
        "description": "List hypotheses, optionally filtered by status.",
        "parameters": {
            "status": {
                "type": "string",
                "description": "Filter: open, supported, rejected, or all",
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 10)",
                "default": 10,
            },
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
            "type": {
                "type": "string",
                "description": "Dataset type (e.g., mat, h5, csv)",
            },
            "description": {
                "type": "string",
                "description": "What the dataset contains",
            },
        },
        "required": ["path", "type", "description"],
    },
    {
        "name": "query_datasets",
        "description": "Search Dataset nodes in the knowledge graph.",
        "parameters": {
            "keyword": {
                "type": "string",
                "description": "Optional keyword to filter by",
                "default": "",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 10)",
                "default": 10,
            },
        },
        "required": [],
    },
]


async def execute_tool(
    tool_name: str, args: dict, config: WheelerConfig
) -> str:
    """Execute a graph tool and return a JSON string result."""
    driver, session = await _get_session(config)
    async with session as s:
        if tool_name == "add_finding":
            return await _add_finding(s, args)
        elif tool_name == "add_hypothesis":
            return await _add_hypothesis(s, args)
        elif tool_name == "add_question":
            return await _add_question(s, args)
        elif tool_name == "link_nodes":
            return await _link_nodes(s, args)
        elif tool_name == "query_findings":
            return await _query_findings(s, args)
        elif tool_name == "query_open_questions":
            return await _query_open_questions(s, args)
        elif tool_name == "query_hypotheses":
            return await _query_hypotheses(s, args)
        elif tool_name == "graph_gaps":
            return await _graph_gaps(s)
        elif tool_name == "add_dataset":
            return await _add_dataset(s, args)
        elif tool_name == "query_datasets":
            return await _query_datasets(s, args)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})


async def _add_finding(session, args: dict) -> str:
    node_id = _generate_id("F")
    await session.run(
        "CREATE (f:Finding {id: $id, description: $desc, "
        "confidence: $confidence, date: $date})",
        id=node_id,
        desc=args["description"],
        confidence=float(args["confidence"]),
        date=_now(),
    )
    return json.dumps({"node_id": node_id, "label": "Finding", "status": "created"})


async def _add_hypothesis(session, args: dict) -> str:
    node_id = _generate_id("H")
    await session.run(
        "CREATE (h:Hypothesis {id: $id, statement: $stmt, "
        "status: $status, date: $date})",
        id=node_id,
        stmt=args["statement"],
        status=args.get("status", "open"),
        date=_now(),
    )
    return json.dumps({"node_id": node_id, "label": "Hypothesis", "status": "created"})


async def _add_question(session, args: dict) -> str:
    node_id = _generate_id("Q")
    await session.run(
        "CREATE (q:OpenQuestion {id: $id, question: $question, "
        "priority: $priority, date_added: $date})",
        id=node_id,
        question=args["question"],
        priority=int(args.get("priority", 5)),
        date=_now(),
    )
    return json.dumps({"node_id": node_id, "label": "OpenQuestion", "status": "created"})


async def _link_nodes(session, args: dict) -> str:
    rel = args["relationship"]
    if rel not in ALLOWED_RELATIONSHIPS:
        return json.dumps({
            "error": f"Invalid relationship: {rel}",
            "allowed": ALLOWED_RELATIONSHIPS,
        })

    src_prefix = args["source_id"].split("-", 1)[0]
    tgt_prefix = args["target_id"].split("-", 1)[0]
    src_label = PREFIX_TO_LABEL.get(src_prefix)
    tgt_label = PREFIX_TO_LABEL.get(tgt_prefix)

    if not src_label or not tgt_label:
        return json.dumps({"error": "Could not determine node labels from IDs"})

    result = await session.run(
        f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
        f"CREATE (a)-[r:{rel}]->(b) RETURN type(r) AS rel",
        src=args["source_id"],
        tgt=args["target_id"],
    )
    record = await result.single()
    if record:
        return json.dumps({
            "status": "linked",
            "source": args["source_id"],
            "target": args["target_id"],
            "relationship": rel,
        })
    return json.dumps({"error": "One or both nodes not found"})


async def _query_findings(session, args: dict) -> str:
    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        result = await session.run(
            "MATCH (f:Finding) WHERE toLower(f.description) CONTAINS toLower($kw) "
            "RETURN f.id AS id, f.description AS desc, f.confidence AS conf, f.date AS date "
            "ORDER BY f.date DESC LIMIT $limit",
            kw=keyword,
            limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (f:Finding) "
            "RETURN f.id AS id, f.description AS desc, f.confidence AS conf, f.date AS date "
            "ORDER BY f.date DESC LIMIT $limit",
            limit=limit,
        )
    records = [r async for r in result]
    findings = [
        {"id": r["id"], "description": r["desc"], "confidence": r["conf"], "date": r["date"]}
        for r in records
    ]
    return json.dumps({"findings": findings, "count": len(findings)})


async def _query_open_questions(session, args: dict) -> str:
    limit = int(args.get("limit", 10))
    result = await session.run(
        "MATCH (q:OpenQuestion) "
        "RETURN q.id AS id, q.question AS question, q.priority AS priority "
        "ORDER BY q.priority DESC LIMIT $limit",
        limit=limit,
    )
    records = [r async for r in result]
    questions = [
        {"id": r["id"], "question": r["question"], "priority": r["priority"]}
        for r in records
    ]
    return json.dumps({"questions": questions, "count": len(questions)})


async def _query_hypotheses(session, args: dict) -> str:
    status = args.get("status", "all")
    limit = int(args.get("limit", 10))

    if status and status != "all":
        result = await session.run(
            "MATCH (h:Hypothesis {status: $status}) "
            "RETURN h.id AS id, h.statement AS stmt, h.status AS status "
            "LIMIT $limit",
            status=status,
            limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (h:Hypothesis) "
            "RETURN h.id AS id, h.statement AS stmt, h.status AS status "
            "LIMIT $limit",
            limit=limit,
        )
    records = [r async for r in result]
    hypotheses = [
        {"id": r["id"], "statement": r["stmt"], "status": r["status"]}
        for r in records
    ]
    return json.dumps({"hypotheses": hypotheses, "count": len(hypotheses)})


async def _graph_gaps(session) -> str:
    """Find knowledge gaps: unlinked questions, unsupported hypotheses, stale analyses."""
    gaps: dict = {}

    # Open questions without linked analyses
    result = await session.run(
        "MATCH (q:OpenQuestion) "
        "WHERE NOT (q)<-[:AROSE_FROM]-() AND NOT ()-[:RELEVANT_TO]->(q) "
        "RETURN q.id AS id, q.question AS question, q.priority AS priority "
        "ORDER BY q.priority DESC LIMIT 10"
    )
    records = [r async for r in result]
    gaps["unlinked_questions"] = [
        {"id": r["id"], "question": r["question"], "priority": r["priority"]}
        for r in records
    ]

    # Hypotheses without supporting/contradicting findings
    result = await session.run(
        "MATCH (h:Hypothesis {status: 'open'}) "
        "WHERE NOT ()-[:SUPPORTS|CONTRADICTS]->(h) "
        "RETURN h.id AS id, h.statement AS stmt "
        "LIMIT 10"
    )
    records = [r async for r in result]
    gaps["unsupported_hypotheses"] = [
        {"id": r["id"], "statement": r["stmt"]}
        for r in records
    ]

    # Stale analyses (script_hash mismatch detected at query time is expensive,
    # so just flag analyses that have no downstream findings)
    result = await session.run(
        "MATCH (a:Analysis) "
        "WHERE NOT (a)-[:GENERATED]->(:Finding) "
        "RETURN a.id AS id, a.script_path AS path "
        "LIMIT 10"
    )
    records = [r async for r in result]
    gaps["analyses_without_findings"] = [
        {"id": r["id"], "script_path": r["path"]}
        for r in records
    ]

    total = sum(len(v) for v in gaps.values())
    gaps["total_gaps"] = total
    return json.dumps(gaps)


async def _add_dataset(session, args: dict) -> str:
    node_id = _generate_id("D")
    await session.run(
        "CREATE (d:Dataset {id: $id, path: $path, type: $type, "
        "description: $desc, date_added: $date})",
        id=node_id,
        path=args["path"],
        type=args["type"],
        desc=args["description"],
        date=_now(),
    )
    return json.dumps({"node_id": node_id, "label": "Dataset", "status": "created"})


async def _query_datasets(session, args: dict) -> str:
    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        result = await session.run(
            "MATCH (d:Dataset) WHERE toLower(d.description) CONTAINS toLower($kw) "
            "OR toLower(d.path) CONTAINS toLower($kw) "
            "RETURN d.id AS id, d.path AS path, d.type AS type, "
            "d.description AS desc, d.date_added AS date "
            "ORDER BY d.date_added DESC LIMIT $limit",
            kw=keyword,
            limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (d:Dataset) "
            "RETURN d.id AS id, d.path AS path, d.type AS type, "
            "d.description AS desc, d.date_added AS date "
            "ORDER BY d.date_added DESC LIMIT $limit",
            limit=limit,
        )
    records = [r async for r in result]
    datasets = [
        {"id": r["id"], "path": r["path"], "type": r["type"],
         "description": r["desc"], "date_added": r["date"]}
        for r in records
    ]
    return json.dumps({"datasets": datasets, "count": len(datasets)})
