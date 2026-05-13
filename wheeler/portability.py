"""Portable archive utilities for Wheeler backup/restore.

Pure functions only. No graph deps, no config deps.
Used by backup.py to rewrite paths and scan for secrets before packing,
and by restore.py to reconstruct absolute paths on the recipient machine.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

# The sentinel placed in archive bytes wherever an absolute path inside
# the project root lived. Greppable, JSON-safe, unlikely to appear in
# real content.
_PROJECT_SENTINEL = "${PROJECT}/"

# ---------------------------------------------------------------------------
# Path rewriting
# ---------------------------------------------------------------------------


def relativize(abs_path: str, project_root: Path) -> tuple[str, bool]:
    """Convert an absolute path to a portable sentinel-prefixed relative path.

    Returns ``("${PROJECT}/<rel-posix>", True)`` when ``abs_path`` resolves
    inside ``project_root.resolve()``, otherwise returns
    ``(abs_path, False)`` unchanged.

    The exactly-equal case (path == project_root) returns
    ``("${PROJECT}/", True)``.
    """
    try:
        resolved = Path(abs_path).resolve()
        root = project_root.resolve()
        # Check containment using is_relative_to (Python 3.9+) equivalence.
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            return abs_path, False
        # relative_to returns PosixPath('.') for the exact-root case.
        # Represent that as "${PROJECT}/" (empty suffix, trailing slash only).
        rel_str = rel.as_posix()
        if rel_str == ".":
            return _PROJECT_SENTINEL, True
        return _PROJECT_SENTINEL + rel_str, True
    except Exception:
        return abs_path, False


def absolutize(stored: str, project_root: Path) -> str:
    """Convert a sentinel-prefixed portable path back to an absolute path.

    Recognises the literal ``${PROJECT}/`` prefix and joins the suffix with
    ``project_root``, returning a POSIX-style absolute path string.

    Anything that does not start with ``${PROJECT}/`` is returned unchanged
    (external paths and bare filenames pass through transparently).
    """
    if stored.startswith(_PROJECT_SENTINEL):
        suffix = stored[len(_PROJECT_SENTINEL):]
        return str(project_root.resolve() / suffix)
    return stored


# ---------------------------------------------------------------------------
# Path field map
# ---------------------------------------------------------------------------

# Labels whose nodes carry a ``path`` field that names a file on disk.
# All other labels have no path field (or it is not machine-specific).
_LABEL_PATH_FIELDS: dict[str, tuple[str, ...]] = {
    "Finding": ("path",),
    "Dataset": ("path",),
    "Document": ("path",),
    "Script": ("path",),
    "Plan": ("path",),
}


def iter_path_fields(label: str) -> Iterable[str]:
    """Yield the names of path-valued fields for a node label.

    Returns an empty iterable for labels not in the hardcoded map.
    The map covers Finding, Dataset, Document, Script, and Plan.
    """
    return _LABEL_PATH_FIELDS.get(label, ())


# ---------------------------------------------------------------------------
# Secret scanning
# ---------------------------------------------------------------------------

# Mirror the exact patterns from .githooks/pre-commit lines 32-38.
# Ordered as in the hook: most specific first so snippets are readable.
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ANTHROPIC_API_KEY", re.compile(r"ANTHROPIC_API_KEY")),
    ("api.anthropic.com", re.compile(r"api\.anthropic\.com")),
    ("import anthropic", re.compile(r"import anthropic")),
    ("from anthropic import", re.compile(r"from anthropic import")),
    ("anthropic.Anthropic()", re.compile(r"anthropic\.Anthropic\(\)")),
    ("sk-ant-token", re.compile(r"sk-ant-[a-zA-Z0-9_-]+")),
]


def scan_for_secrets(content: bytes, filename: str) -> list[tuple[str, str]]:
    """Scan bytes for forbidden API-key patterns.

    Decodes as latin-1 (byte-safe, no surrogates) so binary files do not
    crash the scanner. Returns a list of ``(pattern_name, matched_snippet)``
    pairs, one entry per match found. An empty list means clean.

    The patterns mirror `.githooks/pre-commit` lines 32-38 exactly so that
    an archive produced on a machine with the hook installed cannot contain
    any content the hook would have blocked in source.
    """
    text = content.decode("latin-1")
    hits: list[tuple[str, str]] = []
    for name, pattern in _SECRET_PATTERNS:
        for m in pattern.finditer(text):
            snippet = m.group(0)[:80]
            hits.append((name, snippet))
    return hits


# ---------------------------------------------------------------------------
# External reference discovery
# ---------------------------------------------------------------------------


def discover_external_reference(abs_path: str) -> dict | None:
    """Probe whether ``abs_path`` sits inside a git repository.

    If the path exists and ``git rev-parse --show-toplevel`` succeeds from
    its parent directory, return a dict with:

    - ``path``: the original ``abs_path``
    - ``git_remote``: ``remote.origin.url`` (empty string if not configured)
    - ``git_commit``: the HEAD SHA (empty string on failure)
    - ``git_dirty``: True if the working tree has uncommitted changes

    Returns ``None`` if the path does not exist or is not inside a git repo.
    """
    p = Path(abs_path)
    if not p.exists():
        return None

    parent = str(p.parent) if p.is_file() else str(p)

    try:
        result = subprocess.run(
            ["git", "-C", parent, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    # Fetch remote URL (best-effort, empty string if not set)
    try:
        remote_result = subprocess.run(
            ["git", "-C", parent, "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        git_remote = remote_result.stdout.strip() if remote_result.returncode == 0 else ""
    except Exception:
        git_remote = ""

    # Fetch HEAD commit SHA
    try:
        commit_result = subprocess.run(
            ["git", "-C", parent, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        git_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else ""
    except Exception:
        git_commit = ""

    # Dirty check: any output from status --porcelain means dirty
    try:
        status_result = subprocess.run(
            ["git", "-C", parent, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        git_dirty = bool(status_result.stdout.strip()) if status_result.returncode == 0 else False
    except Exception:
        git_dirty = False

    return {
        "path": abs_path,
        "git_remote": git_remote,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
    }


# ---------------------------------------------------------------------------
# Manifest signature
# ---------------------------------------------------------------------------


def compute_manifest_signature(manifest: dict) -> str:
    """Compute a SHA-256 signature over the manifest contents.

    The ``manifest_signature`` key itself is excluded from the digest so
    the function is idempotent: signing an already-signed manifest produces
    the same result as signing the unsigned one.

    Returns a string of the form ``"sha256:<hex>"``.
    """
    payload = {k: v for k, v in manifest.items() if k != "manifest_signature"}
    serialised = json.dumps(payload, sort_keys=True).encode("utf-8")
    hex_digest = hashlib.sha256(serialised).hexdigest()
    return f"sha256:{hex_digest}"
