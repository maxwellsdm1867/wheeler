"""Tests for the external-call failsafe (job lifecycle + honest Execution status).

Every external-service call is an Execution that must TRUTHFULLY record whether
the job actually completed. A failed / canceled / incomplete job must not have
its (partial or empty) output ingested as if real: the ingest records a FAILED
Execution so the attempt is visible, but fabricates NO Findings / Hypotheses /
Papers. Two layers:
  1. job_outcome: pure unit cases (A2A Task states, non-Task dicts, garbage).
  2. live-Neo4j e2e: a FAILED Theorizer Task whose artifacts WOULD parse to a
     theory still ingests zero theory nodes, leaving only a failed Execution.

Run: python -m pytest tests/integrations/asta/test_failsafe.py -q
The e2e class is skipped automatically when Neo4j is not reachable.
"""

from __future__ import annotations

import json
import uuid

import pytest

from wheeler.integrations.asta._marshal import job_outcome

# A minimal theory artifact that parse_theorizer DOES turn into one theory with
# one law. Wrapping it in a failed-status Task lets the e2e prove the failsafe
# GATE (not an empty parse) is what suppresses the output.
_THEORY_ARTIFACT = {
    "artifactId": "theory-1",
    "metadata": {"type": "theory"},
    "parts": [
        {
            "kind": "data",
            "data": {
                "id": "theory-1",
                "name": "Failsafe Test Theory",
                "description": "A theory that must NOT be ingested from a failed run.",
                "entities": {},
                "annotations": {},
                "content": [
                    {
                        "id": "c1",
                        "type": "SECTIONS",
                        "title": "Theory Statements",
                        "childIds": ["c2"],
                    },
                    {
                        "id": "c2",
                        "type": "SECTION",
                        "title": "The law that should never be stored",
                        "childIds": ["c3"],
                    },
                    {"id": "c3", "type": "MARKDOWN", "text": "Body of the law."},
                ],
            },
        }
    ],
}


def _failed_task() -> dict:
    return {
        "kind": "task",
        "id": "task-failed-1",
        "status": {
            "state": "failed",
            "message": {"parts": [{"text": "the upstream model timed out"}]},
        },
        "metadata": {"run_id": "gen-failsafe-failed-01"},
        "artifacts": [_THEORY_ARTIFACT],
    }


def _completed_task() -> dict:
    doc = _failed_task()
    doc["status"]["state"] = "completed"
    doc["metadata"]["run_id"] = "gen-failsafe-ok-01"
    return doc


# ---------------------------------------------------------------------------
# 1. job_outcome (pure)
# ---------------------------------------------------------------------------


class TestJobOutcome:
    def test_completed_a2a_task_is_ok(self):
        out = job_outcome(_completed_task())
        assert out.ok is True
        assert out.state == "completed"

    @pytest.mark.parametrize("state", ["failed", "canceled", "rejected", "working", "input-required"])
    def test_non_completed_a2a_state_is_not_ok(self, state):
        doc = _failed_task()
        doc["status"]["state"] = state
        out = job_outcome(doc)
        assert out.ok is False
        assert out.state == state
        assert out.detail  # a human reason is surfaced

    def test_failed_task_surfaces_status_message(self):
        out = job_outcome(_failed_task())
        assert out.ok is False
        assert "timed out" in out.detail

    def test_none_is_missing(self):
        out = job_outcome(None)
        assert out.ok is False
        assert out.state == "missing"

    def test_non_dict_is_invalid(self):
        out = job_outcome("not a dict")
        assert out.ok is False
        assert out.state == "invalid"

    def test_plain_result_dict_is_ok(self):
        # A LiteratureSearchResult / S2 response / report envelope has no A2A
        # status block: a present dict is a usable artifact (the transport already
        # rejected the empty / missing cases).
        out = job_outcome({"query": "x", "results": []})
        assert out.ok is True
        assert out.state == "completed"

    def test_uppercase_state_normalized(self):
        doc = _failed_task()
        doc["status"]["state"] = "COMPLETED"
        assert job_outcome(doc).ok is True


# ---------------------------------------------------------------------------
# 2. Live-Neo4j e2e: a FAILED job ingests no outputs, only a failed Execution
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


