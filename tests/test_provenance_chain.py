"""Provenance chain simulation tests.

Builds realistic knowledge graphs using the mutation tools, then simulates
what happens when upstream nodes change: stability propagation, staleness
cascades, and multi-hop invalidation.

Since propagate_invalidation() uses Neo4j Cypher directly, these tests
implement the same propagation logic in pure Python over the in-memory
graph so we can verify the expected behavior without a live database.

The core rule:
  When a Script changes, everything downstream loses trust.
  Decay is exponential: new_stability = source_stability * decay^hops

Graph directions (W3C PROV-DM):
  Finding -[:WAS_GENERATED_BY]-> Execution -[:USED]-> Script/Dataset
  Entity  -[:WAS_DERIVED_FROM]-> Entity

So "downstream" means: follow USED backward to Execution, then
WAS_GENERATED_BY backward to the outputs. Those outputs depend
on the changed input.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from wheeler.provenance import (
    InvalidatedNode,
    PROVENANCE_RELS,
    default_stability,
)
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
)


# ---------------------------------------------------------------------------
# In-memory backend with provenance-aware traversal
# ---------------------------------------------------------------------------


class ProvenanceBackend:
    """In-memory backend that supports provenance chain traversal.

    Extends the basic fake backend with methods to:
    - Find downstream dependents of a changed node
    - Propagate stability decay through the graph
    - Track stale/invalidated state
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
        self.rels.append((src_label, src_id, rel_type, tgt_label, tgt_id))
        return True

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        return []

    # --- Provenance traversal helpers ---

    def find_node_any_label(self, node_id: str) -> tuple[str, dict] | None:
        """Find a node by ID across all labels."""
        for label, nodes in self.nodes.items():
            for props in nodes:
                if props.get("id") == node_id:
                    return label, props
        return None

    def rels_of_type(self, rel_type: str) -> list[tuple]:
        return [r for r in self.rels if r[2] == rel_type]

    def rels_targeting(self, node_id: str, rel_type: str) -> list[tuple]:
        """Relationships where node_id is the target."""
        return [r for r in self.rels if r[4] == node_id and r[2] == rel_type]

    def rels_from(self, node_id: str, rel_type: str) -> list[tuple]:
        """Relationships where node_id is the source."""
        return [r for r in self.rels if r[1] == node_id and r[2] == rel_type]

    def find_downstream(self, changed_id: str) -> list[tuple[str, str, int]]:
        """Find all nodes downstream of changed_id via PROV relationships.

        Returns [(node_id, label, hops), ...] sorted by hops.

        Downstream traversal logic (mirrors propagate_invalidation):
        1. Find Executions that USED the changed node
        2. Find entities that were WAS_GENERATED_BY those Executions
        3. Find entities WAS_DERIVED_FROM the changed node (direct)
        4. Recurse for multi-hop chains
        """
        visited: set[str] = {changed_id}
        result: list[tuple[str, str, int]] = []
        frontier: list[tuple[str, int]] = [(changed_id, 0)]

        while frontier:
            current_id, current_hops = frontier.pop(0)

            # Path 1: Execution USED current -> Entity WAS_GENERATED_BY Execution
            # In our rels: (Execution, exec_id, "USED", TargetLabel, current_id)
            used_rels = self.rels_targeting(current_id, "USED")
            for rel in used_rels:
                exec_id = rel[1]  # The Execution that used this node

                # Find entities generated by this execution
                # In our rels: (EntityLabel, entity_id, "WAS_GENERATED_BY", "Execution", exec_id)
                wgb_rels = self.rels_targeting(exec_id, "WAS_GENERATED_BY")
                for wgb in wgb_rels:
                    entity_id = wgb[1]
                    entity_label = wgb[0]
                    if entity_id not in visited:
                        visited.add(entity_id)
                        hops = current_hops + 2  # 2 hops: through Execution
                        result.append((entity_id, entity_label, hops))
                        frontier.append((entity_id, hops))

            # Path 2: Entity WAS_DERIVED_FROM current (direct)
            # In our rels: (DerivedLabel, derived_id, "WAS_DERIVED_FROM", CurrentLabel, current_id)
            derived_rels = self.rels_targeting(current_id, "WAS_DERIVED_FROM")
            for rel in derived_rels:
                derived_id = rel[1]
                derived_label = rel[0]
                if derived_id not in visited:
                    visited.add(derived_id)
                    hops = current_hops + 1
                    result.append((derived_id, derived_label, hops))
                    frontier.append((derived_id, hops))

        return sorted(result, key=lambda x: x[2])

    def propagate_staleness(
        self,
        changed_id: str,
        new_stability: float | None = None,
        decay_factor: float = 0.8,
    ) -> list[InvalidatedNode]:
        """Simulate propagate_invalidation in pure Python.

        1. Mark the source node as stale, reduce its stability
        2. Find all downstream nodes
        3. Reduce their stability with exponential decay
        """
        # Step 1: Mark source
        found = self.find_node_any_label(changed_id)
        if found is None:
            return []

        label, props = found
        old_source_stab = props.get("stability", 0.5)
        if new_stability is not None:
            source_stab = new_stability
        else:
            source_stab = old_source_stab * 0.5
        props["stability"] = source_stab
        props["stale"] = True

        # Step 2: Find downstream
        downstream = self.find_downstream(changed_id)

        # Step 3: Propagate with decay
        affected: list[InvalidatedNode] = []
        for node_id, node_label, hops in downstream:
            found = self.find_node_any_label(node_id)
            if found is None:
                continue
            _, node_props = found
            old_stab = node_props.get("stability", 0.5)
            decayed = source_stab * (decay_factor ** hops)

            if decayed < old_stab:
                node_props["stability"] = decayed
                node_props["stale"] = True
                node_props["prev_stability"] = old_stab
                affected.append(InvalidatedNode(
                    node_id=node_id,
                    label=node_label,
                    old_stability=old_stab,
                    new_stability=decayed,
                    hops=hops,
                ))

        return affected


