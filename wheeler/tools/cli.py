"""wheeler-tools CLI: deterministic graph and validation commands."""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.table import Table

from wheeler.config import load_config
from wheeler.graph.schema import (
    ALLOWED_RELATIONSHIPS,
    LABEL_TO_PREFIX,
    PREFIX_TO_LABEL,
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


def _generate_id(prefix: str) -> str:
    """Generate a short hex ID with the given prefix."""
    return f"{prefix}-{secrets.token_hex(4)}"


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
    from neo4j import GraphDatabase

    config = load_config()
    node_id = _generate_id("F")
    now = datetime.now(timezone.utc).isoformat()

    driver = GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
    )
    try:
        with driver.session(database=config.neo4j.database) as session:
            session.run(
                "CREATE (f:Finding {id: $id, description: $desc, "
                "confidence: $confidence, date: $date})",
                id=node_id,
                desc=desc,
                confidence=confidence,
                date=now,
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
    from neo4j import GraphDatabase

    config = load_config()
    node_id = _generate_id("Q")
    now = datetime.now(timezone.utc).isoformat()

    driver = GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
    )
    try:
        with driver.session(database=config.neo4j.database) as session:
            session.run(
                "CREATE (q:OpenQuestion {id: $id, question: $question, "
                "priority: $priority, date_added: $date})",
                id=node_id,
                question=question,
                priority=priority,
                date=now,
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

    from neo4j import GraphDatabase

    config = load_config()

    # Determine labels from IDs
    src_prefix = source.split("-", 1)[0]
    tgt_prefix = target.split("-", 1)[0]
    src_label = PREFIX_TO_LABEL.get(src_prefix)
    tgt_label = PREFIX_TO_LABEL.get(tgt_prefix)

    if not src_label or not tgt_label:
        console.print("[red]Could not determine node labels from IDs.[/red]")
        raise typer.Exit(1)

    driver = GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
    )
    try:
        with driver.session(database=config.neo4j.database) as session:
            # Use parameterized query — rel_type is whitelisted above
            result = session.run(
                f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
                f"CREATE (a)-[r:{rel_type}]->(b) RETURN type(r) AS rel",
                src=source,
                tgt=target,
            )
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
    """Detect Analysis nodes with stale script hashes."""
    from wheeler.graph.provenance import detect_stale_analyses

    config = load_config()
    try:
        stale = asyncio.run(detect_stale_analyses(config))
    except Exception as exc:
        console.print(f"[red]Failed to detect stale analyses:[/red] {exc}")
        raise typer.Exit(1)

    if not stale:
        console.print("[green]No stale analyses found.[/green]")
        return

    table = Table(title="Stale Analyses")
    table.add_column("Node ID", style="cyan")
    table.add_column("Script Path")
    table.add_column("Status", style="yellow")
    table.add_column("Executed At")

    for s in stale:
        status = "FILE MISSING" if s.current_hash == "FILE_NOT_FOUND" else "HASH CHANGED"
        table.add_row(s.node_id, s.script_path, status, s.executed_at or "unknown")
    console.print(table)


# ---------------------------------------------------------------------------
# graph add-analysis
# ---------------------------------------------------------------------------


@graph_app.command("add-analysis")
def graph_add_analysis(
    script: str = typer.Option(..., "--script", "-s", help="Path to analysis script"),
    language: str = typer.Option(..., "--language", "-l", help="Language (e.g., matlab, python)"),
    version: str = typer.Option("", "--version", "-v", help="Language version"),
    params: str = typer.Option("", "--params", "-p", help="Parameters used"),
    output: str = typer.Option("", "--output", "-o", help="Path to output file"),
) -> None:
    """Add an Analysis node with provenance tracking."""
    from pathlib import Path as P
    from wheeler.graph.provenance import AnalysisProvenance, create_analysis_node, hash_file

    config = load_config()
    script_path = P(script)
    if not script_path.exists():
        console.print(f"[red]Script not found:[/red] {script}")
        raise typer.Exit(1)

    script_hash = hash_file(script_path)
    output_hash = ""
    if output:
        output_path = P(output)
        if output_path.exists():
            output_hash = hash_file(output_path)

    prov = AnalysisProvenance(
        script_path=str(script_path.resolve()),
        script_hash=script_hash,
        language=language,
        language_version=version,
        parameters=params,
        output_path=output,
        output_hash=output_hash,
    )

    try:
        node_id = asyncio.run(create_analysis_node(prov, config))
        console.print(
            f"[green]Created Analysis:[/green] [{node_id}]\n"
            f"  Script: {script} (SHA-256: {script_hash[:12]}...)\n"
            f"  Language: {language} {version}"
        )
    except Exception as exc:
        console.print(f"[red]Failed:[/red] {exc}")
        raise typer.Exit(1)


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


if __name__ == "__main__":
    app()
