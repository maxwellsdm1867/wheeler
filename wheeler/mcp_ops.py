"""Wheeler Ops MCP Server: provenance, dependency scanning, workspace, citations.

6 tools for operational tasks: staleness detection, dependency scanning,
file hashing, workspace scanning, and citation extraction/validation.
Run: python -m wheeler.mcp_ops
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from wheeler.graph import provenance
from wheeler.tools import graph_tools
from wheeler.validation import citations
from wheeler import workspace
from wheeler.mcp_shared import (
    _config,
    _logged,
    _verify_backend,
)

mcp = FastMCP(
    "wheeler_ops",
    instructions="Provenance and file ops: hash_file, scan_workspace, scan_dependencies, detect_stale, citation extraction and validation, graph_consistency_check. For registering a file node, use wheeler_mutations.ensure_artifact (it calls hash_file internally and writes the graph node).",
)


# --- Provenance ---


@mcp.tool()
@_logged
async def detect_stale() -> list[dict]:
    """Find Wheeler knowledge graph Script nodes whose file has been modified since last recorded hash."""
    stale = await provenance.detect_stale_scripts(_config)
    return [
        {
            "node_id": s.node_id,
            "path": s.path,
            "stored_hash": s.stored_hash,
            "current_hash": s.current_hash,
        }
        for s in stale
    ]


@mcp.tool()
@_logged
async def hash_file(path: str) -> dict:
    """Compute SHA-256 hash of a file for Wheeler research provenance tracking. Most callers should use ensure_artifact instead, which hashes + registers in one call."""
    sha = provenance.hash_file(path)
    return {"path": path, "sha256": sha}


@mcp.tool()
@_logged
async def scan_dependencies(script_path: str, link_to_graph: bool = False) -> dict:
    """Scan a Python script for imports and data file references for Wheeler research provenance.

    Uses AST parsing (no execution) to extract:
    - imports: all imported modules
    - data_files: file paths found in string literals and data-loading calls
      (pd.read_csv, np.load, scipy.io.loadmat, etc.)
    - function_calls: unique function/method calls

    When link_to_graph is True and the script has a matching Analysis node,
    creates DEPENDS_ON edges to any Dataset nodes whose paths match
    detected data files.

    Args:
        script_path: Path to a .py file
        link_to_graph: If True, create graph edges for discovered dependencies
    """
    from wheeler.depscanner import scan_script

    try:
        dep_map = scan_script(script_path)
    except FileNotFoundError:
        return {"error": f"Script not found: {script_path}"}
    except SyntaxError as exc:
        return {"error": f"Parse error: {exc}"}

    result = dep_map.to_dict()

    if link_to_graph and dep_map.data_files:
        edges = await _link_dependencies(script_path, dep_map.data_files)
        result["edges_created"] = edges

    return result


async def _link_dependencies(
    script_path: str, data_files: list[dict[str, str]]
) -> list[dict]:
    """Best-effort: find Analysis node for this script and link to matching Datasets."""
    edges: list[dict] = []
    try:
        backend = await graph_tools._get_backend(_config)

        # Find Analysis node by script_path
        analyses = await backend.run_cypher(
            "MATCH (a:Analysis) WHERE a.script_path CONTAINS $path "
            "RETURN a.id AS id ORDER BY a.date DESC LIMIT 1",
            parameters={"path": script_path},
        )
        if not analyses:
            return [{"note": f"No Analysis node found for {script_path}"}]

        analysis_id = analyses[0]["id"]

        # Find Dataset nodes matching any of the detected data file paths
        for df in data_files:
            datasets = await backend.run_cypher(
                "MATCH (d:Dataset) WHERE d.path CONTAINS $path "
                "RETURN d.id AS id",
                parameters={"path": df["path"]},
            )
            for ds in datasets:
                link_result = await graph_tools.execute_tool(
                    "link_nodes",
                    {
                        "source_id": analysis_id,
                        "target_id": ds["id"],
                        "relationship": "DEPENDS_ON",
                    },
                    _config,
                )
                edges.append(json.loads(link_result))
    except Exception as exc:
        edges.append({"error": f"Graph linking failed: {exc}"})
    return edges


# --- Workspace ---


@mcp.tool()
@_logged
async def scan_workspace() -> dict:
    """Scan research workspace paths defined in wheeler.yaml to discover data files and scripts for knowledge graph indexing.

    Only use for research asset discovery when building or updating the Wheeler
    knowledge graph (e.g. during /wh:ingest), not for general file browsing or
    non-research tasks. For general file operations use Read/Glob tools instead.
    """
    summary = workspace.scan_workspace(_config.workspace, _config.paths)
    return {
        "project_dir": summary.project_dir,
        "total_files": summary.total_files,
        "scripts": [
            {"path": f.path, "extension": f.extension, "size_bytes": f.size_bytes}
            for f in summary.scripts
        ],
        "data_files": [
            {"path": f.path, "extension": f.extension, "size_bytes": f.size_bytes}
            for f in summary.data_files
        ],
    }


# --- Citation validation ---


@mcp.tool()
@_logged
async def extract_citations(text: str) -> list[str]:
    """Extract all Wheeler knowledge graph node ID citations ([F-3a2b] format) from text using regex."""
    return citations.extract_citations(text)


@mcp.tool()
@_logged
async def validate_citations(text: str) -> dict:
    """Validate all Wheeler knowledge graph citations in text against Neo4j. Checks existence and provenance."""
    results = await citations.validate_citations(text, _config)
    valid = sum(1 for r in results if r.status == citations.CitationStatus.VALID)
    return {
        "total": len(results),
        "valid": valid,
        "results": [
            {
                "node_id": r.node_id,
                "status": r.status.value,
                "label": r.label,
                "details": r.details,
            }
            for r in results
        ],
    }


# --- Retrieval quality ---


@mcp.tool()
@_logged
async def compute_retrieval_quality(
    output_text: str,
    retrieved_node_ids: str = "",
) -> dict:
    """Compute retrieval quality metrics for generated text.

    Measures how effectively the knowledge graph was used:
    - context_precision: fraction of retrieved nodes actually cited
    - coverage_gaps: terms in output not backed by any graph node

    Args:
        output_text: The generated text to evaluate
        retrieved_node_ids: Comma-separated node IDs that were retrieved as context
    """
    from wheeler.validation.ledger import compute_retrieval_metrics
    from wheeler.knowledge.store import list_nodes
    from pathlib import Path

    retrieved = (
        [r.strip() for r in retrieved_node_ids.split(",") if r.strip()]
        if retrieved_node_ids
        else []
    )

    # Build node text corpus from knowledge files
    knowledge_dir = Path(_config.knowledge_path)
    node_texts: dict[str, str] = {}
    try:
        from wheeler.models import title_for_node

        nodes = list_nodes(knowledge_dir)
        for node in nodes:
            node_texts[node.id] = title_for_node(node)
    except Exception:
        pass  # if knowledge dir doesn't exist, corpus is empty

    metrics = compute_retrieval_metrics(output_text, retrieved, node_texts)
    return metrics


# --- Consistency ---


@mcp.tool()
@_logged
async def graph_consistency_check(repair: bool = False) -> dict:
    """Check consistency across graph, JSON, and synthesis layers.

    Compares node inventories in Neo4j, knowledge/*.json, and synthesis/*.md.
    Reports nodes that exist in one layer but not others.

    Set repair=True to fix detected drift:
    - Regenerate missing synthesis files from JSON
    - Delete orphaned synthesis files with no backing JSON
    - Warn about graph/JSON mismatches (manual intervention needed)

    Use during /wh:dream consolidation or /wh:close end-of-session sweep.
    """
    from dataclasses import asdict
    from wheeler.consistency import check_consistency, repair_consistency

    report = await check_consistency(_config)
    result = asdict(report)

    if repair:
        repair_log = await repair_consistency(_config, report, dry_run=False)
        result["repairs"] = repair_log
    else:
        result["repairs"] = await repair_consistency(_config, report, dry_run=True)

    return result


# --- Community detection ---


@mcp.tool()
@_logged
async def detect_communities(min_size: int = 3) -> dict:
    """Detect research theme clusters in the Wheeler knowledge graph.

    Uses connected components to find groups of related nodes.
    Returns communities with member details, label distributions,
    and summary statistics.

    Use during /wh:dream consolidation to surface emergent research themes.
    Communities with 3+ nodes are returned by default.

    Args:
        min_size: Minimum community size to include (default 3)
    """
    from wheeler.communities import find_communities
    return await find_communities(_config, min_size=min_size)


# --- Contract validation ---


@mcp.tool()
@_logged
async def validate_task_contract(
    session_id: str,
    required_finding_count: int = 0,
    confidence_min: float = 0.0,
    required_hypothesis_count: int = 0,
    require_provenance: bool = True,
    must_reference: str = "",
) -> dict:
    """Validate task output against a contract.

    Check that a task session produced the expected graph nodes,
    provenance links, and references. Use during /wh:reconvene to
    verify independent tasks met their goals.

    Args:
        session_id: The session ID of the task to validate
        required_finding_count: Minimum Finding nodes expected (0 = skip check)
        confidence_min: Minimum confidence for findings (0.0 = skip check)
        required_hypothesis_count: Minimum Hypothesis nodes expected (0 = skip check)
        require_provenance: Check that findings have WAS_GENERATED_BY links
        must_reference: Comma-separated node IDs that must be referenced by task output
    """
    from wheeler.contracts import (
        TaskContract, NodeRequirement, LinkRequirement, validate_contract,
    )

    reqs: list[NodeRequirement] = []
    if required_finding_count > 0:
        reqs.append(NodeRequirement(
            type="Finding", min_count=required_finding_count,
            confidence_min=confidence_min,
        ))
    if required_hypothesis_count > 0:
        reqs.append(NodeRequirement(
            type="Hypothesis", min_count=required_hypothesis_count,
        ))

    links: list[LinkRequirement] = []
    if require_provenance and required_finding_count > 0:
        links.append(LinkRequirement(
            from_type="Finding",
            relationship="WAS_GENERATED_BY",
            to_type="Execution",
        ))

    refs = [r.strip() for r in must_reference.split(",") if r.strip()] if must_reference else []

    contract = TaskContract(
        task_id=f"validate-{session_id}",
        required_nodes=reqs,
        required_links=links,
        must_reference=refs,
    )

    result = await validate_contract(_config, contract, session_id)
    return {
        "passed": result.passed,
        "violations": result.violations,
        "checks_run": result.checks_run,
        "summary": result.summary,
    }


# --- Entry point ---


def main():
    import asyncio

    from wheeler.graph.driver import invalidate_async_driver

    asyncio.run(_verify_backend())
    invalidate_async_driver()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
