---
name: close
description: Use when ending a Wheeler research session to sweep orphan nodes and write a SESSION synthesis to the knowledge graph
allowed-tools:
  - Read
  - Write
  - Bash
  - Agent
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__graph_status
  - mcp__wheeler_core__graph_gaps
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_core__show_node
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_notes
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_documents
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_query__query_executions
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_mutations__unlink_nodes
  - mcp__wheeler_mutations__delete_node
  - mcp__wheeler_mutations__add_execution
  - mcp__wheeler_mutations__add_document
  - mcp__wheeler_mutations__add_finding
  - mcp__wheeler_mutations__add_note
  - mcp__wheeler_mutations__add_question
  - mcp__wheeler_mutations__update_node
  - mcp__wheeler_ops__detect_stale
  - mcp__wheeler_ops__graph_consistency_check
  - mcp__wheeler_ops__validate_citations
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__graph_health
  - mcp__plugin_wh_wheeler_core__graph_context
  - mcp__plugin_wh_wheeler_core__graph_status
  - mcp__plugin_wh_wheeler_core__graph_gaps
  - mcp__plugin_wh_wheeler_core__run_cypher
  - mcp__plugin_wh_wheeler_core__show_node
  - mcp__plugin_wh_wheeler_query__query_findings
  - mcp__plugin_wh_wheeler_query__query_hypotheses
  - mcp__plugin_wh_wheeler_query__query_open_questions
  - mcp__plugin_wh_wheeler_query__query_notes
  - mcp__plugin_wh_wheeler_query__query_papers
  - mcp__plugin_wh_wheeler_query__query_documents
  - mcp__plugin_wh_wheeler_query__query_datasets
  - mcp__plugin_wh_wheeler_query__query_plans
  - mcp__plugin_wh_wheeler_query__query_executions
  - mcp__plugin_wh_wheeler_mutations__link_nodes
  - mcp__plugin_wh_wheeler_mutations__unlink_nodes
  - mcp__plugin_wh_wheeler_mutations__delete_node
  - mcp__plugin_wh_wheeler_mutations__add_execution
  - mcp__plugin_wh_wheeler_mutations__add_document
  - mcp__plugin_wh_wheeler_mutations__add_finding
  - mcp__plugin_wh_wheeler_mutations__add_note
  - mcp__plugin_wh_wheeler_mutations__add_question
  - mcp__plugin_wh_wheeler_mutations__update_node
  - mcp__plugin_wh_wheeler_ops__detect_stale
  - mcp__plugin_wh_wheeler_ops__graph_consistency_check
  - mcp__plugin_wh_wheeler_ops__validate_citations
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/close.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="close"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `execute`. Orchestration: `subagents`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
