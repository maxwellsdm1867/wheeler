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
# marshal-out ingest function dispatched below. ``s2`` is a short alias for
# semantic_scholar.
_INGESTERS = {
    "paper_finder",
    "paper-finder",
    "theorizer",
    "semantic_scholar",
    "semantic-scholar",
    "s2",
    "scholar_qa",
    "scholar-qa",
    "literature-report",
    "discover",
    "assistant",
    "asta-assistant",
    "research-assistant",
}

# Tools whose deliverable is a MARKDOWN document, not a JSON ``-o`` artifact. The
# ingest verb reads these as text (not json.loads) and dispatches to the markdown
# ingest path. Asta Literature Reports is the first such tool.
_MARKDOWN_TOOLS = {"scholar_qa", "scholar-qa", "literature-report"}

# The kind + service tag recorded for a FAILED attempt of each tool (the
# record-failure verb writes a failed Execution when the external CLI produced no
# usable artifact). Keyed on the normalized tool name.
_FAILURE_META = {
    "paper_finder": ("paper-search", "asta:paper-finder"),
    "paper-finder": ("paper-search", "asta:paper-finder"),
    "theorizer": ("theory-generation", "asta:theorizer"),
    "semantic_scholar": ("paper-lookup", "asta:semantic-scholar"),
    "semantic-scholar": ("paper-lookup", "asta:semantic-scholar"),
    "s2": ("paper-lookup", "asta:semantic-scholar"),
    "scholar_qa": ("literature-report", "asta:scholar-qa"),
    "scholar-qa": ("literature-report", "asta:scholar-qa"),
    "literature-report": ("literature-report", "asta:scholar-qa"),
    "discover": ("equation-discovery", "llmsr:discover"),
    "assistant": ("research-assistant", "asta:assistant"),
    "asta-assistant": ("research-assistant", "asta:assistant"),
    "research-assistant": ("research-assistant", "asta:assistant"),
}

# Tools whose artifact is a DIRECTORY (a mission project tree), not a single
# file. The ingest verb passes the directory path straight through to the
# directory-walking ingest rather than reading it as text or JSON. The Asta
# Research Assistant is the first such tool.
_DIRECTORY_TOOLS = {"assistant", "asta-assistant", "research-assistant"}


def _echo_report(report) -> None:
    """Print an ingest summary, surfacing a failed / partial run honestly."""
    typer.echo(
        f"created={report.created} deduped={report.deduped} "
        f"linked={report.linked} skipped={report.skipped} used={report.used} "
        f"execution={report.execution_id or '-'}"
    )
    if report.failed:
        # Honest signal: the job did not complete; no outputs were fabricated.
        # The reason (the server's own message when it sent one, else the
        # job_outcome fallback) rides along so the caller can tell auth from
        # quota from a transient server error without querying custom_error.
        # On stderr: it is a diagnostic, not part of the machine-read summary.
        reason = report.error_reason
        typer.echo(
            f"FAILED: job did not complete (state={report.job_state or 'unknown'}"
            f"{', reason: ' + reason if reason else ''}). "
            "The Execution is recorded as failed; no outputs were ingested.",
            err=True,
        )
    if report.artifact:
        typer.echo(f"artifact: {report.artifact}")
    if report.paper_ids:
        typer.echo("papers: " + ", ".join(report.paper_ids))


