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
