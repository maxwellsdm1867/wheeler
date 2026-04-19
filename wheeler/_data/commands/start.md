---
name: wh:start
description: Start a Wheeler research session or pick the right /wh:* command for your task
argument-hint: "[describe your task, or leave blank]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
  - Skill
  - mcp__wheeler_core__graph_status
  - mcp__wheeler_core__graph_context
---

# Wheeler Router

Route the user to the right `/wh:*` command. Do not ask which command to use: analyze their intent and invoke via the Skill tool.

## Routing procedure

1. If `$ARGUMENTS` is non-empty, treat it as the user's task description and skip to step 3.
2. If `$ARGUMENTS` is empty:
   - Check `.plans/STATE.md` and `.wheeler/` for session context.
   - Ask the user what they're working on via AskUserQuestion with 2-4 options covering the most likely intents (e.g., "starting a new investigation", "adding data to the knowledge graph", "continuing prior work", "writing up results").
3. Match intent to a `/wh:*` command using this priority:
   - **Session lifecycle**: `status`/`resume` at session start; `pause`/`close` at session end; `chat` for casual discussion
   - **Data capture** (concrete artifacts provided): `add` (DOI, paper, dataset, file) over `note` (insight, observation)
   - **Investigation workflow** (progressive): `discuss` -> `plan` -> `execute` -> `write`
   - **Graph operations**: `ask` (query), `compile` (synthesis), `dream` (maintenance)
   - **Collaboration**: `pair` (interactive), `handoff` (background), `reconvene` (review)
   - **Meta**: `report` (time window), `triage` (GitHub issues), `dev-feedback` (Wheeler bugs)
4. Invoke the chosen command via the Skill tool. Prefix with a one-line explanation of the routing choice.
5. Never route to `queue`, `init`, `ingest`, or `update`: those require explicit user invocation.
6. If the task is not Wheeler-related, say so plainly and let the user decide whether to proceed.

## Style

- Never use em dashes. Use colons, commas, periods, parentheses.
- Be brief. The user wants to get into the right mode, not read about modes.
