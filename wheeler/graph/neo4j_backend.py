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

from collections.abc import Awaitable, Callable
import logging
from typing import Any, TypeVar

from wheeler.config import WheelerConfig
from wheeler.graph.backend import GraphBackend
from wheeler.graph.cypher_guard import CYPHER_WRITE_RE, is_read_only_cypher
from wheeler.graph.circuit_breaker import (
    CircuitBreaker,
)
from wheeler.graph.schema import (
    LABEL_TO_PREFIX,
    generate_node_id,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Prefix used to flatten the ``custom`` bag into discrete scalar properties.
# Neo4j cannot store a nested map as a single property, so a node's
# ``custom={"k": v}`` is written as ``custom_k = v`` and reassembled on read.
_CUSTOM_PREFIX = "custom_"

# The write-detection rule lives in graph/cypher_guard.py because the MCP
# surface needs the identical rule to enforce its read-only boundary, and a
# second copy there had drifted into permitting CREATE(n:...) while refusing
# reads that merely mention a Dataset. Re-exported under the old private names
# so existing call sites and tests keep working.
_CYPHER_WRITE_RE = CYPHER_WRITE_RE
_is_read_only_cypher = is_read_only_cypher


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

        # A project that named a keychain profile and did not get one must not
        # silently connect somewhere else. Falling through would reach the
        # built-in localhost default, which is either a stopped instance or,
        # worse, a DIFFERENT graph that answers happily and takes the writes.
        if getattr(self._config.neo4j, "profile_missing", False):
            declared = self._config.neo4j.profile
            raise RuntimeError(
                f"this project connects through the keychain profile "
                f"{declared!r}, and no credential is stored under that name on "
                f"this machine. Refusing to fall back to "
                f"{self._config.neo4j.uri}, which is not the graph this project "
                f"asked for. Fix with: wheeler login --profile {declared}"
            )
        return get_async_driver(self._config)

    @property
    def _database(self) -> str:
        return self._config.neo4j.database

    @property
    def _project_tag(self) -> str:
        """Non-empty when Community Edition namespace isolation is active."""
        return self._config.neo4j.project_tag

    # -- execution helpers --
    #
    # Both route through the same wrapper so the breaker bookkeeping cannot
    # drift between the replayed and the not-replayed paths. The wrapper checks
    # the breaker before each attempt, lets CircuitOpenError propagate, records
    # a transient failure against the counter, and records a deterministic
    # Cypher error as the underlying cause without advancing the counter.
    #
    # `operation` is always a factory, called once per attempt, so each attempt
    # opens its own session. Attempts run strictly sequentially: a Neo4j session
    # forbids concurrent queries, so nothing here may become an asyncio.gather.

    async def _retry(
        self, operation: Callable[[], Awaitable[T]], *, label: str
    ) -> T:
        """Run ``operation``, replaying it on a transient failure.

        Only for operations that are safe to replay: reads, and writes whose
        Cypher is idempotent (MATCH ... SET, DETACH DELETE).
        """
        from wheeler.graph.driver import run_with_retry

        return await run_with_retry(operation, breaker=self._cb, label=label)

    async def _once(
        self, operation: Callable[[], Awaitable[T]], *, label: str
    ) -> T:
        """Run ``operation`` exactly once, never replaying it.

        For call sites where a replay could duplicate data. Expressed as the
        one-attempt case of the same wrapper rather than a hand-rolled
        try/except, so the two paths cannot report failures differently.
        """
        from wheeler.graph.driver import run_with_retry

        return await run_with_retry(
            operation, breaker=self._cb, attempts=1, label=label
        )

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

        # Stamp the origin (machine / database / project) on every node.
        # This belongs at the backend rather than in the add_* handlers because
        # each handler builds an explicit props dict, so anything merged into the
        # tool args upstream never reaches Neo4j. Doing it here also covers nodes
        # created outside a handler, such as the provenance-helper Execution.
        # Existing keys win, so a restore replaying an archived node keeps the
        # machine that originally wrote it.
        from wheeler.machine import origin_props

        for key, value in origin_props(self._config).items():
            props.setdefault(key, value)

        # Build SET clause from properties -- reference via $props.key
        # to avoid kwarg collision with the Neo4j driver's own parameters.
        prop_assignments = ", ".join(f"{k}: $props.{k}" for k in props)
        stmt = f"CREATE (n:{label} {{{prop_assignments}}})"

        async def _run() -> None:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                await session.run(stmt, parameters={"props": props})

        # NOT RETRIED: a bare CREATE must not be replayed.
        #
        # The `id` uniqueness constraint means a replay cannot actually produce
        # a duplicate node, so the hazard is subtler than duplication: if the
        # commit landed and only the acknowledgement was lost, the replay hits
        # ConstraintValidationFailed and this method reports failure for a write
        # that in fact succeeded. The caller would then write a repair receipt
        # for a node that exists. Failing once, honestly, is better.
        await self._once(_run, label="create_node")

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

        async def _run():
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(stmt, parameters=params)
                return await result.single()

        # Retried: a read changes nothing, so replaying it is free.
        record = await self._retry(_run, label="get_node")

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

        async def _run():
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(stmt, parameters=params)
                return await result.single()

        # Retried: `MATCH ... SET` assigns fixed values from $props, so applying
        # it twice leaves exactly the state applying it once does.
        record = await self._retry(_run, label="update_node")

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

        # Survives across attempts: if attempt 1 saw the node and then lost the
        # connection, attempt 2 may find it already gone because attempt 1's
        # delete actually committed. Without this, the replay would report
        # "not found" for a delete that succeeded, and the caller would leave
        # the node's JSON and synthesis files behind as orphans.
        existed = False

        async def _run() -> bool:
            nonlocal existed
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                # Check existence
                result = await session.run(
                    f"{match_clause} RETURN n.id",
                    parameters=params,
                )
                record = await result.single()
                if record is None:
                    return existed
                existed = True

                await session.run(
                    f"{match_clause} DETACH DELETE n",
                    parameters=params,
                )
            return True

        # Retried: DETACH DELETE is idempotent, deleting an absent node is a
        # no-op, and `existed` keeps the return value honest across a replay.
        deleted = await self._retry(_run, label="delete_node")

        if deleted:
            logger.debug("Deleted %s node %s", label, node_id)
        return deleted

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

        async def _run():
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(stmt, parameters=params)
                return await result.single()

        # NOT RETRIED: this is the one call site where a replay really does
        # duplicate data. Relationships carry no uniqueness constraint, so a
        # `CREATE (a)-[r:TYPE]->(b)` replayed after a committed-but-unacked
        # write silently produces a second parallel edge of the same type, and
        # a doubled provenance edge is invisible until someone counts.
        # Switching this to MERGE would make it replay-safe, but that changes
        # link semantics (it would dedupe existing edges), so it belongs in its
        # own change rather than smuggled in with retry wiring.
        record = await self._once(_run, label="create_relationship")

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

        async def _run():
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(stmt, parameters=params)
                return [r async for r in result]

        # Retried: a read changes nothing, so replaying it is free.
        records = await self._retry(_run, label="query_nodes")

        return [_reassemble_custom(dict(r["n"])) for r in records]

    async def count_all(self) -> dict[str, Any]:
        """Use the existing schema.get_status implementation."""
        self._cb.check()
        from wheeler.graph.schema import get_status

        async def _run() -> dict[str, Any]:
            return await get_status(self._config)

        # NOT RETRIED: `get_status` catches its own exceptions and reports
        # `_status: offline` instead of raising, so there is no failure here for
        # a retry to see. It is deliberately un-retried at its own definition
        # too: it is a probe that must stay fast when Neo4j is simply down.
        return await self._once(_run, label="count_all")

    # -- raw cypher --

    async def run_cypher(
        self, query: str, params: dict | None = None
    ) -> list[dict]:
        self._cb.check()

        async def _run() -> list[dict]:
            driver = self._driver()
            async with driver.session(database=self._database) as session:
                result = await session.run(query, parameters=params or {})
                return [dict(r) async for r in result]

        # Retried ONLY for a provably read-only query. This is the raw escape
        # hatch: most callers (the query_* tools, search, the dashboard) read,
        # but merge.py and restore.py send writes through here too, so the
        # decision has to be made per query rather than per method.
        if _is_read_only_cypher(query):
            return await self._retry(_run, label="run_cypher (read-only)")
        return await self._once(_run, label="run_cypher (write)")
