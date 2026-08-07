"""Retry behaviour of the Neo4j backend.

Which call sites replay and which do not is a correctness decision, not a
tuning knob, so it is pinned here per method:

    retried      get_node, update_node, delete_node, query_nodes,
                 run_cypher when the query is provably read-only
    not retried  create_node, create_relationship, count_all,
                 run_cypher when the query can write

The two `not retried` writes are the interesting half. A replayed
`CREATE (a)-[r:TYPE]->(b)` silently doubles a provenance edge, and a replayed
node CREATE reports failure for a write that landed.
"""

from __future__ import annotations

import asyncio

from neo4j.exceptions import AuthError, ServiceUnavailable
import pytest

from wheeler.config import WheelerConfig
from wheeler.graph.circuit_breaker import CBState, CircuitOpenError
import wheeler.graph.driver as drv
from wheeler.graph.neo4j_backend import Neo4jBackend, _is_read_only_cypher


class _FakeNeo4jError(Exception):
    """Stand-in for a deterministic Neo4jError, as in test_circuit_breaker.py."""

    def __init__(self, code: str, message: str = "bad cypher") -> None:
        super().__init__(message)
        self.code = code


_SYNTAX_ERROR = "Neo.ClientError.Statement.SyntaxError"


class _FakeResult:
    def __init__(self, rows: list) -> None:
        self._rows = list(rows)

    async def single(self):
        return self._rows[0] if self._rows else None

    def __aiter__(self):
        async def _gen():
            for row in self._rows:
                yield row

        return _gen()


class _FakeSession:
    def __init__(self, driver: _FakeDriver) -> None:
        self._driver = driver

    async def __aenter__(self) -> _FakeSession:
        self._driver.in_flight += 1
        self._driver.max_in_flight = max(
            self._driver.max_in_flight, self._driver.in_flight
        )
        return self

    async def __aexit__(self, *exc_info) -> bool:
        self._driver.in_flight -= 1
        return False

    async def run(self, query: str, parameters: dict | None = None, **_kwargs):
        driver = self._driver
        call_index = len(driver.queries)
        driver.queries.append(query)
        driver.params.append(parameters or {})
        # Yield to the loop so an accidental gather would actually interleave.
        await asyncio.sleep(0)
        error = driver.on_run(query, call_index)
        if error is not None:
            raise error
        return _FakeResult(driver.rows)


class _FakeDriver:
    """Driver stand-in with scripted per-run failures and overlap tracking."""

    def __init__(self, rows: list | None = None, on_run=None) -> None:
        self.rows: list = list(rows or [])
        self.on_run = on_run or (lambda query, call_index: None)
        self.queries: list[str] = []
        self.params: list[dict] = []
        self.sessions = 0
        self.in_flight = 0
        self.max_in_flight = 0

    def session(self, database: str | None = None, **_kwargs) -> _FakeSession:
        self.sessions += 1
        return _FakeSession(self)


def _fail_times(count: int, error_factory=lambda: ServiceUnavailable("wan blip")):
    """on_run hook that fails the first `count` run() calls, then succeeds."""
    state = {"n": 0}

    def hook(query: str, call_index: int):
        state["n"] += 1
        return error_factory() if state["n"] <= count else None

    return hook


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch):
    """No backoff sleeps: these tests assert counts, not timing."""
    monkeypatch.setenv(drv._ENV_RETRY_BASE_DELAY, "0")
    drv.invalidate_async_driver()
    yield
    drv.invalidate_async_driver()


def _backend(driver: _FakeDriver, *, project_tag: str = "") -> Neo4jBackend:
    config = WheelerConfig()
    config.neo4j.project_tag = project_tag
    backend = Neo4jBackend(config)
    backend._driver = lambda: driver  # type: ignore[method-assign]
    return backend


