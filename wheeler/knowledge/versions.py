"""Append-only node versions: snapshots, content hashes, version reads.

A node's id is stable for life; its content has a version. Version 1 is the
creation. Every field or tier change bumps it and, before the change lands,
the previous state is written once to ``knowledge/versions/<id>/v<n>.json``.
The current state stays in ``knowledge/<id>.json``. So every version that
ever existed is readable: the current one from the main file, earlier ones
from the snapshots. A node that was never changed has no snapshot directory.

Metadata changes (stale flags, stale_since, session bookkeeping) do not bump
the version: version tracks content, and the change_log tracks everything.

Layering: models only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from wheeler.models import NodeBase

# Fields that change without the content changing. Excluded from the hash so
# a stale flag or a re-render does not look like an edit.
VOLATILE_FIELDS: frozenset[str] = frozenset({
    "updated", "change_log", "stale", "stale_since", "session_id",
    "display_name", "content_version", "content_hash", "stability",
    "origin_machine", "origin_host", "origin_database", "origin_project",
})

VERSIONS_DIR = "versions"


def content_hash_of(model: NodeBase) -> str:
    """16 hex chars of SHA-256 over the content fields, canonically serialised."""
    data = model.model_dump(exclude=set(VOLATILE_FIELDS))
    blob = json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def snapshot_dir(knowledge_path: Path, node_id: str) -> Path:
    return Path(knowledge_path) / VERSIONS_DIR / node_id


def snapshot(knowledge_path: Path, model: NodeBase) -> Path | None:
    """Write the node's CURRENT state as ``v<version>.json`` before it changes.

    Idempotent: an existing snapshot for that version is left alone, so a
    retried write cannot overwrite history. Returns the path, or None when
    the snapshot already existed.
    """
    d = snapshot_dir(knowledge_path, model.id)
    d.mkdir(parents=True, exist_ok=True)
    target = d / f"v{model.content_version or 1}.json"
    if target.exists():
        return None
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(target)
    return target


def bump(model: NodeBase) -> None:
    """Advance to the next content version and refresh the content hash."""
    model.content_version = (model.content_version or 1) + 1
    model.content_hash = content_hash_of(model)


def list_versions(knowledge_path: Path, node_id: str, current: int | None = None) -> list[int]:
    """Version numbers readable for *node_id*: snapshots plus the current one."""
    d = snapshot_dir(knowledge_path, node_id)
    found = set()
    if d.exists():
        for f in d.glob("v*.json"):
            try:
                found.add(int(f.stem[1:]))
            except ValueError:
                continue
    if current:
        found.add(current)
    return sorted(found)


def read_version(knowledge_path: Path, node_id: str, version: int) -> dict:
    """The node as a dict at *version*. Raises FileNotFoundError if unknown.

    The current version lives in the main file; earlier ones in snapshots.
    """
    from wheeler.knowledge.store import read_node

    try:
        current = read_node(Path(knowledge_path), node_id)
    except FileNotFoundError:
        current = None
    if current is not None and (current.content_version or 1) == version:
        return current.model_dump()
    snap = snapshot_dir(knowledge_path, node_id) / f"v{version}.json"
    if not snap.exists():
        raise FileNotFoundError(f"{node_id} has no version {version}")
    return json.loads(snap.read_text(encoding="utf-8"))