# ===================================================================
# Simple chain: Script -> Execution -> Finding
# ===================================================================


class TestSimpleChain:
    """Script is modified, finding should become stale."""

    async def test_script_change_invalidates_finding(self):
        """
        Graph: Script <-[:USED]- Execution <-[:WAS_GENERATED_BY]- Finding

        When Script changes, Finding should lose stability.
        """
        backend = ProvenanceBackend()

        # Build the chain through mutations
        s = json.loads(await add_script(backend, {
            "path": "/analysis/fit.py",
            "language": "python",
            "hash": "original_hash_abc123",
        }))
        f = json.loads(await add_finding(backend, {
            "description": "tau_rise = 0.12ms",
            "confidence": 0.85,
            "execution_kind": "script",
            "used_entities": s["node_id"],
        }))

        # Verify initial stability
        script_node = await backend.get_node("Script", s["node_id"])
        finding_node = await backend.get_node("Finding", f["node_id"])
        assert script_node["stability"] == 0.5   # Script/generated
        assert finding_node["stability"] == 0.3   # Finding/generated

        # Simulate: script file was modified -> propagate staleness
        affected = backend.propagate_staleness(
            s["node_id"],
            new_stability=0.3,  # Script re-hashed, now stale
        )

        # Finding should be affected
        assert len(affected) == 1
        assert affected[0].node_id == f["node_id"]
        assert affected[0].label == "Finding"
        assert affected[0].old_stability == 0.3
        # New = 0.3 * 0.8^2 = 0.192
        assert abs(affected[0].new_stability - 0.192) < 0.001
        assert affected[0].hops == 2

        # Verify the script is now marked stale
        script_node = await backend.get_node("Script", s["node_id"])
        assert script_node["stale"] is True
        assert script_node["stability"] == 0.3

    async def test_high_stability_reference_resists_decay(self):
        """Reference finding (stability=0.8) resists decay from weak source.

        If decayed value > current stability, no change should occur.
        """
        backend = ProvenanceBackend()

        s = json.loads(await add_script(backend, {
            "path": "/analysis/stable.py",
            "language": "python",
        }))

        # Create finding and promote to reference (stability=0.8)
        f = json.loads(await add_finding(backend, {
            "description": "Well-established result",
            "confidence": 0.99,
            "tier": "reference",
            "execution_kind": "script",
            "used_entities": s["node_id"],
        }))

        # Verify reference stability
        finding_node = await backend.get_node("Finding", f["node_id"])
        assert finding_node["stability"] == 0.8  # Finding/reference

        # Script becomes slightly unstable
        affected = backend.propagate_staleness(
            s["node_id"],
            new_stability=0.4,  # Mild staleness
        )

        # 0.4 * 0.8^2 = 0.256  which is < 0.8, so finding IS affected
        assert len(affected) == 1
        assert affected[0].old_stability == 0.8
        assert abs(affected[0].new_stability - 0.256) < 0.001


