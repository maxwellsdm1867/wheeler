---
name: wh:asta
description: Route a research task to the right Asta service (Paper Finder, Semantic Scholar, Theorizer, or DataVoyager) and suggest the most useful next Asta action from the graph state. Use for "use asta", "which asta tool", "find/look up/theorize/analyze with asta", or when unsure which Asta adapter fits.
argument-hint: "[describe your task, or leave blank for a graph-aware suggestion]"
allowed-tools:
  - Read
  - AskUserQuestion
  - Skill
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__graph_gaps
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_findings
---

# Asta Router

Pick the right Asta service for the user's research intent and dispatch the matching
`/wh:asta-*` act. Read the graph first, then suggest. Confirm before anything paid.

## Routing procedure

1. If `$ARGUMENTS` is non-empty, treat it as the intent and skip to step 3.
2. If `$ARGUMENTS` is empty: read the graph (`graph_context`, `graph_gaps`) and propose
   the highest-value next Asta action from the graph state (see Graph-aware suggestions),
   then confirm with the user via AskUserQuestion (offer 2-4 concrete options).
3. Match intent to a service:
   - Broad literature discovery ("find papers on X", "what is known about Y") ->
     `/wh:asta-lit` (Paper Finder). Cheap.
   - A specific paper, its citations, or snippet evidence ("look up Z", "what cites Y",
     "find the quote about X") -> `/wh:asta-scholar` (Semantic Scholar). Cheap. Citations
     build the CITES citation graph.
   - Hypothesis or theory generation ("generate theories about X", "what could explain
     Y", "form hypotheses") -> `/wh:asta-theorize` (Theorizer). EXPENSIVE (about 7 dollars,
     about 20 minutes): confirm with the user before dispatching.
   - Analyze the user's own data ("analyze this CSV", "find patterns in my .mat",
     "statistics on this dataset") -> DataVoyager. NOT YET BUILT (planned, Phase 4): say so
     plainly and do not pretend to run it. Offer Paper Finder or Semantic Scholar instead
     if literature would help.
4. Before dispatching an expensive service (Theorizer, and DataVoyager once built), confirm
   cost and time with the user. For the cheap services, dispatch directly.
5. Invoke the chosen `/wh:asta-*` act via the Skill tool, prefixed with a one-line
   explanation of the routing choice.
6. If the task is not an Asta-suited research action, say so plainly and point the user to
   `/wh:start` for general Wheeler routing.

## Graph-aware suggestions

Use the graph state to suggest the highest-value next action, not just a keyword match.
Read `graph_gaps` and `search_context`, then look for:
- An OpenQuestion with linked Papers but no Hypotheses -> suggest Theorizer.
- A Finding or Hypothesis with no supporting literature -> suggest Paper Finder or
  Semantic Scholar.
- A Paper with no CITES edges -> suggest `asta papers citations` via `/wh:asta-scholar`.
- A Dataset with an open analysis question -> suggest DataVoyager (once built).

Surface the trade-offs when you suggest:
- Paper Finder: broad semantic discovery, relevance-ranked.
- Semantic Scholar: precise lookup plus the citation graph plus snippet evidence.
- Theorizer: literature-grounded theories with supporting and contradicting evidence
  (expensive).
- DataVoyager: code-executing analysis of your own data (paid, uploads files; not yet
  built).

## Style

- Never use em dashes. Use colons, commas, periods, parentheses.
- Be brief. The user wants to get into the right tool, not read about tools.
- Always confirm before a paid service. Never claim to have run a service that is not built.
