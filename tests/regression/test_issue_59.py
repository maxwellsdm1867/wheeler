"""Regression test for issue #59: mcp/ensure_artifact figure artifacts with null title.

When ensure_artifact creates a Finding node for a figure (.svg, .png, etc.),
the title field should be populated from the filename stem, not left null.

Root cause: _build_delegated_args for Finding artifacts does NOT include the
hash field in the returned handler_args dict, unlike all other artifact types.
Additionally, the handler_args dict for Finding must include the title field
(defaulted from stem if not provided) so that add_finding receives it.

This test verifies the core logic: _build_delegated_args must produce a title
for figure Findings when none is provided (defaulting to filename stem).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_delegated_args_figure_has_title():
    """_build_delegated_args must include title (defaulted from stem) for figure Findings.

    This is the low-level test that validates the core logic before the
    handler_args dict is passed to add_finding or execute_tool.
    """
    from wheeler.tools.graph_tools.mutations import _build_delegated_args

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test with SVG (from issue #59)
        svg_path = Path(tmpdir) / "profile_vp_wide.svg"
        svg_path.write_text("<svg></svg>")

        tool_name, handler_args = _build_delegated_args(
            "Finding", "figure", str(svg_path), {}, "somehash",
        )

        # Core assertions
        assert tool_name == "add_finding", "Should delegate to add_finding"
        assert "title" in handler_args, "title must be in handler_args"
        assert handler_args["title"] is not None, "title must not be None"
        assert handler_args["title"] != "", "title must not be empty string"
        assert handler_args["title"] == "profile_vp_wide", (
            f"title should be filename stem, got {handler_args['title']!r}"
        )
        assert handler_args["artifact_type"] == "figure"
        assert "title" in handler_args.get("_defaulted", []), (
            "title should be recorded as defaulted (not user-provided)"
        )


def test_build_delegated_args_png_figure_has_title():
    """_build_delegated_args defaults PNG figure title from stem."""
    from wheeler.tools.graph_tools.mutations import _build_delegated_args

    with tempfile.TemporaryDirectory() as tmpdir:
        png_path = Path(tmpdir) / "canonical_shapes_strip.png"
        png_path.write_bytes(b"fake PNG data")

        tool_name, handler_args = _build_delegated_args(
            "Finding", "figure", str(png_path), {}, "hash",
        )

        assert tool_name == "add_finding"
        assert handler_args["title"] == "canonical_shapes_strip"
        assert handler_args["artifact_type"] == "figure"


def test_build_delegated_args_figure_respects_explicit_title():
    """_build_delegated_args uses explicit title when provided, does not override."""
    from wheeler.tools.graph_tools.mutations import _build_delegated_args

    with tempfile.TemporaryDirectory() as tmpdir:
        svg_path = Path(tmpdir) / "figure.svg"
        svg_path.write_text("<svg></svg>")

        # User provides explicit title
        tool_name, handler_args = _build_delegated_args(
            "Finding", "figure", str(svg_path),
            {"title": "Custom Figure Title"},
            "hash",
        )

        assert tool_name == "add_finding"
        assert handler_args["title"] == "Custom Figure Title"
        assert "title" not in handler_args.get("_defaulted", []), (
            "title should NOT be in _defaulted when user provided it"
        )


def test_build_delegated_args_figure_includes_hash_field():
    """Finding artifacts from ensure_artifact must include the hash field.

    Script, Dataset, Document, and Plan artifacts include hash in
    handler_args (via **common). Finding artifacts use manual dict
    construction and previously dropped the hash field, breaking change
    detection: ensure_artifact compares the stored hash on every call, so
    a figure registered without a hash was permanently seen as changed.
    """
    from wheeler.tools.graph_tools.mutations import _build_delegated_args

    with tempfile.TemporaryDirectory() as tmpdir:
        svg_path = Path(tmpdir) / "profile.svg"
        svg_path.write_text("<svg></svg>")
        file_hash = "abc123"

        _tool_name, handler_args = _build_delegated_args(
            "Finding", "figure", str(svg_path), {}, file_hash,
        )

        assert handler_args.get("hash") == file_hash, (
            "hash field missing from Finding handler_args; "
            "the computed file hash must be passed through to add_finding"
        )


def test_ensure_artifact_replicates_issue_59():
    """Direct replication of issue #59: ensure_artifact with figure + no title.

    Issue #59 reports that three figure findings (F-17c35fe1, F-c5b492d3,
    F-08fe6441) registered via ensure_artifact had null titles. This test
    verifies that _build_delegated_args correctly sets title from stem, so
    the title should NOT be null or empty in handler_args. If this test
    fails, it means the bug has been introduced or was never fixed.
    """
    from wheeler.tools.graph_tools.mutations import _build_delegated_args

    with tempfile.TemporaryDirectory() as tmpdir:
        # Replicate the exact filenames from the issue
        filenames = ["profile_vp_wide.svg", "canonical_shapes_strip.svg", "takeaways_block.svg"]

        for filename in filenames:
            svg_path = Path(tmpdir) / filename
            svg_path.write_text("<svg></svg>")

            # Call _build_delegated_args without providing title (as user would)
            _tool_name, handler_args = _build_delegated_args(
                "Finding", "figure", str(svg_path), {}, "somehash",
            )

            # Extract the expected stem
            expected_title = svg_path.stem

            # This is the core assertion that would catch issue #59
            actual_title = handler_args.get("title")
            assert actual_title is not None, (
                f"Issue #59: title is None for {filename}"
            )
            assert actual_title != "", (
                f"Issue #59: title is empty string for {filename}"
            )
            assert actual_title == expected_title, (
                f"Issue #59: title mismatch for {filename}. "
                f"Expected {expected_title!r}, got {actual_title!r}"
            )
