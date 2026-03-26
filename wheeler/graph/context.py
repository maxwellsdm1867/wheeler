"""Size-limited graph context injection for pre-query enrichment.

Fetches recent findings, open questions, and active hypotheses from
Neo4j and formats them into a compact context block (< 500 tokens).
This is injected before the user's prompt in CHAT and PLANNING modes.
"""

from __future__ import annotations

import logging

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)
from wheeler.graph.driver import get_async_driver, close_async_driver


# Backward-compatible aliases
_get_driver = get_async_driver


async def prewarm_driver(config: WheelerConfig) -> None:
    """Pre-warm the singleton driver so first query pays no creation cost."""
    get_async_driver(config)


async def close_driver():
    """Close the singleton driver. Call on shutdown."""
    await close_async_driver()


async def fetch_context(config: WheelerConfig) -> str:
    """Pull size-limited graph context for prompt injection.

    Returns a formatted string with recent findings, open questions,
    and active hypotheses, bounded by config limits. Findings are split
    by tier (reference vs generated) so downstream agents can distinguish
    established knowledge from new work.

    Queries run sequentially within one session — Neo4j sessions are not
    safe for concurrent queries via asyncio.gather.
    """
    driver = get_async_driver(config)
    sections: list[str] = []
    try:
        async with driver.session(database=config.neo4j.database) as session:
            # Reference findings
            result = await session.run(
                "MATCH (f:Finding) WHERE f.tier = 'reference' "
                "RETURN f.id AS id, f.description AS desc "
                "ORDER BY f.date DESC LIMIT $limit",
                limit=config.context_max_findings,
            )
            ref_findings = [r async for r in result]

            # Generated findings (includes null tier for backward compat)
            result = await session.run(
                "MATCH (f:Finding) WHERE f.tier IS NULL OR f.tier = 'generated' "
                "RETURN f.id AS id, f.description AS desc "
                "ORDER BY f.date DESC LIMIT $limit",
                limit=config.context_max_findings,
            )
            gen_findings = [r async for r in result]

            # Open questions
            result = await session.run(
                "MATCH (q:OpenQuestion) RETURN q.id AS id, q.question AS q "
                "ORDER BY q.priority DESC LIMIT $limit",
                limit=config.context_max_questions,
            )
            questions = [r async for r in result]

            # Active hypotheses
            result = await session.run(
                "MATCH (h:Hypothesis {status: 'open'}) "
                "RETURN h.id AS id, h.statement AS stmt LIMIT $limit",
                limit=config.context_max_hypotheses,
            )
            hypotheses = [r async for r in result]

            if ref_findings:
                lines = [f"- [{r['id']}] {r['desc']}" for r in ref_findings]
                sections.append("### Established Knowledge (reference)\n" + "\n".join(lines))
            if gen_findings:
                lines = [f"- [{r['id']}] {r['desc']}" for r in gen_findings]
                sections.append("### Recent Work (generated)\n" + "\n".join(lines))
            if questions:
                lines = [f"- [{r['id']}] {r['q']}" for r in questions]
                sections.append("### Open Questions\n" + "\n".join(lines))
            if hypotheses:
                lines = [f"- [{r['id']}] {r['stmt']}" for r in hypotheses]
                sections.append("### Active Hypotheses\n" + "\n".join(lines))
    except Exception as exc:
        logger.warning("fetch_context failed (Neo4j offline?): %s", exc)
        return ""

    if not sections:
        return ""
    return "## Research Context (from knowledge graph)\n\n" + "\n\n".join(sections)
