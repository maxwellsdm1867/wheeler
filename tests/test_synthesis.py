"""Tests for synthesis markdown rendering and writing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler.knowledge.render import render_synthesis, _obsidian_backlinks
from wheeler.knowledge.store import write_synthesis
from wheeler.models import (
    FindingModel,
    HypothesisModel,
    OpenQuestionModel,
    PaperModel,
    ResearchNoteModel,
)


class TestObsidianBacklinks:
    """Test citation-to-backlink conversion."""

    def test_converts_finding_citation(self):
        assert _obsidian_backlinks("[F-3a2b]") == "[[F-3a2b]]"

    def test_converts_hypothesis_citation(self):
        assert _obsidian_backlinks("[H-12345678]") == "[[H-12345678]]"

    def test_converts_multiple_citations(self):
        text = "See [F-3a2b] and [H-5678] for details"
        assert _obsidian_backlinks(text) == "See [[F-3a2b]] and [[H-5678]] for details"

    def test_ignores_non_node_brackets(self):
        text = "[some text] and [F-3a2b]"
        assert _obsidian_backlinks(text) == "[some text] and [[F-3a2b]]"

    def test_handles_all_prefixes(self):
        for prefix in ["F", "H", "Q", "D", "P", "W", "S", "X", "N", "L"]:
            text = f"[{prefix}-abcd1234]"
            assert _obsidian_backlinks(text) == f"[[{prefix}-abcd1234]]"

    def test_handles_plan_prefix(self):
        assert _obsidian_backlinks("[PL-abcd1234]") == "[[PL-abcd1234]]"


class TestRenderSynthesis:
    """Test synthesis markdown output."""

    def test_finding_has_frontmatter(self):
        model = FindingModel(
            id="F-test1234",
            description="tau_rise = 0.12ms",
            confidence=0.88,
            tier="generated",
            created="2026-04-05T12:00:00Z",
        )
        md = render_synthesis(model)
        assert md.startswith("---\n")
        assert "id: F-test1234" in md
        assert "type: Finding" in md
        assert "tier: generated" in md
        assert "confidence: 0.88" in md
        assert "created: 2026-04-05" in md

    def test_finding_has_body(self):
        model = FindingModel(
            id="F-test1234",
            description="tau_rise = 0.12ms",
            confidence=0.88,
        )
        md = render_synthesis(model)
        assert "tau_rise = 0.12ms" in md
        assert "# Finding [F-test1234]" in md

    def test_finding_with_artifact(self):
        model = FindingModel(
            id="F-test1234",
            description="VP-loss curve",
            confidence=0.85,
            path="figures/vploss.png",
            artifact_type="figure",
        )
        md = render_synthesis(model)
        assert "artifact_type: figure" in md
        assert "![figure](figures/vploss.png)" in md

    def test_finding_with_source(self):
        model = FindingModel(
            id="F-test1234",
            description="Collaborator result",
            confidence=0.9,
            source="Jane Doe",
        )
        md = render_synthesis(model)
        assert "source: Jane Doe" in md
        assert "*Source*: Jane Doe" in md

    def test_hypothesis_has_status_in_frontmatter(self):
        model = HypothesisModel(
            id="H-test5678",
            statement="Cell type determines timing",
            status="open",
            tier="generated",
        )
        md = render_synthesis(model)
        assert "status: open" in md
        assert "type: Hypothesis" in md

    def test_paper_has_year_and_doi(self):
        model = PaperModel(
            id="P-test9999",
            title="Spike Response Model",
            authors="Gerstner",
            year=1995,
            doi="10.1162/neco.1995",
            tier="reference",
        )
        md = render_synthesis(model)
        assert "year: 1995" in md
        assert "doi: 10.1162/neco.1995" in md
        assert "tier: reference" in md

    def test_question_has_priority(self):
        model = OpenQuestionModel(
            id="Q-testaaaa",
            question="Does cell type affect tau?",
            priority=8,
        )
        md = render_synthesis(model)
        assert "priority: 8" in md

    def test_tags_in_frontmatter(self):
        model = FindingModel(
            id="F-tagged01",
            description="tagged finding",
            confidence=0.5,
            tags=["electrophysiology", "parasol"],
        )
        md = render_synthesis(model)
        assert "tags:" in md
        assert "  - electrophysiology" in md
        assert "  - parasol" in md

    def test_relationships_section(self):
        model = FindingModel(
            id="F-test1234",
            description="A finding",
            confidence=0.8,
        )
        rels = [
            {
                "target_id": "H-5678abcd",
                "relationship": "SUPPORTS",
                "target_title": "Some hypothesis",
                "direction": "outgoing",
            },
            {
                "source_id": "P-aaaa1111",
                "relationship": "CITES",
                "target_title": "A paper",
                "direction": "incoming",
            },
        ]
        md = render_synthesis(model, relationships=rels)
        assert "## Relationships" in md
        assert "**SUPPORTS** [[H-5678abcd]]" in md
        assert "[[P-aaaa1111]] **CITES** this" in md

    def test_no_relationships_section_when_empty(self):
        model = FindingModel(
            id="F-test1234",
            description="Isolated finding",
            confidence=0.5,
        )
        md = render_synthesis(model)
        assert "## Relationships" not in md

    def test_backlinks_in_body(self):
        model = ResearchNoteModel(
            id="N-note0001",
            title="Note about findings",
            content="Based on [F-3a2b] and [H-5678]",
        )
        md = render_synthesis(model)
        assert "[[F-3a2b]]" in md
        assert "[[H-5678]]" in md


class TestWriteSynthesis:
    """Test synthesis file writing."""

    def test_creates_file(self, tmp_path):
        path = write_synthesis(tmp_path, "F-test1234", "# Finding\n\nContent\n")
        assert path.exists()
        assert path.name == "F-test1234.md"
        assert path.read_text() == "# Finding\n\nContent\n"

    def test_creates_directory(self, tmp_path):
        synth_dir = tmp_path / "synthesis"
        write_synthesis(synth_dir, "F-test1234", "# Test\n")
        assert synth_dir.is_dir()
        assert (synth_dir / "F-test1234.md").exists()

    def test_overwrites_existing(self, tmp_path):
        write_synthesis(tmp_path, "F-test1234", "version 1")
        write_synthesis(tmp_path, "F-test1234", "version 2")
        assert (tmp_path / "F-test1234.md").read_text() == "version 2"


class TestTripleWriteIntegration:
    """Test that execute_tool produces synthesis files."""

    async def test_add_finding_creates_synthesis(self, tmp_path):
        from wheeler.tools.graph_tools import execute_tool

        mock_config = MagicMock()
        mock_config.knowledge_path = str(tmp_path / "knowledge")
        mock_config.synthesis_path = str(tmp_path / "synthesis")
        mock_config.graph.backend = "neo4j"
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        # Fake backend
        class FakeBackend:
            async def create_node(self, label, props):
                return props.get("id", "")
            async def create_relationship(self, *a):
                return True
            async def run_cypher(self, *a, **kw):
                return []

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=FakeBackend()):
            result_str = await execute_tool(
                "add_finding",
                {"description": "Triple-write test", "confidence": 0.77},
                mock_config,
            )

        result = json.loads(result_str)
        node_id = result["node_id"]

        # JSON file should exist
        json_file = tmp_path / "knowledge" / f"{node_id}.json"
        assert json_file.exists()

        # Synthesis file should exist
        synth_file = tmp_path / "synthesis" / f"{node_id}.md"
        assert synth_file.exists()

        # Synthesis should have frontmatter and content
        content = synth_file.read_text()
        assert content.startswith("---\n")
        assert f"id: {node_id}" in content
        assert "Triple-write test" in content
        assert "confidence: 0.77" in content

    async def test_add_note_creates_synthesis(self, tmp_path):
        from wheeler.tools.graph_tools import execute_tool

        mock_config = MagicMock()
        mock_config.knowledge_path = str(tmp_path / "knowledge")
        mock_config.synthesis_path = str(tmp_path / "synthesis")
        mock_config.graph.backend = "neo4j"
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        class FakeBackend:
            async def create_node(self, label, props):
                return props.get("id", "")
            async def create_relationship(self, *a):
                return True
            async def run_cypher(self, *a, **kw):
                return []

        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=FakeBackend()):
            result_str = await execute_tool(
                "add_note",
                {"content": "Synthesis test note", "title": "Test"},
                mock_config,
            )

        node_id = json.loads(result_str)["node_id"]
        synth_file = tmp_path / "synthesis" / f"{node_id}.md"
        assert synth_file.exists()
        content = synth_file.read_text()
        assert "Synthesis test note" in content

    async def test_set_tier_updates_synthesis(self, tmp_path):
        from wheeler.tools.graph_tools import execute_tool

        mock_config = MagicMock()
        mock_config.knowledge_path = str(tmp_path / "knowledge")
        mock_config.synthesis_path = str(tmp_path / "synthesis")
        mock_config.graph.backend = "neo4j"
        mock_config.neo4j.project_tag = ""
        mock_config.neo4j.database = "neo4j"

        class FakeBackend:
            def __init__(self):
                self.nodes = {}
            async def create_node(self, label, props):
                self.nodes[props["id"]] = props
                return props["id"]
            async def update_node(self, label, node_id, properties):
                if node_id in self.nodes:
                    self.nodes[node_id].update(properties)
                    return True
                return False
            async def create_relationship(self, *a):
                return True
            async def run_cypher(self, *a, **kw):
                return []

        backend = FakeBackend()
        with patch("wheeler.tools.graph_tools._get_backend", new_callable=AsyncMock, return_value=backend):
            # Create finding
            result_str = await execute_tool(
                "add_finding",
                {"description": "Tier test", "confidence": 0.9},
                mock_config,
            )
            node_id = json.loads(result_str)["node_id"]

            # Verify initial tier in synthesis
            synth_file = tmp_path / "synthesis" / f"{node_id}.md"
            assert "tier: generated" in synth_file.read_text()

            # Update tier
            await execute_tool(
                "set_tier",
                {"node_id": node_id, "tier": "reference"},
                mock_config,
            )

            # Verify updated tier in synthesis
            assert "tier: reference" in synth_file.read_text()
