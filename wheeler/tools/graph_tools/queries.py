"""Graph query tools: search nodes, find gaps."""

from __future__ import annotations

import json


async def query_findings(session, args: dict) -> str:
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
    findings = [
        {"id": r["id"], "description": r["desc"], "confidence": r["conf"], "date": r["date"]}
        for r in records
    ]
    return json.dumps({"findings": findings, "count": len(findings)})


async def query_open_questions(session, args: dict) -> str:
    limit = int(args.get("limit", 10))
    result = await session.run(
        "MATCH (q:OpenQuestion) "
        "RETURN q.id AS id, q.question AS question, q.priority AS priority "
        "ORDER BY q.priority DESC LIMIT $limit",
        limit=limit,
    )
    records = [r async for r in result]
    questions = [
        {"id": r["id"], "question": r["question"], "priority": r["priority"]}
        for r in records
    ]
    return json.dumps({"questions": questions, "count": len(questions)})


async def query_hypotheses(session, args: dict) -> str:
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
    hypotheses = [
        {"id": r["id"], "statement": r["stmt"], "status": r["status"]}
        for r in records
    ]
    return json.dumps({"hypotheses": hypotheses, "count": len(hypotheses)})


async def query_datasets(session, args: dict) -> str:
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
    datasets = [
        {"id": r["id"], "path": r["path"], "type": r["type"],
         "description": r["desc"], "date_added": r["date"]}
        for r in records
    ]
    return json.dumps({"datasets": datasets, "count": len(datasets)})


async def query_papers(session, args: dict) -> str:
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
    papers = [
        {"id": r["id"], "title": r["title"], "authors": r["authors"],
         "doi": r["doi"], "year": r["year"]}
        for r in records
    ]
    return json.dumps({"papers": papers, "count": len(papers)})


async def query_documents(session, args: dict) -> str:
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
    documents = [
        {"id": r["id"], "title": r["title"], "path": r["path"],
         "section": r["section"], "status": r["status"], "date": r["date"]}
        for r in records
    ]
    return json.dumps({"documents": documents, "count": len(documents)})


async def graph_gaps(session) -> str:
    """Find knowledge gaps: unlinked questions, unsupported hypotheses, stale analyses.

    Queries run sequentially within one session — Neo4j sessions are not
    safe for concurrent queries via asyncio.gather.
    """
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

    gaps: dict = {
        "unlinked_questions": [
            {"id": r["id"], "question": r["question"], "priority": r["priority"]}
            for r in q_records
        ],
        "unsupported_hypotheses": [
            {"id": r["id"], "statement": r["stmt"]}
            for r in h_records
        ],
        "analyses_without_findings": [
            {"id": r["id"], "script_path": r["path"]}
            for r in a_records
        ],
        "unreported_findings": [
            {"id": r["id"], "description": r["desc"]}
            for r in f_records
        ],
        "orphaned_papers": [
            {"id": r["id"], "title": r["title"]}
            for r in p_records
        ],
    }
    gaps["total_gaps"] = sum(len(v) for v in gaps.values() if isinstance(v, list))
    return json.dumps(gaps)
