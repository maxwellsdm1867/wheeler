"""Stress invariants for graph-linked procedure discovery and bounded disclosure.

These are deterministic plumbing tests. They do not estimate an agent's intent
classification error rate; the independent native-host evaluation does that.
"""
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


@pytest.mark.parametrize("read_mode", ["full", "fields", "unchanged", "batch"])
@pytest.mark.parametrize("relation", ["direct", "neighbor"])
@pytest.mark.parametrize("transition", ["accept", "retire", "revise", "damage", "delete-receipt", "outage"])
async def test_repeated_reads_refresh_guidance_independently_of_unchanged_artifact(
    config, monkeypatch, read_mode, relation, transition,
):
    """Same node bytes must not cache stale skill decisions across graph changes."""
    from wheeler import mcp_core

    old = save_skill(config, "W-old", skill_state="candidate" if transition == "accept" else "accepted")
    graph = SkillGraph([old])
    backend_getter = AsyncMock(return_value=graph)
    monkeypatch.setattr(graph_tools, "_get_backend", backend_getter)
    monkeypatch.setattr(mcp_core, "_config", config)
    artifact_id = "D-db" if relation == "direct" else "F-result"
    monkeypatch.setattr(mcp_core, "_read_node_any_layer", AsyncMock(return_value={
        "id": artifact_id, "type": "Dataset" if relation == "direct" else "Finding",
        "description": "The artifact itself did not change", "content_version": 7,
    }))
    monkeypatch.setattr(mcp_core, "_neighbors_of", AsyncMock(return_value=[{"id": "D-db"}]))
    kwargs = {"node_id": artifact_id, "neighbors": relation == "neighbor"}
    if read_mode == "fields":
        kwargs["fields"] = "description"
    elif read_mode == "unchanged":
        kwargs["if_changed_since"] = "v7"
    elif read_mode == "batch":
        kwargs = {"node_ids": [artifact_id], "neighbors": relation == "neighbor"}

    async def read():
        result = await mcp_core.show_node(**kwargs)
        return result["nodes"][0] if read_mode == "batch" else result

    first = await read()
    assert [s["id"] for s in first["linked_skills"]] == ([] if transition == "accept" else ["W-old"])
    expected, status = [], "complete"
    if transition == "accept":
        graph.skills = [save_skill(config, "W-old")]
        expected = ["W-old"]
    elif transition == "retire":
        graph.skills = [save_skill(config, "W-old", skill_state="retracted")]
    elif transition == "revise":
        graph.skills.append(save_skill(config, "W-new", skill_supersedes="W-old", skill_version=2))
        expected = ["W-new"]
    elif transition == "damage":
        (config.resolved_project_root / "W-old" / "SKILL.md").write_text("Unreviewed instructions")
        status = "unavailable"
    elif transition == "delete-receipt":
        (config.resolved_project_root / "W-old" / "capture-complete.json").unlink()
        status = "unavailable"
    elif transition == "outage":
        backend_getter.side_effect = RuntimeError("offline")
        status = "unavailable"
    second = await read()
    assert [s["id"] for s in second["linked_skills"]] == expected
    assert second["linked_skills_status"] == status
    assert "Use stable IDs, not filenames." not in json.dumps(second)
    if read_mode == "unchanged":
        assert second["changed"] is False


@pytest.mark.parametrize("count", [0, 1, 19, 20, 21, 80, 101])
@pytest.mark.parametrize("damage", ["none", "first", "last"])
async def test_large_skill_catalog_is_bounded_and_never_reanimates_broken_skills(config, count, damage):
    skills = [save_skill(config, f"W-{i:04d}", skill_name=f"procedure-{i}") for i in range(count)]
    broken = None
    if count and damage != "none":
        broken = skills[0 if damage == "first" else -1]["id"]
        (config.resolved_project_root / broken / "SKILL.md").unlink()
    result = await discover_skills(["D-db"] * 30, config, SkillGraph(skills))
    actual = {s["id"] for s in result["linked_skills"]}
    assert len(actual) <= 20
    assert broken not in actual
    expected = {s["id"] for s in skills[:20]} - {broken}
    assert actual == expected
    if count > 20:
        assert result["linked_skills_status"] == "truncated"
    elif broken:
        assert result["linked_skills_status"] == "unavailable"
    else:
        assert result["linked_skills_status"] == "complete"
    assert "Use stable IDs, not filenames." not in json.dumps(result)


