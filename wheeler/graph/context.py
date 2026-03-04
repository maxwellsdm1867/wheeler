"""Size-limited graph context injection for pre-query enrichment.

Fetches recent findings, open questions, and active hypotheses from
Neo4j and formats them into a compact context block (< 500 tokens).
This is injected before the user's prompt in CHAT and PLANNING modes.
"""

from __future__ import annotations

import asyncio

from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

from wheeler.config import WheelerConfig

# Singleton driver — reused across queries to avoid 100ms+ creation overhead.
_driver = None
_driver_uri: str | None = None


def _get_driver(config: WheelerConfig):
    global _driver, _driver_uri
    uri = config.neo4j.uri
    if _driver is not None and _driver_uri == uri:
        return _driver
    _driver = AsyncGraphDatabase.driver(
        uri,
        auth=(config.neo4j.username, config.neo4j.password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )
    _driver_uri = uri
    return _driver


async def prewarm_driver(config: WheelerConfig) -> None:
    """Pre-warm the singleton driver so first query pays no creation cost."""
    _get_driver(config)


async def close_driver():
    """Close the singleton driver. Call on shutdown."""
    global _driver, _driver_uri
    if _driver is not None:
        await _driver.close()
        _driver = None
        _driver_uri = None


async def fetch_context(config: WheelerConfig) -> str:
    """Pull size-limited graph context for prompt injection.

    Returns a formatted string with recent findings, open questions,
    and active hypotheses, bounded by config limits. Runs all three
    queries concurrently for ~60-100ms savings.
    """
    driver = _get_driver(config)
    sections: list[str] = []
    try:
        async with driver.session(database=config.neo4j.database) as session:
            # Run all 3 queries concurrently
            findings_result, questions_result, hypotheses_result = (
                await asyncio.gather(
                    session.run(
                        "MATCH (f:Finding) RETURN f.id AS id, f.description AS desc "
                        "ORDER BY f.date DESC LIMIT $limit",
                        limit=config.context_max_findings,
                    ),
                    session.run(
                        "MATCH (q:OpenQuestion) RETURN q.id AS id, q.question AS q "
                        "ORDER BY q.priority DESC LIMIT $limit",
                        limit=config.context_max_questions,
                    ),
                    session.run(
                        "MATCH (h:Hypothesis {status: 'open'}) "
                        "RETURN h.id AS id, h.statement AS stmt LIMIT $limit",
                        limit=config.context_max_hypotheses,
                    ),
                )
            )

            # Consume results (can also be parallel, but records are small)
            findings = [r async for r in findings_result]
            questions = [r async for r in questions_result]
            hypotheses = [r async for r in hypotheses_result]

            if findings:
                lines = [f"- [{r['id']}] {r['desc']}" for r in findings]
                sections.append("### Recent Findings\n" + "\n".join(lines))
            if questions:
                lines = [f"- [{r['id']}] {r['q']}" for r in questions]
                sections.append("### Open Questions\n" + "\n".join(lines))
            if hypotheses:
                lines = [f"- [{r['id']}] {r['stmt']}" for r in hypotheses]
                sections.append("### Active Hypotheses\n" + "\n".join(lines))
    except Exception:
        raise

    if not sections:
        return ""
    return "## Research Context (from knowledge graph)\n\n" + "\n\n".join(sections)
