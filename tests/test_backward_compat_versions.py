"""Nodes written before versioning existed must keep working, everywhere.

Wheeler graphs predate `content_version`, `content_hash` and `content_tokens`
by most of their history: a real project has thousands of nodes whose JSON
files have none of those keys and whose graph nodes have none of those
properties, linked by edges with no `created_at` or version pins. Those nodes
are not migrated, by design, so every read and write path has to treat their
absence as version 1 rather than as an error or a false signal.

Every test here builds a genuinely OLD node: created through the normal path,
then stripped of the new keys in BOTH layers, and its edges stripped of their
pins, so what is exercised is the real pre-upgrade shape rather than a
defaulted model. Live against the local Neo4j under a per-test tag.
"""

from __future__ import annotations

import json
import uuid

import pytest

from wheeler.knowledge import versions as V

_TEST_PASSWORD = "research-graph"


def _local_uri() -> str | None:
    import os

    if uri := os.environ.get("WHEELER_TEST_NEO4J_URI"):
        return uri
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

# Exactly what a pre-versioning node lacks.
NEW_NODE_PROPS = ("content_version", "content_hash", "content_tokens")
NEW_EDGE_PROPS = ("created_at", "source_version", "target_version")


def _graph(query, **params):
    from neo4j import GraphDatabase

    d = GraphDatabase.driver(_URI, auth=("neo4j", _TEST_PASSWORD))
    with d.session(database="neo4j") as s:
        rows = s.run(query, **params).data()
    d.close()
    return rows


def _make_old(node_id: str, knowledge_dir) -> None:
    """Strip the versioning keys from both layers: this is now a pre-upgrade node."""
    _graph(
        "MATCH (n {id: $id}) REMOVE n.content_version, n.content_hash, n.content_tokens",
        id=node_id,
    )
    f = knowledge_dir / f"{node_id}.json"
    data = json.loads(f.read_text())
    for k in NEW_NODE_PROPS:
        data.pop(k, None)
    f.write_text(json.dumps(data, indent=2))


def _make_edges_old(node_id: str) -> None:
    _graph(
        "MATCH ({id: $id})-[r]-() REMOVE r.created_at, r.source_version, r.target_version",
        id=node_id,
    )


@pytest.fixture
def live_cfg(tmp_path):
    from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    tag = f"bctest-{uuid.uuid4().hex[:8]}"
    cfg = WheelerConfig(
        neo4j=Neo4jConfig(uri=_URI, username="neo4j", password=_TEST_PASSWORD, database="neo4j", project_tag=tag),
        project=ProjectMeta(name="backward-compat-test"),
        project_root=str(tmp_path),
    )
    gt.reset_backend_cache()
    invalidate_async_driver()
    yield cfg
    _graph("MATCH (n {_wheeler_project: $tag}) DETACH DELETE n", tag=tag)
    gt.reset_backend_cache()
    invalidate_async_driver()


async def _old_finding(cfg, tmp_path, text="legacy finding text", **extra):
    """A Finding indistinguishable from one written before versioning existed."""
    from wheeler.tools.graph_tools import execute_tool

    r = json.loads(await execute_tool("add_finding", {"description": text, "confidence": 0.6, **extra}, cfg))
    nid = r["node_id"]
    _make_old(nid, tmp_path / "knowledge")
    return nid


# ---------------------------------------------------------------- the fixture itself


@needs_neo4j
@pytest.mark.asyncio
async def test_the_old_shape_really_is_old(live_cfg, tmp_path):
    """Guard the guard: if _make_old stopped stripping, every test below would pass vacuously."""
    nid = await _old_finding(live_cfg, tmp_path)
    props = _graph("MATCH (n {id: $id}) RETURN keys(n) AS k", id=nid)[0]["k"]
    assert not (set(NEW_NODE_PROPS) & set(props)), props
    on_disk = json.loads((tmp_path / "knowledge" / f"{nid}.json").read_text())
    assert not (set(NEW_NODE_PROPS) & set(on_disk))


# ---------------------------------------------------------------- reads


