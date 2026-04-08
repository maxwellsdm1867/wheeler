"""Tests for wheeler.consistency module."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.consistency import check_consistency, repair_consistency, ConsistencyReport


class FakeBackend:
    """Mock backend returning configured node IDs."""

    def __init__(self, node_ids):
        self._node_ids = node_ids

    async def run_cypher(self, query, parameters=None):
        return [{"id": nid} for nid in self._node_ids]

    async def initialize(self):
        pass


class TestConsistencyReport:
    def test_report_serializes(self):
        report = ConsistencyReport(
            graph_only=["F-aaa"],
            json_only=["F-bbb"],
            synthesis_missing=["F-ccc"],
            synthesis_orphaned=["F-ddd"],
            total_graph=10,
            total_json=9,
            total_synthesis=7,
        )
        d = asdict(report)
        assert d["graph_only"] == ["F-aaa"]
        assert d["total_graph"] == 10

    def test_empty_report(self):
        report = ConsistencyReport()
        assert report.graph_only == []
        assert report.total_graph == 0


class TestCheckConsistency:
    async def test_detects_synthesis_missing(self, tmp_path):
        """Nodes in JSON but not in synthesis are reported."""
        from wheeler.config import load_config
        from wheeler.models import FindingModel
        from wheeler.knowledge.store import write_node

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Create a JSON file with no matching synthesis
        model = FindingModel(
            id="F-test1111",
            type="Finding",
            description="Test finding",
            confidence=0.9,
            created="2026-04-08T00:00:00+00:00",
        )
        write_node(knowledge_dir, model)

        backend = FakeBackend(["F-test1111"])
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            report = await check_consistency(config)

        assert "F-test1111" in report.synthesis_missing
        assert report.total_json == 1
        assert report.total_synthesis == 0

    async def test_detects_synthesis_orphaned(self, tmp_path):
        """Synthesis files with no backing JSON are reported."""
        from wheeler.config import load_config

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Create orphaned synthesis file
        (synthesis_dir / "F-orphan01.md").write_text("orphaned content")

        backend = FakeBackend([])
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            report = await check_consistency(config)

        assert "F-orphan01" in report.synthesis_orphaned
        assert report.total_synthesis == 1
        assert report.total_json == 0

    async def test_detects_graph_only(self, tmp_path):
        """Nodes in graph but not in JSON are reported."""
        from wheeler.config import load_config

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        backend = FakeBackend(["F-graphonly"])
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            report = await check_consistency(config)

        assert "F-graphonly" in report.graph_only
        assert report.total_graph == 1

    async def test_detects_json_only(self, tmp_path):
        """Nodes in JSON but not in graph are reported."""
        from wheeler.config import load_config
        from wheeler.models import FindingModel
        from wheeler.knowledge.store import write_node

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        model = FindingModel(
            id="F-jsononly1",
            type="Finding",
            description="JSON only finding",
            confidence=0.5,
            created="2026-04-08T00:00:00+00:00",
        )
        write_node(knowledge_dir, model)

        # Graph returns empty set
        backend = FakeBackend([])
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            report = await check_consistency(config)

        assert "F-jsononly1" in report.json_only

    async def test_excludes_synthesis_index_files(self, tmp_path):
        """INDEX.md, OPEN_QUESTIONS.md, EVIDENCE_MAP.md are not counted as nodes."""
        from wheeler.config import load_config

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Create index files that should be excluded
        (synthesis_dir / "INDEX.md").write_text("index")
        (synthesis_dir / "OPEN_QUESTIONS.md").write_text("questions")
        (synthesis_dir / "EVIDENCE_MAP.md").write_text("evidence")

        backend = FakeBackend([])
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            report = await check_consistency(config)

        assert report.total_synthesis == 0
        assert report.synthesis_orphaned == []

    async def test_handles_graph_down_gracefully(self, tmp_path):
        """When the graph backend raises, graph_ids should be empty (not crash)."""
        from wheeler.config import load_config

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        class FailingBackend:
            async def run_cypher(self, query, parameters=None):
                raise ConnectionError("Neo4j is down")

            async def initialize(self):
                pass

        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=FailingBackend(),
        ):
            report = await check_consistency(config)

        assert report.total_graph == 0
        assert report.graph_only == []

    async def test_perfect_consistency(self, tmp_path):
        """When all layers agree, all diff lists should be empty."""
        from wheeler.config import load_config
        from wheeler.models import FindingModel
        from wheeler.knowledge.store import write_node, write_synthesis

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        model = FindingModel(
            id="F-perfect1",
            type="Finding",
            description="All layers agree",
            confidence=0.95,
            created="2026-04-08T00:00:00+00:00",
        )
        write_node(knowledge_dir, model)
        write_synthesis(synthesis_dir, "F-perfect1", "# Finding\n")

        backend = FakeBackend(["F-perfect1"])
        with patch(
            "wheeler.tools.graph_tools._get_backend",
            new_callable=AsyncMock,
            return_value=backend,
        ):
            report = await check_consistency(config)

        assert report.graph_only == []
        assert report.json_only == []
        assert report.synthesis_missing == []
        assert report.synthesis_orphaned == []
        assert report.total_graph == 1
        assert report.total_json == 1
        assert report.total_synthesis == 1


class TestRepairConsistency:
    async def test_dry_run_produces_actions_no_writes(self, tmp_path):
        """dry_run=True should list actions but not create files."""
        from wheeler.config import load_config

        config = load_config()
        config.knowledge_path = str(tmp_path / "knowledge")
        config.synthesis_path = str(tmp_path / "synthesis")

        report = ConsistencyReport(synthesis_missing=["F-test1"])
        result = await repair_consistency(config, report, dry_run=True)
        assert result["dry_run"] is True
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "regenerate_synthesis"
        assert result["actions"][0]["dry_run"] is True
        # No file should have been created
        assert not (tmp_path / "synthesis" / "F-test1.md").exists()

    async def test_repair_regenerates_synthesis(self, tmp_path):
        """With a real JSON file and dry_run=False, synthesis should be created."""
        from wheeler.config import load_config
        from wheeler.models import FindingModel
        from wheeler.knowledge.store import write_node

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Create a JSON file
        model = FindingModel(
            id="F-test1",
            type="Finding",
            description="Test finding",
            confidence=0.9,
            created="2026-04-08T00:00:00+00:00",
        )
        write_node(knowledge_dir, model)

        report = ConsistencyReport(synthesis_missing=["F-test1"])
        result = await repair_consistency(config, report, dry_run=False)
        assert result["dry_run"] is False
        assert result["actions"][0]["status"] == "ok"
        assert (synthesis_dir / "F-test1.md").exists()

    async def test_repair_deletes_orphaned_synthesis(self, tmp_path):
        """Orphaned synthesis files should be deleted."""
        from wheeler.config import load_config

        config = load_config()
        synthesis_dir = tmp_path / "synthesis"
        synthesis_dir.mkdir()
        config.synthesis_path = str(synthesis_dir)
        config.knowledge_path = str(tmp_path / "knowledge")

        # Create orphaned synthesis file
        (synthesis_dir / "F-orphan.md").write_text("orphaned")

        report = ConsistencyReport(synthesis_orphaned=["F-orphan"])
        result = await repair_consistency(config, report, dry_run=False)
        assert result["actions"][0]["status"] == "ok"
        assert not (synthesis_dir / "F-orphan.md").exists()

    async def test_repair_reports_graph_only_as_warning(self, tmp_path):
        """graph_only nodes produce warn_graph_only actions."""
        from wheeler.config import load_config

        config = load_config()
        config.knowledge_path = str(tmp_path / "knowledge")
        config.synthesis_path = str(tmp_path / "synthesis")

        report = ConsistencyReport(graph_only=["F-gonly1", "F-gonly2"])
        result = await repair_consistency(config, report, dry_run=False)
        warn_actions = [a for a in result["actions"] if a["action"] == "warn_graph_only"]
        assert len(warn_actions) == 2
        assert warn_actions[0]["node_id"] == "F-gonly1"

    async def test_repair_reports_json_only_as_warning(self, tmp_path):
        """json_only nodes produce warn_json_only actions."""
        from wheeler.config import load_config

        config = load_config()
        config.knowledge_path = str(tmp_path / "knowledge")
        config.synthesis_path = str(tmp_path / "synthesis")

        report = ConsistencyReport(json_only=["F-jonly1"])
        result = await repair_consistency(config, report, dry_run=False)
        warn_actions = [a for a in result["actions"] if a["action"] == "warn_json_only"]
        assert len(warn_actions) == 1
        assert warn_actions[0]["node_id"] == "F-jonly1"

    async def test_repair_handles_missing_json_gracefully(self, tmp_path):
        """If the JSON file is gone when repair runs, it should log an error, not crash."""
        from wheeler.config import load_config

        config = load_config()
        knowledge_dir = tmp_path / "knowledge"
        synthesis_dir = tmp_path / "synthesis"
        knowledge_dir.mkdir()
        synthesis_dir.mkdir()
        config.knowledge_path = str(knowledge_dir)
        config.synthesis_path = str(synthesis_dir)

        # Report says F-gone needs synthesis, but the JSON file does not exist
        report = ConsistencyReport(synthesis_missing=["F-gone"])
        result = await repair_consistency(config, report, dry_run=False)
        assert result["actions"][0]["status"] == "error"
        assert "F-gone" in result["actions"][0]["error"]

    async def test_total_count_matches_actions(self, tmp_path):
        """The total field should match the number of actions."""
        from wheeler.config import load_config

        config = load_config()
        config.knowledge_path = str(tmp_path / "knowledge")
        config.synthesis_path = str(tmp_path / "synthesis")

        report = ConsistencyReport(
            synthesis_missing=["F-a", "F-b"],
            synthesis_orphaned=["F-c"],
            graph_only=["F-d"],
            json_only=["F-e"],
        )
        result = await repair_consistency(config, report, dry_run=True)
        assert result["total"] == len(result["actions"])
        assert result["total"] == 5
