"""Restore-verify and portable restore for Wheeler backup archives.

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

The archive layout (from issue #27, extended in v2):
    manifest.json              metadata, counts, file hashes
    graph_nodes.jsonl          one ``{"label": ..., "props": {...}}`` per line
    graph_relationships.jsonl  one rel per line
    project/                   full project_root tree (v2 archives only)
    knowledge/                 (file-level state, not validated here)
    synthesis/
    .wheeler/
    wheeler.yaml

v2 archives add ``manifest_version: 2``, ``archive_uuid``, ``embedder``,
``schema_version``, ``source``, ``manifest_signature``, ``external_references``,
and the ``project/`` subtree.  v1 archives still pass ``--verify``.
``restore_fresh`` and ``restore_merge`` require ``manifest_version >= 2``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import shutil
import tarfile
import tempfile
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml

from wheeler.config import WheelerConfig, load_config
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


def _sha256_file(path: Path) -> str:
    """Hash a file with SHA-256, return ``sha256:<hex>``."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


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
    """Return (ok, detail, parsed_manifest_or_None).

    For v1 archives (no ``manifest_version`` key), only the base required keys
    are checked so ``verify_backup`` stays backward-compatible.  The caller is
    responsible for any additional v2-specific gating.
    """
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


# ---------------------------------------------------------------------------
# v2-specific manifest gating (used by restore_fresh / restore_merge)
# ---------------------------------------------------------------------------

# Props that are internal/regenerated by triple-write on the recipient.
# Never replay these -- they will be regenerated automatically.
_STRIP_PROPS: frozenset[str] = frozenset({
    "_wheeler_project",
    "_search_text",
    "_defaulted",
})

# Map graph labels to their add_* tool names.  Labels that don't follow
# the simple ``add_<lower>`` pattern are listed explicitly.
_LABEL_TO_TOOL: dict[str, str] = {
    "Finding": "add_finding",
    "Hypothesis": "add_hypothesis",
    "OpenQuestion": "add_question",
    "Dataset": "add_dataset",
    "Paper": "add_paper",
    "Document": "add_document",
    "ResearchNote": "add_note",
    "Script": "add_script",
    "Execution": "add_execution",
    "Plan": "add_plan",
    "Ledger": "add_ledger",
}


def _gate_v2_manifest(
    manifest: dict[str, Any],
    recipient_config: WheelerConfig,
    *,
    accept_signature_mismatch: bool = False,
) -> tuple[bool, str, list[str]]:
    """Perform v2-specific gating checks.

    Returns ``(ok, error_message_or_empty, warnings_list)``.
    ``ok=False`` means the caller must abort; ``ok=True`` with non-empty
    warnings means proceed but tell the user.

    Checks (in order):
    1. manifest_version >= 2
    2. manifest_signature valid (unless accept_signature_mismatch=True)
    3. wheeler_version major match
    4. schema_version match
    5. embedder.model match (warning only)
    """
    from wheeler.portability import compute_manifest_signature

    warnings: list[str] = []

    mv = manifest.get("manifest_version")
    if mv is None or (isinstance(mv, (int, float)) and mv < 2):
        return (
            False,
            "archive predates portable restore; only --verify is supported",
            warnings,
        )

    # Signature check (skip if key absent -- allows hand-crafted test archives).
    stored_sig = manifest.get("manifest_signature")
    if stored_sig is not None:
        expected_sig = compute_manifest_signature(manifest)
        if stored_sig != expected_sig:
            if accept_signature_mismatch:
                warnings.append(
                    f"manifest signature mismatch (stored={stored_sig!r}, "
                    f"computed={expected_sig!r}); proceeding because "
                    "accept_signature_mismatch=True"
                )
            else:
                return (
                    False,
                    (
                        f"archive integrity check failed: manifest signature "
                        f"mismatch (stored={stored_sig!r}, "
                        f"computed={expected_sig!r}). "
                        "Pass accept_signature_mismatch=True to override."
                    ),
                    warnings,
                )

    # Wheeler version major match.
    import wheeler as _wh

    installed_version = _wh.__version__
    archive_version = manifest.get("wheeler_version", "")
    try:
        installed_major = int(installed_version.split(".")[0])
        archive_major = int(str(archive_version).split(".")[0])
        if installed_major != archive_major:
            return (
                False,
                (
                    f"major version mismatch: archive has wheeler_version "
                    f"{archive_version!r}, installed is {installed_version!r}. "
                    f"Upgrade Wheeler or restore on a matching install."
                ),
                warnings,
            )
    except (ValueError, IndexError):
        warnings.append(
            f"could not parse wheeler_version from archive ({archive_version!r}); skipping major-version check"
        )

    # Schema version match.
    archive_schema = manifest.get("schema_version")
    recipient_schema = _wh.KNOWLEDGE_SCHEMA_VERSION
    if archive_schema is not None and str(archive_schema) != str(recipient_schema):
        return (
            False,
            (
                f"schema_version mismatch: archive has {archive_schema!r}, "
                f"recipient requires {recipient_schema!r}."
            ),
            warnings,
        )

    # Embedder model check (warning only).
    embedder = manifest.get("embedder") or {}
    archive_model = embedder.get("model")
    recipient_model = recipient_config.search.model if recipient_config.search else None
    if archive_model and recipient_model and archive_model != recipient_model:
        warnings.append(
            f"embedder model mismatch: archive used {archive_model!r}, "
            f"recipient uses {recipient_model!r}. "
            "Embeddings will NOT be copied; run 'wheeler embeddings rebuild' after restore."
        )

    return True, "", warnings