@integrate_app.command("record-failure")
def record_failure(
    tool: str = typer.Argument(..., help="Tool name whose run failed."),
    reason: str = typer.Option(
        "external service call failed",
        "--reason",
        help="Short reason (e.g. the CLI stderr) stamped on the failed Execution.",
    ),
    link_to: Optional[str] = typer.Option(
        None, "--link-to", help="Node id (Plan/Question) the failed run AROSE_FROM."
    ),
    used: Optional[str] = typer.Option(
        None, "--used", help="Comma-separated graph node ids the request was built FROM."
    ),
    session_id: Optional[str] = typer.Option(
        None,
        "--session-id",
        help="Stable run key so the failed Execution dedupes with a later retry.",
    ),
) -> None:
    """Record a FAILED external-service attempt that produced no artifact.

    The marshal-in act calls this when the external CLI exits non-zero or returns
    no usable artifact: the transport returns nothing, so the ingest is never
    reached and the attempt would otherwise leave NO trace. This writes a visible,
    queryable failed Execution (status="failed", service-tagged, reason in
    custom_error), wired to its inputs (USED) and Plan (AROSE_FROM). Idempotent on
    (service, session_id), so a retry of the same logical run reuses it.
    """
    tool_key = tool.strip().lower()
    if tool_key not in _FAILURE_META:
        typer.echo(
            f"Unknown tool '{tool}'. Supported: {', '.join(sorted(_INGESTERS))}.",
            err=True,
        )
        raise typer.Exit(code=2)
    kind, service = _FAILURE_META[tool_key]

    from wheeler.config import load_config

    config = load_config()
    parsed_used = [i.strip() for i in used.split(",") if i.strip()] if used else []
    sid = (session_id or "").strip() or f"failed-{abs(hash(reason)) & 0xffffffff:08x}"

    async def _do():
        # One event loop: get the backend and write the failed Execution together
        # (a nested asyncio.run would bind the backend to a closed loop).
        from wheeler.integrations.asta._marshal import record_failed_execution
        from wheeler.tools.graph_tools import _get_backend

        backend = await _get_backend(config)
        return await record_failed_execution(
            backend=backend,
            config=config,
            service=service,
            session_id=sid,
            kind=kind,
            description=f"{service} FAILED: {reason}",
            reason=reason,
            link_to=link_to,
            used_inputs=parsed_used or None,
        )

    report = asyncio.run(_do())
    typer.echo(
        f"recorded failed execution={report.execution_id or '-'} "
        f"(state={report.job_state}, used={report.used})"
    )


