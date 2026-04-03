"""End-to-end tests for note creation, retrieval, and graph integration.

Tests the full round-trip: add_note -> dual-write to knowledge JSON ->
query_notes -> link to findings -> show_node. Uses RichFakeBackend
for graph operations and real filesystem for knowledge files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wheeler.tools.graph_tools.mutations import (
    add_finding,
    add_note,
    add_question,
    link_nodes,
    set_tier,
)


# ---------------------------------------------------------------------------
# In-memory backend (same pattern as test_task_completion.py)
# ---------------------------------------------------------------------------


class RichFakeBackend:
    """In-memory graph backend for testing without Neo4j."""

    def __init__(self):
        self.nodes: dict[str, list[dict]] = {}
        self.rels: list[tuple[str, str, str, str, str]] = []

    async def create_node(self, label: str, props: dict) -> str:
        self.nodes.setdefault(label, []).append(dict(props))
        return props.get("id", "")

    async def get_node(self, label: str, node_id: str) -> dict | None:
        for props in self.nodes.get(label, []):
            if props.get("id") == node_id:
                return dict(props)
        return None

    async def update_node(self, label: str, node_id: str, properties: dict) -> bool:
        for props in self.nodes.get(label, []):
            if props.get("id") == node_id:
                props.update(properties)
                return True
        return False

    async def delete_node(self, label: str, node_id: str) -> bool:
        lst = self.nodes.get(label, [])
        for i, props in enumerate(lst):
            if props.get("id") == node_id:
                lst.pop(i)
                return True
        return False

    async def create_relationship(
        self, src_label, src_id, rel_type, tgt_label, tgt_id
    ) -> bool:
        self.rels.append((src_label, src_id, rel_type, tgt_label, tgt_id))
        return True

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        return []

    def rels_of_type(self, rel_type: str) -> list[tuple]:
        return [r for r in self.rels if r[2] == rel_type]

    def node_count(self, label: str) -> int:
        return len(self.nodes.get(label, []))


# ===================================================================
# Note creation tests
# ===================================================================


class TestNoteCreation:
    """Test that notes are created with correct structure."""

    async def test_add_note_minimal(self):
        """Note with only content (required field)."""
        backend = RichFakeBackend()
        result = json.loads(await add_note(backend, {
            "content": "Interesting spike pattern at 35C",
        }))
        assert result["node_id"].startswith("N-")
        assert result["label"] == "ResearchNote"
        assert result["status"] == "created"

    async def test_add_note_with_title_and_context(self):
        """Note with all optional fields populated."""
        backend = RichFakeBackend()
        result = json.loads(await add_note(backend, {
            "content": "The VP-loss metric seems biased toward parasol cells",
            "title": "VP-loss bias observation",
            "context": "Reviewing results from population analysis",
        }))
        node_id = result["node_id"]
        node = await backend.get_node("ResearchNote", node_id)
        assert node is not None
        assert node["content"] == "The VP-loss metric seems biased toward parasol cells"
        assert node["title"] == "VP-loss bias observation"
        assert node["context"] == "Reviewing results from population analysis"

    async def test_note_gets_default_tier_and_stability(self):
        """Notes default to generated tier with stability 0.3."""
        backend = RichFakeBackend()
        result = json.loads(await add_note(backend, {
            "content": "Should explore temperature dependence",
        }))
        node = await backend.get_node("ResearchNote", result["node_id"])
        assert node["tier"] == "generated"
        assert node["stability"] == 0.3

    async def test_note_carries_session_id(self):
        """Session ID propagates to note nodes."""
        backend = RichFakeBackend()
        session = "session-test0001"
        await add_note(backend, {
            "content": "Session tracking test",
            "session_id": session,
        })
        notes = backend.nodes.get("ResearchNote", [])
        assert len(notes) == 1
        assert notes[0]["session_id"] == session

    async def test_multiple_notes_independent(self):
        """Multiple notes get distinct IDs."""
        backend = RichFakeBackend()
        ids = []
        for content in ["Note A", "Note B", "Note C"]:
            result = json.loads(await add_note(backend, {"content": content}))
            ids.append(result["node_id"])

        assert len(set(ids)) == 3
        assert backend.node_count("ResearchNote") == 3


# ===================================================================
# Note provenance tests
# ===================================================================


class TestNoteProvenance:
    """Test provenance-completing for notes."""

    async def test_note_with_provenance_from_finding(self):
        """Note created during discussion of a finding gets provenance chain."""
        backend = RichFakeBackend()

        # Prior finding
        finding = json.loads(await add_finding(backend, {
            "description": "Spike rate doubles at 35C",
            "confidence": 0.9,
        }))
        finding_id = finding["node_id"]

        # Note with provenance
        note = json.loads(await add_note(backend, {
            "content": "This doubling might be an artifact of the recording temperature",
            "title": "Temperature artifact concern",
            "execution_kind": "discuss",
            "used_entities": finding_id,
        }))
        assert "provenance" in note
        prov = note["provenance"]

        exec_id = prov["execution_id"]
        assert prov["execution_kind"] == "discuss"
        assert finding_id in prov["linked_inputs"]

        # Verify graph structure
        wgb = backend.rels_of_type("WAS_GENERATED_BY")
        assert len(wgb) == 1
        assert wgb[0][1] == note["node_id"]
        assert wgb[0][4] == exec_id

        used = backend.rels_of_type("USED")
        assert len(used) == 1
        assert used[0][4] == finding_id

    async def test_note_with_multiple_inputs(self):
        """Note referencing multiple findings."""
        backend = RichFakeBackend()

        f1 = json.loads(await add_finding(backend, {
            "description": "Parasol ON tau = 0.12ms", "confidence": 0.85,
        }))
        f2 = json.loads(await add_finding(backend, {
            "description": "Midget ON tau = 0.14ms", "confidence": 0.82,
        }))

        note = json.loads(await add_note(backend, {
            "content": "Consistent tau difference between cell types",
            "execution_kind": "discuss",
            "used_entities": f"{f1['node_id']},{f2['node_id']}",
        }))
        prov = note["provenance"]
        assert len(prov["linked_inputs"]) == 2
        assert f1["node_id"] in prov["linked_inputs"]
        assert f2["node_id"] in prov["linked_inputs"]


# ===================================================================
# Note linking tests
# ===================================================================


class TestNoteLinking:
    """Test that notes can be linked to other graph nodes."""

    async def test_note_relevant_to_question(self):
        """Note linked as RELEVANT_TO an OpenQuestion."""
        backend = RichFakeBackend()

        question = json.loads(await add_question(backend, {
            "question": "Does cell type affect tau?",
            "priority": 7,
        }))
        note = json.loads(await add_note(backend, {
            "content": "Literature suggests yes, see Gerstner 1995",
        }))

        link = json.loads(await link_nodes(backend, {
            "source_id": note["node_id"],
            "target_id": question["node_id"],
            "relationship": "RELEVANT_TO",
        }))
        assert link["status"] == "linked"

        rels = backend.rels_of_type("RELEVANT_TO")
        assert len(rels) == 1
        assert rels[0][1] == note["node_id"]
        assert rels[0][4] == question["node_id"]

    async def test_note_supports_hypothesis(self):
        """Note can SUPPORT a hypothesis (informal evidence)."""
        backend = RichFakeBackend()

        from wheeler.tools.graph_tools.mutations import add_hypothesis

        hyp = json.loads(await add_hypothesis(backend, {
            "statement": "Temperature-dependent gating drives spike rate",
        }))
        note = json.loads(await add_note(backend, {
            "content": "Qualitative observation: cells fire faster when warmed",
        }))

        link = json.loads(await link_nodes(backend, {
            "source_id": note["node_id"],
            "target_id": hyp["node_id"],
            "relationship": "SUPPORTS",
        }))
        assert link["status"] == "linked"

    async def test_note_linked_to_finding(self):
        """Note RELEVANT_TO a finding for annotation."""
        backend = RichFakeBackend()

        finding = json.loads(await add_finding(backend, {
            "description": "VP-loss < 0.15 for all parasol fits",
            "confidence": 0.95,
        }))
        note = json.loads(await add_note(backend, {
            "content": "This threshold should be validated on a holdout set",
        }))

        link = json.loads(await link_nodes(backend, {
            "source_id": note["node_id"],
            "target_id": finding["node_id"],
            "relationship": "RELEVANT_TO",
        }))
        assert link["status"] == "linked"

        rels = backend.rels_of_type("RELEVANT_TO")
        assert len(rels) == 1
        assert rels[0][0] == "ResearchNote"  # source label
        assert rels[0][3] == "Finding"       # target label


# ===================================================================
# Note tier management
# ===================================================================


class TestNoteTierManagement:
    """Test tier promotion/demotion for notes."""

    async def test_note_tier_promotion(self):
        """Note promoted from generated to reference."""
        backend = RichFakeBackend()

        note = json.loads(await add_note(backend, {
            "content": "Confirmed observation worth keeping",
        }))
        node_id = note["node_id"]

        # Verify default
        node = await backend.get_node("ResearchNote", node_id)
        assert node["tier"] == "generated"

        # Promote
        tier_result = json.loads(await set_tier(backend, {
            "node_id": node_id,
            "tier": "reference",
        }))
        assert tier_result["status"] == "updated"

        node = await backend.get_node("ResearchNote", node_id)
        assert node["tier"] == "reference"


# ===================================================================
# Dual-write integration (knowledge files)
# ===================================================================


class TestNoteDualWrite:
    """Test that notes are dual-written to knowledge JSON files."""

    async def test_note_written_to_knowledge_dir(self, tmp_path):
        """Calling execute_tool for add_note creates a JSON file."""
        from unittest.mock import AsyncMock, patch, MagicMock

        from wheeler.tools.graph_tools import execute_tool

        # Create a mock config with knowledge_path pointing to tmp_path
        mock_config = MagicMock()
        mock_config.knowledge_path = str(tmp_path)
        mock_config.graph.backend = "neo4j"
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        # Use our fake backend
        backend = RichFakeBackend()
        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            result_str = await execute_tool(
                "add_note",
                {"content": "Dual-write test note", "title": "Test Title"},
                mock_config,
            )

        result = json.loads(result_str)
        node_id = result["node_id"]

        # Verify JSON file was created
        json_file = tmp_path / f"{node_id}.json"
        assert json_file.exists(), f"Expected {json_file} to exist"

        # Verify file content
        data = json.loads(json_file.read_text())
        assert data["id"] == node_id
        assert data["content"] == "Dual-write test note"
        assert data["title"] == "Test Title"
        assert data["type"] == "ResearchNote"
        assert data["tier"] == "generated"

    async def test_note_readable_after_dual_write(self, tmp_path):
        """Note can be read back from knowledge store after dual-write."""
        from unittest.mock import AsyncMock, patch, MagicMock

        from wheeler.knowledge.store import read_node
        from wheeler.tools.graph_tools import execute_tool

        mock_config = MagicMock()
        mock_config.knowledge_path = str(tmp_path)
        mock_config.graph.backend = "neo4j"
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        backend = RichFakeBackend()
        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            result_str = await execute_tool(
                "add_note",
                {"content": "Round-trip test", "title": "Round Trip"},
                mock_config,
            )

        node_id = json.loads(result_str)["node_id"]

        # Read back through knowledge store
        model = read_node(tmp_path, node_id)
        assert model.content == "Round-trip test"
        assert model.title == "Round Trip"
        assert model.type == "ResearchNote"

    async def test_finding_also_dual_writes(self, tmp_path):
        """Verify findings also dual-write (not just notes)."""
        from unittest.mock import AsyncMock, patch, MagicMock

        from wheeler.knowledge.store import read_node
        from wheeler.tools.graph_tools import execute_tool

        mock_config = MagicMock()
        mock_config.knowledge_path = str(tmp_path)
        mock_config.graph.backend = "neo4j"
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        backend = RichFakeBackend()
        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            result_str = await execute_tool(
                "add_finding",
                {"description": "VP-loss < 0.15", "confidence": 0.95},
                mock_config,
            )

        node_id = json.loads(result_str)["node_id"]
        model = read_node(tmp_path, node_id)
        assert model.description == "VP-loss < 0.15"
        assert model.type == "Finding"
