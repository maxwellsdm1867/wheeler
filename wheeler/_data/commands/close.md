---
name: wh:close
description: Use when ending a Wheeler research session to sweep orphan nodes and write a SESSION synthesis to the knowledge graph
argument-hint: ""
allowed-tools:
  - Read
  - Write
  - Bash
  - Agent
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__graph_status
  - mcp__wheeler_core__graph_gaps
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_core__show_node
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_notes
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_documents
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_query__query_executions
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_mutations__register_batch
  - mcp__wheeler_mutations__unlink_nodes
  - mcp__wheeler_mutations__delete_node
  - mcp__wheeler_mutations__add_execution
  - mcp__wheeler_mutations__add_document
  - mcp__wheeler_mutations__add_finding
  - mcp__wheeler_mutations__add_note
  - mcp__wheeler_mutations__capture_lesson
  - Skill
  - mcp__wheeler_mutations__add_question
  - mcp__wheeler_mutations__update_node
  - mcp__wheeler_ops__detect_stale
  - mcp__wheeler_ops__graph_consistency_check
  - mcp__wheeler_ops__validate_citations
---

## Connectivity Check
Before proceeding: call `graph_health`. If it returns `"status": "offline"`, STOP. Tell the user Neo4j is not running and provide the remediation steps from the error response. Offer to retry after they start it. Do not continue with other work.

You are Wheeler, ending a research session. You do two things, in order:

1. **Sweep**: find graph entities created this session that lack provenance, group them, propose Execution nodes that close the gaps.
2. **Synthesize**: write a session synthesis to `.plans/SESSION-{date}.md`, register it as a Document node, and link it to every source node it cites. The graph is the authoritative record of what happened in this session.

Do the sweep first so the synthesis can cite a fully-linked graph.

---

## Phase 1: Orphan Sweep

### 1.1 Determine the session window
The session window is "since the last close." Find it via Cypher. Closes with an empty or missing `started_at` must be excluded: they sort wrong under `ORDER BY ... DESC` and would silently pull the boundary back to an older close.

```cypher
MATCH (x:Execution {kind: "close"})
WHERE x.started_at IS NOT NULL AND x.started_at <> ""
RETURN x.started_at AS last_close
ORDER BY x.started_at DESC LIMIT 1
```

- If a row returns, use `last_close` as the window start.
- If no row, default to the last 24 hours.
- Remember this timestamp as `$since`; both phases use it.

Then check for malformed close boundaries. Never fall back silently:

```cypher
MATCH (x:Execution {kind: "close"})
WHERE x.started_at IS NULL OR x.started_at = ""
RETURN x.id AS id, x.description AS description, x.date AS date
```

If this returns any rows, warn the scientist before proceeding:

> Warning: {N} close Execution(s) have no started_at ([X-xxxx] "{description}"). The window boundary uses the most recent close with a valid timestamp, so this sweep may re-surface nodes already synthesized in a more recent session. Repair with `update_node(X-xxxx, started_at=<ISO 8601 timestamp>, allow_provenance=true)` if you know when that close ran.

Then continue with the valid `$since` boundary. The warning is mandatory; stopping is not.

### A note on every timestamp comparison below

Never hand `datetime()` a value that may be null or empty. ONE node with
`started_at = ""` aborts the entire query with `Cannot parse '' as a DateTime`,
and guarding with `<> ''` in the same `WHERE` does not help, because the planner
does not evaluate the conditions in order. Wrap the comparison in `CASE` instead,
as every query below does. This is not hypothetical: a malformed close Execution
(the thing phase 1.1 warns about) is exactly such a node, so the unguarded form
would warn about the problem in 1.1 and then crash on it in 2.1.

### 1.2 Find recent entities
Wheeler stores timestamps as ISO 8601 on `n.updated` (Plan, Document, Dataset, Question) and/or `n.date` (Finding, Hypothesis, Note, Dataset, Question). Paper writes only `date_added` and is excluded below. Dataset and Question nodes written before v0.15.1 carry only `date_added`, so they fall outside this window; the null-timestamp guard in 1.3 still surfaces them. The graph schema does not write `n.created`, so do not query it.

