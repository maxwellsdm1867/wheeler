"""Restore-verify for Wheeler backup archives.

Issue #28: ``wheeler restore --verify <archive>``

Restores a backup archive (produced by issue #27 ``wheeler backup``) into
an isolated scratch namespace inside the live Neo4j instance, compares it
to the archive's manifest, and emits a PASS/FAIL verdict with diagnostics.
The user's live data is never touched: writes are gated by a non-empty
``project_tag`` (a sentinel value, not the user's tag), and cleanup deletes
only nodes that carry that sentinel.

Why namespace isolation rather than Docker/Testcontainers: Wheeler already
supports per-project isolation on Community Edition via the
``_wheeler_project`` property (see ``wheeler/graph/neo4j_backend.py``).
Restore-verify reuses that machinery so it works with any Neo4j install
the user already has running, without a Docker dependency.

The archive layout (from issue #27):
    manifest.json              metadata, counts, file hashes
    graph_nodes.jsonl          one ``{"label": ..., "props": {...}}`` per line
    graph_relationships.jsonl  one rel per line
    knowledge/                 (file-level state, not validated here)
    synthesis/
    .wheeler/
    wheeler.yaml
"""

from __future__ import annotations

import json
import logging
import secrets
import tarfile
import tempfile
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.graph.backend import GraphBackend, get_backend

logger = logging.getLogger(__name__)


# Default sentinel namespace tag for restore-verify. A unique random suffix
# is appended so concurrent verify runs can coexist without colliding.
_VERIFY_TAG_PREFIX = "__restore_verify__"

# Manifest keys that must be present and well-formed.
_REQUIRED_MANIFEST_KEYS = (
    "wheeler_version",
    "node_counts_by_label",
    "relationship_count_by_type",
)

# How many nodes per label to sample for property comparison.
_PROPERTY_SAMPLE_PER_LABEL = 10

# Properties we consider "representative" for the sample-comparison check.
# Missing properties on a node are skipped (not all node types have all of these).
_PROPERTY_SAMPLE_FIELDS = ("id", "title", "type")


class RestoreVerifyError(RuntimeError):
    """Raised when restore-verify cannot proceed safely (e.g. empty project_tag)."""


def _make_scratch_tag() -> str:
    """Build a per-run sentinel tag so parallel verifies don't collide."""
    return f"{_VERIFY_TAG_PREFIX}{secrets.token_hex(4)}"


def _scratch_config(base: WheelerConfig, scratch_tag: str) -> WheelerConfig:
    """Return a config copy whose project_tag is forced to the sentinel.

    Pydantic v2 ``model_copy(deep=True)`` would clone but reuses the same
    Neo4jConfig object; we deep-copy so mutating ``neo4j.project_tag`` on
    the clone never leaks back to the caller's config.
    """
    cloned = deepcopy(base)
    cloned.neo4j.project_tag = scratch_tag
    return cloned


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping blank lines."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open() as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _validate_manifest(manifest_path: Path) -> tuple[bool, str, dict[str, Any] | None]:
    """Return (ok, detail, parsed_manifest_or_None)."""
    if not manifest_path.exists():
        return False, "manifest.json missing from archive", None
    try:
        with manifest_path.open() as fh:
            manifest = json.load(fh)
    except json.JSONDecodeError as exc:
        return False, f"manifest.json is not valid JSON: {exc}", None
    if not isinstance(manifest, dict):
        return False, "manifest.json must be a JSON object", None
    missing = [k for k in _REQUIRED_MANIFEST_KEYS if k not in manifest]
    if missing:
        return (
            False,
            f"manifest.json missing required keys: {', '.join(missing)}",
            manifest,
        )
    nc = manifest.get("node_counts_by_label", {})
    rc = manifest.get("relationship_count_by_type", {})
    if not isinstance(nc, dict) or not isinstance(rc, dict):
        return (
            False,
            "manifest counts must be dicts (label -> int, rel_type -> int)",
            manifest,
        )
    return True, (
        f"manifest valid (wheeler_version={manifest.get('wheeler_version')}, "
        f"{len(nc)} labels, {len(rc)} rel types)"
    ), manifest