@pytest.mark.parametrize("tool_name,result_key", [
    ("query_findings", "findings"), ("query_hypotheses", "hypotheses"),
    ("query_open_questions", "questions"), ("query_datasets", "datasets"),
    ("query_papers", "papers"), ("query_documents", "documents"),
    ("query_plans", "plans"), ("query_notes", "notes"),
    ("query_scripts", "scripts"), ("query_executions", "executions"),
    ("query_review_queue", "items"),
])
@pytest.mark.parametrize("case", ["empty", "citation-only", "actual", "mixed-malformed"])
async def test_all_typed_read_routes_respect_selected_identity_and_partial_coverage(
    config, monkeypatch, tool_name, result_key, case,
):
    graph = SkillGraph([save_skill(config)])
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=graph))
    rows = {
        "empty": [],
        "citation-only": [{"id": "D-other", "description": "[D-db]", "source_ids": ["D-db"]}],
        "actual": [{"id": "D-db"}],
        "mixed-malformed": [{"id": "D-db"}, {"id": None}],
    }[case]
    payload = {result_key: rows, "count": len(rows), "metadata": {"id": "D-db"}}
    monkeypatch.setitem(graph_tools._TOOL_REGISTRY, tool_name, AsyncMock(return_value=json.dumps(payload)))
    result = json.loads(await graph_tools.execute_tool(tool_name, {}, config))
    assert result[result_key] == rows
    assert result["count"] == len(rows)
    expected = ["W-lesson"] if case in {"actual", "mixed-malformed"} else []
    assert [s["id"] for s in result["linked_skills"]] == expected
    assert result["linked_skills_status"] == ("unavailable" if case == "mixed-malformed" else "complete")
    assert "Use stable IDs, not filenames." not in json.dumps(result)


@pytest.mark.parametrize("irrelevant_count", [1, 19, 20, 21, 100])
async def test_late_linked_procedure_omission_is_explicit_but_repeated_read_cannot_recover_it(config, irrelevant_count):
    """Quantify saturation: ordinary repeats return the same ID-ordered page."""
    skills = [save_skill(config, f"W-{i:04d}", skill_name=f"irrelevant-{i}") for i in range(irrelevant_count)]
    skills.append(save_skill(config, "W-zzzz", skill_name="only-applicable-procedure"))
    graph = SkillGraph(skills)
    first = await discover_skills(["D-db"], config, graph)
    repeated = await discover_skills(["D-db"], config, graph)
    assert repeated == first
    ids = {s["id"] for s in first["linked_skills"]}
    assert ("W-zzzz" in ids) == (irrelevant_count < 20)
    if irrelevant_count >= 20:
        assert first["linked_skills_status"] == "truncated"


@pytest.mark.parametrize("desc_length", [0, 239, 240, 241, 700, 1024])
def test_text_context_never_silently_omits_applicability_description(desc_length):
    description = "x" * desc_length + " Skip schema-only inspection."
    result = format_skill_context({
        "linked_skills_status": "complete",
        "linked_skills": [{"id": "W-a", "name": "read-joins", "description": description}],
    })
    # Loss of exclusion language can flip a negative task into a false positive.
    assert description in result or "truncated" in result


@pytest.mark.parametrize("count", [1, 5, 20])
def test_text_context_respects_default_byte_budget_with_large_valid_names(count):
    result = format_skill_context({
        "linked_skills_status": "complete",
        "linked_skills": [{"id": f"W-{i:08x}", "name": "n" * 64, "description": "d" * 1024} for i in range(count)],
    })
    assert len(result) <= 2400
    assert "Use stable IDs, not filenames." not in result


async def test_graph_gaps_returned_node_is_a_discovery_encounter(config, monkeypatch):
    """A gap-review entry carries a selected real node, just like typed queries."""
    graph = SkillGraph([save_skill(config, skill_target_ids=["F-unreported"])])
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=graph))
    payload = {"unreported_findings": [{"id": "F-unreported", "description": "Report this fit"}], "total_gaps": 1}
    monkeypatch.setitem(graph_tools._TOOL_REGISTRY, "graph_gaps", AsyncMock(return_value=json.dumps(payload)))
    result = json.loads(await graph_tools.execute_tool("graph_gaps", {}, config))
    assert [s["id"] for s in result.get("linked_skills", [])] == ["W-lesson"]


@pytest.mark.parametrize("state", ["accepted", "candidate", "retracted"])
@pytest.mark.parametrize("disclosure", ["full", "trimmed", "pointer"])
@pytest.mark.parametrize("full", [False, True])
async def test_direct_skill_search_hit_preserves_its_activation_state(config, monkeypatch, state, disclosure, full):
    from wheeler import mcp_core, mcp_shared
    from wheeler.search import retrieval

    skill = save_skill(config, skill_state=state)
    graph = SkillGraph([skill])
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=graph))
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(mcp_core, "DISCLOSURE", disclosure)
    monkeypatch.setattr(mcp_shared, "_node_meta", AsyncMock(return_value={}))
    monkeypatch.setattr(retrieval, "multi_search", AsyncMock(return_value=[skill]))
    result = await mcp_core.search_findings("join recordings", full=full)
    row, = result["results"]
    assert row.get("skill_name") == "join-recordings"
    assert row.get("skill_state") == state
    assert bool(result["linked_skills"]) == (state == "accepted")


