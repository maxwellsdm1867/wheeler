"""Graph mutation tools: create nodes, link nodes, set properties.

All handlers take a ``GraphBackend`` instance (not a raw session) so
they work with the configured backend (Neo4j).

Provenance-completing: when ``execution_kind`` is passed, mutation tools
auto-create an Execution activity node and link inputs (USED) and
outputs (WAS_GENERATED_BY) in a single call.  The agent focuses on
science; infrastructure handles bookkeeping.
"""

from __future__ import annotations

import json
import logging
import os

from wheeler.graph.schema import ALLOWED_RELATIONSHIPS, PREFIX_TO_LABEL, generate_node_id
from wheeler.provenance import default_stability

from ._common import _now

# Common synonyms that agents may use instead of the canonical types.
# Mapped before validation so link_nodes accepts them transparently.
RELATIONSHIP_ALIASES: dict[str, str] = {
    "USES": "USED",
    "IMPLEMENTS": "WAS_DERIVED_FROM",
    "PRODUCES": "WAS_GENERATED_BY",
    "GENERATES": "WAS_GENERATED_BY",
    "INFORMED_BY": "WAS_INFORMED_BY",
    "DERIVED_FROM": "WAS_DERIVED_FROM",
    "GENERATED_BY": "WAS_GENERATED_BY",
    "USED_DATA": "DEPENDS_ON",
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provenance-completing helper
# ---------------------------------------------------------------------------


async def _complete_provenance(
    backend,
    entity_id: str,
    entity_label: str,
    args: dict,
) -> dict | None:
    """Auto-create an Execution node and provenance links if requested.

    If ``args["execution_kind"]`` is set, creates an Execution activity
    and links:
      - (entity) -[:WAS_GENERATED_BY]-> (execution)
      - (execution) -[:USED]-> (input) for each ID in args["used_entities"]

    Returns a provenance summary dict, or None if no provenance was requested.
    """
    execution_kind = args.get("execution_kind", "")
    if not execution_kind:
        return None

    now = _now()
    exec_id = generate_node_id("X")
    exec_desc = args.get("execution_description", "")
    exec_display = f"{execution_kind}: {exec_desc[:30]}" if execution_kind and exec_desc else execution_kind or exec_desc[:40]

    # Create the Execution activity node
    await backend.create_node("Execution", {
        "id": exec_id,
        "kind": execution_kind,
        "agent_id": args.get("agent_id", "wheeler"),
        "status": "completed",
        "started_at": args.get("started_at", now),
        "ended_at": args.get("ended_at", now),
        "session_id": args.get("session_id", ""),
        "description": exec_desc,
        "date": now,
        "tier": "generated",
        "stability": default_stability("Execution", "generated"),
        "display_name": exec_display,
    })

    # Link: entity -[:WAS_GENERATED_BY]-> execution
    entity_prefix = entity_id.split("-", 1)[0]
    src_label = PREFIX_TO_LABEL.get(entity_prefix, entity_label)
    await backend.create_relationship(
        src_label, entity_id, "WAS_GENERATED_BY", "Execution", exec_id,
    )

    # Link: execution -[:USED]-> each input entity
    used_entities = args.get("used_entities", [])
    if isinstance(used_entities, str):
        used_entities = [s.strip() for s in used_entities.split(",") if s.strip()]

    linked_inputs = []
    for input_id in used_entities:
        input_prefix = input_id.split("-", 1)[0]
        input_label = PREFIX_TO_LABEL.get(input_prefix)
        if input_label:
            await backend.create_relationship(
                "Execution", exec_id, "USED", input_label, input_id,
            )
            linked_inputs.append(input_id)
        else:
            logger.warning("_complete_provenance: unknown prefix in %s", input_id)

    logger.info(
        "Provenance: %s -[WAS_GENERATED_BY]-> %s (kind=%s, used %d inputs)",
        entity_id, exec_id, execution_kind, len(linked_inputs),
    )

    return {
        "execution_id": exec_id,
        "execution_kind": execution_kind,
        "linked_inputs": linked_inputs,
    }


# ---------------------------------------------------------------------------
# Mutation tools
# ---------------------------------------------------------------------------


async def add_finding(backend, args: dict) -> str:
    node_id = generate_node_id("F")
    display_name = args["description"][:40]
    await backend.create_node("Finding", {
        "id": node_id,
        "description": args["description"],
        "confidence": float(args["confidence"]),
        "path": args.get("path", ""),
        "artifact_type": args.get("artifact_type", ""),
        "source": args.get("source", ""),
        "date": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Finding", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created Finding %s (confidence=%.2f)", node_id, float(args["confidence"]))
    result = {"node_id": node_id, "label": "Finding", "status": "created"}

    prov = await _complete_provenance(backend, node_id, "Finding", args)
    if prov:
        result["provenance"] = prov

    return json.dumps(result)


async def add_hypothesis(backend, args: dict) -> str:
    node_id = generate_node_id("H")
    display_name = args["statement"][:40]
    await backend.create_node("Hypothesis", {
        "id": node_id,
        "statement": args["statement"],
        "status": args.get("status", "open"),
        "date": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Hypothesis", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created Hypothesis %s", node_id)
    result = {"node_id": node_id, "label": "Hypothesis", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "Hypothesis", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


async def add_question(backend, args: dict) -> str:
    node_id = generate_node_id("Q")
    display_name = args["question"][:40]
    await backend.create_node("OpenQuestion", {
        "id": node_id,
        "question": args["question"],
        "priority": int(args.get("priority", 5)),
        "date_added": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("OpenQuestion", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created OpenQuestion %s (priority=%d)", node_id, int(args.get("priority", 5)))
    result = {"node_id": node_id, "label": "OpenQuestion", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "OpenQuestion", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


async def add_dataset(backend, args: dict) -> str:
    node_id = generate_node_id("D")
    path = args["path"]
    display_name = os.path.basename(path) if path else args["description"][:40]
    await backend.create_node("Dataset", {
        "id": node_id,
        "path": path,
        "type": args["type"],
        "description": args["description"],
        "date_added": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Dataset", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created Dataset %s: %s", node_id, args["path"])
    result = {"node_id": node_id, "label": "Dataset", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "Dataset", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


async def add_paper(backend, args: dict) -> str:
    node_id = generate_node_id("P")
    authors = args.get("authors", "")
    year = int(args.get("year", 0))
    if authors and year:
        display_name = f"{authors.split(',')[0].strip()} et al., {year}"
    else:
        display_name = args["title"][:40]
    await backend.create_node("Paper", {
        "id": node_id,
        "title": args["title"],
        "authors": authors,
        "doi": args.get("doi", ""),
        "year": year,
        "date_added": _now(),
        "tier": "reference",  # Papers are published, always reference
        "stability": default_stability("Paper", "reference"),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created Paper %s: %s", node_id, args["title"][:60])
    return json.dumps({"node_id": node_id, "label": "Paper", "status": "created"})


async def add_document(backend, args: dict) -> str:
    node_id = generate_node_id("W")
    now = _now()
    title = args["title"]
    path = args["path"]
    display_name = title[:40] if title else os.path.basename(path) if path else ""
    await backend.create_node("Document", {
        "id": node_id,
        "title": title,
        "path": path,
        "section": args.get("section", ""),
        "status": args.get("status", "draft"),
        "date": now,
        "updated": now,
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Document", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created Document %s: %s", node_id, args["title"][:60])
    result = {"node_id": node_id, "label": "Document", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "Document", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


async def add_note(backend, args: dict) -> str:
    node_id = generate_node_id("N")
    title = args.get("title", "")
    display_name = title[:40] if title else args["content"][:40]
    await backend.create_node("ResearchNote", {
        "id": node_id,
        "title": title,
        "content": args["content"],
        "context": args.get("context", ""),
        "date": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("ResearchNote", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created ResearchNote %s: %s", node_id, args.get("title", "")[:60])
    result = {"node_id": node_id, "label": "ResearchNote", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "ResearchNote", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


async def add_script(backend, args: dict) -> str:
    node_id = generate_node_id("S")
    path = args.get("path", "")
    display_name = os.path.basename(path) if path else ""
    await backend.create_node("Script", {
        "id": node_id,
        "path": path,
        "hash": args.get("hash", ""),
        "language": args.get("language", ""),
        "version": args.get("version", ""),
        "date": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Script", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created Script %s: %s", node_id, args.get("path", "")[:60])
    return json.dumps({"node_id": node_id, "label": "Script", "status": "created"})


async def add_execution(backend, args: dict) -> str:
    node_id = generate_node_id("X")
    now = _now()
    kind = args.get("kind", "")
    description = args.get("description", "")
    display_name = f"{kind}: {description[:30]}" if kind and description else kind or description[:40]
    await backend.create_node("Execution", {
        "id": node_id,
        "kind": kind,
        "agent_id": args.get("agent_id", "wheeler"),
        "status": args.get("status", "completed"),
        "started_at": args.get("started_at", now),
        "ended_at": args.get("ended_at", now),
        "session_id": args.get("session_id", ""),
        "description": description,
        "date": now,
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Execution", args.get("tier", "generated")),
        "display_name": display_name,
    })
    logger.info("Created Execution %s (%s): %s", node_id, args.get("kind", ""), args.get("description", "")[:60])
    return json.dumps({"node_id": node_id, "label": "Execution", "status": "created"})


async def add_ledger(backend, args: dict) -> str:
    node_id = generate_node_id("L")
    mode = args.get("mode", "")
    display_name = f"Ledger: {mode}" if mode else "Ledger"
    await backend.create_node("Ledger", {
        "id": node_id,
        "mode": mode,
        "prompt_summary": args.get("prompt_summary", ""),
        "ungrounded": bool(args.get("ungrounded", False)),
        "pass_rate": float(args.get("pass_rate", 0.0)),
        "date": _now(),
        "tier": "generated",
        "stability": default_stability("Ledger", "generated"),
        "session_id": args.get("session_id", ""),
        "display_name": display_name,
    })
    logger.info("Created Ledger %s (mode=%s)", node_id, args.get("mode", ""))
    return json.dumps({"node_id": node_id, "label": "Ledger", "status": "created"})


async def link_nodes(backend, args: dict) -> str:
    rel = args["relationship"]
    rel = RELATIONSHIP_ALIASES.get(rel, rel)
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




async def unlink_nodes(backend, args: dict) -> str:
    rel = args["relationship"]
    rel = RELATIONSHIP_ALIASES.get(rel, rel)
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

    # Delete the relationship via Cypher
    records = await backend.run_cypher(
        f"MATCH (a:{src_label} {{id: $source}})-[r:{rel}]->(b:{tgt_label} {{id: $target}}) "
        "DELETE r RETURN count(r) AS deleted",
        {"source": args["source_id"], "target": args["target_id"]},
    )
    deleted_count = records[0]["deleted"] if records else 0

    if deleted_count > 0:
        logger.info("Unlinked %s -[%s]-> %s", args["source_id"], rel, args["target_id"])
        return json.dumps({
            "status": "unlinked",
            "source": args["source_id"],
            "target": args["target_id"],
            "relationship": rel,
        })
    logger.warning(
        "unlink_nodes: relationship not found (%s -[%s]-> %s)",
        args["source_id"], rel, args["target_id"],
    )
    return json.dumps({"error": "Relationship not found"})


async def delete_node(backend, args: dict) -> str:
    node_id = args["node_id"]
    prefix = node_id.split("-", 1)[0]
    label = PREFIX_TO_LABEL.get(prefix)
    if not label:
        return json.dumps({"error": f"Unknown node prefix: {prefix}"})

    deleted = await backend.delete_node(label, node_id)
    if deleted:
        logger.info("Deleted node %s (label=%s)", node_id, label)
        return json.dumps({
            "status": "deleted",
            "node_id": node_id,
            "label": label,
        })
    logger.warning("delete_node: node %s not found", node_id)
    return json.dumps({"error": f"Node {node_id} not found"})


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
