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


class TestSummarizeDrift:
    def test_empty_report_is_clean(self):
        from wheeler.consistency import summarize_drift

        summary = summarize_drift(ConsistencyReport())
        assert summary["total_divergent"] == 0
        assert summary["exceeds_threshold"] is False
        assert "json_only_by_prefix" not in summary
        assert "graph_only_by_prefix" not in summary

    def test_counts_all_categories(self):
        from wheeler.consistency import summarize_drift

        report = ConsistencyReport(
            graph_only=["X-a", "F-b"],
            json_only=["A-c"],
            synthesis_missing=["A-c", "W-d"],
            synthesis_orphaned=["F-e"],
        )
        summary = summarize_drift(report)
        assert summary["graph_only"] == 2
        assert summary["json_only"] == 1
        assert summary["synthesis_missing"] == 2
        assert summary["synthesis_orphaned"] == 1
        assert summary["total_divergent"] == 6

    def test_threshold_boundary(self):
        from wheeler.consistency import summarize_drift

        report = ConsistencyReport(json_only=[f"F-{i:04d}" for i in range(10)])
        assert summarize_drift(report, threshold=10)["exceeds_threshold"] is False
        report = ConsistencyReport(json_only=[f"F-{i:04d}" for i in range(11)])
        assert summarize_drift(report, threshold=10)["exceeds_threshold"] is True

    def test_prefix_breakdown_flags_whole_node_class(self):
        """An entire node class missing from the graph (legacy A-* Analysis
        files that only exist in JSON) shows up as a single loud prefix count."""
        from wheeler.consistency import summarize_drift

        report = ConsistencyReport(
            json_only=[f"A-{i:08x}" for i in range(15)] + ["W-aaaa", "W-bbbb"],
            graph_only=["X-1111", "X-2222", "F-3333"],
        )
        summary = summarize_drift(report)
        assert summary["json_only_by_prefix"]["A"] == 15
        assert summary["json_only_by_prefix"]["W"] == 2
        assert summary["graph_only_by_prefix"]["X"] == 2
        assert summary["graph_only_by_prefix"]["F"] == 1

    def test_default_threshold_constant(self):
        from wheeler.consistency import DRIFT_WARNING_THRESHOLD, summarize_drift

        summary = summarize_drift(ConsistencyReport())
        assert summary["threshold"] == DRIFT_WARNING_THRESHOLD


class TestGraphHealthDriftSurfacing:
    """graph_health surfaces triple-write drift proactively (issue #60)."""

    async def test_warns_when_drift_exceeds_threshold(self):
        report = ConsistencyReport(
            json_only=[f"A-{i:08x}" for i in range(20)],
            total_graph=5,
            total_json=25,
            total_synthesis=5,
        )
        mock_counts = {"Finding": 5}
        with patch(
            "wheeler.mcp_core.schema.get_status",
            new_callable=AsyncMock,
            return_value=mock_counts,
        ), patch(
            "wheeler.consistency.check_consistency",
            new_callable=AsyncMock,
            return_value=report,
        ):
            from wheeler.mcp_core import graph_health

            result = await graph_health()

        assert result["status"] == "connected"
        assert result["drift"]["total_divergent"] == 20
        assert result["drift"]["exceeds_threshold"] is True
        assert result["drift"]["json_only_by_prefix"]["A"] == 20
        assert any("drift" in w.lower() for w in result.get("warnings", []))

    async def test_no_drift_warning_below_threshold(self):
        report = ConsistencyReport(
            json_only=["F-aaaa"],
            total_graph=10,
            total_json=11,
            total_synthesis=11,
        )
        mock_counts = {"Finding": 10}
        with patch(
            "wheeler.mcp_core.schema.get_status",
            new_callable=AsyncMock,
            return_value=mock_counts,
        ), patch(
            "wheeler.consistency.check_consistency",
            new_callable=AsyncMock,
            return_value=report,
        ):
            from wheeler.mcp_core import graph_health

            result = await graph_health()

        assert result["status"] == "connected"
        assert result["drift"]["total_divergent"] == 1
        assert result["drift"]["exceeds_threshold"] is False
        assert not any(
            "drift" in w.lower() for w in result.get("warnings", [])
        )

    async def test_offline_graph_skips_drift_check(self):
        mock_counts = {"Finding": 0, "_status": "offline", "_error": "Connection refused"}
        with patch(
            "wheeler.mcp_core.schema.get_status",
            new_callable=AsyncMock,
            return_value=mock_counts,
        ):
            from wheeler.mcp_core import graph_health

            result = await graph_health()

        assert result["status"] == "offline"
        assert "drift" not in result

    async def test_drift_check_failure_is_nonfatal(self):
        mock_counts = {"Finding": 3}
        with patch(
            "wheeler.mcp_core.schema.get_status",
            new_callable=AsyncMock,
            return_value=mock_counts,
        ), patch(
            "wheeler.consistency.check_consistency",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            from wheeler.mcp_core import graph_health

            result = await graph_health()

        assert result["status"] == "connected"
        assert result["drift"] == {"error": "boom"}


class TestConsistencyCheckSummary:
    """graph_consistency_check includes the compact drift summary (issue #60)."""

    async def test_result_includes_summary(self):
        report = ConsistencyReport(
            json_only=["A-aaaa"],
            graph_only=["X-bbbb"],
            total_graph=2,
            total_json=2,
            total_synthesis=1,
        )
        with patch(
            "wheeler.consistency.check_consistency",
            new_callable=AsyncMock,
            return_value=report,
        ):
            from wheeler.mcp_ops import graph_consistency_check

            result = await graph_consistency_check(repair=False)

        assert result["summary"]["total_divergent"] == 2
        assert result["summary"]["json_only_by_prefix"] == {"A": 1}
        assert result["summary"]["graph_only_by_prefix"] == {"X": 1}
        assert result["summary"]["exceeds_threshold"] is False