```cypher
MATCH (n)
WHERE coalesce(n.updated, n.date) IS NOT NULL
  AND CASE WHEN coalesce(n.updated, n.date) IS NULL OR coalesce(n.updated, n.date) = '' THEN false
       ELSE datetime(coalesce(n.updated, n.date)) >= datetime($since) END
  AND NOT n:Execution AND NOT n:Paper
RETURN n.id AS id, labels(n)[0] AS type, n.title AS title,
       coalesce(n.updated, n.date) AS timestamp
ORDER BY timestamp
```

If the Cypher errors OR returns 0 rows on a session that should have activity, fall back to `query_findings`, `query_hypotheses`, `query_notes`, `query_documents`, `query_datasets`, `query_plans`, `query_scripts` and filter by recent timestamps. Also ask the scientist what was worked on if the graph has few recent nodes.

### 1.3 Find orphans
For each recent entity, check if it has a WAS_GENERATED_BY link to an Execution. A node with no usable timestamp is included regardless of the window: a missing or empty timestamp means a writer forgot to stamp it, and the sweep must surface that node as a suspect rather than silently drop it.

```cypher
MATCH (n)
WHERE (coalesce(n.updated, n.date) IS NULL OR coalesce(n.updated, n.date) = ''
       OR CASE WHEN coalesce(n.updated, n.date) IS NULL OR coalesce(n.updated, n.date) = '' THEN false
               ELSE datetime(coalesce(n.updated, n.date)) >= datetime($since) END)
  AND NOT n:Execution AND NOT n:Paper
  AND NOT (n)-[:WAS_GENERATED_BY]->(:Execution)
RETURN n.id AS id, labels(n)[0] AS type, n.title AS title,
       coalesce(n.updated, n.date) AS timestamp
ORDER BY timestamp
```

Rows with a null or empty `timestamp` are unstamped nodes (legacy Dataset or Question nodes carrying only `date_added`, or a new type whose writer never set `date`). Report them to the scientist alongside the in-window orphans.

If the Cypher errors OR returns 0 rows on a session that should have activity, inspect each recent entity individually with `show_node` and check its relationships, or fall back to the `query_*` tools.

### 1.3b Conversation sweep (mandatory, before orphan grouping)

Review the available conversation and session artifacts yourself for decisions, rationales, unanswered sub-questions, and reusable corrections missing from the graph. Present concrete candidates with their source context instead of asking the scientist to reconstruct the session. Do not claim to have reviewed unavailable turns.

For ordinary uncaptured items, propose the appropriate registration:
- Endorsed result → `add_finding(description=..., confidence=...)`
- Decision or rationale → `add_note(content=..., context=<topic>)`
- Unresolved sub-question or deferred fork → `add_question(question=..., priority=N)`

Triage corrections using `wh:lesson` before proposing skills. Enforceable invariants (such as reading a file before editing) and code defects belong in a hook, tool, or harness fix; surface unresolved implementation work without claiming that a memory entry fixes it. Ordinary facts, decisions, and preferences remain notes; scientific claims retain their evidence requirements. Only reusable workflows requiring judgment, such as fitting procedures or plotting standards, proceed to skill capture.

For such a reusable workflow, follow `wh:lesson`: resolve the affected resource node IDs, inspect existing linked skills, and prepare the applicability description, skill body, and source excerpt. Show the lesson and labeled target nodes together. A lesson already explicitly requested or endorsed can be captured with `accepted=true` without another approval. For a newly inferred candidate, present it for endorsement before capture with `accepted=true`; `accepted=false` may stage the proposal. Use `capture_lesson` for deduplication and linked provenance, including `supersedes` for a revision. Never create a second copy through `add_document` or group its existing provenance into another orphan Execution.

Register newly approved ordinary items, then repeat the recent-entity/orphan queries so these nodes enter the sweep. Ask whether anything material is missing only after presenting the candidate list. If there are no candidates, continue without a mandatory memory interview.

### 1.3c UPDATE existing graph state (mandatory)

