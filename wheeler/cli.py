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
        write_config(project_dir, project=ProjectMeta(name=project_name))
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
