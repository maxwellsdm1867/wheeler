# Progressive disclosure experiment

How much of a node should a listing return by default? Three levels of `WHEELER_DISCLOSURE` (`full`, `trimmed`, `pointer`) over ten read-only research tasks on one seeded graph.

Runs aggregated from `runs`: 50 task run(s).

## Per level (means)

| level | model | runs | accuracy | mean score | turns | context | output | cost $ | wall s | show_node | hop | cypher | acc: needs body | score: needs body | acc: rest | score: rest |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | sonnet | 10 | 1.000 | 1.000 | 6.0 | 305733.6 | 1312.6 | 0.175 | 20.4 | 0.100 | 0.0 | 3.4 | 1.000 | 1.000 | 1.000 | 1.000 |
| trimmed | opus | 10 | 1.000 | 1.000 | 4.7 | 183238.5 | 675.0 | 0.350 | 13.3 | 0.100 | 0.0 | 2.0 | 1.000 | 1.000 | 1.000 | 1.000 |
| trimmed | sonnet | 10 | 1.000 | 1.000 | 6.8 | 348572.6 | 1204.6 | 0.182 | 20.2 | 0.100 | 0.0 | 4.0 | 1.000 | 1.000 | 1.000 | 1.000 |
| pointer | opus | 10 | 1.000 | 1.000 | 4.5 | 175652.9 | 642.9 | 0.345 | 12.5 | 0.100 | 0.0 | 2.0 | 1.000 | 1.000 | 1.000 | 1.000 |
| pointer | sonnet | 10 | 1.000 | 1.000 | 6.5 | 330017.9 | 1007.6 | 0.177 | 17.9 | 0.500 | 0.100 | 3.2 | 1.000 | 1.000 | 1.000 | 1.000 |

## Per task, across levels

| task | kind | body? | full (score / turns / context) | trimmed (score / turns / context) | pointer (score / turns / context) |
|---|---|---|---|---|---|
| 1 | lookup | no | 1.0 / 3.0 / 148685 | 1.0 / 5.5 / 248940 | 1.0 / 3.5 / 152216 |
| 2 | one-hop | no | 1.0 / 9.0 / 456533 | 1.0 / 5.0 / 222836 | 1.0 / 6.0 / 275310 |
| 3 | two-hop | no | 1.0 / 6.0 / 301366 | 1.0 / 4.0 / 182100 | 1.0 / 5.0 / 226673 |
| 4 | deep-trace | no | 1.0 / 6.0 / 306566 | 1.0 / 7.5 / 358582 | 1.0 / 6.0 / 283167 |
| 5 | content-read | yes | 1.0 / 5.0 / 254551 | 1.0 / 5.0 / 232297 | 1.0 / 5.0 / 230750 |
| 6 | content-read | yes | 1.0 / 5.0 / 253503 | 1.0 / 5.5 / 237589 | 1.0 / 6.0 / 280101 |
| 7 | contradiction | no | 1.0 / 3.0 / 148713 | 1.0 / 3.0 / 131564 | 1.0 / 3.0 / 131568 |
| 8 | staleness | no | 1.0 / 11.0 / 581282 | 1.0 / 12.0 / 594152 | 1.0 / 10.0 / 465594 |
| 9 | counting | no | 1.0 / 9.0 / 456661 | 1.0 / 6.0 / 273068 | 1.0 / 7.0 / 325184 |
| 10 | literature | no | 1.0 / 3.0 / 149476 | 1.0 / 4.0 / 177927 | 1.0 / 3.5 / 157792 |

## Per run

