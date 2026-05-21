"""Regression test for issue #54: mcp__wheeler_core__show_node ImportError.

Root cause: the unanchored `knowledge/` line in `.gitignore` caused hatch
to exclude `wheeler/knowledge/` from the published wheel, so users hit
`No module named 'wheeler.knowledge'` when show_node lazily imports it.

The fix anchors the gitignore patterns. The critical test below builds
a wheel and asserts the subpackage is present.
"""

import asyncio
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_wheeler_knowledge_in_built_wheel():
    """The packaging bug: built wheel must include wheeler/knowledge/.

    Builds a wheel from the source tree and verifies that the knowledge
    subpackage is present. Fails on a tree where `.gitignore` has an
    unanchored `knowledge/` pattern (it excludes wheeler/knowledge/).
    """
    with tempfile.TemporaryDirectory() as tmp:
        outdir = Path(tmp)
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(outdir), str(REPO_ROOT)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            pytest.skip(f"wheel build unavailable: {result.stderr[-500:]}")

        wheels = list(outdir.glob("wheeler-*.whl"))
        assert wheels, f"no wheel built in {outdir}"
        with zipfile.ZipFile(wheels[0]) as zf:
            names = zf.namelist()

        required = [
            "wheeler/knowledge/__init__.py",
            "wheeler/knowledge/store.py",
            "wheeler/knowledge/render.py",
            "wheeler/knowledge/migrate.py",
        ]
        missing = [r for r in required if r not in names]
        assert not missing, (
            f"wheel is missing {missing}. "
            "Likely cause: unanchored `knowledge/` line in .gitignore "
            "matches wheeler/knowledge/ and excludes it from the build. "
            "Fix by anchoring the pattern with a leading slash (`/knowledge/`)."
        )


def test_gitignore_knowledge_pattern_is_anchored():
    """The .gitignore line that excludes the per-project runtime knowledge/
    directory must be anchored with a leading slash so it does not match
    wheeler/knowledge/ (the subpackage)."""
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    lines = [line.strip() for line in gitignore.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    unanchored_offenders = [line for line in lines if line in ("knowledge/", "synthesis/")]
    assert not unanchored_offenders, (
        f"unanchored .gitignore patterns {unanchored_offenders} "
        "match wheeler/knowledge/ and would exclude the subpackage from the wheel. "
        "Anchor them with a leading slash."
    )


@pytest.mark.asyncio
async def test_show_node_lazy_import_works_in_editable_install():
    """End-to-end check: show_node reads a Finding from disk. Stays green
    in the editable dev tree (does not detect the packaging bug itself,
    but guards against regressions in the import path or read logic)."""
    from wheeler.knowledge.store import write_node
    from wheeler.mcp_core import show_node
    from wheeler.models import FindingModel

    with tempfile.TemporaryDirectory() as tmpdir:
        knowledge_path = Path(tmpdir)
        finding = FindingModel(
            id="F-test0001",
            title="Test finding",
            description="A test finding for issue #54",
            confidence=0.8,
        )
        write_node(knowledge_path, finding)

        with patch("wheeler.mcp_core._config.knowledge_path", str(knowledge_path)):
            result = await show_node("F-test0001")

        assert result["id"] == "F-test0001"
        assert "error" not in result


@pytest.mark.asyncio
async def test_show_node_not_found_returns_error():
    """show_node returns a clear error string for missing ids (no stack trace)."""
    from wheeler.mcp_core import show_node

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("wheeler.mcp_core._config.knowledge_path", str(tmpdir)):
            result = await show_node("F-nonexistent")
        assert "error" in result
        assert "not found" in result["error"].lower()
