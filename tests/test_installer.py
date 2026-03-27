"""Tests for wheeler.installer module.

Uses tmp_path to avoid touching real ~/.claude/.
"""

from __future__ import annotations

import hashlib
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
    hooks = data / "hooks"
    cmds.mkdir(parents=True)
    agents.mkdir(parents=True)
    hooks.mkdir(parents=True)

    (cmds / "discuss.md").write_text("# discuss\nplaceholder")
    (cmds / "plan.md").write_text("# plan\nplaceholder")
    (agents / "wheeler-worker.md").write_text("# worker\nplaceholder")
    (hooks / "wheeler-check-update.js").write_text("// update hook")
    (hooks / "wheeler-statusline.js").write_text("// statusline hook")

    return data


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


def test_install_copies_files(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    files = installer.install()

    assert len(files) == 5
    assert (fake_home / ".claude" / "commands" / "wh" / "discuss.md").exists()
    assert (fake_home / ".claude" / "commands" / "wh" / "plan.md").exists()
    assert (fake_home / ".claude" / "agents" / "wheeler-worker.md").exists()
    assert (fake_home / ".claude" / "hooks" / "wheeler-check-update.js").exists()
    assert (fake_home / ".claude" / "hooks" / "wheeler-statusline.js").exists()


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
    assert len(manifest["files"]) == 5


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------


def test_uninstall_removes_files(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()
    removed = installer.uninstall()

    assert len(removed) == 5
    assert not (fake_home / ".claude" / "commands" / "wh" / "discuss.md").exists()
    assert not (fake_home / ".claude" / "wheeler-manifest.json").exists()


def test_uninstall_no_manifest(fake_home):
    removed = installer.uninstall()
    assert removed == []


# ---------------------------------------------------------------------------
# hook registration
# ---------------------------------------------------------------------------


def test_install_registers_session_start_hook(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()

    settings_path = fake_home / ".claude" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text())
    session_hooks = settings["hooks"]["SessionStart"]
    commands = [
        h["command"]
        for entry in session_hooks
        for h in entry.get("hooks", [])
    ]
    assert any("wheeler-check-update" in c for c in commands)


def test_install_preserves_existing_hooks(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    # Pre-existing settings with a GSD hook
    settings_path = fake_home / ".claude" / "settings.json"
    existing = {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "node gsd-check-update.js"}]}
            ]
        }
    }
    settings_path.write_text(json.dumps(existing))

    installer.install()

    settings = json.loads(settings_path.read_text())
    session_hooks = settings["hooks"]["SessionStart"]
    # Both GSD and Wheeler hooks should be present
    assert len(session_hooks) == 2
    commands = [
        h["command"]
        for entry in session_hooks
        for h in entry.get("hooks", [])
    ]
    assert any("gsd-check-update" in c for c in commands)
    assert any("wheeler-check-update" in c for c in commands)


