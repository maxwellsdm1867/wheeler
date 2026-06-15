---
name: wheeler-service-creator
description: >-
  Scaffold a NEW Wheeler service adapter that integrates an external tool into
  Wheeler end to end. Reach for this whenever the user wants to "create a wheeler
  service", "add a new tool adapter", "scaffold an integration", "wrap a service
  for wheeler", "onboard <some CLI/API/agent> into the graph", "ingest a new
  tool's output", or otherwise connect an external research tool (a search API, a
  generator, an analyzer, an agent card) to Wheeler so its results land in the
  knowledge graph with provenance, even if they do not say the word "adapter".
  Given the tool (interview the scientist, or read its `--help` / agent card), it
  produces four pieces: (a) the declarative registry contract the router reads
  (`.wheeler/services.yaml` or the bundled default), (b) a marshal-out ingest
  module wired to the shared `_marshal.py` helpers with BOTH provenance sides
  (`Execution -[USED]-> inputs`, produced nodes `-[WAS_GENERATED_BY]->
  Execution`), (c) the marshal-in act `/wh:<provider>-<tool>` that reads graph
  context, passes `--used` source ids, and shells out, and (d) a parse-unit +
  live-Neo4j e2e test stub. A bundled scaffolder emits the skeleton files; the
  human then captures one real output, fills the parser against it, and runs the
  adversarial review to land it. Do NOT trigger for RUNNING an existing adapter
  (that is the `/wh:asta-*` acts), for graph lookups or queries, or for generic
  coding unrelated to wiring up a new external service.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Wheeler service creator

You scaffold a new Wheeler service adapter from a tool. A tool becomes a
declarative **contract** (one manifest entry the registry reads); a command opts
in via a flag; a run is one Execution whose wiring has THREE parts: structural
inputs (`USED`), structural outputs (`WAS_GENERATED_BY`), and SEMANTIC wiring of
the new outputs to the EXISTING graph (the Wheeler relationships, a judgment call
that lives in the act, not the parser). The Asta adapters are instance #1 and
your concrete template. You produce the four pieces, then hand the scientist a
short to-do list: capture one real output, fill the parser against it, run the
adversarial review, land it.

You write SKELETONS, not finished adapters. The parser is tool-specific and can
only be written against a real captured output, which you do not have at scaffold
time. Your job is to lay down every piece of the structure correctly so the human
fills one function (`parse_<tool>`) and reviews.

## Two load-bearing ideas you must get right

Everything below is in service of these two. Read them first.

### The registry reads the contract; the adapter does not hardcode the provider

The contract you write is DATA, read by `wheeler/integrations/registry.py`:

- `load_services(config)` returns every parsed `ServiceContract` (id, provider,
  name, description, kind, act, cost, available, when, plus opaque `inputs` /
  `output`). It reads the USER override at `<project_root>/.wheeler/services.yaml`
  when present, else the bundled default `wheeler/integrations/services.default.yaml`.
  The user file WINS (it is not merged with the default). Pure read: no graph, no
  network, never raises; a malformed entry is skipped and logged.
- `available_services(config)` runs each contract's `available` shell probe and
  returns only the ones that pass.

The router act `/wh:asta` already consumes this (it lists only available services
and routes by `when` / `description`, warning on `cost`). So your new service
becomes routable the moment its contract entry exists and its probe passes. You
do NOT add the new service to any hardcoded table; you add a contract entry and
the registry surfaces it. Whether you append to the user `.wheeler/services.yaml`
or the bundled `services.default.yaml` depends on scope: a project-local service
goes in the user file; a service that should ship with Wheeler goes in the
default (and then `sync_data` is not involved, the manifest is package data).

### Wiring has THREE parts, and a complete adapter does all three

A service call is ONE Execution. Its wiring has three parts. The first two are
STRUCTURAL provenance (mechanical, in the parser); the third is SEMANTIC (a
judgment call, in the act). An adapter that does only the first two is
incomplete.

