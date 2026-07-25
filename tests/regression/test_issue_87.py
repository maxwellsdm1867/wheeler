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


class TestTitleDedupUnicode:
    """The emitted Cypher must fold non-ASCII case and match Unicode whitespace.

    Neo4j evaluates JAVA regex, where `(?i)` and `\\s` are both ASCII-only by
    default. Without the U flag (UNICODE_CHARACTER_CLASS, which implies
    UNICODE_CASE) the fallback silently declines to match two classes of title
    that a real corpus is full of:

      - an uppercase non-ASCII letter in the STORED title ("MULLER CELLS" with
        an umlaut, a Greek-letter title)
      - a non-ASCII space in the STORED title, notably U+00A0, which
        publisher-scraped titles carry

    Both are false negatives: the duplicate this fallback exists to prevent gets
    created anyway. Measured against live Neo4j before the U flag was added, all
    of the cases below returned no match.
    """

    def _emitted_pattern(self, title: str) -> str:
        """Run the helper against a stub backend and capture the regex it emits."""
        import asyncio

        from wheeler.config import WheelerConfig
        from wheeler.integrations.asta._marshal import (
            _find_paper_by_normalized_title,
        )

        captured: dict[str, object] = {}

        class _StubBackend:
            async def run_cypher(self, query, params):
                captured["query"] = query
                captured["params"] = params
                return []

        asyncio.run(
            _find_paper_by_normalized_title(
                _StubBackend(), WheelerConfig(), title
            )
        )
        return str(captured["params"]["pat"])  # type: ignore[index]

    def test_pattern_enables_unicode_character_class(self):
        """The inline flags must request Unicode semantics, not just (?i)."""
        pattern = self._emitted_pattern("Muller cells in primate retina")

        flags = pattern[: pattern.index(")") + 1]
        assert "U" in flags or "u" in flags, (
            "The emitted Neo4j regex starts with "
            f"{flags!r}, which is ASCII-only in Java. Without the U flag "
            "(UNICODE_CHARACTER_CLASS, implying UNICODE_CASE) a stored title "
            "with an uppercase accented letter, or with a U+00A0 no-break "
            "space, will not match and a duplicate Paper is created anyway."
        )

    def test_pattern_folds_non_ascii_case_and_unicode_space(self):
        """Verify against Python's re, which mirrors Java's Unicode semantics here."""
        import re

        stored_variants = [
            "CAFÉ NAÏVE POINCARÉ SECTION",  # uppercase accents
            "café naïve poincaré section",  # lowercase accents
            "Café Naïve Poincaré Section",  # U+00A0 spaces
            "Café Naïve Poincaré　Section",  # thin + ideographic
        ]
        pattern = self._emitted_pattern("café naïve poincaré section")
        # Strip the Java inline flags; re-express them as Python flags. Python's
        # re is Unicode-aware by default for str patterns, which is exactly the
        # behavior the U flag buys us in Java.
        body = pattern[pattern.index(")") + 1 :]
        compiled = re.compile(body, re.IGNORECASE | re.UNICODE)

        for stored in stored_variants:
            assert compiled.match(stored), (
                f"stored title {stored!r} should match the emitted pattern; "
                "a non-ASCII case or space difference must not defeat dedup"
            )

        assert not compiled.match("a completely different title"), (
            "the pattern must stay anchored and not match unrelated titles"
        )


# Full e2e coverage lives in the cycle's verifier round-trip against live Neo4j:
#   1. Create a Paper via add_paper with title="Example Paper" (no corpus_id)
#   2. Ingest paper_finder artifact with paper(title="example paper", corpus_id="123")
#   3. Verify created=0, deduped=1 (not created=1, deduped=0)
#   4. Verify only ONE Paper node exists for that title
#   5. Verify two DISTINCT corpus_ids sharing a title stay two nodes
