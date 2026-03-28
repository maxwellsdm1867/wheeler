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
