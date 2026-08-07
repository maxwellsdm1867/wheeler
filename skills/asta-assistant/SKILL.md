---
name: asta-assistant
description: Use when the user wants to run the Asta Research Assistant as a long-range autonomous mission seeded from the Wheeler knowledge graph, then harvest its results back into the graph. Seeds a self-contained mission folder from a Question or Plan, hands off for the scientist to drive with /loop, and ingests the completed work with provenance. Routable as a plan step.
argument-hint: "[mission question, or: harvest <mission-slug>]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(asta --version)
  - Bash(mkdir:*)
  - Bash(cp:*)
  - Bash(ls:*)
  - Bash(git init:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git status)
  - Bash(wheeler integrate:*)
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__show_node
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_review_queue
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__search_context
  - mcp__plugin_wh_wheeler_core__show_node
  - mcp__plugin_wh_wheeler_query__query_open_questions
  - mcp__plugin_wh_wheeler_query__query_plans
  - mcp__plugin_wh_wheeler_query__query_findings
  - mcp__plugin_wh_wheeler_query__query_datasets
  - mcp__plugin_wh_wheeler_query__query_hypotheses
  - mcp__plugin_wh_wheeler_query__query_papers
  - mcp__plugin_wh_wheeler_query__query_review_queue
  - mcp__plugin_wh_wheeler_mutations__link_nodes
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/asta-assistant.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="asta-assistant"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `write`. Orchestration: `none`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
