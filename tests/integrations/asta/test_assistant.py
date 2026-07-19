"""Tests for the Asta Research Assistant adapter (directory deliverable).

UNLIKE the other Asta adapters (one CLI call, one file artifact), the deliverable
is a mission DIRECTORY (project.md + work/<slug>/README.md + work/<slug>/data/),
so the parser walks a tree and the ingest harvests it. Two layers, NEITHER making
a live assistant call:

  1. parse_assistant: build a fake mission tree on disk and assert the walk
     (mission identity, completed work items, verdicts, data files), plus
     defensive cases (a missing project.md yields ``(None, RunMeta())``; a work
     README with no Results is skipped; a bad path never raises).
  2. live-Neo4j e2e: harvest a fake mission with a RUN-UNIQUE mission slug (so its
     work_key dedupe keys can never collide with or delete a production Finding),
     assert BOTH provenance sides (Execution -[USED]-> the seed input, and each
     produced Finding / Dataset / Script / Document -[WAS_GENERATED_BY]-> the run),
     then re-harvest and assert idempotency. Skipped when Neo4j is not reachable.

Run: python -m pytest tests/integrations/asta/test_assistant.py -q
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from wheeler.integrations.asta.assistant import (
    ProjectRecord,
    RunMeta,
    WorkItem,
    parse_assistant,
)

SERVICE_TAG = "asta:assistant"


# ---------------------------------------------------------------------------
# Fixture builder: a fake mission tree on disk
# ---------------------------------------------------------------------------


def _build_mission(root: Path, slug: str) -> Path:
    """Create a mission directory tree under ``root/<slug>`` and return it.

    Two completed work items (one with data artifacts, one without) plus one
    not-yet-executed item (empty Results) that the parser must skip.
    """
    mission = root / slug
    (mission / "work").mkdir(parents=True, exist_ok=True)

    (mission / "project.md").write_text(
        "# Goal\n"
        "Investigate the E2E widget response under load.\n\n"
        "# Background\n"
        "Prior work established a baseline; the dataset holds the recordings.\n\n"
        "# Completed Work\n"
        "- [analyze-widget](work/analyze-widget/README.md) - analyze the widget\n"
        "- [summarize](work/summarize/README.md) - summarize\n\n"
        "# Pending Work\n"
        "- [pending-task](work/pending-task/README.md) (status: pending-plan) - later\n"
    )

    # 1. A completed item WITH data artifacts (a Dataset + a Script).
    aw = mission / "work" / "analyze-widget"
    (aw / "data").mkdir(parents=True, exist_ok=True)
    (aw / "README.md").write_text(
        "---\n"
        "slug: analyze-widget\n"
        "status: done\n"
        "---\n\n"
        "# Goal\n"
        "Analyze the widget response under load.\n\n"
        "# Instructions\n"
        "1. Compute the response curve.\n\n"
        "# Results\n"
        "## Summary\n"
        "The widget response scales linearly with load.\n\n"
        "## Artifacts\n"
        "- data/widget.csv\n\n"
        "# Assessment\n"
        "## Verdict\n"
        "accomplished\n\n"
        "## Reasoning\n"
        "The data supports linear scaling.\n"
    )
    (aw / "data" / "widget.csv").write_text("load,response\n1,1.0\n2,2.0\n")
    (aw / "data" / "compute.py").write_text("print('compute the response curve')\n")

    # 2. A completed item WITHOUT data artifacts, verdict partial.
    sm = mission / "work" / "summarize"
    sm.mkdir(parents=True, exist_ok=True)
    (sm / "README.md").write_text(
        "---\n"
        "slug: summarize\n"
        "status: done\n"
        "---\n\n"
        "# Goal\n"
        "Summarize the widget analysis.\n\n"
        "# Results\n"
        "A partial summary was produced; some load regimes were not covered.\n\n"
        "# Assessment\n"
        "## Verdict\n"
        "partial\n\n"
        "## Root cause\n"
        "missing data for high load\n"
    )

    # 3. A NOT-yet-executed item (empty Results): the parser must skip it.
    pt = mission / "work" / "pending-task"
    pt.mkdir(parents=True, exist_ok=True)
    (pt / "README.md").write_text(
        "---\n"
        "slug: pending-task\n"
        "status: pending-plan\n"
        "---\n\n"
        "# Goal\n"
        "Do the later thing.\n\n"
        "# Results\n\n"
        "# Assessment\n"
    )
    return mission


# ---------------------------------------------------------------------------
# 1. Parse the mission directory (defensive, never a live call)
# ---------------------------------------------------------------------------


class TestParseAssistant:
    def test_missing_project_md_is_none(self, tmp_path):
        (tmp_path / "empty").mkdir()
        record, run_meta = parse_assistant(tmp_path / "empty")
        assert record is None
        assert isinstance(run_meta, RunMeta)

    def test_nonexistent_path_is_none(self, tmp_path):
        record, _ = parse_assistant(tmp_path / "does-not-exist")
        assert record is None

    def test_walks_completed_work(self, tmp_path):
        mission = _build_mission(tmp_path, "widget-mission")
        record, run_meta = parse_assistant(mission)
        assert isinstance(record, ProjectRecord)
        # The slug is the basename plus a short hash of the resolved absolute path
        # (uniqueness so distinct missions never collide on one Execution).
        assert record.slug.startswith("widget-mission-")
        assert run_meta.run_id == record.slug
        assert "widget response" in record.title.lower()
        assert "baseline" in record.background.lower()
        # Two completed items; the pending one (empty Results) is skipped.
        slugs = {w.slug for w in record.work_items}
        assert slugs == {"analyze-widget", "summarize"}

    def test_verdicts_and_data_files(self, tmp_path):
        mission = _build_mission(tmp_path, "widget-mission")
        record, _ = parse_assistant(mission)
        by_slug = {w.slug: w for w in record.work_items}
        assert by_slug["analyze-widget"].verdict == "accomplished"
        assert by_slug["summarize"].verdict == "partial"
        assert by_slug["summarize"].root_cause.startswith("missing data")
        # analyze-widget carries its two data artifacts; summarize has none.
        aw_data = {Path(p).name for p in by_slug["analyze-widget"].data_files}
        assert aw_data == {"widget.csv", "compute.py"}
        assert by_slug["summarize"].data_files == []

    def test_accepts_project_md_path(self, tmp_path):
        mission = _build_mission(tmp_path, "widget-mission")
        record, _ = parse_assistant(mission / "project.md")
        assert record is not None
        assert record.slug.startswith("widget-mission-")

    def test_two_missions_same_basename_get_distinct_slugs(self, tmp_path):
        # Same directory NAME under different parents must not collide (else they
        # would share one Execution and cross-dedupe each other's Findings).
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        m1 = _build_mission(tmp_path / "a", "analysis")
        m2 = _build_mission(tmp_path / "b", "analysis")
        r1, _ = parse_assistant(m1)
        r2, _ = parse_assistant(m2)
        assert r1.slug != r2.slug
        assert r1.slug.startswith("analysis-") and r2.slug.startswith("analysis-")

    def test_result_summary_prefers_summary_subsection(self, tmp_path):
        mission = _build_mission(tmp_path, "widget-mission")
        record, _ = parse_assistant(mission)
        aw = next(w for w in record.work_items if w.slug == "analyze-widget")
        assert aw.result_summary.startswith("The widget response scales linearly")

    def test_workitem_dataclass_defaults(self):
        item = WorkItem(slug="x")
        assert item.data_files == []
        assert item.verdict == ""


class TestParseRealFormat:
    """Cover the VERBATIM upstream asta-assistant output shape (not the parser-
    convenient headings the happy-path fixtures use), which the adversarial review
    showed the first cut of the parser mishandled."""

    def _mission(self, root: Path, readme: str) -> Path:
        m = root / "mission"
        (m / "work" / "step").mkdir(parents=True, exist_ok=True)
        (m / "project.md").write_text("# Goal\nStudy the thing.\n\n# Background\nctx\n")
        (m / "work" / "step" / "README.md").write_text(readme)
        return m

    def test_partially_accomplished_is_partial_not_accomplished(self, tmp_path):
        # The review-work skill's ## Verdict body is free text; "partially
        # accomplished" must NOT read as the bare "accomplished".
        readme = (
            "---\nslug: step\nstatus: done\n---\n\n# Goal\nG\n\n"
            "# Results\nThe analysis ran.\n\n"
            "# Assessment\n## Verdict\npartially accomplished\n"
        )
        record, _ = parse_assistant(self._mission(tmp_path, readme))
        assert record.work_items[0].verdict == "partial"

    def test_root_cause_with_template_parenthetical_heading(self, tmp_path):
        # review-work writes "## Root cause (if not fully accomplished)" verbatim.
        readme = (
            "---\nslug: step\nstatus: done\n---\n\n# Goal\nG\n\n"
            "# Results\nDid work.\n\n"
            "# Assessment\n## Verdict\npartial\n\n"
            "## Root cause (if not fully accomplished)\nmissing data for high load\n"
        )
        record, _ = parse_assistant(self._mission(tmp_path, readme))
        assert record.work_items[0].root_cause.startswith("missing data")

    def test_closed_atx_results_heading_is_recognized(self, tmp_path):
        # A closed ATX heading (## Results ##) is valid CommonMark; the work item
        # must still be harvested, not silently skipped.
        readme = (
            "---\nslug: step\nstatus: done\n---\n\n# Goal\nG\n\n"
            "# Results ##\nA real result.\n\n# Assessment\n## Verdict\naccomplished\n"
        )
        record, _ = parse_assistant(self._mission(tmp_path, readme))
        assert len(record.work_items) == 1
        assert record.work_items[0].result_summary.startswith("A real result")
        assert record.work_items[0].verdict == "accomplished"

    def test_bom_project_md_parses_goal_and_title(self, tmp_path):
        m = tmp_path / "mission"
        m.mkdir()
        (m / "project.md").write_bytes(
            "﻿# Goal\nCharacterize the widget.\n\n# Background\nx\n".encode("utf-8")
        )
        record, _ = parse_assistant(m)
        assert record is not None
        assert "characterize the widget" in record.title.lower()
        assert record.goal.strip().startswith("Characterize")

    def test_non_utf8_bytes_do_not_raise(self, tmp_path):
        m = tmp_path / "mission"
        (m / "work" / "step").mkdir(parents=True)
        # A stray non-UTF-8 byte (0xff) in project.md must not raise.
        (m / "project.md").write_bytes(b"# Goal\nCaf\xe9 study \xff\n\n# Background\nx\n")
        (m / "work" / "step" / "README.md").write_bytes(
            b"---\nslug: step\nstatus: done\n---\n\n# Goal\nG\n\n# Results\n\xfe done\n"
        )
        record, _ = parse_assistant(m)  # must not raise
        assert record is not None
        assert len(record.work_items) == 1

    def test_unclosed_frontmatter_fence_does_not_corrupt_status(self, tmp_path):
        # An unterminated --- fence must not let a body line overwrite status.
        readme = (
            "---\nslug: step\nstatus: done\n\n# Goal\nG\n\n"
            "# Results\nnote: status is not a real key here\n"
            "status: CORRUPTED\n"
        )
        record, _ = parse_assistant(self._mission(tmp_path, readme))
        item = record.work_items[0]
        # No closing fence -> frontmatter discarded -> slug falls back to dir name,
        # status is empty, NOT the body's "CORRUPTED".
        assert item.status != "CORRUPTED"


# ---------------------------------------------------------------------------
# 2. Live-Neo4j e2e (per-run e2e_tag, run-unique mission slug)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def e2e_config():
    from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig

    return WheelerConfig(
        neo4j=Neo4jConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="research-graph",
            database="neo4j",
        ),
        project=ProjectMeta(name="Integrations-E2E-Test"),
    )


@pytest.fixture(scope="module")
def neo4j_available(e2e_config) -> bool:
    import asyncio

    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _check():
        driver = AsyncGraphDatabase.driver(
            e2e_config.neo4j.uri,
            auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )
        try:
            async with driver.session(database=e2e_config.neo4j.database) as s:
                await s.run("RETURN 1")
            return True
        except Exception:
            return False
        finally:
            await driver.close()

    return asyncio.run(_check())


@pytest.fixture(autouse=True)
def _reset_driver_singleton():
    import wheeler.graph.driver as drv

    drv._async_driver = None
    drv._async_driver_uri = None
    yield
    drv._async_driver = None
    drv._async_driver_uri = None


def _cleanup_assistant(e2e_config, e2e_tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged. EXACTLY the
    e2e_tag delete, never by service (the e2e config runs on the SHARED default
    namespace where production nodes carry the same service tag)."""
    import asyncio

    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _run():
        driver = AsyncGraphDatabase.driver(
            e2e_config.neo4j.uri,
            auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )
        try:
            async with driver.session(database=e2e_config.neo4j.database) as s:
                await s.run(
                    "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n", tag=e2e_tag
                )
        finally:
            await driver.close()

    asyncio.run(_run())