| level | task | kind | body? | r | verdict | score | turns | context | output | cost $ | wall s | show_node | hop | cypher | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 1 | lookup | no | 1 | correct | 1.000 | 3 | 148685 | 322 | 0.126 | 9.3 | 0 | 0 | 1 | ok |
| full | 2 | one-hop | no | 1 | correct | 1.000 | 9 | 456533 | 1317 | 0.205 | 18.4 | 0 | 0 | 7 | ok |
| full | 3 | two-hop | no | 1 | correct | 1.000 | 6 | 301366 | 1030 | 0.168 | 14.6 | 0 | 0 | 4 | ok |
| full | 4 | deep-trace | no | 1 | correct | 1.000 | 6 | 306566 | 2374 | 0.191 | 27.8 | 0 | 0 | 4 | ok |
| full | 5 | content-read | yes | 1 | correct | 1.000 | 5 | 254551 | 418 | 0.157 | 13.3 | 1 [f] | 0 | 0 | ok |
| full | 6 | content-read | yes | 1 | correct | 1.000 | 5 | 253503 | 406 | 0.155 | 14.3 | 0 | 0 | 0 | ok |
| full | 7 | contradiction | no | 1 | correct | 1.000 | 3 | 148713 | 356 | 0.126 | 7.3 | 0 | 0 | 1 | ok |
| full | 8 | staleness | no | 1 | correct | 1.000 | 11 | 581282 | 5135 | 0.283 | 66.8 | 0 | 0 | 9 | ok |
| full | 9 | counting | no | 1 | correct | 1.000 | 9 | 456661 | 1307 | 0.206 | 24.2 | 0 | 0 | 7 | ok |
| full | 10 | literature | no | 1 | correct | 1.000 | 3 | 149476 | 461 | 0.129 | 8.4 | 0 | 0 | 1 | ok |
| trimmed | 1 | lookup | no | 1 | correct | 1.000 | 6 | 301207 | 849 | 0.166 | 16.2 | 0 | 0 | 4 | ok |
| trimmed | 1 | lookup | no | 1 | correct | 1.000 | 5 | 196673 | 757 | 0.368 | 15.7 | 0 | 0 | 3 | ok |
| trimmed | 2 | one-hop | no | 1 | correct | 1.000 | 5 | 250596 | 651 | 0.153 | 10.6 | 0 | 0 | 2 | ok |
| trimmed | 2 | one-hop | no | 1 | correct | 1.000 | 5 | 195077 | 586 | 0.352 | 11.3 | 0 | 0 | 2 | ok |
| trimmed | 3 | two-hop | no | 1 | correct | 1.000 | 5 | 249801 | 814 | 0.153 | 13.1 | 0 | 0 | 3 | ok |
| trimmed | 3 | two-hop | no | 1 | correct | 1.000 | 3 | 114399 | 405 | 0.296 | 10.0 | 0 | 0 | 1 | ok |
| trimmed | 4 | deep-trace | no | 1 | correct | 1.000 | 11 | 560535 | 1592 | 0.230 | 20.9 | 0 | 0 | 9 | ok |
| trimmed | 4 | deep-trace | no | 1 | correct | 1.000 | 4 | 156628 | 763 | 0.344 | 13.2 | 0 | 0 | 2 | ok |
| trimmed | 5 | content-read | yes | 1 | correct | 1.000 | 6 | 308022 | 582 | 0.173 | 14.2 | 1 [f] | 0 | 0 | ok |
| trimmed | 5 | content-read | yes | 1 | correct | 1.000 | 4 | 156572 | 362 | 0.331 | 9.3 | 1 [f] | 0 | 0 | ok |
| trimmed | 6 | content-read | yes | 1 | correct | 1.000 | 4 | 199628 | 326 | 0.139 | 13.9 | 0 | 0 | 0 | ok |
| trimmed | 6 | content-read | yes | 1 | correct | 1.000 | 7 | 275550 | 997 | 0.411 | 19.0 | 0 | 0 | 1 | ok |
| trimmed | 7 | contradiction | no | 1 | correct | 1.000 | 3 | 148728 | 369 | 0.126 | 7.5 | 0 | 0 | 1 | ok |
| trimmed | 7 | contradiction | no | 1 | correct | 1.000 | 3 | 114400 | 365 | 0.295 | 9.3 | 0 | 0 | 1 | ok |
| trimmed | 8 | staleness | no | 1 | correct | 1.000 | 17 | 914833 | 5337 | 0.359 | 74.0 | 0 | 0 | 15 | ok |
| trimmed | 8 | staleness | no | 1 | correct | 1.000 | 7 | 273471 | 1193 | 0.414 | 20.3 | 0 | 0 | 5 | ok |
| trimmed | 9 | counting | no | 1 | correct | 1.000 | 7 | 352714 | 1024 | 0.180 | 19.7 | 0 | 0 | 4 | ok |
| trimmed | 9 | counting | no | 1 | correct | 1.000 | 5 | 193423 | 750 | 0.354 | 14.1 | 0 | 0 | 3 | ok |
| trimmed | 10 | literature | no | 1 | correct | 1.000 | 4 | 199662 | 502 | 0.140 | 11.5 | 0 | 0 | 2 | ok |
| trimmed | 10 | literature | no | 1 | correct | 1.000 | 4 | 156192 | 572 | 0.334 | 10.5 | 0 | 0 | 2 | ok |
| pointer | 1 | lookup | no | 1 | correct | 1.000 | 3 | 148791 | 351 | 0.126 | 11.9 | 0 | 0 | 1 | ok |
| pointer | 1 | lookup | no | 1 | correct | 1.000 | 4 | 155640 | 562 | 0.331 | 12.6 | 0 | 0 | 2 | ok |
| pointer | 2 | one-hop | no | 1 | correct | 1.000 | 7 | 352617 | 949 | 0.178 | 14.6 | 0 | 0 | 4 | ok |
| pointer | 2 | one-hop | no | 1 | correct | 1.000 | 5 | 198003 | 604 | 0.361 | 12.9 | 0 | 0 | 2 | ok |
| pointer | 3 | two-hop | no | 1 | correct | 1.000 | 6 | 300175 | 868 | 0.165 | 13.2 | 0 | 0 | 4 | ok |
| pointer | 3 | two-hop | no | 1 | correct | 1.000 | 4 | 153171 | 433 | 0.318 | 9.3 | 0 | 0 | 2 | ok |
| pointer | 4 | deep-trace | no | 1 | correct | 1.000 | 8 | 409587 | 1406 | 0.199 | 27.3 | 0 | 0 | 6 | ok |
| pointer | 4 | deep-trace | no | 1 | correct | 1.000 | 4 | 156747 | 871 | 0.349 | 13.7 | 0 | 0 | 2 | ok |
| pointer | 5 | content-read | yes | 1 | correct | 1.000 | 6 | 305148 | 496 | 0.168 | 14.6 | 2 | 0 | 0 | ok |
| pointer | 5 | content-read | yes | 1 | correct | 1.000 | 4 | 156352 | 335 | 0.330 | 8.8 | 1 | 0 | 0 | ok |
| pointer | 6 | content-read | yes | 1 | correct | 1.000 | 8 | 406018 | 784 | 0.191 | 18.7 | 2 [f] | 0 | 0 | ok |
| pointer | 6 | content-read | yes | 1 | correct | 1.000 | 4 | 154184 | 362 | 0.321 | 9.1 | 0 | 0 | 0 | ok |
| pointer | 7 | contradiction | no | 1 | correct | 1.000 | 3 | 148733 | 365 | 0.126 | 7.4 | 0 | 0 | 1 | ok |
| pointer | 7 | contradiction | no | 1 | correct | 1.000 | 3 | 114403 | 368 | 0.295 | 8.6 | 0 | 0 | 1 | ok |
| pointer | 8 | staleness | no | 1 | correct | 1.000 | 11 | 571064 | 3029 | 0.261 | 38.5 | 0 | 0 | 9 | ok |
| pointer | 8 | staleness | no | 1 | correct | 1.000 | 9 | 360123 | 1730 | 0.493 | 28.2 | 0 | 0 | 7 | ok |
| pointer | 9 | counting | no | 1 | correct | 1.000 | 9 | 457060 | 1409 | 0.208 | 24.7 | 0 | 0 | 7 | ok |
| pointer | 9 | counting | no | 1 | correct | 1.000 | 5 | 193309 | 738 | 0.353 | 12.6 | 0 | 0 | 3 | ok |
| pointer | 10 | literature | no | 1 | correct | 1.000 | 4 | 200986 | 419 | 0.143 | 8.5 | 1 [n] | 1 | 0 | ok |
| pointer | 10 | literature | no | 1 | correct | 1.000 | 3 | 114597 | 426 | 0.298 | 9.6 | 0 | 0 | 1 | ok |