@needs_neo4j
@pytest.mark.asyncio
async def test_show_node_reads_an_old_node_as_version_1(live_cfg, tmp_path, monkeypatch):
    import wheeler.mcp_core as core

    monkeypatch.setattr(core, "_config", live_cfg)
    nid = await _old_finding(live_cfg, tmp_path)
    fn = getattr(core.show_node, "fn", core.show_node)

    node = await fn(nid)
    assert node["id"] == nid and node["description"] == "legacy finding text"
    assert node["content_version"] == 1  # model default, not an error
    assert node.get("content_hash", "") == ""  # never computed, and not faked

    # the version machinery reports it honestly: one readable version, no snapshots
    assert V.list_versions(tmp_path / "knowledge", nid, current=1) == [1]
    assert V.read_version(tmp_path / "knowledge", nid, 1)["description"] == "legacy finding text"
    with pytest.raises(FileNotFoundError):
        V.read_version(tmp_path / "knowledge", nid, 2)


@needs_neo4j
@pytest.mark.asyncio
async def test_if_changed_since_on_an_old_node_never_claims_unchanged(live_cfg, tmp_path, monkeypatch):
    """An old node has no hash, so the freshness check must fall to the safe side and return content."""
    import wheeler.mcp_core as core

    monkeypatch.setattr(core, "_config", live_cfg)
    nid = await _old_finding(live_cfg, tmp_path)
    fn = getattr(core.show_node, "fn", core.show_node)

    for token in ("", "deadbeefdeadbeef", "v2"):
        out = await fn(nid, if_changed_since=token) if token else await fn(nid)
        assert out.get("changed") is not False, token
        assert out["description"] == "legacy finding text"
    # "v1" is a truthful match for an unversioned node and may short-circuit
    stub = await fn(nid, if_changed_since="v1")
    assert stub["content_version"] == 1


@needs_neo4j
@pytest.mark.asyncio
async def test_pointer_listing_includes_old_nodes(live_cfg, tmp_path, monkeypatch):
    import wheeler.mcp_query as q
    from wheeler import mcp_shared

    monkeypatch.setattr(q, "_config", live_cfg)
    monkeypatch.setattr(mcp_shared, "DISCLOSURE", "pointer")
    nid = await _old_finding(live_cfg, tmp_path, text="legacy " + "z" * 400)

    fn = getattr(q.query_findings, "fn", q.query_findings)
    row = next(r for r in (await fn())["findings"] if r["id"] == nid)
    assert row["type"] == "Finding"
    assert row["content_version"] == 1  # coalesced, not missing
    assert len(row["updated"]) == 10  # falls back to the creation stamp
    assert row["headline"].startswith("legacy")
    assert "description" not in row


# ---------------------------------------------------------------- writes


@needs_neo4j
@pytest.mark.asyncio
async def test_updating_an_old_node_snapshots_the_legacy_state_as_v1(live_cfg, tmp_path):
    """The first edit of an old node must preserve the pre-edit text, not lose it."""
    from wheeler.tools.graph_tools import execute_tool

    kdir = tmp_path / "knowledge"
    nid = await _old_finding(live_cfg, tmp_path)

    await execute_tool("update_node", {"node_id": nid, "description": "edited text"}, live_cfg)

    after = json.loads((kdir / f"{nid}.json").read_text())
    assert after["content_version"] == 2 and len(after["content_hash"]) == 16
    assert after["content_tokens"] > 0
    assert after["description"] == "edited text"

    snap = V.read_version(kdir, nid, 1)
    assert snap["description"] == "legacy finding text"  # the legacy state survived
    assert V.list_versions(kdir, nid, current=2) == [1, 2]

    g = _graph("MATCH (n {id: $id}) RETURN n.content_version AS v, n.content_hash AS h", id=nid)[0]
    assert g["v"] == 2 and g["h"] == after["content_hash"]


@needs_neo4j
@pytest.mark.asyncio
async def test_set_tier_on_an_old_node(live_cfg, tmp_path):
    from wheeler.tools.graph_tools import execute_tool

    nid = await _old_finding(live_cfg, tmp_path)
    await execute_tool("set_tier", {"node_id": nid, "tier": "reference"}, live_cfg)
    after = json.loads((tmp_path / "knowledge" / f"{nid}.json").read_text())
    assert after["content_version"] == 2 and after["tier"] == "reference"
    assert V.read_version(tmp_path / "knowledge", nid, 1)["tier"] == "generated"


