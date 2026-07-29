"""Assemble the dashboard data dict from the live knowledge graph.

``gather_dashboard_data(config)`` opens one backend, runs the existing
read-only ``query_*`` helpers SEQUENTIALLY (each ``run_cypher`` is independently
sessioned; never ``asyncio.gather`` graph queries), enriches findings from their
``knowledge/{id}.json`` files (so figure-only fields like ``artifact_type`` and
``path`` are available), reconciles local pins/notes, and returns the plain dict
``render`` consumes. This module is read-only: it never mutates the graph and so
does not route through ``execute_tool``.

The ranking/selection/pin/note logic is factored into pure module-level
functions so they unit-test without Neo4j.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)

OPEN_PLAN_STATUSES = ("approved", "in-progress")
SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- pure helpers


def rank_results(findings: list[dict]) -> list[dict]:
    """Rank findings as 'major results': fresh first, then high confidence, then
    high stability. Deterministic (ties broken by id)."""
    return sorted(
        findings,
        key=lambda f: (
            bool(f.get("stale", False)),
            -float(f.get("confidence") or 0.0),
            -float(f.get("stability") or 0.0),
            str(f.get("id", "")),
        ),
    )


def select_open_plans(plans: list[dict]) -> list[dict]:
    """Keep only plans whose status is open (approved or in-progress)."""
    return [p for p in plans if str(p.get("status", "")).lower() in OPEN_PLAN_STATUSES]


def is_figure(f: dict, root: Path) -> bool:
    """True if a finding is a figure with a resolvable, existing file."""
    if str(f.get("artifact_type", "")).lower() != "figure":
        return False
    path = f.get("path") or ""
    if not path:
        return False
    p = Path(path)
    fp = p if p.is_absolute() else (root / p)
    return fp.exists()


def select_figures(findings: list[dict], root: Path) -> list[dict]:
    """Findings that are on-disk figures, in the given order."""
    return [f for f in findings if is_figure(f, root)]


def split_pinned(
    figures: list[dict], pinned_ids: list[str]
) -> tuple[list[dict], list[dict]]:
    """Return (hero, rest). ``hero`` follows pin order and drops dangling pins
    (ids that no longer resolve to a figure). ``rest`` keeps the input order."""
    by_id = {f.get("id"): f for f in figures}
    hero = [by_id[i] for i in pinned_ids if i in by_id]
    pinned_set = {i for i in pinned_ids if i in by_id}
    rest = [f for f in figures if f.get("id") not in pinned_set]
    return hero, rest


# --------------------------------------------------------------------------- local state I/O


def _state_dir(config: WheelerConfig) -> Path:
    root = Path(getattr(config, "project_root", ".") or ".")
    return root / ".wheeler" / "dashboard"


def _read_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _current_tag(config: WheelerConfig) -> str:
    return getattr(config.neo4j, "project_tag", "") if hasattr(config, "neo4j") else ""


def _tag_matches(config: WheelerConfig, data: dict) -> bool:
    """True if the state file belongs to the current project_tag. Files written
    before tag-stamping (no project_tag key) are treated as matching for
    back-compat; a stamped tag that differs from the current one is rejected so
    pins/notes from another namespace do not render against this project."""
    stored = data.get("project_tag")
    if stored is None:
        return True
    return str(stored) == _current_tag(config)


def _write_state(path: Path, payload: dict) -> None:
    """Atomic write (tmp + rename), mirroring knowledge/store.write_node."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.rename(path)


def read_pins(config: WheelerConfig) -> list[str]:
    data = _read_state(_state_dir(config) / "pins.json")
    if not _tag_matches(config, data):
        return []
    pins = data.get("pins", [])
    return [str(x) for x in pins] if isinstance(pins, list) else []


def write_pins(config: WheelerConfig, pins: list[str]) -> None:
    _write_state(
        _state_dir(config) / "pins.json",
        {"project_tag": _current_tag(config), "pins": pins},
    )


# --------------------------------------------------------------------------- figure notes (graph)
#
# A note on a figure is a research fact, so it lives in the graph as a
# ResearchNote (N-) linked RELEVANT_TO the figure (F-), giving it provenance and
# letting it travel with backups: exactly the wh:note / add_note path. The
# dashboard writes these through execute_tool (the only graph writer; lazy
# import, like integrations) and reads them back per figure. The in-browser
# textarea remains a browser-local scratch pad, seeded from the durable note.


