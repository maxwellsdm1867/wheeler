"""E2E tests for v0.7.0 graph-as-source-of-truth plan lifecycle.

Tests the full plan lifecycle against a live Neo4j instance:
  - Plan creation via add_plan and ensure_artifact
  - query_plans with keyword/status filters
  - Status transitions: draft -> approved -> in-progress -> completed
  - Plan + Execution provenance linking
  - Session continuation notes linked to plans
  - Process provenance (pause/handoff Execution nodes)
  - Knowledge file + synthesis triple-write for plans

Run: python -m pytest tests/e2e/test_plan_lifecycle.py -v
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
    """Tag a node for cleanup after test."""
    async with driver.session(database=db) as session:
        await session.run(
            "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
            id=node_id, tag=E2E_TAG,
        )


async def _get_prop(driver, db, label, node_id, prop):
    """Read a single property from a node."""
    async with driver.session(database=db) as session:
        result = await session.run(
            f"MATCH (n:{label} {{id: $id}}) RETURN n.{prop} AS val",
            id=node_id,
        )
        rec = await result.single()
        return rec["val"] if rec else None


async def _rel_exists(driver, db, src_id, rel_type, tgt_id):
    """Check if a relationship exists between two nodes."""
    async with driver.session(database=db) as session:
        result = await session.run(
            "MATCH (a {id: $src})-[r]->(b {id: $tgt}) "
            "WHERE type(r) = $rel RETURN count(r) AS c",
            src=src_id, tgt=tgt_id, rel=rel_type,
        )
        rec = await result.single()
        return rec["c"] > 0


# ────────────────────────────────────────────────────────
# 1. Plan creation and query_plans
# ────────────────────────────────────────────────────────


class TestPlanCreation:
    """Create plans via add_plan and verify they're queryable."""

    @pytest.mark.asyncio
    async def test_add_plan_creates_node(self, e2e_config):
        """add_plan creates a Plan node with correct label and prefix."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        result = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Calcium oscillation frequency scaling",
             "status": "draft"},
            e2e_config,
        ))
        assert result["label"] == "Plan"
        assert result["node_id"].startswith("PL-")

        driver = get_async_driver(e2e_config)
        await _tag(driver, e2e_config.neo4j.database, result["node_id"])

        # Verify status in graph
        status = await _get_prop(
            driver, e2e_config.neo4j.database,
            "Plan", result["node_id"], "status",
        )
        assert status == "draft"

    @pytest.mark.asyncio
    async def test_add_plan_with_all_statuses(self, e2e_config):
        """All four lifecycle statuses are accepted by add_plan."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        for status in ("draft", "approved", "in-progress", "completed"):
            result = json.loads(await execute_tool(
                "add_plan",
                {"title": f"E2E: Status test ({status})", "status": status},
                e2e_config,
            ))
            assert "error" not in result, f"Status '{status}' should be valid"
            assert result["label"] == "Plan"
            await _tag(driver, e2e_config.neo4j.database, result["node_id"])

            actual = await _get_prop(
                driver, e2e_config.neo4j.database,
                "Plan", result["node_id"], "status",
            )
            assert actual == status

    @pytest.mark.asyncio
    async def test_add_plan_rejects_invalid_status(self, e2e_config):
        """Old 'final' status and arbitrary strings are rejected."""
        from wheeler.tools.graph_tools import execute_tool

        result = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Bad status", "status": "final"},
            e2e_config,
        ))
        assert "error" in result
        assert result["error"] == "validation_failed"

        result2 = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Bad status 2", "status": "bogus"},
            e2e_config,
        ))
        assert "error" in result2


# ────────────────────────────────────────────────────────
# 2. query_plans: filtering by keyword and status
# ────────────────────────────────────────────────────────


