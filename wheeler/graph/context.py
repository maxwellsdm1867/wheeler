"""Size-limited graph context injection for pre-query enrichment.

Fetches recent findings, open questions, and active hypotheses from
Neo4j and formats them into a compact context block (< 500 tokens).
This is injected before the user's prompt in CHAT and PLANNING modes.
"""

from __future__ import annotations

import logging

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)
from wheeler.graph.driver import get_async_driver  # noqa: E402


def _project_filter(alias: str, project_tag: str) -> str:
    """Return a Cypher WHERE fragment for project namespace isolation.

    When *project_tag* is non-empty, returns something like
    ``" AND f._wheeler_project = $ptag"``.  Otherwise returns ``""``.
    """
    if not project_tag:
        return ""
    return f" AND {alias}._wheeler_project = $ptag"


async def fetch_context(config: WheelerConfig, topic: str = "") -> str:
    """Pull size-limited graph context for prompt injection.

    Returns a formatted string with recent findings, open questions,
    and active hypotheses, bounded by config limits. Findings are split
    by tier (reference vs generated) so downstream agents can distinguish
    established knowledge from new work.

    When *topic* is non-empty, results are filtered to those containing
    the topic string (case-insensitive substring match on the relevant
    text field for each node type).

    Queries run sequentially within one session -- Neo4j sessions are not
    safe for concurrent queries via asyncio.gather.
    """
    driver = get_async_driver(config)
    sections: list[str] = []
    project_tag = config.neo4j.project_tag
    # Extra params dict: includes ptag only when namespacing is active
    extra: dict = {}
    if project_tag:
        extra["ptag"] = project_tag

    pf = _project_filter("f", project_tag)
    pq = _project_filter("q", project_tag)
    ph = _project_filter("h", project_tag)

    # Optional topic filter (case-insensitive substring match)
    topic = topic.strip() if topic else ""
    tf_findings = ""
    tf_questions = ""
    tf_hypotheses = ""
    topic_params: dict = {}
    if topic:
        tf_findings = " AND toLower(f.description) CONTAINS toLower($topic)"
        tf_questions = " AND toLower(q.question) CONTAINS toLower($topic)"
        tf_hypotheses = " AND toLower(h.statement) CONTAINS toLower($topic)"
        topic_params = {"topic": topic}

    try:
        async with driver.session(database=config.neo4j.database) as session:
            # Reference findings
            result = await session.run(
                "MATCH (f:Finding) WHERE f.tier = 'reference'"
                f"{pf}{tf_findings} "
                "RETURN f.id AS id, f.description AS desc "
                "ORDER BY f.date DESC LIMIT $limit",
                limit=config.context_max_findings,
                **extra, **topic_params,
            )
            ref_findings = [r async for r in result]

            # Generated findings (includes null tier for backward compat)
            result = await session.run(
                "MATCH (f:Finding) WHERE (f.tier IS NULL OR f.tier = 'generated')"
                f"{pf}{tf_findings} "
                "RETURN f.id AS id, f.description AS desc "
                "ORDER BY f.date DESC LIMIT $limit",
                limit=config.context_max_findings,
                **extra, **topic_params,
            )
            gen_findings = [r async for r in result]

            # Open questions
            result = await session.run(
                "MATCH (q:OpenQuestion) WHERE true"
                f"{pq}{tf_questions} "
                "RETURN q.id AS id, q.question AS question "
                "ORDER BY q.priority DESC LIMIT $limit",
                limit=config.context_max_questions,
                **extra, **topic_params,
            )
            questions = [r async for r in result]

            # Active hypotheses
            result = await session.run(
                "MATCH (h:Hypothesis) WHERE h.status = 'open'"
                f"{ph}{tf_hypotheses} "
                "RETURN h.id AS id, h.statement AS stmt LIMIT $limit",
                limit=config.context_max_hypotheses,
                **extra, **topic_params,
            )
            hypotheses = [r async for r in result]

            if ref_findings:
                lines = [f"- [{r['id']}] {r['desc']}" for r in ref_findings]
                sections.append("### Established Knowledge (reference)\n" + "\n".join(lines))
            if gen_findings:
                lines = [f"- [{r['id']}] {r['desc']}" for r in gen_findings]
                sections.append("### Recent Work (generated)\n" + "\n".join(lines))
            if questions:
                lines = [f"- [{r['id']}] {r['question']}" for r in questions]
                sections.append("### Open Questions\n" + "\n".join(lines))
            if hypotheses:
                lines = [f"- [{r['id']}] {r['stmt']}" for r in hypotheses]
                sections.append("### Active Hypotheses\n" + "\n".join(lines))
    except Exception as exc:
        logger.warning("fetch_context failed (Neo4j offline?): %s", exc)
        return ""

    if not sections:
        return ""
    # TODO: Once graph nodes carry a `title` field, context injection can
    # use short titles from knowledge files instead of full descriptions,
    # keeping the context block compact while still being informative.
    header = "## Research Context (from knowledge graph)"
    if topic:
        header += f" -- topic: {topic}"
    return header + "\n\n" + "\n\n".join(sections)
