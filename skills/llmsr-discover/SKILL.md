---
name: llmsr-discover
description: Use when the user wants to discover or fit a closed-form equation from a dataset via LLM-SR and ingest the result into the Wheeler knowledge graph
argument-hint: "[dataset id or what to model]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Task
  - Bash(wheeler llmsr:*)
  - Bash(wheeler integrate:*)
  - Bash(codex:*)
  - mcp__wheeler_core__search_context
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__search_context
  - mcp__plugin_wh_wheeler_query__query_datasets
  - mcp__plugin_wh_wheeler_query__query_open_questions
  - mcp__plugin_wh_wheeler_query__query_hypotheses
  - mcp__plugin_wh_wheeler_query__query_findings
  - mcp__plugin_wh_wheeler_mutations__link_nodes
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/llmsr-discover.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="llmsr-discover"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `write`. Orchestration: `subagents`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