# ---------------------------------------------------------------------------
# Target-shape helpers
# ---------------------------------------------------------------------------


def _target_is_clean(target_root: Path) -> bool:
    """Return True if target_root is safe to restore into without --force.

    Accepts:
    - Non-existent path.
    - Exists and is empty.
    - Clean shell: only ``.git/``, ``.gitignore``.
    - Pristine ``wheeler init`` output: managed dirs all empty plus
      ``wheeler.yaml`` present.

    Everything else returns False (caller should require force=True).
    """
    if not target_root.exists():
        return True
    if not target_root.is_dir():
        return False

    contents = list(target_root.iterdir())
    if not contents:
        return True

    # Allow a clean git shell: only .git and/or .gitignore.
    allowed_names = {".git", ".gitignore"}
    if all(p.name in allowed_names for p in contents):
        return True

    # Pristine wheeler init: managed dirs (all empty) + wheeler.yaml (any content).
    managed = {".plans", ".notes", ".logs", ".wheeler", "knowledge", "synthesis"}
    actual_names = {p.name for p in contents}
    unexpected = actual_names - managed - {"wheeler.yaml"}
    if unexpected:
        return False

    # Each managed dir that exists must be empty.
    for p in contents:
        if p.name in managed and p.is_dir():
            if any(p.iterdir()):
                return False

    return True


# ---------------------------------------------------------------------------
# Path absolutization helper for node props
# ---------------------------------------------------------------------------


def _absolutize_node_props(
    props: dict[str, Any],
    label: str,
    target_root: Path,
) -> tuple[dict[str, Any], list[str]]:
    """Rewrite sentinel-prefixed path fields to absolute paths on target.

    Returns (updated_props, externally_rooted_list) where each entry in
    externally_rooted_list is the original stored value for paths that did
    NOT carry the sentinel (i.e., were external on the source machine).
    """
    from wheeler.portability import absolutize, iter_path_fields

    result = dict(props)
    externals: list[str] = []
    for field in iter_path_fields(label):
        stored = props.get(field)
        if not stored:
            continue
        from wheeler.portability import _PROJECT_SENTINEL  # noqa: PLC0415

        if str(stored).startswith(_PROJECT_SENTINEL):
            result[field] = absolutize(stored, target_root)
        else:
            # External path: pass through unchanged but record it.
            externals.append(stored)
    return result, externals


# ---------------------------------------------------------------------------
# Restore log writer
# ---------------------------------------------------------------------------


def _resolve_synthesis_sentinel(file_path: Path, target_root: Path) -> None:
    """Replace ``${PROJECT}/`` with the target project root in a synthesis file.

    Reads the file, substitutes the sentinel in-place, and writes back.
    Called during extraction so synthesis files are usable before triple-write
    regenerates them.  Errors are logged and silently ignored; a broken
    synthesis file is not a fatal restore error.
    """
    from wheeler.portability import _PROJECT_SENTINEL  # noqa: PLC0415

    try:
        raw = file_path.read_bytes()
        if _PROJECT_SENTINEL.encode("utf-8") not in raw:
            return  # Nothing to do.
        root_bytes = str(target_root.resolve()).encode("utf-8") + b"/"
        resolved = raw.replace(_PROJECT_SENTINEL.encode("utf-8"), root_bytes)
        file_path.write_bytes(resolved)
    except Exception as exc:
        logger.warning("Could not resolve sentinel in %s: %s", file_path, exc)


