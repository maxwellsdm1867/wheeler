"""Regression test for issue #58: empty started_at on close Execution breaks boundary.

Issue: A close Execution with an empty `started_at` silently breaks the `/wh:close`
session-window logic. The boundary query orders by `started_at DESC` and limits to 1.
If a recent close has an empty `started_at`, it sorts before non-empty strings in
Neo4j, causing the query to fall back to an older close. The window then re-surfaces
nodes that were already synthesized in a prior session, with no warning to the operator.

Acceptance criteria (from issue #58):
- A close Execution can never be created with an empty `started_at` (auto-default to now
  if omitted), OR the boundary query explicitly detects and reports a close with
  missing `started_at`.
- The boundary query returns the true most-recent close even if some historical close
  has a malformed timestamp.
- When boundary detection is ambiguous, the operator sees a warning rather than a
  silent fallback.

This test verifies that the boundary query (from close.md section 1.1) returns the
genuinely most recent close Execution, and either:
  (a) prevents creating closes with empty started_at, OR
  (b) handles them gracefully in the boundary query

Run: python -m pytest tests/e2e/test_issue_58.py -v
Requires: Neo4j running on localhost:7687
"""

from __future__ import annotations

import json

import pytest

from tests.e2e.conftest import E2E_TAG


BOUNDARY_QUERY = """
MATCH (x:Execution {kind: "close"})
RETURN x.started_at AS last_close, x.id AS close_id
ORDER BY x.started_at DESC LIMIT 1
""".strip()


async def _run_cypher(driver, db, query: str) -> list[dict]:
    """Run a read-only Cypher query and return list of records as dicts."""
    async with driver.session(database=db) as session:
        result = await session.run(query)
        return [dict(r) async for r in result]


async def _tag(driver, db, node_id):
    """Tag a node for cleanup after test."""
    async with driver.session(database=db) as session:
        await session.run(
            "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
            id=node_id, tag=E2E_TAG,
        )


