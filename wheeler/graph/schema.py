"""Neo4j schema: constraints, indexes, init and status functions."""

from __future__ import annotations

import logging
import secrets

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)


from wheeler.models import LABEL_TO_PREFIX, NODE_LABELS, PREFIX_TO_LABEL  # noqa: E402


def generate_node_id(prefix: str) -> str:
    """Generate a unique node ID with the given prefix (e.g., 'F-abc12345')."""
    return f"{prefix}-{secrets.token_hex(4)}"

# Uniqueness constraints — every node type has a unique `id`
CONSTRAINTS: list[str] = [
    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
    for label in NODE_LABELS
]

# Indexes for common query patterns
INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS FOR (f:Finding) ON (f.date)",
    "CREATE INDEX IF NOT EXISTS FOR (f:Finding) ON (f.confidence)",
    "CREATE INDEX IF NOT EXISTS FOR (q:OpenQuestion) ON (q.priority)",
    "CREATE INDEX IF NOT EXISTS FOR (h:Hypothesis) ON (h.status)",
    "CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.doi)",
    "CREATE INDEX IF NOT EXISTS FOR (a:Analysis) ON (a.date)",
    "CREATE INDEX IF NOT EXISTS FOR (a:Analysis) ON (a.script_hash)",
    "CREATE INDEX IF NOT EXISTS FOR (a:Analysis) ON (a.script_path)",
    "CREATE INDEX IF NOT EXISTS FOR (a:Analysis) ON (a.executed_at)",
    "CREATE INDEX IF NOT EXISTS FOR (pl:Plan) ON (pl.status)",
    "CREATE INDEX IF NOT EXISTS FOR (w:Document) ON (w.date)",
    "CREATE INDEX IF NOT EXISTS FOR (w:Document) ON (w.status)",
    "CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.title)",
    "CREATE INDEX IF NOT EXISTS FOR (n:ResearchNote) ON (n.date)",
    # Knowledge file pointers
    "CREATE INDEX IF NOT EXISTS FOR (f:Finding) ON (f.file_path)",
    "CREATE INDEX IF NOT EXISTS FOR (h:Hypothesis) ON (h.file_path)",
    "CREATE INDEX IF NOT EXISTS FOR (q:OpenQuestion) ON (q.file_path)",
    "CREATE INDEX IF NOT EXISTS FOR (d:Dataset) ON (d.file_path)",
    "CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.file_path)",
    "CREATE INDEX IF NOT EXISTS FOR (w:Document) ON (w.file_path)",
    "CREATE INDEX IF NOT EXISTS FOR (n:ResearchNote) ON (n.file_path)",
]

# Project namespace indexes — used for Community Edition isolation.
# Only applied when project_tag is set.
PROJECT_INDEXES: list[str] = [
    f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n._wheeler_project)"
    for label in NODE_LABELS
]

# Allowed relationship types (whitelist for link command)
ALLOWED_RELATIONSHIPS: list[str] = [
    "PRODUCED",
    "SUPPORTS",
    "CONTRADICTS",
    "USED_DATA",
    "GENERATED",
    "RAN_SCRIPT",
    "CITES",
    "RELEVANT_TO",
    "REFERENCED_IN",
    "STUDIED_IN",
    "CONTAINS",
    "DEPENDS_ON",
    "AROSE_FROM",
    "INFORMED",
    "BASED_ON",
    "APPEARS_IN",
]


async def ensure_database(config: WheelerConfig) -> str:
    """Create the project's Neo4j database if it doesn't exist.

    Neo4j Community Edition only supports the default 'neo4j' database.
    When the requested database differs from 'neo4j' and creation fails
    (Community Edition), we fall back to the default database and enable
    property-based namespace isolation via ``config.neo4j.project_tag``.

    Returns the database name actually in use.
    """
    from wheeler.graph.driver import get_async_driver

    db_name = config.neo4j.database
    if db_name == "neo4j":
        # Default database — check if a project name was configured.
        # If so, enable namespace isolation even on the default database
        # (the user wants isolation but didn't set a custom DB name).
        if config.project.name and not config.neo4j.project_tag:
            config.neo4j.project_tag = config.project.name
            logger.info(
                "Project namespace isolation enabled: _wheeler_project='%s'",
                config.neo4j.project_tag,
            )
        return db_name

    driver = get_async_driver(config)
    try:
        # CREATE DATABASE is only available in Enterprise/Aura
        async with driver.session(database="system") as session:
            await session.run(
                f"CREATE DATABASE `{db_name}` IF NOT EXISTS"
            )
        logger.info("Ensured database '%s' exists (Enterprise/Aura)", db_name)
    except Exception as exc:
        # Community Edition — fall back to default database with namespacing
        project_tag = config.project.name or db_name
        config.neo4j.project_tag = project_tag
        config.neo4j.database = "neo4j"
        logger.info(
            "Could not create database '%s' (Community Edition?): %s. "
            "Falling back to 'neo4j' database with namespace isolation: "
            "_wheeler_project='%s'.",
            db_name, exc, project_tag,
        )
    return config.neo4j.database


async def init_schema(config: WheelerConfig) -> list[str]:
    """Apply all constraints and indexes to Neo4j. Returns list of applied statements."""
    from wheeler.graph.driver import get_async_driver
    driver = get_async_driver(config)
    applied: list[str] = []

    stmts = CONSTRAINTS + INDEXES
    if config.neo4j.project_tag:
        stmts = stmts + PROJECT_INDEXES

    async with driver.session(database=config.neo4j.database) as session:
        for stmt in stmts:
            await session.run(stmt)
            applied.append(stmt)
    logger.info("Schema initialized: %d constraints/indexes applied", len(applied))
    return applied


async def get_status(config: WheelerConfig) -> dict[str, int]:
    """Return node counts per label in a single query.

    Returns zeroed counts if Neo4j is unavailable — never crashes the caller.
    """
    counts: dict[str, int] = {label: 0 for label in NODE_LABELS}
    try:
        from wheeler.graph.driver import get_async_driver
        driver = get_async_driver(config)

        project_tag = config.neo4j.project_tag
        if project_tag:
            parts = [
                f"MATCH (n:{label}) WHERE n._wheeler_project = $ptag "
                f"RETURN '{label}' AS label, count(n) AS cnt"
                for label in NODE_LABELS
            ]
        else:
            parts = [
                f"MATCH (n:{label}) RETURN '{label}' AS label, count(n) AS cnt"
                for label in NODE_LABELS
            ]
        query = " UNION ALL ".join(parts)

        async with driver.session(database=config.neo4j.database) as session:
            if project_tag:
                result = await session.run(query, ptag=project_tag)
            else:
                result = await session.run(query)
            records = [r async for r in result]
            for rec in records:
                counts[rec["label"]] = rec["cnt"]
    except Exception as exc:
        logger.warning("graph_status failed (Neo4j offline?): %s", exc)
    return counts
