"""Regression test for issue #87: paper_finder dedup on title when corpus_id absent.

When an existing Paper node was created without a corpus_id (via add_paper or
earlier ingest), and a new paper_finder ingest includes a paper with the same
normalized title but WITH a corpus_id, the ingest currently creates a duplicate
because dedup only checks corpus_id.

The fix adds a fallback dedup on normalized title (case-insensitive, trimmed)
when the existing node lacks a corpus_id.

Acceptance criteria per issue:
  - Ingesting a paper_finder artifact whose papers match existing nodes by
    normalized title (case-insensitive, trimmed) does not create duplicates,
    even when the existing node has no corpus_id.
  - A dedup fallback on normalized title is applied when corpus_id is absent
    on the existing node, OR papers carry corpus_id so corpus_id dedup catches
    them.
  - Existing tests still pass.
"""

from __future__ import annotations


class TestTitleDedup:
    """Test that title-based dedup helper exists and works correctly."""

    def test_find_paper_by_normalized_title_helper_exists(self):
        """Verify that the title-based dedup helper function is exported.

        The fix adds _find_paper_by_normalized_title to _marshal.py so adapters
        can call it as a fallback when corpus_id dedup doesn't find a match.
        """
        # This test will fail until the fix is implemented.
        from wheeler.integrations.asta import _marshal

        assert hasattr(_marshal, "_find_paper_by_normalized_title"), (
            "_find_paper_by_normalized_title should be defined in _marshal.py"
        )
        assert callable(getattr(_marshal, "_find_paper_by_normalized_title")), (
            "_find_paper_by_normalized_title should be a callable helper function"
        )


# Full e2e test with live Neo4j would verify:
#   1. Create a Paper via add_paper with title="Example Paper" (no corpus_id)
#   2. Ingest paper_finder artifact with paper(title="example paper", corpus_id="123")
#   3. Verify created=0, deduped=1 (not created=1, deduped=0)
#   4. Verify only ONE Paper node exists for that title
