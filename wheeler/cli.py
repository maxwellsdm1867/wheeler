"""Wheeler top-level CLI entry point (`wheeler` console script).

Extends the legacy `wheeler.tools.cli:app` Typer instance with the commands
designed for the `uvx wheeler` / `uv tool install wheeler` install path:

- `wheeler init <project>`       scaffold a new Wheeler project
- `wheeler serve [server]`       start an MCP server (debug / standalone)
- `wheeler doctor`               sanity check
- `wheeler migrate-to-plugin`    drop the legacy ~/.claude/ install for the plugin

Plus a `--version` flag on the root.

The legacy `wheeler-tools` console script keeps pointing at
`wheeler.tools.cli:app` and only sees the legacy command surface, since
that module never imports this one.
"""

from __future__ import annotations

import importlib
import json
import shutil
import sys
from importlib import resources
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

import wheeler
from wheeler.config import ProjectMeta
from wheeler.scaffold import scaffold_project, write_config
from wheeler.tools.cli import app

# Override the legacy Typer help string ("Wheeler deterministic tools...") with
# something appropriate for the top-level `wheeler` command.
app.info.name = "wheeler"
app.info.help = "Wheeler: a Claude Code-native research assistant with provenance tracking."

console = Console()


# ---------------------------------------------------------------------------
# --version flag (eager callback, exits before subcommand dispatch)
# ---------------------------------------------------------------------------


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"wheeler {wheeler.__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Wheeler: a Claude Code-native research assistant with provenance tracking."""


# ---------------------------------------------------------------------------
# wheeler init
# ---------------------------------------------------------------------------


def _write_project_mcp_json(project_dir: Path) -> tuple[Path, list[str]]:
    """Write `.mcp.json` to *project_dir*, resolving installed script paths.

    Returns ``(path, warnings)``. Warnings list is empty when every Wheeler
    console script resolves to a real binary on PATH.
    """
    template_data = (resources.files("wheeler") / "_data" / "mcp.json").read_text()
    template = json.loads(template_data)
    warnings: list[str] = []

    for key, entry in template.get("mcpServers", {}).items():
        if key == "neo4j":
            continue
        cmd_name = entry.get("command", "")
        resolved = shutil.which(cmd_name)
        if resolved:
            entry["command"] = resolved
        else:
            warnings.append(cmd_name)

    dest = project_dir / ".mcp.json"
    dest.write_text(json.dumps(template, indent=2) + "\n")
    return dest, warnings


CLOUD_CHOICE = "cloud"
LOCAL_CHOICE = "local"

# Where Aura's credentials download lands, and what it is called. Matching the
# real filename means a new user usually never types a path: they click download
# and Wheeler finds it. Glob rather than exact name because the instance id and
# creation date are baked into it (`Neo4j-2de7b9a2-Created-2026-08-09.txt`).
_AURA_FILE_GLOB = "Neo4j-*.txt"
_AURA_FILE_DIRS = ("Downloads", "Desktop", "")


def discover_aura_files(home: Path | None = None) -> list[Path]:
    """Aura credentials files already on this machine, newest first."""
    base = home or Path.home()
    found: list[Path] = []
    for folder in _AURA_FILE_DIRS:
        directory = base / folder if folder else base
        try:
            found.extend(p for p in directory.glob(_AURA_FILE_GLOB) if p.is_file())
        except OSError:
            continue
    return sorted(set(found), key=lambda p: p.stat().st_mtime, reverse=True)


def diagnose_aura_failure(exc: Exception) -> str:
    """Turn a connection failure into the thing the user should actually do.

    Aura's three common failures are indistinguishable from the driver error
    alone, and each has a completely different fix. Guessing wrong costs a user
    the whole evening, which is why this maps them explicitly.
    """
    text = f"{type(exc).__name__}: {exc}".lower()

    if "resolve" in text or "nodename" in text or "name or service not known" in text:
        return (
            "That hostname does not exist any more, so the instance was DELETED.\n"
            "  AuraDB Free pauses after 72 hours idle and is deleted after 90 days\n"
            "  paused. Create a new instance at https://console.neo4j.io and\n"
            "  download its credentials file."
        )
    if "unauthorized" in text or "authenticationrate" in text or "autherror" in text:
        return (
            "The instance is reachable but rejected those credentials.\n"
            "  Aura shows the password ONCE, at creation, so an edited or partial\n"
            "  file is the usual cause. Re-download it, or reset the password in\n"
            "  the console under the instance's ... menu."
        )
    if "unavailable" in text or "timed out" in text or "timeout" in text:
        return (
            "The instance did not answer. Two likely reasons:\n"
            "  - it is PAUSED (Free pauses after 72 hours idle): resume it at\n"
            "    https://console.neo4j.io and try again.\n"
            "  - it was just created: Aura needs up to 60 seconds before it\n"
            "    accepts connections."
        )
    return (
        "Could not connect. Check the instance is running at "
        "https://console.neo4j.io,\n  then re-run: wheeler login --aura-file "
        "<file> --profile <name>"
    )


def _print_aura_signup_help() -> None:
    """The shortest true path from nothing to a credentials file."""
    console.print(
        "\n[bold]Setting up a cloud graph[/bold]\n"
        "  1. Open [cyan]https://console.neo4j.io[/cyan] and sign up (free, no card).\n"
        "  2. Create an instance. [bold]AuraDB Free[/bold] is enough for one project.\n"
        "  3. When it is created Aura shows the password [bold]once[/bold] and offers a\n"
        "     credentials file. Download it. It is the only copy.\n"
        "  4. Come back here with that file.\n"
        "[dim]  Free instances pause after 72 hours idle (resume in one click) and\n"
        "  are deleted after 90 days paused. A new instance needs ~60s before it\n"
        "  accepts connections.[/dim]\n"
    )