def test_install_idempotent_hooks(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()
    installer.install()  # Second install

    settings_path = fake_home / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    session_hooks = settings["hooks"]["SessionStart"]
    wheeler_hooks = [
        entry
        for entry in session_hooks
        if any("wheeler-check-update" in h.get("command", "") for h in entry.get("hooks", []))
    ]
    # Should only have one Wheeler entry, not duplicated
    assert len(wheeler_hooks) == 1


def test_uninstall_deregisters_hooks(fake_home, fake_data, monkeypatch):
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()
    installer.uninstall()

    settings_path = fake_home / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    session_hooks = settings["hooks"]["SessionStart"]
    commands = [
        h["command"]
        for entry in session_hooks
        for h in entry.get("hooks", [])
    ]
    assert not any("wheeler-check-update" in c for c in commands)


def test_install_hooks_in_manifest(fake_home, fake_data, monkeypatch):
    """Hook .js files should appear in the manifest for uninstall tracking."""
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    files = installer.install()

    hook_keys = [k for k in files if k.endswith(".js")]
    assert len(hook_keys) == 2
    assert any("wheeler-check-update.js" in k for k in hook_keys)
    assert any("wheeler-statusline.js" in k for k in hook_keys)


def test_uninstall_removes_hook_files(fake_home, fake_data, monkeypatch):
    """Uninstall should delete .js hook files from disk."""
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()
    assert (fake_home / ".claude" / "hooks" / "wheeler-check-update.js").exists()

    installer.uninstall()
    assert not (fake_home / ".claude" / "hooks" / "wheeler-check-update.js").exists()
    assert not (fake_home / ".claude" / "hooks" / "wheeler-statusline.js").exists()


def test_register_hooks_malformed_settings(fake_home, monkeypatch):
    """Malformed settings.json should be replaced cleanly."""
    settings_path = fake_home / ".claude" / "settings.json"
    settings_path.write_text("NOT VALID JSON {{{")
    monkeypatch.setattr(installer, "INSTALL_BASE", fake_home / ".claude")

    installer._register_hooks()

    settings = json.loads(settings_path.read_text())
    assert "hooks" in settings
    assert "SessionStart" in settings["hooks"]


def test_deregister_hooks_malformed_settings(fake_home, monkeypatch):
    """Malformed settings.json should be silently ignored on deregister."""
    settings_path = fake_home / ".claude" / "settings.json"
    settings_path.write_text("NOT VALID JSON {{{")
    monkeypatch.setattr(installer, "INSTALL_BASE", fake_home / ".claude")

    # Should not raise
    installer._deregister_hooks()

    # File should be unchanged (not overwritten)
    assert settings_path.read_text() == "NOT VALID JSON {{{"


def test_deregister_hooks_no_settings_file(fake_home, monkeypatch):
    """Deregister should be a no-op if settings.json doesn't exist."""
    monkeypatch.setattr(installer, "INSTALL_BASE", fake_home / ".claude")

    # Should not raise
    installer._deregister_hooks()


def test_deregister_hooks_preserves_other_hooks(fake_home, monkeypatch):
    """Deregister should only remove wheeler hooks, not GSD or others."""
    settings_path = fake_home / ".claude" / "settings.json"
    monkeypatch.setattr(installer, "INSTALL_BASE", fake_home / ".claude")

    settings = {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "node gsd-check-update.js"}]},
                {"hooks": [{"type": "command", "command": 'node "wheeler-check-update.js"'}]},
            ]
        }
    }
    settings_path.write_text(json.dumps(settings))

    installer._deregister_hooks()

    result = json.loads(settings_path.read_text())
    session_hooks = result["hooks"]["SessionStart"]
    assert len(session_hooks) == 1
    assert "gsd-check-update" in session_hooks[0]["hooks"][0]["command"]


# ---------------------------------------------------------------------------
# _detect_install_source
# ---------------------------------------------------------------------------


def test_detect_editable_install(monkeypatch):
    """Detect editable install from 'Editable project location' line."""
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = (
                "Name: wheeler\n"
                "Version: 0.2.0\n"
                "Editable project location: /home/user/wheeler\n"
                "Location: /home/user/wheeler\n"
            )
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    assert installer._detect_install_source() == "editable"


def test_detect_pypi_install(monkeypatch):
    """Standard pip install should return 'pypi'."""
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = (
                "Name: wheeler\n"
                "Version: 0.2.0\n"
                "Location: /usr/lib/python3/site-packages\n"
            )
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    assert installer._detect_install_source() == "pypi"


def test_detect_install_source_pip_fails(monkeypatch):
    """Fallback to 'pypi' when pip show fails."""
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    assert installer._detect_install_source() == "pypi"


def test_detect_install_source_timeout(monkeypatch):
    """Fallback to 'pypi' when pip show times out."""
    import subprocess as sp

    def fake_run(*args, **kwargs):
        raise sp.TimeoutExpired(cmd="pip show", timeout=10)

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    assert installer._detect_install_source() == "pypi"


# ---------------------------------------------------------------------------
# _check_github_latest / _check_pypi_latest implementations
# ---------------------------------------------------------------------------


