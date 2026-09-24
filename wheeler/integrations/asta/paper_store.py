"""Build an Asta ``--paper-store`` payload from curated graph Papers.

A marshal-IN module, and the first deterministic one. Every other helper in this
package is marshal-OUT (a tool ran, write the result to the graph). This one runs
the other way: it turns curated graph state into a tool payload, so the input side
of a service call stops being prose a model hand-assembles and starts being a
function. The failure that motivated it (Wheeler issue #85) was exactly a
hand-built store that the server rejected with no detail.

It reads the graph and writes a file. It creates NO graph nodes and NO edges, so
unlike the ingest modules it never imports ``execute_tool``.

WHY THE GRAPH AND NOT THE RAW ARTIFACT
--------------------------------------
The obvious source is the ``asta literature find -o`` artifact, but that is the
wrong one: it holds every paper the search returned, including the ones the
scientist screened out. The curated set lives in the graph, where off-target
nodes were deleted and the survivors were linked to a Question. Reading from the
graph is what makes the seed reflect a human judgment rather than a raw search.
It also yields the Paper ids, so the run can record ``USED`` against the exact
nodes that seeded it.

THE CLOSED-CORPUS PROBLEM (the whole reason for ``markdown`` mode)
-----------------------------------------------------------------
From ``asta generate-theories literature-theory-generation --help``:

    Entries with `paper_markdown` are used directly. Entries without
    `paper_markdown` but with at least one of `corpus_id`, `s2_id`, or `title`
    are hydrated server-side ... Hydration is performed during the PaperFinder
    step, so it requires `search_additional_papers=True`; with PaperFinder
    disabled, identifier-only entries are dropped.

So an identifier-only store CANNOT give a curated corpus: hydrating it forces
PaperFinder to run, and PaperFinder reintroduces the very papers that were
screened out. Only ``paper_markdown`` entries are usable with
``--no-search-additional-papers``, which is the one combination that yields a
closed corpus. That is why ``markdown`` is the default mode and why it refuses to
silently downgrade a paper that has no abstract: one identifier-only entry in an
otherwise-markdown store forces PaperFinder back on and quietly destroys the
guarantee the mode exists to provide.

TOP-LEVEL SHAPE
---------------
The per-entry contract above is documented; the container shape is not. A JSON
list is emitted, which matches the help's "entries" language and is the shape a
"store" of records naturally takes. If a future asta version wants an object,
this is the single place to change it. A rejected store now reports a reason
(Wheeler issue #86), so verifying costs one run.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)

MODE_MARKDOWN = "markdown"
MODE_IDENTIFIERS = "identifiers"
MODES = (MODE_MARKDOWN, MODE_IDENTIFIERS)


@dataclass
class PaperStoreResult:
    """The outcome of one export.

    ``closed`` is the load-bearing field: True only when every emitted entry
    carries ``paper_markdown``, which is the sole condition under which
    ``--no-search-additional-papers`` yields a corpus limited to these papers.
    """

    mode: str = MODE_MARKDOWN
    entries: list[dict[str, Any]] = field(default_factory=list)
    paper_ids: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    selected: int = 0

    @property
    def closed(self) -> bool:
        return bool(self.entries) and all(
            e.get("paper_markdown") for e in self.entries
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "selected": self.selected,
            "exported": len(self.entries),
            "skipped": len(self.skipped),
            "closed": self.closed,
            "paper_ids": list(self.paper_ids),
        }


def _render_markdown(row: dict[str, Any]) -> str:
    """Render one Paper node as the markdown the theorizer consumes directly.

    Abstract-level, not full text: the graph stores what Paper Finder returned.
    Thinner than the server's own S2 + OCR hydration, and that is the trade the
    mode makes, buying corpus control at the cost of per-paper depth.
    """
    title = (row.get("title") or "").strip()
    lines = [f"# {title}" if title else "# (untitled)", ""]

    meta: list[str] = []
    if row.get("authors"):
        meta.append(f"**Authors:** {row['authors']}")
    year = row.get("year") or 0
    if year:
        meta.append(f"**Year:** {year}")
    if row.get("venue"):
        meta.append(f"**Venue:** {row['venue']}")
    if row.get("doi"):
        meta.append(f"**DOI:** {row['doi']}")
    if row.get("url"):
        meta.append(f"**URL:** {row['url']}")
    if row.get("corpus_id"):
        meta.append(f"**Corpus ID:** {row['corpus_id']}")
    if meta:
        lines.extend(meta)
        lines.append("")

    lines.append("## Abstract")
    lines.append("")
    lines.append((row.get("abstract") or "").strip())
    return "\n".join(lines).rstrip() + "\n"


async def _select_papers(
    backend,
    config: WheelerConfig,
    *,
    link_to: str | None,
    paper_ids: list[str] | None,
) -> list[dict[str, Any]]:
    """Read the curated Paper set from the graph, deterministically ordered.

    Project-aware, mirroring the read scoping used by the other helpers here.
    The abstract lives in the flattened custom bag (``custom_abstract``) because
    ``PaperModel`` has no abstract field; ``parse_paper_finder`` promotes it
    there via ``_CUSTOM_SCALAR_KEYS``.
    """
    params: dict[str, Any] = {}
    clauses: list[str] = []

    if paper_ids:
        match = "MATCH (p:Paper)"
        clauses.append("p.id IN $ids")
        params["ids"] = list(paper_ids)
    else:
        match = "MATCH (p:Paper)-[:RELEVANT_TO]->(t)"
        clauses.append("t.id = $link_to")
        params["link_to"] = link_to

    ptag = getattr(config.neo4j, "project_tag", "") or ""
    if ptag:
        clauses.append("p._wheeler_project = $ptag")
        params["ptag"] = ptag

    query = (
        f"{match} WHERE " + " AND ".join(clauses) + " "
        "RETURN p.id AS id, p.corpus_id AS corpus_id, p.title AS title, "
        "p.authors AS authors, p.year AS year, p.doi AS doi, "
        "p.custom_abstract AS abstract, p.custom_venue AS venue, "
        "p.custom_url AS url "
        "ORDER BY p.id"
    )
    rows = await backend.run_cypher(query, params)
    return list(rows or [])


async def build_paper_store(
    config: WheelerConfig,
    *,
    link_to: str | None = None,
    paper_ids: list[str] | None = None,
    mode: str = MODE_MARKDOWN,
) -> PaperStoreResult:
    """Build a paper store from graph Papers selected by link target or id.

    In ``markdown`` mode a Paper with no abstract is SKIPPED, not downgraded to
    an identifier: mixing one identifier-only entry into the store would force
    ``search_additional_papers=True`` and silently reopen the corpus. Callers
    should surface the skipped list so the scientist can add the abstract or
    choose ``identifiers`` mode deliberately.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    if not link_to and not paper_ids:
        raise ValueError("pass link_to or paper_ids to select the papers")

    from wheeler.graph.backend import get_backend

    backend = get_backend(config)
    rows = await _select_papers(
        backend, config, link_to=link_to, paper_ids=paper_ids
    )

    result = PaperStoreResult(mode=mode, selected=len(rows))
    for row in rows:
        pid = row.get("id") or ""
        corpus_id = str(row.get("corpus_id") or "")
        title = (row.get("title") or "").strip()

        if mode == MODE_MARKDOWN:
            abstract = (row.get("abstract") or "").strip()
            if not abstract:
                # Refuse to downgrade: see the module docstring. A silent
                # identifier-only entry here would reopen the corpus.
                result.skipped.append({"id": pid, "title": title})
                continue
            entry: dict[str, Any] = {"paper_markdown": _render_markdown(row)}
            # corpus_id rides along so the server's dedupe-by-corpus_id still
            # works if PaperFinder is enabled anyway.
            if corpus_id:
                entry["corpus_id"] = corpus_id
            if title:
                entry["title"] = title
        else:
            if not corpus_id and not title:
                result.skipped.append({"id": pid, "title": title})
                continue
            entry = {}
            if corpus_id:
                entry["corpus_id"] = corpus_id
            if title:
                entry["title"] = title

        result.entries.append(entry)
        if pid:
            result.paper_ids.append(pid)

    return result


def write_paper_store(result: PaperStoreResult, out_path: str | Path) -> Path:
    """Write the store JSON atomically (tmp then rename), returning the path."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(result.entries, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return path
