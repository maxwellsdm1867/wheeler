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
- `init`: Initialize new project (fresh or restored from a backup archive)
- `resume`/`pause`: Session continuity
- `handoff`/`reconvene`/`queue`: Independent work pipeline
- `report`: Generate work log
- `close`: End-of-session provenance sweep
- `graph-link`: Propose grouped Execution provenance for session orphans (batched approval; companion to /wh:close)
- `graph-review`: Non-destructive graph quality audit (wrong types, broken paths, duplicates, isolated subgraphs) with suggested fixes
- `backup`: Snapshot canonical state to single-file tar.gz archive
- `restore`: Verify a backup archive (currently --verify / --dry-run only)
- `start`: User-invoked router. Asks for task intent (or takes $ARGUMENTS) and invokes the best /wh:* command.

### Development
- `triage`: Triage GitHub issues against planned work
- `dev-feedback`: File Wheeler bugs/friction as structured GitHub issues

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

## Graph CRUD at the right time (every act follows this)

Every act that holds a conversation with the scientist interacts with the graph in four ways: READ, CREATE, UPDATE, and (rarely) DELETE. The act prompt must be explicit about *when* each happens. Intermediate artifacts and state changes that aren't pinned to the graph during the session evaporate when the conversation ends.

### READ — at the start, to ground the conversation

Before asking the scientist anything substantive, call `search_context` or `graph_context` with the topic in `$ARGUMENTS`. Post a one-line preamble: `Graph has [F-xxxx] "label", [H-yyyy] "label" | Gaps: ...`. This shapes every subsequent question. Re-query only when the topic pivots.

### CREATE — as artifacts emerge, or at an explicit end-of-session sweep

Conversational acts produce three classes of intermediate artifacts:
- A result the scientist endorsed (evidence-grounded) → `add_finding` (`F-xxxx`)
- A decision, methodology choice, rationale → `add_note` (`N-xxxx`)
- A sub-question, fork, "check later" → `add_question` (`Q-xxxx`, the OpenQuestion primitive)

Conservative rule: prefer `add_question` over `add_note` / `add_finding` when the scientist hasn't endorsed an answer. An open `Q-xxxx` is a "come back to this" pointer; promoting prematurely forges a record.

Wire every new node to either an active Plan via `link_nodes(new_id, PL-xxxx, "AROSE_FROM")` or to an act-specific Execution (`kind="discuss"|"pair"|"write"|...`) via `link_nodes(new_id, X-xxxx, "WAS_GENERATED_BY")`. Orphan nodes accumulate debt for `/wh:close`.

### UPDATE — when conversation changes existing graph state

These are easy to miss because the conversation moves on, but they are load-bearing:

- A new Finding bears on an existing Hypothesis → `link_nodes(F-xxxx, H-xxxx, "SUPPORTS"|"CONTRADICTS")`.
- A new Finding or Note answers an existing OpenQuestion → `update_node(Q-xxxx, status="answered")` AND `link_nodes(<answer source>, Q-xxxx, "RELEVANT_TO")`. The `Q-xxxx` will no longer surface in `query_open_questions()`, so the user stops seeing it on resume.
- A Plan's success criterion is verifiable against current graph state → `update_node(PL-xxxx, status="completed")` plus plan-file frontmatter.

Never silently rewrite a Hypothesis `statement` or a Finding `description`. UPDATE existing prose only with explicit scientist approval.

### DELETE — almost never

Wheeler does not delete by default. "Closing" a thread is a *status transition* (`Q-xxxx`: open→answered, `Plan`: in-progress→completed, `Hypothesis`: open→supported|refuted), not a hard delete. Provenance must stay reachable.

### At natural session-end points, prompt the scientist to close

Long sessions accumulate orphan nodes and unswept conversation. `/wh:close` fixes that, but users don't know to run it. Each act that has a clear "we're done" moment must suggest it inline:

> Done. When you're ready to lock this in, run `/wh:close` to sweep any remaining orphan nodes, mark answered questions, and write a session synthesis. Then `/wh:start` or `/wh:plan` for the next task.

The close prompt is appropriate after: a plan is approved (in `/wh:plan`), all tasks of a plan execute (in `/wh:execute`), a `/wh:reconvene` review wraps, a draft is registered (in `/wh:write`), a pair session wraps (in `/wh:pair`), a `/wh:chat` session created any nodes, a `/wh:discuss` round closes a CONTEXT. It is NOT appropriate inside quick-action acts (`/wh:note`, `/wh:add`, `/wh:ask`).

### Action-prompt labeling rule (titles alongside [NODE_ID])

When a command presents a graph node to the scientist for a decision (approve/edit/skip, close out, sign off, mark as), or in a status/summary/progress listing where the scientist scans many nodes at once, include a short label alongside each `[NODE_ID]`. The label is the first 80-120 chars of the node's `description`, `statement`, `question`, or `title` field, coalesced. Format: `[NODE_ID] "label"` or `[NODE_ID] label`.

This avoids forcing a separate `show_node` lookup before the scientist can decide. Bare `[NODE_ID]` remains the right style for factual claims in synthesis prose (compile, write), where the citation is a reference inside flowing text and the label would clutter the sentence. Confirm-style messages right after creation ("Added: [F-xxxx] ...", "Noted: [N-xxxx] ...") already include the title and don't need restating.
