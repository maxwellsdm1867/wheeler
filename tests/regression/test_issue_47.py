"""Regression test for issue #47: figure title triple-lock.

Issue: When /wh:execute produces a figure, the filename slug should match
the graph Finding node's title field, and both should match the visible
on-figure title. Currently, there is no enforcement of this triple-lock,
and Finding nodes don't even have a title field to store it.

Acceptance criteria:
- Finding nodes should have a title field
- ensure_artifact should accept a title parameter for Findings
- ensure_artifact should pass title through to add_finding
- For PNG findings, optionally warn when filename base != title
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFigureTitleTripleLock:
    """Test that figure artifacts can store and match title fields."""

    def test_finding_model_has_title_field(self):
        """Finding model should have a title field to store the slug."""
        from wheeler.models import FindingModel

        # Check if title field exists
        finding_fields = FindingModel.model_fields
        # Currently fails: Finding has no title field
        assert "title" in finding_fields, (
            "FindingModel should have a 'title' field "
            "to store figure filename slug"
        )

    def test_ensure_artifact_accepts_title_for_finding(self, tmp_path: Path):
        """ensure_artifact should accept and pass through title for Finding artifacts."""
        # Create a temp PNG file
        png_path = tmp_path / "fig_F_theta0.png"
        png_path.write_bytes(b"fake png data")

        from wheeler.tools.graph_tools.mutations import _build_delegated_args

        # Test that _build_delegated_args passes title through to add_finding
        tool_name, handler_args = _build_delegated_args(
            label="Finding",
            secondary="figure",
            path=str(png_path),
            args={
                "artifact_type": "figure",
                "title": "fig_F_theta0",
                "description": "F theta0 vs delta scatter plot",
                "confidence": 0.8,
            },
            file_hash="abc123",
        )

        # Currently fails: title is not in handler_args
        assert tool_name == "add_finding"
        assert "title" in handler_args, (
            "add_finding handler should receive title parameter from ensure_artifact"
        )
        assert handler_args["title"] == "fig_F_theta0", (
            f"Title should be passed through, got {handler_args.get('title')}"
        )

    def test_ensure_artifact_should_warn_on_title_filename_mismatch(self, tmp_path: Path):
        """ensure_artifact should warn when .png Finding title doesn't match filename slug."""
        # Create a PNG file with one slug name
        png_path = tmp_path / "fig_F_theta0.png"
        png_path.write_bytes(b"fake png data")

        from wheeler.tools.graph_tools.mutations import ensure_artifact

        # This test documents the acceptance criterion:
        # ensure_artifact should validate/warn when filename base != title for PNG Findings
        # Currently: no validation happens
        # After fix: should warn or validate

        # For now, just document what should happen
        filename_base = png_path.stem  # "fig_F_theta0"
        mismatched_title = "completely_different_title"

        assert filename_base != mismatched_title, "Test setup: filenames should not match"
        # After fix, calling ensure_artifact with mismatched title should warn or error

    def test_figure_slug_matches_filename_and_title(self, tmp_path: Path):
        """Test triple-lock: filename slug == title == graph node title."""
        slug = "fig_F_theta0_vs_delta"
        png_path = tmp_path / f"{slug}.png"
        png_path.write_bytes(b"fake png data")

        from wheeler.tools.graph_tools.mutations import _build_delegated_args

        # The triple-lock contract: when ensure_artifact creates a Finding for a PNG,
        # the title should be stored on the Finding node
        tool_name, handler_args = _build_delegated_args(
            label="Finding",
            secondary="figure",
            path=str(png_path),
            args={
                "artifact_type": "figure",
                "title": slug,
                "description": "Fig: F theta0 vs delta scatter -- parasol vs midget",
                "confidence": 0.9,
            },
            file_hash="xyz789",
        )

        # After fix: handler_args should include title
        assert tool_name == "add_finding"
        # Currently fails: title is not passed to add_finding
        assert "title" in handler_args, (
            "Finding handler should receive title to enforce triple-lock: "
            "filename slug == title == graph node title"
        )
        assert handler_args["title"] == slug
