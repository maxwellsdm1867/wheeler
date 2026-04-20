"""Tests for Claude Code hooks: read-before-mutate and file access tracking."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def tracking_dir(tmp_path, monkeypatch):
    """Set up a temp .wheeler/session-reads/ directory."""
    wheeler_dir = tmp_path / ".wheeler" / "session-reads"
    wheeler_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return wheeler_dir


def _run_hook(module: str, stdin_data: dict, cwd: str | Path) -> dict:
    """Run a hook module as a subprocess with JSON on stdin.

    Returns the parsed JSON response from stdout, or an empty dict
    if no JSON was produced.
    """
    result = subprocess.run(
        [sys.executable, "-m", module],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    if result.stdout.strip():
        return json.loads(result.stdout)
    return {}


class TestTrackFileAccess:
    """Tests for wheeler.hooks.track_file_access."""

    def test_tracks_read_path(self, tracking_dir, tmp_path):
        test_file = tmp_path / "data.csv"
        test_file.write_text("x,y\n1,2")

        _run_hook(
            "wheeler.hooks.track_file_access",
            {
                "session_id": "sess-001",
                "tool_name": "Read",
                "tool_input": {"file_path": str(test_file)},
            },
            cwd=tmp_path,
        )

        tracking_file = tracking_dir / "sess-001.txt"
        assert tracking_file.exists()
        lines = tracking_file.read_text().strip().splitlines()
        assert str(test_file.resolve()) in lines

    def test_tracks_write_path(self, tracking_dir, tmp_path):
        test_file = tmp_path / "output.md"

        _run_hook(
            "wheeler.hooks.track_file_access",
            {
                "session_id": "sess-002",
                "tool_name": "Write",
                "tool_input": {"file_path": str(test_file)},
            },
            cwd=tmp_path,
        )

        tracking_file = tracking_dir / "sess-002.txt"
        assert tracking_file.exists()
        lines = tracking_file.read_text().strip().splitlines()
        assert str(test_file.resolve()) in lines

    def test_no_path_no_tracking(self, tracking_dir, tmp_path):
        _run_hook(
            "wheeler.hooks.track_file_access",
            {
                "session_id": "sess-003",
                "tool_name": "Read",
                "tool_input": {},
            },
            cwd=tmp_path,
        )

        tracking_file = tracking_dir / "sess-003.txt"
        assert not tracking_file.exists()

    def test_creates_tracking_dir(self, tmp_path, monkeypatch):
        """Tracking dir is created if it doesn't exist."""
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "plan.md"
        test_file.write_text("# Plan")

        _run_hook(
            "wheeler.hooks.track_file_access",
            {
                "session_id": "sess-004",
                "tool_name": "Write",
                "tool_input": {"file_path": str(test_file)},
            },
            cwd=tmp_path,
        )

        tracking_file = tmp_path / ".wheeler" / "session-reads" / "sess-004.txt"
        assert tracking_file.exists()


