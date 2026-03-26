"""E2E test fixtures: Neo4j connection, sandbox directory, cleanup."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from wheeler.config import WheelerConfig, Neo4jConfig, ProjectMeta, ProjectPaths

SANDBOX_DIR = Path(__file__).parent / "sandbox"

# Test node IDs are prefixed so we can clean them up
E2E_TAG = "e2e_test"


@pytest.fixture(scope="session")
def e2e_config() -> WheelerConfig:
    """WheelerConfig pointing to local Neo4j for e2e tests."""
    return WheelerConfig(
        neo4j=Neo4jConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="research-graph",
            database="neo4j",
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
def sandbox(e2e_config) -> Path:
    """Create sandbox directory with SRM-like test files."""
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

    return SANDBOX_DIR


@pytest.fixture(scope="session")
def neo4j_available(e2e_config) -> bool:
    """Check if Neo4j is reachable."""
    import asyncio
    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _check():
        driver = AsyncGraphDatabase.driver(
            e2e_config.neo4j.uri,
            auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )
        try:
            async with driver.session(database=e2e_config.neo4j.database) as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False
        finally:
            await driver.close()

    return asyncio.run(_check())


@pytest.fixture(autouse=True)
def skip_without_neo4j(neo4j_available):
    """Skip e2e tests if Neo4j is not running."""
    if not neo4j_available:
        pytest.skip("Neo4j not available — skipping e2e tests")


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
    """Clean up e2e test nodes after each test."""
    yield
    if not neo4j_available:
        return
    from wheeler.graph.driver import get_async_driver
    driver = get_async_driver(e2e_config)
    async with driver.session(database=e2e_config.neo4j.database) as session:
        await session.run(
            "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
            tag=E2E_TAG,
        )


@pytest.fixture(scope="session", autouse=True)
def cleanup_graph(e2e_config, neo4j_available):
    """Clean up all e2e test nodes after the test session."""
    yield  # Run tests first

    if not neo4j_available:
        return

    import asyncio
    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _cleanup():
        # Create a fresh driver — can't reuse singleton across event loops
        driver = AsyncGraphDatabase.driver(
            e2e_config.neo4j.uri,
            auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )
        try:
            async with driver.session(database=e2e_config.neo4j.database) as session:
                await session.run(
                    "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
                    tag=E2E_TAG,
                )
        finally:
            await driver.close()

    asyncio.run(_cleanup())
