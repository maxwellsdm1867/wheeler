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

    assert props.get("updated") is None or props.get("updated") is not None, (
        "If 'updated' is set, that is also acceptable for the close filter"
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
