# Batch registration experiment (issue #117)

Measures the token and turn cost of registering one completed analysis run's
provenance (1 execution, 23 file artifacts, 6 findings, 43 edges) into the
Wheeler graph, under five strategies, against a scored ground truth.

```
make_fixture.py     builds fixture/ (synthetic export + BRIEF.md.template + gold.json)
run.py              one strategy, N repeats: scratch project, seed, launch, parse, score, clean up
report.py           aggregates runs/*/results.json into REPORT.md
prompts/            s1.md .. s5.md plus the shared head and tail
fixture/            generated, deterministic, safe to regenerate
runs/               one directory per run (project copy, transcript, results.json)
```

## Setup

Everything runs from the worktree root with the worktree first on `PYTHONPATH`
(see the caveat at the end) and the shared venv's interpreter:

```bash
cd /Users/maxwellsdm/Documents/GitHub/wheeler/.worktrees/batch
export PYTHONPATH=$PWD
.venv/bin/python -c "import wheeler; print(wheeler.__file__)"   # must print a path under .worktrees/batch
.venv/bin/python evals/batch_registration/make_fixture.py        # idempotent
```

Neo4j must be up at `bolt://localhost:7717` (user `neo4j`, database `neo4j`).
The `claude` CLI must be on `PATH` and logged in to the subscription; no API
credential is used, and any direct API credential found in the environment is
dropped before `claude` is spawned.

## Running a strategy

```bash
.venv/bin/python evals/batch_registration/run.py --strategy 0                 # oracle, no model
.venv/bin/python evals/batch_registration/run.py --strategy 1 --repeat 3      # status quo, 3 runs
.venv/bin/python evals/batch_registration/run.py --strategy 2 --model opus    # batch MCP tools
.venv/bin/python evals/batch_registration/run.py --strategy 3                 # manifest + CLI
.venv/bin/python evals/batch_registration/run.py --strategy 4                 # manifest, dry-run, CLI
.venv/bin/python evals/batch_registration/run.py --strategy 5                 # one subagent
.venv/bin/python evals/batch_registration/run.py --strategy 1 --plan          # print command + prompt, run nothing
```

Options: `--model` (default `sonnet`), `--repeat` (default 1), `--max-turns`
(default 250), `--timeout-s` (default 3 h, kills `claude`), `--keep` (leave the
tagged nodes in Neo4j after scoring), `--plan` (print only).

| strategy | method | extra tools granted |
|---|---|---|
| 0 | oracle: `register_batch` from `gold.json`, no model | none |
| 1 | one `ensure_artifact` / `add_finding` / `link_nodes` call per item | none |
| 2 | `register_batch`, one mutation call (the shipped shape; the prototype flag `WHEELER_BATCH_TOOLS` is now a no-op) | none |
| 3 | Write `provenance.yaml`, one `integrate register` CLI call | `Bash(<python> -m wheeler.tools.cli integrate register*)` |
| 4 | same as 3 with `--dry-run` first | same as 3 |
| 6 | split batch form: `ensure_artifacts` + `add_*` + `link_nodes_batch` (historical: those two tools were measured and NOT shipped, so s6 cannot be re-run on the current branch) | none |
| 5 | one `general-purpose` subagent runs the strategy 1 method | `Agent` |

Every strategy gets `mcp__wheeler_mutations`, `mcp__wheeler_query`,
`mcp__wheeler_core`, `Read`, `Glob`, `Grep`, `Write`. `--strict-mcp-config`
keeps the user's own MCP servers out of the run.

Strategies 2, 3 and 4 depend on code that lands with the same branch (the batch
MCP tools behind `WHEELER_BATCH_TOOLS`, and `wheeler integrate register`). Until
those exist the model will find the tools missing and the transcripts will show
what it does instead, which is itself a measurement, but not the intended one.

## What one run does

