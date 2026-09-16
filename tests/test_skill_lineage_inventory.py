"""Writer inventory and immutable revision heads, separate from activation."""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests import test_lesson_flow as flow
from tests.test_skill_discovery import save_skill
from wheeler.config import WheelerConfig
from wheeler.skill_discovery import discover_skills
from wheeler.tools import graph_tools

lesson_project = flow.lesson_project


@pytest.mark.parametrize("action", ["new-from-ancestor", "accept-intermediate", "accept-root-candidate", "retire-then-accept-intermediate"])
async def test_accepted_descendant_blocks_stale_branch_and_candidate_promotion(lesson_project, action):
    config, _, _ = lesson_project
    a = await flow.capture(config, accepted=action != "accept-root-candidate")
    b = await flow.capture(config, accepted=False, supersedes=a["node_id"], instructions="Proposed check")
    c = await flow.capture(config, supersedes=b["node_id"], instructions="Approved refined check")
    if action == "retire-then-accept-intermediate":
        await graph_tools.execute_tool("retire_skill", {"node_id": c["node_id"], "reason": "Obsolete"}, config)
    if action == "new-from-ancestor":
        result = await graph_tools.execute_tool("capture_lesson", flow.lesson_args(
            supersedes=a["node_id"], instructions="Stale alternate", accepted=False,
        ), config)
    else:
        target = a if action == "accept-root-candidate" else b
        result = await graph_tools.execute_tool("accept_skill", {"node_id": target["node_id"]}, config)
    assert json.loads(result)["error"] == "invalid_lesson"
    # The real current head remains revisable, including explicit replacement
    # of retired guidance. The writer requires clear restoration intent.
    latest = await flow.capture(config, supersedes=c["node_id"], instructions="Next approved correction")
    assert latest["version"] == 4


@pytest.mark.parametrize("state", ["candidate", "retracted", "incomplete"])
async def test_same_name_and_scope_never_creates_independent_inactive_duplicate(lesson_project, state):
    config, _, _ = lesson_project
    a = await flow.capture(config, accepted=False)
    if state != "candidate":
        await graph_tools.execute_tool("update_node", {"node_id": a["node_id"], "skill_state": state}, config)
    result = json.loads(await graph_tools.execute_tool("capture_lesson", flow.lesson_args(instructions="Changed procedure"), config))
    assert result["error"] == "skill_exists"
    assert a["node_id"] in result["existing_ids"]


async def test_incomplete_revision_must_be_repaired_before_extending_lineage(lesson_project):
    config, _, _ = lesson_project
    a = await flow.capture(config)
    await graph_tools.execute_tool("update_node", {"node_id": a["node_id"], "skill_state": "incomplete"}, config)
    result = json.loads(await graph_tools.execute_tool("capture_lesson", flow.lesson_args(
        supersedes=a["node_id"], instructions="Premature revision",
    ), config))
    assert result["error"] == "invalid_lesson"
    assert "Repair" in result["message"]


async def test_inventory_requires_explicit_metadata_only_mode(monkeypatch):
    from wheeler import mcp_core
    from tests.live_schema import live_tools

    result = await mcp_core.show_node(node_id="D-a", skill_inventory=True)
    assert "error" in result
    schema = (await live_tools())["show_node"].parameters["properties"]
    assert schema["skill_inventory"]["type"] == "boolean"


@pytest.mark.parametrize("act_id", ["ask", "chat", "pair", "execute", "discuss", "plan", "resume", "write", "compile"])
def test_consumer_gate_never_requests_writer_inventory_or_global_fallback(act_id):
    from wheeler import acts

    body = acts.find_act(act_id).body
    assert "A complete empty `linked_skills` list ends this gate" in body
    assert "without searching native or global skill catalogs" in body
    assert "do not ask the scientist whether a skill is useful" in body
    assert "same skill ID and version" in body
    assert "Ordinary consumers never request writer inventory" in body
    assert "skill_inventory=true" not in body


def test_writer_inventory_covers_candidates_without_reinstating_retired_history():
    from wheeler import acts

    body = acts.find_act("lesson").body
    assert "skill_inventory=true" in body and "skill_inventory_next_page" in body
    assert "plausible active or candidate matches" in body
    assert "never silently reinstate" in body
    assert "For an unchanged candidate explicitly endorsed" in body
    assert "revise it with `supersedes` rather than inventing another name" in body


@pytest.fixture
async def live_project(tmp_path, monkeypatch):
    from wheeler import mcp_core
    from wheeler.graph.driver import close_async_driver
    from wheeler.graph.neo4j_backend import Neo4jBackend

    uri = os.environ.get("WHEELER_LESSON_TEST_URI")
    if not uri:
        pytest.skip("Needs explicit isolated Neo4j test URI")
    tag = "lineage-test-" + uuid4().hex
    config = WheelerConfig(project_root=str(tmp_path), neo4j={
        "password": "",
        "uri": uri, "username": "neo4j", "database": "neo4j", "project_tag": tag,
    })
    await close_async_driver()
    backend = Neo4jBackend(config)
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=backend))
    monkeypatch.setattr(mcp_core, "_config", config)
    target = "D-" + uuid4().hex[:8]
    await backend.create_node("Dataset", {"id": target, "description": "Isolated lineage fixture"})
    try:
        yield config, backend, target
    finally:
        await backend.run_cypher("MATCH (n) WHERE n._wheeler_project IN $tags DETACH DELETE n", {"tags": [tag, tag + "-foreign"]})
        await close_async_driver()


