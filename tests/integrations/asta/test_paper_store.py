"""Tests for the paper-store marshal-in helper (Wheeler issue #85).

The load-bearing property is the CLOSED-CORPUS guarantee. From the asta CLI help:
identifier-only entries are hydrated during the PaperFinder step, so they require
``search_additional_papers=True``, which means PaperFinder runs and can
reintroduce papers the scientist screened out. Only a store where EVERY entry
carries ``paper_markdown`` can be paired with ``--no-search-additional-papers``.

So the invariant under test is: ``result.closed`` is True only when the store is
genuinely usable with PaperFinder off, and a paper with no abstract is dropped
rather than silently downgraded to an identifier (which would reopen the corpus).
"""

from __future__ import annotations

import asyncio
import json

import pytest

from wheeler.config import WheelerConfig
from wheeler.integrations.asta.paper_store import (
    MODE_IDENTIFIERS,
    MODE_MARKDOWN,
    build_paper_store,
    write_paper_store,
)


class _StubBackend:
    """Returns canned Paper rows and records the Cypher it was asked to run."""

    def __init__(self, rows):
        self.rows = rows
        self.queries: list[tuple[str, dict]] = []

    async def run_cypher(self, query, params):
        self.queries.append((query, params))
        return self.rows


def _row(pid, *, abstract="", corpus_id="", title="T", **kw):
    base = {
        "id": pid,
        "corpus_id": corpus_id,
        "title": title,
        "authors": "A. Author",
        "year": 2020,
        "doi": "",
        "abstract": abstract,
        "venue": "",
        "url": "",
    }
    base.update(kw)
    return base


def _build(rows, **kw):
    backend = _StubBackend(rows)
    import wheeler.graph.backend as backend_mod

    original = backend_mod.get_backend
    backend_mod.get_backend = lambda config: backend
    try:
        result = asyncio.run(
            build_paper_store(WheelerConfig(), link_to="Q-1", **kw)
        )
    finally:
        backend_mod.get_backend = original
    return result, backend


class TestClosedCorpusGuarantee:
    def test_all_abstracts_yields_closed_corpus(self):
        result, _ = _build(
            [
                _row("P-1", abstract="First abstract.", corpus_id="11"),
                _row("P-2", abstract="Second abstract.", corpus_id="22"),
            ]
        )
        assert result.closed is True
        assert len(result.entries) == 2
        assert all("paper_markdown" in e for e in result.entries)
        assert result.paper_ids == ["P-1", "P-2"]

    def test_paper_without_abstract_is_skipped_not_downgraded(self):
        """The core invariant: no silent identifier-only entry in markdown mode.

        Downgrading would force search_additional_papers=True and quietly reopen
        the corpus, which is the exact failure this feature exists to prevent.
        """
        result, _ = _build(
            [
                _row("P-1", abstract="Has one.", corpus_id="11"),
                _row("P-2", abstract="", corpus_id="22", title="No abstract"),
            ]
        )
        assert len(result.entries) == 1
        assert result.skipped == [{"id": "P-2", "title": "No abstract"}]
        assert result.closed is True, (
            "dropping the abstract-less paper must preserve the closed-corpus "
            "guarantee for the papers that remain"
        )
        for entry in result.entries:
            assert entry.get("paper_markdown"), (
                "an entry without paper_markdown would force PaperFinder on"
            )

    def test_identifiers_mode_is_never_closed(self):
        result, _ = _build(
            [
                _row("P-1", abstract="Has one.", corpus_id="11"),
                _row("P-2", abstract="Also has one.", corpus_id="22"),
            ],
            mode=MODE_IDENTIFIERS,
        )
        assert result.closed is False, (
            "identifier-only entries are hydrated during the PaperFinder step, "
            "so this store can never be paired with --no-search-additional-papers"
        )
        assert all("paper_markdown" not in e for e in result.entries)
        assert all("corpus_id" in e for e in result.entries)

    def test_empty_selection_is_not_closed(self):
        result, _ = _build([])
        assert result.entries == []
        assert result.closed is False, (
            "an empty store must not report closed=yes; there is nothing to run"
        )


