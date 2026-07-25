"""Regression test for issue #83: skill/wh:asta-lit query composition guidance.

Issue: The wh:asta-lit act composes queries for Asta Paper Finder without
guidance on query format. When composed queries contain exclusion clauses
("Exclude mouse, rat...") or meta-framing ("Core papers on...", "Restrict to..."),
Paper Finder may reject them with "No rules matched for paper specification".

The act should instruct Claude to write positive topical queries only.

Steps to reproduce:
1. Read the wh:asta-lit act
2. Observe it lacks guidance on query composition rules
3. Invoke /wh:asta-lit with a request implying exclusions
4. The act composes a query with negative/meta clauses
5. Paper Finder rejects the query (v0.18.1) or performs poorly (newer versions)

Expected: The act documents positive query composition rules.
Actual: The act lacks this guidance.
"""

from __future__ import annotations

from pathlib import Path


def test_asta_lit_act_documents_positive_query_format() -> None:
    """The wh:asta-lit act should document that queries must be positive topical."""
    repo_root = Path(__file__).resolve().parents[2]
    act_path = repo_root / ".claude" / "commands" / "wh" / "asta-lit.md"

    assert act_path.exists(), f"Act file not found: {act_path}"
    act_content = act_path.read_text()

    # The act should provide guidance on query format.
    # These phrases must be SPECIFIC to the new guidance. A bare "topic" is not
    # enough: the unfixed act already said "ask the user for a topic", so that
    # substring matched on main and the assertion guarded nothing.
    has_positive_guidance = any(
        phrase in act_content.lower()
        for phrase in [
            "positive topical",
            "topical query",
            "positive query",
            "avoid exclusion",
            "avoid negative",
            "no exclusion",
            "no 'exclude'",
            "no 'restrict'",
            "no meta-framing",
            "without exclusion",
        ]
    )

    assert has_positive_guidance, (
        "The wh:asta-lit act does not document query format guidance. "
        "It should instruct Claude to write positive topical queries only, "
        "without exclusion clauses ('Exclude...'), negations, or meta-framing "
        "('Core papers on', 'Restrict to', etc.). "
        "This causes Paper Finder to reject or mishandle such queries."
    )


def test_asta_lit_act_advises_reshaping_negative_requests() -> None:
    """The wh:asta-lit act should explain how to reshape negative user requests."""
    repo_root = Path(__file__).resolve().parents[2]
    act_path = repo_root / ".claude" / "commands" / "wh" / "asta-lit.md"

    act_content = act_path.read_text()

    # The act should mention reshaping or converting negative requests to positive queries
    has_reshape_guidance = any(
        phrase in act_content.lower()
        for phrase in [
            "reshape",
            "rephrase",
            "rewrite",
            "convert",
            "instead of",
            "as a positive",
            "focus on what",
            "focus on topic",
        ]
    )

    assert has_reshape_guidance, (
        "The wh:asta-lit act does not explain how to reshape negative user requests "
        "(e.g., 'excluding mouse studies') into positive queries (e.g., 'primate parasol mechanisms'). "
        "Users cannot compose valid queries without this guidance."
    )


def test_asta_lit_act_specifies_no_exclusion_keywords() -> None:
    """The wh:asta-lit act should explicitly forbid exclusion keywords in queries."""
    repo_root = Path(__file__).resolve().parents[2]
    act_path = repo_root / ".claude" / "commands" / "wh" / "asta-lit.md"

    act_content = act_path.read_text()

    # The act should explicitly mention that exclusions are not allowed
    has_exclusion_warning = (
        "exclude" in act_content.lower() and
        ("not" in act_content.lower() or "avoid" in act_content.lower() or "do not" in act_content.lower())
    )

    assert has_exclusion_warning, (
        "The wh:asta-lit act should explicitly warn against using 'Exclude', "
        "'Avoid', or negation clauses in Paper Finder queries. "
        "Paper Finder's specification parser rejects or performs poorly on such phrasing."
    )


def test_asta_lit_data_commands_asta_lit_in_sync() -> None:
    """The shipped .claude/commands/wh/asta-lit.md and wheel/_data/commands/asta-lit.md must be identical."""
    repo_root = Path(__file__).resolve().parents[2]
    source_path = repo_root / ".claude" / "commands" / "wh" / "asta-lit.md"
    shipped_path = repo_root / "wheeler" / "_data" / "commands" / "asta-lit.md"

    assert source_path.exists(), f"Source act not found: {source_path}"
    assert shipped_path.exists(), f"Shipped act not found: {shipped_path}"

    source_content = source_path.read_text()
    shipped_content = shipped_path.read_text()

    assert source_content == shipped_content, (
        "The .claude/commands/wh/asta-lit.md and wheeler/_data/commands/asta-lit.md "
        "are out of sync. Run `python -c \"from wheeler.installer import sync_data; sync_data()\"` "
        "to regenerate the shipped version."
    )