@needs_neo4j
@pytest.mark.asyncio
async def test_metadata_update_on_an_old_node_does_not_invent_a_version(live_cfg, tmp_path):
    from wheeler.tools.graph_tools import execute_tool

    nid = await _old_finding(live_cfg, tmp_path)
    await execute_tool("update_node", {"node_id": nid, "stale": True}, live_cfg)
    after = json.loads((tmp_path / "knowledge" / f"{nid}.json").read_text())
    assert after["stale"] is True
    assert after["content_version"] == 1  # still unversioned, as it should be
    assert not (tmp_path / "knowledge" / "versions" / nid).exists()


# ---------------------------------------------------------------- edges


@needs_neo4j
@pytest.mark.asyncio
async def test_old_edges_never_report_a_false_moved(live_cfg, tmp_path, monkeypatch):
    """An unpinned edge cannot know whether its endpoint moved, so it must not claim it did."""
    import wheeler.mcp_core as core
    from wheeler.tools.graph_tools import execute_tool

    monkeypatch.setattr(core, "_config", live_cfg)
    fid = await _old_finding(live_cfg, tmp_path)
    hid = json.loads(await execute_tool("add_hypothesis", {"statement": "legacy hypothesis"}, live_cfg))["node_id"]
    _make_old(hid, tmp_path / "knowledge")
    await execute_tool("link_nodes", {"source_id": fid, "target_id": hid, "relationship": "SUPPORTS"}, live_cfg)
    _make_edges_old(fid)

    edge = _graph("MATCH ({id: $f})-[r:SUPPORTS]->({id: $h}) RETURN keys(r) AS k", f=fid, h=hid)[0]["k"]
    assert not (set(NEW_EDGE_PROPS) & set(edge)), edge

    fn = getattr(core.show_node, "fn", core.show_node)
    hop = (await fn(fid, neighbors=True))["neighbors"]
    assert len(hop) == 1
    assert hop[0]["id"] == hid and hop[0]["content_version"] == 1
    assert "moved" not in hop[0]

    # even after the neighbour really moves, an unpinned edge stays silent
    await execute_tool("update_node", {"node_id": hid, "statement": "revised"}, live_cfg)
    hop2 = (await fn(fid, neighbors=True))["neighbors"]
    assert hop2[0]["content_version"] == 2
    assert "moved" not in hop2[0]


@needs_neo4j
@pytest.mark.asyncio
async def test_a_new_edge_onto_an_old_node_pins_version_1(live_cfg, tmp_path):
    from wheeler.tools.graph_tools import execute_tool

    fid = await _old_finding(live_cfg, tmp_path)
    hid = json.loads(await execute_tool("add_hypothesis", {"statement": "fresh hypothesis"}, live_cfg))["node_id"]
    await execute_tool("link_nodes", {"source_id": fid, "target_id": hid, "relationship": "SUPPORTS"}, live_cfg)
    e = _graph("MATCH ({id: $f})-[r:SUPPORTS]->({id: $h}) RETURN r.source_version AS sv, r.target_version AS tv", f=fid, h=hid)[0]
    assert e["sv"] == 1  # the old, unversioned endpoint reads as v1
    assert e["tv"] == 1


# ---------------------------------------------------------------- citations


@needs_neo4j
@pytest.mark.asyncio
async def test_citations_of_old_nodes(live_cfg, tmp_path):
    from wheeler.tools.graph_tools import execute_tool
    from wheeler.validation.citations import CitationStatus, validate_citations

    nid = await _old_finding(live_cfg, tmp_path)

    bare = await validate_citations(f"A claim [{nid}].", live_cfg)
    assert [r.status for r in bare] != [CitationStatus.OUTDATED]

    pinned = await validate_citations(f"A claim [{nid}@1].", live_cfg)
    assert [r.status for r in pinned] != [CitationStatus.OUTDATED]  # v1 pin on an unversioned node is current

    await execute_tool("update_node", {"node_id": nid, "description": "now edited"}, live_cfg)
    after = await validate_citations(f"A claim [{nid}@1].", live_cfg)
    assert [r.status for r in after] == [CitationStatus.OUTDATED]
    assert after[0].details == "cited v1, node is now v2"