async def _replay_nodes(
    backend: GraphBackend,
    nodes: list[dict[str, Any]],
) -> tuple[dict[str, int], list[str]]:
    """Replay node JSONL into the scratch namespace.

    Returns (counts_by_label, errors). Each line is ``{"label": ..., "props": {...}}``.
    The backend auto-stamps ``_wheeler_project`` because project_tag is set
    on the config it was built with.
    """
    counts: dict[str, int] = defaultdict(int)
    errors: list[str] = []
    for entry in nodes:
        label = entry.get("label")
        props = entry.get("props") or {}
        if not label or not isinstance(props, dict):
            errors.append(f"malformed node entry: {entry!r}")
            continue
        try:
            await backend.create_node(label, dict(props))
            counts[label] += 1
        except Exception as exc:
            errors.append(f"create_node({label}, id={props.get('id')!r}) failed: {exc}")
    return dict(counts), errors


async def _replay_relationships(
    backend: GraphBackend,
    rels: list[dict[str, Any]],
    node_label_by_id: dict[str, str],
) -> tuple[dict[str, int], list[str]]:
    """Replay relationship JSONL into the scratch namespace.

    Each line is ``{"source_id": ..., "rel_type": ..., "target_id": ...,
    "rel_props": {...}}``. We look up the source/target labels from the
    node JSONL we just replayed; relationships pointing at unknown IDs are
    counted as errors (the manifest comparison will surface the count drop).
    """
    counts: dict[str, int] = defaultdict(int)
    errors: list[str] = []
    for entry in rels:
        rel_type = entry.get("rel_type")
        src_id = entry.get("source_id")
        tgt_id = entry.get("target_id")
        if not (rel_type and src_id and tgt_id):
            errors.append(f"malformed relationship entry: {entry!r}")
            continue
        src_label = node_label_by_id.get(src_id)
        tgt_label = node_label_by_id.get(tgt_id)
        if not src_label or not tgt_label:
            errors.append(
                f"relationship {src_id} -[{rel_type}]-> {tgt_id} "
                f"references unknown node ID(s)"
            )
            continue
        try:
            ok = await backend.create_relationship(
                src_label, src_id, rel_type, tgt_label, tgt_id
            )
            if ok:
                counts[rel_type] += 1
            else:
                errors.append(
                    f"create_relationship returned False for "
                    f"{src_id} -[{rel_type}]-> {tgt_id}"
                )
        except Exception as exc:
            errors.append(
                f"create_relationship({src_id} -[{rel_type}]-> {tgt_id}) "
                f"failed: {exc}"
            )
    return dict(counts), errors


def _compare_counts(
    expected: dict[str, int],
    actual: dict[str, int],
    label_for_msg: str,
) -> tuple[bool, str]:
    """Compare two ``{name: count}`` dicts. Return (ok, detail)."""
    all_keys = set(expected) | set(actual)
    mismatches: list[str] = []
    for key in sorted(all_keys):
        exp = expected.get(key, 0)
        act = actual.get(key, 0)
        if exp != act:
            mismatches.append(f"{label_for_msg} {key}: expected {exp}, got {act}")
    if mismatches:
        return False, mismatches[0]
    return True, f"all {len(all_keys)} {label_for_msg.lower()}s match"