class TestReadsAreRetried:
    async def test_get_node_survives_a_transient_failure(self):
        driver = _FakeDriver(rows=[{"n": {"id": "F-1", "title": "t"}}],
                             on_run=_fail_times(1))
        backend = _backend(driver)

        node = await backend.get_node("Finding", "F-1")

        assert node == {"id": "F-1", "title": "t"}
        assert driver.sessions == 2, "should have opened a fresh session to retry"

    async def test_query_nodes_survives_a_transient_failure(self):
        driver = _FakeDriver(rows=[{"n": {"id": "F-1"}}, {"n": {"id": "F-2"}}],
                             on_run=_fail_times(1))
        backend = _backend(driver)

        rows = await backend.query_nodes("Finding", limit=5)

        assert [r["id"] for r in rows] == ["F-1", "F-2"]
        assert driver.sessions == 2

    async def test_update_node_survives_a_transient_failure(self):
        """MATCH ... SET assigns fixed values, so a replay is a no-op."""
        driver = _FakeDriver(rows=[{"n.id": "F-1"}], on_run=_fail_times(1))
        backend = _backend(driver)

        assert await backend.update_node("Finding", "F-1", {"title": "new"}) is True
        assert driver.sessions == 2

    async def test_a_retry_reruns_the_same_query(self):
        driver = _FakeDriver(rows=[{"n": {"id": "F-1"}}], on_run=_fail_times(1))
        backend = _backend(driver)

        await backend.get_node("Finding", "F-1")

        assert len(driver.queries) == 2
        assert driver.queries[0] == driver.queries[1]

    async def test_project_tag_filter_survives_every_retried_attempt(self):
        """backup-track just fixed a leak from a query missing this filter."""
        driver = _FakeDriver(rows=[{"n": {"id": "F-1"}}], on_run=_fail_times(1))
        backend = _backend(driver, project_tag="proj-a")

        await backend.get_node("Finding", "F-1")

        assert len(driver.queries) == 2
        for query in driver.queries:
            assert "_wheeler_project = $ptag" in query
        for params in driver.params:
            assert params["ptag"] == "proj-a"

    async def test_exhausted_retries_raise_the_underlying_error(self):
        driver = _FakeDriver(on_run=_fail_times(99))
        backend = _backend(driver)

        with pytest.raises(ServiceUnavailable):
            await backend.get_node("Finding", "F-1")

        assert driver.sessions == drv._DEFAULT_RETRY_ATTEMPTS


class TestDeterministicErrorsAreNotRetried:
    async def test_a_syntax_error_is_not_replayed(self):
        driver = _FakeDriver(
            on_run=_fail_times(99, lambda: _FakeNeo4jError(_SYNTAX_ERROR))
        )
        backend = _backend(driver)

        with pytest.raises(_FakeNeo4jError):
            await backend.get_node("Finding", "F-1")

        assert driver.sessions == 1, "retrying a caller bug just repeats it"

    async def test_a_syntax_error_does_not_advance_the_breaker(self):
        driver = _FakeDriver(
            on_run=_fail_times(99, lambda: _FakeNeo4jError(_SYNTAX_ERROR))
        )
        backend = _backend(driver)

        with pytest.raises(_FakeNeo4jError):
            await backend.get_node("Finding", "F-1")

        assert backend._cb.state == CBState.CLOSED
        assert backend._cb._failure_count == 0
        assert backend._cb._last_underlying is not None

    async def test_an_auth_error_is_not_replayed(self):
        """Retrying a wrong password cannot heal, and may lock the account."""
        driver = _FakeDriver(on_run=_fail_times(99, lambda: AuthError("nope")))
        backend = _backend(driver)

        with pytest.raises(AuthError):
            await backend.get_node("Finding", "F-1")

        assert driver.sessions == 1

    async def test_a_write_conflict_style_error_is_not_replayed(self):
        driver = _FakeDriver(
            on_run=_fail_times(
                99,
                lambda: _FakeNeo4jError("Neo.ClientError.Schema.ConstraintValidationFailed"),
            )
        )
        backend = _backend(driver)

        with pytest.raises(_FakeNeo4jError):
            await backend.query_nodes("Finding")

        assert driver.sessions == 1


