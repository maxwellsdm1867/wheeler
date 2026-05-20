"""Regression test for issue #41: scientific reasoning enforcement in plans.

Issue: Plans produced by /wh:plan for non-trivial scientific questions
should document scientific reasoning (foundation, method justification,
alternative comparisons, assumptions/failure modes) before approval.

The plan verification self-check should fail or warn if scientific
reasoning is missing from plans with method choices.
"""

import pytest
import re
from pathlib import Path


def test_plan_verification_includes_scientific_reasoning_check():
    """Plan verification checklist should include scientific reasoning check."""
    plan_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "plan.md"
    assert plan_cmd.exists(), f"Plan command not found at {plan_cmd}"

    content = plan_cmd.read_text()

    # The plan verification section is documented at lines ~141-152
    # It currently includes 7 checks, but none for scientific reasoning
    verification_section = content[
        content.find("### Plan verification") : content.find("### Plan lifecycle:")
    ]

    # Count the current verification items
    items = re.findall(r"^\d+\.\s+\*\*(.+?)\*\*:", verification_section, re.MULTILINE)
    assert len(items) > 0, "No verification items found"

    # Check that scientific reasoning is mentioned in verification
    # (Either as a separate item or integrated into existing items)
    has_scientific_check = any(
        "scientific" in item.lower() or "reasoning" in item.lower() for item in items
    )

    assert has_scientific_check, (
        f"Plan verification checklist does not include scientific reasoning check. "
        f"Current items: {items}"
    )


def test_plan_template_mentions_scientific_reasoning():
    """Plan template/format should guide authors to include scientific reasoning."""
    plan_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "plan.md"
    content = plan_cmd.read_text()

    # The plan format block shows what sections plans should have
    # It should mention or encourage scientific reasoning documentation
    format_section = content[content.find("### Plan format:") : content.find("### Plan format (continued):")]

    # Either the format template itself should have a scientific reasoning section,
    # or the verification should mention it as a required section
    has_reasoning_guidance = (
        "scientific" in format_section.lower() and "reasoning" in format_section.lower()
    ) or (
        "## Scientific" in content
    )

    # If not in format, it must be in verification or elsewhere
    verification_section = content[
        content.find("### Plan verification") : content.find("### Plan lifecycle:")
    ]
    has_reasoning_in_verification = "scientific" in verification_section.lower() or "reasoning" in verification_section.lower()

    assert has_reasoning_guidance or has_reasoning_in_verification, (
        "Plan format and verification do not guide authors to document scientific reasoning. "
        "Should be either: (1) in the template format as a section, or (2) in the verification checklist"
    )


def test_plan_file_format_matches_command_doc():
    """Verify .plans files and command doc stay in sync."""
    plan_cmd_path = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "plan.md"
    data_cmd_path = Path(__file__).parent.parent.parent / "wheeler" / "_data" / "commands" / "plan.md"

    assert plan_cmd_path.exists(), f"Command not found at {plan_cmd_path}"
    assert data_cmd_path.exists(), f"Data command not found at {data_cmd_path}"

    # Both should be identical (per CLAUDE.md requirement)
    cmd_content = plan_cmd_path.read_text()
    data_content = data_cmd_path.read_text()

    assert cmd_content == data_content, (
        "Plan command files are out of sync. "
        f"{plan_cmd_path} and {data_cmd_path} must be identical."
    )