```
                  (3) SEMANTIC: new outputs vs the EXISTING graph
                       SUPPORTS / CONTRADICTS / RELEVANT_TO / CITES
                                       |
input  -[USED]<-  Execution  ->[WAS_GENERATED_BY]  output  - - - - ->  existing graph node
        (1) structural input            (2) structural output
```

1. **Structural input (`USED`)**: the marshal-in built the tool payload FROM
   graph nodes (the question, seeded Findings, a Dataset path). The act passes
   those ids as `--used`; the ingest records `Execution -[USED]-> each input`
   via `_record_used` (existence-guarded, link_once, never fabricates a missing
   id).
2. **Structural output (`WAS_GENERATED_BY`)**: every node the parser PRODUCED
   this run (Findings, Hypotheses, the raw artifact node) is generated by the
   Execution. The raw node is wired by `register_output_artifact`; the produced
   graph nodes by `_record_generated` (or inline `_link_once(produced_id,
   "WAS_GENERATED_BY", exec_id)`), which the scaffolded skeleton calls for you.
   The ONE exception: **Papers are reference entities** (per `/wh:close`,
   `/wh:graph-link`), so they carry NO `WAS_GENERATED_BY`; a paper the knowledge
   was derived FROM is an INPUT, so it gets `Execution -[USED]-> paper` instead.
3. **Semantic wiring (`SUPPORTS` / `CONTRADICTS` / `RELEVANT_TO` / `CITES` /
   ...)**: the new outputs connected to what was ALREADY in the graph, a result
   `SUPPORTS`/`CONTRADICTS` an existing Hypothesis, a new Hypothesis
   `CONTRADICTS` one already in the graph, a Finding `RELEVANT_TO` an open
   Question, a Paper `CITES`. This is JUDGMENT: it means comparing the new
   outputs against the current graph, so it lives in the marshal-in ACT
   (post-ingest, via `link_nodes`), NOT in the mechanical parser. **Draw the
   line carefully**: the deterministic ingest DOES wire the edges KNOWN FROM THE
   SERVICE OUTPUT (the Theorizer states which papers support vs contradict ITS
   own laws, a citations run knows its `--target`); those are part 2's structural
   bucketing, asserted from the artifact. Part 3 wires NEW outputs to PRIOR graph
   nodes the service never saw, which no parser can know.

Parts 1 and 2 are why the chain is transitive off ONE Execution:
`output -[WAS_GENERATED_BY]-> Execution -[USED]-> input`, with no
per-input/per-output edges. The adversarial review checks all three: both
structural sides, AND that the act carries a post-ingest semantic-wiring step.

## When this fires

The scientist wants to wrap an external tool so its output lands in the graph
with provenance. Examples: a new Asta sub-tool, a different literature API, a
domain analyzer that emits JSON, an agent with an A2A card. Read the spec
`docs/asta-engine-spec.md` section 3 for the design intent.

Do NOT fire for running an existing adapter (that is the `/wh:<provider>-<tool>`
act itself), for graph queries, or for generic coding.

## The template you are copying

Study these before you scaffold. They are the canonical example; mirror their
structure, their docstrings, and their invariants. All paths are relative to the
repo root.

- `wheeler/integrations/asta/_marshal.py` -- the SHARED marshal-out helpers
  (`ImportReport`, the persisted corpus_id index, `_link_once` / `_edge_exists`,
  `_node_exists` / `_record_used` for input-side provenance). Your adapter
  imports these; it does NOT reimplement them.
- `wheeler/integrations/asta/ingest.py` -- Paper Finder, the simplest adapter
  (output is a Dataset of reference records).
- `wheeler/integrations/asta/theorizer.py` -- the richest adapter (parses an A2A
  Task into a Finding/Hypothesis/Paper subgraph, output is a Document).
- `wheeler/integrations/asta/semantic_scholar.py` -- a multi-shape adapter
  (auto-detects sub-kind, output is a Dataset).
- `wheeler/integrations/asta/artifacts.py` -- `register_output_artifact`: durably
  saves the raw `-o` dump and registers it as a Document (W-) or Dataset (D-)
  node `WAS_GENERATED_BY` the run Execution.
