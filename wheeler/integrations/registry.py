"""Light service-extension registry: a declarative manifest of services.

A service is a declarative CONTRACT (one manifest entry). Commands read the
registry instead of hardcoding providers. This module is a PURE READ: it has no
graph dependency, imports no LLM-provider SDK, and never raises on a bad
manifest. A missing file falls back to the bundled default; a malformed entry is
skipped and logged; the loaders always return a list (possibly empty).

Two manifests exist:
  - the bundled DEFAULT at ``wheeler/integrations/services.default.yaml``
    (ships with the package),
  - an optional USER override at ``<project_root>/.wheeler/services.yaml``
    (wins when present).

``load_services`` returns every parsed contract. ``available_services`` runs each
contract's ``available`` shell probe and returns only the ones that pass.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)

# The bundled default manifest sits next to this module.
_DEFAULT_MANIFEST = Path(__file__).resolve().parent / "services.default.yaml"

# Probe wall-clock ceiling. The probe is an availability check (e.g.
# "asta auth status"), so it should be fast; we cap it so a hung binary cannot
# stall the router.
_PROBE_TIMEOUT = 10


@dataclass(frozen=True)
class ServiceContract:
    """One declarative service entry from the manifest.

    Carries identity, the act that drives it, cost/availability hints, and the
    free-text ``when`` trigger. It does NOT carry a field-map DSL: the heavy
    marshalling stays tool-specific in each adapter. ``kind`` is one of
    ``"shell-out"`` or ``"local"``.
    """

    id: str
    provider: str
    name: str
    description: str
    kind: str
    act: str
    cost: str
    available: str
    when: str
    # Optional input ports / output shape from the manifest, kept opaque here
    # (the registry does not interpret them; adapters do).
    inputs: list[dict[str, Any]] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)


# Fields required for a manifest entry to parse into a ServiceContract.
_REQUIRED_FIELDS = (
    "id",
    "provider",
    "name",
    "description",
    "kind",
    "act",
    "cost",
    "available",
    "when",
)

_VALID_KINDS = ("shell-out", "local")


def _user_manifest_path(config: WheelerConfig | None) -> Path | None:
    """Resolve the user override path ``<project_root>/.wheeler/services.yaml``.

    Returns None when no config is supplied (caller then uses the default only).
    """
    if config is None:
        return None
    root = Path(config.project_root).resolve()
    return root / ".wheeler" / "services.yaml"


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    """Read raw service entries from a YAML manifest file.

    Defensive: a missing file, unreadable file, non-mapping document, or a
    ``services:`` key that is not a list yields an empty list (logged). Never
    raises.
    """
    try:
        raw = path.read_text()
    except OSError as exc:
        logger.warning("registry: could not read manifest %s: %s", path, exc)
        return []

    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        logger.warning("registry: manifest %s is not valid YAML: %s", path, exc)
        return []

    if doc is None:
        # Empty manifest (the user file may ship empty): no services.
        return []
    if not isinstance(doc, dict):
        logger.warning("registry: manifest %s is not a mapping; ignoring", path)
        return []

    services = doc.get("services")
    if services is None:
        return []
    if not isinstance(services, list):
        logger.warning(
            "registry: 'services' in %s is not a list; ignoring", path
        )
        return []

    return [entry for entry in services if isinstance(entry, dict)]


def _parse_entry(entry: dict[str, Any]) -> ServiceContract | None:
    """Parse one raw manifest entry into a ServiceContract.

    Returns None (and logs) when the entry is missing a required field or has an
    unknown ``kind``. Never raises.
    """
    missing = [f for f in _REQUIRED_FIELDS if not entry.get(f)]
    if missing:
        logger.warning(
            "registry: skipping service entry %r; missing fields: %s",
            entry.get("id", "<no id>"),
            ", ".join(missing),
        )
        return None

    kind = str(entry["kind"])
    if kind not in _VALID_KINDS:
        logger.warning(
            "registry: skipping service %r; unknown kind %r (expected one of %s)",
            entry["id"],
            kind,
            ", ".join(_VALID_KINDS),
        )
        return None

    inputs_raw = entry.get("inputs")
    inputs = (
        [i for i in inputs_raw if isinstance(i, dict)]
        if isinstance(inputs_raw, list)
        else []
    )
    output_raw = entry.get("output")
    output = output_raw if isinstance(output_raw, dict) else {}

    return ServiceContract(
        id=str(entry["id"]),
        provider=str(entry["provider"]),
        name=str(entry["name"]),
        description=str(entry["description"]),
        kind=kind,
        act=str(entry["act"]),
        cost=str(entry["cost"]),
        available=str(entry["available"]),
        when=str(entry["when"]),
        inputs=inputs,
        output=output,
    )


def load_services(config: WheelerConfig | None = None) -> list[ServiceContract]:
    """Load service contracts from the user override or the bundled default.

    Resolution: if ``<project_root>/.wheeler/services.yaml`` exists, it wins and
    the default is NOT merged in; otherwise the bundled
    ``services.default.yaml`` is used. Malformed entries are skipped (logged);
    a missing or malformed file yields the default or an empty list. Never
    raises.

    This is a pure read: no graph access, no subprocess, no network.
    """
    user_path = _user_manifest_path(config)
    if user_path is not None and user_path.is_file():
        logger.info("registry: loading user manifest %s", user_path)
        raw_entries = _read_manifest(user_path)
    else:
        logger.info("registry: loading bundled default manifest %s", _DEFAULT_MANIFEST)
        raw_entries = _read_manifest(_DEFAULT_MANIFEST)

    contracts: list[ServiceContract] = []
    for entry in raw_entries:
        parsed = _parse_entry(entry)
        if parsed is not None:
            contracts.append(parsed)
    return contracts


def _probe_passes(command: str) -> bool:
    """Run an availability probe; True iff it exits 0.

    A missing binary, non-zero exit, timeout, or empty command counts as
    unavailable. Never raises.
    """
    command = command.strip()
    if not command:
        return False

    try:
        argv = shlex.split(command)
    except ValueError as exc:
        logger.warning("registry: probe %r is not a valid command: %s", command, exc)
        return False
    if not argv:
        return False

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.info("registry: probe %r timed out; treating as unavailable", argv[:2])
        return False
    except (FileNotFoundError, OSError) as exc:
        logger.info("registry: probe %r could not launch: %s", argv[:1], exc)
        return False

    return proc.returncode == 0


def available_services(
    config: WheelerConfig | None = None,
) -> list[ServiceContract]:
    """Return the loaded contracts whose ``available`` probe passes.

    Runs each contract's probe via subprocess; a non-zero exit or missing binary
    filters the contract out. Pure read with respect to the graph: it shells out
    only to the declared probes, never to an LLM provider. Never raises.
    """
    return [c for c in load_services(config) if _probe_passes(c.available)]
