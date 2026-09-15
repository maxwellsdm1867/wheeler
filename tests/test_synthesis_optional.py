"""The synthesis layer is a human view and can be switched off.

`synthesis/` holds Obsidian-compatible markdown rendered from the knowledge
JSON. Nothing in Wheeler reads it back: every tool reads the JSON or queries
the graph. A project that does not browse the graph in Obsidian pays a file
write on every mutation plus, on every link, a re-render of BOTH endpoints
that costs two graph queries each. `synthesis_enabled: false` turns that off.

The graph and JSON layers must be untouched by the flag, and the consistency
checker must not then call every node drifted.
"""

from __future__ import annotations

import json
import uuid

import pytest

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


def _cfg(tmp_path, *, synthesis: bool):
    from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    tag = f"synopt-{uuid.uuid4().hex[:8]}"
    cfg = WheelerConfig(
        neo4j=Neo4jConfig(uri=_URI, username="neo4j", password=_TEST_PASSWORD, database="neo4j", project_tag=tag),
        project=ProjectMeta(name="synthesis-optional"),
        project_root=str(tmp_path),
        synthesis_enabled=synthesis,
    )
    gt.reset_backend_cache()
    invalidate_async_driver()
    return cfg


def _cleanup(cfg):
    from neo4j import GraphDatabase
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    d = GraphDatabase.driver(_URI, auth=("neo4j", _TEST_PASSWORD))
    with d.session(database="neo4j") as s:
        s.run("MATCH (n {_wheeler_project: $t}) DETACH DELETE n", t=cfg.neo4j.project_tag).consume()
    d.close()
    gt.reset_backend_cache()
    invalidate_async_driver()


def test_the_flag_defaults_to_on_so_nothing_changes_for_existing_projects():
    from wheeler.config import WheelerConfig

    assert WheelerConfig().synthesis_enabled is True


def test_a_config_without_the_key_reads_as_on():
    """An existing wheeler.yaml has no such key and must keep its behaviour."""
    from wheeler.tools.graph_tools import _synthesis_enabled

    class Legacy:
        pass

    assert _synthesis_enabled(Legacy()) is True


@needs_neo4j
@pytest.mark.asyncio
async def test_off_skips_synthesis_but_keeps_graph_and_json_intact(tmp_path):
    from wheeler.tools.graph_tools import execute_tool

    cfg = _cfg(tmp_path, synthesis=False)
    try:
        f = json.loads(await execute_tool("add_finding", {"description": "a finding", "confidence": 0.7}, cfg))
        h = json.loads(await execute_tool("add_hypothesis", {"statement": "a hypothesis"}, cfg))
        await execute_tool("link_nodes", {"source_id": f["node_id"], "target_id": h["node_id"], "relationship": "SUPPORTS"}, cfg)
        await execute_tool("update_node", {"node_id": f["node_id"], "description": "edited"}, cfg)
        await execute_tool("set_tier", {"node_id": f["node_id"], "tier": "reference"}, cfg)

        # JSON layer: complete, including the version bumps
        doc = json.loads((tmp_path / "knowledge" / f"{f['node_id']}.json").read_text())
        assert doc["description"] == "edited" and doc["tier"] == "reference"
        assert doc["content_version"] == 3

        # synthesis layer: nothing written at all
        assert not (tmp_path / "synthesis").exists() or not list((tmp_path / "synthesis").glob("*.md"))

        # graph layer: the edge is there
        from neo4j import GraphDatabase

        d = GraphDatabase.driver(_URI, auth=("neo4j", _TEST_PASSWORD))
        with d.session(database="neo4j") as s:
            rows = s.run(
                "MATCH ({id:$a})-[r:SUPPORTS]->({id:$b}) RETURN type(r) AS t",
                a=f["node_id"], b=h["node_id"],
            ).data()
        d.close()
        assert [r["t"] for r in rows] == ["SUPPORTS"]
    finally:
        _cleanup(cfg)


@needs_neo4j
@pytest.mark.asyncio
async def test_on_still_writes_synthesis(tmp_path):
    """The control: the same sequence with the flag on produces the view."""
    from wheeler.tools.graph_tools import execute_tool

    cfg = _cfg(tmp_path, synthesis=True)
    try:
        f = json.loads(await execute_tool("add_finding", {"description": "a finding", "confidence": 0.7}, cfg))
        h = json.loads(await execute_tool("add_hypothesis", {"statement": "a hypothesis"}, cfg))
        await execute_tool("link_nodes", {"source_id": f["node_id"], "target_id": h["node_id"], "relationship": "SUPPORTS"}, cfg)
        for nid in (f["node_id"], h["node_id"]):
            assert (tmp_path / "synthesis" / f"{nid}.md").exists()
        # the link re-render ran: the endpoint's view names its neighbour
        assert h["node_id"] in (tmp_path / "synthesis" / f"{f['node_id']}.md").read_text()
    finally:
        _cleanup(cfg)


@needs_neo4j
@pytest.mark.asyncio
async def test_off_does_not_make_the_consistency_checker_report_drift(tmp_path):
    from wheeler.consistency import check_consistency
    from wheeler.tools.graph_tools import execute_tool

    cfg = _cfg(tmp_path, synthesis=False)
    try:
        ids = []
        for i in range(3):
            r = json.loads(await execute_tool("add_finding", {"description": f"f{i}", "confidence": 0.5}, cfg))
            ids.append(r["node_id"])
        report = await check_consistency(cfg)
        assert [i for i in ids if i in report.synthesis_missing] == []

        # a leftover file from before the switch is still reported as an orphan
        syn = tmp_path / "synthesis"
        syn.mkdir(parents=True, exist_ok=True)
        (syn / "F-00000000.md").write_text("stale view\n")
        report2 = await check_consistency(cfg)
        assert "F-00000000" in report2.synthesis_orphaned
    finally:
        _cleanup(cfg)


