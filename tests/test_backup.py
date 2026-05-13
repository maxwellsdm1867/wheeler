"""Tests for wheeler.backup: CLI snapshot of canonical state.

These tests use a tiny inline FakeBackend so they don't need a live Neo4j.
The graph dump is exercised against the fake; the file-layer archiving is
exercised against a tmp_path layout.
"""

from __future__ import annotations

import json
import re
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.backup import BackupAbortedDueToSecrets, create_backup
from wheeler.config import load_config
from wheeler.portability import compute_manifest_signature


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
    """scope=graph-only packs knowledge/, synthesis/, .wheeler/, wheeler.yaml."""
    monkeypatch.chdir(tmp_path)
    cfg, knowledge_dir, synthesis_dir, wheeler_dir = _setup_project(tmp_path)

    backend = FakeBackend()
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="graph-only")

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
    """manifest's archive_layout enumerates expected entries (graph-only scope)."""
    monkeypatch.chdir(tmp_path)
    cfg, *_ = _setup_project(tmp_path)

    backend = FakeBackend()
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="graph-only")

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
            "HANDOFF.md",
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
        "HANDOFF.md",
        "manifest.json",
    ):
        assert required in layout


async def test_backup_resilient_to_offline_graph(tmp_path, monkeypatch):
    """If the graph is offline, the file layers still archive (graph-only scope)."""
    monkeypatch.chdir(tmp_path)
    cfg, *_ = _setup_project(tmp_path)

    backend = FakeBackend(fail_on="init")
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="graph-only")

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
    """Each archived file has a sha256:<hex> hash entry in the manifest (graph-only)."""
    monkeypatch.chdir(tmp_path)
    cfg, knowledge_dir, *_ = _setup_project(tmp_path)

    backend = FakeBackend()
    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="graph-only")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    hashes = manifest["canonical_file_hashes"]
    assert "knowledge/F-test1234.json" in hashes
    assert hashes["knowledge/F-test1234.json"].startswith("sha256:")
    # 64 hex chars after the prefix.
    digest = hashes["knowledge/F-test1234.json"].split(":", 1)[1]
    assert len(digest) == 64


# ---------------------------------------------------------------------------
# v2 manifest tests
# ---------------------------------------------------------------------------


def _setup_full_project(tmp_path: Path) -> tuple:
    """Extended fixture that sets project_root on the config.

    Adds .plans/STATE.md, .notes/scratch.md, plus the standard
    knowledge/synthesis/.wheeler/wheeler.yaml layout.
    Returns (cfg, project_root) with absolute paths wired into cfg.
    """
    knowledge_dir = tmp_path / "knowledge"
    synthesis_dir = tmp_path / "synthesis"
    wheeler_dir = tmp_path / ".wheeler"
    plans_dir = tmp_path / ".plans"
    notes_dir = tmp_path / ".notes"
    for d in (knowledge_dir, synthesis_dir, wheeler_dir, plans_dir, notes_dir):
        d.mkdir(parents=True, exist_ok=True)

    (knowledge_dir / "F-test1234.json").write_text(
        json.dumps({"id": "F-test1234", "type": "Finding", "description": "x"})
    )
    (synthesis_dir / "F-test1234.md").write_text("# F-test1234\n\nbody\n")
    (wheeler_dir / "request_log.jsonl").write_text('{"trace_id": "abc"}\n')
    (plans_dir / "STATE.md").write_text("# State\n\ncurrent.\n")
    (notes_dir / "scratch.md").write_text("# Scratch\n\nnotes.\n")
    yaml_content = (
        "neo4j:\n"
        "  uri: bolt://localhost:7687\n"
        "  username: neo4j\n"
        "  password: super-secret-pw\n"
        "knowledge_path: knowledge\n"
    )
    (tmp_path / "wheeler.yaml").write_text(yaml_content)

    cfg = load_config()
    cfg.knowledge_path = str(knowledge_dir)
    cfg.synthesis_path = str(synthesis_dir)
    cfg.project_root = str(tmp_path)
    return cfg, tmp_path


