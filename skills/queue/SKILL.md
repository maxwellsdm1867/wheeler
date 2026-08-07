---
name: queue
description: Background task execution (used by wh queue headless runner)
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - mcp__wheeler_core__*
  - mcp__wheeler_query__*
  - mcp__wheeler_mutations__*
  - mcp__wheeler_ops__*
  - mcp__plugin_wh_wheeler_core__*
  - mcp__plugin_wh_wheeler_query__*
  - mcp__plugin_wh_wheeler_mutations__*
  - mcp__plugin_wh_wheeler_ops__*
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/queue.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="queue"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `execute`. Orchestration: `none`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
