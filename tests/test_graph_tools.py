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
            "add_note",
            "add_script",
            "add_execution",
            "add_plan",
            "ensure_artifact",
            "link_nodes",
            "unlink_nodes",
            "delete_node",
            "update_node",
            "query_findings",
            "query_open_questions",
            "query_hypotheses",
            "query_notes",
            "query_scripts",
            "query_executions",
            "graph_gaps",
            "add_dataset",
            "query_datasets",
            "add_paper",
            "query_papers",
            "add_document",
            "query_documents",
            "set_tier",
            "search_findings",
            "index_node",
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


class TestMutationStability:
    """Verify that mutation tools include stability in the props dict."""

    @pytest.mark.asyncio
    async def test_add_finding_includes_stability(self):
        from wheeler.tools.graph_tools.mutations import add_finding

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_finding(FakeBackend(), {"description": "test", "confidence": 0.8})
        assert "stability" in captured_props
        assert captured_props["stability"] == 0.3  # Finding + generated

    @pytest.mark.asyncio
    async def test_add_paper_includes_stability(self):
        from wheeler.tools.graph_tools.mutations import add_paper

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_paper(FakeBackend(), {"title": "Test paper"})
        assert "stability" in captured_props
        assert captured_props["stability"] == 0.9  # Paper + reference

    @pytest.mark.asyncio
    async def test_add_script_includes_stability(self):
        from wheeler.tools.graph_tools.mutations import add_script

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_script(FakeBackend(), {"path": "/test.py", "language": "python"})
        assert "stability" in captured_props
        assert captured_props["stability"] == 0.5  # Script + generated


class TestDisplayName:
    """Verify that mutation tools set display_name on created nodes (Issue #8)."""

    @pytest.mark.asyncio
    async def test_add_finding_display_name(self):
        from wheeler.tools.graph_tools.mutations import add_finding

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_finding(FakeBackend(), {
            "description": "tau_rise equals 0.12ms across all tested cell types in the dataset",
            "confidence": 0.8,
        })
        # First 40 chars of description
        assert captured_props["display_name"] == "tau_rise equals 0.12ms across all tested"
        assert len(captured_props["display_name"]) == 40

    @pytest.mark.asyncio
    async def test_add_script_display_name_is_filename(self):
        from wheeler.tools.graph_tools.mutations import add_script

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_script(FakeBackend(), {"path": "/data/scripts/analyze_spikes.py", "language": "python"})
        assert captured_props["display_name"] == "analyze_spikes.py"

    @pytest.mark.asyncio
    async def test_add_paper_display_name_with_authors_and_year(self):
        from wheeler.tools.graph_tools.mutations import add_paper

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_paper(FakeBackend(), {"title": "Spike Response Model", "authors": "Gerstner, Kistler", "year": 1995})
        assert captured_props["display_name"] == "Gerstner et al., 1995"

    @pytest.mark.asyncio
    async def test_add_paper_display_name_without_authors(self):
        from wheeler.tools.graph_tools.mutations import add_paper

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_paper(FakeBackend(), {"title": "A Very Long Paper Title That Exceeds Forty Characters Easily"})
        assert captured_props["display_name"] == "A Very Long Paper Title That Exceeds For"

    @pytest.mark.asyncio
    async def test_add_dataset_display_name_from_path(self):
        from wheeler.tools.graph_tools.mutations import add_dataset

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_dataset(FakeBackend(), {"path": "/data/recordings/cell_data.mat", "type": "mat", "description": "Cell recordings"})
        assert captured_props["display_name"] == "cell_data.mat"

    @pytest.mark.asyncio
    async def test_add_execution_display_name(self):
        from wheeler.tools.graph_tools.mutations import add_execution

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_execution(FakeBackend(), {"kind": "script_run", "description": "Analyze cold exposure responses across multiple conditions"})
        # Format: "{kind}: {description[:30]}"
        assert captured_props["display_name"] == "script_run: Analyze cold exposure response"

    @pytest.mark.asyncio
    async def test_add_ledger_display_name(self):
        from wheeler.tools.graph_tools.mutations import add_ledger

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_ledger(FakeBackend(), {"mode": "execute"})
        assert captured_props["display_name"] == "Ledger: execute"

    @pytest.mark.asyncio
    async def test_add_hypothesis_display_name(self):
        from wheeler.tools.graph_tools.mutations import add_hypothesis

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_hypothesis(FakeBackend(), {"statement": "Channel gating drives temperature dependence"})
        assert captured_props["display_name"] == "Channel gating drives temperature depend"

    @pytest.mark.asyncio
    async def test_add_question_display_name(self):
        from wheeler.tools.graph_tools.mutations import add_question

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_question(FakeBackend(), {"question": "Does cell type affect tau?"})
        assert captured_props["display_name"] == "Does cell type affect tau?"

    @pytest.mark.asyncio
    async def test_add_document_display_name(self):
        from wheeler.tools.graph_tools.mutations import add_document

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_document(FakeBackend(), {"title": "Results: Spike Generation", "path": "docs/results.md"})
        assert captured_props["display_name"] == "Results: Spike Generation"

    @pytest.mark.asyncio
    async def test_add_note_display_name(self):
        from wheeler.tools.graph_tools.mutations import add_note

        captured_props = {}

        class FakeBackend:
            async def create_node(self, label, props):
                captured_props.update(props)

        await add_note(FakeBackend(), {"title": "Insight about tau", "content": "The tau values are consistent"})
        assert captured_props["display_name"] == "Insight about tau"


