"""Tests for Wheeler core modules.

Run with: source .venv/bin/activate && python -m pytest tests/ -v
"""

from wheeler import __version__
from wheeler.config import WheelerConfig, ModelsConfig


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_string():
    assert __version__ == "0.3.9"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_has_mcp_path():
    config = WheelerConfig()
    assert config.mcp_config_path == ".mcp.json"


def test_model_per_mode_defaults():
    """Each mode should have a model configured."""
    config = WheelerConfig()
    assert config.models.chat == "sonnet"
    assert config.models.planning == "opus"
    assert config.models.writing == "opus"
    assert config.models.execute == "sonnet"


def test_model_per_mode_custom():
    """Model config should be overridable."""
    config = WheelerConfig(models=ModelsConfig(chat="haiku", execute="sonnet"))
    assert config.models.chat == "haiku"
    assert config.models.execute == "sonnet"
