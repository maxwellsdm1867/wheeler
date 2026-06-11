"""Regression test for issue #69: wheeler update fails on uv tool installs.

The update command must detect uv-managed tool installs and use uv to upgrade,
not pip (which is not available in uv tool venvs).

All tests here assert EXPECTED FIXED behavior. On main (before fix), the
uv-path tests will FAIL. The pip-path test may PASS as baseline confirmation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import wheeler
import wheeler.installer as installer


@pytest.fixture()
def fake_home(tmp_path, monkeypatch):
    """Override Path.home() to use tmp_path."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(installer, "INSTALL_BASE", claude_dir)
    monkeypatch.setattr(installer, "MANIFEST_PATH", claude_dir / "wheeler-manifest.json")
    return home


def test_detect_install_source_returns_uv_when_executable_is_in_uv_tools_path(monkeypatch):
    """After fix: _detect_install_source() returns 'uv' when sys.executable is in ~/.local/share/uv/tools/.

    This is the primary signal for a uv tool install. When the Python executable
    is at ~/.local/share/uv/tools/wheeler/bin/python, the installer knows to use
    'uv tool upgrade'.

    Expected behavior after fix: returns 'uv'
    Current behavior on main: returns 'github' (FAIL)
    """
    # Simulate sys.executable pointing to a uv tool venv
    uv_tool_python = Path.home() / ".local" / "share" / "uv" / "tools" / "wheeler" / "bin" / "python"

    monkeypatch.setattr(sys, "executable", str(uv_tool_python))

    # Mock subprocess.run so pip show doesn't actually run
    def fake_run(cmd, *args, **kwargs):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        return result

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    # After fix, should detect uv from the executable path
    detected = installer._detect_install_source()
    assert detected == "uv", (
        f"Expected 'uv' but got '{detected}'. "
        f"sys.executable={sys.executable} should signal uv tool install."
    )


def test_detect_install_source_returns_uv_when_pip_unavailable_and_uv_available(monkeypatch):
    """After fix: _detect_install_source() returns 'uv' when pip fails and uv is on PATH.

    When pip is not available (pip show fails) but 'uv' command is available on
    the system PATH, the installer should infer a uv tool install and return 'uv'.

    Expected behavior after fix: returns 'uv'
    Current behavior on main: returns 'github' (FAIL)
    """
    call_log = []

    def fake_run(cmd, *args, **kwargs):
        call_log.append(cmd)
        if isinstance(cmd, list):
            cmd_str = " ".join(str(c) for c in cmd)
        else:
            cmd_str = str(cmd)

        # pip show fails (pip not available in uv tool venv)
        if "pip" in cmd_str and "show" in cmd_str:
            result = MagicMock()
            result.returncode = 1
            result.stdout = ""
            return result

        result = MagicMock()
        result.returncode = 0
        return result

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    # Mock shutil.which to report uv is available
    def fake_which(cmd):
        if cmd == "uv":
            return "/usr/local/bin/uv"
        return None

    monkeypatch.setattr(installer.shutil, "which", fake_which)

    # After fix: should detect uv when pip fails but uv is available
    detected = installer._detect_install_source()
    assert detected == "uv", (
        f"Expected 'uv' but got '{detected}'. "
        f"When pip unavailable but uv available, should return 'uv'."
    )


def test_update_with_uv_source_uses_uv_tool_upgrade(monkeypatch, fake_home):
    """After fix: update(source='uv') runs 'uv tool upgrade wheeler' via subprocess.

    When the installer detects or is told source='uv', it must invoke
    'uv tool upgrade wheeler', NOT 'python -m pip install'.

    This test captures the subprocess call log and verifies the correct command
    is used for uv-managed installs.

    Expected: calls uv tool upgrade, does NOT call python -m pip
    Current on main: pip path will be taken, subprocess.CalledProcessError raised (FAIL)
    """
    call_log = []

    def fake_run(cmd, *args, **kwargs):
        call_log.append(cmd)

        if isinstance(cmd, list):
            cmd_str = " ".join(str(c) for c in cmd)
        else:
            cmd_str = str(cmd)

        # uv tool upgrade should succeed
        if "uv" in cmd_str and "tool" in cmd_str and "upgrade" in cmd_str:
            result = MagicMock()
            result.returncode = 0
            return result

        # If pip is invoked, that's wrong for uv path
        if "pip" in cmd_str and "install" in cmd_str:
            raise subprocess.CalledProcessError(1, cmd)

        result = MagicMock()
        result.returncode = 0
        return result

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    # Create minimal manifest
    manifest_path = fake_home / ".claude" / "wheeler-manifest.json"
    manifest_path.write_text(json.dumps({"version": "0.9.1", "files": {}}))

    with patch.object(installer, "install"):
        # After fix: this should succeed
        result = installer.update(source="uv")

    # Verify the call log contains uv tool upgrade, not pip
    uv_calls = [c for c in call_log if isinstance(c, list) and "uv" in str(c)]
    pip_calls = [c for c in call_log if isinstance(c, list) and "pip" in str(c) and "install" in str(c)]

    assert len(uv_calls) > 0, (
        f"Expected 'uv tool upgrade' call in subprocess log, but got none. "
        f"Call log: {call_log}"
    )
    assert len(pip_calls) == 0, (
        f"Expected NO pip install calls for source='uv', but got {len(pip_calls)}. "
        f"Call log: {call_log}"
    )


