"""Circuit breaker for Neo4j backend connections.

Prevents cascading timeouts when Neo4j is unreachable. After a configurable
number of consecutive failures, the breaker opens and subsequent calls fail
immediately (<1ms) instead of waiting for connection timeouts (~30s).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CBState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open. Caller should fail fast."""


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout: float = 60.0  # seconds

    _state: CBState = field(default=CBState.CLOSED, init=False, repr=False)
    _failure_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)

    @property
    def state(self) -> CBState:
        if self._state == CBState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CBState.HALF_OPEN
                logger.info("Circuit breaker -> HALF_OPEN (probing)")
        return self._state

    def record_success(self) -> None:
        if self._state != CBState.CLOSED:
            logger.info("Circuit breaker -> CLOSED (recovered)")
        self._failure_count = 0
        self._state = CBState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CBState.OPEN
            logger.warning(
                "Circuit breaker -> OPEN (failures=%d, retry in %.0fs)",
                self._failure_count,
                self.recovery_timeout,
            )

    def check(self) -> None:
        """Raise CircuitOpenError if circuit is open. Call before every backend operation."""
        if self.state == CBState.OPEN:
            remaining = self.recovery_timeout - (time.monotonic() - self._last_failure_time)
            raise CircuitOpenError(
                f"Neo4j circuit breaker open. Retry in {max(0, remaining):.0f}s"
            )
