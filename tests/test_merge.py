"""Tests for wheeler.merge entity resolution module.

Uses FakeBackend and tmp_path to test propose_merge, execute_merge,
and the underlying helpers without requiring a running Neo4j instance.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.models import (
    ChangeEntry,
    FindingModel,
    HypothesisModel,
    OpenQuestionModel,
)
from wheeler.knowledge.store import write_node
from wheeler.merge import (
    _find_conflicts,
    _merge_metadata,
    execute_merge,
    propose_merge,
)

NOW = datetime.now(timezone.utc).isoformat()
EARLIER = "2025-01-01T00:00:00+00:00"
LATER = "2026-06-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(node_id: str = "F-aabb0011", **overrides) -> FindingModel:
    defaults = dict(
        id=node_id,
        description="Spike rate increases with temperature",
        confidence=0.85,
        tier="generated",
        created=NOW,
        updated=NOW,
        tags=["electrophysiology"],
    )
    defaults.update(overrides)
    return FindingModel(**defaults)


def _make_hypothesis(node_id: str = "H-cc221100", **overrides) -> HypothesisModel:
    defaults = dict(
        id=node_id,
        statement="Na+ channel kinetics explain temperature sensitivity",
        status="open",
        tier="generated",
        created=NOW,
        updated=NOW,
        tags=["ion-channels"],
    )
    defaults.update(overrides)
    return HypothesisModel(**defaults)


def _write_finding_to_disk(knowledge_dir: Path, model: FindingModel) -> None:
    write_node(knowledge_dir, model)


def _make_config(tmp_path: Path):
    """Build a minimal WheelerConfig-like object for tests."""
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    synthesis_dir = tmp_path / "synthesis"
    synthesis_dir.mkdir(exist_ok=True)

    config = MagicMock()
    config.knowledge_path = str(knowledge_dir)
    config.synthesis_path = str(synthesis_dir)
    config.search = MagicMock()
    config.search.store_path = str(tmp_path / "embeddings")
    return config


class FakeBackend:
    """Minimal in-memory graph backend for testing merge logic."""

    def __init__(self):
        self.cypher_responses: list[list[dict]] = []
        self._cypher_call_index = 0
        self.deleted_nodes: list[tuple[str, str]] = []
        self.delete_should_fail = False

    def queue_cypher(self, response: list[dict]) -> None:
        self.cypher_responses.append(response)

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        if self._cypher_call_index < len(self.cypher_responses):
            result = self.cypher_responses[self._cypher_call_index]
            self._cypher_call_index += 1
            return result
        return []

    async def delete_node(self, label: str, node_id: str) -> bool:
        if self.delete_should_fail:
            raise RuntimeError("Simulated graph delete failure")
        self.deleted_nodes.append((label, node_id))
        return True


# ---------------------------------------------------------------------------
# propose_merge tests
# ---------------------------------------------------------------------------


class TestProposeMerge:
    @pytest.mark.asyncio
    async def test_propose_merge_keeps_more_connected(self, tmp_path):
        """Node with more relationships is chosen as the keeper."""
        config = _make_config(tmp_path)
        knowledge_dir = Path(config.knowledge_path)

        model_a = _make_finding("F-aaaa0001", description="Finding A", created=NOW)
        model_b = _make_finding("F-bbbb0002", description="Finding B", created=NOW)
        _write_finding_to_disk(knowledge_dir, model_a)
        _write_finding_to_disk(knowledge_dir, model_b)

        backend = FakeBackend()
        # count_relationships for A: 2
        backend.queue_cypher([{"cnt": 2}])
        # count_relationships for B: 5
        backend.queue_cypher([{"cnt": 5}])
        # _get_relationships for merge_from (A, since B has more)
        backend.queue_cypher([])  # outgoing
        backend.queue_cypher([])  # incoming

        with patch("wheeler.tools.graph_tools._get_backend", new=AsyncMock(return_value=backend)):
            result = await propose_merge(config, "F-aaaa0001", "F-bbbb0002")

        assert result["keep"] == "F-bbbb0002"
        assert result["merge_from"] == "F-aaaa0001"
        assert result["keep_relationships"] == 5
        assert result["merge_from_relationships"] == 2

    @pytest.mark.asyncio
    async def test_propose_merge_type_mismatch(self, tmp_path):
        """Different node types returns an error."""
        config = _make_config(tmp_path)
        knowledge_dir = Path(config.knowledge_path)

        finding = _make_finding("F-aaaa0001")
        hyp = _make_hypothesis("H-cc221100")
        write_node(knowledge_dir, finding)
        write_node(knowledge_dir, hyp)

        backend = FakeBackend()

        with patch("wheeler.tools.graph_tools._get_backend", new=AsyncMock(return_value=backend)):
            result = await propose_merge(config, "F-aaaa0001", "H-cc221100")

        assert "error" in result
        assert "Cannot merge different types" in result["error"]

    @pytest.mark.asyncio
    async def test_propose_merge_missing_node(self, tmp_path):
        """Missing node returns error."""
        config = _make_config(tmp_path)
        backend = FakeBackend()

        with patch("wheeler.tools.graph_tools._get_backend", new=AsyncMock(return_value=backend)):
            result = await propose_merge(config, "F-nonexist", "F-also-gone")

        assert "error" in result
        assert "Node not found" in result["error"]

    @pytest.mark.asyncio
    async def test_propose_finds_conflicts(self, tmp_path):
        """Different descriptions are reported as conflicts."""
        config = _make_config(tmp_path)
        knowledge_dir = Path(config.knowledge_path)

        model_a = _make_finding("F-aaaa0001", description="Description Alpha")
        model_b = _make_finding("F-bbbb0002", description="Description Beta")
        _write_finding_to_disk(knowledge_dir, model_a)
        _write_finding_to_disk(knowledge_dir, model_b)

        backend = FakeBackend()
        # Equal counts => tie
        backend.queue_cypher([{"cnt": 1}])
        backend.queue_cypher([{"cnt": 1}])
        backend.queue_cypher([])  # outgoing for merge_from
        backend.queue_cypher([])  # incoming for merge_from

        with patch("wheeler.tools.graph_tools._get_backend", new=AsyncMock(return_value=backend)):
            result = await propose_merge(config, "F-aaaa0001", "F-bbbb0002")

        assert "field_conflicts" in result
        desc_conflict = [c for c in result["field_conflicts"] if c["field"] == "description"]
        assert len(desc_conflict) == 1

    @pytest.mark.asyncio
    async def test_propose_merge_tie_keeps_earlier(self, tmp_path):
        """Equal relationship counts: earlier created date wins."""
        config = _make_config(tmp_path)
        knowledge_dir = Path(config.knowledge_path)

        model_a = _make_finding("F-aaaa0001", created=LATER)
        model_b = _make_finding("F-bbbb0002", created=EARLIER)
        _write_finding_to_disk(knowledge_dir, model_a)
        _write_finding_to_disk(knowledge_dir, model_b)

        backend = FakeBackend()
        # Equal counts
        backend.queue_cypher([{"cnt": 3}])
        backend.queue_cypher([{"cnt": 3}])
        backend.queue_cypher([])  # outgoing for merge_from
        backend.queue_cypher([])  # incoming for merge_from

        with patch("wheeler.tools.graph_tools._get_backend", new=AsyncMock(return_value=backend)):
            result = await propose_merge(config, "F-aaaa0001", "F-bbbb0002")

        # B was created earlier, so B is kept
        assert result["keep"] == "F-bbbb0002"
        assert result["merge_from"] == "F-aaaa0001"


# ---------------------------------------------------------------------------
# execute_merge tests
# ---------------------------------------------------------------------------


class TestExecuteMerge:
    @pytest.mark.asyncio
    async def test_execute_merge_redirects_and_deletes(self, tmp_path):
        """Full merge flow: redirect relationships, delete merge_from, update files."""
        config = _make_config(tmp_path)
        knowledge_dir = Path(config.knowledge_path)
        synthesis_dir = Path(config.synthesis_path)

        keep = _make_finding("F-keep0001", description="Keeper finding", tags=["alpha"])
        merge_from = _make_finding("F-merge002", description="Merge finding", tags=["beta"])
        _write_finding_to_disk(knowledge_dir, keep)
        _write_finding_to_disk(knowledge_dir, merge_from)

        # Also create synthesis files for both
        (synthesis_dir / "F-keep0001.md").write_text("# Keep", encoding="utf-8")
        (synthesis_dir / "F-merge002.md").write_text("# Merge", encoding="utf-8")

        backend = FakeBackend()
        # _redirect_relationships outgoing query
        backend.queue_cypher([
            {"rel": "SUPPORTS", "tid": "H-target01", "tlabel": "Hypothesis"},
        ])
        # _redirect_relationships: CREATE for outgoing redirect
        backend.queue_cypher([])
        # _redirect_relationships incoming query
        backend.queue_cypher([])

        with patch("wheeler.tools.graph_tools._get_backend", new=AsyncMock(return_value=backend)):
            result = await execute_merge(config, "F-keep0001", "F-merge002")

        assert result["status"] == "merged"
        assert result["keep"] == "F-keep0001"
        assert result["merged_from"] == "F-merge002"
        assert result["relationships_redirected"] == 1

        # Keep node's JSON should exist and be updated
        assert (knowledge_dir / "F-keep0001.json").exists()
        # Merge from's JSON should be deleted
        assert not (knowledge_dir / "F-merge002.json").exists()
        # Merge from's synthesis should be deleted
        assert not (synthesis_dir / "F-merge002.md").exists()
        # Keep's synthesis should exist (updated)
        assert (synthesis_dir / "F-keep0001.md").exists()

        # Backend received a delete call
        assert ("Finding", "F-merge002") in backend.deleted_nodes

    @pytest.mark.asyncio
    async def test_execute_merge_graph_failure_rolls_back(self, tmp_path):
        """If graph delete fails, temp files are cleaned up."""
        config = _make_config(tmp_path)
        knowledge_dir = Path(config.knowledge_path)
        synthesis_dir = Path(config.synthesis_path)

        keep = _make_finding("F-keep0001")
        merge_from = _make_finding("F-merge002")
        _write_finding_to_disk(knowledge_dir, keep)
        _write_finding_to_disk(knowledge_dir, merge_from)

        backend = FakeBackend()
        backend.delete_should_fail = True
        # _redirect_relationships queries
        backend.queue_cypher([])  # outgoing
        backend.queue_cypher([])  # incoming

        with patch("wheeler.tools.graph_tools._get_backend", new=AsyncMock(return_value=backend)):
            result = await execute_merge(config, "F-keep0001", "F-merge002")

        assert result["status"] == "failed"
        assert "Graph delete failed" in result["error"]
        # Temp files should be cleaned up
        assert not (knowledge_dir / "F-keep0001.json.merge-tmp").exists()
        assert not (synthesis_dir / "F-keep0001.md.merge-tmp").exists()
        # Original files should still be intact
        assert (knowledge_dir / "F-keep0001.json").exists()
        assert (knowledge_dir / "F-merge002.json").exists()

    @pytest.mark.asyncio
    async def test_execute_merge_records_change_log(self, tmp_path):
        """Merged node has a change_log entry with action='merged'."""
        config = _make_config(tmp_path)
        knowledge_dir = Path(config.knowledge_path)

        keep = _make_finding("F-keep0001")
        merge_from = _make_finding("F-merge002")
        _write_finding_to_disk(knowledge_dir, keep)
        _write_finding_to_disk(knowledge_dir, merge_from)

        backend = FakeBackend()
        backend.queue_cypher([])  # outgoing
        backend.queue_cypher([])  # incoming

        with patch("wheeler.tools.graph_tools._get_backend", new=AsyncMock(return_value=backend)):
            result = await execute_merge(config, "F-keep0001", "F-merge002")

        assert result["status"] == "merged"

        # Read back the kept node and check change_log
        from wheeler.knowledge.store import read_node
        kept = read_node(knowledge_dir, "F-keep0001")
        merged_entries = [e for e in kept.change_log if e.action == "merged"]
        assert len(merged_entries) == 1
        assert "F-merge002" in merged_entries[0].changes["merged_from"]
        assert merged_entries[0].actor == "entity_resolution"


# ---------------------------------------------------------------------------
# _merge_metadata tests
# ---------------------------------------------------------------------------


class TestMergeMetadata:
    def test_merge_metadata_unions_tags(self):
        """Tag union produces the combined set."""
        keep = _make_finding(tags=["alpha", "beta"])
        merge = _make_finding(tags=["beta", "gamma"])
        _merge_metadata(keep, merge)
        assert set(keep.tags) == {"alpha", "beta", "gamma"}

    def test_merge_metadata_takes_higher_confidence(self):
        """Higher confidence from merge node is adopted."""
        keep = _make_finding(confidence=0.6)
        merge = _make_finding(confidence=0.9)
        _merge_metadata(keep, merge)
        assert keep.confidence == 0.9

    def test_merge_metadata_keeps_own_confidence_when_higher(self):
        """Keep's confidence stays if already higher."""
        keep = _make_finding(confidence=0.95)
        merge = _make_finding(confidence=0.5)
        _merge_metadata(keep, merge)
        assert keep.confidence == 0.95

    def test_merge_metadata_takes_earlier_created(self):
        """Earlier created date is adopted."""
        keep = _make_finding(created=LATER)
        merge = _make_finding(created=EARLIER)
        _merge_metadata(keep, merge)
        assert keep.created == EARLIER

    def test_merge_metadata_keeps_own_created_when_earlier(self):
        """Keep's created date stays if already earlier."""
        keep = _make_finding(created=EARLIER)
        merge = _make_finding(created=LATER)
        _merge_metadata(keep, merge)
        assert keep.created == EARLIER

    def test_merge_metadata_promotes_tier(self):
        """Reference tier wins over generated."""
        keep = _make_finding(tier="generated")
        merge = _make_finding(tier="reference")
        _merge_metadata(keep, merge)
        assert keep.tier == "reference"

    def test_merge_metadata_keeps_reference_tier(self):
        """Keep's reference tier is not demoted."""
        keep = _make_finding(tier="reference")
        merge = _make_finding(tier="generated")
        _merge_metadata(keep, merge)
        assert keep.tier == "reference"


