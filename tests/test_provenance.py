"""Tests for wheeler.graph.provenance and wheeler.provenance modules."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.graph.provenance import (
    ScriptProvenance,
    StaleScript,
    hash_file,
)
from wheeler.provenance import (
    InvalidatedNode,
    default_stability,
    PROVENANCE_RELS,
)


class TestHashFile:
    def test_hash_known_content(self, tmp_path):
        f = tmp_path / "test.m"
        f.write_text("hello world")
        h = hash_file(f)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest

    def test_hash_deterministic(self, tmp_path):
        f = tmp_path / "test.m"
        f.write_text("deterministic content")
        assert hash_file(f) == hash_file(f)

    def test_hash_changes_with_content(self, tmp_path):
        f = tmp_path / "test.m"
        f.write_text("version 1")
        h1 = hash_file(f)
        f.write_text("version 2")
        h2 = hash_file(f)
        assert h1 != h2

    def test_hash_empty_file(self, tmp_path):
        f = tmp_path / "empty.m"
        f.write_text("")
        h = hash_file(f)
        assert len(h) == 64

    def test_hash_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            hash_file("/nonexistent/file.m")


class TestScriptProvenance:
    def test_create_minimal(self):
        prov = ScriptProvenance(
            path="/path/to/script.m",
            hash="abc123",
            language="matlab",
        )
        assert prov.path == "/path/to/script.m"
        assert prov.language == "matlab"
        assert prov.version == ""
        assert prov.tier == "generated"

    def test_create_full(self):
        prov = ScriptProvenance(
            path="/path/to/script.py",
            hash="def456",
            language="python",
            version="3.11",
            tier="reference",
        )
        assert prov.version == "3.11"
        assert prov.tier == "reference"


class TestStaleScript:
    def test_create(self):
        s = StaleScript(
            node_id="S-abcd1234",
            path="/path/to/script.m",
            stored_hash="old_hash",
            current_hash="new_hash",
        )
        assert s.node_id == "S-abcd1234"
        assert s.stored_hash != s.current_hash

    def test_missing_file(self):
        s = StaleScript(
            node_id="S-abcd1234",
            path="/missing/script.m",
            stored_hash="old_hash",
            current_hash="FILE_NOT_FOUND",
        )
        assert s.current_hash == "FILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# Tests for wheeler.provenance (top-level module)
# ---------------------------------------------------------------------------


class TestDefaultStability:
    def test_paper_reference(self):
        assert default_stability("Paper", "reference") == 0.9

    def test_finding_generated(self):
        assert default_stability("Finding", "generated") == 0.3

    def test_script_generated(self):
        assert default_stability("Script", "generated") == 0.5

    def test_dataset_reference(self):
        assert default_stability("Dataset", "reference") == 1.0

    def test_unknown_label_uses_tier_fallback(self):
        assert default_stability("UnknownType", "reference") == 0.8
        assert default_stability("UnknownType", "generated") == 0.3

    def test_unknown_tier_uses_default(self):
        assert default_stability("Finding", "unknown_tier") == 0.3


class TestProvenanceRels:
    def test_contains_prov_standard_names(self):
        assert "USED" in PROVENANCE_RELS
        assert "WAS_GENERATED_BY" in PROVENANCE_RELS
        assert "WAS_DERIVED_FROM" in PROVENANCE_RELS

    def test_no_old_names(self):
        for rel in PROVENANCE_RELS:
            assert rel not in ("USED_DATA", "GENERATED", "BASED_ON", "INFORMED")


class TestInvalidatedNode:
    def test_create(self):
        n = InvalidatedNode(
            node_id="F-1234abcd",
            label="Finding",
            old_stability=0.8,
            new_stability=0.3,
            hops=2,
        )
        assert n.node_id == "F-1234abcd"
        assert n.old_stability > n.new_stability
        assert n.hops == 2


class TestPropagateInvalidation:
    """Test propagate_invalidation with mocked Neo4j driver."""

    @pytest.mark.asyncio
    async def test_node_not_found_returns_empty(self):
        """When the changed node doesn't exist, return empty list."""
        from wheeler.provenance import propagate_invalidation

        mock_config = MagicMock()
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        # Mock driver returns no records for source query
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        with patch("wheeler.graph.driver.get_async_driver", return_value=mock_driver):
            result = await propagate_invalidation(
                mock_config, changed_node_id="S-nonexistent"
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_source_marked_stale(self):
        """Source query should SET stale=true and use $props.key params."""
        from wheeler.provenance import propagate_invalidation

        mock_config = MagicMock()
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        # Source query returns stability
        source_result = AsyncMock()
        source_result.single = AsyncMock(return_value={"new_stab": 0.3})

        # Downstream query returns empty
        async def _empty_aiter():
            return
            yield  # noqa: unreachable — makes this an async generator

        downstream_result = AsyncMock()
        downstream_result.__aiter__ = lambda self: _empty_aiter()

        mock_session = AsyncMock()
        call_count = 0

        async def mock_run(query, parameters=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Verify source query uses $props.key style
                assert "$props.nid" in query
                assert "$props.now" in query
                assert "props" in parameters
                return source_result
            return downstream_result

        mock_session.run = mock_run
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        with patch("wheeler.graph.driver.get_async_driver", return_value=mock_driver):
            result = await propagate_invalidation(
                mock_config,
                changed_node_id="S-12345678",
                new_stability=0.3,
            )

        assert result == []
        assert call_count == 2  # source + downstream queries

    @pytest.mark.asyncio
    async def test_downstream_query_uses_prov_directions(self):
        """Downstream query should follow PROV-DM edge directions."""
        from wheeler.provenance import propagate_invalidation

        mock_config = MagicMock()
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        source_result = AsyncMock()
        source_result.single = AsyncMock(return_value={"new_stab": 0.3})

        async def _empty_aiter():
            return
            yield  # noqa: unreachable — makes this an async generator

        downstream_result = AsyncMock()
        downstream_result.__aiter__ = lambda self: _empty_aiter()

        queries_captured = []

        mock_session = AsyncMock()

        async def mock_run(query, parameters=None):
            queries_captured.append(query)
            if len(queries_captured) == 1:
                return source_result
            return downstream_result

        mock_session.run = mock_run
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        with patch("wheeler.graph.driver.get_async_driver", return_value=mock_driver):
            await propagate_invalidation(
                mock_config, changed_node_id="S-12345678", new_stability=0.3
            )

        # Verify downstream query uses PROV edge types for traversal
        downstream_q = queries_captured[1]
        assert "WAS_GENERATED_BY" in downstream_q
        assert "USED" in downstream_q
        assert "WAS_DERIVED_FROM" in downstream_q
