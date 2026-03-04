"""Project scaffolding: directory detection, creation, and config writing."""

from __future__ import annotations

from pathlib import Path

import yaml

from wheeler.config import WheelerConfig, ProjectMeta, ProjectPaths

# Common directory names by category, checked during detection.
_DETECTION_PATTERNS: dict[str, list[str]] = {
    "code": ["scripts", "src", "analysis", "code", "matlab", "lib"],
    "data": ["data", "raw", "datasets", "recordings"],
    "results": ["results", "output", "outputs", "processed"],
    "figures": ["figures", "figs", "plots", "images"],
    "docs": ["docs", "writing", "drafts", "papers", "notes"],
}

# Wheeler-managed directories, always created.
_MANAGED_DIRS = [".plans", ".logs", ".wheeler"]


def detect_project_dirs(root: Path) -> dict[str, list[str]]:
    """Scan *root* for directories matching common category patterns.

    Returns a dict mapping category name to list of relative directory paths
    that exist under *root*.
    """
    found: dict[str, list[str]] = {}
    for category, patterns in _DETECTION_PATTERNS.items():
        matches: list[str] = []
        for name in patterns:
            candidate = root / name
            if candidate.is_dir():
                matches.append(name)
        if matches:
            found[category] = matches
    return found


def create_project_dirs(root: Path, dirs: list[str]) -> list[str]:
    """Create directories under *root*. Returns list of directories that were created."""
    created: list[str] = []
    for d in dirs:
        target = root / d
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(d)
    return created


def scaffold_managed_dirs(root: Path) -> list[str]:
    """Create Wheeler-managed directories (.plans, .logs, .wheeler).

    Returns list of directories that were newly created.
    """
    return create_project_dirs(root, _MANAGED_DIRS)


def write_config(
    root: Path,
    *,
    project: ProjectMeta | None = None,
    paths: ProjectPaths | None = None,
    existing_config: WheelerConfig | None = None,
) -> Path:
    """Write (or update) ``wheeler.yaml`` in *root*.

    If *existing_config* is provided, merges new values into it.
    Returns the path to the written file.
    """
    config = existing_config or WheelerConfig()
    if project is not None:
        config.project = project
    if paths is not None:
        config.paths = paths

    config_path = root / "wheeler.yaml"
    data = config.model_dump(exclude_defaults=True)
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return config_path


def scaffold_project(root: Path) -> dict[str, list[str]]:
    """Full scaffold: detect dirs + create managed dirs.

    Returns ``{"detected": [...], "created": [...]}``.
    """
    detected = detect_project_dirs(root)
    created = scaffold_managed_dirs(root)
    return {"detected": detected, "created": created}
