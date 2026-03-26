"""Tests for wheeler.validation.citations module."""

import pytest

from wheeler.validation.citations import (
    CITATION_PATTERN,
    CitationResult,
    CitationStatus,
    extract_citations,
    keyword_overlap_score,
)


class TestCitationExtraction:
    def test_extract_single_finding(self):
        text = "We observed [F-3a2b] in the data."
        assert extract_citations(text) == ["F-3a2b"]

    def test_extract_multiple_citations(self):
        text = "Both [F-3a2b] and [H-00ff] are relevant, plus [E-12345678]."
        result = extract_citations(text)
        assert result == ["F-3a2b", "H-00ff", "E-12345678"]

    def test_extract_plan_prefix(self):
        text = "See plan [PL-abcd1234]."
        assert extract_citations(text) == ["PL-abcd1234"]

    def test_extract_all_prefixes(self):
        prefixes = ["PL", "F", "H", "Q", "E", "A", "D", "P", "C", "T", "W"]
        for prefix in prefixes:
            text = f"Node [{prefix}-abcd] found."
            result = extract_citations(text)
            assert result == [f"{prefix}-abcd"], f"Failed for prefix {prefix}"

    def test_deduplication(self):
        text = "[F-3a2b] appears twice: [F-3a2b]."
        assert extract_citations(text) == ["F-3a2b"]

    def test_no_citations(self):
        text = "This text has no citations at all."
        assert extract_citations(text) == []

    def test_invalid_prefix_ignored(self):
        text = "Invalid [X-abcd] and [ZZ-1234] are not matched."
        assert extract_citations(text) == []

    def test_too_short_hex(self):
        text = "Too short: [F-abc]"
        assert extract_citations(text) == []

    def test_too_long_hex(self):
        text = "Too long: [F-123456789]"
        assert extract_citations(text) == []

    def test_exact_4_char_hex(self):
        assert extract_citations("[F-abcd]") == ["F-abcd"]

    def test_exact_8_char_hex(self):
        assert extract_citations("[F-abcd1234]") == ["F-abcd1234"]

    def test_mixed_valid_invalid(self):
        text = "[F-abcd] valid, [X-1234] invalid, [H-5678] valid"
        assert extract_citations(text) == ["F-abcd", "H-5678"]


class TestCitationPattern:
    def test_pattern_matches_valid(self):
        assert CITATION_PATTERN.search("[F-3a2b]")
        assert CITATION_PATTERN.search("[PL-abcd1234]")
        assert CITATION_PATTERN.search("[Q-0000]")

    def test_pattern_rejects_invalid(self):
        assert not CITATION_PATTERN.search("[X-abcd]")
        assert not CITATION_PATTERN.search("[F-abc]")  # too short
        assert not CITATION_PATTERN.search("F-abcd")  # no brackets


class TestCitationResult:
    def test_valid_result(self):
        r = CitationResult(
            node_id="F-abcd",
            status=CitationStatus.VALID,
            label="Finding",
        )
        assert r.status == CitationStatus.VALID
        assert r.label == "Finding"

    def test_not_found_result(self):
        r = CitationResult(
            node_id="F-0000",
            status=CitationStatus.NOT_FOUND,
            details="Finding node not found in graph",
        )
        assert r.status == CitationStatus.NOT_FOUND

    def test_stale_status_exists(self):
        assert CitationStatus.STALE.value == "stale"

    def test_stale_result(self):
        r = CitationResult(
            node_id="A-abcd",
            status=CitationStatus.STALE,
            label="Analysis",
            details="Script has been modified since analysis ran",
        )
        assert r.status == CitationStatus.STALE


class TestKeywordOverlap:
    def test_full_overlap(self):
        score = keyword_overlap_score("hello world", "hello world")
        assert score == 1.0

    def test_partial_overlap(self):
        score = keyword_overlap_score("hello world foo", "hello world")
        assert score == 1.0  # all desc words in text

    def test_no_overlap(self):
        score = keyword_overlap_score("alpha beta", "gamma delta")
        assert score == 0.0

    def test_empty_description(self):
        assert keyword_overlap_score("hello", "") == 0.0

    def test_case_insensitive(self):
        score = keyword_overlap_score("Hello World", "hello world")
        assert score == 1.0