class TestCircuitBreakerStillGoverns:
    async def test_an_open_breaker_fails_fast_without_touching_the_driver(self):
        driver = _FakeDriver()
        backend = _backend(driver)
        for _ in range(backend._cb.failure_threshold):
            backend._cb.record_failure()
        assert backend._cb.state == CBState.OPEN

        with pytest.raises(CircuitOpenError):
            await backend.get_node("Finding", "F-1")

        assert driver.sessions == 0

    async def test_exhausted_retries_open_the_breaker(self):
        driver = _FakeDriver(on_run=_fail_times(99))
        backend = _backend(driver)

        with pytest.raises(ServiceUnavailable):
            await backend.get_node("Finding", "F-1")

        assert backend._cb.state == CBState.OPEN

    async def test_a_recovered_read_leaves_the_breaker_closed(self):
        driver = _FakeDriver(rows=[{"n": {"id": "F-1"}}], on_run=_fail_times(1))
        backend = _backend(driver)

        await backend.get_node("Finding", "F-1")

        assert backend._cb.state == CBState.CLOSED
        assert backend._cb._failure_count == 0

    async def test_the_breaker_opens_before_the_call_returns(self):
        """Once open, the next call must not reach the driver at all."""
        driver = _FakeDriver(on_run=_fail_times(99))
        backend = _backend(driver)

        with pytest.raises(ServiceUnavailable):
            await backend.get_node("Finding", "F-1")
        sessions_after_first = driver.sessions

        with pytest.raises(CircuitOpenError):
            await backend.get_node("Finding", "F-2")

        assert driver.sessions == sessions_after_first


class TestAttemptsAreSequential:
    async def test_sessions_never_overlap(self):
        """A Neo4j session forbids concurrent queries: no gather, ever."""
        driver = _FakeDriver(rows=[{"n": {"id": "F-1"}}], on_run=_fail_times(2))
        backend = _backend(driver)

        await backend.get_node("Finding", "F-1")

        assert driver.sessions == 3
        assert driver.max_in_flight == 1

    async def test_delete_node_sessions_never_overlap(self):
        driver = _FakeDriver(rows=[{"n.id": "F-1"}], on_run=_fail_times(1))
        backend = _backend(driver)

        await backend.delete_node("Finding", "F-1")

        assert driver.max_in_flight == 1


class TestWritesThatMustNotBeReplayed:
    async def test_create_node_is_not_retried(self):
        driver = _FakeDriver(on_run=_fail_times(99))
        backend = _backend(driver)

        with pytest.raises(ServiceUnavailable):
            await backend.create_node("Finding", {"id": "F-1", "title": "t"})

        assert driver.sessions == 1, "a replayed CREATE misreports a landed write"

    async def test_create_relationship_is_not_retried(self):
        driver = _FakeDriver(on_run=_fail_times(99))
        backend = _backend(driver)

        with pytest.raises(ServiceUnavailable):
            await backend.create_relationship("Finding", "F-1", "USED", "Script", "S-1")

        assert driver.sessions == 1, "a replayed CREATE doubles a provenance edge"

    async def test_a_failed_write_still_advances_the_breaker(self):
        """Not replaying must not mean not noticing."""
        driver = _FakeDriver(on_run=_fail_times(99))
        backend = _backend(driver)

        with pytest.raises(ServiceUnavailable):
            await backend.create_node("Finding", {"id": "F-1"})

        assert backend._cb._failure_count == 1
        assert backend._cb._last_underlying is not None

    async def test_a_successful_write_still_resets_the_breaker(self):
        driver = _FakeDriver(rows=[{"rel": "USED"}])
        backend = _backend(driver)
        backend._cb.record_failure()

        assert await backend.create_relationship(
            "Finding", "F-1", "USED", "Script", "S-1"
        ) is True
        assert backend._cb._failure_count == 0


class TestDeleteNodeReplay:
    async def test_happy_path_is_unchanged(self):
        driver = _FakeDriver(rows=[{"n.id": "F-1"}])
        backend = _backend(driver)

        assert await backend.delete_node("Finding", "F-1") is True
        assert len(driver.queries) == 2
        assert "DETACH DELETE" in driver.queries[1]

    async def test_a_missing_node_returns_false(self):
        driver = _FakeDriver(rows=[])
        backend = _backend(driver)

        assert await backend.delete_node("Finding", "F-1") is False
        assert len(driver.queries) == 1, "nothing to delete, so no DELETE issued"

    async def test_a_replay_after_the_delete_committed_still_reports_true(self):
        """The delete landed, then the connection dropped before the ack.

        The replayed existence check finds nothing. Reporting False there would
        tell the caller the node was never in the graph, and its JSON and
        synthesis files would be left behind as orphans.
        """
        driver = _FakeDriver(rows=[{"n.id": "F-1"}])

        def hook(query: str, call_index: int):
            if "DETACH DELETE" in query and call_index == 1:
                driver.rows = []  # the delete committed
                return ServiceUnavailable("ack lost")
            return None

        driver.on_run = hook
        backend = _backend(driver)

        assert await backend.delete_node("Finding", "F-1") is True
        assert driver.sessions == 2


