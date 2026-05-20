"""Regression test for issue #45: workflow to flag Findings reframed by follow-up traces.

Issue: When a newer Finding reframes an older Finding (e.g., Finding B RELEVANT_TO
Finding A where B contains new framing), there is no automated workflow to flag or
handle the older Finding's stale description. This test verifies that EITHER:
  (a) /wh:dream includes framing-divergence detection, OR
  (b) a new skill /wh:revise-finding exists, OR
  (c) appropriate graph schema (REFRAMED_BY/SUPERSEDED_BY) and tools are available.
"""

import pytest
from pathlib import Path
import re


def test_wh_dream_has_framing_divergence_detection():
    """Verify /wh:dream includes framing divergence detection step.

    Specifically looking for detection that when Finding B is RELEVANT_TO
    Finding A, and B's description reframes A's description, A is flagged
    for revision. This should appear in Phase 2 or Phase 3.
    """
    dream_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "dream.md"
    assert dream_cmd.exists(), f"Dream command not found at {dream_cmd}"

    content = dream_cmd.read_text()

    # Look for specific mentions of:
    # - "framing divergence" or "framing-divergence"
    # - "divergence between linked Findings"
    # - "reframed" in context of Findings
    # - "semantic divergence" of descriptions
    # - "RELEVANT_TO" paired with description analysis
    # - Explicit mention of handling reframed Findings
    has_framing_detection = any([
        "framing divergence" in content.lower() or "framing-divergence" in content.lower(),
        "reframed" in content.lower() and "finding" in content.lower(),
        "divergence" in content.lower() and "linked" in content.lower() and "finding" in content.lower(),
        ("semantic" in content.lower() and "divergence" in content.lower()),
        ("new finding" in content.lower() and "reframe" in content.lower()),
        ("RELEVANT_TO" in content and "description" in content and ("divergence" in content.lower() or "reframe" in content.lower())),
    ])

    assert has_framing_detection, (
        "Dream command does not implement framing divergence detection. "
        "No phase exists to flag or handle Findings reframed by newer RELEVANT_TO traces. "
        "Issue #45 requires: When Finding B is RELEVANT_TO Finding A and B's description "
        "contains different framing than A, flag A for revision."
    )


def test_wh_revise_finding_skill_exists():
    """Verify /wh:revise-finding skill exists as alternative to dream detection."""
    revise_finding_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "revise-finding.md"

    # This is OK to not exist IF dream detection is present
    # But if neither exists, the test should fail
    dream_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "dream.md"
    dream_content = dream_cmd.read_text()

    has_dream_detection = any([
        "framing divergence" in dream_content.lower() or "framing-divergence" in dream_content.lower(),
        "reframed" in dream_content.lower() and "finding" in dream_content.lower(),
        "divergence" in dream_content.lower() and "linked" in dream_content.lower() and "finding" in dream_content.lower(),
    ])

    # At least one of these must be true:
    # (a) /wh:dream has framing detection, OR
    # (b) /wh:revise-finding skill exists
    assert has_dream_detection or revise_finding_cmd.exists(), (
        "Neither /wh:dream framing detection nor /wh:revise-finding skill exists. "
        "Issue #45 requires at least one workflow to handle reframed Findings."
    )


def test_graph_schema_has_reframing_relationships():
    """Verify graph schema supports reframing relationships if needed."""
    schema_file = Path(__file__).parent.parent.parent / "wheeler" / "graph" / "schema.py"
    assert schema_file.exists(), f"Schema file not found at {schema_file}"

    content = schema_file.read_text()

    # Look for relationship type definitions
    # Should have either REFRAMED_BY, SUPERSEDED_BY, or rely on RELEVANT_TO
    allowed_rels = [
        "REFRAMED_BY",
        "SUPERSEDED_BY",
        "RELEVANT_TO",  # existing fallback
    ]

    # At minimum, RELEVANT_TO should be defined (it already is)
    has_relevant_to = "RELEVANT_TO" in content

    assert has_relevant_to, (
        "Graph schema missing RELEVANT_TO relationship. "
        "Cannot link reframed Findings without this."
    )

    # Check if extended relationships for clarity exist
    has_reframing_rel = any(rel in content for rel in ["REFRAMED_BY", "SUPERSEDED_BY"])

    # The test doesn't fail if these are missing, but notes for improvement
    if not has_reframing_rel:
        # This is informational; it's acceptable to use RELEVANT_TO
        # as long as the workflow properly detects and handles it
        pass


def test_dream_file_format_matches_data_dir():
    """Verify dream command file parity between repo and data dir."""
    repo_dream = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "dream.md"
    data_dream = Path(__file__).parent.parent.parent / "wheeler" / "_data" / "commands" / "dream.md"

    assert repo_dream.exists(), f"Repo dream command not found at {repo_dream}"
    assert data_dream.exists(), f"Data dream command not found at {data_dream}"

    repo_content = repo_dream.read_text()
    data_content = data_dream.read_text()

    assert repo_content == data_content, (
        "Dream command files are out of sync. "
        f"{repo_dream} and {data_dream} must be identical."
    )


def test_issue_45_workflow_exists():
    """Integration test: verify at least ONE workflow exists to handle reframed Findings."""
    dream_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "dream.md"
    revise_finding_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "revise-finding.md"

    dream_content = dream_cmd.read_text()

    # Check for framing detection in /wh:dream (specific to reframed Findings)
    has_dream_framing_detection = any([
        "framing divergence" in dream_content.lower() or "framing-divergence" in dream_content.lower(),
        "reframed" in dream_content.lower() and "finding" in dream_content.lower(),
        ("RELEVANT_TO" in dream_content and "divergence" in dream_content.lower() and "description" in dream_content.lower()),
    ])

    # Check if /wh:revise-finding exists
    has_revise_skill = revise_finding_cmd.exists()

    # At least ONE must be present
    assert has_dream_framing_detection or has_revise_skill, (
        "Issue #45: No workflow exists to flag earlier Findings reframed by follow-up traces. "
        "Neither /wh:dream framing-divergence detection nor /wh:revise-finding skill is available. "
        "Expected: (a) /wh:dream adds phase to detect when Finding B RELEVANT_TO A "
        "with different framing, and surfaces A for revision, OR "
        "(b) new skill /wh:revise-finding guides manual revision workflow."
    )
