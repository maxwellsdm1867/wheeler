"""Offline capture → new graph read → applicable skill flows.

The graph is an in-memory backend and artifacts are real files in tmp_path.
The SQLite example checks the saved query's behavior, not an LLM's compliance.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from tests.test_e2e_notes import RichFakeBackend
from wheeler.config import WheelerConfig
from wheeler.tools import graph_tools


DATABASE_ID = "D-retinadb"
DATASET_ID = "D-parasol1"
SOURCE_ID = "N-correct1"
CORRECT_SQL = """SELECT r.recording_id, r.cell_type, m.value
FROM recordings AS r
JOIN measurements AS m ON m.recording_id = r.recording_id
WHERE r.cell_type = 'parasol'
ORDER BY r.recording_id"""
INSTRUCTIONS = f"""# Query retinal recordings safely

Use this when joining recordings and measurements in the retinal database.
Basenames are display labels and can be duplicated across recordings.
Join by the stable recording_id. Check that the join returns one row per
requested measurement before interpreting results by cell type.

```sql
{CORRECT_SQL};
```
"""


class LessonBackend(RichFakeBackend):
    """Persist graph state across reads; do not simulate an agent's decisions."""

    def __init__(self):
        super().__init__()
        self.fail_applies_to = False

    async def create_node(self, label, props):
        if await self.get_node(label, props["id"]):
            await self.update_node(label, props["id"], props)
            return props["id"]
        return await super().create_node(label, props)

    async def query_nodes(self, label, filters=None, order_by=None, limit=10):
        nodes = [dict(n) for n in self.nodes.get(label, [])
                 if all(n.get(k) == v for k, v in (filters or {}).items())]
        return nodes[:limit]

    async def create_relationship(self, src_label, src_id, rel_type, tgt_label,
                                  tgt_id, rel_props=None):
        if self.fail_applies_to and rel_type == "APPLIES_TO":
            return False
        if not await self.get_node(src_label, src_id) or not await self.get_node(tgt_label, tgt_id):
            return False
        rel = (src_label, src_id, rel_type, tgt_label, tgt_id)
        if rel not in self.rels:
            self.rels.append(rel)
        return True

    async def run_cypher(self, query, params=None):
        params = params or {}
        if "RETURN count(r) AS count" in query:
            return [{"count": sum(1 for _, src, rel, _, target in self.rels
                                  if src == params["source_id"] and target == params["target_id"]
                                  and rel == params["relationship"])}]
        if "startNode(r)" in query:
            found = []
            for source_label, source, rel, target_label, target in self.rels:
                if source == params["id"]:
                    found.append({"nid": target, "nlabel": target_label, "rel": rel, "dir": "out"})
                elif target == params["id"]:
                    found.append({"nid": source, "nlabel": source_label, "rel": rel, "dir": "in"})
            return found
        if "RETURN skill" in query:
            docs = self.nodes.get("Document", [])
            superseded = {n.get("skill_supersedes") for n in docs
                          if n.get("skill_state") in {"accepted", "retracted"}}
            found = []
            for node in sorted(docs, key=lambda n: n["id"]):
                if node.get("skill_state") != "accepted" or not node.get("skill_name") or node["id"] in superseded:
                    continue
                targets = [t for _, s, rel, _, t in self.rels
                           if s == node["id"] and rel == "APPLIES_TO"
                           and (t in params["node_ids"] or s in params["node_ids"])]
                if targets:
                    found.append({"skill": dict(node), "matched_target_ids": targets})
            return found[:params["limit"]]
        if "AS tid" in query:
            return [{"rel": r, "tid": t, "tlabel": tl}
                    for _, s, r, tl, t in self.rels if s == params["nid"]]
        if "AS sid" in query:
            return [{"rel": r, "sid": s, "slabel": sl}
                    for sl, s, r, _, t in self.rels if t == params["nid"]]
        # Two-hop provenance expansion returns none for this fixture.
        return []


