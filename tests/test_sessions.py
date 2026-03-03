"""Tests for wheeler.sessions module."""

import json

import pytest

from wheeler.sessions import (
    Session,
    SessionSummary,
    Turn,
    list_sessions,
    load_session,
    new_session,
    save_session,
)


class TestTurn:
    def test_create(self):
        t = Turn(role="user", content="What about contrast?", mode="chat")
        assert t.role == "user"
        assert t.content == "What about contrast?"
        assert t.mode == "chat"
        assert t.timestamp  # auto-populated

    def test_custom_timestamp(self):
        t = Turn(role="assistant", content="response", mode="chat",
                 timestamp="2024-01-01T00:00:00")
        assert t.timestamp == "2024-01-01T00:00:00"


class TestSession:
    def test_new_session(self):
        s = new_session()
        assert s.session_id.startswith("s-")
        assert len(s.session_id) == 10  # "s-" + 8 hex chars
        assert s.created_at
        assert s.turns == []

    def test_add_turn(self):
        s = new_session()
        s.add_turn("user", "hello", "chat")
        s.add_turn("assistant", "hi there", "chat")
        assert len(s.turns) == 2
        assert s.turns[0].role == "user"
        assert s.turns[1].role == "assistant"

    def test_summary_context_empty(self):
        s = new_session()
        assert s.summary_context() == ""

    def test_summary_context_with_turns(self):
        s = new_session()
        s.add_turn("user", "What about ON parasols?", "chat")
        s.add_turn("assistant", "ON parasol cells show...", "chat")
        ctx = s.summary_context()
        assert "Previous Session Context" in ctx
        assert "Scientist" in ctx
        assert "Wheeler" in ctx
        assert "ON parasol" in ctx

    def test_summary_context_truncates_long_content(self):
        s = new_session()
        s.add_turn("user", "x" * 1000, "chat")
        ctx = s.summary_context()
        # Content should be truncated to 500 chars
        assert len(ctx) < 1000

    def test_summary_context_limits_turns(self):
        s = new_session()
        for i in range(30):
            s.add_turn("user", f"msg {i}", "chat")
        ctx = s.summary_context(max_turns=5)
        # Should only include last 5 turns
        assert "msg 25" in ctx
        assert "msg 29" in ctx
        assert "msg 0" not in ctx


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        s = new_session()
        s.title = "Contrast analysis"
        s.add_turn("user", "What's the contrast index?", "chat")
        s.add_turn("assistant", "The index is 0.73 [F-3a2b]", "chat")

        save_session(s, base=tmp_path)
        loaded = load_session(s.session_id, base=tmp_path)

        assert loaded is not None
        assert loaded.session_id == s.session_id
        assert loaded.title == "Contrast analysis"
        assert len(loaded.turns) == 2
        assert loaded.turns[0].content == "What's the contrast index?"
        assert loaded.turns[1].content == "The index is 0.73 [F-3a2b]"

    def test_load_nonexistent(self, tmp_path):
        assert load_session("s-doesnotexist", base=tmp_path) is None

    def test_save_creates_directory(self, tmp_path):
        subdir = tmp_path / "nested" / "sessions"
        s = new_session()
        save_session(s, base=subdir)
        assert subdir.exists()

    def test_save_file_is_valid_json(self, tmp_path):
        s = new_session()
        s.add_turn("user", "test", "chat")
        path = save_session(s, base=tmp_path)
        with open(path) as f:
            data = json.load(f)
        assert data["session_id"] == s.session_id
        assert len(data["turns"]) == 1

    def test_list_sessions_empty(self, tmp_path):
        assert list_sessions(base=tmp_path) == []

    def test_list_sessions_multiple(self, tmp_path):
        s1 = new_session()
        s1.title = "First"
        s1.add_turn("user", "hello", "chat")
        save_session(s1, base=tmp_path)

        s2 = new_session()
        s2.title = "Second"
        s2.add_turn("user", "hi", "chat")
        s2.add_turn("assistant", "hey", "chat")
        save_session(s2, base=tmp_path)

        sessions = list_sessions(base=tmp_path)
        assert len(sessions) == 2
        ids = {s.session_id for s in sessions}
        assert s1.session_id in ids
        assert s2.session_id in ids

    def test_list_sessions_summary_fields(self, tmp_path):
        s = new_session()
        s.title = "My session"
        s.add_turn("user", "q1", "chat")
        s.add_turn("assistant", "a1", "chat")
        s.add_turn("user", "q2", "planning")
        save_session(s, base=tmp_path)

        sessions = list_sessions(base=tmp_path)
        assert len(sessions) == 1
        summary = sessions[0]
        assert summary.session_id == s.session_id
        assert summary.title == "My session"
        assert summary.turn_count == 3

    def test_overwrite_session(self, tmp_path):
        s = new_session()
        s.add_turn("user", "first", "chat")
        save_session(s, base=tmp_path)

        s.add_turn("user", "second", "chat")
        save_session(s, base=tmp_path)

        loaded = load_session(s.session_id, base=tmp_path)
        assert len(loaded.turns) == 2
