"""Workspace scanner: walks project directory and collects file inventory."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from wheeler.config import WorkspaceConfig

logger = logging.getLogger(__name__)


_SCRIPT_EXTENSIONS = {".py", ".m"}
_DATA_EXTENSIONS = {".mat", ".h5", ".csv", ".hdf5"}


@dataclass
class FileInfo:
    path: str  # relative to project_dir
    category: str  # "script" | "data" | "other"
    extension: str
    size_bytes: int


@dataclass
class WorkspaceSummary:
    project_dir: str
    scripts: list[FileInfo] = field(default_factory=list)
    data_files: list[FileInfo] = field(default_factory=list)
    total_files: int = 0


def _categorize(ext: str) -> str:
    if ext in _SCRIPT_EXTENSIONS:
        return "script"
    if ext in _DATA_EXTENSIONS:
        return "data"
    return "other"


def scan_workspace(config: WorkspaceConfig) -> WorkspaceSummary:
    """Walk project_dir, collect files matching scan_patterns."""
    root = Path(config.project_dir).resolve()
    summary = WorkspaceSummary(project_dir=str(root))

    if not root.is_dir():
        logger.debug("Workspace dir does not exist: %s", root)
        return summary

    logger.debug("Scanning workspace: %s", root)

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        # Check exclusions
        rel = path.relative_to(root)
        if any(part in config.exclude_dirs for part in rel.parts):
            continue

        # Check against scan patterns
        if not any(fnmatch(path.name, pat) for pat in config.scan_patterns):
            continue

        ext = path.suffix.lower()
        category = _categorize(ext)
        info = FileInfo(
            path=str(rel),
            category=category,
            extension=ext,
            size_bytes=path.stat().st_size,
        )

        if category == "script":
            summary.scripts.append(info)
        elif category == "data":
            summary.data_files.append(info)

        summary.total_files += 1

    return summary


def format_workspace_context(summary: WorkspaceSummary) -> str:
    """Format workspace summary as compact markdown for system prompt injection."""
    if summary.total_files == 0:
        return ""

    lines = [f"## Workspace: {summary.project_dir}"]

    if summary.scripts:
        # Group by parent directory
        dirs: dict[str, list[str]] = {}
        for f in summary.scripts:
            parent = str(Path(f.path).parent)
            dirs.setdefault(parent, []).append(Path(f.path).name)
        dir_summaries = []
        for d, files in sorted(dirs.items()):
            if len(files) <= 3:
                dir_summaries.append(f"{d}/ ({', '.join(files)})")
            else:
                dir_summaries.append(f"{d}/ ({len(files)} files)")
        lines.append(f"Scripts ({len(summary.scripts)}): {', '.join(dir_summaries)}")

    if summary.data_files:
        dirs: dict[str, list[str]] = {}
        for f in summary.data_files:
            parent = str(Path(f.path).parent)
            dirs.setdefault(parent, []).append(Path(f.path).name)
        dir_summaries = []
        for d, files in sorted(dirs.items()):
            if len(files) <= 3:
                dir_summaries.append(f"{d}/ ({', '.join(files)})")
            else:
                dir_summaries.append(f"{d}/ ({len(files)} files)")
        lines.append(f"Data files ({len(summary.data_files)}): {', '.join(dir_summaries)}")

    # Key paths: unique top-level directories
    top_dirs = sorted({Path(f.path).parts[0] for f in summary.scripts + summary.data_files if len(Path(f.path).parts) > 1})
    if top_dirs:
        lines.append(f"Key paths: {', '.join(d + '/' for d in top_dirs)}")

    return "\n".join(lines)
