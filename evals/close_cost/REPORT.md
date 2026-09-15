# /wh:close mechanical sweep: inline or one subagent?

Runs aggregated from `runs`: 12 run(s).

## What is measured

Only the MECHANICAL half of a close: the phases that need a timestamp and the graph, not the conversation. Those are 1.1 (window boundary plus the malformed-close check), 1.2 (recent entities), 1.3 (orphans), 1.6 (`detect_stale`), 2.1 (per-type inventory), 2.4 (`validate_citations`) and 2.6 (`graph_consistency_check`).

The judgment phases (1.3b conversation sweep, 1.3c graph-state updates, orphan grouping in 1.4, and the synthesis narrative in 2.2) need the scientist and stay in the main session in BOTH arms, so they cancel out and are deliberately excluded. Nothing here says what a whole close costs; it says what the delegable part of one costs.

## Per run

| run | arm | ctx | ctx target | ctx achieved | turns | parent turns | sub turns | input | cache read | cache create | output | context total | cost $ | wall s | tool calls | sweep calls | subagent | sub usage visible | win recall | win prec | orph recall | orph prec | inv exact | all exact | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20260915T190855Z-inline-small-r1 | inline | small | 30000 | 108174 | 13 | 13 | 0 | 2544 | 1205017 | 87465 | 6365 | 1295026 | 0.657 | 60.9 | 25 | 13 | no | no | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T190958Z-split-small-r1 | split | small | 30000 | 100126 | 8 | 3 | 5 | 2777 | 389554 | 122775 | 7311 | 515106 | 0.572 | 70.8 | 19 | 13 | yes | yes | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T191112Z-inline-large-r1 | inline | large | 400000 | 670790 | 12 | 12 | 0 | 2740 | 6575049 | 644891 | 10424 | 7222680 | 4.0 | 110.4 | 56 | 13 | no | no | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T191304Z-split-large-r1 | split | large | 400000 | 666060 | 7 | 4 | 3 | 2973 | 1379685 | 676432 | 14914 | 2059090 | 3.1 | 117.0 | 65 | 21 | yes | yes | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T191806Z-inline-small-r1 | inline | small | 30000 | 105766 | 7 | 7 | 0 | 2532 | 583012 | 79867 | 4941 | 665411 | 0.488 | 47.9 | 20 | 13 | no | no | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T191856Z-inline-small-r2 | inline | small | 30000 | 105152 | 9 | 9 | 0 | 2536 | 784430 | 79253 | 3892 | 866219 | 0.515 | 48.1 | 18 | 13 | no | no | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T191946Z-split-small-r1 | split | small | 30000 | 100497 | 9 | 3 | 6 | 2779 | 437292 | 123062 | 7068 | 563133 | 0.580 | 68.9 | 20 | 13 | yes | yes | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T192057Z-split-small-r2 | split | small | 30000 | 101495 | 9 | 4 | 5 | 2777 | 443568 | 122189 | 7936 | 568534 | 0.590 | 71.6 | 19 | 13 | yes | yes | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T192210Z-inline-large-r1 | inline | large | 400000 | 670661 | 13 | 13 | 0 | 2742 | 7238565 | 644762 | 10011 | 7886069 | 4.1 | 92.0 | 56 | 13 | no | no | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T192344Z-inline-large-r2 | inline | large | 400000 | 670636 | 10 | 10 | 0 | 2736 | 5239371 | 644737 | 9272 | 5886844 | 3.7 | 93.6 | 56 | 13 | no | no | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T192520Z-split-large-r1 | split | large | 400000 | 665851 | 14 | 4 | 10 | 2987 | 1714718 | 693568 | 17445 | 2411273 | 3.2 | 154.8 | 66 | 13 | yes | yes | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |
| 20260915T192756Z-split-large-r2 | split | large | 400000 | 501389 | 9 | 3 | 6 | 2977 | 852716 | 509415 | 9978 | 1365108 | 2.3 | 91.6 | 37 | 13 | yes | yes | 1.000 | 1.000 | 1.000 | 1.000 | yes | yes | ok |

## Per cell (means by arm and context)

