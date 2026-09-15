"""Regression test for issue #115: statusline context percentage disagrees with /context.

Issue: The wheeler-statusline.js script discards the payload's used_percentage and
recomputes a different number using a hardcoded 16.5% auto compact buffer. The
rendered percentage doesn't match the payload's used_percentage or what /context reports.

The divergence grows with context depth:
  payload used=5 (remaining=95)   -> statusline shows 6%   (off by 1 point)
  payload used=48 (remaining=52)  -> statusline shows 57%  (off by 9 points)
  payload used=60 (remaining=40)  -> statusline shows 72%  (off by 12 points)
  payload used=75 (remaining=25)  -> statusline shows 90%  (off by 15 points)

Acceptance criteria:
1. When a payload has used_percentage=X, the meaning is unambiguous to a user
   comparing against /context.
2. The 16.5 constant is either documented or no longer silently applied.
3. When remaining_percentage is absent, the segment is defined and not blank.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def run_statusline_script(payload_dict: dict) -> str:
    """Run the statusline script with a JSON payload, return stripped output."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "wheeler" / "_data" / "hooks" / "wheeler-statusline.js"

    payload_json = json.dumps(payload_dict)

    result = subprocess.run(
        ["node", str(script_path)],
        input=payload_json,
        capture_output=True,
        text=True,
        timeout=3,
    )

    output = result.stdout

    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    stripped = ansi_escape.sub("", output)
    return stripped


def extract_percentage(output: str) -> int | None:
    """Extract the percentage value from statusline output.

    Returns the numeric percentage or None if no percentage found.
    """
    match = re.search(r"(\d+)%", output)
    if match:
        return int(match.group(1))
    return None


def test_statusline_percentage_matches_payload_or_is_labeled():
    """Test that the rendered percentage either matches the payload or is
    visibly labeled as something different.

    This test checks the main acceptance criterion: a user comparing the
    statusline against /context should see matching numbers OR a clear label
    distinguishing them.

    The test accepts EITHER resolution:
    A) The rendered percentage equals the payload's used_percentage, OR
    B) The rendered percentage is accompanied by a visible label (e.g.,
       'compact-adjusted' or similar notation) that distinguishes it from raw usage.
    """
    test_cases = [
        {"used": 5, "remaining": 95},
        {"used": 48, "remaining": 52},
        {"used": 60, "remaining": 40},
        {"used": 75, "remaining": 25},
    ]

    for case in test_cases:
        payload = {
            "model": {"display_name": "Claude"},
            "workspace": {"current_dir": "/test"},
            "context_window": {
                "total_input_tokens": 52846,
                "context_window_size": 1000000,
                "used_percentage": case["used"],
                "remaining_percentage": case["remaining"],
            },
        }

        output = run_statusline_script(payload)
        rendered_pct = extract_percentage(output)

        assert rendered_pct is not None, f"No percentage found in output: {output}"

        has_matching_percentage = rendered_pct == case["used"]

        has_distinguishing_label = bool(
            re.search(
                r"(compact|adjusted|buffer|reserve)",
                output,
                re.IGNORECASE,
            )
        )

        if not has_matching_percentage and not has_distinguishing_label:
            raise AssertionError(
                f"Test case used={case['used']} remaining={case['remaining']}: "
                f"statusline shows {rendered_pct}% but payload says {case['used']}%. "
                f"Rendered percentage does not match payload and output lacks a "
                f"distinguishing label (like 'compact' or 'adjusted'). "
                f"Output: {output}"
            )


def test_statusline_missing_remaining_percentage_renders_valid_segment():
    """Test that when remaining_percentage is absent, the output is defined
    and does not produce a blank or misleading segment.

    Current behavior: the context indicator segment is omitted when remaining_percentage
    is absent. This test verifies that behavior is defined and does not break the
    overall output structure.
    """
    payload = {
        "model": {"display_name": "Claude"},
        "workspace": {"current_dir": "/test"},
        "context_window": {
            "total_input_tokens": 52846,
            "context_window_size": 1000000,
            "used_percentage": 5,
        },
    }

    output = run_statusline_script(payload)

    assert output is not None, "Output should not be None"
    assert output.strip() != "", "Output should not be blank"

    assert "Claude" in output, "Output should contain model name"
    assert "test" in output, "Output should contain directory name"

    percentage = extract_percentage(output)
    if percentage is not None:
        assert (
            0 <= percentage <= 100
        ), f"If percentage is present, it should be 0-100, got {percentage}%"
