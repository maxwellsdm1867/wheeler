"""Tests for ``wheeler restore --verify`` (issue #28).

The fixtures here build hand-rolled tar.gz backup archives that mimic the
format issue #27 produces. We don't depend on the real ``wheeler backup``
implementation: that lets these tests pass even when #27 lands later.

Each test uses an in-memory ``FakeBackend`` that mirrors the
project-tag-aware namespace isolation: every node is stamped with
``_wheeler_project`` (the scratch sentinel), and the cleanup Cypher is
intercepted so we can assert it ran without needing a real Neo4j.
"""

from __future__ import annotations

import json
import tarfile
from collections import defaultdict
from pathlib import Path

import pytest

from wheeler.config import WheelerConfig
from wheeler.restore import (
    RestoreVerifyError,
    _scratch_config,
    verify_backup,
)


# ---------------------------------------------------------------------------
# FakeBackend: in-memory mock that honors the project_tag contract.
# ---------------------------------------------------------------------------


class FakeBackend:
    """In-memory backend that mimics the project_tag-aware contract.

    - ``create_node`` stamps ``_wheeler_project`` from ``project_tag``
      (same behavior as ``Neo4jBackend.create_node`` lines 81-82).
    - ``run_cypher`` intercepts the three Cypher templates restore.py
      issues: count-by-label, count-by-rel, fetch-all-nodes, and the
      DETACH DELETE cleanup. Anything else is logged as unsupported.
    - ``cleanup_calls`` tracks every DETACH DELETE invocation so tests
      can assert cleanup ran (or didn't, with --keep-scratch).
    """

    def __init__(self, project_tag: str):
        self.project_tag = project_tag
        # Storage: {label: [props_dict, ...]}
        self.nodes_by_label: dict[str, list[dict]] = defaultdict(list)
        # All nodes by id for relationship resolution
        self.nodes_by_id: dict[str, dict] = {}
        self.node_label_by_id: dict[str, str] = {}
        # Relationships: list of (src_id, rel_type, tgt_id)
        self.relationships: list[tuple[str, str, str]] = []
        # Track cleanup-cypher calls so tests can assert
        self.cleanup_calls: list[str] = []
        self.initialized = False
        self.closed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def close(self) -> None:
        self.closed = True

    async def create_node(self, label: str, properties: dict) -> str:
        props = dict(properties)
        if self.project_tag:
            props["_wheeler_project"] = self.project_tag
        nid = props.get("id")
        if not nid:
            nid = f"{label[0]}-fake{len(self.nodes_by_id):04x}"
            props["id"] = nid
        self.nodes_by_label[label].append(props)
        self.nodes_by_id[nid] = props
        self.node_label_by_id[nid] = label
        return nid

    async def get_node(self, label, node_id):  # pragma: no cover - unused
        return self.nodes_by_id.get(node_id)

    async def update_node(self, label, node_id, properties):  # pragma: no cover
        self.nodes_by_id[node_id].update(properties)
        return True

    async def delete_node(self, label, node_id):  # pragma: no cover
        self.nodes_by_id.pop(node_id, None)
        return True

    async def create_relationship(
        self, src_label, src_id, rel_type, tgt_label, tgt_id
    ) -> bool:
        if src_id not in self.nodes_by_id or tgt_id not in self.nodes_by_id:
            return False
        self.relationships.append((src_id, rel_type, tgt_id))
        return True

    async def query_nodes(  # pragma: no cover - unused
        self, label, filters=None, order_by=None, limit=10
    ):
        return list(self.nodes_by_label.get(label, []))[:limit]

    async def count_all(self):  # pragma: no cover - unused
        return {label: len(items) for label, items in self.nodes_by_label.items()}

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        params = params or {}
        ptag = params.get("ptag", "")
        # 1) DETACH DELETE cleanup
        if "DETACH DELETE" in query:
            self.cleanup_calls.append(ptag)
            if ptag and ptag == self.project_tag:
                self.nodes_by_label.clear()
                self.nodes_by_id.clear()
                self.node_label_by_id.clear()
                self.relationships.clear()
            return []
        # 2) Count nodes by label (UNWIND labels(n))
        if "UNWIND labels(n)" in query and "count(*)" in query:
            out = []
            for label, items in self.nodes_by_label.items():
                matching = [
                    it for it in items if it.get("_wheeler_project") == ptag
                ]
                if matching:
                    out.append({"lbl": label, "cnt": len(matching)})
            return out
        # 3) Count rels by type
        if "MATCH (a)-[r]->(b)" in query and "count(*)" in query:
            counts: dict[str, int] = defaultdict(int)
            for src_id, rel_type, tgt_id in self.relationships:
                src = self.nodes_by_id.get(src_id, {})
                tgt = self.nodes_by_id.get(tgt_id, {})
                if (
                    src.get("_wheeler_project") == ptag
                    and tgt.get("_wheeler_project") == ptag
                ):
                    counts[rel_type] += 1
            return [{"rel": rt, "cnt": c} for rt, c in counts.items()]
        # 4) Fetch all nodes by tag
        if "RETURN n, labels(n)" in query:
            out = []
            for nid, props in self.nodes_by_id.items():
                if props.get("_wheeler_project") == ptag:
                    out.append(
                        {
                            "n": props,
                            "labels": [self.node_label_by_id.get(nid, "Unknown")],
                        }
                    )
            return out
        return []  # pragma: no cover - unrecognized query


