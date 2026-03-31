"""Graph mutation tools: create nodes, link nodes, set properties.

All handlers take a ``GraphBackend`` instance (not a raw session) so
they work with any configured backend (Neo4j, Kuzu, etc.).
"""

from __future__ import annotations

import json
import logging

from wheeler.graph.schema import ALLOWED_RELATIONSHIPS, PREFIX_TO_LABEL, generate_node_id

from ._common import _now

logger = logging.getLogger(__name__)


async def add_finding(backend, args: dict) -> str:
    node_id = generate_node_id("F")
    await backend.create_node("Finding", {
        "id": node_id,
        "description": args["description"],
        "confidence": float(args["confidence"]),
        "date": _now(),
        "tier": args.get("tier", "generated"),
    })
    logger.info("Created Finding %s (confidence=%.2f)", node_id, float(args["confidence"]))
    return json.dumps({"node_id": node_id, "label": "Finding", "status": "created"})


async def add_hypothesis(backend, args: dict) -> str:
    node_id = generate_node_id("H")
    await backend.create_node("Hypothesis", {
        "id": node_id,
        "statement": args["statement"],
        "status": args.get("status", "open"),
        "date": _now(),
        "tier": args.get("tier", "generated"),
    })
    logger.info("Created Hypothesis %s", node_id)
    return json.dumps({"node_id": node_id, "label": "Hypothesis", "status": "created"})


async def add_question(backend, args: dict) -> str:
    node_id = generate_node_id("Q")
    await backend.create_node("OpenQuestion", {
        "id": node_id,
        "question": args["question"],
        "priority": int(args.get("priority", 5)),
        "date_added": _now(),
        "tier": args.get("tier", "generated"),
    })
    logger.info("Created OpenQuestion %s (priority=%d)", node_id, int(args.get("priority", 5)))
    return json.dumps({"node_id": node_id, "label": "OpenQuestion", "status": "created"})


async def add_dataset(backend, args: dict) -> str:
    node_id = generate_node_id("D")
    await backend.create_node("Dataset", {
        "id": node_id,
        "path": args["path"],
        "type": args["type"],
        "description": args["description"],
        "date_added": _now(),
        "tier": args.get("tier", "generated"),
    })
    logger.info("Created Dataset %s: %s", node_id, args["path"])
    return json.dumps({"node_id": node_id, "label": "Dataset", "status": "created"})


async def add_paper(backend, args: dict) -> str:
    node_id = generate_node_id("P")
    await backend.create_node("Paper", {
        "id": node_id,
        "title": args["title"],
        "authors": args.get("authors", ""),
        "doi": args.get("doi", ""),
        "year": int(args.get("year", 0)),
        "date_added": _now(),
        "tier": "reference",  # Papers are published — always reference
    })
    logger.info("Created Paper %s: %s", node_id, args["title"][:60])
    return json.dumps({"node_id": node_id, "label": "Paper", "status": "created"})


async def add_document(backend, args: dict) -> str:
    node_id = generate_node_id("W")
    now = _now()
    await backend.create_node("Document", {
        "id": node_id,
        "title": args["title"],
        "path": args["path"],
        "section": args.get("section", ""),
        "status": args.get("status", "draft"),
        "date": now,
        "updated": now,
        "tier": args.get("tier", "generated"),
    })
    logger.info("Created Document %s: %s", node_id, args["title"][:60])
    return json.dumps({"node_id": node_id, "label": "Document", "status": "created"})


async def add_note(backend, args: dict) -> str:
    node_id = generate_node_id("N")
    await backend.create_node("ResearchNote", {
        "id": node_id,
        "title": args.get("title", ""),
        "content": args["content"],
        "context": args.get("context", ""),
        "date": _now(),
        "tier": args.get("tier", "generated"),
    })
    logger.info("Created ResearchNote %s: %s", node_id, args.get("title", "")[:60])
    return json.dumps({"node_id": node_id, "label": "ResearchNote", "status": "created"})


async def add_script(backend, args: dict) -> str:
    node_id = generate_node_id("S")
    await backend.create_node("Script", {
        "id": node_id,
        "path": args.get("path", ""),
        "hash": args.get("hash", ""),
        "language": args.get("language", ""),
        "version": args.get("version", ""),
        "date": _now(),
        "tier": args.get("tier", "generated"),
    })
    logger.info("Created Script %s: %s", node_id, args.get("path", "")[:60])
    return json.dumps({"node_id": node_id, "label": "Script", "status": "created"})


async def add_execution(backend, args: dict) -> str:
    node_id = generate_node_id("X")
    now = _now()
    await backend.create_node("Execution", {
        "id": node_id,
        "kind": args.get("kind", ""),
        "agent_id": args.get("agent_id", "wheeler"),
        "status": args.get("status", "completed"),
        "started_at": args.get("started_at", now),
        "ended_at": args.get("ended_at", now),
        "session_id": args.get("session_id", ""),
        "description": args.get("description", ""),
        "date": now,
        "tier": args.get("tier", "generated"),
    })
    logger.info("Created Execution %s (%s): %s", node_id, args.get("kind", ""), args.get("description", "")[:60])
    return json.dumps({"node_id": node_id, "label": "Execution", "status": "created"})


async def add_ledger(backend, args: dict) -> str:
    node_id = generate_node_id("L")
    await backend.create_node("Ledger", {
        "id": node_id,
        "mode": args.get("mode", ""),
        "prompt_summary": args.get("prompt_summary", ""),
        "ungrounded": bool(args.get("ungrounded", False)),
        "pass_rate": float(args.get("pass_rate", 0.0)),
        "date": _now(),
        "tier": "generated",
    })
    logger.info("Created Ledger %s (mode=%s)", node_id, args.get("mode", ""))
    return json.dumps({"node_id": node_id, "label": "Ledger", "status": "created"})


async def link_nodes(backend, args: dict) -> str:
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

    linked = await backend.create_relationship(
        src_label, args["source_id"], rel, tgt_label, args["target_id"],
    )
    if linked:
        logger.info("Linked %s -[%s]-> %s", args["source_id"], rel, args["target_id"])
        return json.dumps({
            "status": "linked",
            "source": args["source_id"],
            "target": args["target_id"],
            "relationship": rel,
        })
    logger.warning("link_nodes failed: one or both nodes not found (%s, %s)", args["source_id"], args["target_id"])
    return json.dumps({"error": "One or both nodes not found"})


async def set_tier(backend, args: dict) -> str:
    tier = args["tier"]
    if tier not in ("reference", "generated"):
        return json.dumps({"error": f"Invalid tier: {tier}. Must be 'reference' or 'generated'."})

    node_id = args["node_id"]
    prefix = node_id.split("-", 1)[0]
    label = PREFIX_TO_LABEL.get(prefix)
    if not label:
        return json.dumps({"error": f"Unknown node prefix: {prefix}"})

    updated = await backend.update_node(label, node_id, {"tier": tier})
    if updated:
        logger.info("Set tier %s -> %s", node_id, tier)
        return json.dumps({"node_id": node_id, "tier": tier, "status": "updated"})
    logger.warning("set_tier: node %s not found", node_id)
    return json.dumps({"error": f"Node {node_id} not found"})
