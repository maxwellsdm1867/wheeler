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
        props = dict(properties)
        if "id" not in props:
            prefix = LABEL_TO_PREFIX.get(label)
            if not prefix:
                raise ValueError(f"Unknown label: {label}")
            props["id"] = generate_node_id(prefix)

        node_id = props["id"]

        # Inject project namespace tag when isolation is active
        if self._project_tag:
            props["_wheeler_project"] = self._project_tag

        # Build SET clause from properties — reference via $props.key
        # to avoid kwarg collision with the Neo4j driver's own parameters.
        prop_assignments = ", ".join(f"{k}: $props.{k}" for k in props)
        stmt = f"CREATE (n:{label} {{{prop_assignments}}})"

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            await session.run(stmt, parameters={"props": props})

        logger.debug("Created %s node %s", label, node_id)
        return node_id

    async def get_node(self, label: str, node_id: str) -> dict | None:
        params: dict = {"id": node_id}
        if self._project_tag:
            stmt = (
                f"MATCH (n:{label} {{id: $id}}) "
                f"WHERE n._wheeler_project = $ptag RETURN n"
            )
            params["ptag"] = self._project_tag
        else:
            stmt = f"MATCH (n:{label} {{id: $id}}) RETURN n"

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, parameters=params)
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

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, parameters=params)
            record = await result.single()

        return record is not None

    async def delete_node(self, label: str, node_id: str) -> bool:
        params: dict = {"id": node_id}
        if self._project_tag:
            match_clause = (
                f"MATCH (n:{label} {{id: $id}}) "
                f"WHERE n._wheeler_project = $ptag"
            )
            params["ptag"] = self._project_tag
        else:
            match_clause = f"MATCH (n:{label} {{id: $id}})"

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            # Check existence
            result = await session.run(
                f"{match_clause} RETURN n.id",
                parameters=params,
            )
            record = await result.single()
            if record is None:
                return False

            await session.run(
                f"{match_clause} DETACH DELETE n",
                parameters=params,
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
        params: dict = {"src": src_id, "tgt": tgt_id}
        if self._project_tag:
            stmt = (
                f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
                f"WHERE a._wheeler_project = $ptag AND b._wheeler_project = $ptag "
                f"CREATE (a)-[r:{rel_type}]->(b) RETURN type(r) AS rel"
            )
            params["ptag"] = self._project_tag
        else:
            stmt = (
                f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
                f"CREATE (a)-[r:{rel_type}]->(b) RETURN type(r) AS rel"
            )

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, parameters=params)
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

        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(stmt, parameters=params)
            records = [r async for r in result]

        return [dict(r["n"]) for r in records]

    async def count_all(self) -> dict[str, int]:
        """Use the existing schema.get_status implementation."""
        from wheeler.graph.schema import get_status

        return await get_status(self._config)

    # -- raw cypher --

    async def run_cypher(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        driver = self._driver()
        async with driver.session(database=self._database) as session:
            result = await session.run(query, parameters=params or {})
            return [dict(r) async for r in result]
