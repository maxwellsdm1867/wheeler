"""Wheeler installer: install/uninstall/update slash commands and agents.

This is the LEGACY distribution path: it copies `wh/*.md` act files into
`~/.claude/commands/wh/`. The supported path is the `wh` Claude Code plugin,
which serves the same acts as `/wh:<name>` skills. The two collide: a
file-based `~/.claude/commands/wh/plan.md` silently wins over the plugin's
`plan` skill, so a user with both keeps running stale copies with no error.
`detect_plugin()` + `install(force=...)` make that collision loud, and
`wheeler migrate-to-plugin` resolves it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
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

# Plugin distribution. Claude Code namespaces plugin skills as
# `/<plugin>:<skill>`, so plugin "wh" from marketplace "wheeler" serves
# `/wh:plan` etc. That is the same command namespace the legacy tree owns.
PLUGIN_NAME = "wh"
PLUGIN_MARKETPLACE = "wheeler"
PLUGIN_SPEC = f"{PLUGIN_NAME}@{PLUGIN_MARKETPLACE}"
MARKETPLACE_ADD_CMD = f"/plugin marketplace add {GITHUB_REPO}"
PLUGIN_INSTALL_CMD = f"/plugin install {PLUGIN_SPEC}"
# Claude Code's plugin bookkeeping, relative to INSTALL_BASE.
INSTALLED_PLUGINS_REL = Path("plugins") / "installed_plugins.json"
KNOWN_MARKETPLACES_REL = Path("plugins") / "known_marketplaces.json"


def _hash_file(path: Path) -> str:
    """Return SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_data_path() -> Path:
    """Return path to wheeler/_data/ using importlib.resources."""
    return Path(str(resources.files("wheeler") / "_data"))


# ---------------------------------------------------------------------------
# Plugin / legacy collision detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginStatus:
    """What we can tell about a Claude Code plugin owning the /wh: namespace.

    `enabled` and `disabled` come from the `enabledPlugins` key in the
    settings scopes; `installed` from `plugins/installed_plugins.json`,
    which records both user- and project-scope installs. Scope precedence
    is not modelled: any scope enabling the plugin counts as enabled.
    """

    name: str = PLUGIN_NAME
    enabled: bool = False
    disabled: bool = False
    installed: bool = False
    keys: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    marketplaces: tuple[str, ...] = ()

    @property
    def present(self) -> bool:
        """True when Claude Code knows about the plugin at all."""
        return self.enabled or self.disabled or self.installed

    @property
    def active(self) -> bool:
        """True when the plugin can actually serve /wh: commands."""
        return self.enabled or (self.installed and not self.disabled)

    def describe(self) -> str:
        """One-line human summary."""
        if not self.present:
            return f"plugin '{self.name}' not installed"
        state = "enabled" if self.enabled else ("disabled" if self.disabled else "installed")
        where = ", ".join(self.scopes) or "unknown scope"
        key = self.keys[0] if self.keys else self.name
        return f"plugin '{key}' {state} ({where})"


@dataclass(frozen=True)
class LegacyStatus:
    """State of the legacy file-based install under `~/.claude/`."""

    present: bool = False
    version: Optional[str] = None
    installed_at: Optional[str] = None
    files: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    untracked_commands: tuple[str, ...] = ()

    @property
    def has_manifest(self) -> bool:
        return self.version is not None or bool(self.files)

    def describe(self) -> str:
        """One-line human summary."""
        if not self.present:
            return "no legacy install"
        n_acts = len(self.commands) + len(self.untracked_commands)
        ver = self.version or "unknown version"
        return f"{n_acts} act file(s) in {INSTALL_BASE / COMMANDS_REL} ({ver})"


class PluginShadowError(RuntimeError):
    """A legacy `~/.claude/commands/wh/` install would shadow the wh plugin."""

    def __init__(self, message: str, plugin: PluginStatus) -> None:
        super().__init__(message)
        self.plugin = plugin


