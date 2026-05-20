"""Regression test for issue #43: wheeler-researcher profile missing Write tools.

Issue: The wheeler-researcher subagent profile lacks Write and Edit tools,
preventing it from saving research notes to disk. This forces the agent to
return content inline and ask the parent to save it, breaking provenance
and wasting tokens.

Expected: wheeler-researcher should have Write and Edit in allowed-tools.
"""

import pytest
import yaml
from pathlib import Path


def test_wheeler_researcher_profile_has_write_tools():
    """Wheeler-researcher agent should be able to write files."""
    agent_path = Path(__file__).parent.parent.parent / ".claude" / "agents" / "wheeler-researcher.md"
    assert agent_path.exists(), f"Agent profile not found at {agent_path}"

    content = agent_path.read_text()

    # Extract YAML frontmatter
    lines = content.split("\n")
    assert lines[0] == "---", "Agent profile should start with YAML frontmatter"

    # Find the closing ---
    yaml_end = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            yaml_end = i
            break

    assert yaml_end is not None, "Agent profile should have closing --- for YAML"

    yaml_content = "\n".join(lines[1:yaml_end])
    frontmatter = yaml.safe_load(yaml_content)

    assert frontmatter is not None, "Failed to parse YAML frontmatter"
    assert "allowed-tools" in frontmatter, "Agent profile missing 'allowed-tools' key"

    allowed_tools = frontmatter["allowed-tools"]
    assert isinstance(allowed_tools, list), "allowed-tools should be a list"

    # Check that Write tool is available
    has_write = "Write" in allowed_tools
    assert has_write, (
        f"wheeler-researcher missing 'Write' tool. "
        f"Current allowed-tools: {allowed_tools}"
    )

    # Check that Edit tool is available
    has_edit = "Edit" in allowed_tools
    assert has_edit, (
        f"wheeler-researcher missing 'Edit' tool. "
        f"Current allowed-tools: {allowed_tools}"
    )


def test_wheeler_researcher_system_prompt_reflects_write_capability():
    """If agent has Write tools, system prompt should acknowledge it."""
    agent_path = Path(__file__).parent.parent.parent / ".claude" / "agents" / "wheeler-researcher.md"
    content = agent_path.read_text()

    # Extract the markdown body (after the closing ---)
    lines = content.split("\n")
    yaml_end = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            yaml_end = i
            break

    markdown_body = "\n".join(lines[yaml_end + 1 :])

    # Extract frontmatter to check for Write tool
    yaml_content = "\n".join(lines[1:yaml_end])
    frontmatter = yaml.safe_load(yaml_content)
    allowed_tools = frontmatter.get("allowed-tools", [])
    has_write = "Write" in allowed_tools

    # If Write is in allowed-tools, the system prompt should NOT say "cannot write"
    if has_write:
        assert "NO file writing" not in markdown_body and "cannot write" not in markdown_body.lower(), (
            "System prompt claims agent cannot write files, but Write tool is in allowed-tools. "
            "Update the system prompt to reflect write capability."
        )


def test_agent_profile_mirrored_in_data_dir():
    """Agent profile should be mirrored in wheeler/_data/agents/."""
    agent_path = Path(__file__).parent.parent.parent / ".claude" / "agents" / "wheeler-researcher.md"
    data_path = Path(__file__).parent.parent.parent / "wheeler" / "_data" / "agents" / "wheeler-researcher.md"

    assert agent_path.exists(), f"Agent profile not found at {agent_path}"
    assert data_path.exists(), f"Agent data file not found at {data_path}"

    # Both should be identical (per CLAUDE.md requirement)
    agent_content = agent_path.read_text()
    data_content = data_path.read_text()

    assert agent_content == data_content, (
        "wheeler-researcher agent files are out of sync. "
        f"{agent_path} and {data_path} must be identical."
    )
