"""Tests for wheeler.config module."""

from pathlib import Path

import pytest
import yaml

from wheeler.config import WheelerConfig, Neo4jConfig, load_config

NEO4J_ENV_VARS = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE")


@pytest.fixture()
def clean_neo4j_env(monkeypatch: pytest.MonkeyPatch):
    """Drop ambient NEO4J_* vars so precedence assertions are deterministic."""
    for var in NEO4J_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("WHEELER_PROJECT_ROOT", raising=False)


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


class TestEnvOverridesYaml:
    """Precedence is env > wheeler.yaml > model default.

    Regression: every Neo4j field uses Field(default_factory=os.getenv(...)),
    so a pinned YAML value used to mean the factory never fired and NEO4J_URI
    and friends were dead whenever wheeler.yaml named them.
    """

    def _pinned_yaml(self, tmp_path: Path) -> Path:
        yaml_path = tmp_path / "wheeler.yaml"
        yaml_path.write_text(yaml.dump({
            "neo4j": {
                "uri": "bolt://from-yaml:7687",
                "username": "yaml-user",
                "password": "yaml-pass",
                "database": "yaml-db",
            },
        }))
        return yaml_path

    def test_neo4j_uri_env_beats_pinned_yaml(self, tmp_path, monkeypatch, clean_neo4j_env):
        """NEO4J_URI must win over a wheeler.yaml that pins a different URI."""
        yaml_path = self._pinned_yaml(tmp_path)
        monkeypatch.setenv("NEO4J_URI", "bolt://from-env:7687")

        config = load_config(yaml_path)

        assert config.neo4j.uri == "bolt://from-env:7687"
        # Unset vars leave the YAML values alone.
        assert config.neo4j.username == "yaml-user"
        assert config.neo4j.password == "yaml-pass"
        assert config.neo4j.database == "yaml-db"

    def test_all_four_neo4j_fields_are_overridable(self, tmp_path, monkeypatch, clean_neo4j_env):
        yaml_path = self._pinned_yaml(tmp_path)
        monkeypatch.setenv("NEO4J_URI", "bolt://env-host:7999")
        monkeypatch.setenv("NEO4J_USERNAME", "env-user")
        monkeypatch.setenv("NEO4J_PASSWORD", "env-pass")
        monkeypatch.setenv("NEO4J_DATABASE", "env-db")

        config = load_config(yaml_path)

        assert config.neo4j.uri == "bolt://env-host:7999"
        assert config.neo4j.username == "env-user"
        assert config.neo4j.password == "env-pass"
        assert config.neo4j.database == "env-db"

    def test_env_beats_yaml_through_discovered_config(self, tmp_path, monkeypatch, clean_neo4j_env):
        """Same precedence through the real path: load_config() with no argument."""
        self._pinned_yaml(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NEO4J_URI", "bolt://envwins:1")

        config = load_config()

        assert config.neo4j.uri == "bolt://envwins:1"

    def test_yaml_beats_default_when_env_unset(self, tmp_path, clean_neo4j_env):
        yaml_path = self._pinned_yaml(tmp_path)

        config = load_config(yaml_path)

        assert config.neo4j.uri == "bolt://from-yaml:7687"

    def test_env_applies_when_there_is_no_yaml(self, tmp_path, monkeypatch, clean_neo4j_env):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NEO4J_PASSWORD", "env-only-pass")

        config = load_config()

        assert config.neo4j.password == "env-only-pass"
        assert config.neo4j.uri == "bolt://localhost:7687"

    def test_empty_env_var_does_not_blank_yaml(self, tmp_path, clean_neo4j_env, monkeypatch):
        """An empty string is treated as unset, not as an override to ""."""
        yaml_path = self._pinned_yaml(tmp_path)
        monkeypatch.setenv("NEO4J_URI", "")

        config = load_config(yaml_path)

        assert config.neo4j.uri == "bolt://from-yaml:7687"

    def test_non_neo4j_fields_are_not_touched(self, tmp_path, monkeypatch, clean_neo4j_env):
        """The override list is explicit: only the four Neo4j connection fields."""
        yaml_path = tmp_path / "wheeler.yaml"
        yaml_path.write_text(yaml.dump({
            "neo4j": {"uri": "bolt://from-yaml:7687", "project_tag": "yaml-tag"},
            "max_turns": 42,
        }))
        monkeypatch.setenv("NEO4J_URI", "bolt://from-env:7687")

        config = load_config(yaml_path)

        assert config.neo4j.uri == "bolt://from-env:7687"
        assert config.neo4j.project_tag == "yaml-tag"
        assert config.max_turns == 42
