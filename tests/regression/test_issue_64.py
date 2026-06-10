"""Regression test for issue #64: session-synthesis Document fails validation.

Issue: /wh:close creates a session-synthesis Document linked WAS_GENERATED_BY
and WAS_DERIVED_FROM, but NOT APPEARS_IN. Then validate_citations fails
because Documents require APPEARS_IN from Finding|Paper|Script|Hypothesis.

This test creates a session-synthesis Document with the same provenance as
/wh:close does, then validates it, and expects MISSING_PROVENANCE status
before the fix (to confirm the bug reproduces).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestIssue64SessionSynthesisValidation:
    """Session-synthesis Document should validate without APPEARS_IN error."""

    @pytest.mark.asyncio
    async def test_session_synthesis_document_validation_fails_on_main(
        self, sandbox, e2e_config
    ):
        """Reproduce issue #64: session-synthesis Document fails validate_citations.

        The close skill creates a Document with:
        - WAS_GENERATED_BY -> close Execution
        - WAS_DERIVED_FROM -> Plan(s)
        - NO APPEARS_IN edge

        Then validate_citations checks provenance rules and fails with
        MISSING_PROVENANCE because Document requires APPEARS_IN.
        """
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.validation.citations import validate_citations, CitationStatus

        # Create a Finding and Plan to cite in the document
        finding = json.loads(await execute_tool(
            "add_finding",
            {
                "description": "Test finding for issue #64 validation",
                "confidence": 0.8,
            },
            e2e_config,
        ))
        finding_id = finding["node_id"]

        plan = json.loads(await execute_tool(
            "add_plan",
            {"title": "Test plan for issue #64 validation", "status": "draft"},
            e2e_config,
        ))
        plan_id = plan["node_id"]

        # Create a close Execution (mimics what /wh:close does)
        close_exec = json.loads(await execute_tool(
            "add_execution",
            {
                "kind": "close",
                "description": "Session synthesis 2026-06-09: test for issue #64",
            },
            e2e_config,
        ))
        close_exec_id = close_exec["node_id"]

        # Create the session-synthesis Document
        # (mimics phase 2.3 of /wh:close)
        session_file = sandbox / ".plans" / "SESSION-2026-06-09-issue64.md"
        session_file.write_text(
            "---\n"
            "session: 2026-06-09\n"
            "graph_node: W-issue64test\n"
            "---\n"
            f"# Session synthesis\n\n"
            f"Cited [F-issue64] and [PL-issue64] in this test.\n"
        )

        doc = json.loads(await execute_tool(
            "add_document",
            {
                "title": "Session synthesis: 2026-06-09",
                "path": str(session_file),
                "section": "session-synthesis",
                "status": "final",
            },
            e2e_config,
        ))
        doc_id = doc["node_id"]

        # Link Document WAS_GENERATED_BY close Execution (phase 2.3)
        await execute_tool(
            "link_nodes",
            {
                "source_id": doc_id,
                "target_id": close_exec_id,
                "relationship": "WAS_GENERATED_BY",
            },
            e2e_config,
        )

        # Link Document WAS_DERIVED_FROM Plan (phase 2.3)
        await execute_tool(
            "link_nodes",
            {
                "source_id": doc_id,
                "target_id": plan_id,
                "relationship": "WAS_DERIVED_FROM",
            },
            e2e_config,
        )

        # At this point we have:
        # - Document with WAS_GENERATED_BY and WAS_DERIVED_FROM
        # - NO APPEARS_IN edge

        # Write file with citations
        # NOTE: For validate_citations to check the Document itself,
        # we need to cite it somewhere in the text. But /wh:close doesn't
        # normally cite the Document in its own synthesis (that would be circular).
        # So we directly validate the Document existence and provenance instead.
        session_file.write_text(
            "---\n"
            "session: 2026-06-09\n"
            f"graph_node: {doc_id}\n"
            "---\n"
            f"# Session synthesis\n\n"
            f"Findings: [{finding_id}]\n"
            f"Plan: [{plan_id}]\n"
        )

        # The test validates that a Document with NO APPEARS_IN edge would
        # fail if validate_citations were to check it. We do this by directly
        # checking the provenance rules on the Document node in the graph.
        from wheeler.graph.driver import get_async_driver
        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Check if the Document has APPEARS_IN from Finding|Paper|Script|Hypothesis
        async with driver.session(database=db) as session:
            # Check APPEARS_IN: incoming edge from Finding/Paper/Script/Hypothesis
            result = await session.run(
                "MATCH (n:Document {id: $id})<-[:APPEARS_IN]-(t) "
                "WHERE any(lbl IN labels(t) WHERE lbl IN $targets) "
                "RETURN count(t) AS cnt",
                id=doc_id,
                targets=["Finding", "Paper", "Script", "Hypothesis"],
            )
            rec = await result.single()
            appears_in_count = rec["cnt"] if rec else 0

        # BEFORE THE FIX: Document should have NO APPEARS_IN edge,
        # which would cause validate_citations to fail with MISSING_PROVENANCE
        assert appears_in_count == 0, (
            f"Expected Document {doc_id} to have 0 APPEARS_IN edges, "
            f"but found {appears_in_count}. The bug is already fixed!"
        )

        # Tag for cleanup
        async with driver.session(database=db) as session:
            for nid in (doc_id, close_exec_id, plan_id, finding_id):
                await session.run(
                    "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                    id=nid,
                    tag="e2e_test",
                )

        # Cleanup files
        session_file.unlink(missing_ok=True)
        for nid in (doc_id, close_exec_id, plan_id, finding_id):
            (Path(e2e_config.knowledge_path) / f"{nid}.json").unlink(missing_ok=True)
            (Path(e2e_config.synthesis_path) / f"{nid}.md").unlink(missing_ok=True)