class TestQueryPlans:
    """query_plans returns correct results filtered by keyword and status."""

    @pytest.mark.asyncio
    async def test_query_plans_returns_created_plan(self, e2e_config):
        """A plan created via add_plan is immediately queryable."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        created = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Spike timing precision", "status": "approved"},
            e2e_config,
        ))
        plan_id = created["node_id"]
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Query by keyword
        result = json.loads(await execute_tool(
            "query_plans",
            {"keyword": "Spike timing precision"},
            e2e_config,
        ))
        assert result["count"] >= 1
        ids = [p["id"] for p in result["plans"]]
        assert plan_id in ids

    @pytest.mark.asyncio
    async def test_query_plans_filter_by_status(self, e2e_config):
        """Status filter returns only matching plans."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        # Create one approved, one draft
        approved = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Approved plan for filter test", "status": "approved"},
            e2e_config,
        ))
        draft = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Draft plan for filter test", "status": "draft"},
            e2e_config,
        ))
        await _tag(driver, e2e_config.neo4j.database, approved["node_id"])
        await _tag(driver, e2e_config.neo4j.database, draft["node_id"])

        # Query approved only
        result = json.loads(await execute_tool(
            "query_plans", {"status": "approved"}, e2e_config,
        ))
        returned_ids = [p["id"] for p in result["plans"]]
        assert approved["node_id"] in returned_ids
        # Draft should not appear in approved filter
        assert draft["node_id"] not in returned_ids

    @pytest.mark.asyncio
    async def test_query_plans_keyword_and_status(self, e2e_config):
        """Combined keyword + status filter works."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Retinal ganglion cell classification",
             "status": "in-progress"},
            e2e_config,
        ))
        await _tag(driver, e2e_config.neo4j.database, plan["node_id"])

        # Match both keyword and status
        result = json.loads(await execute_tool(
            "query_plans",
            {"keyword": "ganglion", "status": "in-progress"},
            e2e_config,
        ))
        assert result["count"] >= 1
        ids = [p["id"] for p in result["plans"]]
        assert plan["node_id"] in ids

        # Same keyword, wrong status: should not match
        result2 = json.loads(await execute_tool(
            "query_plans",
            {"keyword": "ganglion", "status": "completed"},
            e2e_config,
        ))
        ids2 = [p["id"] for p in result2["plans"]]
        assert plan["node_id"] not in ids2

    @pytest.mark.asyncio
    async def test_query_plans_empty_graph(self, e2e_config):
        """query_plans on a topic with no matches returns empty list."""
        from wheeler.tools.graph_tools import execute_tool

        result = json.loads(await execute_tool(
            "query_plans",
            {"keyword": "zzz_nonexistent_topic_zzz"},
            e2e_config,
        ))
        assert result["count"] == 0
        assert result["plans"] == []

    @pytest.mark.asyncio
    async def test_query_plans_returns_expected_fields(self, e2e_config):
        """Each plan record has id, title, status, path, hash, date, updated, tier."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        created = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Field check plan", "status": "draft"},
            e2e_config,
        ))
        await _tag(driver, e2e_config.neo4j.database, created["node_id"])

        result = json.loads(await execute_tool(
            "query_plans",
            {"keyword": "Field check plan"},
            e2e_config,
        ))
        assert result["count"] >= 1
        plan = next(p for p in result["plans"] if p["id"] == created["node_id"])

        # All expected fields present
        for field in ("id", "title", "status", "date", "updated", "tier"):
            assert field in plan, f"Missing field: {field}"
        assert plan["status"] == "draft"
        assert plan["tier"] == "generated"


# ────────────────────────────────────────────────────────
# 3. Status transitions via update_node
# ────────────────────────────────────────────────────────