def test_check_github_strips_v_prefix(monkeypatch):
    """GitHub tag 'v1.2.3' should return '1.2.3'."""
    import io

    class FakeResp:
        def read(self):
            return json.dumps({"tag_name": "v1.2.3"}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        installer.urllib.request, "urlopen", lambda *a, **kw: FakeResp()
    )
    assert installer._check_github_latest() == "1.2.3"


def test_check_github_no_v_prefix(monkeypatch):
    """GitHub tag '1.2.3' (no v) should return '1.2.3'."""
    class FakeResp:
        def read(self):
            return json.dumps({"tag_name": "1.2.3"}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        installer.urllib.request, "urlopen", lambda *a, **kw: FakeResp()
    )
    assert installer._check_github_latest() == "1.2.3"


def test_check_github_empty_tag(monkeypatch):
    """Empty tag_name should return None."""
    class FakeResp:
        def read(self):
            return json.dumps({"tag_name": ""}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        installer.urllib.request, "urlopen", lambda *a, **kw: FakeResp()
    )
    assert installer._check_github_latest() is None


def test_check_github_missing_tag_key(monkeypatch):
    """Response without tag_name should return None."""
    class FakeResp:
        def read(self):
            return json.dumps({"message": "Not Found"}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        installer.urllib.request, "urlopen", lambda *a, **kw: FakeResp()
    )
    assert installer._check_github_latest() is None


def test_check_github_network_error(monkeypatch):
    """Network error should return None, not raise."""
    monkeypatch.setattr(
        installer.urllib.request,
        "urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(urllib_error_for_test()),
    )
    assert installer._check_github_latest() is None


def urllib_error_for_test():
    return installer.urllib.error.URLError("Network unreachable")


def test_check_pypi_parses_output(monkeypatch):
    """PyPI check should parse pip index output format."""
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = "wheeler (1.5.0)\n  Available versions: 1.5.0, 1.4.0\n"
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    assert installer._check_pypi_latest() == "1.5.0"


def test_check_pypi_no_match(monkeypatch):
    """Unexpected pip output should return None."""
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = "some unexpected output\n"
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    assert installer._check_pypi_latest() is None


def test_check_pypi_failure(monkeypatch):
    """pip failure should return None."""
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    assert installer._check_pypi_latest() is None


# ---------------------------------------------------------------------------
# _find_repo_root
# ---------------------------------------------------------------------------


def test_find_repo_root_via_git(monkeypatch):
    """Should use git rev-parse output when available."""
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = "/home/user/wheeler\n"
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    assert installer._find_repo_root() == Path("/home/user/wheeler")


def test_find_repo_root_fallback(tmp_path, monkeypatch):
    """Should walk up directories looking for .claude/commands/wh/."""
    # Create marker directory
    (tmp_path / ".claude" / "commands" / "wh").mkdir(parents=True)

    def fake_run(*args, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path / "sub" / "deep"))
    # cwd doesn't exist but its parents include tmp_path
    # Actually we need cwd to be under tmp_path for parent walk
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    monkeypatch.setattr(Path, "cwd", staticmethod(lambda: sub))

    assert installer._find_repo_root() == tmp_path


def test_find_repo_root_not_found(tmp_path, monkeypatch):
    """Should raise FileNotFoundError if no root found."""
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))

    with pytest.raises(FileNotFoundError, match="Cannot find repository root"):
        installer._find_repo_root()


# ---------------------------------------------------------------------------
# version cache edge cases
# ---------------------------------------------------------------------------


def test_version_cache_corrupt_json(tmp_path, monkeypatch):
    """Corrupt cache file should return None."""
    cache_path = tmp_path / "version-check.json"
    cache_path.write_text("NOT JSON {{")
    monkeypatch.setattr(installer, "VERSION_CACHE_PATH", cache_path)

    assert installer._read_version_cache() is None