def _choose_graph(
    graph: Optional[str], profile: Optional[str], aura_file: Optional[Path], yes: bool
):  # noqa: ANN202 (returns Neo4jConfig)
    """Decide which graph a new project connects to, and record it.

    Both routes end the same way: the credential goes to the OS keychain and
    `wheeler.yaml` stores only a PROFILE NAME plus a DATABASE. Nothing secret in
    a checked-in file, and the binding is per project, so one project changing
    where it points cannot move any other.

    - local: a Neo4j on this computer. DEFAULT when instances are present.
      Desktop's UI runs only one at a time, but the `bin/neo4j` script inside
      each instance has no such limit, so several run side by side once their
      ports differ. That is what lets one window per project each hold its own
      graph, with no network and nothing to keep alive.
    - cloud: a hosted Neo4j (Aura). Reachable from any machine, but one database
      per instance and a free instance pauses after 72h idle.

    The profile is stored PER PROJECT rather than in the shared `default` slot,
    because the keychain outranks `wheeler.yaml`: a credential in `default` would
    silently redirect every other Wheeler project on the machine.
    """
    from wheeler import desktop
    from wheeler.config import Neo4jConfig

    local_instances = desktop.instances()

    if graph is None:
        if yes:
            graph = LOCAL_CHOICE if local_instances else CLOUD_CHOICE
        else:
            found = (
                f"  local  a Neo4j on this computer. Found "
                f"{len(local_instances)} instance(s); several can run at once  "
                "[recommended]\n"
                if local_instances
                else "  local  a Neo4j on this computer (none found yet)\n"
            )
            graph = typer.prompt(
                "Which graph should this project use?\n"
                + found
                + "  cloud  a hosted Neo4j (Aura). Reachable from any machine\n"
                "Choice",
                default=LOCAL_CHOICE if local_instances else CLOUD_CHOICE,
            )
    graph = str(graph).strip().lower()
    if graph not in (CLOUD_CHOICE, LOCAL_CHOICE):
        raise typer.BadParameter(
            f"--graph must be {CLOUD_CHOICE!r} or {LOCAL_CHOICE!r}, got {graph!r}"
        )

    if graph == LOCAL_CHOICE:
        return _setup_local(local_instances, profile, yes)

    from wheeler import credentials

    slot = (profile or "").strip() or "wheeler-cloud"

    # 1. An explicit file always wins.
    if aura_file is not None:
        if _store_aura_file(aura_file, slot):
            return Neo4jConfig(profile=slot)
        return Neo4jConfig(profile=slot)

    # 2. Already stored? Nothing to do.
    if credentials.load(slot):
        console.print(f"[green]Using the credential already stored as '{slot}'.[/green]")
        return Neo4jConfig(profile=slot)

    # 3. Non-interactive: bind and tell them the one command left.
    if yes:
        console.print(
            f"[yellow]No credential stored under profile '{slot}' yet.[/yellow]\n"
            f"[dim]Finish with: wheeler login --aura-file <file> --profile {slot}[/dim]"
        )
        return Neo4jConfig(profile=slot)

    # 4. Interactive: offer a file we can already see, else walk them through it.
    candidates = discover_aura_files()
    if candidates:
        console.print("\n[bold]Found an Aura credentials file:[/bold]")
        for index, path in enumerate(candidates[:5], start=1):
            console.print(f"  {index}. {escape(str(path))}")
        console.print("  0. none of these, I need to create an instance")
        pick = typer.prompt("Use which", default="1").strip()
        if pick not in ("0", ""):
            try:
                chosen = candidates[int(pick) - 1]
            except (ValueError, IndexError):
                chosen = None
            if chosen is not None and _store_aura_file(chosen, slot):
                return Neo4jConfig(profile=slot)
            return Neo4jConfig(profile=slot)

    _print_aura_signup_help()
    typed = typer.prompt(
        "Path to the credentials file (blank to finish this later)", default=""
    ).strip()
    if typed:
        _store_aura_file(Path(typed).expanduser(), slot)
    else:
        console.print(
            f"[dim]This project is bound to profile '{slot}'. Finish with:\n"
            f"  wheeler login --aura-file <file> --profile {slot}[/dim]"
        )
    return Neo4jConfig(profile=slot)


def _store_aura_file(path: Path, slot: str) -> bool:
    """Parse, CONNECT, then store. Returns whether it worked.

    Connecting before storing is the point: a credential that does not work is
    worse than none, because the user then trusts the keychain and goes looking
    at Neo4j. On failure the hint names the actual fix rather than echoing a
    driver error.
    """
    from wheeler import aura, credentials

    try:
        creds = aura.parse_credentials_file(path)
    except Exception as exc:
        console.print(f"[red]Could not read {escape(str(path))}:[/red] {escape(str(exc))}")
        console.print(
            "[dim]Expected Aura's downloaded file, containing NEO4J_URI, "
            "NEO4J_USERNAME and NEO4J_PASSWORD.[/dim]"
        )
        return False

    console.print(f"[dim]Connecting to {escape(creds.uri)} ...[/dim]")
    try:
        aura.validate_connection(creds.uri, creds.username, creds.password, creds.database)
    except Exception as exc:
        console.print(f"[red]That credential did not work.[/red]\n  {diagnose_aura_failure(exc)}")
        return False

    try:
        credentials.save(slot, creds.uri, creds.username, creds.password, creds.database)
    except Exception as exc:
        console.print(f"[red]Connected, but could not store it:[/red] {escape(str(exc))}")
        return False

    console.print(
        f"[green]Connected and stored[/green] {escape(creds.uri)} as profile '{slot}'."
    )
    return True


@app.command("init")
def cmd_init(
    project_dir: Path = typer.Argument(
        ...,
        help="Path to the new project directory. Created if missing.",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        help="Project name written to wheeler.yaml. Default: directory name.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation when target directory is not empty.",
    ),
    skip_install: bool = typer.Option(
        False,
        "--skip-install",
        help="Skip installing slash commands/agents to ~/.claude/.",
    ),
    skip_mcp: bool = typer.Option(
        False,
        "--skip-mcp",
        help="Skip writing project-local .mcp.json.",
    ),
    graph: Optional[str] = typer.Option(
        None,
        "--graph",
        help="Which graph this project uses: 'cloud' (recommended) or 'local'. "
             "Prompts when omitted.",
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        help="Keychain profile holding the cloud credential (default: wheeler-cloud).",
    ),
    aura_file: Optional[Path] = typer.Option(
        None,
        "--aura-file",
        help="Aura credentials file to verify and store for this project.",
    ),
) -> None:
    """Scaffold a new Wheeler project.

    Creates the project directory, scaffolds .plans/ .logs/ .wheeler/, writes
    wheeler.yaml, drops a project-local .mcp.json that points at the installed
    wheeler-*-mcp servers, and installs slash commands + agents to ~/.claude/.

    Idempotent: re-running on an existing project leaves user edits intact.
    """
    project_dir = project_dir.expanduser().resolve()

    if project_dir.exists() and project_dir.is_dir() and any(project_dir.iterdir()):
        if not yes and not typer.confirm(
            f"Directory {project_dir} is not empty. Continue?",
            default=True,
        ):
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    project_dir.mkdir(parents=True, exist_ok=True)

    created = scaffold_project(project_dir)
    if created["created"]:
        console.print(f"[green]Scaffolded:[/green] {', '.join(created['created'])}")
    else:
        console.print("[dim]Managed dirs already present.[/dim]")

    config_path = project_dir / "wheeler.yaml"
    if config_path.exists():
        console.print(f"[dim]wheeler.yaml already exists at {config_path} (left untouched).[/dim]")
    else:
        project_name = name or project_dir.name
        neo4j_cfg = _choose_graph(graph, profile, aura_file, yes)
        write_config(
            project_dir, project=ProjectMeta(name=project_name), neo4j=neo4j_cfg
        )
        console.print(f"[green]Wrote[/green] {config_path}")

    if not skip_mcp:
        mcp_path = project_dir / ".mcp.json"
        if mcp_path.exists():
            console.print(f"[dim].mcp.json already exists at {mcp_path} (left untouched).[/dim]")
        else:
            dest, missing = _write_project_mcp_json(project_dir)
            console.print(f"[green]Wrote[/green] {dest}")
            if missing:
                console.print(
                    "[yellow]Note:[/yellow] these scripts are not on PATH yet: "
                    + ", ".join(missing)
                )
                console.print(
                    "[dim]Bare command names were written; run "
                    "`uv tool install wheeler` for a persistent install.[/dim]"
                )

    if not skip_install:
        from wheeler.installer import PluginShadowError
        from wheeler.installer import install as _install

        try:
            files = _install()
            console.print(
                f"[green]Installed {len(files)} file(s) to ~/.claude/ "
                "(slash commands + agents + hooks).[/green]"
            )
        except PluginShadowError:
            # The plugin already serves every /wh: act. Writing the legacy
            # tree here would shadow it, so skip it and say why.
            console.print(
                "[dim]Slash command install skipped: the wh plugin is already "
                "installed and serves every /wh: act.[/dim]"
            )
        except Exception as exc:
            console.print(f"[yellow]Slash command install skipped:[/yellow] {exc}")

    console.print()
    console.print(f"[bold green]Wheeler project ready at {project_dir}[/bold green]")
    console.print("Next:")
    console.print(f"  cd {project_dir}")
    console.print("  claude")
    console.print("  /wh:start")