- `wheeler/integrations/asta/cli.py` -- the single `wheeler integrate ingest`
  verb that the act shells out to (`--link-to`, `--used`, `--target`).
- `wheeler/integrations/registry.py` + `services.default.yaml` -- the registry
  that reads service contracts (`load_services` / `available_services`) and the
  bundled default manifest your new entry mirrors.
- `.claude/commands/wh/asta.md` -- the ROUTER act. It reads the registry (not a
  hardcoded table) and dispatches the matching service act. Study how it lists
  only available services and routes by `when` / `cost`; your new service plugs
  into it for free once its contract exists.
- `.claude/commands/wh/asta-lit.md`, `asta-theorize.md`, `asta-scholar.md` -- the
  marshal-in acts. Each reads graph context, picks a link target, shells out to
  the tool CLI, then calls `wheeler integrate ingest ... --used <ids>` (part 1,
  the structural INPUT side; the ingest wires part 2, the structural OUTPUT side,
  `WAS_GENERATED_BY`). Each then carries a post-ingest "Wire semantics to the
  existing graph" step (part 3): it reads the new ids plus the existing graph and
  applies the `SUPPORTS` / `CONTRADICTS` / `RELEVANT_TO` / `CITES` edges to PRIOR
  nodes via `link_nodes`, confirming each judgment with the scientist.
- `tests/integrations/asta/test_theorizer.py` -- the test template: parse-unit
  tests (no live call) PLUS a live-Neo4j e2e class with the per-run `e2e_tag`
  hermetic-teardown convention. Its e2e assertions check BOTH provenance sides
  (USED edges from the run, WAS_GENERATED_BY edges into it).

## Two ways to lay down the skeleton

There is a bundled scaffolder, `assets/scaffold_service.py`, that writes all four
skeleton files deterministically from a contract. Prefer it: hand-copying the
boilerplate from the templates is slow and easy to get subtly wrong (a dropped
provenance edge, a missing invariant), and the scaffolder bakes in the
load-bearing structure (the lazy `execute_tool` import, both provenance helpers,
the hermetic-teardown test) so you only have to fill the one thing it cannot
know: the parser.

**Fast path (recommended).** Gather the contract (Step 1), then run the
scaffolder once. It is stdlib-only, writes nothing it cannot, and is idempotent
(it appends the registry entry without clobbering, and will not overwrite an
existing file unless you pass `--overwrite`):

```bash
# from the repo root; use plain `python` if ./.venv is absent
./.venv/bin/python .claude/skills/wheeler-service-creator/assets/scaffold_service.py \
  --provider <provider> --tool <tool> --name "<Name>" \
  --description "<one line>" --raw-node <document|dataset> \
  --nodes "<Comma,Separated,NodeTypes>" \
  --cli '<the exact CLI the act runs, with -o /tmp/<tool>.json>' \
  --available "<probe command>" --cost "<cost string>" --when "<router phrase>"
```

Add `--dry-run` first to preview the paths it will touch. It prints one line per
file (wrote / appended / skipped). Then read each emitted file, confirm it
matches the contract, and move to the per-file steps below to UNDERSTAND what was
generated and to fill the gaps (the parser body, the CLI verb wiring in Step 4,
the `_data` sync in Step 5). The scaffolder does not touch `cli.py` or run
`sync_data`, so Steps 4 and 5 are still yours.

**Manual path.** If the scaffolder is absent or the tool is unusual enough that
the skeleton would not fit, write the four files by hand from the templates. The
per-step sections below are the spec either way: they describe exactly what each
file must contain, which is also what the scaffolder emits.

## Step 1: gather the contract

Interview the scientist, or read the tool's `--help` / agent card. You need a
small contract dict. Ask only for what you cannot infer; default the rest.

- **provider**: the family (e.g. `asta`, `s2`, `myorg`). Lower-case, slug-safe.
- **tool**: the specific tool (e.g. `paper-finder`, `theorizer`, `datavoyager`).
  Lower-case, slug-safe. Together they give the service id
  `<provider>-<tool>`, the service tag `<provider>:<tool>`, the act
  `/wh:<provider>-<tool>`, and the module `wheeler/integrations/<provider>/<tool>.py`.
