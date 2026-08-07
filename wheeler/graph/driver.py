"""Centralized Neo4j driver management.

All modules that need a Neo4j connection should use these functions instead
of creating drivers directly. This ensures consistent configuration,
resource pooling, and proper lifecycle management.

Async driver: singleton, reused across all async queries.
Sync driver: per-call, used by CLI commands only.

Connection settings (pool size, timeouts) are tuned so a remote database
(Neo4j Aura over ``neo4j+s://``) survives a WAN blip, while staying harmless
against a local Desktop instance. They are read from ``WHEELER_NEO4J_*``
environment variables rather than ``Neo4jConfig`` so they can be adjusted
without a config-schema change; folding them into ``Neo4jConfig`` is the
natural follow-up.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import hashlib
import logging
import os
import random
from typing import Any, TypeVar

from neo4j import AsyncGraphDatabase, GraphDatabase, NotificationMinimumSeverity

from wheeler.config import WheelerConfig
from wheeler.graph.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    is_deterministic_neo4j_error,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# -- connection settings --
# Defaults picked to work against a remote database without being wrong for a
# local one:
#   pool size   50   far more than a single-user research session opens, and
#                    under the connection cap of an Aura Free instance.
#   acquisition 30s  a request that cannot get a pooled connection in half a
#                    minute is not going to get one.
#   lifetime  1800s  Aura sits behind a load balancer that quietly drops
#                    long-lived connections, so recycle before it does.
#   connect     15s  enough for a TLS handshake across a WAN, short enough
#                    that an unreachable host fails while you are watching.
_DEFAULT_POOL_SIZE = 50
_DEFAULT_ACQUISITION_TIMEOUT = 30.0
_DEFAULT_MAX_LIFETIME = 1800.0
_DEFAULT_CONNECT_TIMEOUT = 15.0

_ENV_POOL_SIZE = "WHEELER_NEO4J_POOL_SIZE"
_ENV_ACQUISITION_TIMEOUT = "WHEELER_NEO4J_ACQUISITION_TIMEOUT"
_ENV_MAX_LIFETIME = "WHEELER_NEO4J_MAX_LIFETIME"
_ENV_CONNECT_TIMEOUT = "WHEELER_NEO4J_CONNECT_TIMEOUT"

# -- retry settings --
# 3 attempts with 0.25s exponential backoff adds at most ~0.75s of sleep to a
# doomed operation, which is cheap next to the connect timeout above.
_DEFAULT_RETRY_ATTEMPTS = 3
_DEFAULT_RETRY_BASE_DELAY = 0.25
_ENV_RETRY_ATTEMPTS = "WHEELER_NEO4J_RETRY_ATTEMPTS"
_ENV_RETRY_BASE_DELAY = "WHEELER_NEO4J_RETRY_BASE_DELAY"
# Jitter as a fraction of the computed delay, so concurrent processes that
# lost the same connection do not all come back at the same instant.
_RETRY_JITTER = 0.25

# Async singleton — reused across queries to avoid 100ms+ creation overhead.
_async_driver = None
# Authoritative cache key: see `_driver_key`.
_async_driver_key: tuple[str, str, str, str] | None = None
# The URI component of the key, kept as its own global for logging and for
# callers that only care which host the cached driver points at.
_async_driver_uri: str | None = None


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    """Read an int from the environment, falling back loudly on garbage."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning("%s=%r is not an integer, using %d", name, raw, default)
        return default
    if value < minimum:
        logger.warning(
            "%s=%d is below the minimum %d, using %d", name, value, minimum, minimum
        )
        return minimum
    return value


