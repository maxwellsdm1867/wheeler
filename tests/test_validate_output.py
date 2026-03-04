"""Tests for wheeler.validate_output module."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from wheeler.validate_output import validate_log


class TestValidateLog:
    @pytest.mark.asyncio
    async def test_extracts_citations_from_json_result(self, tmp_path):
        log = tmp_path / "test.json"
        log.write_text(json.dumps({"result": "Found [F-3a2b] in the data"}))

        from wheeler.validation.citations import CitationResult, CitationStatus
        mock_results = [
            CitationResult(node_id="F-3a2b", status=CitationStatus.VALID, label="Finding"),
        ]
        with patch("wheeler.validate_output.validate_citations", new_callable=AsyncMock, return_value=mock_results), \
             patch("wheeler.validate_output.store_entry", new_callable=AsyncMock):
            await validate_log(str(log))

        # Should have appended validation to the JSON
        data = json.loads(log.read_text())
        assert "_citation_validation" in data
        assert data["_citation_validation"]["valid"] == 1
        assert data["_citation_validation"]["pass_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_flags_ungrounded_response(self, tmp_path):
        log = tmp_path / "test.json"
        # Long response with no citations
        log.write_text(json.dumps({"result": "A" * 100}))

        with patch("wheeler.validate_output.store_entry", new_callable=AsyncMock):
            await validate_log(str(log))

        data = json.loads(log.read_text())
        assert "_citation_validation" in data
        assert data["_citation_validation"]["ungrounded"] is True

    @pytest.mark.asyncio
    async def test_skips_short_response(self, tmp_path):
        log = tmp_path / "test.json"
        log.write_text(json.dumps({"result": "OK"}))

        await validate_log(str(log))

        # Should not modify file (too short to flag)
        data = json.loads(log.read_text())
        assert "_citation_validation" not in data

    @pytest.mark.asyncio
    async def test_handles_missing_file(self):
        await validate_log("/nonexistent/path.json")
        # Should not raise

    @pytest.mark.asyncio
    async def test_handles_plain_text_output(self, tmp_path):
        log = tmp_path / "test.json"
        log.write_text("Found [F-abcd1234] in analysis")

        from wheeler.validation.citations import CitationResult, CitationStatus
        mock_results = [
            CitationResult(node_id="F-abcd1234", status=CitationStatus.NOT_FOUND, label="Finding", details="not found"),
        ]
        with patch("wheeler.validate_output.validate_citations", new_callable=AsyncMock, return_value=mock_results), \
             patch("wheeler.validate_output.store_entry", new_callable=AsyncMock):
            await validate_log(str(log))

        # Plain text gets wrapped into JSON with validation appended
        data = json.loads(log.read_text())
        assert "_citation_validation" in data
        assert data["_citation_validation"]["invalid"] == ["F-abcd1234"]
