"""Tests for wheeler.graph.driver: cache identity, connection settings, retry.

The cache-identity tests cover a latent bug: the singleton was keyed on the
URI alone, so rotating a password or switching user against the same host
silently handed back a driver still holding the old credentials.
"""

from __future__ import annotations

import asyncio
import logging

from neo4j.exceptions import (
    AuthError,
    DatabaseError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)
import pytest

from wheeler.config import WheelerConfig
from wheeler.graph.circuit_breaker import CBState, CircuitBreaker, CircuitOpenError
import wheeler.graph.driver as drv


class _FakeNeo4jError(Exception):
    """Minimal stand-in for neo4j.exceptions.Neo4jError (has a `code`).

    Same shape as the helper in tests/test_circuit_breaker.py.
    """

    def __init__(self, code: str, message: str = "boom") -> None:
        super().__init__(message)
        self.code = code


class _FakeDriver:
    def __init__(self, uri: str, **kwargs) -> None:
        self.uri = uri
        self.kwargs = kwargs
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakeGraphDatabase:
    """Records every driver construction so tests can assert on kwargs."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def driver(self, uri: str, **kwargs):
        self.calls.append((uri, kwargs))
        return _FakeDriver(uri, **kwargs)


_ENV_NAMES = (
    drv._ENV_POOL_SIZE,
    drv._ENV_ACQUISITION_TIMEOUT,
    drv._ENV_MAX_LIFETIME,
    drv._ENV_CONNECT_TIMEOUT,
    drv._ENV_RETRY_ATTEMPTS,
    drv._ENV_RETRY_BASE_DELAY,
)


@pytest.fixture(autouse=True)
def _isolate_driver_state(monkeypatch):
    """Driver globals and WHEELER_NEO4J_* env are module state: isolate them."""
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    drv.invalidate_async_driver()
    yield
    drv.invalidate_async_driver()


@pytest.fixture
def fake_db(monkeypatch) -> _FakeGraphDatabase:
    fake = _FakeGraphDatabase()
    monkeypatch.setattr(drv, "AsyncGraphDatabase", fake)
    monkeypatch.setattr(drv, "GraphDatabase", fake)
    return fake


def _config(
    *,
    uri: str = "bolt://localhost:7687",
    username: str = "neo4j",
    password: str = "research-graph",
    database: str = "neo4j",
) -> WheelerConfig:
    """Build a config by assignment, so no env-precedence logic is involved."""
    config = WheelerConfig()
    config.neo4j.uri = uri
    config.neo4j.username = username
    config.neo4j.password = password
    config.neo4j.database = database
    return config


class TestDriverCacheIdentity:
    def test_same_config_reuses_driver(self, fake_db):
        config = _config()
        first = drv.get_async_driver(config)
        second = drv.get_async_driver(config)

        assert first is second
        assert len(fake_db.calls) == 1

    def test_changed_uri_creates_new_driver(self, fake_db):
        first = drv.get_async_driver(_config(uri="bolt://localhost:7687"))
        second = drv.get_async_driver(_config(uri="neo4j+s://abc.databases.neo4j.io"))

        assert first is not second
        assert len(fake_db.calls) == 2
        assert fake_db.calls[1][0] == "neo4j+s://abc.databases.neo4j.io"

    def test_changed_username_creates_new_driver(self, fake_db):
        first = drv.get_async_driver(_config(username="neo4j"))
        second = drv.get_async_driver(_config(username="someone-else"))

        assert first is not second
        assert fake_db.calls[1][1]["auth"] == ("someone-else", "research-graph")

    def test_changed_password_creates_new_driver(self, fake_db):
        """The original bug: same URI, new password, stale driver reused."""
        first = drv.get_async_driver(_config(password="old-secret"))
        second = drv.get_async_driver(_config(password="new-secret"))

        assert first is not second
        assert len(fake_db.calls) == 2
        assert fake_db.calls[1][1]["auth"] == ("neo4j", "new-secret")

    def test_changed_database_creates_new_driver(self, fake_db):
        first = drv.get_async_driver(_config(database="neo4j"))
        second = drv.get_async_driver(_config(database="other-project"))

        assert first is not second
        assert len(fake_db.calls) == 2

    def test_cache_key_records_identity_without_plaintext_password(self, fake_db):
        drv.get_async_driver(_config(password="research-graph"))

        assert drv._async_driver_key is not None
        uri, username, database, pw_digest = drv._async_driver_key
        assert (uri, username, database) == ("bolt://localhost:7687", "neo4j", "neo4j")
        assert "research-graph" not in pw_digest
        # A digest, not the secret, and stable for the same password.
        assert pw_digest == drv._driver_key(_config(password="research-graph"))[3]

    def test_uri_global_tracks_the_cached_driver(self, fake_db):
        drv.get_async_driver(_config(uri="neo4j://host:7688"))
        assert drv._async_driver_uri == "neo4j://host:7688"

    def test_invalidate_clears_driver_key_and_uri(self, fake_db):
        drv.get_async_driver(_config())
        assert drv._async_driver is not None

        drv.invalidate_async_driver()

        assert drv._async_driver is None
        assert drv._async_driver_key is None
        assert drv._async_driver_uri is None

    def test_invalidate_does_not_close_the_driver(self, fake_db):
        """The deliberate leak: the driver's event loop is already dead."""
        driver = drv.get_async_driver(_config())
        drv.invalidate_async_driver()
        assert driver.closed is False

    async def test_close_closes_and_clears(self, fake_db):
        driver = drv.get_async_driver(_config())

        await drv.close_async_driver()

        assert driver.closed is True
        assert drv._async_driver is None
        assert drv._async_driver_key is None
        assert drv._async_driver_uri is None

    async def test_close_is_a_noop_without_a_driver(self):
        await drv.close_async_driver()  # must not raise
        assert drv._async_driver is None


