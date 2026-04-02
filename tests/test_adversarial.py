"""Adversarial tests for Wheeler MCP tool layer.

Verifies that mutation tools, query tools, and citation validation
handle malformed, malicious, and edge-case inputs gracefully -- returning
structured errors instead of crashing.
"""

from __future__ import annotations

import json

import pytest

from wheeler.tools.graph_tools.mutations import (
    add_finding,
    add_hypothesis,
    add_question,
    add_document,
    add_note,
    add_paper,
    add_script,
    link_nodes,
    set_tier,
)
from wheeler.validation.citations import extract_citations


# ---------------------------------------------------------------------------
# Shared FakeBackend for mutation tests
# ---------------------------------------------------------------------------


class FakeBackend:
    """In-memory backend that records every call for inspection.

    Nodes are stored in ``nodes[label]`` as a list of property dicts.
    Relationships are stored in ``rels`` as 5-tuples matching the
    ``GraphBackend.create_relationship`` signature.
    """

    def __init__(self, *, create_relationship_returns: bool = True):
        self.nodes: dict[str, list[dict]] = {}
        self.rels: list[tuple[str, str, str, str, str]] = []
        self._cr_returns = create_relationship_returns

    async def create_node(self, label: str, props: dict) -> str:
        self.nodes.setdefault(label, []).append(props)
        return props.get("id", "")

    async def create_relationship(
        self, src_label, src_id, rel_type, tgt_label, tgt_id
    ) -> bool:
        self.rels.append((src_label, src_id, rel_type, tgt_label, tgt_id))
        return self._cr_returns

    async def get_node(self, label: str, node_id: str) -> dict | None:
        for props in self.nodes.get(label, []):
            if props.get("id") == node_id:
                return props
        return None

    async def update_node(self, label: str, node_id: str, properties: dict) -> bool:
        for props in self.nodes.get(label, []):
            if props.get("id") == node_id:
                props.update(properties)
                return True
        return False

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        return []


# ===================================================================
# Adversarial mutation tests
# ===================================================================


