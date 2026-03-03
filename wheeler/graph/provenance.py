"""Provenance capture: file hashing, analysis node creation, staleness detection."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from neo4j import AsyncGraphDatabase

from wheeler.config import WheelerConfig


def hash_file(path: str | Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class AnalysisProvenance:
    script_path: str
    script_hash: str
    language: str
    language_version: str = ""
    parameters: str = ""
    output_path: str = ""
    output_hash: str = ""


@dataclass
class StaleAnalysis:
    node_id: str
    script_path: str
    stored_hash: str
    current_hash: str
    executed_at: str = ""


def _generate_id() -> str:
    return f"A-{secrets.token_hex(4)}"


async def create_analysis_node(
    prov: AnalysisProvenance, config: WheelerConfig
) -> str:
    """Create an Analysis node in Neo4j with provenance data. Returns node ID."""
    driver = AsyncGraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
    )
    node_id = _generate_id()
    now = datetime.now(timezone.utc).isoformat()
    try:
        async with driver.session(database=config.neo4j.database) as session:
            await session.run(
                "CREATE (a:Analysis {"
                "  id: $id,"
                "  script_path: $script_path,"
                "  script_hash: $script_hash,"
                "  language: $language,"
                "  language_version: $language_version,"
                "  parameters: $parameters,"
                "  output_path: $output_path,"
                "  output_hash: $output_hash,"
                "  executed_at: $executed_at,"
                "  date: $date"
                "})",
                id=node_id,
                script_path=prov.script_path,
                script_hash=prov.script_hash,
                language=prov.language,
                language_version=prov.language_version,
                parameters=prov.parameters,
                output_path=prov.output_path,
                output_hash=prov.output_hash,
                executed_at=now,
                date=now,
            )
    finally:
        await driver.close()
    return node_id


async def detect_stale_analyses(config: WheelerConfig) -> list[StaleAnalysis]:
    """Find Analysis nodes whose script_hash doesn't match the file on disk."""
    driver = AsyncGraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
    )
    stale: list[StaleAnalysis] = []
    try:
        async with driver.session(database=config.neo4j.database) as session:
            result = await session.run(
                "MATCH (a:Analysis) WHERE a.script_path IS NOT NULL "
                "AND a.script_hash IS NOT NULL "
                "RETURN a.id AS id, a.script_path AS path, "
                "a.script_hash AS hash, a.executed_at AS executed_at"
            )
            records = [r async for r in result]
        for rec in records:
            script_path = Path(rec["path"])
            if not script_path.exists():
                # File missing — also stale
                stale.append(StaleAnalysis(
                    node_id=rec["id"],
                    script_path=rec["path"],
                    stored_hash=rec["hash"],
                    current_hash="FILE_NOT_FOUND",
                    executed_at=rec.get("executed_at", ""),
                ))
                continue
            current_hash = hash_file(script_path)
            if current_hash != rec["hash"]:
                stale.append(StaleAnalysis(
                    node_id=rec["id"],
                    script_path=rec["path"],
                    stored_hash=rec["hash"],
                    current_hash=current_hash,
                    executed_at=rec.get("executed_at", ""),
                ))
    finally:
        await driver.close()
    return stale