def _env_float(name: str, default: float, *, minimum: float = 0.0) -> float:
    """Read a float from the environment, falling back loudly on garbage."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw.strip())
    except ValueError:
        logger.warning("%s=%r is not a number, using %s", name, raw, default)
        return default
    if value < minimum:
        logger.warning(
            "%s=%s is below the minimum %s, using %s", name, value, minimum, minimum
        )
        return minimum
    return value


def connection_settings() -> dict[str, Any]:
    """Driver connection settings as a kwargs dict.

    Returned as one dict so the async and sync drivers cannot drift apart.
    Typed loosely because the neo4j driver constructors are heavily
    overloaded and reject a narrowed ``**kwargs`` mapping.
    """
    return {
        "max_connection_pool_size": _env_int(_ENV_POOL_SIZE, _DEFAULT_POOL_SIZE),
        "connection_acquisition_timeout": _env_float(
            _ENV_ACQUISITION_TIMEOUT, _DEFAULT_ACQUISITION_TIMEOUT, minimum=1.0
        ),
        "max_connection_lifetime": _env_float(
            _ENV_MAX_LIFETIME, _DEFAULT_MAX_LIFETIME, minimum=1.0
        ),
        "connection_timeout": _env_float(
            _ENV_CONNECT_TIMEOUT, _DEFAULT_CONNECT_TIMEOUT, minimum=1.0
        ),
    }


def _driver_key(config: WheelerConfig) -> tuple[str, str, str, str]:
    """Identity of a driver: everything that changes who we connect as.

    Keying on the URI alone was a latent bug: rotate the password or switch
    user while the URI stays put and the stale driver, still holding the old
    credentials, was silently handed back. The password is folded in as a
    short digest rather than plaintext so rotation invalidates the cache
    without parking the secret in a module global.

    The database is part of the key even though sessions select it per call:
    it costs at most one extra driver per identity change and keeps the cache
    honest if the driver ever gets constructed with a default database.
    """
    neo4j_cfg = config.neo4j
    pw_digest = hashlib.sha256(neo4j_cfg.password.encode("utf-8")).hexdigest()[:16]
    return (neo4j_cfg.uri, neo4j_cfg.username, neo4j_cfg.database, pw_digest)


def get_async_driver(config: WheelerConfig):
    """Get or create the singleton async Neo4j driver."""
    global _async_driver, _async_driver_key, _async_driver_uri
    key = _driver_key(config)
    if _async_driver is not None and _async_driver_key == key:
        logger.debug("Reusing async driver for %s", key[0])
        return _async_driver
    if _async_driver is not None:
        # Deliberately not closed: closing is async and this is a sync
        # function. Same trade-off as `invalidate_async_driver` below.
        logger.info("Neo4j connection identity changed, replacing cached async driver")
    settings = connection_settings()
    logger.info(
        "Creating async Neo4j driver for %s (database=%s, pool=%s, connect_timeout=%ss)",
        key[0],
        key[2],
        settings["max_connection_pool_size"],
        settings["connection_timeout"],
    )
    _async_driver = AsyncGraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
        **settings,
    )
    _async_driver_key = key
    _async_driver_uri = key[0]
    return _async_driver


def get_sync_driver(config: WheelerConfig):
    """Create a new sync Neo4j driver. Caller must close it."""
    return GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
        **connection_settings(),
    )


async def close_async_driver():
    """Close the singleton async driver. Call on shutdown."""
    global _async_driver, _async_driver_key, _async_driver_uri
    if _async_driver is not None:
        logger.info("Closing async Neo4j driver")
        await _async_driver.close()
        _async_driver = None
        _async_driver_key = None
        _async_driver_uri = None


def invalidate_async_driver():
    """Discard the cached async driver without closing it.

    Call after asyncio.run() returns to prevent reuse of a driver
    bound to a now-closed event loop. The driver is not closed because
    its event loop is already dead.
    """
    global _async_driver, _async_driver_key, _async_driver_uri
    _async_driver = None
    _async_driver_key = None
    _async_driver_uri = None


# -- retry --


def retry_attempts() -> int:
    """Total attempts (not extra retries) for a retryable operation."""
    return _env_int(_ENV_RETRY_ATTEMPTS, _DEFAULT_RETRY_ATTEMPTS)


def retry_base_delay() -> float:
    """Backoff base in seconds; attempt N sleeps base * 2**(N-1) plus jitter."""
    return _env_float(_ENV_RETRY_BASE_DELAY, _DEFAULT_RETRY_BASE_DELAY)


def is_retryable_neo4j_error(exc: BaseException) -> bool:
    """Whether ``exc`` is worth one more attempt.

    Classification is delegated, never duplicated:

    - ``CircuitOpenError`` is the breaker saying stop. Never retried.
    - :func:`is_deterministic_neo4j_error` already names the Cypher errors
      that reflect a caller bug (syntax, type, parameter, schema). Retrying
      those just repeats the bug.
    - Otherwise the neo4j driver's own ``is_retryable()`` decides: True for
      ``TransientError``, ``ServiceUnavailable`` and ``SessionExpired``,
      False for ``ClientError`` (auth included), ``DatabaseError``, and
      ``IncompleteCommit`` (a commit whose outcome is unknown must not be
      replayed).
    - An exception without that method is retried only if it is an
      ``OSError``, i.e. a socket-level blip.
    """
    if isinstance(exc, CircuitOpenError):
        return False
    if is_deterministic_neo4j_error(exc):
        return False
    classify = getattr(exc, "is_retryable", None)
    if callable(classify):
        try:
            return bool(classify())
        except Exception:  # pragma: no cover - defensive
            return False
    return isinstance(exc, OSError)


async def run_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    breaker: CircuitBreaker | None = None,
    attempts: int | None = None,
    base_delay: float | None = None,
    label: str = "neo4j operation",
) -> T:
    """Await ``operation()`` again when it fails transiently.

    ``operation`` is an async *factory*, called once per attempt, so every
    attempt opens its own session: retrying a half-consumed result is not a
    thing. Attempts are strictly sequential. A Neo4j session does not allow
    concurrent queries, so there is no ``asyncio.gather`` here and callers
    must not add one.

    ``breaker`` is honoured, never bypassed: it is checked before each
    attempt, a ``CircuitOpenError`` propagates immediately, and each failed
    attempt is recorded exactly as a direct call would record it (transient
    failures advance the counter, deterministic ones only set the underlying
    cause). Three failed attempts against a default breaker therefore open
    it, which is the intended reading of "Neo4j is not answering".

    Only retryable operations should use this. A status probe that already
    degrades gracefully is better off failing fast.
    """
    max_attempts = attempts if attempts is not None else retry_attempts()
    delay = base_delay if base_delay is not None else retry_base_delay()
    last_exc: BaseException | None = None

    for attempt in range(1, max(1, max_attempts) + 1):
        if breaker is not None:
            breaker.check()
        try:
            result = await operation()
        except CircuitOpenError:
            raise
        except Exception as exc:
            last_exc = exc
            if breaker is not None:
                breaker.record_underlying(exc)
                if not is_deterministic_neo4j_error(exc):
                    breaker.record_failure()
            if attempt >= max_attempts or not is_retryable_neo4j_error(exc):
                raise
            sleep_for = delay * (2 ** (attempt - 1))
            sleep_for += random.uniform(0.0, sleep_for * _RETRY_JITTER)
            logger.warning(
                "%s failed (attempt %d/%d, %s: %s), retrying in %.2fs",
                label,
                attempt,
                max_attempts,
                type(exc).__name__,
                exc,
                sleep_for,
            )
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
        else:
            if breaker is not None:
                breaker.record_success()
            return result

    # Unreachable: the loop either returns or raises. Kept so the function
    # never falls off the end returning None.
    raise last_exc if last_exc is not None else RuntimeError(f"{label} did not run")
