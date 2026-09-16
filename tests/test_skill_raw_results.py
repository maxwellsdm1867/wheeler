"""Raw graph discovery uses typed, scoped resource identities, never ID-shaped prose."""

from unittest.mock import AsyncMock

import pytest
from neo4j.graph import Graph, Node, Path, Relationship

from tests.test_skill_discovery import SkillGraph, save_skill
from wheeler.config import WheelerConfig
from wheeler.skill_raw_results import discover_raw_result_skills


@pytest.fixture
def config(tmp_path):
    return WheelerConfig(project_root=str(tmp_path))


def node(node_id="D-db", *, label="Dataset", project=None, **properties):
    props = {"id": node_id, **properties}
    if project is not None:
        props["_wheeler_project"] = project
    return Node(Graph(), node_id, 1, [label], props)


async def test_real_node_discloses_description_without_full_body(config):
    skill = save_skill(config)
    graph = SkillGraph([skill])
    result = await discover_raw_result_skills([{"resource": node()}], config, graph)
    assert result["linked_skills_status"] == "complete"
    assert [item["id"] for item in result["linked_skills"]] == [skill["id"]]
    assert "Use stable IDs, not filenames." not in str(result)
    assert graph.calls[0][1]["node_ids"] == ["D-db"]


@pytest.mark.parametrize("rows", [
    [{"id": "D-db", "type": "Dataset", "_wheeler_project": "current"}],
    [{"node": {"id": "D-db", "labels": ["Dataset"]}}],
    [{"description": "D-db: how to fit this recording"}],
    [{"D-db": "value", "count": 12}],
    [{"ids": ["D-db"]}],
])
async def test_scalar_and_fake_node_results_never_trigger(config, rows):
    graph = SkillGraph([save_skill(config)])
    result = await discover_raw_result_skills(rows, config, graph)
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "not_checked"
    assert "show_node" in result["linked_skills_guidance"]
    assert graph.calls == []


@pytest.mark.parametrize("project", [None, "foreign", ""])
async def test_foreign_or_unknown_namespace_cannot_activate_same_id(config, project):
    config.neo4j.project_tag = "current"
    graph = SkillGraph([save_skill(config, _wheeler_project="current")])
    result = await discover_raw_result_skills(
        [{"resource": node(project=project)}], config, graph,
    )
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "not_checked"
    assert graph.calls == []


async def test_current_namespace_and_foreign_same_id_are_separated(config):
    config.neo4j.project_tag = "current"
    graph = SkillGraph([save_skill(config, _wheeler_project="current")])
    result = await discover_raw_result_skills(
        [{"foreign": node(project="foreign"), "local": node(project="current")}], config, graph,
    )
    assert [item["id"] for item in result["linked_skills"]] == ["W-lesson"]
    assert graph.calls[0][1]["node_ids"] == ["D-db"]
    assert graph.calls[0][1]["ptag"] == "current"


@pytest.mark.parametrize("node_id,label", [
    ("D-db", "Script"), ("X-db", "Dataset"), ("D-", "Dataset"), ("D", "Dataset"),
])
async def test_wheeler_id_must_match_real_node_label(config, node_id, label):
    graph = SkillGraph([save_skill(config)])
    result = await discover_raw_result_skills(
        [{"node": node(node_id, label=label)}], config, graph,
    )
    assert result["linked_skills_status"] == "not_checked"
    assert graph.calls == []


async def test_paths_and_nested_values_discover_both_nodes_once(config):
    graph = Graph()
    start = Node(graph, "1", 1, ["Finding"], {"id": "F-fit"})
    end = Node(graph, "2", 2, ["Dataset"], {"id": "D-db"})
    relationship = Relationship(graph, "3", 3, {})
    relationship._start_node = start
    relationship._end_node = end
    path = Path(start, relationship)
    backend = SkillGraph([save_skill(config)])
    result = await discover_raw_result_skills(
        [{"paths": [{"path": path}], "duplicate": end}], config, backend,
    )
    assert result["linked_skills_status"] == "complete"
    assert backend.calls[0][1]["node_ids"] == ["F-fit", "D-db"]
    assert [item["id"] for item in result["linked_skills"]] == ["W-lesson"]


