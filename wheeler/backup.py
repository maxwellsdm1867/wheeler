"""Snapshot Wheeler's canonical state to a single tar.gz archive.

This module is invoked from the Typer CLI (``wheeler backup``), NOT from an
MCP tool.

Why a CLI subcommand and not an MCP tool: the MCP transport caps tool
results at ~235k chars, which a full graph dump (nodes + relationships)
saturates almost immediately on a real research project. Running in-process
through ``backend.run_cypher`` avoids the cap entirely and lets us stream
JSONL into the archive.

Layout of the produced archive (``wheeler-backup-YYYYMMDD-HHMMSS.tar.gz``):

    manifest.json               timestamp, version, counts, file hashes,
                                archive layout, manifest_version=2,
                                archive_uuid, path_rewrite_scheme,
                                embedder, schema_version, source,
                                external_references, excluded_paths,
                                manifest_signature
    project/                    full project_root tree (scope=project)
      knowledge/  synthesis/    paths rewritten in-bytes
      .plans/  .notes/  .logs/  docs/  scripts/  ...
      .wheeler/  (no backups/)
      wheeler.yaml              password stripped to ${NEO4J_PASSWORD}
    graph_nodes.jsonl           one JSON object per line (paths rewritten)
    graph_relationships.jsonl   one JSON object per line (unchanged)

scope="graph-only" (v1 behaviour): no project/ tree; archive contains only
  knowledge/  synthesis/  .wheeler/  wheeler.yaml  graph_nodes.jsonl
  graph_relationships.jsonl  manifest.json

If Neo4j is unreachable the file layers are still archived; the JSONL graph
dumps are written empty and the manifest records ``graph_available: false``.
"""

from __future__ import annotations

