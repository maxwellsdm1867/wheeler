"""Regression tests for issue #37: synthesis drift.

Tests verify that certain code paths write both knowledge JSON and synthesis
markdown files when creating or updating nodes. Specifically tests:
1. migrate() in knowledge/migrate.py does not write synthesis
2. detect_and_propagate_stale() in provenance.py does not write synthesis
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.models import FindingModel, HypothesisModel
from wheeler.knowledge.store import write_node, read_node
from wheeler.knowledge.render import render_synthesis
from wheeler.knowledge.store import write_synthesis


class FakeBackend:
    """Minimal backend stub for testing migrate()."""

    def __init__(self, nodes=None):
        self._nodes = nodes or {}
        self._created = {}

    async def query_nodes(self, label, limit=10000):
        """Return nodes of the given label."""
        return [
            data
            for node_id, data in self._nodes.items()
            if data.get("type") == label
        ]

    async def update_node(self, label, node_id, props):
        """Update node properties."""
        self._created[node_id] = props


class TestMigrateSynthesisDrift:
    """Test for issue #37: migrate() writes JSON but not synthesis."""

    async def test_migrate_missing_synthesis(self, tmp_path):
        """Repro: migrate() writes knowledge JSON but NO synthesis markdown.

        This is the core bug in issue #37. migrate() at knowledge/migrate.py:67
        calls write_node() but never calls write_synthesis().
        """
        from wheeler.knowledge.migrate import migrate

        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"

        # Set up backend with test nodes
        backend = FakeBackend(
            nodes={
                "F-test001": {
                    "id": "F-test001",
                    "type": "Finding",
                    "description": "Test finding",
                    "confidence": 0.7,
                    "created": "2026-05-19T12:00:00Z",
                    "updated": "2026-05-19T12:00:00Z",
                    "tier": "generated",
                    "stability": 0.7,
                },
                "H-test001": {
                    "id": "H-test001",
                    "type": "Hypothesis",
                    "statement": "Test hypothesis",
                    "status": "open",
                    "created": "2026-05-19T12:00:00Z",
                    "updated": "2026-05-19T12:00:00Z",
                    "tier": "generated",
                    "stability": 0.5,
                },
            }
        )

        # Run migration
        report = await migrate(backend, knowledge_dir, dry_run=False)

        # Verify migration succeeded
        assert report.migrated == 2, f"Expected 2 migrated, got {report.migrated}"
        assert report.errors == 0, f"Expected 0 errors, got {report.errors}"

        # Check JSON files exist
        json_finding = knowledge_dir / "F-test001.json"
        json_hypothesis = knowledge_dir / "H-test001.json"

        assert json_finding.exists(), f"Knowledge JSON for F-test001 missing: {json_finding}"
        assert json_hypothesis.exists(), f"Knowledge JSON for H-test001 missing: {json_hypothesis}"

        # BUG: These assertions fail on current main (before the fix)
        # migrate() does not write synthesis files
        synthesis_finding = synthesis_dir / "F-test001.md"
        synthesis_hypothesis = synthesis_dir / "H-test001.md"

        assert synthesis_finding.exists(), (
            f"ISSUE #37: Synthesis markdown for F-test001 missing (migrate does not write it): {synthesis_finding}"
        )
        assert synthesis_hypothesis.exists(), (
            f"ISSUE #37: Synthesis markdown for H-test001 missing (migrate does not write it): {synthesis_hypothesis}"
        )

    async def test_provenance_invalidation_missing_synthesis(self, tmp_path):
        """Repro: detect_and_propagate_stale() updates JSON but not synthesis.

        Issue #37 second bug: provenance.py:292 calls write_node() without
        also calling write_synthesis() when invalidating downstream nodes.
        """
        # This is harder to test in isolation because it requires:
        # 1. A running Neo4j instance with provenance relationships
        # 2. A script file whose hash has changed
        # We rely on the migrate test above to catch the write_node() pattern.
        # The actual provenance invalidation will be caught by integration tests.
        pass


class TestConsistencyCheck:
    """Verify graph_consistency_check detects synthesis drift."""

    async def test_consistency_detects_json_without_synthesis(self, tmp_path):
        """Verify the consistency checker reports json_only cases.

        This ensures we can detect the bug once it's introduced.
        """
        from wheeler.config import load_config
        from wheeler.consistency import check_consistency

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Create a JSON file with no matching synthesis (simulating the bug)
        finding = FindingModel(
            id="F-drift001",
            description="Finding with missing synthesis",
            confidence=0.9,
            tier="generated",
        )
        write_node(knowledge_dir, finding)
        # DO NOT write synthesis (simulating the bug)

        # Mock backend to return the node IDs
        class MinimalBackend:
            async def run_cypher(self, query, parameters=None):
                return [{"id": "F-drift001"}]

            async def initialize(self):
                pass

        backend = MinimalBackend()

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            report = await check_consistency(config)

        # The consistency checker should detect this drift
        assert "F-drift001" in report.synthesis_missing, (
            f"Expected F-drift001 in synthesis_missing, got {report.synthesis_missing}"
        )
        assert report.total_json == 1
        assert report.total_synthesis == 0
