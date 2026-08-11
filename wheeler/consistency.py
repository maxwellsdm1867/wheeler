"""Consistency checker for Wheeler's triple-write layers.

Compares inventories across graph (Neo4j), knowledge files (JSON),
and synthesis files (markdown) to detect drift and optionally repair it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from wheeler.config import (
    project_knowledge_dir,
    project_synthesis_dir,
    WheelerConfig,
)
from wheeler.models import PREFIX_TO_LABEL

logger = logging.getLogger(__name__)


def is_node_view(stem: str) -> bool:
    """Whether a synthesis filename stem names a NODE, not an index or report.

    `synthesis/` holds two unrelated kinds of file. Node views (`F-3a2b1c4d.md`)
    are rendered from `knowledge/{id}.json` and are meaningfully "orphaned" when
    that JSON is gone. Index and report views (`INDEX.md`, `MORNING-2026-08-08.md`)
    are written by acts, have no backing JSON by design, and are the scientist's
    output.

    This used to be a hardcoded set of three names: INDEX, OPEN_QUESTIONS and
    EVIDENCE_MAP. `/wh:dream` writes a fourth, `MORNING-{date}.md`, on every run.
    It therefore landed in `synthesis_orphaned` and `repair_consistency` DELETED
    the morning brief. An allowlist of literal names cannot survive a new index
    file being added; a structural rule can.

    The rule: a stem is a node view only if it begins with a known node-id
    prefix followed by "-". Both misclassifications fall the safe way. A node
    view misread as an index is merely not cleaned up, so drift persists but
    nothing is destroyed. The reverse, which is the destructive direction, can
    only happen if an index file is deliberately named like a node id.
    """
    prefix, sep, _rest = stem.partition("-")
    return bool(sep) and prefix in PREFIX_TO_LABEL

# Divergent-node count above which routine health checks warn loudly
DRIFT_WARNING_THRESHOLD = 10


@dataclass
class ConsistencyReport:
    """Result of comparing the three storage layers."""

    graph_only: list[str] = field(default_factory=list)        # in graph, not in JSON
    json_only: list[str] = field(default_factory=list)         # in JSON, not in graph
    synthesis_missing: list[str] = field(default_factory=list)  # in JSON, no synthesis
    synthesis_orphaned: list[str] = field(default_factory=list)  # synthesis exists, no JSON
    # Present on disk but not parseable as a knowledge node. A DIFFERENT problem
    # from json_only, and separated because the remedy differs: json_only is
    # expected drift, unreadable needs a migration or a repair.
    unreadable: list[str] = field(default_factory=list)
    total_graph: int = 0
    total_json: int = 0
    total_synthesis: int = 0


async def audit_paths(config: WheelerConfig) -> dict:
    """Report the portable/absolute mix of stored file paths on this machine.

    The graph holds both spellings indefinitely: portable (``${PROJECT}/a.py``)
    for anything written since portable paths landed, absolute for everything
    before, upgraded opportunistically as artifacts are touched. That hybrid is
    fine, but it must not be invisible. Without this the only way to learn that
    half a graph still holds one machine's absolute paths is to carry it to
    another computer and watch the file references fail.

    Buckets, per node with a non-empty ``path``:

    - ``portable`` / ``absolute``: which spelling is stored
    - ``resolvable``: this machine can turn it into a local path at all
    - ``present``: that local path actually exists on disk
    - ``by_root``: which named root each portable path uses, with absolute paths
      under ``(absolute)`` and portable paths naming a root this machine does not
      configure under ``(unconfigured)``
    """
    from wheeler.portability import is_portable, resolve as resolve_portable
    from wheeler.tools.graph_tools import _get_backend

    try:
        # `_get_backend` is INSIDE the try because it initialises the backend,
        # which connects. Leaving it outside made an unreachable graph raise out
        # of here and take the whole consistency check down with it, when the
        # rest of that check (JSON and synthesis inventories) is pure file I/O
        # and still has something useful to say. `check_consistency` degrades the
        # same way for the same reason.
        backend = await _get_backend(config)
        records = await backend.run_cypher(
            "MATCH (n) WHERE n.path IS NOT NULL AND n.path <> '' "
            "RETURN n.path AS path"
        )
    except Exception as exc:
        logger.warning("Cannot query graph for path audit: %s", exc)
        return {"error": str(exc), "total": 0}

    roots = config.resolved_roots
    counts = {"total": 0, "portable": 0, "absolute": 0, "resolvable": 0, "present": 0}
    by_root: dict[str, int] = {}

    for rec in records:
        stored = rec.get("path") or ""
        if not stored:
            continue
        counts["total"] += 1

        if is_portable(stored):
            counts["portable"] += 1
            root_name = stored[2 : stored.index("}")].lower()
        else:
            counts["absolute"] += 1
            root_name = "(absolute)"

        resolved = resolve_portable(stored, roots)
        if resolved is None:
            by_root["(unconfigured)"] = by_root.get("(unconfigured)", 0) + 1
            continue

        by_root[root_name] = by_root.get(root_name, 0) + 1
        counts["resolvable"] += 1
        try:
            if resolved.exists():
                counts["present"] += 1
        except OSError:  # pragma: no cover - unreadable mount
            pass

    return {
        **counts,
        "by_root": dict(sorted(by_root.items(), key=lambda kv: kv[1], reverse=True)),
        "configured_roots": sorted(roots),
    }


async def check_consistency(config: WheelerConfig) -> ConsistencyReport:
    """Compare graph, knowledge/, and synthesis/ inventories."""
    from wheeler.tools.graph_tools import _get_backend

    backend = await _get_backend(config)

    # Graph inventory
    try:
        records = await backend.run_cypher("MATCH (n) RETURN n.id AS id")
        graph_ids = {r["id"] for r in records if r.get("id")}
    except Exception as exc:
        logger.warning("Cannot query graph for consistency check: %s", exc)
        graph_ids = set()

    # JSON inventory
    knowledge_dir = project_knowledge_dir(config)
    if knowledge_dir.is_dir():
        json_ids = {f.stem for f in knowledge_dir.glob("*.json")}
    else:
        json_ids = set()

    # Synthesis inventory: node views only. Index and report views (INDEX.md,
    # MORNING-{date}.md, ...) have no backing JSON by design, so counting them
    # here would report them as orphaned and get them deleted by repair.
    synthesis_dir = project_synthesis_dir(config)
    if synthesis_dir.is_dir():
        synth_ids = {
            f.stem for f in synthesis_dir.glob("*.md") if is_node_view(f.stem)
        }
    else:
        synth_ids = set()

    # Split "in JSON, not in graph" into genuine drift versus files that do not
    # parse at all.
    #
    # These two inventories disagreed silently: `store.list_nodes` parses each
    # file and DROPS an unparseable one with only a log line, while the glob
    # above counts it. A legacy `A-4d9c7c5d.json` (type "Analysis", a label
    # retired in favour of Script) made this checkout report 27,213 files by
    # glob and 27,212 by list_nodes. The drift detector was wrong by one and
    # nothing said so.
    #
    # Only the json_only candidates are test-parsed, never the whole store.
    # Cost is proportional to drift rather than to store size, which matters:
    # parsing all of knowledge/ takes ~3.7s at 27k nodes against ~33ms for the
    # glob. The tradeoff is that an unparseable file which DOES have a graph
    # node is not detected here; that needs the content-hash sidecar planned in
    # Tier 1 of docs/boundary-audit.md.
    json_only_candidates = sorted(json_ids - graph_ids)
    json_only: list[str] = []
    unreadable: list[str] = []
    if json_only_candidates:
        from wheeler.knowledge.store import read_node

        for node_id in json_only_candidates:
            try:
                read_node(knowledge_dir, node_id)
                json_only.append(node_id)
            except Exception as exc:
                logger.warning(
                    "Unreadable knowledge file %s: %s. Run "
                    "`wheeler graph migrate-prov` if it is a legacy node.",
                    node_id, exc,
                )
                unreadable.append(node_id)

    return ConsistencyReport(
        graph_only=sorted(graph_ids - json_ids),
        json_only=json_only,
        synthesis_missing=sorted(json_ids - synth_ids),
        synthesis_orphaned=sorted(synth_ids - json_ids),
        unreadable=unreadable,
        total_graph=len(graph_ids),
        total_json=len(json_ids),
        total_synthesis=len(synth_ids),
    )


def summarize_drift(
    report: ConsistencyReport,
    threshold: int = DRIFT_WARNING_THRESHOLD,
) -> dict:
    """Compact drift summary for embedding in routine health/status output.

    Counts divergent nodes per category and breaks json_only and graph_only
    down by node-ID prefix so that an entire missing node class (e.g. all
    legacy A-* Analysis files present only in JSON) is visible at a glance.
    """
    def _by_prefix(ids: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for nid in ids:
            prefix = nid.split("-", 1)[0] if "-" in nid else nid
            counts[prefix] = counts.get(prefix, 0) + 1
        return counts

    # `unreadable` counts toward divergence. Excluding it would let the summary
    # report "0 divergent" while a knowledge file cannot be parsed at all,
    # which is the same silent blindness that let the two inventories disagree
    # by one for months.
    total_divergent = (
        len(report.graph_only)
        + len(report.json_only)
        + len(report.synthesis_missing)
        + len(report.synthesis_orphaned)
        + len(report.unreadable)
    )
    summary: dict = {
        "total_divergent": total_divergent,
        "graph_only": len(report.graph_only),
        "json_only": len(report.json_only),
        "synthesis_missing": len(report.synthesis_missing),
        "synthesis_orphaned": len(report.synthesis_orphaned),
        "unreadable": len(report.unreadable),
        "threshold": threshold,
        "exceeds_threshold": total_divergent > threshold,
    }
    if report.unreadable:
        summary["unreadable_ids"] = sorted(report.unreadable)
        summary["unreadable_fix"] = (
            "run `wheeler graph migrate-prov` if these are legacy nodes"
        )
    if report.json_only:
        summary["json_only_by_prefix"] = _by_prefix(report.json_only)
    if report.graph_only:
        summary["graph_only_by_prefix"] = _by_prefix(report.graph_only)
    return summary


async def repair_consistency(
    config: WheelerConfig,
    report: ConsistencyReport,
    dry_run: bool = True,
) -> dict:
    """Repair detected drift between layers. Returns action log.

    Repairs:
    - synthesis_missing: read JSON, render markdown, write synthesis file
    - synthesis_orphaned: delete orphaned synthesis files
    - graph_only: warn only (regenerating JSON from graph is complex)
    - json_only: warn only (may be pre-migration or graph delete failed)
    - unreadable: warn only, with the remedy (a migration, not a repair)
    """
    actions: list[dict] = []

    # synthesis_missing: regenerate from JSON
    for node_id in report.synthesis_missing:
        if dry_run:
            actions.append({"node_id": node_id, "action": "regenerate_synthesis", "dry_run": True})
            continue
        try:
            from wheeler.knowledge.store import read_node, write_synthesis
            from wheeler.knowledge.render import render_synthesis

            knowledge_dir = project_knowledge_dir(config)
            synthesis_dir = project_synthesis_dir(config)
            model = read_node(knowledge_dir, node_id)
            markdown = render_synthesis(model, roots=config.resolved_roots)
            write_synthesis(synthesis_dir, node_id, markdown)
            actions.append({"node_id": node_id, "action": "regenerate_synthesis", "status": "ok"})
        except Exception as exc:
            actions.append({"node_id": node_id, "action": "regenerate_synthesis", "status": "error", "error": str(exc)})

    # synthesis_orphaned: delete stale markdown
    for node_id in report.synthesis_orphaned:
        # Refuse at the deletion site as well as at the inventory. This is the
        # only irreversible action in the repair path, and the caller supplies
        # the list: a report built by an older or buggy check_consistency, or
        # hand-assembled, must not be able to unlink a scientist's morning
        # brief. Checking only where the list is built would leave that open.
        if not is_node_view(node_id):
            logger.warning(
                "Refusing to delete %s.md: not a node view. Index and report "
                "views have no backing JSON by design.", node_id,
            )
            actions.append({
                "node_id": node_id,
                "action": "delete_orphaned_synthesis",
                "status": "refused_not_a_node_view",
            })
            continue
        if dry_run:
            actions.append({"node_id": node_id, "action": "delete_orphaned_synthesis", "dry_run": True})
            continue
        try:
            path = project_synthesis_dir(config) / f"{node_id}.md"
            if path.exists():
                path.unlink()
            actions.append({"node_id": node_id, "action": "delete_orphaned_synthesis", "status": "ok"})
        except Exception as exc:
            actions.append({"node_id": node_id, "action": "delete_orphaned_synthesis", "status": "error", "error": str(exc)})

    # graph_only and json_only: warn only
    for node_id in report.graph_only:
        actions.append({"node_id": node_id, "action": "warn_graph_only"})
    for node_id in report.json_only:
        actions.append({"node_id": node_id, "action": "warn_json_only"})
    # unreadable: warn with the remedy, which is a migration rather than a
    # repair. Never auto-migrate here: rewriting a file the checker cannot
    # parse is the wrong thing to do without the scientist looking at it.
    for node_id in report.unreadable:
        actions.append({
            "node_id": node_id,
            "action": "warn_unreadable",
            "fix": "run `wheeler graph migrate-prov` if this is a legacy node",
        })

    return {"dry_run": dry_run, "actions": actions, "total": len(actions)}