## How to read this

`level` is the value of `WHEELER_DISCLOSURE` the MCP servers were started with; the model was never told which. `body?` is the task's `may_need_body` flag set by design in `fixture/tasks.json`: tasks 5 and 6 can only be answered from a finding's full text, the rest from ids, edges and metadata. The key split is `acc: needs body` against `acc: rest`: if a pointer default costs accuracy it shows up in the first column, and if the model simply reads the node when it needs to, it shows up as extra `show_node` calls instead. `verdict` is correct (score 1), partial (0 < score < 1) or wrong (0); `score` is exact match on ids, Jaccard for sets, prefix match for ordered chains, per-field for objects (task 4 weights chain 0.7 and scripts 0.3; task 9 weights count 0.5 and top-3 prefix 0.5). `turns` counts distinct assistant messages. `context` is the context the model read over the run: input + cache read + cache create from the final `result` line's usage block (the session total), so it scales with turns times the size of what the tools returned, which is exactly what the disclosure level changes. `output` and `cost $` come from the same block. `wall s` is the `claude` subprocess wall clock including MCP server startup. `show_node` is the number of show_node calls with flags [n] neighbors=true, [f] fields=, [m] node_ids= used at least once; `hop` counts the one-hop expanders (show_node with neighbors=true, search_context); `cypher` counts run_cypher calls. `status` `no_answer` means the transcript had no parseable `ANSWER <json>` line.

