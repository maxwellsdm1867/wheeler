"""Centralized Neo4j driver management.

All modules that need a Neo4j connection should use these functions instead
of creating drivers directly. This ensures consistent configuration,
resource pooling, and proper lifecycle management.

Async driver: singleton, reused across all async queries.
Sync driver: per-call, used by CLI commands only.
"""

from __future__ import annotations

import logging

from neo4j import AsyncGraphDatabase, GraphDatabase, NotificationMinimumSeverity

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)

# Async singleton — reused across queries to avoid 100ms+ creation overhead.
_async_driver = None
_async_driver_uri: str | None = None


def get_async_driver(config: WheelerConfig):
    """Get or create the singleton async Neo4j driver."""
    global _async_driver, _async_driver_uri
    uri = config.neo4j.uri
    if _async_driver is not None and _async_driver_uri == uri:
        logger.debug("Reusing async driver for %s", uri)
        return _async_driver
    logger.info("Creating async Neo4j driver for %s", uri)
    _async_driver = AsyncGraphDatabase.driver(
        uri,
        auth=(config.neo4j.username, config.neo4j.password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )
    _async_driver_uri = uri
    return _async_driver


def get_sync_driver(config: WheelerConfig):
    """Create a new sync Neo4j driver. Caller must close it."""
    return GraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )


async def close_async_driver():
    """Close the singleton async driver. Call on shutdown."""
    global _async_driver, _async_driver_uri
    if _async_driver is not None:
        logger.info("Closing async Neo4j driver")
        await _async_driver.close()
        _async_driver = None
        _async_driver_uri = None


def invalidate_async_driver():
    """Discard the cached async driver without closing it.

    Call after asyncio.run() returns to prevent reuse of a driver
    bound to a now-closed event loop. The driver is not closed because
    its event loop is already dead.
    """
    global _async_driver, _async_driver_uri
    _async_driver = None
    _async_driver_uri = None
