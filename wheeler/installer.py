"""Wheeler installer: install/uninstall/update slash commands and agents."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Optional

import wheeler

MANIFEST_PATH = Path.home() / ".claude" / "wheeler-manifest.json"
INSTALL_BASE = Path.home() / ".claude"
COMMANDS_REL = Path("commands") / "wh"
AGENTS_REL = Path("agents")


def _hash_file(path: Path) -> str:
    """Return SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_data_path() -> Path:
    """Return path to wheeler/_data/ using importlib.resources."""
    return Path(str(resources.files("wheeler") / "_data"))


def install(link: bool = False) -> dict[str, str]:
    """Copy (or symlink) files from wheeler/_data/ to ~/.claude/.

    Args:
        link: If True, create symlinks instead of copies.

    Returns:
        Dict mapping relative path -> SHA-256 hash.
    """
    data = _get_data_path()
    installed: dict[str, str] = {}

    mappings = [
        (data / "commands", INSTALL_BASE / COMMANDS_REL, COMMANDS_REL),
        (data / "agents", INSTALL_BASE / AGENTS_REL, AGENTS_REL),
    ]

    for src_dir, dst_dir, rel_base in mappings:
        if not src_dir.is_dir():
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src_file in sorted(src_dir.glob("*.md")):
            dst_file = dst_dir / src_file.name
            if dst_file.exists() or dst_file.is_symlink():
                dst_file.unlink()
            if link:
                dst_file.symlink_to(src_file.resolve())
            else:
                shutil.copy2(src_file, dst_file)
            rel_key = str(rel_base / src_file.name)
            installed[rel_key] = _hash_file(src_file)

    write_manifest(installed)
    return installed


def uninstall() -> list[str]:
    """Remove all files listed in manifest, then remove the manifest."""
    manifest = read_manifest()
    removed: list[str] = []
    if manifest is None:
        return removed

    for rel_path in manifest.get("files", {}):
        full = INSTALL_BASE / rel_path
        if full.exists() or full.is_symlink():
            full.unlink()
            removed.append(rel_path)

    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()

    return removed


def update() -> None:
    """Backup local mods, pip-upgrade wheeler, then reinstall files."""
    backup_local_mods()
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "wheeler"],
        check=True,
    )
    install()


def sync_data(repo_root: Path | None = None) -> list[str]:
    """Dev command: copy project slash commands/agents into wheeler/_data/.

    Args:
        repo_root: Repository root. Auto-detected if None.

    Returns:
        List of files that were out of sync (different hash).
    """
    if repo_root is None:
        repo_root = _find_repo_root()

    data = _get_data_path()
    out_of_sync: list[str] = []

    mappings = [
        (repo_root / ".claude" / "commands" / "wh", data / "commands", "*.md"),
        (repo_root / ".claude" / "agents", data / "agents", "wheeler-*.md"),
    ]

    for src_dir, dst_dir, pattern in mappings:
        if not src_dir.is_dir():
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src_file in sorted(src_dir.glob(pattern)):
            dst_file = dst_dir / src_file.name
            src_hash = _hash_file(src_file)
            if dst_file.exists() and _hash_file(dst_file) == src_hash:
                continue
            shutil.copy2(src_file, dst_file)
            out_of_sync.append(str(src_file.relative_to(repo_root)))

    return out_of_sync


def _find_repo_root() -> Path:
    """Find the repository root by looking for .git directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    # Fallback: walk up from cwd looking for .claude/commands/wh/
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".claude" / "commands" / "wh").is_dir():
            return parent
    raise FileNotFoundError("Cannot find repository root")


def check_version() -> tuple[str, Optional[str], bool]:
    """Compare installed version vs PyPI latest.

    Returns:
        (installed_version, latest_or_None, update_available)
    """
    installed = wheeler.__version__
    latest: Optional[str] = None
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "index", "versions", "wheeler"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Output format: "wheeler (X.Y.Z)"
            for line in result.stdout.splitlines():
                if "wheeler" in line and "(" in line:
                    latest = line.split("(")[1].split(")")[0].strip()
                    break
    except (subprocess.TimeoutExpired, Exception):
        pass

    update_available = latest is not None and latest != installed
    return installed, latest, update_available


def write_manifest(files: dict[str, str]) -> None:
    """Write manifest with version, timestamp, and file hashes."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": wheeler.__version__,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")


def read_manifest() -> dict | None:
    """Read and return parsed manifest, or None if not found."""
    if not MANIFEST_PATH.exists():
        return None
    try:
        return json.loads(MANIFEST_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def backup_local_mods() -> list[str]:
    """Back up locally modified files before update.

    Compares installed file hashes against manifest.
    Modified files are copied to ~/.claude/wheeler-patches/<timestamp>/.

    Returns:
        List of backed-up relative paths.
    """
    manifest = read_manifest()
    if manifest is None:
        return []

    backed_up: list[str] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path.home() / ".claude" / "wheeler-patches" / timestamp

    for rel_path, expected_hash in manifest.get("files", {}).items():
        full = INSTALL_BASE / rel_path
        if not full.exists():
            continue
        current_hash = _hash_file(full)
        if current_hash != expected_hash:
            backup_dir.mkdir(parents=True, exist_ok=True)
            dst = backup_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
            backed_up.append(rel_path)

    return backed_up


def merge_mcp_config(project_dir: Path | None = None) -> None:
    """Merge wheeler MCP entries into project .mcp.json.

    Adds wheeler and neo4j server entries without overwriting
    existing entries the user may have customized.

    Args:
        project_dir: Project directory. Uses cwd if None.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    # Read template from _data
    data = _get_data_path()
    template_path = data / "mcp.json"
    if not template_path.exists():
        return

    template = json.loads(template_path.read_text())
    template_servers = template.get("mcpServers", {})

    # Read existing project config
    project_mcp = project_dir / ".mcp.json"
    if project_mcp.exists():
        try:
            existing = json.loads(project_mcp.read_text())
        except (json.JSONDecodeError, OSError):
            existing = {}
    else:
        existing = {}

    existing_servers = existing.setdefault("mcpServers", {})

    # Merge: add template entries only if not already present
    for name, config in template_servers.items():
        if name not in existing_servers:
            existing_servers[name] = config

    project_mcp.write_text(json.dumps(existing, indent=2) + "\n")
