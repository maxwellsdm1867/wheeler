"""E2E provenance chain tests against live Neo4j.

Builds real provenance chains in Neo4j, modifies upstream nodes,
runs propagate_invalidation, and verifies downstream stability
changes via Cypher queries.

Run: python -m pytest tests/e2e/test_provenance_chain.py -v
Requires: Neo4j running on localhost:7687
"""

from __future__ import annotations

import json

import pytest

from tests.e2e.conftest import E2E_TAG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _tag(driver, db, *node_ids):
    """Tag nodes for cleanup after the test."""
    async with driver.session(database=db) as session:
        for nid in node_ids:
            await session.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=nid, tag=E2E_TAG,
            )


async def _get_stability(driver, db, node_id) -> float:
    """Read current stability from the graph."""
    async with driver.session(database=db) as session:
        result = await session.run(
            "MATCH (n {id: $id}) RETURN n.stability AS stability",
            id=node_id,
        )
        rec = await result.single()
        assert rec is not None, f"Node {node_id} not found in graph"
        return float(rec["stability"])


async def _is_stale(driver, db, node_id) -> bool:
    """Check if a node is marked stale."""
    async with driver.session(database=db) as session:
        result = await session.run(
            "MATCH (n {id: $id}) RETURN n.stale AS stale",
            id=node_id,
        )
        rec = await result.single()
        assert rec is not None, f"Node {node_id} not found in graph"
        return bool(rec["stale"])


# ===================================================================
# Simple chain: Script -> Execution -> Finding
# ===================================================================


class TestSimpleChainE2E:
    """Script changes, finding should lose stability in real Neo4j."""

    @pytest.mark.asyncio
    async def test_script_change_propagates_to_finding(self, e2e_config, sandbox):
        """Build Script -> Execution -> Finding, then invalidate the script.

        After propagation:
        - Script should be marked stale with reduced stability
        - Finding should be marked stale with decayed stability
        """
        from wheeler.graph.driver import get_async_driver
        from wheeler.provenance import propagate_invalidation
        from wheeler.tools.graph_tools import execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create real file for path validation
        script_file = sandbox / "scripts" / "provchain_fit.py"
        script_file.write_text("# e2e provchain test\n")

        # Build the chain using real tools
        script = json.loads(await execute_tool(
            "add_script",
            {"path": str(script_file), "language": "python",
             "hash": "e2e_hash_original"},
            e2e_config,
        ))
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E provchain: tau = 0.12ms",
             "confidence": 0.85,
             "execution_kind": "script",
             "used_entities": script["node_id"]},
            e2e_config,
        ))
        exec_id = finding["provenance"]["execution_id"]

        await _tag(driver, db, script["node_id"], finding["node_id"], exec_id)

        # Verify initial stability
        script_stab = await _get_stability(driver, db, script["node_id"])
        finding_stab = await _get_stability(driver, db, finding["node_id"])
        assert script_stab == 0.5   # Script/generated
        assert finding_stab == 0.3  # Finding/generated

        # Propagate invalidation (real Cypher)
        affected = await propagate_invalidation(
            e2e_config,
            changed_node_id=script["node_id"],
            new_stability=0.1,
        )

        # Script should be stale
        assert await _is_stale(driver, db, script["node_id"])
        assert await _get_stability(driver, db, script["node_id"]) == pytest.approx(0.1)

        # Finding should be affected
        assert len(affected) >= 1
        finding_affected = [a for a in affected if a.node_id == finding["node_id"]]
        assert len(finding_affected) == 1
        assert finding_affected[0].hops == 2

        # Verify in graph
        new_stab = await _get_stability(driver, db, finding["node_id"])
        # 0.1 * 0.8^2 = 0.064
        assert new_stab == pytest.approx(0.064, abs=0.001)
        assert await _is_stale(driver, db, finding["node_id"])


# ===================================================================
# Branching: One script feeds multiple findings
# ===================================================================


