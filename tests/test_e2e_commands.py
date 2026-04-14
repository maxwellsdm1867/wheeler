"""End-to-end tests for Wheeler command workflows.

Tests complete research workflows as they happen through the tool layer:
discuss -> plan -> execute -> reconvene patterns, MCP tool round-trips,
and multi-step graph construction with dual-write verification.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.tools.graph_tools.mutations import (
    add_dataset,
    add_document,
    add_finding,
    add_hypothesis,
    add_note,
    add_paper,
    add_question,
    add_script,
    link_nodes,
    set_tier,
)


# ---------------------------------------------------------------------------
# In-memory backend
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

    def rels_from(self, node_id: str) -> list[tuple]:
        return [r for r in self.rels if r[1] == node_id]

    def rels_to(self, node_id: str) -> list[tuple]:
        return [r for r in self.rels if r[4] == node_id]

    def node_count(self, label: str) -> int:
        return len(self.nodes.get(label, []))

    def all_node_ids(self) -> list[str]:
        return [p["id"] for nodes in self.nodes.values() for p in nodes if "id" in p]


# ===================================================================
# Discuss -> Plan -> Execute workflow
# ===================================================================


class TestDiscussPlanExecute:
    """Simulate the discuss -> plan -> execute workflow through mutations."""

    async def test_discuss_captures_question_and_note(self):
        """Discuss phase: scientist raises question, Wheeler captures note.

        Simulates /wh:discuss producing an OpenQuestion and ResearchNote.
        """
        backend = RichFakeBackend()
        session = "session-discuss01"

        # Scientist asks a question during discussion
        q_result = json.loads(await add_question(backend, {
            "question": "Why does VP-loss vary across cell types?",
            "priority": 8,
            "session_id": session,
        }))
        q_id = q_result["node_id"]
        assert q_id.startswith("Q-")

        # Wheeler captures a note about the discussion context
        n_result = json.loads(await add_note(backend, {
            "content": "Scientist hypothesizes that receptive field size correlates with VP-loss",
            "title": "RF size hypothesis from discussion",
            "context": "During /wh:discuss about VP-loss variation",
            "session_id": session,
        }))
        n_id = n_result["node_id"]

        # Link note to question
        link = json.loads(await link_nodes(backend, {
            "source_id": n_id,
            "target_id": q_id,
            "relationship": "RELEVANT_TO",
        }))
        assert link["status"] == "linked"

        # Verify both share session
        q_node = await backend.get_node("OpenQuestion", q_id)
        n_node = await backend.get_node("ResearchNote", n_id)
        assert q_node["session_id"] == session
        assert n_node["session_id"] == session

    async def test_plan_produces_hypothesis_from_question(self):
        """Plan phase: question leads to hypothesis with RELEVANT_TO link.

        Simulates /wh:plan taking a question and producing a testable hypothesis.
        """
        backend = RichFakeBackend()

        # Question from discuss phase
        q = json.loads(await add_question(backend, {
            "question": "Is spike timing precision cell-type specific?",
            "priority": 9,
        }))
        q_id = q["node_id"]

        # Plan phase produces a hypothesis
        h = json.loads(await add_hypothesis(backend, {
            "statement": "Parasol cells have tighter spike timing than midget cells",
            "execution_kind": "discuss",
            "used_entities": q_id,
        }))
        h_id = h["node_id"]
        assert "provenance" in h

        # Hypothesis is linked to the question
        link = json.loads(await link_nodes(backend, {
            "source_id": h_id,
            "target_id": q_id,
            "relationship": "RELEVANT_TO",
        }))
        assert link["status"] == "linked"

    async def test_execute_produces_finding_from_script(self):
        """Execute phase: script runs, produces finding, links to hypothesis.

        Simulates /wh:execute running an analysis script and recording results.
        """
        backend = RichFakeBackend()

        # Prior hypothesis from plan phase
        h = json.loads(await add_hypothesis(backend, {
            "statement": "Parasol cells have tighter spike timing",
        }))
        h_id = h["node_id"]

        # Register the analysis script
        s = json.loads(await add_script(backend, {
            "path": "/analysis/spike_timing.py",
            "language": "python",
            "hash": "abc123",
        }))
        s_id = s["node_id"]

        # Register the dataset
        d = json.loads(await add_dataset(backend, {
            "path": "/data/spikes.mat",
            "type": "mat",
            "description": "Spike recordings from parasol and midget cells",
        }))
        d_id = d["node_id"]

        # Execute: script + dataset -> finding
        f = json.loads(await add_finding(backend, {
            "description": "Parasol jitter = 0.8ms vs midget jitter = 2.1ms (p < 0.001)",
            "confidence": 0.92,
            "execution_kind": "script",
            "used_entities": f"{s_id},{d_id}",
            "execution_description": "Spike timing analysis across cell types",
        }))
        f_id = f["node_id"]
        assert "provenance" in f

        # Link finding to hypothesis it supports
        link = json.loads(await link_nodes(backend, {
            "source_id": f_id,
            "target_id": h_id,
            "relationship": "SUPPORTS",
        }))
        assert link["status"] == "linked"

        # Verify complete graph structure
        assert backend.node_count("Hypothesis") == 1
        assert backend.node_count("Script") == 1
        assert backend.node_count("Dataset") == 1
        assert backend.node_count("Finding") == 1
        assert backend.node_count("Execution") == 1

        # Finding -> Execution -> Script + Dataset
        prov = f["provenance"]
        assert len(prov["linked_inputs"]) == 2
        assert s_id in prov["linked_inputs"]
        assert d_id in prov["linked_inputs"]

    async def test_full_discuss_plan_execute_cycle(self):
        """Complete workflow: question -> hypothesis -> script -> finding -> document.

        End-to-end simulation of a full research cycle.
        """
        backend = RichFakeBackend()
        session = "session-full-cycle"

        # 1. DISCUSS: identify question
        q = json.loads(await add_question(backend, {
            "question": "What drives VP-loss variation?",
            "priority": 9,
            "session_id": session,
        }))

        # 2. PLAN: formulate hypothesis
        h = json.loads(await add_hypothesis(backend, {
            "statement": "Receptive field size determines VP-loss",
            "execution_kind": "discuss",
            "used_entities": q["node_id"],
            "session_id": session,
        }))

        # 3. EXECUTE: run analysis
        s = json.loads(await add_script(backend, {
            "path": "/analysis/rf_vploss.py",
            "language": "python",
            "session_id": session,
        }))

        f = json.loads(await add_finding(backend, {
            "description": "RF diameter correlates with VP-loss (r=0.73, p<0.01)",
            "confidence": 0.88,
            "execution_kind": "script",
            "used_entities": s["node_id"],
            "session_id": session,
        }))

        # Link finding to hypothesis
        json.loads(await link_nodes(backend, {
            "source_id": f["node_id"],
            "target_id": h["node_id"],
            "relationship": "SUPPORTS",
        }))

        # 4. WRITE: create document citing the finding
        p = json.loads(await add_paper(backend, {
            "title": "Receptive field structure in retinal ganglion cells",
            "authors": "Smith et al.",
            "year": 2020,
            "session_id": session,
        }))

        doc = json.loads(await add_document(backend, {
            "title": "Results: RF-VP-loss correlation",
            "path": "docs/results_rf.md",
            "status": "draft",
            "execution_kind": "write",
            "used_entities": f"{f['node_id']},{p['node_id']}",
            "session_id": session,
        }))

        # Verify final graph
        assert backend.node_count("OpenQuestion") == 1
        assert backend.node_count("Hypothesis") == 1
        assert backend.node_count("Script") == 1
        assert backend.node_count("Finding") == 1
        assert backend.node_count("Paper") == 1
        assert backend.node_count("Document") == 1
        # 3 Executions: hypothesis (discuss), finding (script), document (write)
        assert backend.node_count("Execution") == 3

        # Verify relationship types present
        assert len(backend.rels_of_type("WAS_GENERATED_BY")) == 3
        assert len(backend.rels_of_type("SUPPORTS")) == 1
        assert len(backend.rels_of_type("USED")) >= 3


# ===================================================================
# MCP tool round-trip tests
# ===================================================================


class TestMCPToolRoundTrip:
    """Test MCP tools through execute_tool dispatch with dual-write."""

    async def test_add_finding_round_trip(self, tmp_path):
        """Finding created via execute_tool is readable from knowledge store."""
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
                {"description": "Round-trip finding", "confidence": 0.77},
                mock_config,
            )

        result = json.loads(result_str)
        node_id = result["node_id"]
        assert node_id.startswith("F-")

        # Read back
        model = read_node(tmp_path, node_id)
        assert model.description == "Round-trip finding"
        assert model.type == "Finding"

    async def test_add_hypothesis_round_trip(self, tmp_path):
        """Hypothesis created via execute_tool is readable from knowledge store."""
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
                "add_hypothesis",
                {"statement": "Round-trip hypothesis"},
                mock_config,
            )

        result = json.loads(result_str)
        model = read_node(tmp_path, result["node_id"])
        assert model.statement == "Round-trip hypothesis"
        assert model.type == "Hypothesis"

    async def test_add_question_round_trip(self, tmp_path):
        """Question created via execute_tool is readable from knowledge store."""
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
                "add_question",
                {"question": "Round-trip question?", "priority": 7},
                mock_config,
            )

        result = json.loads(result_str)
        model = read_node(tmp_path, result["node_id"])
        assert model.question == "Round-trip question?"
        assert model.type == "OpenQuestion"

    async def test_add_paper_round_trip(self, tmp_path):
        """Paper created via execute_tool has reference tier."""
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
                "add_paper",
                {"title": "Spike Response Model", "authors": "Gerstner", "year": 1995},
                mock_config,
            )

        result = json.loads(result_str)
        model = read_node(tmp_path, result["node_id"])
        assert model.title == "Spike Response Model"
        assert model.tier == "reference"  # Papers are always reference

    async def test_add_dataset_round_trip(self, tmp_path):
        """Dataset created via execute_tool is readable from knowledge store."""
        from wheeler.knowledge.store import read_node
        from wheeler.tools.graph_tools import execute_tool

        mock_config = MagicMock()
        mock_config.knowledge_path = str(tmp_path)
        mock_config.graph.backend = "neo4j"
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        # Create a real file so path validation passes
        data_file = tmp_path / "spikes.mat"
        data_file.write_bytes(b"fake mat data")

        backend = RichFakeBackend()
        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            result_str = await execute_tool(
                "add_dataset",
                {"path": str(data_file), "type": "mat", "description": "Spike data"},
                mock_config,
            )

        result = json.loads(result_str)
        model = read_node(tmp_path, result["node_id"])
        assert model.path == str(data_file)
        assert model.type == "Dataset"

    async def test_add_document_round_trip(self, tmp_path):
        """Document created via execute_tool is readable from knowledge store."""
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
                "add_document",
                {"title": "Methods Draft", "path": "docs/methods.md", "status": "draft"},
                mock_config,
            )

        result = json.loads(result_str)
        model = read_node(tmp_path, result["node_id"])
        assert model.title == "Methods Draft"
        assert model.type == "Document"

    async def test_add_script_round_trip(self, tmp_path):
        """Script created via execute_tool is readable from knowledge store."""
        from wheeler.knowledge.store import read_node
        from wheeler.tools.graph_tools import execute_tool

        mock_config = MagicMock()
        mock_config.knowledge_path = str(tmp_path)
        mock_config.graph.backend = "neo4j"
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        # Create a real file so path validation passes
        script_file = tmp_path / "fit.py"
        script_file.write_text("print('hello')")

        backend = RichFakeBackend()
        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            result_str = await execute_tool(
                "add_script",
                {"path": str(script_file), "language": "python", "hash": "deadbeef"},
                mock_config,
            )

        result = json.loads(result_str)
        model = read_node(tmp_path, result["node_id"])
        assert model.path == str(script_file)
        assert model.type == "Script"


# ===================================================================
# Stale script detection E2E
# ===================================================================


class TestStaleScriptDetection:
    """Test stale script detection with real files."""

    def test_hash_changes_on_file_modification(self, tmp_path):
        """Modifying a script file changes its hash."""
        from wheeler.graph.provenance import hash_file

        script = tmp_path / "analysis.py"
        script.write_text("import numpy as np\nresult = np.mean(data)\n")
        hash1 = hash_file(script)

        # Modify the script
        script.write_text("import numpy as np\nresult = np.median(data)\n")
        hash2 = hash_file(script)

        assert hash1 != hash2

    def test_hash_stable_for_unchanged_file(self, tmp_path):
        """Hash is deterministic for unchanged files."""
        from wheeler.graph.provenance import hash_file

        script = tmp_path / "stable.py"
        script.write_text("x = 42\n")

        assert hash_file(script) == hash_file(script)

    async def test_stale_detection_workflow(self, tmp_path):
        """Full workflow: register script, modify, detect stale."""
        from wheeler.graph.provenance import hash_file

        backend = RichFakeBackend()

        # Create a script file and register it
        script_file = tmp_path / "model_fit.py"
        script_file.write_text("import scipy\nresult = scipy.optimize.minimize(f, x0)\n")
        original_hash = hash_file(script_file)

        s = json.loads(await add_script(backend, {
            "path": str(script_file),
            "language": "python",
            "hash": original_hash,
        }))
        s_id = s["node_id"]

        # Create a finding from this script
        f = json.loads(await add_finding(backend, {
            "description": "Optimal tau = 0.12ms",
            "confidence": 0.85,
            "execution_kind": "script",
            "used_entities": s_id,
        }))

        # Verify script hash matches
        script_node = await backend.get_node("Script", s_id)
        assert script_node["hash"] == original_hash

        # Modify the script
        script_file.write_text("import scipy\nresult = scipy.optimize.minimize(f, x0, method='BFGS')\n")
        new_hash = hash_file(script_file)
        assert new_hash != original_hash

        # The stored hash no longer matches the file
        assert script_node["hash"] != new_hash


# ===================================================================
# Concurrent node creation
# ===================================================================


class TestConcurrentNodeCreation:
    """Test that concurrent node creation produces unique IDs."""

    async def test_parallel_findings_get_unique_ids(self):
        """Creating many findings concurrently yields unique IDs."""
        import asyncio

        backend = RichFakeBackend()

        async def create_finding(i: int) -> str:
            result = json.loads(await add_finding(backend, {
                "description": f"Finding number {i}",
                "confidence": 0.5 + i * 0.01,
            }))
            return result["node_id"]

        ids = await asyncio.gather(*[create_finding(i) for i in range(20)])

        # All IDs should be unique
        assert len(set(ids)) == 20
        assert backend.node_count("Finding") == 20

    async def test_parallel_mixed_nodes_get_unique_ids(self):
        """Creating different node types concurrently yields unique IDs."""
        import asyncio

        backend = RichFakeBackend()

        async def create_nodes():
            tasks = [
                add_finding(backend, {"description": "F1", "confidence": 0.5}),
                add_hypothesis(backend, {"statement": "H1"}),
                add_question(backend, {"question": "Q1?"}),
                add_note(backend, {"content": "N1"}),
                add_finding(backend, {"description": "F2", "confidence": 0.6}),
                add_hypothesis(backend, {"statement": "H2"}),
            ]
            return await asyncio.gather(*tasks)

        results = await create_nodes()
        ids = [json.loads(r)["node_id"] for r in results]

        assert len(set(ids)) == 6
        assert ids[0].startswith("F-")
        assert ids[1].startswith("H-")
        assert ids[2].startswith("Q-")
        assert ids[3].startswith("N-")


# ===================================================================
# Error handling
# ===================================================================


class TestErrorHandling:
    """Test error handling in tool dispatch."""

    async def test_unknown_tool_returns_error(self):
        """Calling an unknown tool name returns an error dict."""
        from wheeler.tools.graph_tools import execute_tool

        mock_config = MagicMock()
        result_str = await execute_tool("nonexistent_tool", {}, mock_config)
        result = json.loads(result_str)
        assert "error" in result
        assert "Unknown tool" in result["error"]

    async def test_invalid_relationship_returns_error(self):
        """link_nodes with invalid relationship type returns error."""
        backend = RichFakeBackend()
        result = json.loads(await link_nodes(backend, {
            "source_id": "F-1234",
            "target_id": "H-5678",
            "relationship": "INVALID_REL_TYPE",
        }))
        assert "error" in result
        assert "Invalid relationship" in result["error"]

    async def test_invalid_tier_returns_error(self):
        """set_tier with invalid tier value returns error."""
        backend = RichFakeBackend()
        result = json.loads(await set_tier(backend, {
            "node_id": "F-1234",
            "tier": "mythical",
        }))
        assert "error" in result

    async def test_link_unknown_prefix_returns_error(self):
        """link_nodes with unrecognized node prefix returns error."""
        backend = RichFakeBackend()
        result = json.loads(await link_nodes(backend, {
            "source_id": "Z-unknown",
            "target_id": "F-1234",
            "relationship": "SUPPORTS",
        }))
        assert "error" in result