| arm | ctx | runs | ctx achieved | turns | input | cache read | cache create | output | context total | cost $ | wall s | sweep calls | win recall | orph recall | all exact rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| inline | large | 3 | 670695.7 | 11.7 | 2739.3 | 6350995.0 | 644796.7 | 9902.3 | 6998531.0 | 4.0 | 98.7 | 13.0 | 1.000 | 1.000 | 1.000 |
| split | large | 3 | 611100.0 | 10.0 | 2979.0 | 1315706.3 | 626471.7 | 14112.3 | 1945157.0 | 2.9 | 121.1 | 15.7 | 1.000 | 1.000 | 1.000 |
| inline | small | 3 | 106364.0 | 9.7 | 2537.3 | 857486.3 | 82195.0 | 5066.0 | 942218.7 | 0.553 | 52.3 | 13.0 | 1.000 | 1.000 | 1.000 |
| split | small | 3 | 100706.0 | 8.7 | 2777.7 | 423471.3 | 122675.3 | 7438.3 | 548924.3 | 0.581 | 70.4 | 13.0 | 1.000 | 1.000 | 1.000 |

## Does the split pay off?

`context total` is input + cache read + cache creation over the whole session, taken from the final `result` line's `modelUsage`, which includes the subagent. `ratio` is split over inline: below 1.0 means the split read less. Correctness sits in the same table on purpose: a cheaper arm that gets the sweep wrong is not cheaper.

| ctx | metric | inline | split | split - inline | split / inline |
|---|---|---|---|---|---|
| large | context total (tokens) | 6998531.0 | 1945157.0 | -5053374.0 | 0.278 |
| large | cost (USD) | 4.0 | 2.9 | -1.1 | 0.722 |
| large | output tokens | 9902.3 | 14112.3 | 4210.0 | 1.4 |
| large | wall clock (s) | 98.7 | 121.1 | 22.4 | 1.2 |
| large | all-gold-exact rate | 1.000 | 1.000 | 0.0 | - |
| small | context total (tokens) | 942218.7 | 548924.3 | -393294.4 | 0.583 |
| small | cost (USD) | 0.553 | 0.581 | 0.028 | 1.1 |
| small | output tokens | 5066.0 | 7438.3 | 2372.3 | 1.5 |
| small | wall clock (s) | 52.3 | 70.4 | 18.1 | 1.3 |
| small | all-gold-exact rate | 1.000 | 1.000 | 0.0 | - |

## How to read this

`ctx target` is the estimated token size of the filler the model was told to read first; `ctx achieved` is the largest per-turn context (input + cache read + cache creation) seen on a PARENT assistant turn, which is what the main session actually carried. A run whose achieved context fell below 70 percent of target is flagged `CTX-MISSED` in the status column and must not be compared with the others.

`input`, `cache read`, `cache create`, `output` and `cost $` come from the final `result` line's `modelUsage`, NOT from its `usage` block. Once an Agent call has run, `usage` carries only the parent's last exchange and undercounts the session by orders of magnitude; `modelUsage` and `total_cost_usd` are session totals that include the subagent. A run where an Agent call happened but no subagent assistant line reached the parent stream is flagged `SUB-UNCOUNTED`: its total is not trustworthy and must not be reported as a win.

`win recall` / `orph recall` are matched-over-expected against the gold id sets, `prec` is matched over what the run returned, so an invented id lowers precision without touching recall. `all exact` is true only when every gold field matches: window set, orphan set, inventory counts, stale script, malformed-close count, citation totals, the `$since` instant and `consistency_ok`.

Two fixture facts that inflate both arms equally and are worth subtracting mentally from the absolute numbers:

- `graph_consistency_check` runs an UNSCOPED `MATCH (n) RETURN n.id` over the whole database. This database is shared and holds about 4100 nodes from other work, so step 7's `graph_only` list comes back with roughly 4100 ids in it. On a single-project database that list would be empty. Each run records `consistency_graph_only` and `consistency_result_chars` in its `results.json`.
- `consistency_ok` is therefore defined on the layers this project owns (`json_only`, `synthesis_missing`, `synthesis_orphaned` all empty) and ignores `graph_only`.

