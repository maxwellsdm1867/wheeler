"""Bulk provenance registration: many nodes, artifacts and edges in one call.

Prototype for issue #116, measured by the #117 experiment. Every write still
goes through :func:`execute_tool`, one item at a time, so the triple-write,
receipts, trace ids and embeddings are untouched. What changes is the API
shape: the caller describes a whole execution's provenance once, instead of
one model round trip per edge.

Manifest shape (JSON or YAML, a plain dict in Python)::

    nodes:                      # non-file nodes, any add_* tool
      - alias: "@exec"
        type: execution         # execution | finding | hypothesis | question | note
        kind: script_run
        description: "..."
      - alias: "@f1"
        type: finding
        description: "..."
        confidence: 0.7
    artifacts:                  # files on disk, routed to ensure_artifact
      - alias: "@fig1"
        path: figures/a.png
        title: "..."
        description: "..."
    edges:                      # either dicts or [source, relationship, target]
      - {source: "@fig1", relationship: WAS_GENERATED_BY, target: "@exec"}
      - ["@exec", "USED", "D-1234abcd"]

An alias starts with ``@`` and is defined by exactly one node or artifact in
the same manifest. Edge endpoints are aliases or literal node ids. Order of
sections is fixed (nodes, then artifacts, then edges) so every edge can resolve.

Failure policy: one bad item never aborts the batch. Each item reports its
own status; the top-level ``status`` is ``ok``, ``partial`` or ``failed``.
There is no rollback, matching the external-call failsafe elsewhere in
Wheeler: what was written is reported truthfully, nothing is undone.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.graph.schema import ALLOWED_RELATIONSHIPS, PREFIX_TO_LABEL

logger = logging.getLogger(__name__)

# Node "type" in a manifest -> add_* tool. Papers, datasets, scripts, plans and
# documents are files or reference entities: register them as artifacts (or
# with the dedicated add_* tool directly), not here.
NODE_TYPE_TO_TOOL: dict[str, str] = {
    "execution": "add_execution",
    "finding": "add_finding",
    "hypothesis": "add_hypothesis",
    "question": "add_question",
    "note": "add_note",
}

_ALIAS_RE = re.compile(r"^@[A-Za-z0-9_][A-Za-z0-9_.-]*$")
_NODE_ID_RE = re.compile(r"^([A-Z]{1,3})-[0-9a-f]{4,}$")

_RESERVED_ITEM_KEYS = {"alias", "type"}


def _alias_map_from_rel(rel: str) -> str:
    from .mutations import RELATIONSHIP_ALIASES

    return RELATIONSHIP_ALIASES.get(rel, rel)


def _normalize_edge(raw: Any) -> dict | None:
    """Accept ``{source, relationship, target}`` or ``[src, rel, dst]``."""
    if isinstance(raw, dict):
        src = raw.get("source") or raw.get("src") or raw.get("from")
        rel = raw.get("relationship") or raw.get("rel") or raw.get("type")
        dst = raw.get("target") or raw.get("dst") or raw.get("to")
        props = raw.get("rel_props") or raw.get("props")
    elif isinstance(raw, (list, tuple)) and len(raw) in (3, 4):
        src, rel, dst = raw[0], raw[1], raw[2]
        props = raw[3] if len(raw) == 4 else None
    else:
        return None
    if not (isinstance(src, str) and isinstance(rel, str) and isinstance(dst, str)):
        return None
    edge: dict = {"source": src.strip(), "relationship": rel.strip().upper(), "target": dst.strip()}
    if isinstance(props, dict) and props:
        edge["rel_props"] = props
    return edge


def _is_node_id(value: str) -> bool:
    m = _NODE_ID_RE.match(value)
    return m is not None and m.group(1) in PREFIX_TO_LABEL


def validate_manifest(
    manifest: dict,
    *,
    base_dir: Path | None = None,
) -> tuple[list[str], dict]:
    """Structural validation, no graph access.

    Returns ``(errors, normalized)``. ``normalized`` has the three sections as
    lists of dicts with ``alias`` present (possibly empty) and artifact paths
    resolved against *base_dir*. It is what :func:`register_batch` consumes.
    """
    errors: list[str] = []
    base = Path(base_dir) if base_dir else Path.cwd()

    nodes = list(manifest.get("nodes") or [])
    artifacts = list(manifest.get("artifacts") or [])
    edges_raw = list(manifest.get("edges") or [])

    if not (nodes or artifacts or edges_raw):
        errors.append("manifest is empty: no nodes, artifacts or edges")

    aliases: dict[str, str] = {}  # alias -> where it was defined

    def _take_alias(item: dict, where: str) -> str:
        alias = str(item.get("alias") or "").strip()
        if not alias:
            return ""
        if not _ALIAS_RE.match(alias):
            errors.append(f"{where}: alias {alias!r} must look like '@name'")
            return ""
        if alias in aliases:
            errors.append(f"{where}: alias {alias!r} already defined by {aliases[alias]}")
            return alias
        aliases[alias] = where
        return alias

    norm_nodes: list[dict] = []
    for i, item in enumerate(nodes):
        where = f"nodes[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        ntype = str(item.get("type") or "").strip().lower()
        if ntype not in NODE_TYPE_TO_TOOL:
            errors.append(
                f"{where}: type {ntype!r} not one of {sorted(NODE_TYPE_TO_TOOL)}; "
                "register files under 'artifacts'"
            )
        alias = _take_alias(item, where)
        fields = {k: v for k, v in item.items() if k not in _RESERVED_ITEM_KEYS}
        norm_nodes.append({"alias": alias, "type": ntype, "fields": fields})

    norm_artifacts: list[dict] = []
    for i, item in enumerate(artifacts):
        where = f"artifacts[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        alias = _take_alias(item, where)
        raw_path = str(item.get("path") or "").strip()
        if not raw_path:
            errors.append(f"{where}: 'path' is required")
            resolved = ""
        else:
            p = Path(raw_path)
            if not p.is_absolute():
                p = base / p
            resolved = str(p.resolve())
            if not p.exists():
                errors.append(f"{where}: file not found: {raw_path}")
        fields = {k: v for k, v in item.items() if k not in _RESERVED_ITEM_KEYS}
        fields["path"] = resolved
        norm_artifacts.append({"alias": alias, "fields": fields})

    norm_edges: list[dict] = []
    for i, raw in enumerate(edges_raw):
        where = f"edges[{i}]"
        edge = _normalize_edge(raw)
        if edge is None:
            errors.append(f"{where}: must be {{source, relationship, target}} or [src, rel, dst]")
            continue
        rel = _alias_map_from_rel(edge["relationship"])
        if rel not in ALLOWED_RELATIONSHIPS:
            errors.append(
                f"{where}: relationship {edge['relationship']!r} not allowed; "
                f"one of {ALLOWED_RELATIONSHIPS}"
            )
        edge["relationship"] = rel
        for end in ("source", "target"):
            ref = edge[end]
            if ref.startswith("@"):
                if ref not in aliases:
                    errors.append(f"{where}: {end} alias {ref!r} is not defined in this manifest")
            elif not _is_node_id(ref):
                errors.append(
                    f"{where}: {end} {ref!r} is neither an '@alias' nor a node id like 'F-1a2b3c4d'"
                )
        norm_edges.append(edge)

    normalized = {"nodes": norm_nodes, "artifacts": norm_artifacts, "edges": norm_edges}
    return errors, normalized


async def _literal_ids_missing(normalized: dict, backend) -> list[str]:
    """Which literal node ids referenced by edges do not exist in the graph."""
    missing: list[str] = []
    seen: set[str] = set()
    for edge in normalized["edges"]:
        for end in ("source", "target"):
            ref = edge[end]
            if ref.startswith("@") or ref in seen:
                continue
            seen.add(ref)
            label = PREFIX_TO_LABEL.get(ref.split("-", 1)[0])
            try:
                node = await backend.get_node(label, ref) if label else None
            except Exception as exc:  # pragma: no cover - backend outage
                logger.warning("dry-run existence check failed for %s: %s", ref, exc)
                node = None
            if node is None:
                missing.append(ref)
    return missing


async def register_batch(
    manifest: dict,
    config: WheelerConfig,
    *,
    session_id: str = "",
    dry_run: bool = False,
    base_dir: Path | None = None,
) -> dict:
    """Register a manifest's nodes, artifacts and edges. See module docstring.

    With ``dry_run=True`` nothing is written: the report lists structural
    errors plus any literal node ids that do not exist in the graph, which is
    exactly what a caller needs to fix a manifest once before the real write.
    """
    from . import _get_backend, execute_tool

    errors, normalized = validate_manifest(manifest, base_dir=base_dir)
    counts = {
        "nodes": len(normalized["nodes"]),
        "artifacts": len(normalized["artifacts"]),
        "edges": len(normalized["edges"]),
    }

    if dry_run:
        report: dict = {"dry_run": True, "counts": counts, "errors": errors}
        try:
            backend = await _get_backend(config)
            report["unresolved_ids"] = await _literal_ids_missing(normalized, backend)
        except Exception as exc:
            report["unresolved_ids"] = []
            report["warnings"] = [f"graph unreachable, literal ids not checked: {exc}"]
        report["ok"] = not errors and not report["unresolved_ids"]
        return report

    if errors:
        # Structural errors are cheap to fix and expensive to half-apply.
        return {
            "status": "failed",
            "error": "validation_failed",
            "message": "Nothing was written. Fix the manifest and retry.",
            "errors": errors,
            "counts": counts,
        }

    ids: dict[str, str] = {}
    node_results: list[dict] = []
    artifact_results: list[dict] = []
    edge_results: list[dict] = []
    failures = 0

    for i, item in enumerate(normalized["nodes"]):
        tool = NODE_TYPE_TO_TOOL[item["type"]]
        args = dict(item["fields"])
        if session_id:
            args.setdefault("session_id", session_id)
        parsed = await _run(execute_tool, tool, args, config)
        row = {"index": i, "alias": item["alias"], "type": item["type"]}
        if "error" in parsed:
            failures += 1
            row.update(status="error", error=parsed.get("error"), detail=parsed.get("fields") or parsed.get("message"))
        else:
            row.update(status="created", node_id=parsed.get("node_id"), label=parsed.get("label"))
            if item["alias"]:
                ids[item["alias"]] = parsed["node_id"]
        node_results.append(row)

    for i, item in enumerate(normalized["artifacts"]):
        args = dict(item["fields"])
        if session_id:
            args.setdefault("session_id", session_id)
        parsed = await _run(execute_tool, "ensure_artifact", args, config)
        row = {"index": i, "alias": item["alias"], "path": args.get("path")}
        if "error" in parsed:
            failures += 1
            row.update(status="error", error=parsed.get("error"), detail=parsed.get("fields") or parsed.get("message"))
        else:
            row.update(status=parsed.get("action", "created"), node_id=parsed.get("node_id"), label=parsed.get("label"))
            if item["alias"] and parsed.get("node_id"):
                ids[item["alias"]] = parsed["node_id"]
        artifact_results.append(row)

    for i, edge in enumerate(normalized["edges"]):
        row = {"index": i, **{k: edge[k] for k in ("source", "relationship", "target")}}
        src = ids.get(edge["source"], edge["source"])
        dst = ids.get(edge["target"], edge["target"])
        if src.startswith("@") or dst.startswith("@"):
            failures += 1
            row.update(status="skipped", error="endpoint alias was not created")
            edge_results.append(row)
            continue
        args = {"source_id": src, "target_id": dst, "relationship": edge["relationship"]}
        if edge.get("rel_props"):
            args["rel_props"] = edge["rel_props"]
        if session_id:
            args["session_id"] = session_id
        parsed = await _run(execute_tool, "link_nodes", args, config)
        if "error" in parsed:
            failures += 1
            row.update(status="error", error=parsed.get("error"), source_id=src, target_id=dst)
        else:
            row.update(status="linked", source_id=src, target_id=dst)
        edge_results.append(row)

    total = counts["nodes"] + counts["artifacts"] + counts["edges"]
    if failures == 0:
        status = "ok"
    elif failures >= total:
        status = "failed"
    else:
        status = "partial"

    return {
        "status": status,
        "counts": counts,
        "failures": failures,
        "ids": ids,
        "nodes": node_results,
        "artifacts": artifact_results,
        "edges": edge_results,
    }


async def _run(execute_tool, tool: str, args: dict, config: WheelerConfig) -> dict:
    try:
        return json.loads(await execute_tool(tool, args, config))
    except Exception as exc:  # a crashed item is reported, never raised
        logger.exception("register_batch: %s failed", tool)
        return {"error": f"{type(exc).__name__}: {exc}"}


def load_manifest(path: Path) -> dict:
    """Read a JSON or YAML manifest file."""
    text = Path(path).read_text()
    if str(path).lower().endswith((".yaml", ".yml")):
        import yaml

        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("manifest must be a mapping with nodes/artifacts/edges")
    return data
