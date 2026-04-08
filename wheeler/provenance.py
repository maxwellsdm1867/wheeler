"""Provenance extensions: stability scoring and invalidation propagation.

Extends Wheeler's knowledge graph with W3C PROV-based provenance tracking,
stability scoring for epistemic trust, and automatic invalidation propagation.

Layer 2: depends on config, models, graph.driver, graph.schema.

Usage
-----
Stability scoring::

    from wheeler.provenance import default_stability

    stability = default_stability(label="Finding", tier="generated")  # 0.3

Invalidation propagation::

    from wheeler.provenance import propagate_invalidation

    affected = await propagate_invalidation(config, changed_node_id="S-12ab34cd")

Stale detection with propagation::

    from wheeler.provenance import detect_and_propagate_stale

    result = await detect_and_propagate_stale(config)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stability scoring
# ---------------------------------------------------------------------------

# Default stability by (label, tier).  Values encode epistemic trust:
# how much should downstream entities rely on this one remaining unchanged?

_STABILITY_DEFAULTS: dict[tuple[str, str], float] = {
    # Primary data and published references
    ("Dataset", "reference"):      1.0,
    ("Paper", "reference"):        0.9,
    ("Finding", "reference"):      0.8,
    ("Script", "reference"):       0.7,
    ("Document", "reference"):     0.7,
    ("Hypothesis", "reference"):   0.7,
    # Generated / in-progress work
    ("Dataset", "generated"):      0.7,
    ("Script", "generated"):       0.5,
    ("Finding", "generated"):      0.3,
    ("Hypothesis", "generated"):   0.3,
    ("Document", "generated"):     0.3,
    ("OpenQuestion", "generated"): 0.3,
    ("ResearchNote", "generated"): 0.3,
    ("Plan", "generated"):         0.3,
    ("Ledger", "generated"):       0.5,
}

_TIER_FALLBACK: dict[str, float] = {
    "reference": 0.8,
    "generated": 0.3,
}


def default_stability(label: str, tier: str = "generated") -> float:
    """Return the default stability score for a node type and tier.

    >>> default_stability("Paper", "reference")
    0.9
    >>> default_stability("Finding", "generated")
    0.3
    >>> default_stability("Script", "generated")
    0.5
    """
    return _STABILITY_DEFAULTS.get(
        (label, tier),
        _TIER_FALLBACK.get(tier, 0.3),
    )


# ---------------------------------------------------------------------------
# Invalidation propagation
# ---------------------------------------------------------------------------

@dataclass
class InvalidatedNode:
    """A node whose stability was reduced by upstream invalidation."""

    node_id: str
    label: str
    old_stability: float
    new_stability: float
    hops: int


# W3C PROV relationships that carry invalidation downstream.
# A change in the source means the target may now be stale.
PROVENANCE_RELS = [
    "USED",
    "WAS_GENERATED_BY",
    "WAS_DERIVED_FROM",
    "WAS_INFORMED_BY",
    "DEPENDS_ON",
]


async def propagate_invalidation(
    config: WheelerConfig,
    changed_node_id: str,
    new_stability: float | None = None,
    decay_factor: float = 0.8,
    max_hops: int = 10,
) -> list[InvalidatedNode]:
    """Mark a node as changed and propagate staleness to all downstream nodes.

    Traverses forward through PROV relationships (USED, WAS_GENERATED_BY,
    WAS_DERIVED_FROM, WAS_INFORMED_BY, DEPENDS_ON) and reduces stability
    with exponential decay per hop.

    Parameters
    ----------
    config
        Wheeler configuration (Neo4j connection details).
    changed_node_id
        The node whose content changed (e.g., a script was edited).
    new_stability
        Explicit stability for the changed node.  If None, halves the
        current stability.
    decay_factor
        Multiplicative decay per hop (default 0.8 = 20% reduction per hop).
    max_hops
        Maximum traversal depth (default 10).

    Returns
    -------
    list[InvalidatedNode]
        All downstream nodes whose stability was reduced.
    """
    from wheeler.graph.driver import get_async_driver

    driver = get_async_driver(config)
    project_tag = config.neo4j.project_tag
    now = datetime.now(timezone.utc).isoformat()

    affected: list[InvalidatedNode] = []

    # Build project filter clause (empty string if no namespace isolation)
    ptag_filter = ""
    ptag_params: dict[str, Any] = {}
    if project_tag:
        ptag_filter = "AND source._wheeler_project = $props.ptag "
        ptag_params["ptag"] = project_tag

    async with driver.session(database=config.neo4j.database) as session:
        # Step 1: Mark the source node as stale
        source_query = (
            "MATCH (source {id: $props.nid}) "
            f"WHERE true {ptag_filter}"
            "SET source.stale = true, "
            "    source.stale_since = $props.now, "
            "    source.stability = CASE "
            "        WHEN $props.explicit_stab IS NOT NULL "
            "        THEN $props.explicit_stab "
            "        ELSE coalesce(source.stability, 0.5) * 0.5 "
            "    END "
            "RETURN source.stability AS new_stab"
        )
        result = await session.run(
            source_query,
            parameters={"props": {
                "nid": changed_node_id,
                "now": now,
                "explicit_stab": new_stability,
                **ptag_params,
            }},
        )
        source_rec = await result.single()
        if source_rec is None:
            logger.warning(
                "propagate_invalidation: node %s not found",
                changed_node_id,
            )
            return []

        source_stability = source_rec["new_stab"]

        # Step 2: Find all downstream nodes and update in a single query.
        #
        # Downstream traversal follows PROV-DM edge directions:
        #   (Entity)-[:WAS_GENERATED_BY]->(Execution)-[:USED]->(Entity)
        #
        # All edges point toward the changed entity, so a variable-length
        # path through WAS_GENERATED_BY|USED edges finds all transitive
        # dependents.  Execution nodes are filtered out (intermediaries).
        #
        # Additionally, WAS_DERIVED_FROM edges link entities directly.
        downstream_ptag = ""
        if project_tag:
            downstream_ptag = (
                "AND dep._wheeler_project = $props.ptag "
            )

        # Each entity-to-entity hop traverses 2 edges (WAS_GENERATED_BY
        # + USED), so max_edges = max_hops * 2.
        max_edges = max_hops * 2

        downstream_query = (
            "MATCH (changed {id: $props.nid}) "
            # Path 1: transitive downstream through PROV execution chains.
            f"OPTIONAL MATCH path = (downstream)-[:WAS_GENERATED_BY|USED*2..{max_edges}]->(changed) "
            "WHERE downstream.id <> $props.nid "
            "AND NOT downstream:Execution "
            "WITH changed, collect(DISTINCT {node: downstream, hops: length(path)}) AS via_exec "
            # Path 2: entities derived directly from the changed entity
            f"OPTIONAL MATCH p = (derived)-[:WAS_DERIVED_FROM*1..{max_hops}]->(changed) "
            "WHERE derived.id <> $props.nid "
            "WITH via_exec, collect(DISTINCT {node: derived, hops: length(p)}) AS via_derived "
            "WITH via_exec + via_derived AS all_downstream "
            "UNWIND all_downstream AS item "
            "WITH item.node AS dep, item.hops AS hops "
            "WHERE dep IS NOT NULL "
            f"{downstream_ptag}"
            "WITH dep, min(hops) AS min_hops, "
            "  coalesce(dep.stability, 0.5) AS old_stab "
            "WITH dep, min_hops AS hops, old_stab, "
            "  $props.source_stab * ($props.decay ^ min_hops) AS decayed "
            "WHERE decayed < old_stab "
            "SET dep.stale = true, "
            "    dep.stale_since = $props.now, "
            "    dep.prev_stability = old_stab, "
            "    dep.stability = decayed "
            "RETURN dep.id AS nid, "
            "  labels(dep)[0] AS label, "
            "  old_stab, dep.stability AS new_stab, "
            "  hops "
            "ORDER BY hops, nid"
        )
        result = await session.run(
            downstream_query,
            parameters={"props": {
                "nid": changed_node_id,
                "source_stab": source_stability,
                "decay": decay_factor,
                "now": now,
                **ptag_params,
            }},
        )
        records = [r async for r in result]

        for rec in records:
            dep_id = rec["nid"]
            old_stab = rec["old_stab"]
            new_stab = rec["new_stab"]
            affected.append(InvalidatedNode(
                node_id=dep_id,
                label=rec["label"] or "Unknown",
                old_stability=old_stab,
                new_stability=new_stab,
                hops=rec["hops"],
            ))

            # Best-effort: update JSON change log for invalidated node
            try:
                from wheeler.knowledge.store import read_node, write_node
                from wheeler.models import ChangeEntry
                from pathlib import Path

                knowledge_path = Path(config.knowledge_path)
                node_model = read_node(knowledge_path, dep_id)
                node_model.change_log.append(ChangeEntry(
                    timestamp=now,
                    action="invalidated",
                    changes={
                        "stale": [False, True],
                        "stability": [round(old_stab, 4), round(new_stab, 4)],
                    },
                    actor="provenance_system",
                    reason=f"upstream change in {changed_node_id}",
                ))
                node_model.stale = True
                node_model.stale_since = now
                node_model.stability = new_stab
                write_node(knowledge_path, node_model)
            except (FileNotFoundError, Exception):
                pass  # pre-migration node or file error

    logger.info(
        "Invalidation from %s: %d downstream nodes affected",
        changed_node_id,
        len(affected),
    )
    return affected


async def clear_stale(
    config: WheelerConfig,
    node_id: str,
    new_stability: float | None = None,
) -> bool:
    """Clear the stale flag on a node after re-validation.

    Optionally set a new stability score (e.g., after re-running a script).
    """
    from wheeler.graph.driver import get_async_driver

    driver = get_async_driver(config)
    project_tag = config.neo4j.project_tag

    set_parts = [
        "n.stale = false",
        "n.stale_since = null",
        "n.prev_stability = null",
    ]
    props: dict[str, Any] = {"nid": node_id}

    if new_stability is not None:
        set_parts.append("n.stability = $props.new_stab")
        props["new_stab"] = new_stability

    ptag_filter = ""
    if project_tag:
        ptag_filter = "WHERE n._wheeler_project = $props.ptag "
        props["ptag"] = project_tag

    set_clause = ", ".join(set_parts)
    query = (
        f"MATCH (n {{id: $props.nid}}) "
        f"{ptag_filter}"
        f"SET {set_clause} "
        f"RETURN n.id"
    )

    async with driver.session(database=config.neo4j.database) as session:
        result = await session.run(query, parameters={"props": props})
        record = await result.single()

    if record:
        logger.info("Cleared stale flag on %s", node_id)
        return True
    return False


# ---------------------------------------------------------------------------
# Stale detection with propagation (extends graph/provenance.py)
# ---------------------------------------------------------------------------

async def detect_and_propagate_stale(config: WheelerConfig) -> dict:
    """Detect stale scripts and propagate invalidation downstream.

    Finds Script nodes whose file hash no longer matches disk, marks them
    stale, then propagates reduced stability through all downstream
    entities via PROV relationships.

    This is the function Wheeler's ``detect_stale`` MCP tool should call.
    """
    from wheeler.graph.provenance import detect_stale_scripts

    stale_scripts = await detect_stale_scripts(config)
    all_affected: list[InvalidatedNode] = []

    for stale in stale_scripts:
        affected = await propagate_invalidation(
            config,
            changed_node_id=stale.node_id,
            new_stability=0.3,
        )
        all_affected.extend(affected)

    return {
        "stale_scripts": len(stale_scripts),
        "downstream_affected": len(all_affected),
        "details": {
            "scripts": [
                {
                    "id": s.node_id,
                    "path": s.path,
                    "stored_hash": s.stored_hash[:12],
                    "current_hash": s.current_hash[:12],
                }
                for s in stale_scripts
            ],
            "invalidated": [
                {
                    "id": n.node_id,
                    "label": n.label,
                    "stability": f"{n.old_stability:.2f} -> {n.new_stability:.2f}",
                    "hops": n.hops,
                }
                for n in all_affected
            ],
        },
    }