def _append_restore_log(
    target_root: Path,
    record: dict[str, Any],
) -> None:
    """Append one JSON record to .wheeler/restore_log.jsonl (best-effort)."""
    try:
        log_dir = target_root / ".wheeler"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "restore_log.jsonl"
        with log_path.open("a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception as exc:
        logger.warning("Could not write restore_log.jsonl: %s", exc)


# ---------------------------------------------------------------------------
# Config override helpers
# ---------------------------------------------------------------------------


def _apply_config_overrides(
    yaml_path: Path,
    *,
    neo4j_uri: str | None = None,
    neo4j_password: str | None = None,
    neo4j_database: str | None = None,
    project_tag: str | None = None,
) -> None:
    """Read wheeler.yaml, apply overrides, and write it back.

    If the password field is the ``${NEO4J_PASSWORD}`` sentinel and no
    explicit override is given, resolve from the environment.
    """
    if not yaml_path.exists():
        return
    with yaml_path.open() as fh:
        data = yaml.safe_load(fh) or {}

    neo4j_section = data.setdefault("neo4j", {})

    if neo4j_uri is not None:
        neo4j_section["uri"] = neo4j_uri
    if neo4j_database is not None:
        neo4j_section["database"] = neo4j_database
    if project_tag is not None:
        neo4j_section["project_tag"] = project_tag

    # Password: explicit flag wins; otherwise resolve sentinel from env.
    if neo4j_password is not None:
        neo4j_section["password"] = neo4j_password
    else:
        current_pw = neo4j_section.get("password", "")
        if current_pw == "${NEO4J_PASSWORD}":
            env_pw = os.environ.get("NEO4J_PASSWORD")
            if env_pw:
                neo4j_section["password"] = env_pw
            # If env var not set, leave the sentinel; config.py reads it too.

    with yaml_path.open("w") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False)


# ---------------------------------------------------------------------------
# restore_fresh
# ---------------------------------------------------------------------------


