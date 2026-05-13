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


# ===========================================================================
# Wave 2b: restore_fresh and restore_merge tests
# ===========================================================================

from unittest.mock import AsyncMock, patch  # noqa: E402

from wheeler.restore import (  # noqa: E402
    restore_fresh,
    restore_merge,
)
from wheeler.portability import compute_manifest_signature  # noqa: E402


# ---------------------------------------------------------------------------
# Extended FakeBackend for restore tests (handles existence checks)
# ---------------------------------------------------------------------------


class FakeRestoreBackend(FakeBackend):
    """FakeBackend extended with full CRUD and project-check Cypher support.

    Adds:
    - get_node: returns stored node or None
    - update_node: updates stored node in-place
    - create_relationship: accepts optional rel_props kwarg
    - run_cypher: handles project-count check and parent_dataset queries
    """

    def __init__(self, project_tag: str = "test-project"):
        super().__init__(project_tag)
        # Pre-populated node count for the project-check query (simulate
        # "already has nodes" scenario)
        self._pre_existing_count: int = 0

    async def get_node(self, label: str, node_id: str):
        node = self.nodes_by_id.get(node_id)
        if node is None:
            return None
        # Only return if the label matches.
        if self.node_label_by_id.get(node_id) != label:
            return None
        return dict(node)

    async def update_node(self, label: str, node_id: str, properties: dict) -> bool:
        if node_id not in self.nodes_by_id:
            return False
        self.nodes_by_id[node_id].update(properties)
        label_nodes = self.nodes_by_label.get(label, [])
        for n in label_nodes:
            if n.get("id") == node_id:
                n.update(properties)
                break
        return True

    async def create_relationship(
        self,
        src_label: str,
        src_id: str,
        rel_type: str,
        tgt_label: str,
        tgt_id: str,
        rel_props: dict | None = None,
    ) -> bool:
        if src_id not in self.nodes_by_id or tgt_id not in self.nodes_by_id:
            return False
        self.relationships.append((src_id, rel_type, tgt_id))
        return True

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        params = params or {}
        # Project-node pre-check (used by restore_fresh before writing)
        if "count(n) AS cnt" in query and "_wheeler_project" in query:
            tag = params.get("tag", "")
            if self._pre_existing_count > 0 and tag:
                return [{"cnt": self._pre_existing_count}]
            return [{"cnt": 0}]
        # Dataset parent link lookups (mutations.py auto-links parent_dataset)
        if "WHERE n.path = $path" in query:
            return []
        # Script/Dataset path lookups used by ensure_artifact (not called in restore)
        if "MATCH (n) WHERE" in query:
            return []
        # Delegating remaining patterns to FakeBackend parent
        return await super().run_cypher(query, params)


# ---------------------------------------------------------------------------
# v2 archive builder
# ---------------------------------------------------------------------------


