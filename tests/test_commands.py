"""Tests for Claude Code command files in .claude/commands/wh/."""

import re
from pathlib import Path

import pytest
import yaml

COMMANDS_DIR = Path(__file__).parent.parent / ".claude" / "commands" / "wh"
EXPECTED_COMMANDS = [
    "ask",
    "chat",
    "discuss",
    "dream",
    "execute",
    "handoff",
    "ingest",
    "pair",
    "pause",
    "plan",
    "queue",
    "reconvene",
    "resume",
    "status",
    "write",
]
STALE_ROOT = Path(__file__).parent.parent / ".claude" / "commands"


def test_all_command_files_exist():
    for cmd in EXPECTED_COMMANDS:
        path = COMMANDS_DIR / f"{cmd}.md"
        assert path.exists(), f"Missing command file: {path}"


def test_no_stale_root_command_files():
    for cmd in EXPECTED_COMMANDS:
        path = STALE_ROOT / f"{cmd}.md"
        assert not path.exists(), f"Stale root command file should not exist: {path}"


def test_each_has_yaml_frontmatter():
    for cmd in EXPECTED_COMMANDS:
        path = COMMANDS_DIR / f"{cmd}.md"
        content = path.read_text()
        assert content.startswith("---"), f"{cmd}.md does not start with YAML frontmatter"
        parts = content.split("---", 2)
        # parts[0] is empty string before first ---, parts[1] is frontmatter
        frontmatter = yaml.safe_load(parts[1])
        assert "name" in frontmatter, f"{cmd}.md frontmatter missing 'name' key"
        assert frontmatter["name"].startswith("wh:"), (
            f"{cmd}.md name '{frontmatter['name']}' does not start with 'wh:'"
        )
        assert "allowed-tools" in frontmatter, (
            f"{cmd}.md frontmatter missing 'allowed-tools' key"
        )
        assert isinstance(frontmatter["allowed-tools"], list), (
            f"{cmd}.md 'allowed-tools' is not a list"
        )


def test_queue_has_arguments():
    path = COMMANDS_DIR / "queue.md"
    content = path.read_text()
    assert "$ARGUMENTS" in content, "queue.md should reference $ARGUMENTS"


# Commands that update .plans/STATE.md must have Write permission
STATE_MD_WRITERS = ["plan", "execute", "reconvene", "pause", "handoff", "init", "discuss"]


def test_state_md_writers_have_write_permission():
    for cmd in STATE_MD_WRITERS:
        path = COMMANDS_DIR / f"{cmd}.md"
        content = path.read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        tools = frontmatter["allowed-tools"]
        assert "Write" in tools, f"{cmd}.md updates STATE.md but lacks Write permission"
