# wh/ — Wheeler slash commands (acts)

Each `.md` file is a slash command invoked as `/wh:{name}`.

## Structure

```yaml
---
name: wh:discuss
description: Sharpen the question
argument-hint: "[topic]"
allowed-tools:
  - Read
  - mcp__wheeler__*
---

System prompt markdown here...
```

YAML frontmatter controls tool access. The markdown body IS the system prompt.

## Mode Enforcement

Tool access is the primary enforcement mechanism:
- CHAT: Read + graph reads only
- PLANNING: Read + Write + graph + paper search
- WRITING: Read + Write + Edit + graph reads (strict citations)
- PAIR: Full access, no agents
- EXECUTE: Everything (must log findings to graph with provenance)

## Conventions

- Commands read `.plans/STATE.md` on startup when relevant
- Execute mode creates findings via MCP tools, not raw Cypher
- Write mode validates citations before creating Document nodes
- All modes can call `graph_context` for research context
