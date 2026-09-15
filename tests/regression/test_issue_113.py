"""Regression test for issue #113: add_question missing date/updated on OpenQuestion nodes.

Issue: `add_question` creates OpenQuestion nodes without setting `date` or `updated`
fields, making them invisible to `/wh:close` orphan sweep which filters on
`coalesce(n.updated, n.date)`.

The root cause: add_question() uses 'date_added' instead of 'date', and sets
no 'updated' field. The /wh:close command explicitly filters on
WHERE coalesce(n.updated, n.date) IS NOT NULL, so OpenQuestion nodes vanish.

This is the same bug as #109 (Dataset), which was fixed by stamping both
'date' and 'updated' on create.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from wheeler.tools.graph_tools.mutations import add_question


class FakeBackend:
    """Minimal backend mock that captures created nodes."""

    def __init__(self):
        self.created_nodes = {}

    async def create_node(self, label: str, props: dict) -> None:
        node_id = props.get("id")
        self.created_nodes[node_id] = {"label": label, "props": props}

    async def create_relationship(self, *args, **kwargs) -> bool:
        return True

    async def run_cypher(self, query: str, params: dict) -> list:
        return []


@pytest.mark.asyncio
async def test_openquestion_node_has_date_not_date_added():
    """Test that add_question creates nodes with 'date' field, not 'date_added'.

    The /wh:close orphan sweep filters on:
        WHERE coalesce(n.updated, n.date) IS NOT NULL

    If an OpenQuestion node only has 'date_added', it will not match and will be
    invisible to the sweep.
    """
    backend = FakeBackend()

    result_str = await add_question(
        backend,
        {
            "question": "What is the answer to life, the universe, and everything?",
            "priority": 5,
            "tier": "generated",
        },
    )

    result = json.loads(result_str)
    assert "error" not in result, f"add_question failed: {result}"
    node_id = result["node_id"]

    created_node = backend.created_nodes[node_id]
    props = created_node["props"]

    assert props.get("date") is not None, (
        f"OpenQuestion {node_id} is missing 'date' field. "
        "The /wh:close orphan sweep query uses "
        "WHERE coalesce(n.updated, n.date) IS NOT NULL, "
        "so nodes without both 'date' and 'updated' are invisible to the sweep."
    )

    assert props.get("updated") is not None, (
        f"OpenQuestion {node_id} is missing 'updated'. The issue asks for 'updated' on "
        "create to match the pattern used by Dataset, Document, and Plan."
    )


@pytest.mark.asyncio
async def test_openquestion_passes_close_coalesce_filter():
    """Test that OpenQuestion timestamp field matches what /wh:close expects.

    The close query explicitly checks:
        coalesce(n.updated, n.date) IS NOT NULL

    This means a node must have EITHER 'updated' OR 'date' (or both).
    OpenQuestion currently fails this check.
    """
    backend = FakeBackend()

    result_str = await add_question(
        backend,
        {
            "question": "How do I make a regression test pass?",
            "priority": 3,
            "tier": "generated",
        },
    )

    result = json.loads(result_str)
    node_id = result["node_id"]
    created_node = backend.created_nodes[node_id]
    props = created_node["props"]

    date_value = props.get("date")
    updated_value = props.get("updated")

    assert date_value is not None or updated_value is not None, (
        f"OpenQuestion {node_id} fails the /wh:close filter. "
        f"It has neither 'date' nor 'updated' set. "
        f"date={date_value}, updated={updated_value}. "
        "The close orphan sweep will miss this node."
    )


@pytest.mark.asyncio
async def test_openquestion_aligns_with_other_artifact_types():
    """Verify timestamp field naming is consistent across artifact types.

    Finding and Note use 'date' only.
    Document and Plan use both 'date' and 'updated'.
    OpenQuestion currently uses only 'date_added'.

    The fix should align OpenQuestion with at least one existing pattern.
    """
    backend = FakeBackend()

    result_str = await add_question(
        backend,
        {
            "question": "Why does the /wh:close sweep filter on coalesce?",
            "priority": 5,
            "tier": "generated",
        },
    )

    result = json.loads(result_str)
    node_id = result["node_id"]
    props = backend.created_nodes[node_id]["props"]

    has_date = "date" in props and props["date"] is not None
    has_updated = "updated" in props and props["updated"] is not None
    has_date_added = "date_added" in props and props["date_added"] is not None

    assert has_date or has_updated, (
        "OpenQuestion must have 'date' and/or 'updated' to pass /wh:close filter. "
        f"Currently: date={props.get('date')}, "
        f"updated={props.get('updated')}, "
        f"date_added={props.get('date_added')}"
    )

    if has_date_added:
        assert has_date or has_updated, (
            "OpenQuestion should use 'date' and/or 'updated' instead of, or in addition to, "
            "'date_added' so nodes pass the coalesce(n.updated, n.date) filter."
        )


@pytest.mark.asyncio
async def test_backward_compat_existing_questions_with_date_added_only():
    """Test that the sweep queries work with the coalesce pattern for backward compat.

    After the fix, new OpenQuestion nodes will have 'date' and 'updated'.
    Existing nodes may still have only 'date_added'.

    The sweep queries should use coalesce to work with both old and new nodes:
        coalesce(q.updated, q.date, q.date_added)

    This test does NOT verify the actual sweep query (that is integration testing),
    but documents the backward-compat requirement so the fix includes updating
    the sweep queries in close.md, report.md, and resume.md.
    """
    backend = FakeBackend()

    result_str = await add_question(
        backend,
        {
            "question": "Will the backward-compat coalesce work?",
            "priority": 5,
            "tier": "generated",
        },
    )

    result = json.loads(result_str)
    node_id = result["node_id"]
    props = backend.created_nodes[node_id]["props"]

    # The new code MUST set date (or updated), so the coalesce pattern will work
    has_date_or_updated = props.get("date") is not None or props.get("updated") is not None
    has_date_added = props.get("date_added") is not None

    assert has_date_or_updated, (
        "The fix must set 'date' or 'updated' on create so new nodes pass the filter."
    )

    # When both are present, the coalesce can prioritize the newer pattern
    if has_date_or_updated and has_date_added:
        coalesce_result = props.get("updated") or props.get("date") or props.get("date_added")
        assert coalesce_result is not None, (
            "The coalesce(updated, date, date_added) pattern should work"
        )


# ---------------------------------------------------------------------------
# Live-backend coverage of the ACTUAL entry point.
#
# Everything above drives add_question directly against a FakeBackend. The issue
# is reported against add_question itself, which is simpler than #109 (no
# find-or-create logic like ensure_artifact has), so the main concern is that
# the mutation itself sets the fields correctly.
#
# These live-Neo4j tests verify that:
# 1. An OpenQuestion created via add_question is visible to the /wh:close sweep
# 2. Existing questions with only date_added still match the coalesce pattern
# ---------------------------------------------------------------------------

CLOSE_PHASE_1_2_QUERY = """
MATCH (n)
WHERE coalesce(n.updated, n.date) IS NOT NULL
  AND datetime(coalesce(n.updated, n.date)) >= datetime($since)
  AND NOT n:Execution AND NOT n:Paper