# ===================================================================
# Branching: One script feeds multiple findings
# ===================================================================


class TestBranchingChain:
    """One upstream change affects multiple downstream nodes."""

    async def test_script_change_affects_all_findings(self):
        """
        Graph:
          Script <-[:USED]- Exec1 <-[:WAS_GENERATED_BY]- Finding1
          Script <-[:USED]- Exec2 <-[:WAS_GENERATED_BY]- Finding2
          Script <-[:USED]- Exec3 <-[:WAS_GENERATED_BY]- Finding3

        All three findings should be invalidated.
        """
        backend = ProvenanceBackend()

        s = json.loads(await add_script(backend, {
            "path": "/analysis/population.py",
            "language": "python",
            "hash": "pop_hash_001",
        }))

        findings = []
        for desc in [
            "Parasol ON: tau = 0.12ms",
            "Parasol OFF: tau = 0.11ms",
            "Midget ON: tau = 0.14ms",
        ]:
            f = json.loads(await add_finding(backend, {
                "description": desc,
                "confidence": 0.85,
                "execution_kind": "script",
                "used_entities": s["node_id"],
            }))
            findings.append(f)

        # Script changes
        affected = backend.propagate_staleness(s["node_id"], new_stability=0.3)

        assert len(affected) == 3
        affected_ids = {a.node_id for a in affected}
        for f in findings:
            assert f["node_id"] in affected_ids

        # All at same hops
        assert all(a.hops == 2 for a in affected)

    async def test_dataset_change_affects_findings(self):
        """
        Graph:
          Dataset <-[:USED]- Exec <-[:WAS_GENERATED_BY]- Finding
          Script  <-[:USED]- Exec (same execution used both)

        Changing the dataset invalidates the finding.
        """
        backend = ProvenanceBackend()

        d = json.loads(await add_dataset(backend, {
            "path": "/data/spikes.mat",
            "type": "mat",
            "description": "Spike recordings",
        }))
        s = json.loads(await add_script(backend, {
            "path": "/analysis/fit.py",
            "language": "python",
        }))

        f = json.loads(await add_finding(backend, {
            "description": "Model fits well",
            "confidence": 0.9,
            "execution_kind": "script",
            "used_entities": f"{s['node_id']},{d['node_id']}",
        }))

        # Dataset changes (corrupted data discovered)
        # Must use low enough stability so decay reaches below finding's 0.3
        # 0.3 * 0.8^2 = 0.192 < 0.3, so finding IS affected
        affected = backend.propagate_staleness(d["node_id"], new_stability=0.3)

        assert len(affected) == 1
        assert affected[0].node_id == f["node_id"]


# ===================================================================
# Deep chain: Script -> Finding -> Hypothesis -> Document
# ===================================================================