# ---------------------------------------------------------------------------
# wheeler serve
# ---------------------------------------------------------------------------


_SERVER_MODULES = {
    "core": "wheeler.mcp_core",
    "query": "wheeler.mcp_query",
    "mutations": "wheeler.mcp_mutations",
    "ops": "wheeler.mcp_ops",
}


@app.command("serve")
def cmd_serve(
    server: str = typer.Argument(
        "core",
        help=f"Which MCP server to run. One of: {', '.join(_SERVER_MODULES)}.",
    ),
) -> None:
    """Start a Wheeler MCP server on stdio.

    Claude Code normally launches these directly via .mcp.json or
    ~/.claude/settings.json. This command is for debugging / running
    standalone.
    """
    if server not in _SERVER_MODULES:
        console.print(
            f"[red]Unknown server '{server}'.[/red] "
            f"Pick one of: {', '.join(_SERVER_MODULES)}"
        )
        raise typer.Exit(1)

    module = importlib.import_module(_SERVER_MODULES[server])
    module.main()


# ---------------------------------------------------------------------------
# wheeler migrate-to-plugin
# ---------------------------------------------------------------------------


@app.command("migrate-to-plugin")
def cmd_migrate_to_plugin(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be removed and exit."
    ),
) -> None:
    """Drop the legacy ~/.claude/ install so the wh plugin is not shadowed.

    Claude Code resolves /wh:<name> to a file in ~/.claude/commands/wh/ before
    it looks at the wh plugin's skills, with no error when both exist. This
    removes the legacy files, hooks, statusLine, and MCP registrations that
    `wheeler install` wrote, then prints the two commands that install the
    plugin. Safe and idempotent when there is nothing to migrate.
    """
    from wheeler import installer
    from wheeler.installer import (
        MARKETPLACE_ADD_CMD,
        PLUGIN_INSTALL_CMD,
        detect_plugin,
        legacy_status,
        migrate_to_plugin,
    )

    legacy = legacy_status()
    plugin = detect_plugin(project_dir=Path.cwd())

    console.print(f"Plugin: {plugin.describe()}")
    console.print(f"Legacy: {legacy.describe()}")
    console.print()

    if not legacy.present:
        console.print("[green]Nothing to migrate: no legacy install found.[/green]")
        if plugin.active:
            console.print("[green]The wh plugin is installed and unshadowed.[/green]")
        else:
            console.print("Install the plugin in Claude Code:")
            console.print(f"  [bold]{MARKETPLACE_ADD_CMD}[/bold]")
            console.print(f"  [bold]{PLUGIN_INSTALL_CMD}[/bold]")
        raise typer.Exit(0)

    console.print("[bold]This will remove:[/bold]")
    for rel in legacy.files:
        suffix = " [dim](already gone)[/dim]" if rel in legacy.missing else ""
        console.print(f"  {installer.INSTALL_BASE / rel}{suffix}")
    for name in legacy.untracked_commands:
        console.print(
            f"  {installer.INSTALL_BASE / installer.COMMANDS_REL / (name + '.md')} "
            "[dim](not in manifest)[/dim]"
        )
    console.print("  the Wheeler SessionStart hook and statusLine in settings.json")
    console.print("  the wheeler_* and neo4j mcpServers entries in settings.json")
    console.print()

    if dry_run:
        console.print("[dim]Dry run: nothing removed.[/dim]")
        raise typer.Exit(0)

    if not yes and not typer.confirm("Remove the legacy install?", default=True):
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit(0)

    result = migrate_to_plugin()
    n = len(result.removed) + len(result.removed_untracked)
    console.print(f"[green]Removed {n} file(s) and deregistered hooks/MCP servers.[/green]")
    console.print()

    if result.plugin.active:
        console.print(
            "[green]The wh plugin is installed and no longer shadowed. "
            "Restart Claude Code.[/green]"
        )
    else:
        console.print("Now run these two commands inside Claude Code:")
        console.print(f"  [bold]{MARKETPLACE_ADD_CMD}[/bold]")
        console.print(f"  [bold]{PLUGIN_INSTALL_CMD}[/bold]")


# ---------------------------------------------------------------------------
# wheeler doctor
# ---------------------------------------------------------------------------


_OK = "[green]✓[/green]"
_FAIL = "[red]✗[/red]"
_WARN = "[yellow]⚠[/yellow]"


def _check_import(name: str) -> tuple[bool, str]:
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "")
        return True, ver
    except ImportError as exc:
        return False, str(exc)


def _uri_scheme(uri: str) -> str:
    """Return the lowercased scheme of a Neo4j URI ("" when malformed)."""
    return uri.split("://", 1)[0].lower() if "://" in uri else ""


def _uri_is_tls(uri: str) -> bool:
    """True for the encrypted bolt/neo4j schemes (`+s`, `+ssc`), as Aura uses."""
    scheme = _uri_scheme(uri)
    return scheme.endswith("+s") or scheme.endswith("+ssc")


