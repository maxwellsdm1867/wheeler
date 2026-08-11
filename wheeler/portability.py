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


# A stored path already in portable form. Matched by SHAPE rather than against
# the known root names on purpose: a "${GDRIVE}/..." value read on a machine with
# no gdrive root is still portable, and re-relativizing it against the local cwd
# would corrupt it into a path that resolves nowhere.
_SENTINEL_RE = re.compile(r"^\$\{[A-Z0-9_]+\}/")

# Root ids that can be turned into a sentinel. Anything else is skipped rather
# than escaped, because a root name with a brace or a slash in it would produce a
# sentinel that cannot be parsed back out.
_ROOT_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")


def sentinel_for(root_id: str) -> str:
    """The portable prefix for a root name, e.g. ``data`` -> ``${DATA}/``."""
    return "${" + root_id.upper() + "}/"


def is_portable(stored: str) -> bool:
    """Whether a stored path is already in ``${ROOT}/`` form."""
    return bool(_SENTINEL_RE.match(stored or ""))


def _usable_roots(roots: dict[str, Path]) -> list[tuple[str, Path]]:
    """Valid roots, deepest first.

    Deepest first is what makes nested roots behave: with ``project=/a`` and
    ``data=/a/data``, the file ``/a/data/x.mat`` must portabilize as
    ``${DATA}/x.mat``, not ``${PROJECT}/data/x.mat``. Sorting by resolved path
    length is a cheap stand-in for "most specific containing root".
    """
    usable: list[tuple[str, Path]] = []
    for root_id, root in (roots or {}).items():
        if not root_id or not _ROOT_ID_RE.match(root_id):
            logger.debug("skipping unusable root name %r", root_id)
            continue
        try:
            usable.append((root_id, Path(root).expanduser().resolve()))
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("skipping root %r (%s)", root_id, exc)
    usable.sort(key=lambda pair: len(str(pair[1])), reverse=True)
    return usable


def to_portable(abs_path: str, roots: dict[str, Path]) -> tuple[str, str]:
    """Rewrite an absolute path against the deepest containing root.

    Returns ``(portable_or_unchanged, root_id_or_empty)``. A path inside no known
    root is returned unchanged with an empty root id, which is the correct
    outcome for genuinely external files (a mounted volume, someone else's home)
    and keeps this function total.

    Idempotent: a value that is already portable is returned untouched, so a
    write path that portabilizes and a backup that portabilizes again cannot
    double-encode.

    Both sides are ``resolve()``d, which matters more than it looks: a Google
    Drive folder is normally reached through a symlink, so comparing an
    unresolved file path against a resolved root (or the reverse) silently finds
    no containment and stores an absolute path forever.
    """
    if not abs_path or is_portable(abs_path):
        return abs_path, ""
    try:
        resolved = Path(abs_path).expanduser().resolve()
    except Exception:
        return abs_path, ""

    for root_id, root in _usable_roots(roots):
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            continue
        rel_str = rel.as_posix()
        # relative_to yields '.' when the path IS the root; represent that as the
        # bare sentinel so absolutize round-trips it back to the root itself.
        if rel_str == ".":
            return sentinel_for(root_id), root_id
        return sentinel_for(root_id) + rel_str, root_id
    return abs_path, ""


def resolve(stored: str, roots: dict[str, Path]) -> Path | None:
    """Resolve a stored path on THIS machine, or None when that is impossible.

    ``None`` means "portable, but its root is not configured here", which is a
    different fact from "the file is missing" and callers must not conflate the
    two: a missing file may be stale, an unconfigured root simply lives on
    another computer. Absolute (legacy) values always resolve, because we know
    where they point even when nothing is there.
    """
    if not stored:
        return None
    match = _SENTINEL_RE.match(stored)
    if not match:
        try:
            return Path(stored).expanduser()
        except Exception:  # pragma: no cover - defensive
            return None

    prefix = match.group(0)
    wanted = prefix[2:-2].lower()  # "${DATA}/" -> "data"
    for root_id, root in _usable_roots(roots):
        if root_id.lower() == wanted:
            return root / stored[len(prefix):]
    return None