import getpass
import hashlib
import io
import json
import logging
import platform as _platform_module
import re
import socket
import sys
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from wheeler.config import WheelerConfig
from wheeler.graph.backend import get_backend
from wheeler.portability import (
    compute_manifest_signature,
    discover_external_reference,
    iter_path_fields,
    relativize,
    scan_for_secrets,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HANDOFF.md template (baked into every archive at the top level)
# ---------------------------------------------------------------------------

_HANDOFF_TEMPLATE = """\
# Wheeler handoff archive

This file is a portable snapshot of a Wheeler research project.

- **Archive UUID**: {archive_uuid}
- **Created**: {timestamp} on {hostname} ({platform})
- **Wheeler version at pack time**: {wheeler_version}
- **Schema version**: {schema_version}
- **Scope**: {scope}
- **Contents**: {total_nodes} nodes, {total_relationships} relationships
- **Embedder**: {embedder_model} (dim {embedder_dim}, fastembed {embedder_fastembed_version})

## How to receive this archive

1. Install Wheeler on the recipient machine:

   ```bash
   pip install "wheeler=={wheeler_version}"
   ```

   Major-version mismatch will be rejected by `restore --fresh`. Use the exact version above for a clean restore.

2. Verify the archive is intact (non-destructive, recommended first step):

   ```bash
   wheeler restore {archive_filename} --verify
   ```

   This replays the graph into a scratch namespace and tears it down. No project files are written.

3. Restore into a fresh directory:

   ```bash
   wheeler restore {archive_filename} --fresh --target ./{project_name}
   cd ./{project_name}
   wheeler graph status
   ```

   The target must be empty (or a clean `wheeler init` shell). Pass `--force` to override.

4. Or merge into an existing Wheeler project:

   ```bash
   wheeler restore {archive_filename} --merge --conflict skip
   ```

   Conflict policies: `skip` (default), `replace`, `prefix --prefix <STR>`.

## Configuration overrides (optional)

The packed `wheeler.yaml` has `password: ${{NEO4J_PASSWORD}}`. Set it via env or override at restore:

```bash
NEO4J_PASSWORD=... wheeler restore {archive_filename} --fresh --target ./proj
# or
wheeler restore {archive_filename} --fresh --target ./proj --neo4j-password '...'
```

Other overrides: `--neo4j-uri`, `--neo4j-database`, `--project-tag`.

## External references

{external_references_section}

## Secrets allowed (if any)

{secrets_section}

## Audit trail

A `.wheeler/restore_log.jsonl` record is appended on the recipient's side every time `restore --fresh` or `--merge` runs, and an `Execution(kind="restore")` node is added to the graph. The archive's `archive_uuid` shows up in both.

## Trouble?

- `archive predates portable restore`: this archive is v1 (pre-portability). Only `--verify` is supported. Ask the sender to repack with a newer Wheeler.
- `major version mismatch`: install the Wheeler version listed above.
- `manifest signature invalid`: the archive was modified. Pass `--accept-signature-mismatch` only if you trust the source.
"""


def _generate_handoff_md(
    manifest: dict,
    scope: str,
    archive_filename: str,
) -> bytes:
    """Render the HANDOFF.md template from the manifest and scope.

    Returns UTF-8 bytes ready to pack into the tar.
    """
    source = manifest.get("source") or {}
    embedder = manifest.get("embedder") or {}
    external_refs = manifest.get("external_references") or []
    allowed_secrets = manifest.get("allowed_secret_files") or []

    # External references section.
    if external_refs:
        rows = [
            "This archive references files outside the source project root. "
            "You will need to obtain them separately. They are not in this archive.",
            "",
            "| Node | Field | Original path | Git remote | Git commit |",
            "|------|-------|---------------|------------|------------|",
        ]
        for ref in external_refs[:20]:
            node_id = ref.get("node_id", "")
            field = ref.get("field", "")
            orig = ref.get("original_path", "")
            remote = ref.get("git_remote", "")
            commit = ref.get("git_commit", "")
            rows.append(f"| {node_id} | {field} | {orig} | {remote} | {commit} |")
        if len(external_refs) > 20:
            rows.append(
                f"\n_(and {len(external_refs) - 20} more, see manifest.json for the full list)_"
            )
        ext_section = "\n".join(rows)
    else:
        ext_section = "None. All referenced files are inside the archive."

    # Secrets section.
    if allowed_secrets:
        lines = [
            "The sender packed this archive with `--allow-secrets`. "
            "The following files passed the secret scan with overrides. "
            "Treat the archive as sensitive:",
            "",
        ]
        for entry in allowed_secrets:
            path = entry.get("path", "")
            patterns = ", ".join(entry.get("patterns") or [])
            lines.append(f"- `{path}` (patterns: {patterns})")
        secrets_section = "\n".join(lines)
    else:
        secrets_section = "None. Secret scan passed cleanly."

    filled = _HANDOFF_TEMPLATE.format(
        archive_uuid=manifest.get("archive_uuid", ""),
        timestamp=manifest.get("timestamp", ""),
        hostname=source.get("hostname", "unknown"),
        platform=source.get("platform", "unknown"),
        wheeler_version=manifest.get("wheeler_version", "unknown"),
        schema_version=manifest.get("schema_version", ""),
        scope=scope,
        total_nodes=manifest.get("total_nodes", 0),
        total_relationships=manifest.get("total_relationships", 0),
        embedder_model=embedder.get("model") or "unknown",
        embedder_dim=embedder.get("dim") or "unknown",
        embedder_fastembed_version=embedder.get("fastembed_version") or "unknown",
        archive_filename=archive_filename,
        project_name="my-project",
        external_references_section=ext_section,
        secrets_section=secrets_section,
    )
    return filled.encode("utf-8")


_NODE_DUMP_CYPHER = (
    "MATCH (n) "
    "RETURN labels(n) AS labels, properties(n) AS props"
)

_REL_DUMP_CYPHER = (
    "MATCH (a)-[r]->(b) "
    "RETURN a.id AS source_id, type(r) AS rel_type, "
    "properties(r) AS rel_props, b.id AS target_id"
)

# Directories always excluded from the project/ walk. Non-overridable.
# build/ and dist/ are standard Python build outputs and are listed in
# .gitignore, but the simple gitignore fallback used when pathspec is not
# installed does not handle trailing-slash directory patterns, so we add
# them here for belt-and-braces.
_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist"}
)


class BackupAbortedDueToSecrets(Exception):
    """Raised when scan_for_secrets detects API-key-like content.

    The ``offenders`` attribute is a list of dicts, each with:
      - ``path``: archive-relative path string
      - ``pattern``: name of the matched pattern
      - ``snippet``: the matched text (truncated)
    """

    def __init__(self, offenders: list[dict]) -> None:
        self.offenders = offenders
        paths = ", ".join(o["path"] for o in offenders[:5])
        super().__init__(
            f"Backup aborted: secrets detected in {len(offenders)} file(s): {paths}. "
            "Pass allow_secrets=True to override."
        )


