"""Provenance capture: file hashing, analysis node creation, staleness detection."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)
from wheeler.graph.driver import get_async_driver
from wheeler.graph.schema import generate_node_id


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
    tier: str = "generated"


@dataclass
class StaleAnalysis:
    node_id: str
    script_path: str
    stored_hash: str
    current_hash: str
    executed_at: str = ""


def _generate_id() -> str:
    return generate_node_id("A")


async def create_analysis_node(
    prov: AnalysisProvenance, config: WheelerConfig
) -> str:
    """Create an Analysis node in Neo4j with provenance data. Returns node ID."""
    driver = get_async_driver(config)
    node_id = _generate_id()
    now = datetime.now(timezone.utc).isoformat()
    props: dict = {
        "id": node_id,
        "script_path": prov.script_path,
        "script_hash": prov.script_hash,
        "language": prov.language,
        "language_version": prov.language_version,
        "parameters": prov.parameters,
        "output_path": prov.output_path,
        "output_hash": prov.output_hash,
        "executed_at": now,
        "date": now,
        "tier": prov.tier,
    }
    # Inject project namespace tag when isolation is active
    project_tag = config.neo4j.project_tag
    if project_tag:
        props["_wheeler_project"] = project_tag

    prop_assignments = ", ".join(f"{k}: $props.{k}" for k in props)
    async with driver.session(database=config.neo4j.database) as session:
        await session.run(
            f"CREATE (a:Analysis {{{prop_assignments}}})",
            parameters={"props": props},
        )
    return node_id


async def detect_stale_analyses(config: WheelerConfig) -> list[StaleAnalysis]:
    """Find Analysis nodes whose script_hash doesn't match the file on disk."""
    driver = get_async_driver(config)
    stale: list[StaleAnalysis] = []

    project_tag = config.neo4j.project_tag
    if project_tag:
        query = (
            "MATCH (a:Analysis) WHERE a.script_path IS NOT NULL "
            "AND a.script_hash IS NOT NULL "
            "AND a._wheeler_project = $ptag "
            "RETURN a.id AS id, a.script_path AS path, "
            "a.script_hash AS hash, a.executed_at AS executed_at"
        )
        params: dict = {"ptag": project_tag}
    else:
        query = (
            "MATCH (a:Analysis) WHERE a.script_path IS NOT NULL "
            "AND a.script_hash IS NOT NULL "
            "RETURN a.id AS id, a.script_path AS path, "
            "a.script_hash AS hash, a.executed_at AS executed_at"
        )
        params = {}

    async with driver.session(database=config.neo4j.database) as session:
        result = await session.run(query, parameters=params)
        records = [r async for r in result]
    for rec in records:
        script_path = Path(rec["path"])
        if not script_path.exists():
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
    return stale