def _read_json_file(path: Path) -> dict:
    """Read a JSON object from *path*, returning {} on any problem."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _settings_scopes(project_dir: Path | None = None) -> list[tuple[str, Path]]:
    """Return (label, path) for each settings scope to inspect.

    User scopes live under INSTALL_BASE. Project scopes are only included
    when *project_dir* is given, so the default is confined to the install
    base and stays hermetic under test.
    """
    scopes = [
        ("user", INSTALL_BASE / "settings.json"),
        ("user-local", INSTALL_BASE / "settings.local.json"),
    ]
    if project_dir is not None:
        claude = Path(project_dir) / ".claude"
        scopes += [
            ("project", claude / "settings.json"),
            ("project-local", claude / "settings.local.json"),
        ]
    return scopes


def _plugin_key_name(key: str) -> str:
    """Return the plugin name from a `plugin@marketplace` settings key."""
    return key.split("@", 1)[0].strip()


def detect_plugin(
    plugin_name: str = PLUGIN_NAME, project_dir: Path | None = None
) -> PluginStatus:
    """Detect whether a Claude Code plugin named *plugin_name* is present.

    Reads `enabledPlugins` and `extraKnownMarketplaces` across the settings
    scopes, plus Claude Code's own `plugins/installed_plugins.json`. Any
    plugin with this name owns the `/<plugin_name>:` command namespace no
    matter which marketplace it came from, so matching is on the name part
    of the `plugin@marketplace` key.
    """
    keys: list[str] = []
    scopes: list[str] = []
    marketplaces: list[str] = []
    enabled = False
    disabled = False

    for scope, path in _settings_scopes(project_dir):
        settings = _read_json_file(path)
        entries = settings.get("enabledPlugins")
        if isinstance(entries, dict):
            for key, value in entries.items():
                if _plugin_key_name(key) != plugin_name:
                    continue
                keys.append(key)
                scopes.append(f"enabledPlugins:{scope}")
                if value:
                    enabled = True
                else:
                    disabled = True
        known = settings.get("extraKnownMarketplaces")
        if isinstance(known, dict):
            marketplaces.extend(str(name) for name in known)

    records = _read_json_file(INSTALL_BASE / INSTALLED_PLUGINS_REL).get("plugins")
    installed = False
    if isinstance(records, dict):
        for key, entries_list in records.items():
            if _plugin_key_name(key) != plugin_name:
                continue
            installed = True
            keys.append(key)
            entry_scopes = [
                str(e.get("scope"))
                for e in (entries_list if isinstance(entries_list, list) else [])
                if isinstance(e, dict) and e.get("scope")
            ]
            scopes.extend(f"installed:{s}" for s in entry_scopes or ["unknown"])

    marketplaces.extend(_read_json_file(INSTALL_BASE / KNOWN_MARKETPLACES_REL))

    return PluginStatus(
        name=plugin_name,
        enabled=enabled,
        # An explicit `false` only counts as disabled when nothing enables it.
        disabled=disabled and not enabled,
        installed=installed,
        keys=tuple(dict.fromkeys(keys)),
        scopes=tuple(dict.fromkeys(scopes)),
        marketplaces=tuple(dict.fromkeys(marketplaces)),
    )


def legacy_status() -> LegacyStatus:
    """Describe the legacy install, preferring the manifest over globs.

    The manifest is authoritative for what `wheeler install` wrote. Act
    files present in `~/.claude/commands/wh/` but absent from the manifest
    are reported separately: they shadow the plugin just as effectively.
    """
    manifest = read_manifest() or {}
    files = tuple(manifest.get("files", {}))
    tracked_commands: list[str] = []
    missing: list[str] = []
    for rel in files:
        full = INSTALL_BASE / rel
        if not (full.exists() or full.is_symlink()):
            missing.append(rel)
        if rel.startswith(f"{COMMANDS_REL}/") and rel.endswith(".md"):
            tracked_commands.append(Path(rel).stem)

    cmd_dir = INSTALL_BASE / COMMANDS_REL
    on_disk = (
        {p.stem for p in cmd_dir.glob("*.md")} if cmd_dir.is_dir() else set()
    )
    untracked = sorted(on_disk - set(tracked_commands))

    return LegacyStatus(
        present=bool(files) or bool(on_disk),
        version=manifest.get("version"),
        installed_at=manifest.get("installed_at"),
        files=files,
        commands=tuple(sorted(tracked_commands)),
        missing=tuple(missing),
        untracked_commands=tuple(untracked),
    )


def _shipped_act_count() -> int:
    """Count act files this Wheeler would install (0 if unreadable)."""
    try:
        return len(list((_get_data_path() / "commands").glob("*.md")))
    except Exception:
        return 0


def _example_acts(legacy: LegacyStatus, limit: int = 3) -> tuple[str, ...]:
    """Pick recognizable colliding act names for the error message."""
    present = list(legacy.commands) + list(legacy.untracked_commands)
    preferred = [n for n in ("plan", "execute", "discuss", "ask") if n in present]
    rest = [n for n in sorted(present) if n not in preferred]
    return tuple((preferred + rest or ["plan", "execute", "discuss"])[:limit])


def shadowing_message(plugin: PluginStatus, legacy: LegacyStatus) -> str:
    """Explain the legacy-shadows-plugin collision and name the exact fix."""
    n_acts = len(legacy.commands) + len(legacy.untracked_commands) or _shipped_act_count()
    examples = ", ".join(f"/{PLUGIN_NAME}:{name}" for name in _example_acts(legacy))
    return (
        f"The Claude Code {plugin.describe()}.\n"
        f"A legacy install into {INSTALL_BASE / COMMANDS_REL} SHADOWS it: Claude Code\n"
        f"resolves /{PLUGIN_NAME}:<name> to the file-based command, so all {n_acts} act names\n"
        f"({examples}, ...) keep running stale local copies and the plugin's\n"
        "versions never load. There is no error when this happens.\n"
        "\n"
        "Fix, pick one:\n"
        "  wheeler migrate-to-plugin    remove the legacy tree, keep the plugin (recommended)\n"
        "  wheeler install --force      keep the legacy tree and accept the shadowing"
    )


def plugin_advice(plugin: PluginStatus, legacy: LegacyStatus) -> Optional[str]:
    """Return advice about the plugin/legacy split, or None when consistent.

    Symmetric to `shadowing_message`: covers the case where the legacy tree
    is gone (or was never installed) and the plugin is the thing to rely on.
    """
    if plugin.active and legacy.present:
        return shadowing_message(plugin, legacy)
    if plugin.active and not legacy.present:
        return None
    if legacy.present:
        return (
            "Legacy file-based install in use "
            f"({legacy.describe()}). The supported path is the {PLUGIN_NAME} plugin:\n"
            "  wheeler migrate-to-plugin"
        )
    return (
        f"No Wheeler acts installed. Install the {PLUGIN_NAME} plugin in Claude Code:\n"
        f"  {MARKETPLACE_ADD_CMD}\n"
        f"  {PLUGIN_INSTALL_CMD}"
    )


def install(link: bool = False, force: bool = False) -> dict[str, str]:
    """Copy (or symlink) files from wheeler/_data/ to ~/.claude/.

    Installs commands, agents, and hooks. Registers the SessionStart
    hook in ~/.claude/settings.json so the update checker runs on
    every session, and the statusLine command so the update badge
    is rendered when an update is available.

    LEGACY path. Refuses when a Claude Code plugin named `wh` is active,
    because the files written here silently shadow the plugin's acts.

    Args:
        link: If True, create symlinks instead of copies.
        force: Install even when the wh plugin is active (accepting the
            shadowing). `update()` uses this so an upgrade never leaves a
            half-refreshed legacy tree behind.

    Returns:
        Dict mapping relative path -> SHA-256 hash.

    Raises:
        PluginShadowError: The wh plugin is active and force is False.
    """
    plugin = detect_plugin()
    if plugin.active and not force:
        raise PluginShadowError(shadowing_message(plugin, legacy_status()), plugin)

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

    # Register hooks and MCP servers in settings.json
    _register_hooks()
    _register_mcp_servers()

    write_manifest(installed)
    return installed


def _register_hooks() -> None:
    """Register Wheeler hooks in ~/.claude/settings.json.

    Adds the SessionStart hook for update checking without
    overwriting existing hooks from other tools (e.g. GSD), and
    registers the top-level statusLine command that renders the
    update badge. A pre-existing non-Wheeler statusLine is left
    untouched.
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

    # statusLine is a top-level settings key in Claude Code (not part of
    # the hooks object). It renders the update badge from the version
    # cache. Three cases:
    #   - no statusLine: register Wheeler's full statusline.
    #   - Wheeler-owned (full or wrapper): refresh the script path,
    #     preserving any existing wrap target.
    #   - custom statusLine from another tool: WRAP it. The wrapper runs
    #     the original command with the same stdin and prepends the
    #     update badge only when an update is pending, so the user's
    #     statusline renders unchanged otherwise. The original command
    #     is carried base64-encoded in the wrapper invocation and is
    #     restored verbatim on uninstall.
    statusline_path = str(INSTALL_BASE / HOOKS_REL / "wheeler-statusline.js")
    statusline_command = f'node "{statusline_path}"'
    existing_statusline = settings.get("statusLine")
    if existing_statusline is None:
        settings["statusLine"] = {"type": "command", "command": statusline_command}
    elif (
        isinstance(existing_statusline, dict)
        and "wheeler-statusline" in existing_statusline.get("command", "")
    ):
        wrap = re.search(
            r"--wrap-b64 (\S+)", existing_statusline.get("command", "")
        )
        if wrap:
            existing_statusline["command"] = (
                f"{statusline_command} --wrap-b64 {wrap.group(1)}"
            )
        else:
            existing_statusline["command"] = statusline_command
    elif isinstance(existing_statusline, dict) and existing_statusline.get(
        "command"
    ):
        original = existing_statusline["command"]
        encoded = base64.b64encode(original.encode()).decode()
        settings["statusLine"] = {
            "type": "command",
            "command": f"{statusline_command} --wrap-b64 {encoded}",
        }

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
    _deregister_mcp_servers()

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

    changed = False
    if len(filtered) != len(session_start):
        hooks["SessionStart"] = filtered
        changed = True

    # Remove the statusLine only if it is Wheeler-owned. If it is the
    # Wheeler wrapper around a user's original command, restore the
    # original verbatim instead of deleting.
    statusline = settings.get("statusLine")
    if (
        isinstance(statusline, dict)
        and "wheeler-statusline" in statusline.get("command", "")
    ):
        wrap = re.search(r"--wrap-b64 (\S+)", statusline.get("command", ""))
        restored = None
        if wrap:
            try:
                restored = base64.b64decode(wrap.group(1)).decode()
            except Exception:
                restored = None
        if restored:
            settings["statusLine"] = {"type": "command", "command": restored}
        else:
            del settings["statusLine"]
        changed = True

    if changed:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _register_mcp_servers() -> None:
    """Register Wheeler MCP servers in ~/.claude/settings.json.

    Adds wheeler and neo4j entries to the global mcpServers config
    so they're available in every Claude Code session regardless of
    working directory.  Existing entries are not overwritten.
    """
    settings_path = INSTALL_BASE / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            settings = {}
    else:
        settings = {}

    servers = settings.setdefault("mcpServers", {})

    # Read template for neo4j config
    data = _get_data_path()
    template_path = data / "mcp.json"
    if template_path.exists():
        template = json.loads(template_path.read_text())
        template_servers = template.get("mcpServers", {})
    else:
        template_servers = {}

    # One-time migration: remove legacy monolith "wheeler" key
    if "wheeler" in servers:
        cmd = servers["wheeler"].get("command", "")
        basename = Path(cmd).name if cmd else ""
        if basename == "wheeler-mcp":
            del servers["wheeler"]
            logger.info("Removed legacy 'wheeler' monolith MCP entry")

    # Register split servers from template (don't overwrite user-set entries)
    for key, entry in template_servers.items():
        if key == "neo4j":
            continue  # handled separately below
        if key in servers:
            continue  # respect existing user config
        cmd_name = entry.get("command", "")
        resolved = shutil.which(cmd_name)
        if resolved:
            servers[key] = {**entry, "command": resolved}

    # Neo4j — add from template if not already configured
    if "neo4j" not in servers and "neo4j" in template_servers:
        servers["neo4j"] = template_servers["neo4j"]

    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _deregister_mcp_servers() -> None:
    """Remove Wheeler MCP servers from ~/.claude/settings.json."""
    settings_path = INSTALL_BASE / "settings.json"
    if not settings_path.exists():
        return
    try:
        settings = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    servers = settings.get("mcpServers", {})
    changed = False
    for name in ("wheeler", "wheeler_core", "wheeler_query", "wheeler_mutations", "wheeler_ops", "neo4j"):
        if name in servers:
            del servers[name]
            changed = True

    if changed:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