def _probe_neo4j(cfg) -> tuple[bool, bool, str]:  # noqa: ANN001 (config type is internal)
    """Probe the configured Neo4j URI, then the configured database.

    Returns ``(reachable, database_ok, detail)``. Goes through
    `get_sync_driver` so this exercises the same connection settings the rest
    of Wheeler uses, including the bounded connect timeout that keeps doctor
    from hanging on an unreachable Aura host. Encryption comes from the URI
    scheme and is never passed as a driver argument: the `+s` / `+ssc` schemes
    reject an explicit `encrypted=`, and that is how Aura is addressed.
    """
    try:
        from wheeler.graph.driver import get_sync_driver

        with get_sync_driver(cfg) as drv:
            drv.verify_connectivity()
            try:
                with drv.session(database=cfg.neo4j.database) as session:
                    session.run("RETURN 1").consume()
            except Exception as exc:
                return True, False, f"database '{cfg.neo4j.database}': {_short(exc)}"
        return True, True, ""
    except Exception as exc:
        return False, False, _short(exc)


def _short(exc: object, limit: int = 80) -> str:
    msg = str(exc).replace("\n", " ")
    return msg[:limit] + ("..." if len(msg) > limit else "")


def _isolation_model(cfg, database_ok: bool) -> tuple[str, str]:  # noqa: ANN001
    """Describe which project-isolation model is actually in force.

    `ensure_database()` silently downgrades a dedicated database to
    property-tag namespacing when `CREATE DATABASE` is denied, which is the
    normal case on Aura free tier and on Community Edition. This mirrors that
    resolution so doctor reports the effective model, not the wished-for one.
    """
    db = cfg.neo4j.database
    tag = cfg.neo4j.project_tag
    if tag:
        return "tag", f"property tag _wheeler_project='{tag}' on database '{db}'"
    if db != "neo4j":
        if database_ok:
            return "database", f"dedicated database '{db}'"
        return (
            "downgraded",
            f"database '{db}' not usable, ensure_database() will fall back to "
            f"'neo4j' + tag '{cfg.project.name or db}'",
        )
    if cfg.project.name:
        return (
            "tag",
            f"property tag _wheeler_project='{cfg.project.name}' "
            "(applied by ensure_database on database 'neo4j')",
        )
    return "none", "shared database 'neo4j', no project namespacing"


@app.command("doctor")
def cmd_doctor() -> None:
    """Sanity check: Python, deps, console scripts, Claude Code, Neo4j."""
    table = Table(title="Wheeler doctor")
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center", width=3)
    table.add_column("Detail", style="dim")

    py = sys.version_info
    py_ok = py >= (3, 11)
    table.add_row(
        "Python >= 3.11",
        _OK if py_ok else _FAIL,
        f"{py.major}.{py.minor}.{py.micro}",
    )

    table.add_row("Wheeler", _OK, wheeler.__version__)

    for pkg in ("typer", "rich", "pydantic", "fastmcp", "neo4j", "yaml", "fastembed", "numpy"):
        ok, detail = _check_import(pkg)
        table.add_row(f"  import {pkg}", _OK if ok else _FAIL, detail)

    for script in (
        "wheeler-core-mcp",
        "wheeler-query-mcp",
        "wheeler-mutations-mcp",
        "wheeler-ops-mcp",
    ):
        path = shutil.which(script)
        table.add_row(
            f"  {script}",
            _OK if path else _FAIL,
            path or "not on PATH",
        )

    claude = shutil.which("claude")
    table.add_row(
        "Claude Code CLI",
        _OK if claude else _WARN,
        claude or "npm install -g @anthropic-ai/claude-code",
    )

    # Act delivery: the wh plugin, the legacy tree, or both (the shadowing bug).
    from wheeler import installer

    plugin = installer.detect_plugin(project_dir=Path.cwd())
    legacy = installer.legacy_status()
    n_cmds = len(legacy.commands) + len(legacy.untracked_commands)

    table.add_row(
        "wh plugin",
        _OK if plugin.active else _WARN,
        plugin.describe()
        if plugin.present
        else f"not installed ({installer.PLUGIN_INSTALL_CMD})",
    )
    table.add_row(
        "Legacy ~/.claude acts",
        _WARN if (legacy.present and plugin.active) else _OK,
        legacy.describe(),
    )
    if plugin.active and legacy.present:
        table.add_row(
            "  shadowing",
            _FAIL,
            f"legacy files win over the plugin for all {n_cmds} /wh: acts, "
            "run: wheeler migrate-to-plugin",
        )
    elif not plugin.active and not legacy.present:
        table.add_row("  acts available", _WARN, "none installed by either path")

    cfg = None
    try:
        from wheeler.config import load_config

        cfg = load_config()
    except Exception as exc:
        table.add_row("Wheeler config", _WARN, _short(exc))

    if cfg is not None:
        reachable, database_ok, detail = _probe_neo4j(cfg)
        tls = _uri_is_tls(cfg.neo4j.uri)
        table.add_row(
            "Neo4j URI",
            _OK if reachable else _WARN,
            f"{cfg.neo4j.uri} ({'TLS' if tls else 'no TLS'})",
        )
        if not reachable:
            table.add_row("  connect", _FAIL, detail or "unreachable")
        else:
            table.add_row(
                f"  database '{cfg.neo4j.database}'",
                _OK if database_ok else _WARN,
                "queryable" if database_ok else detail,
            )
        mode, iso_detail = _isolation_model(cfg, database_ok)
        table.add_row(
            "Project isolation",
            _WARN if mode in ("none", "downgraded") else _OK,
            f"{mode}: {iso_detail}",
        )

        # Four sources can supply a Neo4j setting (env > keychain > wheeler.yaml >
        # default), so "where did this value come from" is the first debugging
        # question. Report it rather than making the user reason it out.
        try:
            from wheeler.config import neo4j_sources, shadowed_by_env

            sources = neo4j_sources()
            # Per FIELD, not a set of distinct sources: when only NEO4J_URI is
            # exported, "env, keychain" hides which field the env var took over.
            # Values are deliberately absent. The URI and database are already on
            # their own rows above, the password must never be printed, and each
            # field's env var name is implied by its own name.
            if {row.source for row in sources} == {"default"}:
                summary = "all built-in defaults"
            else:
                summary = ", ".join(f"{row.field}={row.source}" for row in sources)
            table.add_row("Credential source", _OK, summary)

            # The one case worth a warning: a stored credential exists but an
            # exported variable is overriding it. That is the whole of
            # "I ran wheeler login and it still connects to localhost".
            shadowed = shadowed_by_env()
            if shadowed:
                verb = "overrides" if len(shadowed) == 1 else "override"
                them = "it" if len(shadowed) == 1 else "them"
                table.add_row(
                    "  shadowed by env",
                    _WARN,
                    f"{', '.join(shadowed)} {verb} the stored credential; "
                    f"unset {them} or run `wheeler login --status`",
                )
        except Exception as exc:  # keychain unavailable, keyring absent, etc.
            table.add_row("Credential source", _WARN, _short(exc))

    console.print(table)