def _cleanup(e2e_config, e2e_tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged (per-run uuid),
    never by service or corpus_id (the e2e config is the shared namespace)."""
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

    try:
        asyncio.run(_run())
    except Exception:
        # Best-effort teardown: a transient Neo4j blip must not turn a
        # passing test into an ERROR. Orphans carry a per-run uuid e2e_tag.
        pass


class TestFailsafeE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        _cleanup(e2e_config, self._e2e_tag)
        yield
        _cleanup(e2e_config, self._e2e_tag)

    @pytest.mark.asyncio
    async def test_failed_theorizer_job_ingests_no_outputs(self, e2e_config):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.theorizer import (
            ingest_theorizer,
            parse_theorizer,
        )

        doc = _failed_task()
        # Sanity: the artifacts WOULD parse to a theory if the run had completed,
        # so a zero-output ingest proves the GATE suppressed it, not an empty parse.
        theories, _ = parse_theorizer(doc)
        assert len(theories) == 1

        artifact_path = self._tmp / "failed_theorizer.json"
        artifact_path.write_text(json.dumps(doc))

        report = await ingest_theorizer(
            doc, link_to=None, config=e2e_config, artifact_path=str(artifact_path)
        )
        # Tag this run's nodes (Execution + artifact) for hermetic teardown.
        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        run_ids = [i for i in (report.execution_id, report.artifact) if i]
        async with driver.session(database=db) as s:
            if run_ids:
                await s.run(
                    "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                    ids=run_ids,
                    tag=self._e2e_tag,
                )

        # The run is reported failed, with the job's own state.
        assert report.failed is True
        assert report.job_state == "failed"
        assert report.created == 0  # NO theories / hypotheses / papers fabricated
        assert report.execution_id  # but the attempt IS recorded

        async with driver.session(database=db) as s:
            # The Execution exists and is honestly marked failed, carrying the
            # job's state + reason in its queryable custom bag.
            res = await s.run(
                "MATCH (x:Execution {id: $xid}) "
                "RETURN x.status AS status, x.custom_job_state AS job_state, "
                "x.custom_error AS err",
                xid=report.execution_id,
            )
            rec = await res.single()
            assert rec["status"] == "failed"
            assert rec["job_state"] == "failed"
            assert rec["err"]  # the status message was stamped
            # ZERO theory Findings / Hypotheses were generated by this run.
            res = await s.run(
                "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                "WHERE n:Finding OR n:Hypothesis RETURN count(n) AS c",
                xid=report.execution_id,
            )
            assert (await res.single())["c"] == 0

    @pytest.mark.asyncio
    async def test_failed_then_successful_retry_flips_status_to_completed(
        self, e2e_config
    ):
        """A successful retry that REUSES a prior failed Execution (same
        service+session_id) must flip status back to completed, not inherit the
        stale "failed" (regression: status was only set at creation time)."""
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.theorizer import ingest_theorizer

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        async def _tag(report):
            ids = [i for i in (report.execution_id, report.artifact) if i]
            async with driver.session(database=db) as s:
                if ids:
                    await s.run(
                        "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                        ids=ids,
                        tag=self._e2e_tag,
                    )
                if report.execution_id:
                    await s.run(
                        "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                        "SET n.e2e_tag = $tag",
                        xid=report.execution_id,
                        tag=self._e2e_tag,
                    )

        # Same run_id on both -> same session_id -> the SAME Execution is reused.
        failed = _failed_task()
        completed = json.loads(json.dumps(failed))  # deep copy
        completed["status"]["state"] = "completed"  # same run_id, now successful

        artifact_path = self._tmp / "retry.json"

        # 1. Failed run: failed Execution, zero outputs.
        artifact_path.write_text(json.dumps(failed))
        r1 = await ingest_theorizer(
            failed, link_to=None, config=e2e_config, artifact_path=str(artifact_path)
        )
        await _tag(r1)
        assert r1.failed is True
        assert r1.created == 0

        # 2. Successful retry with the same run_id: reuses the Execution, flips it
        # to completed, and now ingests the theory.
        artifact_path.write_text(json.dumps(completed))
        r2 = await ingest_theorizer(
            completed,
            link_to=None,
            config=e2e_config,
            artifact_path=str(artifact_path),
        )
        await _tag(r2)
        assert r2.execution_id == r1.execution_id  # same Execution reused
        assert r2.failed is False
        assert r2.created >= 1  # the theory IS now ingested

        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid}) "
                "RETURN x.status AS status, x.custom_job_state AS job_state",
                xid=r2.execution_id,
            )
            rec = await res.single()
            # The graph no longer lies that the (now successful) run failed.
            assert rec["status"] == "completed"
            assert rec["job_state"] != "failed"

    @pytest.mark.asyncio
    async def test_record_failed_execution_when_no_artifact(self, e2e_config):
        """The visibility half: a never-returned-artifact attempt (the CLI failed)
        still leaves a queryable failed Execution wired to its inputs."""
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta._marshal import record_failed_execution
        from wheeler.tools.graph_tools import _get_backend, execute_tool

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Seed a Question the failed run was supposed to address (its USED input).
        q = json.loads(
            await execute_tool(
                "add_question",
                {"question": "E2E: failed-run input question", "priority": 5},
                e2e_config,
            )
        )
        qid = q["node_id"]
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag", id=qid, tag=self._e2e_tag
            )

        backend = await _get_backend(e2e_config)
        sid = f"failsafe-rec-{uuid.uuid4().hex[:10]}"
        report = await record_failed_execution(
            backend,
            e2e_config,
            service="asta:theorizer",
            session_id=sid,
            kind="theory-generation",
            description="Asta Theorizer FAILED: auth expired",
            reason="auth expired (exit 1)",
            used_inputs=[qid],
        )
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=report.execution_id,
                tag=self._e2e_tag,
            )

        assert report.failed is True
        assert report.execution_id.startswith("X-")
        assert report.used == 1  # the USED edge to the seeded question
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid}) "
                "RETURN x.status AS status, x.custom_error AS err",
                xid=report.execution_id,
            )
            rec = await res.single()
            assert rec["status"] == "failed"
            assert "auth expired" in (rec["err"] or "")
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[:USED]->(q {id: $qid}) "
                "RETURN count(q) AS c",
                xid=report.execution_id,
                qid=qid,
            )
            assert (await res.single())["c"] == 1

        # Idempotent: a "retry" with the same (service, session_id) reuses it.
        report2 = await record_failed_execution(
            backend,
            e2e_config,
            service="asta:theorizer",
            session_id=sid,
            kind="theory-generation",
            description="retry",
            reason="auth expired again",
            used_inputs=[qid],
        )
        assert report2.execution_id == report.execution_id