@integrate_app.command("ingest")
def ingest(
    tool: str = typer.Argument(..., help="Tool name (e.g. paper_finder)."),
    artifact: Path = typer.Argument(..., help="Path to the tool's -o JSON artifact."),
    link_to: Optional[str] = typer.Option(
        None, "--link-to", help="Node id (Plan/Question) to link each result RELEVANT_TO."
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        help=(
            "Cited paper for a semantic_scholar citations artifact (a corpus_id "
            "or a P-id). Each citing paper links CITES it. Ignored otherwise."
        ),
    ),
    used: Optional[str] = typer.Option(
        None,
        "--used",
        help=(
            "Comma-separated graph node ids the request was built FROM (the "
            "question/plan, the seeded Finding ids). The run Execution USED "
            "each one that exists in the graph (input-side provenance)."
        ),
    ),
    find_results: Optional[Path] = typer.Option(
        None,
        "--find-results",
        help=(
            "For a literature report (scholar-qa): the underlying "
            "LiteratureSearchResult JSON (asta literature find -o), used to "
            "enrich each cited paper's metadata by corpus_id. Ignored otherwise."
        ),
    ),
) -> None:
    """Marshal an external-tool artifact into the Wheeler knowledge graph."""
    tool_key = tool.strip().lower()
    if tool_key not in _INGESTERS:
        typer.echo(
            f"Unknown tool '{tool}'. Supported: paper_finder, theorizer, "
            "semantic_scholar (alias s2), scholar_qa (alias literature-report).",
            err=True,
        )
        raise typer.Exit(code=2)

    if not artifact.exists():
        typer.echo(f"Artifact not found: {artifact}", err=True)
        raise typer.Exit(code=2)

    from wheeler.config import load_config

    config = load_config()

    # Comma-separated node ids the request was marshalled in FROM. Trimmed and
    # blanks dropped; the run Execution USED each existing one (input-side
    # provenance). Normalized to None when the parse yields nothing (whether the
    # flag was absent, empty, or all-blank like "   " / ",,,"), so the
    # no-USED-edges path is reached identically rather than passing an empty list.
    _parsed_used = [i.strip() for i in used.split(",") if i.strip()] if used else []
    used_inputs = _parsed_used or None

    # The Asta Research Assistant deliverable is a DIRECTORY (a mission project
    # tree: project.md + work/<slug>/README.md + work/<slug>/data/), not a single
    # file. Pass the directory (or a project.md path) straight to the
    # directory-walking harvest, before any read-as-text/json.
    if tool_key in _DIRECTORY_TOOLS:
        from wheeler.integrations.asta.assistant import ingest_assistant

        report = asyncio.run(
            ingest_assistant(
                str(artifact),
                link_to=link_to,
                config=config,
                used_inputs=used_inputs,
            )
        )
        _echo_report(report)
        return

    # A literature report is MARKDOWN, not a JSON artifact: read it as text and
    # dispatch to the markdown ingest path. The optional --find-results JSON is
    # parsed for paper-metadata enrichment.
    if tool_key in _MARKDOWN_TOOLS:
        try:
            report_markdown = artifact.read_text()
        except OSError as exc:
            typer.echo(f"Could not read report {artifact}: {exc}", err=True)
            raise typer.Exit(code=2)
        find_doc = None
        if find_results is not None:
            if not find_results.exists():
                typer.echo(
                    f"--find-results file not found: {find_results}", err=True
                )
                raise typer.Exit(code=2)
            try:
                find_doc = json.loads(find_results.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                typer.echo(
                    f"Could not read --find-results {find_results}: {exc}", err=True
                )
                raise typer.Exit(code=2)

        from wheeler.integrations.asta.scholar_qa import ingest_scholar_qa

        report = asyncio.run(
            ingest_scholar_qa(
                report_markdown,
                report_path=str(artifact),
                find_results=find_doc,
                link_to=link_to,
                config=config,
                used_inputs=used_inputs,
            )
        )
        _echo_report(report)
        return

    try:
        doc = json.loads(artifact.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        typer.echo(f"Could not read artifact {artifact}: {exc}", err=True)
        raise typer.Exit(code=2)

    if tool_key == "theorizer":
        from wheeler.integrations.asta.theorizer import ingest_theorizer

        report = asyncio.run(
            ingest_theorizer(
                doc,
                link_to=link_to,
                config=config,
                artifact_path=str(artifact),
                used_inputs=used_inputs,
            )
        )
    elif tool_key in ("semantic_scholar", "semantic-scholar", "s2"):
        from wheeler.integrations.asta.semantic_scholar import ingest_semantic_scholar

        report = asyncio.run(
            ingest_semantic_scholar(
                doc,
                link_to=link_to,
                target=target,
                config=config,
                artifact_path=str(artifact),
                used_inputs=used_inputs,
            )
        )
    elif tool_key == "discover":
        from wheeler.integrations.llmsr.discover import ingest_discover

        report = asyncio.run(
            ingest_discover(
                doc,
                link_to=link_to,
                config=config,
                artifact_path=str(artifact),
                used_inputs=used_inputs,
            )
        )
    else:
        from wheeler.integrations.asta.ingest import ingest_paper_finder

        report = asyncio.run(
            ingest_paper_finder(
                doc,
                link_to=link_to,
                config=config,
                artifact_path=str(artifact),
                used_inputs=used_inputs,
            )
        )

    _echo_report(report)


@integrate_app.command("export-paper-store")
def export_paper_store(
    out: Path = typer.Option(
        Path("/tmp/asta-paper-store.json"),
        "--out",
        "-o",
        help="Where to write the paper store JSON.",
    ),
    link_to: Optional[str] = typer.Option(
        None,
        "--link-to",
        help=(
            "Select every Paper linked RELEVANT_TO this node (the Q-/PL- the "
            "literature pass was run against). The curated set, post-screening."
        ),
    ),
    papers: Optional[str] = typer.Option(
        None,
        "--papers",
        help="Comma-separated Paper ids (P-...), instead of --link-to.",
    ),
    mode: str = typer.Option(
        "markdown",
        "--mode",
        help=(
            "markdown: emit paper_markdown per entry (abstract-level) for a "
            "CLOSED corpus with --no-search-additional-papers. "
            "identifiers: emit corpus_id/title only, which REQUIRES "
            "--search-additional-papers and so cannot exclude off-target papers."
        ),
    ),
) -> None:
    """Build an Asta --paper-store payload from curated graph Papers.

    Marshal-IN: reads the graph, writes a file, creates no nodes or edges.
    """
    from wheeler.config import load_config
    from wheeler.integrations.asta.paper_store import (
        MODES,
        build_paper_store,
        write_paper_store,
    )

    mode_key = mode.strip().lower()
    if mode_key not in MODES:
        typer.echo(f"Unknown mode '{mode}'. Supported: {', '.join(MODES)}.", err=True)
        raise typer.Exit(code=2)

    paper_ids = [i.strip() for i in papers.split(",") if i.strip()] if papers else []
    if not link_to and not paper_ids:
        typer.echo("Pass --link-to <Q-/PL- id> or --papers <P-id,...>.", err=True)
        raise typer.Exit(code=2)

    config = load_config()
    result = asyncio.run(
        build_paper_store(
            config,
            link_to=link_to,
            paper_ids=paper_ids or None,
            mode=mode_key,
        )
    )

    if not result.entries:
        typer.echo(
            f"No papers exported (selected={result.selected}, "
            f"skipped={len(result.skipped)}). Nothing written.",
            err=True,
        )
        if result.skipped:
            typer.echo(
                "Every selected Paper lacked an abstract. Add abstracts, or use "
                "--mode identifiers (which cannot give a closed corpus).",
                err=True,
            )
        raise typer.Exit(code=1)

    path = write_paper_store(result, out)

    typer.echo(
        f"mode={result.mode} selected={result.selected} "
        f"exported={len(result.entries)} skipped={len(result.skipped)} "
        f"closed={'yes' if result.closed else 'no'} store={path}"
    )
    if result.paper_ids:
        typer.echo(f"used={','.join(result.paper_ids)}")

    # Skipped papers are not a footnote: each one is a paper the scientist
    # curated that will NOT reach the theorizer. Name them.
    for item in result.skipped:
        typer.echo(
            f"  skipped (no abstract): {item['id']} {item['title'][:70]}", err=True
        )
    if result.skipped:
        typer.echo(
            "Those papers carry no abstract, so they cannot become "
            "paper_markdown. Including them as identifiers would force "
            "PaperFinder on and reopen the corpus, so they were dropped "
            "instead. Add an abstract to include them.",
            err=True,
        )

    # The flag pairing is the whole point and is easy to forget, so print the
    # exact next command rather than describing it.
    if result.closed:
        typer.echo(
            "\nClosed corpus. Run the theorizer with PaperFinder OFF so nothing "
            "outside this set is pulled in:\n"
            f"  asta generate-theories literature-theory-generation \\\n"
            f'    --theory-query "<question>" \\\n'
            f"    --paper-store @{path} \\\n"
            f"    --no-search-additional-papers > /tmp/asta-theorizer.json"
        )
    else:
        typer.echo(
            "\nNOT a closed corpus: identifier-only entries are hydrated during "
            "the PaperFinder step, so PaperFinder must stay ON and may "
            "reintroduce off-target papers.\n"
            f"  asta generate-theories literature-theory-generation \\\n"
            f'    --theory-query "<question>" \\\n'
            f"    --paper-store @{path} \\\n"
            f"    --search-additional-papers > /tmp/asta-theorizer.json"
        )