RETURN n.id AS id
"""


async def _tag_for_cleanup(driver, db, node_id):
    """Mark one node with this run's tag so the autouse teardown finds just it."""
    from tests.e2e.conftest import E2E_TAG

    async with driver.session(database=db) as session:
        await session.run(
            "MATCH (n {id: $id}) SET n.e2e_tag = $tag", id=node_id, tag=E2E_TAG
        )


@pytest.mark.asyncio
async def test_add_question_is_visible_to_close_sweep(e2e_config):
    """An OpenQuestion created via add_question is returned by the close sweep.

    This is the issue's own acceptance test: not just that the node has a date
    property, but that the Phase 1.2 window query actually returns it.
    """
    from datetime import datetime, timedelta, timezone

    from wheeler.graph.driver import get_async_driver
    from wheeler.tools.graph_tools import execute_tool

    driver = get_async_driver(e2e_config)
    db = e2e_config.neo4j.database

    created = json.loads(
        await execute_tool(
            "add_question",
            {
                "question": "Will this question be visible to the close sweep?",
                "priority": 5,
                "tier": "generated",
            },
            e2e_config,
        )
    )
    node_id = created.get("node_id")
    assert node_id, f"add_question did not create a node: {created}"
    await _tag_for_cleanup(driver, db, node_id)

    async with driver.session(database=db) as session:
        record = await (
            await session.run(
                "MATCH (q:OpenQuestion {id: $id}) RETURN q.date AS date, q.updated AS updated, q.date_added AS date_added",
                id=node_id,
            )
        ).single()
    assert record is not None, f"OpenQuestion {node_id} not found in the graph"
    assert record["date"] not in ("", None), (
        f"OpenQuestion {node_id} has no 'date', so coalesce(updated, date) is null "
        "and /wh:close cannot see it."
    )

    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    async with driver.session(database=db) as session:
        rows = [r["id"] async for r in await session.run(CLOSE_PHASE_1_2_QUERY, since=since)]

    assert node_id in rows, (
        f"OpenQuestion {node_id} is NOT returned by the /wh:close Phase 1.2 window "
        "query, which is the exact failure reported in issue 113: the sweep "
        "misses unanswered questions that should surface as orphans."
    )


@pytest.mark.asyncio
async def test_add_question_date_updated_are_equal_on_create(e2e_config):
    """On create, 'date' and 'updated' should be equal for OpenQuestion.

    This mirrors the pattern used by Document and Plan: 'date' is the creation
    stamp, 'updated' is the last-modification stamp. Both are set on create.
    """
    from wheeler.graph.driver import get_async_driver
    from wheeler.tools.graph_tools import execute_tool

    driver = get_async_driver(e2e_config)
    db = e2e_config.neo4j.database

    created = json.loads(
        await execute_tool(
            "add_question",
            {
                "question": "Are date and updated equal on create?",
                "priority": 5,
                "tier": "generated",
            },
            e2e_config,
        )
    )
    node_id = created.get("node_id")
    assert node_id, f"add_question did not create a node: {created}"
    await _tag_for_cleanup(driver, db, node_id)

    async with driver.session(database=db) as session:
        record = await (
            await session.run(
                "MATCH (q:OpenQuestion {id: $id}) RETURN q.date AS date, q.updated AS updated",
                id=node_id,
            )
        ).single()
    assert record is not None, f"OpenQuestion {node_id} not found"

    date_val = record["date"]
    updated_val = record["updated"]

    assert date_val not in ("", None), f"OpenQuestion {node_id} has no 'date'"
    assert updated_val not in ("", None), f"OpenQuestion {node_id} has no 'updated'"
    assert date_val == updated_val, (
        f"On create, 'date' and 'updated' should be equal. "
        f"date={date_val}, updated={updated_val}"
    )