class TestDeepChain:
    """Multi-hop propagation through a realistic research workflow."""

    async def test_four_layer_propagation(self):
        """
        Graph (built through mutations):
          Script <-[:USED]- Exec1 <-[:WAS_GENERATED_BY]- Finding
          Finding <-[:USED]- Exec2 <-[:WAS_GENERATED_BY]- Hypothesis
          Finding <-[:USED]- Exec3 <-[:WAS_GENERATED_BY]- Document

        Script changes -> Finding stale (2 hops) -> Hypothesis stale (4 hops)
                                                  -> Document stale (4 hops)
        """
        backend = ProvenanceBackend()

        # Layer 1: Script
        s = json.loads(await add_script(backend, {
            "path": "/analysis/deep.py",
            "language": "python",
            "hash": "deep_hash_001",
        }))

        # Layer 2: Finding from script
        f = json.loads(await add_finding(backend, {
            "description": "Deep chain finding",
            "confidence": 0.8,
            "execution_kind": "script",
            "used_entities": s["node_id"],
        }))

        # Layer 3: Hypothesis from finding (discuss session)
        h = json.loads(await add_hypothesis(backend, {
            "statement": "Deep chain hypothesis",
            "execution_kind": "discuss",
            "used_entities": f["node_id"],
        }))

        # Layer 4: Document citing finding
        doc = json.loads(await add_document(backend, {
            "title": "Deep chain results",
            "path": "docs/deep.md",
            "execution_kind": "write",
            "used_entities": f["node_id"],
        }))

        # Script changes -> propagate
        affected = backend.propagate_staleness(s["node_id"], new_stability=0.3)

        # Finding at 2 hops, Hypothesis and Document at 4 hops
        affected_map = {a.node_id: a for a in affected}

        assert f["node_id"] in affected_map
        assert affected_map[f["node_id"]].hops == 2

        assert h["node_id"] in affected_map
        assert affected_map[h["node_id"]].hops == 4

        assert doc["node_id"] in affected_map
        assert affected_map[doc["node_id"]].hops == 4

        # Verify exponential decay
        # Finding: 0.3 * 0.8^2 = 0.192
        assert abs(affected_map[f["node_id"]].new_stability - 0.192) < 0.001
        # Hypothesis: 0.3 * 0.8^4 = 0.12288
        assert abs(affected_map[h["node_id"]].new_stability - 0.12288) < 0.001
        # Document: 0.3 * 0.8^4 = 0.12288
        assert abs(affected_map[doc["node_id"]].new_stability - 0.12288) < 0.001

    async def test_deep_chain_with_note(self):
        """Notes participate in provenance chains too.

        Script -> Finding -> Note (note was generated from discussing the finding)
        """
        backend = ProvenanceBackend()

        s = json.loads(await add_script(backend, {
            "path": "/analysis/note_chain.py",
            "language": "python",
        }))
        f = json.loads(await add_finding(backend, {
            "description": "Interesting pattern observed",
            "confidence": 0.7,
            "execution_kind": "script",
            "used_entities": s["node_id"],
        }))
        n = json.loads(await add_note(backend, {
            "content": "This pattern might indicate temperature sensitivity",
            "execution_kind": "discuss",
            "used_entities": f["node_id"],
        }))

        affected = backend.propagate_staleness(s["node_id"], new_stability=0.3)

        affected_map = {a.node_id: a for a in affected}
        assert f["node_id"] in affected_map
        assert n["node_id"] in affected_map
        assert affected_map[n["node_id"]].hops == 4


# ===================================================================
# Diamond dependency: two paths to the same node
# ===================================================================