def _build_v2_archive(
    tmp_path: Path,
    *,
    nodes: list[dict],
    relationships: list[dict],
    manifest_overrides: dict | None = None,
    include_project_subtree: bool = True,
    project_files: dict[str, bytes] | None = None,
    include_embeddings: bool = False,
) -> Path:
    """Build a v2-format tar.gz archive.

    ``nodes`` is a list of JSONL row dicts:
        {"label": ..., "labels": [...], "props": {...}}

    ``relationships`` is a list of JSONL row dicts:
        {"source_id": ..., "rel_type": ..., "target_id": ..., "rel_props": {...}}

    ``project_files`` maps in-project relative paths to byte content
    (e.g. ``{"wheeler.yaml": b"neo4j: {}"}``).

    A signed manifest_signature is computed last if not overridden.
    """
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)

    # Default counts from nodes/rels.
    true_node_counts: dict[str, int] = defaultdict(int)
    for n in nodes:
        lbl = n.get("label") or (n.get("labels") or ["Unknown"])[0]
        true_node_counts[lbl] += 1
    true_rel_counts: dict[str, int] = defaultdict(int)
    for r in relationships:
        true_rel_counts[r.get("rel_type", "UNKNOWN")] += 1

    import wheeler as _wh

    manifest: dict = {
        "manifest_version": 2,
        "archive_uuid": "test-uuid-1234",
        "wheeler_version": _wh.__version__,
        "schema_version": _wh.KNOWLEDGE_SCHEMA_VERSION,
        "timestamp": "2026-05-10T00:00:00Z",
        "node_counts_by_label": dict(true_node_counts),
        "relationship_count_by_type": dict(true_rel_counts),
        "canonical_file_hashes": {},
        "archive_layout": ["manifest.json", "graph_nodes.jsonl",
                           "graph_relationships.jsonl"],
        "embedder": {
            "model": "BAAI/bge-small-en-v1.5",
            "dim": 384,
            "fastembed_version": "0.3.0",
        },
        "source": {
            "hostname": "source-machine",
            "platform": "linux",
            "python_version": "3.11.0",
            "packed_by": "testuser",
        },
        "external_references": [],
        "excluded_paths": [],
    }

    if manifest_overrides:
        for key, val in manifest_overrides.items():
            if isinstance(val, dict) and isinstance(manifest.get(key), dict):
                manifest[key] = {**manifest[key], **val}
            else:
                manifest[key] = val

    # Sign the manifest (unless the test explicitly sets a bad signature).
    if "manifest_signature" not in manifest:
        manifest["manifest_signature"] = compute_manifest_signature(manifest)

    (src / "manifest.json").write_text(json.dumps(manifest, indent=2))

    with (src / "graph_nodes.jsonl").open("w") as f:
        for n in nodes:
            f.write(json.dumps(n) + "\n")
    with (src / "graph_relationships.jsonl").open("w") as f:
        for r in relationships:
            f.write(json.dumps(r) + "\n")

    if include_project_subtree:
        proj_dir = src / "project"
        proj_dir.mkdir(exist_ok=True)
        # Default wheeler.yaml
        (proj_dir / "wheeler.yaml").write_text(
            "neo4j:\n  uri: bolt://localhost:7687\n  password: research-graph\n"
        )
        (proj_dir / "knowledge").mkdir(exist_ok=True)
        (proj_dir / "synthesis").mkdir(exist_ok=True)
        # Extra project files requested by the test.
        if project_files:
            for rel_path, content in project_files.items():
                dest = proj_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)

    if include_embeddings:
        emb_dir = src / "project" / ".wheeler" / "embeddings"
        emb_dir.mkdir(parents=True, exist_ok=True)
        (emb_dir / "index.bin").write_bytes(b"\x00\x01" * 16)

    archive = tmp_path / "backup_v2.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for child in sorted(src.rglob("*")):
            if child.is_file():
                arcname = child.relative_to(src).as_posix()
                tar.add(child, arcname=arcname)
    return archive


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding_node(node_id: str, path: str = "", title: str = "Test finding") -> dict:
    return {
        "label": "Finding",
        "labels": ["Finding"],
        "props": {
            "id": node_id,
            "description": title,
            "confidence": 0.8,
            "path": path,
            "tier": "generated",
            "stability": 0.3,
            "session_id": "",
        },
    }


def _make_script_node(
    node_id: str, path: str = "${PROJECT}/scripts/run.py"
) -> dict:
    return {
        "label": "Script",
        "labels": ["Script"],
        "props": {
            "id": node_id,
            "path": path,
            "language": "python",
            "hash": "sha256:abc",
            "tier": "generated",
            "stability": 0.5,
            "session_id": "",
        },
    }


def _supports_rel(src_id: str, tgt_id: str) -> dict:
    return {
        "source_id": src_id,
        "rel_type": "SUPPORTS",
        "target_id": tgt_id,
        "rel_props": {},
    }


# ---------------------------------------------------------------------------
# Tests: restore_fresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_fresh_populates_graph(tmp_path):
    """restore_fresh into an empty dir: nodes and relationships reach the graph."""
    target = tmp_path / "target"
    target.mkdir()

    nodes = [
        _make_finding_node("F-aa000001", path="${PROJECT}/results/fig1.png"),
        _make_finding_node("F-aa000002"),
    ]
    rels = [_supports_rel("F-aa000001", "F-aa000002")]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=rels)

    backend = FakeRestoreBackend("myproject")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(cfg, archive, target, project_tag="myproject")

    assert result["status"] in ("ok", "partial"), result
    assert result["nodes_restored"] == 2
    assert result["relationships_restored"] == 1
    assert "F-aa000001" in backend.nodes_by_id
    assert "F-aa000002" in backend.nodes_by_id
    assert any(
        r[0] == "F-aa000001" and r[1] == "SUPPORTS" and r[2] == "F-aa000002"
        for r in backend.relationships
    )