class TestBranchingChainE2E:
    """One script change affects all downstream findings."""

    @pytest.mark.asyncio
    async def test_one_script_three_findings(self, e2e_config, sandbox):
        from wheeler.graph.driver import get_async_driver
        from wheeler.provenance import propagate_invalidation
        from wheeler.tools.graph_tools import execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create real file for path validation
        script_file = sandbox / "scripts" / "branch_pop.py"
        script_file.write_text("# e2e branch test\n")

        # One script
        script = json.loads(await execute_tool(
            "add_script",
            {"path": str(script_file), "language": "python",
             "hash": "branch_hash_001"},
            e2e_config,
        ))

        # Three findings from the same script
        tag_ids = [script["node_id"]]
        finding_ids = []
        for desc in ["parasol tau=0.12", "midget tau=0.14", "SBC tau=0.18"]:
            f = json.loads(await execute_tool(
                "add_finding",
                {"description": f"E2E branch: {desc}", "confidence": 0.85,
                 "execution_kind": "script",
                 "used_entities": script["node_id"]},
                e2e_config,
            ))
            finding_ids.append(f["node_id"])
            tag_ids.append(f["node_id"])
            tag_ids.append(f["provenance"]["execution_id"])

        await _tag(driver, db, *tag_ids)

        # Invalidate the script
        affected = await propagate_invalidation(
            e2e_config,
            changed_node_id=script["node_id"],
            new_stability=0.1,
        )

        # All 3 findings should be affected
        affected_ids = {a.node_id for a in affected}
        for fid in finding_ids:
            assert fid in affected_ids, f"Finding {fid} not in affected set"

        # All at 2 hops with same stability
        for a in affected:
            if a.node_id in finding_ids:
                assert a.hops == 2
                assert a.new_stability == pytest.approx(0.064, abs=0.001)


# ===================================================================
# Deep chain: Script -> Finding -> Hypothesis -> Document
# ===================================================================


class TestDeepChainE2E:
    """Multi-hop propagation through a real research workflow."""

    @pytest.mark.asyncio
    async def test_four_layer_cascade(self, e2e_config, sandbox):
        """Script -> Finding (2 hops) -> Hypothesis (4 hops) -> Document doesn't chain further."""
        from wheeler.graph.driver import get_async_driver
        from wheeler.provenance import propagate_invalidation
        from wheeler.tools.graph_tools import execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        tag_ids = []

        # Create real file for path validation
        script_file = sandbox / "scripts" / "deep_analysis.py"
        script_file.write_text("# e2e deep chain test\n")

        # Layer 1: Script
        script = json.loads(await execute_tool(
            "add_script",
            {"path": str(script_file), "language": "python",
             "hash": "deep_hash_001"},
            e2e_config,
        ))
        tag_ids.append(script["node_id"])

        # Layer 2: Finding from script
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E deep: key result",
             "confidence": 0.85,
             "execution_kind": "script",
             "used_entities": script["node_id"]},
            e2e_config,
        ))
        tag_ids.extend([finding["node_id"], finding["provenance"]["execution_id"]])

        # Layer 3: Hypothesis from discussion about finding
        hyp = json.loads(await execute_tool(
            "add_hypothesis",
            {"statement": "E2E deep: mechanism hypothesis",
             "execution_kind": "discuss",
             "used_entities": finding["node_id"]},
            e2e_config,
        ))
        tag_ids.extend([hyp["node_id"], hyp["provenance"]["execution_id"]])

        # Layer 4: Document citing finding
        doc = json.loads(await execute_tool(
            "add_document",
            {"title": "E2E deep: results draft",
             "path": "docs/deep_results.md",
             "execution_kind": "write",
             "used_entities": finding["node_id"]},
            e2e_config,
        ))
        tag_ids.extend([doc["node_id"], doc["provenance"]["execution_id"]])

        await _tag(driver, db, *tag_ids)

        # Invalidate the script
        affected = await propagate_invalidation(
            e2e_config,
            changed_node_id=script["node_id"],
            new_stability=0.1,
        )

        affected_map = {a.node_id: a for a in affected}

        # Finding at 2 hops
        assert finding["node_id"] in affected_map
        assert affected_map[finding["node_id"]].hops == 2
        # 0.1 * 0.8^2 = 0.064
        assert affected_map[finding["node_id"]].new_stability == pytest.approx(0.064, abs=0.001)

        # Hypothesis at 4 hops
        assert hyp["node_id"] in affected_map
        assert affected_map[hyp["node_id"]].hops == 4
        # 0.1 * 0.8^4 = 0.04096
        assert affected_map[hyp["node_id"]].new_stability == pytest.approx(0.04096, abs=0.001)

        # Document at 4 hops
        assert doc["node_id"] in affected_map
        assert affected_map[doc["node_id"]].hops == 4


