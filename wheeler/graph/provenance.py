"""Provenance capture: file hashing, script node creation, staleness detection."""

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
class ScriptProvenance:
    path: str
    hash: str
    language: str
    version: str = ""
    tier: str = "generated"


@dataclass
class StaleScript:
    node_id: str
    path: str
    stored_hash: str
    current_hash: str


def _generate_id() -> str:
    return generate_node_id("S")


async def create_script_node(
    prov: ScriptProvenance, config: WheelerConfig
) -> str:
    """Create a Script node in Neo4j with provenance data. Returns node ID."""
    driver = get_async_driver(config)
    node_id = _generate_id()
    now = datetime.now(timezone.utc).isoformat()
    props: dict = {
        "id": node_id,
        "path": prov.path,
        "hash": prov.hash,
        "language": prov.language,
        "version": prov.version,
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
            f"CREATE (s:Script {{{prop_assignments}}})",
            parameters={"props": props},
        )
    return node_id


async def create_execution_node(
    kind: str,
    agent_id: str,
    description: str,
    session_id: str,
    config: WheelerConfig,
) -> str:
    """Create an Execution node in Neo4j. Returns node ID."""
    driver = get_async_driver(config)
    node_id = generate_node_id("X")
    now = datetime.now(timezone.utc).isoformat()
    props: dict = {
        "id": node_id,
        "kind": kind,
        "agent_id": agent_id,
        "description": description,
        "session_id": session_id,
        "started_at": now,
        "date": now,
        "status": "running",
        "tier": "generated",
    }
    # Inject project namespace tag when isolation is active
    project_tag = config.neo4j.project_tag
    if project_tag:
        props["_wheeler_project"] = project_tag

    prop_assignments = ", ".join(f"{k}: $props.{k}" for k in props)
    async with driver.session(database=config.neo4j.database) as session:
        await session.run(
            f"CREATE (x:Execution {{{prop_assignments}}})",
            parameters={"props": props},
        )
    return node_id


async def detect_stale_scripts(config: WheelerConfig) -> list[StaleScript]:
    """Find Script nodes whose hash doesn't match the file on disk."""
    driver = get_async_driver(config)
    stale: list[StaleScript] = []

    project_tag = config.neo4j.project_tag
    if project_tag:
        query = (
            "MATCH (s:Script) WHERE s.path IS NOT NULL "
            "AND s.hash IS NOT NULL "
            "AND s._wheeler_project = $ptag "
            "RETURN s.id AS id, s.path AS path, "
            "s.hash AS hash"
        )
        params: dict = {"ptag": project_tag}
    else:
        query = (
            "MATCH (s:Script) WHERE s.path IS NOT NULL "
            "AND s.hash IS NOT NULL "
            "RETURN s.id AS id, s.path AS path, "
            "s.hash AS hash"
        )
        params = {}

    async with driver.session(database=config.neo4j.database) as session:
        result = await session.run(query, parameters=params)
        records = [r async for r in result]
    for rec in records:
        script_path = Path(rec["path"])
        if not script_path.exists():
            stale.append(StaleScript(
                node_id=rec["id"],
                path=rec["path"],
                stored_hash=rec["hash"],
                current_hash="FILE_NOT_FOUND",
            ))
            continue
        current_hash = hash_file(script_path)
        if current_hash != rec["hash"]:
            stale.append(StaleScript(
                node_id=rec["id"],
                path=rec["path"],
                stored_hash=rec["hash"],
                current_hash=current_hash,
            ))
    return stale
