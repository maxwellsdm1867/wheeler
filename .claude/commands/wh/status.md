---
name: wh:status
description: Show investigation progress and route to next action
argument-hint: ""
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - mcp__wheeler__graph_status
  - mcp__wheeler__graph_gaps
  - mcp__wheeler__query_findings
  - mcp__wheeler__query_open_questions
  - mcp__wheeler__detect_stale
  - mcp__neo4j__read_neo4j_cypher
---

Show the current state of everything and suggest what to do next.

## Step 1: Investigation Status
Check `.plans/` for:
- `.continue-here.md` — paused work from a previous session
- `*-CONTEXT.md` — discussions that haven't been planned yet
- Active investigation plans (status: approved or in-progress)
- Completed investigations

## Step 2: Task Status
Check `.logs/` for:
- Run `python -m wheeler.log_summary` via Bash
- Unreviewed completed tasks
- Flagged checkpoints needing judgment
- Failed tasks

## Step 3: Graph Status
Use wheeler MCP tools:
- `graph_status` — node counts by type
- `query_findings` — 5 most recent findings with confidence scores
- `query_open_questions` — top 5 open questions by priority
- `graph_gaps` — unsupported hypotheses, unlinked questions
- `detect_stale` — analyses with changed scripts

## Step 4: Present and Route

```
## Active Work
<investigations in progress, paused work, pending contexts>

## Recent Results
<unreviewed logs, recent findings, flagged checkpoints>

## Graph Summary
<node counts, recent findings, open questions, gaps>

## Suggested Next Action
/wh:<command> — <reasoning>
```

### Routing Logic

| Situation | Suggest |
|-----------|---------|
| `.continue-here.md` exists | `/wh:resume` — pick up paused work |
| Unreviewed task logs | `/wh:reconvene` — review results |
| CONTEXT.md without matching plan | `/wh:plan` — plan the discussed investigation |
| Approved plan not yet executed | `/wh:execute` or `/wh:handoff` — start execution |
| Flagged checkpoints | Present inline for quick decisions |
| No active work, graph has gaps | `/wh:plan` — start new investigation |
| Everything clean | "All caught up. What do you want to explore?" |

Format as a compact summary, not a wall of text.

$ARGUMENTS