async def test_mixed_scalar_coverage_is_explicit_and_node_properties_are_not_followed(config):
    graph = SkillGraph([save_skill(config)])
    records = [{"node": node("D-other", mentioned="D-db"), "id": "D-db"}]
    result = await discover_raw_result_skills(records, config, graph)
    assert result["linked_skills_status"] == "complete"
    assert "Scalar projections and map IDs are not checked" in result["linked_skills_coverage"]
    assert result["linked_skills"] == []
    assert graph.calls[0][1]["node_ids"] == ["D-other"]


async def test_empty_results_complete_without_graph_request(config):
    graph = SkillGraph([])
    result = await discover_raw_result_skills([], config, graph)
    assert result["linked_skills_status"] == "complete"
    assert graph.calls == []


async def test_width_bound_preserves_known_discovery_and_reports_incomplete(config):
    graph = SkillGraph([save_skill(config)])
    records = [{"first": node(), "values": list(range(10)) + [node("D-later")]}]
    result = await discover_raw_result_skills(records, config, graph, max_values=5)
    assert result["linked_skills_status"] == "truncated"
    assert result["linked_skills_truncated"] is True
    assert graph.calls[0][1]["node_ids"] == ["D-db"]
    assert [item["id"] for item in result["linked_skills"]] == ["W-lesson"]


async def test_depth_bound_does_not_claim_absence(config):
    graph = SkillGraph([save_skill(config)])
    result = await discover_raw_result_skills(
        [{"nested": [{"node": node()}]}], config, graph, max_depth=1,
    )
    assert result["linked_skills_status"] == "truncated"
    assert graph.calls == []


async def test_cyclic_containers_are_bounded_without_losing_reachable_nodes(config):
    graph = SkillGraph([save_skill(config)])
    recursive = []
    recursive.extend([recursive, node()])
    result = await discover_raw_result_skills([{"nodes": recursive}], config, graph)
    assert result["linked_skills_status"] == "complete"
    assert graph.calls[0][1]["node_ids"] == ["D-db"]


async def test_mcp_raw_result_preserves_shape_count_and_query(config, monkeypatch):
    from wheeler import mcp_core

    skill_graph = SkillGraph([save_skill(config)])
    raw_records = [{"resource": node(), "aggregate": 7}]
    query = "MATCH (n:Dataset) RETURN n AS resource, 7 AS aggregate"
    backend = AsyncMock()

    async def dispatch(actual_query, params=None):
        if actual_query == query:
            assert params is None
            return raw_records
        return await skill_graph.run_cypher(actual_query, params)

    backend.run_cypher.side_effect = dispatch
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(mcp_core.graph_tools, "_get_backend", AsyncMock(return_value=backend))
    result = await mcp_core.run_cypher(query)
    assert result["results"] is raw_records
    assert result["count"] == 1
    assert [item["id"] for item in result["linked_skills"]] == ["W-lesson"]


async def test_mcp_discovery_failure_preserves_successful_query(config, monkeypatch):
    from wheeler import mcp_core

    raw_records = [{"resource": node()}]
    backend = AsyncMock()
    backend.run_cypher.side_effect = [raw_records, RuntimeError("Discovery unavailable")]
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(mcp_core.graph_tools, "_get_backend", AsyncMock(return_value=backend))
    result = await mcp_core.run_cypher("MATCH (n:Dataset) RETURN n")
    assert result["results"] is raw_records
    assert result["count"] == 1
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "unavailable"


async def test_raw_limit_discovers_only_returned_nodes_and_preserves_project_binding(config, monkeypatch):
    from wheeler import mcp_core

    config.neo4j.project_tag = "current"
    graph = SkillGraph([save_skill(config, _wheeler_project="current")])
    backend = AsyncMock()
    query = "MATCH (n:Dataset) WHERE n._wheeler_project = $ptag RETURN n"

    async def dispatch(actual, params):
        if actual == query:
            assert params == {"ptag": "current"}
            return [{"n": node("D-other", project="current")}, {"n": node(project="current")}]
        return await graph.run_cypher(actual, params)

    backend.run_cypher.side_effect = dispatch
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(mcp_core.graph_tools, "_get_backend", AsyncMock(return_value=backend))
    result = await mcp_core.run_cypher(query, limit=1)
    assert result["count"] == 1 and result["total_rows"] == 2
    assert result["project_tag"] == "current"
    assert result["linked_skills"] == []
    assert graph.calls[0][1]["node_ids"] == ["D-other"]