async def test_live_candidate_intermediate_suppresses_all_accepted_ancestors(live_project):
    from wheeler import mcp_core

    config, backend, target = live_project
    async def capture(**kwargs):
        result = json.loads(await graph_tools.execute_tool("capture_lesson", flow.lesson_args(
            target_ids=[target], source_ids=[], **kwargs,
        ), config))
        assert "error" not in result, result
        return result
    a = await capture()
    b = await capture(supersedes=a["node_id"], accepted=False, instructions="Proposed check")
    c = await capture(supersedes=b["node_id"], instructions="Approved refinement")
    active = await discover_skills([target], config, backend)
    assert [s["id"] for s in active["linked_skills"]] == [c["node_id"]]
    inventory = await mcp_core.show_node(node_id=target, skills_only=True, skill_inventory=True)
    assert "linked_skills" not in inventory
    rows = {s["id"]: s for s in inventory["skill_inventory"]}
    assert rows[a["node_id"]]["state"] == "accepted" and rows[a["node_id"]]["active"] is False
    assert rows[b["node_id"]]["state"] == "candidate" and rows[b["node_id"]]["active"] is False
    assert rows[c["node_id"]]["active"] is True
    assert rows[c["node_id"]]["supersedes"] == b["node_id"]
    assert rows[b["node_id"]]["supersedes"] == a["node_id"]
    assert "Use stable IDs, not filenames." not in json.dumps(inventory)
    await graph_tools.execute_tool("retire_skill", {"node_id": c["node_id"], "reason": "Replaced by harness"}, config)
    assert (await discover_skills([target], config, backend))["linked_skills"] == []


@pytest.mark.parametrize("mismatch", ["name", "scope", "namespace", "unrelated-edge", "wrong-parent"])
async def test_live_transitive_suppression_requires_real_scoped_skill_lineage(live_project, mismatch):
    config, backend, target = live_project
    first_id, next_id = "W-" + uuid4().hex[:8], "W-" + uuid4().hex[:8]
    first = save_skill(config, first_id, skill_target_ids=[target], _wheeler_project=config.neo4j.project_tag)
    next_skill = save_skill(config, next_id, skill_target_ids=[target], skill_supersedes=first_id, _wheeler_project=config.neo4j.project_tag)
    if mismatch == "name":
        next_skill["skill_name"] = "different-workflow"
    elif mismatch == "scope":
        next_skill["skill_target_ids"] = [target, "D-different"]
    elif mismatch == "wrong-parent":
        next_skill["skill_supersedes"] = "W-other"
    await backend.create_node("Document", first)
    await backend.create_node("Document", next_skill)
    await backend.create_relationship("Document", first_id, "APPLIES_TO", "Dataset", target)
    await backend.create_relationship("Document", next_id, "WAS_INFORMED_BY" if mismatch == "unrelated-edge" else "WAS_DERIVED_FROM", "Document", first_id)
    if mismatch == "namespace":
        await backend.run_cypher("MATCH (n:Document {id:$id, _wheeler_project:$tag}) SET n._wheeler_project=$foreign", {
            "id": next_id, "tag": config.neo4j.project_tag, "foreign": config.neo4j.project_tag + "-foreign",
        })
    found = await discover_skills([target], config, backend)
    assert [s["id"] for s in found["linked_skills"]] == [first_id]


async def test_live_writer_inventory_pages_candidates_and_retracted_without_activating(live_project):
    from wheeler import mcp_core
    config, backend, target = live_project
    states = ["candidate", "accepted", "retracted", "incomplete"]
    ids = []
    for i in range(25):
        node_id = "W-" + uuid4().hex[:8]
        ids.append(node_id)
        data = save_skill(config, node_id, skill_name=f"workflow-{i}", skill_state=states[i % 4],
                          skill_target_ids=[target], _wheeler_project=config.neo4j.project_tag)
        await backend.create_node("Document", data)
        await backend.create_relationship("Document", node_id, "APPLIES_TO", "Dataset", target)
    first = await mcp_core.show_node(node_id=target, skills_only=True, skill_inventory=True)
    assert len(first["skill_inventory"]) == 20
    assert first["skill_inventory_next_page"]["skill_inventory"] is True
    second = await mcp_core.show_node(**first["skill_inventory_next_page"])
    rows = first["skill_inventory"] + second["skill_inventory"]
    assert [s["id"] for s in rows] == sorted(ids)
    assert {s["state"] for s in rows} == set(states)
    assert all(s["active"] is (s["state"] == "accepted") for s in rows)
    active = await mcp_core.show_node(node_id=target, skills_only=True)
    assert {s["id"] for s in active["linked_skills"]} == {s["id"] for s in rows if s["active"]}
