---
name: note
description: Use when the user wants to capture a research insight as a Wheeler knowledge-graph note
argument-hint: "[note text]"
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
  - mcp__wheeler_mutations__add_note
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_query__query_notes
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__show_node
  - mcp__wheeler_core__search_findings
  - mcp__wheeler_core__index_node
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_mutations__add_note
  - mcp__plugin_wh_wheeler_mutations__link_nodes
  - mcp__plugin_wh_wheeler_query__query_notes
  - mcp__plugin_wh_wheeler_query__query_plans
  - mcp__plugin_wh_wheeler_core__graph_context
  - mcp__plugin_wh_wheeler_core__show_node
  - mcp__plugin_wh_wheeler_core__search_findings
  - mcp__plugin_wh_wheeler_core__index_node
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/note.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="note"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `write`. Orchestration: `none`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