def _wheeler_version() -> str:
    """Read the package version (falls back to the literal in __init__.py)."""
    try:
        import wheeler

        return wheeler.__version__
    except Exception:
        return "unknown"


def _sha256_file(path: Path) -> str:
    """Hash a file with SHA-256, return ``sha256:<hex>``."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _sha256_bytes(data: bytes) -> str:
    """Hash bytes with SHA-256, return ``sha256:<hex>``."""
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _resolve_destination(config: WheelerConfig, destination: Path | None) -> Path:
    """Pick the directory to write the archive into.

    Default: ``<knowledge_path parent>/.wheeler/backups/``. If the knowledge
    path's parent is the cwd (the common case), this collapses to
    ``./.wheeler/backups/``. Falls back to ``Path.cwd() / ".wheeler" / "backups"``.
    """
    if destination is not None:
        return destination
    knowledge_dir = Path(config.knowledge_path)
    if knowledge_dir.is_absolute():
        base = knowledge_dir.parent
    else:
        base = Path.cwd()
    return base / ".wheeler" / "backups"


def _add_bytes_to_tar(
    tar: tarfile.TarFile, arcname: str, data: bytes
) -> None:
    """Add an in-memory bytes blob to the tar."""
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mtime = int(datetime.now(timezone.utc).timestamp())
    tar.addfile(info, io.BytesIO(data))


def _parse_gitignore(root: Path) -> list[str]:
    """Parse .gitignore at root, returning non-comment, non-empty patterns."""
    gi = root / ".gitignore"
    if not gi.exists():
        return []
    patterns: list[str] = []
    for line in gi.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return patterns


def _is_gitignored_simple(rel_posix: str, patterns: list[str]) -> bool:
    """Very simple .gitignore line-match fallback (no pathspec library).

    Matches only plain directory names, plain file names, and ``*.ext``
    glob patterns. Complex gitignore features (negation, ``/`` anchoring,
    double-star) are deliberately not supported. Good enough for the
    most common cases.
    """
    import fnmatch

    parts = rel_posix.split("/")
    for pattern in patterns:
        # Match against each path component (covers dir-name exclusions like
        # "dist" or file-name exclusions like "*.pyc").
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
        # Also match the full relative path for things like "docs/private.md".
        if fnmatch.fnmatch(rel_posix, pattern):
            return True
    return False


def _gitignored(rel_posix: str, patterns: list[str]) -> bool:
    """Apply .gitignore patterns, using pathspec when available."""
    if not patterns:
        return False
    try:
        import pathspec  # type: ignore[import]

        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        return spec.match_file(rel_posix)
    except ImportError:
        return _is_gitignored_simple(rel_posix, patterns)


def _add_dir_to_tar(
    tar: tarfile.TarFile,
    src_dir: Path,
    arcname: str,
    file_hashes: dict[str, str],
    excludes: set[Path] | None = None,
) -> None:
    """Add ``src_dir`` to the tar under ``arcname/``.

    Records per-file SHA-256 in *file_hashes* keyed by the in-archive path.
    Quietly skips paths in *excludes* (resolved absolute paths).
    """
    if not src_dir.exists():
        return
    excludes = excludes or set()

    if not src_dir.is_dir():
        # File-only case: just add it.
        if src_dir.resolve() in excludes:
            return
        try:
            tar.add(src_dir, arcname=arcname, recursive=False)
        except OSError as exc:
            logger.warning("Could not add %s to archive: %s", src_dir, exc)
            return
        try:
            file_hashes[arcname] = _sha256_file(src_dir)
        except OSError as exc:
            logger.warning("Could not hash %s: %s", src_dir, exc)
        return

    for path in sorted(src_dir.rglob("*")):
        resolved = path.resolve()
        # Skip anything inside an excluded directory.
        if any(
            resolved == ex or ex in resolved.parents
            for ex in excludes
        ):
            continue
        rel = path.relative_to(src_dir)
        in_archive = f"{arcname}/{rel.as_posix()}"
        try:
            tar.add(path, arcname=in_archive, recursive=False)
        except OSError as exc:
            logger.warning("Could not add %s to archive: %s", path, exc)
            continue
        if path.is_file():
            try:
                file_hashes[in_archive] = _sha256_file(path)
            except OSError as exc:
                logger.warning("Could not hash %s: %s", path, exc)


async def _dump_graph(
    config: WheelerConfig,
) -> tuple[bytes, bytes, dict[str, int], dict[str, int], bool]:
    """Pull every node and relationship out of Neo4j.

    Returns: (nodes_jsonl_bytes, rels_jsonl_bytes, node_counts_by_label,
    rel_counts_by_type, graph_available).

    On any backend failure (Neo4j down, circuit open, etc.) returns empty
    JSONL blobs, empty counts, graph_available=False. The backup must not
    fail just because the graph is offline.
    """
    backend = get_backend(config)
    node_counts: dict[str, int] = {}
    rel_counts: dict[str, int] = {}
    nodes_buf = io.BytesIO()
    rels_buf = io.BytesIO()

    try:
        await backend.initialize()
    except Exception as exc:
        logger.warning("Graph unavailable for backup (initialize failed): %s", exc)
        return b"", b"", {}, {}, False

    try:
        try:
            node_records = await backend.run_cypher(_NODE_DUMP_CYPHER)
        except Exception as exc:
            logger.warning("Graph node dump failed: %s", exc)
            return b"", b"", {}, {}, False

        for rec in node_records:
            labels = rec.get("labels") or []
            label = labels[0] if labels else "Unknown"
            node_counts[label] = node_counts.get(label, 0) + 1
            line = json.dumps(
                {"label": label, "labels": labels, "props": rec.get("props") or {}},
                sort_keys=True,
            )
            nodes_buf.write(line.encode("utf-8"))
            nodes_buf.write(b"\n")

        try:
            rel_records = await backend.run_cypher(_REL_DUMP_CYPHER)
        except Exception as exc:
            logger.warning("Graph relationship dump failed: %s", exc)
            # Keep node dump but report rels as empty.
            rel_records = []

        for rec in rel_records:
            rt = rec.get("rel_type") or "UNKNOWN"
            rel_counts[rt] = rel_counts.get(rt, 0) + 1
            line = json.dumps(
                {
                    "source_id": rec.get("source_id"),
                    "rel_type": rt,
                    "rel_props": rec.get("rel_props") or {},
                    "target_id": rec.get("target_id"),
                },
                sort_keys=True,
            )
            rels_buf.write(line.encode("utf-8"))
            rels_buf.write(b"\n")
    finally:
        try:
            await backend.close()
        except Exception:
            pass

    return (
        nodes_buf.getvalue(),
        rels_buf.getvalue(),
        node_counts,
        rel_counts,
        True,
    )


def _rewrite_nodes_jsonl(
    nodes_jsonl: bytes,
    project_root: Path,
) -> tuple[bytes, list[dict]]:
    """Rewrite path fields in nodes_jsonl using the ${PROJECT}/ sentinel.

    Returns (rewritten_bytes, external_references).
    external_references entries have shape:
      {node_id, label, field, original_path, **discover_external_reference(original_path)}
    """
    external_references: list[dict] = []
    out = io.BytesIO()
    for raw_line in nodes_jsonl.splitlines():
        if not raw_line.strip():
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            out.write(raw_line)
            out.write(b"\n")
            continue

        label = entry.get("label", "")
        props = entry.get("props") or {}
        node_id = props.get("id", "")

        for field in iter_path_fields(label):
            original = props.get(field)
            if not original:
                continue
            rewritten, is_internal = relativize(str(original), project_root)
            props[field] = rewritten
            if not is_internal:
                ext = {"node_id": node_id, "label": label, "field": field, "original_path": original}
                git_info = discover_external_reference(original)
                if git_info:
                    ext.update(git_info)
                external_references.append(ext)

        entry["props"] = props
        out.write(json.dumps(entry, sort_keys=True).encode("utf-8"))
        out.write(b"\n")

    return out.getvalue(), external_references


def _rewrite_knowledge_json_bytes(content: bytes, project_root: Path) -> bytes:
    """Rewrite path fields in a knowledge JSON blob (in-bytes, not on disk)."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return content

    node_type = data.get("type", "")
    changed = False
    for field in iter_path_fields(node_type):
        original = data.get(field)
        if original:
            rewritten, _ = relativize(str(original), project_root)
            if rewritten != original:
                data[field] = rewritten
                changed = True

    if not changed:
        return content
    return json.dumps(data, indent=2, sort_keys=True).encode("utf-8")