@pytest.fixture
async def lesson_project(tmp_path, monkeypatch):
    config = WheelerConfig(project_root=str(tmp_path))
    backend = LessonBackend()
    monkeypatch.setattr(graph_tools, "_get_backend", AsyncMock(return_value=backend))
    for node_id, description in [(DATABASE_ID, "Retinal recordings database"),
                                 (DATASET_ID, "Parasol recordings subset")]:
        (tmp_path / f"{node_id}.sqlite").touch()
        result = json.loads(await graph_tools.execute_tool("add_dataset", {
            "id": node_id, "path": str(tmp_path / f"{node_id}.sqlite"),
            "type": "sqlite", "description": description,
        }, config))
        assert "error" not in result, result
    await backend.create_relationship("Dataset", DATASET_ID, "DERIVED_FROM", "Dataset", DATABASE_ID)
    result = json.loads(await graph_tools.execute_tool("add_note", {
        "id": SOURCE_ID,
        "content": "Correction: recording basenames repeat; join on recording_id.",
    }, config))
    assert "error" not in result, result
    return config, backend, tmp_path


def lesson_args(**overrides):
    return {
        "name": "retinal-recording-joins",
        "description": "Use when joining recordings and measurements or filtering by cell type in the retinal database.",
        "instructions": INSTRUCTIONS,
        "target_ids": [DATABASE_ID],
        "source_excerpt": "We got two cells back because trace.dat is duplicated. Use recording_id when joining.",
        "source_ids": [SOURCE_ID],
        "accepted": True,
        "problem_statement": "Joining recordings by duplicate basenames mixes cell types and inflates the result count.",
        "benchmark_task": "Query parasol measurements when parasol and midget recordings share trace.dat; return only stable-p with value 12.",
        **overrides,
    }


async def capture(config, **overrides):
    result = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(**overrides), config))
    assert "error" not in result, result
    assert result["status"] != "incomplete", result
    return result


async def fresh_neighbor_read(config, monkeypatch):
    # Search selects only the dataset; the real graph expansion finds its
    # database neighbor and discovers the skill without receiving its name/ID.
    import wheeler.mcp_core as core
    from wheeler.search import retrieval
    monkeypatch.setattr(core, "_config", config)
    monkeypatch.setattr(retrieval, "multi_search", AsyncMock(return_value=[
        {"id": DATASET_ID, "type": "Dataset", "rrf_score": 1.0},
    ]))
    return await core.search_context("Which recordings can I use to study parasol responses?", hops=1)


async def test_correction_survives_fresh_neighbor_read(lesson_project, monkeypatch):
    config, backend, root = lesson_project
    saved = await capture(config)
    result = await fresh_neighbor_read(config, monkeypatch)
    assert [n["id"] for n in result["seed_nodes"]] == [DATASET_ID]
    assert [n["id"] for n in result["related_nodes"]] == [DATABASE_ID]
    skills = result["linked_skills"]
    assert [s["id"] for s in skills] == [saved["node_id"]]
    skill = skills[0]
    graph_skill = await backend.get_node("Document", saved["node_id"])
    file_skill = json.loads((root / "knowledge" / f"{saved['node_id']}.json").read_text())
    for persisted in (graph_skill, file_skill):
        assert persisted["skill_problem"] == lesson_args()["problem_statement"]
        assert persisted["skill_benchmark_task"] == lesson_args()["benchmark_task"]
    assert skill["name"] == "retinal-recording-joins"
    assert skill["target_ids"] == [DATABASE_ID]
    assert "cell type" in skill["description"]
    assert INSTRUCTIONS not in json.dumps(result), "Graph read must return a summary, not the whole procedure"
    body = Path(skill["path"]).read_text()
    assert INSTRUCTIONS in body
    assert "recording_id" in body
    assert (Path(skill["path"]).parent / "source.md").read_text().find("trace.dat") >= 0
    for node_id in (saved["node_id"], saved["source_id"], saved["execution_id"]):
        assert (root / "knowledge" / f"{node_id}.json").is_file()
        assert (root / "synthesis" / f"{node_id}.md").is_file()
    assert any(s == saved["node_id"] and r == "WAS_GENERATED_BY" and t == saved["execution_id"]
               for _, s, r, _, t in backend.rels)
    assert any(s == saved["execution_id"] and r == "USED" and t == SOURCE_ID
               for _, s, r, _, t in backend.rels)