@app.command("keepalive")
def cmd_keepalive(
    install: bool = typer.Option(
        False, "--install", help="Schedule this to run automatically."
    ),
    uninstall: bool = typer.Option(
        False, "--uninstall", help="Remove the scheduled job."
    ),
    every: int = typer.Option(
        None, "--every", help="Hours between pings when installing (default 12)."
    ),
    status: bool = typer.Option(
        False, "--status", help="Show the last few pings and whether a job is installed."
    ),
) -> None:
    """Touch this project's graph so a hosted instance never goes idle.

    AuraDB Free pauses after 72 hours of inactivity and is DELETED after 90 days
    paused, so an unattended cloud project can quietly destroy itself over a
    holiday. One read plus one idempotent write resets that clock.

    Run bare to ping now; `--install` schedules it (launchd on macOS, cron
    elsewhere).
    """
    import asyncio
    import platform
    import subprocess

    from wheeler import keepalive as ka
    from wheeler.config import load_config

    interval = every or ka.DEFAULT_INTERVAL_HOURS

    if status:
        console.print(f"Log: {escape(str(ka.log_path()))}")
        try:
            lines = ka.log_path().read_text().strip().splitlines()[-5:]
            for line in lines:
                console.print(f"  {escape(line)}")
        except OSError:
            console.print("  [dim](no pings recorded yet)[/dim]")
        agent = ka.launch_agent_path()
        console.print(
            f"Scheduled: [green]yes[/green] ({agent})" if agent.exists()
            else "Scheduled: [yellow]no[/yellow]  (run: wheeler keepalive --install)"
        )
        return

    if uninstall:
        agent = ka.launch_agent_path()
        if agent.exists():
            subprocess.run(["launchctl", "unload", str(agent)], capture_output=True)
            agent.unlink()
            console.print(f"[green]Removed[/green] {agent}")
        else:
            console.print("[dim]Nothing scheduled.[/dim]")
        return

    config = load_config()

    if install:
        executable = shutil.which("wheeler") or sys.argv[0]
        root = str(config.resolved_project_root)
        if platform.system() == "Darwin":
            agent = ka.launch_agent_path()
            agent.parent.mkdir(parents=True, exist_ok=True)
            agent.write_text(ka.render_launch_agent(executable, root, interval))
            subprocess.run(["launchctl", "unload", str(agent)], capture_output=True)
            loaded = subprocess.run(
                ["launchctl", "load", str(agent)], capture_output=True, text=True
            )
            if loaded.returncode != 0:
                console.print(
                    f"[yellow]Wrote {agent} but launchctl load failed:[/yellow] "
                    f"{escape(loaded.stderr.strip())}"
                )
            else:
                console.print(
                    f"[green]Scheduled[/green] every {interval}h -> {agent}\n"
                    f"[dim]Pings {config.neo4j.uri} for project {root}[/dim]"
                )
        else:
            console.print(
                "Add this to your crontab (`crontab -e`):\n\n  "
                + escape(ka.render_cron_line(executable, root, interval))
            )
        # Fall through and ping once now, so an install is verified immediately.

    result = asyncio.run(ka.ping(config))
    if result["ok"]:
        console.print(
            f"[green]Ping OK[/green] {escape(result['target'])} "
            f"({result['nodes']} nodes, ping #{result['ping_count']})"
        )
    else:
        console.print(f"[red]Ping FAILED[/red] {escape(result['target'])}")
        console.print(f"  {escape(result['error'])}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# wheeler db  --  see and switch which graph a project uses
# ---------------------------------------------------------------------------

db_app = typer.Typer(help="List and bind the databases this machine can reach.")
app.add_typer(db_app, name="db")


def _databases_on(config) -> tuple[list[str], str]:  # noqa: ANN001
    """(database names, note) for a connection. Never raises.

    `SHOW DATABASES` needs system-database access, which self-hosted Enterprise
    grants and Aura does not. On Aura the answer is still knowable and still
    correct: exactly one database, the one the instance was provisioned with.
    """
    from neo4j import GraphDatabase

    n = config.neo4j
    try:
        driver = GraphDatabase.driver(n.uri, auth=(n.username, n.password))
    except Exception as exc:
        return [], f"unreachable ({type(exc).__name__})"
    try:
        with driver.session(database="system") as session:
            names = [
                r["name"] for r in session.run("SHOW DATABASES") if r["name"] != "system"
            ]
        return sorted(set(names)), ""
    except Exception:
        try:
            with driver.session(database=n.database) as session:
                session.run("RETURN 1").consume()
            return [n.database], "one database per instance (Aura)"
        except Exception as exc:
            return [], f"unreachable ({type(exc).__name__})"
    finally:
        driver.close()


@db_app.command("list")
def cmd_db_list() -> None:
    """Show every database reachable from this project's stored credentials.

    Multi-database is where the switching goes away. A self-hosted Enterprise
    instance serves many databases CONCURRENTLY on one port, so several projects
    can be live at once and each simply names its own. Aura provisions one
    database per instance, so there a second project means a second instance and
    a second keychain profile.
    """
    from wheeler import credentials
    from wheeler.config import effective_profile, load_config

    config = load_config()
    active_profile = effective_profile(config)
    profiles = credentials.list_profiles() or []

    table = Table(title="Reachable databases")
    table.add_column("Profile", style="cyan", no_wrap=True)
    table.add_column("Connection", style="dim")
    table.add_column("Database")
    table.add_column("", no_wrap=True)

    seen: list[tuple[str, str]] = []
    for name in profiles or [active_profile]:
        record = credentials.load(name) or {}
        if not record:
            continue
        from wheeler.config import Neo4jConfig, WheelerConfig

        probe = WheelerConfig(
            neo4j=Neo4jConfig(
                uri=record.get("uri", ""),
                username=record.get("username", ""),
                password=record.get("password", ""),
                database=record.get("database", "neo4j"),
            )
        )
        names, note = _databases_on(probe)
        if not names:
            table.add_row(name, probe.neo4j.uri, f"[yellow]{note}[/yellow]", "")
            continue
        for db in names:
            here = (
                "<- this project"
                if name == active_profile and db == config.neo4j.database
                else ""
            )
            table.add_row(name, probe.neo4j.uri, db, f"[green]{here}[/green]" if here else "")
            seen.append((name, db))

    if not seen and not profiles:
        names, note = _databases_on(config)
        for db in names:
            here = "<- this project" if db == config.neo4j.database else ""
            table.add_row("(wheeler.yaml)", config.neo4j.uri, db,
                          f"[green]{here}[/green]" if here else "")
        if not names:
            table.add_row("(wheeler.yaml)", config.neo4j.uri,
                          f"[yellow]{note}[/yellow]", "")

    console.print(table)
    console.print(
        "[dim]Bind this project to one with: wheeler db use <database> "
        "[--profile <name>][/dim]"
    )


def _set_yaml_neo4j_keys(path: Path, updates: dict[str, str]) -> None:
    """Set keys inside the `neo4j:` block of a wheeler.yaml, IN PLACE.

    Line-level rather than parse-and-redump on purpose: `yaml.dump` would discard
    every comment in the file, and this project's connection block is mostly
    comments explaining why it is bound the way it is. Losing those to a one-word
    change is a bad trade.
    """
    def _emit(key: str, value: str) -> str:
        # Always quote. `off`, `yes`, `true` and `null` are all legal Neo4j
        # database names AND YAML booleans or nulls, so writing them bare turns
        # `database: off` into `False`, which fails pydantic validation and makes
        # every Wheeler command in that project raise until the file is
        # hand-edited. `json.dumps` rather than `yaml.safe_dump` because the
        # latter emits a `...` document-end marker for a bare scalar, which
        # corrupts the file it is spliced into; JSON strings are valid YAML.
        return f"  {key}: {json.dumps(str(value))}"

    lines = path.read_text().splitlines()
    # Tolerate a trailing comment on the block header (`neo4j:  # local`), which
    # an exact match missed, prepending a SECOND `neo4j:` block whose keys PyYAML
    # then silently discarded in favour of the original.
    def _is_block_header(line: str) -> bool:
        stripped = line.split("#", 1)[0].rstrip()
        return stripped == "neo4j:"

    try:
        start = next(i for i, line in enumerate(lines) if _is_block_header(line))
    except StopIteration:
        lines = ["neo4j:", *[_emit(k, v) for k, v in updates.items()], *lines]
        path.write_text("\n".join(lines) + "\n")
        return

    # The block ends at the next line that is neither indented, blank, NOR a
    # comment. Treating a column-0 comment as the end truncated the scan, so an
    # existing `database:` below it survived alongside the newly inserted one and
    # PyYAML's last-wins made `wheeler db use` a silent no-op.
    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("#") and not lines[i].startswith((" ", "\t")):
            end = i
            break

    remaining = dict(updates)
    for i in range(start + 1, end):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            continue
        for key in list(remaining):
            if stripped.startswith(f"{key}:"):
                lines[i] = _emit(key, remaining.pop(key))
    insert_at = end
    for key, value in remaining.items():
        lines.insert(insert_at, _emit(key, value))
        insert_at += 1

    path.write_text("\n".join(lines) + "\n")


@db_app.command("use")
def cmd_db_use(
    database: str = typer.Argument(..., help="Database name to bind this project to."),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Also bind the keychain profile to connect through."
    ),
) -> None:
    """Point THIS project at a database, by editing its wheeler.yaml.

    Per project, never machine-wide: the binding lives in the project's own file,
    so opening a folder IS the switch and two projects can be live at once.
    """
    from wheeler.config import find_config_file, load_config

    config_path = find_config_file()
    if config_path is None:
        console.print("[red]No wheeler.yaml here.[/red] Run `wheeler init .` first.")
        raise typer.Exit(1)

    updates = {"database": database}
    if profile:
        updates["profile"] = profile
    _set_yaml_neo4j_keys(config_path, updates)

    from wheeler.config import reset_keychain_cache

    reset_keychain_cache()
    config = load_config()
    console.print(f"[green]Bound[/green] {config_path} -> database '{database}'")
    console.print(f"[dim]Resolves to: {config.neo4j.uri} db={config.neo4j.database}[/dim]")

    names, note = _databases_on(config)
    if names and database not in names:
        console.print(
            f"[yellow]Warning:[/yellow] '{database}' is not among the databases this "
            f"connection reports ({', '.join(names)}). "
            "Create it with `wheeler db create` if the server allows it."
        )


