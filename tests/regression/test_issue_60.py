"""Regression test for issue #60: silent triple-write drift.

Tests that newly-created nodes appear consistently across all three layers:
graph, JSON, and synthesis. Also verifies that deprecated Analysis nodes
from pre-migration are detected by consistency check.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.config import load_config
from wheeler.consistency import check_consistency
from wheeler.models import ScriptModel, ExecutionModel


class TestTripleWriteConsistency:
    """Verify that new nodes written via execute_tool appear in all three layers."""

    async def test_add_script_writes_all_three_layers(self, tmp_path):
        """When add_script succeeds, graph, JSON, and synthesis all get the node."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.knowledge.store import read_node
        from wheeler.knowledge.render import render_synthesis

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Create a dummy script file
        script_file = tmp_path / "test_script.py"
        script_file.write_text("print('hello')")

        # Execute add_script
        result_str = await execute_tool(
            "add_script",
            {
                "path": str(script_file),
                "language": "python",
                "session_id": "test-session",
            },
            config,
        )
        result = json.loads(result_str)
        assert "error" not in result, result
        script_id = result.get("node_id")
        assert script_id.startswith("S-"), f"Expected S- prefix, got {script_id}"

        # Verify JSON file exists and is readable
        json_path = knowledge_dir / f"{script_id}.json"
        assert json_path.exists(), f"JSON file missing: {json_path}"
        json_model = read_node(knowledge_dir, script_id)
        assert isinstance(json_model, ScriptModel)
        assert json_model.language == "python"

        # Verify synthesis file exists and is readable
        synthesis_path = synthesis_dir / f"{script_id}.md"
        assert synthesis_path.exists(), f"Synthesis file missing: {synthesis_path}"
        markdown = synthesis_path.read_text()
        assert "python" in markdown.lower() or script_id in markdown

        # Verify graph consistency: this node should NOT appear in json_only
        # (it was just created via triple-write)
        from wheeler.tools.graph_tools import _get_backend

        backend = await _get_backend(config)
        records = await backend.run_cypher(
            f"MATCH (n:Script {{id: $nid}}) RETURN n.id AS id", {"nid": script_id}
        )
        assert len(records) > 0, f"Script node {script_id} missing from graph"
        assert records[0]["id"] == script_id

    async def test_add_finding_writes_all_three_layers(self, tmp_path):
        """When add_finding succeeds, all three layers receive the node."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.knowledge.store import read_node
        from wheeler.models import FindingModel

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Execute add_finding
        result_str = await execute_tool(
            "add_finding",
            {
                "description": "Test finding for triple-write",
                "confidence": 0.95,
                "session_id": "test-session",
            },
            config,
        )
        result = json.loads(result_str)
        assert "error" not in result, result
        finding_id = result.get("node_id")
        assert finding_id.startswith("F-"), f"Expected F- prefix, got {finding_id}"

        # Verify all three layers have the node
        json_path = knowledge_dir / f"{finding_id}.json"
        assert json_path.exists(), f"JSON file missing: {json_path}"
        json_model = read_node(knowledge_dir, finding_id)
        assert isinstance(json_model, FindingModel)
        assert json_model.description == "Test finding for triple-write"

        synthesis_path = synthesis_dir / f"{finding_id}.md"
        assert synthesis_path.exists(), f"Synthesis file missing: {synthesis_path}"

        # Graph check
        from wheeler.tools.graph_tools import _get_backend

        backend = await _get_backend(config)
        records = await backend.run_cypher(
            f"MATCH (n:Finding {{id: $nid}}) RETURN n.id AS id", {"nid": finding_id}
        )
        assert len(records) > 0, f"Finding node {finding_id} missing from graph"

    async def test_consistency_check_sees_new_nodes_in_all_layers(self, tmp_path):
        """After triple-write, consistency check should report zero drift."""
        from wheeler.tools.graph_tools import execute_tool, _get_backend

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Create a script node via triple-write
        script_file = tmp_path / "test.py"
        script_file.write_text("x = 1")

        result_str = await execute_tool(
            "add_script",
            {"path": str(script_file), "language": "python", "session_id": "test"},
            config,
        )
        result = json.loads(result_str)
        script_id = result["node_id"]

        # Run consistency check
        report = await check_consistency(config)

        # The newly-created node should appear in all three
        assert report.total_json >= 1
        assert report.total_synthesis >= 1
        assert report.total_graph >= 1

        # And it should NOT be in any diff list
        assert script_id not in report.json_only, (
            f"New node {script_id} incorrectly reported in json_only; "
            "triple-write failed"
        )
        assert script_id not in report.synthesis_missing, (
            f"New node {script_id} incorrectly reported in synthesis_missing; "
            "triple-write incomplete"
        )
        assert script_id not in report.graph_only, (
            f"New node {script_id} incorrectly reported in graph_only; "
            "graph write failed"
        )

    async def test_detects_legacy_analysis_nodes(self, tmp_path):
        """Legacy A-* Analysis JSON files (pre-migration) should be detected as json_only."""
        from wheeler.config import load_config

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Simulate a legacy Analysis JSON file (from before the migration)
        # This would have type="Analysis" but Analysis no longer exists as a node type
        legacy_analysis_id = "A-legacy001"
        legacy_json = {
            "id": legacy_analysis_id,
            "type": "Analysis",  # This type no longer exists
            "script_path": "/some/path/script.py",
            "created": "2026-01-01T00:00:00+00:00",
            "updated": "2026-01-01T00:00:00+00:00",
        }
        analysis_path = knowledge_dir / f"{legacy_analysis_id}.json"
        analysis_path.write_text(json.dumps(legacy_json))

        # Run consistency check with mocked backend (graph returns nothing)
        class FakeBackend:
            async def run_cypher(self, query, parameters=None):
                return []  # Graph returns no nodes

            async def initialize(self):
                pass

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=FakeBackend(),
        ):
            report = await check_consistency(config)

        # The legacy Analysis node should be in json_only
        assert legacy_analysis_id in report.json_only, (
            "Legacy Analysis node should be detected as json_only "
            "(exists in JSON but not in graph)"
        )
        assert report.total_json >= 1
        assert report.total_graph == 0

    async def test_provenance_execution_writes_all_layers(self, tmp_path):
        """When execution_kind is set, the auto-created Execution should reach all layers."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.knowledge.store import read_node
        from wheeler.models import ExecutionModel

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Add a finding with provenance-completing execution_kind
        result_str = await execute_tool(
            "add_finding",
            {
                "description": "Result from a script run",
                "confidence": 0.8,
                "execution_kind": "script_run",
                "execution_description": "Ran analysis.py",
                "session_id": "test-session",
            },
            config,
        )
        result = json.loads(result_str)
        assert "error" not in result

        # The provenance entry should include an execution ID
        prov = result.get("provenance", {})
        exec_id = prov.get("execution_id")
        assert exec_id is not None, "No execution_id in provenance response"
        assert exec_id.startswith("X-"), f"Expected X- prefix for Execution, got {exec_id}"

        # Verify the Execution appears in JSON
        json_path = knowledge_dir / f"{exec_id}.json"
        assert json_path.exists(), (
            f"Execution {exec_id} JSON file missing; "
            "provenance fan-out did not write JSON"
        )
        exec_model = read_node(knowledge_dir, exec_id)
        assert isinstance(exec_model, ExecutionModel)

        # Verify the Execution appears in synthesis
        synthesis_path = synthesis_dir / f"{exec_id}.md"
        assert synthesis_path.exists(), (
            f"Execution {exec_id} synthesis file missing; "
            "provenance fan-out incomplete"
        )

        # Verify the Execution appears in graph
        from wheeler.tools.graph_tools import _get_backend

        backend = await _get_backend(config)
        records = await backend.run_cypher(
            f"MATCH (n:Execution {{id: $nid}}) RETURN n.id AS id", {"nid": exec_id}
        )
        assert len(records) > 0, (
            f"Execution {exec_id} missing from graph; "
            "provenance fan-out did not create graph node"
        )
