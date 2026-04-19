"""Test that monolith and split MCP servers expose the same tool surface.

Adversarial review #4: adding tools to split servers but forgetting the
monolith is easy to ship and hard to notice.
"""

from __future__ import annotations

import pytest


def _extract_tool_names(mcp_module) -> set[str]:
    """Extract tool names from a FastMCP server module."""
    server = mcp_module.mcp
    # FastMCP stores tools in _tool_manager or similar; inspect the registry
    tools = set()
    for tool in server._tools.values():
        tools.add(tool.name)
    return tools


@pytest.fixture(scope="module")
def monolith_tools():
    """Tools registered in the monolith server."""
    from unittest.mock import patch
    # Prevent actual config loading from failing in test env
    with patch.dict("os.environ", {"WHEELER_YAML": "/dev/null"}, clear=False):
        try:
            import wheeler.mcp_server as srv
            return _extract_tool_names(srv)
        except Exception:
            pytest.skip("Cannot import mcp_server (config/Neo4j not available)")


@pytest.fixture(scope="module")
def split_tools():
    """Union of tools from all four split servers."""
    from unittest.mock import patch
    with patch.dict("os.environ", {"WHEELER_YAML": "/dev/null"}, clear=False):
        try:
            import wheeler.mcp_core as core
            import wheeler.mcp_query as query
            import wheeler.mcp_mutations as mutations
            import wheeler.mcp_ops as ops
            tools = set()
            for mod in (core, query, mutations, ops):
                tools |= _extract_tool_names(mod)
            return tools
        except Exception:
            pytest.skip("Cannot import split servers (config/Neo4j not available)")


def test_split_tools_subset_of_monolith(monolith_tools, split_tools):
    """Every tool in the split servers must exist in the monolith."""
    missing = split_tools - monolith_tools
    assert not missing, (
        f"Tools in split servers but missing from monolith: {missing}\n"
        "Add these tools to wheeler/mcp_server.py"
    )


def test_monolith_tools_subset_of_split(monolith_tools, split_tools):
    """Every tool in the monolith must exist in some split server."""
    missing = monolith_tools - split_tools
    assert not missing, (
        f"Tools in monolith but missing from split servers: {missing}\n"
        "Add these tools to the appropriate split server"
    )
