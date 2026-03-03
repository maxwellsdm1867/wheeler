"""Tests for Wheeler core modules.

Run with: source .venv/bin/activate && python -m pytest tests/ -v
"""

import asyncio

import pytest

from wheeler import __version__
from wheeler.modes import Mode, DISALLOWED_TOOLS
from wheeler.modes.state import make_mode_enforcement_hook, ALLOWED_TOOLS
from wheeler.prompts import SYSTEM_PROMPTS, CITATION_RULE
from wheeler.cli import get_mode, set_mode, _handle_command


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_string():
    assert __version__ == "0.1.0"


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

class TestModes:
    def test_all_modes_exist(self):
        assert set(Mode) == {Mode.CHAT, Mode.PLANNING, Mode.WRITING, Mode.EXECUTE}

    def test_mode_values(self):
        assert Mode.CHAT.value == "chat"
        assert Mode.PLANNING.value == "planning"
        assert Mode.WRITING.value == "writing"
        assert Mode.EXECUTE.value == "execute"

    def test_every_mode_has_system_prompt(self):
        for mode in Mode:
            assert mode in SYSTEM_PROMPTS
            assert len(SYSTEM_PROMPTS[mode]) > 0

    def test_every_mode_has_disallowed_tools(self):
        for mode in Mode:
            assert mode in DISALLOWED_TOOLS
            assert isinstance(DISALLOWED_TOOLS[mode], list)

    def test_every_mode_has_allowed_tools(self):
        for mode in Mode:
            assert mode in ALLOWED_TOOLS
            assert isinstance(ALLOWED_TOOLS[mode], list)

    def test_chat_blocks_execution_tools(self):
        blocked = DISALLOWED_TOOLS[Mode.CHAT]
        assert "Bash" in blocked
        assert "Write" in blocked

    def test_planning_blocks_execution_tools(self):
        blocked = DISALLOWED_TOOLS[Mode.PLANNING]
        assert "Bash" in blocked

    def test_writing_blocks_bash_only(self):
        blocked = DISALLOWED_TOOLS[Mode.WRITING]
        assert "Bash" in blocked
        assert "Write" not in blocked

    def test_execute_blocks_nothing(self):
        assert DISALLOWED_TOOLS[Mode.EXECUTE] == []

    def test_all_prompts_contain_citation_rule(self):
        for mode in Mode:
            assert CITATION_RULE in SYSTEM_PROMPTS[mode]


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

class TestHooks:
    @pytest.fixture
    def chat_hook(self):
        return make_mode_enforcement_hook(lambda: Mode.CHAT)

    @pytest.fixture
    def planning_hook(self):
        return make_mode_enforcement_hook(lambda: Mode.PLANNING)

    @pytest.fixture
    def writing_hook(self):
        return make_mode_enforcement_hook(lambda: Mode.WRITING)

    @pytest.fixture
    def execute_hook(self):
        return make_mode_enforcement_hook(lambda: Mode.EXECUTE)

    @pytest.mark.asyncio
    async def test_chat_denies_bash(self, chat_hook):
        result = await chat_hook({"tool_name": "Bash"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_chat_denies_write(self, chat_hook):
        result = await chat_hook({"tool_name": "Write"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_chat_allows_read(self, chat_hook):
        result = await chat_hook({"tool_name": "Read"}, None, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_chat_allows_grep(self, chat_hook):
        result = await chat_hook({"tool_name": "Grep"}, None, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_planning_denies_bash(self, planning_hook):
        result = await planning_hook({"tool_name": "Bash"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_planning_denies_edit(self, planning_hook):
        result = await planning_hook({"tool_name": "Edit"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_writing_denies_bash(self, writing_hook):
        result = await writing_hook({"tool_name": "Bash"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_writing_allows_write(self, writing_hook):
        result = await writing_hook({"tool_name": "Write"}, None, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_execute_allows_everything(self, execute_hook):
        for tool in ["Bash", "Write", "Edit", "Read", "Grep", "Glob"]:
            result = await execute_hook({"tool_name": tool}, None, {})
            assert result == {}, f"Execute mode should allow {tool}"

    @pytest.mark.asyncio
    async def test_deny_includes_reason(self, chat_hook):
        result = await chat_hook({"tool_name": "Bash"}, None, {})
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert "chat mode" in reason.lower()

    @pytest.mark.asyncio
    async def test_hook_reads_current_mode_dynamically(self):
        """Hook should reflect mode changes after creation."""
        current = Mode.CHAT

        def get_mode():
            return current

        hook = make_mode_enforcement_hook(get_mode)

        # Chat mode — Bash denied
        result = await hook({"tool_name": "Bash"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        # Switch to execute — Bash allowed
        current = Mode.EXECUTE
        result = await hook({"tool_name": "Bash"}, None, {})
        assert result == {}


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

class TestCLI:
    def test_get_set_mode(self):
        original = get_mode()
        set_mode(Mode.PLANNING)
        assert get_mode() == Mode.PLANNING
        set_mode(original)  # restore

    def test_handle_help_is_command(self, capsys):
        assert _handle_command("/help") is True

    def test_handle_quit_raises(self):
        with pytest.raises(SystemExit):
            _handle_command("/quit")

    def test_handle_exit_raises(self):
        with pytest.raises(SystemExit):
            _handle_command("/exit")

    def test_handle_mode_switch(self):
        original = get_mode()
        assert _handle_command("/mode execute") is True
        assert get_mode() == Mode.EXECUTE
        set_mode(original)

    def test_handle_mode_show(self):
        assert _handle_command("/mode") is True

    def test_handle_mode_invalid(self):
        assert _handle_command("/mode nonexistent") is True

    def test_handle_unknown_command(self):
        assert _handle_command("/notacommand") is False


# ---------------------------------------------------------------------------
# Engine (import-only — actual SDK calls need a live CLI)
# ---------------------------------------------------------------------------

class TestEngine:
    def test_run_query_is_importable(self):
        from wheeler.engine import run_query
        assert callable(run_query)

    def test_engine_uses_correct_options_structure(self):
        """Verify ClaudeAgentOptions can be constructed with our params."""
        from claude_agent_sdk import ClaudeAgentOptions, HookMatcher
        from wheeler.modes import DISALLOWED_TOOLS, Mode
        from wheeler.modes.state import make_mode_enforcement_hook
        from wheeler.prompts import SYSTEM_PROMPTS

        hook = make_mode_enforcement_hook(lambda: Mode.CHAT)
        opts = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPTS[Mode.CHAT],
            disallowed_tools=DISALLOWED_TOOLS[Mode.CHAT],
            hooks={"PreToolUse": [HookMatcher(hooks=[hook])]},
            permission_mode="bypassPermissions",
            max_turns=10,
        )
        assert opts.system_prompt == SYSTEM_PROMPTS[Mode.CHAT]
        assert opts.disallowed_tools == ["Bash", "Write", "Edit", "NotebookEdit"]
        assert opts.permission_mode == "bypassPermissions"
        assert opts.max_turns == 10
