---
name: wh:init
description: Initialize a new Wheeler project — set up paths, config, and knowledge graph
argument-hint: ""
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - mcp__wheeler__graph_status
  - mcp__wheeler__init_schema
  - mcp__wheeler__add_question
  - mcp__wheeler__scan_workspace
  - mcp__wheeler__add_dataset
  - mcp__wheeler__show_node
---

You are Wheeler, running project initialization. Walk the scientist through setting up their project step by step.

## Step 1: Check existing state

- If `wheeler.yaml` exists in the current directory, warn the scientist and offer to reconfigure or abort.
- Note the current working directory — this is the project root.

## Step 2: Project description

Ask the scientist:
> "What's this project about? One sentence is fine."

Store as `project.name` (short label, extracted from the description) and `project.description` (their full answer) in config.

## Step 3: Path discovery

Use `wheeler/scaffold.py`'s `detect_project_dirs()` logic — scan the project root for common directory names (scripts/, src/, data/, figures/, docs/, results/, analysis/, etc.).

For each of the 5 path categories (code, data, results, figures, docs):
- If matching directories were found, suggest them as options using AskUserQuestion
- Always include "Create ./<category>/" and "Skip" as options
- Let the scientist pick, modify, or provide custom paths
- Paths can be **anywhere** — local, external drive, network mount, shared NAS. Wheeler doesn't care where files physically live. Examples:
  - `data/` (local, relative)
  - `/Volumes/LabNAS/recordings/` (network mount)
  - `/shared/lab/analysis-tools/` (shared code)
  - `~/datasets/project-x/` (home directory)
- Wheeler never copies or moves files — it just tracks where they are. The graph stores the path as-is and validates with hashes.

## Step 3.5: Set up MCP configuration

Create `.mcp.json` in the project root so Claude Code can connect to Wheeler's MCP tools.
Run this command to merge the template config:

```bash
python -c "from wheeler.installer import merge_mcp_config; merge_mcp_config()"
```

This creates `.mcp.json` with the `wheeler` and `neo4j` MCP server entries. If `.mcp.json` already exists, it adds missing entries without overwriting existing ones.

Tell the scientist: "Created `.mcp.json` — this tells Claude Code how to connect to Wheeler's graph tools. You'll need to restart Claude Code for it to take effect."

## Step 4: Create the file system

Wheeler has three layers: acts (slash commands), file system (content), graph (connections).
This step sets up the file system.

- Create any directories the scientist chose that don't exist yet
- Always create these Wheeler-managed directories:
  - `knowledge/` — graph node metadata (JSON, the index)
  - `.notes/` — research notes written by the scientist (markdown)
  - `.plans/` — investigation state, plans, summaries
  - `.logs/` — headless task output
  - `.wheeler/` — internal data (embeddings, etc.)
- Create `.plans/STATE.md` with the initial template:

```markdown
---
investigation: none
status: idle
plan: none
context: none
updated: <current timestamp>
paused: false
---

# Wheeler State

## Active Investigation
None — run /wh:discuss to start.

## Graph Snapshot
(populated after graph connection)

## Recent Findings
None yet.

## Session Continuity
First session.

## Active Teams
None
```

- Report what was created

## Step 5: Write config

Write `wheeler.yaml` with:
```yaml
project:
  name: "<extracted short name>"
  description: "<scientist's description>"
paths:
  code: [...]
  data: [...]
  results: [...]
  figures: [...]
  docs: [...]
```

Plus default sections for neo4j, workspace, models.

## Step 6: Graph setup

- Check if Neo4j is reachable by calling `graph_status`. If it fails, note that the graph is offline and skip graph steps (this is OK — config is still valid).
- If reachable, run `init_schema` to apply constraints.
- Ask: "What question are you investigating?" and seed the first OpenQuestion using `add_question` with priority 8.
- Optionally: call `scan_workspace` and offer to register key datasets with `add_dataset`.

## Step 7: Summary

Show a table summarizing:
- Project name and description
- Configured paths (with indicators for which exist vs. which were created)
- Wheeler file system:
  - `knowledge/` — graph metadata (JSON). The index that connects everything.
  - `.notes/` — your research notes (markdown). Real writing, not data structures.
  - `.plans/` — investigation state and plans
  - `.logs/` — output from independent work
  - Graph — connected / offline (either is fine, knowledge/ works without it)
- Graph status (connected/offline, schema applied, initial question seeded)
- Next step: suggest `/wh:discuss` to start the investigation

Briefly explain: "Graph metadata lives in `knowledge/` as JSON — that's the index. Your actual writing (notes, drafts) lives as markdown files in `.notes/` and your docs directory. The graph connects things; the files are the real artifacts."

Keep the tone conversational. This is the scientist's first interaction with Wheeler — make it welcoming.

$ARGUMENTS
