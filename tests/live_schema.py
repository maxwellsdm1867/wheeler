"""One place to read the tool schemas Wheeler actually serves.

Tests used to assert against `TOOL_DEFINITIONS`, a parallel schema table in
`graph_tools/__init__.py` that nothing registered from. Because nothing
compared the two, it drifted to 29/29 wrong descriptions and 11/29 wrong
parameter sets, while the suite stayed green: the tests and the dead table
agreed with each other, and neither matched the deployed surface.

Assert against this instead. It is the same schema FastMCP hands an agent.
"""

from __future__ import annotations

from typing import Any


async def live_tools() -> dict[str, Any]:
    """Every registered tool across all four servers, keyed by name.

    Values are FastMCP Tool objects: `.name`, `.description`, `.parameters`
    (a JSON Schema dict with "properties" and "required").
    """
    from wheeler import mcp_core, mcp_mutations, mcp_ops, mcp_query

    tools: dict[str, Any] = {}
    for server in (mcp_core.mcp, mcp_query.mcp, mcp_mutations.mcp, mcp_ops.mcp):
        for tool in await server.list_tools():
            tools[tool.name] = tool
    return tools
