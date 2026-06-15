"""Light service-extension registry: a declarative manifest of services.

A service is a declarative CONTRACT (one manifest entry). Commands read the
registry instead of hardcoding providers. This module is a PURE READ: it has no
graph dependency, imports no LLM-provider SDK, and never raises on a bad
manifest. A missing folder/file falls back to the bundled default; a malformed
entry is skipped and logged; the loaders always return a list (possibly empty).

Two distinct ideas, do not conflate them:

  - the bundled CATALOG at ``wheeler/integrations/services.default.yaml``
    (ships with the package): everything that is AVAILABLE to enable.
  - the ENABLED set: what is actually LOADED and visible to the router and to
    plan suggestions.

The ENABLE/DISABLE layer is a FOLDER, not a single override file. The folder
``<project_root>/.wheeler/services/`` is the source of truth for ENABLED
services: each ``<id>.yaml`` file in it is one enabled contract (same schema as
a ``services.default.yaml`` entry, either a single mapping or wrapped under a
``services:`` list, both accepted).

Load precedence (the rule the CLI and the router both rely on):

  - if ``<project_root>/.wheeler/services/`` EXISTS, the folder is truth and
    ``load_services`` returns only the contracts parsed from its ``*.yaml``
    files (an empty or all-garbage folder yields an empty enabled set);
  - if the folder does NOT exist, ``load_services`` falls back to the bundled
    CATALOG so every default stays enabled until the user starts curating
    (backward-compat).

``load_services`` returns the ENABLED set. ``catalog_services`` returns the
bundled catalog (everything available to enable), used by the ``list`` command.
``available_services`` filters the ENABLED set by each contract's ``available``
shell probe and returns only the ones that pass.

A legacy single-file override at ``<project_root>/.wheeler/services.yaml`` is
still honoured for backward-compat, but ONLY when the new
``.wheeler/services/`` folder is absent: the folder always wins.
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


def services_dir(config: WheelerConfig | None) -> Path | None:
    """Resolve the enabled-services folder ``<project_root>/.wheeler/services/``.

    This folder is the source of truth for ENABLED services. Returns None when no
    config is supplied (caller then uses the bundled catalog only).
    """
    if config is None:
        return None
    root = Path(config.project_root).resolve()
    return root / ".wheeler" / "services"


def _user_manifest_path(config: WheelerConfig | None) -> Path | None:
    """Resolve the legacy single-file override ``.wheeler/services.yaml``.

    Honoured only when the ``.wheeler/services/`` folder is absent. Returns None
    when no config is supplied (caller then uses the bundled catalog only).
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


def _read_service_file(path: Path) -> list[dict[str, Any]]:
    """Read raw service entries from one ``.wheeler/services/<id>.yaml`` file.

    Each enabled-service file holds ONE contract, accepted in either shape:
      - a bare mapping (the contract fields at the top level), or
      - the same ``services:`` list shape as the catalog (in which case every
        list entry is read, so a hand-merged file still works).

    Defensive: a missing/unreadable file, invalid YAML, or a non-mapping
    top-level document yields an empty list (logged). Never raises.
    """
    try:
        raw = path.read_text()
    except OSError as exc:
        logger.warning("registry: could not read service file %s: %s", path, exc)
        return []

    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        logger.warning("registry: service file %s is not valid YAML: %s", path, exc)
        return []

    if doc is None:
        return []
    if not isinstance(doc, dict):
        logger.warning("registry: service file %s is not a mapping; ignoring", path)
        return []

    # Allow the catalog-style ``services:`` wrapper as well as a bare mapping.
    if "services" in doc:
        services = doc.get("services")
        if not isinstance(services, list):
            logger.warning(
                "registry: 'services' in %s is not a list; ignoring", path
            )
            return []
        return [entry for entry in services if isinstance(entry, dict)]

    return [doc]


def _load_enabled_dir(folder: Path) -> list[ServiceContract]:
    """Parse every ``*.yaml`` in the enabled-services folder into contracts.

    The folder is the source of truth for ENABLED services. Files are read in
    sorted order for deterministic output; a malformed file is skipped (logged)
    and never aborts the load. Duplicate ids (same contract id from two files)
    keep the first seen. Never raises.
    """
    contracts: list[ServiceContract] = []
    seen: set[str] = set()
    try:
        files = sorted(folder.glob("*.yaml"))
    except OSError as exc:
        logger.warning("registry: could not list %s: %s", folder, exc)
        return []

    for path in files:
        for entry in _read_service_file(path):
            parsed = _parse_entry(entry)
            if parsed is None:
                continue
            if parsed.id in seen:
                logger.warning(
                    "registry: duplicate enabled service id %r (%s); keeping first",
                    parsed.id,
                    path,
                )
                continue
            seen.add(parsed.id)
            contracts.append(parsed)
    return contracts


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


def contract_to_entry(contract: ServiceContract) -> dict[str, Any]:
    """Render a ServiceContract back to a plain YAML-serialisable mapping.

    Used by the ``enable`` CLI to write a faithful ``.wheeler/services/<id>.yaml``
    entry. The shape round-trips through ``_parse_entry`` unchanged. ``inputs``
    and ``output`` are only emitted when non-empty to keep files terse.
    """
    entry: dict[str, Any] = {
        "id": contract.id,
        "provider": contract.provider,
        "name": contract.name,
        "description": contract.description,
        "kind": contract.kind,
        "act": contract.act,
        "cost": contract.cost,
        "available": contract.available,
        "when": contract.when,
    }
    if contract.inputs:
        entry["inputs"] = contract.inputs
    if contract.output:
        entry["output"] = contract.output
    return entry


def catalog_services(
    config: WheelerConfig | None = None,
) -> list[ServiceContract]:
    """Return the bundled CATALOG: every service AVAILABLE to enable.

    This is always the shipped ``services.default.yaml``, independent of what is
    enabled in ``.wheeler/services/``. The ``list`` command uses it to show what
    can be enabled. ``config`` is accepted for signature symmetry but is not
    consulted (the catalog is bundled, not per-project). Never raises.

    Pure read: no graph access, no subprocess, no network.
    """
    contracts: list[ServiceContract] = []
    for entry in _read_manifest(_DEFAULT_MANIFEST):
        parsed = _parse_entry(entry)
        if parsed is not None:
            contracts.append(parsed)
    return contracts


def load_services(config: WheelerConfig | None = None) -> list[ServiceContract]:
    """Load the ENABLED service contracts (what the router/plan acts see).

    Load precedence:
      1. If ``<project_root>/.wheeler/services/`` EXISTS, the folder is the
         source of truth: return only the contracts parsed from its ``*.yaml``
         files (an empty or all-garbage folder yields an empty enabled set).
      2. Else if the legacy single-file ``.wheeler/services.yaml`` exists, it
         wins (backward-compat) and the catalog is NOT merged in.
      3. Else fall back to the bundled CATALOG so every default stays enabled
         until the user starts curating (backward-compat).

    Malformed entries/files are skipped (logged); nothing here ever raises.

    This is a pure read: no graph access, no subprocess, no network.
    """
    folder = services_dir(config)
    if folder is not None and folder.is_dir():
        logger.info("registry: loading enabled services from folder %s", folder)
        return _load_enabled_dir(folder)

    user_path = _user_manifest_path(config)
    if user_path is not None and user_path.is_file():
        logger.info("registry: loading legacy user manifest %s", user_path)
        raw_entries = _read_manifest(user_path)
    else:
        logger.info("registry: loading bundled catalog %s", _DEFAULT_MANIFEST)
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
