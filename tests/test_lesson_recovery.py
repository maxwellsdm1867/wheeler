"""Fault injection at publication and concurrent lifecycle boundaries."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tests.test_lesson_flow import capture, fresh_neighbor_read, lesson_args
from tests.test_lesson_flow import lesson_project as lesson_project
from wheeler.tools import graph_tools


async def test_retirement_serializes_with_capture_replay(lesson_project, monkeypatch):
    config, backend, _ = lesson_project
    saved = await capture(config)
    paused, release = asyncio.Event(), asyncio.Event()
    original = backend.run_cypher

    async def hold(*args, **kwargs):
        if not paused.is_set():
            paused.set()
            await release.wait()
        return await original(*args, **kwargs)

    monkeypatch.setattr(backend, "run_cypher", hold)
    replay = asyncio.create_task(capture(config))
    await asyncio.wait_for(paused.wait(), 5)
    retirement = {"node_id": saved["node_id"], "reason": "Harness now enforces this rule"}
    try:
        busy = json.loads(await graph_tools.execute_tool("retire_skill", retirement, config))
        assert busy["error"] == "capture_busy"
    finally:
        release.set()
        await replay
    retired = json.loads(await graph_tools.execute_tool("retire_skill", retirement, config))
    assert "error" not in retired
    stale_replay = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(), config))
    assert "error" in stale_replay
    assert (await backend.get_node("Document", saved["node_id"]))["skill_state"] == "retracted"


async def test_failed_final_synthesis_cannot_publish_skill(lesson_project, monkeypatch):
    config, _, root = lesson_project
    original = graph_tools._write_synthesis_file

    def fail(node_id, model, config, **kwargs):
        if getattr(model, "skill_state", "") == "accepted":
            return False
        return original(node_id, model, config, **kwargs)

    monkeypatch.setattr(graph_tools, "_write_synthesis_file", fail)
    failed = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(), config))
    assert failed["status"] == "incomplete"
    assert not list(root.rglob("capture-complete.json"))
    hidden = await fresh_neighbor_read(config, monkeypatch)
    assert hidden["linked_skills"] == []
    assert hidden["linked_skills_status"] == "unavailable"
    monkeypatch.setattr(graph_tools, "_write_synthesis_file", original)
    recovered = await capture(config)
    assert recovered["node_id"] == failed["node_id"]
    visible = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in visible["linked_skills"]] == [recovered["node_id"]]


async def test_retired_successor_cannot_be_bypassed_by_old_candidate(lesson_project):
    config, _, _ = lesson_project
    first = await capture(config)
    candidate_args = {"supersedes": first["node_id"], "instructions": "Alternative still under review."}
    await capture(config, accepted=False, **candidate_args)
    chosen = await capture(config, supersedes=first["node_id"], instructions="The chosen revision.")
    await graph_tools.execute_tool("retire_skill", {"node_id": chosen["node_id"], "reason": "Obsolete"}, config)
    competing = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(**candidate_args), config))
    assert "error" in competing


async def test_accept_saved_candidate_by_id_without_reconstructing_context(lesson_project, monkeypatch):
    from wheeler.validation.citations import extract_citations

    config, _, _ = lesson_project
    candidate = await capture(config, accepted=False)
    result = json.loads(await graph_tools.execute_tool("accept_skill", {"node_id": candidate["node_id"]}, config))
    assert "error" not in result, result
    assert result["node_id"] == candidate["node_id"]
    assert result["skill_state"] == "accepted"
    assert extract_citations(f"Applied [{result['node_id']}]") == [result["node_id"]]
    discovered = await fresh_neighbor_read(config, monkeypatch)
    assert [s["id"] for s in discovered["linked_skills"]] == [candidate["node_id"]]
    body = Path(result["path"]).read_text()
    assert lesson_args()["problem_statement"] in body
    assert lesson_args()["benchmark_task"] in body


async def test_accept_rejects_changed_capture_manifest(lesson_project):
    config, backend, _ = lesson_project
    candidate = await capture(config, accepted=False)
    manifest = Path(candidate["path"]).with_name("capture.json")
    data = json.loads(manifest.read_text())
    data["instructions"] = "Different procedure"
    manifest.write_text(json.dumps(data))
    result = json.loads(await graph_tools.execute_tool("accept_skill", {"node_id": candidate["node_id"]}, config))
    assert result["error"] == "invalid_saved_capture"
    assert (await backend.get_node("Document", candidate["node_id"]))["skill_state"] == "candidate"


async def test_historical_skills_do_not_expand_context(lesson_project):
    from wheeler.search.retrieval import expand_search_results

    config, _, _ = lesson_project
    first = await capture(config)
    second = await capture(config, supersedes=first["node_id"], instructions="Use stable keys and check nulls.")
    await capture(config, supersedes=second["node_id"], instructions="An unaccepted alternative.", accepted=False)
    context = await expand_search_results([{"id": "D-retinadb", "type": "Dataset"}], config)
    assert [s["id"] for s in context["linked_skills"]] == [second["node_id"]]
    assert not any(n.get("skill_name") for n in context["related_nodes"])
    assert "An unaccepted alternative" not in json.dumps(context)


async def test_candidate_requires_review_after_harness_change(lesson_project):
    config, backend, root = lesson_project
    script = root / "regression.py"
    script.write_text("# harness v1\n")
    await graph_tools.execute_tool("add_script", {
        "id": "S-harness", "path": str(script), "hash": "v1", "language": "python",
    }, config)
    candidate = await capture(config, accepted=False, harness_ids=["S-harness"])
    skill = await backend.get_node("Document", candidate["node_id"])
    assert json.loads(skill["skill_harness_snapshot"])["S-harness"]["hash"] == "v1"
    await graph_tools.execute_tool("update_node", {"node_id": "S-harness", "hash": "v2"}, config)
    result = json.loads(await graph_tools.execute_tool("accept_skill", {"node_id": candidate["node_id"]}, config))
    assert "error" in result
    assert "Harness metadata changed" in result["message"]


async def test_model_and_run_context_are_versioned_with_evaluation_evidence(lesson_project, monkeypatch):
    config, backend, _ = lesson_project
    # Synthetic metadata verifies persistence; it is not an actual model run.
    result_node = json.loads(await graph_tools.execute_tool("add_note", {
        "content": "Fixture evaluation report: the expected stable-ID result matched.",
        "title": "Fixture benchmark result",
    }, config))
    first = await capture(config, author_model="fixture-author-v1", author_environment="Fixture author host")
    second = await capture(config, supersedes=first["node_id"],
                           author_model="fixture-author-v2", author_environment="Fixture author host 2",
                           tested_model="fixture-test-v2", tested_environment="Fixture test runner; local SQLite",
                           benchmark_result_ids=[result_node["node_id"]])
    old = await backend.get_node("Document", first["node_id"])
    new = await backend.get_node("Document", second["node_id"])
    assert old["skill_author_model"] == "fixture-author-v1"
    assert old["skill_tested_model"] == ""
    assert new["skill_author_model"] == "fixture-author-v2"
    assert new["skill_tested_model"] == "fixture-test-v2"
    assert new["skill_benchmark_result_ids"] == [result_node["node_id"]]
    assert any(s == second["execution_id"] and rel == "USED" and t == result_node["node_id"]
               for _, s, rel, _, t in backend.rels)
    body = Path(second["path"]).read_text()
    assert "fixture-author-v2" in body and "Fixture test runner; local SQLite" in body
    metadata = (await fresh_neighbor_read(config, monkeypatch))["linked_skills"][0]
    assert metadata["author_model"] == "fixture-author-v2"
    assert metadata["tested_model"] == "fixture-test-v2"
    assert "Fixture test runner" not in json.dumps(metadata)


async def test_cannot_claim_tested_model_without_result_evidence(lesson_project):
    config, _, _ = lesson_project
    result = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(
        tested_model="fixture-test", tested_environment="fixture-runner",
    ), config))
    assert result["error"] == "invalid_lesson"
    assert "benchmark_result_ids" in result["message"]


async def test_capture_replay_preserves_content_versions_and_history(lesson_project):
    from wheeler.knowledge.store import read_node
    from wheeler.knowledge.versions import content_hash_of, read_version

    config, backend, root = lesson_project
    saved = await capture(config)
    node_id = saved['node_id']
    before = read_node(root / 'knowledge', node_id)
    assert before.content_version == 2
    assert read_version(root / 'knowledge', node_id, 1)['skill_state'] == 'incomplete'
    await capture(config)
    after = read_node(root / 'knowledge', node_id)
    assert after.content_version == before.content_version
    assert after.content_hash == before.content_hash == content_hash_of(after)
    assert (await backend.get_node('Document', node_id))['content_version'] == after.content_version


async def test_skill_lifecycle_works_without_optional_synthesis(lesson_project):
    from wheeler.knowledge.store import read_node

    config, backend, root = lesson_project
    config.synthesis_enabled = False
    saved = await capture(config, accepted=False)
    accepted = json.loads(await graph_tools.execute_tool('accept_skill', {'node_id': saved['node_id']}, config))
    assert 'error' not in accepted, accepted
    assert not (root / 'synthesis' / (saved['node_id'] + '.md')).exists()
    retired = json.loads(await graph_tools.execute_tool('retire_skill', {
        'node_id': saved['node_id'], 'reason': 'Replaced by validation',
    }, config))
    assert 'error' not in retired, retired
    assert retired['storage'] == {'json': True, 'synthesis': True}
    stored = read_node(root / 'knowledge', saved['node_id'])
    assert stored.skill_state == 'retracted'
    assert stored.content_version == 4
    assert (await backend.get_node('Document', saved['node_id']))['content_version'] == 4


async def test_refresh_recovers_graph_commit_without_losing_version_snapshot(lesson_project, monkeypatch):
    from wheeler.knowledge import store
    from wheeler.knowledge.versions import read_version

    config, backend, root = lesson_project
    candidate = await capture(config, accepted=False)
    node_id = candidate['node_id']
    write = store.write_node

    def fail_accept(directory, node):
        if getattr(node, 'skill_state', '') == 'accepted':
            raise OSError('Injected canonical write failure')
        return write(directory, node)

    monkeypatch.setattr(store, 'write_node', fail_accept)
    failed = json.loads(await graph_tools.execute_tool('accept_skill', {'node_id': node_id}, config))
    assert failed['error'] == 'incomplete_lesson'
    assert store.read_node(root / 'knowledge', node_id).content_version == 2
    monkeypatch.setattr(store, 'write_node', write)
    recovered = json.loads(await graph_tools.execute_tool('accept_skill', {'node_id': node_id}, config))
    assert 'error' not in recovered, recovered
    stored = store.read_node(root / 'knowledge', node_id)
    assert stored.content_version == 3
    assert stored.skill_state == 'accepted'
    assert read_version(root / 'knowledge', node_id, 2)['skill_state'] == 'candidate'
    assert (await backend.get_node('Document', node_id))['content_version'] == 3


async def test_capture_replay_does_not_recreate_provenance_edges(lesson_project, monkeypatch):
    from unittest.mock import AsyncMock

    config, backend, _ = lesson_project
    await capture(config)
    create = AsyncMock(wraps=backend.create_relationship)
    monkeypatch.setattr(backend, "create_relationship", create)
    await capture(config)
    create.assert_not_called()


async def test_oversized_unicode_skill_is_rejected_before_any_capture_writes(lesson_project):
    import copy

    config, backend, root = lesson_project
    before_nodes = copy.deepcopy(backend.nodes)
    before_files = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    # Both requests fit the per-field character limits; the second only exceeds
    # the byte budget once the saved problem statement joins the instructions.
    for overrides in (
        {"instructions": "界" * 90_000},
        {"instructions": "界" * 85_000, "problem_statement": "界" * 5_000},
    ):
        result = json.loads(await graph_tools.execute_tool("capture_lesson", lesson_args(**overrides), config))
        assert result["error"] == "invalid_lesson", result
        assert "256 KiB" in result["message"]
        assert backend.nodes == before_nodes
        assert sorted(str(path.relative_to(root)) for path in root.rglob("*")) == before_files


async def test_unicode_skill_within_byte_budget_remains_discoverable(lesson_project, monkeypatch):
    config, _, _ = lesson_project
    saved = await capture(config, instructions="界" * 85_000)
    assert Path(saved["path"]).stat().st_size <= 256 * 1024
    discovered = await fresh_neighbor_read(config, monkeypatch)
    assert [skill["id"] for skill in discovered["linked_skills"]] == [saved["node_id"]]
