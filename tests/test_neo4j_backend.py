"""Tests for the Neo4j graph database backend.

Uses mocks -- no live Neo4j instance needed. Tests verify that the
backend correctly translates GraphBackend method calls into Cypher
queries via the existing driver.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.config import WheelerConfig
from wheeler.graph.neo4j_backend import (
    Neo4jBackend,
    _flatten_custom,
    _reassemble_custom,
)


@pytest.fixture
def config():
    return WheelerConfig()


def _make_mock_driver():
    """Build a mock neo4j driver with a working async session context manager."""
    session = AsyncMock()
    driver = MagicMock()

    # driver.session() must return an async context manager (not a coroutine).
    # The real neo4j driver.session() is a sync call returning an object with
    # __aenter__/__aexit__.
    @asynccontextmanager
    async def _session(**kwargs):
        yield session

    driver.session = _session
    return driver, session


class TestInitialize:
    async def test_initialize_calls_init_schema(self, config):
        with patch(
            "wheeler.graph.schema.init_schema",
            new_callable=AsyncMock,
        ) as mock_init:
            b = Neo4jBackend(config)
            await b.initialize()
            mock_init.assert_called_once_with(config)


class TestClose:
    async def test_close_calls_close_driver(self, config):
        with patch(
            "wheeler.graph.driver.close_async_driver",
            new_callable=AsyncMock,
        ) as mock_close:
            b = Neo4jBackend(config)
            await b.close()
            mock_close.assert_called_once()


class TestCreateNode:
    async def test_create_finding_generates_id(self, config):
        driver, session = _make_mock_driver()
        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            node_id = await b.create_node("Finding", {
                "description": "Test",
                "confidence": 0.9,
            })

        assert node_id.startswith("F-")
        session.run.assert_called_once()

    async def test_create_finding_with_explicit_id(self, config):
        driver, session = _make_mock_driver()
        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            node_id = await b.create_node("Finding", {
                "id": "F-explicit",
                "description": "Test",
            })

        assert node_id == "F-explicit"

    async def test_create_unknown_label_raises(self, config):
        b = Neo4jBackend(config)
        with pytest.raises(ValueError, match="Unknown label"):
            await b.create_node("NonExistent", {"foo": "bar"})


class TestGetNode:
    async def test_get_existing_node(self, config):
        driver, session = _make_mock_driver()

        mock_record = {"n": {"id": "F-abc123", "description": "Found it"}}
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=mock_record)
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.get_node("Finding", "F-abc123")

        assert result is not None
        assert result["id"] == "F-abc123"

    async def test_get_nonexistent_node(self, config):
        driver, session = _make_mock_driver()

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.get_node("Finding", "F-nonexist")

        assert result is None


class TestUpdateNode:
    async def test_update_existing_node(self, config):
        driver, session = _make_mock_driver()

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"id": "F-abc123"})
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.update_node("Finding", "F-abc123", {
                "description": "Updated",
            })

        assert result is True
        session.run.assert_called_once()

    async def test_update_nonexistent_returns_false(self, config):
        driver, session = _make_mock_driver()

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.update_node("Finding", "F-nonexist", {
                "description": "Nope",
            })

        assert result is False

    async def test_update_empty_props_returns_false(self, config):
        b = Neo4jBackend(config)
        result = await b.update_node("Finding", "F-abc", {})
        assert result is False

    async def test_update_id_only_returns_false(self, config):
        b = Neo4jBackend(config)
        result = await b.update_node("Finding", "F-abc", {"id": "F-new"})
        assert result is False


class TestDeleteNode:
    async def test_delete_existing_node(self, config):
        driver, session = _make_mock_driver()

        # First call (check existence) returns a record
        # Second call (delete) returns nothing
        check_result = AsyncMock()
        check_result.single = AsyncMock(return_value={"id": "F-abc"})
        delete_result = AsyncMock()
        session.run.side_effect = [check_result, delete_result]

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.delete_node("Finding", "F-abc")

        assert result is True
        assert session.run.call_count == 2

    async def test_delete_nonexistent_returns_false(self, config):
        driver, session = _make_mock_driver()

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.delete_node("Finding", "F-nonexist")

        assert result is False


class TestCreateRelationship:
    async def test_successful_link(self, config):
        driver, session = _make_mock_driver()

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"rel": "SUPPORTS"})
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.create_relationship(
                "Finding", "F-abc", "SUPPORTS", "Hypothesis", "H-def",
            )

        assert result is True

    async def test_failed_link(self, config):
        driver, session = _make_mock_driver()

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.create_relationship(
                "Finding", "F-abc", "SUPPORTS", "Hypothesis", "H-nonexist",
            )

        assert result is False


class TestQueryNodes:
    async def test_query_returns_results(self, config):
        driver, session = _make_mock_driver()

        # Mock async iteration over results
        mock_records = [
            {"n": {"id": "F-001", "description": "First"}},
            {"n": {"id": "F-002", "description": "Second"}},
        ]

        mock_result = MagicMock()

        async def async_iter():
            for r in mock_records:
                yield r

        mock_result.__aiter__ = lambda self: async_iter()
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            results = await b.query_nodes("Finding", limit=10)

        assert len(results) == 2


class TestCustomFlattenReassemble:
    """Unit tests for the custom-bag flatten/reassemble helpers."""

    def test_flatten_expands_scalars(self):
        props = {"id": "P-1", "custom": {"relevance_score": 0.87, "venue": "NeurIPS"}}
        out = _flatten_custom(props)
        assert "custom" not in out
        assert out["custom_relevance_score"] == 0.87
        assert out["custom_venue"] == "NeurIPS"
        assert out["id"] == "P-1"

    def test_flatten_skips_non_scalar(self):
        props = {"id": "P-1", "custom": {"ok": 1, "nested": {"x": 1}, "lst": [1, 2]}}
        out = _flatten_custom(props)
        assert out["custom_ok"] == 1
        assert "custom_nested" not in out
        assert "custom_lst" not in out

    def test_flatten_preserves_bool_and_int_and_str(self):
        props = {"custom": {"a": True, "b": 3, "c": "x", "d": 1.5}}
        out = _flatten_custom(props)
        assert out["custom_a"] is True
        assert out["custom_b"] == 3
        assert out["custom_c"] == "x"
        assert out["custom_d"] == 1.5

    def test_flatten_no_custom_unaffected(self):
        props = {"id": "P-1", "title": "t"}
        out = _flatten_custom(props)
        assert out == props

    def test_reassemble_collapses_custom_keys(self):
        node = {
            "id": "P-1",
            "title": "t",
            "custom_relevance_score": 0.87,
            "custom_venue": "NeurIPS",
        }
        out = _reassemble_custom(node)
        assert "custom_relevance_score" not in out
        assert "custom_venue" not in out
        assert out["custom"] == {"relevance_score": 0.87, "venue": "NeurIPS"}
        assert out["title"] == "t"

    def test_reassemble_no_custom_no_empty_bag(self):
        node = {"id": "P-1", "title": "t"}
        out = _reassemble_custom(node)
        assert "custom" not in out
        assert out == node

    def test_round_trip(self):
        original = {"id": "P-1", "title": "t", "custom": {"score": 0.9, "venue": "ICML"}}
        flattened = _flatten_custom(dict(original))
        reassembled = _reassemble_custom(flattened)
        assert reassembled["custom"] == original["custom"]
        assert reassembled["title"] == "t"

    async def test_create_node_flattens_custom(self, config):
        driver, session = _make_mock_driver()
        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            await b.create_node("Paper", {
                "id": "P-flat",
                "title": "Custom paper",
                "custom": {"relevance_score": 0.87, "venue": "NeurIPS"},
            })
        # The CREATE statement must reference flattened custom_<key> props.
        call = session.run.call_args
        stmt = call.args[0]
        sent_props = call.kwargs["parameters"]["props"]
        assert "custom" not in sent_props
        assert sent_props["custom_relevance_score"] == 0.87
        assert sent_props["custom_venue"] == "NeurIPS"
        assert "custom_relevance_score: $props.custom_relevance_score" in stmt

    async def test_get_node_reassembles_custom(self, config):
        driver, session = _make_mock_driver()
        mock_record = {"n": {
            "id": "P-1",
            "title": "t",
            "custom_relevance_score": 0.87,
            "custom_venue": "NeurIPS",
        }}
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=mock_record)
        session.run.return_value = mock_result

        b = Neo4jBackend(config)
        with patch.object(b, "_driver", return_value=driver):
            result = await b.get_node("Paper", "P-1")

        assert result is not None
        assert result["custom"] == {"relevance_score": 0.87, "venue": "NeurIPS"}
        assert "custom_relevance_score" not in result


