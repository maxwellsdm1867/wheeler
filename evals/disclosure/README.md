# Progressive disclosure experiment

How much of a node should a listing return by default? `docs/mcp-token-audit.md`
found that every byte a tool returns is re-read on every later turn, and that
`query_*` listings and search hits were returning whole text bodies when the
model needed a few facts. The MCP servers now read `WHEELER_DISCLOSURE`:

| level | what `query_*`, `search_findings` hits and `search_context` related rows return |
|---|---|
| `full` | complete text fields (what shipped before 2026-09-14) |
| `trimmed` | text cut to 240 chars with a `... [+N chars]` suffix |
| `pointer` | `{id, type, headline (<= 100 chars), updated, version, degree}`, no text body |

In every level `show_node` is the deep read: one id, `node_ids=[...]` for many,
`fields="a,b"` to select, `neighbors=True` for one hop. This harness measures
whether a leaner default costs accuracy on tasks that need the body, or whether
the model simply reads the node when it needs to, and what each level costs in
turns and context.

```
make_fixture.py     builds fixture/ (graph.json, tasks.json, files/) deterministically
run.py              one level, N tasks: scratch project, seed once, launch per task, parse, score, clean up
report.py           aggregates runs/*/t*-r*/results.json into REPORT.md
fixture/            generated, deterministic, safe to regenerate
runs/               one directory per level run (project copy, per-task transcripts and results)
```

## Setup

Everything runs from the worktree root with the worktree first on `PYTHONPATH`
(see the caveat at the end) and the shared venv's interpreter:

```bash
cd /Users/maxwellsdm/Documents/GitHub/wheeler/.worktrees/versions
export PYTHONPATH=$PWD
.venv/bin/python -c "import wheeler; print(wheeler.__file__)"   # must print a path under .worktrees/versions
.venv/bin/python evals/disclosure/make_fixture.py                # idempotent, byte-identical on rerun
.venv/bin/python evals/disclosure/run.py --check-gold            # must print check-gold: PASS
```

Neo4j must be up at `bolt://localhost:7717` (user `neo4j`, database `neo4j`).
The `claude` CLI must be on `PATH` and logged in to the subscription; no API
credential is used, and any direct API credential found in the environment is
dropped before `claude` is spawned.

## Running a level

```bash
.venv/bin/python evals/disclosure/run.py --level full                      # all 10 tasks
.venv/bin/python evals/disclosure/run.py --level trimmed --tasks 5,6       # the two body-reading tasks
.venv/bin/python evals/disclosure/run.py --level pointer --repeat 3        # 3 runs per task
.venv/bin/python evals/disclosure/run.py --level pointer --tasks 1 --plan  # print command + prompt, run nothing
.venv/bin/python evals/disclosure/report.py                                # writes REPORT.md
```

Options: `--level {full,trimmed,pointer}` (required except with `--check-gold`),
`--tasks 1,2,...` (default all), `--model` (default `sonnet`), `--repeat`
(default 1), `--max-turns` (default 40), `--timeout-s` (default 1800, kills
`claude`), `--keep` (leave the tagged nodes in Neo4j), `--plan` (print only),
`--check-gold` (seed, verify every gold against Neo4j, clean up, exit).

Every run gets `mcp__wheeler_query`, `mcp__wheeler_core`, `Read`, `Glob`,
`Grep`. The mutations server is not in `.mcp.json`, so a run is read-only by
construction, and `--strict-mcp-config` keeps the user's own MCP servers out.

The level is only an environment variable passed to the servers. If the
disclosure code has not landed in the branch you run against, every level
behaves the same (whatever the servers currently do) and the transcripts still
record it; the harness does not depend on the feature existing.

## The fixture

A synthetic retinal-electrophysiology project (contrast-dependent shortening of
the spike-history kernel in primate parasol cells): 65 nodes and 109 edges.

| type | n | notes |
|---|---|---|
| OpenQuestion | 1 | priority 8 |
| Hypothesis | 3 | one supported (H2), one rejected (H1), one open (H3) |
| Finding (text) | 14 | 370 to 1,066 chars, with numbers; `WAS_GENERATED_BY` an execution, `APPEARS_IN` a figure |
| Finding (figure) | 6 | `ensure_artifact` on stdlib-encoded PNGs, `artifact_type=figure` |
| Script | 6 | real `.py` files |
| Dataset | 5 | 3 raw (reference tier) + 2 interim (generated), real CSVs |
| Execution | 7 | kind `script_run`; each `USED` a script and its input datasets |
| Document | 3 | real markdown files; two `CITES` 10 and 12 papers |
| Paper | 20 | title, authors, year, synthetic DOI |

The provenance chain for `fig02` is three executions deep (`fig02 <- X3 <- Dint2
<- X2 <- Dint1 <- X1 <- Draw1`), which is what the trace task needs, and the fit
script `S3` sits two levels above three figures, which is what the staleness
task needs. Three findings form a `WAS_DERIVED_FROM` chain.

`graph.json` lists nodes as `{key, tool, args}` (the exact `add_*` /
`ensure_artifact` call, paths project-relative) and edges as `[src, rel, dst]`
by symbolic key. `tasks.json` holds the ten tasks, each with `kind`,
`may_need_body`, the prompt, the required answer shape and a gold by symbolic
key. `make_fixture.py` refuses to write a fixture that violates the contract
(finding lengths, the task 5 number past char 240 and unique in the fixture,
the task 6 phrase past char 400 and absent from the title, chain edges present).

## What one level run does

