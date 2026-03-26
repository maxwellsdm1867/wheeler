"""Tests for wheeler.graph.schema module."""

import pytest

from wheeler.graph.schema import (
    ALLOWED_RELATIONSHIPS,
    CONSTRAINTS,
    INDEXES,
    LABEL_TO_PREFIX,
    NODE_LABELS,
    PREFIX_TO_LABEL,
)


class TestSchema:
    def test_prefix_to_label_mapping(self):
        assert PREFIX_TO_LABEL["F"] == "Finding"
        assert PREFIX_TO_LABEL["H"] == "Hypothesis"
        assert PREFIX_TO_LABEL["Q"] == "OpenQuestion"
        assert PREFIX_TO_LABEL["E"] == "Experiment"
        assert PREFIX_TO_LABEL["A"] == "Analysis"
        assert PREFIX_TO_LABEL["D"] == "Dataset"
        assert PREFIX_TO_LABEL["P"] == "Paper"
        assert PREFIX_TO_LABEL["C"] == "CellType"
        assert PREFIX_TO_LABEL["T"] == "Task"
        assert PREFIX_TO_LABEL["PL"] == "Plan"
        assert PREFIX_TO_LABEL["W"] == "Document"

    def test_label_to_prefix_is_inverse(self):
        for prefix, label in PREFIX_TO_LABEL.items():
            assert LABEL_TO_PREFIX[label] == prefix

    def test_node_labels_complete(self):
        expected = {
            "Plan", "Finding", "Hypothesis", "OpenQuestion",
            "Experiment", "Analysis", "Dataset", "Paper",
            "CellType", "Task", "Document",
        }
        assert set(NODE_LABELS) == expected

    def test_constraints_cover_all_labels(self):
        for label in NODE_LABELS:
            found = any(label in c for c in CONSTRAINTS)
            assert found, f"Missing constraint for {label}"

    def test_constraints_are_unique_id(self):
        for c in CONSTRAINTS:
            assert "REQUIRE n.id IS UNIQUE" in c

    def test_indexes_exist(self):
        assert len(INDEXES) > 0

    def test_provenance_indexes(self):
        """Verify provenance-related indexes exist."""
        index_strs = " ".join(INDEXES)
        assert "script_hash" in index_strs
        assert "script_path" in index_strs
        assert "executed_at" in index_strs

    def test_allowed_relationships(self):
        expected = {
            "PRODUCED", "SUPPORTS", "CONTRADICTS", "USED_DATA",
            "GENERATED", "RAN_SCRIPT", "CITES", "RELEVANT_TO",
            "REFERENCED_IN", "STUDIED_IN", "CONTAINS", "DEPENDS_ON",
            "AROSE_FROM", "INFORMED", "BASED_ON", "APPEARS_IN",
        }
        assert set(ALLOWED_RELATIONSHIPS) == expected