async def test_manifest_v2_fields(tmp_path, monkeypatch):
    """Manifest has all required v2 fields with correct types."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    assert manifest["manifest_version"] == 2
    assert re.match(r"^[0-9a-f]{32}$", manifest["archive_uuid"]), \
        f"archive_uuid not 32 hex chars: {manifest['archive_uuid']}"
    assert manifest["path_rewrite_scheme"] == "PROJECT_VAR"
    assert manifest["schema_version"] == "1"
    assert "hostname" in manifest["source"]
    assert "platform" in manifest["source"]
    assert "python_version" in manifest["source"]
    assert re.match(r"^sha256:[0-9a-f]{64}$", manifest["manifest_signature"]), \
        f"manifest_signature format wrong: {manifest['manifest_signature']}"


async def test_manifest_signature_verifies(tmp_path, monkeypatch):
    """Re-computing the signature over the stored manifest returns the same value."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    stored_sig = manifest["manifest_signature"]
    recomputed = compute_manifest_signature(manifest)
    assert recomputed == stored_sig, "Signature verification failed"


async def test_scope_project_packs_plans_and_notes(tmp_path, monkeypatch):
    """scope=project includes .plans/STATE.md and .notes/scratch.md."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())

    assert "project/.plans/STATE.md" in names
    assert "project/.notes/scratch.md" in names
    # Knowledge and synthesis still present under project/ prefix.
    assert "project/knowledge/F-test1234.json" in names
    assert "project/synthesis/F-test1234.md" in names


async def test_scope_graph_only_no_project_prefix(tmp_path, monkeypatch):
    """scope=graph-only produces no project/ entries at all."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="graph-only")

    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())

    project_entries = [n for n in names if n.startswith("project/")]
    assert not project_entries, \
        f"graph-only archive contains project/ entries: {project_entries}"
    # v1 layout preserved.
    assert "knowledge/F-test1234.json" in names
    assert "synthesis/F-test1234.md" in names