- **name** + **description**: human label and one line of what it does.
- **kind**: `shell-out` (a CLI you invoke, the common case) or `local`.
- **cli_invocation**: the exact command the act runs, with `-o <tempfile>` so it
  dumps JSON (e.g. `asta literature find "$QUERY" -o /tmp/<tool>.json`). Capture
  the auth requirement and rough cost/time.
- **availability**: the probe command whose zero exit means the tool is usable
  (e.g. `asta auth status`). The registry filters out services whose probe fails.
- **cost**: a short human string (e.g. `"expensive (~$7, ~20min)"` or `"free"`).
- **when**: a one-line trigger phrase for the router (e.g. `"hypothesis or
  theory generation"`).
- **inputs (ports)**: the graph nodes the marshal-in synthesizes the request
  FROM. Each is `{name, source, required}` where `source` is `query`
  (the sharpened question), `findings` (seeded Finding ids), `datasets`
  (Dataset paths), etc. These are exactly the ids that become `--used` arguments.
- **output shape**:
  - `raw_node`: `document` (synthesized WRITING, like Theorizer) or `dataset`
    (structured reference RECORDS, like Paper Finder / Semantic Scholar). Pick
    `document` for prose/theories, `dataset` for records/data. NEVER call
    everything a Dataset.
  - `nodes`: the Wheeler node types the parser produces (e.g.
    `[Finding, Hypothesis, Paper]`, or `[Paper]`).
  - `dedupe`: the natural key per produced node type (corpus_id for Papers, a
    content hash for nodes with no external id).
  - `edges`: the semantic relationships (SUPPORTS, CONTRADICTS, CITES,
    APPEARS_IN, RELEVANT_TO, AROSE_FROM, CONTAINS) and which node pairs they join.

Write the contract back to the scientist in one block and confirm it before
generating. A wrong contract means wrong skeletons.

## Step 2: the service contract (registry entry)

Append (do not overwrite) an entry under `services:`. Choose the manifest by
scope:

- a PROJECT-LOCAL service -> the user override `<project_root>/.wheeler/services.yaml`
  (create it with a `services: []` root if absent; the user file wins over the
  default and is not merged with it),
- a service that should SHIP with Wheeler -> the bundled
  `wheeler/integrations/services.default.yaml` (package data; no `sync_data`).

Mirror the existing entries exactly (`registry._REQUIRED_FIELDS` are all of `id,
provider, name, description, kind, act, cost, available, when`; a missing one is
skipped and logged, so the service silently will not appear):

```yaml
  - id: <provider>-<tool>
    provider: <provider>
    name: <Name>
    description: <one line>
    kind: shell-out                 # shell-out | local
    act: /wh:<provider>-<tool>
    cost: "<cost string>"
    available: "<probe command>"    # filtered out on non-zero exit
    when: "<router trigger phrase>"
    inputs:                          # the USED set + the marshalling map
      - { name: <port>, source: <query|findings|datasets>, required: true }
    output:
      raw_node: <document|dataset>
      nodes: [<NodeType>, ...]
```

This is the contract. Identity + ports + output shape, NOT a field-map language:
the parser stays tool-specific Python. `inputs` and `output` are opaque to the
registry (it does not interpret them; the adapter does), so they are optional for
routing but valuable as documentation of the marshalling map. Once this entry
exists and its probe passes, `available_services()` surfaces it and `/wh:asta`
routes to it: you have NOT touched any hardcoded provider table. Confirm by
running the registry: `./.venv/bin/python -c "from wheeler.config import
load_config; from wheeler.integrations.registry import available_services;
print([c.id for c in available_services(load_config())])"`.

## Step 3: the marshal-out ingest skeleton

