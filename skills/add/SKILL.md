---
name: add
description: Use when the user provides a DOI, paper, dataset, or file path to record in the Wheeler knowledge graph
argument-hint: "[text, DOI, or file path]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - WebFetch
  - AskUserQuestion
  - mcp__wheeler_mutations__add_finding
  - mcp__wheeler_mutations__add_hypothesis
  - mcp__wheeler_mutations__add_question
  - mcp__wheeler_mutations__add_note
  - mcp__wheeler_mutations__add_paper
  - mcp__wheeler_mutations__add_dataset
  - mcp__wheeler_mutations__add_document
  - mcp__wheeler_mutations__add_script
  - mcp__wheeler_mutations__add_analysis
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_mutations__set_tier
  - mcp__wheeler_core__search_findings
  - mcp__wheeler_core__show_node
  - mcp__wheeler_core__index_node
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_mutations__add_finding
  - mcp__plugin_wh_wheeler_mutations__add_hypothesis
  - mcp__plugin_wh_wheeler_mutations__add_question
  - mcp__plugin_wh_wheeler_mutations__add_note
  - mcp__plugin_wh_wheeler_mutations__add_paper
  - mcp__plugin_wh_wheeler_mutations__add_dataset
  - mcp__plugin_wh_wheeler_mutations__add_document
  - mcp__plugin_wh_wheeler_mutations__add_script
  - mcp__plugin_wh_wheeler_mutations__add_analysis
  - mcp__plugin_wh_wheeler_mutations__link_nodes
  - mcp__plugin_wh_wheeler_mutations__set_tier
  - mcp__plugin_wh_wheeler_core__search_findings
  - mcp__plugin_wh_wheeler_core__show_node
  - mcp__plugin_wh_wheeler_core__index_node
  - mcp__plugin_wh_wheeler_core__graph_context
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/add.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="add"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `write`. Orchestration: `none`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
