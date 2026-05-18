"""Tests for wheeler.contracts module."""

from __future__ import annotations

from pathlib import Path

import pytest
from wheeler.contracts import (
    TaskContract, NodeRequirement, LinkRequirement, ContractResult,
    validate_contract,
    PlanContract, VALIDATOR_REGISTRY, run_plan_validators,
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


# ---------------------------------------------------------------------------
# PlanContract tests
# ---------------------------------------------------------------------------


class TestPlanContract:
    """Frontmatter parsing, defaults, validation."""

    def test_defaults_match_legacy_behavior(self):
        """A plan with no contract fields should parse to the default contract,
        which is is_default and matches the historical 'analysis, flexible
        citations, no terminal artifact' behavior."""
        c = PlanContract.from_frontmatter({})
        assert c.output_type == "mixed"
        assert c.citation_mode == "flexible"
        assert c.validation == []
        assert c.section == "draft"
        assert c.is_default is True

    def test_writing_contract_round_trip(self):
        """A writing plan contract parses with all four fields set."""
        c = PlanContract.from_frontmatter({
            "output_type": "document",
            "citation_mode": "strict",
            "validation": ["validate_citations"],
            "section": "results",
        })
        assert c.output_type == "document"
        assert c.citation_mode == "strict"
        assert c.validation == ["validate_citations"]
        assert c.section == "results"
        assert c.is_default is False

    def test_unknown_output_type_rejected(self):
        """Typos in output_type surface at parse time, not silently fall through."""
        with pytest.raises(ValueError, match="output_type"):
            PlanContract.from_frontmatter({"output_type": "movie"})

    def test_unknown_citation_mode_rejected(self):
        with pytest.raises(ValueError, match="citation_mode"):
            PlanContract.from_frontmatter({"citation_mode": "moderate"})

    def test_validation_must_be_list(self):
        """A scalar where a list is expected is a config error, not a coerced value."""
        with pytest.raises(ValueError, match="validation"):
            PlanContract.from_frontmatter({"validation": "validate_citations"})

    def test_validation_string_items_coerced(self):
        """List items get str()'d so YAML-parsed ints/floats don't crash later."""
        c = PlanContract.from_frontmatter({"validation": ["validate_citations"]})
        assert c.validation == ["validate_citations"]


class TestValidatorRegistry:
    """Registry contents and the unknown-validator path."""

    def test_known_validators_registered(self):
        """The minimal set of validators required for v1 must be registered."""
        assert "validate_citations" in VALIDATOR_REGISTRY
        assert "graph_consistency_check" in VALIDATOR_REGISTRY

    @pytest.mark.asyncio
    async def test_unknown_validator_produces_violation_not_crash(self):
        """A typo in the plan's validation list must not crash run_plan_validators;
        it should record a violation listing the known validators."""
        from wheeler.config import load_config

        contract = PlanContract(
            output_type="document",
            citation_mode="strict",
            validation=["validate_citations_typo"],
            section="results",
        )
        result = await run_plan_validators(contract, None, load_config())
        assert result.passed is False
        assert result.checks_run == 1
        assert len(result.violations) == 1
        assert "unknown validator" in result.violations[0]

    @pytest.mark.asyncio
    async def test_validate_citations_requires_path(self, tmp_path):
        """The validate_citations runner must report a clean error when given
        no artifact path, rather than crashing."""
        from wheeler.config import load_config

        contract = PlanContract(
            output_type="document",
            citation_mode="strict",
            validation=["validate_citations"],
        )
        result = await run_plan_validators(contract, None, load_config())
        assert result.passed is False
        assert "requires an artifact path" in result.violations[0]

    @pytest.mark.asyncio
    async def test_empty_validation_passes_trivially(self):
        """No validators = nothing to check = pass."""
        from wheeler.config import load_config

        contract = PlanContract()
        result = await run_plan_validators(contract, None, load_config())
        assert result.passed is True
        assert result.checks_run == 0
