"""Graph query tools: search nodes, find gaps.

All handlers take a ``GraphBackend`` instance (not a raw session) and
use ``backend.run_cypher()`` for queries that need filtering/ordering
beyond what ``query_nodes`` supports.

Query functions try to enrich each result with full content from the
knowledge file (``knowledge/{node_id}.json``).  Falls back to graph-only
data when a file doesn't exist (pre-migration nodes).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _QueryContext:
    """Holds config-derived values needed by query functions."""
    knowledge_path: Path | None
    project_tag: str


def _extract_context(args: dict) -> _QueryContext:
    """Pop the injected _config and return a QueryContext.

    Extracts both the knowledge_path (for JSON file enrichment) and
    the project_tag (for Community Edition namespace isolation).
    """
    config: WheelerConfig | None = args.pop("_config", None)
    if config is None:
        return _QueryContext(knowledge_path=None, project_tag="")
    kp = getattr(config, "knowledge_path", None)
    ptag = getattr(config.neo4j, "project_tag", "") if hasattr(config, "neo4j") else ""
    return _QueryContext(
        knowledge_path=Path(kp) if kp else None,
        project_tag=ptag or "",
    )


def _project_where(alias: str, project_tag: str, *, has_existing_where: bool) -> str:
    """Return a Cypher WHERE / AND fragment for project namespace filtering.

    Parameters
    ----------
    alias:
        The Cypher node alias (e.g. ``"f"``).
    project_tag:
        The project namespace tag.  If empty, returns ``""``.
    has_existing_where:
        If ``True``, prepend ``" AND "`` instead of ``" WHERE "``.
    """
    if not project_tag:
        return ""
    prefix = " AND " if has_existing_where else " WHERE "
    return f"{prefix}{alias}._wheeler_project = $ptag"


def _inject_ptag(params: dict, project_tag: str) -> dict:
    """Add $ptag to params dict when project namespacing is active."""
    if project_tag:
        params["ptag"] = project_tag
    return params


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


async def query_findings(backend, args: dict) -> str:
    ctx = _extract_context(args)
    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))
    pw = _project_where("f", ctx.project_tag, has_existing_where=True)

    if keyword:
        records = await backend.run_cypher(
            "MATCH (f:Finding) WHERE toLower(f.description) CONTAINS toLower($kw)"
            f"{pw} "
            "RETURN f.id AS id, f.description AS description, f.confidence AS conf, f.date AS date "
            "ORDER BY f.date DESC LIMIT $limit",
            _inject_ptag({"kw": keyword, "limit": limit}, ctx.project_tag),
        )
    else:
        records = await backend.run_cypher(
            "MATCH (f:Finding)"
            f"{_project_where('f', ctx.project_tag, has_existing_where=False)} "
            "RETURN f.id AS id, f.description AS description, f.confidence AS conf, f.date AS date "
            "ORDER BY f.date DESC LIMIT $limit",
            _inject_ptag({"limit": limit}, ctx.project_tag),
        )

    findings = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(ctx.knowledge_path, node_id)
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
                "description": r["description"],
                "confidence": r["conf"],
                "date": r["date"],
            })

    return json.dumps({"findings": findings, "count": len(findings)})


async def query_open_questions(backend, args: dict) -> str:
    ctx = _extract_context(args)
    limit = int(args.get("limit", 10))

    records = await backend.run_cypher(
        "MATCH (q:OpenQuestion)"
        f"{_project_where('q', ctx.project_tag, has_existing_where=False)} "
        "RETURN q.id AS id, q.question AS question, q.priority AS priority "
        "ORDER BY q.priority DESC LIMIT $limit",
        _inject_ptag({"limit": limit}, ctx.project_tag),
    )

    questions = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(ctx.knowledge_path, node_id)
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


async def query_hypotheses(backend, args: dict) -> str:
    ctx = _extract_context(args)
    status = args.get("status", "all")
    limit = int(args.get("limit", 10))

    if status and status != "all":
        pw = _project_where("h", ctx.project_tag, has_existing_where=True)
        records = await backend.run_cypher(
            "MATCH (h:Hypothesis) WHERE h.status = $status"
            f"{pw} "
            "RETURN h.id AS id, h.statement AS stmt, h.status AS status "
            "LIMIT $limit",
            _inject_ptag({"status": status, "limit": limit}, ctx.project_tag),
        )
    else:
        records = await backend.run_cypher(
            "MATCH (h:Hypothesis)"
            f"{_project_where('h', ctx.project_tag, has_existing_where=False)} "
            "RETURN h.id AS id, h.statement AS stmt, h.status AS status "
            "LIMIT $limit",
            _inject_ptag({"limit": limit}, ctx.project_tag),
        )

    hypotheses = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(ctx.knowledge_path, node_id)
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


async def query_datasets(backend, args: dict) -> str:
    ctx = _extract_context(args)
    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        pw = _project_where("d", ctx.project_tag, has_existing_where=True)
        records = await backend.run_cypher(
            "MATCH (d:Dataset) WHERE (toLower(d.description) CONTAINS toLower($kw) "
            "OR toLower(d.path) CONTAINS toLower($kw))"
            f"{pw} "
            "RETURN d.id AS id, d.path AS path, d.type AS type, "
            "d.description AS description, d.date_added AS date "
            "ORDER BY d.date_added DESC LIMIT $limit",
            _inject_ptag({"kw": keyword, "limit": limit}, ctx.project_tag),
        )
    else:
        records = await backend.run_cypher(
            "MATCH (d:Dataset)"
            f"{_project_where('d', ctx.project_tag, has_existing_where=False)} "
            "RETURN d.id AS id, d.path AS path, d.type AS type, "
            "d.description AS description, d.date_added AS date "
            "ORDER BY d.date_added DESC LIMIT $limit",
            _inject_ptag({"limit": limit}, ctx.project_tag),
        )

    datasets = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(ctx.knowledge_path, node_id)
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
                "description": r["description"],
                "date_added": r["date"],
            })

    return json.dumps({"datasets": datasets, "count": len(datasets)})


async def query_papers(backend, args: dict) -> str:
    ctx = _extract_context(args)
    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        pw = _project_where("p", ctx.project_tag, has_existing_where=True)
        records = await backend.run_cypher(
            "MATCH (p:Paper) WHERE (toLower(p.title) CONTAINS toLower($kw) "
            "OR toLower(p.authors) CONTAINS toLower($kw))"
            f"{pw} "
            "RETURN p.id AS id, p.title AS title, p.authors AS authors, "
            "p.doi AS doi, p.year AS year "
            "ORDER BY p.year DESC LIMIT $limit",
            _inject_ptag({"kw": keyword, "limit": limit}, ctx.project_tag),
        )
    else:
        records = await backend.run_cypher(
            "MATCH (p:Paper)"
            f"{_project_where('p', ctx.project_tag, has_existing_where=False)} "
            "RETURN p.id AS id, p.title AS title, p.authors AS authors, "
            "p.doi AS doi, p.year AS year "
            "ORDER BY p.year DESC LIMIT $limit",
            _inject_ptag({"limit": limit}, ctx.project_tag),
        )

    papers = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(ctx.knowledge_path, node_id)
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


async def query_documents(backend, args: dict) -> str:
    ctx = _extract_context(args)
    keyword = args.get("keyword", "")
    status = args.get("status", "")
    limit = int(args.get("limit", 10))

    if keyword and status:
        pw = _project_where("w", ctx.project_tag, has_existing_where=True)
        records = await backend.run_cypher(
            "MATCH (w:Document) WHERE w.status = $status "
            "AND toLower(w.title) CONTAINS toLower($kw)"
            f"{pw} "
            "RETURN w.id AS id, w.title AS title, w.path AS path, "
            "w.section AS section, w.status AS status, w.date AS date "
            "ORDER BY w.date DESC LIMIT $limit",
            _inject_ptag({"kw": keyword, "status": status, "limit": limit}, ctx.project_tag),
        )
    elif keyword:
        pw = _project_where("w", ctx.project_tag, has_existing_where=True)
        records = await backend.run_cypher(
            "MATCH (w:Document) "
            "WHERE toLower(w.title) CONTAINS toLower($kw)"
            f"{pw} "
            "RETURN w.id AS id, w.title AS title, w.path AS path, "
            "w.section AS section, w.status AS status, w.date AS date "
            "ORDER BY w.date DESC LIMIT $limit",
            _inject_ptag({"kw": keyword, "limit": limit}, ctx.project_tag),
        )
    elif status:
        pw = _project_where("w", ctx.project_tag, has_existing_where=True)
        records = await backend.run_cypher(
            "MATCH (w:Document) WHERE w.status = $status"
            f"{pw} "
            "RETURN w.id AS id, w.title AS title, w.path AS path, "
            "w.section AS section, w.status AS status, w.date AS date "
            "ORDER BY w.date DESC LIMIT $limit",
            _inject_ptag({"status": status, "limit": limit}, ctx.project_tag),
        )
    else:
        records = await backend.run_cypher(
            "MATCH (w:Document)"
            f"{_project_where('w', ctx.project_tag, has_existing_where=False)} "
            "RETURN w.id AS id, w.title AS title, w.path AS path, "
            "w.section AS section, w.status AS status, w.date AS date "
            "ORDER BY w.date DESC LIMIT $limit",
            _inject_ptag({"limit": limit}, ctx.project_tag),
        )

    documents = []
    for r in records:
        node_id = r["id"]
        model = _read_knowledge_node(ctx.knowledge_path, node_id)
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


async def query_notes(backend, args: dict) -> str:
    ctx = _extract_context(args)

    keyword = args.get("keyword", "")
    limit = int(args.get("limit", 10))

    if keyword:
        pw = _project_where("n", ctx.project_tag, has_existing_where=True)
        records = await backend.run_cypher(
            "MATCH (n:ResearchNote) "
            "WHERE (toLower(n.title) CONTAINS toLower($kw) "
            "OR toLower(n.content) CONTAINS toLower($kw))"
            f"{pw} "
            "RETURN n.id AS id, n.title AS title, n.content AS content, "
            "n.context AS context, n.date AS date, n.tier AS tier "
            "ORDER BY n.date DESC LIMIT $limit",
            _inject_ptag({"kw": keyword, "limit": limit}, ctx.project_tag),
        )
    else:
        records = await backend.run_cypher(
            "MATCH (n:ResearchNote)"
            f"{_project_where('n', ctx.project_tag, has_existing_where=False)} "
            "RETURN n.id AS id, n.title AS title, n.content AS content, "
            "n.context AS context, n.date AS date, n.tier AS tier "
            "ORDER BY n.date DESC LIMIT $limit",
            _inject_ptag({"limit": limit}, ctx.project_tag),
        )

    notes = []
    for r in records:
        node_id = r["id"]
        node = _read_knowledge_node(ctx.knowledge_path, node_id)
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


async def graph_gaps(backend, args: dict | None = None) -> str:
    """Find knowledge gaps: unlinked questions, unsupported hypotheses, stale analyses."""
    if args is None:
        args = {}
    ctx = _extract_context(args)

    # Build project WHERE fragments for each alias
    pw_q = _project_where("q", ctx.project_tag, has_existing_where=True)
    pw_h = _project_where("h", ctx.project_tag, has_existing_where=True)
    pw_a = _project_where("a", ctx.project_tag, has_existing_where=True)
    pw_f = _project_where("f", ctx.project_tag, has_existing_where=True)
    pw_p = _project_where("p", ctx.project_tag, has_existing_where=True)

    q_records = await backend.run_cypher(
        "MATCH (q:OpenQuestion) "
        "WHERE NOT (q)<-[:AROSE_FROM]-() AND NOT ()-[:RELEVANT_TO]->(q)"
        f"{pw_q} "
        "RETURN q.id AS id, coalesce(q.question, '') AS question, "
        "coalesce(q.priority, 0) AS priority "
        "ORDER BY q.priority DESC LIMIT 10",
        _inject_ptag({}, ctx.project_tag) or None,
    )

    h_records = await backend.run_cypher(
        "MATCH (h:Hypothesis) WHERE h.status = 'open' "
        "AND NOT ()-[:SUPPORTS|CONTRADICTS]->(h)"
        f"{pw_h} "
        "RETURN h.id AS id, h.statement AS stmt "
        "LIMIT 10",
        _inject_ptag({}, ctx.project_tag) or None,
    )

    a_records = await backend.run_cypher(
        "MATCH (a:Analysis) "
        "WHERE NOT (a)-[:GENERATED]->(:Finding)"
        f"{pw_a} "
        "RETURN a.id AS id, coalesce(a.script_path, '') AS path "
        "LIMIT 10",
        _inject_ptag({}, ctx.project_tag) or None,
    )

    f_records = await backend.run_cypher(
        "MATCH (f:Finding) "
        "WHERE NOT (f)-[:APPEARS_IN]->(:Document)"
        f"{pw_f} "
        "RETURN f.id AS id, coalesce(f.description, '') AS description "
        "ORDER BY f.date DESC LIMIT 10",
        _inject_ptag({}, ctx.project_tag) or None,
    )

    p_records = await backend.run_cypher(
        "MATCH (p:Paper) "
        "WHERE NOT (p)-[:INFORMED|RELEVANT_TO|CITES|APPEARS_IN]->() "
        "AND NOT ()-[:BASED_ON|REFERENCED_IN]->(p)"
        f"{pw_p} "
        "RETURN p.id AS id, coalesce(p.title, '') AS title "
        "LIMIT 10",
        _inject_ptag({}, ctx.project_tag) or None,
    )

    # Enrich gap results with knowledge file data where available
    unlinked_questions = []
    for r in q_records:
        model = _read_knowledge_node(ctx.knowledge_path, r["id"])
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
        model = _read_knowledge_node(ctx.knowledge_path, r["id"])
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
        model = _read_knowledge_node(ctx.knowledge_path, r["id"])
        if model is not None:
            unreported_findings.append({
                "id": model.id, "description": model.description,
            })
        else:
            unreported_findings.append({
                "id": r["id"], "description": r["description"],
            })

    orphaned_papers = []
    for r in p_records:
        model = _read_knowledge_node(ctx.knowledge_path, r["id"])
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
