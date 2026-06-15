"""Tests for the Asta Paper Finder vertical slice.

Three layers, none of which make a live asta call:
  1. parse_paper_finder: pure parse of the checked-in synthetic fixture.
  2. transport.run_asta: contract test driven by a STUB command (a python -c
     one-liner that writes a file or exits non-zero), never real asta.
  3. live-Neo4j e2e: ingest the fixture TWICE and assert idempotency
     (one Paper per corpus_id, RELEVANT_TO edge created once), plus that the
     promoted corpus_id and a parked custom scalar are queryable in Neo4j.

Run: python -m pytest tests/integrations/ -q
The e2e class is skipped automatically when Neo4j is not reachable.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest

from wheeler.integrations.asta.schemas import parse_paper_finder
from wheeler.integrations.asta.transport import run_asta

FIXTURE = Path(__file__).parent / "fixtures" / "paper_finder_sample.json"

# Service tag for every node this adapter writes. Teardown keys on it (plus the
# fixture corpus_ids) so cleanup is hermetic regardless of a per-run e2e tag.
SERVICE_TAG = "asta:paper-finder"

# Every corpus_id the fixture papers carry (normalized digit-strings).
PF_CORPUS_IDS = ["211234567", "222345678"]


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


# ---------------------------------------------------------------------------
# 1. Parse
# ---------------------------------------------------------------------------


class TestParsePaperFinder:
    def test_parses_two_distinct_papers(self):
        records = parse_paper_finder(_load_fixture())
        assert len(records) == 2
        corpus_ids = {r.corpus_id for r in records}
        assert corpus_ids == {"211234567", "222345678"}

    def test_promotes_first_class_fields(self):
        records = parse_paper_finder(_load_fixture())
        srm = next(r for r in records if r.corpus_id == "211234567")
        assert srm.title.startswith("A Spike Response Model")
        assert srm.year == 2021
        assert "Ada Lovelace" in srm.authors
        assert "Carl Sagan" in srm.authors

    def test_parks_custom_scalars(self):
        records = parse_paper_finder(_load_fixture())
        srm = next(r for r in records if r.corpus_id == "211234567")
        assert srm.custom["relevance_score"] == 0.93
        assert srm.custom["venue"] == "Journal of Neuroscience"
        assert srm.custom["url"] == "https://example.org/paper/211234567"
        assert srm.custom["citation_count"] == 142
        assert "abstract" in srm.custom
        # Non-scalar structures are summarized to scalar counts.
        assert srm.custom["snippet_count"] == 1
        assert srm.custom["citation_context_count"] == 1

    def test_citation_contexts_become_cited_corpus_ids(self):
        records = parse_paper_finder(_load_fixture())
        srm = next(r for r in records if r.corpus_id == "211234567")
        assert srm.cited_corpus_ids == ["199888777"]
        vp = next(r for r in records if r.corpus_id == "222345678")
        assert vp.cited_corpus_ids == []

    def test_corpus_id_normalized_to_digit_string(self):
        # Int, digit-string, and float all map to the same normalized key.
        doc = {"results": [
            {"corpusId": 123, "title": "int"},
            {"corpusId": "123", "title": "str"},
            {"corpusId": 123.0, "title": "float"},
        ]}
        records = parse_paper_finder(doc)
        assert [r.corpus_id for r in records] == ["123", "123", "123"]

    def test_defensive_on_garbage(self):
        assert parse_paper_finder({}) == []
        assert parse_paper_finder({"results": "nope"}) == []
        assert parse_paper_finder("not a dict") == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. Transport contract (stub command, never real asta)
# ---------------------------------------------------------------------------


class TestRunAstaTransport:
    def test_success_returns_loaded_json(self, tmp_path):
        out = tmp_path / "result.json"
        payload = {"query": "q", "results": []}
        # Stub command: write the payload to the -o path and exit 0.
        code = (
            "import json,sys;"
            f"open({str(out)!r},'w').write(json.dumps({payload!r}))"
        )
        doc = run_asta([sys.executable, "-c", code], output_path=out)
        assert doc == payload

    def test_nonzero_exit_returns_none(self, tmp_path):
        out = tmp_path / "result.json"
        # Stub writes a file but exits non-zero: must be treated as failure.
        code = (
            f"open({str(out)!r},'w').write('{{}}');"
            "import sys;sys.exit(3)"
        )
        doc = run_asta([sys.executable, "-c", code], output_path=out)
        assert doc is None

    def test_missing_output_returns_none(self, tmp_path):
        out = tmp_path / "never_written.json"
        # Exit 0 but write nothing to the -o path.
        doc = run_asta([sys.executable, "-c", "pass"], output_path=out)
        assert doc is None

    def test_empty_output_returns_none(self, tmp_path):
        out = tmp_path / "empty.json"
        code = f"open({str(out)!r},'w').write('   ')"
        doc = run_asta([sys.executable, "-c", code], output_path=out)
        assert doc is None

    def test_missing_binary_returns_none(self, tmp_path):
        out = tmp_path / "x.json"
        doc = run_asta(["definitely-not-a-real-binary-xyz"], output_path=out)
        assert doc is None


# ---------------------------------------------------------------------------
# 3. Live-Neo4j e2e: ingest idempotency
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


def _cleanup_paper_finder(e2e_config, e2e_tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged.

    The teardown is EXACTLY ``MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n``
    and nothing else. It NEVER deletes by ``service`` or by ``corpus_id``: the
    e2e config runs against the SHARED default Neo4j namespace (project_tag is
    empty), and production ingests carry the SAME ``asta:paper-finder`` service
    tag and the same corpus_ids, so a service-scoped or corpus_id-scoped delete
    would wipe real user data. Every node this run creates is tagged with the
    per-run unique ``e2e_tag`` (a uuid) right after each ingest, scoped off the
    run's Execution and its WAS_GENERATED_BY descendants plus the returned node
    ids, so this delete can only ever match nodes this run created.
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


class TestIngestPaperFinderE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        # Run inside a temp cwd so the on-disk index + knowledge/synthesis
        # writes land in an isolated sandbox we delete afterward. The persisted
        # corpus_id index is therefore fresh per test, so created-vs-deduped
        # counts are hermetic and never depend on leftover cross-run state.
        monkeypatch.chdir(tmp_path)
        # Per-run unique e2e tag (not a shared constant), so this test's
        # teardown can never DETACH DELETE another test's nodes.
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        # Pre-clean any nodes a prior interrupted run left behind, so the
        # first-ingest counts start from a clean graph.
        _cleanup_paper_finder(e2e_config, self._e2e_tag)
        yield
        _cleanup_paper_finder(e2e_config, self._e2e_tag)

    async def _tag_all(self, e2e_config, report):
        """Tag exactly the nodes THIS run created with the per-run e2e tag.

        Scopes strictly off the run's Execution and its WAS_GENERATED_BY fan-in
        plus the ids the ImportReport returned, so teardown (which deletes ONLY
        by e2e_tag) can never touch a pre-existing production node that merely
        shares a service tag or a corpus_id. NEVER tag by service or corpus_id:
        the e2e config runs on the shared default namespace where production
        nodes carry the same asta:paper-finder service and the same corpus_ids.
        """
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        # The exact ids this run produced (Execution, artifact, every Paper).
        run_ids = [i for i in (report.execution_id, report.artifact) if i]
        run_ids += [pid for pid in report.paper_ids if pid]
        async with driver.session(database=db) as s:
            if run_ids:
                await s.run(
                    "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                    ids=run_ids, tag=self._e2e_tag,
                )
            # Anything WAS_GENERATED_BY this run's Execution (papers, the raw
            # Dataset artifact): scoped off the Execution id this run owns.
            if report.execution_id:
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                )

    @pytest.mark.asyncio
    async def test_ingest_is_idempotent(self, e2e_config):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.ingest import ingest_paper_finder

        doc = _load_fixture()

        # Seed a Question to link papers RELEVANT_TO.
        from wheeler.tools.graph_tools import execute_tool

        q_result = json.loads(await execute_tool(
            "add_question",
            {"question": "E2E: which SRM papers are relevant?", "priority": 5},
            e2e_config,
        ))
        question_id = q_result["node_id"]
        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=question_id, tag=self._e2e_tag,
            )

        # First ingest.
        report1 = await ingest_paper_finder(doc, link_to=question_id, config=e2e_config)
        await self._tag_all(e2e_config, report1)
        assert report1.created == 2
        assert report1.deduped == 0

        # Snapshot the Execution provenance fan-in after the first ingest, so we
        # can prove re-ingest neither duplicates the Execution nor grows it. The
        # query is scoped to THIS run's Execution id (not the shared service tag)
        # so a production asta:paper-finder Execution on the shared namespace
        # cannot perturb the count.
        run_exec_id = report1.execution_id
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (n)-[r:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                "RETURN count(r) AS c",
                xid=run_exec_id,
            )
            gen_by_after_first = (await res.single())["c"]

        # Second ingest of the SAME artifact: no new papers.
        report2 = await ingest_paper_finder(doc, link_to=question_id, config=e2e_config)
        await self._tag_all(e2e_config, report2)
        assert report2.created == 0
        assert report2.deduped == 2

        # --- Execution provenance is idempotent across re-ingest ---
        # Re-ingesting the SAME artifact must NOT create a second Execution node,
        # and must NOT accumulate extra WAS_GENERATED_BY edges. (Regression:
        # add_execution was previously called unconditionally, duplicating the
        # Execution and its provenance fan-in on every re-ingest.) Scoped to this
        # run's Execution id so the assertion holds on the shared namespace.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid}) RETURN count(x) AS c",
                xid=run_exec_id,
            )
            assert (await res.single())["c"] == 1
            res = await s.run(
                "MATCH (n)-[r:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                "RETURN count(r) AS c",
                xid=run_exec_id,
            )
            assert (await res.single())["c"] == gen_by_after_first
        # The report points at the same Execution both runs (reused, not new).
        assert report2.execution_id == report1.execution_id

        # Exactly one Paper per corpus_id (idempotency).
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids "
                "RETURN p.corpus_id AS cid, count(p) AS c",
                cids=["211234567", "222345678"],
            )
            rows = {r["cid"]: r["c"] async for r in result}
        assert rows == {"211234567": 1, "222345678": 1}

        # corpus_id is queryable (promoted + indexed).
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (p:Paper {corpus_id: $cid}) RETURN p.id AS id",
                cid="211234567",
            )
            rec = await result.single()
        assert rec is not None
        srm_paper_id = rec["id"]

        # The parked custom scalar is queryable (flatten on write).
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (p:Paper {corpus_id: $cid}) "
                "WHERE p.custom_relevance_score > 0.9 RETURN p.id AS id",
                cid="211234567",
            )
            rec = await result.single()
        assert rec is not None
        assert rec["id"] == srm_paper_id

        # RELEVANT_TO edge exists exactly once despite two ingests (link_once).
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (p:Paper {corpus_id: $cid})-[r:RELEVANT_TO]->(q {id: $qid}) "
                "RETURN count(r) AS c",
                cid="211234567", qid=question_id,
            )
            rec = await result.single()
        assert rec["c"] == 1

        # get_node reassembles the custom bag against the Pydantic model.
        from wheeler.graph.backend import get_backend

        backend = get_backend(e2e_config)
        node = await backend.get_node("Paper", srm_paper_id)
        assert node is not None
        assert node["custom"]["relevance_score"] == 0.93
        assert node["custom"]["venue"] == "Journal of Neuroscience"

    @pytest.mark.asyncio
    async def test_output_artifact_registered_and_linked(self, e2e_config, tmp_path):
        """Every service output is an artifact: register, link, dedupe on re-run.

        Pass artifact_path and assert:
          - a Dataset artifact node exists for that file, tagged with service,
          - it is WAS_GENERATED_BY the run Execution,
          - each Paper is WAS_DERIVED_FROM it,
          - re-ingest does NOT duplicate the artifact node or these edges.
        """
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.ingest import ingest_paper_finder

        doc = _load_fixture()

        # Write the raw -o output to a real file so ensure_artifact (which
        # requires the path to exist) can register it. Lives under the temp cwd.
        artifact_file = tmp_path / "asta_paper_finder_output.json"
        artifact_file.write_text(json.dumps(doc))

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # First ingest with the artifact path.
        report1 = await ingest_paper_finder(
            doc, link_to=None, config=e2e_config, artifact_path=str(artifact_file),
        )
        await self._tag_all(e2e_config, report1)
        assert report1.artifact, "ImportReport.artifact should hold the artifact id"
        artifact_id = report1.artifact
        assert artifact_id.startswith("D-")
        exec_id = report1.execution_id

        # The artifact node exists, is a Dataset, carries the service tag, and
        # points at the DURABLE raw store (not the ephemeral input path). The
        # run_id (thread_id) is the durable-store key and a queryable custom field.
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (d:Dataset {id: $aid}) "
                "RETURN d.service AS service, d.path AS path, "
                "d.custom_run_id AS run_id",
                aid=artifact_id,
            )
            rec = await result.single()
        assert rec is not None
        assert rec["service"] == "asta:paper-finder"
        # Path is the durable store copy, not the ephemeral input file.
        assert rec["path"] != str(artifact_file)
        assert ".wheeler/asta/raw/asta-paper-finder/thread-e2e-0001.json" in rec["path"]
        assert Path(rec["path"]).exists()  # the saved raw output is reachable
        assert rec["run_id"] == "thread-e2e-0001"
        durable_path = rec["path"]

        # Artifact WAS_GENERATED_BY the run Execution (exactly one edge).
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (d:Dataset {id: $aid})-[r:WAS_GENERATED_BY]->(x {id: $xid}) "
                "RETURN count(r) AS c",
                aid=artifact_id, xid=exec_id,
            )
            rec = await result.single()
        assert rec["c"] == 1

        # Each Paper is WAS_DERIVED_FROM the artifact (one edge per paper).
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (p:Paper)-[r:WAS_DERIVED_FROM]->(d:Dataset {id: $aid}) "
                "WHERE p.corpus_id IN $cids "
                "RETURN p.corpus_id AS cid, count(r) AS c",
                aid=artifact_id, cids=["211234567", "222345678"],
            )
            rows = {r["cid"]: r["c"] async for r in result}
        assert rows == {"211234567": 1, "222345678": 1}

        # Second ingest of the SAME artifact: no duplicate artifact node, no
        # duplicate edges (link_once + ensure_artifact path idempotency).
        report2 = await ingest_paper_finder(
            doc, link_to=None, config=e2e_config, artifact_path=str(artifact_file),
        )
        await self._tag_all(e2e_config, report2)
        assert report2.artifact == artifact_id

        # Still exactly one Dataset for this service + durable path (path-dedupe
        # in the raw store + ensure_artifact idempotency on re-ingest).
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (d:Dataset) WHERE d.path = $path AND d.service = $svc "
                "RETURN count(d) AS c",
                path=durable_path, svc="asta:paper-finder",
            )
            rec = await result.single()
        assert rec["c"] == 1

        # WAS_GENERATED_BY still exactly one edge.
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (d:Dataset {id: $aid})-[r:WAS_GENERATED_BY]->(x {id: $xid}) "
                "RETURN count(r) AS c",
                aid=artifact_id, xid=exec_id,
            )
            rec = await result.single()
        assert rec["c"] == 1

        # WAS_DERIVED_FROM still exactly one edge per paper.
        async with driver.session(database=db) as s:
            result = await s.run(
                "MATCH (p:Paper)-[r:WAS_DERIVED_FROM]->(d:Dataset {id: $aid}) "
                "WHERE p.corpus_id IN $cids "
                "RETURN p.corpus_id AS cid, count(r) AS c",
                aid=artifact_id, cids=["211234567", "222345678"],
            )
            rows = {r["cid"]: r["c"] async for r in result}
        assert rows == {"211234567": 1, "222345678": 1}


# ---------------------------------------------------------------------------
# 4. Live-Neo4j e2e: service tag reaches Neo4j on non-Paper node types
# ---------------------------------------------------------------------------


class TestServiceTagReachesNeo4j:
    """Regression: an adapter's service tag must land in Neo4j (not just JSON).

    Before service was promoted to a first-class NodeBase field, only
    add_paper and add_execution forwarded it into create_node props. Every
    other add_* dropped it (extra="allow" let it reach knowledge/{id}.json,
    but `MATCH (n) WHERE n.service = ...` found nothing). This test asserts a
    NON-Paper node created via execute_tool is queryable by service in Neo4j
    AND round-trips through its Pydantic model.
    """

    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        monkeypatch.chdir(tmp_path)
        # Per-run unique e2e tag, so this test's teardown can never DETACH
        # DELETE another test's nodes.
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        yield
        import asyncio

        from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

        tag = self._e2e_tag

        async def _cleanup():
            driver = AsyncGraphDatabase.driver(
                e2e_config.neo4j.uri,
                auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
                notifications_min_severity=NotificationMinimumSeverity.OFF,
            )
            try:
                async with driver.session(database=e2e_config.neo4j.database) as s:
                    await s.run(
                        "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
                        tag=tag,
                    )
            finally:
                await driver.close()

        asyncio.run(_cleanup())

    @pytest.mark.asyncio
    async def test_finding_service_tag_reaches_neo4j(self, e2e_config):
        from wheeler.graph.backend import get_backend
        from wheeler.graph.driver import get_async_driver
        from wheeler.models import model_for_label
        from wheeler.tools.graph_tools import execute_tool

        svc = "prov:svc:1"
        # A Finding is a non-Paper node; before this change its service was
        # dropped before create_node and never reached Neo4j.
        result = json.loads(await execute_tool(
            "add_finding",
            {
                "description": "E2E: service tag on a non-Paper node",
                "confidence": 0.8,
                "service": svc,
            },
            e2e_config,
        ))
        node_id = result["node_id"]
        assert node_id.startswith("F-")

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=node_id, tag=self._e2e_tag,
            )

        # (a) service reached Neo4j and is queryable.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (n) WHERE n.id = $id RETURN n.service AS service",
                id=node_id,
            )
            rec = await res.single()
        assert rec is not None
        assert rec["service"] == svc

        # (b) the node round-trips through its Pydantic model with service set.
        backend = get_backend(e2e_config)
        node = await backend.get_node("Finding", node_id)
        assert node is not None
        model = model_for_label("Finding")(**node)
        assert model.service == svc

    @pytest.mark.asyncio
    async def test_execution_service_tag_reaches_neo4j(self, e2e_config):
        from wheeler.graph.backend import get_backend
        from wheeler.graph.driver import get_async_driver
        from wheeler.models import model_for_label
        from wheeler.tools.graph_tools import execute_tool

        svc = "prov:svc:1"
        result = json.loads(await execute_tool(
            "add_execution",
            {
                "kind": "analysis",
                "description": "E2E: service tag on an Execution node",
                "service": svc,
            },
            e2e_config,
        ))
        node_id = result["node_id"]
        assert node_id.startswith("X-")

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=node_id, tag=self._e2e_tag,
            )

        # (a) service reached Neo4j and is queryable.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (n) WHERE n.id = $id RETURN n.service AS service",
                id=node_id,
            )
            rec = await res.single()
        assert rec is not None
        assert rec["service"] == svc

        # (b) the node round-trips through its Pydantic model with service set.
        backend = get_backend(e2e_config)
        node = await backend.get_node("Execution", node_id)
        assert node is not None
        model = model_for_label("Execution")(**node)
        assert model.service == svc
