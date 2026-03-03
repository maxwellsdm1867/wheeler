"""Tests for wheeler.config module."""

from pathlib import Path
import tempfile

import pytest
import yaml

from wheeler.config import WheelerConfig, Neo4jConfig, load_config


class TestWheelerConfig:
    def test_default_config(self):
        config = WheelerConfig()
        assert config.neo4j.uri == "bolt://localhost:7687"
        assert config.neo4j.username == "neo4j"
        assert config.neo4j.password == "research-graph"
        assert config.neo4j.database == "neo4j"
        assert config.max_turns == 10
        assert config.context_max_findings == 5
        assert config.context_max_questions == 5
        assert config.context_max_hypotheses == 3

    def test_custom_config(self):
        config = WheelerConfig(
            neo4j=Neo4jConfig(uri="bolt://other:7687", password="secret"),
            max_turns=20,
        )
        assert config.neo4j.uri == "bolt://other:7687"
        assert config.neo4j.password == "secret"
        assert config.max_turns == 20

    def test_load_config_missing_file(self):
        config = load_config(Path("/nonexistent/wheeler.yaml"))
        assert config == WheelerConfig()

    def test_load_config_from_yaml(self, tmp_path):
        yaml_path = tmp_path / "wheeler.yaml"
        data = {
            "neo4j": {"uri": "bolt://custom:7687", "password": "custom-pass"},
            "max_turns": 25,
        }
        yaml_path.write_text(yaml.dump(data))

        config = load_config(yaml_path)
        assert config.neo4j.uri == "bolt://custom:7687"
        assert config.neo4j.password == "custom-pass"
        assert config.max_turns == 25
        # Defaults for unspecified fields
        assert config.neo4j.username == "neo4j"
        assert config.context_max_findings == 5

    def test_load_config_empty_yaml(self, tmp_path):
        yaml_path = tmp_path / "wheeler.yaml"
        yaml_path.write_text("")
        config = load_config(yaml_path)
        assert config == WheelerConfig()
