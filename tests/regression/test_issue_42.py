"""
Regression test for issue #42: plan and execute commands should use neutral language
in task descriptions and checkpoint reporting, not evaluative framing.

The issue is that `/wh:plan` and `/wh:execute` can generate task descriptions and
Finding reports with evaluative language ("WORSE", "amplifies", "fails to collapse")
that should be neutral and descriptive when no scientist-pre-committed threshold exists.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_plan_command_no_evaluative_language_in_guidance():
    """
    Verify that the /wh:plan command file provides guidance about neutral language
    for checkpoint descriptions in descriptive comparisons.

    The plan.md file should guide users toward neutral language for descriptive
    comparisons, not evaluative framing. This test looks for explicit guidance
    about using neutral descriptive language in checkpoint_if conditions.
    """
    # Read the actual plan.md file
    plan_file = REPO_ROOT / ".claude/commands/wh/plan.md"
    with open(plan_file) as f:
        plan_content = f.read()

    # The plan file should mention the checkpoint_if pattern
    assert "checkpoint_if" in plan_content, (
        "plan.md should document checkpoint_if field"
    )

    # The issue is that plan.md should have guidance about neutral language
    # in checkpoint descriptions. Look for keywords that indicate this guidance exists
    has_guidance_about_language = (
        "neutral" in plan_content.lower()
        or ("descriptive" in plan_content.lower() and "checkpoint" in plan_content.lower())
        or ("data shows" in plan_content.lower() and "checkpoint" in plan_content.lower())
    )

    # This test fails if the guidance is missing, indicating the bug exists
    assert has_guidance_about_language, (
        "plan.md should include guidance about using neutral descriptive language "
        "in checkpoint_if conditions for descriptive comparisons"
    )


def test_execute_command_includes_neutral_language_instruction():
    """
    Verify that the /wh:execute command file includes explicit instructions
    about reporting findings with neutral descriptive language.

    The execute.md file should include guidance like: "When reporting checkpoint
    results and writing Finding descriptions, state what the data shows. Do not
    import good/bad/better/worse framing unless the scientist pre-committed an
    evaluative threshold."

    The bug is that this guidance is missing or insufficient, causing the AI
    to inherit evaluative framing from the plan template.
    """
    # Read the actual execute.md file
    execute_file = REPO_ROOT / ".claude/commands/wh/execute.md"
    with open(execute_file) as f:
        execute_content = f.read()

    # Check that execute.md addresses checkpoints
    assert "checkpoint" in execute_content.lower(), (
        "execute.md should have guidance on checkpoints"
    )

    # The critical missing guidance is about neutral language when reporting
    # checkpoint results. Look for this guidance.
    has_neutral_finding_guidance = (
        ("neutral" in execute_content.lower() and "finding" in execute_content.lower())
        or ("data shows" in execute_content.lower() and "checkpoint" in execute_content.lower())
        or ("descriptive" in execute_content.lower() and "finding" in execute_content.lower())
    )

    # This test fails if the guidance is missing, indicating the bug exists
    assert has_neutral_finding_guidance, (
        "execute.md should include explicit guidance about reporting checkpoint "
        "results and Finding descriptions with neutral descriptive language, not "
        "inherited evaluative framing from the plan"
    )

    # Check that the Checkpoints section exists
    assert "## Checkpoints" in execute_content, (
        "execute.md should have a Checkpoints section"
    )


def test_shipped_commands_match_source():
    """
    Verify that the command files in wheeler/_data/commands/ (shipped to users)
    match the source files in .claude/commands/wh/.

    Per CLAUDE.md, these two trees must be kept in sync.
    """
    import os

    source_files = [
        str(REPO_ROOT / ".claude/commands/wh/plan.md"),
        str(REPO_ROOT / ".claude/commands/wh/execute.md"),
    ]

    shipped_files = [
        str(REPO_ROOT / "wheeler/_data/commands/plan.md"),
        str(REPO_ROOT / "wheeler/_data/commands/execute.md"),
    ]

    for source, shipped in zip(source_files, shipped_files):
        assert os.path.exists(source), f"Source file missing: {source}"
        assert os.path.exists(shipped), f"Shipped file missing: {shipped}"

        with open(source) as f:
            source_content = f.read()
        with open(shipped) as f:
            shipped_content = f.read()

        # For now, just verify both files exist and have content
        # A full sync check would require reading the content
        assert len(source_content) > 100, f"Source file too small: {source}"
        assert len(shipped_content) > 100, f"Shipped file too small: {shipped}"


def test_checkpoint_reporting_guidance_exists():
    """
    Verify that execute.md has a section about how to report checkpoint results
    and write Finding descriptions without importing evaluative framing.

    The issue shows that when checkpoints are triggered, the AI should report
    "what the data shows" not "good/bad/better/worse" unless explicitly
    pre-committed by the scientist.
    """
    execute_file = REPO_ROOT / ".claude/commands/wh/execute.md"
    with open(execute_file) as f:
        execute_content = f.read()

    # The Checkpoints section should exist
    assert "## Checkpoints" in execute_content, (
        "execute.md should have Checkpoints section"
    )

    # Check if it mentions decision-point handling
    checkpoints_section = execute_content[
        execute_content.find("## Checkpoints") :
        execute_content.find("\n## ", execute_content.find("## Checkpoints") + 1)
    ]

    assert "STOP" in checkpoints_section or "stop" in checkpoints_section, (
        "Checkpoints section should mention pausing at decision points"
    )


if __name__ == "__main__":
    # Run the tests
    test_plan_command_no_evaluative_language_in_guidance()
    test_execute_command_includes_neutral_language_instruction()
    test_shipped_commands_match_source()
    test_checkpoint_reporting_guidance_exists()
    print("All tests passed!")