def relativize(abs_path: str, project_root: Path) -> tuple[str, bool]:
    """Convert an absolute path to a portable sentinel-prefixed relative path.

    Returns ``("${PROJECT}/<rel-posix>", True)`` when ``abs_path`` resolves
    inside ``project_root.resolve()``, otherwise returns
    ``(abs_path, False)`` unchanged.

    The exactly-equal case (path == project_root) returns
    ``("${PROJECT}/", True)``.

    Single-root wrapper over :func:`to_portable`, kept because ``backup.py`` and
    ``restore.py`` are written against this shape and only ever deal with the
    project root.
    """
    portable, root_id = to_portable(abs_path, {"project": project_root})
    return portable, bool(root_id)


def absolutize(stored: str, project_root: Path) -> str:
    """Convert a sentinel-prefixed portable path back to an absolute path.

    Recognises the literal ``${PROJECT}/`` prefix and joins the suffix with
    ``project_root``, returning a POSIX-style absolute path string.

    Anything that does not start with ``${PROJECT}/`` is returned unchanged
    (external paths and bare filenames pass through transparently). A sentinel
    naming some OTHER root also passes through unchanged, since this wrapper only
    knows the project root.
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

# Shape-based secret detection.  The scanner intentionally only looks for
# the actual API-key shape, not for SDK references such as ``import anthropic``
# or env-var names such as ``ANTHROPIC_API_KEY``.  SDK-reference detection
# is a Wheeler *policy* concern handled by ``.githooks/pre-commit``; secret
# scanning is a separate concern that only fires on content that could leak
# a credential.
#
# Real Anthropic API keys look like ``sk-ant-api03-<~95-char base64-ish>``.
# A length floor of 32 characters after the ``sk-ant-`` prefix excludes
# all common test placeholders (e.g. ``sk-ant-test``, ``sk-ant-xxxx``,
# ``sk-ant-supersecret123``, ``sk-ant-xxxxxxxxxxxxxxxxxxx``) while easily
# matching genuine keys.  This matches the industry-standard approach used
# by gitleaks and trufflehog: shape + length/charset constraints rather than
# substring or entropy heuristics.
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("sk-ant-token", re.compile(r"sk-ant-[a-zA-Z0-9_-]{32,}")),
]


# Path allowlist for files that legitimately contain key-shaped strings.
# Mirrors the standard practice in gitleaks and trufflehog (test fixtures
# and the scanner's own definition file are exempted by default) and the
# narrower allowlist already encoded in ``.githooks/pre-commit`` lines 48-50.
# Operators are responsible for not pasting real keys into these locations,
# same convention as the hook.
_ALLOWLIST_PREFIXES: tuple[str, ...] = (
    ".githooks/",
    "tests/",
)
_ALLOWLIST_EXACT: frozenset[str] = frozenset({
    "wheeler/portability.py",
})


def _is_allowlisted(archive_path: str) -> bool:
    """Whether ``archive_path`` is a file where key-shaped strings are
    expected to be fixtures or pattern definitions, not real secrets.

    Strips a leading ``project/`` prefix (used by ``scope=project`` archives)
    before matching against the prefix and exact lists.
    """
    rel = archive_path
    if rel.startswith("project/"):
        rel = rel[len("project/"):]
    if rel in _ALLOWLIST_EXACT:
        return True
    return any(rel.startswith(p) for p in _ALLOWLIST_PREFIXES)


def scan_for_secrets(content: bytes, filename: str) -> list[tuple[str, str]]:
    """Scan bytes for leaked API-key shapes.

    Decodes as latin-1 (byte-safe, no surrogates) so binary files do not
    crash the scanner.  Returns a list of ``(pattern_name, matched_snippet)``
    pairs, one entry per match found.  An empty list means clean.

    Only key shapes are checked.  Things like ``import anthropic`` or the
    bare string ``ANTHROPIC_API_KEY`` are not flagged: those are Wheeler
    policy violations enforced by ``.githooks/pre-commit``, not secret
    leakage.  Mixing the two concerns leads to false positives on every
    file that documents the policy.

    Test fixtures (``tests/``), the pre-commit hook (``.githooks/``), and
    this file itself are exempt from the scan, matching the convention used
    by gitleaks, trufflehog, and detect-secrets.
    """
    if _is_allowlisted(filename):
        return []
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