Create `wheeler/integrations/<provider>/<tool>.py` (and an empty
`wheeler/integrations/<provider>/__init__.py` if the provider package is new).
Copy the structure of `theorizer.py` (for a node-subgraph output) or `ingest.py`
(for a flat record output). The scaffolder emits all of the following; if you are
writing by hand, this is the checklist (each item exists for a reason given
inline, so you can adapt it intelligently rather than copy it blindly):

1. Open with a docstring stating the REAL output shape (fill the placeholder once
   a real output is captured), the bucketing/mapping, and the standing
   invariants verbatim from the template:
   - Defensive: every step tolerates missing pieces, counts and skips, never
     raises.
   - Sequential writes only. Never `asyncio.gather`: `execute_tool` reuses one
     cached backend singleton and Neo4j forbids concurrent queries.
   - link_once: every edge is existence-guarded because the backend's
     `create_relationship` is a bare CREATE that duplicates on re-run.
   - One Execution per RUN, tagged service `<provider>:<tool>`.
2. Define `_SERVICE_TAG = "<provider>:<tool>"` and
   `_RAW_NODE_TYPE = "<document|dataset>"`.
3. Import the SHARED helpers from `_marshal.py`
   (`ImportReport`, `_find_execution`, `_link_once`, `_load_index`,
   `_paper_exists`, `_record_used`, `_save_index`, ...). Do NOT reimplement them.
4. Provide a pure `parse_<tool>(doc) -> (records, run_meta)` that is defensive and
   NEVER raises (leave the body a clearly-marked `# TODO: fill against a real
   captured output` stub returning `([], RunMeta())`, with the small coercion
   helpers `_as_str` / `_as_float` / `_first` copied in so the human only writes
   the shape-walk).
5. Provide `async def ingest_<tool>(doc, *, link_to=None, config, artifact_path=None,
   used_inputs=None) -> ImportReport`. The order below matters because each step
   depends on the Execution id minted at the top:
   - `from wheeler.tools.graph_tools import _get_backend, execute_tool` (lazy,
     function-local: this is the ONLY `execute_tool` caller, so the triple-write
     + write-receipt + trace-id + embedding wiring fires, and `graph_tools/`
     stays adapter-free, mirroring `wheeler/validation/ledger.py`).
   - dedupe-or-create ONE Execution per run via `_find_execution` (idempotent),
     tagged `service=_SERVICE_TAG` with a stable `session_id`.
   - record INPUT-side provenance: `report.used += await _record_used(backend,
     config, exec_id, used_inputs)` (existence-guarded, link_once, never
     fabricates a missing id). This is half of the two-sided chain.
   - register the raw output via `register_output_artifact(artifact_path,
     execution_id=exec_id, service=_SERVICE_TAG, config=config,
     node_type=_RAW_NODE_TYPE, ...)` (best-effort, never raises). This wires the
     raw node's OUTPUT-side `WAS_GENERATED_BY` edge.
   - bucket each parsed record into its nodes, every WRITE through
     `execute_tool`, every edge through `_link_once`. COLLECT the produced node
     ids (excluding Papers).
   - record OUTPUT-side provenance for the produced graph nodes: `await
     _record_generated(backend, config, exec_id, produced_ids, report)` (or an
     inline `_link_once(produced_id, "WAS_GENERATED_BY", exec_id)` per node). The
     scaffolded skeleton already lays down `_record_generated` and the
     produced_ids loop; do not drop it. Wiring only the input side is a bug.
   - apply the Paper rule when the output references papers: papers dedupe on
     `corpus_id`, are REFERENCE ENTITIES (NO `WAS_GENERATED_BY`, so they are NOT
     in `produced_ids`), and if the produced knowledge was DERIVED from a paper,
     the run `Execution -[USED]->` that paper (input side).
   - return the `ImportReport` with created / deduped / linked / skipped / used
     counts.

Every graph write routes through `execute_tool`. Never write the backend or the
files directly. The acceptance bar for the ingest is BOTH provenance sides:
`Execution -[USED]->` each input AND each produced node `-[WAS_GENERATED_BY]->`
the Execution.

## Step 4: register the CLI verb

