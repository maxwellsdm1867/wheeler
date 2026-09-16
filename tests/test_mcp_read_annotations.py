"""Expose actual read semantics to native MCP clients without trusting writes."""
import pytest

from fastmcp import Client


@pytest.mark.parametrize("module_name", ["wheeler.mcp_core", "wheeler.mcp_query"])
async def test_read_annotations_survive_mcp_transport(module_name):
    import importlib

    module = importlib.import_module(module_name)
    async with Client(module.mcp) as client:
        tools = await client.list_tools()
    writes = {"init_schema", "index_node"}
    for tool in tools:
        if tool.name in writes:
            assert tool.annotations is None or tool.annotations.readOnlyHint is not True
        else:
            assert tool.annotations is not None, tool.name
            assert tool.annotations.readOnlyHint is True, tool.name
            assert tool.annotations.destructiveHint is False, tool.name


async def test_lesson_mutations_are_not_mislabeled_as_reads():
    from wheeler import mcp_mutations

    async with Client(mcp_mutations.mcp) as client:
        tools = await client.list_tools()
    for tool in tools:
        assert tool.annotations is None or tool.annotations.readOnlyHint is not True
