"""Tests for Wave 0 provenance migration: knowledge/ JSON file migration.

Tests filesystem migration only (no Neo4j required). Uses pytest tmp_path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wheeler.graph.migration_prov import migrate_knowledge_files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_analysis_json(knowledge_path: Path, node_id: str, **overrides) -> Path:
    """Write a minimal Analysis JSON file and return its path."""
    data = {
        "id": node_id,
        "type": "Analysis",
        "tier": "generated",
        "created": "2026-03-28T04:06:19.352337+00:00",
        "updated": "2026-03-28T04:06:19.352337+00:00",
        "tags": ["electrophysiology"],
        "script_path": "/scripts/analyze.py",
        "script_hash": "abc123def456",
        "language": "python",
        "language_version": "3.14",
        "parameters": "",
        "output_path": "",
        "output_hash": "",
        "executed_at": "2026-03-28T04:06:19.352337+00:00",
    }
    data.update(overrides)
    path = knowledge_path / f"{node_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _write_finding_json(knowledge_path: Path, node_id: str) -> Path:
    """Write a Finding JSON file (non-Analysis) to test that it's ignored."""
    data = {
        "id": node_id,
        "type": "Finding",
        "tier": "generated",
        "created": "2026-03-28T04:06:19.352337+00:00",
        "updated": "2026-03-28T04:06:19.352337+00:00",
        "tags": [],
        "description": "A finding",
        "confidence": 0.8,
    }
    path = knowledge_path / f"{node_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMigrateKnowledgeFiles:
    """Test migrate_knowledge_files() — filesystem migration of A-*.json."""

    def test_migrates_analysis_to_script_and_execution(self, tmp_path: Path):
        """An A-*.json file should produce one S-*.json and one X-*.json."""
        _write_analysis_json(tmp_path, "A-aabb0011")

        report = migrate_knowledge_files(tmp_path)

        assert report["found"] == 1
        assert report["migrated"] == 1
        assert report["errors"] == 0

        # Original should be gone
        assert not (tmp_path / "A-aabb0011.json").exists()

        # Should have exactly one S-*.json and one X-*.json
        s_files = sorted(tmp_path.glob("S-*.json"))
        x_files = sorted(tmp_path.glob("X-*.json"))
        assert len(s_files) == 1
        assert len(x_files) == 1

    def test_script_preserves_key_fields(self, tmp_path: Path):
        """Script JSON should contain path, hash, language, version from the Analysis."""
        _write_analysis_json(
            tmp_path,
            "A-preserve",
            script_path="/scripts/run.m",
            script_hash="deadbeef",
            language="matlab",
            language_version="R2024a",
            tier="reference",
        )

        migrate_knowledge_files(tmp_path)

        s_files = sorted(tmp_path.glob("S-*.json"))
        assert len(s_files) == 1
        script = json.loads(s_files[0].read_text())

        assert script["type"] == "Script"
        assert script["path"] == "/scripts/run.m"
        assert script["hash"] == "deadbeef"
        assert script["language"] == "matlab"
        assert script["version"] == "R2024a"
        assert script["tier"] == "reference"
        assert script["id"].startswith("S-")

    def test_execution_preserves_key_fields(self, tmp_path: Path):
        """Execution JSON should have kind, agent_id, status, timestamps."""
        _write_analysis_json(
            tmp_path,
            "A-exec01",
            executed_at="2026-03-28T12:00:00+00:00",
            tier="generated",
        )

        migrate_knowledge_files(tmp_path)

        x_files = sorted(tmp_path.glob("X-*.json"))
        assert len(x_files) == 1
        execution = json.loads(x_files[0].read_text())

        assert execution["type"] == "Execution"
        assert execution["kind"] == "script"
        assert execution["agent_id"] == "wheeler"
        assert execution["status"] == "completed"
        assert execution["started_at"] == "2026-03-28T12:00:00+00:00"
        assert execution["ended_at"] == "2026-03-28T12:00:00+00:00"
        assert "Migrated from Analysis A-exec01" in execution["description"]
        assert execution["id"].startswith("X-")

    def test_tags_preserved_on_both_outputs(self, tmp_path: Path):
        """Tags from the Analysis should appear on both Script and Execution."""
        _write_analysis_json(
            tmp_path,
            "A-tagged01",
            tags=["calcium", "imaging"],
        )

        migrate_knowledge_files(tmp_path)

        s_files = sorted(tmp_path.glob("S-*.json"))
        x_files = sorted(tmp_path.glob("X-*.json"))
        script = json.loads(s_files[0].read_text())
        execution = json.loads(x_files[0].read_text())

        assert script["tags"] == ["calcium", "imaging"]
        assert execution["tags"] == ["calcium", "imaging"]

    def test_empty_directory_returns_zero_counts(self, tmp_path: Path):
        """An empty knowledge directory should produce zero counts."""
        report = migrate_knowledge_files(tmp_path)

        assert report["found"] == 0
        assert report["migrated"] == 0
        assert report["errors"] == 0

    def test_nonexistent_directory_returns_zero_counts(self, tmp_path: Path):
        """A nonexistent path should return gracefully."""
        missing = tmp_path / "does_not_exist"
        report = migrate_knowledge_files(missing)

        assert report["found"] == 0
        assert report["migrated"] == 0
        assert report["errors"] == 0

    def test_non_analysis_files_are_ignored(self, tmp_path: Path):
        """Files that don't start with A- should not be touched."""
        _write_finding_json(tmp_path, "F-finding01")
        _write_analysis_json(tmp_path, "A-only0001")

        report = migrate_knowledge_files(tmp_path)

        # Only the A-* file should be migrated
        assert report["found"] == 1
        assert report["migrated"] == 1

        # Finding should still exist
        assert (tmp_path / "F-finding01.json").exists()

        # Original analysis gone
        assert not (tmp_path / "A-only0001.json").exists()

    def test_multiple_analysis_files(self, tmp_path: Path):
        """Multiple A-*.json files should each produce S + X pairs."""
        _write_analysis_json(tmp_path, "A-multi001")
        _write_analysis_json(tmp_path, "A-multi002")
        _write_analysis_json(tmp_path, "A-multi003")

        report = migrate_knowledge_files(tmp_path)

        assert report["found"] == 3
        assert report["migrated"] == 3
        assert report["errors"] == 0

        s_files = sorted(tmp_path.glob("S-*.json"))
        x_files = sorted(tmp_path.glob("X-*.json"))
        assert len(s_files) == 3
        assert len(x_files) == 3

        # No A-*.json should remain
        a_files = sorted(tmp_path.glob("A-*.json"))
        assert len(a_files) == 0

    def test_execution_uses_now_when_executed_at_empty(self, tmp_path: Path):
        """When executed_at is empty, Execution timestamps should use current time."""
        _write_analysis_json(
            tmp_path,
            "A-noexec01",
            executed_at="",
        )

        migrate_knowledge_files(tmp_path)

        x_files = sorted(tmp_path.glob("X-*.json"))
        execution = json.loads(x_files[0].read_text())

        # Should be a valid ISO timestamp (not empty)
        assert execution["started_at"] != ""
        assert execution["ended_at"] != ""

    def test_output_files_are_valid_json(self, tmp_path: Path):
        """Both S-*.json and X-*.json should be parseable JSON."""
        _write_analysis_json(tmp_path, "A-valid001")

        migrate_knowledge_files(tmp_path)

        for pattern in ("S-*.json", "X-*.json"):
            for f in tmp_path.glob(pattern):
                data = json.loads(f.read_text())
                assert "id" in data
                assert "type" in data

    def test_details_list_populated(self, tmp_path: Path):
        """The report details should list the migration mapping."""
        _write_analysis_json(tmp_path, "A-detail01")

        report = migrate_knowledge_files(tmp_path)

        assert len(report["details"]) == 1
        assert "A-detail01" in report["details"][0]
        assert "Script S-" in report["details"][0]
        assert "Execution X-" in report["details"][0]
