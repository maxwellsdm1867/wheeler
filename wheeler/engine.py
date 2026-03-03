"""Engine: wraps claude_agent_sdk.query() with mode-aware options."""

from __future__ import annotations

from collections.abc import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    query,
)

from wheeler.modes import DISALLOWED_TOOLS, Mode
from wheeler.modes.state import make_mode_enforcement_hook
from wheeler.prompts import SYSTEM_PROMPTS


async def run_query(
    prompt: str,
    mode: Mode,
    get_mode: callable,
    *,
    max_turns: int = 10,
) -> AsyncIterator[str]:
    """Send *prompt* through the Agent SDK with mode-appropriate settings.

    Yields text chunks as they arrive from the assistant.
    """
    hook = make_mode_enforcement_hook(get_mode)

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPTS[mode],
        disallowed_tools=DISALLOWED_TOOLS[mode],
        hooks={
            "PreToolUse": [HookMatcher(hooks=[hook])],
        },
        permission_mode="bypassPermissions",
        max_turns=max_turns,
    )

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    yield block.text
        elif isinstance(message, ResultMessage):
            if message.is_error:
                yield f"\n[error] {message.result or 'Unknown error'}"
