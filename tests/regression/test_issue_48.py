"""Regression test for issue #48: figure/dataset filenames should embed analysis_name and date prefix.

Issue: When /wh:plan produces figures and datasets, the filenames should include
the analysis name and date prefix so they remain identifiable when detached from
their parent directory. Currently, filenames are just slugs (fig_F_theta0.png,
operating_margin.csv) with analysis context only in the directory path.

Acceptance criteria:
1. /wh:plan task templates generate output paths with prefixed filenames:
   <analysis_name>_<YYYY-MM-DD>_<fig_letter>_<slug>.png
2. /wh:execute produces figures/datasets using the prefixed filename convention
3. Wheeler graph node title field carries the prefixed slug
4. ensure_artifact accepts prefixed filenames without complaint
5. A test verifies that a fresh /wh:plan + /wh:execute produces filenames whose
   base alone identifies (analysis, date, fig-letter, slug) without parent dir context
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
import pytest


class TestFilenamePrefix:
    """Test that figure and dataset filenames include analysis name and date prefix."""

    def test_plan_guidance_mentions_prefixed_filenames(self):
        """Plan command should guide figure/dataset output paths with prefixed naming."""
        plan_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "plan.md"
        assert plan_cmd.exists(), f"Plan command not found at {plan_cmd}"

        content = plan_cmd.read_text()

        # The plan command should mention prefixing filenames with analysis name and date
        # Look for patterns like "<analysis_name>_<YYYY-MM-DD>_<slug>" or similar
        has_prefix_guidance = (
            "analysis_name" in content.lower() or
            "YYYY-MM-DD" in content or
            "prefix" in content.lower() and "filename" in content.lower()
        )

        assert has_prefix_guidance, (
            "Plan command does not mention prefixing filenames with analysis name and date. "
            "Should guide users toward <analysis_name>_<YYYY-MM-DD>_<slug> filename pattern "
            "for global uniqueness of exported figures and datasets."
        )

    def test_execute_guidance_uses_prefixed_filenames(self):
        """Execute command should document writing to prefixed filenames."""
        execute_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "execute.md"
        assert execute_cmd.exists(), f"Execute command not found at {execute_cmd}"

        content = execute_cmd.read_text()

        # The execute command should mention prefixing output filenames
        # Look for patterns indicating the full filename convention
        has_prefix_in_context = (
            "analysis_name" in content.lower() or
            "prefix" in content.lower() or
            "_2026-" in content or  # example date in execute.md
            "analysis_exports" in content and "YYYY-MM-DD" in content
        )

        assert has_prefix_in_context, (
            "Execute command does not mention prefixing output filenames with analysis name and date. "
            "Should document writing figures/datasets with <analysis_name>_<YYYY-MM-DD>_<slug> pattern."
        )

    def test_prefixed_filenames_convention_documented(self):
        """Filename prefixing convention should be clearly documented in task guidance."""
        plan_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "plan.md"
        execute_cmd = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "execute.md"

        plan_content = plan_cmd.read_text()
        execute_content = execute_cmd.read_text()

        # Both commands should mention that filenames should include analysis+date prefix
        # This is the key acceptance criterion: documented behavior
        combined = plan_content + execute_content

        # Check for guidance about filename prefixing with analysis name
        # Looking for variants like:
        # - "analysis_name" mention
        # - "prefix" + "filename"
        # - Example patterns showing <name>_<date>_ prefix
        has_prefix_concept = (
            ("analysis" in combined.lower() and "prefix" in combined.lower()) or
            "<analysis_name>" in combined or
            ("filename" in combined.lower() and "unique" in combined.lower()) or
            "analysis_exports" in combined and "date" in combined.lower()
        )

        assert has_prefix_concept, (
            "Plan and/or execute commands do not adequately document filename prefixing. "
            "Should mention that figures/datasets need <analysis_name>_<YYYY-MM-DD>_ prefix "
            "for global uniqueness when files are detached from parent directories."
        )

    def test_plan_and_execute_sync_with_prefix_guidance(self):
        """Plan and execute commands should both document filename prefixing consistently."""
        plan_cmd_path = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "plan.md"
        plan_data_path = Path(__file__).parent.parent.parent / "wheeler" / "_data" / "commands" / "plan.md"

        execute_cmd_path = Path(__file__).parent.parent.parent / ".claude" / "commands" / "wh" / "execute.md"
        execute_data_path = Path(__file__).parent.parent.parent / "wheeler" / "_data" / "commands" / "execute.md"

        # Sync check (as in issue #46)
        assert plan_cmd_path.exists(), f"Plan command not found at {plan_cmd_path}"
        assert plan_data_path.exists(), f"Data command not found at {plan_data_path}"
        assert execute_cmd_path.exists(), f"Execute command not found at {execute_cmd_path}"
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