async def record_figure_note(config: WheelerConfig, figure_id: str, text: str) -> str | None:
    """Create a ResearchNote and link it RELEVANT_TO the figure. Returns the
    new note id, or None if creation failed. Routes through execute_tool so the
    triple-write (graph + JSON + synthesis) and provenance all apply."""
    from wheeler.tools.graph_tools import execute_tool

    res = json.loads(
        await execute_tool(
            "add_note",
            {
                "content": text,
                "title": f"Dashboard note on {figure_id}",
                "context": "Authored from the Wheeler dashboard",
            },
            config,
        )
    )
    note_id = res.get("node_id")
    if not note_id:
        return None
    await execute_tool(
        "link_nodes",
        {"source_id": note_id, "target_id": figure_id, "relationship": "RELEVANT_TO"},
        config,
    )
    return note_id


async def fetch_figure_notes(backend, figure_ids: list[str], project_tag: str) -> list[dict]:
    """Return ResearchNotes linked RELEVANT_TO any of the given figure ids, as
    rows {fid, nid, content, date}, newest first."""
    if not figure_ids:
        return []
    pw = ""
    params: dict = {"ids": figure_ids}
    if project_tag:
        pw = " AND f._wheeler_project = $ptag AND n._wheeler_project = $ptag"
        params["ptag"] = project_tag
    rows = await backend.run_cypher(
        "MATCH (n:ResearchNote)-[:RELEVANT_TO]->(f:Finding) "
        f"WHERE f.id IN $ids{pw} "
        "RETURN f.id AS fid, n.id AS nid, n.content AS content, n.date AS date "
        "ORDER BY n.date DESC",
        params,
    )
    return [dict(r) for r in rows]


async def list_all_figure_notes(config: WheelerConfig) -> list[dict]:
    """List every ResearchNote linked RELEVANT_TO a figure (for the CLI)."""
    from wheeler.graph.backend import get_backend

    backend = get_backend(config)
    try:
        await backend.initialize()
        ptag = _current_tag(config)
        pw, params = "", {}
        if ptag:
            pw = " WHERE f._wheeler_project = $ptag AND n._wheeler_project = $ptag"
            params["ptag"] = ptag
        rows = await backend.run_cypher(
            "MATCH (n:ResearchNote)-[:RELEVANT_TO]->(f:Finding)"
            f"{pw} RETURN f.id AS fid, n.id AS nid, n.content AS content "
            "ORDER BY n.date DESC",
            params,
        )
        return [dict(r) for r in rows]
    finally:
        await backend.close()


async def fetch_relationships(backend, ids: list[str], project_tag: str) -> dict[str, list[dict]]:
    """Return 1-hop neighbors for each given node id, as a map
    ``{node_id: [{rel, dir, id, label, title}, ...]}``. One Cypher query over all
    ids; project-tag scoped on both endpoints. Deduplicated per node by
    (rel, dir, neighbor_id) so a doubled edge is shown once. Read-only."""
    if not ids:
        return {}
    pw = ""
    params: dict = {"ids": ids}
    if project_tag:
        pw = " AND n._wheeler_project = $ptag AND m._wheeler_project = $ptag"
        params["ptag"] = project_tag
    rows = await backend.run_cypher(
        "MATCH (n)-[r]-(m) "
        f"WHERE n.id IN $ids{pw} "
        "RETURN n.id AS nid, type(r) AS rel, (startNode(r).id = n.id) AS outgoing, "
        "m.id AS oid, labels(m) AS olabels, "
        "coalesce(m.title, m.display_name, m.question, m.statement, m.description, '') "
        "AS otitle",
        params,
    )
    out: dict[str, list[dict]] = {}
    seen: dict[str, set] = {}
    for r in rows:
        r = dict(r)
        nid, oid = r.get("nid"), r.get("oid")
        if not nid or not oid:
            continue
        direction = "out" if r.get("outgoing") else "in"
        key = (r.get("rel"), direction, oid)
        bucket = seen.setdefault(nid, set())
        if key in bucket:
            continue
        bucket.add(key)
        labels = r.get("olabels") or []
        title = (r.get("otitle") or "").strip()
        out.setdefault(nid, []).append({
            "rel": r.get("rel", ""),
            "dir": direction,
            "id": oid,
            "label": labels[0] if labels else "",
            "title": title[:80],
        })
    # Stable order: outgoing first, then by relationship, then neighbor id.
    for nid in out:
        out[nid].sort(key=lambda e: (e["dir"] != "out", e["rel"], e["id"]))
    return out


