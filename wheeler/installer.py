"""Wheeler installer: install/uninstall/update slash commands and agents."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Optional

import wheeler

logger = logging.getLogger(__name__)

MANIFEST_PATH = Path.home() / ".claude" / "wheeler-manifest.json"
INSTALL_BASE = Path.home() / ".claude"
COMMANDS_REL = Path("commands") / "wh"
AGENTS_REL = Path("agents")
HOOKS_REL = Path("hooks")
VERSION_CACHE_PATH = Path.home() / ".cache" / "wheeler" / "version-check.json"
GITHUB_REPO = "maxwellsdm1867/wheeler"
VERSION_CHECK_MAX_AGE_HOURS = 24


def _hash_file(path: Path) -> str:
    """Return SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_data_path() -> Path:
    """Return path to wheeler/_data/ using importlib.resources."""
    return Path(str(resources.files("wheeler") / "_data"))


def install(link: bool = False) -> dict[str, str]:
    """Copy (or symlink) files from wheeler/_data/ to ~/.claude/.

    Installs commands, agents, and hooks. Registers the SessionStart
    hook in ~/.claude/settings.json so the update checker runs on
    every session.

    Args:
        link: If True, create symlinks instead of copies.

    Returns:
        Dict mapping relative path -> SHA-256 hash.
    """
    data = _get_data_path()
    installed: dict[str, str] = {}

    mappings: list[tuple[Path, Path, Path, str]] = [
        (data / "commands", INSTALL_BASE / COMMANDS_REL, COMMANDS_REL, "*.md"),
        (data / "agents", INSTALL_BASE / AGENTS_REL, AGENTS_REL, "*.md"),
        (data / "hooks", INSTALL_BASE / HOOKS_REL, HOOKS_REL, "wheeler-*.js"),
    ]

    for src_dir, dst_dir, rel_base, pattern in mappings:
        if not src_dir.is_dir():
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src_file in sorted(src_dir.glob(pattern)):
            dst_file = dst_dir / src_file.name
            if dst_file.exists() or dst_file.is_symlink():
                dst_file.unlink()
            if link:
                dst_file.symlink_to(src_file.resolve())
            else:
                shutil.copy2(src_file, dst_file)
            rel_key = str(rel_base / src_file.name)
            installed[rel_key] = _hash_file(src_file)

    # Register hooks in settings.json
    _register_hooks()

    write_manifest(installed)
    return installed


def _register_hooks() -> None:
    """Register Wheeler hooks in ~/.claude/settings.json.

    Adds the SessionStart hook for update checking without
    overwriting existing hooks from other tools (e.g. GSD).
    """
    settings_path = INSTALL_BASE / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    session_start = hooks.setdefault("SessionStart", [])

    hook_path = str(INSTALL_BASE / HOOKS_REL / "wheeler-check-update.js")
    hook_command = f'node "{hook_path}"'

    # Check if already registered
    already_registered = False
    for entry in session_start:
        for h in entry.get("hooks", []):
            if "wheeler-check-update" in h.get("command", ""):
                already_registered = True
                # Update path in case it changed
                h["command"] = hook_command
                break

    if not already_registered:
        session_start.append({
            "hooks": [{"type": "command", "command": hook_command}]
        })

    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def uninstall() -> list[str]:
    """Remove all files listed in manifest, deregister hooks, then remove the manifest."""
    manifest = read_manifest()
    removed: list[str] = []
    if manifest is None:
        return removed

    for rel_path in manifest.get("files", {}):
        full = INSTALL_BASE / rel_path
        if full.exists() or full.is_symlink():
            full.unlink()
            removed.append(rel_path)

    _deregister_hooks()

    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()

    return removed