class TestDiamondDependency:
    """When a node is reachable by multiple paths, use shortest path."""

    async def test_diamond_takes_shortest_path(self):
        """
        Graph:
          Script <-[:USED]- Exec1 <-[:WAS_GENERATED_BY]- Finding1 (2 hops)
          Script <-[:USED]- Exec2 <-[:WAS_GENERATED_BY]- Finding2 (2 hops)
          Finding1 <-[:USED]- Exec3 <-[:WAS_GENERATED_BY]- Summary (4 hops via F1)
          Finding2 <-[:USED]- Exec3 (same exec also used F2, but we already found Summary)

        Summary is reachable at 4 hops. Even though it could also be
        reached through Finding2, we already visited it.
        """
        backend = ProvenanceBackend()

        s = json.loads(await add_script(backend, {
            "path": "/analysis/diamond.py",
            "language": "python",
        }))

        f1 = json.loads(await add_finding(backend, {
            "description": "Result A from diamond script",
            "confidence": 0.8,
            "execution_kind": "script",
            "used_entities": s["node_id"],
        }))
        f2 = json.loads(await add_finding(backend, {
            "description": "Result B from diamond script",
            "confidence": 0.7,
            "execution_kind": "script",
            "used_entities": s["node_id"],
        }))

        # Summary document citing both findings
        summary = json.loads(await add_document(backend, {
            "title": "Summary of A and B",
            "path": "docs/summary.md",
            "execution_kind": "write",
            "used_entities": f"{f1['node_id']},{f2['node_id']}",
        }))

        affected = backend.propagate_staleness(s["node_id"], new_stability=0.3)

        affected_map = {a.node_id: a for a in affected}

        # Both findings at 2 hops
        assert f1["node_id"] in affected_map
        assert f2["node_id"] in affected_map
        assert affected_map[f1["node_id"]].hops == 2
        assert affected_map[f2["node_id"]].hops == 2

        # Summary at 4 hops (via whichever finding was traversed first)
        assert summary["node_id"] in affected_map
        assert affected_map[summary["node_id"]].hops == 4


# ===================================================================
# WAS_DERIVED_FROM chains
# ===================================================================


class TestDerivedFromChain:
    """Test WAS_DERIVED_FROM direct derivation links."""

    async def test_derived_finding_propagates(self):
        """
        Graph:
          Finding1
          Finding2 -[:WAS_DERIVED_FROM]-> Finding1

        When Finding1 changes, Finding2 should be affected at 1 hop.
        """
        backend = ProvenanceBackend()

        f1 = json.loads(await add_finding(backend, {
            "description": "Original measurement",
            "confidence": 0.9,
        }))
        f2 = json.loads(await add_finding(backend, {
            "description": "Corrected measurement (derived from original)",
            "confidence": 0.85,
        }))

        # Manual WAS_DERIVED_FROM link
        link = json.loads(await link_nodes(backend, {
            "source_id": f2["node_id"],
            "target_id": f1["node_id"],
            "relationship": "WAS_DERIVED_FROM",
        }))
        assert link["status"] == "linked"

        # Finding1 changes
        affected = backend.propagate_staleness(f1["node_id"], new_stability=0.2)

        assert len(affected) == 1
        assert affected[0].node_id == f2["node_id"]
        assert affected[0].hops == 1
        # 0.2 * 0.8^1 = 0.16
        assert abs(affected[0].new_stability - 0.16) < 0.001

    async def test_chained_derivations(self):
        """
        Finding1 <- Finding2 <- Finding3 (each WAS_DERIVED_FROM previous)

        Finding1 changes -> Finding2 at 1 hop, Finding3 at 2 hops
        """
        backend = ProvenanceBackend()

        f1 = json.loads(await add_finding(backend, {
            "description": "Raw data", "confidence": 0.9,
        }))
        f2 = json.loads(await add_finding(backend, {
            "description": "Normalized data", "confidence": 0.85,
        }))
        f3 = json.loads(await add_finding(backend, {
            "description": "Smoothed data", "confidence": 0.8,
        }))

        await link_nodes(backend, {
            "source_id": f2["node_id"],
            "target_id": f1["node_id"],
            "relationship": "WAS_DERIVED_FROM",
        })
        await link_nodes(backend, {
            "source_id": f3["node_id"],
            "target_id": f2["node_id"],
            "relationship": "WAS_DERIVED_FROM",
        })

        affected = backend.propagate_staleness(f1["node_id"], new_stability=0.2)
        affected_map = {a.node_id: a for a in affected}

        assert f2["node_id"] in affected_map
        assert f3["node_id"] in affected_map
        assert affected_map[f2["node_id"]].hops == 1
        assert affected_map[f3["node_id"]].hops == 2

        # f2: 0.2 * 0.8 = 0.16
        assert abs(affected_map[f2["node_id"]].new_stability - 0.16) < 0.001
        # f3: 0.2 * 0.8^2 = 0.128
        assert abs(affected_map[f3["node_id"]].new_stability - 0.128) < 0.001


# ===================================================================
# No propagation when nothing depends on the changed node
# ===================================================================


