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

## Plan / session lifecycle integration (the intended use; design direction)

The adapters and the `/wh:asta` router are tools; the Wheeler research lifecycle is the
orchestration. The intended use is plan-driven, not standalone:

```
/wh:plan "sharpened question"
   -> Plan node (PL-) + .plans/ file: question, sub-questions, gaps
   -> a step that needs external research (literature / theories / data analysis)
       -> /wh:asta (router), with the PLAN context
           -> reads the plan question + gaps, suggests the service, warns on cost
           -> runs the adapter; outputs link to the PLAN
/wh:execute  -> runs the plan, launching Asta steps as it goes
/wh:close    -> the Plan + its Asta Executions + outputs are one provenance chain
```

Already in place: every adapter takes `--link-to <id>` which accepts a Plan id (results land
RELEVANT_TO the Plan); the `/wh:asta` router exists; every run produces a service-tagged
Execution with provenance.

Needed (later):
1. Tie the Asta run Execution into the Plan (AROSE_FROM the Plan, or the Plan CONTAINS the step
   Execution), so the run is part of the plan provenance chain, not just the results RELEVANT_TO it.
2. Plan-aware router: when `/wh:asta` runs inside `/wh:execute`, read the plan question/gaps to
   suggest the service for the current step (not the whole graph).
3. `/wh:plan` and `/wh:execute` offer to launch `/wh:asta` when a step needs external research
   (the plan asks whether to launch the Asta agent).

Depends on Plans being first-class graph nodes with provenance chains (the sibling pending
project `project_plan_graph_integration`); the Asta-plan integration is that project from the
Asta side. Try after the current adapters + provenance alignment land.

## Generalization: Wheeler service-extension registry (NOT Asta-specific)

The deeper architecture: do NOT hardcode providers into the commands. Orchestration lives in
the acts, and the acts read a declarative, swappable SERVICE REGISTRY. Asta is just the first
registered provider; a user who does not want it simply does not register it.

A user-editable manifest, e.g. `.wheeler/services.yaml` (ships empty; Asta optional):
```yaml
services:
  - id: asta-paper-finder
    name: Paper Finder
    description: broad semantic literature discovery, ranked
    kind: shell-out            # shell-out | local
    act: /wh:asta-lit
    cost: cheap
    available: "asta auth status"   # availability check; filtered out if it fails
    when: "find papers / what is known about X"
  - id: local-analysis
    name: Local analysis
    description: run your own script
    kind: local
    when: "you have a script / want to run it yourself"
```

The plan / `/wh:asta` (generalize to `/wh:services` or `/wh:tools`) reads the registry, lists
only what is actually available (the `available` check), and offers the user the choice: run
locally, or shell out to service X / Y, by matching the plan need against `description`/`when`.
New service = new manifest entry, zero command edits. This is "Wheeler extensions."

This closes the loop with the tool-contract / skill-creator idea from the start of the project:
the registry entry IS the lightweight contract (id, description, invocation, ports, availability,
cost). The registry is the discoverable home the contract always needed; the acts are its
consumer.

Build judgment (rule of three): the principle guides design now. One cheap principled move is to
make `/wh:asta` read a manifest instead of its hardcoded routing table (makes it swappable). The
heavy generic engine (dynamic ports, local-vs-shell-out abstraction, contract validation) waits
for a real SECOND provider, so we do not abstract at n=1.

### Commands stay service-agnostic (optional --service flag)

This applies to EVERY command, not just the router: `/wh:execute`, `/wh:plan`, and the rest stay
service-agnostic and never hardcode a provider. The single opt-in seam is an OPTIONAL flag that
points at a registered service:

```
/wh:execute                          # provider-free; runs locally / does nothing service-specific
/wh:execute --service asta-theorizer # this step shells out to a registered service
/wh:execute --use <id>               # equivalent; resolved against .wheeler/services.yaml
```

With no flag, the command is provider-free. The flag is the only place a service name appears, and
it is resolved through the registry (so an unavailable service is rejected gracefully). The command
body never names Asta or any provider. This keeps every command modular and swappable: integrating
a new service is a registry entry plus the flag, never a command edit.

## Marshal-in provenance: the payload synthesis is a relationship too

Output provenance is recorded (Execution WAS_GENERATED_BY produced nodes, USED evidence). The INPUT
side is equally a relationship to record: the marshal-in synthesizes the tool payload FROM graph
nodes (the question, the Findings seeded into Theorizer extraction_results, the gap that shaped the
query, the Dataset paths handed to DataVoyager), and that synthesis means the run USED those graph
nodes.

Record both edges:
- Execution -[USED]-> each graph node synthesized into the payload (the inputs the request was
  built from).
- Produced outputs -[WAS_DERIVED_FROM]-> those same inputs (transitive lineage).

This completes the bidirectional chain: input graph nodes (USED) -> Execution -> output nodes
(WAS_GENERATED_BY), so any Asta result traces back to the exact graph context that shaped its
request, not just the literature the service returned.

Implementation: the marshal-in act passes the source node ids it consumed (e.g. `--used <ids>` /
`--from <ids>`); the ingest records the USED edges (link_once-guarded). In the registry/contract,
each input port declares its graph source (query | findings | files | session), and the ids it
consumes become the USED set. This is the INPUT half of the tool contract finally earning its keep
(the output half already does the bucketing). Build it alongside the plan/session integration, when
the marshal-in stops being pure act prose and starts passing structured source ids.
