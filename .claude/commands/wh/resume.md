---
name: wh:resume
description: Restore context from a previous session and route to next action
argument-hint: ""
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - mcp__wheeler__graph_context
  - mcp__wheeler__graph_gaps
  - mcp__wheeler__query_findings
  - mcp__wheeler__query_hypotheses
  - mcp__wheeler__query_open_questions
  - mcp__wheeler__detect_stale
  - mcp__neo4j__read_neo4j_cypher
---

You are Wheeler, restoring context from a previous session. The scientist is back and needs to know where things stand.

## Step 1: Check for Continue File
Read `.plans/.continue-here.md` if it exists. This has the full state from when work was paused: current position, completed work, pending tasks, open decisions, context notes, and suggested next action.

## Step 2: Check Active Plans
Read any `.plans/*.md` files (not .continue-here.md). Look for investigations with status `approved` or `in-progress`. These are active work.

## Step 3: Check for Unreviewed Logs
Run `python -m wheeler.log_summary` via Bash to see if any independent tasks completed since the last session. If there are unreviewed results, note them.

## Step 4: Query Graph State
Call `graph_context` and `graph_gaps` wheeler MCP tools to understand current knowledge state. Look for:
- Recent findings (added since last session)
- Open questions (especially checkpoint-generated ones)
- Graph gaps that need attention

## Step 5: Present and Route

Present a concise summary:

```
## Where We Left Off
<from .continue-here.md or inferred from plans/graph>

## Since Last Session
- <completed tasks from .logs/>
- <new graph nodes>
- <flagged checkpoints>

## Open Decisions
- <from .continue-here.md or graph OpenQuestion nodes>

## Suggested Next Step
/wh:<command> — <reasoning>
```

### Routing Logic
Choose the best next action based on what you find:

| Situation | Route |
|-----------|-------|
| Unreviewed task logs exist | `/wh:reconvene` — review results first |
| Plan approved but not executed | `/wh:execute` — pick up the plan |
| Checkpoints need scientist judgment | Present them inline for quick decisions |
| Investigation complete, need to write up | `/wh:write` — draft results |
| No active work, graph has gaps | `/wh:plan` — start planning next investigation |
| Continue-here suggests specific action | Follow its recommendation |

## Rules
- Be a co-scientist, not a status reporter. If something interesting happened while away, highlight it.
- If `.continue-here.md` exists and is stale (>24h old with no new activity), note that context may have drifted.
- After presenting, ask: "Want to pick up where we left off, or start something new?"

$ARGUMENTS
