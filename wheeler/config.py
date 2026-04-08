"""Configuration loader: YAML file + Pydantic model."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pydantic import BaseModel, Field
import yaml

logger = logging.getLogger(__name__)


_DEFAULT_CONFIG_PATH = Path("wheeler.yaml")


class Neo4jConfig(BaseModel):
    uri: str = Field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    username: str = Field(default_factory=lambda: os.getenv("NEO4J_USERNAME", "neo4j"))
    password: str = Field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "research-graph"))
    database: str = Field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))
    # Project namespace for Community Edition isolation.
    # When set, all nodes get a _wheeler_project property and queries filter
    # by it.  Empty string means no namespacing (Enterprise/Aura uses a
    # dedicated database instead).  Populated automatically by ensure_database().
    project_tag: str = ""
    # Circuit breaker: fail fast when Neo4j is unreachable.
    cb_failure_threshold: int = 3
    cb_recovery_timeout: float = 60.0


class DataSourcesConfig(BaseModel):
    epicTreeGUI_root: str = ""
    data_dir: str = ""
    h5_dir: str = ""


class ProjectMeta(BaseModel):
    name: str = ""
    description: str = ""


class ProjectPaths(BaseModel):
    code: list[str] = []
    data: list[str] = []
    results: list[str] = []
    figures: list[str] = []
    docs: list[str] = []


class WorkspaceConfig(BaseModel):
    project_dir: str = "."
    scan_patterns: list[str] = ["*.py", "*.m", "*.mat", "*.h5", "*.hdf5", "*.csv"]
    exclude_dirs: list[str] = [".venv", "__pycache__", ".git", "node_modules", ".wheeler", "knowledge"]


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


class SearchConfig(BaseModel):
    """Semantic search configuration."""

    enabled: bool = True
    store_path: str = ".wheeler/embeddings"
    model: str = "BAAI/bge-small-en-v1.5"


class GraphConfig(BaseModel):
    """Graph backend selection."""
    backend: str = "neo4j"


class WheelerConfig(BaseModel):
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    mcp_config_path: str = ".mcp.json"
    max_turns: int = 10
    context_max_findings: int = 5
    context_max_questions: int = 5
    context_max_hypotheses: int = 3
    project: ProjectMeta = Field(default_factory=ProjectMeta)
    paths: ProjectPaths = Field(default_factory=ProjectPaths)
    data_sources: DataSourcesConfig = Field(default_factory=DataSourcesConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    knowledge_path: str = "knowledge"
    synthesis_path: str = "synthesis"


def load_config(path: Path | None = None) -> WheelerConfig:
    """Load configuration from a YAML file.

    Falls back to defaults if the file doesn't exist.
    """
    config_path = path or _DEFAULT_CONFIG_PATH
    if config_path.exists():
        logger.info("Loading config from %s", config_path)
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return WheelerConfig(**data)
    logger.info("No config file at %s — using defaults", config_path)
    return WheelerConfig()


def configure_logging(level: str | None = None) -> None:
    """Configure Wheeler logging. Call once at application entry points.

    Level resolution: argument > WHEELER_LOG_LEVEL env var > INFO default.
    """
    resolved = (level or os.environ.get("WHEELER_LOG_LEVEL", "INFO")).upper()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    root = logging.getLogger("wheeler")
    root.setLevel(resolved)
    root.addHandler(handler)
