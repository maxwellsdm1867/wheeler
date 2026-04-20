"""E2E tests simulating the actual tool-call sequences each /wh:* act performs.

Each test class walks through the exact steps an act prescribes, calling
real MCP tools against a live Neo4j graph, and verifying the graph holds
the correct state at every step. This catches the case where an act's
instructions produce the wrong graph state even though individual tools
work correctly in isolation.

Run: python -m pytest tests/e2e/test_graph_first_acts.py -v
Requires: Neo4j running on localhost:7687
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.conftest import E2E_TAG


# ────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────


async def _tag(driver, db, node_id):
    async with driver.session(database=db) as session:
        await session.run(
            "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
            id=node_id, tag=E2E_TAG,
        )


async def _get_prop(driver, db, node_id, prop):
    async with driver.session(database=db) as session:
        result = await session.run(
            "MATCH (n {id: $id}) RETURN n[$prop] AS val",
            id=node_id, prop=prop,
        )
        rec = await result.single()
        return rec["val"] if rec else None


async def _count_rels(driver, db, src_id, rel_type, tgt_id):
    async with driver.session(database=db) as session:
        result = await session.run(
            "MATCH (a {id: $src})-[r]->(b {id: $tgt}) "
            "WHERE type(r) = $rel RETURN count(r) AS c",
            src=src_id, tgt=tgt_id, rel=rel_type,
        )
        rec = await result.single()
        return rec["c"]


def _call(coro):
    """Shortcut: await an execute_tool call and parse JSON."""
    return coro


# ────────────────────────────────────────────────────────
# /wh:execute workflow
#
# Step 1: query_plans(status="approved") + query_plans(status="in-progress")
# Step 2: if found, pick plan, read file via path
# Step 3: update_node(PL-xxxx, status="in-progress")
# Step 4: execute tasks, add_finding, link provenance
# Step 5: update_node(PL-xxxx, status="completed")
# ────────────────────────────────────────────────────────


class TestExecuteActWorkflow:
    """Simulate /wh:execute: graph-first plan discovery and execution."""

    @pytest.mark.asyncio
    async def test_execute_finds_approved_plan_from_graph(self, sandbox, e2e_config):
        """
        /wh:execute Step 1: query_plans(status="approved") returns the plan
        WITHOUT any filesystem scan. The graph is the only lookup.
        """
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        cleanup = []

        # Scientist created and approved a plan (via /wh:plan)
        plan_file = sandbox / ".plans" / "e2e-execute-act.md"
        plan_file.write_text(
            "---\ninvestigation: execute-act-test\ngraph_node: \"\"\n"
            "status: approved\n---\n# Test plan\n## Objective\nTest.\n"
        )
        reg = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: Execute act test", "status": "approved"},
            e2e_config,
        ))
        plan_id = reg["node_id"]
        cleanup.append(plan_id)
        await _tag(driver, db, plan_id)

        # --- /wh:execute Step 1: graph-first lookup ---
        approved = json.loads(await execute_tool(
            "query_plans", {"status": "approved"}, e2e_config,
        ))
        in_progress = json.loads(await execute_tool(
            "query_plans", {"status": "in-progress"}, e2e_config,
        ))

        # Plan must be discoverable from graph alone
        all_plans = approved["plans"] + in_progress["plans"]
        found = [p for p in all_plans if p["id"] == plan_id]
        assert len(found) == 1, "Execute must find the approved plan via graph query"
        assert found[0]["status"] == "approved"
        assert found[0]["title"] == "E2E: Execute act test"

        # --- Step 2: read the plan file from graph's path field ---
        plan_path = found[0].get("path", "")
        assert plan_path, "Graph record must have the file path"
        assert Path(plan_path).exists(), "Plan file must exist at graph's path"

        # --- Step 3: transition to in-progress via update_node ---
        update_result = json.loads(await execute_tool(
            "update_node", {"node_id": plan_id, "status": "in-progress"}, e2e_config,
        ))
        assert update_result["changes"]["status"]["new"] == "in-progress"

        # Graph must now show in-progress, not approved
        recheck = json.loads(await execute_tool(
            "query_plans", {"status": "approved"}, e2e_config,
        ))
        assert plan_id not in [p["id"] for p in recheck["plans"]]
        recheck2 = json.loads(await execute_tool(
            "query_plans", {"status": "in-progress"}, e2e_config,
        ))
        assert plan_id in [p["id"] for p in recheck2["plans"]]

        # --- Step 4: execution produces findings with provenance ---
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E execute: tau_rise parasol = 0.12ms",
             "confidence": 0.85},
            e2e_config,
        ))
        cleanup.append(finding["node_id"])
        await _tag(driver, db, finding["node_id"])

        execution = json.loads(await execute_tool(
            "add_execution",
            {"kind": "script_run", "description": "E2E: SRM fit on parasol"},
            e2e_config,
        ))
        cleanup.append(execution["node_id"])
        await _tag(driver, db, execution["node_id"])

        await execute_tool("link_nodes", {
            "source_id": finding["node_id"],
            "target_id": execution["node_id"],
            "relationship": "WAS_GENERATED_BY",
        }, e2e_config)

        # --- Step 5: mark completed ---
        await execute_tool(
            "update_node", {"node_id": plan_id, "status": "completed"}, e2e_config,
        )
        final_status = await _get_prop(driver, db, plan_id, "status")
        assert final_status == "completed"

        # Finding is linked with full provenance
        assert await _count_rels(
            driver, db, finding["node_id"], "WAS_GENERATED_BY", execution["node_id"],
        ) == 1

        # Cleanup
        plan_file.unlink(missing_ok=True)
        for nid in cleanup:
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_execute_onramp_registers_untracked_plan(self, sandbox, e2e_config):
        """
        /wh:execute on-ramp: when graph returns nothing, unregistered .plans/*.md
        files are offered for registration via ensure_artifact.
        """
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Write a plan file that is NOT registered in graph
        plan_file = sandbox / ".plans" / "e2e-onramp.md"
        plan_file.write_text(
            "---\ninvestigation: onramp-test\nstatus: approved\n---\n"
            "# Onramp test\n## Objective\nTest on-ramp.\n"
        )

        # Graph query returns nothing for this topic
        result = json.loads(await execute_tool(
            "query_plans", {"keyword": "onramp-test"}, e2e_config,
        ))
        assert result["count"] == 0, "Plan should not be in graph yet"

        # On-ramp: register via ensure_artifact (what execute.md instructs)
        reg = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: Onramp test", "status": "approved"},
            e2e_config,
        ))
        plan_id = reg["node_id"]
        await _tag(driver, db, plan_id)

        # Now graph query DOES find it
        result2 = json.loads(await execute_tool(
            "query_plans", {"status": "approved"}, e2e_config,
        ))
        assert plan_id in [p["id"] for p in result2["plans"]]

        # Cleanup
        plan_file.unlink(missing_ok=True)
        (Path(e2e_config.knowledge_path) / f"{plan_id}.json").unlink(missing_ok=True)
        (Path(e2e_config.synthesis_path) / f"{plan_id}.md").unlink(missing_ok=True)


# ────────────────────────────────────────────────────────
# /wh:plan workflow
#
# Step 1: query_plans(keyword=topic) to check for duplicates
# Step 2: write .plans/<name>.md
# Step 3: ensure_artifact(path, artifact_type="plan", status="draft")
# Step 4: write PL-xxxx into file frontmatter
# Step 5: on approval, update_node(PL-xxxx, status="approved")
# ────────────────────────────────────────────────────────


class TestPlanActWorkflow:
    """Simulate /wh:plan: dedup check, file write, graph registration, approval."""

    @pytest.mark.asyncio
    async def test_plan_dedup_then_register(self, sandbox, e2e_config):
        """Full /wh:plan flow: dedup check, write file, register, approve."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        topic = "E2E: Ion channel gating kinetics"

        # --- Step 1: dedup check ---
        dedup = json.loads(await execute_tool(
            "query_plans", {"keyword": "gating kinetics"}, e2e_config,
        ))
        assert dedup["count"] == 0, "No duplicate should exist yet"

        # --- Step 2: write the plan file ---
        plan_file = sandbox / ".plans" / "e2e-gating-kinetics.md"
        plan_file.write_text(
            "---\ninvestigation: gating-kinetics\ngraph_node: \"\"\n"
            "status: draft\ncreated: 2026-04-20\nupdated: 2026-04-20\n"
            "waves: 2\ntasks_total: 3\ntasks_wheeler: 2\ntasks_scientist: 1\n"
            "tasks_pair: 0\ngraph_nodes: []\nsuccess_criteria_met: \"0/2\"\n---\n"
            f"# Investigation: {topic}\n## Objective\n"
            "Characterize gating kinetics of Nav1.6 channels.\n"
            "## Tasks\n### 1. Literature search\n- **assignee**: wheeler\n"
        )

        # --- Step 3: register via ensure_artifact ---
        reg = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": topic, "status": "draft"},
            e2e_config,
        ))
        assert reg["action"] == "created"
        plan_id = reg["node_id"]
        await _tag(driver, db, plan_id)

        # --- Step 4: write node_id back into file (what the act instructs) ---
        content = plan_file.read_text()
        content = content.replace('graph_node: ""', f'graph_node: {plan_id}')
        plan_file.write_text(content)

        # Verify: graph has the plan, file has the node ID
        assert plan_id in plan_file.read_text()
        query = json.loads(await execute_tool(
            "query_plans", {"keyword": "gating kinetics"}, e2e_config,
        ))
        assert query["count"] >= 1
        assert any(p["id"] == plan_id for p in query["plans"])

        # --- Step 5: scientist approves ---
        await execute_tool(
            "update_node", {"node_id": plan_id, "status": "approved"}, e2e_config,
        )

        # Graph reflects approval
        approved = json.loads(await execute_tool(
            "query_plans", {"status": "approved"}, e2e_config,
        ))
        assert plan_id in [p["id"] for p in approved["plans"]]

        # --- Dedup: second plan on same topic is detected ---
        dedup2 = json.loads(await execute_tool(
            "query_plans", {"keyword": "gating kinetics"}, e2e_config,
        ))
        assert dedup2["count"] >= 1, "Dedup must detect existing plan"

        # Cleanup
        plan_file.unlink(missing_ok=True)
        (Path(e2e_config.knowledge_path) / f"{plan_id}.json").unlink(missing_ok=True)
        (Path(e2e_config.synthesis_path) / f"{plan_id}.md").unlink(missing_ok=True)


# ────────────────────────────────────────────────────────
# /wh:pause workflow
#
# Step 1: query_plans(status="in-progress") to find active plan
# Step 2: add_note(content=summary, context="session-continuation:PL-xxxx")
# Step 3: link_nodes(note, plan, "AROSE_FROM")
# Step 4: add_execution(kind="pause", description=...)
# Step 5: link_nodes(execution, plan, "WAS_INFORMED_BY")
# Step 6: render .continue-here.md from graph state
# ────────────────────────────────────────────────────────


class TestPauseActWorkflow:
    """Simulate /wh:pause: graph-native session state capture."""

    @pytest.mark.asyncio
    async def test_pause_captures_state_in_graph(self, e2e_config):
        """Full /wh:pause flow: find plan, write note, write execution, link both."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        cleanup = []

        # Setup: create an in-progress plan
        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Pause act investigation", "status": "in-progress"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        cleanup.append(plan_id)
        await _tag(driver, db, plan_id)

        # --- Step 1: find active plan from graph ---
        active = json.loads(await execute_tool(
            "query_plans", {"status": "in-progress"}, e2e_config,
        ))
        found = [p for p in active["plans"] if p["id"] == plan_id]
        assert len(found) == 1

        # --- Step 2: write continuation note ---
        note = json.loads(await execute_tool(
            "add_note",
            {"title": "Session continuation",
             "content": "Completed tasks 1-2 (lit search, data load). "
                        "Task 3 pending (model fitting). Key decision: "
                        "use VP distance metric, not MSE.",
             "context": f"session-continuation:{plan_id}"},
            e2e_config,
        ))
        note_id = note["node_id"]
        cleanup.append(note_id)
        await _tag(driver, db, note_id)

        # --- Step 3: link note to plan ---
        link1 = json.loads(await execute_tool(
            "link_nodes",
            {"source_id": note_id, "target_id": plan_id,
             "relationship": "AROSE_FROM"},
            e2e_config,
        ))
        assert link1["status"] == "linked"

        # --- Step 4: record pause execution ---
        pause_exec = json.loads(await execute_tool(
            "add_execution",
            {"kind": "pause",
             "description": "Pausing: tasks 1-2 done, task 3 pending (model fitting)"},
            e2e_config,
        ))
        pause_id = pause_exec["node_id"]
        cleanup.append(pause_id)
        await _tag(driver, db, pause_id)

        # --- Step 5: link execution to plan ---
        link2 = json.loads(await execute_tool(
            "link_nodes",
            {"source_id": pause_id, "target_id": plan_id,
             "relationship": "WAS_INFORMED_BY"},
            e2e_config,
        ))
        assert link2["status"] == "linked"

        # --- Verify full graph state ---
        # Note linked to plan
        assert await _count_rels(driver, db, note_id, "AROSE_FROM", plan_id) == 1
        # Pause linked to plan
        assert await _count_rels(driver, db, pause_id, "WAS_INFORMED_BY", plan_id) == 1
        # Note has the right context
        ctx = await _get_prop(driver, db, note_id, "context")
        assert ctx == f"session-continuation:{plan_id}"
        # Execution kind is pause
        kind = await _get_prop(driver, db, pause_id, "kind")
        assert kind == "pause"
        # Plan is still in-progress
        status = await _get_prop(driver, db, plan_id, "status")
        assert status == "in-progress"

        # Cleanup
        for nid in cleanup:
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)


# ────────────────────────────────────────────────────────
# /wh:resume workflow
#
# Step 0: query_plans(status="in-progress") — graph is the authority
# Step 1: for each plan, query_notes for continuation context
# Step 2: read plan file from graph's path field
# Step 3: present context to scientist
# ────────────────────────────────────────────────────────


class TestResumeActWorkflow:
    """Simulate /wh:resume: graph-first context restoration."""

    @pytest.mark.asyncio
    async def test_resume_restores_context_from_graph_alone(self, e2e_config):
        """
        /wh:resume can reconstruct full session context from graph
        without reading STATE.md or .continue-here.md.
        """
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        cleanup = []

        # Setup: create the state that /wh:pause would have left
        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Resume context restoration", "status": "in-progress"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        cleanup.append(plan_id)
        await _tag(driver, db, plan_id)

        note = json.loads(await execute_tool(
            "add_note",
            {"title": "Session continuation",
             "content": "Was fitting SRM model to midget data. "
                        "Parasol done, midget in progress. "
                        "Next step: compare tau_rise across types.",
             "context": f"session-continuation:{plan_id}"},
            e2e_config,
        ))
        note_id = note["node_id"]
        cleanup.append(note_id)
        await _tag(driver, db, note_id)

        await execute_tool("link_nodes", {
            "source_id": note_id, "target_id": plan_id,
            "relationship": "AROSE_FROM",
        }, e2e_config)

        # --- /wh:resume Step 0: query graph for in-progress plans ---
        active = json.loads(await execute_tool(
            "query_plans", {"status": "in-progress"}, e2e_config,
        ))
        found_plans = [p for p in active["plans"] if p["id"] == plan_id]
        assert len(found_plans) == 1
        assert found_plans[0]["title"] == "E2E: Resume context restoration"

        # --- Step 1: query notes for continuation ---
        # Search by content since query_notes searches title+content
        notes = json.loads(await execute_tool(
            "query_notes", {"keyword": "fitting SRM model"}, e2e_config,
        ))
        found_notes = [n for n in notes["notes"] if n["id"] == note_id]
        assert len(found_notes) == 1
        assert "midget in progress" in found_notes[0]["content"]
        assert found_notes[0]["context"] == f"session-continuation:{plan_id}"

        # --- The resume act now has everything it needs ---
        # Plan title, status, and path from query_plans
        # Continuation context from query_notes
        # No filesystem read was needed

        # Cleanup
        for nid in cleanup:
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)


# ────────────────────────────────────────────────────────
# /wh:handoff workflow
#
# Step 1: query_plans(status="approved") to find plan
# Step 2: propose tasks from plan
# Step 3: update_node(PL-xxxx, status="in-progress")
# Step 4: add_execution(kind="handoff", status="running") per wave
# Step 5: link_nodes(execution, plan, "WAS_INFORMED_BY")
# ────────────────────────────────────────────────────────


class TestHandoffActWorkflow:
    """Simulate /wh:handoff: graph-first plan lookup, execution provenance."""

    @pytest.mark.asyncio
    async def test_handoff_creates_running_executions(self, e2e_config):
        """Full /wh:handoff flow: find plan, start execution, link provenance."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        cleanup = []

        # Setup: approved plan
        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Handoff act population analysis", "status": "approved"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        cleanup.append(plan_id)
        await _tag(driver, db, plan_id)

        # --- Step 1: find approved plan ---
        approved = json.loads(await execute_tool(
            "query_plans", {"status": "approved"}, e2e_config,
        ))
        assert plan_id in [p["id"] for p in approved["plans"]]

        # --- Step 3: transition to in-progress ---
        await execute_tool(
            "update_node", {"node_id": plan_id, "status": "in-progress"}, e2e_config,
        )

        # --- Step 4: create handoff executions per wave ---
        wave1 = json.loads(await execute_tool(
            "add_execution",
            {"kind": "handoff",
             "description": "Wave 1: literature search + data loading",
             "status": "running"},
            e2e_config,
        ))
        wave1_id = wave1["node_id"]
        cleanup.append(wave1_id)
        await _tag(driver, db, wave1_id)

        wave2 = json.loads(await execute_tool(
            "add_execution",
            {"kind": "handoff",
             "description": "Wave 2: SRM fitting (depends on wave 1)",
             "status": "running"},
            e2e_config,
        ))
        wave2_id = wave2["node_id"]
        cleanup.append(wave2_id)
        await _tag(driver, db, wave2_id)

        # --- Step 5: link executions to plan ---
        for exec_id in (wave1_id, wave2_id):
            await execute_tool("link_nodes", {
                "source_id": exec_id, "target_id": plan_id,
                "relationship": "WAS_INFORMED_BY",
            }, e2e_config)

        # --- Verify graph state ---
        # Both executions are running
        for exec_id in (wave1_id, wave2_id):
            s = await _get_prop(driver, db, exec_id, "status")
            assert s == "running"
            assert await _count_rels(driver, db, exec_id, "WAS_INFORMED_BY", plan_id) == 1

        # Plan is in-progress
        assert await _get_prop(driver, db, plan_id, "status") == "in-progress"

        # query_executions finds the handoffs
        execs = json.loads(await execute_tool(
            "query_executions", {"kind": "handoff"}, e2e_config,
        ))
        exec_ids = [x["id"] for x in execs["executions"]]
        assert wave1_id in exec_ids
        assert wave2_id in exec_ids

        # --- Simulate wave 1 completion ---
        await execute_tool(
            "update_node", {"node_id": wave1_id, "status": "completed"}, e2e_config,
        )
        assert await _get_prop(driver, db, wave1_id, "status") == "completed"
        assert await _get_prop(driver, db, wave2_id, "status") == "running"

        # Cleanup
        for nid in cleanup:
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)


# ────────────────────────────────────────────────────────
# /wh:status workflow
#
# Step 0b: query_plans() — all statuses, group by status
# Step 1: present grouped plan list
# If graph and STATE.md disagree, graph wins
# ────────────────────────────────────────────────────────


class TestStatusActWorkflow:
    """Simulate /wh:status: graph-first plan overview."""

    @pytest.mark.asyncio
    async def test_status_groups_plans_by_status(self, e2e_config):
        """query_plans() returns all plans, groupable by status."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        cleanup = []

        # Create plans in different statuses
        for title, status in [
            ("E2E status: active investigation", "in-progress"),
            ("E2E status: queued investigation", "approved"),
            ("E2E status: brainstorm", "draft"),
            ("E2E status: done investigation", "completed"),
        ]:
            result = json.loads(await execute_tool(
                "add_plan", {"title": title, "status": status}, e2e_config,
            ))
            cleanup.append(result["node_id"])
            await _tag(driver, db, result["node_id"])

        # --- /wh:status Step 0b: query all plans ---
        all_plans = json.loads(await execute_tool(
            "query_plans", {}, e2e_config,
        ))

        # Group by status (what the act does)
        by_status: dict[str, list] = {}
        for p in all_plans["plans"]:
            by_status.setdefault(p["status"], []).append(p)

        # We should find at least one of each status we created
        our_ids = set(cleanup)
        for expected_status in ("in-progress", "approved", "draft", "completed"):
            plans_in_status = by_status.get(expected_status, [])
            our_plans = [p for p in plans_in_status if p["id"] in our_ids]
            assert len(our_plans) >= 1, (
                f"Should find at least one {expected_status} plan from graph"
            )

        # Cleanup
        for nid in cleanup:
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)


# ────────────────────────────────────────────────────────
# /wh:reconvene workflow
#
# Step 0: query_plans(status="in-progress") — graph first
# Step 1: check team tasks
# Step 2: query graph for recent findings/hypotheses
# ────────────────────────────────────────────────────────


class TestReconveneActWorkflow:
    """Simulate /wh:reconvene: graph-first plan + findings discovery."""

    @pytest.mark.asyncio
    async def test_reconvene_finds_plan_and_new_findings(self, e2e_config):
        """Reconvene discovers the active plan and findings produced during handoff."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        cleanup = []

        # Setup: in-progress plan with findings from a handoff
        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Reconvene population comparison", "status": "in-progress"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        cleanup.append(plan_id)
        await _tag(driver, db, plan_id)

        # Agent produced findings during handoff
        f1 = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E reconvene: parasol tau_decay = 0.48ms",
             "confidence": 0.9},
            e2e_config,
        ))
        cleanup.append(f1["node_id"])
        await _tag(driver, db, f1["node_id"])

        f2 = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E reconvene: midget tau_decay = 0.45ms",
             "confidence": 0.88},
            e2e_config,
        ))
        cleanup.append(f2["node_id"])
        await _tag(driver, db, f2["node_id"])

        # --- /wh:reconvene Step 0: find active plan ---
        active = json.loads(await execute_tool(
            "query_plans", {"status": "in-progress"}, e2e_config,
        ))
        found = [p for p in active["plans"] if p["id"] == plan_id]
        assert len(found) == 1

        # --- Step 2: query recent findings ---
        findings = json.loads(await execute_tool(
            "query_findings", {"keyword": "E2E reconvene"}, e2e_config,
        ))
        finding_ids = [f["id"] for f in findings["findings"]]
        assert f1["node_id"] in finding_ids
        assert f2["node_id"] in finding_ids

        # Cleanup
        for nid in cleanup:
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)