class TestPlanStatusTransitions:
    """Full lifecycle: draft -> approved -> in-progress -> completed."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, e2e_config):
        """Walk a plan through all four statuses and verify each transition."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        # Create as draft
        created = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Full lifecycle test", "status": "draft"},
            e2e_config,
        ))
        plan_id = created["node_id"]
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Draft -> Approved
        result = json.loads(await execute_tool(
            "update_node",
            {"node_id": plan_id, "status": "approved"},
            e2e_config,
        ))
        assert "error" not in result
        assert result["changes"]["status"]["old"] == "draft"
        assert result["changes"]["status"]["new"] == "approved"

        status = await _get_prop(
            driver, e2e_config.neo4j.database, "Plan", plan_id, "status",
        )
        assert status == "approved"

        # Approved -> In-progress
        result = json.loads(await execute_tool(
            "update_node",
            {"node_id": plan_id, "status": "in-progress"},
            e2e_config,
        ))
        assert result["changes"]["status"]["new"] == "in-progress"

        # In-progress -> Completed
        result = json.loads(await execute_tool(
            "update_node",
            {"node_id": plan_id, "status": "completed"},
            e2e_config,
        ))
        assert result["changes"]["status"]["new"] == "completed"

        # Verify final state via query
        query_result = json.loads(await execute_tool(
            "query_plans", {"status": "completed"}, e2e_config,
        ))
        ids = [p["id"] for p in query_result["plans"]]
        assert plan_id in ids

    @pytest.mark.asyncio
    async def test_status_change_updates_timestamp(self, e2e_config):
        """update_node on status also bumps the 'updated' timestamp."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        created = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Timestamp test", "status": "draft"},
            e2e_config,
        ))
        plan_id = created["node_id"]
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        updated_before = await _get_prop(
            driver, e2e_config.neo4j.database, "Plan", plan_id, "updated",
        )

        # Transition
        await execute_tool(
            "update_node",
            {"node_id": plan_id, "status": "approved"},
            e2e_config,
        )

        updated_after = await _get_prop(
            driver, e2e_config.neo4j.database, "Plan", plan_id, "updated",
        )
        assert updated_after is not None
        assert updated_after >= updated_before


# ────────────────────────────────────────────────────────
# 4. ensure_artifact for plans (idempotent registration)
# ────────────────────────────────────────────────────────


class TestEnsureArtifactPlan:
    """ensure_artifact with artifact_type=plan creates/updates Plan nodes."""

    @pytest.mark.asyncio
    async def test_ensure_artifact_creates_plan(self, sandbox, e2e_config):
        """ensure_artifact on a .md file with artifact_type=plan creates a Plan node."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        # Write a plan file
        plan_file = sandbox / ".plans" / "e2e-calcium-osc.md"
        plan_file.write_text(
            "---\n"
            "investigation: calcium-oscillation\n"
            "status: draft\n"
            "---\n"
            "# Investigation: Calcium oscillation frequency\n"
            "## Objective\n"
            "Test calcium oscillation frequency scaling.\n"
        )

        result = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: Calcium oscillation frequency",
             "status": "draft"},
            e2e_config,
        ))
        assert result["label"] == "Plan"
        assert result["action"] == "created"
        plan_id = result["node_id"]
        assert plan_id.startswith("PL-")

        driver = get_async_driver(e2e_config)
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Verify queryable
        query = json.loads(await execute_tool(
            "query_plans", {"keyword": "Calcium oscillation"}, e2e_config,
        ))
        assert any(p["id"] == plan_id for p in query["plans"])

    @pytest.mark.asyncio
    async def test_ensure_artifact_idempotent(self, sandbox, e2e_config):
        """Calling ensure_artifact twice on the same file returns 'unchanged'."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        plan_file = sandbox / ".plans" / "e2e-idempotent.md"
        plan_file.write_text(
            "---\ninvestigation: idempotent-test\nstatus: draft\n---\n"
            "# Idempotent test plan\n"
        )

        first = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: Idempotent plan"},
            e2e_config,
        ))
        assert first["action"] == "created"
        plan_id = first["node_id"]

        driver = get_async_driver(e2e_config)
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Same call again
        second = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: Idempotent plan"},
            e2e_config,
        ))
        assert second["action"] == "unchanged"
        assert second["node_id"] == plan_id

    @pytest.mark.asyncio
    async def test_ensure_artifact_detects_change(self, sandbox, e2e_config):
        """Changing the file content triggers 'updated' action."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        plan_file = sandbox / ".plans" / "e2e-change-detect.md"
        plan_file.write_text("# Version 1\nOriginal content.\n")

        first = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: Change detection"},
            e2e_config,
        ))
        plan_id = first["node_id"]

        driver = get_async_driver(e2e_config)
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Modify the file
        plan_file.write_text("# Version 2\nUpdated content with new tasks.\n")

        second = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: Change detection"},
            e2e_config,
        ))
        assert second["action"] == "updated"
        assert second["node_id"] == plan_id


