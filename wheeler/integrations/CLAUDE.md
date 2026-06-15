# integrations/ -- External-tool adapters (Asta first)

Wheeler is the core. Each external tool is wrapped in two thin layers: act
prose shapes the input (marshal in), one deterministic Python function writes
the result to the graph (marshal out). This package holds only the marshal-out
side plus the subprocess boundary. No workflow engine, daemon, or router.

## Modules

- `transport.py` -- `run_asta(argv, *, output_path, timeout)`. The single place
  that shells out to the asta CLI, capturing returncode and stderr. Returns None
  on non-zero exit, timeout, or a missing/empty/unparseable `-o` artifact, else
  the loaded JSON dict. Zero graph dependency, no LLM-provider SDK.
- `schemas.py` -- `parse_paper_finder(doc) -> list[PaperRecord]`. Leaf module
  (stdlib only). Reads the Asta `LiteratureSearchResult` shape defensively and
  splits each paper into promoted fields (corpus_id, title, authors, year),
  custom scalars (relevance_score, venue, url, citation_count, abstract), and
  structured payloads (snippets, citationContexts) used for edges. No graph import.
- `ingest.py` -- `ingest_paper_finder(doc, *, link_to, config) -> ImportReport`.
  The ONLY module that imports `execute_tool` (lazily, function-local, mirroring
  `wheeler/validation/ledger.py`). Writes route through `execute_tool` for
  triple-write; reads use the same cached backend.
- `cli.py` -- `integrate_app` Typer sub-app, one verb: `ingest <tool> <artifact>
  [--link-to ID]`. Registered in `wheeler/tools/cli.py` guarded by try/except.

## Invariants

- **Chokepoint.** `ingest.py` is the sole caller of `execute_tool`. This keeps
  `graph_tools/` asta-free and preserves strict layering. `transport.py` has no
  graph dependency.
- **corpus_id normalization.** Dedupe keys on `corpus_id`, always coerced to a
  digit-string (`str(int(...))`), so an int or a digit-string artifact value map
  to the same Paper. The key is INDEXED on `Paper.corpus_id` and promoted onto
  `PaperModel`.
- **Custom-bag flatten.** Scalar long-tail fields with no promoted model field
  are parked into `PaperModel.custom`. The Neo4j backend flattens `custom` to
  discrete `custom_<key>` props on write and reassembles on read, so they are
  stored AND queryable (`WHERE p.custom_relevance_score > 0.8`).
- **link_once.** Every edge is guarded by an existence check first, because the
  backend's `create_relationship` is a bare `CREATE` that duplicates edges on
  re-ingest. Re-running the same artifact never duplicates papers or edges.
- **Sequential writes.** Never `asyncio.gather`. `execute_tool` reuses one
  cached backend singleton and Neo4j forbids concurrent queries.
- **One Execution per run** (kind `paper-search`, service `asta:paper-finder`),
  not per output node. `session_id` correlates everything written in one turn.
- **Failure isolation.** A failed or canceled CLI run writes nothing. Retries,
  auth, and timeouts stay inside the asta CLI.

## Conventions

- `from __future__ import annotations`; `logging.getLogger(__name__)`; async for
  graph I/O.
- Add no LLM-provider SDK. Never use em dashes.
