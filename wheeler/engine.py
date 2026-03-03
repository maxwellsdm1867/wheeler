"""Engine: wraps claude_agent_sdk.query() with mode-aware options."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

logger = logging.getLogger(__name__)

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    query,
)

from wheeler.config import WheelerConfig
from wheeler.graph.context import fetch_context
from wheeler.workspace import scan_workspace, format_workspace_context
from wheeler.modes import DISALLOWED_TOOLS, Mode
from wheeler.modes.state import make_mode_enforcement_hook
from wheeler.prompts import SYSTEM_PROMPTS
from wheeler.tools.graph_tools import TOOL_DEFINITIONS


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
    hook = make_mode_enforcement_hook(get_mode)

    system_prompt = SYSTEM_PROMPTS[mode]

    # Inject graph context for non-execute modes
    if mode is not Mode.EXECUTE and config is not None:
        try:
            graph_context = await fetch_context(config)
            if graph_context:
                system_prompt = system_prompt + "\n\n" + graph_context
        except Exception:
            logger.debug("Graph context fetch failed", exc_info=True)

    # Annotate available graph tools in the system prompt
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

    # Inject workspace context
    if config is not None:
        try:
            ws_summary = scan_workspace(config.workspace)
            ws_context = format_workspace_context(ws_summary)
            if ws_context:
                system_prompt += "\n\n" + ws_context
                logger.debug(
                    "Workspace context injected: %d scripts, %d data files",
                    len(ws_summary.scripts), len(ws_summary.data_files),
                )
        except Exception:
            logger.debug("Workspace scan failed", exc_info=True)

    # Inject session context from resumed sessions
    if session_context:
        system_prompt = system_prompt + "\n\n" + session_context

    max_turns = config.max_turns if config else 10

    mcp_servers = {}
    if config:
        mcp_path = Path(config.mcp_config_path)
        if mcp_path.exists():
            try:
                with open(mcp_path) as f:
                    mcp_data = json.load(f)
                mcp_servers = mcp_data.get("mcpServers", {})
            except Exception:
                logger.debug("MCP config load failed", exc_info=True)

    options_kwargs: dict = dict(
        system_prompt=system_prompt,
        disallowed_tools=DISALLOWED_TOOLS[mode],
        hooks={
            "PreToolUse": [HookMatcher(hooks=[hook])],
        },
        permission_mode="bypassPermissions",
        max_turns=max_turns,
    )
    if mcp_servers:
        options_kwargs["mcp_servers"] = mcp_servers

    options = ClaudeAgentOptions(**options_kwargs)

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    yield block.text
        elif isinstance(message, ResultMessage):
            if message.is_error:
                yield f"\n[error] {message.result or 'Unknown error'}"