def _detail_for(node: dict, kind: str) -> dict:
    """Build the clickable-detail record for one node (pure)."""
    def num(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f

    fields: list[list[str]] = []
    if kind == "OpenQuestion":
        content = str(node.get("question") or "")
        title = (node.get("title") or "").strip() or "Open question"
        prio = node.get("priority")
        if prio is not None:
            fields.append(["Priority", str(prio)])
    elif kind == "Plan":
        content = str(node.get("description") or node.get("title") or "")
        title = (node.get("title") or "").strip() or "Plan"
        if node.get("status"):
            fields.append(["Status", str(node["status"])])
        if node.get("updated"):
            fields.append(["Updated", str(node["updated"])])
    else:  # Finding (results, figures, hero)
        content = str(node.get("description") or "")
        title = (node.get("title") or "").strip() or "Finding"
        c = num(node.get("confidence"))
        if c is not None and c > 0:
            fields.append(["Confidence", f"{c:.2f}"])
        if node.get("artifact_type"):
            fields.append(["Type", str(node["artifact_type"])])
        if node.get("stale"):
            fields.append(["Stale", "yes"])
        s = num(node.get("stability"))
        if s is not None and s > 0:
            fields.append(["Stability", f"{s:.2f}"])
    if node.get("tier"):
        fields.append(["Tier", str(node["tier"])])
    if node.get("path"):
        fields.append(["Path", str(node["path"])])
    rec = {"kind": kind, "title": title, "content": content, "fields": fields}
    if node.get("note"):
        rec["note"] = str(node["note"])
        rec["note_id"] = str(node.get("note_id") or "")
    return rec


def build_details(
    sections: list[tuple[str, list[dict]]], rels_by_id: dict[str, list[dict]]
) -> dict[str, dict]:
    """Assemble the id -> detail map from (kind, nodes) sections. A node that
    appears in more than one section (e.g. a figure also in results) is built
    once; the later section may enrich it (e.g. a note on the figure card).
    Relationships are attached from ``rels_by_id``. Pure."""
    details: dict[str, dict] = {}
    for kind, nodes in sections:
        for node in nodes:
            nid = node.get("id")
            if not nid:
                continue
            rec = _detail_for(node, kind)
            if nid in details:
                # Keep first kind/content; fold in a note if this copy has one.
                if rec.get("note") and not details[nid].get("note"):
                    details[nid]["note"] = rec["note"]
                    details[nid]["note_id"] = rec.get("note_id", "")
                continue
            rec["rels"] = rels_by_id.get(nid, [])
            details[nid] = rec
    return details


def attach_graph_notes(figures: list[dict], note_rows: list[dict]) -> None:
    """Attach the newest ResearchNote per figure (content + id) to each figure
    dict. Pure; rows are pre-sorted newest-first. Replaces each entry with a
    copy so it never aliases the same finding object shown in the results zone."""
    latest: dict = {}
    for r in note_rows:
        fid = r.get("fid")
        if fid is not None and fid not in latest:
            latest[fid] = r  # first seen = newest (rows sorted date DESC)
    for i, f in enumerate(figures):
        row = latest.get(f.get("id"))
        if row:
            figures[i] = {**f, "note": row.get("content", ""), "note_id": row.get("nid", "")}
        else:
            figures[i] = dict(f)


# --------------------------------------------------------------------------- enrichment


def _enrich_finding(knowledge_path: Path | None, f: dict) -> dict:
    """Merge figure-only fields (path, artifact_type, title, stale, stability)
    from the knowledge JSON file into a finding dict returned by query_findings."""
    if knowledge_path is None:
        return f
    try:
        from wheeler.knowledge.store import read_node

        model = read_node(knowledge_path, f.get("id", ""))
    except FileNotFoundError:
        return f
    except Exception:
        logger.debug("enrichment failed for %s", f.get("id"), exc_info=True)
        return f
    f = dict(f)
    f["path"] = getattr(model, "path", "")
    f["artifact_type"] = getattr(model, "artifact_type", "")
    f["title"] = getattr(model, "title", "")
    f["stale"] = getattr(model, "stale", False)
    f["stability"] = getattr(model, "stability", 0.0)
    return f


def _figure_from_id(knowledge_path: Path | None, node_id: str, root: Path) -> dict | None:
    """Load a figure finding directly by id (used so a pinned figure that is
    older than the fetched findings window is never silently dropped). Returns a
    finding dict if the node is a figure with an existing file, else None."""
    if knowledge_path is None or not node_id:
        return None
    try:
        from wheeler.knowledge.store import read_node

        model = read_node(knowledge_path, node_id)
    except FileNotFoundError:
        return None
    except Exception:
        logger.debug("could not load pinned figure %s", node_id, exc_info=True)
        return None
    f = {
        "id": getattr(model, "id", node_id),
        "description": getattr(model, "description", ""),
        "confidence": getattr(model, "confidence", 0.0),
        "tier": getattr(model, "tier", "generated"),
        "path": getattr(model, "path", ""),
        "artifact_type": getattr(model, "artifact_type", ""),
        "title": getattr(model, "title", ""),
        "stale": getattr(model, "stale", False),
        "stability": getattr(model, "stability", 0.0),
    }
    return f if is_figure(f, root) else None


# --------------------------------------------------------------------------- main entry


async def gather_dashboard_data(
    config: WheelerConfig, *, limit: int = 12, plan_id: str | None = None
) -> dict[str, Any]:
    """Open the backend, query the graph read-only, and build the render dict."""
    from wheeler.graph.backend import get_backend
    from wheeler.tools.graph_tools.queries import (
        query_findings,
        query_open_questions,
        query_plans,
    )

    knowledge_path = Path(config.knowledge_path) if getattr(config, "knowledge_path", None) else None
    project_root = str(Path(getattr(config, "project_root", ".") or ".").resolve())
    project_tag = getattr(config.neo4j, "project_tag", "") if hasattr(config, "neo4j") else ""

    backend = get_backend(config)
    try:
        await backend.initialize()
        q_raw = await query_open_questions(backend, {"_config": config, "limit": limit})
        # Two passes for the two open statuses (query_plans takes a single status).
        plans_acc: list[dict] = []
        for status in OPEN_PLAN_STATUSES:
            pr = await query_plans(
                backend, {"_config": config, "status": status, "limit": max(limit * 2, 40)}
            )
            plans_acc.extend(json.loads(pr).get("plans", []))
        # Fetch findings generously: figure selection filters on a JSON-only field,
        # so a small limit would silently hide figures past the cut.
        f_raw = await query_findings(
            backend, {"_config": config, "limit": max(limit * 4, 200)}
        )

        questions = json.loads(q_raw).get("questions", [])[:limit]
        open_plans = select_open_plans(plans_acc)
        open_plans.sort(
            key=lambda p: (str(p.get("updated", "")), str(p.get("id", ""))), reverse=True
        )
        open_plans = open_plans[:limit]

        findings = json.loads(f_raw).get("findings", [])
        enriched = [_enrich_finding(knowledge_path, f) for f in findings]

        root = Path(project_root)
        all_figures = select_figures(enriched, root)

        # A pinned figure may be older than the fetched findings window; load any
        # such pins directly so they are never silently dropped from the hero.
        pins = read_pins(config)
        present = {f.get("id") for f in all_figures}
        for pid in pins:
            if pid not in present:
                extra = _figure_from_id(knowledge_path, pid, root)
                if extra is not None:
                    all_figures.append(extra)
                    present.add(pid)

        # Pull figure notes from the graph (ResearchNote -RELEVANT_TO-> figure).
        note_rows = await fetch_figure_notes(
            backend, [str(f.get("id", "")) for f in all_figures], project_tag
        )

        attach_graph_notes(all_figures, note_rows)
        hero, rest_figures = split_pinned(all_figures, pins)
        results = rank_results(enriched)[:limit]
        figures = rest_figures[:limit]

        # 1-hop relationships for every node shown, for the click-through detail
        # panel. Gathered inside the open backend (one extra read), then folded
        # into a pure id -> detail map.
        shown_ids = {
            str(n.get("id"))
            for group in (questions, open_plans, results, hero, figures)
            for n in group
            if n.get("id")
        }
        rels_by_id = await fetch_relationships(backend, sorted(shown_ids), project_tag)
        counts = await backend.count_all()
    finally:
        await backend.close()

    details = build_details(
        [
            ("OpenQuestion", questions),
            ("Plan", open_plans),
            ("Finding", results),
            ("Finding", hero),
            ("Finding", figures),
        ],
        rels_by_id,
    )
    clean_counts = {k: v for k, v in (counts or {}).items() if not str(k).startswith("_")}

    return {
        "schema_version": SCHEMA_VERSION,
        "title": "Wheeler Research Dashboard",
        "generated": _now_iso(),
        "project": project_tag,
        "meta": {"project_root": project_root},
        "counts": clean_counts,
        "hero": hero,
        "questions": questions,
        "plans": open_plans,
        "results": results,
        "figures": figures,
        "details": details,
    }


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