# ===================================================================
# Clear stale and re-validate
# ===================================================================


class TestClearStaleE2E:
    """After fixing a script, clear its stale flag and verify."""

    @pytest.mark.asyncio
    async def test_clear_stale_restores_stability(self, e2e_config, sandbox):
        from wheeler.graph.driver import get_async_driver
        from wheeler.provenance import propagate_invalidation, clear_stale
        from wheeler.tools.graph_tools import execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create real file for path validation
        script_file = sandbox / "scripts" / "clear_fix.py"
        script_file.write_text("# e2e clear stale test\n")

        # Build chain
        script = json.loads(await execute_tool(
            "add_script",
            {"path": str(script_file), "language": "python",
             "hash": "clear_hash_001"},
            e2e_config,
        ))
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E clear: result before fix",
             "confidence": 0.8,
             "execution_kind": "script",
             "used_entities": script["node_id"]},
            e2e_config,
        ))
        exec_id = finding["provenance"]["execution_id"]
        await _tag(driver, db, script["node_id"], finding["node_id"], exec_id)

        # Invalidate
        await propagate_invalidation(
            e2e_config,
            changed_node_id=script["node_id"],
            new_stability=0.1,
        )
        assert await _is_stale(driver, db, script["node_id"])

        # Fix the script and clear stale
        cleared = await clear_stale(
            e2e_config,
            node_id=script["node_id"],
            new_stability=0.5,  # Script re-validated
        )
        assert cleared is True

        # Verify script is no longer stale
        stab = await _get_stability(driver, db, script["node_id"])
        assert stab == pytest.approx(0.5)

        # Note: clearing the script doesn't auto-clear the finding.
        # The finding remains stale until explicitly re-validated or
        # the scientist re-runs the analysis.
        assert await _is_stale(driver, db, finding["node_id"])


# ===================================================================
# Stale script detection with real files
# ===================================================================


class TestStaleDetectionE2E:
    """Detect stale scripts by comparing file hashes."""

    @pytest.mark.asyncio
    async def test_detect_stale_after_file_change(self, e2e_config, sandbox):
        """Register a script, modify the file, detect staleness."""
        from wheeler.graph.driver import get_async_driver
        from wheeler.graph.provenance import hash_file, detect_stale_scripts
        from wheeler.tools.graph_tools import execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Create a real file and register it
        script_path = sandbox / "scripts" / "e2e_stale_test.py"
        script_path.write_text("import numpy as np\nresult = np.mean(data)\n")
        original_hash = hash_file(script_path)

        script = json.loads(await execute_tool(
            "add_script",
            {"path": str(script_path), "language": "python",
             "hash": original_hash},
            e2e_config,
        ))
        await _tag(driver, db, script["node_id"])

        # Not stale yet
        stale = await detect_stale_scripts(e2e_config)
        stale_ids = {s.node_id for s in stale}
        assert script["node_id"] not in stale_ids

        # Modify the file
        script_path.write_text("import numpy as np\nresult = np.median(data)\n")

        # Now it should be stale
        stale = await detect_stale_scripts(e2e_config)
        stale_ids = {s.node_id for s in stale}
        assert script["node_id"] in stale_ids

        # Find our stale script's details
        our_stale = [s for s in stale if s.node_id == script["node_id"]][0]
        assert our_stale.stored_hash == original_hash
        assert our_stale.current_hash != original_hash
        assert our_stale.current_hash == hash_file(script_path)


# ===================================================================
# Full detect-and-propagate cycle
# ===================================================================


