"""Regression test for issue #99: asta-assistant seed README presents /goal and /loop as composable.

The seed move writes a README template and a hand-off block that present the two commands
on consecutive lines, inviting the scientist to append text, which makes them read as one
composable instruction. A single input beginning with /goal captures everything that follows,
including the /loop line, preventing the loop from running.

The fix requires:
  1. Separate /goal and /loop visually (e.g., blank line or distinct sections).
  2. Explicitly state they are two separate prompts and why (combined paste is captured by
     /goal's condition).
  3. Goal condition must name "assessment" so a skipped review cannot satisfy it.
  4. README must include a mid-run check (e.g., grep for ## Assessment sections).
"""

from __future__ import annotations

import re
from pathlib import Path


def test_asta_assistant_act_readme_template_separates_commands() -> None:
    """Verify Step 4 README template separates /goal and /loop."""
    act_path = Path(__file__).resolve().parents[2] / ".claude/commands/wh/asta-assistant.md"
    content = act_path.read_text()

    # Extract the README template section (between "## Write `README.md`" or similar and the next heading).
    # The issue shows lines 79-91 contain the defective README template.
    assert act_path.exists(), f"Act file not found: {act_path}"

    # Find the README template block (Step 4)
    readme_start = content.find("# <slug> - Asta research mission")
    assert readme_start > 0, "README template not found in act"

    # Extract a reasonable chunk to analyze (up to the next major section)
    section_end = content.find("## ", readme_start + 10)
    readme_section = content[readme_start:section_end]

    # The defect: /goal and /loop are on consecutive lines
    lines = readme_section.split("\n")

    # Find the lines with /goal and /loop
    goal_line_idx = None
    loop_line_idx = None
    for i, line in enumerate(lines):
        if "/goal" in line and "work items" in line:
            goal_line_idx = i
        elif "/loop" in line and "asta-assistant:run" in line:
            loop_line_idx = i

    assert goal_line_idx is not None, "/goal line not found in README template"
    assert loop_line_idx is not None, "/loop line not found in README template"

    # The bug: /loop is immediately after /goal (no blank lines between)
    # The fix: there MUST be at least one blank line OR they must be in separate sections
    lines_between = loop_line_idx - goal_line_idx

    # On main (defective), they are on consecutive lines: lines_between == 1
    # After fix, there should be at least 2 blank lines or different sections: lines_between > 1
    assert (
        lines_between > 1
    ), f"Step 4 README: /goal and /loop are on consecutive or nearly consecutive lines "
    f"({goal_line_idx} and {loop_line_idx}). Must be separated by at least a blank line "
    f"to indicate they are two separate prompts."

    # Verify the section contains explicit text stating they are separate
    has_separate_prompts_text = (
        "separate prompt" in readme_section.lower()
        or "two separate" in readme_section.lower()
        or "entered as two" in readme_section.lower()
        or "one per prompt" in readme_section.lower()
    )
    assert (
        has_separate_prompts_text
    ), "Step 4 README must explicitly state the two commands must be entered as separate prompts"

    # Verify goal condition includes "assessment"
    has_assessment = "assessment" in readme_section.lower()
    assert (
        has_assessment
    ), "Step 4 README goal condition must name 'assessment' so skipping review cannot satisfy it"


def test_asta_assistant_act_handoff_block_separates_commands() -> None:
    """Verify Step 6 hand-off block separates /goal and /loop."""
    act_path = Path(__file__).resolve().parents[2] / ".claude/commands/wh/asta-assistant.md"
    content = act_path.read_text()

    # Find the hand-off block (Step 6)
    handoff_start = content.find("6. **Hand off.**")
    assert handoff_start > 0, "Hand-off section not found in act"

    # Extract the block (up to the next major section, line with leading digits)
    section_end = content.find("\n## ", handoff_start + 10)
    if section_end < 0:
        section_end = len(content)
    handoff_section = content[handoff_start:section_end]

    # Find the code block containing the commands
    code_block_match = re.search(r"```.*?```", handoff_section, re.DOTALL)
    assert code_block_match, "No code block found in hand-off section"
    code_block = code_block_match.group(0)

    lines = code_block.split("\n")

    # Find the lines with /goal and /loop
    goal_line_idx = None
    loop_line_idx = None
    for i, line in enumerate(lines):
        if "/goal" in line:
            goal_line_idx = i
        elif "/loop" in line:
            loop_line_idx = i

    assert goal_line_idx is not None, "/goal line not found in hand-off code block"
    assert loop_line_idx is not None, "/loop line not found in hand-off code block"

    # The bug: /loop is immediately after /goal
    # The fix: there MUST be at least one blank line between them
    lines_between = loop_line_idx - goal_line_idx
    assert (
        lines_between > 1
    ), f"Step 6 hand-off: /goal and /loop are on consecutive lines ({goal_line_idx} and {loop_line_idx}). "
    f"Must be on separate prompts, indicated by blank line or separate code blocks."


def test_asta_assistant_handoff_includes_warning_about_combined_input() -> None:
    """Verify hand-off section warns what happens if /goal and /loop are combined."""
    act_path = Path(__file__).resolve().parents[2] / ".claude/commands/wh/asta-assistant.md"
    content = act_path.read_text()

    # Find the hand-off section
    handoff_start = content.find("6. **Hand off.**")
    assert handoff_start > 0, "Hand-off section not found in act"

    section_end = content.find("\n## ", handoff_start + 10)
    if section_end < 0:
        section_end = len(content)
    handoff_section = content[handoff_start:section_end]

    # The fix should explicitly warn what happens with a combined input
    has_warning = (
        "separate prompt" in handoff_section.lower()
        or "two separate" in handoff_section.lower()
        or "condition" in handoff_section.lower()
        or "captured" in handoff_section.lower()
    )
    assert (
        has_warning
    ), "Hand-off section must warn that /goal and /loop must be separate prompts and explain the consequence of combining them"


def test_asta_assistant_readme_includes_midrun_check() -> None:
    """Verify Step 4 README includes a mid-run check for assessment sections."""
    act_path = Path(__file__).resolve().parents[2] / ".claude/commands/wh/asta-assistant.md"
    content = act_path.read_text()

    # Find the README template section
    readme_start = content.find("# <slug> - Asta research mission")
    assert readme_start > 0, "README template not found in act"

    section_end = content.find("## ", readme_start + 10)
    readme_section = content[readme_start:section_end]

    # The fix requires a mid-run check like: grep -l "## Assessment" work/*/README.md
    has_check = (
        "grep" in readme_section.lower()
        and ("assessment" in readme_section.lower() or "progress" in readme_section.lower())
    ) or ("check" in readme_section.lower() and "assessment" in readme_section.lower())

    assert (
        has_check
    ), "Step 4 README must include a mid-run check (e.g., grep for ## Assessment sections)"


def test_both_act_trees_in_sync() -> None:
    """Verify the act file and its shipped mirror are identical."""
    act_path = Path(__file__).resolve().parents[2] / ".claude/commands/wh/asta-assistant.md"
    mirror_path = (
        Path(__file__).resolve().parents[2] / "wheeler/_data/commands/asta-assistant.md"
    )

    assert act_path.exists(), f"Act file not found: {act_path}"
    assert mirror_path.exists(), f"Mirror file not found: {mirror_path}"

    act_content = act_path.read_text()
    mirror_content = mirror_path.read_text()

    assert (
        act_content == mirror_content
    ), "Act and mirror files must be byte-identical. Run: python -c \"from wheeler.installer import sync_data; sync_data()\""
