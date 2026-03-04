"""Configuration loader: YAML file + Pydantic model."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
import yaml


_DEFAULT_CONFIG_PATH = Path("wheeler.yaml")


class Neo4jConfig(BaseModel):
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "research-graph"
    database: str = "neo4j"


class DataSourcesConfig(BaseModel):
    epicTreeGUI_root: str = ""
    data_dir: str = ""
    h5_dir: str = ""


class WorkspaceConfig(BaseModel):
    project_dir: str = "."
    scan_patterns: list[str] = ["*.py", "*.m", "*.mat", "*.h5", "*.hdf5", "*.csv"]
    exclude_dirs: list[str] = [".venv", "__pycache__", ".git", "node_modules", ".wheeler"]


class ModelsConfig(BaseModel):
    """Model selection per mode. Use aliases (sonnet, opus, haiku) or full names.

    Reasoning:
    - planning: Opus — scientific reasoning, sharpening questions, hypotheses
    - writing: Opus — drafting findings, nuanced prose, revision
    - execute: Sonnet — code generation, tool use, script execution
    - chat: Sonnet — discussion, quick queries
    """
    chat: str = "sonnet"
    planning: str = "opus"
    writing: str = "opus"
    execute: str = "sonnet"


class WheelerConfig(BaseModel):
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    mcp_config_path: str = ".mcp.json"
    max_turns: int = 10
    context_max_findings: int = 5
    context_max_questions: int = 5
    context_max_hypotheses: int = 3
    data_sources: DataSourcesConfig = Field(default_factory=DataSourcesConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)


def load_config(path: Path | None = None) -> WheelerConfig:
    """Load configuration from a YAML file.

    Falls back to defaults if the file doesn't exist.
    """
    config_path = path or _DEFAULT_CONFIG_PATH
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return WheelerConfig(**data)
    return WheelerConfig()
