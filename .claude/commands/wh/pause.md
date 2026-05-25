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
  - mcp__wheeler_mutations__add_finding
  - mcp__wheeler_mutations__add_question
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

## Open Threads
<one line per new OpenQuestion created in this session's sweep>
- [Q-xxxx] <question text> (priority N)
- [Q-yyyy] <question text> (priority N)
<or "None — no unresolved threads from this session." if the sweep produced none>

## Open Decisions
- <checkpoints, forks, questions needing judgment that are NOT yet Q-xxxx nodes>

## Context Notes
<Insights and reasoning from conversation. Pointers to the [F-xxxx] and [N-xxxx] registered during the intermediate-artifact sweep — do NOT re-paste their full content here; the graph holds it.>

## Resume With
`/wh:<command>` — <why this is the right next step>
```

## Intermediate-artifact sweep (mandatory, do this first)

The session almost certainly produced work that lives only in the conversation transcript: a result the scientist talked through, a methodology choice they settled, a sub-question that opened mid-thought. If we don't promote those to the graph at pause, they vanish on resume.

Walk the conversation chronologically. For each substantive intermediate item, classify and register it:

| What it is in the conversation | Graph primitive | Tool |
|---|---|---|
| An observation or result that was reached and the scientist agreed with (resolved) | Finding | `add_finding(statement=..., tier="generated")` |
| A decision, methodology choice, rationale, or context that explains "why we did it this way" | Note | `add_note(content=..., context=...)` |
| A sub-question, fork, "we should check X later", an unresolved thread, anything the scientist did NOT sign off on yet | OpenQuestion | `add_question(question=..., priority=<1-10>)` |

Rules for the sweep:
- **Be conservative.** Only register items that are clearly load-bearing for the investigation. Casual chitchat, debugging detours, and abandoned tangents stay in the transcript.
- **Resolved vs. open is a status call.** If the scientist explicitly accepted a result or made a choice, treat it as resolved (Finding / Note). If anything is "we'll come back to this", "not sure yet", "TODO", "branch we didn't take", treat it as open (`add_question`). When unsure, prefer `add_question` — it is safe to leave an open thread, but it is wrong to forge a finding the scientist hasn't endorsed.
- **Link everything to the active plan.** After creating each new node, call `link_nodes(new_node_id, PL-xxxx, "AROSE_FROM")`.
- **Collect the new `Q-xxxx` IDs.** You will need them for the `.continue-here.md` Open Threads section and for the pause-execution provenance link below.

If the sweep produces nothing, say so explicitly in the continuation note ("No new intermediate artifacts; session was discussion-only.") so resume doesn't go hunting.

## Graph-native session state (mandatory)
The graph is the authoritative record of the pause. The file is the rendered view.

1. Find the active plan: call `query_plans(status="in-progress")`. Use its `PL-xxxx` node ID.
2. Write the continuation context as a graph note: call `add_note(content=<summary of current position, pending work, and context>, context="session-continuation:<PL-xxxx>")`.
3. Link the note to the plan: call `link_nodes(note_id, PL-xxxx, "AROSE_FROM")`.
4. Record the pause event: call `add_execution(kind="pause", description=<investigation + what's pending + count of new findings/notes/open questions>)` and `link_nodes(execution_id, PL-xxxx, "WAS_INFORMED_BY")`.
5. For **each new `Q-xxxx`** created in the sweep above, also call `link_nodes(execution_id, Q-xxxx, "WAS_INFORMED_BY")` so `/wh:resume` can find which open threads this pause opened.
6. Ensure plan stays `in-progress` via `update_node(PL-xxxx, status="in-progress")` unless the scientist explicitly completed it.

Then render `.plans/.continue-here.md` from the note and plan state (as a human-readable view, not the authoritative source).

## Before Writing .continue-here.md
Update `.plans/STATE.md` if it exists: set `paused: true`, update the `updated` timestamp, and update the "Session Continuity" section with the current position (investigation, mode, what was last completed, what's pending).

## Rules
- Call `graph_context` to capture current graph state
- Call `query_plans(status="in-progress")` to find active plans and note their status
- Always run the intermediate-artifact sweep BEFORE writing the continuation note. The sweep is what makes a pause recoverable: it converts conversation transcript into graph-resident artifacts (Findings, Notes, OpenQuestions) tied to the plan.
- Prefer `add_question` over `add_note` when the scientist hasn't endorsed an answer. An open `Q-xxxx` is a graph-visible "come back to this" pointer; a note buried in continuation prose is not.
- Check `TaskList` for any active team tasks and include their status
- Check `.logs/` for any recent unreviewed task results
- Be concise but complete — this file IS the handoff
- After writing, tell the scientist the file is saved AND list the new `[Q-xxxx]` open threads inline so they see what needs revisiting, then say what to do when they return.

$ARGUMENTS
