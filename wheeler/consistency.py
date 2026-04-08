"""Consistency checker for Wheeler's triple-write layers.

Compares inventories across graph (Neo4j), knowledge files (JSON),
and synthesis files (markdown) to detect drift and optionally repair it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)

# Synthesis index files that are NOT node files
_SYNTHESIS_INDEX_FILES = frozenset({"INDEX", "OPEN_QUESTIONS", "EVIDENCE_MAP"})


@dataclass
class ConsistencyReport:
    """Result of comparing the three storage layers."""

    graph_only: list[str] = field(default_factory=list)        # in graph, not in JSON
    json_only: list[str] = field(default_factory=list)         # in JSON, not in graph
    synthesis_missing: list[str] = field(default_factory=list)  # in JSON, no synthesis
    synthesis_orphaned: list[str] = field(default_factory=list)  # synthesis exists, no JSON
    total_graph: int = 0
    total_json: int = 0
    total_synthesis: int = 0


async def check_consistency(config: WheelerConfig) -> ConsistencyReport:
    """Compare graph, knowledge/, and synthesis/ inventories."""
    from wheeler.tools.graph_tools import _get_backend

    backend = await _get_backend(config)

    # Graph inventory
    try:
        records = await backend.run_cypher("MATCH (n) RETURN n.id AS id")
        graph_ids = {r["id"] for r in records if r.get("id")}
    except Exception as exc:
        logger.warning("Cannot query graph for consistency check: %s", exc)
        graph_ids = set()

    # JSON inventory
    knowledge_dir = Path(config.knowledge_path)
    if knowledge_dir.is_dir():
        json_ids = {f.stem for f in knowledge_dir.glob("*.json")}
    else:
        json_ids = set()

    # Synthesis inventory (exclude index files)
    synthesis_dir = Path(config.synthesis_path)
    if synthesis_dir.is_dir():
        synth_ids = {
            f.stem for f in synthesis_dir.glob("*.md")
            if f.stem not in _SYNTHESIS_INDEX_FILES
        }
    else:
        synth_ids = set()

    return ConsistencyReport(
        graph_only=sorted(graph_ids - json_ids),
        json_only=sorted(json_ids - graph_ids),
        synthesis_missing=sorted(json_ids - synth_ids),
        synthesis_orphaned=sorted(synth_ids - json_ids),
        total_graph=len(graph_ids),
        total_json=len(json_ids),
        total_synthesis=len(synth_ids),
    )


async def repair_consistency(
    config: WheelerConfig,
    report: ConsistencyReport,
    dry_run: bool = True,
) -> dict:
    """Repair detected drift between layers. Returns action log.

    Repairs:
    - synthesis_missing: read JSON, render markdown, write synthesis file
    - synthesis_orphaned: delete orphaned synthesis files
    - graph_only: warn only (regenerating JSON from graph is complex)
    - json_only: warn only (may be pre-migration or graph delete failed)
    """
    actions: list[dict] = []

    # synthesis_missing: regenerate from JSON
    for node_id in report.synthesis_missing:
        if dry_run:
            actions.append({"node_id": node_id, "action": "regenerate_synthesis", "dry_run": True})
            continue
        try:
            from wheeler.knowledge.store import read_node, write_synthesis
            from wheeler.knowledge.render import render_synthesis

            knowledge_dir = Path(config.knowledge_path)
            synthesis_dir = Path(config.synthesis_path)
            model = read_node(knowledge_dir, node_id)
            markdown = render_synthesis(model)
            write_synthesis(synthesis_dir, node_id, markdown)
            actions.append({"node_id": node_id, "action": "regenerate_synthesis", "status": "ok"})
        except Exception as exc:
            actions.append({"node_id": node_id, "action": "regenerate_synthesis", "status": "error", "error": str(exc)})

    # synthesis_orphaned: delete stale markdown
    for node_id in report.synthesis_orphaned:
        if dry_run:
            actions.append({"node_id": node_id, "action": "delete_orphaned_synthesis", "dry_run": True})
            continue
        try:
            path = Path(config.synthesis_path) / f"{node_id}.md"
            if path.exists():
                path.unlink()
            actions.append({"node_id": node_id, "action": "delete_orphaned_synthesis", "status": "ok"})
        except Exception as exc:
            actions.append({"node_id": node_id, "action": "delete_orphaned_synthesis", "status": "error", "error": str(exc)})

    # graph_only and json_only: warn only
    for node_id in report.graph_only:
        actions.append({"node_id": node_id, "action": "warn_graph_only"})
    for node_id in report.json_only:
        actions.append({"node_id": node_id, "action": "warn_json_only"})

    return {"dry_run": dry_run, "actions": actions, "total": len(actions)}
