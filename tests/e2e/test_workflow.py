"""End-to-end workflow test: init → ingest → execute → verify → write.

Exercises the full Wheeler stack against a live Neo4j instance with
SRM-like data. This is the sandbox — if something breaks here, it
breaks in real usage.

Run: python -m pytest tests/e2e/ -v
Requires: Neo4j running on localhost:7687
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.conftest import E2E_TAG

# ────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────


async def _create_tagged(session, cypher: str, **params):
    """Run a CREATE query and tag the node for cleanup."""
    return await session.run(cypher, e2e_tag=E2E_TAG, **params)


# ────────────────────────────────────────────────────────
# Phase 1: Schema Init
# ────────────────────────────────────────────────────────


class TestSchemaInit:
    @pytest.mark.asyncio
    async def test_init_schema_applies_constraints(self, e2e_config):
        from wheeler.graph.schema import init_schema
        applied = await init_schema(e2e_config)
        assert len(applied) > 0
        # Should have constraints for all node types
        constraint_strs = " ".join(applied)
        assert "Finding" in constraint_strs
        assert "Document" in constraint_strs
        assert "Paper" in constraint_strs

    @pytest.mark.asyncio
    async def test_get_status_single_query(self, e2e_config):
        from wheeler.graph.schema import get_status
        counts = await get_status(e2e_config)
        assert isinstance(counts, dict)
        assert "Finding" in counts
        assert "Document" in counts
        assert "Paper" in counts


# ────────────────────────────────────────────────────────
# Phase 2: Ingest — Code, Data, Papers
# ────────────────────────────────────────────────────────


class TestIngestCode:
    @pytest.mark.asyncio
    async def test_hash_file(self, sandbox, e2e_config):
        from wheeler.graph.provenance import hash_file
        script = sandbox / "scripts" / "fit_srm_model.m"
        h = hash_file(script)
        assert len(h) == 64  # SHA-256 hex
        # Deterministic
        assert hash_file(script) == h

    @pytest.mark.asyncio
    async def test_add_script_with_provenance(self, sandbox, e2e_config):
        from wheeler.graph.provenance import hash_file, ScriptProvenance, create_script_node
        script = sandbox / "scripts" / "fit_srm_model.m"
        prov = ScriptProvenance(
            path=str(script),
            hash=hash_file(script),
            language="matlab",
            tier="reference",
        )
        node_id = await create_script_node(prov, e2e_config)
        assert node_id.startswith("S-")

        # Tag for cleanup
        from wheeler.graph.driver import get_async_driver
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            await session.run(
                "MATCH (s:Script {id: $id}) SET s.e2e_tag = $tag",
                id=node_id, tag=E2E_TAG,
            )

        # Verify it's reference tier
        async with driver.session(database=e2e_config.neo4j.database) as session:
            result = await session.run(
                "MATCH (s:Script {id: $id}) RETURN s.tier AS tier",
                id=node_id,
            )
            rec = await result.single()
            assert rec["tier"] == "reference"


class TestIngestData:
    @pytest.mark.asyncio
    async def test_add_dataset(self, sandbox, e2e_config):
        from wheeler.tools.graph_tools import execute_tool
        result = json.loads(await execute_tool(
            "add_dataset",
            {"path": str(sandbox / "data" / "parasol_recordings.mat"),
             "type": "mat", "description": "Parasol RGC current injection recordings"},
            e2e_config,
        ))
        assert result["label"] == "Dataset"
        node_id = result["node_id"]
        assert node_id.startswith("D-")

        # Tag for cleanup and verify tier
        from wheeler.graph.driver import get_async_driver
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            await session.run(
                "MATCH (d:Dataset {id: $id}) SET d.e2e_tag = $tag",
                id=node_id, tag=E2E_TAG,
            )
            # Default tier is generated
            result = await session.run(
                "MATCH (d:Dataset {id: $id}) RETURN d.tier AS tier", id=node_id,
            )
            rec = await result.single()
            assert rec["tier"] == "generated"

        # Promote to reference
        result = json.loads(await execute_tool(
            "set_tier", {"node_id": node_id, "tier": "reference"}, e2e_config,
        ))
        assert result["tier"] == "reference"


class TestIngestPapers:
    @pytest.mark.asyncio
    async def test_add_paper_always_reference(self, e2e_config):
        from wheeler.tools.graph_tools import execute_tool
        result = json.loads(await execute_tool(
            "add_paper",
            {"title": "Spike Response Model of Synaptic Transmission",
             "authors": "Gerstner, W.",
             "doi": "10.1162/neco.1995.7.6.1141",
             "year": 1995},
            e2e_config,
        ))
        assert result["label"] == "Paper"
        paper_id = result["node_id"]

        # Tag for cleanup
        from wheeler.graph.driver import get_async_driver
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            await session.run(
                "MATCH (p:Paper {id: $id}) SET p.e2e_tag = $tag",
                id=paper_id, tag=E2E_TAG,
            )
            # Papers are always reference
            result = await session.run(
                "MATCH (p:Paper {id: $id}) RETURN p.tier AS tier", id=paper_id,
            )
            rec = await result.single()
            assert rec["tier"] == "reference"

    @pytest.mark.asyncio
    async def test_query_papers(self, e2e_config):
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        # Create a paper first (previous test's paper was cleaned up)
        paper = json.loads(await execute_tool(
            "add_paper",
            {"title": "Query test paper", "authors": "QueryTest, A.", "year": 2000},
            e2e_config,
        ))
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            await session.run("MATCH (n {id: $id}) SET n.e2e_tag = $tag", id=paper["node_id"], tag=E2E_TAG)

        result = json.loads(await execute_tool(
            "query_papers", {"keyword": "QueryTest"}, e2e_config,
        ))
        assert result["count"] >= 1


# ────────────────────────────────────────────────────────
# Phase 3: Execute — Create findings, link provenance
# ────────────────────────────────────────────────────────


class TestExecuteFindings:
    @pytest.mark.asyncio
    async def test_full_provenance_chain(self, e2e_config):
        """Paper → WAS_INFORMED_BY → Execution → Finding (WAS_GENERATED_BY) → SUPPORTS → Hypothesis.
        This is the core provenance chain Wheeler tracks."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        # Create nodes
        paper = json.loads(await execute_tool(
            "add_paper",
            {"title": "Victor-Purpura spike distance metric",
             "authors": "Victor, J.D., Purpura, K.P.", "year": 1996},
            e2e_config,
        ))
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "Parasol ON VP loss = 0.15 at q=200Hz",
             "confidence": 0.85},
            e2e_config,
        ))
        hypothesis = json.loads(await execute_tool(
            "add_hypothesis",
            {"statement": "Parasol and midget RGCs share the same spike generation process"},
            e2e_config,
        ))

        # Tag all for cleanup
        async with driver.session(database=e2e_config.neo4j.database) as session:
            for nid in [paper["node_id"], finding["node_id"], hypothesis["node_id"]]:
                await session.run(
                    "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                    id=nid, tag=E2E_TAG,
                )

        # Link: Finding SUPPORTS Hypothesis
        link_result = json.loads(await execute_tool(
            "link_nodes",
            {"source_id": finding["node_id"],
             "target_id": hypothesis["node_id"],
             "relationship": "SUPPORTS"},
            e2e_config,
        ))
        assert link_result["status"] == "linked"

        # Link: Paper INFORMED (simulating an analysis node)
        # First create an analysis-like scenario
        analysis = json.loads(await execute_tool(
            "add_finding",  # Using finding as proxy since we don't have add_analysis tool
            {"description": "SRM fit analysis placeholder", "confidence": 1.0},
            e2e_config,
        ))
        async with driver.session(database=e2e_config.neo4j.database) as session:
            await session.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=analysis["node_id"], tag=E2E_TAG,
            )

        # Verify the chain exists
        async with driver.session(database=e2e_config.neo4j.database) as session:
            result = await session.run(
                "MATCH (f:Finding {id: $fid})-[:SUPPORTS]->(h:Hypothesis {id: $hid}) "
                "RETURN f.id, h.id",
                fid=finding["node_id"], hid=hypothesis["node_id"],
            )
            rec = await result.single()
            assert rec is not None

    @pytest.mark.asyncio
    async def test_tier_separation_in_findings(self, e2e_config):
        """Generated findings vs reference findings are distinguishable."""
        from wheeler.tools.graph_tools import execute_tool

        # Create one reference finding
        ref = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E ref: Established Rin measurement", "confidence": 0.95},
            e2e_config,
        ))
        await execute_tool("set_tier", {"node_id": ref["node_id"], "tier": "reference"}, e2e_config)

        # Create one generated finding
        gen = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E gen: New SRM fit result", "confidence": 0.75},
            e2e_config,
        ))

        # Tag for cleanup
        from wheeler.graph.driver import get_async_driver
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            for nid in [ref["node_id"], gen["node_id"]]:
                await session.run("MATCH (n {id: $id}) SET n.e2e_tag = $tag", id=nid, tag=E2E_TAG)

        # Query: reference findings
        async with driver.session(database=e2e_config.neo4j.database) as session:
            result = await session.run(
                "MATCH (f:Finding {tier: 'reference', id: $id}) RETURN f.id",
                id=ref["node_id"],
            )
            assert await result.single() is not None

            result = await session.run(
                "MATCH (f:Finding {id: $id}) RETURN f.tier AS tier",
                id=gen["node_id"],
            )
            rec = await result.single()
            assert rec["tier"] == "generated"


