# Asta x Wheeler: next-phases roadmap (draft)

Status 2026-06-15. Forward plan after Phase 1 (Paper Finder, committed) and Phase 2
(Theorizer, in progress, mapping being refined against a real run).

Every next adapter REUSES the marshal-out machinery already built:
`transport.run_asta`, `register_output_artifact` (every output is an artifact),
`_link_once` (edges never duplicate), the `service` tag, the `custom` queryable bag,
`corpus_id` dedupe, one Execution per run, sequential writes, all through `execute_tool`.
The only new work per adapter is the parser + the output->entity bucketing.

## Phase 3a: Semantic Scholar suite (recommended next: mechanical, cheap, high value)

Commands: `asta papers get | citations | snippet-search | search | author`. All return
paper metadata in the same shape family as Paper Finder (title, abstract, authors, year,
venue, citationCount, url, corpusId-able), so the Paper bucketing + corpus_id dedupe +
custom bag carry over directly.

Output -> graph:
- `get` / `search` -> Paper nodes (reuse the Phase 1 path verbatim).
- `citations` -> for target paper T, each citingPaper C: `add_paper(C)` then
  `C -[CITES]-> T`. This is the one that BUILDS THE CITATION GRAPH. Cheap, high value.
- `snippet-search` -> text excerpts as evidence: a Finding (artifact_type="snippet")
  linked `APPEARS_IN` its Paper, or attached as a custom field. Gives grounded quotes.

Effort: low (reuses Phase 1). Value: high (citation graph + targeted lookup + snippet
evidence). No live-shape risk (shapes already known from the CLI). This is the natural
3rd adapter, which triggers Phase 3b.

## Phase 3b: extract the contract engine (rule of three)

After Paper Finder + Theorizer + Semantic Scholar (3 instances: 2 mechanical, 1 judgment)
extract the genuinely shared ~20% per plan section 8 Phase 3: a tiny ToolContract (tool
name, service tag, dedupe key, schemaVersion fingerprint, declared node-types and
relationships), the schema-fingerprint guard, upsert-by-key, `register_output_artifact`,
`_link_once`, session binding, and a post-ingest `validate_contract`. Minimal registry.
No declarative field-map DSL (YAGNI). Do this only once the three adapters exist.

## Phase 4: DataVoyager (analyze-data): highest research value

`asta analyze-data submit "<query>" <files...> [--context-id]` -> an A2A Task whose
artifacts are the analysis outputs (narrative, code, figures, data). This analyzes the
scientist's OWN data files, so it is the highest-value integration for real research.

Output -> graph:
- One Execution (service="asta:datavoyager", kind="analysis"), `USED` the input
  Dataset(s), session bound to `context-id`.
- Each result artifact into the RIGHT bucket: figure -> Finding(artifact_type="figure")
  via ensure_artifact, code -> Script, data -> Dataset, narrative -> Finding/Document.
- Outputs `WAS_GENERATED_BY` the Execution; `WAS_DERIVED_FROM` the input datasets.

Needs a live-shape capture of the Task artifacts JSON before finalizing the parser
(same caution as Theorizer). Higher effort: A2A async + file upload. Build after the
engine (Phase 3b) so it lands as a contract.

## Phase 5+: as the work calls for it

- AutoDiscovery: ingest run/experiment results as Execution -> Finding chains
  (Bayesian-surprise discoveries become Findings with confidence; MCTS iterations as
  provenance). Gives the discovery loop the cross-run memory it lacks.
- research-step beads import: walk a `.beads/` epic DAG and replay each closed task as
  the matching `add_*` + links. The DAG is near-isomorphic to Wheeler's node + provenance
  model (scope/definitions/literature_review/hypothesis/experiment_design/evidence/
  analysis/synthesis; blocks->DEPENDS_ON, parent-child->CONTAINS, discovered-from->
  AROSE_FROM). A reader, not an asta-service adapter.
- documents / local-paper-index: ingest the asta-documents YAML index (chunked PDFs) as
  Document/Paper nodes; Wheeler already has embeddings + search to layer on top.

## Cross-cutting (applies to every phase)

- Marshal-in acts (informed-by-graph): each tool gets a `/wh:asta-*` act whose prose
  reads context via `search_context` and shapes the query/question. DataVoyager gets
  dataset node paths; Theorizer gets graph Findings seeded as `extraction_results`.
- Every output is an artifact: register + auto-link (now standard in marshal-out).
- Right bucketing per output type: decided deliberately, one output type at a time,
  against the real output shape, never a guess.
