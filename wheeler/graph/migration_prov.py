"""Wave 0 provenance migration: Analysis -> Script + Execution, relationship renames.

Standalone migration that runs against existing Neo4j databases BEFORE
the new provenance schema code is deployed.  Can also migrate local
knowledge/*.json files.

Usage (CLI):
    wh graph migrate-prov          # run full migration
    wh graph migrate-prov --dry-run  # preview without changes

Usage (Python):
    from wheeler.graph.migration_prov import (
        migrate_analysis_nodes,
        rename_relationships,
        migrate_knowledge_files,
    )
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id(prefix: str) -> str:
    """Generate a new node ID: prefix + 8 hex chars."""
    return f"{prefix}-{secrets.token_hex(4)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 1. Migrate Analysis nodes in Neo4j -> Script + Execution
# ---------------------------------------------------------------------------


async def migrate_analysis_nodes(config: WheelerConfig) -> dict:
    """Split every (:Analysis) node into (:Script) + (:Execution) in Neo4j.

    For each Analysis node:
    - Create a Script entity (the code)
    - Create an Execution activity (the act of running it)
    - Wire (exec)-[:USED]->(script)
    - Migrate all existing relationships to the Execution node
    - Delete the original Analysis node

    Returns a summary dict with counts.
    """
    from wheeler.graph.driver import get_async_driver

    driver = get_async_driver(config)
    db = config.neo4j.database
    project_tag = config.neo4j.project_tag

    # Build optional project filter clause
    ptag_where = ""
    params: dict = {}
    if project_tag:
        ptag_where = "WHERE a._wheeler_project = $props.ptag"
        params["ptag"] = project_tag

    # Fetch all Analysis nodes
    fetch_query = f"MATCH (a:Analysis) {ptag_where} RETURN a"
    async with driver.session(database=db) as session:
        result = await session.run(
            fetch_query,
            parameters={"props": params} if params else {},
        )
        records = [r async for r in result]

    migrated = 0
    errors = 0
    details: list[str] = []

    # Use a single session for all migrations (avoids per-node session overhead)
    async with driver.session(database=db) as session:
      for rec in records:
        a = dict(rec["a"])
        a_id = a.get("id", "unknown")
        try:
            script_id = _new_id("S")
            exec_id = _new_id("X")
            now = _now_iso()

            # Build Script properties
            script_props: dict = {
                "id": script_id,
                "path": a.get("script_path", ""),
                "hash": a.get("script_hash", ""),
                "language": a.get("language", ""),
                "version": a.get("language_version", ""),
                "tier": a.get("tier", "generated"),
                "date": a.get("date", now),
                "created": now,
                "updated": now,
            }
            if project_tag:
                script_props["_wheeler_project"] = project_tag

            # Build Execution properties
            executed_at = a.get("executed_at", "") or now
            exec_props: dict = {
                "id": exec_id,
                "kind": "script",
                "agent_id": "wheeler",
                "status": "completed",
                "started_at": executed_at,
                "ended_at": executed_at,
                "description": f"Migrated from Analysis {a_id}",
                "tier": a.get("tier", "generated"),
                "date": a.get("date", now),
                "created": now,
                "updated": now,
            }
            if project_tag:
                exec_props["_wheeler_project"] = project_tag
                # 1. Create Script node
                s_assignments = ", ".join(
                    f"{k}: $props.{k}" for k in script_props
                )
                await session.run(
                    f"CREATE (s:Script {{{s_assignments}}})",
                    parameters={"props": script_props},
                )

                # 2. Create Execution node
                x_assignments = ", ".join(
                    f"{k}: $props.{k}" for k in exec_props
                )
                await session.run(
                    f"CREATE (x:Execution {{{x_assignments}}})",
                    parameters={"props": exec_props},
                )

                # 3. Link (exec)-[:USED]->(script)
                await session.run(
                    "MATCH (x:Execution {id: $props.xid}), "
                    "(s:Script {id: $props.sid}) "
                    "CREATE (x)-[:USED]->(s)",
                    parameters={"props": {"xid": exec_id, "sid": script_id}},
                )

                # 4. Migrate outgoing USED_DATA: (a)-[:USED_DATA]->(d) -> (exec)-[:USED]->(d)
                await session.run(
                    "MATCH (a:Analysis {id: $props.aid})-[r:USED_DATA]->(d) "
                    "WITH a, r, d "
                    "MATCH (x:Execution {id: $props.xid}) "
                    "CREATE (x)-[:USED]->(d) "
                    "DELETE r",
                    parameters={"props": {"aid": a_id, "xid": exec_id}},
                )

                # 5. Migrate outgoing GENERATED: (a)-[:GENERATED]->(f)
                #    -> (f)-[:WAS_GENERATED_BY]->(exec) (FLIP!)
                await session.run(
                    "MATCH (a:Analysis {id: $props.aid})-[r:GENERATED]->(f) "
                    "WITH a, r, f "
                    "MATCH (x:Execution {id: $props.xid}) "
                    "CREATE (f)-[:WAS_GENERATED_BY]->(x) "
                    "DELETE r",
                    parameters={"props": {"aid": a_id, "xid": exec_id}},
                )

                # 6. Migrate incoming INFORMED: (p)-[:INFORMED]->(a)
                #    -> (exec)-[:USED]->(p)
                await session.run(
                    "MATCH (p)-[r:INFORMED]->(a:Analysis {id: $props.aid}) "
                    "WITH a, r, p "
                    "MATCH (x:Execution {id: $props.xid}) "
                    "CREATE (x)-[:USED]->(p) "
                    "DELETE r",
                    parameters={"props": {"aid": a_id, "xid": exec_id}},
                )

                # 7. Transfer any remaining outgoing relationships
                await session.run(
                    "MATCH (a:Analysis {id: $props.aid})-[r]->(t) "
                    "WITH a, r, t, type(r) AS rtype "
                    "MATCH (x:Execution {id: $props.xid}) "
                    "CALL (x, t, rtype) { "
                    "  WITH x, t, rtype "
                    "  FOREACH (_ IN CASE WHEN rtype = 'PRODUCED' THEN [1] ELSE [] END | "
                    "    CREATE (t)-[:WAS_GENERATED_BY]->(x)) "
                    "  FOREACH (_ IN CASE WHEN rtype <> 'PRODUCED' THEN [1] ELSE [] END | "
                    "    CREATE (x)-[:USED]->(t)) "
                    "} "
                    "DELETE r",
                    parameters={"props": {"aid": a_id, "xid": exec_id}},
                )

                # 8. Transfer any remaining incoming relationships
                await session.run(
                    "MATCH (s)-[r]->(a:Analysis {id: $props.aid}) "
                    "WITH a, r, s "
                    "MATCH (x:Execution {id: $props.xid}) "
                    "CREATE (x)-[:USED]->(s) "
                    "DELETE r",
                    parameters={"props": {"aid": a_id, "xid": exec_id}},
                )

                # 9. Delete the Analysis node
                await session.run(
                    "MATCH (a:Analysis {id: $props.aid}) DETACH DELETE a",
                    parameters={"props": {"aid": a_id}},
                )

            migrated += 1
            details.append(
                f"  {a_id} -> Script {script_id} + Execution {exec_id}"
            )
            logger.info("Migrated %s -> %s + %s", a_id, script_id, exec_id)

        except Exception as exc:
            errors += 1
            details.append(f"  ERROR migrating {a_id}: {exc}")
            logger.error("Failed to migrate %s: %s", a_id, exc)

    return {
        "analysis_nodes_found": len(records),
        "migrated": migrated,
        "errors": errors,
        "details": details,
    }


# ---------------------------------------------------------------------------
# 2. Rename relationships across the entire graph
# ---------------------------------------------------------------------------

# (old_type, new_type, flip_direction)
_RELATIONSHIP_RENAMES: list[tuple[str, str, bool]] = [
    ("USED_DATA", "USED", False),
    ("RAN_SCRIPT", "USED", False),
    ("GENERATED", "WAS_GENERATED_BY", True),
    ("PRODUCED", "WAS_GENERATED_BY", True),
    ("BASED_ON", "WAS_DERIVED_FROM", False),
    ("INFORMED", "WAS_INFORMED_BY", True),
    ("REFERENCED_IN", "CITES", False),
    ("STUDIED_IN", "RELEVANT_TO", False),
]


async def rename_relationships(config: WheelerConfig) -> dict:
    """Bulk rename old relationship types to PROV-standard names.

    Some relationships keep direction, others are flipped per the
    W3C PROV-DM dependency-pointing convention.

    Returns a summary dict with counts per relationship type.
    """
    from wheeler.graph.driver import get_async_driver

    driver = get_async_driver(config)
    db = config.neo4j.database
    project_tag = config.neo4j.project_tag

    counts: dict[str, int] = {}
    details: list[str] = []
    total = 0

    for old_type, new_type, flip in _RELATIONSHIP_RENAMES:
        try:
            # Build project-aware filter if needed
            if project_tag:
                # Filter: at least one endpoint belongs to this project
                where_clause = (
                    "WHERE (a._wheeler_project = $props.ptag "
                    "OR b._wheeler_project = $props.ptag) "
                )
                run_params: dict = {"props": {"ptag": project_tag}}
            else:
                where_clause = ""
                run_params = {"props": {}}

            if flip:
                # Create reversed edge, delete old
                query = (
                    f"MATCH (a)-[r:{old_type}]->(b) "
                    f"{where_clause}"
                    f"CREATE (b)-[:{new_type}]->(a) "
                    "DELETE r "
                    "RETURN count(r) AS cnt"
                )
            else:
                # Keep direction
                query = (
                    f"MATCH (a)-[r:{old_type}]->(b) "
                    f"{where_clause}"
                    f"CREATE (a)-[:{new_type}]->(b) "
                    "DELETE r "
                    "RETURN count(r) AS cnt"
                )

            async with driver.session(database=db) as session:
                result = await session.run(query, parameters=run_params)
                record = await result.single()
                cnt = record["cnt"] if record else 0

            direction = "FLIP" if flip else "keep"
            counts[f"{old_type} -> {new_type}"] = cnt
            total += cnt
            if cnt > 0:
                details.append(
                    f"  {old_type} -> {new_type} ({direction}): {cnt}"
                )
                logger.info(
                    "Renamed %d %s -> %s (%s)", cnt, old_type, new_type, direction
                )
            else:
                logger.debug("No %s relationships found", old_type)

        except Exception as exc:
            counts[f"{old_type} -> {new_type}"] = -1
            details.append(f"  ERROR {old_type} -> {new_type}: {exc}")
            logger.error("Failed to rename %s: %s", old_type, exc)

    return {
        "total_renamed": total,
        "counts": counts,
        "details": details,
    }


# ---------------------------------------------------------------------------
# 3. Migrate knowledge/*.json files (A-*.json -> S-*.json + X-*.json)
# ---------------------------------------------------------------------------


def migrate_knowledge_files(knowledge_path: Path) -> dict:
    """Migrate Analysis JSON files to Script + Execution JSON files.

    For each ``A-*.json`` in knowledge_path:
    - Read the AnalysisModel fields
    - Write a ``S-*.json`` (ScriptModel-shaped)
    - Write a ``X-*.json`` (ExecutionModel-shaped)
    - Delete the original ``A-*.json``

    Returns a summary dict with counts.
    """
    if not knowledge_path.is_dir():
        return {"found": 0, "migrated": 0, "errors": 0, "details": []}

    a_files = sorted(knowledge_path.glob("A-*.json"))
    migrated = 0
    errors = 0
    details: list[str] = []

    for a_file in a_files:
        try:
            raw = json.loads(a_file.read_text(encoding="utf-8"))

            # Validate it's actually an Analysis node
            if raw.get("type") != "Analysis":
                details.append(f"  SKIP {a_file.name}: type={raw.get('type')}")
                continue

            now = _now_iso()
            old_id = raw.get("id", a_file.stem)

            # Generate new IDs
            script_id = _new_id("S")
            exec_id = _new_id("X")

            # Build Script JSON
            script_data = {
                "id": script_id,
                "type": "Script",
                "path": raw.get("script_path", ""),
                "hash": raw.get("script_hash", ""),
                "language": raw.get("language", ""),
                "version": raw.get("language_version", ""),
                "tier": raw.get("tier", "generated"),
                "created": now,
                "updated": now,
                "tags": raw.get("tags", []),
            }

            # Build Execution JSON
            executed_at = raw.get("executed_at", "") or now
            exec_data = {
                "id": exec_id,
                "type": "Execution",
                "kind": "script",
                "agent_id": "wheeler",
                "status": "completed",
                "started_at": executed_at,
                "ended_at": executed_at,
                "description": f"Migrated from Analysis {old_id}",
                "tier": raw.get("tier", "generated"),
                "created": now,
                "updated": now,
                "tags": raw.get("tags", []),
            }

            # Atomic write: Script
            s_path = knowledge_path / f"{script_id}.json"
            s_tmp = s_path.with_suffix(".json.tmp")
            s_tmp.write_text(
                json.dumps(script_data, indent=2), encoding="utf-8"
            )
            s_tmp.rename(s_path)

            # Atomic write: Execution
            x_path = knowledge_path / f"{exec_id}.json"
            x_tmp = x_path.with_suffix(".json.tmp")
            x_tmp.write_text(
                json.dumps(exec_data, indent=2), encoding="utf-8"
            )
            x_tmp.rename(x_path)

            # Delete original
            a_file.unlink()

            migrated += 1
            details.append(
                f"  {old_id} -> Script {script_id} + Execution {exec_id}"
            )
            logger.info(
                "Migrated %s -> %s + %s", a_file.name, script_id, exec_id
            )

        except Exception as exc:
            errors += 1
            details.append(f"  ERROR {a_file.name}: {exc}")
            logger.error("Failed to migrate %s: %s", a_file.name, exc)

    return {
        "found": len(a_files),
        "migrated": migrated,
        "errors": errors,
        "details": details,
    }
