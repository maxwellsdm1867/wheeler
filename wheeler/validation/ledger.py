"""Provenance ledger: logs every interaction with citation audit results.

Ledger entries are proper graph nodes (L-prefix) with dual-write to
knowledge/ JSON files, just like every other Wheeler node type.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from wheeler.config import WheelerConfig
from wheeler.validation.citations import CitationResult, CitationStatus

logger = logging.getLogger(__name__)


@dataclass
class LedgerEntry:
    timestamp: str
    mode: str
    prompt_summary: str
    citations_found: list[str]
    citations_valid: list[str]
    citations_invalid: list[str]
    citations_missing_provenance: list[str]
    citations_stale: list[str] = field(default_factory=list)
    ungrounded: bool = False
    # Retrieval quality metrics
    context_nodes_used: int = 0
    context_nodes_retrieved: int = 0
    context_precision: float = 0.0
    coverage_gaps: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        total = len(self.citations_found)
        if total == 0:
            return 0.0
        return len(self.citations_valid) / total


def create_entry(
    mode: str,
    prompt: str,
    citation_results: list[CitationResult],
) -> LedgerEntry:
    """Create a ledger entry from citation validation results."""
    now = datetime.now(timezone.utc).isoformat()
    # Truncate prompt for storage
    summary = prompt[:200] + ("..." if len(prompt) > 200 else "")

    found = [r.node_id for r in citation_results]
    valid = [r.node_id for r in citation_results if r.status == CitationStatus.VALID]
    invalid = [
        r.node_id for r in citation_results if r.status == CitationStatus.NOT_FOUND
    ]
    missing_prov = [
        r.node_id
        for r in citation_results
        if r.status == CitationStatus.MISSING_PROVENANCE
    ]
    stale = [
        r.node_id for r in citation_results if r.status == CitationStatus.STALE
    ]
    # Ungrounded if no citations at all, or any are invalid
    ungrounded = len(found) == 0 or len(invalid) > 0

    return LedgerEntry(
        timestamp=now,
        mode=mode,
        prompt_summary=summary,
        citations_found=found,
        citations_valid=valid,
        citations_invalid=invalid,
        citations_missing_provenance=missing_prov,
        citations_stale=stale,
        ungrounded=ungrounded,
    )


def compute_retrieval_metrics(
    output_text: str,
    retrieved_node_ids: list[str],
    node_texts: dict[str, str],
) -> dict:
    """Compute retrieval quality metrics.

    Args:
        output_text: The generated text (compile/write output)
        retrieved_node_ids: Node IDs that were retrieved for context
        node_texts: Mapping of node_id to primary text content for all graph nodes

    Returns dict with context_nodes_used, context_nodes_retrieved,
    context_precision, and coverage_gaps.
    """
    from wheeler.validation.citations import extract_citations

    # Which retrieved nodes were actually cited?
    cited_ids = set(extract_citations(output_text))
    retrieved_set = set(retrieved_node_ids)
    used = cited_ids & retrieved_set

    context_nodes_used = len(used)
    context_nodes_retrieved = len(retrieved_set)
    context_precision = (
        context_nodes_used / context_nodes_retrieved
        if context_nodes_retrieved > 0
        else 0.0
    )

    # Coverage gaps: extract significant words from output,
    # check if they appear in any graph node's text
    coverage_gaps = _detect_coverage_gaps(output_text, node_texts)

    return {
        "context_nodes_used": context_nodes_used,
        "context_nodes_retrieved": context_nodes_retrieved,
        "context_precision": round(context_precision, 4),
        "coverage_gaps": coverage_gaps,
    }


def _detect_coverage_gaps(output_text: str, node_texts: dict[str, str]) -> list[str]:
    """Find significant terms in output that don't appear in any graph node.

    Uses simple keyword extraction: split on whitespace, filter short words
    and common stop words, check against node text corpus.
    """
    import re

    # Common English stop words (minimal set)
    STOP_WORDS = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor",
        "not", "only", "own", "same", "so", "than", "too", "very", "just",
        "because", "but", "and", "or", "if", "while", "this", "that", "these",
        "those", "it", "its", "we", "our", "they", "their", "which", "what",
        "who", "whom", "also", "about", "up", "one", "two", "new", "first",
    })

    # Extract words from output (lowercase, alpha only, 4+ chars)
    output_words = set(re.findall(r'\b[a-z]{4,}\b', output_text.lower()))
    output_words -= STOP_WORDS

    # Build corpus of all graph node text (lowercase)
    corpus = " ".join(node_texts.values()).lower()

    # Words in output but not in any graph node
    gaps = []
    for word in sorted(output_words):
        if word not in corpus:
            gaps.append(word)

    # Cap at 20 most relevant gaps
    return gaps[:20]


async def store_entry(entry: LedgerEntry, config: WheelerConfig) -> str:
    """Store a ledger entry as a proper Ledger node via the graph backend.

    Uses the same execute_tool dispatch as all other node types, which
    handles dual-write to both graph and knowledge/ JSON files.

    Returns the new node ID.
    """
    from wheeler.tools.graph_tools import execute_tool

    result_str = await execute_tool(
        "add_ledger",
        {
            "mode": entry.mode,
            "prompt_summary": entry.prompt_summary,
            "citations_found": json.dumps(entry.citations_found),
            "citations_valid": json.dumps(entry.citations_valid),
            "citations_invalid": json.dumps(entry.citations_invalid),
            "citations_missing_provenance": json.dumps(entry.citations_missing_provenance),
            "citations_stale": json.dumps(entry.citations_stale),
            "ungrounded": entry.ungrounded,
            "pass_rate": entry.pass_rate,
        },
        config,
    )
    result = json.loads(result_str)
    node_id = result.get("node_id", "")
    logger.info("Stored ledger entry %s (mode=%s, pass_rate=%.0f%%)",
                node_id, entry.mode, entry.pass_rate * 100)
    return node_id