# ---------------------------------------------------------------------------
# Archive fixture builders
# ---------------------------------------------------------------------------


def _build_archive(
    tmp_path: Path,
    *,
    nodes: list[dict],
    relationships: list[dict],
    manifest_overrides: dict | None = None,
) -> Path:
    """Build a tar.gz backup archive in ``tmp_path``. Returns the archive path.

    By default, manifest counts match the JSONL contents exactly. Pass
    ``manifest_overrides`` to inject a mismatch (e.g. inflate a count).
    """
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)

    # Compute true counts from the JSONL we'll write.
    true_node_counts: dict[str, int] = defaultdict(int)
    for n in nodes:
        true_node_counts[n["label"]] += 1
    true_rel_counts: dict[str, int] = defaultdict(int)
    for r in relationships:
        true_rel_counts[r["rel_type"]] += 1

    manifest = {
        "timestamp": "2026-05-10T00:00:00Z",
        "wheeler_version": "0.7.0",
        "node_counts_by_label": dict(true_node_counts),
        "relationship_count_by_type": dict(true_rel_counts),
        "canonical_file_hashes": {},
        "archive_layout": [
            "manifest.json",
            "graph_nodes.jsonl",
            "graph_relationships.jsonl",
        ],
    }
    if manifest_overrides:
        # Deep-merge for nested dict fields like node_counts_by_label.
        for key, val in manifest_overrides.items():
            if isinstance(val, dict) and isinstance(manifest.get(key), dict):
                manifest[key] = {**manifest[key], **val}
            else:
                manifest[key] = val

    (src / "manifest.json").write_text(json.dumps(manifest, indent=2))
    with (src / "graph_nodes.jsonl").open("w") as f:
        for n in nodes:
            f.write(json.dumps(n) + "\n")
    with (src / "graph_relationships.jsonl").open("w") as f:
        for r in relationships:
            f.write(json.dumps(r) + "\n")

    archive = tmp_path / "backup.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for child in src.iterdir():
            tar.add(child, arcname=child.name)
    return archive


def _two_findings_one_link():
    """Standard small fixture: 2 findings + 1 SUPPORTS rel."""
    nodes = [
        {
            "label": "Finding",
            "props": {"id": "F-aaa", "title": "First", "type": "Finding"},
        },
        {
            "label": "Finding",
            "props": {"id": "F-bbb", "title": "Second", "type": "Finding"},
        },
    ]
    relationships = [
        {
            "source_id": "F-aaa",
            "rel_type": "SUPPORTS",
            "target_id": "F-bbb",
            "rel_props": {},
        },
    ]
    return nodes, relationships


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_intact_backup_returns_pass(tmp_path):
    """Archive that matches its own manifest yields verdict=PASS."""
    nodes, rels = _two_findings_one_link()
    archive = _build_archive(tmp_path, nodes=nodes, relationships=rels)

    cfg = WheelerConfig()
    backend = FakeBackend(project_tag="PLACEHOLDER")  # tag set per-call below

    # We have to give the backend the same tag that verify_backup will
    # generate. Easiest: build a scratch_config ourselves and pass that
    # tag into the backend, then inject the backend.
    scratch_tag = "__restore_verify_test_pass__"
    backend.project_tag = scratch_tag

    # Patch _make_scratch_tag so the verify_backup tag matches our backend tag.
    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: scratch_tag
    try:
        result = await verify_backup(cfg, archive, backend=backend)
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "PASS", result
    assert result["first_failure"] is None
    # All declared checks present
    names = {c["name"] for c in result["checks"]}
    assert {
        "archive_extracts",
        "manifest_valid",
        "nodes_replay",
        "relationships_replay",
        "node_counts_match",
        "relationship_counts_match",
        "property_sample_match",
        "scratch_cleanup",
    } <= names


