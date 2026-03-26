"""Graph query tools: search nodes, find gaps.

Query functions use Cypher for filtering, ordering, and limiting, then
try to enrich each result with full content from the knowledge file
(``knowledge/{node_id}.json``).  Falls back to graph-only data when a
file doesn't exist (pre-migration nodes or when knowledge_path is not
configured).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _knowledge_path_from_args(args: dict) -> Path | None:
    """Extract and return knowledge_path from the injected _config, or None."""
    config: WheelerConfig | None = args.pop("_config", None)
    if config is None:
        return None
    kp = getattr(config, "knowledge_path", None)
    return Path(kp) if kp else None


def _read_knowledge_node(knowledge_path: Path | None, node_id: str):  # noqa: ANN202
    """Try to load a node from its JSON knowledge file.

    Returns the Pydantic model on success, or ``None`` on any failure.
    """
    if knowledge_path is None:
        return None
    try:
        from wheeler.knowledge.store import read_node

        return read_node(knowledge_path, node_id)
    except FileNotFoundError:
        return None
    except Exception:
        logger.debug("Failed to read knowledge file for %s", node_id, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------


async def query_findings(session, args: dict) -> str:
    knowledge_path = _knowledge_path_from_args(args)
    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        result = await session.run(
            "MATCH (f:Finding) WHERE toLower(f.description) CONTAINS toLower($kw) "
            "RETURN f.id AS id, f.description AS desc, f.confidence AS conf, f.date AS date "
            "ORDER BY f.date DESC LIMIT $limit",
            kw=keyword,
            limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (f:Finding) "
            "RETURN f.id AS id, f.description AS desc, f.confidence AS conf, f.date AS date "
            "ORDER BY f.date DESC LIMIT $limit",
            limit=limit,
        )
    records = [r async for r in result]

    findings = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(knowledge_path, node_id)
        if model is not None:
            findings.append({
                "id": model.id,
                "description": model.description,
                "confidence": model.confidence,
                "date": model.created,
                "tier": model.tier,
            })
        else:
            findings.append({
                "id": node_id,
                "description": r["desc"],
                "confidence": r["conf"],
                "date": r["date"],
            })

    return json.dumps({"findings": findings, "count": len(findings)})


async def query_open_questions(session, args: dict) -> str:
    knowledge_path = _knowledge_path_from_args(args)
    limit = int(args.get("limit", 10))

    result = await session.run(
        "MATCH (q:OpenQuestion) "
        "RETURN q.id AS id, q.question AS question, q.priority AS priority "
        "ORDER BY q.priority DESC LIMIT $limit",
        limit=limit,
    )
    records = [r async for r in result]

    questions = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(knowledge_path, node_id)
        if model is not None:
            questions.append({
                "id": model.id,
                "question": model.question,
                "priority": model.priority,
                "tier": model.tier,
            })
        else:
            questions.append({
                "id": node_id,
                "question": r["question"],
                "priority": r["priority"],
            })

    return json.dumps({"questions": questions, "count": len(questions)})


async def query_hypotheses(session, args: dict) -> str:
    knowledge_path = _knowledge_path_from_args(args)
    status = args.get("status", "all")
    limit = int(args.get("limit", 10))

    if status and status != "all":
        result = await session.run(
            "MATCH (h:Hypothesis {status: $status}) "
            "RETURN h.id AS id, h.statement AS stmt, h.status AS status "
            "LIMIT $limit",
            status=status,
            limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (h:Hypothesis) "
            "RETURN h.id AS id, h.statement AS stmt, h.status AS status "
            "LIMIT $limit",
            limit=limit,
        )
    records = [r async for r in result]

    hypotheses = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(knowledge_path, node_id)
        if model is not None:
            hypotheses.append({
                "id": model.id,
                "statement": model.statement,
                "status": model.status,
                "tier": model.tier,
            })
        else:
            hypotheses.append({
                "id": node_id,
                "statement": r["stmt"],
                "status": r["status"],
            })

    return json.dumps({"hypotheses": hypotheses, "count": len(hypotheses)})


async def query_datasets(session, args: dict) -> str:
    knowledge_path = _knowledge_path_from_args(args)
    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        result = await session.run(
            "MATCH (d:Dataset) WHERE toLower(d.description) CONTAINS toLower($kw) "
            "OR toLower(d.path) CONTAINS toLower($kw) "
            "RETURN d.id AS id, d.path AS path, d.type AS type, "
            "d.description AS desc, d.date_added AS date "
            "ORDER BY d.date_added DESC LIMIT $limit",
            kw=keyword,
            limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (d:Dataset) "
            "RETURN d.id AS id, d.path AS path, d.type AS type, "
            "d.description AS desc, d.date_added AS date "
            "ORDER BY d.date_added DESC LIMIT $limit",
            limit=limit,
        )
    records = [r async for r in result]

    datasets = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(knowledge_path, node_id)
        if model is not None:
            datasets.append({
                "id": model.id,
                "path": model.path,
                "type": model.data_type,
                "description": model.description,
                "date_added": model.created,
                "tier": model.tier,
            })
        else:
            datasets.append({
                "id": node_id,
                "path": r["path"],
                "type": r["type"],
                "description": r["desc"],
                "date_added": r["date"],
            })

    return json.dumps({"datasets": datasets, "count": len(datasets)})


async def query_papers(session, args: dict) -> str:
    knowledge_path = _knowledge_path_from_args(args)
    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        result = await session.run(
            "MATCH (p:Paper) WHERE toLower(p.title) CONTAINS toLower($kw) "
            "OR toLower(p.authors) CONTAINS toLower($kw) "
            "RETURN p.id AS id, p.title AS title, p.authors AS authors, "
            "p.doi AS doi, p.year AS year "
            "ORDER BY p.year DESC LIMIT $limit",
            kw=keyword,
            limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (p:Paper) "
            "RETURN p.id AS id, p.title AS title, p.authors AS authors, "
            "p.doi AS doi, p.year AS year "
            "ORDER BY p.year DESC LIMIT $limit",
            limit=limit,
        )
    records = [r async for r in result]

    papers = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(knowledge_path, node_id)
        if model is not None:
            papers.append({
                "id": model.id,
                "title": model.title,
                "authors": model.authors,
                "doi": model.doi,
                "year": model.year,
                "tier": model.tier,
            })
        else:
            papers.append({
                "id": node_id,
                "title": r["title"],
                "authors": r["authors"],
                "doi": r["doi"],
                "year": r["year"],
            })

    return json.dumps({"papers": papers, "count": len(papers)})


async def query_documents(session, args: dict) -> str:
    knowledge_path = _knowledge_path_from_args(args)
    keyword = args.get("keyword", "")
    status = args.get("status", "")
    limit = int(args.get("limit", 10))

    if keyword and status:
        result = await session.run(
            "MATCH (w:Document {status: $status}) "
            "WHERE toLower(w.title) CONTAINS toLower($kw) "
            "RETURN w.id AS id, w.title AS title, w.path AS path, "
            "w.section AS section, w.status AS status, w.date AS date "
            "ORDER BY w.date DESC LIMIT $limit",
            kw=keyword,
            status=status,
            limit=limit,
        )
    elif keyword:
        result = await session.run(
            "MATCH (w:Document) "
            "WHERE toLower(w.title) CONTAINS toLower($kw) "
            "RETURN w.id AS id, w.title AS title, w.path AS path, "
            "w.section AS section, w.status AS status, w.date AS date "
            "ORDER BY w.date DESC LIMIT $limit",
            kw=keyword,
            limit=limit,
        )
    elif status:
        result = await session.run(
            "MATCH (w:Document {status: $status}) "
            "RETURN w.id AS id, w.title AS title, w.path AS path, "
            "w.section AS section, w.status AS status, w.date AS date "
            "ORDER BY w.date DESC LIMIT $limit",
            status=status,
            limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (w:Document) "
            "RETURN w.id AS id, w.title AS title, w.path AS path, "
            "w.section AS section, w.status AS status, w.date AS date "
            "ORDER BY w.date DESC LIMIT $limit",
            limit=limit,
        )
    records = [r async for r in result]

    documents = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(knowledge_path, node_id)
        if model is not None:
            documents.append({
                "id": model.id,
                "title": model.title,
                "path": model.path,
                "section": model.section,
                "status": model.status,
                "date": model.created,
                "tier": model.tier,
            })
        else:
            documents.append({
                "id": node_id,
                "title": r["title"],
                "path": r["path"],
                "section": r["section"],
                "status": r["status"],
                "date": r["date"],
            })

    return json.dumps({"documents": documents, "count": len(documents)})


async def query_notes(session, args: dict) -> str:
    knowledge_path = _knowledge_path_from_args(args)

    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        result = await session.run(
            "MATCH (n:ResearchNote) "
            "WHERE toLower(n.title) CONTAINS toLower($kw) "
            "OR toLower(n.content) CONTAINS toLower($kw) "
            "RETURN n.id AS id, n.title AS title, n.content AS content, "
            "n.context AS context, n.date AS date, n.tier AS tier "
            "ORDER BY n.date DESC LIMIT $limit",
            kw=keyword, limit=limit,
        )
    else:
        result = await session.run(
            "MATCH (n:ResearchNote) "
            "RETURN n.id AS id, n.title AS title, n.content AS content, "
            "n.context AS context, n.date AS date, n.tier AS tier "
            "ORDER BY n.date DESC LIMIT $limit",
            limit=limit,
        )

    records = [r async for r in result]
    notes = []
    for r in records:
        node_id = r["id"]
        node = _read_knowledge_node(knowledge_path, node_id)
        if node:
            notes.append({
                "id": node.id, "title": node.title, "content": node.content,
                "context": node.context, "date": node.created, "tier": node.tier,
            })
        else:
            notes.append({
                "id": node_id, "title": r.get("title", ""), "content": r.get("content", ""),
                "context": r.get("context", ""), "date": r.get("date", ""),
                "tier": r.get("tier", "generated"),
            })

    return json.dumps({"notes": notes, "count": len(notes)})


async def graph_gaps(session, args: dict | None = None) -> str:
    """Find knowledge gaps: unlinked questions, unsupported hypotheses, stale analyses.

    Queries run sequentially within one session — Neo4j sessions are not
    safe for concurrent queries via asyncio.gather.
    """
    if args is None:
        args = {}
    knowledge_path = _knowledge_path_from_args(args)

    result = await session.run(
        "MATCH (q:OpenQuestion) "
        "WHERE NOT (q)<-[:AROSE_FROM]-() AND NOT ()-[:RELEVANT_TO]->(q) "
        "RETURN q.id AS id, coalesce(q.question, '') AS question, "
        "coalesce(q.priority, 0) AS priority "
        "ORDER BY q.priority DESC LIMIT 10"
    )
    q_records = [r async for r in result]

    result = await session.run(
        "MATCH (h:Hypothesis {status: 'open'}) "
        "WHERE NOT ()-[:SUPPORTS|CONTRADICTS]->(h) "
        "RETURN h.id AS id, h.statement AS stmt "
        "LIMIT 10"
    )
    h_records = [r async for r in result]

    result = await session.run(
        "MATCH (a:Analysis) "
        "WHERE NOT (a)-[:GENERATED]->(:Finding) "
        "RETURN a.id AS id, coalesce(a.script_path, '') AS path "
        "LIMIT 10"
    )
    a_records = [r async for r in result]

    result = await session.run(
        "MATCH (f:Finding) "
        "WHERE NOT (f)-[:APPEARS_IN]->(:Document) "
        "RETURN f.id AS id, coalesce(f.description, '') AS desc "
        "ORDER BY f.date DESC LIMIT 10"
    )
    f_records = [r async for r in result]

    result = await session.run(
        "MATCH (p:Paper) "
        "WHERE NOT (p)-[:INFORMED|RELEVANT_TO|CITES|APPEARS_IN]->() "
        "AND NOT ()-[:BASED_ON|REFERENCED_IN]->(p) "
        "RETURN p.id AS id, coalesce(p.title, '') AS title "
        "LIMIT 10"
    )
    p_records = [r async for r in result]

    # Enrich gap results with knowledge file data where available
    unlinked_questions = []
    for r in q_records:
        model = _read_knowledge_node(knowledge_path, r["id"])
        if model is not None:
            unlinked_questions.append({
                "id": model.id, "question": model.question, "priority": model.priority,
            })
        else:
            unlinked_questions.append({
                "id": r["id"], "question": r["question"], "priority": r["priority"],
            })

    unsupported_hypotheses = []
    for r in h_records:
        model = _read_knowledge_node(knowledge_path, r["id"])
        if model is not None:
            unsupported_hypotheses.append({
                "id": model.id, "statement": model.statement,
            })
        else:
            unsupported_hypotheses.append({
                "id": r["id"], "statement": r["stmt"],
            })

    unreported_findings = []
    for r in f_records:
        model = _read_knowledge_node(knowledge_path, r["id"])
        if model is not None:
            unreported_findings.append({
                "id": model.id, "description": model.description,
            })
        else:
            unreported_findings.append({
                "id": r["id"], "description": r["desc"],
            })

    orphaned_papers = []
    for r in p_records:
        model = _read_knowledge_node(knowledge_path, r["id"])
        if model is not None:
            orphaned_papers.append({
                "id": model.id, "title": model.title,
            })
        else:
            orphaned_papers.append({
                "id": r["id"], "title": r["title"],
            })

    gaps: dict = {
        "unlinked_questions": unlinked_questions,
        "unsupported_hypotheses": unsupported_hypotheses,
        "analyses_without_findings": [
            {"id": r["id"], "script_path": r["path"]}
            for r in a_records
        ],
        "unreported_findings": unreported_findings,
        "orphaned_papers": orphaned_papers,
    }
    gaps["total_gaps"] = sum(len(v) for v in gaps.values() if isinstance(v, list))
    return json.dumps(gaps)
