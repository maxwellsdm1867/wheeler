"""Neo4j graph database backend for Wheeler.

Thin adapter that maps the :class:`GraphBackend` ABC methods to Cypher
queries executed via the existing singleton async driver in
:mod:`wheeler.graph.driver`.

Supports per-project isolation on Community Edition via a
``_wheeler_project`` property on every node.  When
``config.neo4j.project_tag`` is non-empty all MATCH/CREATE queries
are scoped to that tag.  Enterprise/Aura users get real database
isolation and the tag is left empty.
"""

from __future__ import annotations

import logging
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.graph.backend import GraphBackend
from wheeler.graph.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    is_deterministic_neo4j_error,
)
from wheeler.graph.schema import (
    LABEL_TO_PREFIX,
    generate_node_id,
)

logger = logging.getLogger(__name__)

# Prefix used to flatten the ``custom`` bag into discrete scalar properties.
# Neo4j cannot store a nested map as a single property, so a node's
# ``custom={"k": v}`` is written as ``custom_k = v`` and reassembled on read.
_CUSTOM_PREFIX = "custom_"


def _flatten_custom(props: dict) -> dict:
    """Expand a ``custom`` dict into discrete ``custom_<key>`` scalar props.

    Returns a new props dict. The original ``custom`` key is removed.
    Non-scalar values (dict/list/None) are skipped: Neo4j properties must be
    primitive. Existing nodes with no ``custom`` are unaffected.
    """
    custom = props.get("custom")
    if not isinstance(custom, dict):
        return props
    out = {k: v for k, v in props.items() if k != "custom"}
    for key, value in custom.items():
        if isinstance(value, bool) or isinstance(value, (str, int, float)):
            out[f"{_CUSTOM_PREFIX}{key}"] = value
        else:
            logger.debug(
                "Skipping non-scalar custom field %r (type %s)",
                key, type(value).__name__,
            )
    return out


def _reassemble_custom(node: dict) -> dict:
    """Collapse ``custom_<key>`` props back into a single ``custom`` dict.

    Returns a new dict with the flat ``custom_*`` keys removed from the top
    level and gathered under ``custom``. Nodes without any ``custom_*`` prop
    round-trip unchanged (no empty ``custom`` injected, so back-compat holds).
    """
    custom: dict = {}
    out: dict = {}
    for key, value in node.items():
        if key.startswith(_CUSTOM_PREFIX):
            custom[key[len(_CUSTOM_PREFIX):]] = value
        else:
            out[key] = value
    if custom:
        out["custom"] = custom
    return out


