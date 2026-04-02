"""Graph mutation tools: create nodes, link nodes, set properties.

All handlers take a ``GraphBackend`` instance (not a raw session) so
they work with any configured backend (Neo4j, Kuzu, etc.).

Provenance-completing: when ``execution_kind`` is passed, mutation tools
auto-create an Execution activity node and link inputs (USED) and
outputs (WAS_GENERATED_BY) in a single call.  The agent focuses on
science; infrastructure handles bookkeeping.
"""

from __future__ import annotations

import json
import logging

from wheeler.graph.schema import ALLOWED_RELATIONSHIPS, PREFIX_TO_LABEL, generate_node_id
from wheeler.provenance import default_stability

from ._common import _now

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

    # Create the Execution activity node
    await backend.create_node("Execution", {
        "id": exec_id,
        "kind": execution_kind,
        "agent_id": args.get("agent_id", "wheeler"),
        "status": "completed",
        "started_at": args.get("started_at", now),
        "ended_at": args.get("ended_at", now),
        "session_id": args.get("session_id", ""),
        "description": args.get("execution_description", ""),
        "date": now,
        "tier": "generated",
        "stability": default_stability("Execution", "generated"),
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
    await backend.create_node("Finding", {
        "id": node_id,
        "description": args["description"],
        "confidence": float(args["confidence"]),
        "date": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Finding", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
    })
    logger.info("Created Finding %s (confidence=%.2f)", node_id, float(args["confidence"]))
    result = {"node_id": node_id, "label": "Finding", "status": "created"}

    prov = await _complete_provenance(backend, node_id, "Finding", args)
    if prov:
        result["provenance"] = prov

    return json.dumps(result)


async def add_hypothesis(backend, args: dict) -> str:
    node_id = generate_node_id("H")
    await backend.create_node("Hypothesis", {
        "id": node_id,
        "statement": args["statement"],
        "status": args.get("status", "open"),
        "date": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Hypothesis", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
    })
    logger.info("Created Hypothesis %s", node_id)
    result = {"node_id": node_id, "label": "Hypothesis", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "Hypothesis", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


async def add_question(backend, args: dict) -> str:
    node_id = generate_node_id("Q")
    await backend.create_node("OpenQuestion", {
        "id": node_id,
        "question": args["question"],
        "priority": int(args.get("priority", 5)),
        "date_added": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("OpenQuestion", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
    })
    logger.info("Created OpenQuestion %s (priority=%d)", node_id, int(args.get("priority", 5)))
    result = {"node_id": node_id, "label": "OpenQuestion", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "OpenQuestion", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


async def add_dataset(backend, args: dict) -> str:
    node_id = generate_node_id("D")
    await backend.create_node("Dataset", {
        "id": node_id,
        "path": args["path"],
        "type": args["type"],
        "description": args["description"],
        "date_added": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("Dataset", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
    })
    logger.info("Created Dataset %s: %s", node_id, args["path"])
    result = {"node_id": node_id, "label": "Dataset", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "Dataset", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


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
        "stability": default_stability("Paper", "reference"),
        "session_id": args.get("session_id", ""),
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
        "stability": default_stability("Document", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
    })
    logger.info("Created Document %s: %s", node_id, args["title"][:60])
    result = {"node_id": node_id, "label": "Document", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "Document", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


async def add_note(backend, args: dict) -> str:
    node_id = generate_node_id("N")
    await backend.create_node("ResearchNote", {
        "id": node_id,
        "title": args.get("title", ""),
        "content": args["content"],
        "context": args.get("context", ""),
        "date": _now(),
        "tier": args.get("tier", "generated"),
        "stability": default_stability("ResearchNote", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
    })
    logger.info("Created ResearchNote %s: %s", node_id, args.get("title", "")[:60])
    result = {"node_id": node_id, "label": "ResearchNote", "status": "created"}
    prov = await _complete_provenance(backend, node_id, "ResearchNote", args)
    if prov:
        result["provenance"] = prov
    return json.dumps(result)


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
        "stability": default_stability("Script", args.get("tier", "generated")),
        "session_id": args.get("session_id", ""),
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
        "stability": default_stability("Execution", args.get("tier", "generated")),
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
        "stability": default_stability("Ledger", "generated"),
        "session_id": args.get("session_id", ""),
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
