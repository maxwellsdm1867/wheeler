"""Regression test for issue #109: ensure_artifact missing date/updated on Dataset nodes.

Issue: `ensure_artifact` with `artifact_type="dataset"` creates Dataset nodes
without setting `date` or `updated` fields, making them invisible to `/wh:close`
orphan sweep which filters on `coalesce(n.updated, n.date)`.

The root cause: add_dataset() uses 'date_added' instead of 'date', and sets
no 'updated' field. The /wh:close command explicitly filters on
WHERE coalesce(n.updated, n.date) IS NOT NULL, so Dataset nodes vanish.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from wheeler.config import load_config
from wheeler.tools.graph_tools.mutations import add_dataset


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
async def test_dataset_node_has_date_not_date_added():
    """Test that add_dataset creates nodes with 'date' field, not 'date_added'.

    The /wh:close orphan sweep filters on:
        WHERE coalesce(n.updated, n.date) IS NOT NULL

    If a Dataset node only has 'date_added', it will not match and will be
    invisible to the sweep.
    """
    backend = FakeBackend()

    result_str = await add_dataset(
        backend,
        {
            "path": "/tmp/test.csv",
            "type": "csv",
            "description": "Test dataset",
            "tier": "generated",
        },
    )

    result = json.loads(result_str)
    assert "error" not in result, f"add_dataset failed: {result}"
    node_id = result["node_id"]

    created_node = backend.created_nodes[node_id]
    props = created_node["props"]

    assert props.get("date") is not None, (
        f"Dataset {node_id} is missing 'date' field. "
        "The /wh:close orphan sweep query uses "
        "WHERE coalesce(n.updated, n.date) IS NOT NULL, "
        "so nodes without both 'date' and 'updated' are invisible to the sweep."
    )

    assert props.get("updated") is not None, (
        f"Dataset {node_id} is missing 'updated'. The issue asks for 'updated' on "
        "create as well as on hash change, matching add_document and add_plan."
    )

    assert props.get("date_added") is None, (
        "Dataset should not have 'date_added' field; use 'date' and 'updated' "
        "to match the pattern used by Script, Document, Plan, etc."
    )


@pytest.mark.asyncio
async def test_dataset_passes_close_coalesce_filter():
    """Test that Dataset timestamp field matches what /wh:close expects.

    The close query explicitly checks:
        coalesce(n.updated, n.date) IS NOT NULL

    This means a node must have EITHER 'updated' OR 'date' (or both).
    Dataset currently fails this check.
    """
    backend = FakeBackend()

    result_str = await add_dataset(
        backend,
        {
            "path": "/tmp/analysis.csv",
            "type": "csv",
            "description": "Analysis data",
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
        f"Dataset {node_id} fails the /wh:close filter. "
        f"It has neither 'date' nor 'updated' set. "
        f"date={date_value}, updated={updated_value}. "
        "The close orphan sweep will miss this node."
    )


@pytest.mark.asyncio
async def test_dataset_aligns_with_other_artifact_types():
    """Verify timestamp field naming is consistent across artifact types.

    Script and Finding use 'date' only.
    Document and Plan use both 'date' and 'updated'.
    Dataset currently uses neither (it uses 'date_added').

    The fix should align Dataset with at least one existing pattern.
    """
    backend = FakeBackend()

    result_str = await add_dataset(
        backend,
        {
            "path": "/tmp/data.csv",
            "type": "csv",
            "description": "Test",
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
        "Dataset must have 'date' and/or 'updated' to pass /wh:close filter. "
        f"Currently: date={props.get('date')}, "
        f"updated={props.get('updated')}, "
        f"date_added={props.get('date_added')}"
    )

    if has_date_added:
        assert not has_date, (
            "Dataset should not use both 'date_added' and 'date'. "
            "Transition to 'date' (and optionally 'updated') to match other types."
        )


# ---------------------------------------------------------------------------
# Live-backend coverage of the ACTUAL entry point.
#
# Everything above drives add_dataset directly against a FakeBackend. The issue
# is reported against ensure_artifact, which is find-or-create and routes a
# changed hash through update_node, so the tests above cannot see either the
# real dispatch path or the "updated on hash change" half of the expectation.
# Without the two tests below, that half of the acceptance criteria has no
# durable guard at all and would regress silently.
#
# These take the regression suite's local-Neo4j fixtures: e2e_config points at a
# probed local instance, skip_without_neo4j skips cleanly when there is none,
# reset_driver_singleton clears the cached backend and its circuit breaker, and
# cleanup_test_nodes deletes exactly the nodes carrying this run's e2e_tag.
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
async def test_ensure_artifact_dataset_is_visible_to_close_sweep(e2e_config, tmp_path):
    """A Dataset registered via ensure_artifact is returned by the close sweep.

    This is the issue's own acceptance test: not "the node has a date property"
    but "the Phase 1.2 window query actually returns it".
    """
    from datetime import datetime, timedelta, timezone

    from wheeler.graph.driver import get_async_driver
    from wheeler.tools.graph_tools import execute_tool

    driver = get_async_driver(e2e_config)
    db = e2e_config.neo4j.database

    dataset = tmp_path / "issue_109_sweep.csv"
    dataset.write_text("a,b\n1,2\n")

    created = json.loads(
        await execute_tool(
            "ensure_artifact",
            {"path": str(dataset), "artifact_type": "dataset"},
            e2e_config,
        )
    )
    node_id = created.get("node_id")
    assert node_id, f"ensure_artifact did not create a node: {created}"
    await _tag_for_cleanup(driver, db, node_id)

    async with driver.session(database=db) as session:
        record = await (
            await session.run(
                "MATCH (d:Dataset {id: $id}) RETURN d.date AS date, d.updated AS updated",
                id=node_id,
            )
        ).single()
    assert record is not None, f"Dataset {node_id} not found in the graph"
    assert record["date"] not in ("", None), (
        f"Dataset {node_id} has no 'date', so coalesce(updated, date) is null "
        "and /wh:close cannot see it."
    )

    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    async with driver.session(database=db) as session:
        rows = [r["id"] async for r in await session.run(CLOSE_PHASE_1_2_QUERY, since=since)]

    assert node_id in rows, (
        f"Dataset {node_id} is NOT returned by the /wh:close Phase 1.2 window "
        "query, which is the exact failure reported in issue 109: the sweep "
        "reports zero remaining orphans while unlinked datasets exist."
    )


@pytest.mark.asyncio
async def test_ensure_artifact_refreshes_updated_on_hash_change(e2e_config, tmp_path):
    """Re-registering a changed file moves 'updated' forward and keeps 'date'.

    The issue asks for 'updated' on create AND on hash change. A dataset whose
    content changed must re-enter the sweep window, otherwise a re-registered
    file stays invisible even though it changed.
    """
    from wheeler.graph.driver import get_async_driver
    from wheeler.tools.graph_tools import execute_tool

    driver = get_async_driver(e2e_config)
    db = e2e_config.neo4j.database

    dataset = tmp_path / "issue_109_hash_change.csv"
    dataset.write_text("a,b\n1,2\n")

    first = json.loads(
        await execute_tool(
            "ensure_artifact",
            {"path": str(dataset), "artifact_type": "dataset"},
            e2e_config,
        )
    )
    node_id = first["node_id"]
    await _tag_for_cleanup(driver, db, node_id)

    async def _stamps():
        async with driver.session(database=db) as session:
            record = await (
                await session.run(
                    "MATCH (d:Dataset {id: $id}) "
                    "RETURN d.date AS date, d.updated AS updated, d.hash AS hash",
                    id=node_id,
                )
            ).single()
        return dict(record) if record else {}

    before = await _stamps()
    assert before.get("updated") not in ("", None), "no 'updated' stamped on create"

    dataset.write_text("a,b\n1,2\n3,4\n5,6\n")
    second = json.loads(
        await execute_tool(
            "ensure_artifact",
            {"path": str(dataset), "artifact_type": "dataset"},
            e2e_config,
        )
    )
    assert second["node_id"] == node_id, (
        "ensure_artifact created a SECOND node for the same path instead of "
        f"updating {node_id}: {second}"
    )

    after = await _stamps()
    assert after["hash"] != before["hash"], (
        "the file hash did not change, so this test proved nothing"
    )
    assert after["updated"] > before["updated"], (
        f"'updated' did not move forward on hash change: "
        f"{before['updated']} -> {after['updated']}. A changed dataset stays "
        "outside the /wh:close sweep window."
    )
    assert after["date"] == before["date"], (
        "'date' is the creation stamp and must not move on update: "
        f"{before['date']} -> {after['date']}"
    )
