"""Tests for the Asta Theorizer vertical slice (REAL A2A-Task output shape).

Two layers, neither making a live asta call:
  1. parse_theorizer: parse the trimmed REAL fixture (an A2A Task with theory /
     novelty / extraction artifacts) plus shape-drift / garbage tolerance
     (defensive multi-key fallbacks, never raises).
  2. live-Neo4j e2e: ingest the real fixture, asserting the bucketing subgraph
     (a parent Finding(artifact_type=theory) per theory, CONTAINS law
     Hypotheses, SUPPORTS papers per law, CONTRADICTS papers at theory level,
     novelty parked in queryable custom_novelty on the right Hypothesis, a
     service-tagged Execution carrying run_id/cost/time, a raw Document node
     pointing at the .wheeler/asta/raw store and carrying benchmark fields),
     then re-ingest the SAME artifact and assert idempotency.

Run: python -m pytest tests/integrations/asta/test_theorizer.py -q
The e2e class is skipped automatically when Neo4j is not reachable.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from wheeler.integrations.asta.theorizer import (
    RunMeta,
    parse_theorizer,
)

# Trimmed REAL Theorizer output: an A2A Task with 2 theory artifacts (3 + 2
# laws), their matching novelty artifacts, 1 extraction, and Task.metadata
# (run_id, cost, time). Structurally faithful, under 200KB.
FIXTURE = Path(__file__).parent / "fixtures" / "theorizer_real_sample.json"

# Service tag for every node this adapter writes. Teardown keys on it (plus the
# fixture corpus_ids) so cleanup is hermetic regardless of a per-run e2e tag.
SERVICE_TAG = "asta:theorizer"

# Every distinct corpus_id across supporting + contradicting papers in the
# fixture (normalized to digit-strings).
ALL_CORPUS_IDS = [
    "14681021",
    "206558487",
    "238223285",
    "260377246",
    "277674626",
    "9672349",
]

# The benchmark fields stamped on the run (from Task.metadata).
RUN_ID = "gen-20260615-01ccd779"
RUN_COST = 7.057
RUN_TIME = 1323.7

# Expected bucketing totals derived from the fixture.
N_THEORIES = 2
N_HYPOTHESES = 5  # 3 + 2 laws
N_PAPERS = 6  # distinct corpus_ids
N_SUPPORTS = 15  # SUPPORTS edges (papers per law, summed)
N_CONTRADICTS = 3  # theory-level CONTRADICTS edges


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


# ---------------------------------------------------------------------------
# 1. Defensive parse against the REAL shape
# ---------------------------------------------------------------------------


class TestParseTheorizerReal:
    def test_returns_records_and_run_meta(self):
        records, run_meta = parse_theorizer(_load_fixture())
        assert isinstance(run_meta, RunMeta)
        assert run_meta.run_id == RUN_ID
        assert run_meta.cost == pytest.approx(RUN_COST)
        assert run_meta.time == pytest.approx(RUN_TIME)

    def test_parses_two_theories(self):
        records, _ = parse_theorizer(_load_fixture())
        assert len(records) == N_THEORIES
        names = {r.name for r in records}
        assert any("Eligibility-Window Gain Theory" in n for n in names)
        assert any("Distributed Error Projection Theory" in n for n in names)

    def test_theory_name_and_description_promoted(self):
        records, _ = parse_theorizer(_load_fixture())
        for r in records:
            assert r.name  # SECTION/data name
            assert r.summary  # data.description

    def test_laws_are_section_titles(self):
        records, _ = parse_theorizer(_load_fixture())
        ewgt = next(r for r in records if "Eligibility-Window" in r.name)
        dept = next(r for r in records if "Distributed Error" in r.name)
        assert len(ewgt.laws) == 3
        assert len(dept.laws) == 2
        # Law statement is the SECTION title (real-shape law text).
        assert all(law.text for law in ewgt.laws)
        assert ewgt.laws[0].text.startswith("Multiplicative three-factor")

    def test_law_body_becomes_rationale(self):
        records, _ = parse_theorizer(_load_fixture())
        ewgt = next(r for r in records if "Eligibility-Window" in r.name)
        # The first MARKDOWN child (law body, before "Supporting evidence:")
        # becomes the rationale; the header text must NOT leak in.
        for law in ewgt.laws:
            assert law.rationale
            assert "supporting evidence" not in law.rationale.lower()

    def test_supporting_papers_via_annotations_to_entities(self):
        records, _ = parse_theorizer(_load_fixture())
        ewgt = next(r for r in records if "Eligibility-Window" in r.name)
        law0 = ewgt.laws[0]
        sup_ids = {p.corpus_id for p in law0.supporting}
        # corpus_id comes from entities[...].s2Metadata.corpusId, normalized.
        assert sup_ids  # non-empty
        assert all(cid.isdigit() for cid in sup_ids)
        # Every supporting paper resolves to a known fixture corpus_id.
        assert sup_ids <= set(ALL_CORPUS_IDS)

    def test_contradicting_papers_at_theory_level(self):
        records, _ = parse_theorizer(_load_fixture())
        ewgt = next(r for r in records if "Eligibility-Window" in r.name)
        # Papers annotated under "Conflicting & Unaccounted Evidence" are the
        # theory-level contradicting evidence.
        con_ids = {p.corpus_id for p in ewgt.contradicting}
        assert con_ids
        assert con_ids <= set(ALL_CORPUS_IDS)

    def test_novelty_joined_by_artifact_id(self):
        records, _ = parse_theorizer(_load_fixture())
        ewgt = next(r for r in records if "Eligibility-Window" in r.name)
        # novelty-theory-1-0/1 -> derivable, novelty-theory-1-2 -> established.
        verdicts = [law.novelty for law in ewgt.laws]
        assert verdicts == ["derivable", "derivable", "established"]

    def test_predictions_text_captured(self):
        records, _ = parse_theorizer(_load_fixture())
        ewgt = next(r for r in records if "Eligibility-Window" in r.name)
        assert ewgt.predictions  # Predictions SECTIONS flattened to text

    def test_theory_custom_counts(self):
        records, _ = parse_theorizer(_load_fixture())
        ewgt = next(r for r in records if "Eligibility-Window" in r.name)
        assert ewgt.custom["law_count"] == 3
        assert ewgt.custom.get("novelty_derivable_count") == 2
        assert ewgt.custom.get("novelty_established_count") == 1
        assert ewgt.custom.get("contradicting_count", 0) >= 1

    def test_corpus_ids_normalized_to_digit_strings(self):
        records, _ = parse_theorizer(_load_fixture())
        all_ids = set()
        for r in records:
            for law in r.laws:
                all_ids |= {p.corpus_id for p in law.supporting}
            all_ids |= {p.corpus_id for p in r.contradicting}
        assert all_ids == set(ALL_CORPUS_IDS)

    # --- shape drift / fallbacks ---

    def test_stringified_s2metadata_tolerated(self):
        # s2Metadata may arrive as a stringified Python dict; the parser must
        # still recover corpusId.
        doc = {
            "kind": "task",
            "metadata": {},
            "artifacts": [
                {
                    "artifactId": "theory-1",
                    "metadata": {"type": "theory"},
                    "parts": [
                        {
                            "kind": "data",
                            "data": {
                                "id": "theory-1",
                                "name": "T",
                                "description": "D",
                                "entities": {
                                    "paper-x": {
                                        "id": "paper-x",
                                        "type": "PAPER",
                                        "displayLabel": "Px",
                                        "s2Metadata": "{'corpusId': 4242, 'title': 'Px'}",
                                    }
                                },
                                "annotations": {
                                    "a1": {
                                        "id": "a1",
                                        "entityId": "paper-x",
                                        "type": "SNIPPET",
                                        "text": "",
                                    }
                                },
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
                                        "title": "The law",
                                        "childIds": ["c3", "c4"],
                                    },
                                    {
                                        "id": "c3",
                                        "type": "MARKDOWN",
                                        "text": "Body of the law.",
                                    },
                                    {
                                        "id": "c4",
                                        "type": "MARKDOWN",
                                        "text": "- bullet",
                                        "annotationIds": ["a1"],
                                    },
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        records, _ = parse_theorizer(doc)
        assert len(records) == 1
        law = records[0].laws[0]
        assert law.text == "The law"
        assert law.rationale == "Body of the law."
        assert [p.corpus_id for p in law.supporting] == ["4242"]

    def test_missing_novelty_tolerated(self):
        # A theory whose laws have no matching novelty artifact still parses;
        # the verdicts are just empty.
        doc = {
            "kind": "task",
            "artifacts": [
                {
                    "artifactId": "theory-9",
                    "metadata": {"type": "theory"},
                    "parts": [
                        {
                            "kind": "data",
                            "data": {
                                "name": "T9",
                                "description": "d",
                                "entities": {},
                                "annotations": {},
                                "content": [
                                    {
                                        "id": "s",
                                        "type": "SECTIONS",
                                        "title": "Theory Statements",
                                        "childIds": ["l"],
                                    },
                                    {
                                        "id": "l",
                                        "type": "SECTION",
                                        "title": "Lonely law",
                                        "childIds": [],
                                    },
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        records, _ = parse_theorizer(doc)
        assert len(records) == 1
        assert records[0].laws[0].novelty == ""

    def test_non_theory_artifacts_skipped(self):
        # extraction / novelty / theory_store artifacts are not mapped to theory
        # records in v1.
        records, _ = parse_theorizer(_load_fixture())
        # Only theory artifacts produce records; the fixture has 1 extraction +
        # several novelty artifacts that must not appear as theories.
        assert len(records) == N_THEORIES

    def test_defensive_on_garbage(self):
        assert parse_theorizer({}) == ([], RunMeta())
        assert parse_theorizer({"artifacts": "nope"})[0] == []
        assert parse_theorizer("not a dict")[0] == []  # type: ignore[arg-type]
        assert parse_theorizer(42)[0] == []  # type: ignore[arg-type]
        assert parse_theorizer({"artifacts": []})[0] == []

    def test_verdict_phrases_mapped(self):
        from wheeler.integrations.asta.theorizer import _verdict_from_description

        assert _verdict_from_description("Explicit Established. blah") == "established"
        assert _verdict_from_description("Derivable Unstated. blah") == "derivable"
        assert _verdict_from_description("Genuinely New. blah") == "new"
        assert _verdict_from_description("nonsense leading") == ""


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


def _cleanup_theorizer(e2e_config, e2e_tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged.

    The teardown is EXACTLY ``MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n``
    and nothing else. It NEVER deletes by ``service`` or by ``corpus_id``: the
    e2e config runs against the SHARED default Neo4j namespace (project_tag is
    empty), and production ingests carry the SAME ``asta:theorizer`` service tag
    and the same corpus_ids, so a service-scoped or corpus_id-scoped delete
    would wipe real user data. Every node this run creates is tagged with the
    per-run unique ``e2e_tag`` (a uuid) right after each ingest, scoped off the
    returned node ids (every Paper, the Execution, the artifact) plus the run's
    WAS_GENERATED_BY descendants, so this delete can only ever match nodes this
    run created. Papers are reference entities (no WAS_GENERATED_BY), so they are
    tagged by the returned ids, not via the fan-in.
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


class TestIngestTheorizerE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        # Run inside a temp cwd so the on-disk indices, the durable raw store,
        # and knowledge/synthesis writes land in an isolated sandbox we delete.
        # The persisted corpus_id/hyp/theory indices are therefore fresh per
        # test (relative paths under cwd), so created-vs-deduped counts are
        # hermetic and never depend on leftover cross-run state.
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        # Per-run unique e2e tag (not a shared constant), so this test's
        # teardown can never DETACH DELETE another test's nodes.
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        # Pre-clean any nodes a prior interrupted run left behind, so the
        # first-ingest counts start from a clean graph.
        _cleanup_theorizer(e2e_config, self._e2e_tag)
        yield
        _cleanup_theorizer(e2e_config, self._e2e_tag)

    async def _tag_all(self, e2e_config, report):
        """Tag exactly the nodes THIS run created with the per-run e2e tag.

        Scopes strictly off the ids the ImportReport returned (Execution,
        artifact, every Paper) plus the run's WAS_GENERATED_BY fan-in (every
        parent Finding, law Hypothesis, and the raw Document chain back to the run
        Execution), so teardown (which deletes ONLY by e2e_tag) can never touch a
        pre-existing production node that merely shares a service tag or a
        corpus_id. NEVER tag by service or corpus_id: the e2e config runs on the
        shared default namespace where production nodes carry the same
        asta:theorizer service and the same corpus_ids.

        Papers are REFERENCE ENTITIES: they no longer carry WAS_GENERATED_BY
        (per /wh:close, /wh:graph-link), so they are NOT in the Execution fan-in.
        They are tagged here by ``report.paper_ids`` instead, which keeps the
        teardown hermetic. (The Execution -[USED]-> evidence-paper edge does not
        matter for tagging: the paper ids are already covered by paper_ids.)
        """
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        # paper_ids is the ONLY thing that tags the papers now: they left the
        # WAS_GENERATED_BY fan-in when they became reference entities.
        run_ids = [i for i in (report.execution_id, report.artifact) if i]
        run_ids += [pid for pid in report.paper_ids if pid]
        async with driver.session(database=db) as s:
            if run_ids:
                await s.run(
                    "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                    ids=run_ids, tag=self._e2e_tag,
                )
            # Everything WAS_GENERATED_BY this run's Execution: now the parent
            # Findings, law Hypotheses, and the raw Document node (papers are
            # reference entities and excluded). Scoped off the Execution id this
            # run owns, never the shared service tag.
            if report.execution_id:
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                )

    @pytest.mark.asyncio
    async def test_ingest_buckets_and_is_idempotent(self, e2e_config):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.theorizer import ingest_theorizer
        from wheeler.tools.graph_tools import execute_tool

        doc = _load_fixture()

        # Write the raw fixture to a real file so the durable-store + Document
        # registration path runs end to end.
        artifact_path = self._tmp / "theorizer_raw.json"
        artifact_path.write_text(json.dumps(doc))

        # Seed a Question to link each theory parent AROSE_FROM.
        q_result = json.loads(
            await execute_tool(
                "add_question",
                {
                    "question": "E2E: what governs striatal learning rate?",
                    "priority": 5,
                },
                e2e_config,
            )
        )
        question_id = q_result["node_id"]
        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=question_id,
                tag=self._e2e_tag,
            )

        # --- First ingest ---
        report1 = await ingest_theorizer(
            doc,
            link_to=question_id,
            config=e2e_config,
            artifact_path=str(artifact_path),
        )
        await self._tag_all(e2e_config, report1)
        assert report1.execution_id.startswith("X-")
        run_exec_id = report1.execution_id
        tag = self._e2e_tag
        # parent Findings + Hypotheses + distinct Papers created.
        assert report1.created == N_THEORIES + N_HYPOTHESES + N_PAPERS

        # Parent Finding(artifact_type=theory) exists, one per theory. Scoped to
        # THIS run's e2e_tag (not the shared asta:theorizer service tag): the e2e
        # config runs on the shared default namespace, so a leaked node from a
        # prior interrupted run would otherwise inflate a by-service count and
        # cascade-fail the next run. Every node this run created carries the tag.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'}) "
                "WHERE f.e2e_tag = $tag RETURN count(f) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_THEORIES

        # Each parent CONTAINS its law Hypotheses (5 CONTAINS edges total).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})-[r:CONTAINS]->(h:Hypothesis) "
                "WHERE f.e2e_tag = $tag RETURN count(r) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_HYPOTHESES

        # SUPPORTS edges: Paper -> Hypothesis (per law).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper)-[r:SUPPORTS]->(h:Hypothesis) "
                "WHERE h.e2e_tag = $tag RETURN count(r) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_SUPPORTS

        # CONTRADICTS edges: Paper -> parent theory Finding (theory level).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper)-[r:CONTRADICTS]->(f:Finding {artifact_type: 'theory'}) "
                "WHERE f.e2e_tag = $tag RETURN count(r) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_CONTRADICTS

        # novelty parked in custom_novelty and queryable (NOT in status).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (h:Hypothesis) WHERE h.e2e_tag = $tag "
                "AND h.custom_novelty = 'established' RETURN count(h) AS c",
                tag=tag,
            )
            est_count = (await res.single())["c"]
            res = await s.run(
                "MATCH (h:Hypothesis) WHERE h.e2e_tag = $tag "
                "AND h.custom_novelty = 'derivable' RETURN count(h) AS c",
                tag=tag,
            )
            der_count = (await res.single())["c"]
            # status must stay on the open/supported/rejected enum, never novelty.
            res = await s.run(
                "MATCH (h:Hypothesis) WHERE h.e2e_tag = $tag "
                "RETURN collect(DISTINCT h.status) AS statuses",
                tag=tag,
            )
            statuses = (await res.single())["statuses"]
        assert est_count == 1  # one law has novelty="established"
        assert der_count == 4  # four laws have novelty="derivable"
        assert set(statuses) <= {"open"}
        assert "established" not in statuses
        assert "derivable" not in statuses

        # Verify the novelty landed on the RIGHT Hypothesis (the EWGT law 2).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (h:Hypothesis) WHERE h.e2e_tag = $tag "
                "AND h.custom_novelty = 'established' "
                "RETURN h.statement AS stmt LIMIT 1",
                tag=tag,
            )
            stmt = (await res.single())["stmt"]
        assert stmt.startswith("Biochemical gate & nonlinearity law")

        # The run Execution, exactly one, carrying benchmark fields. Scoped to
        # this run's Execution id (not the shared service tag) so a production
        # asta:theorizer Execution on the shared namespace cannot perturb it.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid}) "
                "RETURN count(x) AS c, collect(x.kind)[0] AS kind, "
                "collect(x.custom_run_id)[0] AS run_id, "
                "collect(x.custom_cost)[0] AS cost, "
                "collect(x.custom_time)[0] AS time",
                xid=run_exec_id,
            )
            rec = await res.single()
        assert rec["c"] == 1
        assert rec["kind"] == "theory-generation"
        assert rec["run_id"] == RUN_ID
        assert float(rec["cost"]) == pytest.approx(RUN_COST)
        assert float(rec["time"]) == pytest.approx(RUN_TIME)

        # Snapshot the WAS_GENERATED_BY fan-in to the Execution after the first
        # ingest. Re-ingest must NOT grow this (the Execution is idempotent and
        # link_once guards every provenance edge), so we re-check it below. Scoped
        # to this run's Execution id so the shared namespace cannot perturb it.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (n)-[r:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                "RETURN count(r) AS c",
                xid=run_exec_id,
            )
            gen_by_after_first = (await res.single())["c"]
        # The run Execution is WAS_GENERATED_BY the Wheeler-PRODUCED nodes only:
        # the parent theory Findings, the law Hypotheses, and the raw Document.
        # Papers are REFERENCE ENTITIES and are EXCLUDED from the fan-in (per
        # /wh:close, /wh:graph-link). N_PAPERS no longer counts here.
        assert gen_by_after_first == N_THEORIES + N_HYPOTHESES + 1

        # Papers carry NO WAS_GENERATED_BY: zero evidence papers in the fan-in.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper)-[r:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                "RETURN count(r) AS c",
                xid=run_exec_id,
            )
            assert (await res.single())["c"] == 0

        # Instead, the run Execution -[USED]-> each evidence Paper: the theories
        # were derived from the supporting/contradicting evidence, so each
        # distinct evidence paper is a genuine INPUT the run consumed. All
        # N_PAPERS papers in this fixture are evidence (theorizer papers come only
        # from law.supporting / theory.contradicting), and link_once collapses a
        # paper used by several laws to ONE USED edge, so the count is N_PAPERS.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(p:Paper) "
                "RETURN count(r) AS c",
                xid=run_exec_id,
            )
            assert (await res.single())["c"] == N_PAPERS
        # The USED targets are exactly the evidence papers (reachable both via
        # Execution-USED and via SUPPORTS/CONTRADICTS).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[:USED]->(p:Paper) "
                "WHERE p.corpus_id IN $cids RETURN count(DISTINCT p) AS c",
                xid=run_exec_id, cids=ALL_CORPUS_IDS,
            )
            assert (await res.single())["c"] == N_PAPERS

        # parent AROSE_FROM the seed Question.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})-[r:AROSE_FROM]->(q {id: $qid}) "
                "WHERE f.e2e_tag = $tag RETURN count(r) AS c",
                qid=question_id, tag=tag,
            )
            assert (await res.single())["c"] == N_THEORIES

        # Each Paper is distinct (6 corpus_ids -> 6 Paper nodes).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids "
                "RETURN count(DISTINCT p) AS c",
                cids=ALL_CORPUS_IDS,
            )
            assert (await res.single())["c"] == N_PAPERS

        # --- Raw output node is a Document (W-), points at the durable store,
        # carries benchmark fields, and is WAS_GENERATED_BY the Execution. ---
        assert report1.artifact.startswith("W-")  # Document, NOT Dataset
        from wheeler.graph.backend import get_backend

        backend = get_backend(e2e_config)
        raw_node = await backend.get_node("Document", report1.artifact)
        assert raw_node is not None
        # Path points into the durable raw store, NOT the ephemeral input path.
        assert ".wheeler/asta/raw/asta-theorizer" in raw_node["path"]
        assert Path(raw_node["path"]).exists()  # the saved file is reachable
        assert raw_node["service"] == "asta:theorizer"
        assert raw_node["custom"]["run_id"] == RUN_ID
        assert float(raw_node["custom"]["cost"]) == pytest.approx(RUN_COST)
        assert float(raw_node["custom"]["time"]) == pytest.approx(RUN_TIME)

        # raw Document WAS_GENERATED_BY the run Execution (scoped to this run's
        # Document id and Execution id, so the shared namespace cannot perturb it).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (w:Document {id: $wid})-[r:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                "RETURN count(r) AS c",
                wid=report1.artifact, xid=run_exec_id,
            )
            assert (await res.single())["c"] == 1

        # Each generated node WAS_DERIVED_FROM the raw Document.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (n)-[r:WAS_DERIVED_FROM]->(w:Document {id: $wid}) "
                "RETURN count(r) AS c",
                wid=report1.artifact,
            )
            derived = (await res.single())["c"]
        # parents + hypotheses + papers all chain back through the raw node.
        assert derived == N_THEORIES + N_HYPOTHESES + N_PAPERS

        # custom bag round-trips through the Pydantic model on read.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (h:Hypothesis) WHERE h.e2e_tag = $tag "
                "AND h.custom_novelty = 'established' RETURN h.id AS id LIMIT 1",
                tag=tag,
            )
            hyp_id = (await res.single())["id"]
        node = await backend.get_node("Hypothesis", hyp_id)
        assert node is not None
        assert node["custom"]["novelty"] == "established"
        assert node["custom"].get("rationale")  # law body became rationale
        assert node["status"] == "open"

        # --- Second ingest of the SAME artifact: idempotent ---
        report2 = await ingest_theorizer(
            doc,
            link_to=question_id,
            config=e2e_config,
            artifact_path=str(artifact_path),
        )
        await self._tag_all(e2e_config, report2)
        # Nothing new is created; every theory/law/paper is deduped.
        assert report2.created == 0
        assert report2.deduped == N_THEORIES + N_HYPOTHESES + N_PAPERS

        # Still exactly the same node counts (scoped to this run's e2e_tag /
        # Execution id so the shared default namespace cannot perturb them).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'}) "
                "WHERE f.e2e_tag = $tag RETURN count(f) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_THEORIES
            res = await s.run(
                "MATCH (h:Hypothesis) WHERE h.e2e_tag = $tag RETURN count(h) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_HYPOTHESES
            res = await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids "
                "RETURN count(DISTINCT p) AS c",
                cids=ALL_CORPUS_IDS,
            )
            assert (await res.single())["c"] == N_PAPERS
            # Still exactly one raw Document node (path-dedupe in the store).
            res = await s.run(
                "MATCH (w:Document {id: $wid}) RETURN count(w) AS c",
                wid=report1.artifact,
            )
            assert (await res.single())["c"] == 1

        # Edges are not duplicated by the second ingest (link_once).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})-[r:CONTAINS]->(h:Hypothesis) "
                "WHERE f.e2e_tag = $tag RETURN count(r) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_HYPOTHESES
            res = await s.run(
                "MATCH (p:Paper)-[r:SUPPORTS]->(h:Hypothesis) "
                "WHERE h.e2e_tag = $tag RETURN count(r) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_SUPPORTS
            res = await s.run(
                "MATCH (p:Paper)-[r:CONTRADICTS]->(f:Finding {artifact_type: 'theory'}) "
                "WHERE f.e2e_tag = $tag RETURN count(r) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_CONTRADICTS
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})-[r:AROSE_FROM]->(q {id: $qid}) "
                "WHERE f.e2e_tag = $tag RETURN count(r) AS c",
                qid=question_id, tag=tag,
            )
            assert (await res.single())["c"] == N_THEORIES

        # --- Execution provenance is idempotent across re-ingest ---
        # Re-ingesting the SAME artifact must NOT create a second Execution node,
        # and must NOT accumulate extra WAS_GENERATED_BY edges. (Regression:
        # add_execution was previously called unconditionally, so a re-ingest
        # duplicated the Execution and its provenance fan-in.) Scoped to this
        # run's Execution id so the shared namespace cannot perturb the counts.
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
            # The Execution -[USED]-> evidence-paper edges are also link_once
            # guarded, so re-ingest must NOT grow them: still exactly N_PAPERS.
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(p:Paper) "
                "RETURN count(r) AS c",
                xid=run_exec_id,
            )
            assert (await res.single())["c"] == N_PAPERS
        # The report points at the same Execution both runs (reused, not new).
        assert report2.execution_id == report1.execution_id

    @pytest.mark.asyncio
    async def test_used_inputs_record_input_provenance(self, e2e_config):
        """Input-side provenance: Execution -[USED]-> the marshalled-in inputs.

        On TOP of the per-evidence-paper USED edges, seed an OpenQuestion + a
        Finding (the prose-consulted inputs, e.g. the Finding ids seeded into
        extraction_results) and pass them as used_inputs with a fabricated
        missing id. Assert:
          - Execution -[USED]-> each existing seeded input exactly once,
          - the missing id is skipped (no error, no edge, no fabricated node),
          - link_once collapses overlap (no extra USED to the evidence papers),
          - re-ingest does NOT duplicate the USED edges,
          - the full chain is queryable: a produced node (a parent theory
            Finding) -[WAS_GENERATED_BY]-> Execution -[USED]-> the seeded input.
        """
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.theorizer import ingest_theorizer
        from wheeler.tools.graph_tools import execute_tool

        doc = _load_fixture()
        artifact_path = self._tmp / "theorizer_used_raw.json"
        artifact_path.write_text(json.dumps(doc))
        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Seed two real graph inputs the marshal-in would have consumed (the
        # question that motivated the run + a Finding seeded into extraction).
        q_result = json.loads(await execute_tool(
            "add_question",
            {"question": "E2E USED th: what governs the rate?", "priority": 5},
            e2e_config,
        ))
        question_id = q_result["node_id"]
        f_result = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E USED th: seeded extraction result", "confidence": 0.8},
            e2e_config,
        ))
        finding_id = f_result["node_id"]
        missing_id = "Q-doesnotexist99"

        # Tag the seeded inputs too so teardown stays hermetic.
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                ids=[question_id, finding_id], tag=self._e2e_tag,
            )

        used = [question_id, finding_id, missing_id]

        report1 = await ingest_theorizer(
            doc,
            link_to=question_id,
            config=e2e_config,
            artifact_path=str(artifact_path),
            used_inputs=used,
        )
        await self._tag_all(e2e_config, report1)
        exec_id = report1.execution_id
        # Only the two existing seeded ids are linked by _record_used; the
        # missing id is skipped. (The evidence-paper USED edges are counted in
        # report.linked, not report.used.)
        assert report1.used == 2

        # Execution -[USED]-> each EXISTING seeded input exactly once.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(n) "
                "WHERE n.id IN $ids RETURN n.id AS id, count(r) AS c",
                xid=exec_id, ids=[question_id, finding_id],
            )
            rows = {r["id"]: r["c"] async for r in res}
        assert rows == {question_id: 1, finding_id: 1}

        # The missing id has NO USED edge and was NOT fabricated.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(n {id: $mid}) "
                "RETURN count(r) AS c",
                xid=exec_id, mid=missing_id,
            )
            assert (await res.single())["c"] == 0
            res = await s.run(
                "MATCH (n {id: $mid}) RETURN count(n) AS c", mid=missing_id,
            )
            assert (await res.single())["c"] == 0

        # The evidence-paper USED edges are untouched (link_once collapses any
        # overlap; the seeded inputs are not papers, so still exactly N_PAPERS).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(p:Paper) "
                "RETURN count(r) AS c",
                xid=exec_id,
            )
            assert (await res.single())["c"] == N_PAPERS

        # The full chain is queryable: a produced parent theory Finding
        # -[WAS_GENERATED_BY]-> Execution -[USED]-> the seeded input.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'theory'})"
                "-[:WAS_GENERATED_BY]->(x:Execution {id: $xid})-[:USED]->(n) "
                "WHERE n.id IN $ids RETURN count(DISTINCT n) AS c",
                xid=exec_id, ids=[question_id, finding_id],
            )
            assert (await res.single())["c"] == 2

        # Re-ingest of the SAME artifact + used_inputs: USED edges not duplicated.
        report2 = await ingest_theorizer(
            doc,
            link_to=question_id,
            config=e2e_config,
            artifact_path=str(artifact_path),
            used_inputs=used,
        )
        await self._tag_all(e2e_config, report2)
        assert report2.execution_id == exec_id
        assert report2.used == 0
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(n) "
                "WHERE n.id IN $ids RETURN count(r) AS c",
                xid=exec_id, ids=[question_id, finding_id],
            )
            assert (await res.single())["c"] == 2

        # --- Direct overlap path: a used_input that is ALSO an evidence paper ---
        # _ingest_paper_edge already created Execution -[USED]-> each evidence
        # paper. Passing one of those P-ids back as a used_input must collapse via
        # link_once: _record_used sees the edge already exists, so report.used
        # counts it as NOT newly linked (0), and the total USED-to-Paper count
        # does not grow. This exercises the overlap branch directly (the seeded
        # Question/Finding above are non-papers, so they never hit it).
        assert report1.paper_ids, "fixture should have at least one evidence paper"
        evidence_paper_id = report1.paper_ids[0]
        report3 = await ingest_theorizer(
            doc,
            link_to=question_id,
            config=e2e_config,
            artifact_path=str(artifact_path),
            used_inputs=[evidence_paper_id],
        )
        await self._tag_all(e2e_config, report3)
        assert report3.execution_id == exec_id
        # The evidence paper was already USED by _ingest_paper_edge, so the
        # explicit used_input adds NO new USED edge (link_once collapse).
        assert report3.used == 0
        async with driver.session(database=db) as s:
            # That paper still has exactly one USED edge from the Execution.
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(p:Paper {id: $pid}) "
                "RETURN count(r) AS c",
                xid=exec_id, pid=evidence_paper_id,
            )
            assert (await res.single())["c"] == 1
            # And the total Execution-USED-Paper fan-out is unchanged (N_PAPERS).
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(p:Paper) "
                "RETURN count(r) AS c",
                xid=exec_id,
            )
            assert (await res.single())["c"] == N_PAPERS