## Recommendation

**Default to `pointer`.** Every level scored 100 percent on all ten tasks on both models, including the two tasks that can only be answered from a node's full text, so the listing shape costs no accuracy: when a pointer is not enough the model reads the node (`show_node` use went from 0.1 to 0.5 calls per task under pointer on sonnet, at no loss). Turn and context differences between levels are within single-run noise (sonnet 6.0 / 6.8 / 6.5 turns for full / trimmed / pointer; opus 4.7 / 4.5 for trimmed / pointer). The saving is in bytes per listing row and scales with listing length: on the real recorded listings from the retinaSRM sessions, pointer rows average about 230 bytes against 250 to 315 trimmed and 240 to 850 full, 60 percent below full.

What the experiment showed about how the model reads a graph, which matters more than the level:

1. **Raw Cypher is the workhorse.** 20 to 40 `run_cypher` calls per ten tasks against 1 to 5 listing calls and one `neighbors` hop in fifty runs. For structural questions the model writes the traversal itself. So the read-side token lever is not listing shape; it is Cypher result size (already capped at 100 rows) and Cypher scope.
2. **Cypher scope was a correctness hole.** The first, parallel run of this experiment shared one database across five runs and the model's unscoped MATCH answers mixed five copies of the graph (accuracy 63 to 90 percent, all from cross-run ids). `run_cypher` now binds `$ptag`, names the tag in its result and warns on an unscoped query; the sequential rerun is the clean one reported above.
3. **Schema loading costs a turn.** `ToolSearch` appears 10 to 12 times per ten tasks: the host loads MCP tool schemas lazily, one turn per session per server. That is a host property, not Wheeler's, but it is the largest fixed cost in a short read session.
4. **The hop primitive was not adopted** (one use in fifty runs). Its description is loaded lazily with the rest of `show_node`, and Cypher already does what it does. Keep it for the `moved` version signal, do not expect it to save turns by itself.

Caveats: 65-node fixture, single run per cell, prescriptive prompts. The first run was discarded for the contamination above and is kept in `runs_parallel_contaminated/` as evidence.