def test_check_version_cached_ignores_wrong_installed(tmp_path, monkeypatch):
    """Cache for a different installed version should be treated as stale."""
    cache_path = tmp_path / "version-check.json"
    monkeypatch.setattr(installer, "VERSION_CACHE_PATH", cache_path)

    # Cache was written for a different installed version
    installer._write_version_cache("0.1.0", "0.3.0", True)

    monkeypatch.setattr(installer, "_check_github_latest", lambda: "99.0.0")
    monkeypatch.setattr(installer, "_check_pypi_latest", lambda: None)

    installed, latest, _ = installer.check_version_cached()
    # Should have done a fresh check, not returned stale cache
    assert latest == "99.0.0"


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


def test_check_version_current_github(monkeypatch):
    """GitHub reports same version — no update available."""
    monkeypatch.setattr(
        installer, "_check_github_latest", lambda: wheeler.__version__
    )
    monkeypatch.setattr(installer, "_check_pypi_latest", lambda: None)

    installed, latest, update_available = installer.check_version()
    assert installed == wheeler.__version__
    assert latest == wheeler.__version__
    assert update_available is False


def test_check_version_update_available_github(monkeypatch):
    """GitHub reports newer version."""
    monkeypatch.setattr(installer, "_check_github_latest", lambda: "99.0.0")
    monkeypatch.setattr(installer, "_check_pypi_latest", lambda: None)

    installed, latest, update_available = installer.check_version()
    assert installed == wheeler.__version__
    assert latest == "99.0.0"
    assert update_available is True


def test_check_version_falls_back_to_pypi(monkeypatch):
    """When GitHub fails, falls back to PyPI."""
    monkeypatch.setattr(installer, "_check_github_latest", lambda: None)
    monkeypatch.setattr(installer, "_check_pypi_latest", lambda: "99.0.0")

    installed, latest, update_available = installer.check_version()
    assert latest == "99.0.0"
    assert update_available is True


def test_check_version_both_unreachable(monkeypatch):
    """When both GitHub and PyPI fail."""
    monkeypatch.setattr(installer, "_check_github_latest", lambda: None)
    monkeypatch.setattr(installer, "_check_pypi_latest", lambda: None)

    installed, latest, update_available = installer.check_version()
    assert installed == wheeler.__version__
    assert latest is None
    assert update_available is False


# ---------------------------------------------------------------------------
# _compare_versions
# ---------------------------------------------------------------------------


def test_compare_versions_newer():
    assert installer._compare_versions("0.2.0", "0.3.0") is True


def test_compare_versions_same():
    assert installer._compare_versions("0.2.0", "0.2.0") is False


def test_compare_versions_older():
    assert installer._compare_versions("0.3.0", "0.2.0") is False


def test_compare_versions_major():
    assert installer._compare_versions("0.2.0", "1.0.0") is True


# ---------------------------------------------------------------------------
# version cache
# ---------------------------------------------------------------------------


def test_version_cache_roundtrip(tmp_path, monkeypatch):
    cache_path = tmp_path / "version-check.json"
    monkeypatch.setattr(installer, "VERSION_CACHE_PATH", cache_path)

    installer._write_version_cache("0.2.0", "0.3.0", True)
    cache = installer._read_version_cache()

    assert cache is not None
    assert cache["installed"] == "0.2.0"
    assert cache["latest"] == "0.3.0"
    assert cache["update_available"] is True
    assert "checked_at" in cache


def test_version_cache_missing(tmp_path, monkeypatch):
    cache_path = tmp_path / "nonexistent" / "version-check.json"
    monkeypatch.setattr(installer, "VERSION_CACHE_PATH", cache_path)

    assert installer._read_version_cache() is None


def test_check_version_cached_uses_cache(tmp_path, monkeypatch):
    """Cached check should return cached result without hitting network."""
    cache_path = tmp_path / "version-check.json"
    monkeypatch.setattr(installer, "VERSION_CACHE_PATH", cache_path)

    # Write a fresh cache
    installer._write_version_cache(wheeler.__version__, "99.0.0", True)

    # These should NOT be called if cache is fresh
    call_count = {"github": 0, "pypi": 0}

    def no_github():
        call_count["github"] += 1
        return None

    def no_pypi():
        call_count["pypi"] += 1
        return None

    monkeypatch.setattr(installer, "_check_github_latest", no_github)
    monkeypatch.setattr(installer, "_check_pypi_latest", no_pypi)

    installed, latest, update_available = installer.check_version_cached()

    assert installed == wheeler.__version__
    assert latest == "99.0.0"
    assert update_available is True
    assert call_count["github"] == 0
    assert call_count["pypi"] == 0