@pytest.mark.asyncio
async def test_restore_fresh_absolutizes_path_fields(tmp_path):
    """Path fields carrying ${PROJECT}/ sentinel are rewritten to target_root."""
    target = tmp_path / "target"
    target.mkdir()

    sentinel_path = "${PROJECT}/results/fig1.png"
    nodes = [_make_finding_node("F-bb000001", path=sentinel_path)]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("myproject")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(cfg, archive, target, project_tag="myproject")

    assert result["status"] in ("ok", "partial")
    node = backend.nodes_by_id.get("F-bb000001", {})
    stored_path = node.get("path", "")
    assert "${PROJECT}" not in stored_path, f"sentinel still in path: {stored_path}"
    assert str(target.resolve()) in stored_path, (
        f"target root not in path: {stored_path}"
    )


@pytest.mark.asyncio
async def test_restore_fresh_accepts_pristine_init_shell(tmp_path):
    """A clean target with only empty managed dirs is accepted."""
    target = tmp_path / "target"
    target.mkdir()
    # Simulate pristine wheeler init output.
    for d in ("knowledge", "synthesis", ".plans", ".notes"):
        (target / d).mkdir()
    (target / "wheeler.yaml").write_text("neo4j:\n  uri: bolt://localhost:7687\n")

    nodes = [_make_finding_node("F-cc000001")]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("proj")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(cfg, archive, target, project_tag="proj")

    assert "error" not in result or result.get("status") != "error", result


@pytest.mark.asyncio
async def test_restore_fresh_refuses_populated_dir_without_force(tmp_path):
    """Populated target is refused without force=True."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "important_data.csv").write_text("data")

    archive = _build_v2_archive(tmp_path, nodes=[], relationships=[])
    cfg = WheelerConfig()

    result = await restore_fresh(cfg, archive, target)  # force defaults to False

    assert result["status"] == "error"
    assert "not empty" in result["error"].lower() or "force" in result["error"].lower()


@pytest.mark.asyncio
async def test_restore_fresh_refuses_populated_dir_force_true(tmp_path):
    """force=True overrides the shape check but Neo4j check still applies."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "some_file.txt").write_text("existing")

    nodes = [_make_finding_node("F-dd000001")]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("proj2")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(cfg, archive, target, force=True, project_tag="proj2")

    # Should proceed (Neo4j empty), not return shape-check error.
    assert result.get("status") != "error" or "not empty" not in result.get("error", "")


@pytest.mark.asyncio
async def test_restore_fresh_refuses_populated_neo4j(tmp_path):
    """Even with force=True: refuse if Neo4j has nodes with the target project tag."""
    target = tmp_path / "target"
    target.mkdir()

    nodes = [_make_finding_node("F-ee000001")]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("populated-project")
    backend._pre_existing_count = 5  # simulate existing nodes

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(
            cfg, archive, target,
            force=True,
            project_tag="populated-project",
        )

    assert result["status"] == "error"
    assert "populated" in result["error"].lower() or "existing" in result["error"].lower() or "namespace" in result["error"].lower()


@pytest.mark.asyncio
async def test_restore_fresh_refuses_v1_archive(tmp_path):
    """v1 archive (no manifest_version) triggers the expected error."""
    target = tmp_path / "target"
    target.mkdir()

    # Build a v1-style archive using the original _build_archive helper.
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    nodes = [
        {"label": "Finding", "props": {"id": "F-v1test1", "title": "v1"}},
    ]
    archive = _build_archive(v1_dir, nodes=nodes, relationships=[])

    cfg = WheelerConfig()
    result = await restore_fresh(cfg, archive, target)

    assert result["status"] == "error"
    assert "predates portable restore" in result["error"]


