"""Tests for wheeler.request_log module."""

from __future__ import annotations

import json

from wheeler.request_log import RequestLog, RequestLogger


class TestRequestLog:
    def test_creation_defaults(self):
        entry = RequestLog(
            timestamp="2026-03-31T12:00:00+00:00",
            tool_name="add_finding",
            latency_ms=42.5,
            status="ok",
            session_id="session-abc123",
        )
        assert entry.tool_name == "add_finding"
        assert entry.node_id == ""
        assert entry.label == ""
        assert entry.error == ""

    def test_creation_with_all_fields(self):
        entry = RequestLog(
            timestamp="2026-03-31T12:00:00+00:00",
            tool_name="add_finding",
            latency_ms=42.5,
            status="ok",
            session_id="session-abc123",
            node_id="F-3a2b",
            label="Finding",
            error="",
        )
        assert entry.node_id == "F-3a2b"
        assert entry.label == "Finding"

    def test_error_entry(self):
        entry = RequestLog(
            timestamp="2026-03-31T12:00:00+00:00",
            tool_name="add_finding",
            latency_ms=100.0,
            status="error",
            session_id="session-abc123",
            error="Connection refused",
        )
        assert entry.status == "error"
        assert entry.error == "Connection refused"


class TestRequestLoggerLog:
    def test_writes_jsonl(self, tmp_path):
        rl = RequestLogger(tmp_path)
        entry = RequestLog(
            timestamp="2026-03-31T12:00:00+00:00",
            tool_name="add_finding",
            latency_ms=42.5,
            status="ok",
            session_id="session-abc123",
        )
        rl.log(entry)

        log_file = tmp_path / "request_log.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["tool_name"] == "add_finding"
        assert data["latency_ms"] == 42.5
        assert data["status"] == "ok"

    def test_appends_multiple_entries(self, tmp_path):
        rl = RequestLogger(tmp_path)
        for i in range(3):
            rl.log(RequestLog(
                timestamp=f"2026-03-31T12:0{i}:00+00:00",
                tool_name=f"tool_{i}",
                latency_ms=float(i * 10),
                status="ok",
                session_id="session-abc123",
            ))

        log_file = tmp_path / "request_log.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "deep" / "nested"
        rl = RequestLogger(nested)
        rl.log(RequestLog(
            timestamp="2026-03-31T12:00:00+00:00",
            tool_name="test",
            latency_ms=1.0,
            status="ok",
            session_id="session-abc123",
        ))
        assert (nested / "request_log.jsonl").exists()


class TestRequestLoggerReadRecent:
    def test_empty_when_no_file(self, tmp_path):
        rl = RequestLogger(tmp_path)
        assert rl.read_recent() == []

    def test_reads_all_when_fewer_than_n(self, tmp_path):
        rl = RequestLogger(tmp_path)
        for i in range(3):
            rl.log(RequestLog(
                timestamp=f"2026-03-31T12:0{i}:00+00:00",
                tool_name=f"tool_{i}",
                latency_ms=float(i),
                status="ok",
                session_id="session-abc123",
            ))
        entries = rl.read_recent(50)
        assert len(entries) == 3

    def test_reads_last_n(self, tmp_path):
        rl = RequestLogger(tmp_path)
        for i in range(10):
            rl.log(RequestLog(
                timestamp=f"2026-03-31T12:{i:02d}:00+00:00",
                tool_name=f"tool_{i}",
                latency_ms=float(i),
                status="ok",
                session_id="session-abc123",
            ))
        entries = rl.read_recent(3)
        assert len(entries) == 3
        assert entries[0]["tool_name"] == "tool_7"
        assert entries[2]["tool_name"] == "tool_9"

    def test_skips_malformed_lines(self, tmp_path):
        log_file = tmp_path / "request_log.jsonl"
        log_file.write_text('not json\n{"tool_name":"ok","timestamp":"t","latency_ms":1.0,"status":"ok","session_id":"s","node_id":"","label":"","error":""}\n')
        rl = RequestLogger(tmp_path)
        entries = rl.read_recent()
        assert len(entries) == 1
        assert entries[0]["tool_name"] == "ok"


class TestRequestLoggerSummary:
    def test_empty_log(self, tmp_path):
        rl = RequestLogger(tmp_path)
        summary = rl.summary()
        assert summary == {"total": 0}

    def test_all_ok(self, tmp_path):
        rl = RequestLogger(tmp_path)
        for i in range(5):
            rl.log(RequestLog(
                timestamp=f"2026-03-31T12:0{i}:00+00:00",
                tool_name="add_finding",
                latency_ms=float(10 * (i + 1)),  # 10, 20, 30, 40, 50
                status="ok",
                session_id="session-abc123",
            ))
        summary = rl.summary()
        assert summary["total"] == 5
        assert summary["errors"] == 0
        assert summary["error_rate"] == 0.0
        assert summary["avg_latency_ms"] == 30.0
        assert summary["p50_latency_ms"] == 30.0

    def test_mixed_ok_and_error(self, tmp_path):
        rl = RequestLogger(tmp_path)
        # 3 ok, 2 errors
        for i in range(3):
            rl.log(RequestLog(
                timestamp=f"2026-03-31T12:0{i}:00+00:00",
                tool_name="add_finding",
                latency_ms=10.0,
                status="ok",
                session_id="session-abc123",
            ))
        for i in range(2):
            rl.log(RequestLog(
                timestamp=f"2026-03-31T12:1{i}:00+00:00",
                tool_name="add_finding",
                latency_ms=100.0,
                status="error",
                session_id="session-abc123",
                error="Connection refused",
            ))
        summary = rl.summary()
        assert summary["total"] == 5
        assert summary["errors"] == 2
        assert summary["error_rate"] == 0.4

    def test_single_entry(self, tmp_path):
        rl = RequestLogger(tmp_path)
        rl.log(RequestLog(
            timestamp="2026-03-31T12:00:00+00:00",
            tool_name="graph_health",
            latency_ms=5.0,
            status="ok",
            session_id="session-abc123",
        ))
        summary = rl.summary()
        assert summary["total"] == 1
        assert summary["errors"] == 0
        assert summary["avg_latency_ms"] == 5.0
        assert summary["p50_latency_ms"] == 5.0
        assert summary["p99_latency_ms"] == 5.0
