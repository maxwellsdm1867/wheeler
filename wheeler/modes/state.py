"""Mode state machine: enums, tool restrictions, and enforcement logic."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class Mode(Enum):
    CHAT = "chat"
    PLANNING = "planning"
    WRITING = "writing"
    EXECUTE = "execute"


# Positive allow-list per mode (used by engine to set allowed_tools)
ALLOWED_TOOLS: dict[Mode, list[str]] = {
    Mode.CHAT: ["Read", "Glob", "Grep"],
    Mode.PLANNING: ["Read", "Write", "Glob", "Grep"],
    Mode.WRITING: ["Read", "Write", "Edit", "Glob", "Grep"],
    Mode.EXECUTE: [],  # empty = no restriction
}

# Negative block-list per mode (used by hooks as secondary enforcement)
DISALLOWED_TOOLS: dict[Mode, list[str]] = {
    Mode.CHAT: ["Bash", "Write", "Edit", "NotebookEdit"],
    Mode.PLANNING: ["Bash", "Edit", "NotebookEdit"],
    Mode.WRITING: ["Bash"],
    Mode.EXECUTE: [],
}


def make_mode_enforcement_hook(
    get_mode: callable,
):
    """Return a hook callback that enforces tool restrictions for the current mode.

    Args:
        get_mode: A callable returning the current Mode.
    """

    async def mode_enforcement_hook(
        input_data,
        tool_use_id: str | None,
        context,
    ):
        mode = get_mode()
        tool_name: str = input_data.get("tool_name", "")
        blocked = DISALLOWED_TOOLS.get(mode, [])

        if tool_name in blocked:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"{mode.value} mode — {tool_name} is not allowed. "
                        f"Switch to a different mode first."
                    ),
                }
            }
        return {}

    return mode_enforcement_hook
