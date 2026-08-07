---
name: service
description: "Route a research task to the right registered external service (Asta literature, LLM-SR equation discovery, or any enabled service), interview the scientist for that service's inputs, show the assembled request, and dispatch it. Use for \"use a service\", \"invoke X\", \"which tool fits this\", or naming a service by id."
argument-hint: "[service name or describe your task]"
allowed-tools:
  - Read
  - AskUserQuestion
  - Skill
  - Bash(./.venv/bin/python -c *)
  - Bash(python -c *)
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__search_context
  - mcp__plugin_wh_wheeler_core__graph_context
  - mcp__plugin_wh_wheeler_query__query_datasets
  - mcp__plugin_wh_wheeler_query__query_open_questions
  - mcp__plugin_wh_wheeler_query__query_papers
  - mcp__plugin_wh_wheeler_query__query_hypotheses
  - mcp__plugin_wh_wheeler_query__query_findings
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/service.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="service"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `chat`. Orchestration: `skill-dispatch`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
