"""`wheeler integrate register <manifest>`: bulk provenance from a file.

Strategy 3/4 of the #117 experiment. The model writes one JSON or YAML manifest
(nodes, artifacts, edges; see wheeler/tools/graph_tools/batch.py) and this verb
applies it through the same triple-write path as every MCP tool. `--dry-run`
reports structural errors and unresolved node ids without writing, so a caller
can fix the manifest once before the real write.

Exit codes: 0 when everything landed (or the dry run is clean), 1 when the dry
run found problems or nothing could be written, 2 on a usage error. A partial
write exits 0 and says so: what landed is reported truthfully, nothing is
rolled back.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer


def register_manifest(
    manifest: Path = typer.Argument(..., help="JSON or YAML manifest (nodes, artifacts, edges)."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate only: structure, files, relationship names, literal ids."
    ),
    base_dir: Optional[Path] = typer.Option(
        None, "--base-dir", help="Resolve relative artifact paths against this dir (default: the manifest's dir)."
    ),
    as_json: bool = typer.Option(False, "--json", help="Print the full result as JSON."),
) -> None:
    """Register a manifest's nodes, artifacts and edges in one shot."""
    from wheeler.config import load_config
    from wheeler.tools.graph_tools.batch import load_manifest, register_batch

    if not manifest.exists():
        typer.echo(f"Manifest not found: {manifest}", err=True)
        raise typer.Exit(code=2)
    try:
        data = load_manifest(manifest)
    except Exception as exc:
        typer.echo(f"Could not parse manifest: {exc}", err=True)
        raise typer.Exit(code=2)

    config = load_config()
    # Each asyncio.run() gets its own loop, and the module-level backend cache
    # holds a driver bound to whichever loop created it. Reset around the run so
    # a second invocation in the same process (tests, notebooks) does not reuse
    # a driver attached to a closed loop.
    _reset_graph_state()
    try:
        result = asyncio.run(
            register_batch(
                data, config, dry_run=dry_run,
                base_dir=base_dir or manifest.resolve().parent,
            )
        )
    finally:
        _reset_graph_state()

    if as_json:
        typer.echo(json.dumps(result, indent=2, default=str))
    else:
        _echo(result)

    if dry_run:
        raise typer.Exit(code=0 if result.get("ok") else 1)
    raise typer.Exit(code=1 if result.get("status") == "failed" else 0)


def _reset_graph_state() -> None:
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    gt.reset_backend_cache()
    invalidate_async_driver()


def _echo(result: dict) -> None:
    counts = result.get("counts", {})
    if result.get("dry_run"):
        typer.echo(
            f"dry run: {counts.get('nodes', 0)} nodes, {counts.get('artifacts', 0)} artifacts, "
            f"{counts.get('edges', 0)} edges"
        )
        for err in result.get("errors", []):
            typer.echo(f"  error: {err}")
        for nid in result.get("unresolved_ids", []):
            typer.echo(f"  unresolved id: {nid} (not in the graph)")
        for w in result.get("warnings", []):
            typer.echo(f"  warning: {w}")
        typer.echo("OK: manifest is valid" if result.get("ok") else "NOT OK: fix the items above")
        return

    if result.get("error") == "validation_failed":
        typer.echo("nothing written: manifest invalid")
        for err in result.get("errors", []):
            typer.echo(f"  error: {err}")
        return

    typer.echo(
        f"{result.get('status')}: {counts.get('nodes', 0)} nodes, {counts.get('artifacts', 0)} artifacts, "
        f"{counts.get('edges', 0)} edges, {result.get('failures', 0)} failures"
    )
    for alias, nid in sorted(result.get("ids", {}).items()):
        typer.echo(f"  {alias} -> {nid}")
    for section in ("nodes", "artifacts", "edges"):
        for row in result.get(section, []):
            if row.get("status") in ("error", "skipped"):
                what = row.get("alias") or row.get("path") or (
                    f"{row.get('source')} -[{row.get('relationship')}]-> {row.get('target')}"
                )
                typer.echo(f"  {section}[{row['index']}] {what}: {row.get('error')} {row.get('detail') or ''}".rstrip())
