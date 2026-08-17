# Graph context recipes

The reference half of `wheeler-skill-creator`. Two things live here: the
authoritative **tool surface** (which tool is on which server, and whether it
reads or writes) and the **recipes** (which read to make for which intent, and
how to interpret what comes back).

Read this before you write a generated skill's "Graph read" section. Do not
reconstruct the tool names from memory: they moved in v0.14.0 and a stale name
fails silently.

---

## 1. The tool surface

Wheeler exposes 53 MCP tools across four servers. The server is part of the tool
id, so a tool named under the wrong server is denied exactly as if it did not
exist.

```
mcp__wheeler_core__<tool>        14 tools   health, context, search, cypher, schema, acts
mcp__wheeler_query__<tool>       11 tools   typed read-only listings
mcp__wheeler_mutations__<tool>   18 tools   every write
mcp__wheeler_ops__<tool>         10 tools   validators, scanners, consistency
```

**`mcp__wheeler__<tool>` (no server segment) is dead.** That was the monolith
`wheeler/mcp_server.py`, deleted in v0.14.0. A grant using it denies the tool.
The skill still fires, then quietly cannot read the graph, and the model falls
back to grep without ever reporting that the graph lookup was unavailable. This
is the single most common defect in a hand-written Wheeler skill, and the reason
`audit_skill.py` treats it as a BLOCKER.

### core (14)

| Tool | Class | Use for |
|---|---|---|
| `search_context` | read | **The default read.** Meaning-based match plus 1-hop (all rels) and 2-hop (PROV only) expansion. One call gives seed node plus producing script plus source data. |
| `search_findings` | read | Meaning-based match, no expansion. Cheaper when you only need the statement, not the chain. |
| `show_node` | read | One node by id, with its fields. |
| `run_cypher` | read | Precise neighborhood or aggregate. Read-only by tool design (CREATE/DELETE rejected). |
| `graph_context` | read | Recent activity for session orientation. Not an artifact lookup. |
| `graph_status` | read | Node and edge counts. |
| `graph_health` | read | Connectivity plus the config and credential layer behind a failure. |
| `graph_gaps` | read | Sparse areas, unlinked nodes, thin regions. |
| `propose_merge` | read | Previews a merge (explicitly makes no changes). `execute_merge` is the write. |
| `list_acts` | read | The 39 act names. |
| `get_act` | read | One act body, byte-identical, plus a host orchestration note. |
| `request_log_summary` | read | Recent MCP calls by trace id. |
| `index_node` | **write** | Writes an embedding to `.wheeler/embeddings/`. |
| `init_schema` | **write** | Creates constraints and indexes. |

### query (11)

All read. All take keyword plus limit filters and return a list of one node type.

`query_findings`, `query_hypotheses`, `query_open_questions`, `query_datasets`,
`query_papers`, `query_documents`, `query_plans`, `query_notes`,
`query_executions`, `query_analyses`, `query_review_queue`

Two traps:

- **`query_scripts` is not a tool name.** Script nodes are listed by
  `query_analyses` (the MCP tool wraps the `query_scripts` graph op under the
  older public name). Granting `mcp__wheeler_query__query_scripts` denies it.
- `query_review_queue` is the odd one out: it returns nodes of **any** type left
  `custom_review_state=undiscussed` by a batch ingest, not one type.

### mutations (18)

All write. Every one routes through `execute_tool()`, which is what fires the
triple-write (Neo4j node, `knowledge/{id}.json`, `synthesis/{id}.md`) plus the
embedding, the write receipt, and the trace id.

`add_finding`, `add_hypothesis`, `add_question`, `add_dataset`, `add_paper`,
`add_document`, `add_note`, `add_plan`, `add_execution`, `add_analysis`,
`add_script`, `ensure_artifact`, `link_nodes`, `unlink_nodes`, `update_node`,
`set_tier`, `delete_node`, `execute_merge`

Prefer `ensure_artifact` for registering any file (script, dataset, figure,
plan, document): it hashes and creates-or-updates in one call.