async def restore_fresh(
    config: WheelerConfig,
    archive_path: Path,
    target_root: Path,
    *,
    force: bool = False,
    accept_signature_mismatch: bool = False,
    neo4j_uri: str | None = None,
    neo4j_password: str | None = None,
    neo4j_database: str | None = None,
    project_tag: str | None = None,
) -> dict[str, Any]:
    """Restore a v2 backup archive to a fresh target directory.

    Steps:
    1. Validate manifest (v2 gates, signature, version, schema, embedder).
    2. Check target shape (must be clean unless force=True).
    3. Check recipient Neo4j for existing project nodes.
    4. Extract project/ subtree to target_root.
    5. Apply config overrides and build recipient WheelerConfig.
    6. Replay nodes via execute_tool.
    7. Replay relationships via execute_tool.
    8. Copy embeddings (only if embedder model matched).
    9. Surface external paths.
    10. Write audit trail (Execution node + restore_log.jsonl).
    11. Return result dict.
    """
    archive_path = Path(archive_path)
    target_root = Path(target_root)

    warnings: list[str] = []
    restore_failures: list[dict[str, Any]] = []
    externally_rooted_paths: list[dict[str, Any]] = []

    # -- Extract to a temp directory first so we can inspect the manifest
    #    before touching the target.
    with tempfile.TemporaryDirectory(prefix="wheeler-restore-fresh-") as tmp:
        tmp_root = Path(tmp)

        try:
            archive_root = _extract_archive(archive_path, tmp_root)
        except (tarfile.TarError, OSError) as exc:
            return {
                "status": "error",
                "error": f"archive extraction failed: {exc}",
                "archive_path": str(archive_path),
            }

        manifest_ok, manifest_detail, manifest = _validate_manifest(
            archive_root / "manifest.json"
        )
        if not manifest_ok or manifest is None:
            return {
                "status": "error",
                "error": f"manifest invalid: {manifest_detail}",
                "archive_path": str(archive_path),
            }

        # -- v2 gating
        v2_ok, v2_error, v2_warnings = _gate_v2_manifest(
            manifest,
            config,
            accept_signature_mismatch=accept_signature_mismatch,
        )
        warnings.extend(v2_warnings)
        if not v2_ok:
            return {
                "status": "error",
                "error": v2_error,
                "archive_path": str(archive_path),
            }

        archive_uuid = manifest.get("archive_uuid", "")
        embedder_ok = not any("embedder model mismatch" in w for w in v2_warnings)

        nodes_jsonl = _read_jsonl(archive_root / "graph_nodes.jsonl")
        rels_jsonl = _read_jsonl(archive_root / "graph_relationships.jsonl")

        # -- Target shape check
        if not _target_is_clean(target_root) and not force:
            return {
                "status": "error",
                "error": (
                    f"target_root {target_root} is not empty or a clean shell. "
                    "Pass force=True to override."
                ),
                "archive_path": str(archive_path),
            }

        # -- Recipient Neo4j check: refuse if project tag already has nodes.
        effective_tag = project_tag or config.neo4j.project_tag
        if effective_tag:
            try:
                check_cfg = deepcopy(config)
                check_cfg.neo4j.project_tag = effective_tag
                check_backend = get_backend(check_cfg)
                await check_backend.initialize()
                try:
                    rows = await check_backend.run_cypher(
                        "MATCH (n) WHERE n._wheeler_project = $tag RETURN count(n) AS cnt LIMIT 1",
                        {"tag": effective_tag},
                    )
                    cnt = rows[0].get("cnt", 0) if rows else 0
                    if cnt > 0:
                        return {
                            "status": "error",
                            "error": (
                                f"recipient Neo4j already has {cnt} node(s) tagged "
                                f"_wheeler_project={effective_tag!r}. "
                                "Refusing to restore into a populated namespace. "
                                "Use restore_merge or choose a different project_tag."
                            ),
                            "archive_path": str(archive_path),
                        }
                finally:
                    try:
                        await check_backend.close()
                    except Exception:
                        pass
            except Exception as exc:
                warnings.append(
                    f"Could not pre-check recipient Neo4j for existing nodes: {exc}. "
                    "Proceeding without the check."
                )

        # -- Extract project/ subtree (must happen before graph replay so
        #    files exist on disk when _PATH_MUST_EXIST fires).
        # The embeddings directory is handled separately (step 8) so we can
        # gate it on the embedder-model check.  Skip it during the bulk
        # project extraction to avoid copying incompatible vectors.
        _SKIP_DURING_PROJECT_EXTRACT = frozenset({".wheeler/embeddings"})

        project_src = archive_root / "project"
        if project_src.is_dir():
            target_root.mkdir(parents=True, exist_ok=True)
            for item in project_src.rglob("*"):
                rel = item.relative_to(project_src)
                rel_str = rel.as_posix()
                # Skip the embeddings subtree; handled conditionally in step 8.
                if any(rel_str == skip or rel_str.startswith(skip + "/")
                       for skip in _SKIP_DURING_PROJECT_EXTRACT):
                    continue
                dest = target_root / rel
                if item.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
                    # Resolve ${PROJECT}/ sentinel in synthesis Markdown files
                    # so intermediate state is correct before triple-write runs.
                    if rel_str.startswith("synthesis/") and item.name.endswith(".md"):
                        _resolve_synthesis_sentinel(dest, target_root)
        else:
            # Fallback: old layout without project/ subtree.
            target_root.mkdir(parents=True, exist_ok=True)

        # -- Apply config overrides to the extracted wheeler.yaml.
        yaml_path = target_root / "wheeler.yaml"
        _apply_config_overrides(
            yaml_path,
            neo4j_uri=neo4j_uri,
            neo4j_password=neo4j_password,
            neo4j_database=neo4j_database,
            project_tag=project_tag,
        )

        # -- Build recipient WheelerConfig rooted at target_root.
        recipient_config = load_config(yaml_path) if yaml_path.exists() else WheelerConfig()
        recipient_config.project_root = str(target_root)
        # Ensure knowledge/synthesis paths are rooted at target.
        if not Path(recipient_config.knowledge_path).is_absolute():
            recipient_config.knowledge_path = str(target_root / recipient_config.knowledge_path)
        if not Path(recipient_config.synthesis_path).is_absolute():
            recipient_config.synthesis_path = str(target_root / recipient_config.synthesis_path)

        # -- Replay nodes
        from wheeler.tools.graph_tools import execute_tool

        nodes_restored = 0
        for entry in nodes_jsonl:
            labels = entry.get("labels") or []
            label = entry.get("label") or (labels[0] if labels else None)
            props = entry.get("props") or {}
            if not label or not isinstance(props, dict):
                restore_failures.append({
                    "node_id": props.get("id", "<unknown>"),
                    "label": label or "<missing>",
                    "error": "malformed entry: missing label or props",
                })
                continue

            # Skip internal meta-labels (e.g. the node label list sometimes
            # contains internal labels).
            tool_name = _LABEL_TO_TOOL.get(label)
            if not tool_name:
                restore_failures.append({
                    "node_id": props.get("id", "<unknown>"),
                    "label": label,
                    "error": f"no tool registered for label {label!r}",
                })
                continue

            # Absolutize path fields; collect externals.
            abs_props, ext_paths = _absolutize_node_props(props, label, target_root)
            for ext_path in ext_paths:
                externally_rooted_paths.append({
                    "node_id": abs_props.get("id", ""),
                    "label": label,
                    "original_path": ext_path,
                })

            # Strip regenerated-on-write props.
            args = {k: v for k, v in abs_props.items() if k not in _STRIP_PROPS}

            # Signal that _PATH_MUST_EXIST errors should be downgraded.
            args["_restoring"] = True

            try:
                result_str = await execute_tool(tool_name, args, recipient_config)
                result = json.loads(result_str)
                if "error" in result:
                    restore_failures.append({
                        "node_id": args.get("id", "<unknown>"),
                        "label": label,
                        "error": result["error"],
                    })
                else:
                    nodes_restored += 1
                # Surface field warnings as restore warnings.
                if result.get("warnings"):
                    for field, msg in result["warnings"].items():
                        warnings.append(f"node {args.get('id', '?')} field {field!r}: {msg}")
            except Exception as exc:
                restore_failures.append({
                    "node_id": args.get("id", "<unknown>"),
                    "label": label,
                    "error": str(exc),
                })

        # -- Replay relationships
        rels_restored = 0
        for entry in rels_jsonl:
            source_id = entry.get("source_id")
            rel_type = entry.get("rel_type")
            target_id = entry.get("target_id")
            rel_props = entry.get("rel_props") or {}
            if not (source_id and rel_type and target_id):
                restore_failures.append({
                    "node_id": f"{source_id}->{target_id}",
                    "label": "relationship",
                    "error": "malformed relationship entry",
                })
                continue
            try:
                link_args: dict[str, Any] = {
                    "source_id": source_id,
                    "relationship": rel_type,
                    "target_id": target_id,
                }
                if rel_props:
                    link_args["rel_props"] = rel_props
                result_str = await execute_tool("link_nodes", link_args, recipient_config)
                result = json.loads(result_str)
                if "error" in result:
                    restore_failures.append({
                        "node_id": f"{source_id}->{target_id}",
                        "label": "relationship",
                        "error": result["error"],
                    })
                else:
                    rels_restored += 1
            except Exception as exc:
                restore_failures.append({
                    "node_id": f"{source_id}->{target_id}",
                    "label": "relationship",
                    "error": str(exc),
                })

        # -- Copy embeddings (only if embedder model matched)
        if embedder_ok:
            src_embeddings = archive_root / "project" / ".wheeler" / "embeddings"
            if not src_embeddings.exists():
                src_embeddings = archive_root / ".wheeler" / "embeddings"
            if src_embeddings.is_dir():
                dest_embeddings = target_root / ".wheeler" / "embeddings"
                dest_embeddings.mkdir(parents=True, exist_ok=True)
                for item in src_embeddings.rglob("*"):
                    rel = item.relative_to(src_embeddings)
                    dest = dest_embeddings / rel
                    if item.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
        else:
            warnings.append(
                "Embeddings NOT copied due to embedder model mismatch. "
                "Run 'wheeler embeddings rebuild' to regenerate embeddings on the recipient."
            )

        # -- Audit trail (best-effort)
        source_info = manifest.get("source") or {}
        hostname = source_info.get("hostname", "unknown")
        wh_version_src = manifest.get("wheeler_version", "unknown")
        n = nodes_restored
        m = rels_restored
        k = len(restore_failures)

        try:
            await execute_tool(
                "add_execution",
                {
                    "kind": "restore",
                    "description": (
                        f"Restored from {archive_uuid} "
                        f"(source: {hostname}, {wh_version_src}). "
                        f"nodes={n}, rels={m}, failures={k}"
                    ),
                    "status": "completed",
                },
                recipient_config,
            )
        except Exception as exc:
            warnings.append(f"Could not record restore Execution node: {exc}")

        # Compute archive SHA-256 for the log.
        try:
            archive_sha256 = _sha256_file(archive_path)
        except Exception:
            archive_sha256 = ""

        import wheeler as _wh

        log_record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "archive_path": str(archive_path),
            "archive_sha256": archive_sha256,
            "archive_uuid": archive_uuid,
            "manifest_version": manifest.get("manifest_version", 1),
            "source": {
                "hostname": hostname,
                "wheeler_version": wh_version_src,
                "platform": source_info.get("platform", ""),
            },
            "recipient": {"wheeler_version": _wh.__version__},
            "mode": "fresh",
            "nodes_restored": n,
            "relationships_restored": m,
            "failures": k,
            "warnings": warnings,
        }
        _append_restore_log(target_root, log_record)

        status = "ok" if k == 0 else "partial"
        return {
            "status": status,
            "target_root": str(target_root),
            "archive_path": str(archive_path),
            "archive_uuid": archive_uuid,
            "nodes_restored": n,
            "relationships_restored": m,
            "restore_failures": restore_failures,
            "externally_rooted_paths": externally_rooted_paths,
            "external_references": manifest.get("external_references", []),
            "warnings": warnings,
        }


