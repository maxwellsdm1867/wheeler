"""Task-completion tests for Wheeler research workflows.

End-to-end scenarios that exercise complete research workflows through the
tool layer (mutations + queries), verifying that the graph structure is
correct after each multi-step workflow.

Uses a richer FakeBackend that tracks nodes and relationships in memory
so the full graph structure can be inspected without Neo4j or Kuzu.
"""

from __future__ import annotations

import json

import pytest

from wheeler.tools.graph_tools.mutations import (
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
# Rich FakeBackend with queryable in-memory graph
# ---------------------------------------------------------------------------


class RichFakeBackend:
    """In-memory graph backend that supports both writes and reads.

    Nodes: ``nodes[label] = [props_dict, ...]``
    Relationships: ``rels = [(src_label, src_id, rel_type, tgt_label, tgt_id), ...]``

    Supports ``get_node``, ``update_node``, ``create_relationship`` (with
    existence checking), and ``run_cypher`` (returns [] -- Cypher not
    actually parsed, but query tools still work for structure verification).
    """

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
        # Check both nodes exist
        src_exists = any(
            p.get("id") == src_id for p in self.nodes.get(src_label, [])
        )
        tgt_exists = any(
            p.get("id") == tgt_id for p in self.nodes.get(tgt_label, [])
        )
        # For provenance-completing, target nodes (inputs) may not be in
        # our backend yet (they're "pre-existing" in a real graph). We
        # store the relationship regardless to allow inspection.
        self.rels.append((src_label, src_id, rel_type, tgt_label, tgt_id))
        return True

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        return []

    # --- Inspection helpers ---

    def all_node_ids(self) -> list[str]:
        """Return all node IDs across all labels."""
        ids = []
        for label_nodes in self.nodes.values():
            for props in label_nodes:
                if "id" in props:
                    ids.append(props["id"])
        return ids

    def rels_from(self, node_id: str) -> list[tuple[str, str, str, str, str]]:
        """Return all relationships originating from node_id."""
        return [r for r in self.rels if r[1] == node_id]

    def rels_to(self, node_id: str) -> list[tuple[str, str, str, str, str]]:
        """Return all relationships targeting node_id."""
        return [r for r in self.rels if r[4] == node_id]

    def rels_of_type(self, rel_type: str) -> list[tuple[str, str, str, str, str]]:
        """Return all relationships of a given type."""
        return [r for r in self.rels if r[2] == rel_type]

    def node_count(self, label: str) -> int:
        return len(self.nodes.get(label, []))


# ===================================================================
# Research workflow tests
# ===================================================================


class TestResearchWorkflow:
    """Test complete research workflows through the tool layer."""

    async def test_full_provenance_chain(self):
        """Script -> Execution -> Finding, all linked via provenance-completing.

        Workflow: add_script, then add_finding with execution_kind pointing
        at the script. Verify the full provenance chain:
          Finding -[WAS_GENERATED_BY]-> Execution -[USED]-> Script
        """
        backend = RichFakeBackend()

        # 1. Create a script
        script_result = json.loads(await add_script(backend, {
            "path": "/analysis/fit_model.py",
            "language": "python",
            "hash": "abc123def456",
        }))
        script_id = script_result["node_id"]
        assert script_id.startswith("S-")

        # 2. Create a finding with provenance pointing to the script
        finding_result = json.loads(await add_finding(backend, {
            "description": "Model fit yields tau_rise = 0.12ms",
            "confidence": 0.85,
            "execution_kind": "script",
            "used_entities": script_id,
            "execution_description": "SRM model fitting run",
        }))
        finding_id = finding_result["node_id"]
        assert finding_id.startswith("F-")
        assert "provenance" in finding_result

        prov = finding_result["provenance"]
        exec_id = prov["execution_id"]

        # 3. Verify graph structure
        # Nodes: Script + Finding + Execution
        assert backend.node_count("Script") == 1
        assert backend.node_count("Finding") == 1
        assert backend.node_count("Execution") == 1

        # Relationships:
        # Finding -[WAS_GENERATED_BY]-> Execution
        wgb_rels = backend.rels_of_type("WAS_GENERATED_BY")
        assert len(wgb_rels) == 1
        assert wgb_rels[0][1] == finding_id  # source = Finding
        assert wgb_rels[0][4] == exec_id     # target = Execution

        # Execution -[USED]-> Script
        used_rels = backend.rels_of_type("USED")
        assert len(used_rels) == 1
        assert used_rels[0][1] == exec_id    # source = Execution
        assert used_rels[0][4] == script_id  # target = Script

        # Verify provenance response
        assert prov["execution_kind"] == "script"
        assert script_id in prov["linked_inputs"]

    async def test_discussion_to_hypothesis(self):
        """Discussion produces hypothesis from an existing finding.

        Workflow:
        1. add_finding (prior result)
        2. add_hypothesis with execution_kind="discuss", used_entities=finding_id
        3. Verify: Hypothesis -[WAS_GENERATED_BY]-> Execution -[USED]-> Finding
        """
        backend = RichFakeBackend()

        # 1. Prior finding
        finding_result = json.loads(await add_finding(backend, {
            "description": "Spike frequency doubles at 35C",
            "confidence": 0.9,
        }))
        finding_id = finding_result["node_id"]

        # 2. Hypothesis derived from discussion about the finding
        hyp_result = json.loads(await add_hypothesis(backend, {
            "statement": "Temperature-dependent channel gating drives spike rate",
            "execution_kind": "discuss",
            "used_entities": finding_id,
        }))
        hyp_id = hyp_result["node_id"]
        assert hyp_id.startswith("H-")
        assert "provenance" in hyp_result

        prov = hyp_result["provenance"]
        exec_id = prov["execution_id"]

        # 3. Verify chain
        wgb_rels = backend.rels_of_type("WAS_GENERATED_BY")
        assert len(wgb_rels) == 1
        assert wgb_rels[0][1] == hyp_id
        assert wgb_rels[0][4] == exec_id

        used_rels = backend.rels_of_type("USED")
        assert len(used_rels) == 1
        assert used_rels[0][1] == exec_id
        assert used_rels[0][4] == finding_id

        assert prov["execution_kind"] == "discuss"
        assert finding_id in prov["linked_inputs"]

    async def test_write_session(self):
        """Writing session produces document citing findings and papers.

        Workflow:
        1. add_paper, add_finding
        2. add_document with execution_kind="write", used_entities=finding+paper
        3. Verify: Document -[WAS_GENERATED_BY]-> Execution -[USED]-> {Finding, Paper}
        """
        backend = RichFakeBackend()

        # 1. Create a paper and a finding
        paper_result = json.loads(await add_paper(backend, {
            "title": "Spike Response Model (Gerstner 1995)",
            "authors": "Gerstner, W.",
            "year": 1995,
        }))
        paper_id = paper_result["node_id"]

        finding_result = json.loads(await add_finding(backend, {
            "description": "4-param SRM fits parasol cells with VP-loss < 0.2",
            "confidence": 0.88,
        }))
        finding_id = finding_result["node_id"]

        # 2. Create a document citing both
        doc_result = json.loads(await add_document(backend, {
            "title": "Results: SRM Fitting",
            "path": "docs/results_srm.md",
            "section": "results",
            "status": "draft",
            "execution_kind": "write",
            "used_entities": f"{finding_id},{paper_id}",
            "execution_description": "Writing results section",
        }))
        doc_id = doc_result["node_id"]
        assert doc_id.startswith("W-")
        assert "provenance" in doc_result

        prov = doc_result["provenance"]
        exec_id = prov["execution_id"]

        # 3. Verify chain
        wgb_rels = backend.rels_of_type("WAS_GENERATED_BY")
        assert len(wgb_rels) == 1
        assert wgb_rels[0][1] == doc_id
        assert wgb_rels[0][4] == exec_id

        used_rels = backend.rels_of_type("USED")
        assert len(used_rels) == 2
        used_targets = {r[4] for r in used_rels}
        assert finding_id in used_targets
        assert paper_id in used_targets

    async def test_multi_finding_analysis(self):
        """Multiple findings from a single script execution.

        Workflow:
        1. add_script
        2. add_finding x3, all with same script as used_entity
        3. Verify 3 separate Execution nodes, each linked to the script
        """
        backend = RichFakeBackend()

        script_result = json.loads(await add_script(backend, {
            "path": "/analysis/population.py",
            "language": "python",
        }))
        script_id = script_result["node_id"]

        finding_ids = []
        for desc, conf in [
            ("Parasol ON: tau_rise = 0.12", 0.85),
            ("Parasol OFF: tau_rise = 0.11", 0.82),
            ("Midget ON: tau_rise = 0.14", 0.78),
        ]:
            result = json.loads(await add_finding(backend, {
                "description": desc,
                "confidence": conf,
                "execution_kind": "script",
                "used_entities": script_id,
            }))
            finding_ids.append(result["node_id"])

        # 3 Findings + 1 Script + 3 Executions = 7 nodes
        assert backend.node_count("Finding") == 3
        assert backend.node_count("Script") == 1
        assert backend.node_count("Execution") == 3

        # Each Finding has WAS_GENERATED_BY its own Execution
        wgb = backend.rels_of_type("WAS_GENERATED_BY")
        assert len(wgb) == 3

        # Each Execution USED the same Script
        used = backend.rels_of_type("USED")
        assert len(used) == 3
        assert all(r[4] == script_id for r in used)

    async def test_hypothesis_evidence_linking(self):
        """Hypothesis linked to supporting and contradicting findings.

        Workflow:
        1. Create hypothesis
        2. Create 2 findings
        3. link_nodes: finding1 SUPPORTS hypothesis, finding2 CONTRADICTS hypothesis
        4. Verify relationship structure
        """
        backend = RichFakeBackend()

        hyp_result = json.loads(await add_hypothesis(backend, {
            "statement": "Channel gating is temperature-independent",
        }))
        hyp_id = hyp_result["node_id"]

        f1_result = json.loads(await add_finding(backend, {
            "description": "No change in gating at 25C vs 30C",
            "confidence": 0.6,
        }))
        f1_id = f1_result["node_id"]

        f2_result = json.loads(await add_finding(backend, {
            "description": "Gating doubles at 35C",
            "confidence": 0.9,
        }))
        f2_id = f2_result["node_id"]

        # Link: F1 SUPPORTS H
        link1 = json.loads(await link_nodes(backend, {
            "source_id": f1_id,
            "target_id": hyp_id,
            "relationship": "SUPPORTS",
        }))
        assert link1["status"] == "linked"

        # Link: F2 CONTRADICTS H
        link2 = json.loads(await link_nodes(backend, {
            "source_id": f2_id,
            "target_id": hyp_id,
            "relationship": "CONTRADICTS",
        }))
        assert link2["status"] == "linked"

        # Verify
        supports = backend.rels_of_type("SUPPORTS")
        assert len(supports) == 1
        assert supports[0][1] == f1_id
        assert supports[0][4] == hyp_id

        contradicts = backend.rels_of_type("CONTRADICTS")
        assert len(contradicts) == 1
        assert contradicts[0][1] == f2_id
        assert contradicts[0][4] == hyp_id

    async def test_session_tracking(self):
        """All nodes from one session share session_id."""
        backend = RichFakeBackend()
        session_id = "session-test1234"

        await add_finding(backend, {
            "description": "Finding 1",
            "confidence": 0.5,
            "session_id": session_id,
        })
        await add_hypothesis(backend, {
            "statement": "Hypothesis 1",
            "session_id": session_id,
        })
        await add_note(backend, {
            "content": "Interesting observation",
            "session_id": session_id,
        })

        # All nodes should carry the session_id
        for label in ("Finding", "Hypothesis", "ResearchNote"):
            nodes = backend.nodes.get(label, [])
            assert len(nodes) == 1, f"Expected 1 {label} node"
            assert nodes[0]["session_id"] == session_id, (
                f"{label} missing session_id"
            )

    async def test_tier_promotion_workflow(self):
        """Finding starts as generated, gets promoted to reference.

        Workflow:
        1. add_finding (tier defaults to "generated")
        2. set_tier to "reference"
        3. Verify tier updated
        """
        backend = RichFakeBackend()

        result = json.loads(await add_finding(backend, {
            "description": "VP-loss < 0.15 for all parasol fits",
            "confidence": 0.95,
        }))
        node_id = result["node_id"]

        # Verify default tier
        node = await backend.get_node("Finding", node_id)
        assert node is not None
        assert node["tier"] == "generated"

        # Promote to reference
        tier_result = json.loads(await set_tier(backend, {
            "node_id": node_id,
            "tier": "reference",
        }))
        assert tier_result["status"] == "updated"
        assert tier_result["tier"] == "reference"

        # Verify stored value
        node = await backend.get_node("Finding", node_id)
        assert node["tier"] == "reference"

    async def test_question_to_finding_pipeline(self):
        """OpenQuestion leads to investigation, producing a Finding.

        Workflow:
        1. add_question
        2. add_script (the analysis that addresses the question)
        3. add_finding with provenance from script
        4. link_nodes: finding RELEVANT_TO question
        5. Verify full graph
        """
        backend = RichFakeBackend()

        q_result = json.loads(await add_question(backend, {
            "question": "Does VP-loss depend on cell type?",
            "priority": 8,
        }))
        q_id = q_result["node_id"]

        s_result = json.loads(await add_script(backend, {
            "path": "/analysis/cell_type_comparison.py",
            "language": "python",
        }))
        s_id = s_result["node_id"]

        f_result = json.loads(await add_finding(backend, {
            "description": "VP-loss is 40% higher in midget vs parasol cells",
            "confidence": 0.87,
            "execution_kind": "script",
            "used_entities": s_id,
        }))
        f_id = f_result["node_id"]

        # Link finding to the question it answers
        link_result = json.loads(await link_nodes(backend, {
            "source_id": f_id,
            "target_id": q_id,
            "relationship": "RELEVANT_TO",
        }))
        assert link_result["status"] == "linked"

        # Verify graph: Q, S, F, X nodes
        assert backend.node_count("OpenQuestion") == 1
        assert backend.node_count("Script") == 1
        assert backend.node_count("Finding") == 1
        assert backend.node_count("Execution") == 1

        # RELEVANT_TO links Finding to Question
        rel_to = backend.rels_of_type("RELEVANT_TO")
        assert len(rel_to) == 1
        assert rel_to[0][1] == f_id
        assert rel_to[0][4] == q_id

    async def test_paper_cites_chain(self):
        """Paper -> CITES -> Finding chain.

        Workflow:
        1. add_paper
        2. add_finding
        3. link_nodes: paper CITES finding
        """
        backend = RichFakeBackend()

        p_result = json.loads(await add_paper(backend, {
            "title": "Retinal ganglion cell spike response models",
            "authors": "Smith, Jones",
            "year": 2024,
        }))
        p_id = p_result["node_id"]

        f_result = json.loads(await add_finding(backend, {
            "description": "SRM captures 95% variance in parasol ON cells",
            "confidence": 0.92,
        }))
        f_id = f_result["node_id"]

        link_result = json.loads(await link_nodes(backend, {
            "source_id": p_id,
            "target_id": f_id,
            "relationship": "CITES",
        }))
        assert link_result["status"] == "linked"

        cites = backend.rels_of_type("CITES")
        assert len(cites) == 1
        assert cites[0][1] == p_id
        assert cites[0][4] == f_id

    async def test_stability_values_assigned_correctly(self):
        """Each node type gets the correct default stability.

        Based on provenance.default_stability:
        - Finding/generated = 0.3
        - Paper/reference = 0.9
        - Script/generated = 0.5
        - Hypothesis/generated = 0.3
        """
        backend = RichFakeBackend()

        await add_finding(backend, {"description": "test", "confidence": 0.5})
        await add_paper(backend, {"title": "test paper"})
        await add_script(backend, {"path": "/test.py", "language": "python"})
        await add_hypothesis(backend, {"statement": "test hypothesis"})

        assert backend.nodes["Finding"][0]["stability"] == 0.3
        assert backend.nodes["Paper"][0]["stability"] == 0.9
        assert backend.nodes["Script"][0]["stability"] == 0.5
        assert backend.nodes["Hypothesis"][0]["stability"] == 0.3

    async def test_complex_provenance_graph(self):
        """Complex multi-input provenance: two datasets + one script -> finding.

        Workflow:
        1. add_finding with execution_kind="script" and 3 used_entities
           (2 datasets + 1 script, all as pre-existing IDs)
        2. Verify Execution is created with 3 USED links
        """
        backend = RichFakeBackend()

        dataset1_id = "D-aaaa1111"
        dataset2_id = "D-bbbb2222"
        script_id = "S-cccc3333"

        result = json.loads(await add_finding(backend, {
            "description": "Cross-cell-type analysis reveals consistent tau_decay",
            "confidence": 0.75,
            "execution_kind": "script",
            "used_entities": f"{dataset1_id},{dataset2_id},{script_id}",
            "execution_description": "Population analysis across parasol and midget",
        }))

        prov = result["provenance"]
        assert len(prov["linked_inputs"]) == 3
        assert dataset1_id in prov["linked_inputs"]
        assert dataset2_id in prov["linked_inputs"]
        assert script_id in prov["linked_inputs"]

        used_rels = backend.rels_of_type("USED")
        assert len(used_rels) == 3

    async def test_document_appears_in_workflow(self):
        """Finding APPEARS_IN Document.

        Workflow:
        1. add_finding
        2. add_document
        3. link_nodes: finding APPEARS_IN document
        """
        backend = RichFakeBackend()

        f_result = json.loads(await add_finding(backend, {
            "description": "Key result about spike timing",
            "confidence": 0.88,
        }))
        f_id = f_result["node_id"]

        d_result = json.loads(await add_document(backend, {
            "title": "Methods Draft",
            "path": "docs/methods.md",
        }))
        d_id = d_result["node_id"]

        link = json.loads(await link_nodes(backend, {
            "source_id": f_id,
            "target_id": d_id,
            "relationship": "APPEARS_IN",
        }))
        assert link["status"] == "linked"

        appears = backend.rels_of_type("APPEARS_IN")
        assert len(appears) == 1
        assert appears[0][1] == f_id
        assert appears[0][4] == d_id
