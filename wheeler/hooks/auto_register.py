"""PostToolUse hook: auto-register research artifacts in the graph.

Fires after Write or Edit. If the written file is a research artifact
(plan, note, document, synthesis, script, dataset, figure) in a tracked
location, this hook calls ensure_artifact so the file is registered as a
graph node without the scientist or the slash command prompt having to
remember.

Idempotent: existing nodes get their hash updated. Non-blocking on
failure: if Neo4j is down, the hook logs a warning record and exits.

The hook reasons about TWO things to decide whether to register:

  1. Extension: must be in `_TRACKED_EXTS` (covers scripts, datasets,
     markdown/tex/pdf documents, and figure files).
  2. Location: markdown files MUST be inside a Wheeler-managed prose dir
     (`.plans/`, `.notes/`, `docs/`, `synthesis/`) so we don't register
     README.md, CHANGELOG.md, etc. Scripts and datasets register from any
     path except `_EXCLUDED_DIRS` (caches, vendor trees, build outputs).

Audit: every fire (success or failure) appends one JSON line to
`.wheeler/auto_register.jsonl`. Failures never surface to the user.

Wired in `.claude/settings.json` PostToolUse on Write|Edit.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# File extensions that map to research-artifact node types in the graph.
# Mirrors `_EXT_TO_TYPE` in wheeler/tools/graph_tools/mutations.py; keep in
# sync if that map grows.
_PROSE_EXTS = frozenset({".md", ".tex", ".pdf"})
_SCRIPT_EXTS = frozenset({".py", ".m", ".r", ".R", ".jl", ".sh"})
_DATASET_EXTS = frozenset({".mat", ".h5", ".hdf5", ".csv", ".npy", ".parquet"})
_FIGURE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".svg", ".tif", ".tiff"})

# Prose files (.md/.tex/.pdf) only register when written into a Wheeler-
# managed directory. Anywhere else they are probably project docs the
# scientist does not want in the graph (README, CHANGELOG, vendor docs).
_PROSE_DIRS = frozenset({".plans", ".notes", "docs", "synthesis"})

# Directories whose contents are NEVER auto-registered, regardless of
# extension. Caches, vendor trees, build outputs, Wheeler's own bookkeeping.
_EXCLUDED_DIRS = frozenset({
    ".venv", ".env", "venv",
    "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git",
    "dist", "build", ".tox",
    ".wheeler",  # Wheeler's own logs and embeddings
})


def _should_register(path: Path) -> bool:
    """Return True if this path is a research artifact worth registering."""
    parts = set(path.parts)
    if parts & _EXCLUDED_DIRS:
        return False
    ext = path.suffix.lower()
    if ext in _PROSE_EXTS:
        return bool(parts & _PROSE_DIRS)
    if ext in _SCRIPT_EXTS or ext in _DATASET_EXTS or ext in _FIGURE_EXTS:
        return True
    return False


def _log(record: dict) -> None:
    """Append one JSON line to the auto-register audit log. Never raises."""
    try:
        log_dir = Path(".wheeler")
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "auto_register.jsonl", "a") as f:
            json.dump(record, f, default=str)
            f.write("\n")
    except Exception:
        # The hook must never surface errors to the user. If we can't even
        # log the audit record, swallow it.
        pass


async def _register(path: str) -> dict:
    """Call ensure_artifact via the canonical execute_tool dispatch.

    Routing through execute_tool ensures the triple-write (graph + JSON
    + synthesis) and the request-log trace_id fire just like every other
    mutation. The hook never writes to the graph directly.
    """
    from wheeler.config import load_config
    from wheeler.tools.graph_tools import execute_tool

    config = load_config()
    raw = await execute_tool(
        "ensure_artifact",
        {"path": path},
        config,
    )
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
    return raw if isinstance(raw, dict) else {"raw": raw}


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_input = data.get("tool_input", {})
    raw_path = tool_input.get("file_path") or tool_input.get("path", "")
    if not raw_path:
        return

    try:
        abs_path = Path(raw_path).resolve()
    except (OSError, ValueError):
        return

    if not abs_path.exists():
        # File was deleted or never written. Nothing to register.
        return

    if not _should_register(abs_path):
        return

    ts = datetime.now(timezone.utc).isoformat()
    try:
        result = asyncio.run(_register(str(abs_path)))
        _log({
            "ts": ts,
            "path": str(abs_path),
            "result": result,
        })
    except Exception as exc:
        # Non-blocking: Neo4j down, config missing, etc. Record and move on.
        _log({
            "ts": ts,
            "path": str(abs_path),
            "error": f"{type(exc).__name__}: {exc}",
        })


if __name__ == "__main__":
    main()
