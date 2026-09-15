# Batch registration experiment (issue #117)

Runs aggregated from `runs`: 12 run(s).

## Per run

| run | s | model | turns | input | cache read | cache create | output | cost $ | wall s | nodes | edges | edge recall | edge prec | mutation calls | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20260915T013853Z-s0-r1 | 0 | - | 0 | 0 | 0 | 0 | 0 | 0.0 | 1.9 | 30/30 | 43/43 | 1.000 | 1.000 | 1 | ok |
| 20260915T014322Z-s1-r1 | 1 | sonnet | 76 | 152 | 5035577 | 56021 | 11768 | 1.4 | 149.8 | 30/30 | 43/43 | 1.000 | 1.000 | 73 | ok |
| 20260915T014322Z-s2-r1 | 2 | sonnet | 5 | 10 | 233960 | 40383 | 5782 | 0.268 | 55.2 | 30/30 | 43/43 | 1.000 | 1.000 | 1 | ok |
| 20260915T014322Z-s3-r1 | 3 | sonnet | 9 | 18 | 480794 | 57430 | 5110 | 0.379 | 54.2 | 30/30 | 43/43 | 1.000 | 1.000 | 1 | ok |
| 20260915T014322Z-s4-r1 | 4 | sonnet | 8 | 16 | 425764 | 46908 | 5624 | 0.331 | 56.4 | 30/30 | 43/43 | 1.000 | 1.000 | 1 | ok |
| 20260915T014322Z-s5-r1 | 5 | sonnet | 77 | 4 | 70378 | 30377 | 1269 | 1.3 | 168.5 | 30/30 | 43/43 | 1.000 | 1.000 | 73 | ok |
| 20260915T014559Z-s1-r1 | 1 | opus | 75 | 150 | 4124414 | 52556 | 12483 | 2.9 | 189.9 | 30/30 | 43/43 | 1.000 | 1.000 | 73 | ok |
| 20260915T014559Z-s2-r1 | 2 | opus | 3 | 6 | 94113 | 36083 | 4209 | 0.515 | 45.9 | 30/30 | 43/43 | 1.000 | 1.000 | 1 | ok |
| 20260915T014559Z-s3-r1 | 3 | opus | 12 | 24 | 579371 | 54955 | 5672 | 0.983 | 67.9 | 30/30 | 43/43 | 1.000 | 1.000 | 1 | ok |
| 20260915T014559Z-s4-r1 | 4 | opus | 14 | 28 | 698226 | 55406 | 7433 | 1.1 | 95.6 | 30/30 | 43/43 | 1.000 | 1.000 | 1 | ok |
| 20260915T014729Z-s2-r1 | 2 | sonnet | 5 | 10 | 237117 | 33833 | 4587 | 0.230 | 44.0 | 30/30 | 43/43 | 1.000 | 1.000 | 1 | ok |
| 20260915T014729Z-s6-r1 | 6 | sonnet | 7 | 14 | 363126 | 43237 | 8439 | 0.332 | 76.1 | 30/30 | 43/43 | 1.000 | 1.000 | 9 | ok |

## Per strategy (means)

| s | model | runs | turns | input | cache read | cache create | output | cost $ | wall s | nodes | edges | edge recall | edge prec | mutation calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | - | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.9 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 1.000 |
| 1 | opus | 1 | 75.0 | 150.0 | 4124414.0 | 52556.0 | 12483.0 | 2.9 | 189.9 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 73.0 |
| 1 | sonnet | 1 | 76.0 | 152.0 | 5035577.0 | 56021.0 | 11768.0 | 1.4 | 149.8 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 73.0 |
| 2 | opus | 1 | 3.0 | 6.0 | 94113.0 | 36083.0 | 4209.0 | 0.515 | 45.9 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 1.000 |
| 2 | sonnet | 2 | 5.0 | 10.0 | 235538.5 | 37108.0 | 5184.5 | 0.249 | 49.6 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 1.000 |
| 3 | opus | 1 | 12.0 | 24.0 | 579371.0 | 54955.0 | 5672.0 | 0.983 | 67.9 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 1.000 |
| 3 | sonnet | 1 | 9.0 | 18.0 | 480794.0 | 57430.0 | 5110.0 | 0.379 | 54.2 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 1.000 |
| 4 | opus | 1 | 14.0 | 28.0 | 698226.0 | 55406.0 | 7433.0 | 1.1 | 95.6 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 1.000 |
| 4 | sonnet | 1 | 8.0 | 16.0 | 425764.0 | 46908.0 | 5624.0 | 0.331 | 56.4 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 1.000 |
| 5 | sonnet | 1 | 77.0 | 4.0 | 70378.0 | 30377.0 | 1269.0 | 1.3 | 168.5 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 73.0 |
| 6 | sonnet | 1 | 7.0 | 14.0 | 363126.0 | 43237.0 | 8439.0 | 0.332 | 76.1 | 30.0/30 | 43.0/43 | 1.000 | 1.000 | 9.0 |

