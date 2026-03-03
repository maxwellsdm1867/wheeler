"""Provenance trace: walk the graph backwards from a node to show its full chain."""

from __future__ import annotations

from dataclasses import dataclass

from neo4j import AsyncGraphDatabase

from wheeler.config import WheelerConfig
from wheeler.graph.schema import PREFIX_TO_LABEL


@dataclass
class TraceStep:
    node_id: str
    label: str
    description: str
    relationship: str  # how this node connects to the next
    properties: dict


@dataclass
class TraceResult:
    root_id: str
    root_label: str
    root_description: str
    chain: list[TraceStep]
    root_properties: dict


async def trace_node(node_id: str, config: WheelerConfig) -> TraceResult | None:
    """Walk the graph backwards from a node, following provenance relationships.

    Returns the full chain: e.g. Finding ← Analysis ← Dataset ← Experiment.
    Returns None if the node doesn't exist.
    """
    prefix = node_id.split("-", 1)[0]
    label = PREFIX_TO_LABEL.get(prefix)
    if label is None:
        return None

    driver = AsyncGraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
    )
    try:
        async with driver.session(database=config.neo4j.database) as session:
            # Check root node exists
            result = await session.run(
                f"MATCH (n:{label} {{id: $id}}) RETURN n",
                id=node_id,
            )
            record = await result.single()
            if record is None:
                return None

            root_node = dict(record["n"])
            root_desc = (
                root_node.get("description")
                or root_node.get("statement")
                or root_node.get("question")
                or root_node.get("title")
                or root_node.get("name")
                or ""
            )

            # Walk backwards: find all incoming relationships up to 5 hops
            result = await session.run(
                "MATCH path = (n {id: $id})<-[*1..5]-(upstream) "
                "UNWIND relationships(path) AS r "
                "WITH startNode(r) AS src, endNode(r) AS tgt, type(r) AS rel "
                "RETURN src.id AS src_id, labels(src)[0] AS src_label, "
                "  src.description AS src_desc, src.statement AS src_stmt, "
                "  src.question AS src_q, src.title AS src_title, "
                "  src.name AS src_name, "
                "  src {.script_path, .script_hash, .language, .confidence, "
                "       .priority, .status, .doi, .date, .executed_at} AS src_props, "
                "  tgt.id AS tgt_id, rel",
                id=node_id,
            )
            records = [r async for r in result]

            # Build chain from records, deduplicating
            seen = set()
            chain: list[TraceStep] = []
            for rec in records:
                src_id = rec["src_id"]
                if src_id and src_id not in seen and src_id != node_id:
                    seen.add(src_id)
                    desc = (
                        rec["src_desc"]
                        or rec["src_stmt"]
                        or rec["src_q"]
                        or rec["src_title"]
                        or rec["src_name"]
                        or ""
                    )
                    props = {
                        k: v
                        for k, v in (rec["src_props"] or {}).items()
                        if v is not None
                    }
                    chain.append(TraceStep(
                        node_id=src_id,
                        label=rec["src_label"] or "Unknown",
                        description=desc,
                        relationship=rec["rel"],
                        properties=props,
                    ))

            return TraceResult(
                root_id=node_id,
                root_label=label,
                root_description=root_desc,
                chain=chain,
                root_properties={
                    k: v for k, v in root_node.items()
                    if k not in ("id", "description", "statement", "question",
                                 "title", "name")
                    and v is not None
                },
            )
    finally:
        await driver.close()
