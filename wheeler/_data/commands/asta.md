---
name: wh:asta
description: Route a research task to the right Asta service (Paper Finder, Semantic Scholar, Theorizer, or DataVoyager) and suggest the most useful next Asta action from the graph state. Use for "use asta", "which asta tool", "find/look up/theorize/analyze with asta", or when unsure which Asta adapter fits.
argument-hint: "[describe your task, or leave blank for a graph-aware suggestion]"
allowed-tools:
  - Read
  - AskUserQuestion
  - Skill
  - Bash(asta auth status)
  - Bash(wheeler graph status)
  - Bash(./.venv/bin/python -c *)
  - Bash(python -c *)
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__graph_gaps
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_findings
---

# Asta / Service Router

Pick the right service for the user's research intent and dispatch the matching
`/wh:*` act. The available services come from the registry (a declarative
manifest), not a hardcoded table. Read the graph first, then suggest. Confirm
before anything paid.

## Read the registry first

The service list is data, not prose in this file. Load the AVAILABLE services
(those whose availability probe passes) from the registry:

```bash
./.venv/bin/python -c "from wheeler.config import load_config; from wheeler.integrations.registry import available_services; import json; print(json.dumps([{'id': c.id, 'name': c.name, 'act': c.act, 'kind': c.kind, 'cost': c.cost, 'when': c.when, 'description': c.description} for c in available_services(load_config())], indent=2))"
```

(If `./.venv/bin/python` is not present, use plain `python`.) The registry reads
the user override at `.wheeler/services.yaml` if it exists, else the bundled
default. It runs each service's `available` probe (for example `asta auth
status`) and returns only the ones that pass, so an unauthenticated or
uninstalled service simply will not appear. Do NOT maintain a service table in
this file; trust the registry. If the list is empty, tell the user no services
are available (likely asta is not authenticated: `asta auth status`) and stop.

## Routing procedure

1. Load the available services from the registry (above).
2. If `$ARGUMENTS` is non-empty, treat it as the intent and skip to step 4.
3. If `$ARGUMENTS` is empty: read the graph (`graph_context`, `graph_gaps`) and
   propose the highest-value next action from the graph state (see Graph-aware
   suggestions), then confirm with the user via AskUserQuestion (offer 2-4
   concrete options drawn from the available services).
4. Match the intent to one of the AVAILABLE services using its `when` and
   `description` fields. Do not offer a service that is not in the list.
5. Warn on `cost`. Before dispatching any service whose `cost` is not "free" or
   "cheap" (for example Theorizer at about 7 dollars, about 20 minutes), confirm
   cost and time with the user. For free or cheap services, dispatch directly.
6. Invoke the chosen service's `act` via the Skill tool, prefixed with a
   one-line explanation of the routing choice.
7. If the intent is not served by any available service (for example
   "analyze my CSV" when DataVoyager is not built or not authenticated), say so
   plainly: name the missing capability, do not pretend to run it, and offer the
   closest available service (literature discovery often helps) or point the
   user to `/wh:start` for general Wheeler routing.

## Graph-aware suggestions

Use the graph state to suggest the highest-value next action, not just a keyword
match. Read `graph_gaps` and `search_context`, then look for these patterns and
map each to an AVAILABLE service (skip the suggestion if the matching service is
not in the registry list):

- An OpenQuestion with linked Papers but no Hypotheses -> suggest the theory
  service (Theorizer) if available. Warn on its cost.
- A Finding or Hypothesis with no supporting literature -> suggest a literature
  service (Paper Finder or Semantic Scholar) if available.
- A Paper with no CITES edges -> suggest the citation lookup (Semantic Scholar
  `papers citations`) if available.
- A Dataset with an open analysis question -> suggest a data-analysis service
  (DataVoyager) if it appears in the available list; otherwise say it is not
  available and offer literature instead.

Surface the trade-offs from each service's `description` when you suggest, and
always state the `cost` for paid services.

## Style

- Never use em dashes. Use colons, commas, periods, parentheses.
- Be brief. The user wants to get into the right tool, not read about tools.
- Always confirm before a paid service. Never claim to have run a service that
  is unavailable or not built.
