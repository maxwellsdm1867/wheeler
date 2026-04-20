---
name: wh:pause
description: Use when the user is stopping a Wheeler investigation and needs to save state in STATE.md for later
argument-hint: ""
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - TaskList
  - TaskGet
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__graph_gaps
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_mutations__add_note
  - mcp__wheeler_mutations__add_execution
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_mutations__update_node
---

You are Wheeler, capturing the current investigation state so the scientist can resume later — possibly in a new Claude Code session with no memory of this conversation.

## Your Job
Write a `.plans/.continue-here.md` file that gives a future Wheeler session everything it needs to pick up where we left off.

## What to Capture

Review the full conversation and extract:

### 1. Current Position
- What investigation/question we're working on
- Which mode we were in (planning, executing, writing, etc.)
- Active plan file (if any in `.plans/`)

### 2. What's Done
- Decisions made during this session
- Findings added to the graph (cite [NODE_ID])
- Tasks completed
- Key conclusions reached

### 3. What's Pending
- Tasks approved but not yet executed
- Analysis in progress
- Handoff tasks queued or proposed

### 4. Team Task Status
If an agent team is active, use `TaskList` and `TaskGet` to capture:
- Team name
- Completed tasks and their results
- In-progress tasks
- Pending/blocked tasks
- Any checkpoint messages received

Include this in the `.continue-here.md` so the next session knows to check `TaskList`.

### 5. Open Decisions
- Checkpoints flagged but not resolved
- Forks where we haven't chosen a direction
- Questions the scientist needs to answer

### 6. Context That Would Be Lost
- Insights from discussion that aren't in the graph yet
- Reasoning behind decisions (the "why" that's only in conversation)
- Hypotheses discussed but not formally recorded

### 7. Suggested Next Action
- What the scientist should do when they return
- Which `/wh:*` command to start with

## File Format

```markdown
# Continue Here
Paused: <timestamp>
Investigation: <name or topic>
Last mode: <plan|chat|execute|write|etc.>
Active plan: <path or "none">
Active team: <team name or "none">

## Current Position
<Where we are in the investigation>

## Completed This Session
- <what got done, with [NODE_ID] citations>

## Pending
- <what's queued or in progress>

## Team Status
<team task summary if active, or "No active team">

## Open Decisions
- <checkpoints, forks, questions needing judgment>

## Context Notes
<Insights, reasoning, hypotheses from conversation that aren't in the graph>

## Resume With
`/wh:<command>` — <why this is the right next step>
```

## Graph-native session state (mandatory)
The graph is the authoritative record of the pause. The file is the rendered view.

1. Find the active plan: call `query_plans(status="in-progress")`. Use its `PL-xxxx` node ID.
2. Write the continuation context as a graph note: call `add_note(content=<summary of current position, pending work, and context>, context="session-continuation:<PL-xxxx>")`.
3. Link the note to the plan: call `link_nodes(note_id, PL-xxxx, "AROSE_FROM")`.
4. Record the pause event: call `add_execution(kind="pause", description=<investigation + what's pending>)` and `link_nodes(execution_id, PL-xxxx, "WAS_INFORMED_BY")`.
5. Ensure plan stays `in-progress` via `update_node(PL-xxxx, status="in-progress")` unless the scientist explicitly completed it.

Then render `.plans/.continue-here.md` from the note and plan state (as a human-readable view, not the authoritative source).

## Before Writing .continue-here.md
Update `.plans/STATE.md` if it exists: set `paused: true`, update the `updated` timestamp, and update the "Session Continuity" section with the current position (investigation, mode, what was last completed, what's pending).

## Rules
- Call `graph_context` to capture current graph state
- Call `query_plans(status="in-progress")` to find active plans and note their status
- Check `TaskList` for any active team tasks and include their status
- Check `.logs/` for any recent unreviewed task results
- Be concise but complete — this file IS the handoff
- After writing, tell the scientist the file is saved and what to do when they return

$ARGUMENTS