class TestAdversarialMutations:
    """Test that mutation tools handle malicious or malformed inputs."""

    # ---- Empty / missing required fields ----

    async def test_add_finding_empty_description(self):
        """An empty description is accepted (not validated at tool layer)
        but should still produce a valid JSON response with node_id."""
        backend = FakeBackend()
        result = json.loads(await add_finding(backend, {"description": "", "confidence": 0.5}))
        assert result["status"] == "created"
        assert result["node_id"].startswith("F-")
        # The empty description is stored as-is
        stored = backend.nodes["Finding"][0]
        assert stored["description"] == ""

    async def test_add_finding_missing_description_raises(self):
        """Missing required 'description' key should raise KeyError."""
        backend = FakeBackend()
        with pytest.raises(KeyError):
            await add_finding(backend, {"confidence": 0.5})

    async def test_add_finding_missing_confidence_raises(self):
        """Missing required 'confidence' key should raise KeyError."""
        backend = FakeBackend()
        with pytest.raises(KeyError):
            await add_finding(backend, {"description": "test"})

    async def test_add_finding_negative_confidence(self):
        """Negative confidence is passed through (no validation at tool layer)."""
        backend = FakeBackend()
        result = json.loads(await add_finding(backend, {"description": "test", "confidence": -0.5}))
        assert result["status"] == "created"
        stored = backend.nodes["Finding"][0]
        assert stored["confidence"] == -0.5

    async def test_add_finding_confidence_over_one(self):
        """Confidence > 1.0 is passed through (no validation at tool layer)."""
        backend = FakeBackend()
        result = json.loads(await add_finding(backend, {"description": "test", "confidence": 2.5}))
        assert result["status"] == "created"
        stored = backend.nodes["Finding"][0]
        assert stored["confidence"] == 2.5

    async def test_add_finding_confidence_not_a_number(self):
        """Non-numeric confidence should raise ValueError from float()."""
        backend = FakeBackend()
        with pytest.raises((ValueError, TypeError)):
            await add_finding(backend, {"description": "test", "confidence": "not_a_number"})

    async def test_add_hypothesis_empty_statement(self):
        """Empty statement is accepted at tool layer."""
        backend = FakeBackend()
        result = json.loads(await add_hypothesis(backend, {"statement": ""}))
        assert result["status"] == "created"

    async def test_add_question_zero_priority(self):
        """Priority of 0 should be accepted."""
        backend = FakeBackend()
        result = json.loads(await add_question(backend, {"question": "Why?", "priority": 0}))
        assert result["status"] == "created"
        stored = backend.nodes["OpenQuestion"][0]
        assert stored["priority"] == 0

    async def test_add_question_negative_priority(self):
        """Negative priority is passed through (no validation at tool layer)."""
        backend = FakeBackend()
        result = json.loads(await add_question(backend, {"question": "Why?", "priority": -5}))
        assert result["status"] == "created"
        stored = backend.nodes["OpenQuestion"][0]
        assert stored["priority"] == -5

    async def test_add_document_missing_path_raises(self):
        """Missing required 'path' key should raise KeyError."""
        backend = FakeBackend()
        with pytest.raises(KeyError):
            await add_document(backend, {"title": "Draft"})

    async def test_add_note_missing_content_raises(self):
        """Missing required 'content' key should raise KeyError."""
        backend = FakeBackend()
        with pytest.raises(KeyError):
            await add_note(backend, {"title": "Untitled"})

    # ---- Injection-like strings (should be stored verbatim, not executed) ----

    async def test_finding_description_with_cypher_injection(self):
        """Cypher-like syntax in description should be stored as plain text."""
        backend = FakeBackend()
        evil = "MATCH (n) DETACH DELETE n"
        result = json.loads(await add_finding(backend, {"description": evil, "confidence": 0.5}))
        assert result["status"] == "created"
        assert backend.nodes["Finding"][0]["description"] == evil

    async def test_finding_description_with_html_injection(self):
        """HTML in description should be stored verbatim."""
        backend = FakeBackend()
        html = '<script>alert("xss")</script>'
        result = json.loads(await add_finding(backend, {"description": html, "confidence": 0.5}))
        assert result["status"] == "created"
        assert backend.nodes["Finding"][0]["description"] == html

    async def test_finding_description_with_unicode(self):
        """Unicode characters (math, CJK, emoji) in description should be preserved."""
        backend = FakeBackend()
        desc = "\u222b f(x)dx = F(x) + C \u2014 \u6d4b\u8bd5"
        result = json.loads(await add_finding(backend, {"description": desc, "confidence": 0.9}))
        assert result["status"] == "created"
        assert backend.nodes["Finding"][0]["description"] == desc

    async def test_finding_description_very_long(self):
        """Very long description (10K chars) should be stored without truncation."""
        backend = FakeBackend()
        desc = "x" * 10_000
        result = json.loads(await add_finding(backend, {"description": desc, "confidence": 0.5}))
        assert result["status"] == "created"
        assert len(backend.nodes["Finding"][0]["description"]) == 10_000

    # ---- link_nodes edge cases ----

    async def test_link_nodes_invalid_relationship_type(self):
        """Invalid relationship type returns a structured error."""
        backend = FakeBackend()
        result = json.loads(await link_nodes(backend, {
            "source_id": "F-aaaa1111",
            "target_id": "H-bbbb2222",
            "relationship": "HATES",
        }))
        assert "error" in result
        assert "Invalid relationship" in result["error"]
        assert "allowed" in result

    async def test_link_nodes_nonexistent_source_prefix(self):
        """Unknown source prefix (ZZ-...) returns structured error."""
        backend = FakeBackend()
        result = json.loads(await link_nodes(backend, {
            "source_id": "ZZ-aaaa1111",
            "target_id": "H-bbbb2222",
            "relationship": "SUPPORTS",
        }))
        assert "error" in result
        assert "Could not determine node labels" in result["error"]

    async def test_link_nodes_nonexistent_target_prefix(self):
        """Unknown target prefix returns structured error."""
        backend = FakeBackend()
        result = json.loads(await link_nodes(backend, {
            "source_id": "F-aaaa1111",
            "target_id": "ZZ-bbbb2222",
            "relationship": "SUPPORTS",
        }))
        assert "error" in result

    async def test_link_nodes_backend_returns_false(self):
        """When backend returns False (nodes not found), link_nodes returns error."""
        backend = FakeBackend(create_relationship_returns=False)
        result = json.loads(await link_nodes(backend, {
            "source_id": "F-aaaa1111",
            "target_id": "H-bbbb2222",
            "relationship": "SUPPORTS",
        }))
        assert "error" in result
        assert "not found" in result["error"]

    async def test_link_nodes_empty_ids(self):
        """Empty source/target IDs should produce an error (no dash to split)."""
        backend = FakeBackend()
        result = json.loads(await link_nodes(backend, {
            "source_id": "",
            "target_id": "",
            "relationship": "SUPPORTS",
        }))
        assert "error" in result

    async def test_link_nodes_malformed_ids(self):
        """IDs without dash should fail to resolve to a label."""
        backend = FakeBackend()
        result = json.loads(await link_nodes(backend, {
            "source_id": "noprefixhere",
            "target_id": "H-bbbb2222",
            "relationship": "SUPPORTS",
        }))
        assert "error" in result

    # ---- set_tier edge cases ----

    async def test_set_tier_invalid_tier_value(self):
        """Tier must be 'reference' or 'generated'; anything else is rejected."""
        backend = FakeBackend()
        result = json.loads(await set_tier(backend, {"node_id": "F-aaaa1111", "tier": "premium"}))
        assert "error" in result
        assert "Invalid tier" in result["error"]

    async def test_set_tier_nonexistent_node_prefix(self):
        """Unknown prefix in node_id returns error."""
        backend = FakeBackend()
        result = json.loads(await set_tier(backend, {"node_id": "ZZ-aaaa1111", "tier": "reference"}))
        assert "error" in result
        assert "Unknown node prefix" in result["error"]

    async def test_set_tier_node_not_found(self):
        """Valid prefix but node doesn't exist returns error."""
        backend = FakeBackend()
        # Backend has no nodes, so update_node returns False
        result = json.loads(await set_tier(backend, {"node_id": "F-aaaa1111", "tier": "reference"}))
        assert "error" in result
        assert "not found" in result["error"]

    async def test_set_tier_empty_string(self):
        """Empty tier string is invalid."""
        backend = FakeBackend()
        result = json.loads(await set_tier(backend, {"node_id": "F-aaaa1111", "tier": ""}))
        assert "error" in result

    # ---- Provenance-completing edge cases ----

    async def test_provenance_with_invalid_used_entity_prefix(self):
        """Unknown prefix in used_entities is silently skipped (not linked)."""
        backend = FakeBackend()
        result = json.loads(await add_finding(backend, {
            "description": "test",
            "confidence": 0.7,
            "execution_kind": "script",
            "used_entities": "ZZ-unknown123",
        }))
        assert result["status"] == "created"
        prov = result["provenance"]
        # The unknown-prefix entity should NOT appear in linked_inputs
        assert prov["linked_inputs"] == []
        # Execution was still created
        assert prov["execution_id"].startswith("X-")

    async def test_provenance_with_mixed_valid_invalid_entities(self):
        """Mix of valid and invalid prefixes: only valid ones get linked."""
        backend = FakeBackend()
        result = json.loads(await add_finding(backend, {
            "description": "test",
            "confidence": 0.7,
            "execution_kind": "script",
            "used_entities": "D-abc12345,ZZ-unknown,S-def67890",
        }))
        prov = result["provenance"]
        assert "D-abc12345" in prov["linked_inputs"]
        assert "S-def67890" in prov["linked_inputs"]
        assert "ZZ-unknown" not in prov["linked_inputs"]
        assert len(prov["linked_inputs"]) == 2

    async def test_provenance_with_execution_kind_but_no_description(self):
        """Execution created even without execution_description."""
        backend = FakeBackend()
        result = json.loads(await add_finding(backend, {
            "description": "test",
            "confidence": 0.5,
            "execution_kind": "discuss",
        }))
        assert "provenance" in result
        # Execution node has empty description
        exec_nodes = backend.nodes.get("Execution", [])
        assert len(exec_nodes) == 1
        assert exec_nodes[0]["description"] == ""

    async def test_provenance_with_whitespace_only_used_entities(self):
        """used_entities of ' , , ' should produce no USED links."""
        backend = FakeBackend()
        result = json.loads(await add_finding(backend, {
            "description": "test",
            "confidence": 0.5,
            "execution_kind": "script",
            "used_entities": " , , ",
        }))
        prov = result["provenance"]
        assert prov["linked_inputs"] == []

    async def test_provenance_not_triggered_without_execution_kind(self):
        """No provenance when execution_kind is absent."""
        backend = FakeBackend()
        result = json.loads(await add_finding(backend, {
            "description": "test",
            "confidence": 0.5,
        }))
        assert "provenance" not in result
        assert "Execution" not in backend.nodes