@dataclass(frozen=True)
class MigrationResult:
    """Outcome of `migrate_to_plugin()`."""

    legacy: LegacyStatus
    plugin: PluginStatus
    removed: tuple[str, ...] = ()
    removed_untracked: tuple[str, ...] = ()
    migrated: bool = False

    @property
    def next_steps(self) -> tuple[str, ...]:
        """Commands the user runs in Claude Code to get the plugin."""
        if self.plugin.active:
            return ()
        return (MARKETPLACE_ADD_CMD, PLUGIN_INSTALL_CMD)


def migrate_to_plugin(remove_untracked: bool = True) -> MigrationResult:
    """Remove the legacy install so the wh plugin stops being shadowed.

    Idempotent and safe to run with nothing installed: when there is no
    legacy tree it removes nothing and reports what to do next. Does not
    require the plugin to be installed first.

    Args:
        remove_untracked: Also delete act files in `~/.claude/commands/wh/`
            that the manifest does not list (a pre-manifest install). They
            shadow the plugin exactly as effectively as tracked ones.
    """
    legacy = legacy_status()
    plugin = detect_plugin()
    if not legacy.present:
        return MigrationResult(legacy=legacy, plugin=plugin)

    # The manifest is the record of what `wheeler install` wrote; uninstall()
    # owns hook/statusLine/MCP deregistration as well as the files.
    removed = tuple(uninstall())

    removed_untracked: list[str] = []
    cmd_dir = INSTALL_BASE / COMMANDS_REL
    if remove_untracked and cmd_dir.is_dir():
        for leftover in sorted(cmd_dir.glob("*.md")):
            leftover.unlink()
            removed_untracked.append(str(COMMANDS_REL / leftover.name))
    if cmd_dir.is_dir() and not any(cmd_dir.iterdir()):
        cmd_dir.rmdir()

    return MigrationResult(
        legacy=legacy,
        plugin=plugin,
        removed=removed,
        removed_untracked=tuple(removed_untracked),
        migrated=True,
    )


