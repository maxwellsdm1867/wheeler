"""Migration tool: export existing graph nodes to knowledge JSON files."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from wheeler.graph.backend import GraphBackend
from wheeler.models import (
    LABEL_TO_PREFIX, NODE_LABELS, NodeBase, model_for_label, title_for_node
)
from wheeler.knowledge.store import write_node, node_exists

logger = logging.getLogger(__name__)


@dataclass
class MigrationReport:
    migrated: int = 0
    skipped: int = 0
    errors: int = 0
    details: list[str] = field(default_factory=list)


async def migrate(
    backend: GraphBackend,
    knowledge_path: Path,
    dry_run: bool = False,
) -> MigrationReport:
    """Migrate all graph nodes to filesystem-backed format.

    For each node:
    1. Read all properties from graph
    2. Build Pydantic model
    3. Write JSON file to knowledge/
    4. Update graph node with file_path and title

    Idempotent: skips nodes that already have a JSON file.
    """
    report = MigrationReport()

    for label in NODE_LABELS:
        nodes = await backend.query_nodes(label, limit=10000)
        prefix = LABEL_TO_PREFIX.get(label, "?")

        for node_data in nodes:
            node_id = node_data.get("id", "")
            if not node_id:
                report.errors += 1
                report.details.append(f"Node in {label} with no id, skipped")
                continue

            # Skip if file already exists
            if node_exists(knowledge_path, node_id):
                report.skipped += 1
                continue

            if dry_run:
                report.details.append(f"Would migrate {node_id}")
                report.migrated += 1
                continue

            try:
                # Build Pydantic model from graph data
                model = _graph_data_to_model(label, node_data)

                # Write file
                write_node(knowledge_path, model)

                # Update graph node with file_path and title
                title = title_for_node(model)
                file_path = str(knowledge_path / model.file_name)
                await backend.update_node(label, node_id, {
                    "file_path": file_path,
                    "title": title,
                })

                report.migrated += 1
            except Exception as exc:
                report.errors += 1
                report.details.append(f"Failed to migrate {node_id}: {exc}")
                logger.warning("Migration failed for %s: %s", node_id, exc)

    return report


def _graph_data_to_model(label: str, data: dict) -> NodeBase:
    """Convert graph node properties to the corresponding Pydantic model."""
    model_cls = model_for_label(label)

    # Map graph property names to model field names
    props = dict(data)

    # Dataset uses "type" in graph but "data_type" in model -- must remap
    # BEFORE we overwrite props["type"] with the label discriminator.
    if label == "Dataset" and "type" in props and props["type"] != "Dataset":
        props["data_type"] = props["type"]

    props["type"] = label

    # Handle date field mapping:
    # Graph uses "date" or "date_added", model uses "created"
    if "created" not in props or not props["created"]:
        props["created"] = props.get("date", "") or props.get("date_added", "")
    if "updated" not in props or not props["updated"]:
        props["updated"] = props.get("created", "")

    return model_cls.model_validate(props)
