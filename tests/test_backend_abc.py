"""Tests verifying both backends implement the GraphBackend ABC."""

from __future__ import annotations

import inspect

import pytest

from wheeler.graph.backend import GraphBackend, get_backend
from wheeler.graph.neo4j_backend import Neo4jBackend
from wheeler.config import WheelerConfig

try:
    import kuzu as _kuzu_mod
    from wheeler.graph.kuzu_backend import KuzuBackend

    _has_kuzu = True
except ImportError:
    _has_kuzu = False
    KuzuBackend = None  # type: ignore[assignment,misc]

_skip_no_kuzu = pytest.mark.skipif(not _has_kuzu, reason="kuzu not installed")


class TestABCCompliance:
    """Verify that both backends implement every abstract method."""

    def _abstract_methods(self) -> set[str]:
        """Return the set of abstract method names from GraphBackend."""
        return set(GraphBackend.__abstractmethods__)

    @_skip_no_kuzu
    def test_kuzu_implements_all(self):
        methods = self._abstract_methods()
        for method in methods:
            assert hasattr(KuzuBackend, method), f"KuzuBackend missing {method}"
            impl = getattr(KuzuBackend, method)
            assert callable(impl), f"KuzuBackend.{method} is not callable"

    def test_neo4j_implements_all(self):
        methods = self._abstract_methods()
        for method in methods:
            assert hasattr(Neo4jBackend, method), f"Neo4jBackend missing {method}"
            impl = getattr(Neo4jBackend, method)
            assert callable(impl), f"Neo4jBackend.{method} is not callable"

    @_skip_no_kuzu
    def test_kuzu_is_instantiable(self, tmp_path):
        """KuzuBackend can be instantiated (does not call initialize)."""
        b = KuzuBackend(str(tmp_path / "abc_test"))
        assert isinstance(b, GraphBackend)

    def test_neo4j_is_instantiable(self):
        """Neo4jBackend can be instantiated (does not connect)."""
        config = WheelerConfig()
        b = Neo4jBackend(config)
        assert isinstance(b, GraphBackend)

    def test_all_abstract_methods_are_async(self):
        """Every abstract method on GraphBackend should be async."""
        for name in self._abstract_methods():
            method = getattr(GraphBackend, name)
            assert inspect.iscoroutinefunction(method), (
                f"GraphBackend.{name} should be async"
            )

    def test_neo4j_signatures_match(self):
        """Neo4jBackend should have matching signatures for each method."""
        for name in self._abstract_methods():
            abc_sig = inspect.signature(getattr(GraphBackend, name))
            neo4j_sig = inspect.signature(getattr(Neo4jBackend, name))

            abc_params = list(abc_sig.parameters.keys())
            neo4j_params = list(neo4j_sig.parameters.keys())

            assert abc_params == neo4j_params, (
                f"Neo4jBackend.{name} signature mismatch: {neo4j_params} != {abc_params}"
            )

    @_skip_no_kuzu
    def test_kuzu_signatures_match(self):
        """KuzuBackend should have matching signatures for each method."""
        for name in self._abstract_methods():
            abc_sig = inspect.signature(getattr(GraphBackend, name))
            kuzu_sig = inspect.signature(getattr(KuzuBackend, name))

            abc_params = list(abc_sig.parameters.keys())
            kuzu_params = list(kuzu_sig.parameters.keys())

            assert abc_params == kuzu_params, (
                f"KuzuBackend.{name} signature mismatch: {kuzu_params} != {abc_params}"
            )


class TestFactory:
    @_skip_no_kuzu
    def test_get_backend_kuzu(self, tmp_path):
        config = WheelerConfig(
            graph={"backend": "kuzu", "kuzu_path": str(tmp_path / "factory_test")},
        )
        b = get_backend(config)
        assert isinstance(b, KuzuBackend)

    def test_get_backend_neo4j(self):
        config = WheelerConfig(graph={"backend": "neo4j"})
        b = get_backend(config)
        assert isinstance(b, Neo4jBackend)

    def test_get_backend_default(self):
        config = WheelerConfig()
        b = get_backend(config)
        from wheeler.graph.kuzu_backend import KuzuBackend
        assert isinstance(b, KuzuBackend)
