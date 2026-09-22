---
name: skill-creator
description: Use when the user wants an interview to create or adapt a Wheeler workflow skill for their artifacts and graph context
argument-hint: "[workflow to streamline, or existing skill to adapt]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - Skill
  - mcp__wheeler_core__list_acts
  - mcp__wheeler_core__get_act
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__show_node
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_core__index_node
  - mcp__wheeler_query__*
  - mcp__wheeler_mutations__*
  - mcp__wheeler_ops__graph_consistency_check
  - mcp__plugin_wh_wheeler_core__list_acts
  - mcp__plugin_wh_wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__graph_health
  - mcp__plugin_wh_wheeler_core__search_context
  - mcp__plugin_wh_wheeler_core__show_node
  - mcp__plugin_wh_wheeler_core__run_cypher
  - mcp__plugin_wh_wheeler_core__index_node
  - mcp__plugin_wh_wheeler_query__*
  - mcp__plugin_wh_wheeler_mutations__*
  - mcp__plugin_wh_wheeler_ops__graph_consistency_check
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/skill-creator.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="skill-creator"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `execute`. Orchestration: `skill-dispatch`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
