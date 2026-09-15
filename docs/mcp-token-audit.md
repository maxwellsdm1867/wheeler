# MCP token and time audit (2026-09-14)

Source: 29 Claude Code sessions of the retinaSRM project (2026-08-13 to 2026-09-14),
3,381 tool calls in the transcripts and 11,193 Wheeler MCP calls in that project's
`.wheeler/request_log.jsonl` (the log also sees subagent sessions). Scripts:
`evals/mcp_result_diet/replay.py` (bytes saved by the new shaping, replayed over the
recorded payloads) and the ad hoc transcript parser it grew out of.

The question the scientist asked: the acts send whole payloads back to the model
when the model only needs a few facts to act. Every byte a tool returns is re-read
on every later turn of the session, so result size compounds with session length.

## 1. Where the calls went

| tool | calls | share | consecutive runs of 3 or more | longest run | result bytes (median) |
|---|---|---|---|---|---|
| link_nodes | 1,105 | 32.7% | 87 | 98 | 92 |
| ensure_artifact | 524 | 15.5% | 73 | 38 | 549 |
| run_cypher | 114 | 3.4% | 11 | 11 | 1,394 |
| show_node | 59 | 1.7% | 6 | 9 | 1,963 |
| update_node | 59 | 1.7% | 4 | 15 | 1,359 |
| ToolSearch (schema loads) | 56 | 1.7% | | | |
| add_finding | 46 | 1.4% | 3 | 4 | 61 |
| add_execution | 35 | 1.0% | | | 63 |

Wheeler MCP calls were 60.8% of all tool calls. `link_nodes` plus `ensure_artifact`
were 48%; that pair is addressed by `register_batch` (PR #120, measured in
`evals/batch_registration/REPORT.md`). Everything below is about the rest.

## 2. What the bytes were

Byte share of the top-level keys in the recorded results:

| tool | results | mean bytes | where the bytes were | what the caller acts on |
|---|---|---|---|---|
| update_node | 59 | 1,742 | `changes` 96% (old and new text the caller had just written) | node_id, status, updated_fields |
| ensure_artifact | 524 | 547 | `path` 40%, `stored_path` 29%, `hash` 14%, `previous_hash` 6% | node_id, label, action, stale_downstream when nonzero |
| show_node | 59 | 2,519 | `change_log` 40%, `description` 33%, empty `origin_*` and blank fields | the content fields |
| add_finding | 46 | 734 | `similar_existing` 93% (full text of 3 near duplicates) | node_id plus enough of a hint to recognise a duplicate |
| validate_citations | 8 | 5,819 | `results` 99.9%: 532 rows, 479 of them `valid` | the 53 that were not valid |
| search_context | 4 | 6,129 to 35,847 | `related_nodes` 65% (up to 94 nodes), `relationships` 25% | the seeds' immediate neighbourhood |
| query_open_questions | 6 | 9,829 | full question text, about 1 KB per row | id, priority, a headline |
| search_findings | 7 | 8,153 | full text per hit | id, score, a headline |
| detect_stale | 7 | 6,901 | two 64-char hashes per row | node_id, path, reason |
| run_cypher | 113 | 3,571 (max 30,530) | rows the model asked for | rows the model asked for |
| link_nodes | 1,105 | 90 | already minimal | |

Raw Cypher, by purpose (114 calls): look up nodes by id with neighbours 38; free
text or ad hoc 20; list nodes of a label 15; counts 14; recent nodes by date 10;
stale counts 6; relationship traversals 5; find node by path or title 3; list stale
nodes 2 (the two 30 KB results); one refused write. Most of the date window queries
are prescribed verbatim by `/wh:close`; the id lookups with neighbours are what
`show_node` should have answered.

## 3. Time

From the request log (`latency_ms` per call, 11,193 calls):

| tool | calls | p50 ms | p90 ms | note |
|---|---|---|---|---|
| link_nodes | 4,680 | 31 | 104 | |
| ensure_artifact | 1,567 | 68 | 315 | 8 calls took 32 to 42 minutes, see below |
| run_cypher | 1,364 | 99 | 270 | |
| search_context | 203 | 669 | 1,535 | slowest routine tool (embedding plus 2-hop expansion) |
| search_findings | 205 | 370 | 959 | |
| add_finding | 278 | 216 | 795 | includes the similarity check |
| show_node | 719 | 1 | 3 | 101 errors (14%): "not found" while the graph had the node |