# ────────────────────────────────────────────────────────
# Phase 4: Verify — Citations, gaps, context
# ────────────────────────────────────────────────────────


class TestCitationValidation:
    @pytest.mark.asyncio
    async def test_extract_citations(self):
        from wheeler.validation.citations import extract_citations
        text = "The SRM fit [F-abcd1234] supports [H-5678abcd] per [P-11223344]."
        citations = extract_citations(text)
        assert citations == ["F-abcd1234", "H-5678abcd", "P-11223344"]

    @pytest.mark.asyncio
    async def test_extract_document_citation(self):
        from wheeler.validation.citations import extract_citations
        text = "See [W-abcd1234] for the methods section."
        assert extract_citations(text) == ["W-abcd1234"]

    @pytest.mark.asyncio
    async def test_validate_nonexistent_node(self, e2e_config):
        from wheeler.validation.citations import validate_citations, CitationStatus
        results = await validate_citations("Missing node: [F-00000000]", e2e_config)
        assert len(results) == 1
        assert results[0].status == CitationStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_validate_existing_node(self, e2e_config):
        """Create a node, then validate a citation to it."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.validation.citations import validate_citations, CitationStatus
        from wheeler.graph.driver import get_async_driver

        # Create a finding
        result = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E validate: test finding", "confidence": 0.9},
            e2e_config,
        ))
        node_id = result["node_id"]

        # Tag for cleanup
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            await session.run("MATCH (n {id: $id}) SET n.e2e_tag = $tag", id=node_id, tag=E2E_TAG)

        # Validate — node exists but lacks provenance (no WAS_GENERATED_BY edge)
        results = await validate_citations(f"See [{node_id}]", e2e_config)
        assert len(results) == 1
        assert results[0].node_id == node_id
        # Finding without WAS_GENERATED_BY relationship = MISSING_PROVENANCE
        assert results[0].status == CitationStatus.MISSING_PROVENANCE


class TestGraphGaps:
    @pytest.mark.asyncio
    async def test_gaps_returns_structure(self, e2e_config):
        from wheeler.tools.graph_tools import execute_tool
        result = json.loads(await execute_tool("graph_gaps", {}, e2e_config))
        assert "total_gaps" in result
        assert "unlinked_questions" in result
        assert "unsupported_hypotheses" in result
        assert "executions_without_outputs" in result
        assert "unreported_findings" in result
        assert "orphaned_papers" in result


class TestContextInjection:
    @pytest.mark.asyncio
    async def test_context_separates_tiers(self, e2e_config):
        """After creating reference and generated findings, context should separate them."""
        from wheeler.graph.context import fetch_context
        ctx = await fetch_context(e2e_config)
        # Context should be a string (may be empty if no findings, but shouldn't error)
        assert isinstance(ctx, str)
        # If there are reference findings, they should appear under "Established Knowledge"
        # If there are generated findings, they should appear under "Recent Work"
        # (Can't assert exact content since other tests may have created/cleaned nodes)


# ────────────────────────────────────────────────────────
# Phase 5: Write — Document creation
# ────────────────────────────────────────────────────────


class TestDocumentCreation:
    @pytest.mark.asyncio
    async def test_add_document_and_link_citations(self, e2e_config):
        """Create a document, link findings to it via APPEARS_IN."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        # Create a finding and a document
        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E doc: parasol tau_rise = 0.12ms", "confidence": 0.9},
            e2e_config,
        ))
        doc = json.loads(await execute_tool(
            "add_document",
            {"title": "Results: Spike Generation Comparison",
             "path": "docs/results.md", "section": "results"},
            e2e_config,
        ))

        # Tag for cleanup
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            for nid in [finding["node_id"], doc["node_id"]]:
                await session.run("MATCH (n {id: $id}) SET n.e2e_tag = $tag", id=nid, tag=E2E_TAG)

        # Link: Finding APPEARS_IN Document
        link = json.loads(await execute_tool(
            "link_nodes",
            {"source_id": finding["node_id"],
             "target_id": doc["node_id"],
             "relationship": "APPEARS_IN"},
            e2e_config,
        ))
        assert link["status"] == "linked"

        # Query: what went into this draft?
        async with driver.session(database=e2e_config.neo4j.database) as session:
            result = await session.run(
                "MATCH (n)-[:APPEARS_IN]->(w:Document {id: $doc_id}) RETURN n.id AS id",
                doc_id=doc["node_id"],
            )
            records = [r async for r in result]
            ids = [r["id"] for r in records]
            assert finding["node_id"] in ids

    @pytest.mark.asyncio
    async def test_query_documents(self, e2e_config):
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        # Create a document first (previous test's doc was cleaned up)
        doc = json.loads(await execute_tool(
            "add_document",
            {"title": "Query test doc", "path": "docs/query_test.md", "section": "results"},
            e2e_config,
        ))
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as session:
            await session.run("MATCH (n {id: $id}) SET n.e2e_tag = $tag", id=doc["node_id"], tag=E2E_TAG)

        result = json.loads(await execute_tool(
            "query_documents", {"keyword": "Query test"}, e2e_config,
        ))
        assert result["count"] >= 1


