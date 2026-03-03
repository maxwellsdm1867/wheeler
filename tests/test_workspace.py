"""Tests for wheeler.workspace module."""

from pathlib import Path

import pytest

from wheeler.config import WorkspaceConfig
from wheeler.workspace import FileInfo, WorkspaceSummary, scan_workspace, format_workspace_context


class TestScanWorkspace:
    def test_scan_empty_dir(self, tmp_path):
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert summary.total_files == 0
        assert summary.scripts == []
        assert summary.data_files == []

    def test_scan_finds_py_files(self, tmp_path):
        (tmp_path / "analysis.py").write_text("print('hello')")
        (tmp_path / "helper.py").write_text("x = 1")
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert len(summary.scripts) == 2
        assert summary.total_files == 2
        names = {f.path for f in summary.scripts}
        assert "analysis.py" in names
        assert "helper.py" in names

    def test_scan_finds_m_files(self, tmp_path):
        (tmp_path / "run_analysis.m").write_text("% matlab")
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert len(summary.scripts) == 1
        assert summary.scripts[0].extension == ".m"
        assert summary.scripts[0].category == "script"

    def test_scan_finds_data_files(self, tmp_path):
        (tmp_path / "data.mat").write_bytes(b"\x00" * 100)
        (tmp_path / "results.csv").write_text("a,b\n1,2")
        (tmp_path / "big.h5").write_bytes(b"\x00" * 50)
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert len(summary.data_files) == 3
        assert summary.total_files == 3
        extensions = {f.extension for f in summary.data_files}
        assert extensions == {".mat", ".csv", ".h5"}

    def test_scan_finds_hdf5_files(self, tmp_path):
        (tmp_path / "recording.hdf5").write_bytes(b"\x00" * 80)
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert len(summary.data_files) == 1
        assert summary.data_files[0].extension == ".hdf5"
        assert summary.data_files[0].category == "data"

    def test_scan_excludes_venv(self, tmp_path):
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "site.py").write_text("# venv")
        (tmp_path / "main.py").write_text("# real")
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert len(summary.scripts) == 1
        assert summary.scripts[0].path == "main.py"

    def test_scan_excludes_pycache(self, tmp_path):
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "module.py").write_text("# cached")
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert summary.total_files == 0

    def test_scan_respects_custom_patterns(self, tmp_path):
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "script.py").write_text("x = 1")
        config = WorkspaceConfig(
            project_dir=str(tmp_path),
            scan_patterns=["*.json"],
        )
        summary = scan_workspace(config)
        assert summary.total_files == 1

    def test_scan_nested_directories(self, tmp_path):
        sub = tmp_path / "src" / "analysis"
        sub.mkdir(parents=True)
        (sub / "run.py").write_text("# analysis")
        (tmp_path / "data" / "raw").mkdir(parents=True)
        (tmp_path / "data" / "raw" / "epochs.mat").write_bytes(b"\x00")
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert len(summary.scripts) == 1
        assert len(summary.data_files) == 1
        assert summary.scripts[0].path == str(Path("src/analysis/run.py"))

    def test_scan_records_size(self, tmp_path):
        content = b"x" * 42
        (tmp_path / "small.py").write_bytes(content)
        config = WorkspaceConfig(project_dir=str(tmp_path))
        summary = scan_workspace(config)
        assert summary.scripts[0].size_bytes == 42

    def test_scan_nonexistent_dir(self):
        config = WorkspaceConfig(project_dir="/nonexistent/path/xyz")
        summary = scan_workspace(config)
        assert summary.total_files == 0


class TestFormatWorkspaceContext:
    def test_format_empty(self):
        summary = WorkspaceSummary(project_dir="/tmp", total_files=0)
        assert format_workspace_context(summary) == ""

    def test_format_compact(self, tmp_path):
        summary = WorkspaceSummary(
            project_dir=str(tmp_path),
            scripts=[
                FileInfo(path="src/main.py", category="script", extension=".py", size_bytes=100),
                FileInfo(path="src/util.py", category="script", extension=".py", size_bytes=50),
            ],
            data_files=[
                FileInfo(path="data/raw.mat", category="data", extension=".mat", size_bytes=1000),
            ],
            total_files=3,
        )
        context = format_workspace_context(summary)
        assert "## Workspace:" in context
        assert "Scripts (2)" in context
        assert "Data files (1)" in context
        assert len(context) < 500

    def test_format_shows_key_paths(self):
        summary = WorkspaceSummary(
            project_dir="/project",
            scripts=[
                FileInfo(path="wheeler/engine.py", category="script", extension=".py", size_bytes=100),
                FileInfo(path="tests/test_foo.py", category="script", extension=".py", size_bytes=50),
            ],
            total_files=2,
        )
        context = format_workspace_context(summary)
        assert "Key paths:" in context
        assert "wheeler/" in context
        assert "tests/" in context


class TestWorkspaceConfig:
    def test_defaults(self):
        config = WorkspaceConfig()
        assert config.project_dir == "."
        assert "*.py" in config.scan_patterns
        assert "*.m" in config.scan_patterns
        assert "*.mat" in config.scan_patterns
        assert ".venv" in config.exclude_dirs
        assert "__pycache__" in config.exclude_dirs

    def test_custom_values(self):
        config = WorkspaceConfig(
            project_dir="/my/project",
            scan_patterns=["*.r", "*.jl"],
            exclude_dirs=["build"],
        )
        assert config.project_dir == "/my/project"
        assert config.scan_patterns == ["*.r", "*.jl"]
        assert config.exclude_dirs == ["build"]
