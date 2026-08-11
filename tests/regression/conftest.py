"""Conftest for regression tests that need e2e fixtures.

These reuse the e2e machinery but NOT its target. `tests/e2e/` deliberately runs
against the project's real graph, which for this repo is a cloud instance; these
are regression tests and have no business making network calls. Pointing them at
the same place put 151 tests on the far side of a WAN and took this directory
from seconds to 413s, inside the pre-commit hook, on every commit.

So `e2e_config` is overridden below with a local target. Pytest resolves fixtures
from the nearest conftest, so the imported fixtures that depend on it (sandbox,
neo4j_available, cleanup_*) pick up this one automatically.
"""

from __future__ import annotations

import pytest

# Import e2e fixtures so regression e2e tests can use them. `e2e_config` is
# imported too, then deliberately shadowed by the definition below.
from tests.e2e.conftest import (  # noqa: F401
    e2e_config as _cloud_e2e_config,
    sandbox,
    neo4j_available,
    skip_without_neo4j,
    reset_driver_singleton,
    cleanup_test_nodes,
    cleanup_graph,
)


# Session-scoped to match the fixture it shadows: `cleanup_graph` in
# tests/e2e/conftest.py is session-scoped and depends on this, and a
# narrower scope here is a ScopeMismatch error at collection.
_TEST_PASSWORD = "research-graph"


def _local_test_uri() -> str:
    """The local instance that answers to the documented test password.

    Probed, not guessed. Pinning 7687 made every regression test SKIP the moment
    a different Desktop instance took that port, and guessing by database name
    picked an instance with a different password. One attempt per instance, each
    against a different server, so no server sees enough failures to trip Neo4j's
    auth rate limit.

    Falls back to the stock address, where the caller's own probe will skip
    cleanly if nothing is there.
    """
    try:
        from neo4j import GraphDatabase

        from wheeler import desktop

        for inst in desktop.instances():
            try:
                driver = GraphDatabase.driver(
                    inst.bolt_uri, auth=("neo4j", _TEST_PASSWORD)
                )
                with driver.session(database="neo4j") as session:
                    session.run("RETURN 1").consume()
                driver.close()
                return inst.bolt_uri
            except Exception:
                continue
    except Exception:
        pass
    return "bolt://localhost:7687"


@pytest.fixture(scope="session")
def e2e_config():
    """A LOCAL graph for regression tests. See this module's docstring."""
    from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig

    return WheelerConfig(
        neo4j=Neo4jConfig(
            uri=_local_test_uri(),
            username="neo4j",
            password="research-graph",
            database="neo4j",
        ),
        project=ProjectMeta(name="SRM-E2E-Test"),
    )

__all__ = [
    "e2e_config",
    "sandbox",
    "neo4j_available",
    "skip_without_neo4j",
    "reset_driver_singleton",
    "cleanup_test_nodes",
    "cleanup_graph",
]