@pytest.mark.asyncio
async def test_restore_fresh_refuses_tampered_manifest(tmp_path):
    """Mutated manifest_signature triggers an error."""
    target = tmp_path / "target"
    target.mkdir()

    nodes = [_make_finding_node("F-ff000001")]
    # Build with correct signature, then override with wrong one.
    archive = _build_v2_archive(
        tmp_path,
        nodes=nodes,
        relationships=[],
        manifest_overrides={"manifest_signature": "sha256:deadbeef"},
    )

    cfg = WheelerConfig()
    result = await restore_fresh(cfg, archive, target)

    assert result["status"] == "error"
    assert "integrity" in result["error"].lower() or "signature" in result["error"].lower()


@pytest.mark.asyncio
async def test_restore_fresh_accept_signature_mismatch_override(tmp_path):
    """accept_signature_mismatch=True overrides a tampered manifest and proceeds."""
    target = tmp_path / "target"

    nodes = [_make_finding_node("F-gg000001")]
    archive = _build_v2_archive(
        tmp_path,
        nodes=nodes,
        relationships=[],
        manifest_overrides={"manifest_signature": "sha256:deadbeef"},
    )

    backend = FakeRestoreBackend("proj3")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(
            cfg, archive, target,
            accept_signature_mismatch=True,
            project_tag="proj3",
        )

    assert result["status"] != "error" or "integrity" not in result.get("error", "")
    # The mismatch warning should be present.
    assert any("signature" in w.lower() or "mismatch" in w.lower() for w in result.get("warnings", []))


@pytest.mark.asyncio
async def test_restore_fresh_refuses_major_version_mismatch(tmp_path):
    """Archive with major-version-mismatched wheeler_version triggers error."""
    target = tmp_path / "target"

    nodes = [_make_finding_node("F-hh000001")]
    archive = _build_v2_archive(
        tmp_path,
        nodes=nodes,
        relationships=[],
        manifest_overrides={"wheeler_version": "99.0.0"},
    )

    cfg = WheelerConfig()
    result = await restore_fresh(cfg, archive, target)

    assert result["status"] == "error"
    assert "major version" in result["error"].lower() or "mismatch" in result["error"].lower()


@pytest.mark.asyncio
async def test_restore_fresh_skips_embeddings_on_model_mismatch(tmp_path):
    """When embedder.model differs, embeddings are skipped and a warning is emitted."""
    target = tmp_path / "target"

    nodes = [_make_finding_node("F-ii000001")]
    archive = _build_v2_archive(
        tmp_path,
        nodes=nodes,
        relationships=[],
        manifest_overrides={"embedder": {"model": "different-model", "dim": 256}},
        include_embeddings=True,
    )

    backend = FakeRestoreBackend("proj4")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(cfg, archive, target, project_tag="proj4")

    # Embeddings dir should NOT have been created.
    emb_dir = target / ".wheeler" / "embeddings"
    assert not emb_dir.exists() or not list(emb_dir.glob("*.bin")), (
        "Embeddings should not have been copied on model mismatch"
    )
    # Warning must mention embedder.
    assert any(
        "embedder" in w.lower() or "model" in w.lower()
        for w in result.get("warnings", [])
    )


@pytest.mark.asyncio
async def test_restore_fresh_per_node_failure_isolation(tmp_path):
    """A malformed node entry causes a failure record; restore continues."""
    target = tmp_path / "target"

    # One valid node, one malformed (no label field).
    malformed = {"labels": [], "props": {"id": "F-jj000001"}}
    valid = _make_finding_node("F-jj000002")
    nodes = [malformed, valid]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("proj5")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(cfg, archive, target, project_tag="proj5")

    assert len(result["restore_failures"]) == 1
    assert result["nodes_restored"] == 1  # valid node restored
    assert "F-jj000002" in backend.nodes_by_id


@pytest.mark.asyncio
async def test_restore_fresh_config_overrides_written_to_yaml(tmp_path):
    """neo4j_uri / neo4j_password / neo4j_database / project_tag are persisted."""
    target = tmp_path / "target"

    nodes = [_make_finding_node("F-kk000001")]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("override-tag")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        await restore_fresh(
            cfg, archive, target,
            neo4j_uri="bolt://other-host:7687",
            neo4j_password="secret123",
            neo4j_database="mydb",
            project_tag="override-tag",
        )

    import yaml  # noqa: PLC0415

    yaml_path = target / "wheeler.yaml"
    assert yaml_path.exists(), "wheeler.yaml was not created in target"
    with yaml_path.open() as fh:
        data = yaml.safe_load(fh)
    neo4j_cfg = data.get("neo4j", {})
    assert neo4j_cfg.get("uri") == "bolt://other-host:7687"
    assert neo4j_cfg.get("password") == "secret123"
    assert neo4j_cfg.get("database") == "mydb"
    assert neo4j_cfg.get("project_tag") == "override-tag"


