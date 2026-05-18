"""Wheeler top-level CLI entry point (`wheeler` console script).

Extends the legacy `wheeler.tools.cli:app` Typer instance with three commands
designed for the `uvx wheeler` / `uv tool install wheeler` install path:

- `wheeler init <project>`  scaffold a new Wheeler project
- `wheeler serve [server]`  start an MCP server (debug / standalone)
- `wheeler doctor`          sanity check

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
        try:
            from wheeler.installer import install as _install

            files = _install()
            console.print(
                f"[green]Installed {len(files)} file(s) to ~/.claude/ "
                "(slash commands + agents + hooks).[/green]"
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
    "monolith": "wheeler.mcp_server",
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

    cmd_dir = Path.home() / ".claude" / "commands" / "wh"
    n_cmds = len(list(cmd_dir.glob("*.md"))) if cmd_dir.is_dir() else 0
    table.add_row(
        "Slash commands",
        _OK if n_cmds else _WARN,
        f"{n_cmds} installed at {cmd_dir}" if n_cmds else "run: wheeler install",
    )

    try:
        from neo4j import GraphDatabase

        from wheeler.config import load_config

        cfg = load_config()
        with GraphDatabase.driver(
            cfg.neo4j.uri,
            auth=(cfg.neo4j.username, cfg.neo4j.password),
        ) as drv:
            drv.verify_connectivity()
        neo_status = _OK
        neo_detail = cfg.neo4j.uri
    except Exception as exc:
        neo_status = _WARN
        msg = str(exc)
        neo_detail = msg[:80] + ("..." if len(msg) > 80 else "")

    table.add_row("Neo4j reachable", neo_status, neo_detail)

    console.print(table)
