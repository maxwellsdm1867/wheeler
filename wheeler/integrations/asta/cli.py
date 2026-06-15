"""Typer sub-app: ``wheeler integrate``.

One verb only: ``ingest <tool> <artifact.json> [--link-to ID]``. The act
shells out to the asta CLI, then calls this verb to marshal the result into
the graph. There is deliberately no send/dispatch verb (that would make
Wheeler a second router that invokes Asta).
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import typer

logger = logging.getLogger(__name__)

integrate_app = typer.Typer(help="Ingest external-tool artifacts into the knowledge graph.")

# Registry of supported tool names (normalized lower-case). Each maps to a
# marshal-out ingest function dispatched below.
_INGESTERS = {"paper_finder", "paper-finder", "theorizer"}


@integrate_app.command("ingest")
def ingest(
    tool: str = typer.Argument(..., help="Tool name (e.g. paper_finder)."),
    artifact: Path = typer.Argument(..., help="Path to the tool's -o JSON artifact."),
    link_to: Optional[str] = typer.Option(
        None, "--link-to", help="Node id (Plan/Question) to link each result RELEVANT_TO."
    ),
) -> None:
    """Marshal an external-tool artifact into the Wheeler knowledge graph."""
    tool_key = tool.strip().lower()
    if tool_key not in _INGESTERS:
        typer.echo(
            f"Unknown tool '{tool}'. Supported: paper_finder, theorizer.", err=True
        )
        raise typer.Exit(code=2)

    if not artifact.exists():
        typer.echo(f"Artifact not found: {artifact}", err=True)
        raise typer.Exit(code=2)

    try:
        doc = json.loads(artifact.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        typer.echo(f"Could not read artifact {artifact}: {exc}", err=True)
        raise typer.Exit(code=2)

    from wheeler.config import load_config

    config = load_config()

    if tool_key == "theorizer":
        from wheeler.integrations.asta.theorizer import ingest_theorizer

        report = asyncio.run(
            ingest_theorizer(
                doc, link_to=link_to, config=config, artifact_path=str(artifact)
            )
        )
    else:
        from wheeler.integrations.asta.ingest import ingest_paper_finder

        report = asyncio.run(
            ingest_paper_finder(
                doc, link_to=link_to, config=config, artifact_path=str(artifact)
            )
        )

    typer.echo(
        f"created={report.created} deduped={report.deduped} "
        f"linked={report.linked} skipped={report.skipped} "
        f"execution={report.execution_id or '-'}"
    )
    if report.paper_ids:
        typer.echo("papers: " + ", ".join(report.paper_ids))