### ops (10)

| Tool | Class | Note |
|---|---|---|
| `hash_file` | read | Most callers want `ensure_artifact` instead. |
| `scan_workspace` | read | |
| `detect_stale` | read | Reports Scripts whose hash no longer matches disk. Detection only. |
| `detect_communities` | read | Connected components over the graph. |
| `extract_citations` | read | |
| `validate_citations` | read | |
| `validate_task_contract` | read | |
| `compute_retrieval_quality` | read | |
| `graph_consistency_check` | **conditional** | Read at `repair=False` (the default). `repair=True` rewrites synthesis files and deletes orphans. |
| `scan_dependencies` | **conditional** | Read at `link_to_graph=False` (the default). `link_to_graph=True` writes edges. |

A read-only skill may grant a conditional tool, but its body must name the safe
default, so the model does not reach for the writing flag. Never grant
`graph_consistency_check` with repair language to a skill that runs in a
development repo: that repo's `knowledge/` tree is test scratch and repair would
reconcile against garbage.

### The plugin spelling

Under the `wh` plugin, servers are namespaced a second time:
`mcp__plugin_wh_wheeler_core__search_context`. `allowed-tools` is an allowlist
matched on the **full** id, so a grant in one spelling does not cover the other.

- A skill in `.claude/skills/` of a project that connects the servers directly
  (via `.mcp.json`) needs only the plain spelling.
- A skill that must also work for a user who installed the `wh` plugin needs
  **both** spellings for every grant. This is what `wheeler/build_plugin.py`
  emits for the generated act skills.

Pick one policy and apply it to every grant. A half-converted list is worse than
either, because the tools that work and the tools that are denied look identical
in review. `scaffold_skill.py --plugin-spellings` emits both.

---

## 2. Picking the read

The intent decides the read. Match the user's ask to a row, take the narrowest
read that answers it, and stop.

| The user is doing this | Read | Why not something else |
|---|---|---|
| Naming an artifact (a figure, a `.mat`, a script) and asking what made it, or asking you to extend it | `search_context(query, hops=2)` | The 2-hop PROV expansion returns the producing script and the source data in the same call. A `query_*` would need you to already know the type. |
| Asking what a number or claim rests on | `search_context` then read the Finding text | `search_findings` returns the statement but not the chain, and provenance is the actual question. |
| Asking for the statement of a result, no chain needed | `search_findings(query)` | Cheaper. Skip the expansion you will not read. |
| Enumerating by type with a filter ("every approved plan", "the open questions") | `query_plans(status=...)`, `query_open_questions()` | Semantic search over a known type is the wrong instrument: it ranks instead of enumerating, so it silently drops the tail. |
| Referencing a node id directly (`F-`, `H-`, `S-`, `D-`, `P-`, `W-`, `Q-`, `N-`, `X-`, `PL-`) | `show_node(id)`, or one `run_cypher` for the neighborhood | Searching for a node you can already name wastes a call and may rank a different node first. |
| Starting a session, or asking what is going on | `graph_context()` | It is the orientation read. Do not use it to find one artifact. |
| Asking what the graph is missing | `graph_gaps()` | |
| A shape no single tool covers (aggregate, multi-hop with a filter, a count) | One `run_cypher` | Do not chain four typed queries to emulate one Cypher. |

**Comparisons need one read per anchor.** Two concepts crammed into one query
skew retrieval toward whichever is better indexed, and you silently lose half
the comparison. Two anchors means two `search_context` calls.

### The budget

One read by default. A second only for: a weak-match retry with a different
paraphrase, a second anchor in a comparison, or a direct-id neighborhood after a
search located the id. Past that you are investigating, which is an act's job
(`/wh:ask`, `/wh:discuss`), not a context-loading skill's.

A skill that dumps thirty nodes into context is worse than no skill: it costs
the tokens and buries the three lines that mattered.

### Writing the query string

A natural-language paraphrase of what the user is asking about, not keyword
stuffing and not the user's sentence verbatim. Domain terms help; filler hurts.

