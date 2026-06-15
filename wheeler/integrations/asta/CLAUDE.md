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
- `_marshal.py` -- the neutral home for the genuinely-shared marshal-out
  helpers, so the adapters import them from one place instead of reaching into
  the Paper Finder module (`ingest.py`). Holds `ImportReport` (the ingest-run
  outcome dataclass), the persisted corpus_id index load/save helpers
  (`_INDEX_REL_PATH` / `_index_path` / `_load_index` / `_save_index`), the
  project-aware read helpers (`_find_paper_by_corpus_id` / `_find_execution` /
  `_paper_exists`), and the edge-existence / `link_once` write helpers
  (`_edge_exists` / `_link_once`). Like the adapters, it imports `execute_tool`
  lazily (function-local) inside `_link_once` only. No Paper-Finder-,
  Theorizer-, or S2-specific logic lives here.
- `ingest.py` -- `ingest_paper_finder(doc, *, link_to, config, artifact_path=None)
  -> ImportReport`. A marshal-out module that imports `execute_tool` (lazily,
  function-local, mirroring `wheeler/validation/ledger.py`). Writes route through
  `execute_tool` for triple-write; reads use the same cached backend. Imports the
  shared `_link_once` / `_edge_exists` / index / read helpers from `_marshal.py`
  and keeps only Paper-Finder-specific logic (`ingest_paper_finder`,
  `_ingest_one_paper`, the `asta:paper-finder` service tag). When
  `artifact_path` is given it calls `register_output_artifact` and links each
  Paper `WAS_DERIVED_FROM` the artifact (best-effort, link_once-guarded).
- `artifacts.py` -- `register_output_artifact(path, *, execution_id, service,
  config, node_type="dataset", run_id="", benchmark=None, description="") ->
  str | None`. A marshal-out module: it (1) COPIES the ephemeral `-o` dump into a
  durable raw store at `.wheeler/asta/raw/<service-slug>/<key>.json` (key is the
  service `run_id` when present, else a content sha; path-dedupe, never
  re-copies), then (2) registers the SAVED file as a graph node via
  `ensure_artifact` (function-local `execute_tool` import) and links it
  `WAS_GENERATED_BY` the run Execution (reusing `_link_once` from `_marshal.py`). The
  node TYPE is per-adapter, declared by the caller via `node_type` and routed
  through `ensure_artifact`'s `artifact_type` override (a `.json` dump has no
  extension rule, so it would default to Document without the override):
  **Theorizer output is synthesized WRITING, so its raw node is a Document (W-);
  Paper Finder output is structured reference records, so its raw node is a
  Dataset (D-)**. Reserve Dataset for genuine data or recordings. `ensure_artifact`
  forwards neither `service` nor `custom`, so the service tag and the benchmark
  bag (`run_id`, `cost`, `time`, `model`) are stamped via a follow-up
  `update_node` (service is a first-class NodeBase field; benchmark scalars
  flatten to queryable `custom_<key>` props). Best-effort: ANY failure returns
  `None` and logs a warning, never raises, so an artifact problem cannot break
  ingest. Returns the artifact node id.
- `theorizer.py` -- `parse_theorizer(doc) -> (list[TheoryRecord], RunMeta)` and
  `ingest_theorizer(doc, *, link_to, config, artifact_path=None) -> ImportReport`.
  A marshal-out module parsing the REAL Theorizer A2A-Task shape (artifacts
  dispatched on `metadata.type`: theory / novelty / extraction). Each theory
  becomes a parent `Finding(artifact_type="theory")`; each law SECTION a
  `Hypothesis` (`CONTAINS`), its body the `custom_rationale`, its novelty verdict
  the `custom_novelty` (NEVER `status`); supporting papers `SUPPORTS` the law
  Hypothesis, conflicting papers `CONTRADICTS` the theory Finding; predictions
  land in `custom_predictions`. Theories/hypotheses dedupe on a content hash,
  papers on `corpus_id`. Imports `execute_tool` lazily (function-local) and
  reuses `_marshal.py`'s `_link_once` / `_find_paper_by_corpus_id` /
  `_paper_exists` / `_find_execution` helpers + the shared corpus_id index.
