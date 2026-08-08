"""Core file I/O for reading/writing JSON knowledge files.

Each knowledge node is persisted as a single ``{node_id}.json`` file inside
the configured *knowledge_path* directory.  Writes are atomic (tmp + rename)
to avoid partial-write corruption.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from wheeler.models import KNOWLEDGE_NODE_ADAPTER, LABEL_TO_PREFIX, KnowledgeNode, NodeBase

logger = logging.getLogger(__name__)


def _writer_tmp(target: Path) -> Path:
    """A staging path unique to this writer.

    The tmp name used to be a fixed function of the node id
    (``target.with_suffix(".json.tmp")``), so every concurrent writer of one
    node staged into the SAME file and then each renamed it. The rename is
    atomic, but the bytes being renamed could be a blend of two payloads, which
    defeats the whole point of tmp+rename. Two Wheeler sessions writing one node
    is an ordinary occurrence, not an edge case.

    The suffix stays LAST so the file remains invisible to every inventory:
    ``store.list_nodes`` and ``mcp_core``'s health count glob ``*.json``, and
    ``consistency.py`` globs ``*.json`` and ``*.md`` and derives node identity
    from ``Path.stem``. A name like ``F-3a2b.tmp.json`` would match all three
    and manufacture phantom drift.
    """
    return target.with_name(f"{target.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")


def write_node(knowledge_path: Path, model: NodeBase) -> Path:
    """Write a node model to a JSON file.  Atomic write (tmp + rename).

    Creates *knowledge_path* directory if it doesn't exist.
    Returns the path to the written file.
    """
    knowledge_path.mkdir(parents=True, exist_ok=True)

    target = knowledge_path / model.file_name
    tmp = _writer_tmp(target)

    data = model.model_dump_json(indent=2)
    try:
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)

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
    tmp = _writer_tmp(target)

    try:
        tmp.write_text(markdown, encoding="utf-8")
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)

    logger.info("Wrote synthesis %s -> %s", node_id, target)
    return target