| User said | Query |
|---|---|
| "update this figure" plus path `swap_refit_comparison.png` | `single parameter refit cross-type swap VP ratio` |
| "where does the 4.24 come from" | `VP ratio tau_ref refit cross-type` |
| "look into the extreme parasol target test" | `extreme parasol target single param refit` |

---

## 3. Interpreting what comes back

### Score thresholds

`search_context` and `search_findings` return relevance scores that are skewed
low (RRF fusion over four channels, any of which can be unavailable). Absolute
values matter more than the spread.

| Top score | Meaning | Action |
|---|---|---|
| `> 0.3` | Solid hit | Use it. Report the seed and proceed. |
| `0.1 to 0.3` | Plausible but weak | Retry once with a different paraphrase (synonyms, add a domain term). If it stays in band, use the best result and say so: "weak match (0.18), verify this is the right artifact". |
| `< 0.1` | Miss | One line to the user, then fall back to grep or glob. |

**Surface the miss in one line.** A silent fallback is the dangerous case: when
the graph is authoritative but the query was bad, a near-miss grep result gets
reported with full confidence and the user has no signal that the lookup failed.
One short line ("No graph match for `<thing>`, falling back to filesystem")
preserves trust and costs nothing.

### Field names

Primary key on every node is `id`, not `node_id`.

| Label | Where the content is |
|---|---|
| `Finding` | `text`, sometimes `description` on older nodes: coalesce both |
| `Hypothesis` | `statement` |
| `Script`, `Dataset` | `path` |
| `Document`, `OpenQuestion`, `Paper` | `title`, `text` |
| `Execution` | `command`, `started_at` |
| `Plan` | `title`, `status` |

When unsure in Cypher:
`coalesce(m.path, m.title, m.statement, m.description, substring(m.text,0,120))`

### The id-shape collision

Wheeler ids are `<letter>-<8 hex>`. Scientific domains use identifiers in the
same shape: `F-cda75fbf` may be a cell id from a recording, not a Finding. So an
empty neighborhood from a direct-id Cypher does **not** prove the node is
absent. Fall back to `search_context` with the surrounding context as the query
before telling the user it is not in the graph.

### Never block on the graph

If the MCP server is down, the circuit breaker is open, or the query errors,
say so in one line and continue with filesystem tools. A context-loading skill
that refuses to work when Neo4j is unreachable has converted a soft dependency
into a hard one.

---

## 4. If the skill writes

Default to read-only. Reads compose safely, cost little, and cannot corrupt the
graph. Writes need a reason.

When a skill genuinely must write:

- **Every graph write goes through a `mcp__wheeler_mutations__*` tool.** Those
  route through `execute_tool()`, which is where the triple-write, the write
  receipt, the trace id, and the embedding are wired.
- **Never write `knowledge/*.json` or `synthesis/*.md` with `Write` or `Edit`.**
  That produces a file with no graph node and no receipt, which
  `graph_consistency_check` then reports as drift. Reading those files is fine
  and often correct (that is where full content lives).
- **Confirm before mutating.** The generated skill's body must have an explicit
  step where the scientist approves what is about to be written. Wheeler's own
  chat and discuss acts write only on explicit approval, and a skill that fires
  automatically on phrasing has an even weaker mandate than an act the user
  typed.
- **Consider routing to an act instead.** If the write is a recognized Wheeler
  operation (record a note, register an artifact, close a session), the skill
  should tell the user to run `/wh:note`, `/wh:add`, or `/wh:close` rather than
  reimplement it. The acts carry the citation rules and the session bookkeeping
  that a skill would have to duplicate and would eventually drift from.

---

## 5. Deferring to acts

If the user invoked a `/wh:*` command this turn, that act owns the graph
interaction. A skill that also fires and makes its own reads duplicates calls
and can contradict the act's framing. Every generated skill that reads the graph
should carry this line in its "when not to use" section:

> Active `/wh:*` slash command flow. If the user invoked a Wheeler slash command
> this turn, defer to it: it owns the graph interaction.
