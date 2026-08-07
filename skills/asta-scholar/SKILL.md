---
name: asta-scholar
description: "Use when the user wants to query Semantic Scholar via Asta (paper lookup, search, citations, snippet search, or an author's papers) and ingest the results into the Wheeler knowledge graph"
argument-hint: "[query, paper id, or DOI]"
allowed-tools:
  - Read
  - Bash(asta papers:*)
  - Bash(wheeler integrate:*)
  - mcp__wheeler_core__search_context
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__search_context
  - mcp__plugin_wh_wheeler_query__query_papers
  - mcp__plugin_wh_wheeler_query__query_open_questions
  - mcp__plugin_wh_wheeler_query__query_findings
  - mcp__plugin_wh_wheeler_mutations__link_nodes
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/asta-scholar.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="asta-scholar"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `write`. Orchestration: `none`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