@needs_neo4j
@pytest.mark.asyncio
async def test_the_write_receipt_does_not_record_a_failed_layer(tmp_path):
    """Off means "nothing to write", not "the synthesis write failed"."""
    from wheeler.tools.graph_tools import _write_knowledge_file

    cfg = _cfg(tmp_path, synthesis=False)
    try:
        result = json.dumps({"node_id": "F-abcd1234", "label": "Finding"})
        json_ok, synth_ok, _hash, _tok = _write_knowledge_file(
            "add_finding", {"description": "x", "confidence": 0.5}, result, cfg
        )
        assert json_ok is True and synth_ok is True
    finally:
        _cleanup(cfg)


@needs_neo4j
@pytest.mark.asyncio
async def test_the_writers_that_bypass_the_dual_write_helper_are_gated_too(tmp_path):
    """Three paths build the markdown themselves instead of going through
    _write_synthesis_file, so a gate on that helper alone leaked.

    Found by the independent Verifier: ensure_artifact on a hash change runs
    propagate_invalidation, which writes synthesis directly; detect_stale
    reaches the same code; and execute_merge renders its own merged view.
    """
    from wheeler.graph.provenance import detect_stale_scripts
    from wheeler.merge import execute_merge
    from wheeler.tools.graph_tools import execute_tool

    cfg = _cfg(tmp_path, synthesis=False)

    def views():
        d = tmp_path / "synthesis"
        return sorted(p.name for p in d.glob("*.md")) if d.exists() else []

    try:
        script = tmp_path / "a.py"
        script.write_text("x = 1\n")
        art = json.loads(await execute_tool("ensure_artifact", {"path": str(script)}, cfg))
        fin = json.loads(await execute_tool("add_finding", {"description": "downstream", "confidence": 0.6}, cfg))
        ex = json.loads(await execute_tool("add_execution", {"kind": "script_run", "description": "r"}, cfg))
        await execute_tool("link_nodes", {"source_id": ex["node_id"], "target_id": art["node_id"], "relationship": "USED"}, cfg)
        await execute_tool("link_nodes", {"source_id": fin["node_id"], "target_id": ex["node_id"], "relationship": "WAS_GENERATED_BY"}, cfg)

        script.write_text("x = 2\n")  # hash change -> propagate_invalidation
        await execute_tool("ensure_artifact", {"path": str(script)}, cfg)
        assert views() == [], f"propagate_invalidation leaked: {views()}"

        script.write_text("x = 3\n")
        await detect_stale_scripts(cfg)
        assert views() == [], f"detect_stale leaked: {views()}"

        a = json.loads(await execute_tool("add_finding", {"description": "dup a", "confidence": 0.5}, cfg))
        b = json.loads(await execute_tool("add_finding", {"description": "dup b", "confidence": 0.5}, cfg))
        merged = await execute_merge(cfg, a["node_id"], b["node_id"])
        assert views() == [], f"execute_merge leaked: {views()}"
        # and the merge itself still completed: the rename it used to do
        # unconditionally must not abort now that no temp view is written
        assert merged.get("status") == "merged", merged
        assert (tmp_path / "knowledge" / f"{a['node_id']}.json").exists()
    finally:
        _cleanup(cfg)


@needs_neo4j
@pytest.mark.asyncio
async def test_off_skips_the_relationship_queries_not_just_the_file(tmp_path):
    """The per-link gate is where the whole performance claim lives.

    Deleting it leaves no file behind either way, because the inner write is
    also gated, so nothing failed when the Verifier removed it. What it does
    restore is two graph queries per endpoint on every link. Assert on the
    queries, not the file.
    """
    from wheeler.tools.graph_tools import execute_tool
    import wheeler.tools.graph_tools as gt

    for enabled, expect in ((False, 0), (True, None)):
        cfg = _cfg(tmp_path / ("on" if enabled else "off"), synthesis=enabled)
        try:
            f = json.loads(await execute_tool("add_finding", {"description": "f", "confidence": 0.5}, cfg))
            h = json.loads(await execute_tool("add_hypothesis", {"statement": "h"}, cfg))
            backend = await gt._get_backend(cfg)
            seen: list[str] = []
            real = backend.run_cypher

            async def spy(query, params=None, _real=real, _seen=seen):
                _seen.append(query)
                return await _real(query, params)

            backend.run_cypher = spy  # type: ignore[method-assign]
            try:
                await execute_tool(
                    "link_nodes",
                    {"source_id": f["node_id"], "target_id": h["node_id"], "relationship": "SUPPORTS"},
                    cfg,
                )
            finally:
                backend.run_cypher = real  # type: ignore[method-assign]

            rel_queries = [q for q in seen if "RETURN type(r)" in q]
            if expect == 0:
                assert rel_queries == [], f"synthesis off still ran {len(rel_queries)} relationship queries"
            else:
                assert len(rel_queries) == 4, f"expected 4 relationship queries with synthesis on, got {len(rel_queries)}"
        finally:
            _cleanup(cfg)
