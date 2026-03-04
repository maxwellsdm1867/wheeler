"""Tests for wheeler.task_log module."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from wheeler.task_log import (
    build_task_log,
    detect_checkpoints,
    extract_result_text,
    generate_task_id,
)


class TestGenerateTaskId:
    def test_format(self):
        tid = generate_task_id()
        assert tid.startswith("T-")
        parts = tid.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS


class TestDetectCheckpoints:
    def test_detects_fork_decision(self):
        text = "Checkpoint: fork decision — two approaches available"
        flags = detect_checkpoints(text)
        assert len(flags) == 1
        assert flags[0]["type"] == "fork_decision"

    def test_detects_interpretation(self):
        text = "Checkpoint: interpretation needed for these results"
        flags = detect_checkpoints(text)
        assert len(flags) == 1
        assert flags[0]["type"] == "interpretation"

    def test_detects_anomaly(self):
        text = "Checkpoint: anomaly detected in dataset"
        flags = detect_checkpoints(text)
        assert len(flags) == 1
        assert flags[0]["type"] == "anomaly"

    def test_detects_multiple(self):
        text = "Checkpoint: fork decision here.\n\nAlso checkpoint: anomaly in data."
        flags = detect_checkpoints(text)
        assert len(flags) == 2
        types = {f["type"] for f in flags}
        assert types == {"fork_decision", "anomaly"}

    def test_no_checkpoints(self):
        text = "Normal output with no checkpoint flags."
        flags = detect_checkpoints(text)
        assert flags == []

    def test_case_insensitive(self):
        text = "CHECKPOINT: JUDGMENT call required"
        flags = detect_checkpoints(text)
        assert len(flags) == 1
        assert flags[0]["type"] == "judgment"


class TestExtractResultText:
    def test_json_result(self):
        raw = json.dumps({"result": "Found something"})
        assert extract_result_text(raw) == "Found something"

    def test_plain_text(self):
        assert extract_result_text("plain text") == "plain text"

    def test_empty_json(self):
        raw = json.dumps({})
        assert extract_result_text(raw) == ""

    def test_string_json(self):
        raw = json.dumps("just a string")
        assert extract_result_text(raw) == "just a string"


class TestBuildTaskLog:
    @pytest.mark.asyncio
    async def test_creates_structured_log(self, tmp_path):
        log = tmp_path / "test.json"
        log.write_text(json.dumps({"result": "Found [F-3a2b] in the data"}))

        from wheeler.validation.citations import CitationResult, CitationStatus
        mock_results = [
            CitationResult(node_id="F-3a2b", status=CitationStatus.VALID, label="Finding"),
        ]
        with patch("wheeler.task_log.validate_citations", new_callable=AsyncMock, return_value=mock_results), \
             patch("wheeler.task_log.store_entry", new_callable=AsyncMock):
            await build_task_log(str(log), "Test task", "sonnet", 30)

        data = json.loads(log.read_text())
        assert data["task_id"].startswith("T-")
        assert data["task_description"] == "Test task"
        assert data["model"] == "sonnet"
        assert data["duration_seconds"] == 30
        assert data["status"] == "completed"
        assert data["checkpoint_flags"] == []
        assert data["citation_validation"]["valid"] == 1
        assert data["citation_validation"]["pass_rate"] == 1.0
        assert data["result"] == "Found [F-3a2b] in the data"

    @pytest.mark.asyncio
    async def test_flags_checkpoints(self, tmp_path):
        log = tmp_path / "test.json"
        log.write_text(json.dumps({"result": "Checkpoint: fork decision — model A or B?"}))

        with patch("wheeler.task_log.validate_citations", new_callable=AsyncMock, return_value=[]), \
             patch("wheeler.task_log.store_entry", new_callable=AsyncMock):
            await build_task_log(str(log), "Compare models", "sonnet", 60)

        data = json.loads(log.read_text())
        assert data["status"] == "flagged"
        assert len(data["checkpoint_flags"]) == 1
        assert data["checkpoint_flags"][0]["type"] == "fork_decision"

    @pytest.mark.asyncio
    async def test_ungrounded_detection(self, tmp_path):
        log = tmp_path / "test.json"
        log.write_text(json.dumps({"result": "A" * 100}))

        with patch("wheeler.task_log.store_entry", new_callable=AsyncMock):
            await build_task_log(str(log), "Some task", "haiku", 5)

        data = json.loads(log.read_text())
        assert data["citation_validation"]["ungrounded"] is True

    @pytest.mark.asyncio
    async def test_handles_missing_file(self):
        await build_task_log("/nonexistent/path.json", "task", "sonnet", 0)
        # Should not raise

    @pytest.mark.asyncio
    async def test_short_response_still_logged(self, tmp_path):
        log = tmp_path / "test.json"
        log.write_text(json.dumps({"result": "OK"}))

        await build_task_log(str(log), "Quick check", "haiku", 2)

        data = json.loads(log.read_text())
        # Short response: no citation validation needed but still gets structured log
        assert data["task_id"].startswith("T-")
        assert data["status"] == "completed"
        assert data["citation_validation"] is None
