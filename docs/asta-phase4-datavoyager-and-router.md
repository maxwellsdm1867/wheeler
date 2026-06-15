# Asta Phase 4 (DataVoyager) + the Asta router (plans)

Status 2026-06-15. Designs only. Builds reuse the shipped marshal-out machinery
(`_marshal.py`, `transport.py`, `register_output_artifact`, service tag, link_once,
Execution dedupe, per-adapter raw-node type).

## Part A: DataVoyager integration (Phase 4)

### What it is
`asta analyze-data submit "<question>" <files...> [--context-id]` uploads the local
data file(s) to the caller's DataVoyager workspace (the CLI does the S3 upload), then
a multi-agent pipeline writes and EXECUTES code in a sandboxed notebook to answer the
question. `submit` returns a task id; `asta analyze-data poll <task_id>` blocks to the
final A2A Task JSON. `--context-id` continues an existing workspace. Highest research
value: it analyzes the scientist's OWN data, not the literature.

### Marshal-in (act prose, informed-by-graph)
- Tighten the question (name the dataset, phrase it as something code can answer), per
  the upstream skill. Pull the dataset path(s) from graph Dataset nodes (the scientist
  references a D- node or a file; we resolve its `path`). Never pre-upload, the CLI does.
- Bind a `context-id` to the investigation (a Plan or Question node) so follow-up
  analyses reuse the SAME DataVoyager workspace. This is the first real same-provider
  session reuse (the session-binding the design reserved as YAGNI until now).

### Transport
DataVoyager is submit-then-poll. transport runs `asta analyze-data submit ...` to get the
task id, then `asta analyze-data poll <id> --output <file>` to block to the final Task
JSON. Failure isolation unchanged: a non-completed terminal state writes nothing.

### PREREQUISITE: live-shape capture (like Theorizer)
The artifact taxonomy DataVoyager emits (`metadata.type` values for narrative / code /
figure / produced-data) is unknown until a real run. Capture one real analyze-data Task
on a small real dataset BEFORE building the parser. Needs a real data file + a paid run.

### Output bucketing (right entities, per the data-vs-synthesis rule)
The output is an A2A Task with artifacts (parser mirrors Theorizer: iterate artifacts,
dispatch on `metadata.type`). Buckets:
- One Execution: `service="asta:datavoyager"`, `kind="analysis"`, `USED` the input
  Dataset(s), `session_id = context_id`, benchmark fields (run_id/cost/time) if present.
- Narrative / conclusions -> Finding (the analysis result; `artifact_type="analysis"`).
  A long writeup -> Document (synthesized writing).
- Code the agent wrote and ran -> Script nodes (save the code to a file, register).
- Figures -> Finding(`artifact_type="figure"`) + the image saved via ensure_artifact.
- PRODUCED DATA files -> Dataset nodes (this IS genuine data -> Dataset, per the rule).
- Raw Task JSON -> the per-adapter raw node. DECISION: an analysis is synthesis-leaning
  but carries data; default Document (the analysis writeup), flag for the reviewer.
- Provenance: every output `WAS_GENERATED_BY` the Execution; the analysis
  `WAS_DERIVED_FROM` the input Dataset(s); figures/scripts/data linked to the analysis.

### Firsts this adapter introduces
First adapter to: create Script + Dataset + figure-Finding nodes; `USE` input Datasets
as provenance inputs; bind a real provider session (`context_id`); and chain follow-up
runs in one workspace. Everything else reuses the shipped helpers.

### Build sequence
1. Capture the real Task shape (paid live run on a small dataset).
2. Team build (parser + ingest + bucketing + act) -> 3-lens adversarial review (one lens
   re-runs the tests) -> reconcile to green.
3. Commit. Then a real-data end-to-end ingest like we did for Theorizer.

### Open decisions for the reviewer
Raw-node type (Document vs Dataset for a mixed analysis output); figure storage
(Finding + ensure_artifact image); how submit+poll is wrapped in transport; whether a
produced-data Dataset should be `WAS_DERIVED_FROM` the input Dataset (data lineage).

## Part B: the Asta router (`/wh:asta`)

A graph-aware router act, modeled on `/wh:start`, that picks the right Asta service for a
research intent and warns before the expensive ones. It is an act (markdown system
prompt), no Python.

### Routing table (intent -> adapter)
| Intent | Service | Act | Cost |
|---|---|---|---|
| broad literature discovery ("find papers on X", "what is known about Y") | Paper Finder | /wh:asta-lit | cheap |
| specific paper, its citations, or snippet evidence ("look up Z", "what cites Y", "find the quote about X") | Semantic Scholar | /wh:asta-scholar | cheap |
| hypothesis / theory generation ("generate theories about X", "what could explain Y", "form hypotheses") | Theorizer | /wh:asta-theorize | EXPENSIVE (~$7, ~20min) |
| analyze the scientist's own data ("analyze this CSV", "find patterns in my .mat") | DataVoyager | /wh:asta-data | paid, uploads files |

### Graph-aware suggestion (the part that earns its keep)
Before routing, read graph context (`search_context`, `graph_gaps`, `query_*`) and
suggest the most useful NEXT Asta action given the graph state, not just keyword-match:
- a Question with papers but no theories -> suggest Theorizer
- a Finding/Hypothesis with no supporting literature -> suggest Paper Finder or Sem Scholar
- a Paper with no citation graph -> suggest `asta papers citations`
- a Dataset node with an open analysis question -> suggest DataVoyager
Surface the trade-offs: Paper Finder = broad semantic discovery; Semantic Scholar =
precise lookup + citation graph; Theorizer = literature-grounded theories (expensive);
DataVoyager = code-executing analysis of your data (paid, uploads files). Always warn
before the expensive two and confirm before dispatching them.

### Implementation
A `.claude/commands/wh/asta.md` act with the routing/decision table + a "read the graph
first, then suggest" step, dispatching the chosen `/wh:asta-*` act via the Skill tool.
Complements `/wh:start` (which routes Wheeler acts); `/wh:asta` routes Asta services with
their cost warnings. Narrow trigger vocabulary so it fires on "use asta", "which asta
tool", "find/theorize/analyze with asta", not on general coding. Build it as a small
act-only change (no team needed); it can ship alongside or before Phase 4.
