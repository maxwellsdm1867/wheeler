"""Neo4j graph database backend for Wheeler.

Thin adapter that maps the :class:`GraphBackend` ABC methods to Cypher
queries executed via the existing singleton async driver in
:mod:`wheeler.graph.driver`.
"""

from __future__ import annotations

import logging

from wheeler.config import WheelerConfig
from wheeler.graph.backend import GraphBackend
from wheeler.graph.schema import (
    LABEL_TO_PREFIX,
    generate_node_id,
)

logger = logging.getLogger(__name__)


class Neo4jBackend(GraphBackend):
    """Neo4j backend using the existing async driver singleton."""

    def __init__(self, config: WheelerConfig) -> None:
        self._config = config

    def _driver(self):
        from wheeler.graph.driver import get_async_driver

        return get_async_driver(self._config)

    @property
    def _database(self) -> str:
        return self._config.neo4j.database

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
        props = dict(properties)
        if "id" not in props:
            prefix = LABEL_TO_PREFIX.get(label)
            if not prefix:
                raise ValueError(f"Unknown label: {label}")
            props["id"] = generate_node_id(prefix)

        node_id = props["id"]

        # Build SET clause from properties
        prop_assignments = ", ".join(f"{k}: ${k}" for k in props)
        stmt = f"CREATE (n:{label} {{{prop_assignments}}})"

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            await session.run(stmt, **props)

        logger.debug("Created %s node %s", label, node_id)
        return node_id

    async def get_node(self, label: str, node_id: str) -> dict | None:
        stmt = f"MATCH (n:{label} {{id: $id}}) RETURN n"
        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, id=node_id)
            record = await result.single()

        if record is None:
            return None

        node = record["n"]
        return dict(node)

    async def update_node(
        self, label: str, node_id: str, properties: dict
    ) -> bool:
        props = {k: v for k, v in properties.items() if k != "id"}
        if not props:
            return False

        set_clauses = ", ".join(f"n.{k} = ${k}" for k in props)
        stmt = f"MATCH (n:{label} {{id: $id}}) SET {set_clauses} RETURN n.id"
        params = {"id": node_id, **props}

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, **params)
            record = await result.single()

        return record is not None

    async def delete_node(self, label: str, node_id: str) -> bool:
        driver = self._driver()
        async with driver.session(database=self._database) as session:
            # Check existence
            result = await session.run(
                f"MATCH (n:{label} {{id: $id}}) RETURN n.id", id=node_id,
            )
            record = await result.single()
            if record is None:
                return False

            await session.run(
                f"MATCH (n:{label} {{id: $id}}) DETACH DELETE n", id=node_id,
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
        stmt = (
            f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
            f"CREATE (a)-[r:{rel_type}]->(b) RETURN type(r) AS rel"
        )
        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, src=src_id, tgt=tgt_id)
            record = await result.single()

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
        where_parts: list[str] = []
        params: dict = {"limit": limit}
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

        stmt = (
            f"MATCH (n:{label}){where_clause}"
            f" RETURN n{order_clause} LIMIT $limit"
        )

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, **params)
            records = [r async for r in result]

        return [dict(r["n"]) for r in records]

    async def count_nodes(self, label: str) -> int:
        stmt = f"MATCH (n:{label}) RETURN count(n) AS cnt"
        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt)
            record = await result.single()
        return record["cnt"] if record else 0

    async def count_all(self) -> dict[str, int]:
        """Use the existing schema.get_status implementation."""
        from wheeler.graph.schema import get_status

        return await get_status(self._config)

    # -- graph-specific queries --

    async def find_unlinked(
        self,
        label: str,
        rel_types: list[str],
        direction: str = "any",
    ) -> list[dict]:
        rel_pattern = "|".join(rel_types)
        if direction == "incoming":
            where = f"NOT (n)<-[:{rel_pattern}]-()"
        elif direction == "outgoing":
            where = f"NOT (n)-[:{rel_pattern}]->()"
        else:
            where = f"NOT (n)-[:{rel_pattern}]-()"

        stmt = f"MATCH (n:{label}) WHERE {where} RETURN n"
        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt)
            records = [r async for r in result]
        return [dict(r["n"]) for r in records]

    async def find_connected(
        self,
        node_id: str,
        rel_type: str,
        direction: str = "outgoing",
    ) -> list[dict]:
        from wheeler.graph.schema import PREFIX_TO_LABEL

        prefix = node_id.split("-", 1)[0]
        src_label = PREFIX_TO_LABEL.get(prefix)
        if not src_label:
            logger.warning("find_connected: unknown prefix %s", prefix)
            return []

        if direction == "incoming":
            stmt = (
                f"MATCH (n:{src_label} {{id: $id}})<-[:{rel_type}]-(m) "
                f"RETURN m"
            )
        else:
            stmt = (
                f"MATCH (n:{src_label} {{id: $id}})-[:{rel_type}]->(m) "
                f"RETURN m"
            )

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, id=node_id)
            records = [r async for r in result]

        return [dict(r["m"]) for r in records]
