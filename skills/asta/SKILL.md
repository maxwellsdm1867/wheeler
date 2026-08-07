---
name: asta
description: "Route a research task to the right Asta service (Paper Finder, Semantic Scholar, Theorizer, or Literature Reports) and dispatch its act. Use for \"use asta\", \"which asta tool\", \"find/look up/theorize/review with asta\", or when unsure which Asta adapter fits."
argument-hint: "[describe your task, or leave blank to be asked]"
allowed-tools:
  - Read
  - AskUserQuestion
  - Skill
  - Bash(asta auth status)
  - Bash(./.venv/bin/python -c *)
  - Bash(python -c *)
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__search_context
  - mcp__plugin_wh_wheeler_core__graph_context
  - mcp__plugin_wh_wheeler_query__query_papers
  - mcp__plugin_wh_wheeler_query__query_open_questions
  - mcp__plugin_wh_wheeler_query__query_hypotheses
  - mcp__plugin_wh_wheeler_query__query_findings
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/asta.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="asta"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `chat`. Orchestration: `skill-dispatch`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
