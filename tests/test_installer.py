"""Tests for wheeler.installer module.

Uses tmp_path to avoid touching real ~/.claude/.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import wheeler
import wheeler.installer as installer


@pytest.fixture()
def fake_home(tmp_path, monkeypatch):
    """Override Path.home() and INSTALL_BASE/MANIFEST_PATH to use tmp_path."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(installer, "INSTALL_BASE", claude_dir)
    monkeypatch.setattr(installer, "MANIFEST_PATH", claude_dir / "wheeler-manifest.json")
    return home


@pytest.fixture()
def fake_data(tmp_path):
    """Create a fake _data/ directory with sample files."""
    data = tmp_path / "_data"
    cmds = data / "commands"
    agents = data / "agents"
    cmds.mkdir(parents=True)
    agents.mkdir(parents=True)

    (cmds / "discuss.md").write_text("# discuss\nplaceholder")
    (cmds / "plan.md").write_text("# plan\nplaceholder")
    (agents / "wheeler-worker.md").write_text("# worker\nplaceholder")

    return data


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


def test_install_copies_files(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    files = installer.install()

    assert len(files) == 3
    assert (fake_home / ".claude" / "commands" / "wh" / "discuss.md").exists()
    assert (fake_home / ".claude" / "commands" / "wh" / "plan.md").exists()
    assert (fake_home / ".claude" / "agents" / "wheeler-worker.md").exists()


def test_install_symlinks(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install(link=True)

    dst = fake_home / ".claude" / "commands" / "wh" / "discuss.md"
    assert dst.is_symlink()


def test_install_writes_manifest(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()

    manifest_path = fake_home / ".claude" / "wheeler-manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert "version" in manifest
    assert "installed_at" in manifest
    assert "files" in manifest
    assert len(manifest["files"]) == 3


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------


def test_uninstall_removes_files(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()
    removed = installer.uninstall()

    assert len(removed) == 3
    assert not (fake_home / ".claude" / "commands" / "wh" / "discuss.md").exists()
    assert not (fake_home / ".claude" / "wheeler-manifest.json").exists()


def test_uninstall_no_manifest(fake_home):
    removed = installer.uninstall()
    assert removed == []


# ---------------------------------------------------------------------------
# manifest roundtrip
# ---------------------------------------------------------------------------


def test_manifest_roundtrip(fake_home):
    files = {"commands/wh/discuss.md": "abc123", "agents/worker.md": "def456"}
    installer.write_manifest(files)

    manifest = installer.read_manifest()
    assert manifest is not None
    assert manifest["files"] == files
    assert manifest["version"] == wheeler.__version__


def test_read_manifest_missing(fake_home):
    assert installer.read_manifest() is None


# ---------------------------------------------------------------------------
# backup_local_mods
# ---------------------------------------------------------------------------


def test_backup_local_mods(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()

    # Modify an installed file
    modified = fake_home / ".claude" / "commands" / "wh" / "discuss.md"
    modified.write_text("# modified locally")

    backed = installer.backup_local_mods()
    assert len(backed) == 1
    assert "commands/wh/discuss.md" in backed[0]

    # Verify backup directory was created
    patches = fake_home / ".claude" / "wheeler-patches"
    assert patches.exists()


def test_backup_no_mods(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()
    backed = installer.backup_local_mods()
    assert backed == []


# ---------------------------------------------------------------------------
# sync_data
# ---------------------------------------------------------------------------


def test_sync_data(tmp_path, monkeypatch):
    # Create fake repo with .claude/commands/wh/ and .claude/agents/
    repo = tmp_path / "repo"
    (repo / ".claude" / "commands" / "wh").mkdir(parents=True)
    (repo / ".claude" / "agents").mkdir(parents=True)
    (repo / ".claude" / "commands" / "wh" / "discuss.md").write_text("# new version")
    (repo / ".claude" / "agents" / "wheeler-worker.md").write_text("# new agent")

    # Create fake _data with stale content
    data = tmp_path / "_data"
    (data / "commands").mkdir(parents=True)
    (data / "agents").mkdir(parents=True)
    (data / "commands" / "discuss.md").write_text("# old version")

    monkeypatch.setattr(installer, "_get_data_path", lambda: data)

    changed = installer.sync_data(repo_root=repo)
    assert len(changed) >= 1
    # Verify content was synced
    assert (data / "commands" / "discuss.md").read_text() == "# new version"
    assert (data / "agents" / "wheeler-worker.md").read_text() == "# new agent"


def test_sync_data_already_in_sync(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".claude" / "commands" / "wh").mkdir(parents=True)
    content = "# same"
    (repo / ".claude" / "commands" / "wh" / "discuss.md").write_text(content)

    data = tmp_path / "_data"
    (data / "commands").mkdir(parents=True)
    (data / "commands" / "discuss.md").write_text(content)

    monkeypatch.setattr(installer, "_get_data_path", lambda: data)

    changed = installer.sync_data(repo_root=repo)
    assert changed == []


# ---------------------------------------------------------------------------
# check_version
# ---------------------------------------------------------------------------


def test_check_version_current(monkeypatch):
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = f"wheeler ({wheeler.__version__})\n"
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    installed, latest, update_available = installer.check_version()
    assert installed == wheeler.__version__
    assert latest == wheeler.__version__
    assert update_available is False


def test_check_version_update_available(monkeypatch):
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = "wheeler (99.0.0)\n"
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    installed, latest, update_available = installer.check_version()
    assert installed == wheeler.__version__
    assert latest == "99.0.0"
    assert update_available is True


def test_check_version_pypi_unreachable(monkeypatch):
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    installed, latest, update_available = installer.check_version()
    assert installed == wheeler.__version__
    assert latest is None
    assert update_available is False


# ---------------------------------------------------------------------------
# merge_mcp_config
# ---------------------------------------------------------------------------


def test_mcp_merge_fresh(tmp_path, monkeypatch):
    """Merge into a project with no existing .mcp.json."""
    data = tmp_path / "_data"
    data.mkdir()
    template = {
        "mcpServers": {
            "wheeler": {"type": "stdio", "command": "wheeler-mcp"},
            "neo4j": {"type": "stdio", "command": "neo4j-mcp"},
        }
    }
    (data / "mcp.json").write_text(json.dumps(template))
    monkeypatch.setattr(installer, "_get_data_path", lambda: data)

    project = tmp_path / "project"
    project.mkdir()

    installer.merge_mcp_config(project_dir=project)

    result = json.loads((project / ".mcp.json").read_text())
    assert "wheeler" in result["mcpServers"]
    assert "neo4j" in result["mcpServers"]


def test_mcp_merge_preserves_existing(tmp_path, monkeypatch):
    """Merge should not overwrite user-customized entries."""
    data = tmp_path / "_data"
    data.mkdir()
    template = {
        "mcpServers": {
            "wheeler": {"type": "stdio", "command": "wheeler-mcp"},
            "neo4j": {"type": "stdio", "command": "default-neo4j"},
        }
    }
    (data / "mcp.json").write_text(json.dumps(template))
    monkeypatch.setattr(installer, "_get_data_path", lambda: data)

    project = tmp_path / "project"
    project.mkdir()
    existing = {
        "mcpServers": {
            "neo4j": {"type": "stdio", "command": "custom-neo4j", "env": {"DB": "custom"}},
            "other-tool": {"type": "stdio", "command": "other"},
        }
    }
    (project / ".mcp.json").write_text(json.dumps(existing))

    installer.merge_mcp_config(project_dir=project)

    result = json.loads((project / ".mcp.json").read_text())
    # Existing neo4j config should be preserved (not overwritten)
    assert result["mcpServers"]["neo4j"]["command"] == "custom-neo4j"
    # Wheeler should be added
    assert "wheeler" in result["mcpServers"]
    # Other tools should be preserved
    assert "other-tool" in result["mcpServers"]


def test_mcp_merge_no_template(tmp_path, monkeypatch):
    """If no template exists, merge should be a no-op."""
    data = tmp_path / "_data"
    data.mkdir()
    monkeypatch.setattr(installer, "_get_data_path", lambda: data)

    project = tmp_path / "project"
    project.mkdir()

    installer.merge_mcp_config(project_dir=project)

    assert not (project / ".mcp.json").exists()