class Neo4jBackend(GraphBackend):
    """Neo4j backend using the existing async driver singleton."""

    def __init__(self, config: WheelerConfig) -> None:
        self._config = config
        self._cb = CircuitBreaker(
            failure_threshold=config.neo4j.cb_failure_threshold,
            recovery_timeout=config.neo4j.cb_recovery_timeout,
        )

    def _driver(self):
        from wheeler.graph.driver import get_async_driver

        return get_async_driver(self._config)

    @property
    def _database(self) -> str:
        return self._config.neo4j.database

    @property
    def _project_tag(self) -> str:
        """Non-empty when Community Edition namespace isolation is active."""
        return self._config.neo4j.project_tag

    # -- lifecycle --

    async def initialize(self) -> None:
        """Apply constraints and indexes via the existing schema module."""
        from wheeler.graph.schema import init_schema

        await init_schema(self._config)

    async def close(self) -> None:
        """Close the singleton async driver."""
        from wheeler.graph.driver import close_async_driver

        await close_async_driver()

    # -- node CRUD --

    async def create_node(self, label: str, properties: dict) -> str:
        self._cb.check()
        # Flatten the custom bag into discrete custom_<key> scalar props so
        # Neo4j can store them (a nested map is not a valid property value).
        props = _flatten_custom(dict(properties))
        if "id" not in props:
            prefix = LABEL_TO_PREFIX.get(label)
            if not prefix:
                raise ValueError(f"Unknown label: {label}")
            props["id"] = generate_node_id(prefix)

        node_id = props["id"]

        # Inject project namespace tag when isolation is active
        if self._project_tag:
            props["_wheeler_project"] = self._project_tag

        # Build SET clause from properties -- reference via $props.key
        # to avoid kwarg collision with the Neo4j driver's own parameters.
        prop_assignments = ", ".join(f"{k}: $props.{k}" for k in props)
        stmt = f"CREATE (n:{label} {{{prop_assignments}}})"

        try:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                await session.run(stmt, parameters={"props": props})
            self._cb.record_success()
        except CircuitOpenError:
            raise
        except Exception as exc:
            if is_deterministic_neo4j_error(exc):
                self._cb.record_underlying(exc)
                raise
            self._cb.record_failure()
            self._cb.record_underlying(exc)
            raise

        logger.debug("Created %s node %s", label, node_id)
        return node_id

    async def get_node(self, label: str, node_id: str) -> dict | None:
        self._cb.check()
        params: dict = {"id": node_id}
        if self._project_tag:
            stmt = (
                f"MATCH (n:{label} {{id: $id}}) "
                f"WHERE n._wheeler_project = $ptag RETURN n"
            )
            params["ptag"] = self._project_tag
        else:
            stmt = f"MATCH (n:{label} {{id: $id}}) RETURN n"

        try:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(stmt, parameters=params)
                record = await result.single()
            self._cb.record_success()
        except CircuitOpenError:
            raise
        except Exception as exc:
            if is_deterministic_neo4j_error(exc):
                self._cb.record_underlying(exc)
                raise
            self._cb.record_failure()
            self._cb.record_underlying(exc)
            raise

        if record is None:
            return None

        node = record["n"]
        # Collapse flattened custom_<key> props back into a single custom dict.
        return _reassemble_custom(dict(node))

    async def update_node(
        self, label: str, node_id: str, properties: dict
    ) -> bool:
        self._cb.check()
        # Flatten any custom bag the same way create_node does, so an update
        # that carries custom={...} writes discrete custom_<key> scalar props
        # rather than attempting to SET a nested map (which Neo4j rejects).
        flattened = _flatten_custom({k: v for k, v in properties.items() if k != "id"})
        props = flattened
        if not props:
            return False

        set_clauses = ", ".join(f"n.{k} = $props.{k}" for k in props)
        params: dict = {"id": node_id, "props": props}

        if self._project_tag:
            stmt = (
                f"MATCH (n:{label} {{id: $id}}) "
                f"WHERE n._wheeler_project = $ptag "
                f"SET {set_clauses} RETURN n.id"
            )
            params["ptag"] = self._project_tag
        else:
            stmt = f"MATCH (n:{label} {{id: $id}}) SET {set_clauses} RETURN n.id"

        try:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(stmt, parameters=params)
                record = await result.single()
            self._cb.record_success()
        except CircuitOpenError:
            raise
        except Exception as exc:
            if is_deterministic_neo4j_error(exc):
                self._cb.record_underlying(exc)
                raise
            self._cb.record_failure()
            self._cb.record_underlying(exc)
            raise

        return record is not None

    async def delete_node(self, label: str, node_id: str) -> bool:
        self._cb.check()
        params: dict = {"id": node_id}
        if self._project_tag:
            match_clause = (
                f"MATCH (n:{label} {{id: $id}}) "
                f"WHERE n._wheeler_project = $ptag"
            )
            params["ptag"] = self._project_tag
        else:
            match_clause = f"MATCH (n:{label} {{id: $id}})"

        try:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                # Check existence
                result = await session.run(
                    f"{match_clause} RETURN n.id",
                    parameters=params,
                )
                record = await result.single()
                if record is None:
                    self._cb.record_success()
                    return False

                await session.run(
                    f"{match_clause} DETACH DELETE n",
                    parameters=params,
                )
            self._cb.record_success()
        except CircuitOpenError:
            raise
        except Exception as exc:
            if is_deterministic_neo4j_error(exc):
                self._cb.record_underlying(exc)
                raise
            self._cb.record_failure()
            self._cb.record_underlying(exc)
            raise

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
        rel_props: dict | None = None,
    ) -> bool:
        self._cb.check()
        params: dict = {"src": src_id, "tgt": tgt_id}

        # Build the SET clause for relationship properties when provided.
        set_clause = ""
        if rel_props:
            set_parts = []
            for i, (k, v) in enumerate(rel_props.items()):
                param_key = f"rp_{i}"
                params[param_key] = v
                set_parts.append(f"r.{k} = ${param_key}")
            set_clause = " SET " + ", ".join(set_parts)

        if self._project_tag:
            stmt = (
                f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
                f"WHERE a._wheeler_project = $ptag AND b._wheeler_project = $ptag "
                f"CREATE (a)-[r:{rel_type}]->(b){set_clause} RETURN type(r) AS rel"
            )
            params["ptag"] = self._project_tag
        else:
            stmt = (
                f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
                f"CREATE (a)-[r:{rel_type}]->(b){set_clause} RETURN type(r) AS rel"
            )

        try:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(stmt, parameters=params)
                record = await result.single()
            self._cb.record_success()
        except CircuitOpenError:
            raise
        except Exception as exc:
            if is_deterministic_neo4j_error(exc):
                self._cb.record_underlying(exc)
                raise
            self._cb.record_failure()
            self._cb.record_underlying(exc)
            raise

        if record:
            logger.debug("Linked %s -[%s]-> %s", src_id, rel_type, tgt_id)
            return True
        return False

    # -- queries --

    async def query_nodes(
        self,
        label: str,
        filters: dict | None = None,
        order_by: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        self._cb.check()
        where_parts: list[str] = []
        params: dict = {"limit": limit}
        if filters:
            for key, value in filters.items():
                where_parts.append(f"n.{key} = $filters.{key}")
                params.setdefault("filters", {})[key] = value

        # Project namespace filter
        if self._project_tag:
            where_parts.append("n._wheeler_project = $ptag")
            params["ptag"] = self._project_tag

        where_clause = ""
        if where_parts:
            where_clause = " WHERE " + " AND ".join(where_parts)

        order_clause = ""
        if order_by:
            order_clause = f" ORDER BY n.{order_by} DESC"

        stmt = (
            f"MATCH (n:{label}){where_clause}"
            f" RETURN n{order_clause} LIMIT $limit"
        )

        try:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(stmt, parameters=params)
                records = [r async for r in result]
            self._cb.record_success()
        except CircuitOpenError:
            raise
        except Exception as exc:
            if is_deterministic_neo4j_error(exc):
                self._cb.record_underlying(exc)
                raise
            self._cb.record_failure()
            self._cb.record_underlying(exc)
            raise

        return [_reassemble_custom(dict(r["n"])) for r in records]

    async def count_all(self) -> dict[str, Any]:
        """Use the existing schema.get_status implementation."""
        self._cb.check()
        from wheeler.graph.schema import get_status

        try:
            result = await get_status(self._config)
            self._cb.record_success()
            return result
        except CircuitOpenError:
            raise
        except Exception as exc:
            if is_deterministic_neo4j_error(exc):
                self._cb.record_underlying(exc)
                raise
            self._cb.record_failure()
            self._cb.record_underlying(exc)
            raise

    # -- raw cypher --

    async def run_cypher(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        self._cb.check()
        try:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(query, parameters=params or {})
                records = [dict(r) async for r in result]
            self._cb.record_success()
            return records
        except CircuitOpenError:
            raise
        except Exception as exc:
            if is_deterministic_neo4j_error(exc):
                self._cb.record_underlying(exc)
                raise
            self._cb.record_failure()
            self._cb.record_underlying(exc)
            raise
