# What does the mechanical half of a `/wh:close` cost?

A close does two different kinds of work. Some of it is a sweep: run a
timestamped query, count rows, hash a file, validate a citation. The rest is
judgment: ask the scientist what is missing, group orphans into executions,
write the narrative. This experiment measures only the first kind, and asks
whether moving it out of the main session into one subagent is cheaper.

```
make_fixture.py     builds fixture/ (project skeleton, graph manifest, gold, context filler)
run.py              one arm at one context size: scratch project, seed, launch, parse, score, clean up
report.py           aggregates runs/*/results.json into REPORT.md
prompts/            inline.md, split.md, and the two shared fragments both arms include
fixture/            generated, deterministic, safe to regenerate
runs/               one directory per run (project copy, transcript, results.json)
```

## What is and is not measured

Measured, because they need only a timestamp and the graph:

| act phase | what it does |
|---|---|
| 1.1 | find the window boundary (`$since`) and warn about closes with no `started_at` |
| 1.2 | every entity stamped at or after `$since` |
| 1.3 | which of those have no `WAS_GENERATED_BY` edge |
| 1.6 | `detect_stale` |
| 2.1 | per-type inventory over the same window |
| 2.4 | `validate_citations` on a draft document |
| 2.6 | `graph_consistency_check(repair=false)` |

NOT measured, on purpose: 1.3b (asking the scientist what never reached the
graph), 1.3c (walking open questions, hypotheses and plans with the scientist),
1.4 (grouping orphans into proposed Executions) and 2.2 (writing the synthesis
narrative). Those need the scientist, so they stay in the main session in BOTH
arms and cancel out of the comparison. Nothing here says what a whole close
costs. It says what the delegable part of one costs.

Both arms end with the same digest contract, so they are comparable:

```
DIGEST {"since": ..., "malformed_closes": N, "window_ids": [...], "orphan_ids": [...],
        "inventory": {...}, "stale": [...], "citations": {"total": N, "valid": N},
        "consistency_ok": true|false}
```

- `inline`: read the prior-session filler, then run the sweep yourself.
- `split`: read the prior-session filler, then hand the ENTIRE sweep to exactly
  one `Agent` subagent that never reads the filler, and relay its digest
  verbatim.

## Setup

Everything runs from the worktree root with the worktree first on `PYTHONPATH`
and the shared venv's interpreter. Never `pip install` into that venv: it is a
symlink shared with the main checkout and sibling worktrees.

```bash
cd /Users/maxwellsdm/Documents/GitHub/wheeler/.worktrees/closecost
export PYTHONPATH=$PWD
.venv/bin/python -c "import wheeler; print(wheeler.__file__)"   # must print a path under this worktree
.venv/bin/python evals/close_cost/make_fixture.py               # deterministic, idempotent
```

Neo4j must be up at `bolt://localhost:7717` (user `neo4j`, database `neo4j`).
The `claude` CLI must be on `PATH` and logged in to the subscription. No API
credential is used: any direct API credential in the environment is stripped
before `claude` is spawned.

## Running

```bash
.venv/bin/python evals/close_cost/run.py --check-gold                      # prove the fixture, clean up
.venv/bin/python evals/close_cost/run.py --arm inline --context small --plan
.venv/bin/python evals/close_cost/run.py --arm inline --context small
.venv/bin/python evals/close_cost/run.py --arm split  --context small
.venv/bin/python evals/close_cost/run.py --arm inline --context large
.venv/bin/python evals/close_cost/run.py --arm split  --context large
.venv/bin/python evals/close_cost/report.py
```

Options: `--model` (default `sonnet`), `--repeat` (default 1), `--max-turns`
(default 60), `--timeout-s` (default 1 h), `--keep` (leave the tagged nodes in
Neo4j), `--plan` (print the command and prompt, seed nothing, launch nothing).

`--check-gold` must pass before any model run. It seeds the fixture, runs every
gold query the way the act runs it, prints each result beside the expected one,
and deletes its own tag.

## One run at a time. This is not optional.

The database at `bolt://localhost:7717` is shared and holds roughly 4100 real
nodes. Every node this harness creates carries a unique per-run
`neo4j.project_tag` (`closecost-<UTC ts>-<arm>-<context>`), and cleanup deletes
only that tag.

The typed `query_*` tools are project-scoped, but **`run_cypher` is not**. The
sweep's window queries are raw Cypher, and the prompt tells the model to scope
them by hand with `WHERE n._wheeler_project = $ptag`. If two runs overlap, the
second run's freshly created nodes sit inside the first run's window, and any
query the model forgets to scope silently reads them. An earlier experiment was
contaminated exactly this way.

So the harness refuses to start when either of these is true:

- `evals/close_cost/.run.lock` exists (a run is in flight, or one crashed)
- any `closecost-*` tag is still present in the database

If it refuses because of a stray tag, delete it explicitly and re-check:

```cypher
MATCH (n) WHERE n._wheeler_project = '<tag>' DETACH DELETE n
```

Never delete anything that is not one of your own tags.

## Context inflation, and how the harness proves it happened

A close is expensive partly because it happens at the END of a session, when
the main context is already full. The interesting question is how that
interacts with delegation, so each arm runs at two context sizes.

The mechanism is the one a real session actually has: the model is told to read
`context/*.md` in full before doing anything else. That filler is synthetic
prior-session material (analysis narration, tool-output-looking tables, code
snippets) generated deterministically and sized with
`wheeler.knowledge.versions.estimate_tokens`. It is split into files of about
20k tokens each so no single `Read` is truncated by the host: `small` is 2 files
(about 30k tokens), `large` is 20 files (about 400k tokens).

