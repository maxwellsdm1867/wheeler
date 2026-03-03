"""Size-limited graph context injection for pre-query enrichment.

Fetches recent findings, open questions, and active hypotheses from
Neo4j and formats them into a compact context block (< 500 tokens).
This is injected before the user's prompt in CHAT and PLANNING modes.

Phase 2 will wire this into the engine's query pipeline.
"""

from __future__ import annotations

from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

from wheeler.config import WheelerConfig


async def fetch_context(config: WheelerConfig) -> str:
    """Pull size-limited graph context for prompt injection.

    Returns a formatted string with recent findings, open questions,
    and active hypotheses, bounded by config limits.
    """
    driver = AsyncGraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )
    sections: list[str] = []
    try:
        async with driver.session(database=config.neo4j.database) as session:
            # Recent findings
            result = await session.run(
                "MATCH (f:Finding) RETURN f.id AS id, f.description AS desc "
                "ORDER BY f.date DESC LIMIT $limit",
                limit=config.context_max_findings,
            )
            findings = [r async for r in result]
            if findings:
                lines = [f"- [{r['id']}] {r['desc']}" for r in findings]
                sections.append("### Recent Findings\n" + "\n".join(lines))

            # Open questions
            result = await session.run(
                "MATCH (q:OpenQuestion) RETURN q.id AS id, q.question AS q "
                "ORDER BY q.priority DESC LIMIT $limit",
                limit=config.context_max_questions,
            )
            questions = [r async for r in result]
            if questions:
                lines = [f"- [{r['id']}] {r['q']}" for r in questions]
                sections.append("### Open Questions\n" + "\n".join(lines))

            # Active hypotheses
            result = await session.run(
                "MATCH (h:Hypothesis {status: 'open'}) "
                "RETURN h.id AS id, h.statement AS stmt LIMIT $limit",
                limit=config.context_max_hypotheses,
            )
            hypotheses = [r async for r in result]
            if hypotheses:
                lines = [f"- [{r['id']}] {r['stmt']}" for r in hypotheses]
                sections.append("### Active Hypotheses\n" + "\n".join(lines))
    finally:
        await driver.close()

    if not sections:
        return ""
    return "## Research Context (from knowledge graph)\n\n" + "\n\n".join(sections)