# ===================================================================
# Adversarial query tests
# ===================================================================


class TestAdversarialQueries:
    """Test that query tools handle edge-case arguments.

    Query tools issue Cypher against the backend. With FakeBackend
    returning [] for run_cypher, we verify the tool doesn't crash and
    returns well-formed JSON.
    """

    async def test_query_with_very_long_keyword(self):
        from wheeler.tools.graph_tools.queries import query_findings

        backend = FakeBackend()
        result = json.loads(await query_findings(backend, {"keyword": "x" * 10_000, "limit": 5}))
        assert "findings" in result
        assert result["count"] == 0

    async def test_query_with_special_characters(self):
        from wheeler.tools.graph_tools.queries import query_findings

        backend = FakeBackend()
        result = json.loads(await query_findings(backend, {"keyword": "'; DROP TABLE--", "limit": 5}))
        assert "findings" in result
        assert result["count"] == 0

    async def test_query_with_unicode_keyword(self):
        from wheeler.tools.graph_tools.queries import query_findings

        backend = FakeBackend()
        result = json.loads(await query_findings(backend, {"keyword": "\u222b\u2202\u03c8/\u2202t", "limit": 5}))
        assert "findings" in result

    async def test_query_with_zero_limit(self):
        from wheeler.tools.graph_tools.queries import query_findings

        backend = FakeBackend()
        result = json.loads(await query_findings(backend, {"limit": 0}))
        assert "findings" in result

    async def test_query_with_negative_limit(self):
        from wheeler.tools.graph_tools.queries import query_findings

        backend = FakeBackend()
        result = json.loads(await query_findings(backend, {"limit": -1}))
        assert "findings" in result

    async def test_query_with_very_large_limit(self):
        from wheeler.tools.graph_tools.queries import query_findings

        backend = FakeBackend()
        result = json.loads(await query_findings(backend, {"limit": 999_999}))
        assert "findings" in result

    async def test_query_hypotheses_invalid_status(self):
        from wheeler.tools.graph_tools.queries import query_hypotheses

        backend = FakeBackend()
        result = json.loads(await query_hypotheses(backend, {"status": "nonexistent_status"}))
        assert "hypotheses" in result
        assert result["count"] == 0

    async def test_query_documents_both_filters(self):
        from wheeler.tools.graph_tools.queries import query_documents

        backend = FakeBackend()
        result = json.loads(await query_documents(backend, {
            "keyword": "test",
            "status": "draft",
            "limit": 5,
        }))
        assert "documents" in result

    async def test_graph_gaps_with_empty_graph(self):
        from wheeler.tools.graph_tools.queries import graph_gaps

        backend = FakeBackend()
        result = json.loads(await graph_gaps(backend, {}))
        assert "total_gaps" in result
        assert result["total_gaps"] == 0