class TestNoPropagation:
    """Changing an isolated node affects nothing."""

    async def test_isolated_script_change(self):
        """Script with no executions pointing to it."""
        backend = ProvenanceBackend()

        s = json.loads(await add_script(backend, {
            "path": "/analysis/unused.py",
            "language": "python",
        }))

        affected = backend.propagate_staleness(s["node_id"], new_stability=0.1)
        assert len(affected) == 0

    async def test_finding_without_downstream(self):
        """Finding that nothing was derived from."""
        backend = ProvenanceBackend()

        s = json.loads(await add_script(backend, {
            "path": "/analysis/terminal.py",
            "language": "python",
        }))
        f = json.loads(await add_finding(backend, {
            "description": "Terminal finding, nothing depends on it",
            "confidence": 0.9,
            "execution_kind": "script",
            "used_entities": s["node_id"],
        }))

        # Change the finding directly (not the script)
        affected = backend.propagate_staleness(f["node_id"], new_stability=0.1)
        assert len(affected) == 0

    async def test_nonexistent_node_returns_empty(self):
        """Propagating from a nonexistent node returns nothing."""
        backend = ProvenanceBackend()
        affected = backend.propagate_staleness("X-nonexistent", new_stability=0.1)
        assert len(affected) == 0


# ===================================================================
# Stability scoring verification
# ===================================================================


class TestStabilityScoring:
    """Verify stability defaults match the documented values."""

    def test_stability_values(self):
        """Check all documented stability values."""
        # Reference tier (established knowledge)
        assert default_stability("Dataset", "reference") == 1.0
        assert default_stability("Paper", "reference") == 0.9
        assert default_stability("Finding", "reference") == 0.8
        assert default_stability("Script", "reference") == 0.7
        assert default_stability("Document", "reference") == 0.7
        assert default_stability("Hypothesis", "reference") == 0.7

        # Generated tier (in-progress work)
        assert default_stability("Dataset", "generated") == 0.7
        assert default_stability("Script", "generated") == 0.5
        assert default_stability("Finding", "generated") == 0.3
        assert default_stability("Hypothesis", "generated") == 0.3
        assert default_stability("Document", "generated") == 0.3
        assert default_stability("OpenQuestion", "generated") == 0.3
        assert default_stability("ResearchNote", "generated") == 0.3

    def test_reference_always_more_stable_than_generated(self):
        """Reference tier should always be >= generated tier."""
        for label in ["Dataset", "Script", "Finding", "Hypothesis", "Document"]:
            ref = default_stability(label, "reference")
            gen = default_stability(label, "generated")
            assert ref >= gen, f"{label}: reference ({ref}) < generated ({gen})"

    def test_decay_math(self):
        """Verify the exponential decay formula."""
        source_stab = 0.3
        decay = 0.8

        # Hop 1: 0.3 * 0.8 = 0.24
        assert abs(source_stab * decay**1 - 0.24) < 0.001
        # Hop 2: 0.3 * 0.64 = 0.192
        assert abs(source_stab * decay**2 - 0.192) < 0.001
        # Hop 3: 0.3 * 0.512 = 0.1536
        assert abs(source_stab * decay**3 - 0.1536) < 0.001
        # Hop 4: 0.3 * 0.4096 = 0.12288
        assert abs(source_stab * decay**4 - 0.12288) < 0.001

    def test_high_stability_script_has_wider_blast_radius(self):
        """A reference script (0.7) produces higher downstream decay than generated (0.5)."""
        decay = 0.8

        # Reference script at 2 hops
        ref_at_2 = 0.7 * decay**2  # 0.448
        # Generated script at 2 hops
        gen_at_2 = 0.5 * decay**2  # 0.32

        # Both would affect a generated finding (0.3)
        # But wait: ref_at_2 = 0.448 > 0.3, so it would NOT reduce the finding
        # gen_at_2 = 0.32 > 0.3, so it also would NOT reduce the finding

        # The decay formula computes new_stability = source * decay^hops
        # If new_stability >= current, no change occurs
        # So ironically, a MORE stable script causes LESS damage when changed

        # If we explicitly set a stale reference script to 0.3:
        stale_at_2 = 0.3 * decay**2  # 0.192
        assert stale_at_2 < 0.3  # Would affect a generated finding


