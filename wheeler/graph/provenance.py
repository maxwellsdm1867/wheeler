"""Provenance capture: file hashing, script node creation, staleness detection."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)
from wheeler.graph.driver import get_async_driver  # noqa: E402
from wheeler.graph.schema import generate_node_id  # noqa: E402


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
    # Why this node looks stale. Only ``changed`` may invalidate anything
    # downstream; see ``detect_stale_scripts`` for what separates the three.
    reason: str = "changed"
    # The machine that wrote the node, for reporting. Empty on legacy nodes.
    origin_host: str = ""


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
    """Find Script nodes whose file no longer matches, classified by why.

    Three outcomes, and only the first is a reason to invalidate anything:

    - ``changed``: the file belongs to this machine and its bytes moved (or it
      was deleted). This is genuine staleness and propagates downstream.
    - ``diverged``: the bytes differ, but another machine wrote this node. That
      is two copies of a file, not a new result, and cascading it would mark a
      colleague's whole provenance chain stale from here.
    - ``absent``: the file cannot be located on this machine at all, because its
      root is not configured here. It lives on another computer and says nothing
      about whether the work is current.

    The distinction is what makes a shared graph survivable. Before it existed,
    opening a graph written on another machine found every path missing, reported
    ``FILE_NOT_FOUND`` for each, and invalidated everything reachable beneath.

    A node with no ``origin_machine`` (everything written before origin stamping)
    is attributed by EVIDENCE rather than by a blanket default, because neither
    blanket answer is safe. If its file is present here, a hash mismatch is real
    staleness: the file being on this disk is what makes it ours. If its file is
    absent, it is reported ``absent`` and cascades nothing, because "my file was
    deleted" and "this graph came from another machine" are indistinguishable
    from the node alone, and only one of them should invalidate anything.
    """
    from wheeler.machine import machine_id
    from wheeler.portability import resolve as resolve_portable

    driver = get_async_driver(config)
    stale: list[StaleScript] = []

    project_tag = config.neo4j.project_tag
    ptag_filter = ""
    props: dict = {}
    if project_tag:
        ptag_filter = "AND s._wheeler_project = $props.ptag "
        props["ptag"] = project_tag

    query = (
        "MATCH (s:Script) WHERE s.path IS NOT NULL "
        "AND s.hash IS NOT NULL "
        f"{ptag_filter}"
        "RETURN s.id AS id, s.path AS path, "
        "s.hash AS hash, s.origin_machine AS origin_machine, "
        "s.origin_host AS origin_host"
    )

    async with driver.session(database=config.neo4j.database) as session:
        result = await session.run(query, parameters={"props": props})
        records = [r async for r in result]

    roots = config.resolved_roots
    here = machine_id()

    for rec in records:
        origin = rec.get("origin_machine") or ""
        origin_host = rec.get("origin_host") or ""
        ours = (not origin) or origin == here

        script_path = resolve_portable(rec["path"], roots)
        if script_path is None:
            # Portable, but its root is not configured on this machine.
            stale.append(StaleScript(
                node_id=rec["id"], path=rec["path"], stored_hash=rec["hash"],
                current_hash="ROOT_NOT_CONFIGURED", reason="absent",
                origin_host=origin_host,
            ))
            continue

        if not script_path.exists():
            stale.append(StaleScript(
                node_id=rec["id"], path=rec["path"], stored_hash=rec["hash"],
                current_hash="FILE_NOT_FOUND",
                # A MISSING file cascades only when the node is positively ours.
                # Unattributed is not the same as ours here: a graph copied to a
                # new machine (or to Aura) carries thousands of legacy nodes with
                # no origin at all, whose files were never on this computer, and
                # reading those as "my file was deleted" invalidates the whole
                # graph on first contact. Measured against a real Aura copy of
                # this repo's graph: 1,359 of 1,452 Scripts, every one of them a
                # path that had only ever existed in another machine's tmp dir.
                #
                # Legacy nodes keep their old behaviour where it is safe, which
                # is the hash-mismatch branch below: the file being PRESENT is
                # itself the evidence that it belongs to this machine.
                reason="changed" if (origin and ours) else "absent",
                origin_host=origin_host,
            ))
            continue

        current_hash = hash_file(script_path)
        if current_hash != rec["hash"]:
            stale.append(StaleScript(
                node_id=rec["id"], path=rec["path"], stored_hash=rec["hash"],
                current_hash=current_hash,
                reason="changed" if ours else "diverged",
                origin_host=origin_host,
            ))
    return stale
