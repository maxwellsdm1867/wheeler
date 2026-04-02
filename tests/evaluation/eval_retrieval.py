"""Retrieval evaluation framework for Wheeler knowledge graph search.

Measures Precision@k, Recall, and Mean Reciprocal Rank (MRR) for both
semantic search (search_findings via fastembed) and keyword search
(query_findings via Cypher). Runs offline with mock data when no graph
backend is available.

Usage:
    python tests/evaluation/eval_retrieval.py
    python tests/evaluation/eval_retrieval.py --test-set path/to/custom.json
    python tests/evaluation/eval_retrieval.py --k 3
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test set loader
# ---------------------------------------------------------------------------

DEFAULT_TEST_SET = Path(__file__).parent / "retrieval_test_set.json"


@dataclass
class RetrievalTestCase:
    """A single retrieval evaluation test case."""

    query: str
    expected_node_type: str
    expected_keywords: list[str]
    difficulty: str  # "simple", "semantic", "multi_hop"


def load_test_set(path: Path | None = None) -> list[RetrievalTestCase]:
    """Load and validate retrieval test cases from a JSON file.

    Args:
        path: Path to test set JSON. Defaults to the bundled test set.

    Returns:
        List of validated test cases.

    Raises:
        FileNotFoundError: If the test set file does not exist.
        ValueError: If any test case is malformed.
    """
    if path is None:
        path = DEFAULT_TEST_SET
    with open(path) as f:
        raw = json.load(f)

    cases: list[RetrievalTestCase] = []
    for i, entry in enumerate(raw):
        _validate_test_case(entry, i)
        cases.append(
            RetrievalTestCase(
                query=entry["query"],
                expected_node_type=entry["expected_node_type"],
                expected_keywords=entry["expected_keywords"],
                difficulty=entry["difficulty"],
            )
        )
    return cases


def _validate_test_case(entry: dict, index: int) -> None:
    """Validate that a test case dict has all required fields."""
    required = {"query", "expected_node_type", "expected_keywords", "difficulty"}
    missing = required - set(entry.keys())
    if missing:
        raise ValueError(f"Test case {index} missing fields: {missing}")
    if entry["difficulty"] not in ("simple", "semantic", "multi_hop"):
        raise ValueError(
            f"Test case {index} has invalid difficulty: {entry['difficulty']!r}"
        )
    if not isinstance(entry["expected_keywords"], list) or not entry["expected_keywords"]:
        raise ValueError(
            f"Test case {index} expected_keywords must be a non-empty list"
        )


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def result_is_relevant(
    result_text: str,
    expected_keywords: list[str],
    *,
    match_threshold: int = 1,
) -> bool:
    """Check whether a single result is relevant based on keyword overlap.

    A result is relevant if at least `match_threshold` of the expected
    keywords appear (case-insensitive) in the result text.

    Args:
        result_text: The text content of a search result.
        expected_keywords: Keywords that should appear in relevant results.
        match_threshold: Minimum number of keywords required for relevance.

    Returns:
        True if the result is relevant.
    """
    text_lower = result_text.lower()
    matched = sum(1 for kw in expected_keywords if kw.lower() in text_lower)
    return matched >= match_threshold


def precision_at_k(
    results: list[dict[str, Any]],
    expected_keywords: list[str],
    k: int = 5,
) -> float:
    """Precision@k: fraction of top-k results that are relevant.

    Args:
        results: Search results, each with a "text" key.
        expected_keywords: Keywords that define relevance.
        k: Number of top results to consider.

    Returns:
        Precision score between 0.0 and 1.0.
    """
    top_k = results[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(
        1
        for r in top_k
        if result_is_relevant(r.get("text", "") + " " + r.get("description", ""), expected_keywords)
    )
    return relevant_count / len(top_k)


def recall(
    results: list[dict[str, Any]],
    expected_keywords: list[str],
) -> float:
    """Recall: did any result contain the expected keywords?

    Binary recall -- 1.0 if at least one result is relevant, else 0.0.

    Args:
        results: All search results.
        expected_keywords: Keywords that define relevance.

    Returns:
        1.0 or 0.0.
    """
    for r in results:
        text = r.get("text", "") + " " + r.get("description", "")
        if result_is_relevant(text, expected_keywords):
            return 1.0
    return 0.0


def reciprocal_rank(
    results: list[dict[str, Any]],
    expected_keywords: list[str],
) -> float:
    """Reciprocal rank: 1/position of the first relevant result.

    Args:
        results: Search results in ranked order.
        expected_keywords: Keywords that define relevance.

    Returns:
        1/rank of first relevant result, or 0.0 if none found.
    """
    for i, r in enumerate(results, start=1):
        text = r.get("text", "") + " " + r.get("description", "")
        if result_is_relevant(text, expected_keywords):
            return 1.0 / i
    return 0.0


# ---------------------------------------------------------------------------
# Mock data: used when no live graph is available
# ---------------------------------------------------------------------------

MOCK_NODES: list[dict[str, str]] = [
    # Findings
    {"id": "F-0001", "label": "Finding", "text": "Calcium oscillation frequency increases with temperature in cortical neurons"},
    {"id": "F-0002", "label": "Finding", "text": "Sodium channel conductance follows Hodgkin-Huxley kinetics in squid giant axon"},
    {"id": "F-0003", "label": "Finding", "text": "Resting membrane potential is approximately -70mV in hippocampal pyramidal cells"},
    {"id": "F-0004", "label": "Finding", "text": "Action potential threshold voltage shifts with extracellular potassium concentration"},
    {"id": "F-0005", "label": "Finding", "text": "Synaptic vesicle release probability is modulated by presynaptic calcium levels"},
    {"id": "F-0006", "label": "Finding", "text": "Patch clamp recording reveals single channel conductance of 20pS for AMPA receptors"},
    {"id": "F-0007", "label": "Finding", "text": "EPSP amplitude decreases with distance from the synapse due to cable properties"},
    {"id": "F-0008", "label": "Finding", "text": "Interneuron firing rate increases during gamma oscillations in hippocampus"},
    {"id": "F-0009", "label": "Finding", "text": "Potassium delayed rectifier current activates at -40mV with slow kinetics"},
    {"id": "F-0010", "label": "Finding", "text": "Temperature reduction slows spike timing and broadens action potential waveform in cold conditions"},
    {"id": "F-0011", "label": "Finding", "text": "Neurotransmitter release at the synapse requires SNARE complex assembly for vesicle fusion"},
    {"id": "F-0012", "label": "Finding", "text": "EEG oscillation patterns during sleep show characteristic delta wave activity"},
    {"id": "F-0013", "label": "Finding", "text": "Mitochondrial ATP production is the primary metabolic energy source in active neural tissue"},
    {"id": "F-0014", "label": "Finding", "text": "Apoptosis-mediated cell death contributes to neurodegeneration through excitotoxicity pathways"},
    {"id": "F-0015", "label": "Finding", "text": "Myelination increases conduction velocity along axons by enabling saltatory propagation"},
    {"id": "F-0016", "label": "Finding", "text": "Membrane resistance and capacitance determine the passive electrical properties of neurons"},
    {"id": "F-0017", "label": "Finding", "text": "Rhythmic oscillation patterns in cortical circuits emerge from inhibitory-excitatory balance"},
    {"id": "F-0018", "label": "Finding", "text": "Pharmacological receptor modulation with GABAergic drugs alters brain electrical activity"},
    {"id": "F-0019", "label": "Finding", "text": "Channel gating kinetics of Nav1.6 differ from Nav1.2 in initial segment"},
    {"id": "F-0020", "label": "Finding", "text": "Burst detection pipeline identified 342 bursting events in the ephys recording dataset"},
    {"id": "F-0021", "label": "Finding", "text": "Membrane time constant finding: tau = 25ms measured from voltage clamp step responses"},
    {"id": "F-0022", "label": "Finding", "text": "Impedance measurements reveal frequency-dependent changes in the updated impedance script output"},
    {"id": "F-0023", "label": "Finding", "text": "Calcium imaging results show elevated activity during whisker stimulation epochs"},
    {"id": "F-0024", "label": "Finding", "text": "Inhibitory dominance contradicted by evidence of excitatory-led fast oscillations"},
    # Hypotheses
    {"id": "H-0001", "label": "Hypothesis", "text": "LTP and NMDA receptor-dependent plasticity forms the molecular basis of spatial memory"},
    {"id": "H-0002", "label": "Hypothesis", "text": "Calcium imaging hypothesis: astrocytic calcium waves modulate synaptic transmission"},
    {"id": "H-0003", "label": "Hypothesis", "text": "Inhibitory dominance hypothesis: tonic inhibition gates cortical excitability"},
    # Papers
    {"id": "P-0001", "label": "Paper", "text": "Hodgkin AL, Huxley AF (1952) A quantitative description of membrane current and its application to conduction and excitation in nerve"},
    {"id": "P-0002", "label": "Paper", "text": "Synaptic plasticity mechanisms reviewed: from LTP induction to memory consolidation"},
    # OpenQuestions
    {"id": "Q-0001", "label": "OpenQuestion", "text": "What open questions arose from voltage clamp experiments on fast sodium currents?"},
    # Datasets
    {"id": "D-0001", "label": "Dataset", "text": "Raw ephys recording dataset: 32-channel silicon probe, spike sorting ready"},
    {"id": "D-0002", "label": "Dataset", "text": "Calcium imaging dataset: two-photon microscopy, GCaMP6f, barrel cortex"},
    # Executions
    {"id": "X-0001", "label": "Execution", "text": "Script run: channel gating analysis pipeline, produced Nav1.6 kinetics findings"},
    {"id": "X-0002", "label": "Execution", "text": "Spike sorting analysis execution on ephys recording dataset using Kilosort"},
    {"id": "X-0003", "label": "Execution", "text": "Provenance trace of membrane time constant measurement from voltage clamp protocol"},
    # Documents
    {"id": "W-0001", "label": "Document", "text": "Results document citing burst detection pipeline findings in barrel cortex"},
]


# ---------------------------------------------------------------------------
# Retrieval backends
# ---------------------------------------------------------------------------


@dataclass
class RetrievalResult:
    """Aggregated result from one retrieval channel."""

    results: list[dict[str, Any]]
    source: str  # "semantic" or "keyword"


def _semantic_search_mock(query: str, nodes: list[dict[str, str]], limit: int = 10) -> list[dict[str, Any]]:
    """Simulate semantic search using keyword overlap scoring.

    This is a rough proxy for embedding-based search. For real evaluation,
    replace with actual EmbeddingStore.search() calls.
    """
    query_tokens = set(query.lower().split())
    scored: list[tuple[float, dict[str, str]]] = []
    for node in nodes:
        text_tokens = set(node["text"].lower().split())
        # Jaccard-like overlap score
        overlap = len(query_tokens & text_tokens)
        if overlap > 0:
            score = overlap / len(query_tokens | text_tokens)
            scored.append((score, node))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"node_id": n["id"], "label": n["label"], "text": n["text"], "score": round(s, 4)}
        for s, n in scored[:limit]
    ]


def _keyword_search_mock(query: str, nodes: list[dict[str, str]], limit: int = 10) -> list[dict[str, Any]]:
    """Simulate keyword search (case-insensitive substring match).

    Mimics the behavior of query_findings with a keyword parameter.
    """
    query_lower = query.lower()
    keywords = query_lower.split()
    results: list[dict[str, Any]] = []
    for node in nodes:
        text_lower = node["text"].lower()
        if any(kw in text_lower for kw in keywords):
            results.append({
                "node_id": node["id"],
                "label": node["label"],
                "text": node["text"],
                "description": node["text"],
            })
        if len(results) >= limit:
            break
    return results


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------


@dataclass
class CaseResult:
    """Evaluation result for a single test case."""

    query: str
    difficulty: str
    semantic_precision: float
    semantic_recall: float
    semantic_rr: float
    keyword_precision: float
    keyword_recall: float
    keyword_rr: float


@dataclass
class EvalReport:
    """Aggregated evaluation report."""

    case_results: list[CaseResult] = field(default_factory=list)
    k: int = 5

    def add(self, result: CaseResult) -> None:
        self.case_results.append(result)

    def summary_by_difficulty(self) -> dict[str, dict[str, float]]:
        """Compute mean metrics grouped by difficulty level."""
        groups: dict[str, list[CaseResult]] = {}
        for cr in self.case_results:
            groups.setdefault(cr.difficulty, []).append(cr)

        summary: dict[str, dict[str, float]] = {}
        for diff, cases in sorted(groups.items()):
            n = len(cases)
            summary[diff] = {
                "count": n,
                "semantic_precision": _mean([c.semantic_precision for c in cases]),
                "semantic_recall": _mean([c.semantic_recall for c in cases]),
                "semantic_mrr": _mean([c.semantic_rr for c in cases]),
                "keyword_precision": _mean([c.keyword_precision for c in cases]),
                "keyword_recall": _mean([c.keyword_recall for c in cases]),
                "keyword_mrr": _mean([c.keyword_rr for c in cases]),
            }
        return summary

    def overall_summary(self) -> dict[str, float]:
        """Compute mean metrics across all test cases."""
        if not self.case_results:
            return {}
        return {
            "count": len(self.case_results),
            "semantic_precision": _mean([c.semantic_precision for c in self.case_results]),
            "semantic_recall": _mean([c.semantic_recall for c in self.case_results]),
            "semantic_mrr": _mean([c.semantic_rr for c in self.case_results]),
            "keyword_precision": _mean([c.keyword_precision for c in self.case_results]),
            "keyword_recall": _mean([c.keyword_recall for c in self.case_results]),
            "keyword_mrr": _mean([c.keyword_rr for c in self.case_results]),
        }


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def run_evaluation(
    test_cases: list[RetrievalTestCase],
    nodes: list[dict[str, str]] | None = None,
    k: int = 5,
) -> EvalReport:
    """Run retrieval evaluation over test cases using mock data.

    Args:
        test_cases: List of retrieval test cases.
        nodes: Mock node data. Defaults to MOCK_NODES.
        k: Number of top results for Precision@k.

    Returns:
        Aggregated evaluation report.
    """
    if nodes is None:
        nodes = MOCK_NODES

    report = EvalReport(k=k)

    for tc in test_cases:
        semantic_results = _semantic_search_mock(tc.query, nodes, limit=k)
        keyword_results = _keyword_search_mock(tc.query, nodes, limit=k)

        case_result = CaseResult(
            query=tc.query,
            difficulty=tc.difficulty,
            semantic_precision=precision_at_k(semantic_results, tc.expected_keywords, k=k),
            semantic_recall=recall(semantic_results, tc.expected_keywords),
            semantic_rr=reciprocal_rank(semantic_results, tc.expected_keywords),
            keyword_precision=precision_at_k(keyword_results, tc.expected_keywords, k=k),
            keyword_recall=recall(keyword_results, tc.expected_keywords),
            keyword_rr=reciprocal_rank(keyword_results, tc.expected_keywords),
        )
        report.add(case_result)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(report: EvalReport) -> str:
    """Format an evaluation report as a human-readable string."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("Wheeler Retrieval Evaluation Report")
    lines.append("=" * 72)
    lines.append("")

    # Per-case details
    lines.append("Per-case results:")
    lines.append("-" * 72)
    for cr in report.case_results:
        lines.append(f"  [{cr.difficulty:>9s}] {cr.query}")
        lines.append(
            f"    semantic: P@{report.k}={cr.semantic_precision:.2f}  "
            f"recall={cr.semantic_recall:.2f}  RR={cr.semantic_rr:.2f}"
        )
        lines.append(
            f"    keyword:  P@{report.k}={cr.keyword_precision:.2f}  "
            f"recall={cr.keyword_recall:.2f}  RR={cr.keyword_rr:.2f}"
        )
    lines.append("")

    # By difficulty
    lines.append("Results by difficulty:")
    lines.append("-" * 72)
    by_diff = report.summary_by_difficulty()
    for diff, metrics in by_diff.items():
        n = int(metrics["count"])
        lines.append(f"  {diff} (n={n}):")
        lines.append(
            f"    semantic: P@{report.k}={metrics['semantic_precision']:.3f}  "
            f"recall={metrics['semantic_recall']:.3f}  "
            f"MRR={metrics['semantic_mrr']:.3f}"
        )
        lines.append(
            f"    keyword:  P@{report.k}={metrics['keyword_precision']:.3f}  "
            f"recall={metrics['keyword_recall']:.3f}  "
            f"MRR={metrics['keyword_mrr']:.3f}"
        )
    lines.append("")

    # Overall
    lines.append("Overall:")
    lines.append("-" * 72)
    overall = report.overall_summary()
    if overall:
        lines.append(
            f"  semantic: P@{report.k}={overall['semantic_precision']:.3f}  "
            f"recall={overall['semantic_recall']:.3f}  "
            f"MRR={overall['semantic_mrr']:.3f}"
        )
        lines.append(
            f"  keyword:  P@{report.k}={overall['keyword_precision']:.3f}  "
            f"recall={overall['keyword_recall']:.3f}  "
            f"MRR={overall['keyword_mrr']:.3f}"
        )
    lines.append("=" * 72)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the retrieval evaluation CLI."""
    parser = argparse.ArgumentParser(
        description="Wheeler retrieval evaluation framework"
    )
    parser.add_argument(
        "--test-set",
        type=Path,
        default=None,
        help="Path to test set JSON (default: bundled test set)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="k for Precision@k (default: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of human-readable text",
    )
    args = parser.parse_args(argv)

    test_cases = load_test_set(args.test_set)
    print(f"Loaded {len(test_cases)} test cases")
    print(f"Running with mock data (no live graph)")
    print()

    report = run_evaluation(test_cases, k=args.k)

    if args.json:
        output = {
            "k": report.k,
            "by_difficulty": report.summary_by_difficulty(),
            "overall": report.overall_summary(),
            "cases": [
                {
                    "query": cr.query,
                    "difficulty": cr.difficulty,
                    "semantic_precision": cr.semantic_precision,
                    "semantic_recall": cr.semantic_recall,
                    "semantic_rr": cr.semantic_rr,
                    "keyword_precision": cr.keyword_precision,
                    "keyword_recall": cr.keyword_recall,
                    "keyword_rr": cr.keyword_rr,
                }
                for cr in report.case_results
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(_format_report(report))


if __name__ == "__main__":
    main()