def _compare_property_sample(
    nodes_jsonl: list[dict[str, Any]],
    nodes_in_graph: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Compare representative properties for a sample of nodes per label.

    For each label in the JSONL, take up to ``_PROPERTY_SAMPLE_PER_LABEL``
    nodes; for each sampled node ID, find the corresponding entry in
    ``nodes_in_graph`` and compare ``_PROPERTY_SAMPLE_FIELDS`` (skipping
    fields the JSONL didn't carry). First mismatch wins.
    """
    by_label_jsonl: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in nodes_jsonl:
        label = entry.get("label")
        props = entry.get("props") or {}
        if isinstance(label, str) and isinstance(props, dict) and props.get("id"):
            by_label_jsonl[label].append(props)

    graph_by_id: dict[str, dict[str, Any]] = {}
    for n in nodes_in_graph:
        nid = n.get("id")
        if nid:
            graph_by_id[nid] = n

    sampled = 0
    for label, props_list in by_label_jsonl.items():
        for original in props_list[:_PROPERTY_SAMPLE_PER_LABEL]:
            nid = original["id"]
            in_graph = graph_by_id.get(nid)
            if in_graph is None:
                return False, f"{label} {nid}: present in archive but missing from graph"
            for field in _PROPERTY_SAMPLE_FIELDS:
                if field not in original:
                    continue
                if in_graph.get(field) != original[field]:
                    return False, (
                        f"{label} {nid} property '{field}': "
                        f"expected {original[field]!r}, got {in_graph.get(field)!r}"
                    )
            sampled += 1
    return True, f"property sample matches across {sampled} nodes"


async def _fetch_all_scratch_nodes(
    backend: GraphBackend,
    scratch_tag: str,
) -> list[dict[str, Any]]:
    """Read every node in the scratch namespace via raw Cypher.

    Returns a flat list of node-property dicts. The Cypher returns one row
    per node with a single ``n`` field (a Node), which we convert to a dict.
    """
    rows = await backend.run_cypher(
        "MATCH (n) WHERE n._wheeler_project = $ptag RETURN n, labels(n) AS labels",
        {"ptag": scratch_tag},
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        node = row.get("n") or {}
        # ``run_cypher`` returns dict(record); the value at "n" may be a
        # neo4j Node (mapping-like) or already a dict in fakes.
        if hasattr(node, "items"):
            props = dict(node)
        else:
            props = node if isinstance(node, dict) else {}
        out.append(props)
    return out


async def _count_scratch_nodes_by_label(
    backend: GraphBackend,
    scratch_tag: str,
) -> dict[str, int]:
    """Count scratch-namespace nodes grouped by label."""
    rows = await backend.run_cypher(
        "MATCH (n) WHERE n._wheeler_project = $ptag "
        "UNWIND labels(n) AS lbl "
        "RETURN lbl, count(*) AS cnt",
        {"ptag": scratch_tag},
    )
    out: dict[str, int] = {}
    for row in rows:
        lbl = row.get("lbl")
        cnt = row.get("cnt", 0)
        if isinstance(lbl, str):
            out[lbl] = int(cnt)
    return out


async def _count_scratch_rels_by_type(
    backend: GraphBackend,
    scratch_tag: str,
) -> dict[str, int]:
    """Count scratch-namespace relationships grouped by type."""
    rows = await backend.run_cypher(
        "MATCH (a)-[r]->(b) "
        "WHERE a._wheeler_project = $ptag AND b._wheeler_project = $ptag "
        "RETURN type(r) AS rel, count(*) AS cnt",
        {"ptag": scratch_tag},
    )
    out: dict[str, int] = {}
    for row in rows:
        rel = row.get("rel")
        cnt = row.get("cnt", 0)
        if isinstance(rel, str):
            out[rel] = int(cnt)
    return out


async def _cleanup_scratch(backend: GraphBackend, scratch_tag: str) -> None:
    """DETACH DELETE every node carrying the scratch sentinel.

    Safe by construction: scratch_tag is guaranteed non-empty by
    ``verify_backup`` before any writes. We never DETACH DELETE without
    a project-tag predicate.
    """
    if not scratch_tag:
        raise RestoreVerifyError(
            "refusing to cleanup with empty scratch tag (would wipe whole graph)"
        )
    await backend.run_cypher(
        "MATCH (n) WHERE n._wheeler_project = $ptag DETACH DELETE n",
        {"ptag": scratch_tag},
    )
    logger.info("Restore-verify scratch namespace cleaned: tag=%s", scratch_tag)


def _extract_archive(archive_path: Path, dest_dir: Path) -> Path:
    """Extract a tar.gz archive into ``dest_dir``. Returns the inner root.

    Backup archives may either contain files at the top level or wrap them
    in a single directory (e.g. ``wheeler-backup-2026-05-10/``). We handle
    both by returning whichever path actually contains ``manifest.json``.
    """
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(dest_dir)
    if (dest_dir / "manifest.json").exists():
        return dest_dir
    children = [p for p in dest_dir.iterdir() if p.is_dir()]
    if len(children) == 1 and (children[0] / "manifest.json").exists():
        return children[0]
    return dest_dir


async def verify_backup(
    config: WheelerConfig,
    archive_path: Path,
    keep_scratch: bool = False,
    backend: GraphBackend | None = None,
) -> dict[str, Any]:
    """Verify a backup archive is restorable.

    Parameters
    ----------
    config:
        The active Wheeler config. We deep-copy it before flipping
        ``project_tag`` to the scratch sentinel so the caller's config is
        never mutated.
    archive_path:
        Path to a tar.gz archive produced by ``wheeler backup``.
    keep_scratch:
        Skip the cleanup step. Useful when debugging a FAIL: leaves the
        replayed scratch nodes in the graph for manual inspection.
    backend:
        Inject a backend (for tests). If None, a real
        ``Neo4jBackend(scratch_config)`` is built. The backend MUST
        already be configured for the scratch tag.

    Returns
    -------
    dict with keys: verdict ("PASS"|"FAIL"), checks (list), first_failure
    (str|None), archive_path (str), scratch_tag (str).
    """
    archive_path = Path(archive_path)
    scratch_tag = _make_scratch_tag()

    checks: list[dict[str, str]] = []
    first_failure: str | None = None

    def _record(name: str, result: str, detail: str) -> None:
        nonlocal first_failure
        checks.append({"name": name, "result": result, "detail": detail})
        if result == "FAIL" and first_failure is None:
            first_failure = f"{name}: {detail}"

    # Up-front existence check so we fail with a clear message rather than
    # tarfile internals.
    if not archive_path.exists():
        _record("archive_exists", "FAIL", f"archive not found: {archive_path}")
        return {
            "verdict": "FAIL",
            "checks": checks,
            "first_failure": first_failure,
            "archive_path": str(archive_path),
            "scratch_tag": scratch_tag,
        }

    with tempfile.TemporaryDirectory(prefix="wheeler-restore-verify-") as tmp:
        tmp_root = Path(tmp)
        try:
            archive_root = _extract_archive(archive_path, tmp_root)
        except (tarfile.TarError, OSError) as exc:
            _record("archive_extracts", "FAIL", f"extract failed: {exc}")
            return {
                "verdict": "FAIL",
                "checks": checks,
                "first_failure": first_failure,
                "archive_path": str(archive_path),
                "scratch_tag": scratch_tag,
            }
        _record("archive_extracts", "PASS", f"extracted to {archive_root}")

        manifest_ok, manifest_detail, manifest = _validate_manifest(
            archive_root / "manifest.json"
        )
        _record(
            "manifest_valid",
            "PASS" if manifest_ok else "FAIL",
            manifest_detail,
        )
        if not manifest_ok or manifest is None:
            return {
                "verdict": "FAIL",
                "checks": checks,
                "first_failure": first_failure,
                "archive_path": str(archive_path),
                "scratch_tag": scratch_tag,
            }

        nodes_jsonl = _read_jsonl(archive_root / "graph_nodes.jsonl")
        rels_jsonl = _read_jsonl(archive_root / "graph_relationships.jsonl")

        # Build a backend pinned to the scratch tag. CRITICAL safety check:
        # never let the scratch tag be empty/falsy. If it ever was, every
        # CREATE would land in the user's live namespace and cleanup could
        # nuke their data.
        scratch_cfg = _scratch_config(config, scratch_tag)
        if not scratch_cfg.neo4j.project_tag:
            raise RestoreVerifyError(
                "scratch project_tag is empty: refusing to write to live graph"
            )

        owned_backend = backend is None
        if backend is None:
            backend = get_backend(scratch_cfg)
            await backend.initialize()

        try:
            # Replay nodes and relationships into the scratch namespace.
            label_by_id: dict[str, str] = {}
            for entry in nodes_jsonl:
                lbl = entry.get("label")
                props = entry.get("props") or {}
                nid = props.get("id")
                if isinstance(lbl, str) and isinstance(nid, str):
                    label_by_id[nid] = lbl

            replay_node_counts, node_errors = await _replay_nodes(
                backend, nodes_jsonl
            )
            replay_rel_counts, rel_errors = await _replay_relationships(
                backend, rels_jsonl, label_by_id
            )

            if node_errors:
                _record(
                    "nodes_replay",
                    "FAIL",
                    f"{len(node_errors)} node-replay error(s); first: {node_errors[0]}",
                )
            else:
                _record(
                    "nodes_replay",
                    "PASS",
                    f"replayed {sum(replay_node_counts.values())} node(s) "
                    f"across {len(replay_node_counts)} label(s)",
                )

            if rel_errors:
                _record(
                    "relationships_replay",
                    "FAIL",
                    f"{len(rel_errors)} rel-replay error(s); first: {rel_errors[0]}",
                )
            else:
                _record(
                    "relationships_replay",
                    "PASS",
                    f"replayed {sum(replay_rel_counts.values())} relationship(s) "
                    f"across {len(replay_rel_counts)} type(s)",
                )

            # Compare node counts against manifest.
            graph_node_counts = await _count_scratch_nodes_by_label(
                backend, scratch_tag
            )
            ok, detail = _compare_counts(
                manifest["node_counts_by_label"],
                graph_node_counts,
                label_for_msg="node count for label",
            )
            _record("node_counts_match", "PASS" if ok else "FAIL", detail)

            # Compare relationship counts against manifest.
            graph_rel_counts = await _count_scratch_rels_by_type(
                backend, scratch_tag
            )
            ok, detail = _compare_counts(
                manifest["relationship_count_by_type"],
                graph_rel_counts,
                label_for_msg="relationship count for type",
            )
            _record("relationship_counts_match", "PASS" if ok else "FAIL", detail)

            # Property sample.
            graph_nodes_dump = await _fetch_all_scratch_nodes(backend, scratch_tag)
            ok, detail = _compare_property_sample(nodes_jsonl, graph_nodes_dump)
            _record("property_sample_match", "PASS" if ok else "FAIL", detail)

        finally:
            if not keep_scratch:
                try:
                    await _cleanup_scratch(backend, scratch_tag)
                except Exception as exc:
                    # Cleanup failure does not flip a PASS to FAIL: it's a
                    # separate concern. We log loudly and surface a check.
                    logger.warning("scratch cleanup failed: %s", exc)
                    _record(
                        "scratch_cleanup",
                        "FAIL",
                        f"cleanup of tag {scratch_tag} failed: {exc}",
                    )
                else:
                    _record(
                        "scratch_cleanup",
                        "PASS",
                        f"removed scratch namespace {scratch_tag}",
                    )
            if owned_backend:
                try:
                    await backend.close()
                except Exception as exc:
                    logger.debug("backend.close() raised during verify: %s", exc)

    verdict = "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL"
    return {
        "verdict": verdict,
        "checks": checks,
        "first_failure": first_failure,
        "archive_path": str(archive_path),
        "scratch_tag": scratch_tag,
    }