class TestDetectAndPropagateE2E:
    """Full cycle: detect stale scripts, propagate, verify downstream."""

    @pytest.mark.asyncio
    async def test_full_stale_propagation_cycle(self, e2e_config, sandbox):
        """
        1. Create script file and register with hash
        2. Create finding from script
        3. Modify the script file
        4. Call detect_and_propagate_stale
        5. Verify finding is now stale with reduced stability
        """
        from wheeler.graph.driver import get_async_driver
        from wheeler.graph.provenance import hash_file
        from wheeler.provenance import detect_and_propagate_stale
        from wheeler.tools.graph_tools import execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # 1. Create script file
        script_path = sandbox / "scripts" / "e2e_full_cycle.py"
        script_path.write_text("v1: original analysis code\n")
        original_hash = hash_file(script_path)

        script = json.loads(await execute_tool(
            "add_script",
            {"path": str(script_path), "language": "python",
             "hash": original_hash},
            e2e_config,
        ))

        # 2. Create finding from script
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E full cycle: measurement result",
             "confidence": 0.9,
             "execution_kind": "script",
             "used_entities": script["node_id"]},
            e2e_config,
        ))
        exec_id = finding["provenance"]["execution_id"]
        await _tag(driver, db, script["node_id"], finding["node_id"], exec_id)

        # Verify initial state
        assert await _get_stability(driver, db, finding["node_id"]) == pytest.approx(0.3)

        # 3. Modify the script file
        script_path.write_text("v2: bug fix in analysis code\n")

        # 4. Detect and propagate
        result = await detect_and_propagate_stale(e2e_config)

        assert result["stale_scripts"] >= 1

        # 5. Verify finding is now stale
        finding_stab = await _get_stability(driver, db, finding["node_id"])
        assert finding_stab < 0.3, (
            f"Finding stability should be reduced below 0.3, got {finding_stab}"
        )
        assert await _is_stale(driver, db, finding["node_id"])


# ===================================================================
# WAS_DERIVED_FROM propagation
# ===================================================================


class TestDerivedFromE2E:
    """Test WAS_DERIVED_FROM chain propagation in real Neo4j."""

    @pytest.mark.asyncio
    async def test_derived_finding_gets_stale(self, e2e_config):
        """Finding2 WAS_DERIVED_FROM Finding1. Invalidating F1 hits F2."""
        from wheeler.graph.driver import get_async_driver
        from wheeler.provenance import propagate_invalidation
        from wheeler.tools.graph_tools import execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        f1 = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E derived: original measurement",
             "confidence": 0.9},
            e2e_config,
        ))
        f2 = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E derived: corrected measurement",
             "confidence": 0.85},
            e2e_config,
        ))

        # Link: F2 WAS_DERIVED_FROM F1
        link = json.loads(await execute_tool(
            "link_nodes",
            {"source_id": f2["node_id"],
             "target_id": f1["node_id"],
             "relationship": "WAS_DERIVED_FROM"},
            e2e_config,
        ))
        assert link["status"] == "linked"

        await _tag(driver, db, f1["node_id"], f2["node_id"])

        # Invalidate F1
        affected = await propagate_invalidation(
            e2e_config,
            changed_node_id=f1["node_id"],
            new_stability=0.1,
        )

        # F2 should be affected
        affected_ids = {a.node_id for a in affected}
        assert f2["node_id"] in affected_ids

        # Verify in graph
        f2_stab = await _get_stability(driver, db, f2["node_id"])
        # 0.1 * 0.8^1 = 0.08 (1 hop for WAS_DERIVED_FROM)
        assert f2_stab == pytest.approx(0.08, abs=0.01)


# ===================================================================
# Realistic scenario: bug discovery
# ===================================================================


