"""End-to-end tests for Wheeler's filesystem-backed knowledge graph.

Tests model round-trips, store operations, rendering, title extraction,
label mapping, dual-write helpers, and migration data conversion.
All filesystem tests use pytest's ``tmp_path`` fixture -- no Neo4j needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from wheeler.models import (
    DatasetModel,
    DocumentModel,
    ExecutionModel,
    FindingModel,
    HypothesisModel,
    KNOWLEDGE_NODE_ADAPTER,
    NodeBase,
    OpenQuestionModel,
    PaperModel,
    PlanModel,
    ScriptModel,
    model_for_label,
    title_for_node,
)
from wheeler.knowledge.store import (
    delete_node,
    list_nodes,
    node_exists,
    read_node,
    write_node,
)
from wheeler.knowledge.render import render_node
from wheeler.knowledge.migrate import _graph_data_to_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc).isoformat()


def _make_finding(**overrides) -> FindingModel:
    defaults = dict(
        id="F-aabb0011",
        description="Spike rate increases with temperature",
        confidence=0.85,
        tier="generated",
        created=NOW,
        updated=NOW,
        tags=["electrophysiology", "temperature"],
    )
    defaults.update(overrides)
    return FindingModel(**defaults)


def _make_hypothesis(**overrides) -> HypothesisModel:
    defaults = dict(
        id="H-cc221100",
        statement="Na+ channel kinetics explain the temperature sensitivity",
        status="open",
        tier="generated",
        created=NOW,
        updated=NOW,
        tags=["ion-channels"],
    )
    defaults.update(overrides)
    return HypothesisModel(**defaults)


def _make_question(**overrides) -> OpenQuestionModel:
    defaults = dict(
        id="Q-dd334455",
        question="Does the effect persist at sub-threshold voltages?",
        priority=7,
        tier="generated",
        created=NOW,
        updated=NOW,
    )
    defaults.update(overrides)
    return OpenQuestionModel(**defaults)


def _make_paper(**overrides) -> PaperModel:
    defaults = dict(
        id="P-ee556677",
        title="Temperature dependence of neuronal firing rates",
        authors="Smith, Jones",
        doi="10.1234/neuro.2024",
        year=2024,
        tier="reference",
        created=NOW,
        updated=NOW,
    )
    defaults.update(overrides)
    return PaperModel(**defaults)


def _make_dataset(**overrides) -> DatasetModel:
    defaults = dict(
        id="D-ff889900",
        path="/data/recordings/exp01.h5",
        data_type="h5",
        description="Whole-cell recordings at 25C and 37C",
        tier="generated",
        created=NOW,
        updated=NOW,
    )
    defaults.update(overrides)
    return DatasetModel(**defaults)


def _make_document(**overrides) -> DocumentModel:
    defaults = dict(
        id="W-11223344",
        title="Results: Temperature effects on spike generation",
        path="/docs/results_temperature.md",
        section="results",
        status="draft",
        tier="generated",
        created=NOW,
        updated=NOW,
    )
    defaults.update(overrides)
    return DocumentModel(**defaults)


def _make_script(**overrides) -> ScriptModel:
    defaults = dict(
        id="S-55667788",
        path="/scripts/analyze_temperature.py",
        hash="abc123def456",
        language="python",
        version="3.11",
        tier="generated",
        created=NOW,
        updated=NOW,
    )
    defaults.update(overrides)
    return ScriptModel(**defaults)


def _make_execution(**overrides) -> ExecutionModel:
    defaults = dict(
        id="X-55667788",
        kind="script",
        agent_id="wheeler",
        status="completed",
        started_at=NOW,
        ended_at=NOW,
        description="Temperature analysis run",
        tier="generated",
        created=NOW,
        updated=NOW,
    )
    defaults.update(overrides)
    return ExecutionModel(**defaults)


# ===================================================================
# 1. Model round-trip via KNOWLEDGE_NODE_ADAPTER
# ===================================================================


class TestModelRoundTrip:
    """Serialize each model to JSON, deserialize via the discriminated union."""

    @pytest.mark.parametrize(
        "model",
        [
            _make_finding(),
            _make_hypothesis(),
            _make_question(),
            _make_paper(),
            _make_dataset(),
            _make_document(),
            _make_script(),
            _make_execution(),
            PlanModel(id="PL-plan0001", status="active", tier="generated", created=NOW, updated=NOW),
        ],
        ids=lambda m: m.type,
    )
    def test_round_trip_preserves_all_fields(self, model: NodeBase):
        """JSON serialize -> deserialize returns identical model with correct type."""
        json_bytes = model.model_dump_json().encode()
        restored = KNOWLEDGE_NODE_ADAPTER.validate_json(json_bytes)

        assert type(restored) is type(model)
        assert restored.model_dump() == model.model_dump()

    def test_discriminated_union_returns_correct_type(self):
        """Adapter should resolve each type discriminator correctly."""
        finding = _make_finding()
        hyp = _make_hypothesis()

        f_bytes = finding.model_dump_json().encode()
        h_bytes = hyp.model_dump_json().encode()

        assert isinstance(KNOWLEDGE_NODE_ADAPTER.validate_json(f_bytes), FindingModel)
        assert isinstance(KNOWLEDGE_NODE_ADAPTER.validate_json(h_bytes), HypothesisModel)

    def test_extra_fields_survive_round_trip(self):
        """NodeBase allows extra fields -- they should persist through JSON."""
        finding = FindingModel(
            id="F-extra001",
            description="test",
            confidence=0.5,
            custom_field="extra_value",
        )
        json_bytes = finding.model_dump_json().encode()
        restored = KNOWLEDGE_NODE_ADAPTER.validate_json(json_bytes)
        assert restored.model_dump()["custom_field"] == "extra_value"


# ===================================================================
# 2. Store operations
# ===================================================================


class TestStoreOperations:
    """File I/O: write, read, list, delete, exists."""

    def test_write_read_round_trip(self, tmp_path: Path):
        finding = _make_finding()
        write_node(tmp_path, finding)
        restored = read_node(tmp_path, finding.id)

        assert type(restored) is FindingModel
        assert restored.id == finding.id
        assert restored.description == finding.description
        assert restored.confidence == finding.confidence
        assert restored.tags == finding.tags

    def test_write_creates_directory(self, tmp_path: Path):
        subdir = tmp_path / "nested" / "knowledge"
        finding = _make_finding()
        path = write_node(subdir, finding)

        assert subdir.is_dir()
        assert path.exists()

    def test_list_nodes_no_filter(self, tmp_path: Path):
        f = _make_finding()
        h = _make_hypothesis()
        q = _make_question()
        write_node(tmp_path, f)
        write_node(tmp_path, h)
        write_node(tmp_path, q)

        nodes = list_nodes(tmp_path)
        assert len(nodes) == 3
        ids = {n.id for n in nodes}
        assert ids == {f.id, h.id, q.id}

    def test_list_nodes_with_type_filter(self, tmp_path: Path):
        f = _make_finding()
        h = _make_hypothesis()
        write_node(tmp_path, f)
        write_node(tmp_path, h)

        findings = list_nodes(tmp_path, type_filter="Finding")
        assert len(findings) == 1
        assert findings[0].id == f.id

        hypotheses = list_nodes(tmp_path, type_filter="Hypothesis")
        assert len(hypotheses) == 1
        assert hypotheses[0].id == h.id

    def test_list_nodes_unknown_filter_returns_empty(self, tmp_path: Path):
        write_node(tmp_path, _make_finding())
        assert list_nodes(tmp_path, type_filter="Nonexistent") == []

    def test_list_nodes_nonexistent_directory_returns_empty(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist"
        assert list_nodes(missing) == []

    def test_delete_node_returns_true_then_false(self, tmp_path: Path):
        finding = _make_finding()
        write_node(tmp_path, finding)

        assert delete_node(tmp_path, finding.id) is True
        assert delete_node(tmp_path, finding.id) is False

    def test_delete_node_actually_removes_file(self, tmp_path: Path):
        finding = _make_finding()
        write_node(tmp_path, finding)
        delete_node(tmp_path, finding.id)

        assert not (tmp_path / finding.file_name).exists()

    def test_node_exists_before_and_after_write(self, tmp_path: Path):
        finding = _make_finding()
        assert node_exists(tmp_path, finding.id) is False

        write_node(tmp_path, finding)
        assert node_exists(tmp_path, finding.id) is True

    def test_read_node_missing_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="No knowledge file"):
            read_node(tmp_path, "F-nonexistent")

    def test_overwrite_existing_node(self, tmp_path: Path):
        finding = _make_finding(confidence=0.5)
        write_node(tmp_path, finding)

        updated = _make_finding(confidence=0.95)
        write_node(tmp_path, updated)

        restored = read_node(tmp_path, finding.id)
        assert restored.confidence == 0.95

    def test_file_name_property(self):
        finding = _make_finding()
        assert finding.file_name == f"{finding.id}.json"

    def test_written_file_is_valid_json(self, tmp_path: Path):
        finding = _make_finding()
        path = write_node(tmp_path, finding)

        data = json.loads(path.read_text())
        assert data["id"] == finding.id
        assert data["type"] == "Finding"


# ===================================================================
# 3. Render
# ===================================================================


class TestRender:
    """Markdown rendering for different node types."""

    def test_render_finding_has_key_fields(self):
        finding = _make_finding()
        md = render_node(finding)

        assert f"[{finding.id}]" in md
        assert "Finding" in md
        assert str(finding.confidence) in md
        assert finding.description in md

    def test_render_paper_shows_title_authors_year(self):
        paper = _make_paper()
        md = render_node(paper)

        assert f"[{paper.id}]" in md
        assert "Paper" in md
        assert paper.title in md
        assert paper.authors in md
        assert str(paper.year) in md

    def test_render_hypothesis_shows_statement(self):
        hyp = _make_hypothesis()
        md = render_node(hyp)

        assert f"[{hyp.id}]" in md
        assert hyp.statement in md
        assert hyp.status in md

    def test_render_open_question_shows_priority(self):
        q = _make_question()
        md = render_node(q)

        assert f"[{q.id}]" in md
        assert q.question in md
        assert str(q.priority) in md

    def test_render_dataset_shows_path_and_type(self):
        ds = _make_dataset()
        md = render_node(ds)

        assert f"[{ds.id}]" in md
        assert ds.path in md
        assert ds.data_type in md

    def test_render_document_shows_section_status(self):
        doc = _make_document()
        md = render_node(doc)

        assert f"[{doc.id}]" in md
        assert doc.title in md

    def test_render_script_shows_path(self):
        s = _make_script()
        md = render_node(s)

        assert f"[{s.id}]" in md
        assert s.path in md

    def test_render_execution_shows_description(self):
        x = _make_execution()
        md = render_node(x)

        assert f"[{x.id}]" in md
        assert x.description in md

    def test_render_finding_with_tags(self):
        finding = _make_finding(tags=["calcium", "imaging"])
        md = render_node(finding)

        assert "calcium" in md
        assert "imaging" in md

    def test_render_ends_with_newline(self):
        """All renderers should produce markdown ending with a newline."""
        models = [
            _make_finding(),
            _make_hypothesis(),
            _make_question(),
            _make_paper(),
            _make_dataset(),
            _make_document(),
            _make_script(),
            _make_execution(),
        ]
        for m in models:
            md = render_node(m)
            assert md.endswith("\n"), f"{m.type} render does not end with newline"


# ===================================================================
# 4. Title extraction
# ===================================================================


class TestTitleExtraction:

    def test_finding_title(self):
        f = _make_finding(description="Short finding")
        assert title_for_node(f) == "Short finding"

    def test_hypothesis_title(self):
        h = _make_hypothesis(statement="Ion channels matter")
        assert title_for_node(h) == "Ion channels matter"

    def test_question_title(self):
        q = _make_question(question="Why does it happen?")
        assert title_for_node(q) == "Why does it happen?"

    def test_paper_title(self):
        p = _make_paper(title="A great paper")
        assert title_for_node(p) == "A great paper"

    def test_document_title(self):
        d = _make_document(title="Results draft")
        assert title_for_node(d) == "Results draft"

    def test_dataset_title(self):
        ds = _make_dataset(description="Ephys recordings")
        assert title_for_node(ds) == "Ephys recordings"

    def test_script_title(self):
        s = _make_script()
        assert title_for_node(s) == "Script: /scripts/analyze_temperature.py"

    def test_execution_title(self):
        x = _make_execution()
        assert title_for_node(x) == "Temperature analysis run"

    def test_truncation_at_100_chars(self):
        long_desc = "x" * 200
        f = _make_finding(description=long_desc)
        title = title_for_node(f)
        assert len(title) == 100
        assert title == "x" * 100


# ===================================================================
# 5. Model-label mapping
# ===================================================================


class TestModelForLabel:

    @pytest.mark.parametrize(
        "label, expected_cls",
        [
            ("Finding", FindingModel),
            ("Hypothesis", HypothesisModel),
            ("OpenQuestion", OpenQuestionModel),
            ("Dataset", DatasetModel),
            ("Paper", PaperModel),
            ("Document", DocumentModel),
            ("Script", ScriptModel),
            ("Execution", ExecutionModel),
            ("Plan", PlanModel),
        ],
    )
    def test_returns_correct_class(self, label: str, expected_cls: type):
        assert model_for_label(label) is expected_cls

    def test_unknown_label_raises_key_error(self):
        with pytest.raises(KeyError):
            model_for_label("Unknown")

    def test_case_sensitive(self):
        with pytest.raises(KeyError):
            model_for_label("finding")


# ===================================================================
# 6. Dual-write helper (_write_knowledge_file)
# ===================================================================


class TestDualWrite:
    """Test _write_knowledge_file builds correct models from tool args."""

    def _make_config(self, tmp_path: Path):
        from wheeler.config import WheelerConfig

        return WheelerConfig(knowledge_path=str(tmp_path))

    def test_add_finding_creates_file(self, tmp_path: Path):
        from wheeler.tools.graph_tools import _write_knowledge_file

        config = self._make_config(tmp_path)
        args = {"description": "Calcium signals correlate with firing", "confidence": 0.9}
        result = json.dumps({"node_id": "F-dual0001", "label": "Finding", "status": "created"})

        _write_knowledge_file("add_finding", args, result, config)

        node = read_node(tmp_path, "F-dual0001")
        assert isinstance(node, FindingModel)
        assert node.description == "Calcium signals correlate with firing"
        assert node.confidence == 0.9
        assert node.tier == "generated"

    def test_add_hypothesis_creates_file(self, tmp_path: Path):
        from wheeler.tools.graph_tools import _write_knowledge_file

        config = self._make_config(tmp_path)
        args = {"statement": "Na+ channels drive the effect", "status": "open"}
        result = json.dumps({"node_id": "H-dual0002", "label": "Hypothesis", "status": "created"})

        _write_knowledge_file("add_hypothesis", args, result, config)

        node = read_node(tmp_path, "H-dual0002")
        assert isinstance(node, HypothesisModel)
        assert node.statement == "Na+ channels drive the effect"
        assert node.status == "open"

    def test_add_question_creates_file(self, tmp_path: Path):
        from wheeler.tools.graph_tools import _write_knowledge_file

        config = self._make_config(tmp_path)
        args = {"question": "What about K+ channels?", "priority": 8}
        result = json.dumps({"node_id": "Q-dual0003", "label": "OpenQuestion", "status": "created"})

        _write_knowledge_file("add_question", args, result, config)

        node = read_node(tmp_path, "Q-dual0003")
        assert isinstance(node, OpenQuestionModel)
        assert node.question == "What about K+ channels?"
        assert node.priority == 8

    def test_add_dataset_creates_file(self, tmp_path: Path):
        from wheeler.tools.graph_tools import _write_knowledge_file

        config = self._make_config(tmp_path)
        args = {
            "path": "/data/exp02.h5",
            "type": "h5",
            "description": "Voltage clamp recordings",
        }
        result = json.dumps({"node_id": "D-dual0004", "label": "Dataset", "status": "created"})

        _write_knowledge_file("add_dataset", args, result, config)

        node = read_node(tmp_path, "D-dual0004")
        assert isinstance(node, DatasetModel)
        assert node.path == "/data/exp02.h5"
        assert node.data_type == "h5"

    def test_add_paper_creates_file(self, tmp_path: Path):
        from wheeler.tools.graph_tools import _write_knowledge_file

        config = self._make_config(tmp_path)
        args = {
            "title": "Hodgkin-Huxley revisited",
            "authors": "Hodgkin, Huxley",
            "doi": "10.1234/hh.1952",
            "year": 1952,
        }
        result = json.dumps({"node_id": "P-dual0005", "label": "Paper", "status": "created"})

        _write_knowledge_file("add_paper", args, result, config)

        node = read_node(tmp_path, "P-dual0005")
        assert isinstance(node, PaperModel)
        assert node.title == "Hodgkin-Huxley revisited"
        assert node.tier == "reference"  # papers default to reference

    def test_add_document_creates_file(self, tmp_path: Path):
        from wheeler.tools.graph_tools import _write_knowledge_file

        config = self._make_config(tmp_path)
        args = {
            "title": "Methods: Patch clamp protocol",
            "path": "/docs/methods.md",
            "section": "methods",
            "status": "draft",
        }
        result = json.dumps({"node_id": "W-dual0006", "label": "Document", "status": "created"})

        _write_knowledge_file("add_document", args, result, config)

        node = read_node(tmp_path, "W-dual0006")
        assert isinstance(node, DocumentModel)
        assert node.title == "Methods: Patch clamp protocol"
        assert node.section == "methods"
        assert node.status == "draft"

    def test_no_node_id_in_result_does_nothing(self, tmp_path: Path):
        from wheeler.tools.graph_tools import _write_knowledge_file

        config = self._make_config(tmp_path)
        result = json.dumps({"message": "no node_id here"})

        _write_knowledge_file("add_finding", {"description": "x", "confidence": 0.5}, result, config)

        # Directory should be empty (no file created)
        assert list(tmp_path.glob("*.json")) == []

    def test_unknown_tool_name_does_nothing(self, tmp_path: Path):
        from wheeler.tools.graph_tools import _write_knowledge_file

        config = self._make_config(tmp_path)
        result = json.dumps({"node_id": "X-unknown", "label": "Unknown"})

        _write_knowledge_file("unknown_tool", {}, result, config)

        assert list(tmp_path.glob("*.json")) == []


# ===================================================================
# 7. Migration: _graph_data_to_model
# ===================================================================


class TestGraphDataToModel:
    """Test converting graph node dicts to Pydantic models."""

    def test_finding_conversion(self):
        data = {
            "id": "F-migr0001",
            "description": "Migrated finding",
            "confidence": 0.7,
            "tier": "reference",
            "created": NOW,
            "updated": NOW,
            "tags": [],
        }
        model = _graph_data_to_model("Finding", data)
        assert isinstance(model, FindingModel)
        assert model.id == "F-migr0001"
        assert model.description == "Migrated finding"
        assert model.confidence == 0.7

    def test_hypothesis_conversion(self):
        data = {
            "id": "H-migr0002",
            "statement": "Migrated hypothesis",
            "status": "supported",
            "created": NOW,
        }
        model = _graph_data_to_model("Hypothesis", data)
        assert isinstance(model, HypothesisModel)
        assert model.statement == "Migrated hypothesis"
        assert model.status == "supported"

    def test_date_field_mapping_from_date(self):
        """Graph nodes may use 'date' instead of 'created'."""
        data = {
            "id": "F-date0001",
            "description": "Has date field",
            "confidence": 0.5,
            "date": "2024-01-15T10:00:00Z",
        }
        model = _graph_data_to_model("Finding", data)
        assert model.created == "2024-01-15T10:00:00Z"

    def test_date_field_mapping_from_date_added(self):
        """Graph nodes may use 'date_added' instead of 'created'."""
        data = {
            "id": "Q-date0002",
            "question": "When was this added?",
            "date_added": "2024-06-01T12:00:00Z",
        }
        model = _graph_data_to_model("OpenQuestion", data)
        assert model.created == "2024-06-01T12:00:00Z"

    def test_dataset_type_mapping(self):
        """Dataset graph nodes use 'type' for data_type, which collides with discriminator."""
        data = {
            "id": "D-type0001",
            "path": "/data/file.csv",
            "type": "csv",
            "description": "A CSV file",
            "created": NOW,
        }
        model = _graph_data_to_model("Dataset", data)
        assert isinstance(model, DatasetModel)
        assert model.data_type == "csv"
        assert model.type == "Dataset"  # discriminator is restored

    def test_paper_conversion(self):
        data = {
            "id": "P-migr0003",
            "title": "A great paper",
            "authors": "Author A, Author B",
            "doi": "10.5555/test",
            "year": 2023,
            "created": NOW,
        }
        model = _graph_data_to_model("Paper", data)
        assert isinstance(model, PaperModel)
        assert model.title == "A great paper"
        assert model.year == 2023

    def test_document_conversion(self):
        data = {
            "id": "W-migr0004",
            "title": "Draft results",
            "path": "/docs/draft.md",
            "section": "results",
            "status": "draft",
            "created": NOW,
        }
        model = _graph_data_to_model("Document", data)
        assert isinstance(model, DocumentModel)
        assert model.title == "Draft results"

    def test_script_conversion(self):
        data = {
            "id": "S-migr0005",
            "path": "/foo.py",
            "hash": "abc",
            "language": "python",
            "created": NOW,
        }
        model = _graph_data_to_model("Script", data)
        assert isinstance(model, ScriptModel)
        assert model.path == "/foo.py"
        assert model.language == "python"

    def test_execution_conversion(self):
        data = {
            "id": "X-migr0006",
            "kind": "script",
            "agent_id": "wheeler",
            "status": "completed",
            "created": NOW,
        }
        model = _graph_data_to_model("Execution", data)
        assert isinstance(model, ExecutionModel)
        assert model.kind == "script"
        assert model.agent_id == "wheeler"
        assert model.status == "completed"

    def test_updated_defaults_to_created(self):
        """When 'updated' is missing, it should fall back to 'created'."""
        data = {
            "id": "F-upd00001",
            "description": "No updated field",
            "confidence": 0.5,
            "created": "2024-03-01T00:00:00Z",
        }
        model = _graph_data_to_model("Finding", data)
        assert model.updated == "2024-03-01T00:00:00Z"

    def test_existing_created_not_overwritten(self):
        """If 'created' is already set, 'date' should not overwrite it."""
        data = {
            "id": "F-pres0001",
            "description": "Already has created",
            "confidence": 0.5,
            "created": "2024-01-01T00:00:00Z",
            "date": "2023-06-15T00:00:00Z",
        }
        model = _graph_data_to_model("Finding", data)
        assert model.created == "2024-01-01T00:00:00Z"