1. Creates `runs/<UTC ts>-<level>/project/`: `fixture/files/` plus `wheeler.yaml`
   (unique `project_tag`) and a two-server `.mcp.json` whose env carries
   `PYTHONPATH`, `WHEELER_DISCLOSURE=<level>` and the safety variables below.
2. Seeds the whole fixture through `execute_tool`: nodes in `graph.json` order,
   then every edge with `link_nodes`, then a title pass with `update_node` in
   `update_order`. Findings are created without a title so the pass gives each
   one an `updated` stamp; the order is the task 9 gold. Writes `seed_ids.json`.
3. For each task and repeat, writes `t<k>-r<n>/prompt.md` and `command.txt`,
   launches `claude -p` with cwd = the project, parses `transcript.jsonl`, scores
   the `ANSWER <json>` line against the gold resolved to real ids, writes
   `results.json`.
4. Writes `level_summary.json` (mean score, accuracy, turns, context, and the
   `may_need_body` versus rest split) and, unless `--keep`, deletes every node
   with the tag.

Seeding takes about 6 s and happens once per level run, not once per task; a
task is read-only so the shared graph is safe.

## Prompt

```
You are answering a question about the Wheeler knowledge graph of this project. Use the
Wheeler MCP tools. Prefer the fewest calls that answer correctly; read a node's full
content only when you need it.

Question: <task prompt, nodes named by file path, statement or title, never by id>

Answer shape: <per-task JSON shape>.

Reply with exactly one line: ANSWER <json>
```

The model is not told which disclosure level is active.

## Tasks and scoring

| # | kind | body? | gold shape | score |
|---|---|---|---|---|
| 1 | lookup: script behind fig03 | no | one Script id | exact |
| 2 | one-hop: findings that SUPPORTS H2 | no | set of Finding ids | Jaccard |
| 3 | two-hop: datasets used by fig05's execution | no | set of Dataset ids | Jaccard |
| 4 | deep trace: fig02 to raw dataset | no | `{chain: [...], scripts: [...]}` | 0.7 prefix + 0.3 Jaccard |
| 5 | content read: confidence + peak latency in F11 | yes | `{confidence, peak_latency_ms}` | per field |
| 6 | content read: finding mentioning a phrase at char 400+ | yes | one Finding id | exact |
| 7 | contradiction: (finding, hypothesis) pairs | no | set of pairs | Jaccard |
| 8 | staleness: figures downstream of fit_srm.py | no | set of figure ids | Jaccard |
| 9 | counting: findings RELEVANT_TO Q1, top-3 by `updated` | no | `{count, top3}` | 0.5 exact + 0.5 prefix |
| 10 | literature: papers cited by document W1 | no | set of Paper ids | Jaccard |

Verdict: correct (score 1), partial (0 < score < 1), wrong (0 or no ANSWER
line). Task 5's number sits past character 240 of its finding so a trimmed row
cannot show it, and task 6's phrase sits past character 400 and is not in the
title, so neither a trimmed row nor a pointer headline can show it. Both are
reachable in every level through `show_node` or a keyword search; the question
is whether the model gets there and what it costs.

## Tag isolation and cleanup

The local database holds thousands of unrelated test nodes. Every level run
writes a unique `neo4j.project_tag` (`disclosure-<ts>-<level>`) into its scratch
`wheeler.yaml`. `Neo4jBackend` stamps `_wheeler_project = <tag>` on every node
it creates and scopes every `MATCH` to it, so seeding, the model's MCP calls,
the gold verifier and the cleanup see only that run's nodes. Cleanup is
`MATCH (n {_wheeler_project: $tag}) DETACH DELETE n` followed by a count that
must be 0 (recorded under `cleanup` in `level_summary.json`).

Three more guards keep a run from resolving to any other graph: the servers and
`claude` get `WHEELER_NO_KEYCHAIN=1` (the OS keychain layer outranks
`wheeler.yaml`), explicit `NEO4J_*` variables pointing at the scratch database,
and `WHEELER_PROJECT_ROOT` set to the scratch project.

## `--check-gold`

Seeds into a `disclosure-<ts>-checkgold` tag, resolves every task's gold to the
created ids, and verifies each against Neo4j with the query the task is about
(the script behind fig03, the SUPPORTS set, the chain edges one by one, the
number's character offset and uniqueness, the transitive `WAS_GENERATED_BY|USED`
reach of S3, the `updated` ordering, the CITES set), prints the resolved answers,
writes `check_gold.json`, cleans up and exits nonzero on any mismatch. Run it
after any change to `make_fixture.py`.

## Caveats

- **PYTHONPATH while the branch is unmerged.** `.venv` is a symlink to the main
  checkout's venv, whose editable install of `wheeler` points at the main
  checkout, not this worktree. Without `PYTHONPATH=<worktree>` the harness and
  the MCP servers would import the main checkout's `wheeler`, which does not read
  `WHEELER_DISCLOSURE`. `run.py` refuses to start when the import resolves
  elsewhere and writes `PYTHONPATH` into `.mcp.json` and the `claude` environment.
- Wall clock includes MCP server startup. Compare across runs on one machine only.
- The title pass bumps each text finding's `content_version` to 2, so pointer
  rows show `version: 2` for text findings and `1` for figures. That is realistic
  and does not affect any gold.
- `runs/` holds full transcripts and a copy of the fixture per level run. It is
  not git-ignored by this directory; decide before committing.


## Outcome

See `REPORT.md`, Recommendation. Default became `pointer`; `run_cypher` gained `$ptag` binding and an unscoped-query warning. Run the levels ONE AT A TIME (or on separate databases): raw Cypher is not project-scoped, and concurrent runs on one database contaminate each other's answers (`runs_parallel_contaminated/`).
