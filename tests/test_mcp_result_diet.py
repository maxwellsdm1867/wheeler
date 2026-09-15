"""MCP result diet: wrappers return what the model acts on, full payload one flag away.

Background (docs/mcp-token-audit.md): in 29 real sessions, 96 percent of an
update_node result echoed the text just written, 89 percent of an
ensure_artifact result was paths and hashes the caller passed in or never
used, 40 percent of show_node was the change log, and show_node failed on 14
percent of calls because the JSON layer was missing while the graph had the
node. The wrapper layer is where the model-facing payload is built, so that is
where these tests bite; the core handlers keep their full results.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.mcp_shared import (
    _compact_write_result,
    _strip_empty,
    _trim_rows,
    _trim_text,
)

_TEST_PASSWORD = "research-graph"


def _local_uri() -> str | None:
    from neo4j import GraphDatabase

    for port in (7717, 7687, 7697, 7707):
        uri = f"bolt://localhost:{port}"
        try:
            d = GraphDatabase.driver(uri, auth=("neo4j", _TEST_PASSWORD))
            with d.session(database="neo4j") as s:
                s.run("RETURN 1").consume()
            d.close()
            return uri
        except Exception:
            continue
    return None


_URI = _local_uri()
needs_neo4j = pytest.mark.skipif(_URI is None, reason="no local Neo4j answering the test password")


# ---------------------------------------------------------------- helpers


class TestHelpers:
    def test_trim_text_cuts_and_reports_the_remainder(self):
        long = "x" * 1000
        out = _trim_text(long, 240)
        assert out.startswith("x" * 240) and out.endswith("... [+760 chars]")
        assert _trim_text("short", 240) == "short"
        assert _trim_text(42, 240) == 42

    def test_trim_rows_only_touches_text_keys(self):
        rows = {"questions": [{"id": "Q-1", "question": "q" * 500, "priority": 7}], "count": 1}
        out = _trim_rows(rows)
        assert out["questions"][0]["id"] == "Q-1" and out["questions"][0]["priority"] == 7
        assert len(out["questions"][0]["question"]) < 300
        assert out["count"] == 1

    def test_strip_empty(self):
        assert _strip_empty({"a": "", "b": None, "c": [], "d": {}, "e": 0, "f": "x", "g": False}) == {"e": 0, "f": "x", "g": False}

    def test_compact_write_result_counts_inputs_and_shortens_hints(self):
        parsed = {
            "node_id": "F-1", "label": "Finding", "status": "created",
            "provenance": {"execution_id": "X-1", "execution_kind": "write", "linked_inputs": ["A-1"] * 40},
            "similar_existing": [{"node_id": "F-2", "text": "y" * 900, "similarity": 0.91}],
        }
        out = _compact_write_result(parsed)
        assert out["provenance"] == {"execution_id": "X-1", "execution_kind": "write", "linked_inputs_count": 40}
        assert out["similar_existing"][0]["node_id"] == "F-2"
        assert len(out["similar_existing"][0]["text"]) < 160
        assert _compact_write_result({"error": "x"}) == {"error": "x"}


# ------------------------------------------------------------- mutations


class TestMutationWrappers:
    @pytest.mark.asyncio
    async def test_update_node_drops_the_old_new_echo_unless_verbose(self):
        core = json.dumps({
            "node_id": "F-1", "label": "Finding", "updated_fields": ["description"],
            "changes": {"description": {"old": "a" * 2000, "new": "b" * 2000}}, "status": "updated",
        })
        from wheeler.mcp_mutations import update_node

        fn = getattr(update_node, "fn", update_node)
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=core):
            lean = await fn("F-1", description="b" * 2000)
            full = await fn("F-1", description="b" * 2000, verbose=True)
        assert lean == {"node_id": "F-1", "label": "Finding", "updated_fields": ["description"], "status": "updated"}
        assert "changes" in full and len(json.dumps(full)) > 4000

    @pytest.mark.asyncio
    async def test_ensure_artifact_keeps_id_label_action_and_drops_echoes(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x = 1\n")
        core = json.dumps({
            "node_id": "S-1", "label": "Script", "action": "updated", "path": str(f), "stored_path": "${code}/a.py",
            "path_upgraded": False, "hash": "h" * 64, "previous_hash": "g" * 64, "stale_downstream": 0,
            "provenance": {"execution_id": "X-9", "execution_kind": "script", "linked_inputs": ["D-1", "D-2"]},
        })
        from wheeler.mcp_mutations import ensure_artifact

        fn = getattr(ensure_artifact, "fn", ensure_artifact)
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=core):
            lean = await fn(str(f))
            full = await fn(str(f), verbose=True)
        assert lean == {
            "node_id": "S-1", "label": "Script", "action": "updated",
            "provenance": {"execution_id": "X-9", "execution_kind": "script", "linked_inputs_count": 2},
        }
        assert full["hash"] == "h" * 64 and full["stored_path"] == "${code}/a.py"

    @pytest.mark.asyncio
    async def test_ensure_artifact_keeps_nonzero_stale_count_and_errors_intact(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x = 1\n")
        from wheeler.mcp_mutations import ensure_artifact

        fn = getattr(ensure_artifact, "fn", ensure_artifact)
        stale = json.dumps({"node_id": "S-1", "label": "Script", "action": "updated", "hash": "h", "stale_downstream": 52})
        err = json.dumps({"error": "label_mismatch", "node_id": "S-1", "existing_label": "Script", "detected_label": "Document", "path": str(f), "fix": "..."})
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=stale):
            out = await fn(str(f))
        assert out["stale_downstream"] == 52 and "hash" not in out
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=err):
            out = await fn(str(f))
        assert out == json.loads(err)

    @pytest.mark.asyncio
    async def test_add_finding_compacts_provenance_and_similar_hints(self):
        core = json.dumps({
            "node_id": "F-1", "label": "Finding", "status": "created",
            "provenance": {"execution_id": "X-1", "execution_kind": "write", "linked_inputs": ["P-1"] * 60},
        })
        from wheeler.mcp_mutations import add_finding

        fn = getattr(add_finding, "fn", add_finding)
        with patch("wheeler.mcp_mutations.graph_tools.execute_tool", new_callable=AsyncMock, return_value=core), \
             patch("wheeler.mcp_mutations._check_similar_nodes", return_value=[{"node_id": "F-0", "text": "z" * 700, "similarity": 0.9}]):
            out = await fn("a finding", 0.7)
        assert out["provenance"]["linked_inputs_count"] == 60 and "linked_inputs" not in out["provenance"]
        assert len(out["similar_existing"][0]["text"]) < 160


# ------------------------------------------------------------------ query


class TestQueryWrappers:
    @pytest.mark.asyncio
    async def test_every_query_tool_trims_text_unless_full(self, monkeypatch):
        import wheeler.mcp_query as q
        from wheeler import mcp_shared

        monkeypatch.setattr(mcp_shared, "DISCLOSURE", "trimmed")  # the pointer default is tested in test_versions
        long_q = "w" * 1500
        core = json.dumps({"questions": [{"id": "Q-1", "question": long_q, "priority": 5}], "count": 1})
        fn = getattr(q.query_open_questions, "fn", q.query_open_questions)
        with patch("wheeler.mcp_query.graph_tools.execute_tool", new_callable=AsyncMock, return_value=core):
            lean = await fn()
            full = await fn(full=True)
        assert lean["questions"][0]["question"].endswith("... [+1260 chars]")
        assert full["questions"][0]["question"] == long_q

    def test_all_eleven_query_tools_accept_full(self):
        import wheeler.mcp_query as q

        tools = asyncio.run(q.mcp.list_tools())
        assert len(tools) == 11
        for t in tools:
            props = (getattr(t, "inputSchema", None) or getattr(t, "parameters", None) or {}).get("properties", {})
            assert "full" in props, t.name


# ------------------------------------------------------------------- core


class TestCoreWrappers:
    @pytest.mark.asyncio
    async def test_run_cypher_caps_rows_and_says_so(self):
        from wheeler.mcp_core import run_cypher

        fn = getattr(run_cypher, "fn", run_cypher)
        backend = AsyncMock()
        backend.run_cypher = AsyncMock(return_value=[{"i": i} for i in range(250)])
        with patch("wheeler.mcp_core.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            out = await fn("MATCH (n) RETURN n.id AS i")
            small = await fn("MATCH (n) RETURN n.id AS i", limit=10)
            uncapped = await fn("MATCH (n) RETURN n.id AS i", limit=0)
        assert out["count"] == 100 and out["truncated"] is True and out["total_rows"] == 250
        assert small["count"] == 10 and len(small["results"]) == 10
        assert uncapped["count"] == 250 and "truncated" not in uncapped

    @pytest.mark.asyncio
    async def test_search_findings_trims_hit_text_unless_full(self, monkeypatch):
        from wheeler import mcp_core, mcp_shared
        from wheeler.mcp_core import search_findings

        monkeypatch.setattr(mcp_shared, "DISCLOSURE", "trimmed")
        monkeypatch.setattr(mcp_core, "DISCLOSURE", "trimmed")

        fn = getattr(search_findings, "fn", search_findings)
        hits = [{"id": "F-1", "type": "Finding", "description": "d" * 2000, "rrf_score": 0.5}]
        with patch("wheeler.search.retrieval.multi_search", new_callable=AsyncMock, return_value=hits):
            lean = await fn("q")
            full = await fn("q", full=True)
        assert len(lean["results"][0]["text"]) < 300 and lean["results"][0]["node_id"] == "F-1"
        assert len(full["results"][0]["text"]) == 2000

    def test_show_node_requires_an_id(self):
        from wheeler.mcp_core import show_node

        fn = getattr(show_node, "fn", show_node)
        assert "error" in asyncio.run(fn())


# ----------------------------------------------------------------- ops


class TestOpsWrappers:
    @pytest.mark.asyncio
    async def test_detect_stale_omits_hashes_unless_verbose(self):
        from types import SimpleNamespace

        from wheeler.mcp_ops import detect_stale

        fn = getattr(detect_stale, "fn", detect_stale)
        rows = [SimpleNamespace(node_id="S-1", path="a.py", reason="changed", origin_host="h", stored_hash="a" * 64, current_hash="b" * 64)]
        with patch("wheeler.mcp_ops.provenance.detect_stale_scripts", new_callable=AsyncMock, return_value=rows):
            lean = await fn()
            full = await fn(verbose=True)
        assert lean == [{"node_id": "S-1", "path": "a.py", "reason": "changed", "origin_host": "h"}]
        assert full[0]["stored_hash"] == "a" * 64


    @pytest.mark.asyncio
    async def test_validate_citations_lists_only_problems_unless_verbose(self):
        from types import SimpleNamespace

        from wheeler.mcp_ops import validate_citations
        from wheeler.validation.citations import CitationStatus

        fn = getattr(validate_citations, "fn", validate_citations)
        rows = [SimpleNamespace(node_id=f"F-{i}", status=CitationStatus.VALID, label="Finding", details="ok") for i in range(40)]
        rows.append(SimpleNamespace(node_id="F-x", status=CitationStatus.STALE, label="Finding", details="script changed"))
        with patch("wheeler.mcp_ops.citations.validate_citations", new_callable=AsyncMock, return_value=rows):
            lean = await fn("[F-1] ... [F-x]")
            full = await fn("[F-1] ... [F-x]", verbose=True)
        assert lean["total"] == 41 and lean["valid"] == 40
        assert lean["by_status"] == {"valid": 40, "stale": 1}
        assert lean["results"] == [{"node_id": "F-x", "status": "stale", "label": "Finding", "details": "script changed"}]
        assert len(full["results"]) == 41


class TestSearchContextCap:
    @pytest.mark.asyncio
    async def test_related_nodes_capped_and_relationships_filtered(self):
        from wheeler.mcp_core import search_context

        fn = getattr(search_context, "fn", search_context)
        seeds = [{"id": "F-s", "type": "Finding"}]
        expanded = {
            "seed_nodes": [{"id": "F-s", "summary": "seed"}],
            "related_nodes": [{"id": f"N-{i}", "summary": "r"} for i in range(60)],
            "relationships": [{"source": "F-s", "relationship": "USED", "target": f"N-{i}"} for i in range(60)],
            "total_related": 60,
        }
        with patch("wheeler.search.retrieval.multi_search", new_callable=AsyncMock, return_value=seeds), \
             patch("wheeler.search.retrieval.expand_search_results", new_callable=AsyncMock, return_value=json.loads(json.dumps(expanded))):
            lean = await fn("q")
        assert len(lean["related_nodes"]) == 20 and lean["truncated_related"] is True
        assert lean["total_related"] == 60
        assert {r["target"] for r in lean["relationships"]} == {f"N-{i}" for i in range(20)}
        with patch("wheeler.search.retrieval.multi_search", new_callable=AsyncMock, return_value=seeds), \
             patch("wheeler.search.retrieval.expand_search_results", new_callable=AsyncMock, return_value=json.loads(json.dumps(expanded))):
            full = await fn("q", max_related=0)
        assert len(full["related_nodes"]) == 60 and "truncated_related" not in full


# ------------------------------------------------- show_node, live layers


@pytest.fixture
def live_cfg(tmp_path):
    from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    tag = f"diettest-{uuid.uuid4().hex[:8]}"
    cfg = WheelerConfig(
        neo4j=Neo4jConfig(uri=_URI, username="neo4j", password=_TEST_PASSWORD, database="neo4j", project_tag=tag),
        project=ProjectMeta(name="result-diet-test"),
        project_root=str(tmp_path),
    )
    gt.reset_backend_cache()
    invalidate_async_driver()
    yield cfg
    from neo4j import GraphDatabase

    d = GraphDatabase.driver(_URI, auth=("neo4j", _TEST_PASSWORD))
    with d.session(database="neo4j") as s:
        s.run("MATCH (n {_wheeler_project: $tag}) DETACH DELETE n", tag=tag).consume()
    d.close()
    gt.reset_backend_cache()
    invalidate_async_driver()


@needs_neo4j
@pytest.mark.asyncio
async def test_show_node_batch_change_log_fields_and_graph_fallback(live_cfg, tmp_path, monkeypatch):
    import wheeler.mcp_core as core
    from wheeler.tools.graph_tools import execute_tool

    monkeypatch.setattr(core, "_config", live_cfg)
    ids = []
    for i in range(3):
        r = json.loads(await execute_tool("add_finding", {"description": f"finding {i} " + "t" * 50, "confidence": 0.6}, live_cfg))
        ids.append(r["node_id"])
    # an edit so the change_log has more than the creation entry
    await execute_tool("update_node", {"node_id": ids[0], "description": "edited " + "u" * 50}, live_cfg)

    fn = getattr(core.show_node, "fn", core.show_node)

    one = await fn(ids[0])
    assert one["id"] == ids[0] and "change_log" not in one and one["description"].startswith("edited")
    assert "" not in one.values() and [] not in one.values()
    with_log = await fn(ids[0], include_change_log=True)
    assert len(with_log["change_log"]) >= 2

    picked = await fn(ids[0], fields="confidence")
    assert set(picked) <= {"id", "type", "confidence"} and picked["confidence"] == 0.6

    # JSON layer gone for one node: the graph still has it, so show_node must too.
    (tmp_path / "knowledge" / f"{ids[1]}.json").unlink()
    many = await fn(node_ids=ids + ["F-00000000"])
    assert many["count"] == 3 and many["missing"] == ["F-00000000"]
    by_id = {n["id"]: n for n in many["nodes"]}
    assert by_id[ids[1]].get("source") == "graph" and by_id[ids[1]]["description"].startswith("finding 1")
    assert "source" not in by_id[ids[0]]


@pytest.mark.asyncio
async def test_run_cypher_binds_ptag_and_warns_on_unscoped_query_in_shared_db(monkeypatch):
    """Raw Cypher is not project-scoped; in a shared database an unscoped MATCH reads
    every project's nodes. The wrapper binds $ptag and says so in the result."""
    import wheeler.mcp_core as core
    from wheeler.config import Neo4jConfig, WheelerConfig

    fn = getattr(core.run_cypher, "fn", core.run_cypher)
    backend = AsyncMock()
    backend.run_cypher = AsyncMock(return_value=[{"i": 1}])
    monkeypatch.setattr(core, "_config", WheelerConfig(neo4j=Neo4jConfig(project_tag="proj-a")))
    with patch("wheeler.mcp_core.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
        unscoped = await fn("MATCH (n:Finding) RETURN n.id")
        scoped = await fn("MATCH (n:Finding) WHERE n._wheeler_project = $ptag RETURN n.id")
    assert backend.run_cypher.call_args_list[0].args[1] == {"ptag": "proj-a"}
    assert unscoped["project_tag"] == "proj-a" and "warning" in unscoped
    assert scoped["project_tag"] == "proj-a" and "warning" not in scoped

    monkeypatch.setattr(core, "_config", WheelerConfig(neo4j=Neo4jConfig(project_tag="")))
    with patch("wheeler.mcp_core.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
        solo = await fn("MATCH (n) RETURN n.id")
    assert backend.run_cypher.call_args_list[-1].args[1] is None
    assert "project_tag" not in solo and "warning" not in solo
