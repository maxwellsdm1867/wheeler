"""Keep a hosted graph from going idle, and say so honestly when it cannot.

Why this exists: AuraDB Free pauses an instance after 72 hours of inactivity and
DELETES it after 90 days paused. A project whose graph is a free cloud instance
therefore rots on its own if nobody touches it over a long weekend, and the
failure arrives as a hostname that no longer resolves, which is unrecoverable.
This module does the smallest thing that resets that clock.

It performs a READ and a WRITE, not just a connection. A connection alone is a
weak signal to lean a 90-day deletion policy on, and a write is unambiguous
activity. The write is a single idempotent node, so a decade of pings leaves the
graph exactly one node heavier:

    (:WheelerHeartbeat {id: 'heartbeat'})

That node doubles as the record: `last_ping`, `ping_count`, and which machine
did it, so "has anything been keeping this alive?" is answerable from the graph
itself rather than from a log file on one laptop.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

HEARTBEAT_ID = "heartbeat"
HEARTBEAT_LABEL = "WheelerHeartbeat"

# Twice a day. The budget is 72 hours, so this tolerates five consecutive
# failures (a closed laptop over a long weekend) and still lands inside it.
DEFAULT_INTERVAL_HOURS = 12

LOG_NAME = "keepalive.log"


def log_path() -> Path:
    """Where ping results are appended, for diagnosing a scheduler that is not firing."""
    return Path.home() / ".wheeler" / LOG_NAME


def _record(line: str) -> None:
    """Append one line to the keepalive log. Never raises."""
    try:
        target = log_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a") as handle:
            handle.write(line + "\n")
    except OSError as exc:  # pragma: no cover - defensive
        logger.debug("could not write keepalive log: %s", exc)


async def ping(config) -> dict:  # noqa: ANN001 (WheelerConfig, kept import-free)
    """Read from and write to the graph. Returns a result dict, never raises.

    Returning rather than raising because the caller is usually a scheduler with
    nowhere to show a traceback; the dict is what gets logged and what the CLI
    renders.
    """
    from wheeler.machine import machine_id, machine_label
    from wheeler.tools.graph_tools import _get_backend

    now = datetime.now(timezone.utc).isoformat()
    target = f"{config.neo4j.uri} db={config.neo4j.database}"

    try:
        backend = await _get_backend(config)
        # READ
        rows = await backend.run_cypher("MATCH (n) RETURN count(n) AS c")
        node_count = rows[0]["c"] if rows else 0
        # WRITE: one idempotent node, so this never accumulates.
        written = await backend.run_cypher(
            f"MERGE (h:{HEARTBEAT_LABEL} {{id: $id}}) "
            "SET h.last_ping = $now, "
            "    h.ping_count = coalesce(h.ping_count, 0) + 1, "
            "    h.origin_host = $host, h.origin_machine = $machine "
            "RETURN h.ping_count AS count",
            {
                "id": HEARTBEAT_ID,
                "now": now,
                "host": machine_label(),
                "machine": machine_id(),
            },
        )
        count = written[0]["count"] if written else 0
        result = {
            "ok": True,
            "at": now,
            "target": target,
            "nodes": node_count,
            "ping_count": count,
        }
        _record(f"{now}\tOK\t{target}\tnodes={node_count}\tping#{count}")
        return result
    except Exception as exc:
        result = {
            "ok": False,
            "at": now,
            "target": target,
            "error": f"{type(exc).__name__}: {exc}",
        }
        _record(f"{now}\tFAIL\t{target}\t{type(exc).__name__}: {exc}")
        return result


# ── Scheduling ──────────────────────────────────────────────────────
# launchd on macOS, cron elsewhere. Not a generic abstraction over the two: they
# disagree about almost everything, and a wrong plist fails silently, which is
# the worst possible outcome for a job whose entire purpose is to run unattended.

AGENT_LABEL = "com.wheeler.keepalive"


def launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{AGENT_LABEL}.plist"


def render_launch_agent(executable: str, project_root: str, interval_hours: int) -> str:
    """A launchd agent that runs `wheeler keepalive` on an interval.

    `WHEELER_PROJECT_ROOT` is baked in because launchd starts the job with no
    working directory worth having: without it the config resolver would walk up
    from `/` and find no project, so the ping would target the built-in localhost
    default and quietly keep nothing alive.
    """
    seconds = max(1, int(interval_hours)) * 3600
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{AGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{executable}</string>
        <string>keepalive</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>WHEELER_PROJECT_ROOT</key><string>{project_root}</string>
    </dict>
    <key>StartInterval</key><integer>{seconds}</integer>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>{log_path()}</string>
    <key>StandardErrorPath</key><string>{log_path()}</string>
</dict>
</plist>
"""


def render_cron_line(executable: str, project_root: str, interval_hours: int) -> str:
    """A crontab line for non-macOS hosts."""
    hours = max(1, min(23, int(interval_hours)))
    return (
        f"0 */{hours} * * * WHEELER_PROJECT_ROOT={project_root} "
        f"{executable} keepalive >> {log_path()} 2>&1"
    )
