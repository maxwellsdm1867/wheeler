"""Tests for wheeler.graph.driver singleton management."""

from __future__ import annotations

import wheeler.graph.driver as drv
from wheeler.graph.driver import invalidate_async_driver


def test_invalidate_async_driver_clears_singleton():
    """invalidate_async_driver() resets the cached driver without closing it."""
    # Arrange: simulate a driver that was created in a previous event loop
    drv._async_driver = "fake-driver"
    drv._async_driver_uri = "bolt://fake:7687"

    # Act
    invalidate_async_driver()

    # Assert: both globals are cleared
    assert drv._async_driver is None
    assert drv._async_driver_uri is None


def test_invalidate_async_driver_noop_when_no_driver():
    """invalidate_async_driver() is safe to call when no driver exists."""
    drv._async_driver = None
    drv._async_driver_uri = None

    # Should not raise
    invalidate_async_driver()

    assert drv._async_driver is None
    assert drv._async_driver_uri is None
