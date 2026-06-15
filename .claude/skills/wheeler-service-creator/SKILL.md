---
name: wheeler-service-creator
description: >-
  Scaffold a NEW Wheeler service adapter from a tool, closing the loop with the
  tool-contract idea. Given a tool (interview the scientist, or read its
  `--help` / agent card), it drafts (a) the `.wheeler/services.yaml` registry
  entry (identity, ports, output shape, availability, cost), (b) a marshal-out
  ingest skeleton `wheeler/integrations/<provider>/<tool>.py` wired to
  `_marshal.py` helpers + `register_output_artifact` (the only `execute_tool`
  caller, lazy import), (c) the marshal-in act `/wh:<provider>-<tool>` that reads
  graph context, passes `--used` source ids, and shells out, and (d) a
  parse-unit + live-Neo4j e2e test stub following the per-run `e2e_tag`
  hermetic-teardown convention. Use whenever the user wants to "create a wheeler
  service", "add a new tool adapter", "scaffold an integration", "wrap a service
  for wheeler", "ingest a new tool's output into the graph", or onboard any
  external research tool (a search API, a generator, an analyzer, an agent card)
  as a provenance-tracked Wheeler adapter. The skill mostly emits prose
  instructions and skeleton files; it tells the human to capture one real output,
  fill the parser against it, then run the adversarial-review workflow to land it.
  Do NOT trigger for using an EXISTING adapter (that is `/wh:asta-*`), for graph
  lookups, or for generic coding.
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
declarative **contract** (one `.wheeler/services.yaml` entry); a command opts in
via a flag; a run is a step whose provenance reaches BACK to its graph inputs
(`USED`) and FORWARD to its graph outputs (`WAS_GENERATED_BY`). The Asta
adapters are instance #1 and your concrete template. You produce the four
pieces, then hand the scientist a short to-do list: capture one real output,
fill the parser against it, run the adversarial review, land it.

You write SKELETONS, not finished adapters. The parser is tool-specific and can
only be written against a real captured output, which you do not have at scaffold
time. Your job is to lay down every piece of the structure correctly so the human
fills one function (`parse_<tool>`) and reviews.

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
- `.claude/commands/wh/asta-lit.md`, `asta-theorize.md`, `asta-scholar.md` -- the
  marshal-in acts. Each reads graph context, picks a link target, shells out to
  the tool CLI, then calls `wheeler integrate ingest ... --used <ids>`.
- `tests/integrations/asta/test_theorizer.py` -- the test template: parse-unit
  tests (no live call) PLUS a live-Neo4j e2e class with the per-run `e2e_tag`
  hermetic-teardown convention.

If the user has an `assets/` scaffolder available next to this SKILL.md, you MAY
run it to emit the skeleton files mechanically (see "Optional scaffolder"
below). Otherwise write them by hand from the templates. Markdown-driven (writing
the files yourself) is fully acceptable.

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

## Step 2: the `.wheeler/services.yaml` entry

Append (do not overwrite) an entry under `services:`. `services.yaml` is
user-editable and ships empty; create it with a `services: []` root if absent.
Mirror the spec's shape exactly:

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
the parser stays tool-specific Python. Leave a comment pointing at the module
that implements it.

## Step 3: the marshal-out ingest skeleton

Create `wheeler/integrations/<provider>/<tool>.py` (and an empty
`wheeler/integrations/<provider>/__init__.py` if the provider package is new).
Copy the structure of `theorizer.py` (for a node-subgraph output) or `ingest.py`
(for a flat record output). The skeleton MUST:

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
   used_inputs=None) -> ImportReport`. It MUST, in order:
   - `from wheeler.tools.graph_tools import _get_backend, execute_tool` (lazy,
     function-local: this is the ONLY `execute_tool` caller, so the triple-write
     + write-receipt + trace-id + embedding wiring fires, and `graph_tools/`
     stays adapter-free, mirroring `wheeler/validation/ledger.py`).
   - dedupe-or-create ONE Execution per run via `_find_execution` (idempotent),
     tagged `service=_SERVICE_TAG` with a stable `session_id`.
   - record input-side provenance: `report.used += await _record_used(backend,
     config, exec_id, used_inputs)` (existence-guarded, link_once, never
     fabricates a missing id).
   - register the raw output via `register_output_artifact(artifact_path,
     execution_id=exec_id, service=_SERVICE_TAG, config=config,
     node_type=_RAW_NODE_TYPE, ...)` (best-effort, never raises).
   - bucket each parsed record into its nodes, every WRITE through
     `execute_tool`, every edge through `_link_once`.
   - apply the Paper rule when the output references papers: papers dedupe on
     `corpus_id`, are REFERENCE ENTITIES (NO `WAS_GENERATED_BY`), and if the
     produced knowledge was DERIVED from a paper, the run `Execution -[USED]->`
     that paper.
   - return the `ImportReport` with created / deduped / linked / skipped / used
     counts.

Every graph write routes through `execute_tool`. Never write the backend or the
files directly.

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
  tool's `Bash(<tool>:*)`, `Bash(wheeler integrate:*)`, and the read-only MCP
  tools the preflight needs (`mcp__wheeler_core__search_context`, the relevant
  `mcp__wheeler_query__query_*`).
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
     then RE-INGESTS the same artifact and asserts idempotency (identical counts,
     `created==0` on the second pass).

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