- `cli.py` -- `integrate_app` Typer sub-app, one verb: `ingest <tool> <artifact>
  [--link-to ID]`. Registered in `wheeler/tools/cli.py` guarded by try/except.
  Note: the generic `integrate` CLI currently lives here and moves up to
  `wheeler/integrations/` when the contract engine is extracted (Phase 3).

## Invariants

- **Chokepoint.** The marshal-out modules (`ingest.py`, `theorizer.py`,
  `semantic_scholar.py`, `artifacts.py`) plus the shared `_marshal.py` are the
  only callers of `execute_tool`, and each imports it lazily (function-local).
  `_marshal.py` holds the shared read/link/dedupe helpers (`_load_index` /
  `_save_index` / `_find_paper_by_corpus_id` / `_find_execution` /
  `_paper_exists` / `_edge_exists` / `_link_once` + `ImportReport`); the four
  adapters import them from there rather than from `ingest.py`. This keeps
  `graph_tools/` asta-free and preserves strict layering. `transport.py` and
  `schemas.py` have no graph dependency.
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
- **Citations link via CITES + Execution provenance, never RELEVANT_TO the
  question.** For the Semantic Scholar `citations` sub-kind, a citing paper links
  ONLY via `citingPaper -[CITES]-> target`, `WAS_GENERATED_BY` the run Execution,
  and `WAS_DERIVED_FROM` the raw node. A citing paper is NOT relevant to the
  question, so `link_to` (RELEVANT_TO) is NOT applied to citing papers. Papers are
  reference entities that are never orphans (per /wh:close and /wh:graph-link):
  the CITES edge plus Execution provenance is their linkage. RELEVANT_TO is
  applied only to get / search / snippet results, which ARE relevant to the
  question.
- **Sequential writes.** Never `asyncio.gather`. `execute_tool` reuses one
  cached backend singleton and Neo4j forbids concurrent queries.
- **One Execution per run, idempotent.** Each run gets one Execution (kind
  `paper-search` / service `asta:paper-finder`, or kind `theory-generation` /
  service `asta:theorizer`), not one per output node. `session_id` (the stable
  run id) correlates everything written in one turn. The Execution itself dedupes
  on `(service, session_id)` via `_find_execution`: re-ingesting the same
  artifact REUSES the existing Execution rather than creating a duplicate node
  and a second `WAS_GENERATED_BY` fan-in. Both adapters stamp `custom_run_id` on
  the Execution (theorizer also `custom_cost` / `custom_time`) so runs are
  benchmarkable by one query shape.
- **Stale-index guard.** The persisted corpus_id / hypothesis / theory id
  indices are only trusted when the node still lives in the graph. A hit is
  verified with an existence read (`_paper_exists` / `_finding_exists` /
  `_hypothesis_exists`) before reuse; a dead id (deleted or pruned node) is
  dropped from the index so resolution falls through to a fresh read or create.
  Without this guard a stale id would make `link_once` target a missing node and
  SILENTLY DROP the SUPPORTS/CONTRADICTS edge, losing provenance.
- **Every service output is an artifact.** The raw `-o` JSON dump is COPIED into
  the durable raw store (`.wheeler/asta/raw/<service-slug>/<key>.json`) and the
  SAVED file is registered as a graph node via `register_output_artifact`, with
  the node type matching the artifact nature (Document for Theorizer synthesized
  writing, Dataset for Paper Finder structured records). Edges added:
  `Artifact -[WAS_GENERATED_BY]-> Execution` (the run that produced it) and each
  generated node `-[WAS_DERIVED_FROM]-> Artifact` (so every node chains back
  through the raw output to the service run). Both are `link_once`-guarded; the
  durable save dedupes on path and `ensure_artifact` dedupes on path, so
  re-ingest creates no duplicate node or edges. Artifact registration is
  best-effort and never aborts ingest.
- **Failure isolation.** A failed or canceled CLI run writes nothing. Retries,
  auth, and timeouts stay inside the asta CLI.

## Conventions

- `from __future__ import annotations`; `logging.getLogger(__name__)`; async for
  graph I/O.
- Add no LLM-provider SDK. Never use em dashes.