@db_app.command("create")
def cmd_db_create(
    database: str = typer.Argument(..., help="Database to create."),
) -> None:
    """Create a database on this project's connection (Enterprise only).

    Aura refuses this: it provisions one database per instance, so a second
    project there means a second instance rather than a second database.
    """
    from neo4j import GraphDatabase

    from wheeler.config import load_config

    config = load_config()
    n = config.neo4j
    driver = GraphDatabase.driver(n.uri, auth=(n.username, n.password))
    try:
        with driver.session(database="system") as session:
            session.run(f"CREATE DATABASE `{database}` IF NOT EXISTS").consume()
        console.print(f"[green]Created[/green] database '{database}' on {n.uri}")
        console.print(f"[dim]Bind a project to it with: wheeler db use {database}[/dim]")
    except Exception as exc:
        console.print(f"[red]Could not create '{database}':[/red] {escape(str(exc))[:200]}")
        console.print(
            "[dim]Aura provisions one database per instance and refuses CREATE "
            "DATABASE. Create another instance instead, then:\n"
            "  wheeler login --aura-file <file> --profile <name>\n"
            "  wheeler db use <db> --profile <name>[/dim]"
        )
        raise typer.Exit(1)
    finally:
        driver.close()


@db_app.command("instances")
def cmd_db_instances() -> None:
    """List the local Neo4j instances on this machine, and whether they can co-run.

    Every Desktop instance ships its own `bin/neo4j`, so the CLI is never
    missing; it is just buried under an opaque uuid with a JRE that is not on
    PATH. This finds both.
    """
    from wheeler import desktop

    root = desktop.desktop_root()
    if root is None:
        console.print(
            "[yellow]No Neo4j Desktop instances found on this machine.[/yellow]\n"
            "[dim]That is fine: a project can point at any Neo4j via wheeler.yaml, "
            "or use a cloud instance (wheeler init --graph cloud).[/dim]"
        )
        return

    found = desktop.instances()
    table = Table(title=f"Local Neo4j instances ({len(found)})")
    table.add_column("Instance", style="cyan", no_wrap=True)
    table.add_column("Databases")
    table.add_column("Bolt", no_wrap=True)
    table.add_column("HTTP", no_wrap=True)
    table.add_column("State", no_wrap=True)

    for inst in found:
        running = desktop.status(inst)
        table.add_row(
            inst.short_id,
            ", ".join(inst.databases) or "[dim](none)[/dim]",
            str(inst.ports.get("bolt", "?")),
            str(inst.ports.get("http", "?")),
            "[green]running[/green]" if running else "[dim]stopped[/dim]",
        )
    console.print(table)

    conflicts = desktop.port_conflicts(found)
    if conflicts:
        console.print(
            "\n[yellow]These instances cannot run at the same time:[/yellow]"
        )
        for name, port, owners in conflicts:
            console.print(f"  {name} port {port} claimed by: {', '.join(owners)}")
        console.print(
            "[dim]Give each its own ports in "
            "<instance>/conf/neo4j.conf. Seven settings need to differ, not one: "
            + ", ".join(s for _n, s, _d in desktop.PORT_SETTINGS)
            + ".[/dim]"
        )
    else:
        console.print(
            "[dim]All ports are distinct, so these can run concurrently "
            "(the Desktop UI still starts only one; use `wheeler db start`).[/dim]"
        )

    if desktop.java_home() is None:
        console.print(
            "[yellow]No bundled JRE found[/yellow], so `wheeler db start` cannot "
            "run. Start an instance once from the Desktop UI first."
        )


