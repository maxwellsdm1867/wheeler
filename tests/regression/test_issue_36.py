"""Regression: issue #36 -- Execution nodes auto-created by _complete_provenance
land graph-only.

The issue body's literal steps (a bare ``add_execution(...)`` call) DO triple-write
correctly on current ``main`` because that path runs through ``execute_tool`` and
is registered in ``_MUTATION_TOOLS``. The actual broken path is indirect: every
other mutation handler (``add_finding``, ``add_note``, ``add_script``, ...) calls
``_complete_provenance`` after creating its primary node when the caller passes
``execution_kind``. That helper calls ``backend.create_node("Execution", ...)``
directly, bypassing ``execute_tool``, so the implicitly-created Execution never
gets its ``knowledge/X-*.json`` or ``synthesis/X-*.md`` written. That is what
the user observes as "63 existing graph-only Executions".

These tests pin the contract: after any mutation that produces a provenance
Execution, the Execution must also have JSON + synthesis on disk.

These tests are expected to FAIL on main until the fix lands.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class FakeBackend:
    """In-memory backend that records create_node + create_relationship calls."""

    def __init__(self) -> None:
        self.nodes: dict[str, tuple[str, dict]] = {}
        self.rels: list[tuple[str, str, str, str, str]] = []

    async def create_node(self, label: str, props: dict) -> str:
        nid = props["id"]
        self.nodes[nid] = (label, dict(props))
        return nid

    async def get_node(self, label: str, node_id: str) -> dict | None:
        if node_id in self.nodes and self.nodes[node_id][0] == label:
            return dict(self.nodes[node_id][1])
        return None

    async def update_node(self, label: str, node_id: str, props: dict) -> bool:
        if node_id in self.nodes:
            self.nodes[node_id][1].update(props)
            return True
        return False

    async def delete_node(self, label: str, node_id: str) -> bool:
        return self.nodes.pop(node_id, None) is not None

    async def create_relationship(
        self, src_label: str, src_id: str, rel_type: str,
        tgt_label: str, tgt_id: str,
    ) -> bool:
        self.rels.append((src_label, src_id, rel_type, tgt_label, tgt_id))
        return True

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        return []


def _make_config(tmp_path: Path) -> MagicMock:
    cfg = MagicMock()
    cfg.knowledge_path = str(tmp_path / "knowledge")
    cfg.synthesis_path = str(tmp_path / "synthesis")
    cfg.graph.backend = "neo4j"
    cfg.neo4j.project_tag = ""
    cfg.neo4j.database = "neo4j"
    return cfg


class TestDirectAddExecution:
    """Baseline: the literal steps in issue #36 already triple-write on main.

    Kept here so any regression on the direct path is caught too.
    """

    async def test_direct_add_execution_writes_json(self, tmp_path: Path) -> None:
        from wheeler.tools.graph_tools import execute_tool

        cfg = _make_config(tmp_path)
        backend = FakeBackend()
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result_str = await execute_tool(
                "add_execution",
                {"kind": "discuss", "description": "test execution"},
                cfg,
            )

        result = json.loads(result_str)
        node_id = result["node_id"]
        assert node_id.startswith("X-")
        json_file = tmp_path / "knowledge" / f"{node_id}.json"
        assert json_file.exists(), (
            f"add_execution must write {json_file}, but it is missing. "
            "Triple-write contract is broken for the direct path."
        )

    async def test_direct_add_execution_writes_synthesis(self, tmp_path: Path) -> None:
        from wheeler.tools.graph_tools import execute_tool

        cfg = _make_config(tmp_path)
        backend = FakeBackend()
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result_str = await execute_tool(
                "add_execution",
                {"kind": "discuss", "description": "test execution"},
                cfg,
            )

        result = json.loads(result_str)
        node_id = result["node_id"]
        synth_file = tmp_path / "synthesis" / f"{node_id}.md"
        assert synth_file.exists(), (
            f"add_execution must write {synth_file}, but it is missing."
        )


class TestProvenanceExecutionTripleWrite:
    """The actual bug: ``_complete_provenance`` creates Execution nodes via
    ``backend.create_node`` directly, skipping ``execute_tool``'s triple-write.

    Repro path: any ``add_*`` mutation called with ``execution_kind`` causes an
    Execution to be auto-created. That Execution must end up with all three
    layers, just like a top-level ``add_execution``.
    """

    async def test_finding_provenance_execution_writes_json(
        self, tmp_path: Path,
    ) -> None:
        from wheeler.tools.graph_tools import execute_tool

        cfg = _make_config(tmp_path)
        backend = FakeBackend()
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result_str = await execute_tool(
                "add_finding",
                {
                    "description": "fixture: provenance test",
                    "confidence": 0.5,
                    "execution_kind": "discuss",
                    "execution_description": "fixture exec from repro",
                },
                cfg,
            )

        result = json.loads(result_str)
        finding_id = result["node_id"]
        prov = result.get("provenance") or {}
        exec_id = prov.get("execution_id")
        assert exec_id, (
            "Expected add_finding(execution_kind=...) to return provenance.execution_id"
        )
        assert exec_id.startswith("X-")

        # Finding writes all three layers. Sanity check that path is healthy.
        assert (tmp_path / "knowledge" / f"{finding_id}.json").exists()
        assert (tmp_path / "synthesis" / f"{finding_id}.md").exists()

        # The auto-created Execution must also write all three layers.
        exec_json = tmp_path / "knowledge" / f"{exec_id}.json"
        assert exec_json.exists(), (
            f"Execution auto-created by _complete_provenance is graph-only: "
            f"{exec_json} is missing. Triple-write contract bypassed."
        )

    async def test_finding_provenance_execution_writes_synthesis(
        self, tmp_path: Path,
    ) -> None:
        from wheeler.tools.graph_tools import execute_tool

        cfg = _make_config(tmp_path)
        backend = FakeBackend()
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result_str = await execute_tool(
                "add_finding",
                {
                    "description": "fixture: provenance test",
                    "confidence": 0.5,
                    "execution_kind": "discuss",
                    "execution_description": "fixture exec from repro",
                },
                cfg,
            )

        result = json.loads(result_str)
        exec_id = (result.get("provenance") or {}).get("execution_id")
        assert exec_id
        exec_md = tmp_path / "synthesis" / f"{exec_id}.md"
        assert exec_md.exists(), (
            f"Execution auto-created by _complete_provenance has no synthesis: "
            f"{exec_md} is missing."
        )

    async def test_note_provenance_execution_writes_both(
        self, tmp_path: Path,
    ) -> None:
        """Same bug surface via add_note (different primary entity, same helper)."""
        from wheeler.tools.graph_tools import execute_tool

        cfg = _make_config(tmp_path)
        backend = FakeBackend()
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            result_str = await execute_tool(
                "add_note",
                {
                    "content": "fixture: note for provenance test",
                    "execution_kind": "discuss",
                    "execution_description": "fixture exec via note",
                },
                cfg,
            )

        result = json.loads(result_str)
        exec_id = (result.get("provenance") or {}).get("execution_id")
        assert exec_id, "add_note(execution_kind=...) must report provenance.execution_id"
        exec_json = tmp_path / "knowledge" / f"{exec_id}.json"
        exec_md = tmp_path / "synthesis" / f"{exec_id}.md"
        assert exec_json.exists(), f"missing {exec_json}"
        assert exec_md.exists(), f"missing {exec_md}"


# Pytest auto-runs async tests when pytest-asyncio's auto mode is on; the
# Wheeler test suite is configured that way already (see existing
# tests/test_e2e_notes.py). If it ever stops being auto, the explicit marker
# below makes the intent clear.
pytestmark = pytest.mark.asyncio