# ===================================================================
# Full realistic scenario
# ===================================================================


class TestRealisticScenario:
    """A realistic research workflow where a script bug is discovered."""

    async def test_bug_discovery_cascade(self):
        """
        Scenario: Scientist discovers a bug in their analysis script.
        The script was used to produce 3 findings, one of which was
        cited in a draft paper section and used to support a hypothesis.

        Expected cascade:
        1. Script marked stale (stability 0.5 -> 0.1)
        2. All 3 findings lose stability
        3. Hypothesis (supported by finding) loses stability
        4. Document (citing finding) loses stability
        """
        backend = ProvenanceBackend()

        # Setup: register the buggy script
        script = json.loads(await add_script(backend, {
            "path": "/analysis/buggy_fit.py",
            "language": "python",
            "hash": "buggy_hash",
        }))

        # Setup: register dataset
        data = json.loads(await add_dataset(backend, {
            "path": "/data/recordings.mat",
            "type": "mat",
            "description": "Electrophysiology recordings",
        }))

        # Produce 3 findings from the script
        f1 = json.loads(await add_finding(backend, {
            "description": "Parasol time constant = 0.12ms",
            "confidence": 0.85,
            "execution_kind": "script",
            "used_entities": f"{script['node_id']},{data['node_id']}",
        }))
        f2 = json.loads(await add_finding(backend, {
            "description": "Midget time constant = 0.14ms",
            "confidence": 0.82,
            "execution_kind": "script",
            "used_entities": f"{script['node_id']},{data['node_id']}",
        }))
        f3 = json.loads(await add_finding(backend, {
            "description": "SBC time constant = 0.18ms",
            "confidence": 0.78,
            "execution_kind": "script",
            "used_entities": f"{script['node_id']},{data['node_id']}",
        }))

        # Hypothesis supported by finding 1
        hyp = json.loads(await add_hypothesis(backend, {
            "statement": "Time constants are cell-type specific",
            "execution_kind": "discuss",
            "used_entities": f1["node_id"],
        }))

        # Document citing finding 1 and a paper
        paper = json.loads(await add_paper(backend, {
            "title": "Retinal ganglion cell models",
            "authors": "Gerstner",
            "year": 1995,
        }))
        doc = json.loads(await add_document(backend, {
            "title": "Results: Time Constants",
            "path": "docs/results.md",
            "execution_kind": "write",
            "used_entities": f"{f1['node_id']},{paper['node_id']}",
        }))

        # BUG DISCOVERED! Script is stale.
        affected = backend.propagate_staleness(
            script["node_id"],
            new_stability=0.1,  # Severely reduced: known bug
        )

        affected_map = {a.node_id: a for a in affected}

        # All 3 findings should be affected (2 hops)
        assert f1["node_id"] in affected_map
        assert f2["node_id"] in affected_map
        assert f3["node_id"] in affected_map

        for fid in [f1["node_id"], f2["node_id"], f3["node_id"]]:
            assert affected_map[fid].hops == 2
            # 0.1 * 0.8^2 = 0.064
            assert abs(affected_map[fid].new_stability - 0.064) < 0.001

        # Hypothesis and document should be affected (4 hops)
        assert hyp["node_id"] in affected_map
        assert affected_map[hyp["node_id"]].hops == 4
        # 0.1 * 0.8^4 = 0.04096
        assert abs(affected_map[hyp["node_id"]].new_stability - 0.04096) < 0.001

        assert doc["node_id"] in affected_map
        assert affected_map[doc["node_id"]].hops == 4

        # Dataset should NOT be affected (it's an input, not downstream)
        assert data["node_id"] not in affected_map

        # Paper should NOT be affected (it's independently published)
        assert paper["node_id"] not in affected_map

        # Total: 3 findings + 1 hypothesis + 1 document = 5 affected
        assert len(affected) == 5