def _rewrite_synthesis_md_bytes(content: bytes, project_root: Path) -> bytes:
    """Replace absolute path occurrences of project_root in synthesis Markdown.

    Replaces any substring matching the resolved project root prefix (with
    optional trailing slash) with ``${PROJECT}/``, matching the sentinel
    that ``portability.relativize`` and ``portability.absolutize`` use.
    Only modifies the bytes; on-disk file is never touched.

    The emitted sentinel is always ``${PROJECT}/`` (with trailing slash) so
    that ``absolutize`` in portability.py recognises it.  An existing
    trailing slash in the source is consumed to avoid ``${PROJECT}//``.
    """
    root_str = str(project_root.resolve())
    escaped = re.escape(root_str)
    # Pass 1: replace <root>/ (with slash) -> ${PROJECT}/
    # The slash is consumed so we never produce ${PROJECT}//.
    p_with_slash = re.compile(escaped.encode("utf-8") + rb"/")
    result = p_with_slash.sub(b"${PROJECT}/", content)
    # Pass 2: replace bare <root> at a token boundary (quote, whitespace,
    # end-of-string) that was NOT followed by a slash.
    p_bare = re.compile(escaped.encode("utf-8") + rb"(?=\"|\s|$)")
    return p_bare.sub(b"${PROJECT}/", result)


