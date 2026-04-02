"""Tests for the retrieval evaluation framework.

Verifies:
- Test set JSON is valid and complete
- Scoring functions produce correct results
- Evaluation script imports and runs correctly
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.evaluation.eval_retrieval import (
    CaseResult,
    EvalReport,
    RetrievalTestCase,
    _keyword_search_mock,
    _semantic_search_mock,
    load_test_set,
    precision_at_k,
    recall,
    reciprocal_rank,
    result_is_relevant,
    run_evaluation,
)


# ---------------------------------------------------------------------------
# Test set validation
# ---------------------------------------------------------------------------

TEST_SET_PATH = Path(__file__).parent / "evaluation" / "retrieval_test_set.json"

VALID_NODE_TYPES = {
    "Finding",
    "Hypothesis",
    "Paper",
    "OpenQuestion",
    "Dataset",
    "Document",
    "Execution",
    "Script",
    "ResearchNote",
}
VALID_DIFFICULTIES = {"simple", "semantic", "multi_hop"}


class TestTestSetValid:
    """Verify the test set JSON is well-formed."""

    def test_file_exists(self) -> None:
        assert TEST_SET_PATH.exists(), f"Test set not found at {TEST_SET_PATH}"

    def test_valid_json(self) -> None:
        with open(TEST_SET_PATH) as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_has_30_cases(self) -> None:
        with open(TEST_SET_PATH) as f:
            data = json.load(f)
        assert len(data) == 30, f"Expected 30 test cases, got {len(data)}"

    def test_required_fields(self) -> None:
        with open(TEST_SET_PATH) as f:
            data = json.load(f)
        for i, case in enumerate(data):
            assert "query" in case, f"Case {i} missing 'query'"
            assert "expected_node_type" in case, f"Case {i} missing 'expected_node_type'"
            assert "expected_keywords" in case, f"Case {i} missing 'expected_keywords'"
            assert "difficulty" in case, f"Case {i} missing 'difficulty'"

    def test_valid_node_types(self) -> None:
        with open(TEST_SET_PATH) as f:
            data = json.load(f)
        for i, case in enumerate(data):
            assert case["expected_node_type"] in VALID_NODE_TYPES, (
                f"Case {i} has invalid node type: {case['expected_node_type']}"
            )

    def test_valid_difficulties(self) -> None:
        with open(TEST_SET_PATH) as f:
            data = json.load(f)
        for i, case in enumerate(data):
            assert case["difficulty"] in VALID_DIFFICULTIES, (
                f"Case {i} has invalid difficulty: {case['difficulty']}"
            )

    def test_difficulty_distribution(self) -> None:
        with open(TEST_SET_PATH) as f:
            data = json.load(f)
        counts: dict[str, int] = {}
        for case in data:
            counts[case["difficulty"]] = counts.get(case["difficulty"], 0) + 1
        assert counts.get("simple", 0) == 10, f"Expected 10 simple, got {counts.get('simple', 0)}"
        assert counts.get("semantic", 0) == 10, f"Expected 10 semantic, got {counts.get('semantic', 0)}"
        assert counts.get("multi_hop", 0) == 10, f"Expected 10 multi_hop, got {counts.get('multi_hop', 0)}"

    def test_keywords_are_nonempty_lists(self) -> None:
        with open(TEST_SET_PATH) as f:
            data = json.load(f)
        for i, case in enumerate(data):
            kw = case["expected_keywords"]
            assert isinstance(kw, list) and len(kw) > 0, (
                f"Case {i} expected_keywords must be a non-empty list"
            )

    def test_load_test_set_function(self) -> None:
        cases = load_test_set()
        assert len(cases) == 30
        assert all(isinstance(c, RetrievalTestCase) for c in cases)


# ---------------------------------------------------------------------------
# Scoring function tests
# ---------------------------------------------------------------------------


class TestResultIsRelevant:
    """Unit tests for the relevance checker."""

    def test_single_keyword_match(self) -> None:
        assert result_is_relevant("calcium signaling in neurons", ["calcium"])

    def test_case_insensitive(self) -> None:
        assert result_is_relevant("CALCIUM OSCILLATION", ["calcium", "oscillation"])

    def test_no_match(self) -> None:
        assert not result_is_relevant("banana recipe", ["calcium", "neuron"])

    def test_partial_match_below_threshold(self) -> None:
        assert not result_is_relevant(
            "calcium in food", ["calcium", "neuron"], match_threshold=2
        )

    def test_partial_match_at_threshold(self) -> None:
        assert result_is_relevant(
            "calcium oscillation frequency", ["calcium", "oscillation"], match_threshold=2
        )


class TestPrecisionAtK:
    """Unit tests for Precision@k."""

    def test_all_relevant(self) -> None:
        results = [
            {"text": "calcium oscillation finding"},
            {"text": "calcium wave propagation"},
        ]
        assert precision_at_k(results, ["calcium"], k=2) == 1.0

    def test_none_relevant(self) -> None:
        results = [
            {"text": "banana recipe"},
            {"text": "weather forecast"},
        ]
        assert precision_at_k(results, ["calcium"], k=2) == 0.0

    def test_half_relevant(self) -> None:
        results = [
            {"text": "calcium oscillation"},
            {"text": "banana recipe"},
            {"text": "calcium wave"},
            {"text": "weather forecast"},
        ]
        assert precision_at_k(results, ["calcium"], k=4) == 0.5

    def test_empty_results(self) -> None:
        assert precision_at_k([], ["calcium"], k=5) == 0.0

    def test_k_larger_than_results(self) -> None:
        results = [{"text": "calcium signaling"}]
        assert precision_at_k(results, ["calcium"], k=5) == 1.0

    def test_uses_description_field(self) -> None:
        results = [{"text": "", "description": "calcium oscillation"}]
        assert precision_at_k(results, ["calcium"], k=1) == 1.0


class TestRecall:
    """Unit tests for binary recall."""

    def test_relevant_found(self) -> None:
        results = [
            {"text": "banana recipe"},
            {"text": "calcium oscillation"},
        ]
        assert recall(results, ["calcium"]) == 1.0

    def test_nothing_relevant(self) -> None:
        results = [{"text": "banana recipe"}]
        assert recall(results, ["calcium"]) == 0.0

    def test_empty_results(self) -> None:
        assert recall([], ["calcium"]) == 0.0


class TestReciprocalRank:
    """Unit tests for MRR computation."""

    def test_first_result_relevant(self) -> None:
        results = [{"text": "calcium oscillation"}]
        assert reciprocal_rank(results, ["calcium"]) == 1.0

    def test_second_result_relevant(self) -> None:
        results = [
            {"text": "banana recipe"},
            {"text": "calcium oscillation"},
        ]
        assert reciprocal_rank(results, ["calcium"]) == 0.5

    def test_third_result_relevant(self) -> None:
        results = [
            {"text": "banana"},
            {"text": "weather"},
            {"text": "calcium data"},
        ]
        assert reciprocal_rank(results, ["calcium"]) == pytest.approx(1.0 / 3.0)

    def test_no_relevant_result(self) -> None:
        results = [{"text": "banana"}, {"text": "weather"}]
        assert reciprocal_rank(results, ["calcium"]) == 0.0

    def test_empty_results(self) -> None:
        assert reciprocal_rank([], ["calcium"]) == 0.0


# ---------------------------------------------------------------------------
# Mock search tests
# ---------------------------------------------------------------------------


class TestMockSearch:
    """Verify mock search implementations work correctly."""

    SAMPLE_NODES = [
        {"id": "F-001", "label": "Finding", "text": "Calcium oscillation frequency in neurons"},
        {"id": "F-002", "label": "Finding", "text": "Sodium channel conductance measurements"},
        {"id": "H-001", "label": "Hypothesis", "text": "Potassium regulates resting potential"},
    ]

    def test_semantic_search_returns_results(self) -> None:
        results = _semantic_search_mock("calcium oscillation", self.SAMPLE_NODES)
        assert len(results) > 0
        assert results[0]["label"] == "Finding"

    def test_semantic_search_empty_for_unrelated(self) -> None:
        results = _semantic_search_mock("quantum entanglement", self.SAMPLE_NODES)
        assert len(results) == 0

    def test_semantic_search_respects_limit(self) -> None:
        results = _semantic_search_mock("calcium", self.SAMPLE_NODES, limit=1)
        assert len(results) <= 1

    def test_keyword_search_finds_match(self) -> None:
        results = _keyword_search_mock("calcium", self.SAMPLE_NODES)
        assert len(results) == 1
        assert results[0]["node_id"] == "F-001"

    def test_keyword_search_no_match(self) -> None:
        results = _keyword_search_mock("quantum", self.SAMPLE_NODES)
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Integration: run_evaluation
# ---------------------------------------------------------------------------


class TestRunEvaluation:
    """Integration tests for the full evaluation pipeline."""

    def test_runs_with_defaults(self) -> None:
        cases = load_test_set()
        report = run_evaluation(cases)
        assert isinstance(report, EvalReport)
        assert len(report.case_results) == 30

    def test_summary_by_difficulty_has_all_groups(self) -> None:
        cases = load_test_set()
        report = run_evaluation(cases)
        by_diff = report.summary_by_difficulty()
        assert "simple" in by_diff
        assert "semantic" in by_diff
        assert "multi_hop" in by_diff

    def test_overall_summary_has_metrics(self) -> None:
        cases = load_test_set()
        report = run_evaluation(cases)
        overall = report.overall_summary()
        assert "semantic_precision" in overall
        assert "semantic_recall" in overall
        assert "semantic_mrr" in overall
        assert "keyword_precision" in overall
        assert "keyword_recall" in overall
        assert "keyword_mrr" in overall

    def test_metrics_in_valid_range(self) -> None:
        cases = load_test_set()
        report = run_evaluation(cases)
        for cr in report.case_results:
            for val in (
                cr.semantic_precision,
                cr.semantic_recall,
                cr.semantic_rr,
                cr.keyword_precision,
                cr.keyword_recall,
                cr.keyword_rr,
            ):
                assert 0.0 <= val <= 1.0, f"Metric out of range: {val}"

    def test_custom_k(self) -> None:
        cases = load_test_set()
        report = run_evaluation(cases, k=3)
        assert report.k == 3
        assert len(report.case_results) == 30

    def test_custom_nodes(self) -> None:
        cases = [
            RetrievalTestCase(
                query="calcium",
                expected_node_type="Finding",
                expected_keywords=["calcium"],
                difficulty="simple",
            )
        ]
        nodes = [{"id": "F-1", "label": "Finding", "text": "calcium oscillation"}]
        report = run_evaluation(cases, nodes=nodes, k=5)
        assert len(report.case_results) == 1
        assert report.case_results[0].semantic_recall == 1.0
        assert report.case_results[0].keyword_recall == 1.0


# ---------------------------------------------------------------------------
# EvalReport dataclass
# ---------------------------------------------------------------------------


class TestEvalReport:
    """Unit tests for EvalReport aggregation."""

    def test_empty_report(self) -> None:
        report = EvalReport()
        assert report.overall_summary() == {}
        assert report.summary_by_difficulty() == {}

    def test_add_and_count(self) -> None:
        report = EvalReport()
        report.add(CaseResult("q", "simple", 1.0, 1.0, 1.0, 0.5, 0.5, 0.5))
        assert len(report.case_results) == 1

    def test_overall_computes_mean(self) -> None:
        report = EvalReport()
        report.add(CaseResult("q1", "simple", 1.0, 1.0, 1.0, 0.0, 0.0, 0.0))
        report.add(CaseResult("q2", "simple", 0.0, 0.0, 0.0, 1.0, 1.0, 1.0))
        overall = report.overall_summary()
        assert overall["semantic_precision"] == pytest.approx(0.5)
        assert overall["keyword_precision"] == pytest.approx(0.5)
