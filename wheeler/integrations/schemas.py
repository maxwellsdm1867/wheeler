"""Schema parsing for external-tool artifacts (marshal-out, anti-corruption).

This is a leaf module: stdlib only, no graph import, no anthropic import.
``parse_paper_finder`` reads the Asta ``LiteratureSearchResult`` shape and
splits each paper's fields into three buckets:

  - promoted: corpus_id, title, authors, year (first-class PaperModel fields)
  - custom:   scalar long-tail fields parked into the queryable custom bag
              (relevance_score, venue, url, citation_count, abstract)
  - structured: non-scalar payloads handled as edges or kept in JSON
                (snippets, citation_contexts)

The function is defensive: it tolerates missing keys and coerces ``corpusId``
to ``str(int(...))`` so the dedupe key is stable regardless of whether the
artifact carried an int or a digit-string.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PaperRecord:
    """One paper normalized for ingest.

    Attributes:
        corpus_id: Stable dedupe key, always a string of digits ("" if absent).
        title: Paper title.
        authors: Comma-joined author names (PaperModel stores authors as str).
        year: Publication year (0 if unknown).
        custom: Scalar long-tail fields for the queryable custom bag.
        cited_corpus_ids: Source corpus ids from citationContexts (-> CITES).
        raw: The original paper dict, preserved for downstream JSON if needed.
    """

    corpus_id: str
    title: str
    authors: str
    year: int
    custom: dict[str, Any] = field(default_factory=dict)
    cited_corpus_ids: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def _normalize_corpus_id(value: Any) -> str:
    """Coerce a corpus id to a digit-string, or "" if not a clean integer."""
    if value is None:
        return ""
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return ""
    s = str(value).strip()
    if s.isdigit():
        return str(int(s))
    return s if s else ""


def _join_authors(value: Any) -> str:
    """Render the authors list (list of {name, authorId}) as a comma string."""
    if not isinstance(value, list):
        return str(value) if value else ""
    names: list[str] = []
    for author in value:
        if isinstance(author, dict):
            name = author.get("name", "")
            if name:
                names.append(str(name))
        elif isinstance(author, str):
            names.append(author)
    return ", ".join(names)


def _coerce_year(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# Scalar long-tail fields parked into the custom bag. Each maps an artifact
# key to the custom_<key> name the backend will store. Only scalar values are
# kept; None and non-scalars are dropped.
_CUSTOM_SCALAR_KEYS: tuple[tuple[str, str], ...] = (
    ("relevanceScore", "relevance_score"),
    ("venue", "venue"),
    ("url", "url"),
    ("citationCount", "citation_count"),
    ("abstract", "abstract"),
)


def _scalar_or_none(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    return None


def _parse_paper(paper: dict[str, Any]) -> PaperRecord | None:
    """Parse one paper dict into a PaperRecord, or None if unusable."""
    if not isinstance(paper, dict):
        logger.warning("parse_paper_finder: skipping non-dict paper entry")
        return None

    corpus_id = _normalize_corpus_id(paper.get("corpusId"))
    title = str(paper.get("title", "")).strip()
    if not corpus_id and not title:
        logger.warning("parse_paper_finder: skipping paper with no corpus_id or title")
        return None

    custom: dict[str, Any] = {}
    for src_key, dst_key in _CUSTOM_SCALAR_KEYS:
        val = _scalar_or_none(paper.get(src_key))
        if val is not None and val != "":
            custom[dst_key] = val

    # Summarize non-scalar structures to scalar counts (cheap filterable signal).
    snippets = paper.get("snippets")
    if isinstance(snippets, list) and snippets:
        custom["snippet_count"] = len(snippets)

    cited: list[str] = []
    citation_contexts = paper.get("citationContexts")
    if isinstance(citation_contexts, list):
        for ctx in citation_contexts:
            if not isinstance(ctx, dict):
                continue
            src = _normalize_corpus_id(ctx.get("sourceCorpusId"))
            if src:
                cited.append(src)
    if cited:
        custom["citation_context_count"] = len(cited)

    return PaperRecord(
        corpus_id=corpus_id,
        title=title,
        authors=_join_authors(paper.get("authors")),
        year=_coerce_year(paper.get("year")),
        custom=custom,
        cited_corpus_ids=cited,
        raw=paper,
    )


def parse_paper_finder(doc: dict[str, Any]) -> list[PaperRecord]:
    """Parse an Asta LiteratureSearchResult doc into PaperRecords.

    Defensive: a missing or malformed ``results`` list yields an empty list
    rather than raising, so a partial artifact never aborts ingest.
    """
    if not isinstance(doc, dict):
        logger.warning("parse_paper_finder: doc is not a dict, got %s", type(doc).__name__)
        return []

    results = doc.get("results")
    if not isinstance(results, list):
        logger.warning("parse_paper_finder: 'results' missing or not a list")
        return []

    records: list[PaperRecord] = []
    for paper in results:
        record = _parse_paper(paper)
        if record is not None:
            records.append(record)
    return records
