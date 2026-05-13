"""Circuit breaker for Neo4j backend connections.

Prevents cascading timeouts when Neo4j is unreachable. After a configurable
number of consecutive failures, the breaker opens and subsequent calls fail
immediately (<1ms) instead of waiting for connection timeouts (~30s).

Deterministic Cypher errors (schema constraint violations, syntax errors,
type errors, missing parameters, argument errors) do not advance the
failure counter, because retrying them will not heal: they reflect a bug
in the caller, not a transient network problem. Call sites should still
register such exceptions via :meth:`CircuitBreaker.record_underlying` so
that, if a later transient burst opens the breaker, the user-facing
message can name the most recent underlying cause.
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


# Neo4j error codes that are deterministic (will not heal on retry).
# These should NOT advance the circuit breaker's failure counter.
_DETERMINISTIC_NEO4J_CODES: frozenset[str] = frozenset(
    {
        "Neo.ClientError.Statement.SyntaxError",
        "Neo.ClientError.Statement.TypeError",
        "Neo.ClientError.Statement.ParameterMissing",
        "Neo.ClientError.Statement.ArgumentError",
    }
)

# Any Neo.ClientError.Schema.* code is also deterministic
# (constraint violations, missing constraints, etc.).
_DETERMINISTIC_NEO4J_PREFIXES: tuple[str, ...] = ("Neo.ClientError.Schema.",)


def is_deterministic_neo4j_error(exc: BaseException) -> bool:
    """Return True if ``exc`` is a deterministic Neo4j Cypher error.

    Duck-types on the ``code`` attribute used by ``neo4j.exceptions.Neo4jError``.
    Returns False if the attribute is missing or not a string.
    """
    code = getattr(exc, "code", None)
    if not isinstance(code, str):
        return False
    if code in _DETERMINISTIC_NEO4J_CODES:
        return True
    return any(code.startswith(prefix) for prefix in _DETERMINISTIC_NEO4J_PREFIXES)


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout: float = 60.0  # seconds

    _state: CBState = field(default=CBState.CLOSED, init=False, repr=False)
    _failure_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)
    _last_underlying: BaseException | None = field(default=None, init=False, repr=False)

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

    def record_underlying(self, exc: BaseException) -> None:
        """Remember the most recent underlying exception.

        Stored independently of the failure counter so that deterministic
        errors (which do not advance the counter) still surface their
        cause in any later :class:`CircuitOpenError` message.
        """
        self._last_underlying = exc

    def check(self) -> None:
        """Raise CircuitOpenError if circuit is open. Call before every backend operation."""
        if self.state == CBState.OPEN:
            remaining = self.recovery_timeout - (time.monotonic() - self._last_failure_time)
            msg = f"Neo4j circuit breaker open. Retry in {max(0, remaining):.0f}s"
            if self._last_underlying is not None:
                cause_msg = str(self._last_underlying)
                if len(cause_msg) > 200:
                    cause_msg = cause_msg[:200] + "..."
                cls_name = type(self._last_underlying).__name__
                msg = f"{msg}. Most recent failure: {cls_name}: {cause_msg}"
            raise CircuitOpenError(msg)
