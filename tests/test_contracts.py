"""Tests for wheeler.contracts module."""

from __future__ import annotations

import pytest
from wheeler.contracts import (
    TaskContract, NodeRequirement, LinkRequirement, ContractResult,
    validate_contract,
)


class FakeBackend:
    """Mock backend returning pre-configured query results."""
    def __init__(self, results=None):
        self._results = results or {}
        self.queries = []

    async def run_cypher(self, query, parameters=None):
        self.queries.append((query, parameters))
        # Match based on query content
        for key, val in self._results.items():
            if key in query:
                return val
        return []

    async def initialize(self):
        pass


class TestContractResult:
    def test_passed_result(self):
        r = ContractResult(passed=True, checks_run=3)
        assert "all 3 checks passed" in r.summary

    def test_failed_result(self):
        r = ContractResult(passed=False, violations=["missing nodes"], checks_run=3)
        assert "1 of 3" in r.summary

    def test_zero_checks_passed(self):
        r = ContractResult(passed=True, checks_run=0)
        assert "all 0 checks passed" in r.summary

    def test_multiple_violations(self):
        r = ContractResult(
            passed=False,
            violations=["missing nodes", "low confidence", "no links"],
            checks_run=5,
        )
        assert "3 of 5" in r.summary


class TestValidateContract:
    @pytest.mark.asyncio
    async def test_all_requirements_met(self):
        """Contract passes when all required nodes and links exist."""
        from unittest.mock import patch, AsyncMock

        backend = FakeBackend({
            "Finding": [{"id": "F-abc", "confidence": 0.9}],
            "WAS_GENERATED_BY": [{"aid": "F-abc"}],
        })

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                required_nodes=[NodeRequirement(type="Finding", min_count=1, confidence_min=0.7)],
                required_links=[LinkRequirement(from_type="Finding", relationship="WAS_GENERATED_BY", to_type="Execution")],
            )
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is True
        assert result.checks_run == 2

    @pytest.mark.asyncio
    async def test_missing_nodes_fails(self):
        """Contract fails when required node count not met."""
        from unittest.mock import patch, AsyncMock

        backend = FakeBackend({
            "Finding": [],  # no findings
        })

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                required_nodes=[NodeRequirement(type="Finding", min_count=1)],
            )
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is False
        assert any("Expected >= 1 Finding" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_low_confidence_fails(self):
        """Contract fails when confidence below threshold."""
        from unittest.mock import patch, AsyncMock

        backend = FakeBackend({
            "Finding": [{"id": "F-abc", "confidence": 0.5}],
        })

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                required_nodes=[NodeRequirement(type="Finding", min_count=1, confidence_min=0.7)],
            )
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is False
        assert any("confidence 0.50 < 0.70" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_missing_links_fails(self):
        """Contract fails when required provenance links missing."""
        from unittest.mock import patch, AsyncMock

        backend = FakeBackend({
            "WAS_GENERATED_BY": [],  # no links
        })

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                required_links=[LinkRequirement(from_type="Finding", relationship="WAS_GENERATED_BY", to_type="Execution")],
            )
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is False
        assert any("WAS_GENERATED_BY" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_must_reference_fails(self):
        """Contract fails when output doesn't reference required inputs."""
        from unittest.mock import patch, AsyncMock

        backend = FakeBackend({})  # no references found

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                must_reference=["D-1234"],
            )
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is False
        assert any("D-1234" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_empty_contract_passes(self):
        """Contract with no requirements always passes."""
        from unittest.mock import patch, AsyncMock

        backend = FakeBackend({})

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(task_id="test")
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is True
        assert result.checks_run == 0

    @pytest.mark.asyncio
    async def test_multiple_node_types(self):
        """Contract checks multiple node type requirements independently."""
        from unittest.mock import patch, AsyncMock

        backend = FakeBackend({
            "Finding": [{"id": "F-abc", "confidence": 0.9}],
            "Hypothesis": [],  # no hypotheses
        })

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                required_nodes=[
                    NodeRequirement(type="Finding", min_count=1),
                    NodeRequirement(type="Hypothesis", min_count=1),
                ],
            )
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is False
        assert result.checks_run == 2
        assert len(result.violations) == 1
        assert any("Hypothesis" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_confidence_none_skipped(self):
        """Nodes without a confidence field are not flagged for low confidence."""
        from unittest.mock import patch, AsyncMock

        backend = FakeBackend({
            "Finding": [{"id": "F-abc", "confidence": None}],
        })

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                required_nodes=[NodeRequirement(type="Finding", min_count=1, confidence_min=0.7)],
            )
            result = await validate_contract(config, contract, "session-test")

        # Node count met, confidence is None so not checked
        assert result.passed is True
        assert result.checks_run == 1

    @pytest.mark.asyncio
    async def test_backend_error_captured(self):
        """Backend errors are captured as violations, not raised."""
        from unittest.mock import patch, AsyncMock

        class ErrorBackend:
            async def run_cypher(self, query, parameters=None):
                raise RuntimeError("connection refused")

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=ErrorBackend()):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                required_nodes=[NodeRequirement(type="Finding", min_count=1)],
            )
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is False
        assert any("Failed to query" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_multiple_must_references(self):
        """Each must_reference ID is checked independently."""
        from unittest.mock import patch, AsyncMock

        class ParamAwareBackend:
            """Backend that returns results based on parameter values."""
            def __init__(self):
                self.queries = []

            async def run_cypher(self, query, parameters=None):
                self.queries.append((query, parameters))
                # Return a match only when querying for D-1234
                if parameters and parameters.get("mid") == "D-1234":
                    return [{"nid": "F-abc"}]
                return []

        backend = ParamAwareBackend()

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            from wheeler.config import load_config
            config = load_config()

            contract = TaskContract(
                task_id="test",
                must_reference=["D-1234", "D-5678"],
            )
            result = await validate_contract(config, contract, "session-test")

        assert result.passed is False
        assert result.checks_run == 2
        # D-1234 found, D-5678 not found
        assert len(result.violations) == 1
        assert any("D-5678" in v for v in result.violations)
