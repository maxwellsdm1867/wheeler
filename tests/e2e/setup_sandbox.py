#!/usr/bin/env python3
"""Populate the local Neo4j graph with SRM-like reference context.

Run: python tests/e2e/setup_sandbox.py [--reset]

This creates a sandbox graph with:
  - Analysis nodes for SRM scripts (reference tier)
  - Dataset nodes for recording data (reference tier)
  - Paper nodes for key literature (reference tier)
  - Finding nodes for established results (reference tier)
  - Hypothesis and OpenQuestion nodes (generated tier)
  - Full provenance chain: Paper → Analysis → Finding → Document

After running, test Wheeler commands against this graph:
  /wh:status, /wh:ingest, /wh:plan, etc.

Use --reset to wipe all sandbox nodes and start fresh.
"""

from __future__ import annotations

import asyncio
import sys

from wheeler.config import load_config
from wheeler.graph.driver import get_async_driver
from wheeler.graph.schema import init_schema, get_status, generate_node_id
from wheeler.tools.graph_tools import execute_tool

SANDBOX_TAG = "sandbox"


async def reset_sandbox(config):
    """Delete all sandbox-tagged nodes."""
    driver = get_async_driver(config)
    async with driver.session(database=config.neo4j.database) as session:
        result = await session.run(
            "MATCH (n) WHERE n.sandbox = $tag DETACH DELETE n RETURN count(*) AS deleted",
            tag=SANDBOX_TAG,
        )
        rec = await result.single()
        print(f"Deleted {rec['deleted']} sandbox nodes.")


async def tag_node(config, node_id: str):
    """Tag a node for sandbox cleanup."""
    driver = get_async_driver(config)
    async with driver.session(database=config.neo4j.database) as session:
        await session.run(
            "MATCH (n {id: $id}) SET n.sandbox = $tag",
            id=node_id, tag=SANDBOX_TAG,
        )