class TestProvenanceCompleting:
    """Verify that mutation tools auto-create Execution + links when execution_kind is set."""

    @pytest.mark.asyncio
    async def test_add_finding_without_provenance(self):
        """Without execution_kind, no Execution is created."""
        from wheeler.tools.graph_tools.mutations import add_finding

        nodes_created = []

        class FakeBackend:
            async def create_node(self, label, props):
                nodes_created.append(label)
            async def create_relationship(self, *a):
                pass

        result = json.loads(await add_finding(
            FakeBackend(), {"description": "test", "confidence": 0.8}
        ))
        assert result["status"] == "created"
        assert "provenance" not in result
        assert nodes_created == ["Finding"]

    @pytest.mark.asyncio
    async def test_add_finding_with_provenance(self):
        """With execution_kind, auto-creates Execution + links."""
        from wheeler.tools.graph_tools.mutations import add_finding

        nodes_created = []
        rels_created = []

        class FakeBackend:
            async def create_node(self, label, props):
                nodes_created.append((label, props.get("id", "")))
            async def create_relationship(self, src_l, src_id, rel, tgt_l, tgt_id):
                rels_created.append((src_l, rel, tgt_l))
                return True

        result = json.loads(await add_finding(
            FakeBackend(),
            {
                "description": "spike freq doubles",
                "confidence": 0.85,
                "execution_kind": "script",
                "used_entities": "D-abc12345,S-def67890",
                "execution_description": "cold exposure analysis",
            },
        ))

        # Finding + Execution created
        labels = [n[0] for n in nodes_created]
        assert "Finding" in labels
        assert "Execution" in labels

        # Provenance in response
        assert "provenance" in result
        prov = result["provenance"]
        assert prov["execution_kind"] == "script"
        assert len(prov["linked_inputs"]) == 2
        assert "D-abc12345" in prov["linked_inputs"]
        assert "S-def67890" in prov["linked_inputs"]

        # Relationships: WAS_GENERATED_BY + 2x USED
        rel_types = [r[1] for r in rels_created]
        assert "WAS_GENERATED_BY" in rel_types
        assert rel_types.count("USED") == 2

    @pytest.mark.asyncio
    async def test_add_hypothesis_with_provenance(self):
        """Provenance-completing works on Hypothesis too."""
        from wheeler.tools.graph_tools.mutations import add_hypothesis

        nodes_created = []

        class FakeBackend:
            async def create_node(self, label, props):
                nodes_created.append(label)
            async def create_relationship(self, *a):
                return True

        result = json.loads(await add_hypothesis(
            FakeBackend(),
            {
                "statement": "channel gating drives temp dependence",
                "execution_kind": "discuss",
                "used_entities": "F-aaa11111",
            },
        ))
        assert "Hypothesis" in nodes_created
        assert "Execution" in nodes_created
        assert result["provenance"]["execution_kind"] == "discuss"

    @pytest.mark.asyncio
    async def test_provenance_with_empty_used_entities(self):
        """Execution is created even with no inputs."""
        from wheeler.tools.graph_tools.mutations import add_finding

        rels_created = []

        class FakeBackend:
            async def create_node(self, label, props):
                pass
            async def create_relationship(self, *a):
                rels_created.append(a)
                return True

        result = json.loads(await add_finding(
            FakeBackend(),
            {
                "description": "observation",
                "confidence": 0.5,
                "execution_kind": "discuss",
                "used_entities": "",
            },
        ))
        assert "provenance" in result
        # Only WAS_GENERATED_BY, no USED (no inputs)
        assert len(rels_created) == 1
        assert rels_created[0][2] == "WAS_GENERATED_BY"




