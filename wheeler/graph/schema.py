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
    "CREATE INDEX IF NOT EXISTS FOR (e:Experiment) ON (e.date)",
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


async def init_schema(config: WheelerConfig) -> list[str]:
    """Apply all constraints and indexes to Neo4j. Returns list of applied statements."""
    from wheeler.graph.driver import get_async_driver
    driver = get_async_driver(config)
    applied: list[str] = []
    async with driver.session(database=config.neo4j.database) as session:
        for stmt in CONSTRAINTS + INDEXES:
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

        parts = [
            f"MATCH (n:{label}) RETURN '{label}' AS label, count(n) AS cnt"
            for label in NODE_LABELS
        ]
        query = " UNION ALL ".join(parts)

        async with driver.session(database=config.neo4j.database) as session:
            result = await session.run(query)
            records = [r async for r in result]
            for rec in records:
                counts[rec["label"]] = rec["cnt"]
    except Exception as exc:
        logger.warning("graph_status failed (Neo4j offline?): %s", exc)
    return counts
