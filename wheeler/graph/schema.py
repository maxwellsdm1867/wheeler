"""Neo4j schema: constraints, indexes, init and status functions."""

from __future__ import annotations

from neo4j import AsyncGraphDatabase

from wheeler.config import WheelerConfig

# Node ID prefix → label mapping
PREFIX_TO_LABEL: dict[str, str] = {
    "PL": "Plan",
    "F": "Finding",
    "H": "Hypothesis",
    "Q": "OpenQuestion",
    "E": "Experiment",
    "A": "Analysis",
    "D": "Dataset",
    "P": "Paper",
    "C": "CellType",
    "T": "Task",
}

LABEL_TO_PREFIX: dict[str, str] = {v: k for k, v in PREFIX_TO_LABEL.items()}

# All node labels in the schema
NODE_LABELS = list(PREFIX_TO_LABEL.values())

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
]


async def _get_driver(config: WheelerConfig):
    return AsyncGraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
    )


async def init_schema(config: WheelerConfig) -> list[str]:
    """Apply all constraints and indexes to Neo4j. Returns list of applied statements."""
    driver = await _get_driver(config)
    applied: list[str] = []
    try:
        async with driver.session(database=config.neo4j.database) as session:
            for stmt in CONSTRAINTS + INDEXES:
                await session.run(stmt)
                applied.append(stmt)
    finally:
        await driver.close()
    return applied


async def get_status(config: WheelerConfig) -> dict[str, int]:
    """Return node counts per label."""
    driver = await _get_driver(config)
    counts: dict[str, int] = {}
    try:
        async with driver.session(database=config.neo4j.database) as session:
            for label in NODE_LABELS:
                result = await session.run(
                    f"MATCH (n:{label}) RETURN count(n) AS cnt"
                )
                record = await result.single()
                counts[label] = record["cnt"] if record else 0
    finally:
        await driver.close()
    return counts
