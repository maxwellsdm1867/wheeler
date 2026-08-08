"""wheeler-tools CLI: deterministic graph and validation commands."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.table import Table
from typer.core import TyperGroup

from wheeler.config import load_config, project_knowledge_dir, project_synthesis_dir
from wheeler.graph.schema import (
    ALLOWED_RELATIONSHIPS,
    get_status,
    init_schema,
)
from wheeler.validation.citations import (
    CitationStatus,
    extract_citations,
    validate_citations,
)

console = Console()

app = typer.Typer(
    name="wheeler-tools",
    help="Wheeler deterministic tools: graph management and citation validation.",
    add_completion=False,
)
graph_app = typer.Typer(help="Knowledge graph management commands.")
app.add_typer(graph_app, name="graph")

dev_app = typer.Typer(help="Developer commands.")
app.add_typer(dev_app, name="dev")

dashboard_app = typer.Typer(
    help="Render an interactive HTML research dashboard from the knowledge graph."
)
app.add_typer(dashboard_app, name="dashboard")

# External-tool integrations (Asta Paper Finder, etc.). Guarded so a missing
# integrations package never breaks the rest of the CLI.
try:
    from wheeler.integrations.asta.cli import integrate_app

    app.add_typer(integrate_app, name="integrate")
except ImportError:
    pass

# Service enable/disable curation (the .wheeler/services/ folder). Guarded the
# same way so a missing integrations package never breaks the rest of the CLI.
try:
    from wheeler.integrations.services_cli import services_app

    app.add_typer(services_app, name="services")
except ImportError:
    pass

# LLM-SR equation-discovery driver (init/prompt/submit/best). Guarded so a
# missing optional dependency cannot break the rest of the CLI.
#
# On failure the group is still REGISTERED, as a stub that reports the real
# cause. Dropping it silently (the previous behavior) made a missing optional
# extra indistinguishable from an absent engine or a genuine import bug: all
# three surfaced as "No such command 'llmsr'" with no hint, which sent the
# scientist chasing the wrong fix. Naming the failing module is the whole point.
try:
    from wheeler.integrations.llmsr.cli import llmsr_app

    app.add_typer(llmsr_app, name="llmsr")
except ImportError as _llmsr_exc:  # pragma: no cover - needs the extra absent
    _llmsr_error = _llmsr_exc
    _llmsr_missing = (getattr(_llmsr_exc, "name", "") or "").split(".")[0]
    if _llmsr_missing == "scipy":
        _llmsr_hint = (
            "LLM-SR needs the optional scipy extra. Install it with "
            "`uv tool install wheeler --with scipy` or "
            "`pip install 'wheeler[llmsr]'`."
        )
    elif _llmsr_missing:
        _llmsr_hint = (
            f"The LLM-SR engine could not import {_llmsr_missing!r}. "
            "Install that dependency, or reinstall Wheeler with the llmsr extra."
        )
    else:
        _llmsr_hint = (
            "The LLM-SR engine failed to import. The error above names the cause."
        )

    def _llmsr_report_unavailable() -> None:
        """Print the real cause on stderr and exit non-zero."""
        typer.echo(f"wheeler llmsr is unavailable: {_llmsr_error}", err=True)
        typer.echo(_llmsr_hint, err=True)
        raise typer.Exit(code=1)

    class _LlmsrUnavailableGroup(TyperGroup):
        """Answer with the diagnostic for ANY invocation, subcommands included.

        A Click Group resolves the first positional as a subcommand name before
        the group callback ever runs, so `wheeler llmsr init --spec x` would
        otherwise die with "No such command 'init'" and no explanation: the
        exact class of message this stub exists to eliminate. Overriding
        resolve_command catches every verb, known or not. `--help` is unaffected
        because Click's help option is eager and exits before resolution.
        """

        def resolve_command(self, ctx, args):  # type: ignore[no-untyped-def]
            _llmsr_report_unavailable()

    # Rich renders the help string and would read "[llmsr]" as a style tag,
    # swallowing it and printing a wrong install command. Escape it for help;
    # the stderr echo above is plain text and needs no escaping.
    _llmsr_help_hint = _llmsr_hint.replace("[", "\\[")
    _llmsr_stub = typer.Typer(
        cls=_LlmsrUnavailableGroup,
        help=(
            f"LLM-SR equation discovery (UNAVAILABLE: {_llmsr_error}). "
            f"{_llmsr_help_hint}"
        ),
    )

    @_llmsr_stub.callback(invoke_without_command=True)
    def _llmsr_unavailable() -> None:
        """Report why the LLM-SR engine is unavailable instead of vanishing."""
        _llmsr_report_unavailable()

    app.add_typer(_llmsr_stub, name="llmsr")


# ---------------------------------------------------------------------------
# graph init
# ---------------------------------------------------------------------------


@graph_app.command("init")
def graph_init() -> None:
    """Apply schema constraints and indexes to Neo4j."""
    config = load_config()
    try:
        applied = asyncio.run(init_schema(config))
        console.print(f"[green]Applied {len(applied)} constraints/indexes.[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to init schema:[/red] {exc}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# graph status
# ---------------------------------------------------------------------------


@graph_app.command("status")
def graph_status() -> None:
    """Show node counts per label in the knowledge graph."""
    config = load_config()
    try:
        counts = asyncio.run(get_status(config))
    except Exception as exc:
        console.print(f"[red]Failed to get status:[/red] {exc}")
        raise typer.Exit(1)

    table = Table(title="Knowledge Graph Status")
    table.add_column("Label", style="cyan")
    table.add_column("Count", justify="right")
    total = 0
    for label, count in sorted(counts.items()):
        # _status / _error sentinels carry str values when the backend
        # is offline; skip them so the totals row stays numeric.
        if label.startswith("_") or not isinstance(count, int):
            continue
        table.add_row(label, str(count))
        total += count
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
    console.print(table)


# ---------------------------------------------------------------------------
# graph add-finding
# ---------------------------------------------------------------------------


def _run_mutation(tool_name: str, args: dict) -> dict:
    """Run one graph mutation through the same path the MCP tools use.

    These three verbs used to open a sync driver and issue bare Cypher, which
    skipped the entire triple-write: no knowledge/{id}.json, no
    synthesis/{id}.md, no embedding, no WriteReceipt, no trace_id, and for
    `link` no synthesis re-render of either endpoint. A node created that way
    lands as `graph_only`, which is precisely the drift class
    `repair_consistency` CANNOT fix -- it warns and stops, because regenerating
    content from a ~100-char graph node is not supported. The CLI was
    manufacturing the one inconsistency the repair path cannot resolve.

    `execute_tool` returns a JSON STRING and reports failure as an `error` key
    rather than raising, so the error check here is not optional: without it,
    failures print as successes.
    """
    import asyncio
    import json as _json

    from wheeler.tools.graph_tools import execute_tool

    config = load_config()
    try:
        raw = asyncio.run(execute_tool(tool_name, dict(args), config))
    except Exception as exc:
        console.print(f"[red]Failed:[/red] {exc}")
        raise typer.Exit(1)

    result = _json.loads(raw)
    if "error" in result:
        console.print(f"[red]Failed:[/red] {result['error']}")
        raise typer.Exit(1)
    return result


@graph_app.command("add-finding")
def graph_add_finding(
    desc: str = typer.Option(..., "--desc", "-d", help="Finding description"),
    confidence: float = typer.Option(
        ..., "--confidence", "-c", help="Confidence score (0.0-1.0)"
    ),
) -> None:
    """Add a Finding node to the knowledge graph."""
    result = _run_mutation(
        "add_finding", {"description": desc, "confidence": confidence}
    )
    console.print(
        f"[green]Created Finding:[/green] [{result['node_id']}] {desc}"
    )


# ---------------------------------------------------------------------------
# graph add-question
# ---------------------------------------------------------------------------


@graph_app.command("add-question")
def graph_add_question(
    question: str = typer.Option(..., "--question", "-q", help="The open question"),
    priority: int = typer.Option(
        5, "--priority", "-p", help="Priority (1=low, 10=high)"
    ),
) -> None:
    """Add an OpenQuestion node to the knowledge graph."""
    result = _run_mutation(
        "add_question", {"question": question, "priority": priority}
    )
    console.print(
        f"[green]Created OpenQuestion:[/green] [{result['node_id']}] {question}"
    )


# ---------------------------------------------------------------------------
# graph link
# ---------------------------------------------------------------------------


@graph_app.command("link")
def graph_link(
    source: str = typer.Option(..., "--from", "-s", help="Source node ID"),
    target: str = typer.Option(..., "--to", "-t", help="Target node ID"),
    rel_type: str = typer.Option(
        ...,
        "--rel",
        "-r",
        help=f"Relationship type. Allowed: {', '.join(ALLOWED_RELATIONSHIPS)}",
    ),
) -> None:
    """Create a relationship between two nodes."""
    if rel_type not in ALLOWED_RELATIONSHIPS:
        console.print(
            f"[red]Invalid relationship type:[/red] {rel_type}\n"
            f"Allowed: {', '.join(ALLOWED_RELATIONSHIPS)}"
        )
        raise typer.Exit(1)



    _run_mutation(
        "link_nodes",
        {"source_id": source, "target_id": target, "relationship": rel_type},
    )
    console.print(f"[green]Linked:[/green] [{source}] -[{rel_type}]-> [{target}]")


# ---------------------------------------------------------------------------
# graph trace
# ---------------------------------------------------------------------------


@graph_app.command("trace")
def graph_trace(
    node_id: str = typer.Argument(help="Node ID to trace (e.g., F-3a2b)"),
) -> None:
    """Trace provenance chain backwards from a node."""
    from rich.tree import Tree
    from wheeler.graph.trace import trace_node

    config = load_config()
    try:
        result = asyncio.run(trace_node(node_id, config))
    except Exception as exc:
        console.print(f"[red]Trace failed:[/red] {exc}")
        raise typer.Exit(1)

    if result is None:
        console.print(f"[red]Node not found:[/red] {node_id}")
        raise typer.Exit(1)

    # Build a Rich tree
    root_text = f"[bold cyan][{result.root_id}][/bold cyan] {result.root_label}"
    if result.root_description:
        root_text += f": {result.root_description}"
    tree = Tree(root_text)

    if not result.chain:
        tree.add("[dim]No upstream provenance found[/dim]")
    else:
        for step in result.chain:
            step_text = (
                f"[cyan][{step.node_id}][/cyan] {step.label}"
                f" [dim]—[{step.relationship}]→[/dim]"
            )
            if step.description:
                step_text += f" {step.description}"
            branch = tree.add(step_text)
            for key, val in step.properties.items():
                branch.add(f"[dim]{key}:[/dim] {val}")

    console.print(tree)


# ---------------------------------------------------------------------------
# graph stale
# ---------------------------------------------------------------------------


@graph_app.command("stale")
def graph_stale() -> None:
    """Detect Script nodes with stale file hashes."""
    from wheeler.graph.provenance import detect_stale_scripts

    config = load_config()
    try:
        stale = asyncio.run(detect_stale_scripts(config))
    except Exception as exc:
        console.print(f"[red]Failed to detect stale scripts:[/red] {exc}")
        raise typer.Exit(1)

    if not stale:
        console.print("[green]No stale scripts found.[/green]")
        return

    table = Table(title="Stale Scripts")
    table.add_column("Node ID", style="cyan")
    table.add_column("Path")
    table.add_column("Status", style="yellow")

    for s in stale:
        status = "FILE MISSING" if s.current_hash == "FILE_NOT_FOUND" else "HASH CHANGED"
        table.add_row(s.node_id, s.path, status)
    console.print(table)


# ---------------------------------------------------------------------------
# graph add-script
# ---------------------------------------------------------------------------


@graph_app.command("add-script")
def graph_add_script(
    script: str = typer.Option(..., "--script", "-s", help="Path to script file"),
    language: str = typer.Option(..., "--language", "-l", help="Language (e.g., matlab, python)"),
    version: str = typer.Option("", "--version", "-v", help="Language version"),
) -> None:
    """Add a Script node with provenance tracking."""
    from pathlib import Path as P
    from wheeler.graph.provenance import ScriptProvenance, create_script_node, hash_file

    config = load_config()
    script_path = P(script)
    if not script_path.exists():
        console.print(f"[red]Script not found:[/red] {script}")
        raise typer.Exit(1)

    script_hash = hash_file(script_path)

    prov = ScriptProvenance(
        path=str(script_path.resolve()),
        hash=script_hash,
        language=language,
        version=version,
    )

    try:
        node_id = asyncio.run(create_script_node(prov, config))
        console.print(
            f"[green]Created Script:[/green] [{node_id}]\n"
            f"  Path: {script} (SHA-256: {script_hash[:12]}...)\n"
            f"  Language: {language} {version}"
        )
    except Exception as exc:
        console.print(f"[red]Failed:[/red] {exc}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# graph migrate-prov
# ---------------------------------------------------------------------------


@graph_app.command("migrate-prov")
def graph_migrate_prov(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing changes"),
    skip_neo4j: bool = typer.Option(False, "--skip-neo4j", help="Only migrate knowledge/ JSON files"),
    skip_files: bool = typer.Option(False, "--skip-files", help="Only migrate Neo4j graph"),
) -> None:
    """Migrate provenance schema: Analysis -> Script + Execution, rename relationships."""
    from wheeler.graph.migration_prov import (
        migrate_analysis_nodes,
        migrate_knowledge_files,
        rename_relationships,
    )

    config = load_config()
    # Anchored on the project root, not the CWD: a migration run from a
    # subdirectory must rewrite the project's knowledge/ files, not create an
    # empty one next to wherever the shell happened to be.
    knowledge_path = project_knowledge_dir(config)

    if dry_run:
        console.print("[yellow]DRY RUN — showing what would be migrated[/yellow]\n")

    # --- Neo4j migration ---
    if not skip_files and not skip_neo4j:
        # Both: Neo4j first, then files
        pass  # fall through to unified logic below
    elif skip_neo4j and skip_files:
        console.print("[red]Cannot skip both Neo4j and files.[/red]")
        raise typer.Exit(1)

    if not skip_neo4j:
        console.print("[bold]Phase 1: Migrate Analysis nodes in Neo4j[/bold]")
        if dry_run:
            console.print("  (would split Analysis -> Script + Execution)")
        else:
            try:
                node_report = asyncio.run(migrate_analysis_nodes(config))
                console.print(
                    f"  Found: {node_report['analysis_nodes_found']}, "
                    f"Migrated: {node_report['migrated']}, "
                    f"Errors: {node_report['errors']}"
                )
                for d in node_report.get("details", []):
                    console.print(d)
            except Exception as exc:
                console.print(f"  [red]Failed:[/red] {exc}")
                raise typer.Exit(1)

        console.print("\n[bold]Phase 2: Rename relationships in Neo4j[/bold]")
        if dry_run:
            console.print("  (would rename USED_DATA->USED, GENERATED->WAS_GENERATED_BY, etc.)")
        else:
            try:
                rel_report = asyncio.run(rename_relationships(config))
                console.print(f"  Total renamed: {rel_report['total_renamed']}")
                for d in rel_report.get("details", []):
                    console.print(d)
            except Exception as exc:
                console.print(f"  [red]Failed:[/red] {exc}")
                raise typer.Exit(1)

    if not skip_files:
        console.print("\n[bold]Phase 3: Migrate knowledge/ JSON files[/bold]")
        if dry_run:
            a_files = sorted(knowledge_path.glob("A-*.json"))
            console.print(f"  Would migrate {len(a_files)} A-*.json file(s)")
        else:
            try:
                file_report = migrate_knowledge_files(knowledge_path)
                console.print(
                    f"  Found: {file_report['found']}, "
                    f"Migrated: {file_report['migrated']}, "
                    f"Errors: {file_report['errors']}"
                )
                for d in file_report.get("details", []):
                    console.print(d)
            except Exception as exc:
                console.print(f"  [red]Failed:[/red] {exc}")
                raise typer.Exit(1)

    console.print("\n[green]Provenance migration complete.[/green]")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@app.command("validate")
def validate(
    text: str = typer.Argument(help="Text to validate citations in"),
) -> None:
    """Extract and validate citations in text against the knowledge graph."""
    config = load_config()
    citations = extract_citations(text)

    if not citations:
        console.print("[yellow]No citations found in text.[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found {len(citations)} citation(s): {', '.join(citations)}")

    try:
        results = asyncio.run(validate_citations(text, config))
    except Exception as exc:
        console.print(f"[red]Validation failed (Neo4j error):[/red] {exc}")
        raise typer.Exit(1)

    table = Table(title="Citation Validation Results")
    table.add_column("Node ID", style="cyan")
    table.add_column("Label")
    table.add_column("Status")
    table.add_column("Details")

    for r in results:
        style = {
            CitationStatus.VALID: "green",
            CitationStatus.NOT_FOUND: "red",
            CitationStatus.MISSING_PROVENANCE: "yellow",
            CitationStatus.STALE: "yellow",
        }[r.status]
        table.add_row(
            r.node_id,
            r.label or "?",
            f"[{style}]{r.status.value}[/{style}]",
            r.details,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# login / logout
# ---------------------------------------------------------------------------
# Replaces four NEO4J_* exports in a shell profile. The password goes to the OS
# keychain, and `--status` answers the question that four config layers create:
# which one is actually supplying the URI.

# Source labels, coloured by how surprising each one is at debug time. An env var
# silently outranking a stored credential is the trap, so it is the loud one.
_SOURCE_STYLES = {
    "env": "yellow",
    "keychain": "green",
    "yaml": "cyan",
    "default": "dim",
}

# Aura refuses connections for up to a minute after an instance is created, and
# the driver error for that is indistinguishable from a wrong URI.
_AURA_WARMUP_HINT = (
    "A freshly created Aura instance can take up to 60 seconds to accept "
    "connections. If it was just created, wait and run this again."
)


def _looks_like_aura(uri: str) -> bool:
    """Whether a URI points at Aura rather than a local or self-hosted instance."""
    return "databases.neo4j.io" in uri or uri.startswith(("neo4j+s://", "bolt+s://"))


def _print_connection_status() -> None:
    """Show which layer supplies each Neo4j field, plus keychain state."""
    from wheeler import credentials
    from wheeler.config import neo4j_sources, shadowed_by_env

    profile = credentials.active_profile()

    table = Table(title=f"Neo4j connection (profile '{profile}')")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Source", no_wrap=True)
    table.add_column("From", style="dim")
    table.add_column("Value")
    for row in neo4j_sources():
        style = _SOURCE_STYLES.get(row.source, "")
        # escape(): a URI can carry square brackets (bolt://[::1]:7687) and rich
        # would read those as markup.
        table.add_row(
            row.field,
            f"[{style}]{row.source}[/{style}]" if style else row.source,
            escape(row.origin),
            escape(row.display),
        )
    console.print(table)
    console.print("[dim]Precedence: env > keychain > wheeler.yaml > default[/dim]")

    available, detail = credentials.keyring_status()
    if available:
        console.print(f"Keychain: [green]available[/green] [dim]({escape(detail)})[/dim]")
        stored = credentials.list_profiles()
        if stored:
            console.print(f"Stored profiles: {', '.join(stored)}")
        else:
            console.print("[dim]No stored profiles. Run: wheeler login --aura-file <path>[/dim]")
    else:
        console.print(f"Keychain: [yellow]unavailable[/yellow] {escape(detail)}")

    shadowed = shadowed_by_env()
    if shadowed:
        # One shadowing variable is the common case, so agreement matters here:
        # the plural-only phrasing reads as a typo exactly when most users see it.
        verb = "overrides" if len(shadowed) == 1 else "override"
        them = "it" if len(shadowed) == 1 else "them"
        console.print(
            f"[yellow]Warning:[/yellow] {', '.join(shadowed)} in the environment "
            f"{verb} the stored credential. Unset {them} to use the keychain."
        )


def _login_from_aura_api():  # noqa: ANN202 (returns aura.AuraCredentials)
    """Power path: OAuth client_credentials, then pick from GET /v1/instances."""
    from wheeler import aura

    console.print(
        "[bold]Aura management API[/bold]\n"
        f"Create a Client ID and Secret at {aura.AURA_CONSOLE_URL} under "
        "Account Details.\n"
        "[dim]There is no browser sign-in flow: client credentials are the only "
        "grant Aura offers.[/dim]"
    )
    client_id = typer.prompt("Aura API Client ID").strip()
    client_secret = typer.prompt("Aura API Client Secret", hide_input=True)

    token = aura.request_token(client_id, client_secret)
    instances = aura.list_instances(token)
    if not instances:
        raise aura.AuraApiError(
            "those credentials see no Aura instances. Create one in the console first."
        )

    if len(instances) == 1:
        chosen = instances[0]
        console.print(f"Using the only instance visible: {escape(chosen.describe())}")
    else:
        console.print(f"\n{len(instances)} instances:")
        for index, inst in enumerate(instances, start=1):
            console.print(f"  {index}. {escape(inst.describe())}")
        pick = typer.prompt("Which instance", default="1")
        try:
            chosen = instances[int(pick) - 1]
        except (ValueError, IndexError):
            raise typer.BadParameter(f"{pick!r} is not one of 1..{len(instances)}") from None

    if not chosen.connection_url:
        raise aura.AuraApiError(
            f"instance {chosen.name or chosen.id} reports no connection_url yet "
            "(it may still be starting)"
        )

    # GET /v1/instances cannot return a password: Aura hands one out only in the
    # POST /v1/instances reply at creation, and never again. So we ask.
    console.print(
        f"\n[dim]The API does not expose instance passwords. Paste the one saved "
        f"when '{chosen.name or chosen.id}' was created.[/dim]"
    )
    password = typer.prompt("Password", hide_input=True)
    username = typer.prompt("Username", default="neo4j").strip()
    database = typer.prompt("Database", default="neo4j").strip()
    return aura.AuraCredentials(
        uri=aura.normalize_uri(chosen.connection_url),
        username=username,
        password=password,
        database=database,
        instance_id=chosen.id,
        instance_name=chosen.name,
    )


def _login_from_prompts(uri: str | None, username: str | None, database: str | None):  # noqa: ANN202
    """Fallback path: type the four fields, password without echo."""
    from wheeler import aura
    from wheeler.config import load_config

    current = load_config().neo4j
    asked_uri = uri or typer.prompt("Neo4j URI", default=current.uri)
    asked_user = username or typer.prompt("Username", default=current.username)
    password = typer.prompt("Password", hide_input=True)
    asked_db = database or typer.prompt("Database", default=current.database)
    return aura.AuraCredentials(
        uri=aura.normalize_uri(asked_uri),
        username=asked_user.strip(),
        password=password,
        database=asked_db.strip(),
    )


@app.command("login")
def cmd_login(
    aura_file: Optional[Path] = typer.Option(
        None,
        "--aura-file",
        help="Aura credentials file to read (the download offered at instance creation).",
    ),
    aura_api: bool = typer.Option(
        False,
        "--aura",
        help="Look the instance up through the Aura management API (needs an API key).",
    ),
    profile: str = typer.Option(
        "",
        "--profile",
        "-p",
        help="Named credential slot, so one machine can hold several instances.",
    ),
    status: bool = typer.Option(
        False,
        "--status",
        help="Report where each Neo4j setting comes from, then exit.",
    ),
    uri: Optional[str] = typer.Option(None, "--uri", help="Skip the URI prompt."),
    username: Optional[str] = typer.Option(None, "--username", help="Skip the username prompt."),
    database: Optional[str] = typer.Option(None, "--database", help="Skip the database prompt."),
) -> None:
    """Store Neo4j credentials in the OS keychain instead of a shell profile.

    Three routes, easiest first:

      wheeler login --aura-file creds.txt   drag in Aura's credentials file
      wheeler login --aura                  look the instance up via the Aura API
      wheeler login                         type the four fields

    The credential is validated by connecting before it is stored, and the
    password is never written to a file or echoed. `--status` shows which of env,
    keychain, wheeler.yaml, or the built-in default is supplying each field.
    """
    from wheeler import aura, credentials
    from wheeler.config import reset_keychain_cache

    if status:
        _print_connection_status()
        return

    if aura_file is not None and aura_api:
        console.print("[red]Pick one of --aura-file or --aura, not both.[/red]")
        raise typer.Exit(2)

    target_profile = profile.strip() or credentials.active_profile()

    available, detail = credentials.keyring_status()
    if not available:
        console.print(f"[red]No usable OS keychain:[/red] {escape(detail)}")
        console.print(
            f"[dim]Install the extra with: {escape(credentials.INSTALL_HINT)}\n"
            "Until then, set NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD / "
            "NEO4J_DATABASE in the environment.[/dim]"
        )
        raise typer.Exit(1)

    try:
        if aura_file is not None:
            creds = aura.parse_credentials_file(aura_file)
            console.print(f"Read credentials for [bold]{escape(creds.label())}[/bold]")
        elif aura_api:
            creds = _login_from_aura_api()
        else:
            creds = _login_from_prompts(uri, username, database)
    except aura.AuraError as exc:
        console.print(f"[red]Login failed:[/red] {escape(str(exc))}")
        raise typer.Exit(1)

    console.print(f"Validating {escape(creds.uri)} as {creds.username!r} ...")
    try:
        detail = aura.validate_connection(
            creds.uri, creds.username, creds.password, creds.database
        )
    except aura.AuraError as exc:
        # Nothing is stored on a failed validation: a saved credential that does
        # not work sends the user debugging Neo4j instead of the credential.
        console.print(f"[red]Not saved.[/red] {escape(str(exc))}")
        if _looks_like_aura(creds.uri):
            # Only for Aura: on a local instance this hint sends the reader
            # looking for a warm-up delay that does not exist.
            console.print(f"[dim]{_AURA_WARMUP_HINT}[/dim]")
        raise typer.Exit(1)
    console.print(f"[green]Connected:[/green] {escape(detail)}")

    try:
        saved = credentials.save(
            target_profile,
            creds.uri,
            creds.username,
            creds.password,
            creds.database,
        )
    except credentials.CredentialStoreError as exc:
        console.print(f"[red]Could not store the credential:[/red] {escape(str(exc))}")
        raise typer.Exit(1)
    reset_keychain_cache()

    console.print(f"[green]Saved to the OS keychain as profile '{saved}'.[/green]")
    if saved != credentials.DEFAULT_PROFILE:
        console.print(
            f"[dim]Select it with: export {credentials.PROFILE_ENV}={saved}[/dim]"
        )
    _print_connection_status()


@app.command("logout")
def cmd_logout(
    profile: str = typer.Option("", "--profile", "-p", help="Profile to forget."),
    all_profiles: bool = typer.Option(
        False, "--all", help="Forget every stored profile."
    ),
) -> None:
    """Remove stored Neo4j credentials from the OS keychain."""
    from wheeler import credentials
    from wheeler.config import reset_keychain_cache

    available, detail = credentials.keyring_status()
    if not available:
        console.print(f"[yellow]Nothing to remove:[/yellow] {detail}")
        return

    targets = (
        credentials.list_profiles()
        if all_profiles
        else [profile.strip() or credentials.active_profile()]
    )
    if not targets:
        console.print("[yellow]No stored profiles.[/yellow]")
        return

    removed = []
    for name in targets:
        try:
            if credentials.delete(name):
                removed.append(name)
        except credentials.CredentialStoreError as exc:
            console.print(f"[red]Could not remove profile '{name}':[/red] {escape(str(exc))}")
            raise typer.Exit(1)
    reset_keychain_cache()

    if removed:
        console.print(f"[green]Removed profile(s):[/green] {', '.join(removed)}")
    else:
        console.print(f"[yellow]Nothing stored for:[/yellow] {', '.join(targets)}")


# ---------------------------------------------------------------------------
# install / uninstall / update / version
# ---------------------------------------------------------------------------


@app.command("install")
def cmd_install(
    link: bool = typer.Option(False, "--link", "-l", help="Symlink instead of copy"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Install even when the wh plugin is present (accepts the shadowing).",
    ),
) -> None:
    """LEGACY: copy slash commands, agents, and MCP servers into ~/.claude/.

    Superseded by the `wh` Claude Code plugin, which serves the same acts
    and updates itself:

        /plugin marketplace add maxwellsdm1867/wheeler
        /plugin install wh@wheeler

    Files written here SHADOW the plugin's acts, so this refuses to run when
    the plugin is present. Use `wheeler migrate-to-plugin` to switch over.
    """
    from wheeler.installer import PluginShadowError, install

    try:
        files = install(link=link, force=force)
        mode = "Linked" if link else "Installed"
        console.print(f"[green]{mode} {len(files)} file(s).[/green]")
        console.print("[green]MCP servers registered in ~/.claude/settings.json.[/green]")
        console.print("[dim]Wheeler works from any directory. Restart Claude Code to connect.[/dim]")
        if force:
            console.print(
                "[yellow]Warning:[/yellow] the wh plugin is present and these files "
                "shadow it. Run [bold]wheeler migrate-to-plugin[/bold] to fix."
            )
    except PluginShadowError as exc:
        console.print("[red]Refusing to install: the wh plugin is already present.[/red]")
        console.print(str(exc))
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Install failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command("uninstall")
def cmd_uninstall() -> None:
    """Remove the legacy Wheeler slash commands and agents from ~/.claude/."""
    from wheeler.installer import (
        detect_plugin,
        legacy_status,
        plugin_advice,
        uninstall,
    )

    try:
        removed = uninstall()
        if removed:
            console.print(f"[green]Removed {len(removed)} file(s):[/green]")
            for rel in removed:
                console.print(f"  {rel}")
        else:
            console.print("[yellow]Nothing to remove (no manifest found).[/yellow]")
        # Say where the acts come from now: the plugin, or nowhere.
        advice = plugin_advice(detect_plugin(), legacy_status())
        if advice:
            console.print()
            console.print(advice)
    except Exception as exc:
        console.print(f"[red]Uninstall failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command("update")
def cmd_update(
    source: str = typer.Option(
        None,
        "--source",
        "-s",
        help="Install source: pypi, github, editable, or uv (auto-detected if omitted)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Upgrade Wheeler (pip or uv, per install source) and reinstall files."""
    import wheeler
    from wheeler.installer import (
        _detect_install_source,
        check_version,
        update,
    )

    old_version = wheeler.__version__
    detected = source or _detect_install_source()

    # Check what's available
    console.print(f"Current version: [bold]{old_version}[/bold]")
    console.print("Checking for updates...")
    _, latest, update_available = check_version()

    if detected == "editable":
        # Editable installs always pull — commits may have new
        # commands/tools without a version bump.
        console.print("Install source: [cyan]editable[/cyan]")
        if latest and update_available:
            console.print(f"New version available: [bold]{latest}[/bold]")
        else:
            console.print("[dim]Pulling latest commits...[/dim]")
    elif latest:
        if not update_available:
            console.print(f"[green]Already up to date ({old_version}).[/green]")
            return
        console.print(f"New version available: [bold]{latest}[/bold]")
        console.print(f"Install source: [cyan]{detected}[/cyan]")
    else:
        console.print("[dim]Could not determine latest version — upgrading anyway.[/dim]")
        console.print(f"Install source: [cyan]{detected}[/cyan]")

    if not yes:
        confirm = typer.confirm("Proceed with update?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    try:
        console.print("Upgrading...")
        new_version = update(source=source)
        console.print(
            f"[green]Updated: {old_version} → {new_version}[/green]"
        )
        # update() refreshes the legacy tree with force=True so an upgrade is
        # never left half-applied. Say so when that tree shadows the plugin.
        from wheeler.installer import detect_plugin, legacy_status

        if detect_plugin().active and legacy_status().present:
            console.print(
                "[yellow]Warning:[/yellow] the wh plugin is installed and the legacy "
                "~/.claude/commands/wh/ tree shadows it.\n"
                "Run [bold]wheeler migrate-to-plugin[/bold] to remove the legacy tree."
            )
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Upgrade failed:[/red] {exc}")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Update failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command("backup")
def cmd_backup(
    destination: Optional[Path] = typer.Option(
        None,
        "--destination",
        "-d",
        help="Directory to write the archive into. Default: <project>/.wheeler/backups/",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to wheeler.yaml. Default: ./wheeler.yaml or built-in defaults.",
    ),
    include_remote: bool = typer.Option(
        False,
        "--include-remote",
        help="Reserved (no-op). Local-only for now; remote destinations TBD.",
    ),
    scope: str = typer.Option(
        "project",
        "--scope",
        help="Scope of the archive: 'project' (default, full project tree) or 'graph-only' (v1-style metadata-only archive).",
    ),
    max_artifact_size: Optional[int] = typer.Option(
        None,
        "--max-artifact-size",
        help="Skip files larger than this many bytes. Skipped files are recorded in the manifest.",
    ),
    allow_secrets: bool = typer.Option(
        False,
        "--allow-secrets",
        help="Override the secret scan and allow API keys in the archive.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the size-readout confirmation prompt.",
    ),
) -> None:
    """Snapshot Wheeler's canonical state to a tar.gz archive.

    Bundles the full project tree (scope=project) or just the Wheeler-managed
    subset (scope=graph-only), plus a JSONL dump of every node and relationship
    in Neo4j, plus a manifest.json describing layout, version, counts, and
    SHA-256 hashes.

    Runs in-process so the MCP transport's ~235k-char tool-result cap does
    not apply: a full graph dump fits easily.

    Scope: 'project' packs the whole project_root tree (default). Use
    'graph-only' for a smaller v1-style metadata-only archive.
    """
    import sys

    from wheeler.backup import BackupAbortedDueToSecrets, create_backup

    if scope not in ("project", "graph-only"):
        console.print("[red]--scope must be 'project' or 'graph-only'[/red]")
        raise typer.Exit(2)

    cfg = load_config(config_path) if config_path else load_config()

    # Confirmation prompt when not skipped and stdin is a TTY.
    if not yes and sys.stdin.isatty():
        import os

        project_root = Path(getattr(cfg, "project_root", ".")).resolve()
        total_size = 0
        total_files = 0
        if scope == "project" and project_root.exists():
            for dirpath, dirnames, filenames in os.walk(project_root):
                # Skip heavy directories that backup also excludes.
                dirnames[:] = [
                    d
                    for d in dirnames
                    if d not in (".git", ".venv", "venv", "__pycache__", "node_modules")
                    and not (Path(dirpath) / d).resolve()
                    == (project_root / ".wheeler" / "backups").resolve()
                ]
                for fname in filenames:
                    fp = Path(dirpath) / fname
                    try:
                        fsize = fp.stat().st_size
                        if max_artifact_size is None or fsize <= max_artifact_size:
                            total_size += fsize
                            total_files += 1
                    except OSError:
                        pass
        size_mb = total_size / (1024 * 1024)
        console.print(
            f"Backup will include approximately [bold]{size_mb:.1f} MB[/bold] "
            f"across [bold]{total_files}[/bold] files. Proceed? [y/N] ",
            end="",
        )
        answer = input().strip().lower()
        if answer not in ("y", "yes"):
            console.print("[yellow]Backup aborted.[/yellow]")
            raise typer.Exit(0)

    try:
        archive = asyncio.run(
            create_backup(
                cfg,
                destination=destination,
                include_remote=include_remote,
                scope=scope,  # type: ignore[arg-type]
                max_artifact_size=max_artifact_size,
                allow_secrets=allow_secrets,
                yes=True,  # prompt already handled above
            )
        )
    except BackupAbortedDueToSecrets as exc:
        console.print("[red]Backup aborted: secrets detected in the project tree.[/red]")
        for offender in exc.offenders[:10]:
            console.print(
                f"  [yellow]{offender['path']}[/yellow]: "
                f"pattern '{offender['pattern']}' matched '{offender['snippet']}'"
            )
        if len(exc.offenders) > 10:
            console.print(f"  ... and {len(exc.offenders) - 10} more.")
        console.print(
            "\nTo override (not recommended), rerun with [bold]--allow-secrets[/bold]."
        )
        raise typer.Exit(2)
    except Exception as exc:
        console.print(f"[red]Backup failed:[/red] {exc}")
        raise typer.Exit(1)

    size_mb = archive.stat().st_size / (1024 * 1024)
    console.print(f"[green]Backup created:[/green] {archive}")
    console.print(f"[dim]Size: {size_mb:.2f} MB[/dim]")

    # Show hand-off hint when the output is a TTY (suppress in piped contexts).
    if sys.stderr.isatty():
        sys.stderr.write(
            f"\n[OK] Archive: {archive} ({size_mb:.2f} MB)\n\n"
            "Hand this archive to the recipient. They run:\n"
            f"  wheeler restore {archive.name} --verify          # check integrity\n"
            f"  wheeler restore {archive.name} --fresh --target ./<dir>   # restore into empty dir\n\n"
            "Full instructions are baked into the archive as HANDOFF.md. To read without extracting:\n"
            f"  tar -xOzf {archive.name} HANDOFF.md | less\n"
        )

    # If --allow-secrets was used and secrets were packed, warn explicitly so
    # the operator cannot overlook the security decision.
    if allow_secrets:
        import tarfile as _tarfile

        try:
            with _tarfile.open(archive, "r:gz") as _tar:
                _mf = _tar.extractfile("manifest.json")
                if _mf is not None:
                    import json as _json

                    _manifest = _json.loads(_mf.read())
                    _allowed = _manifest.get("allowed_secret_files") or []
                    if _allowed:
                        console.print(
                            f"[bold yellow][WARN][/bold yellow] "
                            f"{len(_allowed)} file(s) containing secrets were "
                            "packed because --allow-secrets was set:"
                        )
                        for _entry in _allowed:
                            _pats = ", ".join(_entry.get("patterns") or [])
                            console.print(
                                f"  [yellow]{_entry['path']}[/yellow]"
                                f" (patterns: {_pats})"
                            )
        except Exception:
            pass  # Best-effort: never fail the backup command due to post-scan


@app.command("version")
def cmd_version() -> None:
    """Show installed version and check for updates."""
    from wheeler.installer import check_version

    installed, latest, update_available = check_version()
    console.print(f"Wheeler [bold]{installed}[/bold]")
    if latest:
        if update_available:
            console.print(
                f"[yellow]Update available:[/yellow] {latest} "
                "(run [bold]wheeler update[/bold])"
            )
        else:
            console.print("[green]Up to date.[/green]")
    else:
        console.print("[dim]Could not check PyPI for updates.[/dim]")


# ---------------------------------------------------------------------------
# dev sync
# ---------------------------------------------------------------------------


@dev_app.command("sync")
def cmd_dev_sync() -> None:
    """Sync project slash commands/agents into wheeler/_data/ for packaging."""
    from wheeler.installer import sync_data

    try:
        changed = sync_data()
        if changed:
            console.print(f"[yellow]Synced {len(changed)} out-of-sync file(s):[/yellow]")
            for f in changed:
                console.print(f"  {f}")
        else:
            console.print("[green]All files already in sync.[/green]")
    except Exception as exc:
        console.print(f"[red]Sync failed:[/red] {exc}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@app.command("migrate")
def cmd_migrate(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be migrated without writing files"),
) -> None:
    """Migrate existing graph nodes to knowledge/ JSON files."""
    from wheeler.graph.backend import get_backend
    from wheeler.knowledge.migrate import migrate

    config = load_config()
    backend = get_backend(config)

    async def _run() -> None:
        await backend.initialize()
        try:
            report = await migrate(
                backend,
                project_knowledge_dir(config),
                dry_run=dry_run,
                synthesis_path=project_synthesis_dir(config),
            )
        finally:
            await backend.close()

        # Print report
        if dry_run:
            console.print("[yellow]DRY RUN — no files written[/yellow]")

        table = Table(title="Migration Report")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")
        table.add_row("Migrated", f"[green]{report.migrated}[/green]")
        table.add_row("Skipped (already exist)", str(report.skipped))
        table.add_row("Errors", f"[red]{report.errors}[/red]" if report.errors else "0")
        console.print(table)

        if report.details:
            console.print("\n[bold]Details:[/bold]")
            for detail in report.details:
                console.print(f"  {detail}")

    try:
        asyncio.run(_run())
    except Exception as exc:
        console.print(f"[red]Migration failed:[/red] {exc}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# dashboard
# ---------------------------------------------------------------------------


@dashboard_app.callback(invoke_without_command=True)
def dashboard_main(
    ctx: typer.Context,
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    port: int = typer.Option(8765, "--port", "-p", help="Port to bind."),
    limit: int = typer.Option(12, "--limit", "-l", help="Max items per zone."),
    open_browser: bool = typer.Option(
        True, "--open/--no-open", help="Open the dashboard in a browser."
    ),
) -> None:
    """Serve a live HTML dashboard that re-queries the graph on every load."""
    if ctx.invoked_subcommand is not None:
        return

    from wheeler.dashboard.serve import render_live, serve

    config = load_config()

    # Fail fast with a friendly message if the graph is unreachable, rather than
    # binding a port that only serves error pages.
    try:
        render_live(config, limit)
    except Exception as exc:
        console.print(f"[red]Could not read the graph:[/red] {exc}")
        console.print(
            "[yellow]Is Neo4j running?[/yellow] Check your connection in wheeler.yaml."
        )
        raise typer.Exit(1)

    def _announce(url: str) -> None:
        console.print(f"[green]Dashboard live at[/green] {url}  [dim](Ctrl+C to stop)[/dim]")

    try:
        serve(config, host=host, port=port, limit=limit, open_browser=open_browser, on_start=_announce)
    except OSError as exc:
        console.print(f"[red]Could not start server on {host}:{port}:[/red] {exc}")
        console.print("[yellow]Try a different --port.[/yellow]")
        raise typer.Exit(1)


@dashboard_app.command("pin")
def dashboard_pin(
    figure_id: str = typer.Argument(..., help="Finding/figure id to pin (e.g. F-1a2b)."),
) -> None:
    """Pin a figure as a main (hero) figure on the dashboard."""
    from wheeler.dashboard.gather import read_pins, write_pins

    config = load_config()
    pins = read_pins(config)
    if figure_id in pins:
        console.print(f"[yellow]Already pinned:[/yellow] {figure_id}")
        return
    pins.append(figure_id)
    write_pins(config, pins)
    console.print(f"[green]Pinned:[/green] {figure_id} ({len(pins)} pinned)")


@dashboard_app.command("unpin")
def dashboard_unpin(
    figure_id: str = typer.Argument(..., help="Figure id to unpin."),
) -> None:
    """Remove a figure from the main (hero) figures."""
    from wheeler.dashboard.gather import read_pins, write_pins

    config = load_config()
    pins = read_pins(config)
    if figure_id not in pins:
        console.print(f"[yellow]Not pinned:[/yellow] {figure_id}")
        return
    pins = [p for p in pins if p != figure_id]
    write_pins(config, pins)
    console.print(f"[green]Unpinned:[/green] {figure_id} ({len(pins)} pinned)")


@dashboard_app.command("pins")
def dashboard_pins() -> None:
    """List the currently pinned figures."""
    from wheeler.dashboard.gather import read_pins

    config = load_config()
    pins = read_pins(config)
    if not pins:
        console.print("[yellow]No pinned figures.[/yellow]")
        return
    for i, p in enumerate(pins, start=1):
        console.print(f"  {i}. {p}")


@dashboard_app.command("note")
def dashboard_note(
    figure_id: str = typer.Argument(..., help="Figure id to annotate (e.g. F-1a2b)."),
    text: str = typer.Argument(..., help="Note text."),
) -> None:
    """Record a durable note on a figure as a provenance-tracked ResearchNote.

    Creates a ResearchNote (N-) linked RELEVANT_TO the figure, via the same
    add_note path as wh:note, so the note lives in the graph and travels with
    backups. Shown under the figure on the dashboard.
    """
    from wheeler.dashboard.gather import record_figure_note

    config = load_config()
    if not text.strip():
        console.print("[yellow]Provide note text to record.[/yellow]")
        raise typer.Exit(1)
    try:
        note_id = asyncio.run(record_figure_note(config, figure_id, text))
    except Exception as exc:
        console.print(f"[red]Could not record note:[/red] {exc}")
        raise typer.Exit(1)
    if not note_id:
        console.print("[red]Note was not created.[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Recorded[/green] {note_id} (ResearchNote) linked to {figure_id}")


@dashboard_app.command("notes")
def dashboard_notes() -> None:
    """List figure notes (ResearchNotes linked to figures) from the graph."""
    from wheeler.dashboard.gather import list_all_figure_notes

    config = load_config()
    try:
        rows = asyncio.run(list_all_figure_notes(config))
    except Exception as exc:
        console.print(f"[red]Could not read notes:[/red] {exc}")
        raise typer.Exit(1)
    if not rows:
        console.print("[yellow]No figure notes.[/yellow]")
        return
    for r in rows:
        content = str(r.get("content", ""))
        snippet = content if len(content) <= 70 else content[:70] + "..."
        console.print(f"  {r.get('nid')} -> {r.get('fid')}: {snippet}")


# ---------------------------------------------------------------------------
# restore
# ---------------------------------------------------------------------------


@app.command("restore")
def cmd_restore(
    archive_path: Path = typer.Argument(..., help="Path to backup archive (tar.gz)"),
    verify: bool = typer.Option(
        False, "--verify", help="Verify restorability without applying changes"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Alias for --verify"
    ),
    keep_scratch: bool = typer.Option(
        False,
        "--keep-scratch",
        help="Skip cleanup of the scratch namespace (debugging, used with --verify)",
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to wheeler.yaml"
    ),
    fresh: bool = typer.Option(
        False,
        "--fresh",
        help="Restore archive into a fresh (empty or clean) target directory.",
    ),
    merge: bool = typer.Option(
        False,
        "--merge",
        help="Merge archive nodes into the current project (conflict policy governs collisions).",
    ),
    target: Optional[Path] = typer.Option(
        None,
        "--target",
        help="Recipient project root. Required with --fresh.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow --fresh into a non-clean target directory.",
    ),
    accept_signature_mismatch: bool = typer.Option(
        False,
        "--accept-signature-mismatch",
        help="Bypass the manifest signature gate (not recommended).",
    ),
    conflict: str = typer.Option(
        "skip",
        "--conflict",
        help="Conflict policy for --merge: skip, replace, or prefix.",
    ),
    prefix: Optional[str] = typer.Option(
        None,
        "--prefix",
        help="ID prefix for incoming nodes when --conflict=prefix.",
    ),
    neo4j_uri: Optional[str] = typer.Option(
        None,
        "--neo4j-uri",
        help="Override Neo4j URI for the recipient project.",
    ),
    neo4j_password: Optional[str] = typer.Option(
        None,
        "--neo4j-password",
        help="Override Neo4j password for the recipient project.",
    ),
    neo4j_database: Optional[str] = typer.Option(
        None,
        "--neo4j-database",
        help="Override Neo4j database name for the recipient project.",
    ),
    project_tag: Optional[str] = typer.Option(
        None,
        "--project-tag",
        help="Override project_tag for the recipient project.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Non-interactive mode: skip confirmation prompts.",
    ),
) -> None:
    """Restore from a backup archive.

    Three modes are supported:

    --verify (or --dry-run): Replay the archive into an isolated scratch
    namespace inside Neo4j, compare against the manifest, then delete the
    scratch namespace. Live data is never touched.

    --fresh --target DIR: Extract the full project tree and replay all
    graph nodes and relationships into a fresh (empty or clean) target
    directory. Requires manifest_version >= 2 (v2 archives).

    --merge: Merge archive nodes into the current (possibly populated)
    project. Conflict policy is governed by --conflict (skip, replace,
    or prefix). Requires manifest_version >= 2 (v2 archives).

    Config overrides (--neo4j-uri, --neo4j-password, --neo4j-database,
    --project-tag) are applied to the recipient's wheeler.yaml before
    graph replay begins.

    An Execution(kind="restore") node is added to the graph and
    .wheeler/restore_log.jsonl is appended on success.
    """
    import sys

    # Enforce mode mutex.
    modes_set = sum([bool(verify or dry_run), bool(fresh), bool(merge)])
    if modes_set > 1:
        console.print(
            "[red]--verify, --fresh, and --merge are mutually exclusive. "
            "Specify exactly one mode.[/red]"
        )
        raise typer.Exit(2)
    if modes_set == 0:
        # Default to verify for backward compatibility.
        verify = True

    cfg = load_config(config_path) if config_path else load_config()

    if verify or dry_run:
        from wheeler.restore import RestoreVerifyError, verify_backup

        try:
            result = asyncio.run(
                verify_backup(cfg, archive_path, keep_scratch=keep_scratch)
            )
        except RestoreVerifyError as exc:
            console.print(f"[red]Restore-verify aborted (safety check):[/red] {exc}")
            raise typer.Exit(1)
        except Exception as exc:
            console.print(f"[red]Restore-verify failed:[/red] {exc}")
            raise typer.Exit(1)

        verdict = result["verdict"]
        color = "green" if verdict == "PASS" else "red"
        console.print(f"[{color}]Verdict: {verdict}[/{color}]")
        console.print(f"[dim]Archive: {result['archive_path']}[/dim]")
        console.print(f"[dim]Scratch tag: {result['scratch_tag']}[/dim]")

        for check in result["checks"]:
            cresult = check["result"]
            cstyle = "green" if cresult == "PASS" else "red"
            console.print(
                f"  [{cstyle}][{cresult}][/{cstyle}] "
                f"{check['name']}: {check['detail']}"
            )

        if verdict == "FAIL":
            if result.get("first_failure"):
                console.print(f"\n[red]First failure:[/red] {result['first_failure']}")
            raise typer.Exit(1)

        # PASS: show next-step hints when the output is a TTY.
        if sys.stderr.isatty():
            archive_name = Path(result.get("archive_path", "")).name or str(archive_path)
            sys.stderr.write(
                "\n[OK] Archive is intact.\n\n"
                "To restore into a fresh directory:\n"
                f"  wheeler restore {archive_name} --fresh --target ./<dir>\n\n"
                "Or read the bundled instructions:\n"
                f"  tar -xOzf {archive_name} HANDOFF.md\n"
            )

    elif fresh:
        if target is None:
            console.print("[red]--target DIR is required with --fresh.[/red]")
            raise typer.Exit(2)

        from wheeler.restore import restore_fresh

        try:
            result = asyncio.run(
                restore_fresh(
                    cfg,
                    archive_path,
                    target,
                    force=force,
                    accept_signature_mismatch=accept_signature_mismatch,
                    neo4j_uri=neo4j_uri,
                    neo4j_password=neo4j_password,
                    neo4j_database=neo4j_database,
                    project_tag=project_tag,
                )
            )
        except Exception as exc:
            console.print(f"[red]Restore (fresh) failed:[/red] {exc}")
            raise typer.Exit(1)

        if result.get("status") == "error":
            console.print(f"[red]Restore (fresh) refused:[/red] {result.get('error', 'unknown error')}")
            for w in result.get("warnings", []):
                console.print(f"[yellow]  Warning: {w}[/yellow]")
            raise typer.Exit(1)

        console.print("[green]Restore complete.[/green]")
        console.print(f"  Target root:            {result.get('target_root')}")
        console.print(f"  Archive UUID:           {result.get('archive_uuid')}")
        console.print(f"  Nodes restored:         {result.get('nodes_restored', 0)}")
        console.print(f"  Relationships restored: {result.get('relationships_restored', 0)}")
        console.print(f"  Failures:               {result.get('restore_failures', [])!r}" if result.get('restore_failures') else "  Failures:               0")
        ext = result.get("externally_rooted_paths", [])
        if ext:
            console.print(
                f"[yellow]  Heads up: {len(ext)} node(s) point at paths outside the archive. "
                "They are listed in .wheeler/restore_log.jsonl.[/yellow]"
            )
        for w in result.get("warnings", []):
            console.print(f"[yellow]  Warning: {w}[/yellow]")

    elif merge:
        if conflict not in ("skip", "replace", "prefix"):
            console.print("[red]--conflict must be skip, replace, or prefix.[/red]")
            raise typer.Exit(2)
        if conflict == "prefix" and not prefix:
            console.print("[red]--prefix STR is required when --conflict=prefix.[/red]")
            raise typer.Exit(2)

        from wheeler.restore import restore_merge

        try:
            result = asyncio.run(
                restore_merge(
                    cfg,
                    archive_path,
                    conflict_policy=conflict,  # type: ignore[arg-type]
                    prefix=prefix,
                    accept_signature_mismatch=accept_signature_mismatch,
                    neo4j_uri=neo4j_uri,
                    neo4j_password=neo4j_password,
                    neo4j_database=neo4j_database,
                    project_tag=project_tag,
                )
            )
        except Exception as exc:
            console.print(f"[red]Restore (merge) failed:[/red] {exc}")
            raise typer.Exit(1)

        if result.get("status") == "error":
            console.print(f"[red]Restore (merge) refused:[/red] {result.get('error', 'unknown error')}")
            for w in result.get("warnings", []):
                console.print(f"[yellow]  Warning: {w}[/yellow]")
            raise typer.Exit(1)

        console.print("[green]Merge complete.[/green]")
        console.print(f"  Archive UUID:           {result.get('archive_uuid')}")
        console.print(f"  Nodes restored:         {result.get('nodes_restored', 0)}")
        console.print(f"  Relationships restored: {result.get('relationships_restored', 0)}")
        console.print(f"  Skipped (conflict):     {result.get('skipped', 0)}")
        console.print(f"  Replaced:               {result.get('replaced', 0)}")
        console.print(f"  Prefixed:               {result.get('prefixed', 0)}")
        console.print(f"  Failures:               {len(result.get('restore_failures', []))}")
        ext = result.get("externally_rooted_paths", [])
        if ext:
            console.print(
                f"[yellow]  Heads up: {len(ext)} node(s) point at paths outside the archive. "
                "They are listed in .wheeler/restore_log.jsonl.[/yellow]"
            )
        for w in result.get("warnings", []):
            console.print(f"[yellow]  Warning: {w}[/yellow]")


@app.command("show")
def cmd_show(
    node_id: str = typer.Argument(help="Node ID (e.g., F-3a2b)"),
    raw: bool = typer.Option(False, "--raw", help="Show raw JSON instead of markdown"),
) -> None:
    """Display a knowledge node as formatted markdown."""
    from wheeler.knowledge import render, store

    config = load_config()
    knowledge_path = project_knowledge_dir(config)

    try:
        model = store.read_node(knowledge_path, node_id)
    except FileNotFoundError:
        console.print(f"[red]Node not found:[/red] {node_id}")
        raise typer.Exit(1)

    if raw:
        console.print_json(model.model_dump_json(indent=2))
    else:
        md = render.render_node(model)
        console.print(Markdown(md))


if __name__ == "__main__":
    app()