class TestConnectionSettings:
    def test_defaults(self):
        settings = drv.connection_settings()

        assert settings == {
            "max_connection_pool_size": drv._DEFAULT_POOL_SIZE,
            "connection_acquisition_timeout": drv._DEFAULT_ACQUISITION_TIMEOUT,
            "max_connection_lifetime": drv._DEFAULT_MAX_LIFETIME,
            "connection_timeout": drv._DEFAULT_CONNECT_TIMEOUT,
        }

    def test_async_driver_gets_the_settings(self, fake_db):
        drv.get_async_driver(_config())

        _uri, kwargs = fake_db.calls[0]
        for key, value in drv.connection_settings().items():
            assert kwargs[key] == value

    def test_sync_driver_gets_the_same_settings(self, fake_db):
        drv.get_sync_driver(_config())

        _uri, kwargs = fake_db.calls[0]
        for key, value in drv.connection_settings().items():
            assert kwargs[key] == value

    def test_env_overrides(self, monkeypatch):
        monkeypatch.setenv(drv._ENV_POOL_SIZE, "7")
        monkeypatch.setenv(drv._ENV_ACQUISITION_TIMEOUT, "12.5")
        monkeypatch.setenv(drv._ENV_MAX_LIFETIME, "600")
        monkeypatch.setenv(drv._ENV_CONNECT_TIMEOUT, "45")

        settings = drv.connection_settings()

        assert settings["max_connection_pool_size"] == 7
        assert settings["connection_acquisition_timeout"] == 12.5
        assert settings["max_connection_lifetime"] == 600.0
        assert settings["connection_timeout"] == 45.0

    def test_blank_env_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv(drv._ENV_POOL_SIZE, "   ")
        assert drv.connection_settings()["max_connection_pool_size"] == drv._DEFAULT_POOL_SIZE

    def test_unparseable_env_warns_and_falls_back(self, monkeypatch, caplog):
        monkeypatch.setenv(drv._ENV_POOL_SIZE, "lots")
        monkeypatch.setenv(drv._ENV_CONNECT_TIMEOUT, "soon")

        with caplog.at_level(logging.WARNING, logger=drv.logger.name):
            settings = drv.connection_settings()

        assert settings["max_connection_pool_size"] == drv._DEFAULT_POOL_SIZE
        assert settings["connection_timeout"] == drv._DEFAULT_CONNECT_TIMEOUT
        assert drv._ENV_POOL_SIZE in caplog.text
        assert drv._ENV_CONNECT_TIMEOUT in caplog.text

    def test_below_minimum_env_is_clamped_with_a_warning(self, monkeypatch, caplog):
        monkeypatch.setenv(drv._ENV_POOL_SIZE, "0")
        monkeypatch.setenv(drv._ENV_CONNECT_TIMEOUT, "-5")

        with caplog.at_level(logging.WARNING, logger=drv.logger.name):
            settings = drv.connection_settings()

        assert settings["max_connection_pool_size"] == 1
        assert settings["connection_timeout"] == 1.0
        assert "minimum" in caplog.text

    def test_retry_settings_are_env_overridable(self, monkeypatch):
        assert drv.retry_attempts() == drv._DEFAULT_RETRY_ATTEMPTS
        assert drv.retry_base_delay() == drv._DEFAULT_RETRY_BASE_DELAY

        monkeypatch.setenv(drv._ENV_RETRY_ATTEMPTS, "5")
        monkeypatch.setenv(drv._ENV_RETRY_BASE_DELAY, "0.05")

        assert drv.retry_attempts() == 5
        assert drv.retry_base_delay() == 0.05


