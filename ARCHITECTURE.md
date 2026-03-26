# Wheeler: Architecture

## Three Layers

Wheeler is three things stacked:

```
┌─────────────────────────────────────────────┐
│  ACTS          /wh:* slash commands         │  What you DO
│                bin/wh headless runner        │
├─────────────────────────────────────────────┤
│  FILE SYSTEM   knowledge/*.json             │  What you KNOW
│                .plans/*.md                   │
│                .logs/*.json                  │
├─────────────────────────────────────────────┤
│  GRAPH         metadata + relationships     │  How things CONNECT
│                embeddings + file pointers    │
└─────────────────────────────────────────────┘
```

**Acts** are slash commands — the verbs. `/wh:discuss`, `/wh:plan`, `/wh:execute`, `/wh:write`. Each one gives Claude the right tools and constraints for that stage of work. YAML frontmatter restricts which tools are available per mode. The markdown body is the system prompt. No custom orchestration code — Claude Code is the orchestrator.

**File system** is the source of truth for all content. Knowledge nodes live as JSON files in `knowledge/` — one file per node (`F-3a2b.json`, `H-7c1d.json`, etc.). Investigation state lives in `.plans/`. Logs live in `.logs/`. You can browse, grep, git-diff, and directly read any of it. No query language needed to access your own knowledge.

**Graph** is the index layer. It stores metadata (id, type, tier, title, timestamps), relationships (which finding came from which analysis, which paper informed which method), embeddings (for semantic search), and file pointers (path to the JSON file). The graph tells you how things connect. The files tell you what they say.

The graph is a library catalog. You don't read the catalog — you read the books. The catalog tells you which books are related.

---

## Acts (Slash Commands)

Each act is a `.md` file in `.claude/commands/wh/` with YAML frontmatter controlling tool access.

| Act | Purpose | Tool Access |
|-----|---------|-------------|
| `/wh:discuss` | Sharpen the question | Read + graph reads |
| `/wh:plan` | Structure the investigation | Read + Write + graph + paper search |
| `/wh:execute` | Run analyses, record findings | Everything |
| `/wh:write` | Draft text with citations | Read + Write + Edit + graph reads |
| `/wh:chat` | Quick discussion | Read + graph reads |
| `/wh:pair` | Live co-work | Full access, no agents |
| `/wh:handoff` | Propose independent tasks | Read + Write + graph |
| `/wh:reconvene` | Review independent results | Read + graph |
| `/wh:pause` | Capture state | Write |
| `/wh:resume` | Restore context | Read |
| `/wh:ask` | Query graph, trace provenance | Read + graph reads |
| `/wh:dream` | Graph consolidation | Graph + Write |
| `/wh:ingest` | Bootstrap from existing data | Everything |
| `/wh:init` | Set up new project | Everything |

### Why Slash Commands, Not Agent SDK

Claude Code's native slash command system does everything:
- Mode enforcement via YAML `allowed-tools`
- System prompts via markdown body
- Context injection via `graph_context` MCP tool

This replaced ~1500 lines of planned Python orchestration.

### Headless Work

For background tasks: `wh queue "task"` and `wh quick "task"` run `claude -p` (headless) with structured JSON output. No API keys — runs on Max subscription.

---

## File System

### Knowledge Files (`knowledge/`)

Every knowledge node is a JSON file. The ID prefix tells you the type:

```
knowledge/
  F-3a2b1c4d.json   # Finding
  H-7c1d2e3f.json   # Hypothesis
  Q-1b8f4a2c.json   # Open Question
  P-a4f20e91.json   # Paper
  D-9e3b4c5d.json   # Dataset
  W-5d2a1b3c.json   # Document
  A-2f4a7b8c.json   # Analysis
  PL-abcd1234.json  # Plan
  ...
```

Each file is self-contained JSON with all fields:

