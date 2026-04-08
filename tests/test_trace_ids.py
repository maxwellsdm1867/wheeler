"""Tests for trace_id support in wheeler.request_log."""

from __future__ import annotations

import json

from wheeler.request_log import RequestLog, RequestLogger


class TestRequestLogTraceIdField:
    def test_request_log_trace_id_field(self):
        """RequestLog accepts trace_id field."""
        entry = RequestLog(
            timestamp="2026-04-08T12:00:00+00:00",
            tool_name="add_finding",
            latency_ms=42.5,
            status="ok",
            session_id="session-abc123",
            trace_id="t-abc123def456",
        )
        assert entry.trace_id == "t-abc123def456"

    def test_request_log_trace_id_default(self):
        """trace_id defaults to empty string when not provided."""
        entry = RequestLog(
            timestamp="2026-04-08T12:00:00+00:00",
            tool_name="add_finding",
            latency_ms=42.5,
            status="ok",
            session_id="session-abc123",
        )
        assert entry.trace_id == ""


class TestRequestLogTraceIdSerialization:
    def test_request_log_trace_id_serialization(self, tmp_path):
        """trace_id appears in JSON output."""
        rl = RequestLogger(tmp_path)
        entry = RequestLog(
            timestamp="2026-04-08T12:00:00+00:00",
            tool_name="add_finding",
            latency_ms=10.0,
            status="ok",
            session_id="session-abc123",
            trace_id="t-aabbccdd",
        )
        rl.log(entry)

        log_file = tmp_path / "request_log.jsonl"
        data = json.loads(log_file.read_text().strip())
        assert data["trace_id"] == "t-aabbccdd"


class TestRequestLogBackwardCompat:
    def test_request_log_backward_compat(self, tmp_path):
        """Old entries without trace_id still load (default empty string)."""
        log_file = tmp_path / "request_log.jsonl"
        # Write an entry that lacks the trace_id field (pre-upgrade format)
        old_entry = {
            "timestamp": "2026-04-01T12:00:00+00:00",
            "tool_name": "graph_health",
            "latency_ms": 5.0,
            "status": "ok",
            "session_id": "session-old",
            "node_id": "",
            "label": "",
            "error": "",
        }
        log_file.write_text(json.dumps(old_entry) + "\n")

        rl = RequestLogger(tmp_path)
        entries = rl.read_recent(10)
        assert len(entries) == 1
        # The raw dict from JSON will not have trace_id, but it should
        # still load without error. get() with default handles this.
        assert entries[0].get("trace_id", "") == ""


class TestQueryTrace:
    def test_query_trace_returns_matching(self, tmp_path):
        """query_trace returns entries with the given trace_id."""
        rl = RequestLogger(tmp_path)
        # Log three entries: two with the target trace_id, one with a different one
        for i, tid in enumerate(["t-abc", "t-abc", "t-xyz"]):
            rl.log(RequestLog(
                timestamp=f"2026-04-08T12:0{i}:00+00:00",
                tool_name=f"tool_{i}",
                latency_ms=float(i),
                status="ok",
                session_id="session-abc123",
                trace_id=tid,
            ))

        results = rl.query_trace("t-abc")
        assert len(results) == 2
        assert all(e["trace_id"] == "t-abc" for e in results)

    def test_query_trace_empty_for_unknown(self, tmp_path):
        """query_trace returns empty list for a trace_id that does not exist."""
        rl = RequestLogger(tmp_path)
        rl.log(RequestLog(
            timestamp="2026-04-08T12:00:00+00:00",
            tool_name="add_finding",
            latency_ms=10.0,
            status="ok",
            session_id="session-abc123",
            trace_id="t-exists",
        ))

        results = rl.query_trace("t-nonexistent")
        assert results == []
