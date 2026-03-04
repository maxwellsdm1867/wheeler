"""Engine: wraps claude_agent_sdk.query() with mode-aware options."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

logger = logging.getLogger(__name__)

# --- API key guardrail ---
# Wheeler runs on Max subscription via Claude CLI subprocess.
# If ANTHROPIC_API_KEY leaks into the environment, the CLI uses API billing
# instead of Max. Strip it so the CLI always falls back to OAuth/Max auth.
_STRIPPED_API_KEY = os.environ.pop("ANTHROPIC_API_KEY", None)
if _STRIPPED_API_KEY:
    logger.info(
        "Stripped ANTHROPIC_API_KEY from environment — "
        "Wheeler uses Max subscription, not API billing"
    )

from wheeler.config import WheelerConfig
from wheeler.modes import DISALLOWED_TOOLS, Mode
from wheeler.modes.state import make_mode_enforcement_hook
from wheeler.prompts import SYSTEM_PROMPTS

# SDK stderr log file — captures raw JS stack traces, MCP failures, etc.
_stderr_file = None


def _get_stderr_log_file():
    """Return a file handle for SDK stderr, writing to ~/.wheeler/sdk_stderr.log."""
    global _stderr_file
    if _stderr_file is not None:
        return _stderr_file
    log_dir = Path.home() / ".wheeler"
    log_dir.mkdir(parents=True, exist_ok=True)
    _stderr_file = open(log_dir / "sdk_stderr.log", "a")
    return _stderr_file


# Heavy imports deferred to first query call
_sdk_loaded = False
_sdk = {}  # populated by _ensure_sdk()

# MCP config cache — parsed once, reused across queries
_mcp_cache: dict | None = None
_mcp_cache_path: str | None = None


def _load_mcp_servers(config_path: str) -> dict:
    """Load MCP server config from disk, cached after first read."""
    global _mcp_cache, _mcp_cache_path
    if _mcp_cache is not None and _mcp_cache_path == config_path:
        return _mcp_cache
    path = Path(config_path)
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        _mcp_cache = data.get("mcpServers", {})
        _mcp_cache_path = config_path
        return _mcp_cache
    except Exception:
        logger.debug("MCP config load failed", exc_info=True)
        return {}


def _ensure_sdk():
    global _sdk_loaded, _sdk
    if _sdk_loaded:
        return
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        HookMatcher,
        ResultMessage,
        TextBlock,
        query,
    )
    _sdk.update(
        AssistantMessage=AssistantMessage,
        ClaudeAgentOptions=ClaudeAgentOptions,
        HookMatcher=HookMatcher,
        ResultMessage=ResultMessage,
        TextBlock=TextBlock,
        query=query,
    )
    _sdk_loaded = True


async def run_query(
    prompt: str,
    mode: Mode,
    get_mode: callable,
    *,
    config: WheelerConfig | None = None,
    session_context: str = "",
) -> AsyncIterator[str]:
    """Send *prompt* through the Agent SDK with mode-appropriate settings.

    Yields text chunks as they arrive from the assistant.
    """
    _ensure_sdk()

    hook = make_mode_enforcement_hook(get_mode)

    system_prompt = SYSTEM_PROMPTS[mode]

    # --- Parallel context gathering ---
    # Graph context + workspace scan run concurrently (saves ~130ms).
    graph_context = ""
    ws_context = ""

    async def _fetch_graph():
        if mode is Mode.EXECUTE or config is None:
            return ""
        try:
            from wheeler.graph.context import fetch_context
            return await fetch_context(config)
        except Exception:
            logger.debug("Graph context fetch failed", exc_info=True)
            return ""

    async def _fetch_workspace():
        if config is None:
            return ""
        try:
            from wheeler.workspace import scan_workspace, format_workspace_context
            ws_summary = scan_workspace(config.workspace)
            ctx = format_workspace_context(ws_summary)
            if ctx:
                logger.debug(
                    "Workspace context: %d scripts, %d data files",
                    len(ws_summary.scripts), len(ws_summary.data_files),
                )
            return ctx
        except Exception:
            logger.debug("Workspace scan failed", exc_info=True)
            return ""

    graph_context, ws_context = await asyncio.gather(
        _fetch_graph(), _fetch_workspace()
    )

    if graph_context:
        system_prompt = system_prompt + "\n\n" + graph_context

    # Annotate available graph tools in the system prompt
    from wheeler.tools.graph_tools import TOOL_DEFINITIONS
    tool_names = [t["name"] for t in TOOL_DEFINITIONS]
    system_prompt += (
        "\n\n## Available Graph Tools\n"
        "You have these domain-specific tools for the knowledge graph "
        "(use instead of raw Cypher): " + ", ".join(tool_names) + ".\n"
        "Use graph_gaps in planning mode to find investigation opportunities."
    )

    # Inject data source info if configured
    if config and config.data_sources.epicTreeGUI_root:
        system_prompt += (
            "\n\n## Data Access: epicTreeGUI\n"
            f"Data directory: {config.data_sources.data_dir}\n"
            f"epicTreeGUI root: {config.data_sources.epicTreeGUI_root}\n\n"
            "MATLAB wrapper functions (call via mcp__matlab__evaluate_matlab_code):\n"
            "- wheeler_setup(epicTreeGUI_root) — run first to set MATLAB paths\n"
            "- wheeler_list_data(data_dir) — list available .mat files\n"
            "- wheeler_load_data(filepath, {splitters}) — load & split tree\n"
            "- wheeler_tree_info(var_name, node_path) — inspect a node\n"
            "- wheeler_get_responses(var_name, node_path, stream) — get response data\n"
            "- wheeler_run_analysis(var_name, node_path, type) — run analysis\n\n"
            "Available splitters: splitOnCellType, splitOnContrast, "
            "splitOnF1F2Contrast, splitOnProtocol, splitOnExperimentDate, "
            "splitOnRadiusOrDiameter, splitOnTemporalFrequency, "
            "splitOnHoldingSignal\n\n"
            "WORKFLOW: setup → list_data → load_data → tree_info → "
            "get_responses/run_analysis → log Finding to graph"
        )

    if ws_context:
        system_prompt += "\n\n" + ws_context

    # Inject session context from resumed sessions
    if session_context:
        system_prompt = system_prompt + "\n\n" + session_context

    max_turns = config.max_turns if config else 10

    mcp_servers = _load_mcp_servers(config.mcp_config_path) if config else {}

    # Select model based on mode
    model = None
    if config:
        mode_to_field = {
            Mode.CHAT: config.models.chat,
            Mode.PLANNING: config.models.planning,
            Mode.WRITING: config.models.writing,
            Mode.EXECUTE: config.models.execute,
        }
        model = mode_to_field.get(mode)
        if model:
            logger.debug("Mode %s using model: %s", mode.value, model)

    HookMatcher = _sdk["HookMatcher"]
    ClaudeAgentOptions = _sdk["ClaudeAgentOptions"]

    # Route SDK subprocess stderr to log file instead of terminal.
    # The SDK dumps raw JS stack traces that bypass the stderr callback,
    # so we redirect at the file-descriptor level.
    _stderr_log = logging.getLogger(__name__ + ".sdk_stderr")
    _log_file = _get_stderr_log_file()

    def _on_stderr(line: str) -> None:
        stripped = line.rstrip()
        if stripped:
            _stderr_log.debug("%s", stripped)

    options_kwargs: dict = dict(
        system_prompt=system_prompt,
        disallowed_tools=DISALLOWED_TOOLS[mode],
        hooks={
            "PreToolUse": [HookMatcher(hooks=[hook])],
        },
        permission_mode="bypassPermissions",
        max_turns=max_turns,
        debug_stderr=_log_file,
        stderr=_on_stderr,
    )
    if model:
        options_kwargs["model"] = model
    if mcp_servers:
        options_kwargs["mcp_servers"] = mcp_servers

    options = ClaudeAgentOptions(**options_kwargs)

    AssistantMessage = _sdk["AssistantMessage"]
    ResultMessage = _sdk["ResultMessage"]
    TextBlock = _sdk["TextBlock"]

    async for message in _sdk["query"](prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    yield block.text
        elif isinstance(message, ResultMessage):
            if message.is_error:
                yield f"\n[error] {message.result or 'Unknown error'}"