The act does not call Python directly; it shells out to `wheeler integrate ingest
<tool> <artifact.json> --link-to <id> --used <ids>`. Wire the new tool into
`wheeler/integrations/asta/cli.py` (or a sibling `<provider>/cli.py` if the
provider is new and gets its own sub-app):

1. Add the tool name (and any alias) to the `_INGESTERS` set.
2. Add a dispatch branch that lazily imports `ingest_<tool>` and calls it inside
   `asyncio.run(...)`, forwarding `link_to`, `config`, `artifact_path=str(artifact)`,
   and `used_inputs`. Keep the existing `--used` parsing (comma-split, blanks
   dropped, normalized to `None`).

If you create a new provider sub-app, register it on the top-level Typer app the
same way `integrate_app` is registered, and keep one `ingest` verb only (no
send/dispatch verb: Wheeler must not become a second router that invokes the tool).

## Step 5: the marshal-in act

Create `.claude/commands/wh/<provider>-<tool>.md`, copying `asta-theorize.md` (or
`asta-lit.md` for a flat search). The act IS the system prompt. It MUST:

- Frontmatter: `name: wh:<provider>-<tool>`, a narrow `description` (the trigger
  vocabulary, demanding tool + knowledge-graph words so it does not auto-fire on
  generic coding), `argument-hint`, and `allowed-tools` limited to `Read`, the
  tool's `Bash(<tool>:*)`, `Bash(wheeler integrate:*)`, the read-only MCP tools
  the preflight needs (`mcp__wheeler_core__search_context`, the relevant
  `mcp__wheeler_query__query_*` including `query_open_questions` and
  `query_hypotheses` for the semantic-wiring step), and
  `mcp__wheeler_mutations__link_nodes` (the only write the act needs, for part 3
  below).
- **Preflight**: confirm the tool is installed (its `--version` / availability
  probe); stop cleanly if not. Read graph context with `search_context` and the
  typed `query_*` to SHARPEN the request and pick a link target. "Do not invent
  results / theories. Do not do the scientist's thinking."
- **Choose the request + link target**: the request is `$ARGUMENTS` or derived
  from the active question; pick at most one `Q-`/`PL-` link target.
- **Run**: the exact `cli_invocation` writing to a temp file. A non-zero exit
  reports and stops (a failed run writes nothing to the graph by design).
- **Ingest**: `wheeler integrate ingest <tool> <tempfile> --link-to <id> --used
  <id>,<id>`. Spell out that `--used` carries the graph node ids the request was
  built FROM (the link target plus any seeded source ids), recording
  `Execution -[USED]-> each input` so every result traces back to the graph
  context that shaped it. State that the verb is idempotent.
- **Wire semantics to the existing graph** (part 3, the judgment step): a brief
  post-ingest section. State that the ingest is STRUCTURALLY complete but does
  not connect the new outputs to what was ALREADY in the graph, because that is a
  judgment call, so it lives here in the act. The step: read the new node ids
  from the ingest report and the existing graph (`search_context`,
  `query_open_questions`, `query_hypotheses`, `query_findings`); identify the
  `SUPPORTS` / `CONTRADICTS` / `RELEVANT_TO` / `CITES` edges between NEW outputs
  and EXISTING nodes; confirm the judgment calls with the scientist; apply via
  `mcp__wheeler_mutations__link_nodes`. Keep it brief. Tune the edges to the
  node types this tool produces (a theory-generator weights new Hypotheses vs
  existing Hypotheses `SUPPORTS`/`CONTRADICTS`; a literature tool weights new
  Papers `RELEVANT_TO`/`CITES`).
- **Report**: relay the printed summary in one or two sentences; suggest the
  `query_*` filters to browse the new nodes. Never editorialize the science.
- **No em dashes** anywhere.

After writing acts you MUST sync the `_data` mirror so the shipped package
matches (the same command exists in `.claude/commands/wh/` and
`wheeler/_data/commands/`): run
`python -c "from wheeler.installer import sync_data; sync_data()"`.

## Step 6: the test stub

