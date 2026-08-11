"""E2E test fixtures: Neo4j connection, sandbox directory, cleanup."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from wheeler.config import WheelerConfig, Neo4jConfig, ProjectMeta, ProjectPaths

# Test nodes are tagged with this so we can clean them up. It must be BOTH
# unique per process AND stable across duplicate imports of this module:
#
#   * Unique per process, because ``cleanup_test_nodes`` is autouse and
#     function-scoped and its delete is global ("MATCH (n) WHERE n.e2e_tag =
#     $tag DETACH DELETE n"). With one shared literal, every test in every
#     session deletes every OTHER concurrent session's in-flight nodes, which
#     surfaces as "Node X not found in graph" mid-test.
#   * Stable across imports, because tests/e2e/ has no __init__.py, so this file
#     is imported TWICE per process: once by pytest as ``conftest`` (the copy
#     that supplies the fixtures) and once as ``tests.e2e.conftest`` (the copy
#     the test modules read E2E_TAG from). A bare module-level uuid4() would
#     mint a different tag in each copy, so the fixtures would clean a tag no
#     test ever wrote and every node would leak.
#
# Caching in the environment makes the value process-global rather than
# module-global. The cache is keyed on the pid so a value inherited from a
# parent process is replaced rather than shared with a sibling session.
_TAG_ENV = "WHEELER_E2E_TAG"
_TAG_PREFIX = f"e2e_test_{os.getpid()}_"


def _process_e2e_tag() -> str:
    """Return this process's e2e tag, minting it once on first import."""
    cached = os.environ.get(_TAG_ENV, "")
    if cached.startswith(_TAG_PREFIX):
        return cached
    tag = _TAG_PREFIX + uuid.uuid4().hex
    os.environ[_TAG_ENV] = tag
    return tag


E2E_TAG = _process_e2e_tag()

# The sandbox is a real on-disk project tree. It is per process, and it lives
# outside the checkout:
#   * Per process, because the ``sandbox`` fixture rmtree's and rewrites it and
#     tests read their files back by path. Two sessions sharing one directory
#     read each other's .plans/*.md, so a plan written by one session is
#     reported "unchanged" to the other and the graph_node id in the file
#     belongs to the wrong run.
#   * Outside the checkout, because .gitignore and pyproject's norecursedirs
#     both name the fixed literal tests/e2e/sandbox, so per-run directories
#     inside tests/e2e/ would show up as untracked and be walked at collection.
# It is named after E2E_TAG so a stray directory is traceable to the run (and
# the pid) that made it. resolve() matters on macOS, where the temp dir is a
# /tmp -> /private/tmp symlink: the graph stores resolved paths, so tests that
# compare a stored path against str(sandbox / ...) need the resolved form.
SANDBOX_DIR = (Path(tempfile.gettempdir()) / f"wheeler-{E2E_TAG}").resolve()


@pytest.fixture(scope="session")
def e2e_config() -> WheelerConfig:
    """WheelerConfig pointing at THIS PROJECT'S graph for e2e tests.

    Resolved from the project's own config rather than hardcoded to localhost, so
    the e2e suite exercises the deployment the project actually uses. For this
    repo that is the cloud instance behind the `aura-wheeler` keychain slot: a
    sandbox holding no research data, where an e2e run also covers TLS, WAN
    latency and the transient-retry path a local instance never triggers.

    Tests in this directory must therefore stay additive and self-cleaning. The
    target is shared, so deleting by label or with a bare `MATCH (n)` would take
    other nodes with it; scope every write and every cleanup to a per-run tag.
    """
    from tests.conftest import e2e_neo4j_config

    resolved = e2e_neo4j_config().neo4j
    return WheelerConfig(
        neo4j=Neo4jConfig(
            uri=resolved.uri,
            username=resolved.username,
            password=resolved.password,
            database=resolved.database,
        ),
        project=ProjectMeta(
            name="SRM-E2E-Test",
            description="End-to-end test sandbox for Wheeler with SRM-like data",
        ),
        paths=ProjectPaths(
            code=["scripts/"],
            data=["data/"],
            results=["results/"],
            figures=["figures/"],
            docs=[],
        ),
    )


