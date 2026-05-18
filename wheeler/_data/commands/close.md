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
  - mcp__wheeler_mutations__unlink_nodes
  - mcp__wheeler_mutations__delete_node
  - mcp__wheeler_mutations__add_execution
  - mcp__wheeler_mutations__add_document
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
The session window is "since the last close." Find it via Cypher:

```cypher
MATCH (x:Execution {kind: "close"})
RETURN x.started_at AS last_close
ORDER BY x.started_at DESC LIMIT 1
```

- If a row returns, use `last_close` as the window start.
- If no row, default to the last 24 hours.
- Remember this timestamp as `$since`; both phases use it.

### 1.2 Find recent entities
Wheeler stores timestamps as ISO 8601 on `n.updated` (Plan, Document) and/or `n.date` (Finding, Hypothesis, Note, Question, Dataset, Paper). The graph schema does not write `n.created`, so do not query it.

```cypher
MATCH (n)
WHERE coalesce(n.updated, n.date) IS NOT NULL
  AND datetime(coalesce(n.updated, n.date)) >= datetime($since)
  AND NOT n:Execution AND NOT n:Paper
RETURN n.id AS id, labels(n)[0] AS type, n.title AS title,
       coalesce(n.updated, n.date) AS timestamp
ORDER BY timestamp
```

If the Cypher errors OR returns 0 rows on a session that should have activity, fall back to `query_findings`, `query_hypotheses`, `query_notes`, `query_documents`, `query_datasets`, `query_plans`, `query_scripts` and filter by recent timestamps. Also ask the scientist what was worked on if the graph has few recent nodes.

### 1.3 Find orphans
For each recent entity, check if it has a WAS_GENERATED_BY link to an Execution:

```cypher
MATCH (n)
WHERE coalesce(n.updated, n.date) IS NOT NULL
  AND datetime(coalesce(n.updated, n.date)) >= datetime($since)
  AND NOT n:Execution AND NOT n:Paper
  AND NOT (n)-[:WAS_GENERATED_BY]->(:Execution)
RETURN n.id AS id, labels(n)[0] AS type, n.title AS title,
       coalesce(n.updated, n.date) AS timestamp
ORDER BY timestamp
```

If the Cypher errors OR returns 0 rows on a session that should have activity, inspect each recent entity individually with `show_node` and check its relationships, or fall back to the `query_*` tools.

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

Present the batch to the scientist:

```
## Proposed Provenance Links

### Group 1: Discussion about calcium dynamics
- **Execution**: kind="discuss", description="Discussion of calcium oscillation patterns"
- **Inputs (USED)**: [P-a4f2] Bhatt & Bhalla 2024, [D-5678] cell_042 recordings
- **Outputs (WAS_GENERATED_BY)**: [F-3a2b] frequency scaling finding, [H-7c8d] channel gating hypothesis

### Group 2: ...

Approve all / Edit / Skip?
```

### 1.5 Create approved links
For each approved group:
1. `add_execution` with the proposed kind and description
2. `link_nodes(execution_id, input_id, "USED")` for each input
3. `link_nodes(output_id, execution_id, "WAS_GENERATED_BY")` for each output

### 1.6 Staleness pass
Run `detect_stale` to flag any staleness issues before moving to synthesis.

---

## Phase 2: Session Synthesis

### 2.1 Gather what happened in the window
Run these queries against the same `$since` timestamp. Collect the results into a single working set; you will cite every node in the synthesis.

```cypher
// Findings created in window
MATCH (f:Finding) WHERE datetime(f.date) >= datetime($since)
RETURN f.id, f.description, f.confidence, f.tier, f.date
ORDER BY f.date DESC
```

```cypher
// Hypotheses created or updated in window
MATCH (h:Hypothesis)
WHERE datetime(coalesce(h.updated, h.date)) >= datetime($since)
RETURN h.id, h.statement, h.status, coalesce(h.updated, h.date) AS ts
ORDER BY ts DESC
```

```cypher
// Open Questions opened in window (and any resolved in window via status field)
MATCH (q:OpenQuestion) WHERE datetime(q.date_added) >= datetime($since)
RETURN q.id, q.question, q.priority, q.status, q.date_added
ORDER BY q.priority DESC
```

```cypher
// Plans touched in window (status transitions via updated timestamp)
MATCH (pl:Plan) WHERE datetime(pl.updated) >= datetime($since)
RETURN pl.id, pl.title, pl.status, pl.updated, pl.path
ORDER BY pl.updated DESC
```

```cypher
// Executions run in window (the actual work done)
MATCH (x:Execution) WHERE datetime(x.started_at) >= datetime($since)
OPTIONAL MATCH (x)-[:USED]->(s:Script)
RETURN x.id, x.kind, x.description, s.id AS script_id, x.started_at
ORDER BY x.started_at DESC
```

```cypher
// Documents written in window
MATCH (w:Document) WHERE datetime(w.date) >= datetime($since)
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

3. Link the Document to the close Execution:
   `link_nodes(source_id=W-xxxx, target_id=X-close, relationship="WAS_GENERATED_BY")`

4. Link the close Execution to every source node cited:
   For each ID in the `source_nodes` frontmatter list, call
   `link_nodes(source_id=X-close, target_id=<NODE_ID>, relationship="USED")`.
   This gives the Document a full provenance fan-out: the synthesis "used" every finding, hypothesis, question, plan, and execution it summarized.

5. For each plan touched, also create a direct derivation link:
   `link_nodes(source_id=W-xxxx, target_id=PL-yyyy, relationship="WAS_DERIVED_FROM")`.
   This makes the SESSION queryable as evidence for plan progress.

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
- **NEVER auto-create without user approval in Phase 1.** The orphan-sweep batch is always presented and waited on. The synthesis (Phase 2) does NOT need explicit approval per node — but it must cite only nodes that exist in the graph.
- **Papers are never orphans.** They are reference entities, not produced by Wheeler.
- **Executions are never orphans.** They ARE the provenance.
- **Group related orphans.** Multiple findings from one analysis = one Execution.
- **Be concise.** The synthesis is a record, not a essay. Sectioned prose, every claim cited.
- **If the graph is empty in this window**, write a minimal SESSION file noting that, still register it as a Document, still create the close Execution. The boundary matters even if the content is sparse.
- Never use em dashes. Use colons, commas, periods, parentheses.

$ARGUMENTS
