"""Typer sub-app: ``wheeler services``.

Curate which service contracts are ENABLED (loaded, visible to the router and
to plan suggestions) via the folder ``<project_root>/.wheeler/services/``. That
folder is the source of truth for the enabled set; the bundled
``services.default.yaml`` is the CATALOG of what is available to enable.

Three verbs:
  - ``list``    show loaded/enabled services AND catalog services not enabled.
  - ``enable``  add a catalog entry to ``.wheeler/services/<id>.yaml``.
  - ``disable`` remove ``.wheeler/services/<id>.yaml``.

Seed-on-first-curate: ``enable`` and ``disable`` operate relative to a concrete
folder state. If the folder does not exist yet, the first curate SEEDS it with
all current catalog entries (so existing defaults stay enabled), THEN applies
the enable/disable. This makes a single disable meaningful from the default
state instead of silently dropping every other default.

This CLI WRITES only under ``.wheeler/services/``. It never touches the graph,
the network, or any LLM provider. It never raises on a curating no-op (already
enabled / not enabled).
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from wheeler.config import load_config
from wheeler.integrations.registry import (
    ServiceContract,
    catalog_services,
    contract_to_entry,
    load_services,
    services_dir,
)

logger = logging.getLogger(__name__)
console = Console()

services_app = typer.Typer(
    help="Enable/disable which service contracts are loaded (the .wheeler/services/ folder)."
)


def _resolve_dir() -> Path:
    """Resolve the enabled-services folder for the current project."""
    config = load_config()
    folder = services_dir(config)
    if folder is None:
        # load_config always yields a config, so services_dir is non-None;
        # guard anyway so mypy and a hand-built config never crash the CLI.
        folder = Path(config.project_root).resolve() / ".wheeler" / "services"
    return folder


def _write_contract(folder: Path, contract: ServiceContract) -> Path:
    """Write one enabled-service file ``<folder>/<id>.yaml``. Returns its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{contract.id}.yaml"
    body = yaml.safe_dump(
        contract_to_entry(contract),
        sort_keys=False,
        default_flow_style=False,
    )
    path.write_text(body)
    return path


def _seed_if_absent(folder: Path) -> bool:
    """Seed the folder with the full catalog if it does not exist yet.

    Returns True when seeding happened. After seeding, enable/disable act on a
    concrete folder state, so the other defaults stay enabled. Idempotent: an
    existing folder is left untouched.
    """
    if folder.is_dir():
        return False
    for contract in catalog_services():
        _write_contract(folder, contract)
    logger.info("services: seeded %s with the full catalog", folder)
    return True


# ---------------------------------------------------------------------------
# services list
# ---------------------------------------------------------------------------


@services_app.command("list")
def services_list() -> None:
    """Show LOADED/ENABLED services and catalog services not yet enabled."""
    config = load_config()
    enabled = load_services(config)
    catalog = catalog_services(config)

    enabled_ids = {c.id for c in enabled}
    folder = services_dir(config)
    curating = folder is not None and folder.is_dir()

    loaded_table = Table(title="Loaded services (enabled)")
    loaded_table.add_column("id", style="cyan")
    loaded_table.add_column("provider")
    loaded_table.add_column("act")
    loaded_table.add_column("cost")
    if enabled:
        for c in sorted(enabled, key=lambda c: c.id):
            loaded_table.add_row(c.id, c.provider, c.act, c.cost)
    else:
        loaded_table.add_row("[dim](none)[/dim]", "", "", "")
    console.print(loaded_table)

    if curating:
        console.print(
            f"[dim]Source of truth: {folder} (folder = enabled set).[/dim]"
        )
    else:
        console.print(
            "[dim]No .wheeler/services/ folder yet: every catalog default is "
            "enabled. Run 'wheeler services enable/disable' to start curating.[/dim]"
        )

    not_enabled = [c for c in catalog if c.id not in enabled_ids]
    avail_table = Table(title="Available to enable (catalog, not currently loaded)")
    avail_table.add_column("id", style="green")
    avail_table.add_column("provider")
    avail_table.add_column("description")
    if not_enabled:
        for c in sorted(not_enabled, key=lambda c: c.id):
            avail_table.add_row(c.id, c.provider, c.description)
    else:
        avail_table.add_row("[dim](all catalog services enabled)[/dim]", "", "")
    console.print(avail_table)


