"""Tests for wheeler.log_summary module."""

import json
import pytest
from datetime import datetime, timezone

from wheeler.log_summary import summarize_logs


def _make_log(tmp_path, filename, **overrides):
    """Create a structured log file."""
    entry = {
        "task_id": "T-20260303-143000",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_description": "Test task",
        "status": "completed",
        "model": "sonnet",
        "duration_seconds": 30,
        "checkpoint_flags": [],
        "result": "Found [F-3a2b] in the data",
        "citation_validation": {
            "total": 1,
            "valid": 1,
            "invalid": [],
            "stale": [],
            "missing_provenance": [],
            "pass_rate": 1.0,
        },
        "token_usage": {},
    }
    entry.update(overrides)
    path = tmp_path / filename
    path.write_text(json.dumps(entry))
    return path


class TestSummarizeLogs:
    def test_empty_dir(self, tmp_path):
        result = summarize_logs(str(tmp_path))
        assert result == ""

    def test_nonexistent_dir(self):
        result = summarize_logs("/nonexistent/path")
        assert result == ""

    def test_completed_task(self, tmp_path):
        _make_log(tmp_path, "20260303-143000-queue.json")
        result = summarize_logs(str(tmp_path))
        assert "COMPLETED" in result
        assert "T-20260303-143000" in result
        assert "Test task" in result

    def test_flagged_task(self, tmp_path):
        _make_log(
            tmp_path, "20260303-143000-queue.json",
            status="flagged",
            checkpoint_flags=[{"type": "fork_decision", "context": "Two approaches available"}],
        )
        result = summarize_logs(str(tmp_path))
        assert "FLAGGED" in result
        assert "fork_decision" in result
        assert "Two approaches available" in result

    def test_mixed_tasks(self, tmp_path):
        _make_log(tmp_path, "20260303-140000-queue.json", task_id="T-20260303-140000")
        _make_log(
            tmp_path, "20260303-143000-queue.json",
            task_id="T-20260303-143000",
            status="flagged",
            checkpoint_flags=[{"type": "anomaly", "context": "Weird data"}],
        )
        result = summarize_logs(str(tmp_path))
        assert "COMPLETED (1)" in result
        assert "FLAGGED" in result
        assert "2 total" in result

    def test_skips_non_structured_logs(self, tmp_path):
        # Old format without task_id
        (tmp_path / "old.json").write_text(json.dumps({"result": "hello"}))
        result = summarize_logs(str(tmp_path))
        assert result == ""

    def test_skips_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json{{{")
        result = summarize_logs(str(tmp_path))
        assert result == ""

    def test_citation_summary(self, tmp_path):
        _make_log(tmp_path, "log.json")
        result = summarize_logs(str(tmp_path))
        assert "citations: 1/1" in result

    def test_ungrounded_citation(self, tmp_path):
        _make_log(
            tmp_path, "log.json",
            citation_validation={"total": 0, "valid": 0, "ungrounded": True, "pass_rate": 0.0},
        )
        result = summarize_logs(str(tmp_path))
        assert "UNGROUNDED" in result

    def test_archive(self, tmp_path):
        _make_log(tmp_path, "log.json")
        summarize_logs(str(tmp_path), archive=True)
        assert not (tmp_path / "log.json").exists()
        assert (tmp_path / "archive" / "log.json").exists()

    def test_result_truncation(self, tmp_path):
        _make_log(tmp_path, "log.json", result="X" * 1000)
        result = summarize_logs(str(tmp_path))
        assert "..." in result
