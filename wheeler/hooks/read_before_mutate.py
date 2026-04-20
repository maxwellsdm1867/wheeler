"""PreToolUse hook: block mutations on files not yet Read/Written in this session.

Enforces grounded mutations: you cannot call ensure_artifact, add_plan,
add_document, add_script, add_dataset, or update_node on a path without
having Read or Written that file first. This matches the discipline the
built-in Edit tool enforces ("Read before editing").

Relies on track_file_access.py (PostToolUse hook on Read/Write) to
populate .wheeler/session-reads/{session_id}.txt with accessed paths.

Exit/stdout protocol:
  {"decision": "allow"}  -- proceed
  {"decision": "block", "reason": "..."}  -- block with explanation
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Node ID prefixes for types that carry file paths
_FILE_BEARING_PREFIXES = frozenset({"PL", "D", "W", "S"})


def _respond(decision: str, reason: str = "") -> None:
    """Write a hook response to stdout and exit."""
    resp: dict = {"decision": decision}
    if reason:
        resp["reason"] = reason
    json.dump(resp, sys.stdout)
    sys.exit(0 if decision != "block" else 0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _respond("allow")
        return

    session_id = data.get("session_id", "unknown")
    tool_input = data.get("tool_input", {})

    # Extract path from tool input
    path = tool_input.get("path", "")

    # For update_node without a path arg, check node_id prefix
    if not path and "node_id" in tool_input:
        node_id = tool_input["node_id"]
        prefix = node_id.split("-", 1)[0] if "-" in node_id else ""
        if prefix not in _FILE_BEARING_PREFIXES:
            # Non-file-bearing node type (Finding, Hypothesis, etc.), allow
            _respond("allow")
            return
        # File-bearing update_node without explicit path: allow with warning.
        # Ideally we'd look up the node's path via graph, but that adds
        # latency and a Neo4j dependency to the hook. Accept the gap.
        _respond("allow")
        return

    if not path:
        # No path arg at all, nothing to check
        _respond("allow")
        return

    resolved = str(Path(path).resolve())

    # Check session tracking file
    tracking_file = Path(".wheeler/session-reads") / f"{session_id}.txt"
    if not tracking_file.exists():
        _respond(
            "block",
            f"Read or write {path} first before mutating its graph record. "
            "This enforces grounded mutations.",
        )
        return

    accessed = set(tracking_file.read_text().strip().splitlines())
    if resolved in accessed:
        _respond("allow")
        return

    _respond(
        "block",
        f"Read or write {path} first before mutating its graph record. "
        "This enforces grounded mutations.",
    )


if __name__ == "__main__":
    main()
