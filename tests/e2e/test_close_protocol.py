"""E2E tests for the /wh:close protocol Cypher queries.

Issue #25: the close.md "Find Recent Entities" / "Find Orphan Entities"
queries previously referenced a non-existent `n.created` property and used
epochMillis arithmetic against ISO datetime strings, returning 0 rows on
any real graph.

This test simulates the exact tool-call sequence /wh:close prescribes:
  1. Create a Plan via ensure_artifact (mirrors a session that just made one)
  2. Run the EXACT Cypher from close.md section 1 (recent entities)
  3. Assert the new Plan appears
  4. Run the EXACT Cypher from close.md section 2 (orphan entities)
  5. Assert the new Plan appears (no Execution link yet)

Run: python -m pytest tests/e2e/test_close_protocol.py -v
Requires: Neo4j running on localhost:7687
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.conftest import E2E_TAG


# Cypher queries copied verbatim from .claude/commands/wh/close.md.
# If close.md changes, these literals MUST be updated and the test re-run.
RECENT_ENTITIES_CYPHER = """
MATCH (n)
WHERE coalesce(n.updated, n.date) IS NOT NULL
  AND datetime(coalesce(n.updated, n.date)) >= datetime() - duration({hours: 4})
  AND NOT n:Execution AND NOT n:Paper
RETURN n.id AS id, labels(n)[0] AS type, n.title AS title,
       coalesce(n.updated, n.date) AS timestamp
ORDER BY timestamp
""".strip()

ORPHAN_ENTITIES_CYPHER = """
MATCH (n)
WHERE coalesce(n.updated, n.date) IS NOT NULL
  AND datetime(coalesce(n.updated, n.date)) >= datetime() - duration({hours: 4})
  AND NOT n:Execution AND NOT n:Paper
  AND NOT (n)-[:WAS_GENERATED_BY]->(:Execution)
RETURN n.id AS id, labels(n)[0] AS type, n.title AS title,
       coalesce(n.updated, n.date) AS timestamp
ORDER BY timestamp
""".strip()


async def _tag(driver, db, node_id):
    """Tag a node for cleanup after test."""
    async with driver.session(database=db) as session:
        await session.run(
            "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
            id=node_id, tag=E2E_TAG,
        )


async def _run_cypher(driver, db, query: str) -> list[dict]:
    """Run a read-only Cypher query and return list of records as dicts."""
    async with driver.session(database=db) as session:
        result = await session.run(query)
        return [dict(r) async for r in result]


class TestCloseProtocolCypher:
    """The exact Cypher in .claude/commands/wh/close.md must return real rows."""

    @pytest.mark.asyncio
    async def test_close_md_recent_entities_query_finds_recent_plan(
        self, sandbox, e2e_config
    ):
        """Section 1 Cypher (recent entities) returns a freshly-created Plan."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create a plan file + register via ensure_artifact (mirrors /wh:plan)
        plan_file = sandbox / ".plans" / "e2e-close-recent.md"
        plan_file.write_text(
            "---\ninvestigation: close-recent\nstatus: draft\n---\n"
            "# Close-Protocol Recent Plan\n## Objective\nVerify recent-query.\n"
        )

        plan = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: close-protocol recent plan",
             "status": "draft"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        await _tag(driver, db, plan_id)

        # Run the EXACT Cypher from close.md section 1
        rows = await _run_cypher(driver, db, RECENT_ENTITIES_CYPHER)
        ids = [r["id"] for r in rows]
        assert plan_id in ids, (
            f"close.md 'Find Recent Entities' Cypher did not return new Plan "
            f"{plan_id}. Got rows: {rows}"
        )

        # Cleanup files
        plan_file.unlink(missing_ok=True)
        (Path(e2e_config.knowledge_path) / f"{plan_id}.json").unlink(missing_ok=True)
        (Path(e2e_config.synthesis_path) / f"{plan_id}.md").unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_close_md_orphan_query_finds_recent_plan(
        self, sandbox, e2e_config
    ):
        """Section 2 Cypher (orphan entities) returns a Plan with no Execution link.

        Note: once issue #24 ships (ensure_artifact(plan) auto-provenance), this
        assertion would change to "does not appear" because plans would auto-link
        to a creation Execution. For now, a plan-only graph state IS an orphan.
        """
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create a plan via add_plan (no Execution provenance attached)
        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: close-protocol orphan plan", "status": "draft"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        await _tag(driver, db, plan_id)

        # Run the EXACT Cypher from close.md section 2
        rows = await _run_cypher(driver, db, ORPHAN_ENTITIES_CYPHER)
        ids = [r["id"] for r in rows]
        assert plan_id in ids, (
            f"close.md 'Find Orphan Entities' Cypher did not return new "
            f"orphan Plan {plan_id}. Got rows: {rows}"
        )

        # Sanity: the row carries title + type + a non-null timestamp string
        row = next(r for r in rows if r["id"] == plan_id)
        assert row["type"] == "Plan"
        assert row["title"] == "E2E: close-protocol orphan plan"
        assert row["timestamp"] is not None
        assert isinstance(row["timestamp"], str), (
            f"Timestamp should be ISO 8601 string, got {type(row['timestamp'])}"
        )

        # Cleanup files
        (Path(e2e_config.knowledge_path) / f"{plan_id}.json").unlink(missing_ok=True)
        (Path(e2e_config.synthesis_path) / f"{plan_id}.md").unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_close_md_orphan_query_excludes_node_with_execution_link(
        self, e2e_config
    ):
        """A Finding linked WAS_GENERATED_BY -> Execution should NOT show as orphan."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create a finding + execution + WAS_GENERATED_BY link
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E: non-orphan finding for close-protocol",
             "confidence": 0.7},
            e2e_config,
        ))
        finding_id = finding["node_id"]
        await _tag(driver, db, finding_id)

        execution = json.loads(await execute_tool(
            "add_execution",
            {"kind": "script_run",
             "description": "E2E: execution for close-protocol non-orphan"},
            e2e_config,
        ))
        exec_id = execution["node_id"]
        await _tag(driver, db, exec_id)

        await execute_tool(
            "link_nodes",
            {"source_id": finding_id, "target_id": exec_id,
             "relationship": "WAS_GENERATED_BY"},
            e2e_config,
        )

        # Run the orphan Cypher: finding should NOT appear
        rows = await _run_cypher(driver, db, ORPHAN_ENTITIES_CYPHER)
        ids = [r["id"] for r in rows]
        assert finding_id not in ids, (
            f"Finding {finding_id} has WAS_GENERATED_BY -> Execution but the "
            f"orphan Cypher still returned it. Got rows: {rows}"
        )

        # Cleanup files
        for nid in (finding_id, exec_id):
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)
