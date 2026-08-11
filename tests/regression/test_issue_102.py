"""Regression test for issue #102: config resolution from subdirectories.

Config loader should find wheeler.yaml by walking up parent directories,
not just looking at cwd.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from wheeler.config import load_config, find_config_file, find_project_root


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _isolate_config_layers(monkeypatch):
    """Make wheeler.yaml the winning layer for the duration of these tests.

    load_config resolves in the order env > keychain > yaml > defaults. These
    tests assert that the file layer is found from a subdirectory, so a stray
    NEO4J_* var or a real `wheeler login` keychain entry on the dev machine
    would override the value under test and fail the assertion for a reason
    unrelated to config discovery.
    """
    for var in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("WHEELER_PROJECT_ROOT", raising=False)
    monkeypatch.setattr(
        "wheeler.config._apply_keychain_overrides",
        lambda config, raw_neo4j=None: config,
    )


@pytest.fixture
def project_with_config():
    """Create a temporary project directory with wheeler.yaml and a subdirectory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        config_file = project_root / "wheeler.yaml"

        config_data = {
            "neo4j": {
                "uri": "bolt://custom.example.com:7687",
                "username": "custom_user",
                "password": "custom_test_password",
                "database": "custom_db",
            }
        }
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        subdir = project_root / ".wheeler" / "asta-assistant" / "test-mission"
        subdir.mkdir(parents=True, exist_ok=True)

        yield project_root, subdir


def test_find_project_root_from_subdirectory(project_with_config):
    """find_project_root should walk up from a subdirectory to find the root."""
    project_root, subdir = project_with_config

    original_cwd = os.getcwd()
    try:
        os.chdir(subdir)
        found_root = find_project_root()
        assert found_root.resolve() == project_root.resolve()
    finally:
        os.chdir(original_cwd)


def test_find_config_file_from_subdirectory(project_with_config):
    """find_config_file should locate wheeler.yaml by walking up from a subdirectory."""
    project_root, subdir = project_with_config
    config_file = project_root / "wheeler.yaml"

    original_cwd = os.getcwd()
    try:
        os.chdir(subdir)
        found_config = find_config_file()
        assert found_config is not None
        assert found_config.resolve() == config_file.resolve()
        assert found_config.exists()
    finally:
        os.chdir(original_cwd)


def test_load_config_from_subdirectory_reads_parent_config(project_with_config):
    """load_config should read the parent directory's wheeler.yaml when called from a subdirectory."""
    project_root, subdir = project_with_config
    config_file = project_root / "wheeler.yaml"

    original_cwd = os.getcwd()
    try:
        os.chdir(subdir)
        config = load_config()

        assert config.neo4j.uri == "bolt://custom.example.com:7687"
        assert config.neo4j.username == "custom_user"
        assert config.neo4j.password == "custom_test_password"
        assert config.neo4j.database == "custom_db"
    finally:
        os.chdir(original_cwd)


def test_load_config_subprocess_from_subdirectory(project_with_config):
    """Simulate MCP server: verify subprocess inheriting cwd loads parent config correctly."""
    import subprocess
    import sys
    import json

    project_root, subdir = project_with_config

    # The keychain outranks wheeler.yaml, and this runs in a fresh interpreter
    # where the parent's fixture patch does not apply, so neutralize it here as
    # well. Otherwise a real `wheeler login` entry on the dev machine decides
    # the assertion instead of the config file under test.
    script = """
import json
import wheeler.config as wc
wc._apply_keychain_overrides = lambda config, raw_neo4j=None: config
c = wc.load_config()
print(json.dumps({
    'uri': c.neo4j.uri,
    'username': c.neo4j.username,
    'password': c.neo4j.password,
    'database': c.neo4j.database,
}))
"""

    # PYTHONPATH is mandatory, not defensive. The shared venv installs wheeler
    # editable against the MAIN checkout, and cwd here is a temp dir, so cwd
    # precedence cannot help: without this the subprocess would import the main
    # checkout's wheeler and this test would report on the wrong tree.
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
        "WHEELER_SUBPROCESS_PROBE": "1",
    }
    for var in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"):
        env.pop(var, None)

    original_cwd = os.getcwd()
    try:
        os.chdir(subdir)
        origin = subprocess.run(
            [sys.executable, "-c", "import wheeler, os; print(os.path.dirname(wheeler.__file__))"],
            capture_output=True,
            text=True,
            cwd=str(subdir),
            env=env,
        )
        assert origin.returncode == 0, f"Import probe failed: {origin.stderr}"
        assert Path(origin.stdout.strip()) == REPO_ROOT / "wheeler", (
            "Subprocess imported the wrong wheeler package, so its result would "
            f"describe another tree. Expected {REPO_ROOT / 'wheeler'}, got {origin.stdout.strip()}"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(subdir),
            env=env,
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        data = json.loads(result.stdout.strip())

        assert data["uri"] == "bolt://custom.example.com:7687"
        assert data["username"] == "custom_user"
        assert data["password"] == "custom_test_password"
        assert data["database"] == "custom_db"
    finally:
        os.chdir(original_cwd)


def test_load_config_deep_subdirectory(project_with_config):
    """Test loading config from multiple levels deep in subdirectory tree."""
    project_root, _ = project_with_config

    deep_subdir = project_root / ".wheeler" / "level1" / "level2" / "level3"
    deep_subdir.mkdir(parents=True, exist_ok=True)

    original_cwd = os.getcwd()
    try:
        os.chdir(deep_subdir)
        config = load_config()

        assert config.neo4j.password == "custom_test_password"
        assert config.neo4j.database == "custom_db"
    finally:
        os.chdir(original_cwd)