# ────────────────────────────────────────────────────────
# 5. Process provenance: Execution nodes for pause/handoff
# ────────────────────────────────────────────────────────


class TestProcessProvenance:
    """Execution nodes for pause and handoff events linked to plans."""

    @pytest.mark.asyncio
    async def test_pause_execution_linked_to_plan(self, e2e_config):
        """A pause Execution node links to the active plan via WAS_INFORMED_BY."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        # Create a plan
        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Plan for pause test", "status": "in-progress"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Create a pause Execution
        pause = json.loads(await execute_tool(
            "add_execution",
            {"kind": "pause",
             "description": "Pausing calcium oscillation investigation, pending data"},
            e2e_config,
        ))
        pause_id = pause["node_id"]
        assert pause_id.startswith("X-")
        await _tag(driver, e2e_config.neo4j.database, pause_id)

        # Link: pause WAS_INFORMED_BY plan
        link = json.loads(await execute_tool(
            "link_nodes",
            {"source_id": pause_id, "target_id": plan_id,
             "relationship": "WAS_INFORMED_BY"},
            e2e_config,
        ))
        assert link["status"] == "linked"

        # Verify the relationship exists in the graph
        assert await _rel_exists(
            driver, e2e_config.neo4j.database,
            pause_id, "WAS_INFORMED_BY", plan_id,
        )

    @pytest.mark.asyncio
    async def test_handoff_execution_linked_to_plan(self, e2e_config):
        """A handoff Execution node links to the plan and tracks running status."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        # Create plan
        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Plan for handoff test", "status": "approved"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Create handoff Execution with status=running
        handoff = json.loads(await execute_tool(
            "add_execution",
            {"kind": "handoff",
             "description": "Wave 1: literature search + data loading",
             "status": "running"},
            e2e_config,
        ))
        handoff_id = handoff["node_id"]
        await _tag(driver, e2e_config.neo4j.database, handoff_id)

        # Link to plan
        json.loads(await execute_tool(
            "link_nodes",
            {"source_id": handoff_id, "target_id": plan_id,
             "relationship": "WAS_INFORMED_BY"},
            e2e_config,
        ))

        # Verify status is running
        status = await _get_prop(
            driver, e2e_config.neo4j.database,
            "Execution", handoff_id, "status",
        )
        assert status == "running"

        # Complete the handoff
        result = json.loads(await execute_tool(
            "update_node",
            {"node_id": handoff_id, "status": "completed"},
            e2e_config,
        ))
        assert result["changes"]["status"]["new"] == "completed"


# ────────────────────────────────────────────────────────
# 6. Session continuation notes linked to plans
# ────────────────────────────────────────────────────────