@pytest.mark.parametrize("target_position", [0, 198, 199, 200, 201, 999])
@pytest.mark.parametrize("duplicates", [False, True])
async def test_encounter_budget_limits_unique_nodes_and_marks_late_target_as_unchecked(config, target_position, duplicates):
    ids = [f"D-resource-{i}" for i in range(1000)]
    ids[target_position] = "D-db"
    if duplicates:
        ids = [entry for entry in ids for _ in range(3)]
    graph = SkillGraph([save_skill(config)])
    result = await discover_skills(ids, config, graph)
    assert result["linked_skills_status"] == "truncated"
    assert bool(result["linked_skills"]) == (target_position < 200)
    assert len(graph.calls[0][1]["node_ids"]) == 200


@pytest.mark.parametrize("bucket", [
    "unlinked_questions", "unsupported_hypotheses", "executions_without_outputs",
    "unreported_findings", "orphaned_papers", "potential_duplicates",
])
async def test_gap_discovery_only_uses_declared_identity_slots(config, bucket):
    from wheeler.skill_discovery import enrich_gap_result

    skills = [save_skill(config, "W-selected", skill_target_ids=["D-selected"]), save_skill(config)]
    graph = SkillGraph(skills)
    row = {"id": "D-selected", "description": "See D-db", "nested": {"id": "D-db"}}
    if bucket == "potential_duplicates":
        row = {"node_a": row, "node_b": {"id": "D-other"}, "id": "D-db"}
    payload = {bucket: [row], "counts": {"id": "D-db"}, "other": [{"id": "D-db"}]}
    result = await enrich_gap_result(payload, config, graph)
    assert result[bucket] == payload[bucket]
    assert [s["id"] for s in result["linked_skills"]] == ["W-selected"]
    assert "D-db" not in graph.calls[0][1]["node_ids"]


@pytest.mark.parametrize("summary", [False, True])
async def test_gap_mcp_discovers_duplicate_endpoints_only_after_cap(config, monkeypatch, summary):
    from types import SimpleNamespace
    from wheeler import mcp_core

    graph = SkillGraph([
        save_skill(config, "W-kept", skill_target_ids=["D-kept"]),
        save_skill(config, "W-omitted", skill_target_ids=["D-omitted"]),
    ])
    cap = 3 if summary else 10

    def pair(nid):
        return (SimpleNamespace(node_id=nid, label="Dataset", text=""),
                SimpleNamespace(node_id="D-other", label="Dataset", text=""), 0.95)

    store = AsyncMock()
    store.find_similar_pairs = lambda **kwargs: [pair("D-kept")] * cap + [pair("D-omitted")]
    monkeypatch.setattr(mcp_core, "_get_embedding_store", lambda: store)
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=graph))
    dispatch = AsyncMock(return_value=json.dumps({"total_gaps": 0}))
    monkeypatch.setattr(graph_tools, "execute_tool", dispatch)
    result = await mcp_core.graph_gaps(summary=summary)
    assert len(result["potential_duplicates"]) == cap
    assert [s["id"] for s in result["linked_skills"]] == ["W-kept"]
    assert "D-omitted" not in graph.calls[0][1]["node_ids"]
    assert dispatch.call_args.args[1]["_skip_skill_discovery"] is True


@pytest.mark.parametrize("malformed", [
    {"unreported_findings": None},
    {"unreported_findings": [{"description": "D-db"}]},
    {"potential_duplicates": None},
    {"potential_duplicates": [None]},
    {"potential_duplicates": [{"node_a": {"id": "D-db"}}]},
])
async def test_malformed_gap_identity_is_not_complete_coverage(config, malformed):
    from wheeler.skill_discovery import enrich_gap_result

    graph = SkillGraph([save_skill(config)])
    result = await enrich_gap_result(malformed, config, graph)
    assert result["linked_skills_status"] == "unavailable"
    for key, value in malformed.items():
        assert result[key] == value


async def test_gap_discovery_preserves_query_errors_and_successful_rows_on_outage(config):
    from wheeler.skill_discovery import enrich_gap_result

    graph = AsyncMock()
    graph.run_cypher.side_effect = RuntimeError("offline")
    failure = {"error": "Query failed"}
    assert await enrich_gap_result(failure, config, graph) == failure
    graph.run_cypher.assert_not_called()
    payload = {"unreported_findings": [{"id": "F-real", "description": "Finding survives"}]}
    result = await enrich_gap_result(payload, config, graph)
    assert result["unreported_findings"] == payload["unreported_findings"]
    assert result["linked_skills_status"] == "unavailable"