def test_check_version_cached_stale_cache(tmp_path, monkeypatch):
    """Stale cache should trigger a fresh network check."""
    cache_path = tmp_path / "version-check.json"
    monkeypatch.setattr(installer, "VERSION_CACHE_PATH", cache_path)

    # Write a stale cache (checked_at far in the past)
    cache = {
        "installed": wheeler.__version__,
        "latest": "0.1.0",
        "update_available": False,
        "checked_at": "2020-01-01T00:00:00+00:00",
    }
    cache_path.write_text(json.dumps(cache))

    monkeypatch.setattr(installer, "_check_github_latest", lambda: "99.0.0")
    monkeypatch.setattr(installer, "_check_pypi_latest", lambda: None)

    installed, latest, update_available = installer.check_version_cached()

    assert latest == "99.0.0"
    assert update_available is True


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


# ---------------------------------------------------------------------------
# package data sync guard
# ---------------------------------------------------------------------------


def test_package_data_in_sync():
    """Fail if .claude/commands/wh/ and wheeler/_data/commands/ diverge.

    This prevents shipping a package where the dev commands were updated
    but sync_data() was never run (or its output never committed).
    """
    repo_root = Path(__file__).resolve().parent.parent
    dev_dir = repo_root / ".claude" / "commands" / "wh"
    pkg_dir = repo_root / "wheeler" / "_data" / "commands"

    if not dev_dir.is_dir() or not pkg_dir.is_dir():
        pytest.skip("Not running from a dev checkout")

    dev_files = {f.name for f in dev_dir.glob("*.md")}
    pkg_files = {f.name for f in pkg_dir.glob("*.md")}

    # Every dev command must exist in package data
    missing = dev_files - pkg_files
    assert not missing, (
        f"Commands in .claude/commands/wh/ but not in wheeler/_data/commands/: {missing}\n"
        f"Run: python -c \"from wheeler.installer import sync_data; sync_data()\""
    )

    # Content must match (no stale copies)
    stale = []
    for name in dev_files & pkg_files:
        dev_hash = hashlib.sha256((dev_dir / name).read_bytes()).hexdigest()
        pkg_hash = hashlib.sha256((pkg_dir / name).read_bytes()).hexdigest()
        if dev_hash != pkg_hash:
            stale.append(name)
    assert not stale, (
        f"Commands out of sync between dev and package data: {stale}\n"
        f"Run: python -c \"from wheeler.installer import sync_data; sync_data()\""
    )

    # Also check agents
    dev_agents = repo_root / ".claude" / "agents"
    pkg_agents = repo_root / "wheeler" / "_data" / "agents"
    if dev_agents.is_dir() and pkg_agents.is_dir():
        dev_a = {f.name for f in dev_agents.glob("wheeler-*.md")}
        pkg_a = {f.name for f in pkg_agents.glob("wheeler-*.md")}
        missing_a = dev_a - pkg_a
        assert not missing_a, (
            f"Agents in .claude/agents/ but not in wheeler/_data/agents/: {missing_a}\n"
            f"Run: python -c \"from wheeler.installer import sync_data; sync_data()\""
        )


def test_mcp_merge_no_template(tmp_path, monkeypatch):
    """If no template exists, merge should be a no-op."""
    data = tmp_path / "_data"
    data.mkdir()
    monkeypatch.setattr(installer, "_get_data_path", lambda: data)

    project = tmp_path / "project"
    project.mkdir()

    installer.merge_mcp_config(project_dir=project)

    assert not (project / ".mcp.json").exists()
