"""Append-only content versions, pinned citations, and the pointer disclosure level.

A node's id is stable; its content has a version. Version 1 is the creation,
every field or tier change bumps it, and the state before each bump is kept
at knowledge/versions/<id>/v<n>.json. Edges record the version of each
endpoint they were made against; a citation may pin a version ([F-3a2b@2]);
show_node can read a version, answer "has this changed since", and list one
hop of neighbours as pointers. Live tests run against the local Neo4j under a
per-test tag.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.knowledge import versions as V
from wheeler.models import FindingModel
from wheeler.validation.citations import extract_citation_pins, extract_citations

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


# ------------------------------------------------------------- unit: versions


class TestVersionStore:
    def _model(self, **kw) -> FindingModel:
        base = dict(id="F-deadbeef", type="Finding", description="peak at 40 ms", confidence=0.7)
        base.update(kw)
        return FindingModel(**base)

    def test_content_hash_ignores_volatile_fields_and_tracks_content(self):
        a = self._model()
        b = self._model(updated="2026-01-01", stale=True, session_id="s", display_name="x")
        c = self._model(description="peak at 41 ms")
        assert V.content_hash_of(a) == V.content_hash_of(b)
        assert V.content_hash_of(a) != V.content_hash_of(c)
        assert len(V.content_hash_of(a)) == 16

    def test_snapshot_is_idempotent_and_bump_advances(self, tmp_path):
        m = self._model()
        m.content_version = 1
        first = V.snapshot(tmp_path, m)
        assert first == tmp_path / "versions" / "F-deadbeef" / "v1.json"
        assert V.snapshot(tmp_path, m) is None  # already kept, never overwritten
        V.bump(m)
        assert m.content_version == 2 and m.content_hash == V.content_hash_of(m)
        assert V.list_versions(tmp_path, "F-deadbeef", current=2) == [1, 2]

    def test_read_version_serves_snapshot_or_current(self, tmp_path):
        from wheeler.knowledge.store import write_node

        m = self._model()
        m.content_version = 1
        V.snapshot(tmp_path, m)
        m.description = "peak at 41 ms"
        V.bump(m)
        write_node(tmp_path, m)
        assert V.read_version(tmp_path, "F-deadbeef", 1)["description"] == "peak at 40 ms"
        assert V.read_version(tmp_path, "F-deadbeef", 2)["description"] == "peak at 41 ms"
        with pytest.raises(FileNotFoundError):
            V.read_version(tmp_path, "F-deadbeef", 3)


class TestCitationPins:
    def test_bare_and_pinned_citations(self):
        text = "See [F-3a2b] and [F-3a2b@2], also [H-1c4f@7] and [Q-9999]."
        assert extract_citations(text) == ["F-3a2b", "H-1c4f", "Q-9999"]
        assert extract_citation_pins(text) == {"F-3a2b": 2, "H-1c4f": 7}

    def test_two_pins_keep_the_lower(self):
        assert extract_citation_pins("[F-3a2b@4] then [F-3a2b@2]") == {"F-3a2b": 2}


class TestDisclosureDefault:
    def test_default_level_is_pointer_and_env_overrides(self, monkeypatch):
        import importlib

        from wheeler import mcp_shared

        assert mcp_shared.DISCLOSURE_LEVELS == ("full", "trimmed", "pointer")
        monkeypatch.delenv("WHEELER_DISCLOSURE", raising=False)
        assert importlib.reload(mcp_shared).DISCLOSURE == "pointer"
        monkeypatch.setenv("WHEELER_DISCLOSURE", "trimmed")
        assert importlib.reload(mcp_shared).DISCLOSURE == "trimmed"
        monkeypatch.setenv("WHEELER_DISCLOSURE", "nonsense")
        assert importlib.reload(mcp_shared).DISCLOSURE == "pointer"
        monkeypatch.delenv("WHEELER_DISCLOSURE", raising=False)
        importlib.reload(mcp_shared)


class TestPointerHelpers:
    def test_headline_prefers_title_then_cuts_text_at_a_word(self):
        from wheeler.mcp_shared import _headline

        assert _headline({"title": "Lag-1 counts", "description": "x" * 500}) == "Lag-1 counts"
        h = _headline({"description": ("word " * 60).strip()})
        assert h.endswith("...") and len(h) <= 104 and not h.endswith("wor...")
        assert _headline({}) == ""

    @pytest.mark.asyncio
    async def test_pointerize_replaces_rows_and_keeps_scalars(self):
        from wheeler import mcp_shared

        result = {"findings": [{"id": "F-1", "description": "d" * 400, "confidence": 0.7}], "count": 1}
        meta = {"F-1": {"id": "F-1", "type": "Finding", "degree": 3, "updated": "2026-09-14", "content_version": 2, "title": ""}}
        with patch.object(mcp_shared, "_node_meta", new=AsyncMock(return_value=meta)):
            out = await mcp_shared._pointerize(result, None)
        row = out["findings"][0]
        assert out["count"] == 1
        assert row["id"] == "F-1" and row["type"] == "Finding" and row["degree"] == 3
        assert row["content_version"] == 2 and row["confidence"] == 0.7
        assert "description" not in row and len(row["headline"]) <= 104


# --------------------------------------------------------------------- live


@pytest.fixture
def live_cfg(tmp_path):
    from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    tag = f"vertest-{uuid.uuid4().hex[:8]}"
    cfg = WheelerConfig(
        neo4j=Neo4jConfig(uri=_URI, username="neo4j", password=_TEST_PASSWORD, database="neo4j", project_tag=tag),
        project=ProjectMeta(name="versions-test"),
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


def _graph(uri, query, **params):
    from neo4j import GraphDatabase

    d = GraphDatabase.driver(uri, auth=("neo4j", _TEST_PASSWORD))
    with d.session(database="neo4j") as s:
        rows = s.run(query, **params).data()
    d.close()
    return rows


@needs_neo4j
@pytest.mark.asyncio
async def test_versions_bump_in_json_and_graph_and_snapshots_are_readable(live_cfg, tmp_path):
    from wheeler.tools.graph_tools import execute_tool

    r = json.loads(await execute_tool("add_finding", {"description": "peak at 40 ms", "confidence": 0.6}, live_cfg))
    fid = r["node_id"]
    j = json.loads((tmp_path / "knowledge" / f"{fid}.json").read_text())
    assert j["content_version"] == 1 and len(j["content_hash"]) == 16
    g = _graph(_URI, "MATCH (n {id: $id}) RETURN n.content_version AS v, n.content_hash AS h", id=fid)[0]
    assert g["v"] == 1 and g["h"] == j["content_hash"]

    await execute_tool("update_node", {"node_id": fid, "description": "peak at 41 ms"}, live_cfg)
    await execute_tool("set_tier", {"node_id": fid, "tier": "reference"}, live_cfg)
    j2 = json.loads((tmp_path / "knowledge" / f"{fid}.json").read_text())
    assert j2["content_version"] == 3 and j2["content_hash"] != j["content_hash"]
    g2 = _graph(_URI, "MATCH (n {id: $id}) RETURN n.content_version AS v, n.content_hash AS h", id=fid)[0]
    assert g2["v"] == 3 and g2["h"] == j2["content_hash"]

    kdir = tmp_path / "knowledge"
    assert V.list_versions(kdir, fid, current=3) == [1, 2, 3]
    assert V.read_version(kdir, fid, 1)["description"] == "peak at 40 ms"
    assert V.read_version(kdir, fid, 2)["description"] == "peak at 41 ms" and V.read_version(kdir, fid, 2)["tier"] == "generated"
    assert V.read_version(kdir, fid, 3)["tier"] == "reference"

    # metadata is not content: neither a no-op nor a stale/stability update bumps or snapshots
    before = j2["content_version"]
    await execute_tool("update_node", {"node_id": fid, "description": "peak at 41 ms"}, live_cfg)  # no-op change
    r = json.loads(await execute_tool("update_node", {"node_id": fid, "stale": True, "stability": 0.2}, live_cfg))
    assert r["status"] == "updated" and set(r["updated_fields"]) == {"stale", "stability"}
    j3 = json.loads((tmp_path / "knowledge" / f"{fid}.json").read_text())
    assert j3["content_version"] == before and j3["stale"] is True and j3["content_hash"] == j2["content_hash"]
    assert _graph(_URI, "MATCH (n {id: $id}) RETURN n.content_version AS v", id=fid)[0]["v"] == before
    assert V.list_versions(kdir, fid, current=before) == [1, 2, 3]  # no v3 snapshot written


@needs_neo4j
@pytest.mark.asyncio
async def test_edges_pin_endpoint_versions_and_neighbors_report_moved(live_cfg, tmp_path, monkeypatch):
    import wheeler.mcp_core as core
    from wheeler.tools.graph_tools import execute_tool

    monkeypatch.setattr(core, "_config", live_cfg)
    f = json.loads(await execute_tool("add_finding", {"description": "finding one", "confidence": 0.6}, live_cfg))["node_id"]
    h = json.loads(await execute_tool("add_hypothesis", {"statement": "hypothesis one"}, live_cfg))["node_id"]
    await execute_tool("link_nodes", {"source_id": f, "target_id": h, "relationship": "SUPPORTS"}, live_cfg)
    edge = _graph(_URI, "MATCH ({id: $f})-[r:SUPPORTS]->({id: $h}) RETURN r.source_version AS sv, r.target_version AS tv, r.created_at AS at", f=f, h=h)[0]
    assert edge["sv"] == 1 and edge["tv"] == 1 and edge["at"]

    fn = getattr(core.show_node, "fn", core.show_node)
    hop = (await fn(f, neighbors=True))["neighbors"]
    assert hop == [{"id": h, "rel": "SUPPORTS", "direction": "out", "type": "Hypothesis", "headline": "hypothesis one", "content_version": 1}]

    # the hypothesis moves on; the edge was made against v1
    await execute_tool("update_node", {"node_id": h, "statement": "hypothesis one, revised"}, live_cfg)
    hop2 = (await fn(f, neighbors=True))["neighbors"]
    assert hop2[0]["content_version"] == 2 and hop2[0]["moved"] is True
    back = (await fn(h, neighbors=True))["neighbors"]
    assert back[0]["direction"] == "in" and "moved" not in back[0]


@needs_neo4j
@pytest.mark.asyncio
async def test_show_node_version_read_and_if_changed_since(live_cfg, tmp_path, monkeypatch):
    import wheeler.mcp_core as core
    from wheeler.tools.graph_tools import execute_tool

    monkeypatch.setattr(core, "_config", live_cfg)
    fid = json.loads(await execute_tool("add_finding", {"description": "v one text", "confidence": 0.5}, live_cfg))["node_id"]
    fn = getattr(core.show_node, "fn", core.show_node)
    first = await fn(fid)
    assert first["content_version"] == 1
    unchanged = await fn(fid, if_changed_since=first["content_hash"])
    assert unchanged == {"id": fid, "content_version": 1, "content_hash": first["content_hash"], "changed": False}
    assert (await fn(fid, if_changed_since="v1"))["changed"] is False

    await execute_tool("update_node", {"node_id": fid, "description": "v two text"}, live_cfg)
    changed = await fn(fid, if_changed_since=first["content_hash"])
    assert changed["changed"] is True and changed["description"] == "v two text" and changed["content_version"] == 2
    old = await fn(fid, version=1)
    assert old["description"] == "v one text" and old["is_current"] is False
    cur = await fn(fid, version=2)
    assert cur["is_current"] is True
    assert "error" in await fn(fid, version=9)


@needs_neo4j
@pytest.mark.asyncio
async def test_pinned_citation_is_outdated_after_a_bump(live_cfg):
    from wheeler.tools.graph_tools import execute_tool
    from wheeler.validation.citations import CitationStatus, validate_citations

    fid = json.loads(await execute_tool("add_finding", {"description": "cited finding", "confidence": 0.5}, live_cfg))["node_id"]
    await execute_tool("update_node", {"node_id": fid, "description": "cited finding, revised"}, live_cfg)
    res = {r.node_id + ("@" + r.details.split("cited ")[-1][:2] if r.status == CitationStatus.OUTDATED else ""): r
           for r in await validate_citations(f"Claim [{fid}@1]. Same claim [{fid}].", live_cfg)}
    statuses = sorted(r.status.value for r in res.values())
    assert statuses == ["outdated"], statuses  # one citation id, pinned to v1, node is v2
    only = next(iter(res.values()))
    assert only.details == "cited v1, node is now v2"


@needs_neo4j
@pytest.mark.asyncio
async def test_pointer_level_listing_returns_pointer_rows(live_cfg, monkeypatch):
    import wheeler.mcp_query as q
    from wheeler import mcp_shared
    from wheeler.tools.graph_tools import execute_tool

    monkeypatch.setattr(q, "_config", live_cfg)
    monkeypatch.setattr(mcp_shared, "DISCLOSURE", "pointer")
    fid = json.loads(await execute_tool("add_finding", {"description": "x " * 300, "confidence": 0.9, "title": "Pointer title"}, live_cfg))["node_id"]
    hid = json.loads(await execute_tool("add_hypothesis", {"statement": "h"}, live_cfg))["node_id"]
    await execute_tool("link_nodes", {"source_id": fid, "target_id": hid, "relationship": "SUPPORTS"}, live_cfg)
    fn = getattr(q.query_findings, "fn", q.query_findings)
    out = await fn()
    row = next(r for r in out["findings"] if r["id"] == fid)
    assert row["type"] == "Finding" and row["headline"] == "Pointer title" and row["degree"] == 1
    assert row["content_version"] == 1 and row["confidence"] == 0.9 and "description" not in row
    # a never-edited node still has a recency stamp (the creation date), as a 10-char date
    assert len(row["updated"]) == 10 and row["updated"][:4] == "2026" or row["updated"][:2] == "20"
    full = await fn(full=True)
    assert len(next(r for r in full["findings"] if r["id"] == fid)["description"]) == 600