# ===================================================================
# Adversarial citation validation tests
# ===================================================================


class TestAdversarialValidation:
    """Test citation extraction edge cases (sync, no backend needed)."""

    def test_extract_citations_from_empty_text(self):
        assert extract_citations("") == []

    def test_extract_citations_from_text_with_no_citations(self):
        assert extract_citations("Just a normal sentence with no brackets.") == []

    def test_extract_citations_with_malformed_ids(self):
        """Brackets present but content doesn't match pattern."""
        assert extract_citations("[not-a-citation]") == []
        assert extract_citations("[F-]") == []
        assert extract_citations("[F-ab]") == []  # too short (min 4 hex)
        assert extract_citations("[-abcd]") == []  # missing prefix
        assert extract_citations("[123-abcd]") == []  # numeric prefix

    def test_extract_citations_with_duplicate_ids(self):
        """Duplicates should be deduplicated."""
        text = "[F-abcd1234] and again [F-abcd1234] and [F-abcd1234]"
        result = extract_citations(text)
        assert result == ["F-abcd1234"]

    def test_extract_citations_preserves_order(self):
        """Citations should appear in the order they're first seen."""
        text = "[H-1111] then [F-2222] then [H-1111]"
        assert extract_citations(text) == ["H-1111", "F-2222"]

    def test_extract_citations_from_only_whitespace(self):
        assert extract_citations("   \n\t  ") == []

    def test_extract_citations_with_newlines_between_brackets(self):
        """Newline inside brackets should not match."""
        assert extract_citations("[F-\nabcd]") == []

    def test_extract_citations_adjacent_brackets(self):
        """Two citations right next to each other."""
        text = "[F-aaaa][H-bbbb]"
        assert extract_citations(text) == ["F-aaaa", "H-bbbb"]

    def test_extract_citations_nested_brackets(self):
        """Nested brackets should not cause issues."""
        text = "[[F-abcd]]"
        result = extract_citations(text)
        assert result == ["F-abcd"]

    def test_extract_citations_every_valid_prefix(self):
        """Every known prefix should be extractable."""
        prefixes = ["PL", "F", "H", "Q", "S", "X", "D", "P", "W", "N", "L"]
        for prefix in prefixes:
            text = f"[{prefix}-abcd1234]"
            result = extract_citations(text)
            assert result == [f"{prefix}-abcd1234"], f"Failed for prefix {prefix}"

    def test_extract_citations_unknown_prefix_ignored(self):
        """Prefixes not in the known set should be ignored."""
        for prefix in ["A", "B", "C", "ZZ", "XX", "123"]:
            text = f"[{prefix}-abcd1234]"
            assert extract_citations(text) == [], f"Should ignore prefix {prefix}"

    def test_extract_citations_hex_boundary_4_chars(self):
        """Exactly 4 hex characters should match."""
        assert extract_citations("[F-abcd]") == ["F-abcd"]

    def test_extract_citations_hex_boundary_3_chars_rejected(self):
        """3 hex characters should not match (below minimum)."""
        assert extract_citations("[F-abc]") == []

    def test_extract_citations_hex_boundary_8_chars(self):
        """Exactly 8 hex characters should match."""
        assert extract_citations("[F-abcd1234]") == ["F-abcd1234"]

    def test_extract_citations_hex_boundary_9_chars_rejected(self):
        """9 hex characters should not match (above maximum)."""
        assert extract_citations("[F-abcd12345]") == []
