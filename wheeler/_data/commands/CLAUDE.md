# wh/ -- Wheeler slash commands (acts)

Each `.md` file is a slash command invoked as `/wh:{name}`.

## Structure

```yaml
---
name: wh:discuss
description: Sharpen the question
argument-hint: "[topic]"
allowed-tools:
  - Read
  - mcp__wheeler_core__*
  - mcp__wheeler_query__*
  - mcp__wheeler_mutations__*
  - mcp__wheeler_ops__*
  - mcp__wheeler__*
---

System prompt markdown here...
```

YAML frontmatter controls tool access. The markdown body IS the system prompt.

## Commands

### Core workflow
- `discuss`: Sharpen the question through structured discussion
- `plan`: Planning mode, propose investigations
- `execute`: Execute research tasks with full provenance
- `write`: Draft scientific text with strict citation enforcement

### Knowledge management
- `add`: General-purpose ingest (text, DOI, file path, URL). Classifies and routes.
- `note`: Quick-capture research note
- `ingest`: Bootstrap graph from existing codebase (one-time)
- `compile`: Compile graph into readable synthesis documents (topic, status, evidence map)
- `dream`: Consolidate graph: promote tiers, link orphans, flag duplicates, generate synthesis indexes

### Session management
- `status`: Show investigation progress
- `ask`: Query the knowledge graph
- `chat`: Casual discussion
- `pair`: Live analysis co-work
- `init`: Initialize new project
- `resume`/`pause`: Session continuity
- `handoff`/`reconvene`/`queue`: Independent work pipeline
- `report`: Generate work log
- `close`: End-of-session provenance sweep

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
- Never use em dashes. Use colons, commas, periods, parentheses.
