"""Portable paths against this project's real graph.

Runs against whatever `tests/conftest.py::e2e_neo4j_config` resolves, which for
this repo is the cloud instance behind the `aura-wheeler` keychain slot. That is
the point of an e2e test: it exercises TLS, WAN latency and the transient-retry
path that a local instance never triggers.

Every test here is additive and self-cleaning. It creates nodes carrying a unique
per-run `e2e_tag`, asserts against nodes carrying THAT tag, and deletes exactly
those in teardown. Nothing here counts, matches or deletes across the whole
database: the target is a shared sandbox that holds other people's nodes, so a
bare `MATCH (n) DETACH DELETE n` would take them all with it.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def e2e_target():
    """The connection these tests run against, or a skip."""
    from neo4j import GraphDatabase

    from tests.conftest import e2e_neo4j_config

    cfg = e2e_neo4j_config()
    n = cfg.neo4j
    try:
        driver = GraphDatabase.driver(n.uri, auth=(n.username, n.password))
        driver.verify_connectivity()
        driver.close()
    except Exception as exc:
        pytest.skip(f"graph unreachable at {n.uri}: {type(exc).__name__}: {exc}")
    return n.uri, (n.username, n.password), n.database


@pytest.fixture(autouse=True)
def _fresh_backend_and_driver():
    """Never inherit (or leak) cached backends: this suite uses a real one.

    Each backend owns its circuit breaker, and earlier tests in the full suite
    push MagicMock values through one, tripping it OPEN for 60 seconds.
    Inheriting that makes every write here fail fast with `circuit_open` while
    the same test passes in isolation.
    """
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    gt.reset_backend_cache()
    invalidate_async_driver()
    yield
    gt.reset_backend_cache()
    invalidate_async_driver()


@pytest.fixture
async def live_project(tmp_path, monkeypatch, e2e_target):
    """A tmp project on the real graph, plus a tag and a teardown that uses it.

    ASYNC on purpose. A sync fixture would have to spin its own loop with
    `asyncio.run()` to clean up, and the Neo4j driver is bound to the loop the
    test ran on: the delete then fails with "attached to a different loop" and the
    run's nodes survive in a shared sandbox. `asyncio_mode = "auto"` runs this on
    the test's own loop.
    """
    from wheeler import config as config_mod
    from wheeler import machine
    from wheeler.config import Neo4jConfig, WheelerConfig

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    machine.reset_cache()
    config_mod.reset_roots_cache()

    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    script = root / "src" / "pipeline.py"
    script.write_text("import numpy\n# pipeline\n")
    monkeypatch.setenv("WHEELER_PROJECT_ROOT", str(root))

    uri, auth, database = e2e_target
    cfg = WheelerConfig(
        neo4j=Neo4jConfig(uri=uri, username=auth[0], password=auth[1], database=database)
    )
    cfg.search.enabled = False
    tag = f"portable_e2e_{uuid.uuid4().hex[:10]}"

    yield cfg, root, script, tag

    # Teardown: delete ONLY this run's nodes. Never a bare MATCH (n): the target
    # is a shared sandbox holding other people's nodes.
    try:
        from wheeler.tools.graph_tools import _get_backend

        backend = await _get_backend(cfg)
        await backend.run_cypher(
            "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n", {"tag": tag}
        )
    finally:
        machine.reset_cache()
        config_mod.reset_roots_cache()


async def _tag(cfg, tag: str, *node_ids: str) -> None:
    """Mark nodes as this run's, so teardown can find them."""
    from wheeler.tools.graph_tools import _get_backend

    ids = [i for i in node_ids if i]
    if not ids:
        return
    backend = await _get_backend(cfg)
    await backend.run_cypher(
        "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag", {"ids": ids, "tag": tag}
    )


