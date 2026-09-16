"""Positive and negative boundaries for node-triggered procedural disclosure.

These exercise context delivery, not an LLM's decision to follow a procedure.
Names and incidental prose must never stand in for graph resource identity.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from tests.test_context import _make_async_records, _make_driver_with_results
from tests.test_skill_discovery import SkillGraph, save_skill
from wheeler.config import WheelerConfig, project_knowledge_dir
from wheeler.knowledge.store import write_node
from wheeler.models import DatasetModel
from wheeler.search.retrieval import expand_search_results
from wheeler.skill_discovery import discover_skills
from wheeler.tools import graph_tools


@pytest.fixture
def config(tmp_path):
    return WheelerConfig(project_root=str(tmp_path))


def install_graph(monkeypatch, skills):
    graph = SkillGraph(skills)
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=graph))
    return graph


async def test_same_named_database_does_not_inherit_another_databases_skill(config, monkeypatch):
    from wheeler import mcp_core

    skill = save_skill(config)
    graph = install_graph(monkeypatch, [skill])
    monkeypatch.setattr(mcp_core, "_config", config)
    for node_id in ("D-db", "D-unrelated"):
        write_node(project_knowledge_dir(config), DatasetModel(
            id=node_id, description="Retinal recordings database", path="recordings.sqlite",
        ))

    unrelated = await mcp_core.show_node("D-unrelated")
    assert unrelated["linked_skills"] == []
    assert unrelated["linked_skills_status"] == "complete"
    related = await mcp_core.show_node("D-db")
    assert [item["id"] for item in related["linked_skills"]] == [skill["id"]]
    assert [call[1]["node_ids"] for call in graph.calls] == [["D-unrelated"], ["D-db"]]


async def test_distinct_database_procedures_disclose_applicability_without_loading_bodies(config):
    joining = save_skill(config, "W-join", skill_name="recording-joins",
                         skill_description="Read when joining recordings by stable ID.")
    fitting = save_skill(config, "W-fit", skill_name="fit-preferences",
                         skill_description="Read when fitting response curves; use the scientist's fit preferences.")
    result = await discover_skills(["D-db"], config, SkillGraph([joining, fitting]))
    assert {item["name"] for item in result["linked_skills"]} == {"recording-joins", "fit-preferences"}
    assert {item["description"] for item in result["linked_skills"]} == {
        joining["skill_description"], fitting["skill_description"],
    }
    assert "Use stable IDs, not filenames." not in json.dumps(result)
    assert all("instructions" not in item and "body" not in item for item in result["linked_skills"])


@pytest.mark.parametrize("state", ["candidate", "retracted", "incomplete"])
async def test_unaccepted_or_retired_skill_not_disclosed_even_on_direct_encounter(config, state):
    skill = save_skill(config, skill_state=state)
    result = await discover_skills(["D-db", skill["id"]], config, SkillGraph([skill]))
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "complete"


async def test_one_skill_linked_to_two_encountered_targets_is_disclosed_once(config, monkeypatch):
    skill = save_skill(config, skill_target_ids=["D-db", "D-subset"])
    graph = SkillGraph([skill])
    backend = AsyncMock()

    async def dispatch(query, params):
        if "RETURN skill" in query:
            return await graph.run_cypher(query, params)
        return [{"nid": "D-db", "nlabel": "Dataset", "rel": "WAS_DERIVED_FROM", "dir": "out"}]

    backend.run_cypher.side_effect = dispatch
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=backend))
    result = await expand_search_results([{"id": "D-subset", "type": "Dataset"}], config, max_hops_prov=1)
    assert result["related_nodes"][0]["id"] == "D-db"
    assert [item["id"] for item in result["linked_skills"]] == [skill["id"]]
    assert graph.calls[0][1]["node_ids"] == ["D-subset", "D-db"]


@pytest.mark.parametrize("tool_name, result_key, node_id", [
    ("query_datasets", "datasets", "D-db"),
    ("query_scripts", "scripts", "S-fit"),
    ("query_findings", "findings", "F-result"),
    ("query_documents", "documents", "W-manual"),
])
async def test_typed_graph_result_discloses_linked_skill_without_changing_envelope(
    config, monkeypatch, tool_name, result_key, node_id,
):
    skill = save_skill(config, skill_target_ids=[node_id])
    graph = install_graph(monkeypatch, [skill])
    payload = {result_key: [{"id": node_id, "description": "Returned node"}], "count": 1}
    monkeypatch.setitem(graph_tools._TOOL_REGISTRY, tool_name, AsyncMock(return_value=json.dumps(payload)))
    result = json.loads(await graph_tools.execute_tool(tool_name, {}, config))
    assert result[result_key] == payload[result_key]
    assert result["count"] == 1
    assert [item["id"] for item in result["linked_skills"]] == [skill["id"]]
    assert graph.calls[0][1]["node_ids"] == [node_id]


@pytest.mark.parametrize("row", [
    {"description": "See D-db for instructions"},
    {"id": None, "description": "[D-db]"},
    {"id": ["D-db"]},
    {"id": {"id": "D-db"}},
    {"id": "D-other", "metadata": {"id": "D-db"}},
    "D-db",
])
async def test_typed_query_never_infers_encounters_from_prose_or_nested_metadata(config, monkeypatch, row):
    skill = save_skill(config)
    graph = install_graph(monkeypatch, [skill])
    payload = {"datasets": [row], "count": 1, "description": "D-db"}
    monkeypatch.setitem(graph_tools._TOOL_REGISTRY, "query_datasets", AsyncMock(return_value=json.dumps(payload)))
    result = json.loads(await graph_tools.execute_tool("query_datasets", {}, config))
    assert result["datasets"] == [row]
    assert result.get("linked_skills", []) == []
    assert all("D-db" not in params["node_ids"] for _, params in graph.calls)


async def test_graph_context_discovers_only_actual_record_ids_not_citations_in_text(config, monkeypatch):
    from wheeler.graph import context

    actual = save_skill(config, "W-actual", skill_target_ids=["F-returned"])
    citation_only = save_skill(config, "W-citation", skill_target_ids=["D-db"])
    graph = SkillGraph([actual, citation_only])
    driver, _, _ = _make_driver_with_results([
        [{"id": "F-returned", "desc": "Previously discussed [D-db], see D-db for background."}], [], [], [],
    ])
    session = driver.session.return_value
    original_run = session.run

    async def run(query, **params):
        if "RETURN skill" in query:
            return _make_async_records(await graph.run_cypher(query, params.get("parameters", params)))
        return await original_run(query, **params)

    session.run = run
    monkeypatch.setattr(context, "get_async_driver", lambda _: driver)
    result = await context.fetch_context(config)
    assert "W-actual" in result
    assert "W-citation" not in result
    assert "Use stable IDs, not filenames." not in result
    assert graph.calls[0][1]["node_ids"] == ["F-returned"]


async def test_keyword_search_does_not_promote_linked_skill_metadata_into_search_hits(config, monkeypatch):
    from wheeler.search.retrieval import _keyword_channel

    response = {
        "datasets": [{"id": "D-db"}], "count": 1,
        "linked_skills": [{"id": "W-procedure", "description": "How to query D-db"}],
        "linked_skills_unavailable": [{"id": "W-broken", "reason": "missing_local_copy"}],
        "linked_skills_status": "unavailable",
    }
    monkeypatch.setattr(graph_tools, "execute_tool", AsyncMock(return_value=json.dumps(response)))
    assert await _keyword_channel("retinal", config, 10, "Dataset") == ["D-db"]


async def test_search_findings_discloses_only_skills_for_selected_results(config, monkeypatch):
    from wheeler import mcp_core
    from wheeler.search import retrieval

    matching = save_skill(config, "W-match", skill_target_ids=["D-db"])
    other = save_skill(config, "W-other", skill_target_ids=["D-not-returned"])
    graph = install_graph(monkeypatch, [matching, other])
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(mcp_core, "DISCLOSURE", "pointer")
    monkeypatch.setattr(retrieval, "multi_search", AsyncMock(return_value=[{
        "id": "D-db", "type": "Dataset", "description": "Retinal data", "rrf_score": 1.0,
    }]))
    result = await mcp_core.search_findings("retinal")
    assert result["count"] == 1
    assert result["results"][0]["id"] == "D-db"
    assert [s["id"] for s in result["linked_skills"]] == ["W-match"]
    assert graph.calls[0][1]["node_ids"] == ["D-db"]


async def test_document_listing_marks_candidate_as_inactive(config, monkeypatch):
    candidate = save_skill(config, "W-candidate", skill_state="candidate")
    graph = SkillGraph([candidate])
    backend = AsyncMock()

    async def query(statement, params):
        if "RETURN skill" in statement:
            return await graph.run_cypher(statement, params)
        return [{"id": candidate["id"]}]

    backend.run_cypher.side_effect = query
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=backend))
    response = json.loads(await graph_tools.execute_tool("query_documents", {}, config))
    assert response["documents"][0]["skill_state"] == "candidate"
    assert response["linked_skills"] == []


async def test_internal_keyword_search_skips_discovery_until_context_is_selected(config, monkeypatch):
    from wheeler.search.retrieval import _keyword_channel

    skill = save_skill(config)
    graph = install_graph(monkeypatch, [skill])
    monkeypatch.setitem(graph_tools._TOOL_REGISTRY, "query_datasets", AsyncMock(
        return_value=json.dumps({"datasets": [{"id": "D-db"}], "count": 1}),
    ))
    assert await _keyword_channel("retinal", config, 10, "Dataset") == ["D-db"]
    assert graph.calls == []


async def test_failed_neighbor_expansion_never_claims_complete_discovery(config, monkeypatch):
    skill = save_skill(config)
    graph = SkillGraph([skill])
    backend = AsyncMock()

    async def dispatch(query, params):
        if "RETURN skill" in query:
            return await graph.run_cypher(query, params)
        raise RuntimeError("Neighbor traversal failed")

    backend.run_cypher.side_effect = dispatch
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=backend))
    result = await expand_search_results([{"id": "D-subset", "type": "Dataset"}], config)
    assert result["seed_nodes"][0]["id"] == "D-subset"
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] != "complete"


@pytest.mark.parametrize("disclosure", ["pointer", "trimmed", "full"])
async def test_pointer_listing_preserves_skill_applicability_and_candidate_state(config, monkeypatch, disclosure):
    from wheeler import mcp_query, mcp_shared

    skill = save_skill(config, skill_description="Applicable when joining recording tables. " * 8 + "Skip size checks.")
    install_graph(monkeypatch, [skill])
    monkeypatch.setattr(mcp_query, "_config", config)
    monkeypatch.setattr(mcp_shared, "DISCLOSURE", disclosure)
    discovery = await discover_skills(["D-db"], config)
    payload = {"documents": [{"id": "W-candidate", "title": "Candidate", "skill_name": "candidate", "skill_state": "candidate"}], **discovery}
    monkeypatch.setattr(graph_tools, "execute_tool", AsyncMock(return_value=json.dumps(payload)))
    result = await mcp_query.query_documents()
    assert result["documents"][0]["skill_state"] == "candidate"
    assert result["linked_skills"] == discovery["linked_skills"]
    assert result["linked_skills"][0]["description"] == skill["skill_description"]
    assert result["linked_skills"][0]["path"].endswith("SKILL.md")
    assert "Use stable IDs, not filenames." not in json.dumps(result)


async def test_show_node_neighbor_and_field_selection_preserve_skill_discovery(config, monkeypatch):
    from wheeler import mcp_core

    install_graph(monkeypatch, [save_skill(config)])
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(mcp_core, "_read_node_any_layer", AsyncMock(return_value={"id": "F-result", "description": "Fit"}))
    monkeypatch.setattr(mcp_core, "_neighbors_of", AsyncMock(return_value=[{"id": "D-db", "type": "Dataset"}]))
    result = await mcp_core.show_node("F-result", fields="description", neighbors=True)
    assert result["description"] == "Fit"
    assert [s["id"] for s in result["linked_skills"]] == ["W-lesson"]
    assert result["linked_skills"][0]["matched_target_ids"] == ["D-db"]


async def test_unchanged_node_still_refreshes_newly_linked_guidance(config, monkeypatch):
    from wheeler import mcp_core

    graph = install_graph(monkeypatch, [])
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(mcp_core, "_read_node_any_layer", AsyncMock(return_value={"id": "D-db", "content_version": 1, "description": "Database"}))
    first = await mcp_core.show_node("D-db", if_changed_since="v1")
    assert first["changed"] is False and first["linked_skills"] == []
    graph.skills.append(save_skill(config))
    second = await mcp_core.show_node("D-db", if_changed_since="v1")
    assert second["changed"] is False
    assert [s["id"] for s in second["linked_skills"]] == ["W-lesson"]
    assert "description" not in second


async def test_search_context_cap_excludes_guidance_for_unreturned_neighbors(config, monkeypatch):
    from wheeler import mcp_core
    from wheeler.search import retrieval

    graph = install_graph(monkeypatch, [save_skill(config)])
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(retrieval, "multi_search", AsyncMock(return_value=[{"id": "F-seed"}]))
    monkeypatch.setattr(retrieval, "expand_search_results", AsyncMock(return_value={
        "seed_nodes": [{"id": "F-seed"}],
        "related_nodes": [{"id": "D-other"}, {"id": "D-db"}],
        "relationships": [], "linked_skills": [{"id": "W-lesson"}], "linked_skills_status": "complete",
    }))
    result = await mcp_core.search_context("fit", max_related=1)
    assert result["truncated_related"] is True
    assert result["linked_skills"] == []
    assert graph.calls[0][1]["node_ids"] == ["D-other", "F-seed"]