def _strip_neo4j_password(yaml_bytes: bytes) -> bytes:
    """Replace the Neo4j password value with the literal placeholder.

    Parses YAML, sets neo4j.password = '${NEO4J_PASSWORD}', re-serialises.
    Falls back to a regex replacement on parse failure so the function never
    raises.
    """
    try:
        import yaml as _yaml

        data = _yaml.safe_load(yaml_bytes.decode("utf-8", errors="replace")) or {}
        neo4j_section = data.get("neo4j")
        if isinstance(neo4j_section, dict):
            neo4j_section["password"] = "${NEO4J_PASSWORD}"
            data["neo4j"] = neo4j_section
        return _yaml.dump(data, default_flow_style=False, sort_keys=False).encode("utf-8")
    except Exception:
        # Regex fallback: replace any password: ... line.
        return re.sub(
            rb"(password\s*:\s*).*",
            rb'\1"${NEO4J_PASSWORD}"',
            yaml_bytes,
        )


def _build_embedder_info(config: WheelerConfig) -> dict:
    """Build the embedder identity dict for the manifest.

    Dimension resolution order:
      1. Probe on-disk vectors (if any) via EmbeddingStore.load().
      2. Look up the dim from fastembed's model registry (metadata only,
         no model download).
      3. Fall back to None.
    """
    model: str | None = None
    dim: int | None = None
    fastembed_version: str | None = None

    try:
        model = config.search.model or None
    except Exception:
        pass

    try:
        import fastembed

        fastembed_version = getattr(fastembed, "__version__", None)
    except ImportError:
        return {"model": model, "dim": None, "fastembed_version": None}

    # Path 1: probe on-disk vectors (best-effort).
    try:
        from wheeler.search.embeddings import EmbeddingStore  # lazy import

        store_path = str(
            getattr(config.search, "store_path", ".wheeler/embeddings")
        )
        if Path(store_path).exists():
            store = EmbeddingStore(store_path)
            store.load()
            if store._embeddings:
                first_vec = next(iter(store._embeddings.values()))
                dim = int(len(first_vec))
    except Exception:
        pass

    # Path 2: fastembed metadata lookup if we still don't have a dim.
    if dim is None and model:
        try:
            from fastembed import TextEmbedding

            for m in TextEmbedding.list_supported_models():
                if m.get("model") == model:
                    raw_dim = m.get("dim")
                    if isinstance(raw_dim, int):
                        dim = raw_dim
                    break
        except Exception:
            pass

    return {"model": model, "dim": dim, "fastembed_version": fastembed_version}


