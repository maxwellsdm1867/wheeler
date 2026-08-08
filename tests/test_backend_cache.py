"""Guard tests for backend cache keying.

`_get_backend(config)` used to honour its `config` argument on the first call
and ignore it forever after, which made the parameter a lie. Two consequences,
both of which these tests pin:

  * The triple-write could split across projects: the graph leg came from the
    cached backend while the JSON and synthesis legs came from the `config`
    threaded separately into `_write_knowledge_file`.
  * One circuit breaker served every project, since the breaker is built in
    `Neo4jBackend.__init__`.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


def _config(*, uri="bolt://localhost:7687", tag="", root="/tmp/proj-a", password="pw"):
    """A duck-typed config of the shape the cache key reads."""
    return SimpleNamespace(
        neo4j=SimpleNamespace(
            uri=uri,
            username="neo4j",
            password=password,
            database="neo4j",
            project_tag=tag,
            # Read by Neo4jBackend.__init__ when a test builds a real one.
            cb_failure_threshold=3,
            cb_recovery_timeout=60,
        ),
        resolved_project_root=root,
    )


@pytest.fixture(autouse=True)
def _clean_cache():
    import wheeler.tools.graph_tools as gt

    gt.reset_backend_cache()
    yield
    gt.reset_backend_cache()


class TestKeying:
    async def test_same_config_returns_the_same_backend(self):
        import wheeler.tools.graph_tools as gt

        with patch("wheeler.graph.backend.get_backend") as factory:
            factory.side_effect = lambda cfg: SimpleNamespace(initialize=AsyncMock())
            a = await gt._get_backend(_config())
            b = await gt._get_backend(_config())
        assert a is b, "identical configs should share one backend"

    async def test_different_project_tag_gets_a_different_backend(self):
        import wheeler.tools.graph_tools as gt

        with patch("wheeler.graph.backend.get_backend") as factory:
            factory.side_effect = lambda cfg: SimpleNamespace(initialize=AsyncMock())
            a = await gt._get_backend(_config(tag="proj-a"))
            b = await gt._get_backend(_config(tag="proj-b"))
        assert a is not b

    async def test_different_project_root_gets_a_different_backend(self):
        """The dimension that produced the split triple-write.

        Same Neo4j settings, different project root, is the ordinary
        Community-Edition case whenever project_tag is unset.
        """
        import wheeler.tools.graph_tools as gt

        with patch("wheeler.graph.backend.get_backend") as factory:
            factory.side_effect = lambda cfg: SimpleNamespace(initialize=AsyncMock())
            a = await gt._get_backend(_config(root="/tmp/proj-a"))
            b = await gt._get_backend(_config(root="/tmp/proj-b"))
        assert a is not b

    async def test_rotated_password_gets_a_different_backend(self):
        """Must agree with the async driver's key, which also digests the password."""
        import wheeler.tools.graph_tools as gt

        with patch("wheeler.graph.backend.get_backend") as factory:
            factory.side_effect = lambda cfg: SimpleNamespace(initialize=AsyncMock())
            a = await gt._get_backend(_config(password="old"))
            b = await gt._get_backend(_config(password="new"))
        assert a is not b

    async def test_config_argument_is_actually_honoured(self):
        """The bug in one line: the second config used to be discarded."""
        import wheeler.tools.graph_tools as gt

        seen = []

        def factory(cfg):
            seen.append(cfg.neo4j.project_tag)
            return SimpleNamespace(initialize=AsyncMock())

        with patch("wheeler.graph.backend.get_backend", side_effect=factory):
            await gt._get_backend(_config(tag="proj-a"))
            await gt._get_backend(_config(tag="proj-b"))
        assert seen == ["proj-a", "proj-b"]


class TestBreakerIsolation:
    async def test_each_project_gets_its_own_circuit_breaker(self):
        """One project's failures must not fail-fast another's traffic.

        Asserted on the real Neo4jBackend, since the breaker is built in
        __init__ and that is the property being relied on.
        """
        import wheeler.tools.graph_tools as gt
        from wheeler.graph.neo4j_backend import Neo4jBackend

        with patch.object(Neo4jBackend, "initialize", AsyncMock()):
            a = await gt._get_backend(_config(tag="proj-a"))
            b = await gt._get_backend(_config(tag="proj-b"))

        assert isinstance(a, Neo4jBackend) and isinstance(b, Neo4jBackend)
        assert a._cb is not b._cb, "projects share one circuit breaker"


class TestSchemaInitIsPerDatabase:
    async def test_initialize_runs_once_per_connection_not_once_per_key(self):
        """initialize() issues ~33 DDL statements.

        Constraints and indexes are database-scoped, not project-scoped, so
        keying init like the backend would make the e2e suite pay all of them
        per test (its sandbox mints a fresh project root each time).
        """
        import wheeler.tools.graph_tools as gt

        init = AsyncMock()

        with patch("wheeler.graph.backend.get_backend") as factory:
            factory.side_effect = lambda cfg: SimpleNamespace(initialize=init)
            await gt._get_backend(_config(tag="a", root="/tmp/1"))
            await gt._get_backend(_config(tag="b", root="/tmp/2"))
            await gt._get_backend(_config(tag="c", root="/tmp/3"))

        assert init.await_count == 1, (
            f"schema init ran {init.await_count}x for one database"
        )

    async def test_a_different_database_is_initialized_separately(self):
        import wheeler.tools.graph_tools as gt

        init = AsyncMock()

        with patch("wheeler.graph.backend.get_backend") as factory:
            factory.side_effect = lambda cfg: SimpleNamespace(initialize=init)
            await gt._get_backend(_config(uri="bolt://host-a:7687"))
            await gt._get_backend(_config(uri="bolt://host-b:7687"))

        assert init.await_count == 2


class TestContract:
    def test_the_module_global_singleton_is_gone(self):
        """A future fixture writing `gt._backend_instance = None` would be a
        silent no-op, and the 60-second breaker trap would return with nothing
        failing."""
        import wheeler.tools.graph_tools as gt

        assert not hasattr(gt, "_backend_instance")

    def test_signature_is_unchanged(self):
        """The service scaffolder emits a literal
        `from wheeler.tools.graph_tools import _get_backend, execute_tool`, and
        tests/test_scaffold_service.py asserts that string."""
        import wheeler.tools.graph_tools as gt

        params = list(inspect.signature(gt._get_backend).parameters)
        assert params == ["config"]

    def test_reset_helper_exists(self):
        import wheeler.tools.graph_tools as gt

        assert callable(gt.reset_backend_cache)
