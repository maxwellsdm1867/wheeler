"""Tests for retrieval quality metrics (Enhancement 6: GraphRAG plan)."""

from __future__ import annotations

import pytest

from wheeler.validation.ledger import (
    LedgerEntry,
    compute_retrieval_metrics,
    _detect_coverage_gaps,
)
from wheeler.models import LedgerModel


class TestComputeRetrievalMetrics:
    def test_compute_metrics_all_cited(self):
        """All retrieved nodes were cited: precision = 1.0."""
        output = "The analysis [F-abcd1234] and hypothesis [H-5678abcd] confirm the result."
        retrieved = ["F-abcd1234", "H-5678abcd"]
        node_texts = {"F-abcd1234": "analysis result", "H-5678abcd": "hypothesis statement"}

        metrics = compute_retrieval_metrics(output, retrieved, node_texts)

        assert metrics["context_nodes_used"] == 2
        assert metrics["context_nodes_retrieved"] == 2
        assert metrics["context_precision"] == 1.0

    def test_compute_metrics_none_cited(self):
        """No retrieved nodes were cited: precision = 0.0."""
        output = "This text has no citations at all."
        retrieved = ["F-abcd1234", "H-5678abcd"]
        node_texts = {"F-abcd1234": "analysis result", "H-5678abcd": "hypothesis statement"}

        metrics = compute_retrieval_metrics(output, retrieved, node_texts)

        assert metrics["context_nodes_used"] == 0
        assert metrics["context_nodes_retrieved"] == 2
        assert metrics["context_precision"] == 0.0

    def test_compute_metrics_partial(self):
        """2 of 4 retrieved nodes cited: precision = 0.5."""
        output = "Based on [F-aaaa1111] and [H-bbbb2222], we conclude..."
        retrieved = ["F-aaaa1111", "H-bbbb2222", "D-cccc3333", "P-dddd4444"]
        node_texts = {
            "F-aaaa1111": "finding one",
            "H-bbbb2222": "hypothesis two",
            "D-cccc3333": "dataset three",
            "P-dddd4444": "paper four",
        }

        metrics = compute_retrieval_metrics(output, retrieved, node_texts)

        assert metrics["context_nodes_used"] == 2
        assert metrics["context_nodes_retrieved"] == 4
        assert metrics["context_precision"] == 0.5

    def test_compute_metrics_empty_retrieved(self):
        """No retrieved nodes at all: precision = 0.0, used = 0."""
        output = "Some text with [F-abcd1234] citation."
        retrieved: list[str] = []
        node_texts = {"F-abcd1234": "finding"}

        metrics = compute_retrieval_metrics(output, retrieved, node_texts)

        assert metrics["context_nodes_used"] == 0
        assert metrics["context_nodes_retrieved"] == 0
        assert metrics["context_precision"] == 0.0


class TestCoverageGaps:
    def test_coverage_gaps_detects_missing_terms(self):
        """Output mentions 'calcium' but no graph node does."""
        output = "The calcium concentration was elevated in sample three."
        node_texts = {
            "F-1234abcd": "sodium levels in blood sample",
            "F-5678abcd": "potassium measurements from tissue",
        }

        gaps = _detect_coverage_gaps(output, node_texts)

        assert "calcium" in gaps

    def test_coverage_gaps_no_gaps(self):
        """All significant output terms appear in graph nodes."""
        output = "The sodium levels were measured in blood."
        node_texts = {
            "F-1234abcd": "sodium levels measured in blood samples",
        }

        gaps = _detect_coverage_gaps(output, node_texts)

        # "sodium", "levels", "measured", "blood" all appear in node text
        assert "sodium" not in gaps
        assert "levels" not in gaps
        assert "measured" not in gaps
        assert "blood" not in gaps

    def test_coverage_gaps_filters_stop_words(self):
        """Common stop words are not reported as gaps."""
        output = "This is the most important finding because it could have been relevant."
        node_texts = {"F-1234abcd": "unrelated content here"}

        gaps = _detect_coverage_gaps(output, node_texts)

        # These are all stop words or short words, should not appear
        assert "this" not in gaps
        assert "the" not in gaps
        assert "most" not in gaps
        assert "because" not in gaps
        assert "could" not in gaps
        assert "have" not in gaps
        assert "been" not in gaps

    def test_coverage_gaps_filters_short_words(self):
        """Words under 4 characters are not reported as gaps."""
        output = "The dog ran far and bit its own red hat box toy."
        node_texts = {"F-1234abcd": "unrelated content here"}

        gaps = _detect_coverage_gaps(output, node_texts)

        # All these are 3 chars or fewer
        assert "dog" not in gaps
        assert "ran" not in gaps
        assert "far" not in gaps
        assert "bit" not in gaps
        assert "red" not in gaps
        assert "hat" not in gaps
        assert "box" not in gaps
        assert "toy" not in gaps


class TestModelFields:
    def test_ledger_model_has_new_fields(self):
        """LedgerModel accepts the 4 new retrieval quality fields."""
        model = LedgerModel(
            id="L-test1234",
            type="Ledger",
            mode="compile",
            context_nodes_used=3,
            context_nodes_retrieved=5,
            context_precision=0.6,
            coverage_gaps=["calcium", "spectroscopy"],
        )
        assert model.context_nodes_used == 3
        assert model.context_nodes_retrieved == 5
        assert model.context_precision == 0.6
        assert model.coverage_gaps == ["calcium", "spectroscopy"]

    def test_ledger_model_defaults(self):
        """New fields default to zero/empty."""
        model = LedgerModel(id="L-test2345", type="Ledger")
        assert model.context_nodes_used == 0
        assert model.context_nodes_retrieved == 0
        assert model.context_precision == 0.0
        assert model.coverage_gaps == []

    def test_ledger_entry_has_new_fields(self):
        """LedgerEntry dataclass has the 4 new retrieval quality fields."""
        entry = LedgerEntry(
            timestamp="2026-04-08T00:00:00Z",
            mode="compile",
            prompt_summary="test",
            citations_found=["F-abcd1234"],
            citations_valid=["F-abcd1234"],
            citations_invalid=[],
            citations_missing_provenance=[],
            context_nodes_used=2,
            context_nodes_retrieved=4,
            context_precision=0.5,
            coverage_gaps=["missing_term"],
        )
        assert entry.context_nodes_used == 2
        assert entry.context_nodes_retrieved == 4
        assert entry.context_precision == 0.5
        assert entry.coverage_gaps == ["missing_term"]

    def test_ledger_entry_defaults(self):
        """New LedgerEntry fields default to zero/empty."""
        entry = LedgerEntry(
            timestamp="2026-04-08T00:00:00Z",
            mode="chat",
            prompt_summary="test",
            citations_found=[],
            citations_valid=[],
            citations_invalid=[],
            citations_missing_provenance=[],
        )
        assert entry.context_nodes_used == 0
        assert entry.context_nodes_retrieved == 0
        assert entry.context_precision == 0.0
        assert entry.coverage_gaps == []