Create `tests/integrations/<provider>/test_<tool>.py` (and an empty
`__init__.py`), copying `tests/integrations/asta/test_theorizer.py`. Two layers,
NEITHER making a live tool call:

1. **Parse-unit** (`class TestParse<Tool>`): assert `parse_<tool>` against a
   trimmed REAL fixture in `tests/integrations/<provider>/fixtures/`, plus
   shape-drift / garbage tolerance (a non-dict, an empty artifacts list, missing
   keys -> `([], RunMeta())`, never raises). Leave the fixture path and the
   expected-count constants as clearly-marked TODOs the human fills once a real
   output is captured.
2. **Live-Neo4j e2e** (`class TestIngest<Tool>E2E`): skipped automatically when
   Neo4j is unreachable. Follow the per-run `e2e_tag` hermetic-teardown
   convention EXACTLY:
   - A module-scoped `e2e_config` fixture pointing at local Neo4j, a
     `neo4j_available` probe, and a `_reset_driver_singleton` autouse fixture
     (copy them verbatim from `test_theorizer.py`).
   - A `_cleanup_<tool>(e2e_config, e2e_tag)` helper whose teardown is EXACTLY
     `MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n` and nothing else. NEVER
     delete by `service` or `corpus_id`: the e2e config runs on the SHARED
     default namespace where production nodes carry the same service tag and the
     same corpus_ids, so a service-scoped or corpus_id-scoped delete would wipe
     real user data.
   - An autouse `_skip_and_cleanup` fixture that `monkeypatch.chdir(tmp_path)`
     (so the on-disk indices and the durable raw store are isolated per test),
     mints a per-run unique tag `f"integrations_e2e_{uuid.uuid4().hex}"`, and
     pre-cleans + post-cleans on it.
   - A `_tag_all(e2e_config, report)` helper that tags ONLY the nodes THIS run
     created, scoped off the returned `report` ids (Execution, artifact, every
     Paper) PLUS the run's `WAS_GENERATED_BY` fan-in. NEVER tag by service or
     corpus_id. Papers are reference entities (no `WAS_GENERATED_BY`), so they
     are tagged by `report.paper_ids`, not via the fan-in.
   - One test that ingests the fixture, tags, asserts the bucketing subgraph
     (node counts, edge counts, custom fields) scoped to THIS run's `e2e_tag`,
     and asserts BOTH provenance sides: at least one `Execution -[USED]-> input`
     edge (when `used_inputs` were passed) AND each produced node
     `-[WAS_GENERATED_BY]-> Execution` (and that Papers carry NO
     `WAS_GENERATED_BY`). Then RE-INGEST the same artifact and assert idempotency
     (identical counts, `created==0`, no duplicate USED / WAS_GENERATED_BY
     edges on the second pass).

## Step 7: hand off to the human

You scaffolded the structure; the parser is the one thing only a real output can
teach. Tell the scientist, in this order:

1. **Capture one real output**: run the tool once for real
   (`<cli_invocation>`), save the `-o` JSON, and drop a trimmed copy under
   `tests/integrations/<provider>/fixtures/<tool>_real_sample.json`.
2. **Fill the parser**: write `parse_<tool>` against that captured shape, and
   fill the fixture path + expected-count constants in the test. The skeleton's
   defensive helpers and invariants are already in place; only the shape-walk is
   missing.
3. **Run the tests**: `./.venv/bin/python -m pytest
   tests/integrations/<provider>/test_<tool>.py -q` (the e2e class needs a live
   Neo4j; it skips otherwise).
4. **Adversarial review**: run the repo's adversarial-review workflow on the
   adapter (a fresh reviewer agent re-checks every claim: provenance edges, the
   Paper reference-entity rule, the `--used` input provenance, idempotency, the
   hermetic teardown) before landing. Adding a service is then: run the creator
   -> fill the parser -> review -> land.

Report back the four files you created (the `services.yaml` entry, the ingest
skeleton, the act, the test stub) plus the CLI verb wiring, and the exact to-do
list above. Never use em dashes.