async def _record_backup_execution(
    config: WheelerConfig, archive_path: Path
) -> None:
    """Best-effort: record an Execution(kind=backup) node in the graph.

    Skipped silently if the graph is offline or anything in the dispatch path
    raises. The backup itself must not fail because of this.
    """
    try:
        from wheeler.tools.graph_tools import execute_tool

        await execute_tool(
            "add_execution",
            {
                "kind": "backup",
                "description": f"Backup created: {archive_path}",
                "status": "completed",
            },
            config,
        )
    except Exception as exc:
        logger.info("Skipped backup Execution record (graph offline?): %s", exc)


async def create_backup(
    config: WheelerConfig,
    destination: Path | None = None,
    include_remote: bool = False,
    scope: Literal["project", "graph-only"] = "project",
    max_artifact_size: int | None = None,
    allow_secrets: bool = False,
    yes: bool = True,
) -> Path:
    """Snapshot canonical Wheeler state to a tar.gz archive.

    Parameters
    ----------
    config:
        Loaded ``WheelerConfig``.
    destination:
        Directory to write the archive into. Defaults to
        ``<knowledge parent>/.wheeler/backups/``. Created if missing.
    include_remote:
        Reserved. Local-only for now; remote destinations (S3, Drive, etc.)
        will be wired through the ``wheeler.yaml`` ``backup:`` section in a
        follow-up.
    scope:
        ``"project"`` (default) packs the full project_root tree. ``"graph-only"``
        packs only the Wheeler-managed subset (v1 behaviour): knowledge/,
        synthesis/, .wheeler/, wheeler.yaml plus graph JSONL.
    max_artifact_size:
        If set, skip files larger than this many bytes. Skipped files are
        recorded in the manifest under ``excluded_paths`` with ``reason: too_large``.
    allow_secrets:
        If False (default), abort with ``BackupAbortedDueToSecrets`` when
        ``scan_for_secrets`` detects API-key patterns in any packed file.
    yes:
        Unused. Accepted for library-clean signature compatibility; the CLI
        handles interactive prompts before calling this function.

    Returns
    -------
    Path
        Absolute path to the produced ``wheeler-backup-*.tar.gz``.
    """
    if include_remote:
        logger.warning(
            "include_remote=True requested but remote backends are not yet "
            "wired. Producing local archive only."
        )

    # Resolve project_root from config.
    project_root = Path(config.project_root).resolve()
    if not project_root.exists():
        raise ValueError(
            f"project_root does not exist: {project_root!s}. "
            "Set project_root in wheeler.yaml or ensure the directory exists."
        )

    dest_dir = _resolve_destination(config, destination)
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    stamp = timestamp.strftime("%Y%m%d-%H%M%S")
    archive_path = (dest_dir / f"wheeler-backup-{stamp}.tar.gz").resolve()

    knowledge_dir = Path(config.knowledge_path)
    if not knowledge_dir.is_absolute():
        knowledge_dir = (project_root / knowledge_dir).resolve()
    else:
        knowledge_dir = knowledge_dir.resolve()

    synthesis_dir = Path(config.synthesis_path)
    if not synthesis_dir.is_absolute():
        synthesis_dir = (project_root / synthesis_dir).resolve()
    else:
        synthesis_dir = synthesis_dir.resolve()

    wheeler_dir = (project_root / ".wheeler").resolve()
    wheeler_yaml = (project_root / "wheeler.yaml").resolve()

    # Exclude .wheeler/backups/ to avoid archiving prior archives recursively.
    backups_dir = dest_dir.resolve()

    # Pull the graph first so its size shows up in the manifest counts.
    (
        nodes_jsonl_raw,
        rels_jsonl,
        node_counts,
        rel_counts,
        graph_available,
    ) = await _dump_graph(config)

    # Rewrite path fields in the node JSONL and collect external references.
    nodes_jsonl, external_references = _rewrite_nodes_jsonl(nodes_jsonl_raw, project_root)

    file_hashes: dict[str, str] = {}
    archive_layout: list[str] = []
    excluded_paths: list[dict] = []
    secret_offenders: list[dict] = []

    # Helper: scan bytes for secrets and record offenders.
    def _check_secrets(data: bytes, arc_path: str) -> bool:
        """Return True if clean (or secrets allowed). Record offenders."""
        hits = scan_for_secrets(data, arc_path)
        if hits:
            for name, snippet in hits:
                secret_offenders.append(
                    {"path": arc_path, "pattern": name, "snippet": snippet}
                )
            return allow_secrets
        return True

    # Helper: add bytes to tar with hashing.
    def _pack(arc_path: str, data: bytes) -> None:
        _add_bytes_to_tar(tar, arc_path, data)
        file_hashes[arc_path] = _sha256_bytes(data)

    with tarfile.open(archive_path, mode="w:gz") as tar:
        if scope == "project":
            # Walk the full project_root tree and add everything under project/.
            gi_patterns = _parse_gitignore(project_root)

            for abs_path in sorted(project_root.rglob("*")):
                if not abs_path.is_file():
                    continue

                resolved = abs_path.resolve()
                rel = abs_path.relative_to(project_root)
                rel_posix = rel.as_posix()
                arc_path = f"project/{rel_posix}"

                # --- Exclusion checks ---

                # Excluded hardcoded directory names anywhere in the path.
                if any(part in _EXCLUDED_DIRS for part in rel.parts):
                    excluded_paths.append({"path": arc_path, "reason": "excluded_dir"})
                    continue

                # Exclude .wheeler/backups/ (avoid recursive archives).
                if resolved == backups_dir or backups_dir in resolved.parents:
                    excluded_paths.append({"path": arc_path, "reason": "excluded_dir"})
                    continue

                # .gitignore rules (best-effort).
                if _gitignored(rel_posix, gi_patterns):
                    excluded_paths.append({"path": arc_path, "reason": "gitignored"})
                    continue

                # Size check.
                try:
                    size = abs_path.stat().st_size
                except OSError:
                    size = 0
                if max_artifact_size is not None and size > max_artifact_size:
                    excluded_paths.append({"path": arc_path, "reason": "too_large"})
                    continue

                # Read bytes.
                try:
                    raw = abs_path.read_bytes()
                except OSError as exc:
                    logger.warning("Could not read %s: %s", abs_path, exc)
                    continue

                # Special handling: wheeler.yaml (strip password).
                is_wheeler_yaml = (resolved == wheeler_yaml)
                if is_wheeler_yaml:
                    raw = _strip_neo4j_password(raw)

                # Special handling: knowledge/*.json (rewrite paths in bytes).
                is_knowledge_json = (
                    resolved.parent == knowledge_dir
                    and rel_posix.endswith(".json")
                )
                if is_knowledge_json:
                    raw = _rewrite_knowledge_json_bytes(raw, project_root)

                # Special handling: synthesis/*.md (rewrite absolute path refs).
                is_synthesis_md = (
                    resolved.parent == synthesis_dir
                    and rel_posix.endswith(".md")
                )
                if is_synthesis_md:
                    raw = _rewrite_synthesis_md_bytes(raw, project_root)

                # Secret scan AFTER rewrites (so ${PROJECT} tokens are clean).
                if not _check_secrets(raw, arc_path):
                    # allow_secrets=False: we will raise after the loop;
                    # continue to collect all offenders.
                    continue

                _pack(arc_path, raw)
                if arc_path not in archive_layout:
                    # Only record top-level directory entries.
                    pass

            if secret_offenders and not allow_secrets:
                raise BackupAbortedDueToSecrets(secret_offenders)

            archive_layout.append("project/")

        else:
            # scope="graph-only": v1 behaviour (Wheeler-managed subset only).
            # We still scan for secrets and honour allow_secrets so that an
            # Anthropic API key in wheeler.yaml or a knowledge JSON cannot
            # slip through just because the full project tree was not packed.
            # The scanned pattern set lives in wheeler/portability.py.
            graph_only_dirs: list[tuple[Path, str]] = []
            if knowledge_dir.exists():
                graph_only_dirs.append((knowledge_dir, "knowledge"))
            if synthesis_dir.exists():
                graph_only_dirs.append((synthesis_dir, "synthesis"))
            if wheeler_dir.exists():
                graph_only_dirs.append((wheeler_dir, ".wheeler"))

            for src_dir, arcname in graph_only_dirs:
                for abs_path in sorted(src_dir.rglob("*")):
                    if not abs_path.is_file():
                        continue
                    resolved = abs_path.resolve()
                    # Skip .wheeler/backups/ subtree.
                    if resolved == backups_dir or backups_dir in resolved.parents:
                        continue
                    rel = abs_path.relative_to(src_dir)
                    arc_path = f"{arcname}/{rel.as_posix()}"
                    try:
                        raw = abs_path.read_bytes()
                    except OSError as exc:
                        logger.warning("Could not read %s: %s", abs_path, exc)
                        continue
                    if not _check_secrets(raw, arc_path):
                        continue
                    _pack(arc_path, raw)
                archive_layout.append(f"{arcname}/")

            if wheeler_yaml.exists():
                raw = wheeler_yaml.read_bytes()
                raw = _strip_neo4j_password(raw)
                if _check_secrets(raw, "wheeler.yaml"):
                    _pack("wheeler.yaml", raw)
                archive_layout.append("wheeler.yaml")

            if secret_offenders and not allow_secrets:
                raise BackupAbortedDueToSecrets(secret_offenders)

        # Graph dumps (always present, possibly empty).
        _add_bytes_to_tar(tar, "graph_nodes.jsonl", nodes_jsonl)
        _add_bytes_to_tar(tar, "graph_relationships.jsonl", rels_jsonl)
        file_hashes["graph_nodes.jsonl"] = _sha256_bytes(nodes_jsonl)
        file_hashes["graph_relationships.jsonl"] = _sha256_bytes(rels_jsonl)
        archive_layout.append("graph_nodes.jsonl")
        archive_layout.append("graph_relationships.jsonl")

        # Import schema version constant.
        try:
            from wheeler import KNOWLEDGE_SCHEMA_VERSION
        except ImportError:
            KNOWLEDGE_SCHEMA_VERSION = "1"  # fallback

        # Build allowed_secret_files audit list.  When allow_secrets=True and
        # secrets were found, record each offending file with its pattern names
        # so the audit trail is not silent.  Empty list when allow_secrets=False
        # or no secrets were found (the normal case).
        allowed_secret_files: list[dict] = []
        if allow_secrets and secret_offenders:
            # Deduplicate: one entry per file, collecting all pattern names.
            seen: dict[str, set[str]] = {}
            for offender in secret_offenders:
                fpath = offender["path"]
                seen.setdefault(fpath, set()).add(offender["pattern"])
            for fpath, patterns in sorted(seen.items()):
                allowed_secret_files.append(
                    {"path": fpath, "patterns": sorted(patterns)}
                )

        manifest: dict = {
            # v1 fields (unchanged for back-compat).
            "timestamp": timestamp.isoformat(),
            "wheeler_version": _wheeler_version(),
            "graph_available": graph_available,
            "node_counts_by_label": dict(sorted(node_counts.items())),
            "relationship_count_by_type": dict(sorted(rel_counts.items())),
            "total_nodes": sum(node_counts.values()),
            "total_relationships": sum(rel_counts.values()),
            "canonical_file_hashes": dict(sorted(file_hashes.items())),
            "archive_layout": archive_layout + ["HANDOFF.md", "manifest.json"],
            # v2 new fields.
            "manifest_version": 2,
            "archive_uuid": uuid.uuid4().hex,
            "path_rewrite_scheme": "PROJECT_VAR",
            "project_root_at_pack": str(project_root),
            "embedder": _build_embedder_info(config),
            "schema_version": KNOWLEDGE_SCHEMA_VERSION,
            "source": {
                "hostname": socket.gethostname(),
                "platform": sys.platform,
                "python_version": _platform_module.python_version(),
                "packed_by": _safe_getuser(),
            },
            "external_references": external_references,
            "excluded_paths": excluded_paths,
            "allowed_secret_files": allowed_secret_files,
        }
        # Signature must be computed last (covers everything above).
        manifest["manifest_signature"] = compute_manifest_signature(manifest)

        # Pack HANDOFF.md (top-level, alongside manifest.json).
        handoff_bytes = _generate_handoff_md(
            manifest,
            scope=scope,
            archive_filename=archive_path.name,
        )
        _add_bytes_to_tar(tar, "HANDOFF.md", handoff_bytes)

        manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        _add_bytes_to_tar(tar, "manifest.json", manifest_bytes)

    # Best-effort: record an Execution node so the backup shows in graph history.
    await _record_backup_execution(config, archive_path)

    logger.info("Wheeler backup written: %s", archive_path)
    return archive_path


def _safe_getuser() -> str:
    """Return the current username, falling back to 'unknown' on failure."""
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"
