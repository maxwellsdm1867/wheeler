"""wheeler-tools CLI: deterministic graph and validation commands."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from wheeler.config import load_config
from wheeler.graph.driver import get_sync_driver
from wheeler.graph.schema import (
    ALLOWED_RELATIONSHIPS,
    PREFIX_TO_LABEL,
    generate_node_id,
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



# Re-export for backward compatibility and convenience
_generate_id = generate_node_id


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


@graph_app.command("add-finding")
def graph_add_finding(
    desc: str = typer.Option(..., "--desc", "-d", help="Finding description"),
    confidence: float = typer.Option(
        ..., "--confidence", "-c", help="Confidence score (0.0-1.0)"
    ),
) -> None:
    """Add a Finding node to the knowledge graph."""


    config = load_config()
    node_id = _generate_id("F")
    now = datetime.now(timezone.utc).isoformat()

    driver = get_sync_driver(config)
    try:
        with driver.session(database=config.neo4j.database) as session:
            props: dict = {
                "id": node_id,
                "description": desc,
                "confidence": confidence,
                "date": now,
            }
            if config.neo4j.project_tag:
                props["_wheeler_project"] = config.neo4j.project_tag
            prop_assignments = ", ".join(f"{k}: $props.{k}" for k in props)
            session.run(
                f"CREATE (f:Finding {{{prop_assignments}}})",
                props=props,
            )
        console.print(f"[green]Created Finding:[/green] [{node_id}] {desc}")
    except Exception as exc:
        console.print(f"[red]Failed:[/red] {exc}")
        raise typer.Exit(1)
    finally:
        driver.close()


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


    config = load_config()
    node_id = _generate_id("Q")
    now = datetime.now(timezone.utc).isoformat()

    driver = get_sync_driver(config)
    try:
        with driver.session(database=config.neo4j.database) as session:
            props: dict = {
                "id": node_id,
                "question": question,
                "priority": priority,
                "date_added": now,
            }
            if config.neo4j.project_tag:
                props["_wheeler_project"] = config.neo4j.project_tag
            prop_assignments = ", ".join(f"{k}: $props.{k}" for k in props)
            session.run(
                f"CREATE (q:OpenQuestion {{{prop_assignments}}})",
                props=props,
            )
        console.print(f"[green]Created OpenQuestion:[/green] [{node_id}] {question}")
    except Exception as exc:
        console.print(f"[red]Failed:[/red] {exc}")
        raise typer.Exit(1)
    finally:
        driver.close()


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



    config = load_config()

    # Determine labels from IDs
    src_prefix = source.split("-", 1)[0]
    tgt_prefix = target.split("-", 1)[0]
    src_label = PREFIX_TO_LABEL.get(src_prefix)
    tgt_label = PREFIX_TO_LABEL.get(tgt_prefix)

    if not src_label or not tgt_label:
        console.print("[red]Could not determine node labels from IDs.[/red]")
        raise typer.Exit(1)

    driver = get_sync_driver(config)
    try:
        with driver.session(database=config.neo4j.database) as session:
            # Use parameterized query — rel_type is whitelisted above
            params: dict = {"src": source, "tgt": target}
            if config.neo4j.project_tag:
                stmt = (
                    f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
                    f"WHERE a._wheeler_project = $ptag AND b._wheeler_project = $ptag "
                    f"CREATE (a)-[r:{rel_type}]->(b) RETURN type(r) AS rel"
                )
                params["ptag"] = config.neo4j.project_tag
            else:
                stmt = (
                    f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
                    f"CREATE (a)-[r:{rel_type}]->(b) RETURN type(r) AS rel"
                )
            result = session.run(stmt, **params)
            record = result.single()
            if record:
                console.print(
                    f"[green]Linked:[/green] [{source}] -[{rel_type}]-> [{target}]"
                )
            else:
                console.print("[red]One or both nodes not found.[/red]")
                raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Failed:[/red] {exc}")
        raise typer.Exit(1)
    finally:
        driver.close()


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
    from pathlib import Path as P

    from wheeler.graph.migration_prov import (
        migrate_analysis_nodes,
        migrate_knowledge_files,
        rename_relationships,
    )

    config = load_config()
    knowledge_path = P(config.knowledge_path)

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
# install / uninstall / update / version
# ---------------------------------------------------------------------------


@app.command("install")
def cmd_install(
    link: bool = typer.Option(False, "--link", "-l", help="Symlink instead of copy"),
) -> None:
    """Install Wheeler slash commands, agents, and MCP servers to ~/.claude/."""
    from wheeler.installer import install

    try:
        files = install(link=link)
        mode = "Linked" if link else "Installed"
        console.print(f"[green]{mode} {len(files)} file(s).[/green]")
        console.print("[green]MCP servers registered in ~/.claude/settings.json.[/green]")
        console.print("[dim]Wheeler works from any directory. Restart Claude Code to connect.[/dim]")
    except Exception as exc:
        console.print(f"[red]Install failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command("uninstall")
def cmd_uninstall() -> None:
    """Remove Wheeler slash commands and agents from ~/.claude/."""
    from wheeler.installer import uninstall

    try:
        removed = uninstall()
        if removed:
            console.print(f"[green]Removed {len(removed)} file(s):[/green]")
            for rel in removed:
                console.print(f"  {rel}")
        else:
            console.print("[yellow]Nothing to remove (no manifest found).[/yellow]")
    except Exception as exc:
        console.print(f"[red]Uninstall failed:[/red] {exc}")
        raise typer.Exit(1)


@app.command("update")
def cmd_update(
    source: str = typer.Option(
        None,
        "--source",
        "-s",
        help="Install source: pypi, github, or editable (auto-detected if omitted)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Upgrade Wheeler via pip and reinstall files."""
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
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]pip upgrade failed:[/red] {exc}")
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
    from pathlib import Path

    from wheeler.graph.backend import get_backend
    from wheeler.knowledge.migrate import migrate

    config = load_config()
    backend = get_backend(config)

    async def _run() -> None:
        await backend.initialize()
        try:
            report = await migrate(backend, Path(config.knowledge_path), dry_run=dry_run)
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
    from pathlib import Path

    from wheeler.knowledge import render, store

    config = load_config()
    knowledge_path = Path(config.knowledge_path)

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