class TestIngestAssistantE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        # Run-unique mission slug from the per-run uuid, so its work_key dedupe
        # keys (mission-slug/work-slug) cannot collide with a production Finding.
        self._slug = f"e2e-mission-{self._e2e_tag.rsplit('_', 1)[-1][:12]}"
        _cleanup_assistant(e2e_config, self._e2e_tag)
        yield
        _cleanup_assistant(e2e_config, self._e2e_tag)

    async def _tag_all(self, e2e_config, report, extra_ids=()):
        """Tag ONLY the nodes THIS run created (scoped off the report ids + the
        WAS_GENERATED_BY fan-in), plus any explicit extras (the seed input). Never
        tag by service, so a production node is never caught."""
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        run_ids = [i for i in (report.execution_id, report.artifact) if i]
        run_ids += [i for i in extra_ids if i]
        async with driver.session(database=db) as s:
            if run_ids:
                await s.run(
                    "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                    ids=run_ids, tag=self._e2e_tag,
                )
            if report.execution_id:
                # Every produced node (Finding, Dataset, Script, the mission
                # Document) carries WAS_GENERATED_BY the run Execution.
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                )

    async def _count(self, e2e_config, query, **params):
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            result = await s.run(query, **params)
            row = await result.single()
            return row[0] if row else 0

    @pytest.mark.asyncio
    async def test_harvest_and_idempotent(self, e2e_config):
        from wheeler.integrations.asta.assistant import ingest_assistant
        from wheeler.tools.graph_tools import execute_tool

        # A mission workspace with two completed work items (one with data).
        import json

        mission_root = self._tmp / ".wheeler" / "asta-assistant"
        mission_root.mkdir(parents=True, exist_ok=True)
        mission = _build_mission(mission_root, self._slug)

        # A seed Question the mission USED (input-side provenance).
        q = json.loads(
            await execute_tool(
                "add_question",
                {"question": "E2E: how does the widget respond under load?", "priority": 5},
                e2e_config,
            )
        )
        question_id = q["node_id"]

        report1 = await ingest_assistant(
            str(mission),
            link_to=question_id,
            config=e2e_config,
            used_inputs=[question_id],
        )
        await self._tag_all(e2e_config, report1, extra_ids=[question_id])

        assert report1.execution_id
        assert not report1.failed
        # The mission Document (project.md) is a W- node.
        assert report1.artifact and report1.artifact.startswith("W-")
        xid = report1.execution_id

        # --- Output side: everything produced WAS_GENERATED_BY the run. ---
        docs = await self._count(
            e2e_config,
            "MATCH (d:Document)-[:WAS_GENERATED_BY]->(x:Execution {id:$xid}) "
            "WHERE d.e2e_tag=$tag RETURN count(d)",
            xid=xid, tag=self._e2e_tag,
        )
        assert docs == 1  # the mission Document
        findings = await self._count(
            e2e_config,
            "MATCH (f:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$xid}) "
            "WHERE f.e2e_tag=$tag RETURN count(f)",
            xid=xid, tag=self._e2e_tag,
        )
        assert findings == 2  # analyze-widget + summarize; pending-task skipped
        datasets = await self._count(
            e2e_config,
            "MATCH (d:Dataset)-[:WAS_GENERATED_BY]->(x:Execution {id:$xid}) "
            "WHERE d.e2e_tag=$tag RETURN count(d)",
            xid=xid, tag=self._e2e_tag,
        )
        assert datasets >= 1  # widget.csv
        scripts = await self._count(
            e2e_config,
            "MATCH (s:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$xid}) "
            "WHERE s.e2e_tag=$tag RETURN count(s)",
            xid=xid, tag=self._e2e_tag,
        )
        assert scripts >= 1  # compute.py

        # The analyze-widget Finding WAS_DERIVED_FROM its data artifacts.
        derived = await self._count(
            e2e_config,
            "MATCH (f:Finding {custom_verdict:'accomplished'})-[:WAS_DERIVED_FROM]->"
            "(d) WHERE f.e2e_tag=$tag AND d.e2e_tag=$tag RETURN count(d)",
            tag=self._e2e_tag,
        )
        assert derived >= 2  # widget.csv + compute.py

        # --- Input side: the run USED the seed Question. ---
        used = await self._count(
            e2e_config,
            "MATCH (x:Execution {id:$xid})-[:USED]->(q {id:$qid}) RETURN count(q)",
            xid=xid, qid=question_id,
        )
        assert used == 1

        # This adapter produces no Paper nodes (the reference-entity rule): the
        # harvest never records a paper, so the report's paper list stays empty.
        assert report1.paper_ids == []

        # --- Re-harvest the SAME mission: idempotent. ---
        report2 = await ingest_assistant(
            str(mission),
            link_to=question_id,
            config=e2e_config,
            used_inputs=[question_id],
        )
        await self._tag_all(e2e_config, report2, extra_ids=[question_id])
        assert report2.created == 0  # nothing new on the second pass

        # No duplicate USED edge, no duplicate Findings.
        used2 = await self._count(
            e2e_config,
            "MATCH (x:Execution {id:$xid})-[r:USED]->(q {id:$qid}) RETURN count(r)",
            xid=xid, qid=question_id,
        )
        assert used2 == 1
        findings2 = await self._count(
            e2e_config,
            "MATCH (f:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$xid}) "
            "WHERE f.e2e_tag=$tag RETURN count(f)",
            xid=xid, tag=self._e2e_tag,
        )
        assert findings2 == 2
