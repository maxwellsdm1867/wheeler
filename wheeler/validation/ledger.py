"""Provenance ledger: logs every interaction with citation audit results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

from wheeler.config import WheelerConfig
from wheeler.validation.citations import CitationResult, CitationStatus


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


async def store_entry(entry: LedgerEntry, config: WheelerConfig) -> None:
    """Store a ledger entry as a Ledger node in Neo4j."""
    driver = AsyncGraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )
    try:
        async with driver.session(database=config.neo4j.database) as session:
            await session.run(
                "CREATE (l:Ledger {"
                "  timestamp: $timestamp,"
                "  mode: $mode,"
                "  prompt_summary: $prompt_summary,"
                "  citations_found: $citations_found,"
                "  citations_valid: $citations_valid,"
                "  citations_invalid: $citations_invalid,"
                "  citations_missing_provenance: $citations_missing_provenance,"
                "  citations_stale: $citations_stale,"
                "  ungrounded: $ungrounded,"
                "  pass_rate: $pass_rate"
                "})",
                timestamp=entry.timestamp,
                mode=entry.mode,
                prompt_summary=entry.prompt_summary,
                citations_found=entry.citations_found,
                citations_valid=entry.citations_valid,
                citations_invalid=entry.citations_invalid,
                citations_missing_provenance=entry.citations_missing_provenance,
                citations_stale=entry.citations_stale,
                ungrounded=entry.ungrounded,
                pass_rate=entry.pass_rate,
            )
    finally:
        await driver.close()