class TestReadBeforeMutate:
    """Tests for wheeler.hooks.read_before_mutate."""

    def test_blocks_unread_path(self, tracking_dir, tmp_path):
        test_file = tmp_path / "plan.md"
        test_file.write_text("# Plan")

        resp = _run_hook(
            "wheeler.hooks.read_before_mutate",
            {
                "session_id": "sess-010",
                "tool_name": "mcp__wheeler_mutations__ensure_artifact",
                "tool_input": {"path": str(test_file)},
            },
            cwd=tmp_path,
        )

        assert resp["decision"] == "block"
        assert "Read or write" in resp["reason"]

    def test_allows_after_read(self, tracking_dir, tmp_path):
        test_file = tmp_path / "plan.md"
        test_file.write_text("# Plan")

        # Simulate a prior Read by writing to tracking file
        tracking_file = tracking_dir / "sess-011.txt"
        tracking_file.write_text(str(test_file.resolve()) + "\n")

        resp = _run_hook(
            "wheeler.hooks.read_before_mutate",
            {
                "session_id": "sess-011",
                "tool_name": "mcp__wheeler_mutations__ensure_artifact",
                "tool_input": {"path": str(test_file)},
            },
            cwd=tmp_path,
        )

        assert resp["decision"] == "allow"

    def test_allows_after_write(self, tracking_dir, tmp_path):
        """Write counts as having seen the file."""
        test_file = tmp_path / "plan.md"

        tracking_file = tracking_dir / "sess-012.txt"
        tracking_file.write_text(str(test_file.resolve()) + "\n")

        resp = _run_hook(
            "wheeler.hooks.read_before_mutate",
            {
                "session_id": "sess-012",
                "tool_name": "mcp__wheeler_mutations__add_plan",
                "tool_input": {"path": str(test_file), "title": "Test"},
            },
            cwd=tmp_path,
        )

        assert resp["decision"] == "allow"

    def test_allows_no_path_arg(self, tracking_dir, tmp_path):
        """Mutation with no path arg is allowed (e.g., add_plan with title only)."""
        resp = _run_hook(
            "wheeler.hooks.read_before_mutate",
            {
                "session_id": "sess-013",
                "tool_name": "mcp__wheeler_mutations__add_plan",
                "tool_input": {"title": "My Plan"},
            },
            cwd=tmp_path,
        )

        assert resp["decision"] == "allow"

    def test_allows_non_file_bearing_update(self, tracking_dir, tmp_path):
        """update_node on a Finding (F- prefix) is allowed without path."""
        resp = _run_hook(
            "wheeler.hooks.read_before_mutate",
            {
                "session_id": "sess-014",
                "tool_name": "mcp__wheeler_mutations__update_node",
                "tool_input": {"node_id": "F-3a2b", "confidence": 0.8},
            },
            cwd=tmp_path,
        )

        assert resp["decision"] == "allow"

    def test_allows_file_bearing_update_without_path(self, tracking_dir, tmp_path):
        """update_node on a Plan (PL- prefix) without path is allowed (graceful)."""
        resp = _run_hook(
            "wheeler.hooks.read_before_mutate",
            {
                "session_id": "sess-015",
                "tool_name": "mcp__wheeler_mutations__update_node",
                "tool_input": {"node_id": "PL-a1b2", "status": "completed"},
            },
            cwd=tmp_path,
        )

        assert resp["decision"] == "allow"

    def test_blocks_no_tracking_file(self, tmp_path, monkeypatch):
        """When no tracking file exists, mutations with path are blocked."""
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "data.csv"
        test_file.write_text("x,y")

        resp = _run_hook(
            "wheeler.hooks.read_before_mutate",
            {
                "session_id": "sess-016",
                "tool_name": "mcp__wheeler_mutations__add_dataset",
                "tool_input": {"path": str(test_file), "type": "csv", "description": "test"},
            },
            cwd=tmp_path,
        )

        assert resp["decision"] == "block"

    def test_invalid_stdin_allows(self, tracking_dir, tmp_path):
        """Malformed stdin is handled gracefully (allow, don't crash)."""
        result = subprocess.run(
            [sys.executable, "-m", "wheeler.hooks.read_before_mutate"],
            input="not json",
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        if result.stdout.strip():
            resp = json.loads(result.stdout)
            assert resp["decision"] == "allow"

    def test_end_to_end_track_then_mutate(self, tmp_path, monkeypatch):
        """Full flow: track_file_access records a Read, then read_before_mutate allows."""
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "plan.md"
        test_file.write_text("# Investigation Plan")

        # Step 1: track the Read
        _run_hook(
            "wheeler.hooks.track_file_access",
            {
                "session_id": "sess-e2e",
                "tool_name": "Read",
                "tool_input": {"file_path": str(test_file)},
            },
            cwd=tmp_path,
        )

        # Step 2: mutation should be allowed
        resp = _run_hook(
            "wheeler.hooks.read_before_mutate",
            {
                "session_id": "sess-e2e",
                "tool_name": "mcp__wheeler_mutations__ensure_artifact",
                "tool_input": {"path": str(test_file)},
            },
            cwd=tmp_path,
        )

        assert resp["decision"] == "allow"