Subagent usage visible in the parent stream: 20260915T190958Z-split-small-r1=yes, 20260915T191304Z-split-large-r1=yes, 20260915T191946Z-split-small-r1=yes, 20260915T192057Z-split-small-r2=yes, 20260915T192520Z-split-large-r1=yes, 20260915T192756Z-split-large-r2=yes

Token source per run: 20260915T190855Z-inline-small-r1=modelUsage, 20260915T190958Z-split-small-r1=modelUsage, 20260915T191112Z-inline-large-r1=modelUsage, 20260915T191304Z-split-large-r1=modelUsage, 20260915T191806Z-inline-small-r1=modelUsage, 20260915T191856Z-inline-small-r2=modelUsage, 20260915T191946Z-split-small-r1=modelUsage, 20260915T192057Z-split-small-r2=modelUsage, 20260915T192210Z-inline-large-r1=modelUsage, 20260915T192344Z-inline-large-r2=modelUsage, 20260915T192520Z-split-large-r1=modelUsage, 20260915T192756Z-split-large-r2=modelUsage

## Recommendation

**Move the mechanical sweep into one subagent, for the large-context case only, which in practice means always for `/wh:close`.** A close runs at the END of a session, which is exactly when context is at its largest: measured across 29 real retinaSRM sessions, graph writes happen at a median 348k context against an 83k session median. So the cell that matters here is the large one.

Correctness first, because a cheaper arm that gets the sweep wrong is not cheaper: **all 12 runs produced a byte-exact digest**, matching the gold window set, orphan set, per-type inventory, stale script, malformed-close count, citation totals and `$since`. Both arms, both context sizes, n=3 per cell. The split costs nothing in accuracy.

| context | metric | inline | split | split / inline |
|---|---|---|---|---|
| ~670k | context read | 7.00M | 1.95M | 0.28 |
| ~670k | cost | $4.00 | $2.90 | 0.72 |
| ~670k | wall clock | 98.7 s | 121.1 s | 1.23 |
| ~106k | context read | 0.94M | 0.55M | 0.58 |
| ~106k | cost | $0.553 | $0.581 | 1.05 |
| ~106k | wall clock | 52.3 s | 70.4 s | 1.35 |

Four things this says, two of which correct earlier guesses:

1. **The split only pays at realistic context.** At ~106k it is a wash on cost and slightly worse (5 percent more), because the handoff overhead is not amortised. At ~670k it reads 3.6 times less context and costs 28 percent less. This is the direct explanation for why the batch-registration experiment (`evals/batch_registration`, strategy 5) found subagent delegation cost the same as inline: those runs sat at roughly 50k context, so they measured the small-context cell and generalised it wrongly.

2. **The token ratio overstates the money.** Context read drops 3.6x but cost only 1.4x, because re-read context is billed at the cache-read rate while the split spends more on output (1.4x) and on cache creation for the subagent's own prompt. Quote the cost figure, not the token figure.

3. **The split is slower.** Roughly 20 seconds per close, consistently, at both sizes. Briefing a subagent and relaying its digest is latency the inline arm does not pay. That is the real trade: about a dollar against about 20 seconds.

4. **This is a lower bound on the saving.** Each run ends when the digest is produced, so it does not count what the inline arm leaves behind. In a real session the sweep's query results (including the roughly 70 KB `graph_consistency_check` payload) stay in the main context and are re-read on every later turn for the rest of the session. The split returns a compact digest instead. That compounding is the larger effect and it is not in these numbers.

Scope: this measures only the mechanical half of a close (phases 1.1, 1.2, 1.3, 1.6, 2.1, 2.4, 2.6). The judgment phases need the scientist and stay in the main session in both arms, so they cancel out and are excluded. Nothing here says what a whole close costs.

Caveats: n=3 per cell, one model (sonnet), a 43-node fixture on a shared database whose unscoped `graph_consistency_check` inflates both arms equally. The crossover between "wash" and "worth it" lies somewhere between 106k and 670k and was not located.