@db_app.command("start")
def cmd_db_start(
    name: str = typer.Argument(..., help="Instance id, short id, or a database it holds."),
) -> None:
    """Start a local instance, bypassing Desktop's one-at-a-time UI limit."""
    from wheeler import desktop

    inst = desktop.find(name)
    if inst is None:
        console.print(f"[red]No instance matches {name!r}.[/red] Try: wheeler db instances")
        raise typer.Exit(1)
    ok, out = desktop.start(inst)
    console.print(f"[{'green' if ok else 'red'}]{escape(out) or 'no output'}[/]")
    if ok:
        console.print(f"[dim]{inst.bolt_uri}  databases: {', '.join(inst.databases)}[/dim]")
    else:
        raise typer.Exit(1)


@db_app.command("stop")
def cmd_db_stop(
    name: str = typer.Argument(..., help="Instance id, short id, or a database it holds."),
) -> None:
    """Stop a local instance."""
    from wheeler import desktop

    inst = desktop.find(name)
    if inst is None:
        console.print(f"[red]No instance matches {name!r}.[/red] Try: wheeler db instances")
        raise typer.Exit(1)
    ok, out = desktop.stop(inst)
    console.print(f"[{'green' if ok else 'red'}]{escape(out) or 'no output'}[/]")
    if not ok:
        raise typer.Exit(1)


def _setup_local(local_instances, profile: Optional[str], yes: bool):  # noqa: ANN001,ANN202
    """Walk the user onto a local instance and a database on it.

    The whole reason this is worth walking through: Desktop shows one running
    instance and hides the rest, so a user who has four graphs believes they can
    only reach one and starts swapping. Listing them, naming the databases inside
    each, and reporting which cannot co-run turns that into a choice.
    """
    from wheeler import credentials, desktop
    from wheeler.config import Neo4jConfig

    if not local_instances:
        console.print(
            "[dim]No Neo4j Desktop instances found. Using the standard local "
            "address; edit wheeler.yaml if your Neo4j is elsewhere.[/dim]"
        )
        return Neo4jConfig()

    conflicts = desktop.port_conflicts(local_instances)
    if conflicts:
        console.print(
            f"\n[yellow]{len(conflicts)} port(s) are claimed by more than one "
            "instance, so those cannot run at the same time.[/yellow]\n"
            "[dim]Give each instance its own ports in <instance>/conf/neo4j.conf. "
            "Seven settings need to differ, not just bolt:\n  "
            + ", ".join(s for _n, s, _d in desktop.PORT_SETTINGS)
            + "[/dim]"
        )

    if yes:
        chosen = next(
            (i for i in local_instances if i.databases), local_instances[0]
        )
        db = next((d for d in chosen.databases if d != "neo4j"), "neo4j")
        console.print(f"[dim]Using {chosen.short_id} ({chosen.bolt_uri}), database {db}.[/dim]")
        return Neo4jConfig(uri=chosen.bolt_uri, database=db)

    console.print("\n[bold]Local Neo4j instances[/bold]")
    for index, inst in enumerate(local_instances, start=1):
        dbs = ", ".join(inst.databases) or "(none yet)"
        console.print(
            f"  {index}. {inst.short_id}  bolt {inst.ports.get('bolt')}  "
            f"databases: {dbs}"
        )
    pick = typer.prompt("Use which instance", default="1").strip()
    try:
        chosen = local_instances[int(pick) - 1]
    except (ValueError, IndexError):
        raise typer.BadParameter(f"{pick!r} is not one of 1..{len(local_instances)}") from None

    options = chosen.databases or ["neo4j"]
    console.print(
        "\n[dim]A database per project keeps their graphs separate while sharing "
        "one server. Create new ones later with: wheeler db create <name>[/dim]"
    )
    database = typer.prompt(
        f"Database on {chosen.short_id} ({', '.join(options)})",
        default=next((d for d in options if d != "neo4j"), options[0]),
    ).strip()

    # Credential to the keychain, same as the cloud route, so wheeler.yaml holds
    # no password and the binding is a profile name either way.
    slot = (profile or "").strip() or f"local-{chosen.short_id}"
    if credentials.load(slot):
        console.print(f"[green]Using the credential already stored as '{slot}'.[/green]")
        return Neo4jConfig(profile=slot, database=database)

    username = typer.prompt("Neo4j username", default="neo4j").strip()
    password = typer.prompt("Neo4j password", hide_input=True)
    if not _store_local_credential(chosen.bolt_uri, username, password, database, slot):
        console.print(
            "[dim]Falling back to recording the address in wheeler.yaml without a "
            "password; set NEO4J_PASSWORD or run `wheeler login` later.[/dim]"
        )
        return Neo4jConfig(uri=chosen.bolt_uri, username=username, database=database)
    return Neo4jConfig(profile=slot, database=database)


def _store_local_credential(
    uri: str, username: str, password: str, database: str, slot: str
) -> bool:
    """Connect first, then store. Returns whether it worked."""
    from wheeler import aura, credentials, desktop

    console.print(f"[dim]Connecting to {escape(uri)} ...[/dim]")
    try:
        aura.validate_connection(uri, username, password, database)
    except Exception as exc:
        console.print(f"[red]Could not connect.[/red] {escape(str(exc))[:160]}")
        inst = desktop.find(uri.rsplit(":", 1)[-1])
        console.print(
            "[dim]If the instance is stopped, start it with:\n"
            f"  wheeler db start {inst.short_id if inst else '<instance>'}\n"
            "If the password is wrong, it is the one set when the instance was "
            "created in Neo4j Desktop.[/dim]"
        )
        return False
    try:
        credentials.save(slot, uri, username, password, database)
    except Exception as exc:
        console.print(f"[red]Connected, but could not store it:[/red] {escape(str(exc))}")
        return False
    console.print(f"[green]Connected and stored[/green] {escape(uri)} as profile '{slot}'.")
    return True