@pytest.mark.asyncio
async def test_verify_missing_node_returns_fail(tmp_path):
    """Manifest says 5 Findings but JSONL has only 4: FAIL with named gap."""
    nodes = [
        {"label": "Finding", "props": {"id": f"F-{i:03d}"}} for i in range(4)
    ]
    archive = _build_archive(
        tmp_path,
        nodes=nodes,
        relationships=[],
        manifest_overrides={"node_counts_by_label": {"Finding": 5}},
    )

    cfg = WheelerConfig()
    scratch_tag = "__restore_verify_test_missing__"
    backend = FakeBackend(project_tag=scratch_tag)

    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: scratch_tag
    try:
        result = await verify_backup(cfg, archive, backend=backend)
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "FAIL"
    assert result["first_failure"] is not None
    assert "Finding" in result["first_failure"]
    assert "expected 5" in result["first_failure"]
    assert "got 4" in result["first_failure"]


@pytest.mark.asyncio
async def test_verify_extra_relationship_returns_fail(tmp_path):
    """Manifest claims 3 SUPPORTS but JSONL has 1: FAIL on rel count."""
    nodes, rels = _two_findings_one_link()
    archive = _build_archive(
        tmp_path,
        nodes=nodes,
        relationships=rels,
        manifest_overrides={"relationship_count_by_type": {"SUPPORTS": 3}},
    )

    cfg = WheelerConfig()
    scratch_tag = "__restore_verify_test_extrarel__"
    backend = FakeBackend(project_tag=scratch_tag)

    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: scratch_tag
    try:
        result = await verify_backup(cfg, archive, backend=backend)
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "FAIL"
    # First failure should name the SUPPORTS mismatch.
    assert "SUPPORTS" in result["first_failure"]
    assert "expected 3" in result["first_failure"]


@pytest.mark.asyncio
async def test_verify_property_mismatch_returns_fail(tmp_path):
    """Backend that mutates a node title triggers property_sample_match FAIL.

    We override create_node so the replayed node carries a different title
    than the JSONL source. Counts match (same number of nodes) but the
    sample-property comparison catches the corruption.
    """
    nodes, rels = _two_findings_one_link()
    archive = _build_archive(tmp_path, nodes=nodes, relationships=rels)

    cfg = WheelerConfig()
    scratch_tag = "__restore_verify_test_propmismatch__"

    class CorruptingBackend(FakeBackend):
        async def create_node(self, label, properties):
            props = dict(properties)
            # Silently corrupt the title for one specific node.
            if props.get("id") == "F-bbb":
                props["title"] = "CORRUPTED"
            return await super().create_node(label, props)

    backend = CorruptingBackend(project_tag=scratch_tag)

    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: scratch_tag
    try:
        result = await verify_backup(cfg, archive, backend=backend)
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "FAIL"
    # The first failure must call out the property mismatch.
    assert "property" in result["first_failure"].lower()
    assert "F-bbb" in result["first_failure"]


@pytest.mark.asyncio
async def test_cleanup_runs_on_pass(tmp_path):
    """Cleanup DETACH DELETE runs even when verdict is PASS."""
    nodes, rels = _two_findings_one_link()
    archive = _build_archive(tmp_path, nodes=nodes, relationships=rels)

    cfg = WheelerConfig()
    scratch_tag = "__restore_verify_test_cleanup_pass__"
    backend = FakeBackend(project_tag=scratch_tag)

    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: scratch_tag
    try:
        result = await verify_backup(cfg, archive, backend=backend)
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "PASS"
    assert backend.cleanup_calls == [scratch_tag]
    # Backend storage should be empty post-cleanup (FakeBackend honors the tag).
    assert not backend.nodes_by_id