class TestSelection:
    def test_link_to_selects_via_relevant_to(self):
        _, backend = _build([_row("P-1", abstract="a")])
        query, params = backend.queries[0]
        assert "RELEVANT_TO" in query
        assert params["link_to"] == "Q-1"
        assert "ORDER BY p.id" in query, "export must be deterministic"

    def test_explicit_paper_ids_bypass_the_link(self):
        backend = _StubBackend([_row("P-9", abstract="a")])
        import wheeler.graph.backend as backend_mod

        original = backend_mod.get_backend
        backend_mod.get_backend = lambda config: backend
        try:
            asyncio.run(
                build_paper_store(WheelerConfig(), paper_ids=["P-9"])
            )
        finally:
            backend_mod.get_backend = original
        query, params = backend.queries[0]
        assert "RELEVANT_TO" not in query
        assert params["ids"] == ["P-9"]

    def test_requires_a_selector(self):
        with pytest.raises(ValueError, match="link_to or paper_ids"):
            asyncio.run(build_paper_store(WheelerConfig()))

    def test_rejects_unknown_mode(self):
        with pytest.raises(ValueError, match="mode must be one of"):
            asyncio.run(
                build_paper_store(WheelerConfig(), link_to="Q-1", mode="nope")
            )


class TestMarkdownRendering:
    def test_markdown_carries_title_metadata_and_abstract(self):
        result, _ = _build(
            [
                _row(
                    "P-1",
                    abstract="The abstract body.",
                    corpus_id="123",
                    title="A Paper Title",
                    venue="Nature",
                    year=1999,
                    doi="10.1/x",
                )
            ]
        )
        md = result.entries[0]["paper_markdown"]
        assert md.startswith("# A Paper Title")
        assert "**Authors:** A. Author" in md
        assert "**Year:** 1999" in md
        assert "**Venue:** Nature" in md
        assert "**DOI:** 10.1/x" in md
        assert "## Abstract" in md
        assert "The abstract body." in md

    def test_corpus_id_rides_along_for_server_side_dedupe(self):
        result, _ = _build([_row("P-1", abstract="a", corpus_id="777")])
        assert result.entries[0]["corpus_id"] == "777"


class TestWrite:
    def test_writes_a_json_list(self, tmp_path):
        result, _ = _build([_row("P-1", abstract="a", corpus_id="1")])
        out = tmp_path / "nested" / "store.json"
        path = write_paper_store(result, out)

        assert path.exists()
        payload = json.loads(path.read_text())
        assert isinstance(payload, list), (
            "the store is emitted as a JSON list of entries; see the module "
            "docstring on the inferred top-level shape"
        )
        assert payload[0]["corpus_id"] == "1"
        assert not list(tmp_path.rglob("*.tmp")), "atomic write left a temp file"

    def test_mode_is_reported(self):
        result, _ = _build([_row("P-1", abstract="a")], mode=MODE_MARKDOWN)
        assert result.to_dict()["mode"] == MODE_MARKDOWN
        assert result.to_dict()["closed"] is True


# ---------------------------------------------------------------------------
# live-Neo4j e2e
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def e2e_config():
    """Live config, with the Neo4j block taken from the project's own config.

    Deliberately NOT a hardcoded password. A stale literal here is invisible
    until the credential drifts, and then every graph test fails for a reason
    that has nothing to do with the code under test.
    """
    from wheeler.config import ProjectMeta, load_config

    config = load_config()
    config.project = ProjectMeta(name="PaperStore-E2E-Test")
    return config


@pytest.fixture(scope="module")
def neo4j_available(e2e_config) -> bool:
    """Authenticated probe, not a port check: auth failure means unavailable."""
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
    """Each asyncio.run gets a fresh loop; a cached driver would be bound to a dead one."""
    import wheeler.graph.driver as drv

    drv._async_driver = None
    drv._async_driver_uri = None
    yield
    drv._async_driver = None
    drv._async_driver_uri = None


