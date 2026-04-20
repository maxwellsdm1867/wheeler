"""PostToolUse hook: track file paths accessed via Read/Write.

Appends resolved absolute paths to a session-local tracking file so
that read_before_mutate.py can verify grounded mutations.

Tracking files live at .wheeler/session-reads/{session_id}.txt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    session_id = data.get("session_id", "unknown")
    tool_input = data.get("tool_input", {})

    # Read uses file_path, Write uses file_path
    path = tool_input.get("file_path") or tool_input.get("path", "")
    if not path:
        return

    resolved = str(Path(path).resolve())

    tracking_dir = Path(".wheeler/session-reads")
    tracking_dir.mkdir(parents=True, exist_ok=True)
    tracking_file = tracking_dir / f"{session_id}.txt"

    with open(tracking_file, "a") as f:
        f.write(resolved + "\n")


if __name__ == "__main__":
    main()
