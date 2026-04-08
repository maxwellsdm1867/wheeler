"""Tests for the Neo4j circuit breaker."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from wheeler.graph.circuit_breaker import CBState, CircuitBreaker, CircuitOpenError


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
