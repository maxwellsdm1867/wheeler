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
