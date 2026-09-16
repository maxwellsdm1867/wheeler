"""Public, artifact-scoped recovery of descriptions beyond discovery budgets."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from tests.test_skill_discovery import SkillGraph, save_skill
from wheeler.config import WheelerConfig
from wheeler.skill_discovery import discover_skills, format_skill_context
from wheeler.tools import graph_tools


@pytest.fixture
def config(tmp_path):
    return WheelerConfig(project_root=str(tmp_path))


class PagingSkillGraph(SkillGraph):
    async def run_cypher(self, query, params):
        all_rows = await super().run_cypher(query, {**params, "limit": 10000})
        self.calls[-1] = (query, params)
        assert "ORDER BY skill.id SKIP $offset LIMIT $limit" in query
        start = params.get("offset", 0)
        return all_rows[start:start + params["limit"]]


def install(config, monkeypatch, skills):
    from wheeler import mcp_core

    graph = PagingSkillGraph(skills)
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=graph))
    return graph


@pytest.mark.parametrize("count", [0, 1, 20, 21, 40, 41, 101])
async def test_public_recovery_pages_cover_every_linked_skill_once(config, monkeypatch, count):
    from wheeler import mcp_core

    skills = [save_skill(config, f"W-{i:04d}") for i in range(count)]
    graph = install(config, monkeypatch, skills)
    node_reader = AsyncMock(side_effect=AssertionError("metadata recovery must not disclose artifact content"))
    monkeypatch.setattr(mcp_core, "_read_node_any_layer", node_reader)
    result = await discover_skills(["D-db"], config, graph)
    seen = []
    pages = 0
    while True:
        pages += 1
        seen.extend(s["id"] for s in result["linked_skills"])
        assert len(result["linked_skills"]) <= 20
        assert "Use stable IDs, not filenames." not in json.dumps(result)
        next_args = result.get("linked_skills_next_page")
        if not next_args:
            assert result["linked_skills_status"] == "complete"
            break
        assert result["linked_skills_status"] == "truncated"
        assert next_args["node_ids"] == ["D-db"]
        assert next_args["skill_offset"] == pages * 20
        result = await mcp_core.show_node(**next_args)
        assert pages < 10
    assert seen == [s["id"] for s in skills]
    assert pages == max(1, (count + 19) // 20)
    node_reader.assert_not_called()


async def test_late_only_relevant_skill_recoverable_without_widening_artifact_scope(config, monkeypatch):
    from wheeler import mcp_core

    skills = [save_skill(config, f"W-{i:04d}", skill_description="Use only when plotting.") for i in range(25)]
    skills += [save_skill(config, "W-relevant", skill_description="Use when joining this database."),
               save_skill(config, "W-foreign", skill_target_ids=["D-other"], skill_description="Use when joining this database.")]
    install(config, monkeypatch, skills)
    first = await mcp_core.show_node(node_id="D-db", skills_only=True)
    assert "W-relevant" not in json.dumps(first)
    second = await mcp_core.show_node(**first["linked_skills_next_page"])
    assert "W-relevant" in json.dumps(second)
    assert "W-foreign" not in json.dumps(first) + json.dumps(second)


@pytest.mark.parametrize("damage", ["missing", "candidate", "retired", "superseded", "foreign-project"])
async def test_paging_never_activates_invalid_revision_or_cross_project_skill(config, monkeypatch, damage):
    from wheeler import mcp_core

    config.neo4j.project_tag = "project-a"
    skills = [save_skill(config, f"W-{i:04d}", _wheeler_project="project-a") for i in range(45)]
    target = skills[22]
    if damage == "missing":
        (config.resolved_project_root / target["id"] / "SKILL.md").unlink()
    elif damage in {"candidate", "retired"}:
        skills[22] = save_skill(config, target["id"], skill_state="candidate" if damage == "candidate" else "retracted", _wheeler_project="project-a")
    elif damage == "superseded":
        skills.append(save_skill(config, "W-new", skill_supersedes=target["id"], _wheeler_project="project-a"))
    elif damage == "foreign-project":
        skills[22] = save_skill(config, target["id"], _wheeler_project="project-b")
    graph = install(config, monkeypatch, skills)
    args = {"node_ids": ["D-db"], "skills_only": True}
    seen, failures = [], []
    while args:
        result = await mcp_core.show_node(**args)
        seen.extend(s["id"] for s in result["linked_skills"])
        failures.extend(result.get("linked_skills_unavailable", []))
        args = result.get("linked_skills_next_page")
    assert target["id"] not in seen
    assert len(seen) == (45 if damage == "superseded" else 44)
    if damage == "missing":
        assert [f["id"] for f in failures] == [target["id"]]
    for query, params in graph.calls:
        assert params["ptag"] == "project-a"
        assert "skill._wheeler_project = $ptag" in query
        assert "target._wheeler_project = $ptag" in query
        assert "successor._wheeler_project = $ptag" in query


async def test_skill_attached_to_multiple_encountered_nodes_is_not_repeated_across_pages(config, monkeypatch):
    from wheeler import mcp_core

    skills = [save_skill(config, f"W-{i:04d}", skill_target_ids=["D-db", "S-script"]) for i in range(25)]
    install(config, monkeypatch, skills)
    first = await mcp_core.show_node(node_ids=["D-db", "S-script", "D-db"], skills_only=True)
    assert first["linked_skills_next_page"]["node_ids"] == ["D-db", "S-script"]
    second = await mcp_core.show_node(**first["linked_skills_next_page"])
    seen = [s["id"] for s in first["linked_skills"] + second["linked_skills"]]
    assert len(seen) == len(set(seen)) == 25


async def test_invalid_or_beyond_end_offsets_have_unambiguous_results(config, monkeypatch):
    from wheeler import mcp_core

    install(config, monkeypatch, [save_skill(config)])
    for kwargs in ({"skills_only": True, "skill_offset": -1}, {"skill_offset": 20}):
        result = await mcp_core.show_node(node_id="D-db", **kwargs)
        assert "error" in result
    result = await mcp_core.show_node(node_id="D-db", skills_only=True, skill_offset=100)
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "complete"
    assert "linked_skills_next_page" not in result


async def test_public_schema_and_tool_call_offer_metadata_recovery(config, monkeypatch):
    from wheeler import mcp_core
    from tests.live_schema import live_tools

    install(config, monkeypatch, [save_skill(config)])
    schema = (await live_tools())["show_node"].parameters["properties"]
    assert schema["skills_only"]["type"] == "boolean"
    assert schema["skill_offset"]["type"] == "integer"
    result = await mcp_core.mcp.call_tool("show_node", {"node_ids": ["D-db"], "skills_only": True})
    # FastMCP publishes both text content and a structured return payload.
    assert "W-lesson" in str(result)
    assert "Use stable IDs, not filenames." not in str(result)


async def test_overlarge_encounter_scope_reports_unchecked_nodes_without_global_recovery(config):
    graph = PagingSkillGraph([save_skill(config, f"W-{i:04d}") for i in range(21)])
    ids = ["D-db"] + [f"D-{i:04d}" for i in range(500)]
    result = await discover_skills(ids, config, graph)
    assert result["linked_skills_unchecked_node_count"] == 301
    assert result["linked_skills_next_page"]["node_ids"] == ids[:200]
    assert "remaining artifact IDs" in result["linked_skills_scope_guidance"]


def test_text_budget_omission_offers_scope_preserving_metadata_recovery():
    result = format_skill_context({"linked_skills_status": "complete", "linked_skills": [
        {"id": f"W-{i:08d}", "name": "procedure", "description": "Applicable " * 95} for i in range(5)
    ]})
    assert "truncated" in result
    assert "skills_only=true" in result
    assert "encountered IDs" in result
    assert len(result) <= 2400


@pytest.mark.parametrize("host", ["claude", "codex"])
async def test_lesson_hosts_receive_same_paged_update_before_create_contract(host):
    from wheeler import mcp_core

    delivered = await mcp_core.get_act("lesson", host=host)
    body = delivered["body"]
    assert "skills_only=true" in body and "linked_skills_next_page" in body
    assert body.index("On every capture or revision") < body.index("Call `capture_lesson`")
    assert "purpose, operation, target, and applicability conditions, not name alone" in body
    assert "reuse its name and target scope" in body and "`supersedes`" in body
    assert "Create a new skill only for a clearly distinct reusable workflow" in body
    assert "remove redundant or superseded instructions" in body
    assert "do not accumulate an incident log" in body
    assert "mcp__wheeler_core__show_node" in delivered["allowed_tools"]


async def test_real_neo4j_paging_uses_public_mcp_and_keeps_namespace(tmp_path, monkeypatch):
    """Opt-in against the explicitly supplied isolated server, never user config."""
    import os
    from uuid import uuid4
    from wheeler import mcp_core
    from wheeler.graph.driver import close_async_driver
    from wheeler.graph.neo4j_backend import Neo4jBackend

    uri = os.environ.get("WHEELER_LESSON_TEST_URI")
    if not uri:
        pytest.skip("Needs explicit isolated Neo4j test URI")
    namespace = "skill-page-test-" + uuid4().hex
    config = WheelerConfig(project_root=str(tmp_path), neo4j={
        "password": "",
        "uri": uri, "username": "neo4j", "database": "neo4j", "project_tag": namespace,
    })
    await close_async_driver()
    backend = Neo4jBackend(config)
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=backend))
    monkeypatch.setattr(mcp_core, "_config", config)
    try:
        await backend.create_node("Dataset", {"id": "D-paging-db", "description": "Isolated paging fixture"})
        for i in range(23):
            skill = save_skill(config, f"W-{i:08x}", skill_target_ids=["D-paging-db"], _wheeler_project=namespace)
            await backend.create_node("Document", skill)
            await backend.create_relationship("Document", skill["id"], "APPLIES_TO", "Dataset", "D-paging-db")
        result = await mcp_core.mcp.call_tool("show_node", {"node_id": "D-paging-db", "skills_only": True})
        first = json.loads(result.content[0].text)
        assert len(first["linked_skills"]) == 20
        result = await mcp_core.mcp.call_tool("show_node", first["linked_skills_next_page"])
        second = json.loads(result.content[0].text)
        assert len(second["linked_skills"]) == 3
        assert second["linked_skills_status"] == "complete"
        ids = [s["id"] for s in first["linked_skills"] + second["linked_skills"]]
        assert ids == [f"W-{i:08x}" for i in range(23)]
        assert "Use stable IDs, not filenames." not in json.dumps([first, second])
    finally:
        await backend.run_cypher("MATCH (n {_wheeler_project: $tag}) DETACH DELETE n", {"tag": namespace})
        await close_async_driver()
