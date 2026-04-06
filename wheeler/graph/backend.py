"""Abstract graph database backend.

Defines the interface that graph backends (Neo4j) must
implement. Each backend provides node CRUD, relationship creation, and
query operations over the Wheeler knowledge graph.

Factory function ``get_backend`` returns the configured backend instance.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)


class GraphBackend(ABC):
    """Abstract graph database backend.

    All methods are async. Backends that use sync drivers
    should wrap blocking calls with ``asyncio.to_thread``.
    """

    # --- Lifecycle ---

    @abstractmethod
    async def initialize(self) -> None:
        """Create tables, constraints, and indexes.

        Safe to call multiple times (idempotent).
        """

    @abstractmethod
    async def close(self) -> None:
        """Release resources (connections, file handles)."""

    # --- Node CRUD ---

    @abstractmethod
    async def create_node(self, label: str, properties: dict) -> str:
        """Create a node with the given label and properties.

        The ``id`` key in *properties* is the node's unique identifier.
        If not supplied, the backend should generate one.

        Returns the node ID.
        """

    @abstractmethod
    async def get_node(self, label: str, node_id: str) -> dict | None:
        """Fetch a single node by label and ID.

        Returns the node's properties as a dict, or ``None`` if not found.
        """

    @abstractmethod
    async def update_node(
        self, label: str, node_id: str, properties: dict
    ) -> bool:
        """Update properties on an existing node.

        Only the keys present in *properties* are changed; other properties
        are preserved.

        Returns ``True`` if the node was found and updated.
        """

    @abstractmethod
    async def delete_node(self, label: str, node_id: str) -> bool:
        """Delete a node by label and ID.

        Returns ``True`` if the node existed and was deleted.
        """

    # --- Relationships ---

    @abstractmethod
    async def create_relationship(
        self,
        src_label: str,
        src_id: str,
        rel_type: str,
        tgt_label: str,
        tgt_id: str,
    ) -> bool:
        """Create a directed relationship between two existing nodes.

        Returns ``True`` if both nodes were found and the relationship
        was created.
        """

    # --- Queries ---

    @abstractmethod
    async def query_nodes(
        self,
        label: str,
        filters: dict | None = None,
        order_by: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Query nodes of the given label with optional filters.

        Parameters
        ----------
        label:
            Node label to query (e.g. ``"Finding"``).
        filters:
            Property equality filters (e.g. ``{"status": "open"}``).
        order_by:
            Property name to sort by (descending). ``None`` for default order.
        limit:
            Maximum number of results.
        """

    @abstractmethod
    async def count_all(self) -> dict[str, int]:
        """Return node counts for every label. ``{label: count}``."""

    # --- Raw Cypher ---

    @abstractmethod
    async def run_cypher(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        """Execute a Cypher query and return results as a list of dicts.

        Used by query tools that need filtering/ordering beyond what
        ``query_nodes`` supports (e.g. keyword CONTAINS, complex JOINs).
        """


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_backend(config: WheelerConfig) -> GraphBackend:
    """Return the configured graph backend instance (Neo4j)."""
    from wheeler.graph.neo4j_backend import Neo4jBackend

    return Neo4jBackend(config)