class TestUnlinkNodes:
    """Verify unlink_nodes mutation handler."""

    @pytest.mark.asyncio
    async def test_unlink_success(self):
        from wheeler.tools.graph_tools.mutations import unlink_nodes

        class FakeBackend:
            async def run_cypher(self, query, params=None):
                return [{"deleted": 1}]

        result = json.loads(await unlink_nodes(
            FakeBackend(),
            {"source_id": "F-abc12345", "target_id": "H-def67890", "relationship": "SUPPORTS"},
        ))
        assert result["status"] == "unlinked"
        assert result["source"] == "F-abc12345"
        assert result["target"] == "H-def67890"
        assert result["relationship"] == "SUPPORTS"

    @pytest.mark.asyncio
    async def test_unlink_not_found(self):
        from wheeler.tools.graph_tools.mutations import unlink_nodes

        class FakeBackend:
            async def run_cypher(self, query, params=None):
                return [{"deleted": 0}]

        result = json.loads(await unlink_nodes(
            FakeBackend(),
            {"source_id": "F-abc12345", "target_id": "H-def67890", "relationship": "SUPPORTS"},
        ))
        assert "error" in result
        assert result["error"] == "Relationship not found"

    @pytest.mark.asyncio
    async def test_unlink_invalid_relationship(self):
        from wheeler.tools.graph_tools.mutations import unlink_nodes

        class FakeBackend:
            pass

        result = json.loads(await unlink_nodes(
            FakeBackend(),
            {"source_id": "F-abc12345", "target_id": "H-def67890", "relationship": "BOGUS"},
        ))
        assert "error" in result
        assert "Invalid relationship" in result["error"]

    @pytest.mark.asyncio
    async def test_unlink_alias_mapping(self):
        """Aliases like USES should map to USED before deletion."""
        from wheeler.tools.graph_tools.mutations import unlink_nodes

        captured_query = []

        class FakeBackend:
            async def run_cypher(self, query, params=None):
                captured_query.append(query)
                return [{"deleted": 1}]

        result = json.loads(await unlink_nodes(
            FakeBackend(),
            {"source_id": "F-abc12345", "target_id": "D-def67890", "relationship": "USES"},
        ))
        assert result["status"] == "unlinked"
        assert result["relationship"] == "USED"  # mapped from USES
        assert "USED" in captured_query[0]

    @pytest.mark.asyncio
    async def test_unlink_bad_prefix(self):
        from wheeler.tools.graph_tools.mutations import unlink_nodes

        class FakeBackend:
            pass

        result = json.loads(await unlink_nodes(
            FakeBackend(),
            {"source_id": "ZZ-abc123", "target_id": "H-def67890", "relationship": "SUPPORTS"},
        ))
        assert "error" in result
        assert "Could not determine node labels" in result["error"]


class TestDeleteNode:
    """Verify delete_node mutation handler."""

    @pytest.mark.asyncio
    async def test_delete_success(self):
        from wheeler.tools.graph_tools.mutations import delete_node

        class FakeBackend:
            async def delete_node(self, label, node_id):
                return True

        result = json.loads(await delete_node(
            FakeBackend(),
            {"node_id": "F-abc12345"},
        ))
        assert result["status"] == "deleted"
        assert result["node_id"] == "F-abc12345"
        assert result["label"] == "Finding"

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        from wheeler.tools.graph_tools.mutations import delete_node

        class FakeBackend:
            async def delete_node(self, label, node_id):
                return False

        result = json.loads(await delete_node(
            FakeBackend(),
            {"node_id": "F-abc12345"},
        ))
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_bad_prefix(self):
        from wheeler.tools.graph_tools.mutations import delete_node

        class FakeBackend:
            pass

        result = json.loads(await delete_node(
            FakeBackend(),
            {"node_id": "ZZ-abc123"},
        ))
        assert "error" in result
        assert "Unknown node prefix" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_resolves_all_prefixes(self):
        """All known prefixes should resolve to a label."""
        from wheeler.tools.graph_tools.mutations import delete_node
        from wheeler.graph.schema import PREFIX_TO_LABEL

        for prefix, expected_label in PREFIX_TO_LABEL.items():

            class FakeBackend:
                async def delete_node(self, label, node_id):
                    return True

            result = json.loads(await delete_node(
                FakeBackend(),
                {"node_id": f"{prefix}-test1234"},
            ))
            assert result["status"] == "deleted"
            assert result["label"] == expected_label


class TestToolImports:
    def test_execute_tool_is_callable(self):
        from wheeler.tools.graph_tools import execute_tool
        assert callable(execute_tool)

    def test_tool_definitions_accessible(self):
        from wheeler.tools.graph_tools import TOOL_DEFINITIONS
        assert len(TOOL_DEFINITIONS) == 28