class TestBugDiscoveryE2E:
    """Realistic scenario: scientist discovers a bug in their analysis."""

    @pytest.mark.asyncio
    async def test_bug_cascade(self, e2e_config, sandbox):
        """
        Build a realistic graph:
          Script + Dataset -> Finding1, Finding2
          Finding1 -> Hypothesis (supports)
          Finding1 -> Document (appears_in)

        Modify the script file, detect stale, propagate, verify:
        - Both findings lose stability
        - Hypothesis loses stability (via finding1)
        - Document loses stability (via finding1)
        - Dataset is NOT affected (it's an input)
        """
        from wheeler.graph.driver import get_async_driver
        from wheeler.graph.provenance import hash_file
        from wheeler.provenance import detect_and_propagate_stale
        from wheeler.tools.graph_tools import execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        tag_ids = []

        # Create real script file
        script_path = sandbox / "scripts" / "e2e_bug_test.py"
        script_path.write_text("# v1: buggy analysis\nimport numpy as np\n")

        # Register nodes
        script = json.loads(await execute_tool(
            "add_script",
            {"path": str(script_path), "language": "python",
             "hash": hash_file(script_path)},
            e2e_config,
        ))
        tag_ids.append(script["node_id"])

        # Create real data file for path validation
        data_file = sandbox / "data" / "e2e_bug_recordings.mat"
        data_file.write_bytes(b"fake mat data")

        dataset = json.loads(await execute_tool(
            "add_dataset",
            {"path": str(data_file), "type": "mat",
             "description": "E2E bug: recordings"},
            e2e_config,
        ))
        tag_ids.append(dataset["node_id"])

        # Two findings from script+dataset
        f1 = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E bug: parasol tau=0.12",
             "confidence": 0.85,
             "execution_kind": "script",
             "used_entities": f"{script['node_id']},{dataset['node_id']}"},
            e2e_config,
        ))
        tag_ids.extend([f1["node_id"], f1["provenance"]["execution_id"]])

        f2 = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E bug: midget tau=0.14",
             "confidence": 0.82,
             "execution_kind": "script",
             "used_entities": f"{script['node_id']},{dataset['node_id']}"},
            e2e_config,
        ))
        tag_ids.extend([f2["node_id"], f2["provenance"]["execution_id"]])

        # Hypothesis from finding1
        hyp = json.loads(await execute_tool(
            "add_hypothesis",
            {"statement": "E2E bug: cell type determines tau",
             "execution_kind": "discuss",
             "used_entities": f1["node_id"]},
            e2e_config,
        ))
        tag_ids.extend([hyp["node_id"], hyp["provenance"]["execution_id"]])

        # Document citing finding1
        doc = json.loads(await execute_tool(
            "add_document",
            {"title": "E2E bug: results section",
             "path": "docs/bug_results.md",
             "execution_kind": "write",
             "used_entities": f1["node_id"]},
            e2e_config,
        ))
        tag_ids.extend([doc["node_id"], doc["provenance"]["execution_id"]])

        await _tag(driver, db, *tag_ids)

        # Record initial stabilities
        initial = {}
        for nid in [script["node_id"], dataset["node_id"],
                     f1["node_id"], f2["node_id"],
                     hyp["node_id"], doc["node_id"]]:
            initial[nid] = await _get_stability(driver, db, nid)

        # BUG DISCOVERED: modify the script
        script_path.write_text("# v2: fixed analysis\nimport numpy as np\n# bug fixed\n")

        # Detect and propagate
        result = await detect_and_propagate_stale(e2e_config)
        assert result["stale_scripts"] >= 1

        # Verify: script is stale
        assert await _is_stale(driver, db, script["node_id"])

        # Verify: both findings lost stability
        for fid in [f1["node_id"], f2["node_id"]]:
            new_stab = await _get_stability(driver, db, fid)
            assert new_stab < initial[fid], (
                f"Finding {fid} stability should decrease: {initial[fid]} -> {new_stab}"
            )

        # Verify: hypothesis lost stability
        hyp_stab = await _get_stability(driver, db, hyp["node_id"])
        assert hyp_stab < initial[hyp["node_id"]]

        # Verify: document lost stability
        doc_stab = await _get_stability(driver, db, doc["node_id"])
        assert doc_stab < initial[doc["node_id"]]

        # Verify: dataset is NOT affected (it's an input, not downstream)
        dataset_stab = await _get_stability(driver, db, dataset["node_id"])
        assert dataset_stab == pytest.approx(initial[dataset["node_id"]]), (
            "Dataset should NOT be affected by script change"
        )
