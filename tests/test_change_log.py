"""Tests for node change log (lightweight versioning)."""

from __future__ import annotations

import json

from wheeler.models import ChangeEntry, FindingModel


class TestChangeEntrySerialization:
    """ChangeEntry round-trips through JSON."""

    def test_change_entry_serialization(self):
        entry = ChangeEntry(
            timestamp="2026-04-08T12:00:00+00:00",
            action="created",
            actor="test-session",
            reason="initial creation",
        )
        data = json.loads(entry.model_dump_json())
        restored = ChangeEntry.model_validate(data)
        assert restored.timestamp == entry.timestamp
        assert restored.action == "created"
        assert restored.actor == "test-session"
        assert restored.reason == "initial creation"
        assert restored.changes == {}


class TestNodeBaseChangeLog:
    """NodeBase change_log field behavior."""

    def test_node_base_default_empty_change_log(self):
        node = FindingModel(
            id="F-test1234",
            description="test finding",
            confidence=0.9,
        )
        assert node.change_log == []

    def test_node_base_backward_compat(self):
        """JSON without change_log field deserializes fine (defaults to [])."""
        raw = {
            "id": "F-old12345",
            "type": "Finding",
            "description": "legacy node",
            "confidence": 0.5,
            "tier": "generated",
        }
        node = FindingModel.model_validate(raw)
        assert node.change_log == []

    def test_change_log_append(self):
        node = FindingModel(
            id="F-append01",
            description="appending test",
            confidence=0.7,
        )
        node.change_log.append(ChangeEntry(
            timestamp="2026-04-08T12:00:00+00:00",
            action="created",
            actor="session-1",
        ))
        node.change_log.append(ChangeEntry(
            timestamp="2026-04-08T13:00:00+00:00",
            action="tier_changed",
            changes={"tier": ["generated", "reference"]},
            actor="session-2",
        ))

        # Serialize and restore
        data = json.loads(node.model_dump_json())
        restored = FindingModel.model_validate(data)

        assert len(restored.change_log) == 2
        assert restored.change_log[0].action == "created"
        assert restored.change_log[1].action == "tier_changed"
        assert restored.change_log[1].changes == {"tier": ["generated", "reference"]}


class TestChangeEntryWithChangesDict:
    """Changes dict serializes correctly with typed values."""

    def test_change_entry_with_changes_dict(self):
        entry = ChangeEntry(
            timestamp="2026-04-08T14:00:00+00:00",
            action="tier_changed",
            changes={"tier": ["generated", "reference"]},
            actor="system",
        )
        data = json.loads(entry.model_dump_json())
        assert data["changes"] == {"tier": ["generated", "reference"]}

        restored = ChangeEntry.model_validate(data)
        assert restored.changes["tier"] == ["generated", "reference"]

    def test_change_entry_with_stability_changes(self):
        entry = ChangeEntry(
            timestamp="2026-04-08T14:00:00+00:00",
            action="invalidated",
            changes={
                "stale": [False, True],
                "stability": [0.8, 0.64],
            },
            actor="provenance_system",
            reason="upstream change in S-12ab34cd",
        )
        data = json.loads(entry.model_dump_json())
        restored = ChangeEntry.model_validate(data)
        assert restored.changes["stale"] == [False, True]
        assert restored.changes["stability"] == [0.8, 0.64]
        assert restored.reason == "upstream change in S-12ab34cd"