@pytest.mark.asyncio
async def test_restore_fresh_search_text_not_replayed(tmp_path):
    """The archive's _search_text value must NOT land on the recipient node."""
    target = tmp_path / "target"

    nodes = [{
        "label": "Finding",
        "labels": ["Finding"],
        "props": {
            "id": "F-ll000001",
            "description": "test",
            "confidence": 0.5,
            "_search_text": "this-should-not-appear",
            "tier": "generated",
            "stability": 0.3,
            "session_id": "",
        },
    }]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("proj6")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        await restore_fresh(cfg, archive, target, project_tag="proj6")

    node = backend.nodes_by_id.get("F-ll000001", {})
    assert "_search_text" not in node or node["_search_text"] != "this-should-not-appear", (
        "_search_text from archive must be stripped before replay"
    )


@pytest.mark.asyncio
async def test_restore_fresh_script_path_does_not_exist(tmp_path):
    """Script node with non-existent path still creates a node (path error downgraded)."""
    target = tmp_path / "target"

    missing_path = "${PROJECT}/scripts/analysis.py"
    nodes = [_make_script_node("S-mm000001", path=missing_path)]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("proj7")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(cfg, archive, target, project_tag="proj7")

    # Node should exist (path warning, not error).
    assert "S-mm000001" in backend.nodes_by_id, (
        "Script node must be created even when path does not exist on recipient"
    )
    # No failure recorded for this node.
    failure_ids = [f["node_id"] for f in result["restore_failures"]]
    assert "S-mm000001" not in failure_ids


@pytest.mark.asyncio
async def test_restore_fresh_external_path_recorded(tmp_path):
    """A node with an absolute (non-sentinel) path appears in externally_rooted_paths."""
    target = tmp_path / "target"

    external_path = "/mnt/shared/data/dataset.csv"  # no ${PROJECT}/ prefix
    nodes = [{
        "label": "Dataset",
        "labels": ["Dataset"],
        "props": {
            "id": "D-nn000001",
            "path": external_path,
            "type": "csv",
            "description": "External dataset",
            "tier": "reference",
            "stability": 1.0,
            "session_id": "",
        },
    }]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("proj8")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        result = await restore_fresh(cfg, archive, target, project_tag="proj8")

    externals = result.get("externally_rooted_paths", [])
    assert len(externals) >= 1
    assert any(e.get("original_path") == external_path for e in externals)


@pytest.mark.asyncio
async def test_restore_fresh_execution_node_and_restore_log(tmp_path):
    """restore_fresh writes an Execution(kind=restore) node and a restore_log.jsonl."""
    target = tmp_path / "target"

    nodes = [_make_finding_node("F-oo000001")]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=[])

    backend = FakeRestoreBackend("proj9")

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        await restore_fresh(cfg, archive, target, project_tag="proj9")

    # There should be an Execution node with kind="restore".
    exec_nodes = [
        n for n in backend.nodes_by_id.values()
        if backend.node_label_by_id.get(n.get("id", "")) == "Execution"
        and n.get("kind") == "restore"
    ]
    assert len(exec_nodes) >= 1, "Expected at least one Execution(kind=restore) node"

    # restore_log.jsonl must exist and have a valid record.
    log_path = target / ".wheeler" / "restore_log.jsonl"
    assert log_path.exists(), "restore_log.jsonl not created"
    with log_path.open() as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    assert len(lines) >= 1, "restore_log.jsonl is empty"
    record = json.loads(lines[0])
    # Required fields.
    for field in ("ts", "archive_path", "archive_uuid", "manifest_version",
                  "source", "recipient", "mode", "nodes_restored",
                  "relationships_restored", "failures"):
        assert field in record, f"restore_log.jsonl missing field: {field}"
    assert record["mode"] == "fresh"