# ---------------------------------------------------------------- whole-graph sanity


@needs_neo4j
@pytest.mark.asyncio
async def test_a_mixed_old_and_new_graph_is_consistent(live_cfg, tmp_path):
    """Old and new nodes side by side: no drift, and every layer agrees."""
    from wheeler.consistency import check_consistency
    from wheeler.tools.graph_tools import execute_tool

    old_id = await _old_finding(live_cfg, tmp_path, text="old one")
    new_id = json.loads(await execute_tool("add_finding", {"description": "new one", "confidence": 0.7}, live_cfg))["node_id"]
    await execute_tool("link_nodes", {"source_id": new_id, "target_id": old_id, "relationship": "WAS_DERIVED_FROM"}, live_cfg)

    report = await check_consistency(live_cfg)
    mine = {old_id, new_id}
    for bucket in ("graph_only", "json_only", "synthesis_missing", "json_missing"):
        flagged = set(getattr(report, bucket, []) or []) & mine
        assert not flagged, f"{bucket} flagged {flagged}"

    new_json = json.loads((tmp_path / "knowledge" / f"{new_id}.json").read_text())
    assert new_json["content_version"] == 1 and new_json["content_tokens"] > 0
    old_json = json.loads((tmp_path / "knowledge" / f"{old_id}.json").read_text())
    assert "content_version" not in old_json  # untouched, no silent migration


@needs_neo4j
@pytest.mark.asyncio
async def test_blank_if_changed_since_cannot_match_an_old_node_empty_hash(live_cfg, tmp_path, monkeypatch):
    """A whitespace token used to compare equal to an unversioned node's empty
    content_hash, so show_node answered "unchanged" and the caller never got the
    content it had never seen. Both sides must be non-empty to match."""
    import wheeler.mcp_core as core

    monkeypatch.setattr(core, "_config", live_cfg)
    nid = await _old_finding(live_cfg, tmp_path)
    fn = getattr(core.show_node, "fn", core.show_node)

    for blank in ("  ", "\t", "\n "):
        out = await fn(nid, if_changed_since=blank)
        assert out.get("changed") is not False, blank
        assert out["description"] == "legacy finding text", blank

    # a real version token still short-circuits truthfully
    assert (await fn(nid, if_changed_since="v1"))["changed"] is False
    # and a real hash token on a versioned node still works
    from wheeler.tools.graph_tools import execute_tool

    await execute_tool("update_node", {"node_id": nid, "description": "now versioned"}, live_cfg)
    cur = await fn(nid)
    assert (await fn(nid, if_changed_since=cur["content_hash"]))["changed"] is False
    assert (await fn(nid, if_changed_since="  "))["description"] == "now versioned"


@needs_neo4j
@pytest.mark.asyncio
async def test_legacy_node_with_no_json_file_still_reports_version_1(live_cfg, tmp_path, monkeypatch):
    """The real legacy shape: no content_version on the graph node AND no JSON file.

    show_node then serves from the graph, which carries raw properties rather
    than model defaults, so content_version came back absent. A caller could
    not tell "version 1" from a broken tool. This is what 98 percent of a real
    pre-versioning graph looks like, and the JSON-backed tests above cannot
    catch it because the model default fills the field in.
    """
    import wheeler.mcp_core as core

    monkeypatch.setattr(core, "_config", live_cfg)
    nid = await _old_finding(live_cfg, tmp_path)
    (tmp_path / "knowledge" / f"{nid}.json").unlink()  # graph-only, as in an old project

    fn = getattr(core.show_node, "fn", core.show_node)
    node = await fn(nid)
    assert node["source"] == "graph"
    assert node["content_version"] == 1
    assert node["description"] == "legacy finding text"

    batch = await fn(node_ids=[nid])
    assert batch["nodes"][0]["content_version"] == 1

    # and the freshness check still refuses to claim unchanged
    assert (await fn(nid, if_changed_since="  ")).get("changed") is not False
