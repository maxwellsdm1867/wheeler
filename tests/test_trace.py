"""Tests for wheeler.graph.trace module."""

import pytest

from wheeler.graph.trace import TraceResult, TraceStep


class TestTraceStep:
    def test_create(self):
        step = TraceStep(
            node_id="A-abcd",
            label="Analysis",
            description="Contrast response fit",
            relationship="GENERATED",
            properties={"language": "matlab", "script_path": "/scripts/fit.m"},
        )
        assert step.node_id == "A-abcd"
        assert step.label == "Analysis"
        assert step.relationship == "GENERATED"
        assert step.properties["language"] == "matlab"

    def test_empty_properties(self):
        step = TraceStep(
            node_id="D-1234",
            label="Dataset",
            description="March recordings",
            relationship="USED_DATA",
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
                    node_id="A-7e2d",
                    label="Analysis",
                    description="Naka-Rushton fit",
                    relationship="GENERATED",
                    properties={"language": "matlab"},
                ),
                TraceStep(
                    node_id="D-9f1c",
                    label="Dataset",
                    description="March 2024 recordings",
                    relationship="USED_DATA",
                    properties={},
                ),
            ],
            root_properties={"confidence": 0.85, "date": "2024-03-15"},
        )
        assert result.root_id == "F-3a2b"
        assert len(result.chain) == 2
        assert result.chain[0].label == "Analysis"
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
        """Verify a complete Finding → Analysis → Dataset chain."""
        chain = [
            TraceStep("A-1111", "Analysis", "fit script", "GENERATED", {"language": "matlab"}),
            TraceStep("D-2222", "Dataset", "raw data", "USED_DATA", {}),
        ]
        result = TraceResult(
            root_id="F-aaaa",
            root_label="Finding",
            root_description="Key result",
            chain=chain,
            root_properties={},
        )
        labels = [s.label for s in result.chain]
        assert labels == ["Analysis", "Dataset"]
        rels = [s.relationship for s in result.chain]
        assert rels == ["GENERATED", "USED_DATA"]
