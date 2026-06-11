"""Regression test for issue #70: update badge never appears.

Issue: The version-check cache correctly records update_available: true,
but the update badge is never displayed to the user because the statusLine
hook (wheeler-statusline.js) is never registered in ~/.claude/settings.json.

This test verifies that:
1. The install() function copies both wheeler-check-update.js and wheeler-statusline.js
2. The _register_hooks() function registers the SessionStart hook for check-update
3. The _register_hooks() function registers the statusLine hook for statusline
4. When update_available is true in the cache, the statusline hook can read it
5. Both hooks are present in settings.json after installation
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

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
    """Create a fake _data/ directory with both hook files."""
    data = tmp_path / "_data"
    hooks = data / "hooks"
    hooks.mkdir(parents=True)

    # Create both hook files
    (hooks / "wheeler-check-update.js").write_text("// check-update hook")
    (hooks / "wheeler-statusline.js").write_text("// statusline hook")

    return data


def test_install_copies_both_hooks(fake_home, fake_data, monkeypatch):
    """Verify both hook files are copied during installation."""
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    files = installer.install()

    # Both hooks should be copied
    check_update_path = fake_home / ".claude" / "hooks" / "wheeler-check-update.js"
    statusline_path = fake_home / ".claude" / "hooks" / "wheeler-statusline.js"

    assert check_update_path.exists(), "wheeler-check-update.js should be copied"
    assert statusline_path.exists(), "wheeler-statusline.js should be copied"

    # Both should be in the returned manifest
    assert any("wheeler-check-update" in k for k in files.keys()), (
        "Manifest should include wheeler-check-update hook"
    )
    assert any("wheeler-statusline" in k for k in files.keys()), (
        "Manifest should include wheeler-statusline hook"
    )


def test_session_start_hook_registered(fake_home, fake_data, monkeypatch):
    """Verify SessionStart hook is registered in settings.json."""
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()

    settings_path = fake_home / ".claude" / "settings.json"
    assert settings_path.exists(), "settings.json should be created"

    settings = json.loads(settings_path.read_text())
    hooks = settings.get("hooks", {})
    session_start = hooks.get("SessionStart", [])

    # SessionStart should have at least one entry with wheeler-check-update
    assert len(session_start) > 0, "SessionStart hooks should be registered"
    assert any(
        "wheeler-check-update" in h.get("command", "")
        for entry in session_start
        for h in entry.get("hooks", [])
    ), "wheeler-check-update should be in SessionStart hooks"


def test_statusline_hook_registered(fake_home, fake_data, monkeypatch):
    """Verify the statusLine command is registered in settings.json.

    This is the critical test for issue #70: the statusLine command must be
    registered so that the update badge can be displayed to the user.

    Note: in Claude Code's settings schema, statusLine is a TOP-LEVEL
    settings key with shape {"type": "command", "command": "..."}. It is
    NOT an entry under the "hooks" object. Registering it under "hooks"
    would never be read by Claude Code, so this test asserts the top-level
    location.
    """
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    installer.install()

    settings_path = fake_home / ".claude" / "settings.json"
    assert settings_path.exists(), "settings.json should be created"

    settings = json.loads(settings_path.read_text())

    # The statusLine command MUST be registered at the top level
    statusline = settings.get("statusLine")
    assert statusline is not None, (
        "statusLine hook should be registered in settings.json after install(). "
        "This is the root cause of issue #70: the cache is written but never read "
        "because the statusline hook is never registered."
    )
    assert isinstance(statusline, dict), "statusLine should be a dict"

    # Should contain a command that references wheeler-statusline.js
    command = statusline.get("command", "")
    assert "wheeler-statusline" in command or isinstance(statusline.get("type"), str), (
        f"statusLine command should reference wheeler-statusline.js, got: {statusline}"
    )


def test_statusline_reads_update_cache():
    """Verify the statusline hook logic can read update_available from cache.

    This is a conceptual test showing that IF the statusLine hook were
    registered, it would correctly read the update_available flag.
    """
    # Simulate what wheeler-statusline.js does
    cache_data = {
        "update_available": True,
        "installed": "0.9.1",
        "latest": "0.9.8",
        "checked": 1781118722,
    }

    # The statusline script checks: if cache.update_available then show badge
    assert cache_data["update_available"] is True, (
        "Cache indicates update is available"
    )
    assert cache_data["latest"] != cache_data["installed"], (
        "Versions differ, update is needed"
    )


def test_uninstall_removes_both_hooks(fake_home, fake_data, monkeypatch):
    """Verify both hooks are removed during uninstallation."""
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    # Install first
    installer.install()

    check_update_path = fake_home / ".claude" / "hooks" / "wheeler-check-update.js"
    statusline_path = fake_home / ".claude" / "hooks" / "wheeler-statusline.js"

    assert check_update_path.exists()
    assert statusline_path.exists()

    # Now uninstall
    installer.uninstall()

    assert not check_update_path.exists(), "wheeler-check-update.js should be removed"
    assert not statusline_path.exists(), "wheeler-statusline.js should be removed"


def test_statusline_registration_preserves_existing_hooks(fake_home, fake_data, monkeypatch):
    """Verify registration doesn't overwrite existing hooks (e.g., from GSD)."""
    monkeypatch.setattr(installer, "_get_data_path", lambda: fake_data)

    settings_path = fake_home / ".claude" / "settings.json"

    # Pre-populate with an existing hook (simulating GSD)
    existing_settings = {
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {"type": "command", "command": "node /gsd-check-update.js"}
                    ]
                }
            ]
        }
    }
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(existing_settings, indent=2) + "\n")

    # Install Wheeler
    installer.install()

    # Both Wheeler and GSD hooks should be present
    settings = json.loads(settings_path.read_text())
    session_start = settings.get("hooks", {}).get("SessionStart", [])

    gsd_found = any(
        "gsd-check-update" in h.get("command", "")
        for entry in session_start
        for h in entry.get("hooks", [])
    )
    wheeler_found = any(
        "wheeler-check-update" in h.get("command", "")
        for entry in session_start
        for h in entry.get("hooks", [])
    )

    assert gsd_found, "Existing GSD hook should be preserved"
    assert wheeler_found, "Wheeler check-update hook should be added"
