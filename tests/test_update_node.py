"""Tests for the update_node mutation tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wheeler.models import FindingModel, HypothesisModel


class TestUpdateNodeHandler:
    """Verify the update_node mutation handler directly."""

    @pytest.mark.asyncio
    async def test_basic_description_update(self):
        from wheeler.tools.graph_tools.mutations import update_node

        captured_updates = {}

        class FakeBackend:
            async def get_node(self, label, node_id):
                return {
                    "id": "F-abc12345",
                    "description": "old description",
                    "confidence": 0.5,
                }

            async def update_node(self, label, node_id, props):
                captured_updates.update(props)
                return True

        result = json.loads(await update_node(
            FakeBackend(),
            {"node_id": "F-abc12345", "description": "new description"},
        ))
        assert result["status"] == "updated"
        assert result["node_id"] == "F-abc12345"
        assert result["label"] == "Finding"
        assert "description" in result["updated_fields"]
        assert result["changes"]["description"]["old"] == "old description"
        assert result["changes"]["description"]["new"] == "new description"
        # display_name and _search_text should be set
        assert captured_updates["display_name"] == "new description"
        assert captured_updates["_search_text"] == "new description"

    @pytest.mark.asyncio
    async def test_multiple_field_update(self):
        from wheeler.tools.graph_tools.mutations import update_node

        class FakeBackend:
            async def get_node(self, label, node_id):
                return {
                    "id": "F-abc12345",
                    "description": "old",
                    "confidence": 0.3,
                }

            async def update_node(self, label, node_id, props):
                return True

        result = json.loads(await update_node(
            FakeBackend(),
            {"node_id": "F-abc12345", "description": "updated desc", "confidence": 0.9},
        ))
        assert result["status"] == "updated"
        assert set(result["updated_fields"]) == {"description", "confidence"}
        assert result["changes"]["description"]["new"] == "updated desc"
        assert result["changes"]["confidence"]["old"] == 0.3
        assert result["changes"]["confidence"]["new"] == 0.9

    @pytest.mark.asyncio
    async def test_update_nonexistent_node(self):
        from wheeler.tools.graph_tools.mutations import update_node

        class FakeBackend:
            async def get_node(self, label, node_id):
                return None

        result = json.loads(await update_node(
            FakeBackend(),
            {"node_id": "F-abc12345", "description": "new"},
        ))
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_update_no_fields(self):
        from wheeler.tools.graph_tools.mutations import update_node

        class FakeBackend:
            async def get_node(self, label, node_id):
                return {"id": "F-abc12345", "description": "existing"}

        result = json.loads(await update_node(
            FakeBackend(),
            {"node_id": "F-abc12345"},
        ))
        assert "error" in result
        assert "No fields" in result["error"]

    @pytest.mark.asyncio
    async def test_update_bad_prefix(self):
        from wheeler.tools.graph_tools.mutations import update_node

        class FakeBackend:
            pass

        result = json.loads(await update_node(
            FakeBackend(),
            {"node_id": "ZZ-abc123", "description": "new"},
        ))
        assert "error" in result
        assert "Unknown node ID prefix" in result["error"]

    @pytest.mark.asyncio
    async def test_update_hypothesis_statement(self):
        from wheeler.tools.graph_tools.mutations import update_node

        captured_updates = {}

        class FakeBackend:
            async def get_node(self, label, node_id):
                return {
                    "id": "H-abc12345",
                    "statement": "old hypothesis",
                    "status": "open",
                }

            async def update_node(self, label, node_id, props):
                captured_updates.update(props)
                return True

        result = json.loads(await update_node(
            FakeBackend(),
            {"node_id": "H-abc12345", "statement": "revised hypothesis"},
        ))
        assert result["status"] == "updated"
        assert result["label"] == "Hypothesis"
        assert "statement" in result["updated_fields"]
        assert captured_updates["display_name"] == "revised hypothesis"

    @pytest.mark.asyncio
    async def test_update_no_actual_changes(self):
        """If all provided fields match current values, report no_changes."""
        from wheeler.tools.graph_tools.mutations import update_node

        class FakeBackend:
            async def get_node(self, label, node_id):
                return {
                    "id": "F-abc12345",
                    "description": "same description",
                }

            async def update_node(self, label, node_id, props):
                return True

        result = json.loads(await update_node(
            FakeBackend(),
            {"node_id": "F-abc12345", "description": "same description"},
        ))
        assert result["status"] == "no_changes"
        assert result["updated_fields"] == []

    @pytest.mark.asyncio
    async def test_update_sets_timestamp(self):
        from wheeler.tools.graph_tools.mutations import update_node

        captured_updates = {}

        class FakeBackend:
            async def get_node(self, label, node_id):
                return {"id": "F-abc12345", "description": "old"}

            async def update_node(self, label, node_id, props):
                captured_updates.update(props)
                return True

        await update_node(
            FakeBackend(),
            {"node_id": "F-abc12345", "description": "new"},
        )
        assert "updated" in captured_updates
        # Should be an ISO timestamp string
        assert "T" in captured_updates["updated"]

    @pytest.mark.asyncio
    async def test_update_excludes_internal_keys(self):
        """session_id and _config should not appear in updates."""
        from wheeler.tools.graph_tools.mutations import update_node

        captured_updates = {}

        class FakeBackend:
            async def get_node(self, label, node_id):
                return {"id": "F-abc12345", "description": "old"}

            async def update_node(self, label, node_id, props):
                captured_updates.update(props)
                return True

        await update_node(
            FakeBackend(),
            {
                "node_id": "F-abc12345",
                "description": "new",
                "session_id": "test-session",
                "_config": "should_be_excluded",
            },
        )
        assert "session_id" not in captured_updates
        assert "_config" not in captured_updates
        assert "node_id" not in captured_updates

    @pytest.mark.asyncio
    async def test_update_all_node_types(self):
        """All known prefixes should resolve to a label for update."""
        from wheeler.tools.graph_tools.mutations import update_node
        from wheeler.graph.schema import PREFIX_TO_LABEL

        for prefix, expected_label in PREFIX_TO_LABEL.items():

            class FakeBackend:
                async def get_node(self, label, node_id):
                    return {"id": f"{prefix}-test1234", "tier": "generated"}

                async def update_node(self, label, node_id, props):
                    return True

            result = json.loads(await update_node(
                FakeBackend(),
                {"node_id": f"{prefix}-test1234", "tier": "reference"},
            ))
            assert result["label"] == expected_label, (
                f"Prefix {prefix} should resolve to {expected_label}"
            )


class TestUpdateNodeFieldValidation:
    """Verify that field validation runs for update_node."""

    def test_update_node_in_required_fields(self):
        from wheeler.tools.graph_tools._field_specs import _REQUIRED_FIELDS

        assert "update_node" in _REQUIRED_FIELDS
        assert _REQUIRED_FIELDS["update_node"] == ("node_id",)

    def test_bad_confidence_rejected(self):
        from wheeler.tools.graph_tools._field_specs import validate_and_normalize

        args = {"node_id": "F-abc12345", "confidence": 2.5}
        errors, warnings = validate_and_normalize("update_node", args)
        assert "confidence" in errors
        assert "0.0-1.0" in errors["confidence"]["error"]

    def test_bad_priority_rejected(self):
        from wheeler.tools.graph_tools._field_specs import validate_and_normalize

        args = {"node_id": "Q-abc12345", "priority": 99}
        errors, warnings = validate_and_normalize("update_node", args)
        assert "priority" in errors
        assert "1-10" in errors["priority"]["error"]

    def test_bad_tier_rejected(self):
        from wheeler.tools.graph_tools._field_specs import validate_and_normalize

        args = {"node_id": "F-abc12345", "tier": "bogus"}
        errors, warnings = validate_and_normalize("update_node", args)
        assert "tier" in errors

    def test_valid_confidence_passes(self):
        from wheeler.tools.graph_tools._field_specs import validate_and_normalize

        args = {"node_id": "F-abc12345", "confidence": 0.8}
        errors, warnings = validate_and_normalize("update_node", args)
        assert "confidence" not in errors

    def test_valid_tier_normalized(self):
        from wheeler.tools.graph_tools._field_specs import validate_and_normalize

        args = {"node_id": "F-abc12345", "tier": "Reference"}
        errors, warnings = validate_and_normalize("update_node", args)
        assert "tier" not in errors
        assert args["tier"] == "reference"  # normalized to lowercase

    def test_missing_node_id_rejected(self):
        from wheeler.tools.graph_tools._field_specs import validate_and_normalize

        args = {"description": "test"}
        errors, warnings = validate_and_normalize("update_node", args)
        assert "node_id" in errors


class TestUpdateNodeKnowledgeFile:
    """Verify that update_node updates the knowledge JSON file."""

    def test_update_knowledge_node_helper(self, tmp_path):
        """Directly test the _update_knowledge_node helper."""
        from wheeler.tools.graph_tools import _update_knowledge_node
        from wheeler.knowledge.store import write_node, read_node
        from wheeler.config import WheelerConfig

        # Create a config pointing to tmp_path
        config = WheelerConfig()
        config.knowledge_path = str(tmp_path / "knowledge")
        config.synthesis_path = str(tmp_path / "synthesis")

        # Write initial node
        node = FindingModel(
            id="F-test1234",
            description="original description",
            confidence=0.5,
            tier="generated",
            created="2026-04-16T00:00:00+00:00",
            updated="2026-04-16T00:00:00+00:00",
        )
        write_node(Path(config.knowledge_path), node)

        # Simulate update_node result
        result_str = json.dumps({
            "node_id": "F-test1234",
            "label": "Finding",
            "updated_fields": ["description"],
            "changes": {
                "description": {
                    "old": "original description",
                    "new": "updated description",
                },
            },
            "status": "updated",
        })

        json_ok, synthesis_ok = _update_knowledge_node(
            {"node_id": "F-test1234", "session_id": "test"},
            result_str,
            config,
        )
        assert json_ok is True

        # Re-read and verify
        updated = read_node(Path(config.knowledge_path), "F-test1234")
        assert updated.description == "updated description"
        assert len(updated.change_log) == 1
        assert updated.change_log[0].action == "fields_updated"
        assert updated.change_log[0].changes["description"] == [
            "original description", "updated description",
        ]

    def test_update_knowledge_node_no_file(self, tmp_path):
        """If no knowledge file exists, helper returns (False, False) gracefully."""
        from wheeler.tools.graph_tools import _update_knowledge_node
        from wheeler.config import WheelerConfig

        config = WheelerConfig()
        config.knowledge_path = str(tmp_path / "knowledge")
        config.synthesis_path = str(tmp_path / "synthesis")

        result_str = json.dumps({
            "node_id": "F-missing1",
            "label": "Finding",
            "updated_fields": ["description"],
            "changes": {"description": {"old": "a", "new": "b"}},
            "status": "updated",
        })

        json_ok, synthesis_ok = _update_knowledge_node(
            {"node_id": "F-missing1"},
            result_str,
            config,
        )
        assert json_ok is False
        assert synthesis_ok is False

    def test_update_knowledge_node_with_error_result(self, tmp_path):
        """If the result contains an error, helper skips update."""
        from wheeler.tools.graph_tools import _update_knowledge_node
        from wheeler.config import WheelerConfig

        config = WheelerConfig()
        config.knowledge_path = str(tmp_path / "knowledge")
        config.synthesis_path = str(tmp_path / "synthesis")

        result_str = json.dumps({"error": "Node not found: F-bad12345"})

        json_ok, synthesis_ok = _update_knowledge_node(
            {"node_id": "F-bad12345"},
            result_str,
            config,
        )
        assert json_ok is False
        assert synthesis_ok is False


class TestUpdateNodeSynthesis:
    """Verify that update_node re-renders the synthesis markdown."""

    def test_synthesis_file_updated(self, tmp_path):
        """After update_node, synthesis file should reflect new content."""
        from wheeler.tools.graph_tools import _update_knowledge_node
        from wheeler.knowledge.store import write_node
        from wheeler.config import WheelerConfig

        config = WheelerConfig()
        config.knowledge_path = str(tmp_path / "knowledge")
        config.synthesis_path = str(tmp_path / "synthesis")

        # Write initial node
        node = HypothesisModel(
            id="H-test1234",
            statement="old hypothesis statement",
            status="open",
            tier="generated",
            created="2026-04-16T00:00:00+00:00",
            updated="2026-04-16T00:00:00+00:00",
        )
        write_node(Path(config.knowledge_path), node)

        # Simulate update
        result_str = json.dumps({
            "node_id": "H-test1234",
            "label": "Hypothesis",
            "updated_fields": ["statement"],
            "changes": {
                "statement": {
                    "old": "old hypothesis statement",
                    "new": "revised hypothesis statement",
                },
            },
            "status": "updated",
        })

        json_ok, synthesis_ok = _update_knowledge_node(
            {"node_id": "H-test1234", "session_id": "test"},
            result_str,
            config,
        )

        assert json_ok is True
        assert synthesis_ok is True

        # Verify synthesis file exists and contains new statement
        synthesis_path = Path(config.synthesis_path) / "H-test1234.md"
        assert synthesis_path.exists()
        md_content = synthesis_path.read_text()
        assert "revised hypothesis statement" in md_content


class TestUpdateNodeToolDefinition:
    """Verify that update_node appears in TOOL_DEFINITIONS."""

    def test_update_node_in_definitions(self):
        from wheeler.tools.graph_tools import TOOL_DEFINITIONS

        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert "update_node" in names

    def test_update_node_definition_shape(self):
        from wheeler.tools.graph_tools import TOOL_DEFINITIONS

        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "update_node")
        assert tool["required"] == ["node_id"]
        assert "node_id" in tool["parameters"]
        assert "description" in tool["parameters"]
        assert "confidence" in tool["parameters"]
        assert "statement" in tool["parameters"]
        assert "title" in tool["parameters"]
        assert "content" in tool["parameters"]
        assert "question" in tool["parameters"]
        assert "priority" in tool["parameters"]
        assert "status" in tool["parameters"]
        assert "tier" in tool["parameters"]
        assert "path" in tool["parameters"]


class TestUpdateNodeRegistry:
    """Verify that update_node is in the tool registry."""

    def test_update_node_in_registry(self):
        from wheeler.tools.graph_tools import _TOOL_REGISTRY

        assert "update_node" in _TOOL_REGISTRY

    def test_update_node_not_in_mutation_tools(self):
        """update_node is NOT in _MUTATION_TOOLS (those are for creation only)."""
        from wheeler.tools.graph_tools import _MUTATION_TOOLS

        assert "update_node" not in _MUTATION_TOOLS

    def test_update_node_handler_is_callable(self):
        from wheeler.tools.graph_tools import _TOOL_REGISTRY

        assert callable(_TOOL_REGISTRY["update_node"])
