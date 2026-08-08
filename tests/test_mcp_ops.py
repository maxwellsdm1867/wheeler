"""Tests for wheeler.mcp_ops module.

Ported from the deleted test_mcp_server.py: the monolith carried private copies
of these helpers, the split servers are now the only home.
"""

from unittest.mock import AsyncMock, patch

import pytest

class TestExtractCitations:
    """extract_citations is pure regex — no mocking needed."""

    @pytest.mark.asyncio
    async def test_extract_finds_citations(self):
        from wheeler.mcp_ops import extract_citations
        result = await extract_citations("See [F-3a2b] and [H-0012abcd]")
        assert result == ["F-3a2b", "H-0012abcd"]

    @pytest.mark.asyncio
    async def test_extract_empty_text(self):
        from wheeler.mcp_ops import extract_citations
        result = await extract_citations("No citations here")
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_deduplicates(self):
        from wheeler.mcp_ops import extract_citations
        result = await extract_citations("[F-3a2b] repeated [F-3a2b]")
        assert result == ["F-3a2b"]

class TestScanWorkspace:
    """scan_workspace uses filesystem — mock at the workspace module level."""

    @pytest.mark.asyncio
    async def test_scan_returns_structure(self):
        from wheeler.workspace import WorkspaceSummary, FileInfo
        mock_summary = WorkspaceSummary(
            project_dir="/tmp/test",
            scripts=[FileInfo(path="analysis.py", category="script", extension=".py", size_bytes=1024)],
            data_files=[FileInfo(path="data.mat", category="data", extension=".mat", size_bytes=2048)],
            total_files=2,
        )
        with patch("wheeler.mcp_ops.workspace.scan_workspace", return_value=mock_summary):
            from wheeler.mcp_ops import scan_workspace
            result = await scan_workspace()
        assert result["project_dir"] == "/tmp/test"
        assert result["total_files"] == 2
        assert len(result["scripts"]) == 1
        assert result["scripts"][0]["path"] == "analysis.py"
        assert len(result["data_files"]) == 1

class TestHashFile:
    @pytest.mark.asyncio
    async def test_hash_returns_dict(self):
        with patch("wheeler.mcp_ops.provenance.hash_file", return_value="abc123"):
            from wheeler.mcp_ops import hash_file
            result = await hash_file("/tmp/test.py")
        assert result == {"path": "/tmp/test.py", "sha256": "abc123"}

class TestValidateCitations:
    @pytest.mark.asyncio
    async def test_validate_returns_structure(self):
        from wheeler.validation.citations import CitationResult, CitationStatus
        mock_results = [
            CitationResult(node_id="F-3a2b", status=CitationStatus.VALID, label="Finding"),
            CitationResult(node_id="H-0000", status=CitationStatus.NOT_FOUND, label="Hypothesis", details="not found"),
        ]
        with patch("wheeler.mcp_ops.citations.validate_citations", new_callable=AsyncMock, return_value=mock_results):
            from wheeler.mcp_ops import validate_citations
            result = await validate_citations("See [F-3a2b] and [H-0000]")
        assert result["total"] == 2
        assert result["valid"] == 1
        assert result["results"][0]["status"] == "valid"
        assert result["results"][1]["status"] == "not_found"

class TestScanDependencies:
    """scan_dependencies delegates to depscanner — test MCP wrapper."""

    @pytest.mark.asyncio
    async def test_scan_returns_structure(self, tmp_path):
        script = tmp_path / "test_script.py"
        script.write_text("import numpy as np\ndf = np.load('data.npy')\n")

        from wheeler.mcp_ops import scan_dependencies
        result = await scan_dependencies(str(script))

        assert "imports" in result
        assert "data_files" in result
        assert "function_calls" in result
        assert "numpy" in result["imports"]
        assert any(d["path"] == "data.npy" for d in result["data_files"])

    @pytest.mark.asyncio
    async def test_scan_file_not_found(self):
        from wheeler.mcp_ops import scan_dependencies
        result = await scan_dependencies("/nonexistent/path.py")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_scan_syntax_error(self, tmp_path):
        script = tmp_path / "bad.py"
        script.write_text("def broken(\n")

        from wheeler.mcp_ops import scan_dependencies
        result = await scan_dependencies(str(script))
        assert "error" in result


class TestScanDependenciesLinking:
    """`scan_dependencies(link_to_graph=True)` never created an edge.

    `run_cypher` takes `params`, not `parameters`, so every call raised
    TypeError, and the blanket `except Exception` turned it into a returned
    error dict. The feature was dead for its entire life and nothing said so.
    """

    def test_no_call_site_uses_the_wrong_kwarg(self):
        """Mechanical: one kwarg typo cost this feature its whole lifetime."""
        import pathlib
        import re

        offenders = []
        for path in pathlib.Path("wheeler").rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            # Attribute CALLS only (`backend.run_cypher(...)`). The definition
            # in neo4j_backend.py legitimately wraps the neo4j driver's own
            # `session.run(query, parameters=...)`, which really does take that
            # keyword; matching `def run_cypher(` too would flag it forever.
            for match in re.finditer(r"\.run_cypher\s*\(", src):
                window = src[match.start(): match.start() + 400]
                if re.search(r"\bparameters\s*=", window):
                    line = src[: match.start()].count("\n") + 1
                    offenders.append(f"{path}:{line}")
        assert offenders == [], (
            f"run_cypher takes `params`, not `parameters`: {offenders}"
        )

    async def test_link_dependencies_creates_an_edge(self, monkeypatch):
        """Behavioral: a backend that rejects unexpected kwargs, as the real one does."""
        import wheeler.mcp_ops as ops

        linked: list[dict] = []

        class StubBackend:
            async def run_cypher(self, query, params=None):
                if "Analysis" in query:
                    return [{"id": "A-1111"}]
                return [{"id": "D-2222"}]

        async def fake_get_backend(config):
            return StubBackend()

        async def fake_execute_tool(tool_name, args, config):
            linked.append(args)
            return '{"status": "linked"}'

        monkeypatch.setattr(ops.graph_tools, "_get_backend", fake_get_backend)
        monkeypatch.setattr(ops.graph_tools, "execute_tool", fake_execute_tool)

        edges = await ops._link_dependencies("s.py", [{"path": "d.csv"}])

        assert not any("error" in e for e in edges), edges
        assert linked == [{
            "source_id": "A-1111",
            "target_id": "D-2222",
            "relationship": "DEPENDS_ON",
        }]

    async def test_lookups_are_project_scoped(self, monkeypatch):
        """Fixing the kwarg turned a dead path into a LIVE unscoped CONTAINS scan.

        On a shared Neo4j that would match another project's Analysis/Dataset
        nodes and then link across the namespace boundary, so the scoping had
        to land in the same change as the kwarg fix.
        """
        import wheeler.mcp_ops as ops

        seen: list[tuple[str, dict]] = []

        class StubBackend:
            async def run_cypher(self, query, params=None):
                seen.append((query, params or {}))
                return []

        async def fake_get_backend(config):
            return StubBackend()

        monkeypatch.setattr(ops.graph_tools, "_get_backend", fake_get_backend)
        monkeypatch.setattr(ops._config.neo4j, "project_tag", "proj-a")

        await ops._link_dependencies("s.py", [{"path": "d.csv"}])

        assert seen, "no query issued"
        query, params = seen[0]
        assert "_wheeler_project" in query, f"unscoped query: {query}"
        assert params.get("ptag") == "proj-a"