class TestSessionContinuation:
    """ResearchNote with session-continuation context linked to active plan."""

    @pytest.mark.asyncio
    async def test_continuation_note_linked_to_plan(self, e2e_config):
        """/wh:pause pattern: note with context='session-continuation:PL-xxxx' + AROSE_FROM link."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        # Create plan
        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Plan for continuation test", "status": "in-progress"},
            e2e_config,
        ))
        plan_id = plan["node_id"]
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Create continuation note
        note = json.loads(await execute_tool(
            "add_note",
            {"title": "Session continuation",
             "content": "Working on task 2 (literature search). Task 1 complete. "
                        "Next: compare SRM fit parameters across cell types.",
             "context": f"session-continuation:{plan_id}"},
            e2e_config,
        ))
        note_id = note["node_id"]
        assert note_id.startswith("N-")
        await _tag(driver, e2e_config.neo4j.database, note_id)

        # Link note AROSE_FROM plan
        link = json.loads(await execute_tool(
            "link_nodes",
            {"source_id": note_id, "target_id": plan_id,
             "relationship": "AROSE_FROM"},
            e2e_config,
        ))
        assert link["status"] == "linked"

        # Verify the note is queryable by content keyword
        query = json.loads(await execute_tool(
            "query_notes",
            {"keyword": "compare SRM fit parameters"},
            e2e_config,
        ))
        found = [n for n in query["notes"] if n["id"] == note_id]
        assert len(found) == 1
        # The context field should be preserved
        assert found[0]["context"] == f"session-continuation:{plan_id}"

        # Verify AROSE_FROM relationship
        assert await _rel_exists(
            driver, e2e_config.neo4j.database,
            note_id, "AROSE_FROM", plan_id,
        )


# ────────────────────────────────────────────────────────
# 7. Triple-write: knowledge JSON + synthesis MD
# ────────────────────────────────────────────────────────


class TestPlanTripleWrite:
    """Plan creation triggers knowledge file and synthesis file writes."""

    @pytest.mark.asyncio
    async def test_knowledge_file_created(self, e2e_config):
        """add_plan creates a knowledge/{PL-xxxx}.json file."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        result = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Triple-write knowledge test", "status": "draft"},
            e2e_config,
        ))
        plan_id = result["node_id"]

        driver = get_async_driver(e2e_config)
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Check knowledge file
        knowledge_path = Path(e2e_config.knowledge_path) / f"{plan_id}.json"
        assert knowledge_path.exists(), f"Knowledge file missing: {knowledge_path}"

        # Verify content
        data = json.loads(knowledge_path.read_text())
        assert data["id"] == plan_id
        assert data["title"] == "E2E: Triple-write knowledge test"
        assert data["status"] == "draft"
        assert data["type"] == "Plan"

        # Cleanup file
        knowledge_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_synthesis_file_created(self, e2e_config):
        """add_plan creates a synthesis/{PL-xxxx}.md file."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        result = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Triple-write synthesis test", "status": "approved"},
            e2e_config,
        ))
        plan_id = result["node_id"]

        driver = get_async_driver(e2e_config)
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        # Check synthesis file
        synthesis_path = Path(e2e_config.synthesis_path) / f"{plan_id}.md"
        assert synthesis_path.exists(), f"Synthesis file missing: {synthesis_path}"

        content = synthesis_path.read_text()
        assert plan_id in content
        assert "Triple-write synthesis test" in content

        # Cleanup file
        synthesis_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_update_node_updates_knowledge_file(self, e2e_config):
        """Status transition via update_node updates the knowledge JSON."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        result = json.loads(await execute_tool(
            "add_plan",
            {"title": "E2E: Knowledge update test", "status": "draft"},
            e2e_config,
        ))
        plan_id = result["node_id"]

        driver = get_async_driver(e2e_config)
        await _tag(driver, e2e_config.neo4j.database, plan_id)

        knowledge_path = Path(e2e_config.knowledge_path) / f"{plan_id}.json"

        # Transition to approved
        await execute_tool(
            "update_node",
            {"node_id": plan_id, "status": "approved"},
            e2e_config,
        )

        # Knowledge file should reflect new status
        data = json.loads(knowledge_path.read_text())
        assert data["status"] == "approved"

        # change_log should record the transition
        assert len(data["change_log"]) >= 2  # created + fields_updated
        last_change = data["change_log"][-1]
        assert last_change["action"] == "fields_updated"
        assert "status" in last_change.get("changes", {})

        # Cleanup
        knowledge_path.unlink(missing_ok=True)
        synthesis_path = Path(e2e_config.synthesis_path) / f"{plan_id}.md"
        synthesis_path.unlink(missing_ok=True)


# ────────────────────────────────────────────────────────
# 8. Full scenario: plan -> execute -> pause -> resume
# ────────────────────────────────────────────────────────