@pytest.mark.asyncio
async def test_cleanup_runs_on_fail(tmp_path):
    """Cleanup runs even when verification FAILs (finally-block guarantee)."""
    nodes = [{"label": "Finding", "props": {"id": "F-only"}}]
    archive = _build_archive(
        tmp_path,
        nodes=nodes,
        relationships=[],
        manifest_overrides={"node_counts_by_label": {"Finding": 99}},
    )

    cfg = WheelerConfig()
    scratch_tag = "__restore_verify_test_cleanup_fail__"
    backend = FakeBackend(project_tag=scratch_tag)

    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: scratch_tag
    try:
        result = await verify_backup(cfg, archive, backend=backend)
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "FAIL"
    assert backend.cleanup_calls == [scratch_tag]


@pytest.mark.asyncio
async def test_keep_scratch_skips_cleanup(tmp_path):
    """``keep_scratch=True`` leaves nodes in place and skips DETACH DELETE."""
    nodes, rels = _two_findings_one_link()
    archive = _build_archive(tmp_path, nodes=nodes, relationships=rels)

    cfg = WheelerConfig()
    scratch_tag = "__restore_verify_test_keep__"
    backend = FakeBackend(project_tag=scratch_tag)

    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: scratch_tag
    try:
        result = await verify_backup(
            cfg, archive, keep_scratch=True, backend=backend
        )
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "PASS"
    assert backend.cleanup_calls == []
    # Replayed nodes should still be present.
    assert "F-aaa" in backend.nodes_by_id
    assert "F-bbb" in backend.nodes_by_id


@pytest.mark.asyncio
async def test_refuses_empty_project_tag(tmp_path, monkeypatch):
    """Critical safety: if scratch tag is empty, refuse to write anywhere.

    We force ``_make_scratch_tag`` to return "" so the safety check at the
    top of the write phase trips. The backend must NOT receive any
    create_node calls (otherwise we'd be writing to the user's live
    namespace).
    """
    nodes, rels = _two_findings_one_link()
    archive = _build_archive(tmp_path, nodes=nodes, relationships=rels)

    cfg = WheelerConfig()
    backend = FakeBackend(project_tag="")  # would land in live namespace if used

    monkeypatch.setattr("wheeler.restore._make_scratch_tag", lambda: "")

    with pytest.raises(RestoreVerifyError):
        await verify_backup(cfg, archive, backend=backend)

    # No writes attempted.
    assert not backend.nodes_by_id
    assert not backend.relationships
    assert not backend.cleanup_calls


@pytest.mark.asyncio
async def test_missing_archive_returns_fail(tmp_path):
    """Nonexistent archive path: FAIL with a clear message, no exception."""
    cfg = WheelerConfig()
    bogus = tmp_path / "does-not-exist.tar.gz"
    result = await verify_backup(cfg, bogus, backend=FakeBackend("dummy"))
    assert result["verdict"] == "FAIL"
    assert "not found" in result["first_failure"]


@pytest.mark.asyncio
async def test_invalid_manifest_returns_fail(tmp_path):
    """Missing required manifest keys: FAIL on manifest_valid check."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "manifest.json").write_text(json.dumps({"timestamp": "now"}))
    (src / "graph_nodes.jsonl").write_text("")
    (src / "graph_relationships.jsonl").write_text("")
    archive = tmp_path / "broken.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for child in src.iterdir():
            tar.add(child, arcname=child.name)

    cfg = WheelerConfig()
    backend = FakeBackend(project_tag="__restore_verify_test_badmf__")
    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: "__restore_verify_test_badmf__"
    try:
        result = await verify_backup(cfg, archive, backend=backend)
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "FAIL"
    assert "manifest" in result["first_failure"].lower()
    # Backend should have done nothing because manifest validation gates writes.
    assert not backend.nodes_by_id


def test_scratch_config_does_not_mutate_caller():
    """``_scratch_config`` returns a deep copy: caller's tag stays empty."""
    cfg = WheelerConfig()
    assert cfg.neo4j.project_tag == ""
    scratch = _scratch_config(cfg, "__sentinel__")
    assert scratch.neo4j.project_tag == "__sentinel__"
    # Caller's config must remain pristine.
    assert cfg.neo4j.project_tag == ""
