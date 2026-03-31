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

    async def test_create_script(self, backend: KuzuBackend):
        node_id = await backend.create_node("Script", {
            "path": "/scripts/analyze.py",
            "hash": "abc123",
            "language": "python",
            "version": "3.11",
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("S-")

    async def test_create_execution(self, backend: KuzuBackend):
        node_id = await backend.create_node("Execution", {
            "kind": "script_run",
            "agent_id": "wheeler",
            "status": "completed",
            "started_at": "2024-01-01T00:00:00",
            "ended_at": "2024-01-01T00:01:00",
            "session_id": "",
            "description": "Test execution",
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("X-")

    async def test_create_plan(self, backend: KuzuBackend):
        node_id = await backend.create_node("Plan", {
            "status": "active",
            "date": "2024-01-01",
            "tier": "generated",
        })
        assert node_id.startswith("PL-")

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

    async def test_link_finding_to_execution(self, backend: KuzuBackend):
        x_id = await backend.create_node("Execution", {
            "kind": "script_run",
            "description": "Test run",
            "agent_id": "wheeler",
            "status": "completed",
            "started_at": "2024-01-01T00:00:00",
            "ended_at": "2024-01-01T00:01:00",
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
            "Finding", f_id, "WAS_GENERATED_BY", "Execution", x_id,
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


class TestRunCypherGraphGaps:
    """Test that graph_gaps queries work through Kuzu's Cypher dialect."""

    async def test_graph_gaps_queries(self, backend: KuzuBackend):
        """Run the same Cypher queries that graph_gaps uses."""
        # Create an orphan question (no relationships)
        await backend.create_node("OpenQuestion", {
            "id": "Q-gaptest1",
            "question": "Orphan question?",
            "priority": 5,
            "date_added": "2024-01-01",
            "tier": "generated",
        })
        # Create an orphan finding (no APPEARS_IN)
        await backend.create_node("Finding", {
            "id": "F-gaptest1",
            "description": "Unreported finding",
            "confidence": 0.8,
            "date": "2024-01-01",
            "tier": "generated",
        })
        # Create an orphan paper (no relationships)
        await backend.create_node("Paper", {
            "id": "P-gaptest1",
            "title": "Orphan paper",
            "authors": "Test",
            "doi": "",
            "year": 2024,
            "date_added": "2024-01-01",
            "tier": "reference",
        })

        # These are the actual queries from queries.py graph_gaps()
        q_records = await backend.run_cypher(
            "MATCH (q:OpenQuestion) "
            "WHERE NOT (q)<-[:AROSE_FROM]-() AND NOT ()-[:RELEVANT_TO]->(q) "
            "RETURN q.id AS id, coalesce(q.question, '') AS question, "
            "coalesce(q.priority, 0) AS priority "
            "ORDER BY q.priority DESC LIMIT 10"
        )
        assert len(q_records) >= 1

        f_records = await backend.run_cypher(
            "MATCH (f:Finding) "
            "WHERE NOT (f)-[:APPEARS_IN]->(:Document) "
            "RETURN f.id AS id, coalesce(f.description, '') AS description "
            "ORDER BY f.date DESC LIMIT 10"
        )
        assert len(f_records) >= 1
        # Verify the alias works (was 'desc' which is reserved in Kuzu)
        assert "description" in f_records[0]

        p_records = await backend.run_cypher(
            "MATCH (p:Paper) "
            "WHERE NOT (p)-[:WAS_INFORMED_BY|RELEVANT_TO|CITES|APPEARS_IN]->() "
            "AND NOT ()-[:WAS_DERIVED_FROM|CITES]->(p) "
            "RETURN p.id AS id, coalesce(p.title, '') AS title "
            "LIMIT 10"
        )
        assert len(p_records) >= 1

    async def test_query_findings_cypher(self, backend: KuzuBackend):
        """Test the query_findings Cypher with the fixed alias."""
        await backend.create_node("Finding", {
            "id": "F-qftest1",
            "description": "Queryable finding",
            "confidence": 0.85,
            "date": "2024-01-01",
            "tier": "generated",
        })
        records = await backend.run_cypher(
            "MATCH (f:Finding) WHERE toLower(f.description) CONTAINS toLower($kw) "
            "RETURN f.id AS id, f.description AS description, f.confidence AS conf, f.date AS date "
            "ORDER BY f.date DESC LIMIT 10",
            {"kw": "queryable"},
        )
        assert len(records) == 1
        assert records[0]["description"] == "Queryable finding"


class TestExecuteToolIntegration:
    """Test graph_tools.execute_tool() with the Kuzu backend end-to-end."""

    @pytest.fixture(autouse=True)
    async def _setup_config(self, tmp_path):
        """Create a config for execute_tool and reset the backend singleton."""
        from wheeler.config import WheelerConfig, GraphConfig
        from wheeler.tools import graph_tools

        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        self.config = WheelerConfig(
            graph=GraphConfig(backend="kuzu", kuzu_path=str(tmp_path / "tool_kuzu_db")),
            knowledge_path=str(knowledge_dir),
        )
        graph_tools._backend_instance = None
        yield
        graph_tools._backend_instance = None

    async def test_add_and_query_finding(self):
        import json
        from wheeler.tools import graph_tools

        result = json.loads(await graph_tools.execute_tool(
            "add_finding",
            {"description": "E2E Kuzu finding", "confidence": 0.7},
            self.config,
        ))
        assert result["status"] == "created"
        assert result["node_id"].startswith("F-")

        query = json.loads(await graph_tools.execute_tool(
            "query_findings", {"keyword": "E2E Kuzu"}, self.config,
        ))
        assert query["count"] >= 1

    async def test_graph_gaps_full_stack(self):
        import json
        from wheeler.tools import graph_tools

        # Create an orphan question
        json.loads(await graph_tools.execute_tool(
            "add_question",
            {"question": "Gaps test orphan", "priority": 8},
            self.config,
        ))
        gaps = json.loads(await graph_tools.execute_tool(
            "graph_gaps", {}, self.config,
        ))
        assert "unlinked_questions" in gaps
        assert gaps["total_gaps"] >= 1

    async def test_link_and_set_tier(self):
        import json
        from wheeler.tools import graph_tools

        f = json.loads(await graph_tools.execute_tool(
            "add_finding",
            {"description": "Linkable finding", "confidence": 0.9},
            self.config,
        ))
        h = json.loads(await graph_tools.execute_tool(
            "add_hypothesis", {"statement": "Linkable hyp"}, self.config,
        ))
        link = json.loads(await graph_tools.execute_tool(
            "link_nodes",
            {"source_id": f["node_id"], "target_id": h["node_id"],
             "relationship": "SUPPORTS"},
            self.config,
        ))
        assert link["status"] == "linked"

        tier = json.loads(await graph_tools.execute_tool(
            "set_tier", {"node_id": f["node_id"], "tier": "reference"},
            self.config,
        ))
        assert tier["tier"] == "reference"


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

        # Hypothesis should still exist
        node = await backend.get_node("Hypothesis", h_id)
        assert node is not None