class TestReadOnlyCypherClassification:
    @pytest.mark.parametrize(
        "query",
        [
            "MATCH (n:Finding) RETURN n",
            "MATCH (d:Dataset) RETURN d.file_path",
            "MATCH (n) WHERE n.offset > 3 RETURN count(n)",
            "MATCH (a)-[r:USED]->(b) RETURN a.id, type(r), b.id",
            "MATCH (n:Finding) RETURN n ORDER BY n.updated DESC LIMIT 10",
        ],
    )
    def test_reads_are_read_only(self, query):
        assert _is_read_only_cypher(query) is True

    def test_the_dataset_substring_trap(self):
        """A substring test would see SET in `Dataset` and skip nearly every read."""
        assert _is_read_only_cypher("MATCH (d:Dataset) RETURN d") is True
        assert _is_read_only_cypher("MATCH (n) RETURN n.offset") is True

    @pytest.mark.parametrize(
        "query",
        [
            "CREATE (n:Finding {id: 'F-1'})",
            "MERGE (n:Finding {id: 'F-1'})",
            "MATCH (n:Finding {id: 'F-1'}) SET n.tier = 'core'",
            "MATCH (n:Finding {id: 'F-1'}) DETACH DELETE n",
            "MATCH (n) REMOVE n.stale",
            "DROP INDEX wheeler_fulltext",
            "CALL db.index.fulltext.queryNodes('wheeler_fulltext', $q) YIELD node",
            "MATCH (n) FOREACH (x IN n.tags | CREATE (:Tag {name: x}))",
            "LOAD CSV FROM 'file:///x.csv' AS row CREATE (:Row)",
        ],
    )
    def test_writes_and_indirect_routes_are_not_read_only(self, query):
        assert _is_read_only_cypher(query) is False

    def test_a_read_mentioning_a_write_word_is_merely_not_retried(self):
        """Misclassification must always fall on the safe side."""
        assert _is_read_only_cypher(
            "MATCH (n) WHERE n.title CONTAINS 'create' RETURN n"
        ) is False


class TestRunCypherRoutesByQuery:
    async def test_a_read_only_query_is_retried(self):
        driver = _FakeDriver(rows=[{"id": "F-1"}], on_run=_fail_times(1))
        backend = _backend(driver)

        rows = await backend.run_cypher("MATCH (n:Finding) RETURN n.id AS id")

        assert rows == [{"id": "F-1"}]
        assert driver.sessions == 2

    async def test_a_write_query_is_not_retried(self):
        """merge.py and restore.py send writes through run_cypher."""
        driver = _FakeDriver(on_run=_fail_times(99))
        backend = _backend(driver)

        with pytest.raises(ServiceUnavailable):
            await backend.run_cypher(
                "MATCH (a:Finding {id: $s}), (b:Script {id: $t}) "
                "CREATE (a)-[:USED]->(b)",
                {"s": "F-1", "t": "S-1"},
            )

        assert driver.sessions == 1

    async def test_params_are_passed_through_on_every_attempt(self):
        driver = _FakeDriver(rows=[{"id": "F-1"}], on_run=_fail_times(1))
        backend = _backend(driver)

        await backend.run_cypher(
            "MATCH (n:Finding {id: $id}) RETURN n.id AS id", {"id": "F-1"}
        )

        assert driver.params == [{"id": "F-1"}, {"id": "F-1"}]


class TestCountAll:
    async def test_count_all_reports_offline_without_retrying(self, monkeypatch):
        """get_status swallows its own errors, so there is nothing to retry."""
        calls = []

        async def fake_get_status(config):
            calls.append(1)
            return {"Finding": 0, "_status": "offline"}

        monkeypatch.setattr("wheeler.graph.schema.get_status", fake_get_status)
        backend = _backend(_FakeDriver())

        result = await backend.count_all()

        assert result["_status"] == "offline"
        assert len(calls) == 1