class TestRetryClassification:
    def test_circuit_open_is_never_retryable(self):
        assert drv.is_retryable_neo4j_error(CircuitOpenError("open")) is False

    @pytest.mark.parametrize(
        "code",
        [
            "Neo.ClientError.Statement.SyntaxError",
            "Neo.ClientError.Statement.TypeError",
            "Neo.ClientError.Statement.ParameterMissing",
            "Neo.ClientError.Statement.ArgumentError",
            "Neo.ClientError.Schema.ConstraintValidationFailed",
        ],
    )
    def test_deterministic_cypher_errors_are_not_retryable(self, code):
        """Reuses is_deterministic_neo4j_error rather than reclassifying."""
        assert drv.is_retryable_neo4j_error(_FakeNeo4jError(code)) is False

    @pytest.mark.parametrize(
        "exc",
        [TransientError("busy"), ServiceUnavailable("no route"), SessionExpired("gone")],
    )
    def test_transient_neo4j_errors_are_retryable(self, exc):
        assert drv.is_retryable_neo4j_error(exc) is True

    @pytest.mark.parametrize("exc", [AuthError("nope"), DatabaseError("broken")])
    def test_neo4j_errors_the_driver_calls_final_are_not_retryable(self, exc):
        assert drv.is_retryable_neo4j_error(exc) is False

    def test_socket_errors_are_retryable(self):
        assert drv.is_retryable_neo4j_error(OSError("connection reset")) is True
        assert drv.is_retryable_neo4j_error(TimeoutError("slow")) is True

    def test_unknown_exceptions_are_not_retryable(self):
        assert drv.is_retryable_neo4j_error(ValueError("caller bug")) is False


