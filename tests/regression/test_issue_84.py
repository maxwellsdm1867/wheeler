"""Regression test for issue #84: wh:asta-theorize command template.

Issue: The documented asta CLI command in the wh:asta-theorize act
uses an outdated interface (pre-v0.18.1) with positional question
argument and -o output flag. Asta v0.18.1 requires --theory-query
(required), --mission-statement (optional), and outputs to stdout.

The test verifies the act's command template has been updated
to match the current asta CLI interface.
"""

from __future__ import annotations

from pathlib import Path


def test_asta_theorize_command_uses_theory_query_flag():
    """Verify the wh:asta-theorize act uses --theory-query, not positional question."""
    repo_root = Path(__file__).resolve().parents[2]
    act_file = repo_root / ".claude" / "commands" / "wh" / "asta-theorize.md"

    assert act_file.exists(), f"Act file not found: {act_file}"

    content = act_file.read_text()

    # The documented command must use --theory-query, not a positional argument.
    # Positional form (wrong): asta generate-theories literature-theory-generation "$QUESTION"
    # Flag form (correct): asta generate-theories literature-theory-generation --theory-query "$QUESTION"

    assert (
        "--theory-query" in content
    ), (
        "Act does not document --theory-query flag. "
        "The asta v0.18.1 CLI requires --theory-query (required parameter). "
        "See issue #84 for details."
    )

    # The documented command must NOT use the -o flag (removed in v0.18.1).
    # The old (wrong) form: asta generate-theories ... "$QUESTION" -o /tmp/asta-theorizer.json
    # The new (correct) form: asta generate-theories ... --theory-query ... > /tmp/asta-theorizer.json
    #
    # Note: We check for the specific pattern of the old command:
    # "generate-theories literature-theory-generation" followed by quotes and then "-o"
    # to catch the documented shell command, not just any mention of "-o" elsewhere.

    lines = content.split("\n")
    command_lines = [
        line
        for line in lines
        if "generate-theories" in line and "literature-theory-generation" in line
    ]

    assert len(command_lines) > 0, (
        "No asta generate-theories command found in act. "
        "The act should document how to invoke the theorizer CLI."
    )

    # Check that the documented command(s) do NOT use "-o" in the shell invocation.
    # This is the marker of the old, broken interface.
    for line in command_lines:
        # Skip comment lines
        if line.strip().startswith("#"):
            continue

        # The line should not contain both "generate-theories" and "-o" together,
        # which would indicate the old interface.
        # However, "-o" might appear in comments or in different contexts,
        # so we look for the specific pattern: a command that runs asta with -o.
        #
        # Heuristic: if the line looks like a shell command (contains "asta" and
        # command args) and contains "-o", it's likely the old command.
        if "asta" in line and "-o" in line:
            # The new interface redirects to stdout: > /tmp/asta-theorizer.json
            # The old interface used -o: -o /tmp/asta-theorizer.json
            # Both have the output path, but only the old one has "-o" flag.
            if not "> " in line:
                # If there's no stdout redirect (>), then -o is being used as a flag,
                # which is wrong.
                assert (
                    False
                ), (
                    f"Act command uses '-o' flag (old interface): {line.strip()}\n"
                    "Asta v0.18.1 does not support the '-o' flag. "
                    "Use stdout redirection (>) instead. "
                    "See issue #84."
                )


def test_asta_theorize_command_documents_mission_statement():
    """Verify the wh:asta-theorize act mentions --mission-statement (scope parameter)."""
    repo_root = Path(__file__).resolve().parents[2]
    act_file = repo_root / ".claude" / "commands" / "wh" / "asta-theorize.md"

    assert act_file.exists(), f"Act file not found: {act_file}"

    content = act_file.read_text()

    # The act should document --mission-statement as the way to pass constraints/scope.
    # This is an optional parameter in asta v0.18.1.
    assert "--mission-statement" in content, (
        "Act does not document --mission-statement parameter. "
        "Asta v0.18.1 supports --mission-statement for scope/constraints. "
        "See issue #84."
    )
