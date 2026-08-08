"""The triple-write must land in the PROJECT root, not the process cwd.

This is the bug Phase 0.2 exists for. A server or CLI spawned in a
subdirectory used to resolve `knowledge/` and `synthesis/` against that
subdirectory, so a finding written from `<project>/analysis/scripts` created
`<project>/analysis/scripts/knowledge/F-xxxx.json` and the project's real
knowledge directory never saw it.

Two layers:
  1. live Neo4j, the real `execute_tool` path end to end. Skipped only when
     Neo4j is unreachable. Nodes are tagged with a per-run `e2e_tag` and the
     teardown deletes EXACTLY by that tag: this config runs on the shared
     default namespace where real user nodes live.
  2. the same assertion against a FakeBackend, so the invariant stays covered
     when Neo4j is down.

Run: python -m pytest tests/test_triple_write_project_root.py -q
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import pytest

from wheeler.config import load_config
from wheeler.tools.graph_tools import execute_tool

PROJECT_YAML = """\
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: research-graph
  database: neo4j
knowledge_path: knowledge
synthesis_path: synthesis
"""


def _make_project(tmp_path: Path) -> tuple[Path, Path]:
    """A project root holding wheeler.yaml, plus a nested working directory."""
    root = tmp_path / "project"
    nested = root / "analysis" / "scripts"
    nested.mkdir(parents=True)
    (root / "wheeler.yaml").write_text(PROJECT_YAML)
    return root, nested


def _assert_landed_in_root(root: Path, nested: Path, node_id: str) -> None:
    """The triple-write files are under the project root and nowhere else."""
    assert (root / "knowledge" / f"{node_id}.json").is_file(), (
        f"knowledge JSON missing from the project root; "
        f"root contents: {sorted(p.name for p in root.iterdir())}"
    )
    assert (root / "synthesis" / f"{node_id}.md").is_file(), (
        "synthesis markdown missing from the project root"
    )
    assert not (nested / "knowledge").exists(), (
        "knowledge/ was created in the cwd instead of the project root"
    )
    assert not (nested / "synthesis").exists(), (
        "synthesis/ was created in the cwd instead of the project root"
    )


# ---------------------------------------------------------------------------
# 1. Live Neo4j: the real execute_tool path
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def neo4j_probe_config():
    from wheeler.config import Neo4jConfig, WheelerConfig

    return WheelerConfig(
        neo4j=Neo4jConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="research-graph",
            database="neo4j",
        ),
    )


@pytest.fixture(scope="module")
def neo4j_available(neo4j_probe_config) -> bool:
    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    cfg = neo4j_probe_config.neo4j

    async def _check() -> bool:
        driver = AsyncGraphDatabase.driver(
            cfg.uri,
            auth=(cfg.username, cfg.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )
        try:
            async with driver.session(database=cfg.database) as s:
                await s.run("RETURN 1")
            return True
        except Exception:
            return False
        finally:
            await driver.close()

    return asyncio.run(_check())


@pytest.fixture(autouse=True)
def _fresh_backend_and_driver():
    """Never inherit (or leak) cached backends: this suite uses a real one.

    Backends are now keyed on config identity, so a poisoned instance can only
    affect tests sharing that exact key -- but a stale breaker for the SAME key
    still leaks, so this fixture is still required. Do not delete it as
    obsolete.

    Each backend owns its circuit breaker. Earlier tests in the full suite feed
    MagicMock values through one, which trips that breaker OPEN for 60s;
    inheriting it makes every write here fail fast. Clearing on the way in gives
    this test the state a fresh process has, and clearing on the way out stops
    the next test inheriting a backend bound to this temp project.
    """
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    gt.reset_backend_cache()
    invalidate_async_driver()
    yield
    gt.reset_backend_cache()
    invalidate_async_driver()


async def _tag_node(cfg, node_id: str, tag: str) -> None:
    """Mark one node with this run's tag so teardown can find just it.

    Async because it is called from inside the running test loop; the teardown
    counterpart is sync because fixture teardown runs outside it.
    """
    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    driver = AsyncGraphDatabase.driver(
        cfg.neo4j.uri,
        auth=(cfg.neo4j.username, cfg.neo4j.password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )
    try:
        async with driver.session(database=cfg.neo4j.database) as s:
            await s.run(
                "MATCH (n) WHERE n.id = $id SET n.e2e_tag = $tag",
                id=node_id,
                tag=tag,
            )
    finally:
        await driver.close()


def _cleanup_by_tag(cfg, tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged.

    EXACTLY ``MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n`` and nothing
    else. This config runs on the shared default namespace, where a broader
    MATCH would delete real user data.
    """
    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _run() -> None:
        driver = AsyncGraphDatabase.driver(
            cfg.neo4j.uri,
            auth=(cfg.neo4j.username, cfg.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )
        try:
            async with driver.session(database=cfg.neo4j.database) as s:
                await s.run(
                    "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
                    tag=tag,
                )
        finally:
            await driver.close()

    asyncio.run(_run())


class TestTripleWriteFromSubdirectoryLive:
    """The requested behavioural check, against the live local Neo4j."""

    @pytest.fixture(autouse=True)
    def _project(self, neo4j_available, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j unreachable at bolt://localhost:7687")
        monkeypatch.delenv("WHEELER_PROJECT_ROOT", raising=False)
        self.root, self.nested = _make_project(tmp_path)
        self.tag = f"project_root_e2e_{uuid.uuid4().hex}"
        # cwd is the nested subdirectory for the whole test: this IS the bug.
        monkeypatch.chdir(self.nested)
        self.config = load_config()
        assert self.config.resolved_project_root == self.root.resolve()
        self.created: list[str] = []
        yield
        _cleanup_by_tag(self.config, self.tag)

    async def _add_finding(self, description: str) -> str:
        result = json.loads(await execute_tool(
            "add_finding",
            {"description": description, "confidence": 0.8},
            self.config,
        ))
        assert "error" not in result, result
        node_id = result["node_id"]
        await _tag_node(self.config, node_id, self.tag)
        self.created.append(node_id)
        return node_id

    async def test_finding_lands_in_project_root_not_cwd(self):
        node_id = await self._add_finding(
            "Triple-write from a nested subdirectory lands in the project root"
        )
        _assert_landed_in_root(self.root, self.nested, node_id)

    async def test_written_json_is_readable_and_carries_the_description(self):
        description = "Resolved-path triple-write round-trips through the JSON layer"
        node_id = await self._add_finding(description)

        payload = json.loads(
            (self.root / "knowledge" / f"{node_id}.json").read_text()
        )
        assert payload["id"] == node_id
        assert payload["description"] == description

    async def test_synthesis_markdown_lands_beside_it(self):
        node_id = await self._add_finding("Synthesis lands in the project root too")

        content = (self.root / "synthesis" / f"{node_id}.md").read_text()
        assert content.startswith("---\n")
        assert f"id: {node_id}" in content

    async def test_node_reached_the_graph(self):
        """Guards against a false pass where the write never happened at all."""
        node_id = await self._add_finding("Graph layer of the triple-write")

        from wheeler.tools.graph_tools import _get_backend

        backend = await _get_backend(self.config)
        rows = await backend.run_cypher(
            "MATCH (n) WHERE n.id = $id RETURN n.id AS id", {"id": node_id}
        )
        assert [r["id"] for r in rows] == [node_id]

    async def test_link_nodes_rerenders_into_the_project_root(self):
        """link_nodes re-renders both endpoints: those writes must not escape either."""
        a = await self._add_finding("Link endpoint A")
        b = await self._add_finding("Link endpoint B")

        result = json.loads(await execute_tool(
            "link_nodes",
            {"source_id": a, "target_id": b, "relationship": "SUPPORTS"},
            self.config,
        ))
        assert result.get("status") == "linked", result

        for node_id in (a, b):
            _assert_landed_in_root(self.root, self.nested, node_id)
        assert "Relationships" in (
            self.root / "synthesis" / f"{a}.md"
        ).read_text()


# ---------------------------------------------------------------------------
# 2. Same invariant with a fake backend, so it is covered without Neo4j
# ---------------------------------------------------------------------------


class _FakeBackend:
    async def create_node(self, label, props):
        return props.get("id", "")

    async def create_relationship(self, *a, **kw):
        return True

    async def run_cypher(self, *a, **kw):
        return []

    async def update_node(self, *a, **kw):
        return True


class TestTripleWriteFromSubdirectoryFake:
    async def test_finding_lands_in_project_root_not_cwd(self, tmp_path, monkeypatch):
        from unittest.mock import AsyncMock, patch

        monkeypatch.delenv("WHEELER_PROJECT_ROOT", raising=False)
        root, nested = _make_project(tmp_path)
        monkeypatch.chdir(nested)
        config = load_config()
        config.search.enabled = False

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=_FakeBackend(),
        ):
            result = json.loads(await execute_tool(
                "add_finding",
                {"description": "Fake-backend subdirectory write", "confidence": 0.5},
                config,
            ))

        _assert_landed_in_root(root, nested, result["node_id"])

    async def test_relative_paths_still_follow_an_explicit_project_root(
        self, tmp_path, monkeypatch
    ):
        """WHEELER_PROJECT_ROOT redirects the triple-write, cwd notwithstanding."""
        from unittest.mock import AsyncMock, patch

        root, nested = _make_project(tmp_path)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(nested)
        monkeypatch.setenv("WHEELER_PROJECT_ROOT", str(elsewhere))
        config = load_config()
        config.search.enabled = False

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=_FakeBackend(),
        ):
            result = json.loads(await execute_tool(
                "add_finding",
                {"description": "Explicit project root wins", "confidence": 0.5},
                config,
            ))

        node_id = result["node_id"]
        assert (elsewhere / "knowledge" / f"{node_id}.json").is_file()
        assert not (root / "knowledge").exists()
        assert not (nested / "knowledge").exists()