# ---------------------------------------------------------------------------
# Tests: restore_merge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_merge_skip_leaves_existing_untouched(tmp_path):
    """conflict_policy='skip' does not overwrite existing nodes."""
    backend = FakeRestoreBackend("merge-proj")
    # Pre-populate a Finding in the backend.
    await backend.create_node("Finding", {
        "id": "F-pp000001",
        "description": "original",
        "confidence": 0.9,
        "tier": "reference",
        "stability": 0.9,
        "session_id": "",
    })

    incoming = [{
        "label": "Finding",
        "labels": ["Finding"],
        "props": {
            "id": "F-pp000001",
            "description": "replacement",
            "confidence": 0.1,
            "tier": "generated",
            "stability": 0.3,
            "session_id": "",
        },
    }]
    archive = _build_v2_archive(tmp_path, nodes=incoming, relationships=[])

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        cfg.neo4j.project_tag = "merge-proj"
        result = await restore_merge(cfg, archive, conflict_policy="skip")

    assert result["merge_report"]["skipped"] == 1
    # Original description preserved.
    node = backend.nodes_by_id["F-pp000001"]
    assert node.get("description") == "original", f"Got: {node.get('description')}"


@pytest.mark.asyncio
async def test_restore_merge_replace_updates_existing(tmp_path):
    """conflict_policy='replace' updates the conflicting node with incoming props."""
    backend = FakeRestoreBackend("merge-proj2")
    await backend.create_node("Finding", {
        "id": "F-qq000001",
        "description": "old description",
        "confidence": 0.5,
        "tier": "generated",
        "stability": 0.3,
        "session_id": "",
    })

    incoming = [{
        "label": "Finding",
        "labels": ["Finding"],
        "props": {
            "id": "F-qq000001",
            "description": "new description",
            "confidence": 0.9,
            "tier": "generated",
            "stability": 0.3,
            "session_id": "",
        },
    }]
    archive = _build_v2_archive(tmp_path, nodes=incoming, relationships=[])

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        cfg.neo4j.project_tag = "merge-proj2"
        result = await restore_merge(cfg, archive, conflict_policy="replace")

    assert result["merge_report"]["replaced"] == 1
    node = backend.nodes_by_id["F-qq000001"]
    assert node.get("description") == "new description"


@pytest.mark.asyncio
async def test_restore_merge_prefix_creates_renamed_nodes(tmp_path):
    """conflict_policy='prefix' creates <prefix>__<id> nodes and rewrites rels."""
    backend = FakeRestoreBackend("merge-proj3")

    nodes = [
        _make_finding_node("F-rr000001"),
        _make_finding_node("F-rr000002"),
    ]
    rels = [_supports_rel("F-rr000001", "F-rr000002")]
    archive = _build_v2_archive(tmp_path, nodes=nodes, relationships=rels)

    with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend), \
         patch("wheeler.restore.get_backend", return_value=backend):
        cfg = WheelerConfig()
        cfg.neo4j.project_tag = "merge-proj3"
        result = await restore_merge(
            cfg, archive,
            conflict_policy="prefix",
            prefix="arch1",
        )

    assert result["merge_report"]["prefixed"] == 2
    assert "arch1__F-rr000001" in backend.nodes_by_id
    assert "arch1__F-rr000002" in backend.nodes_by_id
    # Relationship endpoints should use prefixed ids.
    assert any(
        r[0] == "arch1__F-rr000001" and r[1] == "SUPPORTS" and r[2] == "arch1__F-rr000002"
        for r in backend.relationships
    )


# ---------------------------------------------------------------------------
# Back-compat regression: verify_backup still works on v1 archives
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_backup_v1_archive_still_passes(tmp_path):
    """verify_backup tolerates v1 archives (no manifest_version) unchanged."""
    nodes, rels = _two_findings_one_link()
    archive = _build_archive(tmp_path, nodes=nodes, relationships=rels)

    cfg = WheelerConfig()
    scratch_tag = "__restore_verify_v1_compat__"
    backend = FakeBackend(project_tag=scratch_tag)

    import wheeler.restore as restore_mod

    original = restore_mod._make_scratch_tag
    restore_mod._make_scratch_tag = lambda: scratch_tag
    try:
        result = await verify_backup(cfg, archive, backend=backend)
    finally:
        restore_mod._make_scratch_tag = original

    assert result["verdict"] == "PASS", result


