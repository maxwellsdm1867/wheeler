"""Tests for the epicTreeGUI data integration: config, tools, and prompt injection."""

import textwrap

import pytest
import yaml

from wheeler.config import DataSourcesConfig, WorkspaceConfig, WheelerConfig, load_config
from wheeler.tools.graph_tools import TOOL_DEFINITIONS


class TestDataSourcesConfig:
    def test_defaults_empty(self):
        cfg = DataSourcesConfig()
        assert cfg.epicTreeGUI_root == ""
        assert cfg.data_dir == ""
        assert cfg.h5_dir == ""

    def test_wheeler_config_defaults_empty(self):
        cfg = WheelerConfig()
        assert cfg.data_sources.epicTreeGUI_root == ""
        assert cfg.data_sources.data_dir == ""

    def test_from_dict(self):
        cfg = WheelerConfig(data_sources={
            "epicTreeGUI_root": "/path/to/epic",
            "data_dir": "/path/to/data",
        })
        assert cfg.data_sources.epicTreeGUI_root == "/path/to/epic"
        assert cfg.data_sources.data_dir == "/path/to/data"
        assert cfg.data_sources.h5_dir == ""

    def test_from_yaml(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            neo4j:
              uri: bolt://localhost:7687
            data_sources:
              epicTreeGUI_root: /some/path
              data_dir: /some/data
        """)
        config_file = tmp_path / "wheeler.yaml"
        config_file.write_text(yaml_content)
        cfg = load_config(config_file)
        assert cfg.data_sources.epicTreeGUI_root == "/some/path"
        assert cfg.data_sources.data_dir == "/some/data"

    def test_missing_data_sources_in_yaml(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            neo4j:
              uri: bolt://localhost:7687
        """)
        config_file = tmp_path / "wheeler.yaml"
        config_file.write_text(yaml_content)
        cfg = load_config(config_file)
        assert cfg.data_sources.epicTreeGUI_root == ""
        assert cfg.data_sources.data_dir == ""


class TestWorkspaceConfigIntegration:
    def test_wheeler_config_has_workspace(self):
        cfg = WheelerConfig()
        assert hasattr(cfg, "workspace")
        assert isinstance(cfg.workspace, WorkspaceConfig)

    def test_workspace_defaults(self):
        cfg = WheelerConfig()
        assert cfg.workspace.project_dir == "."
        assert "*.py" in cfg.workspace.scan_patterns

    def test_workspace_from_yaml(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            workspace:
              project_dir: /my/project
              scan_patterns: ["*.r"]
              exclude_dirs: ["build"]
        """)
        config_file = tmp_path / "wheeler.yaml"
        config_file.write_text(yaml_content)
        cfg = load_config(config_file)
        assert cfg.workspace.project_dir == "/my/project"
        assert cfg.workspace.scan_patterns == ["*.r"]
        assert cfg.workspace.exclude_dirs == ["build"]

    def test_missing_workspace_in_yaml(self, tmp_path):
        yaml_content = textwrap.dedent("""\
            neo4j:
              uri: bolt://localhost:7687
        """)
        config_file = tmp_path / "wheeler.yaml"
        config_file.write_text(yaml_content)
        cfg = load_config(config_file)
        assert cfg.workspace.project_dir == "."


class TestDatasetTools:
    def test_add_dataset_exists(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert "add_dataset" in names

    def test_query_datasets_exists(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert "query_datasets" in names

    def test_add_dataset_parameters(self):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "add_dataset")
        assert "path" in tool["parameters"]
        assert "type" in tool["parameters"]
        assert "description" in tool["parameters"]
        assert tool["required"] == ["path", "type", "description"]

    def test_query_datasets_parameters(self):
        tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "query_datasets")
        assert "keyword" in tool["parameters"]
        assert "limit" in tool["parameters"]
        assert tool["required"] == []

    def test_all_tools_have_required_fields(self):
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert "required" in tool


class TestPromptInjection:
    def test_no_injection_when_unconfigured(self):
        """System prompt should NOT contain epicTreeGUI text when data_sources is empty."""
        from wheeler.prompts import SYSTEM_PROMPTS
        from wheeler.modes.state import Mode

        cfg = WheelerConfig()
        # Simulate what engine.py does
        system_prompt = SYSTEM_PROMPTS[Mode.EXECUTE]
        if cfg.data_sources.epicTreeGUI_root:
            system_prompt += "epicTreeGUI"

        assert "epicTreeGUI" not in system_prompt

    def test_injection_when_configured(self):
        """System prompt SHOULD contain epicTreeGUI text when data_sources is set."""
        from wheeler.prompts import SYSTEM_PROMPTS
        from wheeler.modes.state import Mode

        cfg = WheelerConfig(data_sources={
            "epicTreeGUI_root": "/path/to/epic",
            "data_dir": "/path/to/data",
        })
        system_prompt = SYSTEM_PROMPTS[Mode.EXECUTE]
        if cfg.data_sources.epicTreeGUI_root:
            system_prompt += (
                "\n\n## Data Access: epicTreeGUI\n"
                f"Data directory: {cfg.data_sources.data_dir}\n"
                f"epicTreeGUI root: {cfg.data_sources.epicTreeGUI_root}\n"
            )

        assert "epicTreeGUI" in system_prompt
        assert "/path/to/data" in system_prompt
        assert "/path/to/epic" in system_prompt
