"""Structured request logging for MCP tool calls.

Logs every tool call with timestamp, tool name, latency, status,
and session_id. Writes to .wheeler/request_log.jsonl (append-only).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RequestLog:
    timestamp: str
    tool_name: str
    latency_ms: float
    status: str  # "ok" or "error"
    session_id: str
    node_id: str = ""  # if a node was created
    label: str = ""  # if a node was created
    error: str = ""  # if status == "error"
    trace_id: str = ""  # unique per logical MCP tool invocation


class RequestLogger:
    def __init__(self, log_dir: Path) -> None:
        self._log_dir = log_dir
        self._log_path = log_dir / "request_log.jsonl"

    def log(self, entry: RequestLog) -> None:
        """Append a request log entry."""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def read_recent(self, n: int = 50) -> list[dict]:
        """Read last N log entries."""
        if not self._log_path.exists():
            return []
        lines = self._log_path.read_text().strip().split("\n")
        entries: list[dict] = []
        for line in lines[-n:]:
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def query_trace(self, trace_id: str) -> list[dict]:
        """Return all log entries matching a trace_id."""
        return [e for e in self.read_recent(1000) if e.get("trace_id") == trace_id]

    def summary(self) -> dict:
        """Return summary stats: total calls, avg latency, error rate."""
        entries = self.read_recent(1000)
        if not entries:
            return {"total": 0}
        total = len(entries)
        errors = sum(1 for e in entries if e["status"] == "error")
        latencies = [e["latency_ms"] for e in entries]
        sorted_latencies = sorted(latencies)
        return {
            "total": total,
            "errors": errors,
            "error_rate": errors / total,
            "avg_latency_ms": round(sum(latencies) / total, 1),
            "p50_latency_ms": sorted_latencies[total // 2],
            "p99_latency_ms": sorted_latencies[int(total * 0.99)],
        }
