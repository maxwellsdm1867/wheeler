"""Bulk provenance registration (issue #116 prototype, measured by #117).

Structural validation is tested without a graph. Everything that writes runs
against a LOCAL Neo4j (the Desktop instance answering to the documented test
password) under a per-test project tag, and is deleted by tag on teardown.
Fake backends drift from the real schema, so the write path is not faked.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import pytest

from wheeler.tools.graph_tools.batch import (
    NODE_TYPE_TO_TOOL,
    load_manifest,
    register_batch,
    validate_manifest,
)

_TEST_PASSWORD = "research-graph"


def _local_uri() -> str | None:
    import os

    if uri := os.environ.get("WHEELER_TEST_NEO4J_URI"):
        return uri
    from neo4j import GraphDatabase

    for port in (7717, 7687, 7697, 7707):
        uri = f"bolt://localhost:{port}"
        try:
            driver = GraphDatabase.driver(uri, auth=("neo4j", _TEST_PASSWORD))
            with driver.session(database="neo4j") as s:
                s.run("RETURN 1").consume()
            driver.close()
            return uri
        except Exception:
            continue
    return None


_URI = _local_uri()
needs_neo4j = pytest.mark.skipif(_URI is None, reason="no local Neo4j answering the test password")


# ---------------------------------------------------------------------------
# Structural validation (no graph)
# ---------------------------------------------------------------------------


def _manifest(tmp_path: Path) -> dict:
    fig = tmp_path / "fig1.png"
    fig.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    return {
        "nodes": [
            {"alias": "@exec", "type": "execution", "kind": "script_run", "description": "ran it"},
            {"alias": "@f1", "type": "finding", "description": "peak at 40 ms", "confidence": 0.7},
        ],
        "artifacts": [{"alias": "@fig1", "path": "fig1.png", "title": "Figure 1"}],
        "edges": [
            {"source": "@fig1", "relationship": "WAS_GENERATED_BY", "target": "@exec"},
            ["@f1", "WAS_GENERATED_BY", "@exec"],
            ["@f1", "APPEARS_IN", "@fig1"],
        ],
    }


class TestValidateManifest:
    def test_clean_manifest_has_no_errors_and_resolves_paths(self, tmp_path):
        errors, norm = validate_manifest(_manifest(tmp_path), base_dir=tmp_path)
        assert errors == []
        assert norm["artifacts"][0]["fields"]["path"] == str((tmp_path / "fig1.png").resolve())
        assert [e["relationship"] for e in norm["edges"]] == ["WAS_GENERATED_BY", "WAS_GENERATED_BY", "APPEARS_IN"]

    def test_undefined_alias_is_reported_with_location(self, tmp_path):
        m = _manifest(tmp_path)
        m["edges"].append(["@nope", "USED", "@exec"])
        errors, _ = validate_manifest(m, base_dir=tmp_path)
        assert any("edges[3]" in e and "@nope" in e for e in errors)

    def test_duplicate_alias_missing_file_bad_rel_bad_type_all_reported(self, tmp_path):
        m = _manifest(tmp_path)
        m["artifacts"].append({"alias": "@fig1", "path": "missing.png"})
        m["edges"].append(["@f1", "CAUSED", "@exec"])
        m["nodes"].append({"alias": "@d", "type": "dataset", "path": "x.csv"})
        errors, _ = validate_manifest(m, base_dir=tmp_path)
        joined = "\n".join(errors)
        assert "already defined" in joined
        assert "file not found: missing.png" in joined
        assert "'CAUSED' not allowed" in joined
        assert "type 'dataset' not one of" in joined

    def test_relationship_aliases_are_mapped(self, tmp_path):
        m = _manifest(tmp_path)
        m["edges"] = [["@exec", "USES", "@fig1"]]
        errors, norm = validate_manifest(m, base_dir=tmp_path)
        assert errors == []
        assert norm["edges"][0]["relationship"] == "USED"

    def test_literal_ids_are_accepted_and_garbage_endpoints_are_not(self, tmp_path):
        m = _manifest(tmp_path)
        m["edges"] = [["@exec", "USED", "D-1a2b3c4d"], ["@exec", "USED", "not-an-id"]]
        errors, _ = validate_manifest(m, base_dir=tmp_path)
        assert len(errors) == 1 and "not-an-id" in errors[0]

    def test_empty_manifest_is_an_error(self):
        errors, _ = validate_manifest({})
        assert errors == ["manifest is empty: no nodes, artifacts or edges"]

    def test_every_node_type_maps_to_a_registered_tool(self):
        import wheeler.tools.graph_tools as gt

        for tool in NODE_TYPE_TO_TOOL.values():
            assert tool in gt._TOOL_REGISTRY

    def test_load_manifest_reads_json_and_yaml(self, tmp_path):
        (tmp_path / "m.json").write_text(json.dumps({"edges": []}))
        (tmp_path / "m.yaml").write_text("edges:\n  - [A-1, USED, B-2]\n")
        assert load_manifest(tmp_path / "m.json") == {"edges": []}
        assert load_manifest(tmp_path / "m.yaml") == {"edges": [["A-1", "USED", "B-2"]]}


# ---------------------------------------------------------------------------
# MCP surface: register_batch ships, the split prototypes do not
# ---------------------------------------------------------------------------


class TestSurface:
    def test_register_batch_is_a_first_class_logged_mutation_tool(self):
        from wheeler.mcp_mutations import mcp

        tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
        assert "register_batch" in tools
        assert tools["register_batch"].description
        fn = getattr(tools["register_batch"], "fn", None)
        assert fn is None or getattr(fn, "_wheeler_logged", False)
        # The split prototypes measured in evals/batch_registration lost; they are not shipped.
        assert "ensure_artifacts" not in tools and "link_nodes_batch" not in tools


# ---------------------------------------------------------------------------
# Live write path
# ---------------------------------------------------------------------------


@pytest.fixture
def live_cfg(tmp_path):
    """A config bound to the local instance, a fresh tag and a temp project."""
    from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    tag = f"batchtest-{uuid.uuid4().hex[:8]}"
    cfg = WheelerConfig(
        neo4j=Neo4jConfig(uri=_URI, username="neo4j", password=_TEST_PASSWORD, database="neo4j", project_tag=tag),
        project=ProjectMeta(name="batch-registration-test"),
        project_root=str(tmp_path),
    )
    gt.reset_backend_cache()
    invalidate_async_driver()
    yield cfg
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(_URI, auth=("neo4j", _TEST_PASSWORD))
    with driver.session(database="neo4j") as s:
        s.run("MATCH (n {_wheeler_project: $tag}) DETACH DELETE n", tag=tag).consume()
    driver.close()
    gt.reset_backend_cache()
    invalidate_async_driver()


def _edges_by_tag(tag: str) -> set[tuple[str, str, str]]:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(_URI, auth=("neo4j", _TEST_PASSWORD))
    with driver.session(database="neo4j") as s:
        rows = s.run(
            "MATCH (a {_wheeler_project: $tag})-[r]->(b {_wheeler_project: $tag}) "
            "RETURN a.id AS a, type(r) AS t, b.id AS b",
            tag=tag,
        ).data()
    driver.close()
    return {(r["a"], r["t"], r["b"]) for r in rows}


@needs_neo4j
@pytest.mark.asyncio
async def test_register_batch_writes_all_three_layers_and_every_edge(live_cfg, tmp_path):
    result = await register_batch(_manifest(tmp_path), live_cfg, base_dir=tmp_path)
    assert result["status"] == "ok", result
    ids = result["ids"]
    assert set(ids) == {"@exec", "@f1", "@fig1"}
    assert ids["@exec"].startswith("X-") and ids["@f1"].startswith("F-") and ids["@fig1"].startswith("F-")

    edges = _edges_by_tag(live_cfg.neo4j.project_tag)
    assert (ids["@fig1"], "WAS_GENERATED_BY", ids["@exec"]) in edges
    assert (ids["@f1"], "WAS_GENERATED_BY", ids["@exec"]) in edges
    assert (ids["@f1"], "APPEARS_IN", ids["@fig1"]) in edges

    for nid in ids.values():
        assert (tmp_path / "knowledge" / f"{nid}.json").exists(), nid
        assert (tmp_path / "synthesis" / f"{nid}.md").exists(), nid


@needs_neo4j
@pytest.mark.asyncio
async def test_one_bad_edge_does_not_abort_the_rest(live_cfg, tmp_path):
    m = _manifest(tmp_path)
    m["edges"].append(["@exec", "USED", "D-00000000"])  # valid shape, node absent
    result = await register_batch(m, live_cfg, base_dir=tmp_path)
    assert result["status"] == "partial"
    assert result["failures"] == 1
    statuses = [e["status"] for e in result["edges"]]
    assert statuses == ["linked", "linked", "linked", "error"]
    assert len(_edges_by_tag(live_cfg.neo4j.project_tag)) == 3


@needs_neo4j
@pytest.mark.asyncio
async def test_dry_run_writes_nothing_and_names_unresolved_ids(live_cfg, tmp_path):
    m = _manifest(tmp_path)
    m["edges"].append(["@exec", "USED", "D-00000000"])
    report = await register_batch(m, live_cfg, dry_run=True, base_dir=tmp_path)
    assert report["dry_run"] is True
    assert report["errors"] == []
    assert report["unresolved_ids"] == ["D-00000000"]
    assert report["ok"] is False
    assert _edges_by_tag(live_cfg.neo4j.project_tag) == set()
    assert not (tmp_path / "knowledge").exists()


@needs_neo4j
@pytest.mark.asyncio
async def test_structural_errors_block_the_whole_write(live_cfg, tmp_path):
    m = _manifest(tmp_path)
    m["edges"].append(["@ghost", "USED", "@exec"])
    result = await register_batch(m, live_cfg, base_dir=tmp_path)
    assert result["status"] == "failed" and result["error"] == "validation_failed"
    assert _edges_by_tag(live_cfg.neo4j.project_tag) == set()


@needs_neo4j
@pytest.mark.asyncio
async def test_ensure_artifacts_is_idempotent_on_unchanged_files(live_cfg, tmp_path):
    m = {"artifacts": _manifest(tmp_path)["artifacts"]}
    first = await register_batch(m, live_cfg, base_dir=tmp_path)
    second = await register_batch(m, live_cfg, base_dir=tmp_path)
    assert first["artifacts"][0]["status"] == "created"
    assert second["artifacts"][0]["status"] == "unchanged"
    assert first["ids"]["@fig1"] == second["ids"]["@fig1"]


@needs_neo4j
def test_cli_register_dry_run_then_write(live_cfg, tmp_path, monkeypatch):
    """The `wheeler integrate register` verb end to end, in-process."""
    import yaml
    from typer.testing import CliRunner

    from wheeler.tools.cli import app

    m = _manifest(tmp_path)
    (tmp_path / "provenance.yaml").write_text(yaml.safe_dump(m))
    (tmp_path / "wheeler.yaml").write_text(yaml.safe_dump({
        "neo4j": {"uri": _URI, "username": "neo4j", "password": _TEST_PASSWORD,
                  "database": "neo4j", "project_tag": live_cfg.neo4j.project_tag},
        "project_root": str(tmp_path),
    }))
    monkeypatch.chdir(tmp_path)
    for var in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"):
        monkeypatch.delenv(var, raising=False)
    runner = CliRunner()

    dry = runner.invoke(app, ["integrate", "register", "provenance.yaml", "--dry-run"])
    assert dry.exit_code == 0, dry.output
    assert "OK: manifest is valid" in dry.output
    assert _edges_by_tag(live_cfg.neo4j.project_tag) == set()

    real = runner.invoke(app, ["integrate", "register", "provenance.yaml"])
    assert real.exit_code == 0, real.output
    assert real.output.startswith("ok: 2 nodes, 1 artifacts, 3 edges, 0 failures")
    assert "@exec ->" in real.output
    assert len(_edges_by_tag(live_cfg.neo4j.project_tag)) == 3


def test_compact_keeps_ids_counts_and_only_failed_rows():
    from wheeler.mcp_mutations import _compact

    full = {
        "status": "partial", "counts": {"nodes": 1, "artifacts": 1, "edges": 2}, "failures": 1,
        "ids": {"@a": "F-1", "@b": "F-2"},
        "nodes": [{"index": 0, "alias": "@a", "status": "created", "node_id": "F-1"}],
        "artifacts": [{"index": 0, "alias": "@b", "status": "unchanged", "node_id": "F-2"}],
        "edges": [
            {"index": 0, "status": "linked"},
            {"index": 1, "status": "error", "error": "One or both nodes not found"},
        ],
    }
    out = _compact(full)
    assert set(out) == {"status", "counts", "failures", "ids", "node_ids", "problems"}
    assert out["node_ids"] == {"nodes": ["F-1"], "artifacts": ["F-2"]}
    assert out["problems"] == [{"section": "edges", "index": 1, "status": "error", "error": "One or both nodes not found"}]
    assert "problems" not in _compact({**full, "edges": full["edges"][:1], "failures": 0})


@needs_neo4j
@pytest.mark.asyncio
async def test_mcp_register_batch_compact_returns_artifact_ids_in_input_order_without_aliases(live_cfg, tmp_path, monkeypatch):
    """Criterion 2 of #116 in the shipped default output, not only with verbose=True."""
    import wheeler.mcp_mutations as mm

    monkeypatch.setattr(mm, "_config", live_cfg)
    files = []
    for name in ("a.py", "b.csv", "c.png"):
        f = tmp_path / name
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + name.encode() if name.endswith(".png") else name.encode())
        files.append({"path": str(f)})
    fn = getattr(mm.register_batch, "fn", mm.register_batch)
    out = await fn(artifacts=files)
    assert out["status"] == "ok"
    assert out["ids"] == {}
    ids = out["node_ids"]["artifacts"]
    assert len(ids) == 3 and ids[0].startswith("S-") and ids[1].startswith("D-") and ids[2].startswith("F-")
    again = await fn(artifacts=files)
    assert again["node_ids"]["artifacts"] == ids
    assert "problems" not in again
