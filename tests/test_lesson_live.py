"""Opt-in real Neo4j check against an explicitly supplied isolated test server.

Run with WHEELER_LESSON_TEST_URI=bolt://127.0.0.1:<test-port>. Does not load
project credentials. Only a unique test namespace is written and cleaned up.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.test_lesson_flow import lesson_args
from wheeler.config import WheelerConfig
from wheeler.graph.driver import close_async_driver
from wheeler.graph.neo4j_backend import Neo4jBackend
from wheeler.search.retrieval import expand_search_results
from wheeler.tools import graph_tools


@pytest.mark.skipif(not os.environ.get("WHEELER_LESSON_TEST_URI"), reason="Needs explicit isolated Neo4j test URI")
async def test_real_neo4j_capture_neighbor_revision_retirement(tmp_path, monkeypatch):
    namespace = "lesson-test-" + uuid4().hex
    config = WheelerConfig(project_root=str(tmp_path), neo4j={
        "uri": os.environ["WHEELER_LESSON_TEST_URI"],
        "username": "neo4j", "password": "", "database": "neo4j", "project_tag": namespace,
    })
    await close_async_driver()
    backend = Neo4jBackend(config)
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=backend))
    try:
        for suffix in ("database", "dataset"):
            path = tmp_path / f"{suffix}.sqlite"
            path.touch()
            result = json.loads(await graph_tools.execute_tool("add_dataset", {
                "id": f"D-{suffix}", "path": str(path), "type": "sqlite", "description": suffix,
            }, config))
            assert "error" not in result, result
        await graph_tools.execute_tool("link_nodes", {
            "source_id": "D-dataset", "target_id": "D-database", "relationship": "RELEVANT_TO",
        }, config)
        args = lesson_args(target_ids=["D-database"], source_ids=[])
        saved = json.loads(await graph_tools.execute_tool("capture_lesson", args, config))
        assert "error" not in saved, saved
        skill = await backend.get_node("Document", saved["node_id"])
        assert skill["skill_state"] == "accepted"
        assert Path(saved["path"]).is_file()
        result = await expand_search_results([{"id": "D-dataset", "type": "Dataset"}], config, max_hops_prov=1)
        assert result["linked_skills_status"] == "complete", result
        assert [s["id"] for s in result["linked_skills"]] == [saved["node_id"]]
        assert "## Benchmark task" not in json.dumps(result)
        # Typed list and compact-context paths must not require a manual
        # follow-up show_node just to discover that procedures exist.
        listing = json.loads(await graph_tools.execute_tool("query_datasets", {"limit": 10}, config))
        assert [s["id"] for s in listing["linked_skills"]] == [saved["node_id"]]
        from wheeler import mcp_core

        monkeypatch.setattr(mcp_core, "_config", config)
        raw = await mcp_core.run_cypher(
            f"MATCH (d:Dataset {{id: 'D-database', _wheeler_project: '{namespace}'}}) RETURN d"
        )
        assert raw["count"] == 1
        assert [s["id"] for s in raw["linked_skills"]] == [saved["node_id"]]
        # Exercise the host-facing MCP serialization, not only the Python
        # wrapper: Neo4j nodes must survive alongside the discovery metadata.
        tool_result = await mcp_core.mcp.call_tool("run_cypher", {"query":
            f"MATCH (d:Dataset {{id: 'D-database', _wheeler_project: '{namespace}'}}) RETURN d"
        })
        delivered = json.loads(tool_result.content[0].text)
        assert delivered["count"] == 1
        assert [s["id"] for s in delivered["linked_skills"]] == [saved["node_id"]]
        scalar = await mcp_core.run_cypher(
            f"MATCH (d:Dataset {{id: 'D-database', _wheeler_project: '{namespace}'}}) RETURN d.id AS id"
        )
        assert scalar["linked_skills"] == []
        assert scalar["linked_skills_status"] == "not_checked"
        replay = json.loads(await graph_tools.execute_tool("capture_lesson", args, config))
        assert replay["status"] == "unchanged", replay
        revised = json.loads(await graph_tools.execute_tool("capture_lesson", {
            **args, "supersedes": saved["node_id"], "instructions": args["instructions"] + "\nCheck NULL keys.",
        }, config))
        assert "error" not in revised, revised
        result = await expand_search_results([{"id": "D-database", "type": "Dataset"}], config, max_hops_prov=1)
        assert [s["id"] for s in result["linked_skills"]] == [revised["node_id"]]
        retired = json.loads(await graph_tools.execute_tool("retire_skill", {
            "node_id": revised["node_id"], "reason": "Test retirement",
        }, config))
        assert "error" not in retired, retired
        result = await expand_search_results([{"id": "D-database", "type": "Dataset"}], config, max_hops_prov=1)
        assert result["linked_skills"] == []
    finally:
        await backend.run_cypher("MATCH (n {_wheeler_project: $tag}) DETACH DELETE n", {"tag": namespace})
        await close_async_driver()
