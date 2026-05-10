"""Tests for wheeler.backup: CLI snapshot of canonical state.

These tests use a tiny inline FakeBackend so they don't need a live Neo4j.
The graph dump is exercised against the fake; the file-layer archiving is
exercised against a tmp_path layout.
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from wheeler.backup import create_backup
from wheeler.config import load_config


class FakeBackend:
    """Mock backend that returns canned node/relationship rows.

    The dump cypher matches on the substring ``MATCH (n)`` for nodes vs
    the relationship pattern, so we route by that.
    """

    def __init__(
        self,
        node_rows: list[dict] | None = None,
        rel_rows: list[dict] | None = None,
        fail_on: str | None = None,
    ) -> None:
        self._node_rows = node_rows or []
        self._rel_rows = rel_rows or []
        self._fail_on = fail_on  # "init" | "nodes" | "rels" | None

    async def initialize(self) -> None:
        if self._fail_on == "init":
            raise RuntimeError("simulated init failure")

    async def close(self) -> None:
        pass

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        # node dump uses MATCH (n) RETURN labels(n)...; rel dump uses ()-[r]->()
        if "()-[r]" in query.replace(" ", "").replace("(a)", "()") or "[r]->" in query:
            if self._fail_on == "rels":
                raise RuntimeError("simulated rel dump failure")
            return list(self._rel_rows)
        if self._fail_on == "nodes":
            raise RuntimeError("simulated node dump failure")
        return list(self._node_rows)


def _setup_project(tmp_path: Path) -> tuple:
    """Build a tiny knowledge/synthesis/.wheeler/wheeler.yaml layout."""
    knowledge_dir = tmp_path / "knowledge"
    synthesis_dir = tmp_path / "synthesis"
    wheeler_dir = tmp_path / ".wheeler"
    knowledge_dir.mkdir()
    synthesis_dir.mkdir()
    wheeler_dir.mkdir()
    (knowledge_dir / "F-test1234.json").write_text(
        json.dumps({"id": "F-test1234", "type": "Finding", "description": "x"})
    )
    (synthesis_dir / "F-test1234.md").write_text("# F-test1234\n\nbody\n")
    (wheeler_dir / "request_log.jsonl").write_text('{"trace_id": "abc"}\n')
    (tmp_path / "wheeler.yaml").write_text("knowledge_path: knowledge\n")

    cfg = load_config()
    cfg.knowledge_path = str(knowledge_dir)
    cfg.synthesis_path = str(synthesis_dir)
    return cfg, knowledge_dir, synthesis_dir, wheeler_dir


async def test_create_backup_produces_archive(tmp_path, monkeypatch):
    """create_backup writes a .tar.gz containing a manifest.json."""
    monkeypatch.chdir(tmp_path)
    cfg, *_ = _setup_project(tmp_path)

    backend = FakeBackend(
        node_rows=[
            {"labels": ["Finding"], "props": {"id": "F-aaa", "description": "x"}},
        ],
        rel_rows=[],
    )

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out")

    assert archive.exists()
    assert archive.name.startswith("wheeler-backup-")
    assert archive.suffix == ".gz"

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        assert "manifest.json" in names
        manifest = json.loads(tar.extractfile("manifest.json").read())

    for key in (
        "timestamp",
        "wheeler_version",
        "graph_available",
        "node_counts_by_label",
        "relationship_count_by_type",
        "canonical_file_hashes",
        "archive_layout",
    ):
        assert key in manifest, f"manifest missing {key}"


async def test_backup_includes_canonical_files(tmp_path, monkeypatch):
    """Files under knowledge/, synthesis/, .wheeler/, and wheeler.yaml are inside."""
    monkeypatch.chdir(tmp_path)
    cfg, knowledge_dir, synthesis_dir, wheeler_dir = _setup_project(tmp_path)

    backend = FakeBackend()
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out")

    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())

    assert "knowledge/F-test1234.json" in names
    assert "synthesis/F-test1234.md" in names
    assert ".wheeler/request_log.jsonl" in names
    assert "wheeler.yaml" in names
    assert "graph_nodes.jsonl" in names
    assert "graph_relationships.jsonl" in names


async def test_manifest_node_counts_match(tmp_path, monkeypatch):
    """Manifest counts mirror what the backend returned."""
    monkeypatch.chdir(tmp_path)
    cfg, *_ = _setup_project(tmp_path)

    backend = FakeBackend(
        node_rows=[
            {"labels": ["Finding"], "props": {"id": "F-1"}},
            {"labels": ["Finding"], "props": {"id": "F-2"}},
            {"labels": ["Finding"], "props": {"id": "F-3"}},
            {"labels": ["Hypothesis"], "props": {"id": "H-1"}},
            {"labels": ["Hypothesis"], "props": {"id": "H-2"}},
        ],
        rel_rows=[
            {
                "source_id": "F-1",
                "rel_type": "WAS_GENERATED_BY",
                "rel_props": {},
                "target_id": "X-1",
            },
            {
                "source_id": "X-1",
                "rel_type": "USED",
                "rel_props": {},
                "target_id": "S-1",
            },
            {
                "source_id": "X-2",
                "rel_type": "USED",
                "rel_props": {},
                "target_id": "S-1",
            },
        ],
    )
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    assert manifest["node_counts_by_label"] == {"Finding": 3, "Hypothesis": 2}
    assert manifest["total_nodes"] == 5
    assert manifest["relationship_count_by_type"] == {
        "WAS_GENERATED_BY": 1,
        "USED": 2,
    }
    assert manifest["total_relationships"] == 3
    assert manifest["graph_available"] is True


async def test_backup_destination_default(tmp_path, monkeypatch):
    """Default destination is <project>/.wheeler/backups/ relative to cwd."""
    monkeypatch.chdir(tmp_path)
    cfg, *_ = _setup_project(tmp_path)

    backend = FakeBackend()
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=None)

    expected = (tmp_path / ".wheeler" / "backups").resolve()
    assert archive.parent == expected, f"archive at {archive.parent}, expected {expected}"


async def test_archive_layout_documented(tmp_path, monkeypatch):
    """manifest's archive_layout enumerates everything in the tar."""
    monkeypatch.chdir(tmp_path)
    cfg, *_ = _setup_project(tmp_path)

    backend = FakeBackend()
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    layout = manifest["archive_layout"]
    # Every documented top-level entry must be either a directory we
    # archived or a file we wrote.
    for entry in layout:
        assert entry in {
            "knowledge/",
            "synthesis/",
            ".wheeler/",
            "wheeler.yaml",
            "graph_nodes.jsonl",
            "graph_relationships.jsonl",
            "manifest.json",
        }, f"unexpected layout entry: {entry}"
    # The four core entries must all be present given _setup_project.
    for required in (
        "knowledge/",
        "synthesis/",
        ".wheeler/",
        "wheeler.yaml",
        "graph_nodes.jsonl",
        "graph_relationships.jsonl",
        "manifest.json",
    ):
        assert required in layout


async def test_backup_resilient_to_offline_graph(tmp_path, monkeypatch):
    """If the graph is offline, the file layers still archive."""
    monkeypatch.chdir(tmp_path)
    cfg, *_ = _setup_project(tmp_path)

    backend = FakeBackend(fail_on="init")
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out")

    assert archive.exists()
    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())
        names = set(tar.getnames())

    assert manifest["graph_available"] is False
    assert manifest["total_nodes"] == 0
    assert manifest["total_relationships"] == 0
    # File layers still present.
    assert "knowledge/F-test1234.json" in names
    assert "synthesis/F-test1234.md" in names


async def test_canonical_file_hashes_are_sha256(tmp_path, monkeypatch):
    """Each archived file has a sha256:<hex> hash entry in the manifest."""
    monkeypatch.chdir(tmp_path)
    cfg, knowledge_dir, *_ = _setup_project(tmp_path)

    backend = FakeBackend()
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    hashes = manifest["canonical_file_hashes"]
    assert "knowledge/F-test1234.json" in hashes
    assert hashes["knowledge/F-test1234.json"].startswith("sha256:")
    # 64 hex chars after the prefix.
    digest = hashes["knowledge/F-test1234.json"].split(":", 1)[1]
    assert len(digest) == 64
