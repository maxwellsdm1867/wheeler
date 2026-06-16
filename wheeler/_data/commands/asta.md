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
---

# Asta / Service Router

Pick the right service for the user's research intent and dispatch the matching
`/wh:*` act. The available services come from the registry (a declarative
manifest), not a hardcoded table. If the user gave no intent, ASK them what they
want first: do not read the graph (it cannot tell you what the user wants to do).
Confirm before anything paid.

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
3. If `$ARGUMENTS` is empty: do NOT read the graph, and do NOT guess. ASK the user
   what they want to do FIRST, with AskUserQuestion: offer 2-4 concrete options
   drawn from the AVAILABLE services (for example "find papers on a topic",
   "look up a specific paper or its citations", "generate theories", "write a
   literature review"), plus the always-present "Other" for a free-text intent.
   Their answer IS the intent. The graph cannot tell you what the user wants, so
   asking it first is wasted work: the chosen service's own act reads the graph
   when it actually needs context.
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