```json
{
  "id": "F-3a2b1c4d",
  "type": "Finding",
  "tier": "generated",
  "description": "Calcium oscillation frequency scales with cell density...",
  "confidence": 0.85,
  "created": "2026-03-26T14:30:00+00:00",
  "updated": "2026-03-26T14:30:00+00:00",
  "tags": ["calcium", "oscillations"]
}
```

Pydantic v2 models (`wheeler/models.py`) define the schema for all 11 node types. Files are written atomically (tmp + rename). `wh show F-3a2b` renders any node as readable markdown.

### Investigation Files (`.plans/`)

YAML frontmatter + markdown body. Machine-readable metadata enables fast scanning.

| File | Created by | Purpose |
|------|-----------|---------|
| `STATE.md` | `/wh:init` | Current investigation state (<100 lines) |
| `{name}-CONTEXT.md` | `/wh:discuss` | Locked decisions, scope, success criteria |
| `{name}.md` | `/wh:plan` | Task list with waves, assignees, checkpoints |
| `{name}-SUMMARY.md` | `/wh:execute` | What happened, graph nodes created |
| `{name}-VERIFICATION.md` | completion | Citation audit, criteria met/unmet |

### Logs (`.logs/`)

JSON output from headless `wh queue` / `wh quick` runs. Read by `/wh:reconvene`.

---

## Knowledge Graph

The graph stores **metadata and relationships**, not content. It is an index over the file system.

### What the Graph Stores

For each node:
- `id`, `type`, `tier`, `title` (~100 chars), `file_path`, `created`
- Filterable metadata: `confidence` (Finding), `priority` (OpenQuestion), `status` (Hypothesis), `doi` (Paper)
- Relationships to other nodes

For relationships (16 types):
```
PRODUCED, SUPPORTS, CONTRADICTS, USED_DATA, GENERATED, RAN_SCRIPT,
CITES, RELEVANT_TO, REFERENCED_IN, STUDIED_IN, CONTAINS, DEPENDS_ON,
AROSE_FROM, INFORMED, BASED_ON, APPEARS_IN
```

### What the Graph Does NOT Store

Full descriptions, statements, questions, or other prose content. That lives in the JSON files. The graph has a short `title` for context injection and display, but the file is the source of truth.

### Node Types

| Prefix | Type | Key Fields (in graph) |
|--------|------|----------------------|
| F | Finding | confidence, date |
| H | Hypothesis | status (open/supported/rejected) |
| Q | OpenQuestion | priority (1-10) |
| D | Dataset | path, data_type |
| P | Paper | doi, year (always tier=reference) |
| W | Document | status (draft/revision/final) |
| A | Analysis | script_path, script_hash, language |
| E | Experiment | date |
| PL | Plan | status |
| C | CellType | — |
| T | Task | — |

### Provenance Chain

```
Paper (reference)
  ─INFORMED─> Analysis (script_hash, params)
                ─USED_DATA─> Dataset (path, hash)
                ─GENERATED─> Finding
                               ─BASED_ON─> Paper
                               ─APPEARS_IN─> Document
```

Analysis nodes store `script_hash` (SHA-256 at execution time) — a cryptographic receipt of exactly what ran. `detect_stale` re-hashes scripts and flags mismatches.

### Context Tiers

Every node has `tier`: `reference` (established) or `generated` (new work). Papers are always reference. The `graph_context` tool separates findings by tier so Claude distinguishes what's verified from what's fresh.

### Backends

Two interchangeable backends via `GraphBackend` ABC:
- **Kuzu** (default) — embedded, zero-config, no Docker
- **Neo4j** — Docker, browser UI at :7474, raw Cypher via MCP

### Semantic Search

Optional (`pip install wheeler[search]`). fastembed + numpy, stored in `.wheeler/embeddings/`. The `search_findings` tool finds conceptually related nodes even with different wording.

---

## How the Layers Connect