def test_update_with_github_source_uses_pip_unchanged(monkeypatch, fake_home):
    """Baseline: update(source='github') still uses pip for traditional installs.

    This test confirms that pip-based upgrade paths are NOT broken by the fix.
    When pip IS available and source='github' or source='pypi', the code should
    continue to use pip as before.

    Expected: calls python -m pip install --upgrade
    This test may PASS on main (baseline) and should still PASS after fix.
    """
    call_log = []

    def fake_run(cmd, *args, **kwargs):
        call_log.append(cmd)

        if isinstance(cmd, list):
            cmd_str = " ".join(str(c) for c in cmd)
        else:
            cmd_str = str(cmd)

        # pip show succeeds (normal pip install)
        if "pip" in cmd_str and "show" in cmd_str:
            result = MagicMock()
            result.returncode = 0
            result.stdout = "Name: wheeler\nLocation: /usr/lib/python3/site-packages\n"
            return result

        # pip install --upgrade succeeds
        if "pip" in cmd_str and "install" in cmd_str and "upgrade" in cmd_str:
            result = MagicMock()
            result.returncode = 0
            return result

        result = MagicMock()
        result.returncode = 0
        return result

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    # Create minimal manifest
    manifest_path = fake_home / ".claude" / "wheeler-manifest.json"
    manifest_path.write_text(json.dumps({"version": "0.9.1", "files": {}}))

    with patch.object(installer, "install"):
        # Should succeed using pip
        result = installer.update(source="github")

    # Verify pip install --upgrade was called
    pip_upgrade_calls = [
        c for c in call_log
        if isinstance(c, list) and "pip" in str(c) and "upgrade" in str(c)
    ]

    assert len(pip_upgrade_calls) > 0, (
        f"Expected 'pip install --upgrade' call for source='github', but got none. "
        f"Call log: {call_log}"
    )


def test_issue_69_end_to_end_uv_scenario(monkeypatch, fake_home):
    """Integration test: reproduce the exact scenario from issue #69.

    Setup: Python is in a uv tool venv (no pip), uv is available on PATH.
    Action: Call update() with auto-detection.
    Expected after fix:
      - _detect_install_source() returns 'uv'
      - update() calls 'uv tool upgrade wheeler' (not pip)
      - No CalledProcessError is raised
      - Version is reloaded and returned

    Current on main: FAILS with CalledProcessError("No module named pip")
    """
    call_log = []

    # Simulate sys.executable in uv tool venv
    uv_tool_python = Path.home() / ".local" / "share" / "uv" / "tools" / "wheeler" / "bin" / "python"
    monkeypatch.setattr(sys, "executable", str(uv_tool_python))

    def fake_run(cmd, *args, **kwargs):
        call_log.append(cmd)

        if isinstance(cmd, list):
            cmd_str = " ".join(str(c) for c in cmd)
        else:
            cmd_str = str(cmd)

        # pip show fails (no pip in uv tool venv)
        if "pip" in cmd_str and "show" in cmd_str:
            result = MagicMock()
            result.returncode = 1
            return result

        # uv tool upgrade succeeds
        if "uv" in cmd_str and "tool" in cmd_str and "upgrade" in cmd_str:
            result = MagicMock()
            result.returncode = 0
            return result

        # If pip install is called, that's the bug
        if "pip" in cmd_str and "install" in cmd_str:
            raise subprocess.CalledProcessError(
                1,
                cmd,
                output="No module named pip"
            )

        result = MagicMock()
        result.returncode = 0
        return result

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    # Mock shutil.which to report uv is available
    def fake_which(cmd):
        if cmd == "uv":
            return "/usr/local/bin/uv"
        return None

    monkeypatch.setattr(installer.shutil, "which", fake_which)

    # Create minimal manifest
    manifest_path = fake_home / ".claude" / "wheeler-manifest.json"
    manifest_path.write_text(json.dumps({"version": "0.9.1", "files": {}}))

    with patch.object(installer, "install"):
        # After fix: should succeed without raising CalledProcessError
        result = installer.update()  # Auto-detect should find 'uv'

    # Verify uv was used, not pip
    uv_calls = [c for c in call_log if isinstance(c, list) and "uv" in str(c)]
    pip_install_calls = [
        c for c in call_log
        if isinstance(c, list) and "pip" in str(c) and "install" in str(c)
    ]

    assert len(uv_calls) > 0, (
        f"Expected 'uv tool upgrade' but got call log: {call_log}"
    )
    assert len(pip_install_calls) == 0, (
        f"Expected NO 'pip install' for uv scenario, but got: {pip_install_calls}"
    )