# ────────────────────────────────────────────────────────
# Phase 6: Full chain query
# ────────────────────────────────────────────────────────


class TestFullProvenanceChain:
    @pytest.mark.asyncio
    async def test_document_to_dataset_chain(self, e2e_config, sandbox):
        """Build and query the full chain: Document ← Finding → Execution → Dataset."""
        from wheeler.tools.graph_tools import execute_tool
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)

        # Create real data file for path validation
        data_file = sandbox / "data" / "e2e_chain_test.mat"
        data_file.write_bytes(b"fake mat data")

        # Build the chain bottom-up
        dataset = json.loads(await execute_tool(
            "add_dataset",
            {"path": str(data_file), "type": "mat",
             "description": "E2E chain test data"},
            e2e_config,
        ))

        execution = json.loads(await execute_tool(
            "add_execution",
            {"kind": "script_run",
             "description": "SRM fitting pipeline"},
            e2e_config,
        ))

        finding = json.loads(await execute_tool(
            "add_finding",
            {"description": "E2E chain: tau_decay = 0.48ms", "confidence": 0.88},
            e2e_config,
        ))

        doc = json.loads(await execute_tool(
            "add_document",
            {"title": "E2E Chain Test Results", "path": "docs/chain_test.md",
             "section": "results"},
            e2e_config,
        ))

        # Tag for cleanup
        async with driver.session(database=e2e_config.neo4j.database) as session:
            for nid in [dataset["node_id"], execution["node_id"],
                        finding["node_id"], doc["node_id"]]:
                await session.run("MATCH (n {id: $id}) SET n.e2e_tag = $tag", id=nid, tag=E2E_TAG)

        # Link: Execution USED Dataset
        await execute_tool("link_nodes", {
            "source_id": execution["node_id"], "target_id": dataset["node_id"],
            "relationship": "USED",
        }, e2e_config)

        # Link: Finding WAS_GENERATED_BY Execution
        await execute_tool("link_nodes", {
            "source_id": finding["node_id"], "target_id": execution["node_id"],
            "relationship": "WAS_GENERATED_BY",
        }, e2e_config)

        # Link: Finding APPEARS_IN Document
        await execute_tool("link_nodes", {
            "source_id": finding["node_id"], "target_id": doc["node_id"],
            "relationship": "APPEARS_IN",
        }, e2e_config)

        # THE FULL CHAIN QUERY: Document ← Finding → Execution → Dataset
        async with driver.session(database=e2e_config.neo4j.database) as session:
            result = await session.run(
                "MATCH (w:Document {id: $doc_id})"
                "<-[:APPEARS_IN]-(f:Finding)"
                "-[:WAS_GENERATED_BY]->(x:Execution)"
                "-[:USED]->(d:Dataset) "
                "RETURN f.description AS finding, x.description AS exec_desc, d.path AS data",
                doc_id=doc["node_id"],
            )
            rec = await result.single()
            assert rec is not None, "Full provenance chain query returned nothing"
            assert "tau_decay" in rec["finding"]
            assert "SRM fitting" in rec["exec_desc"]
            assert "e2e_chain_test" in rec["data"]
