"""Configuration loader: YAML file + Pydantic model."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import threading

from pydantic import BaseModel, Field
import yaml

logger = logging.getLogger(__name__)


_CONFIG_FILENAME = "wheeler.yaml"

# Files/directories that mark the root of a Wheeler project. `find_project_root`
# walks UP from the starting directory and stops at the first ancestor holding
# one of these, so a server or CLI spawned in a subdirectory still resolves to
# the same project.
_ROOT_MARKERS = (_CONFIG_FILENAME, ".wheeler")

# Highest-precedence project root: an explicit env var beats every heuristic.
_PROJECT_ROOT_ENV = "WHEELER_PROJECT_ROOT"

# Env vars that override wheeler.yaml, field by field. Full precedence is
# env > OS keychain > wheeler.yaml > model default: see `load_config`.
_NEO4J_ENV_OVERRIDES: dict[str, str] = {
    "uri": "NEO4J_URI",
    "username": "NEO4J_USERNAME",
    "password": "NEO4J_PASSWORD",
    "database": "NEO4J_DATABASE",
}

# Bottom of the precedence chain. Named rather than inlined so `neo4j_sources`
# can report the built-in value without restating it and drifting.
_NEO4J_DEFAULTS: dict[str, str] = {
    "uri": "bolt://localhost:7687",
    "username": "neo4j",
    "password": "research-graph",
    "database": "neo4j",
}


def find_project_root(start: Path | None = None) -> Path:
    """Resolve the absolute root of the current Wheeler project.

    Precedence:
    1. `WHEELER_PROJECT_ROOT` env var (explicit wins over every heuristic).
    2. The nearest ancestor of `start` (default: cwd) holding `wheeler.yaml`
       or `.wheeler/`.
    3. `start` itself, i.e. the historical cwd-implicit behaviour.
    """
    env_root = os.environ.get(_PROJECT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser().resolve()

    base = (start or Path.cwd()).expanduser().resolve()
    for candidate in (base, *base.parents):
        if any((candidate / marker).exists() for marker in _ROOT_MARKERS):
            return candidate
    return base


def find_config_file(start: Path | None = None) -> Path | None:
    """Return the project's `wheeler.yaml`, or None when there isn't one."""
    candidate = find_project_root(start) / _CONFIG_FILENAME
    return candidate if candidate.exists() else None


class Neo4jConfig(BaseModel):
    uri: str = Field(default_factory=lambda: os.getenv("NEO4J_URI", _NEO4J_DEFAULTS["uri"]))
    username: str = Field(
        default_factory=lambda: os.getenv("NEO4J_USERNAME", _NEO4J_DEFAULTS["username"])
    )
    password: str = Field(
        default_factory=lambda: os.getenv("NEO4J_PASSWORD", _NEO4J_DEFAULTS["password"])
    )
    database: str = Field(
        default_factory=lambda: os.getenv("NEO4J_DATABASE", _NEO4J_DEFAULTS["database"])
    )
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
    # Root of the project tree. "." means "discover it" (see
    # `resolved_project_root`). The raw "." is intentional here so
    # serialisation round-trips cleanly in wheeler.yaml.
    project_root: str = "."

    # -- Resolved absolute paths -------------------------------------------
    # Read-only views over the relative string fields above. Prefer these at
    # call sites: a bare Path(config.knowledge_path) is relative to whatever
    # cwd the process happens to have, which is not the project root when a
    # server or CLI is spawned from a subdirectory.

    @property
    def resolved_project_root(self) -> Path:
        """Absolute project root: env var > explicit config > marker walk-up > cwd."""
        env_root = os.environ.get(_PROJECT_ROOT_ENV)
        if env_root:
            return Path(env_root).expanduser().resolve()
        if self.project_root and self.project_root != ".":
            return Path(self.project_root).expanduser().resolve()
        return find_project_root()

    def _resolve(self, relative: str) -> Path:
        """Join `relative` onto the project root (absolute inputs pass through)."""
        return self.resolved_project_root / Path(relative).expanduser()

    @property
    def resolved_knowledge_path(self) -> Path:
        return self._resolve(self.knowledge_path)

    @property
    def resolved_synthesis_path(self) -> Path:
        return self._resolve(self.synthesis_path)

    @property
    def resolved_wheeler_dir(self) -> Path:
        return self._resolve(".wheeler")

    @property
    def resolved_search_store_path(self) -> Path:
        return self._resolve(self.search.store_path)


def _config_dir(config: object, field: str, default: str) -> Path:
    """Resolved directory for a config path field, tolerating partial configs.

    A real `WheelerConfig` exposes `resolved_<field>`, which is anchored on the
    project root. Duck-typed stand-ins (test doubles, `SimpleNamespace`) carry
    only the raw relative string, so fall back to the historical `Path(raw)`
    rather than inventing a root for them.
    """
    resolved = getattr(config, f"resolved_{field}", None)
    if isinstance(resolved, Path):
        return resolved
    raw = getattr(config, field, None)
    return Path(raw) if isinstance(raw, str) else Path(default)


def project_knowledge_dir(config: object) -> Path:
    """`knowledge/` for this project, anchored on the project root."""
    return _config_dir(config, "knowledge_path", "knowledge")


def project_synthesis_dir(config: object) -> Path:
    """`synthesis/` for this project, anchored on the project root."""
    return _config_dir(config, "synthesis_path", "synthesis")


def project_wheeler_dir(config: object | None = None) -> Path:
    """`.wheeler/` for this project, anchored on the project root.

    Takes no config at the module-level call sites that predate one, where the
    project root is discovered from the marker walk-up instead.
    """
    resolved = getattr(config, "resolved_wheeler_dir", None)
    if isinstance(resolved, Path):
        return resolved
    return find_project_root() / ".wheeler"


def project_search_store_dir(config: object) -> Path:
    """The embedding store for this project, anchored on the project root."""
    resolved = getattr(config, "resolved_search_store_path", None)
    if isinstance(resolved, Path):
        return resolved
    raw = getattr(getattr(config, "search", None), "store_path", None)
    if isinstance(raw, str):
        return Path(raw)
    return project_wheeler_dir(config) / "embeddings"


def _apply_env_overrides(config: WheelerConfig) -> WheelerConfig:
    """Overlay env vars on a config built from YAML, in place.

    Needed because each Neo4j field's `default_factory` only fires when the
    field is absent from the YAML: a pinned `wheeler.yaml` value would
    otherwise make `NEO4J_URI` and friends dead. Precedence must be
    env > YAML > default.
    """
    for field, env_var in _NEO4J_ENV_OVERRIDES.items():
        value = os.environ.get(env_var)
        if not value:
            continue
        if getattr(config.neo4j, field) != value:
            # Names only: never log the value, one of these is the password.
            logger.debug("neo4j.%s overridden by %s", field, env_var)
            setattr(config.neo4j, field, value)
    return config


# ── Keychain layer ──────────────────────────────────────────────────
# Credentials stored by `wheeler login` sit between env and YAML. The lookup is
# cached per process because `load_config` runs on every CLI command and every
# MCP server start, and one keychain read per process is the right budget.

_keychain_cache: dict[str, dict[str, str] | None] = {}

# A keychain read can BLOCK, not just fail: macOS binds a stored item to the
# process that created it, so a different binary reading it can raise a GUI
# prompt. `load_config` runs at MCP server startup, where a hang shows up as a
# dead server with no explanation, so the lookup is bounded and the wait is
# tunable for a slow unlock.
_KEYCHAIN_TIMEOUT_ENV = "WHEELER_KEYCHAIN_TIMEOUT"
_DEFAULT_KEYCHAIN_TIMEOUT = 5.0


def reset_keychain_cache() -> None:
    """Drop the per-process keychain cache. Call after writing a credential."""
    _keychain_cache.clear()


def _keychain_timeout() -> float:
    raw = os.environ.get(_KEYCHAIN_TIMEOUT_ENV, "").strip()
    if not raw:
        return _DEFAULT_KEYCHAIN_TIMEOUT
    try:
        return max(0.1, float(raw))
    except ValueError:
        logger.warning(
            "%s=%r is not a number, using %ss",
            _KEYCHAIN_TIMEOUT_ENV,
            raw,
            _DEFAULT_KEYCHAIN_TIMEOUT,
        )
        return _DEFAULT_KEYCHAIN_TIMEOUT


def keychain_record(profile: str | None = None) -> dict[str, str] | None:
    """Neo4j credentials stored in the OS keychain, or None.

    Never raises and never blocks for long: the read runs on a daemon thread and
    is abandoned after `_keychain_timeout()` seconds, because "the keychain is
    slow" must degrade to "no stored credentials" rather than to a wedged
    process. Cached per profile so this costs one read per process.

    `wheeler.credentials` is imported function-locally: it depends on nothing
    inside Wheeler, so there is no cycle to close, and keeping the import out of
    module scope preserves this module's empty import graph (see the layering
    rules in CLAUDE.md).
    """
    from wheeler import credentials  # noqa: PLC0415 (see docstring)

    name = profile or credentials.active_profile()
    if name in _keychain_cache:
        return _keychain_cache[name]

    result: list[dict[str, str] | None] = [None]

    def _read() -> None:
        result[0] = credentials.load(name)

    timeout = _keychain_timeout()
    reader = threading.Thread(target=_read, name="wheeler-keychain", daemon=True)
    reader.start()
    reader.join(timeout)
    if reader.is_alive():
        # Daemon thread: an abandoned read cannot hold up interpreter exit. The
        # miss is cached so one stuck keychain costs one delay, not one per call.
        logger.warning(
            "keychain lookup for profile %r did not answer in %.1fs, "
            "continuing without stored credentials",
            name,
            timeout,
        )
        _keychain_cache[name] = None
        return None

    _keychain_cache[name] = result[0]
    return result[0]


def _apply_keychain_overrides(config: WheelerConfig) -> WheelerConfig:
    """Overlay keychain-stored Neo4j credentials on a config built from YAML.

    Applied before `_apply_env_overrides` so env still wins, which is what keeps
    CI and containers working unchanged.
    """
    record = keychain_record()
    if not record:
        return config
    for field in _NEO4J_ENV_OVERRIDES:
        value = record.get(field)
        if not value:
            continue
        if getattr(config.neo4j, field) != value:
            # Names only: never log the value, one of these is the password.
            logger.debug("neo4j.%s supplied by the OS keychain", field)
            setattr(config.neo4j, field, value)
    return config


def load_config(path: Path | None = None) -> WheelerConfig:
    """Load configuration from YAML, then overlay the keychain, then env.

    With no explicit `path`, the project's `wheeler.yaml` is discovered by
    walking up from the cwd (see `find_project_root`). Falls back to model
    defaults when there is no file.

    Precedence, highest first:

    1. `NEO4J_*` env vars (see `_apply_env_overrides`)
    2. the OS keychain, written by `wheeler login` (see `_apply_keychain_overrides`)
    3. `wheeler.yaml`
    4. model defaults (`_NEO4J_DEFAULTS`)

    `neo4j_sources` reports which of the four won, field by field.
    """
    config_path = path or find_config_file()
    if config_path is not None and config_path.exists():
        logger.info("Loading config from %s", config_path)
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        config = WheelerConfig(**data)
    else:
        logger.info(
            "No config file at %s: using defaults",
            config_path or f"{_CONFIG_FILENAME} (searched up from {Path.cwd()})",
        )
        config = WheelerConfig()
    return _apply_env_overrides(_apply_keychain_overrides(config))


# ── Where did this setting come from? ───────────────────────────────


@dataclass(frozen=True)
class FieldSource:
    """Which layer supplied one Neo4j connection field, and what it supplied."""

    field: str
    source: str  # "env" | "keychain" | "yaml" | "default"
    origin: str  # human detail: env var name, profile, file path, "built-in"
    value: str

    @property
    def display(self) -> str:
        """The value, with secrets hidden. Safe to print."""
        from wheeler import credentials  # noqa: PLC0415 (leaf module, no cycle)

        return credentials.mask(self.field, self.value)


def _raw_yaml_neo4j(path: Path | None = None) -> tuple[Path | None, dict[str, object]]:
    """The `neo4j:` block as written in wheeler.yaml, plus the file it came from."""
    config_path = path or find_config_file()
    if config_path is None or not config_path.exists():
        return None, {}
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.debug("could not re-read %s for source reporting: %s", config_path, exc)
        return config_path, {}
    section = data.get("neo4j") if isinstance(data, dict) else None
    return config_path, section if isinstance(section, dict) else {}


def neo4j_sources(path: Path | None = None) -> list[FieldSource]:
    """Report which layer supplied each Neo4j field, in `FIELDS` order.

    With four possible sources for a URI, "where did this come from" is the first
    question anyone asks when a connection goes to the wrong host. Printed by
    `wheeler login --status`, and available to `wheeler doctor`.

    Mirrors `load_config`'s resolution exactly; `tests/test_credentials.py`
    asserts the reported values equal the loaded config's, so the two cannot
    drift apart silently.
    """
    from wheeler import credentials  # noqa: PLC0415 (leaf module, no cycle)

    config_path, yaml_neo4j = _raw_yaml_neo4j(path)
    profile = credentials.active_profile()
    record = keychain_record(profile) or {}

    rows: list[FieldSource] = []
    for field, env_var in _NEO4J_ENV_OVERRIDES.items():
        env_value = os.environ.get(env_var)
        yaml_value = yaml_neo4j.get(field)
        if env_value:
            rows.append(FieldSource(field, "env", env_var, env_value))
        elif record.get(field):
            rows.append(FieldSource(field, "keychain", f"profile '{profile}'", record[field]))
        elif isinstance(yaml_value, str):
            rows.append(FieldSource(field, "yaml", str(config_path), yaml_value))
        else:
            rows.append(FieldSource(field, "default", "built-in", _NEO4J_DEFAULTS[field]))
    return rows


def shadowed_by_env() -> list[str]:
    """Env var names that override a stored keychain credential, if any.

    The trap this exists for: a user runs `wheeler login`, the credential stores
    fine, and Wheeler still connects somewhere else because `NEO4J_URI` is
    exported in their shell profile.
    """
    if not keychain_record():
        return []
    return [
        env_var
        for field, env_var in _NEO4J_ENV_OVERRIDES.items()
        if os.environ.get(env_var) and (keychain_record() or {}).get(field)
    ]


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