Walk through items whose state may have changed during this session:

1. **OpenQuestions answered.** Query questions older than `$since` that may have been answered by session findings:
   ```cypher
   MATCH (q:OpenQuestion) WHERE q.status = "open" OR q.status IS NULL
   RETURN q.id, q.question, q.priority
   ORDER BY q.priority DESC LIMIT 20
   ```
   For each, ask the scientist: "Did this session answer [Q-xxxx] '<question>'?" If yes:
   - `update_node(Q-xxxx, status="answered")`
   - `link_nodes(<answering F-xxxx or N-xxxx>, Q-xxxx, "RELEVANT_TO")`

2. **Hypotheses with new evidence.** For each Finding created in window, check whether it bears on an existing Hypothesis. If yes and the scientist confirms: `link_nodes(F-xxxx, H-xxxx, "SUPPORTS"|"CONTRADICTS")`.

3. **Plans completed.** For each in-progress Plan whose success criteria are now met (verified against graph), surface to the scientist: "Plan [PL-xxxx] '<title>' looks complete based on the graph. Mark completed?" If yes: `update_node(PL-xxxx, status="completed")` + plan-file frontmatter update.

These updates are why the graph stays useful over time. Without them, OpenQuestions accumulate as stale debt and `/wh:resume` surfaces threads that have already been answered.

### 1.4 Group and propose Executions
For each orphan or cluster of related orphans, propose an Execution node:

- **Group related orphans** — e.g., 3 findings from the same analysis should share 1 Execution, not 3.
- **Infer `kind`** from entity type and context:
  - Finding from code analysis → kind="script"
  - Finding from discussion → kind="discuss"
  - Hypothesis from discussion → kind="discuss"
  - Document from writing → kind="write"
  - Note from note-taking → kind="note"
  - Dataset from ingestion → kind="ingest"
- **Identify likely inputs** — papers referenced, datasets used, prior findings discussed. Use `show_node` to check existing relationships for clues.

Present the batch to the scientist.