@db_app.command("assign-ports")
def cmd_db_assign_ports(
    apply: bool = typer.Option(False, "--apply", help="Write the changes (default: dry run)."),
    stride: int = typer.Option(10, "--stride", help="Port spacing between instances."),
) -> None:
    """Give each local instance its own ports so they can run concurrently.

    Dry run by default. The first instance keeps the stock ports, so anything
    already pointed at 7687 keeps working and only the surplus instances move.
    """
    from wheeler import desktop

    found = desktop.instances()
    if not found:
        console.print("[yellow]No Neo4j Desktop instances found.[/yellow]")
        return

    plan = desktop.assign_ports(found, stride=stride)

    # Refuse while anything is running. A running server holds its OLD ports
    # until restart, so editing under it produces a machine whose conf and whose
    # reality disagree: the next start of a second instance then collides on
    # ports the file says are free.
    running = [inst.short_id for inst, _p in plan if desktop.status(inst)]
    if running and apply:
        console.print(
            f"[red]Refusing to rewrite ports while {', '.join(running)} "
            "is running.[/red]\n"
            "[dim]A running server keeps its old ports until restart, so the conf "
            "and reality would disagree. Stop it first:\n  wheeler db stop "
            f"{running[0]}[/dim]"
        )
        raise typer.Exit(1)

    changed_any = False
    for inst, wanted in plan:
        moves = {n: p for n, p in wanted.items() if inst.ports.get(n) != p}
        label = f"{inst.short_id}  ({', '.join(inst.databases) or 'no databases'})"
        if not moves:
            console.print(f"  {label}: [dim]already correct[/dim]")
            continue
        changed_any = True
        console.print(f"  {label}")
        for name, port in sorted(moves.items()):
            console.print(f"      {name:10} {inst.ports.get(name)} -> {port}")
        console.print(f"      [dim]-> bolt://localhost:{wanted['bolt']}[/dim]")

    if not changed_any:
        console.print("\n[green]Every instance already has its own ports.[/green]")
        return

    if not apply:
        console.print("\n[dim]Nothing written. Re-run with --apply.[/dim]")
        return

    for inst, changes in desktop.apply_ports(plan):
        if changes:
            console.print(f"[green]Updated[/green] {inst.short_id} ({len(changes)} setting(s))")
    console.print("[dim]A .conf.wheeler-bak was taken for each instance.[/dim]")

    # The regression this whole command creates: a project pointed at a port
    # that just moved. Say so, by name, rather than letting it surface later as
    # an unreachable graph.
    stale = desktop.stale_bindings(plan)
    if stale:
        console.print(
            "\n[yellow]These stored credentials now name a port no instance "
            "serves:[/yellow]"
        )
        for line in stale:
            console.print(f"  {escape(line)}")
        console.print(
            "[dim]Repoint each with: wheeler login --profile <name>  "
            "(or wheeler db use <database> in that project).[/dim]"
        )
    console.print(
        "\n[dim]Any project whose wheeler.yaml pins a bare `uri:` needs the same "
        "check; `wheeler db instances` shows which ports are served now.[/dim]"
    )


@db_app.command("check")
def cmd_db_check(
    start: bool = typer.Option(
        False, "--start", help="Start the serving instance if it is stopped."
    ),
) -> None:
    """Preflight THIS project's graph connection, and say exactly what is wrong.

    The three ways a local multi-instance setup fails all look identical from the
    driver (`ServiceUnavailable`) and have completely different fixes: the
    instance is stopped, no instance serves that port, or the instance is up but
    has no such database. This separates them.
    """
    import asyncio

    from wheeler import desktop
    from wheeler.config import effective_profile, load_config

    config = load_config()
    uri, database = config.neo4j.uri, config.neo4j.database
    console.print(f"[bold]Project[/bold]  {escape(str(config.resolved_project_root))}")
    console.print(f"[bold]Target [/bold]  {escape(uri)}  database={escape(database)}")
    profile = effective_profile(config)
    console.print(f"[bold]Profile[/bold]  {escape(profile)}"
                  + ("  [red](declared but not stored)[/red]" if config.neo4j.profile_missing else ""))

    inst = None
    port = desktop._local_port(uri)
    if port is not None:
        serving = [i for i in desktop.instances() if i.ports.get("bolt") == port]
        inst = serving[0] if serving else None
        if inst is None:
            console.print(f"\n[red]No local instance is configured for port {port}.[/red]")
            for line in desktop.explain_target(uri, database):
                console.print(f"  {escape(line)}")
            raise typer.Exit(1)

        running = desktop.status(inst)
        console.print(
            f"[bold]Instance[/bold] {inst.short_id}  "
            + ("[green]running[/green]" if running else "[yellow]stopped[/yellow]")
            + f"  databases: {', '.join(inst.databases) or '(none)'}"
        )
        if not running and start:
            console.print(f"[dim]Starting {inst.short_id} ...[/dim]")
            ok, out = desktop.start(inst)
            console.print(("[green]" if ok else "[red]") + escape(out.splitlines()[-1] if out else "") + "[/]")
            if not ok:
                raise typer.Exit(1)
        elif not running:
            console.print(
                f"\n[yellow]The instance is stopped, so nothing can connect.[/yellow]\n"
                f"  wheeler db start {inst.short_id}      (or re-run with --start)"
            )
            raise typer.Exit(1)

        if inst.databases and database not in inst.databases:
            console.print(
                f"\n[red]Instance {inst.short_id} has no database "
                f"{escape(database)!r}.[/red]\n"
                f"  wheeler db create {escape(database)}\n"
                f"  or: wheeler db use <one of: {', '.join(inst.databases)}>"
            )
            raise typer.Exit(1)

    # The only check that proves it: actually connect.
    async def _probe() -> tuple[bool, str]:
        from wheeler.tools.graph_tools import _get_backend

        try:
            backend = await _get_backend(config)
            rows = await backend.run_cypher("MATCH (n) RETURN count(n) AS c")
            return True, f"{rows[0]['c']} nodes"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    ok, detail = asyncio.run(_probe())
    if ok:
        console.print(f"\n[green]Connected.[/green] {escape(detail)}")
        return
    console.print(f"\n[red]Could not connect.[/red] {escape(detail[:200])}")
    for line in desktop.explain_target(uri, database):
        console.print(f"  {escape(line)}")
    raise typer.Exit(1)
