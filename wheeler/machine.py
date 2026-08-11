"""Stable identity for the computer Wheeler is running on.

Why this exists: a Wheeler graph can be shared (Aura) while the files it indexes
stay local, so the same graph is reached from more than one computer. Without a
machine stamp, a node cannot say which computer produced it, and Wheeler cannot
tell "this script changed" from "this script belongs to my other laptop". The
second reading is the dangerous one, because staleness propagates downstream: see
``wheeler.provenance.detect_and_propagate_stale``.

Identity is a UUID stored in ``~/.wheeler/machine.json``, not the hostname. A
hostname is renamed by the user, changed by DHCP, and duplicated across a lab's
identically-imaged machines, so it is a label for humans and not a key. Both are
recorded.

This module imports nothing from ``wheeler``, the same rule ``credentials.py``
follows: ``config.py`` is a zero-internal-dependency leaf and reads this, so a
cycle must be impossible by construction. ``origin_props`` therefore reads its
config duck-typed via ``getattr`` rather than importing ``WheelerConfig``.

Every read path degrades instead of raising. A read-only home directory, a
corrupt JSON file, and a missing directory all produce a deterministic fallback
id derived from the hostname, because "we could not name this machine" must never
be the reason a write fails.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import platform
import socket
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

def _machine_file() -> Path:
    """Where this machine's record lives, beside the other user-level state.

    Resolved per call rather than at import: a module constant would freeze
    whatever ``$HOME`` was when the first import happened, which is wrong for any
    process that relocates it (tests, and containers that set HOME after start).
    """
    return Path.home() / ".wheeler" / "machine.json"

# Overrides, in precedence order over the stored file. The id override exists for
# tests and for containers that want a pinned identity; the label override is for
# users who want a friendlier name than the hostname.
_ID_ENV = "WHEELER_MACHINE_ID"
_LABEL_ENV = "WHEELER_MACHINE_LABEL"

# Marks an id that was derived rather than generated and stored, so a support
# question about two machines sharing an id has an obvious first thing to check.
_FALLBACK_PREFIX = "derived-"

# The graph/file property names this module owns. Exported so tests and readers
# do not restate them and drift.
ORIGIN_FIELDS: tuple[str, ...] = (
    "origin_machine",
    "origin_host",
    "origin_database",
    "origin_project",
)

# Cached for the process. Reading a small JSON file is cheap, but this runs on
# every mutation, and the value cannot change under a running process.
_cache: dict[str, str] = {}


def reset_cache() -> None:
    """Drop the per-process cache. For tests that relocate ``$HOME``."""
    _cache.clear()


def _hostname() -> str:
    """Best available human name for this machine. Never raises."""
    for probe in (socket.gethostname, platform.node):
        try:
            name = (probe() or "").strip()
        except Exception:  # pragma: no cover - defensive
            continue
        if name:
            # Strip the mDNS suffix: "maxwells-mbp.local" reads better as
            # "maxwells-mbp" and is the same machine either way.
            return name[: -len(".local")] if name.endswith(".local") else name
    return "unknown-host"


def _derived_id() -> str:
    """A stable id for when the machine file cannot be read or written.

    Deterministic in the hostname, so a machine that cannot persist a UUID still
    reports the SAME id across processes and runs. That keeps staleness
    attribution working (the common case) at the cost of colliding with another
    machine of the same name, which is why it is prefixed and logged.
    """
    digest = hashlib.sha256(_hostname().encode("utf-8")).hexdigest()[:32]
    return f"{_FALLBACK_PREFIX}{digest}"


def _read_record() -> dict[str, str] | None:
    """The stored machine record, or None when there isn't a usable one."""
    target = _machine_file()
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.debug("machine file unreadable: %s", exc)
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("%s is not valid JSON, ignoring it", target)
        return None
    if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not data["id"]:
        return None
    return {str(k): str(v) for k, v in data.items() if isinstance(v, (str, int, float))}


def _write_record(record: dict[str, str]) -> dict[str, str] | None:
    """Persist a new machine record, or None when it could not be stored.

    Atomic tmp+rename, and the file is re-read afterwards. The re-read is not
    paranoia: two Wheeler processes starting at once would each generate a UUID
    and each rename over the other, so without it they would disagree about this
    machine's identity for the rest of their lives. Reading back means both adopt
    whichever record won the rename.

    Returning None on failure rather than the unsaved record is load-bearing. The
    record holds a fresh ``uuid4``, so handing it back would give this machine a
    DIFFERENT identity on every run, which is worse than having no identity: the
    staleness classifier would read its own earlier writes as another machine's.
    The caller derives a stable id instead.
    """
    target = _machine_file()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f"machine.json.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(record, indent=2), encoding="utf-8")
        tmp.replace(target)
    except OSError as exc:
        logger.warning(
            "could not write %s (%s), falling back to a hostname-derived machine id",
            target,
            exc,
        )
        return None
    return _read_record() or record


def _record() -> dict[str, str]:
    """This machine's record, creating and persisting one on first use."""
    if _cache:
        return _cache

    stored = _read_record()
    if stored is None:
        stored = _write_record({
            "id": uuid.uuid4().hex,
            "label": _hostname(),
            "created": datetime.now(timezone.utc).isoformat(),
        })
    if stored is None:
        # Nothing could be persisted, so a random UUID is not an option: it would
        # change on every run. Derive one from the hostname, which at least holds
        # still.
        stored = {"id": _derived_id(), "label": _hostname()}
    if not stored.get("id"):
        stored = {**stored, "id": _derived_id()}
    if not stored.get("label"):
        stored = {**stored, "label": _hostname()}

    _cache.update(stored)
    return _cache


def machine_id() -> str:
    """Stable UUID for this computer. Never raises."""
    override = os.environ.get(_ID_ENV, "").strip()
    if override:
        return override
    try:
        return _record()["id"]
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("machine id lookup failed (%s), deriving one", exc)
        return _derived_id()


def machine_label() -> str:
    """Human-readable name for this computer. Never raises."""
    override = os.environ.get(_LABEL_ENV, "").strip()
    if override:
        return override
    try:
        return _record()["label"]
    except Exception:  # pragma: no cover - defensive
        return _hostname()


def origin_props(config: object) -> dict[str, str]:
    """The origin stamp for a node written from this machine, right now.

    The single source of both the field names and their values. Two callers write
    this stamp, one per storage layer: ``Neo4jBackend.create_node`` for the graph
    and ``execute_tool`` for ``knowledge/*.json``. They must agree, so neither
    builds the dict itself.

    ``config`` is read duck-typed so this module keeps an empty import graph; a
    partial stand-in (``SimpleNamespace``, a test double) yields empty strings
    rather than an AttributeError.
    """
    neo4j = getattr(config, "neo4j", None)
    project = getattr(config, "project", None)

    database = getattr(neo4j, "database", "") or ""
    # Prefer the human project name; fall back to the Community-Edition namespace
    # tag, which is the only project identity a tagged graph has.
    name = getattr(project, "name", "") or getattr(neo4j, "project_tag", "") or ""

    return {
        "origin_machine": machine_id(),
        "origin_host": machine_label(),
        "origin_database": str(database),
        "origin_project": str(name),
    }
