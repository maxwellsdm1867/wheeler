"""Tests for wheeler.scaffold module."""

from pathlib import Path

import pytest
import yaml

from wheeler.config import ProjectMeta, ProjectPaths, WheelerConfig
from wheeler.scaffold import (
    create_project_dirs,
    detect_project_dirs,
    scaffold_managed_dirs,
    scaffold_project,
    write_config,
)


class TestDetectProjectDirs:
    def test_detects_existing_dirs(self, tmp_path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "data").mkdir()
        (tmp_path / "figures").mkdir()
        found = detect_project_dirs(tmp_path)
        assert "code" in found
        assert "scripts" in found["code"]
        assert "data" in found
        assert "figures" in found

    def test_detects_multiple_matches(self, tmp_path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "src").mkdir()
        found = detect_project_dirs(tmp_path)
        assert set(found["code"]) == {"scripts", "src"}

    def test_empty_project(self, tmp_path):
        found = detect_project_dirs(tmp_path)
        assert found == {}

    def test_ignores_files(self, tmp_path):
        (tmp_path / "scripts").write_text("not a dir")
        found = detect_project_dirs(tmp_path)
        assert "code" not in found


class TestCreateProjectDirs:
    def test_creates_missing_dirs(self, tmp_path):
        created = create_project_dirs(tmp_path, ["foo", "bar/baz"])
        assert "foo" in created
        assert "bar/baz" in created
        assert (tmp_path / "foo").is_dir()
        assert (tmp_path / "bar" / "baz").is_dir()

    def test_skips_existing(self, tmp_path):
        (tmp_path / "existing").mkdir()
        created = create_project_dirs(tmp_path, ["existing", "new"])
        assert "existing" not in created
        assert "new" in created


class TestScaffoldManagedDirs:
    def test_creates_managed_dirs(self, tmp_path):
        created = scaffold_managed_dirs(tmp_path)
        assert ".plans" in created
        assert ".logs" in created
        assert ".wheeler" in created
        assert (tmp_path / ".plans").is_dir()
        assert (tmp_path / ".logs").is_dir()
        assert (tmp_path / ".wheeler").is_dir()

    def test_idempotent(self, tmp_path):
        scaffold_managed_dirs(tmp_path)
        created = scaffold_managed_dirs(tmp_path)
        assert created == []


class TestWriteConfig:
    def test_writes_yaml(self, tmp_path):
        meta = ProjectMeta(name="My Project", description="Testing scaffolding")
        paths = ProjectPaths(code=["scripts"], data=["data", "/shared/data"])
        config_path = write_config(tmp_path, project=meta, paths=paths)
        assert config_path == tmp_path / "wheeler.yaml"
        assert config_path.exists()

        data = yaml.safe_load(config_path.read_text())
        assert data["project"]["name"] == "My Project"
        assert data["paths"]["code"] == ["scripts"]
        assert data["paths"]["data"] == ["data", "/shared/data"]

    def test_merges_with_existing(self, tmp_path):
        existing = WheelerConfig(max_turns=20)
        paths = ProjectPaths(figures=["figs"])
        write_config(tmp_path, paths=paths, existing_config=existing)

        data = yaml.safe_load((tmp_path / "wheeler.yaml").read_text())
        assert data["max_turns"] == 20
        assert data["paths"]["figures"] == ["figs"]

    def test_excludes_defaults(self, tmp_path):
        write_config(tmp_path, project=ProjectMeta(name="Test"))
        data = yaml.safe_load((tmp_path / "wheeler.yaml").read_text())
        # Default neo4j settings should not appear
        assert "neo4j" not in data


class TestScaffoldProject:
    def test_full_scaffold(self, tmp_path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "data").mkdir()
        result = scaffold_project(tmp_path)
        assert "scripts" in result["detected"].get("code", [])
        assert "data" in result["detected"].get("data", [])
        assert ".plans" in result["created"]
        assert (tmp_path / ".plans").is_dir()