async def test_candidate_is_hidden_until_accepted(lesson_project, monkeypatch):
    config, _, _ = lesson_project
    candidate = await capture(config, accepted=False)
    assert candidate["skill_state"] == "candidate"
    before = await fresh_neighbor_read(config, monkeypatch)
    assert before.get("linked_skills", []) == []
    accepted = await capture(config)
    assert accepted["node_id"] == candidate["node_id"]
    after = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in after["linked_skills"]] == [accepted["node_id"]]


async def test_replay_does_not_duplicate_skill_or_provenance(lesson_project):
    config, backend, _ = lesson_project
    first = await capture(config)
    counts = {label: len(nodes) for label, nodes in backend.nodes.items()}
    rels = list(backend.rels)
    second = await capture(config)
    assert second["node_id"] == first["node_id"]
    assert second["status"] == "unchanged"
    assert counts == {label: len(nodes) for label, nodes in backend.nodes.items()}
    assert backend.rels == rels


async def test_revision_preserves_old_artifact_and_only_discovers_successor(lesson_project, monkeypatch):
    config, backend, _ = lesson_project
    first = await capture(config)
    read = await fresh_neighbor_read(config, monkeypatch)
    old_path = Path(read["linked_skills"][0]["path"])
    old_bytes = old_path.read_bytes()
    newer = await capture(config, instructions=INSTRUCTIONS + "\nCheck for NULL recording IDs before the join.\n",
                          supersedes=first["node_id"])
    assert newer["node_id"] != first["node_id"]
    assert old_path.read_bytes() == old_bytes
    assert await backend.get_node("Document", first["node_id"]) is not None
    read = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in read["linked_skills"]] == [newer["node_id"]]


async def test_failed_link_is_not_discovered_and_replay_repairs_it(lesson_project, monkeypatch):
    config, backend, _ = lesson_project
    backend.fail_applies_to = True
    failed = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(), config))
    assert "error" in failed or failed.get("status") == "incomplete", failed
    read = await fresh_neighbor_read(config, monkeypatch)
    assert read.get("linked_skills", []) == []
    backend.fail_applies_to = False
    saved = await capture(config)
    read = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in read["linked_skills"]] == [saved["node_id"]]


async def test_saved_query_avoids_duplicate_basename_cross_cell_contamination(lesson_project, monkeypatch):
    config, _, root = lesson_project
    await capture(config)
    read = await fresh_neighbor_read(config, monkeypatch)
    skill_text = Path(read["linked_skills"][0]["path"]).read_text()
    sql = re.search(r"```sql\n(.*?)\n```", skill_text, re.DOTALL).group(1)
    with sqlite3.connect(root / "recordings.sqlite") as db:
        db.executescript("""
        CREATE TABLE recordings(recording_id TEXT PRIMARY KEY, basename TEXT, cell_type TEXT);
        CREATE TABLE measurements(recording_id TEXT, basename TEXT, value REAL);
        INSERT INTO recordings VALUES ('stable-p', 'trace.dat', 'parasol'), ('stable-m', 'trace.dat', 'midget');
        INSERT INTO measurements VALUES ('stable-p', 'trace.dat', 12), ('stable-m', 'trace.dat', 99);
        """)
        wrong = db.execute("""SELECT r.recording_id, m.value FROM recordings r
            JOIN measurements m ON m.basename = r.basename WHERE r.cell_type = 'parasol'""").fetchall()
        assert wrong == [("stable-p", 12.0), ("stable-p", 99.0)]
        assert db.execute(sql).fetchall() == [("stable-p", "parasol", 12.0)]


@pytest.mark.parametrize("overrides", [
    {"target_ids": ["D-notthere"]},
    {"source_ids": ["N-notthere"]},
    {"target_ids": []},
    {"name": "../../escape"},
    {"source_excerpt": ""},
])
async def test_invalid_capture_leaves_no_skill_or_provenance(lesson_project, overrides):
    config, backend, root = lesson_project
    before = {label: [dict(n) for n in nodes] for label, nodes in backend.nodes.items()}
    result = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(**overrides), config))
    assert "error" in result, result
    assert backend.nodes == before
    assert list(root.rglob("SKILL.md")) == []