Inflation is verified, not assumed. The harness parses the transcript and
records, per run:

- `context_first_turn_tokens`: input + cache read + cache creation on the first
  PARENT assistant turn
- `parent_context_peak_tokens`: the largest of that sum over all parent turns,
  which is what the main session actually carried once the filler was in
- `subagent_context_peak_tokens`: the same for turns inside the Agent call
- `context_achieved_tokens`: the peak, which is the honest measure of "how big
  did this session's context get"

If `context_achieved_tokens` falls below 70 percent of the target, the run is
marked `context_target_missed: true`, the harness says so loudly on stdout, and
`report.py` flags the run `CTX-MISSED` in its status column.

The achieved number will normally EXCEED the nominal target, because the system
prompt, the MCP tool definitions and the prompt itself are context the harness
does not control. The 70 percent floor is there to catch the failure mode
(truncated or skipped reads), not the excess.

## Subagent accounting: read this before believing a split-arm number

The final `result` line of a stream-json transcript has a `usage` block, and it
is the obvious thing to read. It is wrong for the split arm. Measured on an
earlier subagent run in `evals/batch_registration/`:

| source | context tokens, no subagent | context tokens, with subagent |
|---|---|---|
| `result.usage` | 5,091,750 | 100,759 |
| per-message sum | 5,091,750 | 4,363,082 |
| `result.modelUsage` | 5,093,368 | 4,431,703 |

With no subagent all three agree. With a subagent, `result.usage` carries only
the parent's last exchange and undercounts by a factor of 44.
`result.modelUsage` and `result.total_cost_usd` are session totals and DO
include the subagent (their cost figures agree to four decimal places).

So this harness reports `modelUsage`, keeps the per-message sum as a
cross-check, and keeps `result.usage` in `results.json` only as evidence. It
also records `subagent_usage_visible`, which is true when at least one
assistant line in the parent stream carried a `parent_tool_use_id`, meaning the
subagent's turns were streamed to the parent and counted. If an Agent call ran
and that flag is false, the split arm's total is UNDERCOUNTED; the harness
prints a warning and `report.py` flags the run `SUB-UNCOUNTED`. A split arm
that looks cheap while flagged is not a result.

## Cost and correctness are reported together

A cheaper arm that gets the sweep wrong is not cheaper. Every run is scored
against `fixture/gold.json` resolved to the ids that seeding actually created:

- `window_ids` and `orphan_ids`: recall and precision, plus exact-set match
- `inventory`: exact match on all six counts
- `stale`, `malformed_closes`, `citations`, `since`, `consistency_ok`: exact
- `all_exact`: every one of the above

`REPORT.md` puts cost and correctness in the same tables and the same
"Does the split pay off?" comparison.

## Fixture facts worth knowing

- **The window.** `$since` is the `started_at` of a close Execution two days
  before the run. 33 non-Execution entities are stamped after it (12 Findings,
  4 OpenQuestions, 3 Hypotheses, 3 ResearchNotes, 2 Documents, 3 Datasets, 4
  Scripts, 2 Plans); 17 of them have a `WAS_GENERATED_BY` edge to one of 3
  in-window Executions and 16 do not, which is the orphan set. Five more nodes
  are stamped five days back and must never appear.
- **Timestamps are written by direct scoped Cypher, not by `update_node`.**
  `update_node` always overwrites `updated` with the current instant, so it
  cannot express a node older than now. Only the timestamp fields are touched;
  the knowledge JSON keeps the instant it was written at, which
  `graph_consistency_check` cannot see because it compares id inventories, not
  fields.
- **The malformed close has `started_at` absent, not empty.** The act's phase
  1.1 accepts `IS NULL OR = ""`, but its phase 2.1 runs
  `datetime(x.started_at)` over every Execution in the project, and Neo4j
  raises on `datetime("")`. An empty string would turn this fixture into a test
  of error recovery instead of a cost measurement. (That is a real latent bug
  in `close.md` 2.1: one Execution with an empty `started_at` breaks the
  inventory query for the whole session.)
- **Inventory Execution count is 4, not 3.** The boundary close's `started_at`
  equals `$since`, and the act's query is `>=`, so the boundary close counts
  itself. The prompt tells both arms to report what the queries return rather
  than to reason about it, so the arms stay comparable.
- **`consistency_ok` ignores `graph_only`.** `check_consistency` runs an
  unscoped `MATCH (n) RETURN n.id`, so on this shared database `graph_only`
  comes back with about 4100 ids from other work. That list is also a real
  token cost in both arms (roughly 70 KB of tool result); each run records
  `consistency_graph_only` and `consistency_result_chars` so the report can say
  how much of the sweep payload it was. On a single-project database it would
  be empty.
- **The stale script** is `scripts/bootstrap.py`, appended to on disk after it
  is registered, so `detect_stale` reports it with `reason: changed`.
- **The citation draft** is `docs/DRAFT-SESSION.md`, rendered at seed time with
  three real ids (two with provenance, one orphan Finding) and one that
  resolves to nothing: 4 total, 2 valid.

## Deliberate non-goals

- No mutations server is wired into `.mcp.json`. This is a read-only
  measurement; the sweep never writes.
- The harness never launches `claude` from `--plan` or `--check-gold`.
- Nothing here is committed.
