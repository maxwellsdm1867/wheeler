"""Tests for the Neo4j circuit breaker."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from wheeler.graph.circuit_breaker import (
    CBState,
    CircuitBreaker,
    CircuitOpenError,
    is_deterministic_neo4j_error,
)


class _FakeNeo4jError(Exception):
    """Mimics neo4j.exceptions.Neo4jError: an exception with a `code` attribute."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def test_initial_state_is_closed():
    cb = CircuitBreaker()
    assert cb.state == CBState.CLOSED


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    assert cb.state == CBState.CLOSED
    cb.record_failure()
    assert cb.state == CBState.CLOSED
    cb.record_failure()
    assert cb.state == CBState.OPEN


def test_check_raises_when_open():
    cb = CircuitBreaker(failure_threshold=1)
    cb.record_failure()
    assert cb.state == CBState.OPEN
    with pytest.raises(CircuitOpenError, match="circuit breaker open"):
        cb.check()


def test_check_passes_when_closed():
    cb = CircuitBreaker()
    # Should not raise
    cb.check()


def test_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    assert cb.state == CBState.OPEN

    # Simulate time passing beyond recovery_timeout
    with patch("wheeler.graph.circuit_breaker.time") as mock_time:
        # First call to monotonic() is in the state property check
        # _last_failure_time was set by record_failure; we need elapsed >= recovery_timeout
        mock_time.monotonic.return_value = cb._last_failure_time + 0.2
        assert cb.state == CBState.HALF_OPEN


def test_success_closes_from_half_open():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    assert cb.state == CBState.OPEN

    # Force into HALF_OPEN
    with patch("wheeler.graph.circuit_breaker.time") as mock_time:
        mock_time.monotonic.return_value = cb._last_failure_time + 0.2
        assert cb.state == CBState.HALF_OPEN

    cb.record_success()
    assert cb.state == CBState.CLOSED


def test_failure_in_half_open_reopens():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()

    # Force into HALF_OPEN
    with patch("wheeler.graph.circuit_breaker.time") as mock_time:
        mock_time.monotonic.return_value = cb._last_failure_time + 0.2
        assert cb.state == CBState.HALF_OPEN

    # Another failure should reopen
    cb.record_failure()
    assert cb.state == CBState.OPEN


def test_success_resets_count():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    # Two failures, one away from opening
    cb.record_success()
    # Count is reset, so two more failures should not open
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CBState.CLOSED
    # Third failure (from reset) opens it
    cb.record_failure()
    assert cb.state == CBState.OPEN


def test_custom_threshold_and_timeout():
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=120.0)
    for _ in range(4):
        cb.record_failure()
    assert cb.state == CBState.CLOSED
    cb.record_failure()
    assert cb.state == CBState.OPEN


def test_check_message_includes_retry_time():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
    cb.record_failure()
    with pytest.raises(CircuitOpenError, match=r"Retry in \d+s"):
        cb.check()


# -- Deterministic-vs-transient error classification (issue #31) --


def test_is_deterministic_schema_constraint_violation():
    exc = _FakeNeo4jError("Neo.ClientError.Schema.ConstraintValidationFailed", "dup id")
    assert is_deterministic_neo4j_error(exc) is True


def test_is_deterministic_statement_syntax_error():
    exc = _FakeNeo4jError("Neo.ClientError.Statement.SyntaxError", "bad cypher")
    assert is_deterministic_neo4j_error(exc) is True


def test_is_deterministic_plain_connection_error_is_false():
    exc = ConnectionError("refused")
    assert is_deterministic_neo4j_error(exc) is False


def test_is_deterministic_no_code_attribute_is_false():
    exc = RuntimeError("boom")
    assert is_deterministic_neo4j_error(exc) is False


def test_deterministic_failures_do_not_advance_counter():
    cb = CircuitBreaker(failure_threshold=3)
    deterministic = _FakeNeo4jError(
        "Neo.ClientError.Schema.ConstraintValidationFailed", "dup id"
    )
    # Simulate the call-site logic: deterministic errors only call
    # record_underlying, not record_failure.
    for _ in range(5):
        assert is_deterministic_neo4j_error(deterministic) is True
        cb.record_underlying(deterministic)
    assert cb._failure_count == 0
    assert cb.state == CBState.CLOSED


def test_open_message_includes_last_underlying_cause():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    transient = ConnectionError("Connection refused on bolt://localhost:7687")
    for _ in range(3):
        cb.record_failure()
        cb.record_underlying(transient)
    assert cb.state == CBState.OPEN
    with pytest.raises(CircuitOpenError) as excinfo:
        cb.check()
    msg = str(excinfo.value)
    assert "Neo4j circuit breaker open" in msg
    assert "Most recent failure: ConnectionError:" in msg
    assert "Connection refused on bolt://localhost:7687" in msg


def test_open_message_truncates_long_cause():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
    long_text = "x" * 500
    transient = ConnectionError(long_text)
    cb.record_failure()
    cb.record_underlying(transient)
    with pytest.raises(CircuitOpenError) as excinfo:
        cb.check()
    msg = str(excinfo.value)
    # 200-char cap + ellipsis
    assert "..." in msg
    # Ensure not the entire 500-char payload made it through
    assert long_text not in msg