async def test_candidate_revision_does_not_hide_accepted_procedure(lesson_project, monkeypatch):
    config, _, _ = lesson_project
    original = await capture(config)
    revision_args = {
        "instructions": INSTRUCTIONS + "\nCheck NULL recording IDs before joining.\n",
        "supersedes": original["node_id"],
    }
    candidate = await capture(config, accepted=False, **revision_args)
    before = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in before["linked_skills"]] == [original["node_id"]]
    accepted = await capture(config, **revision_args)
    assert accepted["node_id"] == candidate["node_id"]
    after = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in after["linked_skills"]] == [candidate["node_id"]]


async def test_live_mcp_surface_exposes_capture_with_candidate_default():
    from wheeler.mcp_mutations import mcp

    tool = next(t for t in await mcp.list_tools() if t.name == "capture_lesson")
    parameters = tool.parameters["properties"]
    assert {"name", "description", "instructions", "target_ids", "source_excerpt",
            "source_ids", "supersedes", "accepted", "problem_statement", "benchmark_task"} <= parameters.keys()
    assert parameters["accepted"]["default"] is False


async def test_retirement_hides_successor_without_reviving_original(lesson_project, monkeypatch):
    config, backend, _ = lesson_project
    original = await capture(config)
    revision_args = {
        "instructions": INSTRUCTIONS + "\nCheck NULL recording IDs before joining.\n",
        "supersedes": original["node_id"],
    }
    successor = await capture(config, **revision_args)
    result = json.loads(await graph_tools.execute_tool("retire_skill", {
        "node_id": successor["node_id"], "reason": "The database now enforces a different recording key.",
    }, config))
    assert "error" not in result, result
    assert all(result["storage"].values())
    read = await fresh_neighbor_read(config, monkeypatch)
    assert read["linked_skills"] == []
    retained = await backend.get_node("Document", successor["node_id"])
    assert retained["skill_state"] == "retracted"
    assert retained["skill_retired_reason"] == "The database now enforces a different recording key."
    assert Path(successor["path"]).exists()
    replay = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(**revision_args), config))
    assert "error" in replay
    read = await fresh_neighbor_read(config, monkeypatch)
    assert read["linked_skills"] == []


async def test_replay_restores_missing_canonical_json(lesson_project, monkeypatch):
    config, _, root = lesson_project
    saved = await capture(config)
    knowledge_file = root / "knowledge" / f"{saved['node_id']}.json"
    knowledge_file.unlink()
    before = await fresh_neighbor_read(config, monkeypatch)
    assert before["linked_skills"] == []
    assert before["linked_skills_status"] == "unavailable"
    recovered = await capture(config)
    assert recovered["node_id"] == saved["node_id"]
    assert knowledge_file.is_file()
    after = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in after["linked_skills"]] == [saved["node_id"]]


async def test_failed_final_canonical_write_is_hidden_until_replay(lesson_project, monkeypatch):
    config, _, _ = lesson_project
    real_writer = graph_tools._update_knowledge_node

    def fail_final_write(args, result_str, config):
        if args.get("skill_state") == "accepted":
            return False, False
        return real_writer(args, result_str, config)

    monkeypatch.setattr(graph_tools, "_update_knowledge_node", fail_final_write)
    failed = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(), config))
    assert failed["status"] == "incomplete", failed
    before = await fresh_neighbor_read(config, monkeypatch)
    assert before["linked_skills"] == []
    assert before["linked_skills_status"] == "unavailable"
    monkeypatch.setattr(graph_tools, "_update_knowledge_node", real_writer)
    recovered = await capture(config)
    assert recovered["node_id"] == failed["node_id"]
    after = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in after["linked_skills"]] == [recovered["node_id"]]


async def test_capture_links_existing_regression_harness_as_evidence(lesson_project):
    config, backend, root = lesson_project
    harness_path = root / "check_recording_join.py"
    harness_path.write_text("# Existing regression harness for duplicate recording basenames.\n")
    harness = json.loads(await graph_tools.execute_tool("add_script", {
        "id": "S-joincheck", "path": str(harness_path), "language": "python",
        "description": "Checks a stable-ID join against duplicate basenames.",
    }, config))
    assert "error" not in harness, harness
    saved = await capture(config, harness_ids=[harness["node_id"]])
    skill = await backend.get_node("Document", saved["node_id"])
    assert skill["skill_harness_ids"] == [harness["node_id"]]
    assert any(s == saved["execution_id"] and rel == "USED" and t == harness["node_id"]
               for _, s, rel, _, t in backend.rels)
