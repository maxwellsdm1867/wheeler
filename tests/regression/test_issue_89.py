"""Regression test for issue #89: llmsr-discover preflight hard-codes one failure cause.

Issue: The /wh:llmsr-discover act's preflight step 1 reads:

    "Confirm the tool is installed: `wheeler llmsr --help`. If it fails, say
     LLM-SR is not available (it needs the `scipy` extra) and stop."

That attributes every preflight failure to a missing scipy extra. In practice the
command can fail because the `llmsr` subcommand is absent from the installed build
while scipy is present, in which case the act tells the scientist a wrong cause and
points them at an irrelevant fix.

This is a defect in the act text itself, verifiable by reading the file. It does not
require the command to be failing on this machine: the act prescribes the wrong
diagnosis unconditionally.

Expected: the preflight branches on the observed error before naming a cause.
Actual: a single hard-coded cause.
"""

from __future__ import annotations

from pathlib import Path

ACT_RELPATH = (".claude", "commands", "wh", "llmsr-discover.md")
MIRROR_RELPATH = ("wheeler", "_data", "commands", "llmsr-discover.md")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _act_text() -> str:
    act_path = _repo_root().joinpath(*ACT_RELPATH)
    assert act_path.exists(), f"Act file not found: {act_path}"
    return act_path.read_text()


def test_preflight_distinguishes_missing_subcommand_from_missing_scipy() -> None:
    """The preflight must name the missing-subcommand case, not just the scipy extra."""
    act_content = _act_text().lower()

    mentions_missing_command = any(
        phrase in act_content
        for phrase in [
            "no such command",
            "not include the llm-sr",
            "does not include the llmsr",
            "cli engine is absent",
            "engine is not present",
            "subcommand is absent",
            "subcommand is missing",
        ]
    )

    assert mentions_missing_command, (
        "The /wh:llmsr-discover preflight does not describe the missing-subcommand "
        "failure mode. When `wheeler llmsr --help` fails with \"No such command 'llmsr'\", "
        "the act should report that the installed Wheeler build does not include the "
        "LLM-SR CLI engine, rather than blaming the scipy extra."
    )


def test_preflight_does_not_hardcode_scipy_as_the_only_cause() -> None:
    """The scipy extra must be presented as one branch, not the sole explanation."""
    act_content = _act_text().lower()

    if "scipy" not in act_content:
        return  # scipy no longer named at all: cannot be hard-coded as the only cause

    branches_on_observed_error = any(
        phrase in act_content
        for phrase in [
            "modulenotfounderror",
            "import error",
            "importerror",
            "if the error",
            "depending on the error",
            "based on the error",
            "which error",
            "distinguish",
        ]
    )

    assert branches_on_observed_error, (
        "The /wh:llmsr-discover preflight names the scipy extra without branching on "
        "the observed error. It should distinguish a missing subcommand "
        "(\"No such command 'llmsr'\") from a genuine scipy import failure "
        "(ModuleNotFoundError) and report whichever actually occurred."
    )


def test_llmsr_discover_act_mirror_in_sync() -> None:
    """The dev act and the shipped package mirror must stay byte-identical."""
    source_path = _repo_root().joinpath(*ACT_RELPATH)
    shipped_path = _repo_root().joinpath(*MIRROR_RELPATH)

    assert source_path.exists(), f"Source act not found: {source_path}"
    assert shipped_path.exists(), f"Shipped act not found: {shipped_path}"

    assert source_path.read_text() == shipped_path.read_text(), (
        ".claude/commands/wh/llmsr-discover.md and "
        "wheeler/_data/commands/llmsr-discover.md are out of sync. Run "
        '`python -c "from wheeler.installer import sync_data; sync_data()"` '
        "to regenerate the shipped version."
    )