The eight slow `ensure_artifact` calls were all Script registrations on 2026-09-11,
in flight at the same time, and all returned `ok`. That pattern matches in-flight
calls spanning a machine sleep or one blocked shared resource; the logs cannot
separate the two. Neither the wrapper nor the backend has a per-call watchdog, so
a stalled call holds the model's turn for as long as the stall lasts. Not fixed
here; recorded as the open time item.

The `show_node` failures were a correctness cost that showed up as time: each one
was a wasted turn followed by a `run_cypher` to read the same node from the graph.

## 4. Decisions and changes

Principle: a wrapper's result carries what the caller acts on. The full payload is
one flag away (`verbose=true` on writes, `full=true` on reads), and the core
handlers, CLI and their tests keep the complete result.

| change | default now | flag |
|---|---|---|
| `update_node` | no `changes` echo; the diff is still in the node's change_log | `verbose` |
| `ensure_artifact` | node_id, label, action, stale_downstream if nonzero; provenance inputs as a count | `verbose` |
| `add_*` | provenance inputs as a count; near-duplicate hints cut to 120 chars | |
| `show_node` | change_log omitted, empty fields dropped; `node_ids` reads many in one call; `fields` selects; falls back to the graph when the JSON file is missing | `include_change_log` |
| `query_*` (all 11) | text fields cut to 240 chars with the remainder count | `full` |
| `search_findings` | hit text cut to 240 chars | `full` |
| `search_context` | related nodes capped at 20, relationships filtered to those kept | `max_related` |
| `validate_citations` | counts by status plus the citations that are not valid | `verbose` |
| `detect_stale` | no hashes | `verbose` |
| `run_cypher` | 100 rows, with `truncated` and `total_rows` when cut | `limit` |
| docstrings | `ensure_artifact` 2,549 to 1,419 chars, `update_node` 1,255 to 744 | |

Not changed, on purpose: `query_papers` rows are already lean (one 23 KB result was
100 rows the model asked for); trimming Cypher cells would save 9% of that tool's
bytes at the cost of hiding data the model asked for by name; `graph_gaps` already
has `summary=true` and whether an act wants the full buckets is the act's call.

## 5. Effect, replayed over the recorded payloads

`evals/mcp_result_diet/replay.py` applies the new default shaping to the 2,023
Wheeler results in the transcripts:

| tool | calls | before KB | after KB | saved |
|---|---|---|---|---|
| ensure_artifact | 516 | 277.5 | 45.9 | 83% |
| update_node | 58 | 100.1 | 6.2 | 94% |
| show_node | 59 | 145.2 | 88.1 | 39% |
| validate_citations | 8 | 45.5 | 11.3 | 75% |
| search_context | 4 | 58.6 | 29.2 | 50% |
| search_findings | 7 | 55.7 | 16.7 | 70% |
| query_open_questions | 6 | 57.6 | 24.0 | 58% |
| add_finding | 46 | 33.0 | 6.2 | 81% |
| detect_stale | 7 | 47.2 | 24.9 | 47% |
| run_cypher | 113 | 396.1 | 365.1 | 8% |
| all Wheeler results | 2,023 | 1,412 | 812 | 42% |

600 KB fewer result bytes, about 150k tokens, before counting that each of those
bytes was re-read on every later turn. With `register_batch` replacing the
`link_nodes` and `ensure_artifact` loops the remaining large item is raw Cypher,
which is mostly act-prescribed.

Tool schema size (what a session pays when a server's tools load): 36,420 chars for
54 tools after the trims, against 33,818 for 53 before. The two trimmed docstrings
gave back 1,600 chars; `register_batch`'s list-of-dict parameters cost 1,700. Net
neutral, and the schema is loaded once per session while results are paid per turn.

## 6. Open items

- A per-call watchdog (or at least a latency warning in the result) for the
  32-minute stalls.
- `/wh:close` prescribes six raw Cypher sweeps; a typed `query_recent(since, labels)`
  would replace most of the 114 Cypher calls and let the result be shaped.
- `graph_gaps` in the acts could pass `summary=true` and page with `offset`.
