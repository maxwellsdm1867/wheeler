"""Backfill embeddings for existing graph nodes.

Fetches all nodes with text fields from the graph and adds embeddings
for any that are missing from the store.  When a ``knowledge_path`` is
provided, the backfill reads full content from JSON knowledge files,
falling back to the graph-supplied dict when a file doesn't exist
(pre-migration nodes).
"""

from __future__ import annotations

import logging
from pathlib import Path

from wheeler.search.embeddings import EmbeddingStore

logger = logging.getLogger(__name__)

# Maps node labels to their primary text field for embedding.
TEXT_FIELDS: dict[str, str] = {
    "Finding": "description",
    "Hypothesis": "statement",
    "OpenQuestion": "question",
    "Paper": "title",
    "Dataset": "description",
    "Document": "title",
}


def _text_from_knowledge_file(
    knowledge_path: Path | None, node_id: str, label: str
) -> str | None:
    """Try to read the primary text field from a knowledge file.

    Returns the text string on success, or ``None`` on any failure so the
    caller can fall back to graph data.
    """
    if knowledge_path is None:
        return None
    text_field = TEXT_FIELDS.get(label)
    if not text_field:
        return None
    try:
        from wheeler.knowledge.store import read_node

        model = read_node(knowledge_path, node_id)
        return getattr(model, text_field, None) or None
    except FileNotFoundError:
        return None
    except Exception:
        logger.debug(
            "Failed to read knowledge file for %s during backfill", node_id, exc_info=True
        )
        return None


async def backfill_embeddings(
    nodes_by_label: dict[str, list[dict[str, str]]],
    store: EmbeddingStore,
    knowledge_path: Path | None = None,
) -> int:
    """Add embeddings for nodes that don't have them yet.

    Args:
        nodes_by_label: ``{label: [node_dicts]}`` where each dict has
            ``"id"`` and the relevant text field.
        store: EmbeddingStore to add embeddings to.
        knowledge_path: Optional path to ``knowledge/`` directory.  When
            provided, each node's text is read from its JSON file first,
            falling back to the dict data when the file doesn't exist.

    Returns:
        Number of new embeddings added.
    """
    added = 0
    for label, nodes in nodes_by_label.items():
        text_field = TEXT_FIELDS.get(label)
        if not text_field:
            continue
        for node in nodes:
            node_id = node.get("id", "")
            if not node_id or store.has(node_id):
                continue

            # Try knowledge file first, fall back to graph dict
            text = _text_from_knowledge_file(knowledge_path, node_id, label)
            if not text:
                text = node.get(text_field, "")

            if text:
                store.add(node_id, label, text)
                added += 1
    logger.info("Backfilled %d new embeddings", added)
    return added
