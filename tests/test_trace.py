"""Tests for wheeler.graph.trace module."""

import pytest

from wheeler.graph.trace import TraceResult, TraceStep


class TestTraceStep:
    def test_create(self):
        step = TraceStep(
            node_id="X-abcd",
            label="Execution",
            description="Contrast response fit",
            relationship="WAS_GENERATED_BY",
            properties={"kind": "script_run", "agent_id": "wheeler"},
        )
        assert step.node_id == "X-abcd"
        assert step.label == "Execution"
        assert step.relationship == "WAS_GENERATED_BY"
        assert step.properties["kind"] == "script_run"

    def test_empty_properties(self):
        step = TraceStep(
            node_id="D-1234",
            label="Dataset",
            description="March recordings",
            relationship="USED",
            properties={},
        )
        assert step.properties == {}


class TestTraceResult:
    def test_create_with_chain(self):
        result = TraceResult(
            root_id="F-3a2b",
            root_label="Finding",
            root_description="ON parasol contrast index 0.73",
            chain=[
                TraceStep(
                    node_id="X-7e2d",
                    label="Execution",
                    description="Naka-Rushton fit",
                    relationship="WAS_GENERATED_BY",
                    properties={"kind": "script_run"},
                ),
                TraceStep(
                    node_id="D-9f1c",
                    label="Dataset",
                    description="March 2024 recordings",
                    relationship="USED",
                    properties={},
                ),
            ],
            root_properties={"confidence": 0.85, "date": "2024-03-15"},
        )
        assert result.root_id == "F-3a2b"
        assert len(result.chain) == 2
        assert result.chain[0].label == "Execution"
        assert result.chain[1].label == "Dataset"

    def test_create_empty_chain(self):
        result = TraceResult(
            root_id="Q-0001",
            root_label="OpenQuestion",
            root_description="What drives nonlinearity?",
            chain=[],
            root_properties={"priority": 8},
        )
        assert result.chain == []

    def test_full_provenance_chain(self):
        """Verify a complete Finding → Execution → Dataset chain."""
        chain = [
            TraceStep("X-1111", "Execution", "fit script", "WAS_GENERATED_BY", {"kind": "script_run"}),
            TraceStep("D-2222", "Dataset", "raw data", "USED", {}),
        ]
        result = TraceResult(
            root_id="F-aaaa",
            root_label="Finding",
            root_description="Key result",
            chain=chain,
            root_properties={},
        )
        labels = [s.label for s in result.chain]
        assert labels == ["Execution", "Dataset"]
        rels = [s.relationship for s in result.chain]
        assert rels == ["WAS_GENERATED_BY", "USED"]
