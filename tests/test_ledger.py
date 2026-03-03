"""Tests for wheeler.validation.ledger module."""

import pytest

from wheeler.validation.citations import CitationResult, CitationStatus
from wheeler.validation.ledger import LedgerEntry, create_entry


class TestLedgerEntry:
    def test_pass_rate_all_valid(self):
        entry = LedgerEntry(
            timestamp="2026-01-01T00:00:00Z",
            mode="chat",
            prompt_summary="test",
            citations_found=["F-abcd", "H-1234"],
            citations_valid=["F-abcd", "H-1234"],
            citations_invalid=[],
            citations_missing_provenance=[],
            ungrounded=False,
        )
        assert entry.pass_rate == 1.0

    def test_pass_rate_some_invalid(self):
        entry = LedgerEntry(
            timestamp="2026-01-01T00:00:00Z",
            mode="chat",
            prompt_summary="test",
            citations_found=["F-abcd", "H-1234"],
            citations_valid=["F-abcd"],
            citations_invalid=["H-1234"],
            citations_missing_provenance=[],
            ungrounded=True,
        )
        assert entry.pass_rate == 0.5

    def test_pass_rate_no_citations(self):
        entry = LedgerEntry(
            timestamp="2026-01-01T00:00:00Z",
            mode="chat",
            prompt_summary="test",
            citations_found=[],
            citations_valid=[],
            citations_invalid=[],
            citations_missing_provenance=[],
            ungrounded=True,
        )
        assert entry.pass_rate == 0.0


class TestCreateEntry:
    def test_create_entry_all_valid(self):
        results = [
            CitationResult(node_id="F-abcd", status=CitationStatus.VALID, label="Finding"),
            CitationResult(node_id="H-1234", status=CitationStatus.VALID, label="Hypothesis"),
        ]
        entry = create_entry("chat", "test prompt", results)
        assert entry.mode == "chat"
        assert entry.citations_found == ["F-abcd", "H-1234"]
        assert entry.citations_valid == ["F-abcd", "H-1234"]
        assert entry.citations_invalid == []
        assert entry.citations_missing_provenance == []
        assert entry.ungrounded is False

    def test_create_entry_with_invalid(self):
        results = [
            CitationResult(node_id="F-abcd", status=CitationStatus.VALID, label="Finding"),
            CitationResult(node_id="H-0000", status=CitationStatus.NOT_FOUND),
        ]
        entry = create_entry("writing", "some text", results)
        assert entry.citations_invalid == ["H-0000"]
        assert entry.ungrounded is True

    def test_create_entry_with_missing_provenance(self):
        results = [
            CitationResult(
                node_id="F-abcd",
                status=CitationStatus.MISSING_PROVENANCE,
                label="Finding",
                details="Finding lacks required provenance",
            ),
        ]
        entry = create_entry("execute", "analysis result", results)
        assert entry.citations_missing_provenance == ["F-abcd"]
        assert entry.citations_invalid == []
        # Not ungrounded because the node exists, just lacks provenance
        assert entry.ungrounded is False

    def test_create_entry_no_citations(self):
        entry = create_entry("chat", "no refs here", [])
        assert entry.citations_found == []
        assert entry.ungrounded is True

    def test_prompt_truncation(self):
        long_prompt = "x" * 300
        entry = create_entry("chat", long_prompt, [])
        assert len(entry.prompt_summary) == 203  # 200 + "..."
        assert entry.prompt_summary.endswith("...")

    def test_timestamp_is_iso(self):
        entry = create_entry("chat", "test", [])
        # Should be parseable ISO format
        assert "T" in entry.timestamp
