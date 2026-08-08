"""The CLI's graph verbs must go through the same write path as the MCP tools.

`wheeler graph add-finding`, `add-question` and `link` opened a sync driver and
issued bare Cypher, skipping the entire triple-write: no knowledge/{id}.json,
no synthesis/{id}.md, no embedding, no WriteReceipt, no trace_id, and for
`link` no synthesis re-render of either endpoint.

The result was worse than "incomplete". A node written that way lands as
`graph_only`, which is exactly the drift class `repair_consistency` cannot fix
(it warns and stops, since regenerating content from a ~100-char graph node is
not supported). The CLI was manufacturing the one inconsistency the repair path
cannot resolve.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from wheeler.tools.cli import app

runner = CliRunner()


class TestVerbsRouteThroughExecuteTool:
    def test_add_finding_uses_execute_tool(self):
        captured: list[tuple[str, dict]] = []

        async def fake_execute_tool(tool_name, args, config):
            captured.append((tool_name, args))
            return json.dumps({"node_id": "F-aaaa1111", "label": "Finding"})

        with patch("wheeler.tools.graph_tools.execute_tool", fake_execute_tool):
            result = runner.invoke(
                app, ["graph", "add-finding", "--desc", "a finding", "-c", "0.8"]
            )

        assert result.exit_code == 0, result.output
        assert captured[0][0] == "add_finding"
        assert captured[0][1]["description"] == "a finding"
        assert "F-aaaa1111" in result.output

    def test_add_question_uses_execute_tool(self):
        captured: list[tuple[str, dict]] = []

        async def fake_execute_tool(tool_name, args, config):
            captured.append((tool_name, args))
            return json.dumps({"node_id": "Q-bbbb2222", "label": "OpenQuestion"})

        with patch("wheeler.tools.graph_tools.execute_tool", fake_execute_tool):
            result = runner.invoke(
                app, ["graph", "add-question", "-q", "why?", "-p", "7"]
            )

        assert result.exit_code == 0, result.output
        assert captured[0][0] == "add_question"
        assert captured[0][1]["priority"] == 7

    def test_link_uses_execute_tool(self):
        captured: list[tuple[str, dict]] = []

        async def fake_execute_tool(tool_name, args, config):
            captured.append((tool_name, args))
            return json.dumps({"status": "linked"})

        with patch("wheeler.tools.graph_tools.execute_tool", fake_execute_tool):
            result = runner.invoke(
                app,
                ["graph", "link", "-s", "F-aaaa1111", "-t", "H-bbbb2222",
                 "-r", "SUPPORTS"],
            )

        assert result.exit_code == 0, result.output
        assert captured[0][0] == "link_nodes"
        assert captured[0][1] == {
            "source_id": "F-aaaa1111",
            "target_id": "H-bbbb2222",
            "relationship": "SUPPORTS",
        }


class TestErrorContract:
    """`execute_tool` reports failure as an `error` KEY, it does not raise.

    Without an explicit check the old try/except would let failures print as
    successes, which is a worse regression than the one being fixed.
    """

    def test_error_dict_exits_nonzero(self):
        async def fake_execute_tool(tool_name, args, config):
            return json.dumps({"error": "Node not found: F-nope"})

        with patch("wheeler.tools.graph_tools.execute_tool", fake_execute_tool):
            result = runner.invoke(
                app,
                ["graph", "link", "-s", "F-aaaa1111", "-t", "H-bbbb2222",
                 "-r", "SUPPORTS"],
            )

        assert result.exit_code == 1, result.output
        assert "Node not found" in result.output
        assert "Linked" not in result.output

    def test_raised_exception_still_exits_nonzero(self):
        async def fake_execute_tool(tool_name, args, config):
            raise RuntimeError("backend down")

        with patch("wheeler.tools.graph_tools.execute_tool", fake_execute_tool):
            result = runner.invoke(
                app, ["graph", "add-finding", "--desc", "x", "-c", "0.5"]
            )

        assert result.exit_code == 1, result.output
        assert "backend down" in result.output

    def test_invalid_relationship_is_still_rejected_before_any_call(self):
        called = False

        async def fake_execute_tool(tool_name, args, config):
            nonlocal called
            called = True
            return json.dumps({"status": "linked"})

        with patch("wheeler.tools.graph_tools.execute_tool", fake_execute_tool):
            result = runner.invoke(
                app,
                ["graph", "link", "-s", "F-a", "-t", "H-b", "-r", "NOT_A_REL"],
            )

        assert result.exit_code == 1
        assert not called, "invalid relationship reached the graph layer"


class TestNoBareCypherRemains:
    """Mechanical guard: the shape of the defect, not one instance of it."""

    def test_cli_issues_no_bare_create_cypher(self):
        import inspect
        import re

        from wheeler.tools import cli

        src = inspect.getsource(cli)
        offenders = [
            line.strip()
            for line in src.splitlines()
            if re.search(r"\bCREATE\s*\(", line)
        ]
        assert offenders == [], (
            f"CLI writes bare Cypher again, bypassing triple-write: {offenders}"
        )

    def test_cli_does_not_open_its_own_write_driver(self):
        import inspect

        from wheeler.tools import cli

        src = inspect.getsource(cli)
        assert "get_sync_driver" not in src, (
            "CLI opens a driver directly again; route mutations through "
            "execute_tool so the triple-write happens"
        )
