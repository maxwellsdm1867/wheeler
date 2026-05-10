"""Snapshot Wheeler's canonical state to a single tar.gz archive.

This module is invoked from the Typer CLI (``wheeler backup``), NOT from an
MCP tool.

Why a CLI subcommand and not an MCP tool: the MCP transport caps tool
results at ~235k chars, which a full graph dump (nodes + relationships)
saturates almost immediately on a real research project. Running in-process
through ``backend.run_cypher`` avoids the cap entirely and lets us stream
JSONL into the archive.

Layout of the produced archive (``wheeler-backup-YYYYMMDD-HHMMSS.tar.gz``):

    knowledge/                  canonical JSON metadata for every node
    synthesis/                  Obsidian-compatible markdown
    .wheeler/                   embeddings, request log, repair queue
                                (excludes .wheeler/backups/ to avoid recursion)
    wheeler.yaml                config file (if present)
    graph_nodes.jsonl           one JSON object per line, all live nodes
    graph_relationships.jsonl   one JSON object per line, all live relationships
    manifest.json               timestamp, version, counts, file hashes,
                                archive layout

If Neo4j is unreachable the file layers are still archived; the JSONL graph
dumps are written empty and the manifest records ``graph_available: false``.

TODO (follow-up): a ``backup:`` section in wheeler.yaml plus an
``include_remote`` switch that pushes the archive to S3 / Drive / etc.
Local-only for now.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from wheeler.config import WheelerConfig
from wheeler.graph.backend import get_backend

logger = logging.getLogger(__name__)


_NODE_DUMP_CYPHER = (
    "MATCH (n) "
    "RETURN labels(n) AS labels, properties(n) AS props"
)

_REL_DUMP_CYPHER = (
    "MATCH (a)-[r]->(b) "
    "RETURN a.id AS source_id, type(r) AS rel_type, "
    "properties(r) AS rel_props, b.id AS target_id"
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

    def _filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        # info.name is the in-archive name; excludes is resolved against disk.
        return info

    if not src_dir.is_dir():
        # File-only case: just add it.
        if src_dir.resolve() in excludes:
            return
        tar.add(src_dir, arcname=arcname, filter=_filter)
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
            tar.add(path, arcname=in_archive, recursive=False, filter=_filter)
        except OSError as exc:
            logger.warning("Could not add %s to archive: %s", path, exc)
            continue
        if path.is_file():
            try:
                file_hashes[in_archive] = _sha256_file(path)
            except OSError as exc:
                logger.warning("Could not hash %s: %s", path, exc)


def _add_bytes_to_tar(
    tar: tarfile.TarFile, arcname: str, data: bytes
) -> None:
    """Add an in-memory bytes blob to the tar."""
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mtime = int(datetime.now(timezone.utc).timestamp())
    tar.addfile(info, io.BytesIO(data))


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

    Returns
    -------
    Path
        Absolute path to the produced ``wheeler-backup-*.tar.gz``.
    """
    if include_remote:
        # TODO: wire wheeler.yaml backup: section + pluggable remotes.
        logger.warning(
            "include_remote=True requested but remote backends are not yet "
            "wired. Producing local archive only."
        )

    dest_dir = _resolve_destination(config, destination)
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    stamp = timestamp.strftime("%Y%m%d-%H%M%S")
    archive_path = (dest_dir / f"wheeler-backup-{stamp}.tar.gz").resolve()

    knowledge_dir = Path(config.knowledge_path).resolve()
    synthesis_dir = Path(config.synthesis_path).resolve()
    # Cwd-relative paths for .wheeler/ and wheeler.yaml: those are always
    # rooted at the project working directory by convention.
    project_root = (
        knowledge_dir.parent
        if Path(config.knowledge_path).is_absolute()
        else Path.cwd()
    )
    wheeler_dir = (project_root / ".wheeler").resolve()
    wheeler_yaml = (project_root / "wheeler.yaml").resolve()

    # Exclude .wheeler/backups/ to avoid archiving prior archives recursively.
    backups_dir = (dest_dir).resolve()

    # Pull the graph first so its size shows up in the manifest counts.
    (
        nodes_jsonl,
        rels_jsonl,
        node_counts,
        rel_counts,
        graph_available,
    ) = await _dump_graph(config)

    file_hashes: dict[str, str] = {}
    archive_layout: list[str] = []

    with tarfile.open(archive_path, mode="w:gz") as tar:
        # File-layer canonical state.
        if knowledge_dir.exists():
            _add_dir_to_tar(tar, knowledge_dir, "knowledge", file_hashes)
            archive_layout.append("knowledge/")
        if synthesis_dir.exists():
            _add_dir_to_tar(tar, synthesis_dir, "synthesis", file_hashes)
            archive_layout.append("synthesis/")
        if wheeler_dir.exists():
            _add_dir_to_tar(
                tar,
                wheeler_dir,
                ".wheeler",
                file_hashes,
                excludes={backups_dir},
            )
            archive_layout.append(".wheeler/")
        if wheeler_yaml.exists():
            _add_dir_to_tar(tar, wheeler_yaml, "wheeler.yaml", file_hashes)
            archive_layout.append("wheeler.yaml")

        # Graph dumps (always present, possibly empty).
        _add_bytes_to_tar(tar, "graph_nodes.jsonl", nodes_jsonl)
        _add_bytes_to_tar(tar, "graph_relationships.jsonl", rels_jsonl)
        archive_layout.append("graph_nodes.jsonl")
        archive_layout.append("graph_relationships.jsonl")

        manifest = {
            "timestamp": timestamp.isoformat(),
            "wheeler_version": _wheeler_version(),
            "graph_available": graph_available,
            "node_counts_by_label": dict(sorted(node_counts.items())),
            "relationship_count_by_type": dict(sorted(rel_counts.items())),
            "total_nodes": sum(node_counts.values()),
            "total_relationships": sum(rel_counts.values()),
            "canonical_file_hashes": dict(sorted(file_hashes.items())),
            "archive_layout": archive_layout + ["manifest.json"],
        }
        manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        _add_bytes_to_tar(tar, "manifest.json", manifest_bytes)

    # Best-effort: record an Execution node so the backup shows in graph history.
    await _record_backup_execution(config, archive_path)

    logger.info("Wheeler backup written: %s", archive_path)
    return archive_path
