"""Backfill embeddings for existing graph nodes.

Fetches all nodes with text fields from the graph and adds embeddings
for any that are missing from the store.
"""

from __future__ import annotations

import logging

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


async def backfill_embeddings(
    nodes_by_label: dict[str, list[dict[str, str]]],
    store: EmbeddingStore,
) -> int:
    """Add embeddings for nodes that don't have them yet.

    Args:
        nodes_by_label: ``{label: [node_dicts]}`` where each dict has
            ``"id"`` and the relevant text field.
        store: EmbeddingStore to add embeddings to.

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
            text = node.get(text_field, "")
            if node_id and text and not store.has(node_id):
                store.add(node_id, label, text)
                added += 1
    logger.info("Backfilled %d new embeddings", added)
    return added