async def populate(config):
    """Populate the graph with SRM-like reference context."""
    import json

    print("\n=== Wheeler Sandbox Setup ===\n")

    # 1. Schema
    print("1. Applying schema constraints...")
    applied = await init_schema(config)
    print(f"   {len(applied)} constraints/indexes applied.")

    # 2. Papers (key SRM literature)
    print("\n2. Adding key papers (reference tier)...")
    papers = {}
    paper_data = [
        {
            "title": "Spike Response Model: A framework for neural coding",
            "authors": "Gerstner, W.",
            "doi": "10.1162/neco.1995.7.6.1141",
            "year": 1995,
        },
        {
            "title": "Spike train metrics for quantifying neural coding",
            "authors": "Victor, J.D., Purpura, K.P.",
            "doi": "10.1088/0954-898X/8/2/003",
            "year": 1997,
        },
        {
            "title": "Functional diversity of retinal ganglion cells in the primate",
            "authors": "Field, G.D., Chichilnisky, E.J.",
            "doi": "10.1146/annurev-neuro-060909-153204",
            "year": 2007,
        },
    ]
    for pd in paper_data:
        result = json.loads(await execute_tool("add_paper", pd, config))
        papers[pd["title"]] = result["node_id"]
        await tag_node(config, result["node_id"])
        print(f"   [{result['node_id']}] {pd['title'][:60]}")

    # 3. Datasets (recording data)
    print("\n3. Adding datasets (reference tier)...")
    datasets = {}
    dataset_data = [
        {"path": "data/parasol_on_recordings.mat", "type": "mat",
         "description": "Parasol ON RGC current injection recordings, 10kHz, 12 cells"},
        {"path": "data/parasol_off_recordings.mat", "type": "mat",
         "description": "Parasol OFF RGC current injection recordings, 10kHz, 8 cells"},
        {"path": "data/midget_on_recordings.mat", "type": "mat",
         "description": "Midget ON RGC current injection recordings, 10kHz, 10 cells"},
        {"path": "data/midget_off_recordings.mat", "type": "mat",
         "description": "Midget OFF RGC current injection recordings, 10kHz, 6 cells"},
        {"path": "data/srm_fit_results.csv", "type": "csv",
         "description": "SRM parameter fits: tau_rise, tau_decay, threshold, noise per cell"},
    ]
    for dd in dataset_data:
        result = json.loads(await execute_tool("add_dataset", dd, config))
        datasets[dd["path"]] = result["node_id"]
        await tag_node(config, result["node_id"])
        # Promote to reference
        await execute_tool("set_tier", {"node_id": result["node_id"], "tier": "reference"}, config)
        print(f"   [{result['node_id']}] {dd['description'][:60]}")

    # 4. Analysis nodes (key scripts)
    print("\n4. Adding analysis scripts (reference tier)...")
    analyses = {}
    driver = get_async_driver(config)
    analysis_data = [
        {"desc": "4-parameter SRM fitting: tau_rise, tau_decay, threshold, noise",
         "path": "scripts/fit_srm_model.m", "lang": "matlab"},
        {"desc": "Victor-Purpura spike distance loss function",
         "path": "scripts/compute_vp_loss.m", "lang": "matlab"},
        {"desc": "Population analysis: compare SRM fits across cell types",
         "path": "scripts/analyze_population.py", "lang": "python"},
        {"desc": "Cross-prediction with rescaling protocol",
         "path": "scripts/cross_predict.m", "lang": "matlab"},
    ]
    for ad in analysis_data:
        node_id = generate_node_id("A")
        analyses[ad["path"]] = node_id
        async with driver.session(database=config.neo4j.database) as session:
            await session.run(
                "CREATE (a:Analysis {id: $id, description: $desc, "
                "script_path: $path, language: $lang, tier: 'reference', "
                "sandbox: $tag, script_hash: ''})",
                id=node_id, desc=ad["desc"], path=ad["path"],
                lang=ad["lang"], tag=SANDBOX_TAG,
            )
        print(f"   [{node_id}] {ad['desc'][:60]}")

    # 5. Link papers → analyses (INFORMED)
    print("\n5. Linking papers to analyses...")
    gerstner_id = papers["Spike Response Model: A framework for neural coding"]
    vp_id = papers["Spike train metrics for quantifying neural coding"]
    await execute_tool("link_nodes", {
        "source_id": gerstner_id,
        "target_id": analyses["scripts/fit_srm_model.m"],
        "relationship": "INFORMED",
    }, config)
    print(f"   {gerstner_id} -INFORMED-> {analyses['scripts/fit_srm_model.m']}")

    await execute_tool("link_nodes", {
        "source_id": vp_id,
        "target_id": analyses["scripts/compute_vp_loss.m"],
        "relationship": "INFORMED",
    }, config)
    print(f"   {vp_id} -INFORMED-> {analyses['scripts/compute_vp_loss.m']}")

    # 6. Link analyses → datasets (USED_DATA)
    print("\n6. Linking analyses to datasets...")
    for ds_path, ds_id in datasets.items():
        if ds_path.endswith(".mat"):
            await execute_tool("link_nodes", {
                "source_id": analyses["scripts/fit_srm_model.m"],
                "target_id": ds_id,
                "relationship": "USED_DATA",
            }, config)
            print(f"   {analyses['scripts/fit_srm_model.m']} -USED_DATA-> {ds_id}")

    # 7. Findings (established results = reference)
    print("\n7. Adding established findings (reference tier)...")
    findings = {}
    finding_data = [
        {"description": "Parasol ON: tau_rise=0.12ms, tau_decay=0.48ms, VP_loss=0.15 at q=200Hz",
         "confidence": 0.92},
        {"description": "Parasol OFF: tau_rise=0.11ms, tau_decay=0.52ms, VP_loss=0.18 at q=200Hz",
         "confidence": 0.89},
        {"description": "Midget ON: tau_rise=0.14ms, tau_decay=0.45ms, VP_loss=0.22 at q=200Hz",
         "confidence": 0.85},
        {"description": "Midget OFF: tau_rise=0.13ms, tau_decay=0.50ms, VP_loss=0.19 at q=200Hz",
         "confidence": 0.87},
        {"description": "Resting potentials not significantly different between parasol and midget (p=0.34)",
         "confidence": 0.95},
    ]
    for fd in finding_data:
        result = json.loads(await execute_tool("add_finding", fd, config))
        findings[fd["description"]] = result["node_id"]
        await tag_node(config, result["node_id"])
        await execute_tool("set_tier", {"node_id": result["node_id"], "tier": "reference"}, config)
        print(f"   [{result['node_id']}] {fd['description'][:60]}")

    # Link findings to analyses
    for fid in findings.values():
        await execute_tool("link_nodes", {
            "source_id": analyses["scripts/fit_srm_model.m"],
            "target_id": fid,
            "relationship": "GENERATED",
        }, config)

    # 8. Hypothesis (generated — this is what we're investigating)
    print("\n8. Adding hypothesis (generated tier)...")
    hyp = json.loads(await execute_tool("add_hypothesis", {
        "statement": "Parasol and midget RGCs share the same spike generation process — SRM parameters should be interchangeable via a scaling factor",
    }, config))
    await tag_node(config, hyp["node_id"])
    print(f"   [{hyp['node_id']}] {hyp['node_id']}")

    # Link findings that support/contradict
    for desc, fid in findings.items():
        if "Resting" in desc:
            await execute_tool("link_nodes", {
                "source_id": fid, "target_id": hyp["node_id"],
                "relationship": "SUPPORTS",
            }, config)

    # 9. Open questions (generated)
    print("\n9. Adding open questions (generated tier)...")
    questions = [
        {"question": "Is the VP loss difference between parasol and midget at q=200Hz biologically meaningful or within noise?", "priority": 8},
        {"question": "Should ON and OFF subtypes be analyzed separately or pooled?", "priority": 7},
        {"question": "Does the SRM cross-prediction improve with frequency-dependent rescaling?", "priority": 9},
    ]
    for qd in questions:
        result = json.loads(await execute_tool("add_question", qd, config))
        await tag_node(config, result["node_id"])
        print(f"   [{result['node_id']}] (priority {qd['priority']}) {qd['question'][:60]}")

    # 10. Summary
    print("\n=== Sandbox Ready ===\n")
    status = await get_status(config)
    for label, count in sorted(status.items()):
        if count > 0:
            print(f"  {label}: {count}")

    print(f"\nTotal: {sum(status.values())} nodes")
    print("\nTest with: /wh:status, /wh:plan, /wh:write")
    print("Reset with: python tests/e2e/setup_sandbox.py --reset")


async def main():
    config = load_config()

    if "--reset" in sys.argv:
        await reset_sandbox(config)
        print("Sandbox cleared. Run without --reset to repopulate.")
        return

    await populate(config)


if __name__ == "__main__":
    asyncio.run(main())
