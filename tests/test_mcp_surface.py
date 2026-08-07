"""Tool-surface guard for the four split MCP servers.

Replaces two deleted files:

- `test_mcp_server.py::TestToolRegistration`, which asserted an exact 50-name set
  against the monolith.
- `test_mcp_surface_parity.py`, which compared the splits against the monolith and
  was skipped once the monolith was deprecated.

With the monolith gone, the splits ARE the surface, so the invariants worth holding
are: the total count, no duplicate tool names across servers, every tool described,
and each server owning only tools that match its documented role
(`CLAUDE.md`: read-only listings -> query; writes -> mutations; validators and
scanners -> ops; everything else -> core).
"""

import pytest

# (module, expected tool count) — the split surface as of the monolith removal.
SERVERS = [
    ("wheeler.mcp_core", 14),
    ("wheeler.mcp_query", 11),
    ("wheeler.mcp_mutations", 18),
    ("wheeler.mcp_ops", 10),
]

TOTAL_TOOLS = 53


async def _tool_names(module_path: str) -> set[str]:
    import importlib

    mod = importlib.import_module(module_path)
    return {t.name for t in await mod.mcp.list_tools()}


@pytest.mark.asyncio
@pytest.mark.parametrize("module_path,expected", SERVERS)
async def test_server_tool_count(module_path, expected):
    """Each split server registers the documented number of tools.

    If this fails you either added a tool without updating the count here and in
    the docs, or registered one in the wrong server.
    """
    names = await _tool_names(module_path)
    assert len(names) == expected, f"{module_path} has {len(names)} tools, expected {expected}"


@pytest.mark.asyncio
async def test_total_surface_is_53_tools():
    names: set[str] = set()
    for module_path, _ in SERVERS:
        names |= await _tool_names(module_path)
    assert len(names) == TOTAL_TOOLS, f"split surface is {len(names)} tools, expected {TOTAL_TOOLS}"


@pytest.mark.asyncio
async def test_no_duplicate_tool_names_across_servers():
    """A tool name must live in exactly one server.

    Two servers exposing the same name means a host sees it twice and the routing
    rule in CLAUDE.md has been broken.
    """
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for module_path, _ in SERVERS:
        for name in await _tool_names(module_path):
            if name in seen:
                collisions.append(f"{name}: {seen[name]} and {module_path}")
            else:
                seen[name] = module_path
    assert not collisions, "duplicate tool names: " + "; ".join(sorted(collisions))


@pytest.mark.asyncio
@pytest.mark.parametrize("module_path,_expected", SERVERS)
async def test_every_tool_has_a_description(module_path, _expected):
    import importlib

    mod = importlib.import_module(module_path)
    undescribed = [t.name for t in await mod.mcp.list_tools() if not (t.description or "").strip()]
    assert not undescribed, f"{module_path} tools missing descriptions: {undescribed}"


@pytest.mark.asyncio
async def test_query_server_is_read_only_by_name():
    """query_* is the read-only listing surface: no mutation verbs may appear there."""
    names = await _tool_names("wheeler.mcp_query")
    mutating = [n for n in names if n.startswith(("add_", "delete_", "update_", "set_", "link_", "unlink_"))]
    assert not mutating, f"mutation-shaped tools in mcp_query: {mutating}"


@pytest.mark.asyncio
async def test_mutations_server_holds_the_write_verbs():
    """The documented write surface lives in mcp_mutations, nowhere else."""
    expected_writes = {
        "add_finding", "add_hypothesis", "add_question", "add_dataset", "add_paper",
        "add_document", "add_note", "add_script", "add_analysis", "add_plan",
        "add_execution", "ensure_artifact", "link_nodes", "unlink_nodes",
        "delete_node", "execute_merge", "set_tier", "update_node",
    }
    names = await _tool_names("wheeler.mcp_mutations")
    assert expected_writes <= names, f"missing write tools: {sorted(expected_writes - names)}"


@pytest.mark.asyncio
async def test_monolith_is_gone():
    """The deprecated monolith must not come back.

    It duplicated every helper in mcp_shared and carried a stale, less-capable
    graph_consistency_check. Re-adding it would reintroduce silent drift.
    """
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("wheeler.mcp_server")