## How to read this

Strategy 0 is the oracle: `register_batch` called directly from the gold manifest with no model, so its tokens and turns are zero by construction and its recall proves the scorer. Strategies 1 to 6 are the model-driven methods described in `prompts/`. `turns` counts distinct assistant messages in the transcript. `input`, `cache read`, `cache create`, `output` and `cost $` come from the final `result` line's usage block, the session total (per-message stream events carry partial output counts and are kept in results.json only as a cross-check). `input` is the uncached share; the context the model read over the whole run is input + cache read + cache create, and because every turn re-reads the whole context, `cache read` scales with turns times context size. `wall s` is the harness-measured wall clock of the `claude` subprocess, including MCP server startup. `nodes` and `edges` are matched-against-gold over expected (30 nodes, 43 edges); `edge recall` is matched over expected and `edge prec` is matched over every edge the run created among tagged nodes, so duplicated or invented edges lower precision without touching recall. `mutation calls` counts calls to `wheeler_mutations` tools plus each non-dry-run CLI `integrate register` call. For strategy 5 the parent transcript may not carry the subagent's usage; check `subagent_usage_visible` in that run's results.json before comparing its token columns with the others.

Strategy 5 subagent usage visible in the parent stream: 20260915T014322Z-s5-r1=True

## Recommendation

**Ship `register_batch` (strategy 2) as a first-class mutations tool and have `/wh:execute`, `/wh:close` and `/wh:graph-link` call it once per execution.** Every strategy reached 100 percent edge recall and precision on the 30-node, 43-edge fixture, so there is no provenance-quality trade-off to weigh; the decision is cost alone.

| versus status quo (same model) | turns | context read (input + cache) | output tokens | cost | wall clock |
|---|---|---|---|---|---|
| sonnet: s2 vs s1 | 5 vs 76 (15x fewer) | 0.27M vs 5.09M (19x less) | 5.2k vs 11.8k | $0.25 vs $1.40 (5.6x) | 50 s vs 150 s |
| opus: s2 vs s1 | 3 vs 75 (25x fewer) | 0.13M vs 4.18M (32x less) | 4.2k vs 12.5k | $0.52 vs $2.90 (5.6x) | 46 s vs 190 s |

Why the others lose:

- **Split batch tools (s6: `ensure_artifacts` + `add_*` + `link_nodes_batch`)**: 7 turns, 9 mutation calls, $0.33 on sonnet. Better than the status quo, but each text Finding is still its own call, and the ids have to round-trip through the model before the edges can be written. `register_batch` puts Findings under `nodes` and lets edges reference `@alias`, which is what removes the remaining turns. Not shipped.
- **Manifest file + CLI (s3, s4)**: 9 to 14 turns, $0.38 to $1.10. The Write plus Bash round trips and reading the CLI's stdout cost more turns than the one MCP call, and the dry-run step (s4) added a turn without catching anything on a clean manifest. The `wheeler integrate register` verb stays, since it is the bulk path for scripts and for hosts without the mutations server, but the acts do not route through it.
- **Subagent (s5)**: 77 turns and $1.30, the same as the status quo. Delegation moves the cost out of the main context; it does not remove it.

Two structural observations that generalise beyond this fixture:

1. **Cost is turns times context.** Every turn re-reads the whole context (the `cache read` column is 45k to 55k per turn here, and grows through a real session), so the number of assistant turns is the lever, not the size of any single call. A 43-edge manifest is about 3k output tokens whichever way it is expressed; emitting it in one turn instead of 43 is the entire saving.
2. **The alias mechanism is what makes one call possible.** Without `@alias`, node creation and edge creation are necessarily two round trips (the ids do not exist yet), which is exactly the s6 shape.

Operational notes: `register_batch` returns compact output by default (alias to id map, counts, and only the rows that failed), because a row per successful item is input tokens on the model's next turn. One bad item never aborts the rest and nothing is rolled back, matching Wheeler's external-call failsafe. The prototype flag `WHEELER_BATCH_TOOLS` and the two split tools were removed when the tool shipped; strategy 6 can no longer be re-run as written and is kept in `prompts/s6.md` for the record.

Caveats: single runs per cell except s2 on sonnet (two runs, $0.27 and $0.23); the fixture is synthetic (realistic names and sizes, but a prescriptive brief that a real `/wh:execute` does not have); the brief tells the model exactly what to register, so recall measures the registration path and not the model's judgement about what deserves registering. In this Claude Code version MCP tool schemas load lazily through `ToolSearch`, which is one of the s2 turns; a host that preloads them would make s2 two turns.