# ---------------------------------------------------------------------------
# _find_conflicts tests
# ---------------------------------------------------------------------------


class TestFindConflicts:
    def test_find_conflicts_empty_when_same(self):
        """Identical nodes produce no conflicts."""
        a = _make_finding(description="Same desc", confidence=0.8, tags=["x"])
        b = _make_finding(description="Same desc", confidence=0.8, tags=["x"])
        conflicts = _find_conflicts(a, b)
        assert conflicts == []

    def test_find_conflicts_reports_description(self):
        """Different descriptions are flagged."""
        a = _make_finding(description="Alpha finding")
        b = _make_finding(description="Beta finding")
        conflicts = _find_conflicts(a, b)
        field_names = [c["field"] for c in conflicts]
        assert "description" in field_names

    def test_find_conflicts_reports_confidence(self):
        """Different confidence values are flagged."""
        a = _make_finding(confidence=0.5)
        b = _make_finding(confidence=0.9)
        conflicts = _find_conflicts(a, b)
        field_names = [c["field"] for c in conflicts]
        assert "confidence" in field_names

    def test_find_conflicts_reports_new_tags(self):
        """Tags only in merge node are flagged."""
        a = _make_finding(tags=["alpha"])
        b = _make_finding(tags=["alpha", "beta"])
        conflicts = _find_conflicts(a, b)
        field_names = [c["field"] for c in conflicts]
        assert "tags" in field_names

    def test_find_conflicts_no_tag_conflict_when_subset(self):
        """Merge tags that are a subset of keep tags produce no tag conflict."""
        a = _make_finding(tags=["alpha", "beta"])
        b = _make_finding(tags=["alpha"])
        conflicts = _find_conflicts(a, b)
        field_names = [c["field"] for c in conflicts]
        assert "tags" not in field_names