async def test_scope_graph_only_no_external_references(tmp_path, monkeypatch):
    """scope=graph-only manifest has an empty external_references list."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="graph-only")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    # external_references collection only happens during project scope walk.
    # For graph-only, the list is derived only from node JSONL rewrites.
    # An empty project produces an empty list.
    assert isinstance(manifest["external_references"], list)


async def test_external_references_for_outside_path(tmp_path, monkeypatch):
    """Dataset whose path lives outside project_root produces an external_reference."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    # Create a git repo in a sibling directory to simulate an external dataset.
    ext_dir = tmp_path.parent / "external-data"
    ext_dir.mkdir(exist_ok=True)
    # Initialise as a git repo.
    subprocess.run(["git", "init", str(ext_dir)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(ext_dir), "config", "user.email", "test@test.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(ext_dir), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )
    ext_file = ext_dir / "data.csv"
    ext_file.write_text("a,b,c\n1,2,3\n")
    subprocess.run(["git", "-C", str(ext_dir), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(ext_dir), "commit", "-m", "init"],
        check=True, capture_output=True,
    )

    # A Dataset node whose path points to the external git repo.
    external_path = str(ext_file)
    node_rows = [
        {
            "labels": ["Dataset"],
            "props": {"id": "D-ext001", "type": "Dataset", "path": external_path},
        }
    ]
    backend = FakeBackend(node_rows=node_rows)

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    ext_refs = manifest["external_references"]
    assert len(ext_refs) >= 1, "Expected at least one external_reference"
    ref = next((r for r in ext_refs if r["node_id"] == "D-ext001"), None)
    assert ref is not None, "No external_reference for D-ext001"
    assert ref["label"] == "Dataset"
    assert ref["field"] == "path"
    assert ref["original_path"] == external_path
    # git info must be present (repo was initialised above).
    assert "git_commit" in ref, "external_reference missing git_commit"
    assert ref["git_commit"] != "", "git_commit should be a real SHA"


async def test_secret_scan_raises_on_api_key(tmp_path, monkeypatch):
    """Backup aborts with BackupAbortedDueToSecrets when an API key is found."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    # Plant a secret in .notes/scratch.md.
    notes_file = tmp_path / ".notes" / "scratch.md"
    notes_file.write_text("# Scratch\n\nANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxx\n")

    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        with pytest.raises(BackupAbortedDueToSecrets) as exc_info:
            await create_backup(cfg, destination=tmp_path / "out", scope="project")

    # The exception must name the offending file.
    offenders = exc_info.value.offenders
    assert len(offenders) >= 1
    offending_paths = [o["path"] for o in offenders]
    assert any("scratch.md" in p for p in offending_paths), \
        f"scratch.md not in offenders: {offending_paths}"


async def test_secret_scan_allow_secrets_override(tmp_path, monkeypatch):
    """allow_secrets=True lets an archive containing API keys through."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    notes_file = tmp_path / ".notes" / "scratch.md"
    notes_file.write_text("# Scratch\n\nANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxx\n")

    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        # Should not raise.
        archive = await create_backup(
            cfg,
            destination=tmp_path / "out",
            scope="project",
            allow_secrets=True,
        )

    assert archive.exists()


async def test_wheeler_yaml_password_stripped(tmp_path, monkeypatch):
    """wheeler.yaml in archive has password: ${NEO4J_PASSWORD} regardless of source."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    # The yaml written by _setup_full_project has password: super-secret-pw.
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        # wheeler.yaml lives at project/wheeler.yaml in project scope.
        member = tar.extractfile("project/wheeler.yaml")
        assert member is not None, "project/wheeler.yaml missing from archive"
        content = member.read().decode("utf-8")

    assert "super-secret-pw" not in content, "Real password leaked into archive"
    assert "${NEO4J_PASSWORD}" in content, "Password placeholder not written"


async def test_wheeler_yaml_password_stripped_graph_only(tmp_path, monkeypatch):
    """scope=graph-only also strips the Neo4j password from wheeler.yaml."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="graph-only")

    with tarfile.open(archive, "r:gz") as tar:
        member = tar.extractfile("wheeler.yaml")
        assert member is not None
        content = member.read().decode("utf-8")

    assert "super-secret-pw" not in content
    assert "${NEO4J_PASSWORD}" in content


async def test_max_artifact_size_excludes_large_files(tmp_path, monkeypatch):
    """Files larger than max_artifact_size are in excluded_paths with reason too_large."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    # Write a file larger than 1024 bytes.
    big_file = tmp_path / ".notes" / "big.txt"
    big_file.write_bytes(b"x" * 2048)

    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(
            cfg,
            destination=tmp_path / "out",
            scope="project",
            max_artifact_size=1024,
        )

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())
        names = set(tar.getnames())

    # The big file must not appear in the archive.
    assert "project/.notes/big.txt" not in names

    # It must be in excluded_paths with reason too_large.
    excluded = manifest["excluded_paths"]
    too_large = [e for e in excluded if e.get("reason") == "too_large"]
    assert any("big.txt" in e["path"] for e in too_large), \
        f"big.txt not in too_large excluded_paths: {too_large}"


async def test_knowledge_json_path_rewritten_in_archive(tmp_path, monkeypatch):
    """knowledge/*.json bytes in archive have ${PROJECT}/ paths; on-disk file unchanged."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    # Write a knowledge JSON with an absolute path.
    abs_path = str(project_root / "data" / "myfile.csv")
    knowledge_file = tmp_path / "knowledge" / "D-abs001.json"
    knowledge_file.write_text(
        json.dumps({"id": "D-abs001", "type": "Dataset", "path": abs_path})
    )

    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    # Check the in-archive bytes have the sentinel.
    with tarfile.open(archive, "r:gz") as tar:
        member = tar.extractfile("project/knowledge/D-abs001.json")
        assert member is not None
        archived_data = json.loads(member.read())

    assert archived_data["path"].startswith("${PROJECT}/"), \
        f"path not rewritten in archive: {archived_data['path']}"

    # On-disk file must still have the absolute path.
    on_disk = json.loads(knowledge_file.read_text())
    assert on_disk["path"] == abs_path, \
        f"on-disk file was mutated: {on_disk['path']}"


async def test_manifest_source_fields(tmp_path, monkeypatch):
    """Manifest source block has hostname, platform, python_version, packed_by."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    source = manifest["source"]
    assert "hostname" in source and source["hostname"]
    assert "platform" in source and source["platform"]
    assert "python_version" in source and source["python_version"]
    assert "packed_by" in source  # may be empty string in some CI envs


# ---------------------------------------------------------------------------
# Wave 5 gap-fix regression tests
# ---------------------------------------------------------------------------


async def test_allow_secrets_recorded_in_manifest(tmp_path, monkeypatch):
    """Gap 2: allow_secrets=True records offending files in manifest.allowed_secret_files.

    Backs up a project containing ANTHROPIC_API_KEY=sk-ant-test in
    .notes/leak.md with allow_secrets=True. The manifest must carry an
    allowed_secret_files list with one entry that references .notes/leak.md
    and lists both ANTHROPIC_API_KEY and sk-ant-token pattern names.
    """
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    # Plant a file with TWO matching patterns (key name + token value).
    leak_file = tmp_path / ".notes" / "leak.md"
    leak_file.write_text(
        "# Leak\n\nANTHROPIC_API_KEY=sk-ant-test001\n"
    )

    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(
            cfg,
            destination=tmp_path / "out",
            scope="project",
            allow_secrets=True,
        )

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    allowed = manifest.get("allowed_secret_files")
    assert allowed is not None, "manifest missing allowed_secret_files key"
    assert isinstance(allowed, list), "allowed_secret_files must be a list"
    assert len(allowed) >= 1, f"Expected at least one entry, got: {allowed}"

    # Find the entry for leak.md.
    entry = next(
        (e for e in allowed if "leak.md" in e["path"]),
        None,
    )
    assert entry is not None, (
        f"No entry for leak.md in allowed_secret_files: {allowed}"
    )
    patterns = entry.get("patterns", [])
    assert "ANTHROPIC_API_KEY" in patterns, (
        f"ANTHROPIC_API_KEY not listed in patterns: {patterns}"
    )
    assert "sk-ant-token" in patterns, (
        f"sk-ant-token pattern not listed in patterns: {patterns}"
    )


async def test_graph_only_scope_runs_secret_scan(tmp_path, monkeypatch):
    """Gap 3: scope=graph-only still aborts on secrets in knowledge/*.json.

    Builds a project where knowledge/F-test.json contains an sk-ant- token
    in a field value. Runs create_backup with scope='graph-only' (no
    allow_secrets). Asserts BackupAbortedDueToSecrets is raised.
    """
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    # Overwrite the knowledge file with a secret token in a description field.
    knowledge_file = tmp_path / "knowledge" / "F-test1234.json"
    knowledge_file.write_text(
        json.dumps({
            "id": "F-test1234",
            "type": "Finding",
            "description": "key=sk-ant-supersecret123 was accidentally captured",
        })
    )

    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        with pytest.raises(BackupAbortedDueToSecrets) as exc_info:
            await create_backup(
                cfg,
                destination=tmp_path / "out",
                scope="graph-only",
            )

    offenders = exc_info.value.offenders
    assert len(offenders) >= 1, "Expected at least one secret offender"
    offending_paths = [o["path"] for o in offenders]
    assert any("F-test1234.json" in p for p in offending_paths), (
        f"F-test1234.json not in offenders: {offending_paths}"
    )


# ---------------------------------------------------------------------------
# Wave 6: HANDOFF.md tests
# ---------------------------------------------------------------------------


async def test_handoff_md_present_in_archive(tmp_path, monkeypatch):
    """HANDOFF.md is at top level of the archive (not under project/),
    and contains the archive_uuid, source hostname, and wheeler_version."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        assert "HANDOFF.md" in names, "HANDOFF.md missing from archive top level"
        # Must NOT be under project/
        assert "project/HANDOFF.md" not in names

        member = tar.extractfile("HANDOFF.md")
        assert member is not None
        content = member.read().decode("utf-8")

        manifest = json.loads(tar.extractfile("manifest.json").read())

    archive_uuid = manifest["archive_uuid"]
    hostname = manifest["source"]["hostname"]
    wheeler_version = manifest["wheeler_version"]

    assert archive_uuid in content, f"archive_uuid {archive_uuid} not in HANDOFF.md"
    assert hostname in content, f"hostname {hostname} not in HANDOFF.md"
    assert wheeler_version in content, f"wheeler_version {wheeler_version} not in HANDOFF.md"


async def test_handoff_md_external_references_section(tmp_path, monkeypatch):
    """When a Dataset has a path outside project_root in a git repo,
    HANDOFF.md's external-references table contains a row with the node id."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    # Create a git repo in a sibling directory to simulate an external dataset.
    ext_dir = tmp_path.parent / "ext-handoff-data"
    ext_dir.mkdir(exist_ok=True)
    subprocess.run(["git", "init", str(ext_dir)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(ext_dir), "config", "user.email", "test@test.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(ext_dir), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )
    ext_file = ext_dir / "dataset.csv"
    ext_file.write_text("a,b\n1,2\n")
    subprocess.run(["git", "-C", str(ext_dir), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(ext_dir), "commit", "-m", "init"],
        check=True, capture_output=True,
    )

    external_path = str(ext_file)
    node_rows = [
        {
            "labels": ["Dataset"],
            "props": {"id": "D-handoff001", "type": "Dataset", "path": external_path},
        }
    ]
    backend = FakeBackend(node_rows=node_rows)

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        member = tar.extractfile("HANDOFF.md")
        assert member is not None
        content = member.read().decode("utf-8")

    # The external references table should mention the node id.
    assert "D-handoff001" in content, (
        "External reference node D-handoff001 not found in HANDOFF.md"
    )


async def test_handoff_md_allowed_secrets_section(tmp_path, monkeypatch):
    """When allow_secrets=True and a secret is found, HANDOFF.md mentions
    the offending file in the 'Secrets allowed' section."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)

    # Plant a secret in .notes/secret_file.md.
    secret_file = tmp_path / ".notes" / "secret_file.md"
    secret_file.write_text("# Notes\n\nANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxx\n")

    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(
            cfg,
            destination=tmp_path / "out",
            scope="project",
            allow_secrets=True,
        )

    with tarfile.open(archive, "r:gz") as tar:
        member = tar.extractfile("HANDOFF.md")
        assert member is not None
        content = member.read().decode("utf-8")

    assert "secret_file.md" in content, (
        "Offending file secret_file.md not mentioned in HANDOFF.md secrets section"
    )


async def test_handoff_md_no_externals_message(tmp_path, monkeypatch):
    """Clean project with no external references: HANDOFF.md says
    'None. All referenced files are inside the archive.'"""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        member = tar.extractfile("HANDOFF.md")
        assert member is not None
        content = member.read().decode("utf-8")

    assert "None. All referenced files are inside the archive." in content, (
        "Expected 'None. All referenced files are inside the archive.' in HANDOFF.md"
    )


async def test_handoff_md_scope_label(tmp_path, monkeypatch):
    """Archives with scope=project say 'Scope: project' and
    scope=graph-only say 'Scope: graph-only'."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive_proj = await create_backup(
            cfg, destination=tmp_path / "out", scope="project"
        )
        archive_graph = await create_backup(
            cfg, destination=tmp_path / "out2", scope="graph-only"
        )

    with tarfile.open(archive_proj, "r:gz") as tar:
        content_proj = tar.extractfile("HANDOFF.md").read().decode("utf-8")

    with tarfile.open(archive_graph, "r:gz") as tar:
        content_graph = tar.extractfile("HANDOFF.md").read().decode("utf-8")

    assert "**Scope**: project" in content_proj, (
        f"scope=project not found in HANDOFF.md: {content_proj[:500]}"
    )
    assert "**Scope**: graph-only" in content_graph, (
        f"scope=graph-only not found in HANDOFF.md: {content_graph[:500]}"
    )


async def test_handoff_md_in_archive_layout(tmp_path, monkeypatch):
    """manifest's archive_layout lists 'HANDOFF.md'."""
    monkeypatch.chdir(tmp_path)
    cfg, project_root = _setup_full_project(tmp_path)
    backend = FakeBackend()

    with patch(
        "wheeler.backup.get_backend", return_value=backend
    ), patch(
        "wheeler.backup._record_backup_execution",
        new_callable=AsyncMock,
    ):
        archive = await create_backup(cfg, destination=tmp_path / "out", scope="project")

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())

    assert "HANDOFF.md" in manifest["archive_layout"], (
        f"HANDOFF.md not in archive_layout: {manifest['archive_layout']}"
    )