def _is_uv_tool_install() -> bool:
    """Best-effort check for a working uv when pip is unavailable.

    A venv without pip is almost always uv-managed; confirm uv is on
    PATH and responds before routing the upgrade through it.
    """
    if shutil.which("uv") is None:
        return False
    probe = subprocess.run(
        ["uv", "tool", "list"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return probe.returncode == 0


def _detect_install_source() -> str:
    """Detect how wheeler was installed.

    Returns:
        "editable" | "uv" | "github" | "pypi"
    """
    exe_parts = Path(sys.executable).parts
    for i in range(len(exe_parts) - 1):
        if exe_parts[i] == "uv" and exe_parts[i + 1] == "tools":
            return "uv"
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
        elif _is_uv_tool_install():
            return "uv"
    except Exception:
        pass
    return "github"


def update(source: str | None = None) -> str:
    """Backup local mods, upgrade wheeler, then reinstall files.

    Args:
        source: Force install source ("pypi", "github", "editable", or "uv").
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
    elif source == "uv":
        # uv tool venvs ship without pip; uv reinstalls from the
        # original spec (git or PyPI) on upgrade.
        subprocess.run(
            ["uv", "tool", "upgrade", "wheeler"],
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

    # Reinstall files by re-executing the FRESHLY UPGRADED wheeler
    # entrypoint, not by calling install() in-process: the running
    # interpreter still holds the pre-upgrade code, so an in-process
    # install would stamp the manifest with the old version and skip any
    # registration logic that is new in the version just installed.
    #
    # --force: an update refreshes a tree that already exists. Refusing here
    # over plugin shadowing would leave the upgrade half-applied, which is
    # worse than a consistent (if shadowing) legacy tree. The caller warns
    # instead; `wheeler migrate-to-plugin` is the resolution.
    new_wheeler = Path(sys.executable).parent / "wheeler"
    try:
        if new_wheeler.exists():
            subprocess.run([str(new_wheeler), "install", "--force"], check=True)
        else:
            install(force=True)
    except subprocess.CalledProcessError:
        # A re-exec hiccup must never leave the upgrade without files.
        install(force=True)

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
            url,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "wheeler-update-checker",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            tag = data.get("tag_name", "")
            return tag.lstrip("v") if tag else None
    except Exception:
        return None


def _check_pypi_latest() -> Optional[str]:
    """Check PyPI's JSON API for the latest version.

    Uses urllib rather than shelling out to pip so the check works in
    pip-less environments such as uv tool venvs.
    """
    url = "https://pypi.org/pypi/wheeler/json"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "wheeler-update-checker",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            version = data.get("info", {}).get("version")
            return version or None
    except Exception:
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
    """Write version check result to cache.

    Writes both timestamp keys: "checked_at" (ISO string, the Python
    convention) and "checked" (epoch seconds, the JS hook convention)
    so either reader accepts a cache written by the other.
    """
    VERSION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    cache = {
        "installed": installed,
        "latest": latest,
        "update_available": update_available,
        "checked_at": now.isoformat(),
        "checked": int(now.timestamp()),
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
            # Accept either timestamp convention: "checked_at" (ISO,
            # Python-written) or "checked" (epoch seconds, written by the
            # wheeler-check-update.js SessionStart hook).
            if "checked_at" in cache:
                checked = datetime.fromisoformat(cache["checked_at"])
            else:
                checked = datetime.fromtimestamp(
                    int(cache["checked"]), tz=timezone.utc
                )
            age_hours = (
                datetime.now(timezone.utc) - checked
            ).total_seconds() / 3600
            if age_hours < max_age_hours and cache.get("installed") == installed:
                return (
                    installed,
                    cache.get("latest"),
                    cache.get("update_available", False),
                )
        except (KeyError, ValueError, TypeError):
            pass

    # Cache is stale or missing — do a fresh check
    installed, latest, update_available = check_version()
    if latest is None and cache is not None and cache.get("installed") == installed:
        # Offline or check failed: keep the previously cached flag instead of
        # clobbering a known update_available=true with false. Only valid if
        # the cached entry refers to the same installed version (an upgrade
        # must still clear the badge).
        latest = cache.get("latest")
        update_available = bool(cache.get("update_available", False))
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