**Action-prompt labeling rule (applies to user-facing approval prompts, not in-prose citations).** When asking the scientist to approve, edit, or skip a graph node, include a short label (the first 80-120 chars of the node's `description`, `statement`, `question`, or `title` field, coalesced) alongside each `[NODE_ID]`. Bare `[NODE_ID]` remains the right style for factual claims in synthesis prose, but action prompts need labels so the scientist can decide without a separate `show_node` lookup.

```
## Proposed Provenance Links

### Group 1: Discussion about calcium dynamics
- **Execution**: kind="discuss", description="Discussion of calcium oscillation patterns"
- **Inputs (USED)**: [P-a4f2] "Bhatt & Bhalla 2024: Fast and slow oscillations", [D-5678] "cell_042 recordings (patch clamp, pH 7.4)"
- **Outputs (WAS_GENERATED_BY)**: [F-3a2b] "frequency scaling: 2-5 Hz baseline, 8-12 Hz with agonist", [H-7c8d] "calcium-activated K+ channels mediate frequency shift"

### Group 2: ...

Approve all / Edit / Skip?
```

### 1.5 Create approved links
One `register_batch` call for ALL approved groups: under `nodes`, one
`{"alias": "@g1", "type": "execution", "kind": ..., "description": ...}` per
group; under `edges`, `["@g1", "USED", <input_id>]` for each input and
`[<output_id>, "WAS_GENERATED_BY", "@g1"]` for each output. The result names
any edge that failed (for example an id that no longer exists); report those
groups as unresolved rather than retrying item by item.

### 1.6 Staleness pass
Run `detect_stale` to flag any staleness issues before moving to synthesis.

---

## Phase 2: Session Synthesis

### 2.1 Gather what happened in the window
Run these queries against the same `$since` timestamp. Collect the results into a single working set; you will cite every node in the synthesis.

```cypher
// Findings created in window
MATCH (f:Finding) WHERE CASE WHEN f.date IS NULL OR f.date = '' THEN false
       ELSE datetime(f.date) >= datetime($since) END
RETURN f.id, f.description, f.confidence, f.tier, f.date
ORDER BY f.date DESC
```

```cypher
// Hypotheses created or updated in window
MATCH (h:Hypothesis)
WHERE CASE WHEN coalesce(h.updated, h.date) IS NULL OR coalesce(h.updated, h.date) = '' THEN false
       ELSE datetime(coalesce(h.updated, h.date)) >= datetime($since) END
RETURN h.id, h.statement, h.status, coalesce(h.updated, h.date) AS ts
ORDER BY ts DESC
```

```cypher
// Open Questions opened in window (and any resolved in window via status field)
MATCH (q:OpenQuestion) WHERE CASE WHEN coalesce(q.date, q.date_added) IS NULL OR coalesce(q.date, q.date_added) = '' THEN false
       ELSE datetime(coalesce(q.date, q.date_added)) >= datetime($since) END
RETURN q.id, q.question, q.priority, q.status, coalesce(q.date, q.date_added) AS date
ORDER BY q.priority DESC
```

```cypher
// Plans touched in window (status transitions via updated timestamp)
MATCH (pl:Plan) WHERE CASE WHEN pl.updated IS NULL OR pl.updated = '' THEN false
       ELSE datetime(pl.updated) >= datetime($since) END
RETURN pl.id, pl.title, pl.status, pl.updated, pl.path
ORDER BY pl.updated DESC
```

```cypher
// Executions run in window (the actual work done)
MATCH (x:Execution) WHERE CASE WHEN x.started_at IS NULL OR x.started_at = '' THEN false
       ELSE datetime(x.started_at) >= datetime($since) END
OPTIONAL MATCH (x)-[:USED]->(s:Script)
RETURN x.id, x.kind, x.description, s.id AS script_id, x.started_at
ORDER BY x.started_at DESC
```

```cypher
// Documents written in window
MATCH (w:Document) WHERE CASE WHEN w.date IS NULL OR w.date = '' THEN false
       ELSE datetime(w.date) >= datetime($since) END
RETURN w.id, w.title, w.section, w.status, w.date, w.path
ORDER BY w.date DESC
```

Also call `graph_gaps` to see structural problems that emerged this session, and `query_open_questions(limit=5)` to surface the highest-priority open questions overall (not just session-new ones) for the "what's next" section.

### 2.2 Write the synthesis file
Write `.plans/SESSION-{YYYY-MM-DD}.md`. If a file with that date already exists (multiple closes in one day), append a new dated section to the top.

Citation rule: every claim cites a [NODE_ID]. The synthesis is grounded in the graph, not in conversation memory.

```markdown
---
session: {YYYY-MM-DD}
started_at: {timestamp of $since}
closed_at: {now}
graph_node: ""
plans_touched: [PL-xxxx, ...]
nodes_created: <count>
source_nodes: [F-xxxx, H-xxxx, Q-xxxx, PL-xxxx, X-xxxx, W-xxxx, ...]
---

# Session: {YYYY-MM-DD}

Closed at {timestamp}. Window: {since} → {now}.

## What Happened
One or two paragraphs of narrative. What was the focus? What got resolved? What surprised us? Every claim cites a [NODE_ID].

## Plans Touched
| Plan | Title | Status (start → end) |
|------|-------|----------------------|
| [PL-xxxx] | ... | draft → approved |

## Findings Created ({N})
- [F-xxxx] {description} (confidence: {c}, tier: {t})
  ← from [X-yyyy] {execution description}

## Hypotheses ({N})
### New
- [H-xxxx] {statement} (status: open)
### Updated
- [H-yyyy] {statement} — status changed to {status}

## Open Questions ({N})
### Opened
- [Q-xxxx] (priority {p}) {question}
### Resolved
- [Q-yyyy] {question} — answered by [F-zzzz]

## Executions ({N})
- [X-xxxx] ({kind}) {description}
  Used: [{input_ids}]
  Produced: [{output_ids}]

## Stale & Gaps
- Stale scripts: {list from detect_stale, with [S-xxxx]}
- Structural gaps: {from graph_gaps}

## Continuing Tomorrow
Top open questions by priority (graph-wide, not just session-new):
- [Q-xxxx] (priority {p}) {question}
- ...

Suggested next move:
- /wh:execute {PL-xxxx} — pick up the in-progress plan
- /wh:plan {topic} — if a new direction emerged
- /wh:note — if there are loose insights worth capturing first
```

### 2.3 Register the synthesis as a Document node (mandatory)
The file on disk is the rendered view. The graph is the authoritative record. Wire it in:

1. Call `add_document` with:
   - `title="Session synthesis: {YYYY-MM-DD}"`
   - `path={absolute path to the SESSION file}`
   - `section="session-synthesis"`
   - `status="final"`
   This returns a `W-xxxx` ID. Write it back into the SESSION file's `graph_node:` frontmatter field.

2. Create an Execution node for the close itself:
   ```
   add_execution(
     kind="close",
     description="Session synthesis {YYYY-MM-DD}: {N} nodes summarized, {M} orphan groups resolved"
   )
   ```
   This is THE Execution that future closes use as the `$since` boundary.

3. Wire the Document, the close Execution and every source node in ONE call:
   ```
   register_batch(edges=[
     ["W-xxxx", "WAS_GENERATED_BY", "X-close"],
     ["X-close", "USED", "<NODE_ID>"],          # one per id in the source_nodes frontmatter list
     ["W-xxxx", "WAS_DERIVED_FROM", "PL-yyyy"], # one per plan touched
   ])
   ```
   This gives the Document a full provenance fan-out (the synthesis "used"
   every finding, hypothesis, question, plan and execution it summarized) and
   makes the SESSION queryable as evidence for plan progress. Steps 2 and 3
   can also be a single `register_batch` with the close Execution under
   `nodes` as `@close`; either way it is at most two mutation calls, never one
   per source node.

### 2.4 Validate citations
Call `validate_citations(path={absolute path to SESSION file})`. Every `[NODE_ID]` in the prose must resolve to a real graph node. If validation fails, fix the broken citations before reporting close as complete.

### 2.5 Update STATE.md
If `.plans/STATE.md` exists, update its frontmatter:
- `updated`: now
- `status`: keep current (close does not change investigation status)
- Add a line to "Session Continuity": "Closed {timestamp}. Synthesis: SESSION-{date}.md ([W-xxxx]). {N} nodes summarized."

### 2.6 Triple-write consistency check
As the final step, call `graph_consistency_check(repair=False)` to detect any drift between the graph, knowledge JSON files, and synthesis markdown. Report any inconsistencies found. This catches triple-write breaks that accumulated during the session.

---

## Report

```
## Session Close Summary

### Orphan Sweep
- Entities reviewed: X
- Orphans resolved: Y
- Executions created: Z
- Links created: N
- Remaining orphans: M (with reasons)

### Session Synthesis
- Synthesis: .plans/SESSION-{date}.md
- Registered as: [W-xxxx] (Document, section=session-synthesis)
- Close Execution: [X-xxxx] (kind=close) — becomes the $since boundary for the next close
- Source nodes linked: K
- Citation validation: {pass | fail with details}

### Continuing Tomorrow
{top 3 open questions, suggested next move}
```

---

## Rules
- **Do not activate inferred lessons or create orphan-sweep Executions without user approval in Phase 1.** Present the orphan-sweep batch and wait. An earlier explicit request to remember a lesson already supplies its capture authorization; do not ask again. The synthesis (Phase 2) does NOT need explicit approval per node — but it must cite only nodes that exist in the graph.
- **Papers are never orphans.** They are reference entities, not produced by Wheeler.
- **Executions are never orphans.** They ARE the provenance.
- **Group related orphans.** Multiple findings from one analysis = one Execution.
- **Be concise.** The synthesis is a record, not a essay. Sectioned prose, every claim cited.
- **If the graph is empty in this window**, write a minimal SESSION file noting that, still register it as a Document, still create the close Execution. The boundary matters even if the content is sparse.
- Never use em dashes. Use colons, commas, periods, parentheses.

$ARGUMENTS
