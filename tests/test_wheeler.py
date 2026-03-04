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

    def test_create_session_succeeds(self):
        """PromptSession creation should not crash (catches bad kwargs)."""
        from wheeler.cli import _create_session
        pt_session = _create_session()
        assert pt_session is not None

    def test_slash_completer_shows_all_on_slash(self):
        """Typing '/' should show all commands."""
        from prompt_toolkit.document import Document
        from wheeler.cli import SlashCommandCompleter, _COMMAND_META
        completer = SlashCommandCompleter()
        doc = Document("/", cursor_position=1)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == len(_COMMAND_META)

    def test_slash_completer_filters(self):
        """Typing '/ch' should filter to /chat."""
        from prompt_toolkit.document import Document
        from wheeler.cli import SlashCommandCompleter
        completer = SlashCommandCompleter()
        doc = Document("/ch", cursor_position=3)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 1
        assert completions[0].text == "/chat"

    def test_slash_completer_has_descriptions(self):
        """Every completion should have a description."""
        from prompt_toolkit.document import Document
        from wheeler.cli import SlashCommandCompleter
        completer = SlashCommandCompleter()
        doc = Document("/", cursor_position=1)
        completions = list(completer.get_completions(doc, None))
        for c in completions:
            assert c.display_meta, f"{c.text} missing description"

    def test_slash_completer_ignores_normal_text(self):
        """Regular text should not trigger completions."""
        from prompt_toolkit.document import Document
        from wheeler.cli import SlashCommandCompleter
        completer = SlashCommandCompleter()
        doc = Document("hello", cursor_position=5)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_prompt_is_async(self):
        """REPL uses prompt_async, not prompt (which conflicts with asyncio.run)."""
        import inspect
        from wheeler.cli import repl
        source = inspect.getsource(repl)
        assert "prompt_async" in source, "repl() must use prompt_async to avoid nested event loop"
        assert "pt_session.prompt(" not in source.replace("prompt_async", ""), \
            "repl() should not use sync prompt()"

    def test_handle_init_is_command(self):
        assert _handle_command("/init") is True

    def test_handle_graph_returns_async_signal(self):
        """The /graph command returns 'graph' so the REPL can await it."""
        assert _handle_command("/graph") == "graph"

    def test_thinking_verbs_populated(self):
        """Ensure thinking verbs list is non-empty for spinner."""
        from wheeler.cli import _THINKING_VERBS
        assert len(_THINKING_VERBS) >= 10
        assert all(isinstance(v, str) for v in _THINKING_VERBS)


# ---------------------------------------------------------------------------
# Engine (import-only — actual SDK calls need a live CLI)
# ---------------------------------------------------------------------------

class TestEngine:
    def test_api_key_stripped_from_env(self):
        """CRITICAL: ANTHROPIC_API_KEY must never leak into SDK subprocess."""
        import os
        # After importing wheeler.engine, the key should be gone
        import wheeler.engine  # noqa: F401
        assert "ANTHROPIC_API_KEY" not in os.environ, \
            "ANTHROPIC_API_KEY found in os.environ — Wheeler would use API billing!"

    def test_run_query_is_importable(self):
        from wheeler.engine import run_query
        assert callable(run_query)

    def test_config_has_mcp_path(self):
        from wheeler.config import WheelerConfig
        config = WheelerConfig()
        assert config.mcp_config_path == ".mcp.json"

    def test_model_per_mode_defaults(self):
        """Each mode should have a model configured."""
        from wheeler.config import WheelerConfig
        config = WheelerConfig()
        assert config.models.chat == "sonnet"
        assert config.models.planning == "opus"    # scientific reasoning needs best model
        assert config.models.writing == "opus"     # nuanced prose needs best model
        assert config.models.execute == "sonnet"   # code gen, tool use

    def test_model_per_mode_custom(self):
        """Model config should be overridable."""
        from wheeler.config import WheelerConfig, ModelsConfig
        config = WheelerConfig(models=ModelsConfig(chat="haiku", execute="sonnet"))
        assert config.models.chat == "haiku"
        assert config.models.execute == "sonnet"

    def test_run_query_accepts_config(self):
        """Verify run_query accepts a WheelerConfig parameter."""
        import inspect
        from wheeler.engine import run_query
        from wheeler.config import WheelerConfig
        sig = inspect.signature(run_query)
        assert "config" in sig.parameters

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
        assert opts.disallowed_tools == ["Bash", "Write", "Edit", "NotebookEdit", "mcp__neo4j__write_neo4j_cypher"]
        assert opts.permission_mode == "bypassPermissions"
        assert opts.max_turns == 10


# ---------------------------------------------------------------------------
# MCP tool blocking
# ---------------------------------------------------------------------------

class TestMCPToolBlocking:
    @pytest.fixture
    def chat_hook(self):
        return make_mode_enforcement_hook(lambda: Mode.CHAT)

    @pytest.fixture
    def execute_hook(self):
        return make_mode_enforcement_hook(lambda: Mode.EXECUTE)

    @pytest.fixture
    def planning_hook(self):
        return make_mode_enforcement_hook(lambda: Mode.PLANNING)

    @pytest.mark.asyncio
    async def test_chat_blocks_neo4j_write(self, chat_hook):
        result = await chat_hook({"tool_name": "mcp__neo4j__write_neo4j_cypher"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_chat_allows_neo4j_read(self, chat_hook):
        result = await chat_hook({"tool_name": "mcp__neo4j__read_neo4j_cypher"}, None, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_chat_blocks_matlab_execution(self, chat_hook):
        result = await chat_hook({"tool_name": "mcp__matlab__run_matlab_file"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_chat_allows_matlab_readonly(self, chat_hook):
        result = await chat_hook({"tool_name": "mcp__matlab__check_matlab_code"}, None, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_chat_allows_matlab_detect(self, chat_hook):
        result = await chat_hook({"tool_name": "mcp__matlab__detect_matlab_toolboxes"}, None, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_planning_blocks_matlab_execution(self, planning_hook):
        result = await planning_hook({"tool_name": "mcp__matlab__evaluate_matlab_code"}, None, {})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_execute_allows_matlab_execution(self, execute_hook):
        result = await execute_hook({"tool_name": "mcp__matlab__run_matlab_file"}, None, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_execute_allows_neo4j_write(self, execute_hook):
        result = await execute_hook({"tool_name": "mcp__neo4j__write_neo4j_cypher"}, None, {})
        assert result == {}
