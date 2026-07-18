"""Tests for the LLM-SR equation-discovery marshal-out adapter.

Two layers, NEITHER making a live discovery run:
  1. parse_discover: a real captured best.json fixture plus shape-drift /
     garbage tolerance (never raises).
  2. live-Neo4j e2e: ingest the fixture, assert the winner subgraph (Script +
     Finding + Document, BOTH provenance sides), then re-ingest and assert
     idempotency. Skipped automatically when Neo4j is unreachable.

Run: python -m pytest tests/integrations/llmsr/test_discover.py -q
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from wheeler.integrations.llmsr.discover import RunMeta, parse_discover

FIXTURE = Path(__file__).parent / "fixtures" / "best_completed.json"
SERVICE_TAG = "llmsr:discover"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


# ---------------------------------------------------------------------------
# 1. Defensive parse
# ---------------------------------------------------------------------------


class TestParseDiscover:
    def test_non_dict_is_empty(self):
        records, run_meta = parse_discover("not a dict")
        assert records == []
        assert isinstance(run_meta, RunMeta)

    def test_empty_doc_is_empty(self):
        records, run_meta = parse_discover({})
        assert records == []
        assert isinstance(run_meta, RunMeta)

    def test_failed_status_yields_no_records(self):
        records, run_meta = parse_discover(
            {"status": "failed", "run_id": "r1", "generator": "claude"}
        )
        assert records == []
        assert run_meta.run_id == "r1"  # metadata still lifted for the failed run

    def test_completed_but_missing_equation_yields_no_records(self):
        records, _ = parse_discover(
            {"status": "completed", "run_id": "r1", "program": ""}
        )
        assert records == []

    def test_parses_real_fixture(self):
        doc = _load_fixture()
        records, run_meta = parse_discover(doc)
        assert len(records) == 1
        assert run_meta.run_id == doc["run_id"]
        assert run_meta.generator == doc["generator"]
        rec = records[0]
        assert rec["metric"] == "mse"
        assert isinstance(rec["value"], float)
        assert rec["equation"] and rec["program"]
        assert len(rec["params"]) == 10


# ---------------------------------------------------------------------------
# 2. Live-Neo4j e2e (per-run e2e_tag, hermetic teardown)
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


def _cleanup_discover(e2e_config, e2e_tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged.

    EXACTLY ``MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n`` and nothing
    else. NEVER delete by ``service``: the e2e config runs on the SHARED default
    namespace where production nodes carry the same service tag, so a
    service-scoped delete would wipe real user data.
    """
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
                    "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
                    tag=e2e_tag,
                )
        finally:
            await driver.close()

    asyncio.run(_run())


class TestIngestDiscoverE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        # Temp cwd so the on-disk indices, the durable raw store, and the written
        # discovery .py all land in a sandbox; per-run unique tag so teardown
        # never touches another test or production data.
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        _cleanup_discover(e2e_config, self._e2e_tag)
        yield
        _cleanup_discover(e2e_config, self._e2e_tag)

    async def _tag_ids(self, e2e_config, ids):
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        ids = [i for i in ids if i]
        if not ids:
            return
        async with driver.session(database=e2e_config.neo4j.database) as s:
            await s.run(
                "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                ids=ids, tag=self._e2e_tag,
            )

    async def _tag_run(self, e2e_config, report):
        """Tag ONLY the nodes THIS run created: the report ids plus the run's
        WAS_GENERATED_BY fan-in (Script, Finding, Document). NEVER by service."""
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        await self._tag_ids(e2e_config, [report.execution_id, report.artifact])
        if report.execution_id:
            async with driver.session(database=db) as s:
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                )

    @pytest.mark.asyncio
    async def test_ingest_buckets_and_is_idempotent(self, e2e_config):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.llmsr.discover import ingest_discover
        from wheeler.tools.graph_tools import execute_tool

        doc = _load_fixture()
        artifact_path = self._tmp / "best.json"
        artifact_path.write_text(json.dumps(doc))

        # Seed a Dataset input so the run has something to USE (input side), and a
        # Question as the link target. Tag both for hermetic cleanup.
        csv = self._tmp / "data.csv"
        csv.write_text("x,y\n1,2\n3,4\n")
        ds = json.loads(await execute_tool("add_dataset", {
            "path": str(csv), "type": "csv", "description": "e2e input",
            "service": SERVICE_TAG,
        }, e2e_config))
        q = json.loads(await execute_tool("add_question", {
            "question": "E2E: does LLM-SR discover a growth law?", "priority": 5,
        }, e2e_config))
        ds_id, question_id = ds["node_id"], q["node_id"]
        await self._tag_ids(e2e_config, [ds_id, question_id])

        # --- First ingest ---
        report1 = await ingest_discover(
            doc, link_to=question_id, config=e2e_config,
            artifact_path=str(artifact_path), used_inputs=[ds_id, question_id],
        )
        await self._tag_run(e2e_config, report1)
        assert report1.execution_id
        assert report1.failed is False
        assert report1.created == 2  # exactly the Script + the Finding

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        xid = report1.execution_id
        async with driver.session(database=db) as s:
            async def count(cypher, **kw):
                r = await s.run(cypher, **kw)
                rec = await r.single()
                return rec[0] if rec else None

            # OUTPUT side: Script + Finding + Document each WAS_GENERATED_BY the run
            assert await count(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(n)", x=xid
            ) == 1
            assert await count(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(n)", x=xid
            ) == 1
            assert await count(
                "MATCH (n:Document)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(n)", x=xid
            ) == 1
            # INPUT side: the run USED the seeded inputs
            assert await count(
                "MATCH (x:Execution {id:$x})-[:USED]->(n) RETURN count(n)", x=xid
            ) >= 1
            # Papers are reference entities: NEVER WAS_GENERATED_BY
            assert await count(
                "MATCH (p:Paper)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(p)", x=xid
            ) == 0
            # Execution status is honest
            assert await count(
                "MATCH (x:Execution {id:$x}) RETURN x.status", x=xid
            ) == "completed"
            # the Script is the FULL program on disk, with the equation queryable
            script_path = await count(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN n.path", x=xid
            )
            assert script_path and Path(script_path).exists()
            assert await count(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.custom_equation", x=xid
            )

        # --- Re-ingest: idempotent ---
        report2 = await ingest_discover(
            doc, link_to=question_id, config=e2e_config,
            artifact_path=str(artifact_path), used_inputs=[ds_id, question_id],
        )
        await self._tag_run(e2e_config, report2)
        assert report2.created == 0
        assert report2.execution_id == xid
        async with driver.session(database=db) as s:
            r = await s.run(
                "MATCH (x:Execution {service:$svc, session_id:$sid}) RETURN count(x)",
                svc=SERVICE_TAG, sid=doc["run_id"],
            )
            assert (await r.single())[0] == 1  # exactly one Execution, reused
            r = await s.run(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(n)",
                x=xid,
            )
            assert (await r.single())[0] == 1  # no duplicate Script
