---
name: wh:asta
description: Route a research task to the right Asta service (Paper Finder, Semantic Scholar, Theorizer, or DataVoyager) and dispatch its act. Use for "use asta", "which asta tool", "find/look up/theorize/analyze with asta", or when unsure which Asta adapter fits.
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
---

# Asta / Service Router

Pick the right service for the user's research intent and dispatch the matching
`/wh:*` act. The available services come from the registry (a declarative
manifest), not a hardcoded table. Intent comes first: if the user gave none, ASK
them what they want BEFORE touching the graph (the graph cannot tell you what the
user wants to do). Once you have the intent, you MAY read the graph to sharpen the
request and decide which service fits. Confirm before anything paid.

## Read the registry first

The service list is data, not prose in this file. Load the AVAILABLE services
(those whose availability probe passes) from the registry:

```bash
./.venv/bin/python -c "from wheeler.config import load_config; from wheeler.integrations.registry import available_services; import json; print(json.dumps([{'id': c.id, 'name': c.name, 'act': c.act, 'kind': c.kind, 'cost': c.cost, 'when': c.when, 'description': c.description} for c in available_services(load_config())], indent=2))"
```

(If `./.venv/bin/python` is not present, use plain `python`.) The registry
returns only ENABLED services. The enabled set is the folder
`.wheeler/services/` when it exists (each `<id>.yaml` is one enabled contract,
curated via `wheeler services enable/disable`), else the bundled catalog
(every default enabled until the user starts curating). It then runs each
service's `available` probe (for example `asta auth status`) and returns only
the ones that pass, so a disabled, unauthenticated, or uninstalled service
simply will not appear. Do NOT maintain a service table in this file; trust the
registry. If the list is empty, tell the user no services are available (either
none are enabled, or asta is not authenticated: `asta auth status`) and stop.

## Routing procedure

1. Load the available services from the registry (above).
2. If `$ARGUMENTS` is non-empty, treat it as the intent and skip to step 4.
3. If `$ARGUMENTS` is empty: do NOT read the graph yet, and do NOT guess. ASK the
   user what they want to do FIRST, with AskUserQuestion: offer 2-4 concrete
   options drawn from the AVAILABLE services (for example "find papers on a
   topic", "look up a specific paper or its citations", "generate theories",
   "write a literature review"), plus the always-present "Other" for a free-text
   intent. Their answer IS the intent.
3a. Now that you have the intent, you MAY read the graph (`search_context`,
   `graph_context`) to sharpen the request and decide which service fits, for
   example to see what is already known on the topic, which papers are recorded,
   or which question this serves. This is optional: skip it for an unambiguous
   intent, use it when the request needs grounding. The chosen service's own act
   reads the graph again when it needs context, so do not over-read here.
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

## Style

- Never use em dashes. Use colons, commas, periods, parentheses.
- Be brief. The user wants to get into the right tool, not read about tools.
- Always confirm before a paid service. Never claim to have run a service that
  is unavailable or not built.
