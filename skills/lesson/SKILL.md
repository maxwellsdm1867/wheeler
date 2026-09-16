---
name: lesson
description: Use when the user asks Wheeler to remember a correction, or save, update, or retire a lesson linked to knowledge-graph resources
argument-hint: "[what to remember or update]"
allowed-tools:
  - Read
  - AskUserQuestion
  - Skill
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__show_node
  - mcp__wheeler_query__query_documents
  - mcp__wheeler_mutations__capture_lesson
  - mcp__wheeler_mutations__accept_skill
  - mcp__wheeler_mutations__retire_skill
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__graph_health
  - mcp__plugin_wh_wheeler_core__search_context
  - mcp__plugin_wh_wheeler_core__show_node
  - mcp__plugin_wh_wheeler_query__query_documents
  - mcp__plugin_wh_wheeler_mutations__capture_lesson
  - mcp__plugin_wh_wheeler_mutations__accept_skill
  - mcp__plugin_wh_wheeler_mutations__retire_skill
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/lesson.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="lesson"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `write`. Orchestration: `skill-dispatch`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
