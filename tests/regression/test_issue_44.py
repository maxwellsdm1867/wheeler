"""
Regression test for issue #44: plan-based mode does not instruct AI to display anchor figures inline.

This test verifies that the /wh:execute skill includes instructions for displaying figures
registered as findings during plan execution, particularly in the plan-based execution path.
"""

import pytest


def test_execute_skill_plan_mode_includes_figure_display_instruction():
    """
    Verify that the /wh:execute skill's plan-based execution section includes
    an explicit instruction to display figures inline after each task completes.

    The issue reports that while planless-mode execution instructs the AI to
    "Display anchor figures for any Dataset or Script referenced," the plan-based
    mode (Step 2a) has no such instruction. This causes figures registered via
    ensure_artifact(artifact_type=finding) to be written to disk and registered
    in the graph but not displayed inline in chat.
    """
    from pathlib import Path

    # Read the execute.md skill file
    skill_path = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "execute.md"
    assert skill_path.exists(), f"Skill file not found at {skill_path}"

    skill_content = skill_path.read_text()

    # Check that Step 2 (plan-based execution) includes instruction to display figures
    # The instruction should be in the context of running tasks that produce findings
    assert "Step 2: Run the plan" in skill_content, "Step 2 title missing"

    # Extract the Step 2 section (from "### Step 2:" to the next "###")
    step2_start = skill_content.find("### Step 2:")
    assert step2_start != -1, "Step 2 section not found"

    step2_end = skill_content.find("\n### ", step2_start + 1)
    if step2_end == -1:
        step2_end = len(skill_content)

    step2_content = skill_content[step2_start:step2_end]

    # Verify the figure display instruction exists somewhere in Step 2
    # Key phrases to check for:
    # - "Display anchor figures" or "display...figures" (from reconvene.md)
    # - "Read the PNG" (from issue body examples)
    # - "inline" in context of figures
    # - "artifact_type=finding" reference

    figure_instruction_found = any([
        "display" in step2_content.lower() and "figure" in step2_content.lower(),
        "read the png" in step2_content.lower(),
        "anchor figure" in step2_content.lower(),
    ])

    assert figure_instruction_found, (
        "Step 2 (plan-based execution) does not include an instruction to display "
        "figures inline. The issue reports that figures registered via ensure_artifact() "
        "are created but not shown to the user unless explicitly Read or prompted for. "
        "This test would pass if the skill includes language like 'Display anchor figures' "
        "or 'Read the PNG' in the plan execution path."
    )


def test_execute_skill_both_copies_have_figure_display_instruction():
    """
    Verify that both copies of the execute.md skill (source and package) carry
    the figure display instruction in their Step 2 section.

    The CLAUDE.md mirror invariant requires `.claude/commands/wh/execute.md`
    (source) and `wheeler/_data/commands/execute.md` (packaged) to stay in
    sync. After fixing #44, both files must include the display instruction
    in plan-based execution; if a future edit drops the instruction from
    either copy, this test catches it.
    """
    from pathlib import Path

    # Read both copies
    source_skill_path = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "execute.md"
    packaged_skill_path = Path(__file__).parent.parent.parent / "wheeler" / "_data" / "commands" / "execute.md"

    assert source_skill_path.exists(), f"Source skill file not found at {source_skill_path}"
    assert packaged_skill_path.exists(), f"Packaged skill file not found at {packaged_skill_path}"

    source_content = source_skill_path.read_text()
    packaged_content = packaged_skill_path.read_text()

    # Both should have the "Step 2: Run the plan" section
    assert "Step 2: Run the plan" in source_content, "Source: Step 2 missing"
    assert "Step 2: Run the plan" in packaged_content, "Packaged: Step 2 missing"

    # Extract Step 2 sections from both
    source_step2_start = source_content.find("### Step 2:")
    packaged_step2_start = packaged_content.find("### Step 2:")

    source_step2_end = source_content.find("\n### ", source_step2_start + 1)
    if source_step2_end == -1:
        source_step2_end = len(source_content)

    packaged_step2_end = packaged_content.find("\n### ", packaged_step2_start + 1)
    if packaged_step2_end == -1:
        packaged_step2_end = len(packaged_content)

    source_step2 = source_content[source_step2_start:source_step2_end]
    packaged_step2 = packaged_content[packaged_step2_start:packaged_step2_end]

    # Both must carry the figure display instruction
    for name, text in [("Source", source_step2), ("Packaged", packaged_step2)]:
        figure_instruction_found = any([
            "display" in text.lower() and "figure" in text.lower(),
            "read the png" in text.lower(),
            "anchor figure" in text.lower(),
        ])
        assert figure_instruction_found, (
            f"{name} copy of execute.md is missing the figure display "
            f"instruction in Step 2 (plan-based execution). Both copies must "
            f"stay in sync; see #44."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
