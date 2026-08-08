"""Tests for wheeler.mcp_shared module.

Ported from the deleted test_mcp_server.py: the monolith carried private copies
of these helpers, the split servers are now the only home.
"""


class TestSessionId:
    """Verify that _SESSION_ID is generated at module level and has the right format."""

    def test_session_id_format(self):
        from wheeler.mcp_shared import _SESSION_ID
        assert _SESSION_ID.startswith("session-")
        hex_part = _SESSION_ID.removeprefix("session-")
        assert len(hex_part) == 8  # token_hex(4) -> 8 hex chars
        int(hex_part, 16)  # should not raise — valid hex

    def test_session_id_is_stable_within_import(self):
        from wheeler.mcp_shared import _SESSION_ID as sid1
        from wheeler.mcp_shared import _SESSION_ID as sid2
        assert sid1 == sid2  # same module, same value


class TestLoggingIsNonFatal:
    """The request log is observability, not a tool result.

    Regression guard for the defect where `RequestLogger.log` (mkdir +
    open(..., "a"), no exception handling) raised from inside `_logged`, the
    handler re-logged, and THAT raise escaped -- replacing the tool's real
    result or its real exception with the logging error, on every logged tool
    across all four servers. This is what made a read-only or absent
    `.wheeler/` fail everything regardless of what a tool actually needed.
    """

    def _unwritable_logger(self, tmp_path):
        """A RequestLogger pointed under an existing FILE, so writes fail.

        Portable and root-safe: no chmod, which root ignores.
        """
        from wheeler.request_log import RequestLogger

        blocker = tmp_path / "not-a-dir"
        blocker.write_text("x", encoding="utf-8")
        return RequestLogger(blocker / "nested")

    def test_tool_succeeds_when_the_log_is_unwritable(self, tmp_path, monkeypatch):
        import asyncio

        from wheeler import mcp_shared

        monkeypatch.setattr(
            mcp_shared, "_request_logger", self._unwritable_logger(tmp_path)
        )

        @mcp_shared._logged
        async def some_tool():
            return {"ok": True}

        assert asyncio.run(some_tool()) == {"ok": True}

    def test_tool_reraises_its_OWN_exception_not_the_logging_one(
        self, tmp_path, monkeypatch
    ):
        """The actual bug: the logging failure REPLACED the real error."""
        import asyncio

        import pytest

        from wheeler import mcp_shared

        monkeypatch.setattr(
            mcp_shared, "_request_logger", self._unwritable_logger(tmp_path)
        )

        @mcp_shared._logged
        async def failing_tool():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            asyncio.run(failing_tool())

    def test_no_log_file_is_created_when_the_path_is_unwritable(
        self, tmp_path, monkeypatch
    ):
        import asyncio

        from wheeler import mcp_shared

        monkeypatch.setattr(
            mcp_shared, "_request_logger", self._unwritable_logger(tmp_path)
        )

        @mcp_shared._logged
        async def some_tool():
            return {"ok": True}

        asyncio.run(some_tool())
        assert not (tmp_path / "not-a-dir" / "nested").exists()

    def test_logging_still_happens_on_the_happy_path(self, tmp_path, monkeypatch):
        """The guard must not silently disable logging when it CAN write."""
        import asyncio
        import json

        from wheeler import mcp_shared
        from wheeler.request_log import RequestLogger

        monkeypatch.setattr(
            mcp_shared, "_request_logger", RequestLogger(tmp_path / "wheeler")
        )

        @mcp_shared._logged
        async def some_tool():
            return {"node_id": "F-abc123", "label": "Finding"}

        asyncio.run(some_tool())

        lines = [
            json.loads(line)
            for line in (tmp_path / "wheeler" / "request_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        assert [entry["tool_name"] for entry in lines] == ["some_tool"]
        assert lines[0]["status"] == "ok"
        assert lines[0]["node_id"] == "F-abc123"