# ---------------------------------------------------------------------------
# services enable
# ---------------------------------------------------------------------------


@services_app.command("enable")
def services_enable(
    service_id: str = typer.Argument(..., help="Catalog service id to enable."),
) -> None:
    """Enable a service: copy its catalog entry into .wheeler/services/<id>.yaml.

    Seeds the folder with the full catalog first when it does not exist, so the
    other defaults stay enabled.
    """
    catalog = {c.id: c for c in catalog_services()}
    if service_id not in catalog:
        console.print(
            f"[red]Unknown service id[/red] {service_id!r}. "
            "Run 'wheeler services list' to see the catalog."
        )
        raise typer.Exit(1)

    folder = _resolve_dir()
    # Record whether the file already existed BEFORE any seed, so the message
    # distinguishes "already enabled" from "seeded in as a catalog default".
    pre_existing = (folder / f"{service_id}.yaml").is_file()
    seeded = _seed_if_absent(folder)

    path = folder / f"{service_id}.yaml"
    _write_contract(folder, catalog[service_id])

    if seeded:
        console.print(
            f"[green]Seeded {folder} with the catalog and enabled[/green] {service_id}."
        )
    elif pre_existing:
        console.print(f"[yellow]{service_id} was already enabled.[/yellow] Rewrote {path}.")
    else:
        console.print(f"[green]Enabled[/green] {service_id} -> {path}")

    _print_state()


# ---------------------------------------------------------------------------
# services disable
# ---------------------------------------------------------------------------


@services_app.command("disable")
def services_disable(
    service_id: str = typer.Argument(..., help="Service id to disable."),
) -> None:
    """Disable a service: remove .wheeler/services/<id>.yaml.

    Validates the id first (mirroring ``enable``): an id that is neither a
    catalog service nor an already-enabled file on disk is rejected with exit 1
    BEFORE any seeding, so a typo never silently materialises the whole folder.

    For a real id, seeds the folder with the full catalog when it does not exist
    yet, so the disable is meaningful from the default state (the other defaults
    stay enabled instead of all being dropped).
    """
    folder = _resolve_dir()
    catalog_ids = {c.id for c in catalog_services()}
    # An id is legitimate to disable if it is a catalog service OR an already
    # enabled file on disk (a hand-added contract beyond the catalog).
    on_disk = (folder / f"{service_id}.yaml").is_file()
    if service_id not in catalog_ids and not on_disk:
        console.print(
            f"[red]Unknown service id[/red] {service_id!r}. "
            "Run 'wheeler services list' to see enabled and catalog services."
        )
        raise typer.Exit(1)

    seeded = _seed_if_absent(folder)

    path = folder / f"{service_id}.yaml"
    if path.is_file():
        path.unlink()
        if seeded:
            console.print(
                f"[green]Seeded {folder} with the catalog and disabled[/green] "
                f"{service_id} (removed {path})."
            )
        else:
            console.print(f"[green]Disabled[/green] {service_id} (removed {path}).")
    else:
        # Known catalog id but no file present after the (possible) seed: a clean
        # no-op. This is reached only for a real id, never a typo.
        console.print(f"[yellow]{service_id} is already disabled.[/yellow]")

    _print_state()


def _print_state() -> None:
    """Print the resulting enabled set after a curate operation."""
    enabled = load_services(load_config())
    ids = ", ".join(sorted(c.id for c in enabled)) or "(none)"
    console.print(f"[bold]Enabled now:[/bold] {ids}")