# ---------------------------------------------------------------------------
# restore_merge
# ---------------------------------------------------------------------------


async def restore_merge(
    config: WheelerConfig,
    archive_path: Path,
    *,
    conflict_policy: Literal["skip", "replace", "prefix"] = "skip",
    prefix: str | None = None,
    accept_signature_mismatch: bool = False,
    neo4j_uri: str | None = None,
    neo4j_password: str | None = None,
    neo4j_database: str | None = None,
    project_tag: str | None = None,
) -> dict[str, Any]:
    """Merge a v2 backup archive into the current (possibly populated) project.

    Unlike ``restore_fresh``, there is no target-shape check: merging into a
    populated graph is the explicit use case.  Conflict resolution is governed
    by ``conflict_policy``:

    - ``skip``: leave existing nodes untouched; only add new ones.
    - ``replace``: overwrite existing nodes via ``update_node``.
    - ``prefix``: rewrite incoming IDs to ``<prefix>__<id>`` so they
      never collide; both endpoints of each relationship are rewritten
      symmetrically using the same mapping.
    """
    archive_path = Path(archive_path)

    warnings: list[str] = []
    restore_failures: list[dict[str, Any]] = []
    externally_rooted_paths: list[dict[str, Any]] = []
    skipped = 0
    replaced = 0
    prefixed = 0
    artifact_file_collisions = 0

    with tempfile.TemporaryDirectory(prefix="wheeler-restore-merge-") as tmp:
        tmp_root = Path(tmp)

        try:
            archive_root = _extract_archive(archive_path, tmp_root)
        except (tarfile.TarError, OSError) as exc:
            return {
                "status": "error",
                "error": f"archive extraction failed: {exc}",
                "archive_path": str(archive_path),
            }

        manifest_ok, manifest_detail, manifest = _validate_manifest(
            archive_root / "manifest.json"
        )
        if not manifest_ok or manifest is None:
            return {
                "status": "error",
                "error": f"manifest invalid: {manifest_detail}",
                "archive_path": str(archive_path),
            }

        # -- v2 gating
        v2_ok, v2_error, v2_warnings = _gate_v2_manifest(
            manifest,
            config,
            accept_signature_mismatch=accept_signature_mismatch,
        )
        warnings.extend(v2_warnings)
        if not v2_ok:
            return {
                "status": "error",
                "error": v2_error,
                "archive_path": str(archive_path),
            }

        archive_uuid = manifest.get("archive_uuid", "")

        nodes_jsonl = _read_jsonl(archive_root / "graph_nodes.jsonl")
        rels_jsonl = _read_jsonl(archive_root / "graph_relationships.jsonl")

        # -- Build working config (honour transient overrides without mutating caller).
        working_config = deepcopy(config)
        if neo4j_uri is not None:
            working_config.neo4j.uri = neo4j_uri
        if neo4j_password is not None:
            working_config.neo4j.password = neo4j_password
        if neo4j_database is not None:
            working_config.neo4j.database = neo4j_database
        if project_tag is not None:
            working_config.neo4j.project_tag = project_tag

        target_root = Path(working_config.project_root).resolve()

        # -- Build id-rewrite mapping for prefix policy.
        id_map: dict[str, str] = {}
        # Maps new (prefixed) id -> label for use in relationship replay.
        prefixed_label_map: dict[str, str] = {}
        if conflict_policy == "prefix":
            if not prefix:
                return {
                    "status": "error",
                    "error": "conflict_policy='prefix' requires a non-empty prefix string.",
                    "archive_path": str(archive_path),
                }
            for entry in nodes_jsonl:
                labels_list = entry.get("labels") or []
                entry_label = entry.get("label") or (labels_list[0] if labels_list else None)
                props = entry.get("props") or {}
                orig_id = props.get("id")
                if orig_id:
                    new_id = f"{prefix}__{orig_id}"
                    id_map[orig_id] = new_id
                    if entry_label:
                        prefixed_label_map[new_id] = entry_label

        from wheeler.tools.graph_tools import execute_tool

        # We need a raw backend for existence checks.
        # Use the module-level ``get_backend`` so test patches apply.
        check_backend = get_backend(working_config)
        try:
            await check_backend.initialize()
        except Exception as exc:
            warnings.append(f"Could not initialize backend for existence checks: {exc}")
            check_backend = None  # type: ignore[assignment]

        nodes_restored = 0

        try:
            for entry in nodes_jsonl:
                labels = entry.get("labels") or []
                label = entry.get("label") or (labels[0] if labels else None)
                props = entry.get("props") or {}
                if not label or not isinstance(props, dict):
                    restore_failures.append({
                        "node_id": props.get("id", "<unknown>"),
                        "label": label or "<missing>",
                        "error": "malformed entry",
                    })
                    continue

                tool_name = _LABEL_TO_TOOL.get(label)
                if not tool_name:
                    restore_failures.append({
                        "node_id": props.get("id", "<unknown>"),
                        "label": label,
                        "error": f"no tool for label {label!r}",
                    })
                    continue

                # Absolutize paths.
                abs_props, ext_paths = _absolutize_node_props(props, label, target_root)
                for ext_path in ext_paths:
                    externally_rooted_paths.append({
                        "node_id": abs_props.get("id", ""),
                        "label": label,
                        "original_path": ext_path,
                    })

                args = {k: v for k, v in abs_props.items() if k not in _STRIP_PROPS}
                args["_restoring"] = True
                orig_id = args.get("id", "")

                # Detect artifact file collision (path exists with different SHA-256).
                for field in ("path",):
                    fpath = args.get(field)
                    if fpath and Path(fpath).exists():
                        artifact_file_collisions += 1
                        break

                if conflict_policy == "prefix" and orig_id in id_map:
                    args["id"] = id_map[orig_id]
                    try:
                        result_str = await execute_tool(tool_name, args, working_config)
                        result = json.loads(result_str)
                        if "error" not in result:
                            nodes_restored += 1
                            prefixed += 1
                        else:
                            restore_failures.append({
                                "node_id": orig_id,
                                "label": label,
                                "error": result["error"],
                            })
                    except Exception as exc:
                        restore_failures.append({
                            "node_id": orig_id,
                            "label": label,
                            "error": str(exc),
                        })
                    continue

                # skip / replace policies: check existence.
                exists = False
                if check_backend is not None and orig_id:
                    try:
                        existing = await check_backend.get_node(label, orig_id)
                        exists = existing is not None
                    except Exception:
                        exists = False

                if exists:
                    if conflict_policy == "skip":
                        skipped += 1
                        continue
                    elif conflict_policy == "replace":
                        # Update existing node with incoming props.
                        update_args = {
                            k: v for k, v in args.items()
                            if k not in ("id", "_restoring")
                        }
                        update_args["node_id"] = orig_id
                        try:
                            result_str = await execute_tool(
                                "update_node", update_args, working_config
                            )
                            result = json.loads(result_str)
                            if "error" not in result:
                                replaced += 1
                                nodes_restored += 1
                            else:
                                restore_failures.append({
                                    "node_id": orig_id,
                                    "label": label,
                                    "error": result["error"],
                                })
                        except Exception as exc:
                            restore_failures.append({
                                "node_id": orig_id,
                                "label": label,
                                "error": str(exc),
                            })
                        continue
                else:
                    try:
                        result_str = await execute_tool(tool_name, args, working_config)
                        result = json.loads(result_str)
                        if "error" not in result:
                            nodes_restored += 1
                        else:
                            restore_failures.append({
                                "node_id": orig_id,
                                "label": label,
                                "error": result["error"],
                            })
                    except Exception as exc:
                        restore_failures.append({
                            "node_id": orig_id,
                            "label": label,
                            "error": str(exc),
                        })

            # -- Replay relationships
            rels_restored = 0
            for entry in rels_jsonl:
                source_id = entry.get("source_id")
                rel_type = entry.get("rel_type")
                target_id = entry.get("target_id")
                rel_props = entry.get("rel_props") or {}

                if not (source_id and rel_type and target_id):
                    restore_failures.append({
                        "node_id": f"{source_id}->{target_id}",
                        "label": "relationship",
                        "error": "malformed relationship entry",
                    })
                    continue

                # Rewrite endpoints for prefix policy.
                if conflict_policy == "prefix":
                    source_id = id_map.get(source_id, source_id)
                    target_id = id_map.get(target_id, target_id)

                # For prefix policy the prefixed IDs break link_nodes' label
                # inference (it splits on "-" which hits the wrong position).
                # Use the backend directly when we have label information.
                if conflict_policy == "prefix" and check_backend is not None:
                    src_label = prefixed_label_map.get(source_id)
                    tgt_label = prefixed_label_map.get(target_id)
                    if src_label and tgt_label:
                        try:
                            ok = await check_backend.create_relationship(
                                src_label, source_id,
                                rel_type,
                                tgt_label, target_id,
                                **({"rel_props": rel_props} if rel_props else {}),
                            )
                            if ok:
                                rels_restored += 1
                            else:
                                restore_failures.append({
                                    "node_id": f"{source_id}->{target_id}",
                                    "label": "relationship",
                                    "error": "create_relationship returned False",
                                })
                        except Exception as exc:
                            restore_failures.append({
                                "node_id": f"{source_id}->{target_id}",
                                "label": "relationship",
                                "error": str(exc),
                            })
                        continue

                try:
                    link_args: dict[str, Any] = {
                        "source_id": source_id,
                        "relationship": rel_type,
                        "target_id": target_id,
                    }
                    if rel_props:
                        link_args["rel_props"] = rel_props
                    result_str = await execute_tool("link_nodes", link_args, working_config)
                    result = json.loads(result_str)
                    if "error" not in result:
                        rels_restored += 1
                    else:
                        restore_failures.append({
                            "node_id": f"{source_id}->{target_id}",
                            "label": "relationship",
                            "error": result["error"],
                        })
                except Exception as exc:
                    restore_failures.append({
                        "node_id": f"{source_id}->{target_id}",
                        "label": "relationship",
                        "error": str(exc),
                    })

        finally:
            if check_backend is not None:
                try:
                    await check_backend.close()
                except Exception:
                    pass

        # -- Audit trail (best-effort)
        source_info = manifest.get("source") or {}
        hostname = source_info.get("hostname", "unknown")
        wh_version_src = manifest.get("wheeler_version", "unknown")
        n = nodes_restored
        m = rels_restored
        k = len(restore_failures)

        try:
            await execute_tool(
                "add_execution",
                {
                    "kind": "restore",
                    "description": (
                        f"Merged from {archive_uuid} "
                        f"(source: {hostname}, {wh_version_src}). "
                        f"nodes={n}, rels={m}, failures={k}, "
                        f"skipped={skipped}, replaced={replaced}, prefixed={prefixed}"
                    ),
                    "status": "completed",
                },
                working_config,
            )
        except Exception as exc:
            warnings.append(f"Could not record restore Execution node: {exc}")

        try:
            archive_sha256 = _sha256_file(archive_path)
        except Exception:
            archive_sha256 = ""

        import wheeler as _wh

        log_record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "archive_path": str(archive_path),
            "archive_sha256": archive_sha256,
            "archive_uuid": archive_uuid,
            "manifest_version": manifest.get("manifest_version", 1),
            "source": {
                "hostname": hostname,
                "wheeler_version": wh_version_src,
                "platform": source_info.get("platform", ""),
            },
            "recipient": {"wheeler_version": _wh.__version__},
            "mode": "merge",
            "nodes_restored": n,
            "relationships_restored": m,
            "failures": k,
            "skipped": skipped,
            "replaced": replaced,
            "prefixed": prefixed,
            "warnings": warnings,
        }
        _append_restore_log(target_root, log_record)

        status = "ok" if k == 0 else "partial"
        return {
            "status": status,
            "archive_path": str(archive_path),
            "archive_uuid": archive_uuid,
            "nodes_restored": n,
            "relationships_restored": m,
            "restore_failures": restore_failures,
            "externally_rooted_paths": externally_rooted_paths,
            "external_references": manifest.get("external_references", []),
            "warnings": warnings,
            "merge_report": {
                "skipped": skipped,
                "replaced": replaced,
                "prefixed": prefixed,
                "externals": len(externally_rooted_paths),
                "failures": k,
                "artifact_file_collisions": artifact_file_collisions,
            },
        }


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
