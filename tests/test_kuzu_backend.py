"""Tests for the Kuzu graph database backend.

Uses a temp directory for each test — no external services needed.
"""

from __future__ import annotations

import pytest

kuzu = pytest.importorskip("kuzu")

from wheeler.graph.kuzu_backend import KuzuBackend, NODE_TABLE_SCHEMAS
from wheeler.graph.schema import NODE_LABELS, ALLOWED_RELATIONSHIPS, LABEL_TO_PREFIX


@pytest.fixture
async def backend(tmp_path):
    """Create and initialize a KuzuBackend in a temporary directory."""
    b = KuzuBackend(str(tmp_path / "test_kuzu_db"))
    await b.initialize()
    yield b
    await b.close()


class TestInitialize:
    async def test_creates_database(self, backend: KuzuBackend):
        """initialize() should succeed without error."""
        # The fixture already called initialize; if we get here, it worked.
        assert backend is not None

    async def test_idempotent(self, backend: KuzuBackend):
        """Calling initialize() twice should not raise."""
        await backend.initialize()

    async def test_all_node_labels_have_schemas(self):
        """Every NODE_LABEL should have a corresponding table schema."""
        assert set(NODE_TABLE_SCHEMAS.keys()) == set(NODE_LABELS)


class TestCreateNode:
    async def test_create_finding(self, backend: KuzuBackend):
        node_id = await backend.create_node("Finding", {
            "description": "Test finding",
            "confidence": 0.9,
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("F-")
        assert len(node_id) == 10

    async def test_create_hypothesis(self, backend: KuzuBackend):
        node_id = await backend.create_node("Hypothesis", {
            "statement": "Test hypothesis",
            "status": "open",
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("H-")

    async def test_create_open_question(self, backend: KuzuBackend):
        node_id = await backend.create_node("OpenQuestion", {
            "question": "Why does X happen?",
            "priority": 7,
            "date_added": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("Q-")

    async def test_create_dataset(self, backend: KuzuBackend):
        node_id = await backend.create_node("Dataset", {
            "path": "/data/test.h5",
            "type": "h5",
            "description": "Test dataset",
            "date_added": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("D-")

    async def test_create_paper(self, backend: KuzuBackend):
        node_id = await backend.create_node("Paper", {
            "title": "Test Paper Title",
            "authors": "Smith, Jones",
            "doi": "10.1234/test",
            "year": 2024,
            "date_added": "2024-01-01",
            "tier": "reference",
        })
        assert node_id.startswith("P-")

    async def test_create_document(self, backend: KuzuBackend):
        node_id = await backend.create_node("Document", {
            "title": "Results Draft",
            "path": "/docs/results.md",
            "section": "results",
            "status": "draft",
            "date": "2024-01-01",
            "updated": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("W-")

    async def test_create_analysis(self, backend: KuzuBackend):
        node_id = await backend.create_node("Analysis", {
            "script_path": "/scripts/analyze.py",
            "script_hash": "abc123",
            "language": "python",
            "language_version": "3.11",
            "parameters": "{}",
            "output_path": "/results/out.csv",
            "output_hash": "def456",
            "executed_at": "2024-01-01T00:00:00",
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("A-")

    async def test_create_plan(self, backend: KuzuBackend):
        node_id = await backend.create_node("Plan", {
            "status": "active",
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("PL-")

    async def test_create_experiment(self, backend: KuzuBackend):
        node_id = await backend.create_node("Experiment", {
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("E-")

    async def test_create_celltype(self, backend: KuzuBackend):
        node_id = await backend.create_node("CellType", {
            "tier": "reference",
        })
        assert node_id.startswith("C-")

    async def test_create_task(self, backend: KuzuBackend):
        node_id = await backend.create_node("Task", {
            "tier": "generated",
        })
        assert node_id.startswith("T-")

    async def test_create_with_explicit_id(self, backend: KuzuBackend):
        node_id = await backend.create_node("Finding", {
            "id": "F-testid01",
            "description": "Custom ID finding",
            "confidence": 0.8,
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id == "F-testid01"

    async def test_create_all_labels(self, backend: KuzuBackend):
        """Every label in NODE_LABELS should be createable."""
        for label in NODE_LABELS:
            prefix = LABEL_TO_PREFIX[label]
            # Minimal properties: just 'tier' (all labels have it)
            props: dict = {"tier": "generated"}
            node_id = await backend.create_node(label, props)
            assert node_id.startswith(f"{prefix}-"), f"Failed for label {label}"


class TestGetNode:
    async def test_get_existing_node(self, backend: KuzuBackend):
        node_id = await backend.create_node("Finding", {
            "description": "Retrievable finding",
            "confidence": 0.75,
            "date": "2024-01-01",
            "tier": "generated",
        })
        result = await backend.get_node("Finding", node_id)
        assert result is not None
        assert result["id"] == node_id
        assert result["description"] == "Retrievable finding"
        assert result["confidence"] == 0.75

    async def test_get_nonexistent_node(self, backend: KuzuBackend):
        result = await backend.get_node("Finding", "F-nonexist")
        assert result is None


class TestUpdateNode:
    async def test_update_properties(self, backend: KuzuBackend):
        node_id = await backend.create_node("Finding", {
            "description": "Original",
            "confidence": 0.5,
            "date": "2024-01-01",
            "tier": "generated",
        })
        updated = await backend.update_node("Finding", node_id, {
            "description": "Updated",
            "confidence": 0.9,
        })
        assert updated is True

        result = await backend.get_node("Finding", node_id)
        assert result is not None
        assert result["description"] == "Updated"
        assert result["confidence"] == 0.9

    async def test_update_preserves_other_properties(self, backend: KuzuBackend):
        node_id = await backend.create_node("Finding", {
            "description": "Keep this",
            "confidence": 0.5,
            "date": "2024-01-01",
            "tier": "generated",
        })
        await backend.update_node("Finding", node_id, {"confidence": 0.99})

        result = await backend.get_node("Finding", node_id)
        assert result is not None
        assert result["description"] == "Keep this"
        assert result["confidence"] == 0.99

    async def test_update_nonexistent_returns_false(self, backend: KuzuBackend):
        updated = await backend.update_node("Finding", "F-nonexist", {
            "description": "Nope",
        })
        assert updated is False


class TestDeleteNode:
    async def test_delete_existing(self, backend: KuzuBackend):
        node_id = await backend.create_node("Finding", {
            "description": "To be deleted",
            "confidence": 0.5,
            "date": "2024-01-01",
            "tier": "generated",
        })
        deleted = await backend.delete_node("Finding", node_id)
        assert deleted is True

        result = await backend.get_node("Finding", node_id)
        assert result is None

    async def test_delete_nonexistent_returns_false(self, backend: KuzuBackend):
        deleted = await backend.delete_node("Finding", "F-nonexist")
        assert deleted is False


class TestCreateRelationship:
    async def test_link_two_nodes(self, backend: KuzuBackend):
        f_id = await backend.create_node("Finding", {
            "description": "A finding",
            "confidence": 0.8,
            "date": "2024-01-01",
            "tier": "generated",
        })
        h_id = await backend.create_node("Hypothesis", {
            "statement": "A hypothesis",
            "status": "open",
            "date": "2024-01-01",
            "tier": "generated",
        })
        linked = await backend.create_relationship(
            "Finding", f_id, "SUPPORTS", "Hypothesis", h_id,
        )
        assert linked is True

    async def test_link_analysis_to_finding(self, backend: KuzuBackend):
        a_id = await backend.create_node("Analysis", {
            "script_path": "/test.py",
            "script_hash": "abc",
            "language": "python",
            "date": "2024-01-01",
            "tier": "generated",
        })
        f_id = await backend.create_node("Finding", {
            "description": "Generated finding",
            "confidence": 0.9,
            "date": "2024-01-01",
            "tier": "generated",
        })
        linked = await backend.create_relationship(
            "Analysis", a_id, "GENERATED", "Finding", f_id,
        )
        assert linked is True


class TestQueryNodes:
    async def test_query_all(self, backend: KuzuBackend):
        for i in range(3):
            await backend.create_node("Finding", {
                "description": f"Finding {i}",
                "confidence": 0.5 + i * 0.1,
                "date": f"2024-01-0{i+1}",
                "tier": "generated",
            })
        results = await backend.query_nodes("Finding")
        assert len(results) == 3

    async def test_query_with_filter(self, backend: KuzuBackend):
        await backend.create_node("Hypothesis", {
            "statement": "Open hyp",
            "status": "open",
            "date": "2024-01-01",
            "tier": "generated",
        })
        await backend.create_node("Hypothesis", {
            "statement": "Supported hyp",
            "status": "supported",
            "date": "2024-01-01",
            "tier": "generated",
        })
        results = await backend.query_nodes("Hypothesis", filters={"status": "open"})
        assert len(results) == 1
        assert results[0]["statement"] == "Open hyp"

    async def test_query_with_limit(self, backend: KuzuBackend):
        for i in range(5):
            await backend.create_node("Finding", {
                "description": f"Finding {i}",
                "confidence": 0.5,
                "date": "2024-01-01",
                "tier": "generated",
            })
        results = await backend.query_nodes("Finding", limit=3)
        assert len(results) == 3

    async def test_query_with_order_by(self, backend: KuzuBackend):
        await backend.create_node("OpenQuestion", {
            "question": "Low priority",
            "priority": 1,
            "date_added": "2024-01-01",
            "tier": "generated",
        })
        await backend.create_node("OpenQuestion", {
            "question": "High priority",
            "priority": 10,
            "date_added": "2024-01-01",
            "tier": "generated",
        })
        results = await backend.query_nodes(
            "OpenQuestion", order_by="priority", limit=10,
        )
        assert len(results) == 2
        # DESC order: highest priority first
        assert results[0]["priority"] == 10

    async def test_query_empty(self, backend: KuzuBackend):
        results = await backend.query_nodes("Finding")
        assert results == []


class TestCountNodes:
    async def test_count_zero(self, backend: KuzuBackend):
        count = await backend.count_nodes("Finding")
        assert count == 0

    async def test_count_nonzero(self, backend: KuzuBackend):
        for i in range(4):
            await backend.create_node("Finding", {
                "description": f"Finding {i}",
                "confidence": 0.5,
                "date": "2024-01-01",
                "tier": "generated",
            })
        count = await backend.count_nodes("Finding")
        assert count == 4


class TestCountAll:
    async def test_count_all_empty(self, backend: KuzuBackend):
        counts = await backend.count_all()
        assert isinstance(counts, dict)
        for label in NODE_LABELS:
            assert counts[label] == 0

    async def test_count_all_with_data(self, backend: KuzuBackend):
        await backend.create_node("Finding", {
            "description": "F1",
            "confidence": 0.5,
            "date": "2024-01-01",
            "tier": "generated",
        })
        await backend.create_node("Hypothesis", {
            "statement": "H1",
            "status": "open",
            "date": "2024-01-01",
            "tier": "generated",
        })
        counts = await backend.count_all()
        assert counts["Finding"] == 1
        assert counts["Hypothesis"] == 1
        assert counts["OpenQuestion"] == 0


class TestFindUnlinked:
    async def test_unlinked_nodes(self, backend: KuzuBackend):
        q_id = await backend.create_node("OpenQuestion", {
            "question": "Unlinked question",
            "priority": 5,
            "date_added": "2024-01-01",
            "tier": "generated",
        })
        results = await backend.find_unlinked(
            "OpenQuestion", ["AROSE_FROM", "RELEVANT_TO"],
        )
        assert len(results) == 1
        assert results[0]["id"] == q_id

    async def test_linked_nodes_excluded(self, backend: KuzuBackend):
        q_id = await backend.create_node("OpenQuestion", {
            "question": "Linked question",
            "priority": 5,
            "date_added": "2024-01-01",
            "tier": "generated",
        })
        f_id = await backend.create_node("Finding", {
            "description": "Related finding",
            "confidence": 0.8,
            "date": "2024-01-01",
            "tier": "generated",
        })
        await backend.create_relationship(
            "Finding", f_id, "RELEVANT_TO", "OpenQuestion", q_id,
        )
        results = await backend.find_unlinked(
            "OpenQuestion", ["RELEVANT_TO"], direction="incoming",
        )
        assert len(results) == 0


class TestFindConnected:
    async def test_find_outgoing(self, backend: KuzuBackend):
        a_id = await backend.create_node("Analysis", {
            "script_path": "/test.py",
            "script_hash": "abc",
            "language": "python",
            "date": "2024-01-01",
            "tier": "generated",
        })
        f_id = await backend.create_node("Finding", {
            "description": "Generated by analysis",
            "confidence": 0.9,
            "date": "2024-01-01",
            "tier": "generated",
        })
        await backend.create_relationship(
            "Analysis", a_id, "GENERATED", "Finding", f_id,
        )
        connected = await backend.find_connected(a_id, "GENERATED", direction="outgoing")
        assert len(connected) == 1
        assert connected[0]["id"] == f_id

    async def test_find_incoming(self, backend: KuzuBackend):
        f_id = await backend.create_node("Finding", {
            "description": "Supporting finding",
            "confidence": 0.9,
            "date": "2024-01-01",
            "tier": "generated",
        })
        h_id = await backend.create_node("Hypothesis", {
            "statement": "Supported hypothesis",
            "status": "open",
            "date": "2024-01-01",
            "tier": "generated",
        })
        await backend.create_relationship(
            "Finding", f_id, "SUPPORTS", "Hypothesis", h_id,
        )
        connected = await backend.find_connected(h_id, "SUPPORTS", direction="incoming")
        assert len(connected) == 1
        assert connected[0]["id"] == f_id

    async def test_find_connected_empty(self, backend: KuzuBackend):
        f_id = await backend.create_node("Finding", {
            "description": "Lonely finding",
            "confidence": 0.5,
            "date": "2024-01-01",
            "tier": "generated",
        })
        connected = await backend.find_connected(f_id, "SUPPORTS", direction="outgoing")
        assert connected == []


class TestDeleteWithRelationships:
    async def test_delete_node_with_relationships(self, backend: KuzuBackend):
        """DETACH DELETE should remove node and its relationships."""
        f_id = await backend.create_node("Finding", {
            "description": "Connected finding",
            "confidence": 0.8,
            "date": "2024-01-01",
            "tier": "generated",
        })
        h_id = await backend.create_node("Hypothesis", {
            "statement": "Connected hypothesis",
            "status": "open",
            "date": "2024-01-01",
            "tier": "generated",
        })
        await backend.create_relationship(
            "Finding", f_id, "SUPPORTS", "Hypothesis", h_id,
        )
        deleted = await backend.delete_node("Finding", f_id)
        assert deleted is True

        # Hypothesis should still exist but have no incoming SUPPORTS
        connected = await backend.find_connected(h_id, "SUPPORTS", direction="incoming")
        assert connected == []
