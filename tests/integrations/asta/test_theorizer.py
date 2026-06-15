"""Tests for the Asta Theorizer vertical slice.

Two layers, neither making a live asta call:
  1. parse_theorizer: defensive parse of the checked-in synthetic fixture plus
     shape-drift / garbage tolerance (multi-key fallbacks, never raises).
  2. live-Neo4j e2e: ingest the fixture, asserting the bucketing subgraph (a
     parent Finding(artifact_type=theory) per theory, CONTAINS law Hypotheses,
     SUPPORTS/CONTRADICTS papers, novelty parked in queryable custom_novelty, a
     service-tagged Execution), then re-ingest the SAME artifact and assert
     idempotency (no duplicate nodes or edges).

Run: python -m pytest tests/integrations/test_theorizer.py -q
The e2e class is skipped automatically when Neo4j is not reachable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wheeler.integrations.asta.theorizer import parse_theorizer

FIXTURE = Path(__file__).parent / "fixtures" / "theorizer_sample.json"

E2E_TAG = "integrations_e2e_test"

# Every distinct corpus_id in the fixture (normalized to digit-strings).
ALL_CORPUS_IDS = [
    "311000001", "311000002", "311000003", "311000004",
    "311000005", "311000006", "311000007", "311000008",
]


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


# ---------------------------------------------------------------------------
# 1. Defensive parse
# ---------------------------------------------------------------------------


class TestParseTheorizer:
    def test_parses_two_theories(self):
        records = parse_theorizer(_load_fixture())
        assert len(records) == 2
        names = {r.name for r in records}
        assert "Adaptive Threshold Spike Response Theory" in names
        assert "Population Decorrelation Theory" in names

    def test_each_theory_has_two_laws(self):
        records = parse_theorizer(_load_fixture())
        for r in records:
            assert len(r.laws) == 2

    def test_laws_carry_text_and_novelty(self):
        records = parse_theorizer(_load_fixture())
        t1 = next(r for r in records if r.name.startswith("Adaptive Threshold"))
        novelties = {law.novelty for law in t1.laws}
        assert novelties == {"established", "new"}
        assert all(law.text for law in t1.laws)

    def test_supporting_and_contradicting_papers_parsed(self):
        records = parse_theorizer(_load_fixture())
        t1 = next(r for r in records if r.name.startswith("Adaptive Threshold"))
        law0 = t1.laws[0]
        sup_ids = {p.corpus_id for p in law0.supporting}
        con_ids = {p.corpus_id for p in law0.contradicting}
        assert sup_ids == {"311000001", "311000002"}
        assert con_ids == {"311000003"}

    def test_theory_custom_counts(self):
        records = parse_theorizer(_load_fixture())
        t1 = next(r for r in records if r.name.startswith("Adaptive Threshold"))
        assert t1.custom["law_count"] == 2
        assert t1.custom.get("novelty_established_count") == 1
        assert t1.custom.get("novelty_new_count") == 1

    def test_corpus_ids_normalized_to_digit_strings(self):
        records = parse_theorizer(_load_fixture())
        all_ids = {
            p.corpus_id
            for r in records
            for law in r.laws
            for p in (law.supporting + law.contradicting)
        }
        assert all_ids == set(ALL_CORPUS_IDS)

    # --- shape drift / fallbacks ---

    def test_results_key_fallback(self):
        doc = {"results": [{"name": "T", "laws": [{"statement": "L"}]}]}
        records = parse_theorizer(doc)
        assert len(records) == 1
        assert records[0].laws[0].text == "L"

    def test_bare_list_doc(self):
        doc = [{"title": "Bare", "statements": [{"text": "L1"}]}]
        records = parse_theorizer(doc)
        assert len(records) == 1
        assert records[0].name == "Bare"

    def test_alternate_paper_keys(self):
        doc = {
            "theories": [
                {
                    "name": "T",
                    "laws": [
                        {
                            "statement": "L",
                            "verdict": "derivable",
                            "supporting": [{"corpus_id": "999", "title": "S"}],
                            "conflicting": [{"corpus_id": "888", "title": "C"}],
                        }
                    ],
                }
            ]
        }
        records = parse_theorizer(doc)
        law = records[0].laws[0]
        assert law.novelty == "derivable"
        assert [p.corpus_id for p in law.supporting] == ["999"]
        assert [p.corpus_id for p in law.contradicting] == ["888"]

    def test_unknown_novelty_dropped(self):
        doc = {"theories": [{"name": "T", "laws": [{"text": "L", "novelty": "weird"}]}]}
        records = parse_theorizer(doc)
        assert records[0].laws[0].novelty == ""

    def test_count_and_skip_unknown_entries(self):
        # A non-dict theory and a theory with no name and no laws are skipped,
        # never raised; the one good theory survives.
        doc = {
            "theories": [
                "garbage",
                {"summary": "no name no laws"},
                {"name": "Good", "laws": [{"text": "L"}]},
            ]
        }
        records = parse_theorizer(doc)
        assert len(records) == 1
        assert records[0].name == "Good"

    def test_defensive_on_garbage(self):
        assert parse_theorizer({}) == []
        assert parse_theorizer({"theories": "nope"}) == []
        assert parse_theorizer("not a dict") == []  # type: ignore[arg-type]
        assert parse_theorizer(42) == []  # type: ignore[arg-type]
        assert parse_theorizer({"theories": []}) == []


# ---------------------------------------------------------------------------
# 2. Live-Neo4j e2e
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


class TestIngestTheorizerE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        # Run inside a temp cwd so the on-disk indices + knowledge/synthesis
        # writes land in an isolated sandbox we delete afterward.
        monkeypatch.chdir(tmp_path)
        yield
        # Teardown: delete all nodes this test created.
        import asyncio

        from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

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
                        tag=E2E_TAG,
                    )
            finally:
                await driver.close()

        asyncio.run(_cleanup())

    async def _tag_all(self, e2e_config):
        """Tag every node this run touched, so teardown can DETACH DELETE it."""
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            # Everything carrying the theorizer service tag (Execution, parent
            # Findings, Hypotheses, Papers, the artifact Dataset).
            await s.run(
                "MATCH (n) WHERE n.service = 'asta:theorizer' SET n.e2e_tag = $tag",
                tag=E2E_TAG,
            )
            # Papers key on corpus_id (service was set at create, but tag by
            # corpus_id too in case a paper pre-existed from another run).
            await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids SET p.e2e_tag = $tag",
                cids=ALL_CORPUS_IDS, tag=E2E_TAG,
            )

    @pytest.mark.asyncio
    async def test_ingest_buckets_and_is_idempotent(self, e2e_config):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.theorizer import ingest_theorizer
        from wheeler.tools.graph_tools import execute_tool

        doc = _load_fixture()

        # Seed a Question to link each theory parent AROSE_FROM.
        q_result = json.loads(await execute_tool(
            "add_question",
            {"question": "E2E: what governs RGC threshold adaptation?", "priority": 5},
            e2e_config,
        ))
        question_id = q_result["node_id"]
        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=question_id, tag=E2E_TAG,
            )

        # --- First ingest ---
        report1 = await ingest_theorizer(doc, link_to=question_id, config=e2e_config)
        await self._tag_all(e2e_config)
        assert report1.execution_id.startswith("X-")
        # 2 parent Findings + 4 Hypotheses + 8 distinct Papers created.
        assert report1.created == 2 + 4 + 8

        # Parent Finding(artifact_type=theory) exists, one per theory.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory', service: 'asta:theorizer'}) "
                "RETURN count(f) AS c"
            )
            rec = await res.single()
        assert rec["c"] == 2

        # Each parent CONTAINS its 2 law Hypotheses (4 CONTAINS edges total).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})-[r:CONTAINS]->(h:Hypothesis) "
                "WHERE f.service = 'asta:theorizer' RETURN count(r) AS c"
            )
            rec = await res.single()
        assert rec["c"] == 4

        # SUPPORTS / CONTRADICTS edges from Papers to Hypotheses exist.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper)-[r:SUPPORTS]->(h:Hypothesis) "
                "WHERE h.service = 'asta:theorizer' RETURN count(r) AS c"
            )
            supports = (await res.single())["c"]
            res = await s.run(
                "MATCH (p:Paper)-[r:CONTRADICTS]->(h:Hypothesis) "
                "WHERE h.service = 'asta:theorizer' RETURN count(r) AS c"
            )
            contradicts = (await res.single())["c"]
        # 6 supporting paper refs, 4 contradicting paper refs in the fixture.
        assert supports == 6
        assert contradicts == 4

        # novelty parked in custom_novelty and queryable (NOT in status).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (h:Hypothesis {service: 'asta:theorizer'}) "
                "WHERE h.custom_novelty = 'new' RETURN count(h) AS c"
            )
            new_count = (await res.single())["c"]
            # status must stay on the open/supported/rejected enum, never novelty.
            res = await s.run(
                "MATCH (h:Hypothesis {service: 'asta:theorizer'}) "
                "RETURN collect(DISTINCT h.status) AS statuses"
            )
            statuses = (await res.single())["statuses"]
        assert new_count == 2  # two laws have novelty="new"
        assert set(statuses) <= {"open"}
        assert "new" not in statuses
        assert "established" not in statuses

        # service-tagged Execution, exactly one per run.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {service: 'asta:theorizer'}) "
                "RETURN count(x) AS c, collect(x.kind)[0] AS kind"
            )
            rec = await res.single()
        assert rec["c"] == 1
        assert rec["kind"] == "theory-generation"

        # parent AROSE_FROM the seed Question.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})-[r:AROSE_FROM]->(q {id: $qid}) "
                "WHERE f.service = 'asta:theorizer' RETURN count(r) AS c",
                qid=question_id,
            )
            rec = await res.single()
        assert rec["c"] == 2

        # Each Paper is distinct (8 corpus_ids -> 8 Paper nodes).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids "
                "RETURN count(DISTINCT p) AS c",
                cids=ALL_CORPUS_IDS,
            )
            rec = await res.single()
        assert rec["c"] == 8

        # custom bag round-trips through the Pydantic model on read.
        from wheeler.graph.backend import get_backend

        backend = get_backend(e2e_config)
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (h:Hypothesis {service: 'asta:theorizer'}) "
                "WHERE h.custom_novelty = 'new' RETURN h.id AS id LIMIT 1"
            )
            hyp_id = (await res.single())["id"]
        node = await backend.get_node("Hypothesis", hyp_id)
        assert node is not None
        assert node["custom"]["novelty"] == "new"
        assert node["status"] == "open"

        # --- Second ingest of the SAME artifact: idempotent ---
        report2 = await ingest_theorizer(doc, link_to=question_id, config=e2e_config)
        await self._tag_all(e2e_config)
        # Nothing new is created; every theory/law/paper is deduped.
        assert report2.created == 0
        assert report2.deduped == 2 + 4 + 8

        # Still exactly the same node counts.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory', service: 'asta:theorizer'}) "
                "RETURN count(f) AS c"
            )
            assert (await res.single())["c"] == 2
            res = await s.run(
                "MATCH (h:Hypothesis {service: 'asta:theorizer'}) RETURN count(h) AS c"
            )
            assert (await res.single())["c"] == 4
            res = await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids "
                "RETURN count(DISTINCT p) AS c",
                cids=ALL_CORPUS_IDS,
            )
            assert (await res.single())["c"] == 8

        # Edges are not duplicated by the second ingest (link_once).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})-[r:CONTAINS]->(h:Hypothesis) "
                "WHERE f.service = 'asta:theorizer' RETURN count(r) AS c"
            )
            assert (await res.single())["c"] == 4
            res = await s.run(
                "MATCH (p:Paper)-[r:SUPPORTS]->(h:Hypothesis) "
                "WHERE h.service = 'asta:theorizer' RETURN count(r) AS c"
            )
            assert (await res.single())["c"] == 6
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})-[r:AROSE_FROM]->(q {id: $qid}) "
                "WHERE f.service = 'asta:theorizer' RETURN count(r) AS c",
                qid=question_id,
            )
            assert (await res.single())["c"] == 2
