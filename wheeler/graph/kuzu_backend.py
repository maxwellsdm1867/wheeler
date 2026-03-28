"""Kuzu graph database backend for Wheeler.

Kuzu is an embedded graph database — no server needed. The database
lives in a directory on disk (default ``.kuzu/``). Kuzu's API is
synchronous, so all calls are wrapped with ``asyncio.to_thread``.

Kuzu Cypher dialect differences from Neo4j:
- Explicit ``CREATE NODE TABLE`` / ``CREATE REL TABLE`` (no auto-schema)
- Primary keys declared in the table definition
- ``CREATE REL TABLE GROUP`` allows one relationship type across many label pairs
- No ``CREATE CONSTRAINT`` / ``CREATE INDEX`` — PKs are auto-indexed
- Parameters via ``conn.execute(query, parameters={...})``
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

try:
    import kuzu
except ImportError:
    kuzu = None  # type: ignore[assignment]

from wheeler.graph.backend import GraphBackend
from wheeler.graph.schema import (
    ALLOWED_RELATIONSHIPS,
    LABEL_TO_PREFIX,
    NODE_LABELS,
    generate_node_id,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node table schemas
# ---------------------------------------------------------------------------

# Each entry: label -> list of (column_name, kuzu_type)
# The first column is always the primary key (id STRING).
NODE_TABLE_SCHEMAS: dict[str, list[tuple[str, str]]] = {
    "Finding": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("description", "STRING"),
        ("confidence", "DOUBLE"),
        ("date", "STRING"),
        ("tier", "STRING"),
    ],
    "Hypothesis": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("statement", "STRING"),
        ("status", "STRING"),
        ("date", "STRING"),
        ("tier", "STRING"),
    ],
    "OpenQuestion": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("question", "STRING"),
        ("priority", "INT64"),
        ("date_added", "STRING"),
        ("tier", "STRING"),
    ],
    "Dataset": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("path", "STRING"),
        ("type", "STRING"),
        ("description", "STRING"),
        ("date_added", "STRING"),
        ("tier", "STRING"),
    ],
    "Paper": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("authors", "STRING"),
        ("doi", "STRING"),
        ("year", "INT64"),
        ("date_added", "STRING"),
        ("tier", "STRING"),
    ],
    "Document": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("path", "STRING"),
        ("section", "STRING"),
        ("status", "STRING"),
        ("date", "STRING"),
        ("updated", "STRING"),
        ("tier", "STRING"),
    ],
    "Analysis": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("script_path", "STRING"),
        ("script_hash", "STRING"),
        ("language", "STRING"),
        ("language_version", "STRING"),
        ("parameters", "STRING"),
        ("output_path", "STRING"),
        ("output_hash", "STRING"),
        ("executed_at", "STRING"),
        ("date", "STRING"),
        ("tier", "STRING"),
    ],
    "Plan": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("status", "STRING"),
        ("date", "STRING"),
        ("tier", "STRING"),
    ],
    "ResearchNote": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("content", "STRING"),
        ("context", "STRING"),
        ("date", "STRING"),
        ("tier", "STRING"),
    ],
    "Ledger": [
        ("id", "STRING"),
        ("title", "STRING"),
        ("file_path", "STRING"),
        ("mode", "STRING"),
        ("prompt_summary", "STRING"),
        ("ungrounded", "BOOL"),
        ("pass_rate", "DOUBLE"),
        ("date", "STRING"),
        ("tier", "STRING"),
    ],
}

# Verify every NODE_LABEL has a schema entry
assert set(NODE_TABLE_SCHEMAS) == set(NODE_LABELS), (
    f"NODE_TABLE_SCHEMAS keys {set(NODE_TABLE_SCHEMAS)} != NODE_LABELS {set(NODE_LABELS)}"
)


def _column_names(label: str) -> list[str]:
    """Return column names for a node table (excluding 'id')."""
    return [col for col, _ in NODE_TABLE_SCHEMAS[label] if col != "id"]


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


class KuzuBackend(GraphBackend):
    """Kuzu embedded graph database backend.

    Parameters
    ----------
    db_path:
        Directory where Kuzu stores its database files.
    """

    def __init__(self, db_path: str = ".kuzu") -> None:
        if kuzu is None:
            raise ImportError(
                "kuzu is required for the Kuzu backend. "
                "Install with: pip install 'wheeler[kuzu]'"
            )
        self._db_path = Path(db_path)
        self._db: kuzu.Database | None = None
        self._conn: kuzu.Connection | None = None

    # -- helpers --

    def _get_conn(self) -> kuzu.Connection:
        if self._conn is None:
            raise RuntimeError("KuzuBackend not initialized — call initialize() first")
        return self._conn

    def _ensure_db(self) -> None:
        """Create Database and Connection objects if needed."""
        if self._db is None:
            # Kuzu creates the database directory itself.
            # Only ensure the *parent* exists.
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = kuzu.Database(str(self._db_path))
            self._conn = kuzu.Connection(self._db)

    def _ensure_column(self, table: str, col: str, col_type: str) -> None:
        """Add a column to an existing table if it doesn't exist."""
        conn = self._get_conn()
        try:
            # Try to query the column to see if it exists
            conn.execute(f"MATCH (n:{table}) RETURN n.{col} LIMIT 1")
        except Exception:
            # Column doesn't exist, add it
            try:
                conn.execute(f"ALTER TABLE {table} ADD {col} {col_type} DEFAULT ''")
                logger.info("Added column %s to %s", col, table)
            except Exception as exc:
                logger.warning("Could not add column %s to %s: %s", col, table, exc)

    def _table_exists(self, table_name: str) -> bool:
        """Check if a node or rel table already exists."""
        conn = self._get_conn()
        try:
            result = conn.execute(
                "CALL show_tables() RETURN *"
            )
            # Columns: [id, name, type, database name, comment]
            while result.has_next():
                row = result.get_next()
                if row[1] == table_name:
                    return True
        except Exception:
            pass
        return False

    # -- lifecycle --

    async def initialize(self) -> None:
        """Create all node and relationship tables."""
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        self._ensure_db()
        conn = self._get_conn()

        # Create node tables
        for label, columns in NODE_TABLE_SCHEMAS.items():
            if self._table_exists(label):
                logger.debug("Node table %s already exists", label)
                continue
            col_defs = ", ".join(f"{name} {typ}" for name, typ in columns)
            stmt = f"CREATE NODE TABLE {label} ({col_defs}, PRIMARY KEY(id))"
            logger.info("Creating node table: %s", label)
            conn.execute(stmt)

        # Create relationship table groups.
        # Each ALLOWED_RELATIONSHIP gets a REL TABLE GROUP covering all
        # label pairs (permissive — any node type can connect to any other).
        for rel_type in ALLOWED_RELATIONSHIPS:
            if self._table_exists(rel_type):
                logger.debug("Rel table %s already exists", rel_type)
                continue
            pairs = ", ".join(
                f"FROM {src} TO {tgt}"
                for src in NODE_LABELS
                for tgt in NODE_LABELS
            )
            stmt = f"CREATE REL TABLE GROUP {rel_type} ({pairs})"
            logger.info("Creating rel table group: %s", rel_type)
            conn.execute(stmt)

        # Add new columns to existing tables that lack them (migration)
        for label in NODE_TABLE_SCHEMAS:
            if not self._table_exists(label):
                continue
            # Check if title/file_path columns exist, add if missing
            self._ensure_column(label, "title", "STRING")
            self._ensure_column(label, "file_path", "STRING")

        logger.info("Kuzu schema initialized at %s", self._db_path)

    async def close(self) -> None:
        """Release the Kuzu connection."""
        # Kuzu connections are lightweight; just drop references.
        self._conn = None
        self._db = None

    # -- node CRUD --

    async def create_node(self, label: str, properties: dict) -> str:
        return await asyncio.to_thread(self._create_node_sync, label, properties)

    def _create_node_sync(self, label: str, properties: dict) -> str:
        conn = self._get_conn()

        # Generate ID if not provided
        props = dict(properties)
        if "id" not in props:
            prefix = LABEL_TO_PREFIX.get(label)
            if not prefix:
                raise ValueError(f"Unknown label: {label}")
            props["id"] = generate_node_id(prefix)

        node_id = props["id"]
        schema_cols = {col for col, _ in NODE_TABLE_SCHEMAS[label]}

        # Build property assignments for columns that exist in the schema
        set_cols = [col for col in schema_cols if col in props]

        stmt = f"CREATE (:{label} {{{', '.join(f'{c}: ${c}' for c in set_cols)}}})"

        params = {col: props[col] for col in set_cols}
        conn.execute(stmt, parameters=params)
        logger.debug("Created %s node %s", label, node_id)
        return node_id

    async def get_node(self, label: str, node_id: str) -> dict | None:
        return await asyncio.to_thread(self._get_node_sync, label, node_id)

    def _get_node_sync(self, label: str, node_id: str) -> dict | None:
        conn = self._get_conn()
        stmt = f"MATCH (n:{label} {{id: $id}}) RETURN n.*"
        result = conn.execute(stmt, parameters={"id": node_id})

        if not result.has_next():
            return None

        row = result.get_next()
        col_names = result.get_column_names()

        # Column names come back as "n.prop" — strip the prefix
        props: dict = {}
        for col_name, value in zip(col_names, row):
            key = col_name.split(".", 1)[-1] if "." in col_name else col_name
            props[key] = value
        return props

    async def update_node(
        self, label: str, node_id: str, properties: dict
    ) -> bool:
        return await asyncio.to_thread(
            self._update_node_sync, label, node_id, properties
        )

    def _update_node_sync(
        self, label: str, node_id: str, properties: dict
    ) -> bool:
        conn = self._get_conn()

        # Don't allow updating the id
        props = {k: v for k, v in properties.items() if k != "id"}
        if not props:
            return False

        set_clauses = ", ".join(f"n.{k} = ${k}" for k in props)
        stmt = f"MATCH (n:{label} {{id: $id}}) SET {set_clauses} RETURN n.id"
        params = {"id": node_id, **props}
        result = conn.execute(stmt, parameters=params)

        return result.has_next()

    async def delete_node(self, label: str, node_id: str) -> bool:
        return await asyncio.to_thread(self._delete_node_sync, label, node_id)

    def _delete_node_sync(self, label: str, node_id: str) -> bool:
        conn = self._get_conn()

        # Check existence first
        check = conn.execute(
            f"MATCH (n:{label} {{id: $id}}) RETURN n.id",
            parameters={"id": node_id},
        )
        if not check.has_next():
            return False

        # Detach delete removes the node and all its relationships
        conn.execute(
            f"MATCH (n:{label} {{id: $id}}) DETACH DELETE n",
            parameters={"id": node_id},
        )
        logger.debug("Deleted %s node %s", label, node_id)
        return True

    # -- relationships --

    async def create_relationship(
        self,
        src_label: str,
        src_id: str,
        rel_type: str,
        tgt_label: str,
        tgt_id: str,
    ) -> bool:
        return await asyncio.to_thread(
            self._create_relationship_sync,
            src_label, src_id, rel_type, tgt_label, tgt_id,
        )

    def _create_relationship_sync(
        self,
        src_label: str,
        src_id: str,
        rel_type: str,
        tgt_label: str,
        tgt_id: str,
    ) -> bool:
        conn = self._get_conn()
        stmt = (
            f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
            f"CREATE (a)-[:{rel_type}]->(b)"
        )
        try:
            conn.execute(stmt, parameters={"src": src_id, "tgt": tgt_id})
        except Exception as exc:
            logger.warning(
                "create_relationship failed %s -[%s]-> %s: %s",
                src_id, rel_type, tgt_id, exc,
            )
            return False
        logger.debug("Linked %s -[%s]-> %s", src_id, rel_type, tgt_id)
        return True

    # -- queries --

    async def query_nodes(
        self,
        label: str,
        filters: dict | None = None,
        order_by: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        return await asyncio.to_thread(
            self._query_nodes_sync, label, filters, order_by, limit,
        )

    def _query_nodes_sync(
        self,
        label: str,
        filters: dict | None = None,
        order_by: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        conn = self._get_conn()

        where_parts: list[str] = []
        params: dict = {}
        if filters:
            for key, value in filters.items():
                where_parts.append(f"n.{key} = ${key}")
                params[key] = value

        where_clause = ""
        if where_parts:
            where_clause = " WHERE " + " AND ".join(where_parts)

        order_clause = ""
        if order_by:
            order_clause = f" ORDER BY n.{order_by} DESC"

        stmt = f"MATCH (n:{label}){where_clause} RETURN n.*{order_clause} LIMIT {limit}"
        result = conn.execute(stmt, parameters=params)

        col_names = result.get_column_names()
        rows: list[dict] = []
        while result.has_next():
            row = result.get_next()
            props: dict = {}
            for col_name, value in zip(col_names, row):
                key = col_name.split(".", 1)[-1] if "." in col_name else col_name
                props[key] = value
            rows.append(props)
        return rows

    async def count_all(self) -> dict[str, int]:
        return await asyncio.to_thread(self._count_all_sync)

    def _count_all_sync(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        conn = self._get_conn()
        for label in NODE_LABELS:
            result = conn.execute(f"MATCH (n:{label}) RETURN count(n)")
            if result.has_next():
                counts[label] = result.get_next()[0]
            else:
                counts[label] = 0
        return counts

    # -- raw cypher --

    async def run_cypher(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        return await asyncio.to_thread(self._run_cypher_sync, query, params)

    def _run_cypher_sync(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        conn = self._get_conn()
        result = conn.execute(query, parameters=params or {})
        col_names = result.get_column_names()
        rows: list[dict] = []
        while result.has_next():
            row = result.get_next()
            d: dict = {}
            for col_name, value in zip(col_names, row):
                # Strip "n." prefix from column names if present
                key = col_name.split(".", 1)[-1] if "." in col_name else col_name
                d[key] = value
            rows.append(d)
        return rows
