"""Summarize recent .logs/ entries for reconvene injection.

Reads structured task logs from .logs/, formats them for injection
into the reconvene system prompt so the LLM has actual data to work with.

Usage: python -m wheeler.log_summary [--since HOURS] [--archive]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def summarize_logs(
    logs_dir: str = ".logs",
    since_hours: int = 24,
    archive: bool = False,
) -> str:
    """Read recent logs and return a formatted summary for reconvene."""
    logs_path = Path(logs_dir)
    if not logs_path.exists():
        return ""

    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)

    entries = []
    for f in sorted(logs_path.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        # Skip non-structured logs (old format without task_id)
        if not isinstance(data, dict) or "task_id" not in data:
            continue

        # Filter by time
        ts = data.get("timestamp", "")
        try:
            entry_time = datetime.fromisoformat(ts)
            if entry_time < cutoff:
                continue
        except (ValueError, TypeError):
            pass  # Include entries with unparseable timestamps

        entries.append((f, data))

    if not entries:
        return ""

    # Categorize
    completed = []
    flagged = []

    for f, data in entries:
        if data.get("status") == "flagged":
            flagged.append((f, data))
        else:
            completed.append((f, data))

    lines = [f"## Recent Independent Tasks ({len(entries)} total, last {since_hours}h)\n"]

    if completed:
        lines.append(f"### COMPLETED ({len(completed)})\n")
        for f, data in completed:
            tid = data.get("task_id", "?")
            desc = data.get("task_description", "?")
            model = data.get("model", "?")
            duration = data.get("duration_seconds", 0)
            result = data.get("result", "")
            # Truncate result for context injection
            result_preview = result[:500] + "..." if len(result) > 500 else result

            cv = data.get("citation_validation")
            cite_summary = ""
            if cv:
                if cv.get("ungrounded"):
                    cite_summary = " | citations: UNGROUNDED"
                else:
                    cite_summary = f" | citations: {cv.get('valid', 0)}/{cv.get('total', 0)}"

            lines.append(f"**{tid}** — {desc}")
            lines.append(f"  Model: {model} | Duration: {duration}s{cite_summary}")
            lines.append(f"  Result: {result_preview}")
            lines.append("")

    if flagged:
        lines.append(f"### FLAGGED — NEEDS YOUR JUDGMENT ({len(flagged)})\n")
        for f, data in flagged:
            tid = data.get("task_id", "?")
            desc = data.get("task_description", "?")
            flags = data.get("checkpoint_flags", [])
            result = data.get("result", "")
            result_preview = result[:500] + "..." if len(result) > 500 else result

            lines.append(f"**{tid}** — {desc}")
            for flag in flags:
                lines.append(f"  ⚑ **{flag.get('type', '?')}**: {flag.get('context', '?')[:150]}")
            lines.append(f"  Result: {result_preview}")
            lines.append("")

    summary = "\n".join(lines)

    if archive:
        _archive_logs([f for f, _ in entries], logs_path)

    return summary


def _archive_logs(files: list[Path], logs_path: Path) -> None:
    """Move processed logs to .logs/archive/."""
    archive_dir = logs_path / "archive"
    archive_dir.mkdir(exist_ok=True)
    for f in files:
        f.rename(archive_dir / f.name)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Summarize Wheeler task logs")
    parser.add_argument("--since", type=int, default=24, help="Hours to look back")
    parser.add_argument("--archive", action="store_true", help="Move processed logs to archive")
    parser.add_argument("--logs-dir", default=".logs", help="Logs directory")
    args = parser.parse_args()

    summary = summarize_logs(args.logs_dir, args.since, args.archive)
    if summary:
        print(summary)
    else:
        print("No recent task logs found.")


if __name__ == "__main__":
    main()