@pytest.fixture(scope="session")
def sandbox(e2e_config) -> Iterator[Path]:
    """Create this process's sandbox directory with SRM-like test files."""
    # Clean slate
    if SANDBOX_DIR.exists():
        shutil.rmtree(SANDBOX_DIR)

    # Create directory structure
    for d in ["scripts", "data", "results", "figures", ".plans", ".logs", ".wheeler"]:
        (SANDBOX_DIR / d).mkdir(parents=True, exist_ok=True)

    # Create a fake SRM script
    (SANDBOX_DIR / "scripts" / "fit_srm_model.m").write_text(
        "% Spike Response Model fitting\n"
        "% Fits 4-parameter linear-rise-exponential-decay SRM\n"
        "function [params, loss] = fit_srm_model(spikes, stimulus, dt)\n"
        "    params0 = [0.1, 0.5, 10, 0.01]; % tau_rise, tau_decay, threshold, noise\n"
        "    options = optimset('MaxIter', 1000);\n"
        "    [params, loss] = fminsearch(@(p) vp_loss(p, spikes, stimulus, dt), params0, options);\n"
        "end\n"
    )

    # Create a VP loss function
    (SANDBOX_DIR / "scripts" / "compute_vp_loss.m").write_text(
        "% Victor-Purpura spike distance loss function\n"
        "function d = vp_loss(params, observed, predicted, q)\n"
        "    d = spkd(observed, predicted, 1/q);\n"
        "end\n"
    )

    # Create a Python analysis script
    (SANDBOX_DIR / "scripts" / "analyze_population.py").write_text(
        "\"\"\"Population analysis: compare SRM fits across cell types.\"\"\"\n"
        "import numpy as np\n"
        "\n"
        "def compare_fits(parasol_params, midget_params):\n"
        "    return np.abs(parasol_params - midget_params)\n"
    )

    # Create fake data files
    (SANDBOX_DIR / "data" / "parasol_recordings.mat").write_bytes(b"fake mat data")
    (SANDBOX_DIR / "data" / "midget_recordings.mat").write_bytes(b"fake mat data")
    (SANDBOX_DIR / "data" / "srm_fit_results.csv").write_text(
        "cell_type,tau_rise,tau_decay,threshold,noise,vp_loss\n"
        "parasol_on,0.12,0.48,9.8,0.012,0.15\n"
        "parasol_off,0.11,0.52,10.1,0.009,0.18\n"
        "midget_on,0.14,0.45,11.2,0.015,0.22\n"
        "midget_off,0.13,0.50,10.8,0.011,0.19\n"
    )

    yield SANDBOX_DIR

    # Best-effort teardown, matching cleanup_test_nodes: a filesystem hiccup
    # here must not turn a passing session into an ERROR.
    try:
        shutil.rmtree(SANDBOX_DIR)
    except Exception:
        logging.getLogger(__name__).warning(
            "e2e sandbox: could not remove %s (best-effort)",
            SANDBOX_DIR,
            exc_info=True,
        )


def _probe_neo4j(e2e_config) -> bool:
    """Return True if Neo4j answers RETURN 1, else False. Never raises."""
    import asyncio
    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _check():
        driver = AsyncGraphDatabase.driver(
            e2e_config.neo4j.uri,
            auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
            connection_acquisition_timeout=5,
        )
        try:
            async with driver.session(database=e2e_config.neo4j.database) as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False
        finally:
            await driver.close()

    try:
        return asyncio.run(_check())
    except Exception:
        return False


@pytest.fixture(scope="function")
def neo4j_available(e2e_config) -> bool:
    """Whether Neo4j is reachable RIGHT NOW (re-checked per test).

    Function-scoped on purpose: a session-scoped check caches the start-of-session
    result, so a transient Neo4j outage mid-session (common under full-suite load)
    would leave tests trusting a stale True and ERRORING on their own connection
    instead of skipping cleanly. Re-probing per test turns a mid-run outage into
    deterministic skips, never errors.
    """
    return _probe_neo4j(e2e_config)


@pytest.fixture(autouse=True)
def skip_without_neo4j(neo4j_available):
    """Skip e2e tests if Neo4j is not reachable for this test."""
    if not neo4j_available:
        pytest.skip("Neo4j not available -- skipping e2e test")


@pytest.fixture(autouse=True)
def reset_driver_singleton():
    """Reset the async driver singleton before each test.

    Each pytest-asyncio test gets its own event loop, so the singleton
    driver from a previous test would be attached to a dead loop.
    """
    import wheeler.graph.driver as drv
    drv._async_driver = None
    drv._async_driver_uri = None
    yield
    drv._async_driver = None
    drv._async_driver_uri = None


@pytest.fixture(autouse=True)
async def cleanup_test_nodes(e2e_config, neo4j_available):
    """Clean up e2e test nodes after each test (best-effort).

    Tolerant of a transient Neo4j failure during teardown: a hiccup here must not
    turn a passing test into an ERROR, so the cleanup is wrapped and logged.
    """
    yield
    if not neo4j_available:
        return
    try:
        from wheeler.graph.driver import get_async_driver
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            await session.run(
                "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
                tag=E2E_TAG,
            )
    except Exception:
        logging.getLogger(__name__).warning(
            "e2e cleanup_test_nodes: Neo4j unavailable during teardown (best-effort)",
            exc_info=True,
        )


@pytest.fixture(scope="session", autouse=True)
def cleanup_graph(e2e_config):
    """Clean up all e2e test nodes after the test session (best-effort).

    Session-scoped, so it does its OWN Neo4j probe (it cannot depend on the
    function-scoped ``neo4j_available``) and never raises: a teardown-time outage
    must not fail the session.
    """
    yield  # Run tests first

    import asyncio
    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _cleanup():
        # Create a fresh driver -- can't reuse the singleton across event loops.
        driver = AsyncGraphDatabase.driver(
            e2e_config.neo4j.uri,
            auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
            connection_acquisition_timeout=5,
        )
        try:
            async with driver.session(database=e2e_config.neo4j.database) as session:
                await session.run(
                    "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
                    tag=E2E_TAG,
                )
        finally:
            await driver.close()

    try:
        asyncio.run(_cleanup())
    except Exception:
        logging.getLogger(__name__).warning(
            "e2e cleanup_graph: Neo4j unavailable at session teardown (best-effort)",
            exc_info=True,
        )