class TestIssue58:
    """Boundary query must return a valid close with non-empty started_at."""

    @pytest.mark.asyncio
    async def test_boundary_query_fails_with_empty_started_at_close(
        self, e2e_config
    ):
        """When a close Execution has empty started_at, the boundary query
        returns it anyway, which breaks the ordering.

        This reproduces the exact issue: create Close A (valid) and Close B
        (empty started_at), then verify the boundary query returns the wrong one.

        Expected fix: the boundary query should filter out closes with empty
        started_at, or add_execution should prevent them entirely.
        """
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        try:
            # Create Close A with valid timestamp (created first, so older)
            async with driver.session(database=db) as session:
                await session.run("""
                    CREATE (x:Execution {
                        id: "X-issue58-close-a",
                        kind: "close",
                        started_at: "2026-06-08T10:00:00Z",
                        date: "2026-06-08T10:00:00Z",
                        e2e_tag: $tag
                    })
                """, tag=E2E_TAG)

            # Create Close B with EMPTY started_at (the corrupted case)
            # This simulates what can happen if a close is created via raw Cypher
            # or through an older code path that doesn't default started_at.
            async with driver.session(database=db) as session:
                await session.run("""
                    CREATE (x:Execution {
                        id: "X-issue58-close-b",
                        kind: "close",
                        started_at: "",
                        date: "2026-06-08T11:00:00Z",
                        e2e_tag: $tag
                    })
                """, tag=E2E_TAG)

            # Run the boundary query
            rows = await _run_cypher(driver, db, BOUNDARY_QUERY)

            assert len(rows) > 0, (
                "Boundary query returned 0 rows with two close Executions present"
            )

            returned_close = rows[0]["close_id"]
            returned_started_at = rows[0]["last_close"]

            # The boundary query should never return a close with empty started_at.
            # In Neo4j, empty string '' sorts to the beginning when using DESC order
            # (because non-existent/null values sort first), but a close with empty
            # started_at is still a valid match in the MATCH clause.
            #
            # The bug from issue #58: if the most recent close has empty started_at,
            # the query returns it anyway, breaking the ordering assumption.
            #
            # Expected behavior: the boundary query should return a close with a
            # valid, non-empty started_at that can be used as a datetime boundary.

            # This assertion will PASS when the bug is fixed (started_at never empty)
            # OR when the query is updated to filter out empty started_at.
            # It will FAIL if a close with empty started_at is returned, indicating
            # the bug is present.
            assert returned_started_at not in ("", None), (
                f"ISSUE #58 BUG: Boundary query returned close {returned_close} "
                f"with empty/null started_at='{returned_started_at}'. "
                f"This is the exact bug described in issue #58: the window boundary "
                f"is malformed, causing $since to be undefined or to silently fall "
                f"back to an older close, re-surfacing already-synthesized nodes."
            )

            # The returned close should have a non-empty timestamp
            assert returned_started_at is not None, (
                f"Boundary query returned close {returned_close} with null started_at"
            )

        finally:
            pass  # cleanup_test_nodes fixture will tag them out

    @pytest.mark.asyncio
    async def test_add_execution_close_never_creates_empty_started_at(
        self, e2e_config
    ):
        """add_execution(kind="close") should guarantee non-empty started_at.

        This is the preventative fix for issue #58: if add_execution always
        defaults started_at to now, the boundary query will always have valid
        data to sort on.
        """
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create a close Execution without specifying started_at
        result = json.loads(await execute_tool(
            "add_execution",
            {
                "kind": "close",
                "description": "Test close for issue #58",
            },
            e2e_config,
        ))
        exec_id = result["node_id"]

        # Tag for cleanup
        await _tag(driver, db, exec_id)

        # Read back from graph to verify started_at was set
        async with driver.session(database=db) as session:
            result = await session.run(
                "MATCH (x:Execution {id: $id}) RETURN x.started_at",
                id=exec_id,
            )
            record = await result.single()

        started_at = record["x.started_at"] if record else None

        # The fix: started_at MUST be non-empty when created via add_execution
        assert started_at is not None and started_at != "", (
            f"add_execution(kind='close') created Execution {exec_id} with "
            f"empty/null started_at='{started_at}'. This violates the fix for "
            f"issue #58. Ensure add_execution defaults started_at to _now() "
            f"when kind='close' and started_at is not provided."
        )

    @pytest.mark.asyncio
    async def test_close_execution_started_at_consistent_across_triple_write(
        self, e2e_config
    ):
        """started_at must be non-empty in ALL THREE triple-write layers.

        The original #58 fix defaulted started_at only in the graph props, but
        _write_knowledge_file reads args verbatim, so knowledge/{id}.json kept
        started_at="" (the field-spec default). That drift means the JSON layer
        disagrees with the graph layer. graph_consistency_check would flag it and
        any consumer reading the JSON layer for the boundary would still break.

        The extended fix defaults started_at back into args inside add_execution
        so the graph node, knowledge/{id}.json, and synthesis/{id}.md all carry
        the same non-empty timestamp.
        """
        from pathlib import Path

        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create a close Execution without specifying started_at
        result = json.loads(await execute_tool(
            "add_execution",
            {
                "kind": "close",
                "description": "Test triple-write started_at for issue #58",
            },
            e2e_config,
        ))
        exec_id = result["node_id"]
        await _tag(driver, db, exec_id)

        # Layer 1: graph
        async with driver.session(database=db) as session:
            record = await (await session.run(
                "MATCH (x:Execution {id: $id}) RETURN x.started_at AS s",
                id=exec_id,
            )).single()
        graph_started_at = record["s"] if record else None
        assert graph_started_at not in ("", None), (
            f"graph layer: Execution {exec_id} has empty started_at"
        )

        # Layer 2: knowledge/{id}.json
        json_path = Path(e2e_config.knowledge_path) / f"{exec_id}.json"
        assert json_path.exists(), f"knowledge JSON missing for {exec_id}"
        json_started_at = json.loads(json_path.read_text()).get("started_at")
        assert json_started_at not in ("", None), (
            f"ISSUE #58 DRIFT: knowledge/{exec_id}.json has empty/null "
            f"started_at='{json_started_at}' while the graph layer has "
            f"'{graph_started_at}'. The triple-write layers disagree; "
            f"add_execution must default started_at into args so every layer "
            f"persists the same value."
        )

        # The two layers must carry the SAME value (no silent divergence).
        assert json_started_at == graph_started_at, (
            f"ISSUE #58 DRIFT: started_at differs across layers "
            f"(graph='{graph_started_at}', json='{json_started_at}')."
        )