def _deregister_hooks() -> None:
    """Remove Wheeler hooks from ~/.claude/settings.json."""
    settings_path = INSTALL_BASE / "settings.json"
    if not settings_path.exists():
        return
    try:
        settings = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    hooks = settings.get("hooks", {})
    session_start = hooks.get("SessionStart", [])

    # Remove entries that reference wheeler hooks
    filtered = [
        entry
        for entry in session_start
        if not any(
            "wheeler-check-update" in h.get("command", "")
            for h in entry.get("hooks", [])
        )
    ]

    if len(filtered) != len(session_start):
        hooks["SessionStart"] = filtered
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _detect_install_source() -> str:
    """Detect how wheeler was installed.

    Returns:
        "editable" | "github" | "pypi"
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "wheeler"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("Editable project location:"):
                    return "editable"
                if line.startswith("Location:") and "site-packages" not in line:
                    return "editable"
    except Exception:
        pass
    return "pypi"


def update(source: str | None = None) -> str:
    """Backup local mods, upgrade wheeler, then reinstall files.

    Args:
        source: Force install source ("pypi", "github", or "editable").
                Auto-detected if None.

    Returns:
        The version after upgrade.
    """
    if source is None:
        source = _detect_install_source()

    backup_local_mods()

    if source == "editable":
        # For editable installs, pull latest and reinstall.
        # Always pull — commits may contain new commands/tools even
        # without a version bump.
        repo_root = _find_repo_root()
        subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(repo_root),
            check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(repo_root)],
            check=True,
        )
    elif source == "github":
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                f"git+https://github.com/{GITHUB_REPO}.git",
            ],
            check=True,
        )
    else:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "wheeler"],
            check=True,
        )

    install()

    # Invalidate cache so next check picks up the new version
    if VERSION_CACHE_PATH.exists():
        try:
            VERSION_CACHE_PATH.unlink()
        except OSError:
            pass

    # Reload version
    import importlib

    importlib.reload(wheeler)
    return wheeler.__version__


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


def _check_github_latest() -> Optional[str]:
    """Check GitHub releases API for the latest version tag.

    Returns:
        Version string (without 'v' prefix) or None if check fails.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/vnd.github.v3+json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            tag = data.get("tag_name", "")
            return tag.lstrip("v") if tag else None
    except Exception:
        return None


def _check_pypi_latest() -> Optional[str]:
    """Check PyPI for the latest version via pip index."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "index", "versions", "wheeler"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "wheeler" in line and "(" in line:
                    return line.split("(")[1].split(")")[0].strip()
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def _compare_versions(installed: str, latest: str) -> bool:
    """Return True if latest is strictly newer than installed.

    Uses packaging.version if available, falls back to tuple comparison.
    """
    try:
        from packaging.version import Version

        return Version(latest) > Version(installed)
    except ImportError:
        pass
    # Fallback: tuple comparison of numeric parts
    try:
        inst = tuple(int(x) for x in installed.split("."))
        lat = tuple(int(x) for x in latest.split("."))
        return lat > inst
    except (ValueError, TypeError):
        return latest != installed


def check_version() -> tuple[str, Optional[str], bool]:
    """Compare installed version vs latest available (GitHub then PyPI).

    Returns:
        (installed_version, latest_or_None, update_available)
    """
    installed = wheeler.__version__
    latest = _check_github_latest() or _check_pypi_latest()
    update_available = latest is not None and _compare_versions(installed, latest)
    return installed, latest, update_available


def _read_version_cache() -> dict | None:
    """Read cached version check result."""
    if not VERSION_CACHE_PATH.exists():
        return None
    try:
        return json.loads(VERSION_CACHE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_version_cache(
    installed: str, latest: str | None, update_available: bool
) -> None:
    """Write version check result to cache."""
    VERSION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache = {
        "installed": installed,
        "latest": latest,
        "update_available": update_available,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        VERSION_CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n")
    except OSError:
        pass


def check_version_cached(
    max_age_hours: int = VERSION_CHECK_MAX_AGE_HOURS,
) -> tuple[str, Optional[str], bool]:
    """Check version using cache; re-checks if cache is stale.

    This is safe to call on every CLI invocation — reads a local file
    and only hits the network if the cache is older than max_age_hours.

    Returns:
        (installed_version, latest_or_None, update_available)
    """
    installed = wheeler.__version__
    cache = _read_version_cache()

    if cache is not None:
        try:
            checked = datetime.fromisoformat(cache["checked_at"])
            age_hours = (
                datetime.now(timezone.utc) - checked
            ).total_seconds() / 3600
            if age_hours < max_age_hours and cache.get("installed") == installed:
                return (
                    installed,
                    cache.get("latest"),
                    cache.get("update_available", False),
                )
        except (KeyError, ValueError):
            pass

    # Cache is stale or missing — do a fresh check
    installed, latest, update_available = check_version()
    _write_version_cache(installed, latest, update_available)
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
    existing entries the user may have customized.  The wheeler
    command is resolved to an absolute path so Claude Code can
    find it without the venv being active.

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

    # Resolve wheeler-mcp to absolute path so it works without venv activation
    if "wheeler" in template_servers:
        wheeler_abs = shutil.which("wheeler-mcp")
        if wheeler_abs:
            template_servers["wheeler"]["command"] = wheeler_abs

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