def _cleanup(e2e_config, e2e_tag):
    """Delete ONLY nodes carrying this run's unique tag. Never unscoped."""
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
        # Best-effort teardown: a transient blip must not turn a pass into an
        # ERROR. Orphans carry the per-run uuid tag.
        pass


class TestPaperStoreE2E:
    """Real graph read: the stub cannot catch a wrong property name.

    The abstract lives at ``custom_abstract`` because the backend flattens the
    custom bag on write. A unit test with canned rows would pass even if the
    Cypher asked for ``p.abstract``, so this reads a Paper that was written the
    way production writes one.
    """

    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping paper-store e2e")
        import uuid

        self._tag = f"paperstore_e2e_{uuid.uuid4().hex}"
        _cleanup(e2e_config, self._tag)
        yield
        _cleanup(e2e_config, self._tag)

    def _seed(self, e2e_config):
        """Create one Question and three Papers, two with abstracts."""
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
                        "CREATE (q:OpenQuestion {id:$qid, question:'seed', e2e_tag:$tag})",
                        qid=f"Q-{self._tag}",
                        tag=self._tag,
                    )
                    papers = [
                        (f"P-{self._tag}-a", "Alpha", "Abstract alpha.", "111"),
                        (f"P-{self._tag}-b", "Beta", "Abstract beta.", "222"),
                        (f"P-{self._tag}-c", "Gamma", "", "333"),
                    ]
                    for pid, title, abstract, cid in papers:
                        await s.run(
                            "MATCH (q:OpenQuestion {id:$qid}) "
                            "CREATE (p:Paper {id:$pid, title:$title, authors:'X. Y', "
                            "year:2021, corpus_id:$cid, custom_abstract:$abs, "
                            "e2e_tag:$tag})-[:RELEVANT_TO]->(q)",
                            qid=f"Q-{self._tag}",
                            pid=pid,
                            title=title,
                            cid=cid,
                            abs=abstract,
                            tag=self._tag,
                        )
            finally:
                await driver.close()

        asyncio.run(_run())

    def test_round_trip_selects_curated_set_and_reads_the_real_abstract(
        self, e2e_config, tmp_path
    ):
        self._seed(e2e_config)

        result = asyncio.run(
            build_paper_store(e2e_config, link_to=f"Q-{self._tag}")
        )

        # The abstract-less Paper is dropped, not downgraded.
        assert len(result.entries) == 2, (
            f"expected the 2 papers with abstracts, got {result.to_dict()}"
        )
        assert len(result.skipped) == 1
        assert result.skipped[0]["title"] == "Gamma"
        assert result.closed is True

        # The real property name is read correctly (custom_abstract, flattened).
        joined = "\n".join(e["paper_markdown"] for e in result.entries)
        assert "Abstract alpha." in joined
        assert "Abstract beta." in joined
        assert "Gamma" not in joined

        # Paper ids come back for --used provenance, deterministically ordered.
        assert result.paper_ids == sorted(result.paper_ids)
        assert all(pid.startswith(f"P-{self._tag}") for pid in result.paper_ids)

        payload = json.loads(
            write_paper_store(result, tmp_path / "store.json").read_text()
        )
        assert isinstance(payload, list) and len(payload) == 2

    def test_explicit_ids_read_from_the_live_graph(self, e2e_config):
        self._seed(e2e_config)
        result = asyncio.run(
            build_paper_store(
                e2e_config,
                paper_ids=[f"P-{self._tag}-a", f"P-{self._tag}-c"],
                mode=MODE_IDENTIFIERS,
            )
        )
        # identifiers mode keeps the abstract-less paper: it needs only an id.
        assert len(result.entries) == 2
        assert result.closed is False
        assert {e["corpus_id"] for e in result.entries} == {"111", "333"}
