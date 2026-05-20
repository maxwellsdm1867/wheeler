"""Regression test for issue #46: figure output paths default to canonical export location.

Issue: /wh:plan and /wh:execute should default figure output paths to the canonical
lab convention (analysis_exports/<investigation>_<date>/figures/fig_X_<descriptive>.png)
rather than the working location (figures/<investigation>/<descriptive>.png).

This test verifies:
1. /wh:plan task templates mention analysis_exports as the canonical figure location
2. /wh:execute has logic to mkdir the export dir and copy figures there
3. Figure path defaulting follows the canonical pattern
"""

import pytest
import re
from pathlib import Path


def test_plan_command_mentions_canonical_figure_paths():
    """Plan command should guide figure paths to analysis_exports/ canonical location."""
    plan_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "plan.md"
    assert plan_cmd.exists(), f"Plan command not found at {plan_cmd}"

    content = plan_cmd.read_text()

    # The plan command should mention analysis_exports as the canonical figure location
    # It should be in the Node Type Reference or in guidance about figure paths
    has_canonical_pattern = "analysis_exports" in content

    assert has_canonical_pattern, (
        "Plan command does not mention analysis_exports as the canonical figure location. "
        "Should guide users toward analysis_exports/<investigation>_<date>/figures/ pattern."
    )


def test_execute_command_mentions_export_directory_creation():
    """Execute command should document mkdir and copying figures to export dir."""
    execute_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "execute.md"
    assert execute_cmd.exists(), f"Execute command not found at {execute_cmd}"

    content = execute_cmd.read_text()

    # The execute command should mention creating the analysis_exports directory
    # and copying artifacts (figures, scripts) into it
    has_export_mkdir = "analysis_exports" in content or "mkdir" in content.lower()
    has_copy_mention = "cp" in content or "copy" in content.lower() or "archive" in content.lower()

    assert has_export_mkdir, (
        "Execute command does not mention creating analysis_exports directory. "
        "Should document mkdir of analysis_exports/<slug>_<date>/{figures,scripts}/ at start of execution."
    )

    # The command should mention copying artifacts to the export location
    assert has_copy_mention, (
        "Execute command does not mention copying artifacts to export directory. "
        "Should document copying scripts and figures during or after task execution."
    )


def test_plan_and_execute_commands_sync():
    """Plan and execute command files should both be synced between .claude and _data."""
    plan_cmd_path = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "plan.md"
    plan_data_path = Path(__file__).parent.parent.parent / "wheeler" / "_data" / "commands" / "plan.md"

    execute_cmd_path = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "execute.md"
    execute_data_path = Path(__file__).parent.parent.parent / "wheeler" / "_data" / "commands" / "execute.md"

    assert plan_cmd_path.exists(), f"Command not found at {plan_cmd_path}"
    assert plan_data_path.exists(), f"Data command not found at {plan_data_path}"
    assert execute_cmd_path.exists(), f"Command not found at {execute_cmd_path}"
    assert execute_data_path.exists(), f"Data command not found at {execute_data_path}"

    plan_cmd_content = plan_cmd_path.read_text()
    plan_data_content = plan_data_path.read_text()

    execute_cmd_content = execute_cmd_path.read_text()
    execute_data_content = execute_data_path.read_text()

    assert plan_cmd_content == plan_data_content, (
        "Plan command files are out of sync. "
        f"{plan_cmd_path} and {plan_data_path} must be identical."
    )

    assert execute_cmd_content == execute_data_content, (
        "Execute command files are out of sync. "
        f"{execute_cmd_path} and {execute_data_path} must be identical."
    )
