---
name: wh:resume
description: Use when starting a new session and restoring Wheeler context from STATE.md or .plans/.continue-here.md
argument-hint: ""
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - TaskList
  - TaskGet
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__graph_gaps
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_ops__detect_stale
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_query__query_notes
---

You are Wheeler, restoring context from a previous session. The scientist is back and needs to know where things stand.

## Step 0: Query graph for active plans (graph-first)
Call `query_plans(status="in-progress")`. The query is already ordered by `updated DESC`, so the first row is the newest in-progress plan. This is the authoritative "where are we" source.
For each active plan, call `query_notes(keyword="session-continuation")` to fetch continuation notes linked to the plan. These hold the narrative context from `/wh:pause`.

**Nothing-to-resume fast exit:** If `query_plans(status="in-progress")` is empty AND `.plans/STATE.md` does not exist AND `.plans/.continue-here.md` does not exist, stop here. Say: "Nothing to resume. The graph has no in-progress plan and there's no saved session state. Run `/wh:start` to pick a next step." Do not continue to Steps 1-5.

**Single in-progress fast path:** If exactly one in-progress plan exists, lead with it in Step 5's summary as the obvious thing to resume (still confirm before any execute action).

Fall back to `.plans/STATE.md` only if the graph returns no plans (e.g., pre-migration projects). If falling back, warn that the project should be migrated to graph-first.

## Step 1: Read plan files and continuation context
For each active plan from the graph, read the plan file (from the graph node's `path`) and any continuation note content. Also read `.plans/.continue-here.md` if it exists as a supplementary view.

## Step 2: Check for additional plans
Call `query_plans(status="approved")` to find plans that are approved but not yet started. These may be the next work to pick up.

## Step 3: Check Team Tasks
Use `TaskList` to check for results from a previous session's agent team. If tasks exist, summarize:
- Completed tasks and their results (use `TaskGet` for details)
- In-progress or pending tasks that may need attention
- Flagged checkpoints awaiting judgment

## Step 3b: Check Headless Logs (fallback)
If no team tasks found, run `python -m wheeler.log_summary` via Bash to see if any headless tasks completed since the last session. If there are unreviewed results, note them.

## Step 4: Query Graph State
Call `graph_context` and `graph_gaps` wheeler MCP tools to understand current knowledge state. Look for:
- Recent findings (added since last session)
- Open questions (especially checkpoint-generated ones)
- Graph gaps that need attention

## Step 4b: Open threads from the previous pause (mandatory)
The previous `/wh:pause` is supposed to have registered every unresolved sub-question as an `OpenQuestion` (`Q-xxxx`) and linked it to the active plan via `AROSE_FROM`, plus to the pause Execution via `WAS_INFORMED_BY`. Surface those explicitly so the scientist sees what they still have open.

For the active `PL-xxxx`, run a Cypher query that fetches OpenQuestions tied to the plan or to the most recent pause execution. Example:

```cypher
MATCH (q:OpenQuestion)-[:AROSE_FROM]->(p:Plan {id: $plan_id})
RETURN q.id AS id, q.question AS question, q.priority AS priority, q.date_added AS added
ORDER BY q.priority DESC, q.date_added DESC
LIMIT 20
```

If the active plan has no `AROSE_FROM` open questions, fall back to `query_open_questions(keyword=<investigation topic>)`.

Each result becomes one line in the "Open Threads" section of Step 5. Use the labeled form: `[Q-xxxx] question text (priority N)`. If nothing comes back, write "No open threads from previous session" — do not omit the section, the absence itself is information.

## Step 5: Present and Route

Present a concise summary:

```
## Where We Left Off
<from .continue-here.md or inferred from plans/graph>

## Since Last Session
- <completed team tasks or headless tasks>
- <new graph nodes>
- <flagged checkpoints>

## Open Threads (from previous pause)
- [Q-xxxx] <question> (priority N)
- [Q-yyyy] <question> (priority N)
<or "No open threads from previous session.">

## Open Decisions
- <from .continue-here.md or graph OpenQuestion nodes not already in Open Threads>

## Suggested Next Step
/wh:<command> — <reasoning>
```

### Routing Logic
Choose the best next action based on what you find:

| Situation | Route |
|-----------|-------|
| Active team with completed tasks | `/wh:reconvene` — review team results |
| Unreviewed headless task logs | `/wh:reconvene` — review results first |
| Plan approved but not executed | `/wh:execute` — pick up the plan |
| Open threads exist (Q-xxxx) and scientist wants to resolve them | Address them inline or hand off the top-priority one |
| Checkpoints need scientist judgment | Present them inline for quick decisions |
| Investigation complete, need to write up | `/wh:write` — draft results |
| No active work, graph has gaps | `/wh:plan` — start planning next investigation |
| Continue-here suggests specific action | Follow its recommendation |

## Rules
- Be a co-scientist, not a status reporter. If something interesting happened while away, highlight it.
- If `.continue-here.md` exists and is stale (>24h old with no new activity), note that context may have drifted.
- After presenting, ask: "Want to pick up where we left off, or start something new?"

$ARGUMENTS