### Act creates knowledge:
```
/wh:execute
  → runs analysis script
  → writes F-3a2b.json to knowledge/
  → creates graph node (metadata + file pointer)
  → links Finding → Analysis → Dataset in graph
  → indexes embedding for semantic search
```

### Act reads knowledge:
```
/wh:discuss
  → calls graph_context (graph returns titles + tiers)
  → Claude reads knowledge/F-3a2b.json for full content
  → OR uses show_node MCP tool
```

### Act queries connections:
```
/wh:plan
  → calls graph_gaps (graph finds unlinked questions, unsupported hypotheses)
  → proposes investigations based on what's MISSING
```

---

## Key Files

```
wheeler/
├── models.py                    # Pydantic models, prefix mappings (source of truth)
├── config.py                    # YAML config loader
├── knowledge/
│   ├── store.py                 # File I/O: read, write, list, delete (atomic)
│   ├── render.py                # Markdown rendering for wh show
│   └── migrate.py               # Migrate existing graph nodes to files
├── graph/
│   ├── backend.py               # GraphBackend ABC + factory
│   ├── kuzu_backend.py          # Kuzu embedded backend
│   ├── neo4j_backend.py         # Neo4j backend
│   ├── driver.py                # Neo4j connection pool singleton
│   ├── schema.py                # Constraints, indexes, generate_node_id()
│   ├── context.py               # Size-limited graph context injection
│   └── provenance.py            # File hashing, staleness detection
├── search/
│   ├── embeddings.py            # EmbeddingStore (fastembed + numpy)
│   └── backfill.py              # Batch embedding for existing nodes
├── validation/
│   └── citations.py             # Regex extraction + Cypher validation
├── tools/
│   ├── cli.py                   # Typer CLI (show, migrate, graph ops)
│   └── graph_tools/             # MCP tool handlers (mutations + queries)
├── mcp_server.py                # FastMCP server (26 tools)
└── workspace.py                 # File discovery + context formatting

.claude/commands/wh/*.md         # Slash commands (acts)
bin/wh                           # Headless task runner
wheeler.yaml                     # Project config
.mcp.json                        # MCP server definitions
```

### Module Dependencies (clean layering)

```
models.py              ← zero internal deps (leaf node)
  ↑
knowledge/store.py     ← models only
knowledge/render.py    ← models only
  ↑
graph/*                ← models + config
  ↑
tools/graph_tools/*    ← graph + knowledge (lazy imports)
mcp_server.py          ← everything
```

---

## Design Principles

1. **Three layers, clear boundaries** — acts operate, files store, graph connects
2. **Files are source of truth** — graph is an index, not a database
3. **Everything is a reference** — claims cite graph nodes `[F-3a2b]`
4. **Deterministic validation** — regex + Cypher, not LLM self-judgment
5. **Structure scales with presence** — loose when interactive, strict when independent
6. **Task routing** — scientist thinks, Wheeler grinds, never the reverse
7. **Zero-config by default** — Kuzu backend, no Docker required
8. **Provenance is cryptographic** — script hashes, not self-reports
9. **No orchestration code** — Claude Code is the orchestrator
10. **No API calls** — runs on Max subscription, `claude -p` for headless

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Content storage | JSON files in `knowledge/` | Browsable, git-trackable, AI-readable, no query language needed |
| Graph role | Metadata + relationships only | Graphs are good at connections, bad as document stores |
| Orchestration | Claude Code slash commands | Zero Python orchestration code, YAML tool restrictions |
| Graph backend | Kuzu (default) / Neo4j | Zero-config local, optional Docker for browser UI |
| Headless work | `claude -p` subprocess | No API key, Max subscription billing |
| Search | fastembed + numpy (optional) | 33MB model, no PyTorch, file-based persistence |
| Models | Pydantic v2 | Schema validation, JSON serialization, discriminated unions |
| Config | YAML (`wheeler.yaml`) | Human-readable, per-project |
