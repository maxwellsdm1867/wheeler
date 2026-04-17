"""Tests for wheeler.graph.context (fetch_context with optional topic filter)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.graph.context import fetch_context


def _make_config(project_tag: str = "") -> MagicMock:
    """Build a minimal mock WheelerConfig for fetch_context."""
    cfg = MagicMock()
    cfg.neo4j.project_tag = project_tag
    cfg.neo4j.database = "neo4j"
    cfg.context_max_findings = 5
    cfg.context_max_questions = 5
    cfg.context_max_hypotheses = 3
    return cfg


def _make_async_records(records: list[dict]):
    """Return an AsyncMock whose async iteration yields the given records."""
    result = AsyncMock()

    async def _aiter(self):
        for r in records:
            yield r

    result.__aiter__ = _aiter
    return result


def _make_driver_with_results(results_per_call: list[list[dict]]):
    """Build mock driver/session that returns successive query results.

    *results_per_call* is a list of lists: each inner list contains
    dicts that will be yielded from the corresponding session.run() call.
    """
    call_idx = 0
    queries_seen: list[str] = []
    params_seen: list[dict] = []

    async def mock_run(query, **kwargs):
        nonlocal call_idx
        queries_seen.append(query)
        params_seen.append(kwargs)
        records = results_per_call[call_idx] if call_idx < len(results_per_call) else []
        call_idx += 1
        return _make_async_records(records)

    mock_session = AsyncMock()
    mock_session.run = mock_run
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    return mock_driver, queries_seen, params_seen


class TestFetchContextNoTopic:
    """Backward-compat: fetch_context with no topic still works."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_nodes(self):
        config = _make_config()
        driver, queries, _ = _make_driver_with_results([[], [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            result = await fetch_context(config)

        assert result == ""
        assert len(queries) == 4  # 4 sequential queries

    @pytest.mark.asyncio
    async def test_returns_sections_when_nodes_exist(self):
        config = _make_config()
        ref = [{"id": "F-0001", "desc": "Reference finding"}]
        gen = [{"id": "F-0002", "desc": "Generated finding"}]
        qs = [{"id": "Q-0001", "question": "Why does X happen?"}]
        hyps = [{"id": "H-0001", "stmt": "X causes Y"}]
        driver, queries, _ = _make_driver_with_results([ref, gen, qs, hyps])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            result = await fetch_context(config)

        assert "## Research Context (from knowledge graph)" in result
        assert "Established Knowledge" in result
        assert "Recent Work" in result
        assert "Open Questions" in result
        assert "Active Hypotheses" in result
        assert "[F-0001]" in result
        assert "[Q-0001]" in result
        # No topic in header
        assert "topic:" not in result

    @pytest.mark.asyncio
    async def test_no_topic_filter_in_queries(self):
        """When topic is empty, no toLower filter should appear."""
        config = _make_config()
        driver, queries, params = _make_driver_with_results([[], [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            await fetch_context(config)

        for q in queries:
            assert "toLower" not in q
            assert "$topic" not in q
        for p in params:
            assert "topic" not in p


class TestFetchContextWithTopic:
    """Tests for the new topic filtering."""

    @pytest.mark.asyncio
    async def test_topic_filter_in_finding_queries(self):
        """When topic is provided, finding queries include toLower filter."""
        config = _make_config()
        driver, queries, params = _make_driver_with_results([[], [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            await fetch_context(config, topic="photon")

        # First two queries are findings (ref + gen)
        for i in range(2):
            assert "toLower(f.description) CONTAINS toLower($topic)" in queries[i]
            assert params[i]["topic"] == "photon"

    @pytest.mark.asyncio
    async def test_topic_filter_in_question_query(self):
        config = _make_config()
        driver, queries, params = _make_driver_with_results([[], [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            await fetch_context(config, topic="scattering")

        # Third query is questions
        assert "toLower(q.question) CONTAINS toLower($topic)" in queries[2]
        assert params[2]["topic"] == "scattering"

    @pytest.mark.asyncio
    async def test_topic_filter_in_hypothesis_query(self):
        config = _make_config()
        driver, queries, params = _make_driver_with_results([[], [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            await fetch_context(config, topic="decay")

        # Fourth query is hypotheses
        assert "toLower(h.statement) CONTAINS toLower($topic)" in queries[3]
        assert params[3]["topic"] == "decay"

    @pytest.mark.asyncio
    async def test_topic_in_header(self):
        """When topic is set and there are results, header includes the topic."""
        config = _make_config()
        ref = [{"id": "F-0001", "desc": "Photon energy measurement"}]
        driver, _, _ = _make_driver_with_results([ref, [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            result = await fetch_context(config, topic="photon")

        assert "-- topic: photon" in result

    @pytest.mark.asyncio
    async def test_topic_whitespace_stripped(self):
        """Leading/trailing whitespace in topic should be stripped."""
        config = _make_config()
        driver, queries, params = _make_driver_with_results([[], [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            await fetch_context(config, topic="  photon  ")

        # Topic param should be stripped
        assert params[0]["topic"] == "photon"

    @pytest.mark.asyncio
    async def test_empty_topic_string_no_filter(self):
        """An all-whitespace topic should behave like no topic."""
        config = _make_config()
        driver, queries, params = _make_driver_with_results([[], [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            await fetch_context(config, topic="   ")

        for q in queries:
            assert "toLower" not in q
        for p in params:
            assert "topic" not in p


class TestFetchContextWithProjectTag:
    """Topic filtering combined with project namespace isolation."""

    @pytest.mark.asyncio
    async def test_topic_and_project_tag_both_applied(self):
        config = _make_config(project_tag="my-project")
        driver, queries, params = _make_driver_with_results([[], [], [], []])

        with patch("wheeler.graph.context.get_async_driver", return_value=driver):
            await fetch_context(config, topic="photon")

        # All queries should have both project filter and topic filter
        for q in queries:
            assert "$ptag" in q or "_wheeler_project" in q
            assert "toLower" in q
        for p in params:
            assert p["ptag"] == "my-project"
            assert p["topic"] == "photon"
