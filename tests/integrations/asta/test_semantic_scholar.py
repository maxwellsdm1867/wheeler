"""Tests for the Asta Semantic Scholar vertical slice (REAL S2 REST shapes).

Two layers, neither making a live asta/S2 call:
  1. parse_semantic_scholar: auto-detect + parse the four trimmed REAL fixtures
     (get / search / citations / snippet) plus shape-drift / garbage tolerance
     (defensive, never raises, corpusId-vs-fallback handling).
  2. live-Neo4j e2e: ingest the citations fixture with a target and assert the
     CITES edges + Paper dedupe; ingest the snippet fixture and assert the
     snippet Findings + APPEARS_IN edges; idempotent re-ingest; the raw Dataset
     node points at the durable .wheeler/asta/raw store.

Run: python -m pytest tests/integrations/asta/test_semantic_scholar.py -q
The e2e class is skipped automatically when Neo4j is not reachable.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from wheeler.integrations.asta.semantic_scholar import (
    S2Parsed,
    parse_semantic_scholar,
)

FIX = Path(__file__).parent / "fixtures"
GET_FIXTURE = FIX / "s2_get.json"
SEARCH_FIXTURE = FIX / "s2_search.json"
CITATIONS_FIXTURE = FIX / "s2_citations.json"
SNIPPET_FIXTURE = FIX / "s2_snippet.json"

# Service tag for every node this adapter writes. Teardown keys on it (plus the
# fixture corpus_ids) so cleanup is hermetic regardless of a per-run e2e tag.
SERVICE_TAG = "asta:semantic-scholar"

# corpus_ids in the citations fixture (citingPaper.corpusId, digit strings).
CITATION_CORPUS_IDS = ["401234001", "401234002", "401234003"]
# corpus_ids in the snippet fixture (paper.corpusId; one repeats across two hits).
SNIPPET_CORPUS_IDS = ["203658198", "12580360"]
# corpus_ids in the get + search fixtures.
GET_CORPUS_ID = "210116405"
SEARCH_CORPUS_IDS = ["301234001", "301234002", "301234003"]

# The cited target paper for the citations e2e (a corpus_id, NOT in the output).
TARGET_CORPUS_ID = "210116405"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# 1. Auto-detect + defensive parse against the REAL shapes
# ---------------------------------------------------------------------------


class TestAutoDetectSubKind:
    def test_detects_get(self):
        parsed = parse_semantic_scholar(_load(GET_FIXTURE))
        assert parsed.sub_kind == "get"
        assert len(parsed.papers) == 1

    def test_detects_search(self):
        parsed = parse_semantic_scholar(_load(SEARCH_FIXTURE))
        assert parsed.sub_kind == "search"
        assert len(parsed.papers) == 3

    def test_detects_citations(self):
        parsed = parse_semantic_scholar(_load(CITATIONS_FIXTURE))
        assert parsed.sub_kind == "citations"
        assert len(parsed.citations) == 3

    def test_detects_snippet(self):
        parsed = parse_semantic_scholar(_load(SNIPPET_FIXTURE))
        assert parsed.sub_kind == "snippet"
        assert len(parsed.snippets) == 3


class TestParseGet:
    def test_corpus_id_from_top_level_when_requested(self):
        # corpusId is present because the act requested --fields corpusId.
        parsed = parse_semantic_scholar(_load(GET_FIXTURE))
        paper = parsed.papers[0]
        assert paper.corpus_id == GET_CORPUS_ID
        assert paper.title.startswith("Causal evidence")
        assert paper.year == 2020
        assert "Maes" in paper.authors

    def test_s2_ids_and_oa_parked_in_custom(self):
        parsed = parse_semantic_scholar(_load(GET_FIXTURE))
        paper = parsed.papers[0]
        assert paper.custom["s2_paper_id"] == "30ec6a4886a349d71bdc372917a6c48d85271f16"
        assert paper.custom["doi"] == "10.1038/s41593-019-0574-1"
        assert paper.custom["venue"] == "Nature Neuroscience"
        assert paper.custom["citation_count"] == 72
        assert "open_access_pdf" in paper.custom

    def test_corpus_id_absent_falls_back_to_paper_id(self):
        # The DEFAULT S2 field set omits corpusId entirely; dedupe must fall
        # back to the s2 paperId (or DOI) so a paper is still ingestable.
        doc = {
            "paperId": "abc123",
            "title": "No corpus id paper",
            "year": 2020,
            "authors": [{"name": "X"}],
        }
        parsed = parse_semantic_scholar(doc)
        assert parsed.sub_kind == "get"
        paper = parsed.papers[0]
        assert paper.corpus_id == ""
        assert paper.fallback_key == "abc123"
        assert paper.custom["s2_paper_id"] == "abc123"

    def test_corpus_id_from_external_ids(self):
        # When the caller requests --fields externalIds (not corpusId directly),
        # corpus_id is recovered from externalIds.CorpusId.
        doc = {
            "paperId": "p1",
            "title": "T",
            "externalIds": {"CorpusId": 555, "DOI": "10.x/y"},
        }
        parsed = parse_semantic_scholar(doc)
        assert parsed.papers[0].corpus_id == "555"
        assert parsed.papers[0].custom["doi"] == "10.x/y"


class TestParseSearch:
    def test_promotes_fields_and_corpus_ids(self):
        parsed = parse_semantic_scholar(_load(SEARCH_FIXTURE))
        cids = {p.corpus_id for p in parsed.papers}
        assert cids == set(SEARCH_CORPUS_IDS)
        first = parsed.papers[0]
        assert first.title.startswith("Dopamine reward prediction-error")
        assert first.custom["citation_count"] == 808


class TestParseCitations:
    def test_citing_papers_normalized(self):
        parsed = parse_semantic_scholar(_load(CITATIONS_FIXTURE))
        cids = {c.citing.corpus_id for c in parsed.citations}
        assert cids == set(CITATION_CORPUS_IDS)
        # Each citing paper promotes title/year/authors.
        for c in parsed.citations:
            assert c.citing.title
            assert c.citing.year >= 2025

    def test_target_is_not_in_the_output(self):
        # The cited (target) paper is the CLI argument, NOT in the artifact.
        doc = _load(CITATIONS_FIXTURE)
        # No top-level paperId / no entry carrying the target corpus id.
        assert "paperId" not in doc
        assert all(
            c.citing.corpus_id != TARGET_CORPUS_ID
            for c in parse_semantic_scholar(doc).citations
        )


class TestParseSnippet:
    def test_snippet_carries_corpus_id_and_text(self):
        parsed = parse_semantic_scholar(_load(SNIPPET_FIXTURE))
        for snip in parsed.snippets:
            assert snip.paper.corpus_id  # snippet-search DOES include corpusId
            assert snip.text
            assert 0.0 <= snip.score <= 1.0
        # corpus_id 12580360 appears in two snippet hits.
        cids = [s.paper.corpus_id for s in parsed.snippets]
        assert cids.count("12580360") == 2

    def test_snippet_kind_captured(self):
        parsed = parse_semantic_scholar(_load(SNIPPET_FIXTURE))
        kinds = {s.kind for s in parsed.snippets}
        assert kinds == {"body", "abstract"}


class TestDefensive:
    def test_garbage_returns_unknown(self):
        assert parse_semantic_scholar({}).sub_kind == "unknown"
        assert parse_semantic_scholar("nope").sub_kind == "unknown"  # type: ignore[arg-type]
        assert parse_semantic_scholar(42).sub_kind == "unknown"  # type: ignore[arg-type]
        assert isinstance(parse_semantic_scholar(None), S2Parsed)  # type: ignore[arg-type]

    def test_empty_data_list_tolerated(self):
        parsed = parse_semantic_scholar({"total": 0, "data": []})
        assert parsed.sub_kind == "search"
        assert parsed.papers == []

    def test_malformed_citation_entries_skipped(self):
        doc = {
            "data": [
                {"citingPaper": {"corpusId": 7, "title": "ok"}},
                {"citingPaper": "not a dict"},
                "garbage",
                {"noCitingPaper": True},
            ]
        }
        parsed = parse_semantic_scholar(doc)
        assert parsed.sub_kind == "citations"
        assert len(parsed.citations) == 1
        assert parsed.citations[0].citing.corpus_id == "7"

    def test_citations_detected_when_first_entry_citing_paper_null(self):
        # A real S2 shape: a withheld citing record arrives as citingPaper:null.
        # Detection must NOT trust data[0] alone (which would misclassify the
        # whole response as a plain search and silently drop every CITES edge);
        # it scans for ANY entry carrying the citingPaper key. The null entry is
        # tolerated per-entry (skip-and-count), so the real citing papers parse.
        doc = _load(CITATIONS_FIXTURE)
        doc["data"].insert(0, {"citingPaper": None})
        parsed = parse_semantic_scholar(doc)
        assert parsed.sub_kind == "citations"
        # The 3 real citing papers survive; the null entry is skipped.
        assert len(parsed.citations) == len(CITATION_CORPUS_IDS)
        cids = {c.citing.corpus_id for c in parsed.citations}
        assert cids == set(CITATION_CORPUS_IDS)

    def test_citations_detected_when_first_entry_citing_paper_missing(self):
        # An entry that carries no citingPaper key at all must not flip detection
        # away from citations when a later entry has one.
        doc = {
            "data": [
                {"someOtherKey": 1},
                {"citingPaper": {"corpusId": 9, "title": "ok"}},
            ]
        }
        parsed = parse_semantic_scholar(doc)
        assert parsed.sub_kind == "citations"
        assert len(parsed.citations) == 1
        assert parsed.citations[0].citing.corpus_id == "9"

    def test_snippet_without_text_or_paper_skipped(self):
        doc = {
            "retrievalVersion": "v1",
            "data": [
                {"snippet": {"text": "", "snippetKind": "body"}, "paper": {"corpusId": 1}},
                {"snippet": {"snippetKind": "body"}, "paper": {"corpusId": 2}},
                {"snippet": {"text": "good", "snippetKind": "abstract"}, "paper": {"corpusId": 3, "title": "T"}},
            ],
        }
        parsed = parse_semantic_scholar(doc)
        assert parsed.sub_kind == "snippet"
        assert len(parsed.snippets) == 1
        assert parsed.snippets[0].paper.corpus_id == "3"


# ---------------------------------------------------------------------------
# 2. Live-Neo4j e2e
# ---------------------------------------------------------------------------


ALL_E2E_CORPUS_IDS = (
    CITATION_CORPUS_IDS + SNIPPET_CORPUS_IDS + [TARGET_CORPUS_ID]
)


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
    """Hermetic teardown: delete every node this adapter could have created.

    Crash-safe and independent of any post-success tagging step: it keys on the
    SERVICE_TAG (set at node creation), on the fixture corpus_ids (papers may
    pre-exist from another run, including the cited target), and on the per-run
    e2e tag (the seed nodes). Deleting on the shared service tag is safe because
    the e2e config uses a dedicated project and no production node carries this
    synthetic service.
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
                    "MATCH (n) WHERE n.service = $svc DETACH DELETE n",
                    svc=SERVICE_TAG,
                )
                await s.run(
                    "MATCH (p:Paper) WHERE p.corpus_id IN $cids DETACH DELETE p",
                    cids=ALL_E2E_CORPUS_IDS,
                )
                await s.run(
                    "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
                    tag=e2e_tag,
                )
        finally:
            await driver.close()

    asyncio.run(_run())