class TestRunWithRetry:
    async def test_returns_the_first_success(self):
        calls = []

        async def op():
            calls.append(1)
            return "ok"

        assert await drv.run_with_retry(op, base_delay=0.0) == "ok"
        assert len(calls) == 1

    async def test_retries_a_transient_failure_then_succeeds(self):
        attempts = []

        async def op():
            attempts.append(1)
            if len(attempts) < 3:
                raise ServiceUnavailable("wan blip")
            return "recovered"

        result = await drv.run_with_retry(op, attempts=3, base_delay=0.0)

        assert result == "recovered"
        assert len(attempts) == 3

    async def test_does_not_retry_a_deterministic_error(self):
        attempts = []

        async def op():
            attempts.append(1)
            raise _FakeNeo4jError("Neo.ClientError.Statement.SyntaxError")

        with pytest.raises(_FakeNeo4jError):
            await drv.run_with_retry(op, attempts=3, base_delay=0.0)

        assert len(attempts) == 1

    async def test_exhausts_attempts_and_raises_the_last_error(self):
        attempts = []

        async def op():
            attempts.append(1)
            raise ServiceUnavailable(f"down {len(attempts)}")

        with pytest.raises(ServiceUnavailable, match="down 3"):
            await drv.run_with_retry(op, attempts=3, base_delay=0.0)

        assert len(attempts) == 3

    async def test_an_open_breaker_fails_fast_without_running_the_operation(self):
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        breaker.record_failure()
        assert breaker.state == CBState.OPEN

        ran = []

        async def op():
            ran.append(1)
            return "should not happen"

        with pytest.raises(CircuitOpenError):
            await drv.run_with_retry(op, breaker=breaker, base_delay=0.0)

        assert ran == []

    async def test_a_circuit_open_error_from_the_operation_is_not_retried(self):
        attempts = []

        async def op():
            attempts.append(1)
            raise CircuitOpenError("open")

        with pytest.raises(CircuitOpenError):
            await drv.run_with_retry(op, attempts=3, base_delay=0.0)

        assert len(attempts) == 1

    async def test_exhausted_attempts_open_the_breaker(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

        async def op():
            raise ServiceUnavailable("down")

        with pytest.raises(ServiceUnavailable):
            await drv.run_with_retry(op, breaker=breaker, attempts=3, base_delay=0.0)

        assert breaker.state == CBState.OPEN

    async def test_a_recovered_operation_resets_the_breaker(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        attempts = []

        async def op():
            attempts.append(1)
            if len(attempts) == 1:
                raise ServiceUnavailable("blip")
            return "ok"

        assert await drv.run_with_retry(
            op, breaker=breaker, attempts=3, base_delay=0.0
        ) == "ok"
        assert breaker.state == CBState.CLOSED
        assert breaker._failure_count == 0

    async def test_a_deterministic_error_does_not_advance_the_breaker(self):
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)

        async def op():
            raise _FakeNeo4jError("Neo.ClientError.Statement.SyntaxError")

        with pytest.raises(_FakeNeo4jError):
            await drv.run_with_retry(op, breaker=breaker, attempts=3, base_delay=0.0)

        assert breaker.state == CBState.CLOSED
        assert breaker._last_underlying is not None

    async def test_attempts_never_overlap(self):
        """A Neo4j session forbids concurrent queries, so retries are serial."""
        in_flight = 0
        max_in_flight = 0
        attempts = []

        async def op():
            nonlocal in_flight, max_in_flight
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            attempts.append(1)
            await asyncio.sleep(0)
            in_flight -= 1
            if len(attempts) < 3:
                raise ServiceUnavailable("blip")
            return "ok"

        await drv.run_with_retry(op, attempts=3, base_delay=0.0)

        assert len(attempts) == 3
        assert max_in_flight == 1

    async def test_attempts_below_one_still_run_once(self):
        attempts = []

        async def op():
            attempts.append(1)
            return "ok"

        assert await drv.run_with_retry(op, attempts=0, base_delay=0.0) == "ok"
        assert len(attempts) == 1

    async def test_retry_warning_names_the_operation(self, caplog):
        attempts = []

        async def op():
            attempts.append(1)
            if len(attempts) == 1:
                raise ServiceUnavailable("blip")
            return "ok"

        with caplog.at_level(logging.WARNING, logger=drv.logger.name):
            await drv.run_with_retry(
                op, attempts=2, base_delay=0.0, label="init_schema"
            )

        assert "init_schema" in caplog.text
        assert "ServiceUnavailable" in caplog.text
