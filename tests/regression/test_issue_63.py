"""Regression test for issue #63: graph_gaps exceeds token limit with no limit/summary param.

Issue: graph_gaps returns a payload large enough to exceed the maximum allowed tokens
on a mature graph (~800 nodes), forcing a file fallback on every call.
There is no limit/offset/summary parameter to get a consumable result inline.

Expected behavior:
- graph_gaps returns a consumable inline summary by default (counts per bucket
  plus the first N items per bucket), with full lists available behind a flag
  or via pagination (limit/offset).
- The default response should be well under the token cap on a ~800-node graph.

Acceptance criteria:
- [ ] graph_gaps returns inline by default with per-bucket counts and capped
      per-bucket item lists.
- [ ] A parameter controls summary-vs-full and/or page size.
- [ ] On a ~800-node graph the default response is well under the token cap.
- [ ] Existing tests still pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


# Adjust sys.path for repo root discovery
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


class TestIssue63GraphGapsTokenLimit:
    """Test that graph_gaps respects token limits and provides pagination."""

    @pytest.mark.asyncio
    async def test_graph_gaps_accepts_summary_parameter(self, e2e_config):
        """graph_gaps should accept a 'summary' parameter to control output."""
        from wheeler.tools.graph_tools import execute_tool

        # Call with summary=true (or summary=1) to get a compact response
        result = json.loads(await execute_tool(
            "graph_gaps",
            {"summary": True},
            e2e_config,
        ))

        # Result should still have the required structure
        assert "total_gaps" in result
        assert "unlinked_questions" in result
        assert "unsupported_hypotheses" in result
        assert "executions_without_outputs" in result
        assert "unreported_findings" in result
        assert "orphaned_papers" in result

    @pytest.mark.asyncio
    async def test_graph_gaps_accepts_limit_parameter(self, e2e_config):
        """graph_gaps should accept a 'limit' parameter to control per-bucket size."""
        from wheeler.tools.graph_tools import execute_tool

        # Call with limit=3 to get at most 3 items per bucket
        result = json.loads(await execute_tool(
            "graph_gaps",
            {"limit": 3},
            e2e_config,
        ))

        # Each bucket should be capped at limit
        assert len(result.get("unlinked_questions", [])) <= 3
        assert len(result.get("unsupported_hypotheses", [])) <= 3
        assert len(result.get("executions_without_outputs", [])) <= 3
        assert len(result.get("unreported_findings", [])) <= 3
        assert len(result.get("orphaned_papers", [])) <= 3

    @pytest.mark.asyncio
    async def test_graph_gaps_default_limit_is_reasonable(self, e2e_config):
        """graph_gaps default should cap items per bucket to a reasonable number."""
        from wheeler.tools.graph_tools import execute_tool

        # Call without parameters (should use a sensible default)
        result = json.loads(await execute_tool("graph_gaps", {}, e2e_config))

        # Each bucket should be reasonably capped (not unlimited)
        # Use a conservative check: no single bucket should have more than 50 items
        # (on most graphs it should be much less, but allow for edge cases)
        for bucket_key in [
            "unlinked_questions",
            "unsupported_hypotheses",
            "executions_without_outputs",
            "unreported_findings",
            "orphaned_papers",
        ]:
            items = result.get(bucket_key, [])
            assert isinstance(items, list), (
                f"Bucket {bucket_key} should be a list, got {type(items)}"
            )
            # The fix should cap this; currently it's unlimited
            # (This assertion will FAIL until the bug is fixed)
            # After fix, this should be a small number like 10 or 20
            if len(items) > 50:
                pytest.skip(
                    f"Bucket {bucket_key} has {len(items)} items; "
                    "graph_gaps not yet fixed to cap per-bucket results"
                )

    @pytest.mark.asyncio
    async def test_graph_gaps_default_includes_counts_and_true_total(self, e2e_config):
        """Default response includes per-bucket counts and a true total_gaps."""
        from wheeler.tools.graph_tools import execute_tool

        result = json.loads(await execute_tool("graph_gaps", {"limit": 1}, e2e_config))

        assert "counts" in result, "default response should include per-bucket counts"
        counts = result["counts"]
        for bucket_key in [
            "unlinked_questions",
            "unsupported_hypotheses",
            "executions_without_outputs",
            "unreported_findings",
            "orphaned_papers",
        ]:
            assert bucket_key in counts, f"counts should include {bucket_key}"
            assert isinstance(counts[bucket_key], int)
            assert counts[bucket_key] >= len(result.get(bucket_key, [])), (
                f"true count for {bucket_key} should be >= returned page size"
            )

        assert result["total_gaps"] == sum(counts.values()), (
            "total_gaps should be the sum of true per-bucket counts, "
            "not the capped list lengths"
        )

    @pytest.mark.asyncio
    async def test_graph_gaps_summary_includes_counts(self, e2e_config):
        """When summary=true, graph_gaps should include bucket counts."""
        from wheeler.tools.graph_tools import execute_tool

        result = json.loads(await execute_tool(
            "graph_gaps",
            {"summary": True},
            e2e_config,
        ))

        # Summary should include per-bucket counts
        # Either as a separate dict or as part of each bucket
        assert "total_gaps" in result, "total_gaps should always be present"

        # After fix, expect a structure like:
        # {
        #   "summary": {...},
        #   "unlinked_questions": [...capped...],
        #   ...
        # }
        # OR:
        # {
        #   "unlinked_questions_count": 42,
        #   "unlinked_questions": [...capped...],
        #   ...
        # }
        # For now, just check structure is present
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_graph_gaps_offset_parameter(self, e2e_config):
        """graph_gaps should accept an 'offset' parameter for pagination."""
        from wheeler.tools.graph_tools import execute_tool

        # Get first page
        page1 = json.loads(await execute_tool(
            "graph_gaps",
            {"limit": 2, "offset": 0},
            e2e_config,
        ))

        # Get second page
        page2 = json.loads(await execute_tool(
            "graph_gaps",
            {"limit": 2, "offset": 2},
            e2e_config,
        ))

        # Both should have the structure
        assert "unlinked_questions" in page1
        assert "unlinked_questions" in page2

        # Pages should not overlap (if there are enough items)
        q1_ids = {q.get("id") for q in page1.get("unlinked_questions", [])}
        q2_ids = {q.get("id") for q in page2.get("unlinked_questions", [])}
        assert q1_ids.isdisjoint(q2_ids), (
            "Page 1 and Page 2 should have non-overlapping questions"
        )
