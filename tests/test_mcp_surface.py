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


class TestDocumentationMatchesReality:
    """Counts and placements in prose drift because nothing checks them.

    Found stale during the boundary audit: three server docstrings understated
    their tool counts (8/12/6 against 11/18/10), CLAUDE.md placed graph_gaps in
    mcp_query when it is registered in mcp_core, and ARCHITECTURE.md referred to
    "all five servers" when there are four. Each was written once and never
    re-checked. These tests make the next such edit fail.
    """

    SERVERS = ("mcp_core", "mcp_query", "mcp_mutations", "mcp_ops")

    async def _tools_for(self, module_name):
        import importlib

        module = importlib.import_module(f"wheeler.{module_name}")
        return {t.name for t in await module.mcp.list_tools()}

    async def test_module_docstring_tool_count_matches_reality(self):
        import importlib
        import re

        for module_name in self.SERVERS:
            module = importlib.import_module(f"wheeler.{module_name}")
            actual = len(await self._tools_for(module_name))
            match = re.search(r"\b(\d+)\s+tools\b", module.__doc__ or "")
            assert match, f"{module_name} docstring states no tool count"
            claimed = int(match.group(1))
            assert claimed == actual, (
                f"{module_name} claims {claimed} tools, serves {actual}"
            )

    async def test_server_instructions_only_name_tools_that_server_owns(self):
        """Catches the graph_gaps-in-mcp_query class of error permanently.

        Cross-references are legitimate and common ("For meaning-based search,
        use wheeler_core.search_findings or search_context"), so a foreign tool
        name is allowed only when the owning server is named just before it.
        An unqualified foreign name in a server's own tool list -- which is how
        graph_gaps came to be advertised by mcp_query -- fails.
        """
        import importlib
        import re

        owner: dict[str, str] = {}
        for module_name in self.SERVERS:
            for name in await self._tools_for(module_name):
                owner[name] = module_name

        for module_name in self.SERVERS:
            module = importlib.import_module(f"wheeler.{module_name}")
            owned = await self._tools_for(module_name)
            text = module.mcp.instructions or ""
            for name, owning in sorted(owner.items()):
                if name in owned:
                    continue
                for match in re.finditer(rf"\b{re.escape(name)}\b", text):
                    preceding = text[max(0, match.start() - 45): match.start()]
                    assert f"wheeler_{owning.removeprefix('mcp_')}" in preceding, (
                        f"{module_name} instructions name {name!r} without "
                        f"attributing it to {owning}; it is registered there, "
                        f"not here"
                    )

    async def test_every_tool_is_logged(self):
        """`request_log_summary` was the one tool with no @_logged wrapper."""
        import importlib

        unlogged = []
        for module_name in self.SERVERS:
            module = importlib.import_module(f"wheeler.{module_name}")
            for tool in await module.mcp.list_tools():
                fn = getattr(tool, "fn", None)
                if fn is not None and not getattr(fn, "_wheeler_logged", False):
                    unlogged.append(f"{module_name}.{tool.name}")
        assert unlogged == [], f"tools missing @_logged: {unlogged}"