1. Creates `runs/<UTC ts>-s<N>-r<k>/project/`: the fixture minus
   `BRIEF.md.template` and `gold.json`, plus `data/raw_epochs_cell01.csv` (the
   seed dataset's file), `wheeler.yaml` and `.mcp.json`.
2. Seeds the two pre-existing nodes through `execute_tool` (`add_question`,
   `add_dataset`) with a `WheelerConfig` built from that yaml, records their ids
   and renders `BRIEF.md` from the template.
3. Launches `claude -p` with cwd = the project (strategies 1 to 5), or calls
   `register_batch` directly (strategy 0). `command.txt`, `prompt.md`,
   `transcript.jsonl` and `stderr.log` land in the run directory.
4. Parses the stream-json transcript: usage summed once per assistant message
   id, turns, a tool-call histogram and sequence, the longest run of one tool,
   the `result` line, and the model's `DONE <nodes> <edges>` line.
5. Scores the tagged subgraph against `gold.json` (see below) and counts
   `knowledge/*.json` and `synthesis/*.md` in the project as a triple-write
   sanity check.
6. Writes `results.json` and, unless `--keep`, deletes every node with the run's
   tag. The run directory is always left on disk.

## Tag isolation and cleanup

The local database holds a few thousand unrelated test nodes. Every run writes
a unique `neo4j.project_tag` (`batchreg-<ts>-s<N>-r<k>`) into its scratch
`wheeler.yaml`. `Neo4jBackend` stamps `_wheeler_project = <tag>` on every node
it creates and scopes every `MATCH` to it, so the seeding, the model's MCP
calls, the CLI, the scorer and the cleanup all see only that run's nodes.

Cleanup is `MATCH (n {_wheeler_project: $tag}) DETACH DELETE n`, then a count
that must come back 0 (recorded under `cleanup` in `results.json`). Nothing
without the tag is ever touched. With `--keep` the nodes stay for inspection;
delete them later with the same Cypher and the tag printed in the run log.

Three more guards keep a run from resolving to any other graph: the servers and
`claude` get `WHEELER_NO_KEYCHAIN=1` (the OS keychain layer outranks
`wheeler.yaml`), explicit `NEO4J_*` variables pointing at the scratch database
(env outranks everything), and `WHEELER_PROJECT_ROOT` set to the scratch
project. The repo's own `wheeler.yaml` and `.wheeler/` are never read.

## Scoring

`gold.json` lists the expected execution, 23 artifacts keyed by relative path
with their expected label, 6 findings keyed by a distinctive phrase, and the 43
edges with symbolic endpoints (`exec`, a relative path, `finding:<key>`,
`QUESTION_ID`, `DATASET_ID`). The scorer pulls every tagged node and edge, then
maps: artifacts by path basename with the label required to match, findings by
case-insensitive key substring in `description`, the execution as the
`Execution` node created under the tag (more than one is noted). Gold edges are
translated to id triples; `edge_recall` is matched over 43 and
`edge_precision` is matched over every edge created among tagged nodes, so
duplicates and inventions cost precision. `results.json` lists the unmatched
artifacts, findings, missed edges, extra edges and extra nodes by name.

## The oracle

`--strategy 0` builds the manifest straight from `gold.json` and calls
`wheeler.tools.graph_tools.batch.register_batch`. It must score 100% node and
edge recall and precision; if it does not, the scorer or the fixture is broken,
not the model. Run it first after any change to `make_fixture.py` or the
scorer. A deliberately broken manifest (dropped, duplicated and invented edges,
an extra node) has been checked to lower recall and precision as expected.

## Report

```bash
.venv/bin/python evals/batch_registration/report.py     # writes REPORT.md
```

One row per run, then per-strategy means, then a reading guide and an empty
`## Recommendation` section for the human.

## Caveats

- **PYTHONPATH while the branch is unmerged.** `.venv` is a symlink to the main
  checkout's venv, whose editable install of `wheeler` points at the main
  checkout, not this worktree. Without `PYTHONPATH=<worktree>` the harness, the
  MCP servers and the CLI would all import the main checkout's `wheeler`, which
  lacks `batch.py` and the batch tools. `run.py` refuses to start when the
  import resolves elsewhere, and writes `PYTHONPATH` into `.mcp.json` and the
  `claude` environment. Once the branch is merged and the venv reinstalled the
  variable becomes harmless.
- Wall clock includes MCP server startup and, on a machine that has never run
  Wheeler search, a one-time fastembed model download triggered by the
  mutations server's similarity check. Compare wall clock across runs on the
  same machine only.
- Strategy 5: Claude Code may not stream the subagent's messages into the
  parent transcript. `subagent_usage_visible` in `results.json` says whether
  any assistant line carried a `parent_tool_use_id`; when it is false, the
  token columns for that run understate the true cost and only the `result`
  line's totals (if present) are comparable.
- `runs/` holds full transcripts and a copy of the fixture per run. It is not
  git-ignored by this directory; decide before committing.


## Outcome

See `REPORT.md`, section Recommendation. `register_batch` shipped as a first-class tool on the mutations server; the split tools and the flag were removed; the CLI verb `wheeler integrate register` stayed.