class TestIngestSemanticScholarE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        # Run inside a temp cwd so the on-disk indices, the durable raw store,
        # and knowledge/synthesis writes land in an isolated sandbox we delete.
        # The persisted corpus_id/snippet indices are therefore fresh per test
        # (relative paths under cwd), so created-vs-deduped counts are hermetic.
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        # Per-run unique e2e tag, so this test's teardown can never DETACH
        # DELETE another test's nodes.
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        _cleanup(e2e_config, self._e2e_tag)
        yield
        _cleanup(e2e_config, self._e2e_tag)

    async def _tag_all(self, e2e_config):
        """Tag every node this run touched with the per-run e2e tag.

        Belt-and-braces only: teardown already deletes on the service tag and
        corpus_ids unconditionally, so a crash before this call still cleans up.
        """
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n) WHERE n.service = $svc SET n.e2e_tag = $tag",
                svc=SERVICE_TAG,
                tag=self._e2e_tag,
            )
            await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids SET p.e2e_tag = $tag",
                cids=ALL_E2E_CORPUS_IDS,
                tag=self._e2e_tag,
            )

    @pytest.mark.asyncio
    async def test_citations_builds_cites_graph_and_is_idempotent(self, e2e_config):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.semantic_scholar import (
            ingest_semantic_scholar,
        )
        from wheeler.tools.graph_tools import execute_tool

        doc = _load(CITATIONS_FIXTURE)
        artifact_path = self._tmp / "s2_citations_raw.json"
        artifact_path.write_text(json.dumps(doc))

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # Pre-create the cited target Paper (the CLI argument). The adapter
        # resolves the --target corpus_id to this Paper for the CITES edges.
        tgt_result = json.loads(
            await execute_tool(
                "add_paper",
                {
                    "title": "Target: dopamine TD prediction errors",
                    "corpus_id": TARGET_CORPUS_ID,
                    "service": SERVICE_TAG,
                },
                e2e_config,
            )
        )
        target_paper_id = tgt_result["node_id"]
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=target_paper_id,
                tag=self._e2e_tag,
            )

        # --- First ingest of the citations artifact, with the target ---
        report1 = await ingest_semantic_scholar(
            doc,
            target=TARGET_CORPUS_ID,
            config=e2e_config,
            artifact_path=str(artifact_path),
        )
        await self._tag_all(e2e_config)
        assert report1.execution_id.startswith("X-")
        # 3 distinct citing papers created (target pre-existed).
        assert report1.created == len(CITATION_CORPUS_IDS)

        # CITES edges: each citing Paper -[CITES]-> the target Paper.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper)-[r:CITES]->(t:Paper {corpus_id: $tcid}) "
                "RETURN count(r) AS c",
                tcid=TARGET_CORPUS_ID,
            )
            assert (await res.single())["c"] == len(CITATION_CORPUS_IDS)

        # One Paper per citing corpus_id.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids "
                "RETURN count(DISTINCT p) AS c",
                cids=CITATION_CORPUS_IDS,
            )
            assert (await res.single())["c"] == len(CITATION_CORPUS_IDS)

        # Each citing Paper WAS_GENERATED_BY the run Execution.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper)-[r:WAS_GENERATED_BY]->(x:Execution {service: $svc}) "
                "WHERE p.corpus_id IN $cids RETURN count(r) AS c",
                svc=SERVICE_TAG,
                cids=CITATION_CORPUS_IDS,
            )
            assert (await res.single())["c"] == len(CITATION_CORPUS_IDS)

        # The Execution kind reflects the sub-shape.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {service: $svc}) "
                "RETURN count(x) AS c, collect(x.kind)[0] AS kind",
                svc=SERVICE_TAG,
            )
            rec = await res.single()
        assert rec["c"] == 1
        assert rec["kind"] == "s2-citations"

        # --- Raw output node is a Dataset (D-), points at the durable store. ---
        assert report1.artifact.startswith("D-")
        from wheeler.graph.backend import get_backend

        backend = get_backend(e2e_config)
        raw_node = await backend.get_node("Dataset", report1.artifact)
        assert raw_node is not None
        assert ".wheeler/asta/raw/asta-semantic-scholar" in raw_node["path"]
        assert Path(raw_node["path"]).exists()
        assert raw_node["service"] == SERVICE_TAG

        # --- Second ingest of the SAME artifact: idempotent ---
        report2 = await ingest_semantic_scholar(
            doc,
            target=TARGET_CORPUS_ID,
            config=e2e_config,
            artifact_path=str(artifact_path),
        )
        await self._tag_all(e2e_config)
        assert report2.created == 0
        assert report2.deduped == len(CITATION_CORPUS_IDS)
        assert report2.execution_id == report1.execution_id

        # CITES edges not duplicated (link_once).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper)-[r:CITES]->(t:Paper {corpus_id: $tcid}) "
                "RETURN count(r) AS c",
                tcid=TARGET_CORPUS_ID,
            )
            assert (await res.single())["c"] == len(CITATION_CORPUS_IDS)

        # Still exactly one Execution and one raw Dataset.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (x:Execution {service: $svc}) RETURN count(x) AS c",
                svc=SERVICE_TAG,
            )
            assert (await res.single())["c"] == 1
            res = await s.run(
                "MATCH (d:Dataset {service: $svc}) RETURN count(d) AS c",
                svc=SERVICE_TAG,
            )
            assert (await res.single())["c"] == 1

    @pytest.mark.asyncio
    async def test_snippets_create_findings_and_appears_in(self, e2e_config):
        from wheeler.graph.backend import get_backend
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.semantic_scholar import (
            ingest_semantic_scholar,
        )

        doc = _load(SNIPPET_FIXTURE)
        artifact_path = self._tmp / "s2_snippet_raw.json"
        artifact_path.write_text(json.dumps(doc))

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        # --- First ingest of the snippet artifact ---
        report1 = await ingest_semantic_scholar(
            doc, config=e2e_config, artifact_path=str(artifact_path)
        )
        await self._tag_all(e2e_config)
        # 2 distinct papers + 3 snippet Findings created (one paper repeats).
        assert report1.created == len(SNIPPET_CORPUS_IDS) + 3

        # 3 snippet Findings, all artifact_type=snippet, service-tagged.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'snippet', service: $svc}) "
                "RETURN count(f) AS c",
                svc=SERVICE_TAG,
            )
            assert (await res.single())["c"] == 3

        # Each snippet Finding -[APPEARS_IN]-> a Paper (3 edges).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'snippet'})-[r:APPEARS_IN]->(p:Paper) "
                "WHERE f.service = $svc RETURN count(r) AS c",
                svc=SERVICE_TAG,
            )
            assert (await res.single())["c"] == 3

        # snippet_kind parked in custom and queryable.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'snippet', service: $svc}) "
                "WHERE f.custom_snippet_kind = 'abstract' RETURN count(f) AS c",
                svc=SERVICE_TAG,
            )
            assert (await res.single())["c"] == 1

        # The Finding confidence is the S2 score, round-tripped through the model.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'snippet', service: $svc}) "
                "RETURN f.id AS id, f.confidence AS conf ORDER BY f.confidence DESC "
                "LIMIT 1",
                svc=SERVICE_TAG,
            )
            rec = await res.single()
        assert rec["conf"] == pytest.approx(0.8415397355260673, abs=1e-6)
        backend = get_backend(e2e_config)
        node = await backend.get_node("Finding", rec["id"])
        assert node is not None
        # The snippet lands in artifact_type, NOT a status field (FindingModel
        # has no status field). Assert the real contract.
        assert node["artifact_type"] == "snippet"
        assert node.get("status") != "snippet"

        # One Paper per snippet corpus_id (the repeated paper deduped).
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper) WHERE p.corpus_id IN $cids "
                "RETURN count(DISTINCT p) AS c",
                cids=SNIPPET_CORPUS_IDS,
            )
            assert (await res.single())["c"] == len(SNIPPET_CORPUS_IDS)

        # --- Second ingest of the SAME artifact: idempotent ---
        report2 = await ingest_semantic_scholar(
            doc, config=e2e_config, artifact_path=str(artifact_path)
        )
        await self._tag_all(e2e_config)
        assert report2.created == 0
        # 2 papers + 3 snippet Findings all deduped.
        assert report2.deduped == len(SNIPPET_CORPUS_IDS) + 3
        assert report2.execution_id == report1.execution_id

        # Findings not duplicated.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'snippet', service: $svc}) "
                "RETURN count(f) AS c",
                svc=SERVICE_TAG,
            )
            assert (await res.single())["c"] == 3
            # APPEARS_IN not duplicated.
            res = await s.run(
                "MATCH (f:Finding {artifact_type: 'snippet'})-[r:APPEARS_IN]->(p:Paper) "
                "WHERE f.service = $svc RETURN count(r) AS c",
                svc=SERVICE_TAG,
            )
            assert (await res.single())["c"] == 3

    @pytest.mark.asyncio
    async def test_corpus_id_less_paper_dedupes_across_runs(self, e2e_config):
        # A get/search artifact whose paper has NO corpusId (the DEFAULT S2 field
        # set omits it) must still dedupe on re-ingest, via the s2 paperId / DOI
        # fallback (persisted index + a graph read on custom_s2_paper_id). It
        # MUST NOT fork a second Paper node for the same paperId.
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.semantic_scholar import (
            ingest_semantic_scholar,
        )

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database

        s2_paper_id = "deadbeefdeadbeefdeadbeefdeadbeef00000001"
        doc = {
            "paperId": s2_paper_id,
            "title": "Corpus-id-less default-field get",
            "year": 2021,
            "authors": [{"name": "A. Nonymous"}],
        }
        artifact_path = self._tmp / "s2_get_no_corpusid_raw.json"
        artifact_path.write_text(json.dumps(doc))

        report1 = await ingest_semantic_scholar(
            doc, config=e2e_config, artifact_path=str(artifact_path)
        )
        await self._tag_all(e2e_config)
        # Belt-and-braces: tag by the parked s2 paperId too, so teardown reaches
        # this node even though it has no corpus_id.
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (p:Paper {custom_s2_paper_id: $sid}) SET p.e2e_tag = $tag",
                sid=s2_paper_id,
                tag=self._e2e_tag,
            )
        assert report1.created == 1
        assert report1.deduped == 0

        report2 = await ingest_semantic_scholar(
            doc, config=e2e_config, artifact_path=str(artifact_path)
        )
        await self._tag_all(e2e_config)
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (p:Paper {custom_s2_paper_id: $sid}) SET p.e2e_tag = $tag",
                sid=s2_paper_id,
                tag=self._e2e_tag,
            )
        # Re-ingest: NO new Paper, the existing one reused.
        assert report2.created == 0
        assert report2.deduped == 1

        # Exactly ONE Paper node for this paperId.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper {custom_s2_paper_id: $sid}) "
                "RETURN count(p) AS c",
                sid=s2_paper_id,
            )
            assert (await res.single())["c"] == 1
