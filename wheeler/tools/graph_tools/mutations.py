"""Graph mutation tools: create nodes, link nodes, set properties."""

from __future__ import annotations

import json
import logging

from wheeler.graph.schema import ALLOWED_RELATIONSHIPS, PREFIX_TO_LABEL, generate_node_id

from ._common import _now

logger = logging.getLogger(__name__)


async def add_finding(session, args: dict) -> str:
    node_id = generate_node_id("F")
    await session.run(
        "CREATE (f:Finding {id: $id, description: $desc, "
        "confidence: $confidence, date: $date, tier: $tier})",
        id=node_id,
        desc=args["description"],
        confidence=float(args["confidence"]),
        date=_now(),
        tier=args.get("tier", "generated"),
    )
    logger.info("Created Finding %s (confidence=%.2f)", node_id, float(args["confidence"]))
    return json.dumps({"node_id": node_id, "label": "Finding", "status": "created"})


async def add_hypothesis(session, args: dict) -> str:
    node_id = generate_node_id("H")
    await session.run(
        "CREATE (h:Hypothesis {id: $id, statement: $stmt, "
        "status: $status, date: $date, tier: $tier})",
        id=node_id,
        stmt=args["statement"],
        status=args.get("status", "open"),
        date=_now(),
        tier=args.get("tier", "generated"),
    )
    logger.info("Created Hypothesis %s", node_id)
    return json.dumps({"node_id": node_id, "label": "Hypothesis", "status": "created"})


async def add_question(session, args: dict) -> str:
    node_id = generate_node_id("Q")
    await session.run(
        "CREATE (q:OpenQuestion {id: $id, question: $question, "
        "priority: $priority, date_added: $date, tier: $tier})",
        id=node_id,
        question=args["question"],
        priority=int(args.get("priority", 5)),
        date=_now(),
        tier=args.get("tier", "generated"),
    )
    logger.info("Created OpenQuestion %s (priority=%d)", node_id, int(args.get("priority", 5)))
    return json.dumps({"node_id": node_id, "label": "OpenQuestion", "status": "created"})


async def add_dataset(session, args: dict) -> str:
    node_id = generate_node_id("D")
    await session.run(
        "CREATE (d:Dataset {id: $id, path: $path, type: $type, "
        "description: $desc, date_added: $date, tier: $tier})",
        id=node_id,
        path=args["path"],
        type=args["type"],
        desc=args["description"],
        date=_now(),
        tier=args.get("tier", "generated"),
    )
    logger.info("Created Dataset %s: %s", node_id, args["path"])
    return json.dumps({"node_id": node_id, "label": "Dataset", "status": "created"})


async def add_paper(session, args: dict) -> str:
    node_id = generate_node_id("P")
    await session.run(
        "CREATE (p:Paper {id: $id, title: $title, authors: $authors, "
        "doi: $doi, year: $year, date_added: $date, tier: $tier})",
        id=node_id,
        title=args["title"],
        authors=args.get("authors", ""),
        doi=args.get("doi", ""),
        year=int(args.get("year", 0)),
        date=_now(),
        tier="reference",  # Papers are published — always reference
    )
    logger.info("Created Paper %s: %s", node_id, args["title"][:60])
    return json.dumps({"node_id": node_id, "label": "Paper", "status": "created"})


async def add_document(session, args: dict) -> str:
    node_id = generate_node_id("W")
    now = _now()
    await session.run(
        "CREATE (w:Document {id: $id, title: $title, path: $path, "
        "section: $section, status: $status, date: $date, updated: $updated, tier: $tier})",
        id=node_id,
        title=args["title"],
        path=args["path"],
        section=args.get("section", ""),
        status=args.get("status", "draft"),
        date=now,
        updated=now,
        tier=args.get("tier", "generated"),
    )
    logger.info("Created Document %s: %s", node_id, args["title"][:60])
    return json.dumps({"node_id": node_id, "label": "Document", "status": "created"})


async def add_note(session, args: dict) -> str:
    node_id = generate_node_id("N")
    await session.run(
        "CREATE (n:ResearchNote {id: $id, title: $title, content: $content, "
        "context: $context, date: $date, tier: $tier})",
        id=node_id,
        title=args.get("title", ""),
        content=args["content"],
        context=args.get("context", ""),
        date=_now(),
        tier=args.get("tier", "generated"),
    )
    logger.info("Created ResearchNote %s: %s", node_id, args.get("title", "")[:60])
    return json.dumps({"node_id": node_id, "label": "ResearchNote", "status": "created"})


async def link_nodes(session, args: dict) -> str:
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
        logger.info("Linked %s -[%s]-> %s", args["source_id"], rel, args["target_id"])
        return json.dumps({
            "status": "linked",
            "source": args["source_id"],
            "target": args["target_id"],
            "relationship": rel,
        })
    logger.warning("link_nodes failed: one or both nodes not found (%s, %s)", args["source_id"], args["target_id"])
    return json.dumps({"error": "One or both nodes not found"})


async def set_tier(session, args: dict) -> str:
    tier = args["tier"]
    if tier not in ("reference", "generated"):
        return json.dumps({"error": f"Invalid tier: {tier}. Must be 'reference' or 'generated'."})

    node_id = args["node_id"]
    prefix = node_id.split("-", 1)[0]
    label = PREFIX_TO_LABEL.get(prefix)
    if not label:
        return json.dumps({"error": f"Unknown node prefix: {prefix}"})

    result = await session.run(
        f"MATCH (n:{label} {{id: $id}}) SET n.tier = $tier RETURN n.id AS id",
        id=node_id,
        tier=tier,
    )
    record = await result.single()
    if record:
        logger.info("Set tier %s -> %s", node_id, tier)
        return json.dumps({"node_id": node_id, "tier": tier, "status": "updated"})
    logger.warning("set_tier: node %s not found", node_id)
    return json.dumps({"error": f"Node {node_id} not found"})