class TestPortablePathsLive:
    async def test_artifact_round_trips_through_a_real_graph(self, live_project):
        """Register a real file, read the node back, resolve it, open the file."""
        from wheeler.portability import resolve
        from wheeler.tools.graph_tools import _get_backend, execute_tool

        cfg, root, script, tag = live_project

        created = json.loads(
            await execute_tool(
                "ensure_artifact", {"path": str(script), "language": "python"}, cfg
            )
        )
        assert "error" not in created, created
        await _tag(cfg, tag, created["node_id"])
        assert created["stored_path"] == "${PROJECT}/src/pipeline.py"

        backend = await _get_backend(cfg)
        rows = await backend.run_cypher(
            "MATCH (n:Script {id: $id}) RETURN n.path AS path, "
            "n.origin_machine AS machine, n.origin_database AS db",
            {"id": created["node_id"]},
        )
        assert rows, "node was not written to the graph"
        assert rows[0]["path"] == "${PROJECT}/src/pipeline.py"
        assert rows[0]["db"] == cfg.neo4j.database

        # The stored value, read back out of a real database, still opens.
        resolved = resolve(rows[0]["path"], cfg.resolved_roots)
        assert resolved is not None
        assert resolved.read_text() == "import numpy\n# pipeline\n"

        # And the JSON layer agrees with the graph.
        record = json.loads(
            (root / "knowledge" / f"{created['node_id']}.json").read_text()
        )
        assert record["path"] == rows[0]["path"]
        assert record["origin_machine"] == rows[0]["machine"]

    async def test_second_call_from_another_cwd_does_not_duplicate(
        self, live_project, tmp_path
    ):
        """The same file registered twice, from a different cwd, is one node."""
        import os

        from wheeler.tools.graph_tools import _get_backend, execute_tool

        cfg, root, script, tag = live_project

        first = json.loads(
            await execute_tool(
                "ensure_artifact", {"path": str(script), "language": "python"}, cfg
            )
        )
        await _tag(cfg, tag, first["node_id"])

        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        previous = Path.cwd()
        try:
            os.chdir(elsewhere)
            second = json.loads(
                await execute_tool(
                    "ensure_artifact", {"path": str(script), "language": "python"}, cfg
                )
            )
        finally:
            os.chdir(previous)
        await _tag(cfg, tag, second.get("node_id", ""))

        assert second["node_id"] == first["node_id"]
        assert second["action"] == "unchanged"

        # Scoped to THIS run's stored path, never to every Script in the graph.
        backend = await _get_backend(cfg)
        rows = await backend.run_cypher(
            "MATCH (n:Script) WHERE n.path = $p RETURN count(n) AS n",
            {"p": first["stored_path"]},
        )
        assert rows[0]["n"] == 1, "a duplicate Script node was created"

    async def test_legacy_absolute_node_is_adopted_and_upgraded(self, live_project):
        """A pre-portable node in a real graph is found, not duplicated."""
        from wheeler.graph.provenance import hash_file
        from wheeler.tools.graph_tools import _get_backend, execute_tool

        cfg, root, script, tag = live_project
        legacy_id = f"S-{uuid.uuid4().hex[:8]}"

        backend = await _get_backend(cfg)
        await backend.create_node("Script", {
            "id": legacy_id,
            "path": str(script),          # absolute, as written before this change
            "hash": hash_file(script),
            "language": "python",
            "e2e_tag": tag,
        })

        result = json.loads(
            await execute_tool(
                "ensure_artifact", {"path": str(script), "language": "python"}, cfg
            )
        )
        await _tag(cfg, tag, result.get("node_id", ""))

        assert result["node_id"] == legacy_id
        assert result["path_upgraded"] is True

        rows = await backend.run_cypher(
            "MATCH (n:Script) WHERE n.e2e_tag = $tag RETURN n.id AS id, n.path AS path",
            {"tag": tag},
        )
        assert len(rows) == 1, "the legacy node was duplicated rather than adopted"
        assert rows[0]["path"] == "${PROJECT}/src/pipeline.py"

    async def test_staleness_does_not_cascade_for_another_machine(self, live_project):
        """A graph written elsewhere must not invalidate itself when opened here."""
        from wheeler.provenance import detect_and_propagate_stale
        from wheeler.tools.graph_tools import _get_backend

        cfg, root, script, tag = live_project
        foreign_id = f"S-{uuid.uuid4().hex[:8]}"

        backend = await _get_backend(cfg)
        await backend.create_node("Script", {
            "id": foreign_id,
            "path": "${GDRIVE}/pipeline.py",
            "hash": "written-on-the-other-laptop",
            "language": "python",
            "origin_machine": "some-other-machine-uuid",
            "origin_host": "home-linux",
            "e2e_tag": tag,
        })

        report = await detect_and_propagate_stale(cfg)

        # Scoped assertions: the sandbox holds other nodes whose files are not
        # here either, so assert on THIS node rather than on global totals.
        assert report["by_reason"].get("absent", 0) >= 1
        rows = await backend.run_cypher(
            "MATCH (n:Script {id: $id}) RETURN n.stale AS stale", {"id": foreign_id}
        )
        assert not rows[0]["stale"], "a foreign node was marked stale"
