"""Tests for wheeler.tools.graph_tools module."""

import json

import pytest

from wheeler.tools.graph_tools import TOOL_DEFINITIONS
from wheeler.graph.schema import generate_node_id as _generate_id


class TestToolDefinitions:
    def test_all_tools_have_required_fields(self):
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool, f"Tool missing name: {tool}"
            assert "description" in tool, f"Tool {tool['name']} missing description"
            assert "parameters" in tool, f"Tool {tool['name']} missing parameters"
            assert "required" in tool, f"Tool {tool['name']} missing required"

    def test_expected_tools_exist(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        expected = {
            "add_finding",
            "add_hypothesis",
            "add_question",
            "link_nodes",
            "query_findings",
            "query_open_questions",
            "query_hypotheses",
            "graph_gaps",
            "add_dataset",
            "query_datasets",
            "add_paper",
            "query_papers",
            "add_document",
            "query_documents",
            "set_tier",
        }
        assert expected == names

    def test_add_finding_parameters(self):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "add_finding")
        assert "description" in tool["parameters"]
        assert "confidence" in tool["parameters"]
        assert tool["required"] == ["description", "confidence"]

    def test_link_nodes_parameters(self):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "link_nodes")
        assert "source_id" in tool["parameters"]
        assert "target_id" in tool["parameters"]
        assert "relationship" in tool["parameters"]

    def test_query_tools_have_limit(self):
        query_tools = [
            t for t in TOOL_DEFINITIONS
            if t["name"].startswith("query_")
        ]
        for tool in query_tools:
            assert "limit" in tool["parameters"], (
                f"{tool['name']} missing limit parameter"
            )

    def test_graph_gaps_no_required(self):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "graph_gaps")
        assert tool["required"] == []

    def test_add_paper_parameters(self):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "add_paper")
        assert "title" in tool["parameters"]
        assert tool["required"] == ["title"]

    def test_add_document_parameters(self):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "add_document")
        assert "title" in tool["parameters"]
        assert "path" in tool["parameters"]
        assert tool["required"] == ["title", "path"]

    def test_set_tier_parameters(self):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "set_tier")
        assert "node_id" in tool["parameters"]
        assert "tier" in tool["parameters"]
        assert tool["required"] == ["node_id", "tier"]

    def test_descriptions_are_nonempty(self):
        for tool in TOOL_DEFINITIONS:
            assert len(tool["description"]) > 10, (
                f"Tool {tool['name']} has too-short description"
            )


class TestGenerateId:
    def test_finding_prefix(self):
        fid = _generate_id("F")
        assert fid.startswith("F-")
        assert len(fid) == 10  # "F-" + 8 hex chars

    def test_hypothesis_prefix(self):
        hid = _generate_id("H")
        assert hid.startswith("H-")

    def test_document_prefix(self):
        wid = _generate_id("W")
        assert wid.startswith("W-")
        assert len(wid) == 10

    def test_paper_prefix(self):
        pid = _generate_id("P")
        assert pid.startswith("P-")

    def test_ids_are_unique(self):
        ids = {_generate_id("F") for _ in range(100)}
        assert len(ids) == 100


class TestToolImports:
    def test_execute_tool_is_callable(self):
        from wheeler.tools.graph_tools import execute_tool
        assert callable(execute_tool)

    def test_tool_definitions_accessible(self):
        from wheeler.tools.graph_tools import TOOL_DEFINITIONS
        assert len(TOOL_DEFINITIONS) == 15