class TestFullPlanScenario:
    """End-to-end scenario: create plan, approve, execute, pause, verify graph state."""

    @pytest.mark.asyncio
    async def test_plan_execute_pause_resume_cycle(self, sandbox, e2e_config):
        """Simulate a full research session with graph-first plan management."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        created_ids = []

        # 1. Create plan file + register via ensure_artifact
        plan_file = sandbox / ".plans" / "e2e-full-scenario.md"
        plan_file.write_text(
            "---\ninvestigation: full-scenario\nstatus: draft\n---\n"
            "# Full Scenario Test\n## Objective\nTest the full lifecycle.\n"
        )

        plan_result = json.loads(await execute_tool(
            "ensure_artifact",
            {"path": str(plan_file), "artifact_type": "plan",
             "title": "E2E: Full scenario test", "status": "draft"},
            e2e_config,
        ))
        plan_id = plan_result["node_id"]
        created_ids.append(plan_id)
        await _tag(driver, db, plan_id)

        # 2. Scientist approves
        await execute_tool(
            "update_node",
            {"node_id": plan_id, "status": "approved"},
            e2e_config,
        )

        # Verify via query_plans
        approved = json.loads(await execute_tool(
            "query_plans", {"status": "approved"}, e2e_config,
        ))
        assert any(p["id"] == plan_id for p in approved["plans"])

        # 3. Start execution
        await execute_tool(
            "update_node",
            {"node_id": plan_id, "status": "in-progress"},
            e2e_config,
        )

        # 4. Execution produces a finding
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E: Parasol ON tau_rise = 0.12ms",
             "confidence": 0.85},
            e2e_config,
        ))
        finding_id = finding["node_id"]
        created_ids.append(finding_id)
        await _tag(driver, db, finding_id)

        # Create execution node for provenance
        execution = json.loads(await execute_tool(
            "add_execution",
            {"kind": "script_run",
             "description": "E2E: SRM fit on parasol data"},
            e2e_config,
        ))
        exec_id = execution["node_id"]
        created_ids.append(exec_id)
        await _tag(driver, db, exec_id)

        # Link: finding WAS_GENERATED_BY execution
        await execute_tool(
            "link_nodes",
            {"source_id": finding_id, "target_id": exec_id,
             "relationship": "WAS_GENERATED_BY"},
            e2e_config,
        )

        # 5. Pause the session (process provenance)
        pause_exec = json.loads(await execute_tool(
            "add_execution",
            {"kind": "pause",
             "description": "Pausing: completed task 1, pending task 2 (midget data)"},
            e2e_config,
        ))
        pause_id = pause_exec["node_id"]
        created_ids.append(pause_id)
        await _tag(driver, db, pause_id)

        await execute_tool(
            "link_nodes",
            {"source_id": pause_id, "target_id": plan_id,
             "relationship": "WAS_INFORMED_BY"},
            e2e_config,
        )

        # Write continuation note
        note = json.loads(await execute_tool(
            "add_note",
            {"title": "Session continuation",
             "content": "Task 1 done (parasol fit). Task 2 pending (midget fit).",
             "context": f"session-continuation:{plan_id}"},
            e2e_config,
        ))
        note_id = note["node_id"]
        created_ids.append(note_id)
        await _tag(driver, db, note_id)

        await execute_tool(
            "link_nodes",
            {"source_id": note_id, "target_id": plan_id,
             "relationship": "AROSE_FROM"},
            e2e_config,
        )

        # 6. Verify the full graph state
        # Plan is still in-progress
        status = await _get_prop(driver, db, "Plan", plan_id, "status")
        assert status == "in-progress"

        # Pause execution linked to plan
        assert await _rel_exists(driver, db, pause_id, "WAS_INFORMED_BY", plan_id)

        # Finding has provenance chain
        assert await _rel_exists(driver, db, finding_id, "WAS_GENERATED_BY", exec_id)

        # Continuation note linked to plan
        assert await _rel_exists(driver, db, note_id, "AROSE_FROM", plan_id)

        # 7. Simulate resume: query_plans finds the in-progress plan
        in_progress = json.loads(await execute_tool(
            "query_plans", {"status": "in-progress"}, e2e_config,
        ))
        assert any(p["id"] == plan_id for p in in_progress["plans"])

        # query_notes finds the continuation (search by content text)
        notes = json.loads(await execute_tool(
            "query_notes",
            {"keyword": "parasol fit"},
            e2e_config,
        ))
        assert any(n["id"] == note_id for n in notes["notes"])

        # Cleanup plan file
        plan_file.unlink(missing_ok=True)

        # Cleanup knowledge + synthesis files
        for nid in created_ids:
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)
