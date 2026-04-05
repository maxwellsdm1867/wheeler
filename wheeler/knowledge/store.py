"""Core file I/O for reading/writing JSON knowledge files.

Each knowledge node is persisted as a single ``{node_id}.json`` file inside
the configured *knowledge_path* directory.  Writes are atomic (tmp + rename)
to avoid partial-write corruption.
"""

from __future__ import annotations

import logging
from pathlib import Path

from wheeler.models import KNOWLEDGE_NODE_ADAPTER, LABEL_TO_PREFIX, KnowledgeNode, NodeBase

logger = logging.getLogger(__name__)


def write_node(knowledge_path: Path, model: NodeBase) -> Path:
    """Write a node model to a JSON file.  Atomic write (tmp + rename).

    Creates *knowledge_path* directory if it doesn't exist.
    Returns the path to the written file.
    """
    knowledge_path.mkdir(parents=True, exist_ok=True)

    target = knowledge_path / model.file_name
    tmp = target.with_suffix(".json.tmp")

    data = model.model_dump_json(indent=2)
    tmp.write_text(data, encoding="utf-8")
    tmp.rename(target)

    logger.info("Wrote node %s -> %s", model.id, target)
    return target


def read_node(knowledge_path: Path, node_id: str) -> KnowledgeNode:
    """Read a node from its JSON file and return the typed Pydantic model.

    Uses the discriminated union so the returned object is the correct
    concrete model type (e.g. ``FindingModel``, ``HypothesisModel``).

    Raises ``FileNotFoundError`` if the file doesn't exist.
    """
    path = knowledge_path / f"{node_id}.json"
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise FileNotFoundError(f"No knowledge file for node {node_id}: {path}") from None
    node: KnowledgeNode = KNOWLEDGE_NODE_ADAPTER.validate_json(data)
    logger.debug("Read node %s from %s", node_id, path)
    return node


def list_nodes(
    knowledge_path: Path, type_filter: str | None = None
) -> list[KnowledgeNode]:
    """List all knowledge nodes, optionally filtered by type.

    *type_filter* is a label string like ``"Finding"``, ``"Hypothesis"``, etc.
    The label is mapped to its filename prefix via ``LABEL_TO_PREFIX`` (e.g.
    ``Finding -> F-``) so only matching files are read.

    If the directory doesn't exist, returns an empty list.
    """
    if not knowledge_path.is_dir():
        return []

    json_files = sorted(knowledge_path.glob("*.json"))

    if type_filter is not None:
        prefix = LABEL_TO_PREFIX.get(type_filter)
        if prefix is None:
            logger.warning("Unknown type_filter %r -- returning empty list", type_filter)
            return []
        file_prefix = f"{prefix}-"
        json_files = [f for f in json_files if f.name.startswith(file_prefix)]

    nodes: list[KnowledgeNode] = []
    for path in json_files:
        try:
            data = path.read_bytes()
            node = KNOWLEDGE_NODE_ADAPTER.validate_json(data)
            nodes.append(node)
        except Exception:
            logger.warning("Skipping unreadable knowledge file: %s", path, exc_info=True)

    logger.debug(
        "Listed %d node(s) from %s (filter=%s)", len(nodes), knowledge_path, type_filter
    )
    return nodes


def delete_node(knowledge_path: Path, node_id: str) -> bool:
    """Delete a node's JSON file.  Returns ``True`` if the file existed."""
    path = knowledge_path / f"{node_id}.json"
    if path.exists():
        path.unlink()
        logger.info("Deleted node %s (%s)", node_id, path)
        return True
    return False


def node_exists(knowledge_path: Path, node_id: str) -> bool:
    """Check if a node's JSON file exists."""
    return (knowledge_path / f"{node_id}.json").is_file()


def write_synthesis(synthesis_path: Path, node_id: str, markdown: str) -> Path:
    """Write a synthesis markdown file.  Atomic write (tmp + rename).

    Creates *synthesis_path* directory if it doesn't exist.
    Returns the path to the written file.
    """
    synthesis_path.mkdir(parents=True, exist_ok=True)

    target = synthesis_path / f"{node_id}.md"
    tmp = target.with_suffix(".md.tmp")

    tmp.write_text(markdown, encoding="utf-8")
    tmp.rename(target)

    logger.info("Wrote synthesis %s -> %s", node_id, target)
    return target
