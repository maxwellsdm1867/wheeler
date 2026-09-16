"""Node-triggered progressive disclosure, independent of a live Neo4j service."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock

import pytest

from wheeler.config import WheelerConfig, project_knowledge_dir
from wheeler.knowledge.store import write_node
from wheeler.models import DatasetModel, DocumentModel
from wheeler.search.retrieval import expand_search_results
from wheeler.skill_discovery import discover_skills


@pytest.fixture
def config(tmp_path):
    return WheelerConfig(project_root=str(tmp_path))


def save_skill(config, node_id="W-lesson", **changes):
    path = config.resolved_project_root / node_id / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nname: join-recordings\n---\nUse stable IDs, not filenames.\n")
    data = {
        "id": node_id, "title": "Join recordings", "path": str(path),
        "hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "skill_name": "join-recordings",
        "skill_description": "Use when joining recording tables in this database.",
        "skill_version": 1, "skill_state": "accepted", "skill_supersedes": "",
        "skill_source_ids": ["N-correction"], "skill_target_ids": ["D-db"],
        "skill_capture_key": f"capture-{node_id}",
    }
    data.update(changes)
    model = DocumentModel(**data)
    write_node(project_knowledge_dir(config), model)
    path.with_name("capture-complete.json").write_text(json.dumps({
        "node_id": model.id,
        "capture_key": model.skill_capture_key,
        "hash": model.hash,
    }))
    return model.model_dump()


class SkillGraph:
    """Small graph interpreter with observable scoped discovery queries."""

    def __init__(self, skills):
        self.skills = skills
        self.calls = []

    async def run_cypher(self, query, params):
        self.calls.append((query, params))
        assert "NOT EXISTS" in query
        assert "successor.skill_state IN ['accepted', 'retracted']" in query
        ptag = params.get("ptag")
        skills = [s for s in self.skills if not ptag or s.get("_wheeler_project") == ptag]
        records = []
        for skill in sorted(skills, key=lambda s: s["id"]):
            if skill["skill_state"] != "accepted":
                continue
            if any(s["skill_state"] in ("accepted", "retracted") and s["skill_supersedes"] == skill["id"] for s in skills):
                continue
            matched = set(skill["skill_target_ids"]) & set(params["node_ids"])
            if matched or skill["id"] in params["node_ids"]:
                records.append({"skill": skill, "matched_target_ids": list(matched)})
        return records[:params["limit"]]


async def test_direct_discovery_discloses_only_metadata(config):
    skill = save_skill(config)
    graph = SkillGraph([skill])
    result = await discover_skills(["D-db", "D-db"], config, graph)
    assert result["linked_skills_status"] == "complete"
    item, = result["linked_skills"]
    assert item["id"] == skill["id"]
    assert item["target_ids"] == ["D-db"]
    assert "Use stable IDs" not in str(result)
    assert len(graph.calls) == 1
    assert graph.calls[0][1]["node_ids"] == ["D-db"]


async def test_unrelated_skills_never_enter_context(config):
    related = save_skill(config, "W-related")
    unrelated = save_skill(config, "W-unrelated", skill_target_ids=["D-other"])
    result = await discover_skills(["D-db"], config, SkillGraph([related, unrelated]))
    assert [s["id"] for s in result["linked_skills"]] == ["W-related"]
    assert "W-unrelated" not in str(result)


async def test_candidates_do_not_replace_prior_but_accepted_revisions_do(config):
    old = save_skill(config, "W-old")
    new = save_skill(config, "W-new", skill_version=2, skill_state="candidate", skill_supersedes="W-old")
    graph = SkillGraph([old, new])
    result = await discover_skills(["D-db"], config, graph)
    assert [s["id"] for s in result["linked_skills"]] == ["W-old"]
    new = save_skill(config, "W-new", skill_version=2, skill_supersedes="W-old")
    graph.skills = [old, new]
    result = await discover_skills(["D-db"], config, graph)
    assert [s["id"] for s in result["linked_skills"]] == ["W-new"]
    # Damage to the latest revision does not revive known-obsolete instructions.
    (config.resolved_project_root / "W-new" / "SKILL.md").write_text("changed")
    result = await discover_skills(["D-db"], config, graph)
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "unavailable"
    assert result["linked_skills_unavailable"][0]["reason"] == "artifact_hash_mismatch"


async def test_retirement_does_not_revive_superseded_guidance(config):
    old = save_skill(config, "W-old")
    retired = save_skill(config, "W-new", skill_version=2, skill_supersedes="W-old", skill_state="retracted")
    result = await discover_skills(["D-db"], config, SkillGraph([old, retired]))
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "complete"


async def test_canonical_incomplete_write_never_becomes_guidance(config):
    skill = save_skill(config, skill_state="incomplete")
    graph = SkillGraph([{**skill, "skill_state": "accepted"}])
    result = await discover_skills(["D-db"], config, graph)
    assert result["linked_skills"] == []
    assert result["linked_skills_unavailable"][0]["reason"] == "canonical_metadata_mismatch"


@pytest.mark.parametrize("damage", ["missing", "wrong_hash", "wrong_key", "wrong_node", "malformed"])
async def test_incomplete_capture_receipt_never_becomes_guidance(config, damage):
    skill = save_skill(config)
    path = config.resolved_project_root / skill["id"] / "capture-complete.json"
    if damage == "missing":
        path.unlink()
    elif damage == "malformed":
        path.write_text("not json")
    else:
        receipt = json.loads(path.read_text())
        field = {"wrong_hash": "hash", "wrong_key": "capture_key", "wrong_node": "node_id"}[damage]
        receipt[field] = "incorrect"
        path.write_text(json.dumps(receipt))
    result = await discover_skills(["D-db"], config, SkillGraph([skill]))
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "unavailable"
    assert result["linked_skills_unavailable"][0]["reason"] == "incomplete_capture"


@pytest.mark.parametrize("damage", ["missing", "stale", "unknown_root"])
async def test_unusable_local_skill_reported(config, damage):
    changes = {"stale": True} if damage == "stale" else {}
    if damage == "unknown_root":
        changes["path"] = "${OTHER_MACHINE}/SKILL.md"
    skill = save_skill(config, **changes)
    if damage == "missing":
        (config.resolved_project_root / skill["id"] / "SKILL.md").unlink()
    result = await discover_skills(["D-db"], config, SkillGraph([skill]))
    assert result["linked_skills"] == []
    assert result["linked_skills_status"] == "unavailable"


async def test_scope_filters_skill_target_and_superseding_revision(config):
    config.neo4j.project_tag = "current"
    own = save_skill(config, "W-own", _wheeler_project="current")
    other = save_skill(config, "W-other", _wheeler_project="other", skill_supersedes="W-own")
    graph = SkillGraph([own, other])
    result = await discover_skills(["D-db"], config, graph)
    assert [s["id"] for s in result["linked_skills"]] == ["W-own"]
    query, params = graph.calls[0]
    assert params["ptag"] == "current"
    for alias in ("skill", "target", "successor"):
        assert f"{alias}._wheeler_project = $ptag" in query


async def test_output_and_encounter_budgets_have_visible_truncation(config):
    graph = SkillGraph([save_skill(config, "W-a"), save_skill(config, "W-b")])
    result = await discover_skills(["D-db"], config, graph, limit=1)
    assert len(result["linked_skills"]) == 1
    assert result["linked_skills_status"] == "truncated"
    assert graph.calls[0][1]["limit"] == 2
    result = await discover_skills(["D-db", "D-other"], config, graph, node_limit=1)
    assert result["linked_skills_status"] == "truncated"
    assert graph.calls[-1][1]["node_ids"] == ["D-db"]


async def test_discovery_failure_does_not_hide_node(config, monkeypatch):
    from wheeler import mcp_core

    write_node(project_knowledge_dir(config), DatasetModel(id="D-db", description="Database"))
    monkeypatch.setattr(mcp_core, "_config", config)
    monkeypatch.setattr("wheeler.tools.graph_tools._get_backend", AsyncMock(side_effect=RuntimeError("offline")))
    result = await mcp_core.show_node("D-db")
    assert result["description"] == "Database"
    assert result["linked_skills_status"] == "unavailable"


async def test_neighbor_database_exposes_skill_outside_search_hop(config, monkeypatch):
    skill = save_skill(config)
    graph = SkillGraph([skill])
    backend = AsyncMock()

    async def dispatch(query, params):
        if "RETURN skill" in query:
            return await graph.run_cypher(query, params)
        return [{"nid": "D-db", "nlabel": "Dataset", "rel": "WAS_DERIVED_FROM", "dir": "out"}]

    backend.run_cypher.side_effect = dispatch
    monkeypatch.setattr("wheeler.tools.graph_tools._get_backend", AsyncMock(return_value=backend))
    result = await expand_search_results([{"id": "D-cells", "type": "Dataset"}], config, max_hops_prov=1)
    assert result["related_nodes"][0]["id"] == "D-db"
    assert result["linked_skills"][0]["id"] == skill["id"]
    assert graph.calls[0][1]["node_ids"] == ["D-cells", "D-db"]


async def test_failed_expansion_preserves_seed(config, monkeypatch):
    monkeypatch.setattr("wheeler.tools.graph_tools._get_backend", AsyncMock(side_effect=RuntimeError("offline")))
    result = await expand_search_results([{"id": "D-cells"}], config)
    assert result["seed_nodes"][0]["id"] == "D-cells"
    assert result["linked_skills_status"] == "unavailable"


async def test_expansion_scopes_neighbors_before_skill_discovery(config, monkeypatch):
    config.neo4j.project_tag = "current"
    backend = AsyncMock()
    backend.run_cypher.return_value = []
    monkeypatch.setattr("wheeler.tools.graph_tools._get_backend", AsyncMock(return_value=backend))
    await expand_search_results([{"id": "D-cells"}], config)
    calls = backend.run_cypher.call_args_list
    hop1, hop2 = calls[0], calls[1]
    for alias in ("seed", "n"):
        assert f"{alias}._wheeler_project = $ptag" in hop1.args[0]
    for alias in ("seed", "h1", "h2"):
        assert f"{alias}._wheeler_project = $ptag" in hop2.args[0]
    assert hop1.args[1]["ptag"] == "current"


def test_skill_node_summary_marks_document_without_body(config):
    from wheeler.search.retrieval import _summarize_node

    skill = save_skill(config)
    summary = _summarize_node(skill["id"], project_knowledge_dir(config))
    assert summary["skill_name"] == "join-recordings"
    assert summary["skill_state"] == "accepted"
    assert "Use stable IDs" not in str(summary)
