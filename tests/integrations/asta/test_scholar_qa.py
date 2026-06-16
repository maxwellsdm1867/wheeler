"""Tests for the Asta Literature Reports (scholar-qa) adapter.

Two layers, NEITHER making a live scholar-qa call:
  1. parse_scholar_qa: parse a REAL report fixture (markdown with the skill's
     [[Key]] / [Key]: <url> citation convention) plus a real find-results JSON
     for the corpus_id enrichment join, plus shape-drift / garbage tolerance
     (never raises).
  2. live-Neo4j e2e: ingest a report with RUN-UNIQUE synthetic corpus_ids,
     assert the bucketing subgraph (one report Document WAS_GENERATED_BY the run
     Execution, each cited Paper CITES-from-doc + USED-by-run, papers carry NO
     WAS_GENERATED_BY), then re-ingest the SAME report and assert idempotency.
     Skipped automatically when Neo4j is not reachable.

The e2e deliberately does NOT reuse the real fixture's corpus_ids: the e2e config
runs on the SHARED default Neo4j namespace, the parse fixture cites real dopamine
papers, and the user's own research graph is about dopamine, so a real corpus_id
could DEDUPE to a pre-existing production Paper which _tag_all would then tag and
the teardown would DETACH DELETE (data loss). Run-unique synthetic corpus_ids
make every e2e Paper brand-new, so created counts are deterministic and teardown
can only ever touch this run's nodes.

Run: python -m pytest tests/integrations/asta/test_scholar_qa.py -q
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from wheeler.integrations.asta.scholar_qa import (
    ReportRecord,
    RunMeta,
    parse_scholar_qa,
)

# Trimmed REAL report: a markdown literature review citing five real dopamine /
# reward-prediction-error papers, using the skill's citation convention
# ([[Key]] inline + references, [Key]: <url> link definitions).
FIXTURE = Path(__file__).parent / "fixtures" / "scholar_qa_real_sample.md"
# Trimmed REAL LiteratureSearchResult: three of the five cited papers, for the
# corpus_id enrichment join (the other two exercise the text-fallback path).
FIND_FIXTURE = Path(__file__).parent / "fixtures" / "scholar_qa_find_sample.json"
SERVICE_TAG = "asta:scholar-qa"

# Every corpus_id cited in the report fixture (normalized to digit-strings).
ALL_CORPUS_IDS = ["91676903", "260988593", "53024913", "220093382", "15402417"]
# The three corpus_ids present in the find-results fixture (enriched).
ENRICHED_CORPUS_IDS = {"91676903", "260988593", "53024913"}
N_PAPERS = 5


def _load_report() -> str:
    return FIXTURE.read_text()


def _load_find() -> dict:
    return json.loads(FIND_FIXTURE.read_text())


# ---------------------------------------------------------------------------
# 1. Defensive parse against the REAL markdown shape
# ---------------------------------------------------------------------------


class TestParseScholarQa:
    def test_returns_record_and_run_meta(self):
        record, run_meta = parse_scholar_qa(_load_report(), _load_find())
        assert isinstance(record, ReportRecord)
        assert isinstance(run_meta, RunMeta)
        assert record.title.startswith("Dopamine and Reward Prediction Error")
        assert record.query == "dopamine reward prediction error"  # from find

    def test_cites_every_referenced_paper_once(self):
        record, _ = parse_scholar_qa(_load_report(), _load_find())
        assert len(record.papers) == N_PAPERS
        cids = {p.corpus_id for p in record.papers}
        assert cids == set(ALL_CORPUS_IDS)

    def test_corpus_ids_extracted_from_all_url_shapes(self):
        # The fixture uses /p/<id>, www./p/<id>, and api...CorpusId:<id> urls.
        record, _ = parse_scholar_qa(_load_report(), _load_find())
        by_key = {p.custom["citation_key"]: p for p in record.papers}
        assert by_key["Maes2020"].corpus_id == "91676903"  # /p/
        assert by_key["Coddington2018"].corpus_id == "53024913"  # www./p/
        assert by_key["Deng2023"].corpus_id == "260988593"  # CorpusId:

    def test_enriched_papers_get_find_metadata(self):
        record, _ = parse_scholar_qa(_load_report(), _load_find())
        by_cid = {p.corpus_id: p for p in record.papers}
        maes = by_cid["91676903"]
        assert maes.year == 2020
        assert "Maes" in maes.authors  # authors lifted from find-results
        assert maes.custom.get("venue") == "Nature Neuroscience"
        assert maes.custom.get("citation_count") == 142

    def test_unenriched_papers_fall_back_to_citation_text(self):
        # Schultz1997 and Cooper2011 are NOT in the find-results fixture, so their
        # metadata comes from the citation text (year from parens, title parsed).
        record, _ = parse_scholar_qa(_load_report(), _load_find())
        by_cid = {p.corpus_id: p for p in record.papers}
        schultz = by_cid["220093382"]
        assert schultz.year == 1997
        assert schultz.authors == ""  # no find-results enrichment
        assert "Neural Substrate of Prediction and Reward" in schultz.title

    def test_dedupes_inline_and_reference_mentions(self):
        # Every key is mentioned inline AND in the References list; each must
        # resolve to ONE paper, with the longer (references) text winning.
        record, _ = parse_scholar_qa(_load_report(), _load_find())
        keys = [p.custom["citation_key"] for p in record.papers]
        assert len(keys) == len(set(keys)) == N_PAPERS

    def test_citation_key_recorded_in_custom(self):
        record, _ = parse_scholar_qa(_load_report(), _load_find())
        keys = {p.custom["citation_key"] for p in record.papers}
        assert keys == {
            "Maes2020",
            "Deng2023",
            "Coddington2018",
            "Schultz1997",
            "Cooper2011",
        }

    def test_parses_without_find_results(self):
        # No enrichment doc: still cites all five (text fallback for every paper).
        record, _ = parse_scholar_qa(_load_report())
        assert len(record.papers) == N_PAPERS
        assert {p.corpus_id for p in record.papers} == set(ALL_CORPUS_IDS)
        assert all(p.authors == "" for p in record.papers)  # no enrichment
        assert record.query == ""  # no find-results -> no query

    def test_report_with_no_references_yields_empty_paper_list(self):
        record, _ = parse_scholar_qa("# Title only\n\nNo citations here.")
        assert isinstance(record, ReportRecord)
        assert record.title == "Title only"
        assert record.papers == []

    def test_link_def_not_mistaken_for_reference_entry(self):
        # A [Key]: url line (single brackets) must NOT be parsed as a [[Key]]
        # reference entry, and vice versa.
        md = (
            "# T\n\n"
            "See [[Foo2020]] for details.\n\n"
            "## References\n"
            "- [[Foo2020]] Foo, B. (2020). A Title. Venue.\n\n"
            "[Foo2020]: https://semanticscholar.org/p/777\n"
        )
        record, _ = parse_scholar_qa(md)
        assert len(record.papers) == 1
        assert record.papers[0].corpus_id == "777"
        assert record.papers[0].custom["citation_key"] == "Foo2020"

    def test_defensive_on_garbage(self):
        assert parse_scholar_qa("") == (None, RunMeta())
        assert parse_scholar_qa("   \n  ") == (None, RunMeta())
        assert parse_scholar_qa(123)[0] is None  # type: ignore[arg-type]
        assert parse_scholar_qa(None)[0] is None  # type: ignore[arg-type]
        assert parse_scholar_qa({})[0] is None  # type: ignore[arg-type]
        # A malformed find_results does not break markdown parsing.
        record, _ = parse_scholar_qa(_load_report(), {"results": "nope"})
        assert len(record.papers) == N_PAPERS

    def test_corpus_id_from_url_variants(self):
        from wheeler.integrations.asta.scholar_qa import _corpus_id_from_url

        assert _corpus_id_from_url("https://semanticscholar.org/p/123") == "123"
        assert _corpus_id_from_url("https://www.semanticscholar.org/p/456") == "456"
        assert (
            _corpus_id_from_url("https://api.semanticscholar.org/CorpusId:789")
            == "789"
        )
        assert _corpus_id_from_url("https://doi.org/10.1/x") == ""
        assert _corpus_id_from_url("") == ""


# ---------------------------------------------------------------------------
# 2. CLI verb glue (markdown read + --find-results), no Neo4j
# ---------------------------------------------------------------------------


class TestScholarQaCliVerb:
    """The `wheeler integrate ingest scholar-qa <report.md>` dispatch.

    scholar-qa is the first MARKDOWN-deliverable tool: the verb must read the
    artifact as TEXT (not json.loads) and forward an optional --find-results JSON.
    Mocks ingest_scholar_qa so the glue is exercised without a live graph.
    """

    def _run(self, args, monkeypatch):
        from typer.testing import CliRunner

        from wheeler.integrations.asta import cli as cli_mod

        captured = {}

        async def _fake_ingest(report_markdown, **kwargs):
            captured["report_markdown"] = report_markdown
            captured.update(kwargs)
            return ImportReportStub()

        class ImportReportStub:
            created = 1
            deduped = 0
            linked = 2
            skipped = 0
            used = 1
            execution_id = "X-stub"
            artifact = "W-stub"
            paper_ids = ["P-stub"]
            failed = False
            job_state = ""

        monkeypatch.setattr(cli_mod, "load_config", lambda: object(), raising=False)
        monkeypatch.setattr(
            "wheeler.config.load_config", lambda: object(), raising=False
        )
        monkeypatch.setattr(
            "wheeler.integrations.asta.scholar_qa.ingest_scholar_qa", _fake_ingest
        )
        result = CliRunner().invoke(cli_mod.integrate_app, args)
        return result, captured

    def test_reads_markdown_not_json(self, tmp_path, monkeypatch):
        report = tmp_path / "report.md"
        report.write_text("# Not JSON\n\n[[A]] x\n\n[A]: https://semanticscholar.org/p/1\n")
        result, captured = self._run(
            ["ingest", "scholar-qa", str(report), "--link-to", "Q-1"], monkeypatch
        )
        assert result.exit_code == 0, result.output
        # The raw markdown reached the ingest verbatim (not parsed as JSON).
        assert captured["report_markdown"].startswith("# Not JSON")
        assert captured["report_path"] == str(report)
        assert captured["link_to"] == "Q-1"
        assert captured["find_results"] is None
        assert "artifact: W-stub" in result.output

    def test_find_results_parsed_and_forwarded(self, tmp_path, monkeypatch):
        report = tmp_path / "report.md"
        report.write_text("# R\n\n[[A]] x\n\n[A]: https://semanticscholar.org/p/1\n")
        find = tmp_path / "find.json"
        find.write_text(json.dumps({"query": "q", "results": []}))
        result, captured = self._run(
            ["ingest", "scholar-qa", str(report), "--find-results", str(find)],
            monkeypatch,
        )
        assert result.exit_code == 0, result.output
        assert captured["find_results"] == {"query": "q", "results": []}

    def test_used_ids_split_and_forwarded(self, tmp_path, monkeypatch):
        report = tmp_path / "report.md"
        report.write_text("# R\n")
        result, captured = self._run(
            ["ingest", "scholar-qa", str(report), "--used", "Q-1, , F-2"],
            monkeypatch,
        )
        assert result.exit_code == 0, result.output
        assert captured["used_inputs"] == ["Q-1", "F-2"]  # blanks dropped

    def test_literature_report_alias(self, tmp_path, monkeypatch):
        report = tmp_path / "report.md"
        report.write_text("# R\n")
        result, _ = self._run(
            ["ingest", "literature-report", str(report)], monkeypatch
        )
        assert result.exit_code == 0, result.output

    def test_missing_find_results_file_errors(self, tmp_path, monkeypatch):
        from typer.testing import CliRunner

        from wheeler.integrations.asta import cli as cli_mod

        report = tmp_path / "report.md"
        report.write_text("# R\n")
        monkeypatch.setattr(
            "wheeler.config.load_config", lambda: object(), raising=False
        )
        result = CliRunner().invoke(
            cli_mod.integrate_app,
            ["ingest", "scholar-qa", str(report), "--find-results", str(tmp_path / "nope.json")],
        )
        assert result.exit_code == 2
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# 3. Live-Neo4j e2e (per-run e2e_tag, hermetic teardown, run-unique corpus_ids)
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


def _cleanup_scholar_qa(e2e_config, e2e_tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged.

    EXACTLY ``MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n`` and nothing
    else. NEVER delete by ``service`` or ``corpus_id``: the e2e config runs on
    the SHARED default namespace where production nodes carry the same service
    tag, so a service- or corpus_id-scoped delete would wipe real user data.
    (The e2e uses RUN-UNIQUE synthetic corpus_ids precisely so no production
    Paper is ever deduped-into, tagged, and then deleted here.)
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

    try:
        asyncio.run(_run())
    except Exception:
        # Best-effort teardown: a transient Neo4j blip must not turn a
        # passing test into an ERROR. Orphans carry a per-run uuid e2e_tag.
        pass


def _build_report(cids: list[str]) -> tuple[str, dict]:
    """Build a report markdown + matching find-results for RUN-UNIQUE corpus_ids.

    Returns ``(markdown, find_results)``. The report cites each corpus_id once
    (inline + in References + a link definition); the find-results enriches the
    first three (the last two exercise the text-fallback path), mirroring the
    real fixture's mix.
    """
    keys = [f"Ref{i}" for i in range(len(cids))]
    inline = " ".join(f"[[{k}]]." for k in keys)
    refs = "\n".join(
        f"- [[{k}]] Author, A. ({2000 + i}). Synthetic paper {i} on the topic. Venue {i}."
        for i, k in enumerate(keys)
    )
    defs = "\n".join(
        f"[{k}]: https://semanticscholar.org/p/{cid}" for k, cid in zip(keys, cids)
    )
    markdown = (
        "# E2E Synthetic Literature Report\n\n"
        "## Executive Summary\n\n"
        f"This synthetic review cites several works {inline}\n\n"
        "## References\n\n"
        f"{refs}\n\n"
        f"{defs}\n"
    )
    find_results = {
        "query": "e2e synthetic topic",
        "results": [
            {
                "corpusId": int(cid),
                "title": f"Enriched synthetic paper {i}",
                "year": 2000 + i,
                "venue": f"Venue {i}",
                "citationCount": 10 + i,
                "authors": [{"name": f"Author {i}"}, {"name": "Coauthor B."}],
            }
            for i, cid in enumerate(cids[:3])  # enrich only the first three
        ],
    }
    return markdown, find_results


class TestIngestScholarQaE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        # Temp cwd so the on-disk corpus_id index + durable raw store land in a
        # sandbox we delete; per-run unique tag so teardown never touches another
        # test; run-unique synthetic corpus_ids so no production Paper is deduped.
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        # Run-unique numeric corpus_ids derived from the per-run uuid, so they
        # cannot collide with a production Paper or a prior interrupted run.
        base = int(self._e2e_tag.rsplit("_", 1)[-1][:12], 16)
        self._cids = [str(base + i) for i in range(N_PAPERS)]
        _cleanup_scholar_qa(e2e_config, self._e2e_tag)
        yield
        _cleanup_scholar_qa(e2e_config, self._e2e_tag)

    async def _tag_all(self, e2e_config, report):
        """Tag ONLY the nodes THIS run created, scoped off the report ids plus
        the run's WAS_GENERATED_BY fan-in. NEVER by service or corpus_id. Papers
        are reference entities (no WAS_GENERATED_BY); tag them via paper_ids."""
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        run_ids = [i for i in (report.execution_id, report.artifact) if i]
        run_ids += [pid for pid in report.paper_ids if pid]
        async with driver.session(database=db) as s:
            if run_ids:
                await s.run(
                    "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                    ids=run_ids,
                    tag=self._e2e_tag,
                )
            if report.execution_id:
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id,
                    tag=self._e2e_tag,
                )

    @pytest.mark.asyncio
    async def test_ingest_buckets_and_is_idempotent(self, e2e_config):
        from wheeler.graph.backend import get_backend
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.asta.scholar_qa import ingest_scholar_qa
        from wheeler.tools.graph_tools import execute_tool

        markdown, find_results = _build_report(self._cids)
        report_path = self._tmp / "report.md"
        report_path.write_text(markdown)

        # Seed a Question so the run has an input to USE and a link target.
        q = json.loads(
            await execute_tool(
                "add_question",
                {"question": "E2E: what does the synthetic review address?", "priority": 5},
                e2e_config,
            )
        )
        question_id = q["node_id"]
        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            await s.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=question_id,
                tag=self._e2e_tag,
            )

        # --- First ingest ---
        report1 = await ingest_scholar_qa(
            markdown,
            report_path=str(report_path),
            find_results=find_results,
            link_to=question_id,
            config=e2e_config,
            used_inputs=[question_id],
        )
        await self._tag_all(e2e_config, report1)
        assert report1.execution_id.startswith("X-")
        xid = report1.execution_id
        tag = self._e2e_tag
        # Five cited papers created (run-unique corpus_ids -> never deduped).
        assert report1.created == N_PAPERS
        assert report1.deduped == 0
        # The report Document is a W- node, NOT a Dataset.
        assert report1.artifact.startswith("W-")
        assert len(report1.paper_ids) == N_PAPERS

        # The report Document: a Document pointing at the durable raw store with
        # its .md extension preserved, WAS_GENERATED_BY the run Execution.
        raw_node = await get_backend(e2e_config).get_node("Document", report1.artifact)
        assert raw_node is not None
        assert ".wheeler/asta/raw/asta-scholar-qa" in raw_node["path"]
        assert raw_node["path"].endswith(".md")
        assert Path(raw_node["path"]).exists()
        assert raw_node["service"] == SERVICE_TAG

        async with driver.session(database=db) as s:
            # report Document WAS_GENERATED_BY the run Execution (exactly one).
            res = await s.run(
                "MATCH (w:Document {id: $wid})-[r:WAS_GENERATED_BY]->"
                "(x:Execution {id: $xid}) RETURN count(r) AS c",
                wid=report1.artifact,
                xid=xid,
            )
            assert (await res.single())["c"] == 1
            # The report Document CITES each cited Paper (5 CITES edges).
            res = await s.run(
                "MATCH (w:Document {id: $wid})-[r:CITES]->(p:Paper) "
                "RETURN count(r) AS c",
                wid=report1.artifact,
            )
            assert (await res.single())["c"] == N_PAPERS
            # The report Document AROSE_FROM the seed Question.
            res = await s.run(
                "MATCH (w:Document {id: $wid})-[r:AROSE_FROM]->(q {id: $qid}) "
                "RETURN count(r) AS c",
                wid=report1.artifact,
                qid=question_id,
            )
            assert (await res.single())["c"] == 1
            # INPUT side: the run USED the seed Question AND each cited Paper.
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[:USED]->(q {id: $qid}) "
                "RETURN count(q) AS c",
                xid=xid,
                qid=question_id,
            )
            assert (await res.single())["c"] == 1
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(p:Paper) "
                "RETURN count(r) AS c",
                xid=xid,
            )
            assert (await res.single())["c"] == N_PAPERS
            # Papers are REFERENCE ENTITIES: NO WAS_GENERATED_BY into the run.
            res = await s.run(
                "MATCH (p:Paper)-[r:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                "RETURN count(r) AS c",
                xid=xid,
            )
            assert (await res.single())["c"] == 0
            # The Execution carries the service tag and the literature-report kind.
            res = await s.run(
                "MATCH (x:Execution {id: $xid}) "
                "RETURN x.kind AS kind, x.service AS svc",
                xid=xid,
            )
            rec = await res.single()
            assert rec["kind"] == "literature-report"
            assert rec["svc"] == SERVICE_TAG

        # Enriched papers carry find-results metadata; unenriched ones do not.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper) WHERE p.e2e_tag = $tag AND p.corpus_id = $cid "
                "RETURN p.year AS year, p.custom_venue AS venue",
                tag=tag,
                cid=self._cids[0],
            )
            rec = await res.single()
            assert rec["year"] == 2000
            assert rec["venue"] == "Venue 0"

        # --- Re-ingest the SAME report: idempotent ---
        report2 = await ingest_scholar_qa(
            markdown,
            report_path=str(report_path),
            find_results=find_results,
            link_to=question_id,
            config=e2e_config,
            used_inputs=[question_id],
        )
        await self._tag_all(e2e_config, report2)
        assert report2.created == 0  # nothing new
        assert report2.deduped == N_PAPERS
        assert report2.execution_id == xid  # same Execution reused
        assert report2.artifact == report1.artifact  # same Document (path-dedupe)

        # No duplicate nodes or provenance edges on the second pass. Every
        # structural-provenance edge stays at exactly its first-pass count
        # (link_once guards each one): CITES, USED->Paper, USED->Question,
        # Document WAS_GENERATED_BY Execution, Document AROSE_FROM Question.
        async with driver.session(database=db) as s:
            res = await s.run(
                "MATCH (p:Paper) WHERE p.e2e_tag = $tag RETURN count(p) AS c",
                tag=tag,
            )
            assert (await res.single())["c"] == N_PAPERS
            res = await s.run(
                "MATCH (w:Document {id: $wid})-[r:CITES]->(:Paper) "
                "RETURN count(r) AS c",
                wid=report1.artifact,
            )
            assert (await res.single())["c"] == N_PAPERS
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(p:Paper) "
                "RETURN count(r) AS c",
                xid=xid,
            )
            assert (await res.single())["c"] == N_PAPERS
            res = await s.run(
                "MATCH (x:Execution {id: $xid})-[r:USED]->(q {id: $qid}) "
                "RETURN count(r) AS c",
                xid=xid,
                qid=question_id,
            )
            assert (await res.single())["c"] == 1  # no duplicate USED->input
            res = await s.run(
                "MATCH (w:Document {id: $wid})-[r:WAS_GENERATED_BY]->"
                "(x:Execution {id: $xid}) RETURN count(r) AS c",
                wid=report1.artifact,
                xid=xid,
            )
            assert (await res.single())["c"] == 1  # no duplicate WAS_GENERATED_BY
            res = await s.run(
                "MATCH (w:Document {id: $wid})-[r:AROSE_FROM]->(q {id: $qid}) "
                "RETURN count(r) AS c",
                wid=report1.artifact,
                qid=question_id,
            )
            assert (await res.single())["c"] == 1  # no duplicate AROSE_FROM
            res = await s.run(
                "MATCH (w:Document {id: $wid}) RETURN count(w) AS c",
                wid=report1.artifact,
            )
            assert (await res.single())["c"] == 1

        # --- Re-ingest an EDITED report at the SAME path: still ONE Document and
        # ONE Execution (the run key is coupled to the report path, not the
        # content sha, so a re-synthesized report does not accrue a second
        # Document to the run). ---
        edited = markdown + "\n\n## Addendum\n\nA later revision adds this section.\n"
        report_path.write_text(edited)
        report3 = await ingest_scholar_qa(
            edited,
            report_path=str(report_path),
            find_results=find_results,
            link_to=question_id,
            config=e2e_config,
            used_inputs=[question_id],
        )
        await self._tag_all(e2e_config, report3)
        assert report3.execution_id == xid  # same Execution despite edited text
        assert report3.artifact == report1.artifact  # same Document, not a second
        async with driver.session(database=db) as s:
            # Still exactly one Document WAS_GENERATED_BY this run's Execution
            # (the edited report did not create a second version node).
            res = await s.run(
                "MATCH (w:Document)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                "RETURN count(DISTINCT w) AS c",
                xid=xid,
            )
            assert (await res.single())["c"] == 1