# ---------------------------------------------------------------------------
# Wave 5 gap-fix regression tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesis_sentinel_resolves_on_restore(tmp_path):
    """Gap 1: synthesis files have no ${PROJECT} literal and no source root after restore.

    Creates project A with a synthesis/*.md file that contains the absolute
    source root in its text. Packs via create_backup (which rewrites the path
    to ${PROJECT}/), then restores into a different target_root (project B).
    Reads the synthesis file from disk on B and asserts:
      - No literal ``${PROJECT}`` remains (sentinel was resolved).
      - No path component of project A's root remains (source root did not leak).
    """
    from unittest.mock import AsyncMock, patch  # noqa: PLC0415

    from wheeler.backup import create_backup  # noqa: PLC0415
    from wheeler.config import WheelerConfig, Neo4jConfig  # noqa: PLC0415

    # ---- Project A layout ----
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    project_b.mkdir(parents=True)

    knowledge_a = project_a / "knowledge"
    synthesis_a = project_a / "synthesis"
    for d in (knowledge_a, synthesis_a, project_a / ".wheeler",
              project_a / ".plans", project_a / ".notes"):
        d.mkdir(parents=True, exist_ok=True)

    abs_path_in_synth = str(project_a.resolve() / "knowledge" / "F-synth001.json")

    # Write a synthesis .md that embeds the absolute path.
    (synthesis_a / "F-synth001.md").write_text(
        f"# F-synth001\n\n"
        f"path: {abs_path_in_synth}\n\n"
        f"Some body text referencing {str(project_a.resolve())} again.\n"
    )
    (knowledge_a / "F-synth001.json").write_text(
        json.dumps({"id": "F-synth001", "type": "Finding", "description": "synthesis sentinel test"})
    )
    (project_a / "wheeler.yaml").write_text(
        "neo4j:\n  uri: bolt://localhost:7687\n  password: pw\n"
        "knowledge_path: knowledge\n"
        "synthesis_path: synthesis\n"
    )

    cfg_a = WheelerConfig(
        neo4j=Neo4jConfig(project_tag="proj-sentinel-a"),
        knowledge_path=str(knowledge_a),
        synthesis_path=str(synthesis_a),
        project_root=str(project_a),
    )

    # Inline FakeBackend for backup (no Neo4j needed).
    class _TinyFake:
        async def initialize(self): pass
        async def close(self): pass
        async def run_cypher(self, q, p=None): return []

    archive_dest = tmp_path / "backups"
    archive_dest.mkdir()

    with patch("wheeler.backup.get_backend", return_value=_TinyFake()), \
         patch("wheeler.backup._record_backup_execution", new_callable=AsyncMock):
        archive_path = await create_backup(
            cfg_a,
            destination=archive_dest,
            scope="project",
        )

    # ---- Restore into project B ----
    class _RestoreFake(FakeRestoreBackend):
        """Minimal backend for restore (no pre-existing nodes)."""

    backend_b = _RestoreFake("proj-sentinel-b")
    cfg_b_initial = WheelerConfig(
        neo4j=Neo4jConfig(project_tag="proj-sentinel-b"),
        project_root=str(project_b),
    )

    with patch("wheeler.tools.graph_tools._get_backend",
               new_callable=AsyncMock, return_value=backend_b), \
         patch("wheeler.restore.get_backend", return_value=backend_b):
        result = await restore_fresh(
            cfg_b_initial,
            archive_path,
            target_root=project_b,
            project_tag="proj-sentinel-b",
        )

    assert result["status"] in ("ok", "partial"), f"restore failed: {result}"

    # ---- Check synthesis files on B ----
    a_root_str = str(project_a.resolve())
    synth_b = project_b / "synthesis"
    assert synth_b.exists(), "synthesis/ dir not extracted to project B"

    for md_file in synth_b.rglob("*.md"):
        content = md_file.read_text(errors="replace")
        assert "${PROJECT}" not in content, (
            f"Literal ${{PROJECT}} sentinel still present in {md_file.name}: "
            f"the synthesis rewrite + restore did not resolve it."
        )
        assert a_root_str not in content, (
            f"Project A's root path leaked into {md_file.name} on project B. "
            f"A root: {a_root_str!r}"
        )
