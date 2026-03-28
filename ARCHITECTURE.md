# Wheeler: Architecture

## Three Layers

Wheeler is three things stacked:

```
+---------------------------------------------+
|  ACTS          /wh:* slash commands         |  What you DO
|                bin/wh headless runner        |
+---------------------------------------------+
|  FILE SYSTEM   .notes/*.md (prose)          |  What you KNOW
|                .plans/*.md (state)           |
|                docs/, scripts/ (artifacts)   |
+---------------------------------------------+
|  GRAPH         knowledge/*.json (index)     |  How things CONNECT
|                metadata + relationships      |
|                embeddings + file pointers     |
+---------------------------------------------+
```

**Acts** are slash commands -- the verbs. `/wh:discuss`, `/wh:plan`, `/wh:execute`, `/wh:write`, `/wh:note`. Each one gives Claude the right tools and constraints for that stage of work. YAML frontmatter restricts which tools are available per mode. The markdown body is the system prompt. No custom orchestration code -- Claude Code is the orchestrator.

**File system** is where real artifacts live. Research notes are markdown in `.notes/`. Drafts and docs live wherever the scientist puts them. Scripts live in the project. Investigation state lives in `.plans/`. These are the actual work products -- natural files you can browse, grep, git-diff, and read directly.

**Graph** is the index layer. `knowledge/*.json` files store node metadata (id, type, tier, timestamps). The graph database stores relationships (which finding came from which analysis, which paper informed which method), embeddings (for semantic search), and file pointers (path to the actual artifact). Graph nodes point to files. They don't contain prose.

The graph is a library catalog. You don't read the catalog -- you read the books. The catalog tells you which books are related.

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

For background tasks: `wh queue "task"` and `wh quick "task"` run `claude -p` (headless) with structured JSON output. No API keys -- runs on Max subscription.

---

## File System

The file system has two halves: the **scientist's workspace** (their data, code, writing) and **Wheeler-managed directories** (graph index, investigation state, notes).

### Scientist's Workspace

Wheeler doesn't own or copy files. It tracks where they are. Paths can point anywhere -- local directories, external drives, network mounts, shared NAS:

```yaml
# wheeler.yaml
paths:
  code: ["scripts/", "/shared/lab/analysis-tools/"]
  data: ["data/", "/Volumes/LabNAS/recordings/"]
  results: ["results/"]
  figures: ["figures/"]
  docs: ["docs/"]
```

`/wh:ingest` scans these paths, creates Dataset and Analysis nodes that point to the actual files. `/wh:execute` knows where to find scripts and data without the scientist spelling it out. The graph stores paths as-is and validates with hashes.

### Wheeler-Managed

```
knowledge/      # Graph index -- JSON metadata, one per node
.notes/         # Research notes -- markdown from /wh:note
.plans/         # Investigation state, plans, summaries
.logs/          # Headless task output
.wheeler/       # Internal (embeddings, etc.)
```

### Graph Metadata (`knowledge/`)

JSON files -- one per knowledge node. Structured data the graph indexes:

```json
{
  "id": "F-3a2b1c4d",
  "type": "Finding",
  "tier": "generated",
  "description": "Calcium oscillation frequency scales with cell density...",
  "confidence": 0.85,
  "created": "2026-03-26T14:30:00+00:00"
}
```

Pydantic v2 models (`wheeler/models.py`) define the schema for all 10 node types. `wh show F-3a2b` renders any node as readable markdown.

### Research Notes (`.notes/`)

Markdown files created by `/wh:note` -- the scientist's actual writing. The graph node in `knowledge/` points here via `file_path`.

```markdown
---
id: N-4e5f6a7b
title: "Temperature dependence of calcium oscillations"
created: 2026-03-26
context: "Reviewing cell_042 recordings"
---

The oscillation frequency seems to drop when we cool the bath below 30C.
Could this be a channel gating effect?
```

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
| PL | Plan | status |
| N | ResearchNote | title, content, context |
| L | Ledger | mode, pass_rate, ungrounded |

### Provenance Chain

```
Paper (reference)
  -INFORMED-> Analysis (script_hash, params)
                -USED_DATA-> Dataset (path, hash)
                -GENERATED-> Finding
                               -BASED_ON-> Paper
                               -APPEARS_IN-> Document
```

Analysis nodes store `script_hash` (SHA-256 at execution time) -- a cryptographic receipt of exactly what ran. `detect_stale` re-hashes scripts and flags mismatches.

### Context Tiers

Every node has `tier`: `reference` (established) or `generated` (new work). Papers are always reference. The `graph_context` tool separates findings by tier so Claude distinguishes what's verified from what's fresh.

### Backends

Two interchangeable backends via `GraphBackend` ABC:
- **Kuzu** -- embedded, zero-config, no Docker
- **Neo4j** -- Docker, browser UI at :7474, raw Cypher via MCP

Selected by `config.graph.backend` ("kuzu" or "neo4j"). Default is neo4j.

### Semantic Search

Optional (`pip install wheeler[search]`). fastembed + numpy, stored in `.wheeler/embeddings/`. The `search_findings` tool finds conceptually related nodes even with different wording.

---

## How the Layers Connect

### Act creates knowledge:
```
/wh:execute
  -> runs analysis script
  -> writes F-3a2b.json to knowledge/
  -> creates graph node (metadata + file pointer)
  -> links Finding -> Analysis -> Dataset in graph
  -> indexes embedding for semantic search
```

### Act reads knowledge:
```
/wh:discuss
  -> calls graph_context (graph returns titles + tiers)
  -> Claude reads knowledge/F-3a2b.json for full content
  -> OR uses show_node MCP tool
```

### Act queries connections:
```
/wh:plan
  -> calls graph_gaps (graph finds unlinked questions, unsupported hypotheses)
  -> proposes investigations based on what's MISSING
```

---

## Module Dependency Graph

### Documented Layering

```
models.py              <- zero internal deps (leaf node)
  ^
config.py              <- zero internal deps (leaf node)
  ^
knowledge/store.py     <- models only
knowledge/render.py    <- models only
  ^
graph/*                <- models + config
  ^
validation/citations   <- config + graph.schema + graph.provenance (lazy)
validation/ledger      <- config + validation.citations + tools (lazy)
  ^
tools/graph_tools/*    <- graph + knowledge (lazy imports)
  ^
mcp_server.py          <- everything
tools/cli.py           <- everything
```

### Actual Module Dependency Map

Every wheeler .py file, its layer, and its actual internal imports.
"Top-level" means the import executes at module load time.
"Lazy" means the import is inside a function and only runs when called.

```
LAYER 0 (leaf nodes -- zero internal deps):
  models.py              top-level: (none)
  config.py              top-level: (none)
  __init__.py            top-level: (none)
  depscanner.py          top-level: (none)
  log_summary.py         top-level: (none)

LAYER 1 (depends on layer 0 only):
  knowledge/store.py     top-level: models
  knowledge/render.py    top-level: models
  workspace.py           top-level: config
  scaffold.py            top-level: config
  installer.py           top-level: wheeler (version only)
                         lazy:      packaging.version (optional)

LAYER 2 (depends on layers 0-1):
  knowledge/__init__.py  top-level: knowledge.store, knowledge.render
  knowledge/migrate.py   top-level: graph.backend, models, knowledge.store
                                    ^^^ CROSS-LAYER: knowledge -> graph
  graph/backend.py       top-level: config
                         lazy:      graph.kuzu_backend, graph.neo4j_backend
  graph/driver.py        top-level: config
  graph/schema.py        top-level: config, models
  graph/context.py       top-level: config, graph.driver
  graph/provenance.py    top-level: config, graph.driver, graph.schema
  graph/trace.py         top-level: config, graph.driver, graph.schema
  graph/kuzu_backend.py  top-level: graph.backend, graph.schema
                         lazy:      graph.schema (inside _find_connected_sync)
  graph/neo4j_backend.py top-level: config, graph.backend, graph.schema
                         lazy:      graph.driver, graph.schema
  graph/__init__.py      top-level: graph.schema
  search/embeddings.py   top-level: (none internal)
  search/__init__.py     top-level: search.embeddings (try/except)
  search/backfill.py     top-level: search.embeddings
                         lazy:      knowledge.store

LAYER 3 (depends on layers 0-2):
  validation/citations.py   top-level: config, graph.schema
                            lazy:      graph.driver, graph.provenance
  validation/ledger.py      top-level: config, validation.citations
                            lazy:      tools.graph_tools (execute_tool)
  validation/__init__.py    top-level: validation.citations, validation.ledger

  tools/graph_tools/_common.py      top-level: (none internal)
  tools/graph_tools/mutations.py    top-level: graph.schema, ._common
  tools/graph_tools/queries.py      top-level: (none at load; TYPE_CHECKING: config)
                                    lazy:      knowledge.store
  tools/graph_tools/__init__.py     top-level: config, graph.schema,
                                               .mutations, .queries, ._common
                                    lazy:      graph.backend, models, knowledge.store

LAYER 4 (top -- depends on everything):
  mcp_server.py          top-level: config, graph.context, graph.schema,
                                    graph.provenance, tools.graph_tools,
                                    validation.citations, workspace
                         lazy:      search.embeddings, knowledge.store,
                                    depscanner
  tools/cli.py           top-level: config, graph.driver, graph.schema,
                                    validation.citations
                         lazy:      graph.trace, graph.provenance,
                                    installer, graph.backend,
                                    knowledge.migrate, knowledge (store/render)
  task_log.py            top-level: config, validation.citations,
                                    validation.ledger
  validate_output.py     top-level: config, validation.citations,
                                    validation.ledger
```

### ASCII Dependency Diagram

```
                      +-------------------+
                      |   mcp_server.py   |  LAYER 4: entry points
                      |   tools/cli.py    |
                      |   task_log.py     |
                      |   validate_output |
                      +---------+---------+
                                |
              +-----------------+------------------+
              |                 |                   |
   +----------v------+  +------v--------+  +-------v----------+
   | tools/           |  | validation/   |  | search/          |  LAYER 3
   |  graph_tools/    |  |  citations.py |  |  backfill.py     |
   |   __init__.py    |  |  ledger.py    |  +------------------+
   |   mutations.py   |  +---------------+
   |   queries.py     |
   +---------+--------+
             |
     +-------+---------+---------------------+
     |                  |                     |
+----v------+    +------v---------+    +------v--------+
| graph/    |    | knowledge/     |    | search/       |  LAYER 2
|  backend  |    |  store.py      |    |  embeddings   |
|  driver   |    |  render.py     |    +---------------+
|  schema   |    |  migrate.py    |
|  context  |    +----------------+
|  provnce  |
|  trace    |
|  kuzu_be  |
|  neo4j_be |
+-----------+
     |                  |
+----v------+    +------v---------+
| config.py |    | models.py      |  LAYER 0-1: foundations
+------------+   +----------------+

Standalone (no internal deps):
  depscanner.py, log_summary.py, installer.py, workspace.py, scaffold.py
```

---

## Layering Violations and Concerns

### 1. knowledge/migrate.py imports from graph layer (CROSS-LAYER)

`knowledge/migrate.py` has a top-level import of `wheeler.graph.backend.GraphBackend`. The documented architecture says knowledge/ depends only on models. However, this is architecturally justified: migration is inherently a bridge between the graph and filesystem layers. It reads from the graph backend and writes to knowledge files. This module is not part of the core knowledge store API -- it's a one-time migration utility.

**Severity**: Low. The import is appropriate for the module's purpose. Could be moved to `tools/` if strict layering is desired, but it works fine where it is.

### 2. validation/ledger.py imports from tools layer (UPWARD DEPENDENCY)

`validation/ledger.py` has a lazy import of `wheeler.tools.graph_tools.execute_tool` inside its `store_entry()` function. This is an upward dependency: validation (layer 3) reaches into tools (layer 3/4) to persist ledger entries.

**Severity**: Medium. The lazy import avoids circular dependency at load time. The coupling exists because ledger entries are stored as graph nodes via the same dual-write path as all other node types. This is intentional -- it reuses the existing add_ledger tool rather than duplicating the dual-write logic. But it creates a hidden circular dependency chain: `tools.graph_tools.__init__` imports nothing from validation, but `validation.ledger` imports from `tools.graph_tools`.

**Potential fix**: Move `store_entry` to `tools/graph_tools/` or have ledger.py write directly via the backend + knowledge store, bypassing the tool dispatch.

### 3. validation/citations.py imports graph.schema at top level

`validation/citations.py` imports `PREFIX_TO_LABEL` from `graph.schema` at the top level. This is technically correct since both are in layer 2-3, but it means loading the validation module also loads the graph schema module. The graph driver and provenance imports are properly lazy (inside `validate_citations()`).

**Severity**: Low. `graph.schema` is lightweight (no I/O at import time).

### 4. tools/cli.py imports graph.driver at top level

`tools/cli.py` does `from wheeler.graph.driver import get_sync_driver` at module load time. This triggers `import neo4j`, which means the CLI fails to load if neo4j is not installed, even for commands that don't need it (like `install`, `version`, `show`).

**Severity**: Medium. Users who only use the Kuzu backend still need `neo4j` installed to run the CLI. The neo4j package is already a core dependency in pyproject.toml, so this works in practice, but it's tighter coupling than necessary.

### 5. graph/context.py and graph/provenance.py import graph.driver at top level

Both modules do top-level `from wheeler.graph.driver import get_async_driver`, which means loading them triggers the neo4j import even if the Kuzu backend is selected. However, `graph/context.py` and `graph/provenance.py` use Neo4j directly (not the backend ABC), so they only work with Neo4j anyway.

**Severity**: Medium. These modules bypass the backend abstraction. When using Kuzu, calling `context.fetch_context()` or `provenance.detect_stale_analyses()` will fail because they use the Neo4j driver directly. The MCP server's `graph_context` and `detect_stale` tools expose these functions, so they're broken under Kuzu unless the MCP server has separate code paths.

### 6. No circular import chains at load time

Despite the lazy upward dependency in `validation/ledger.py`, there are no circular imports at module load time. All potential cycles are broken by lazy imports inside functions. The import graph is a DAG at load time.

---

## Lazy Import Strategy

Wheeler uses lazy imports (inside functions) in three situations:

1. **Breaking potential cycles**: `validation/ledger.py` imports `tools.graph_tools.execute_tool` lazily to avoid a cycle between validation and tools layers.

2. **Optional dependencies**: `graph/backend.py` lazily imports `kuzu_backend` and `neo4j_backend` so only the selected backend's dependencies need to be installed. `search/embeddings.py` lazily imports `fastembed`. `installer.py` lazily imports `packaging.version`.

3. **Deferring heavy imports**: `tools/cli.py` lazily imports `graph.trace`, `graph.provenance`, `installer`, `graph.backend`, and `knowledge` modules inside specific CLI commands so the CLI starts fast.

4. **Query enrichment**: `tools/graph_tools/queries.py` lazily imports `knowledge.store.read_node` inside each query function to enrich results with file data.

---

## Entry Points

| Entry Point | Module | Purpose |
|-------------|--------|---------|
| `wheeler-mcp` | `wheeler.mcp_server:main` | MCP server (FastMCP, stdio transport) |
| `wheeler` | `wheeler.tools.cli:app` | Typer CLI (show, graph, validate, install) |
| `wheeler-tools` | `wheeler.tools.cli:app` | Alias for CLI |
| `python -m wheeler.task_log` | `wheeler.task_log:main` | Post-hoc task log builder |
| `python -m wheeler.validate_output` | `wheeler.validate_output:main` | Post-hoc citation validator |
| `python -m wheeler.log_summary` | `wheeler.log_summary:main` | Reconvene log summarizer |

---

## External Dependencies

### Core (always required)

| Package | Import name | Used by | Purpose |
|---------|-------------|---------|---------|
| pydantic>=2.0 | `pydantic` | models.py, config.py | Schema validation, JSON serialization, discriminated unions |
| pyyaml>=6.0 | `yaml` | config.py, scaffold.py | YAML config file parsing |
| typer>=0.9 | `typer` | tools/cli.py | CLI framework |
| rich>=13.0 | `rich` | tools/cli.py | Terminal output formatting |
| neo4j>=5.0 | `neo4j` | graph/driver.py | Neo4j database driver (async + sync) |
| fastmcp>=2.0 | `fastmcp` | mcp_server.py | MCP protocol server |
| fastembed>=0.4 | `fastembed` | search/embeddings.py | Text embedding model (lazy) |
| numpy>=1.24 | `numpy` | search/embeddings.py | Vector math for embeddings |

### Optional: `[kuzu]`

| Package | Import name | Used by | Purpose |
|---------|-------------|---------|---------|
| kuzu>=0.8 | `kuzu` | graph/kuzu_backend.py | Embedded graph database |

### Optional: `[search]`

| Package | Import name | Used by | Purpose |
|---------|-------------|---------|---------|
| fastembed>=0.4 | `fastembed` | search/embeddings.py | Text embedding generation |
| numpy>=1.24 | `numpy` | search/embeddings.py | Vector storage and cosine similarity |

### Optional: `[test]`

| Package | Import name | Used by | Purpose |
|---------|-------------|---------|---------|
| pytest>=8.0 | `pytest` | tests/ | Test framework |
| pytest-asyncio>=0.23 | `pytest_asyncio` | tests/ | Async test support |
| numpy>=1.24 | `numpy` | tests/ | Test assertions for embeddings |

### Stdlib-only (no external deps)

| Module | Used by | Purpose |
|--------|---------|---------|
| `ast` | depscanner.py | Python script static analysis |
| `hashlib` | graph/provenance.py, installer.py | SHA-256 file hashing |
| `subprocess` | installer.py | pip, git operations |
| `importlib.resources` | installer.py | Package data access |
| `importlib.metadata` | __init__.py | Version detection |
| `re` | validation/citations.py, task_log.py | Citation regex |

### Unused optional dependency: `packaging`

`installer.py` lazily imports `packaging.version.Version` for version comparison, falling back to tuple comparison if unavailable. `packaging` is not declared in any dependency group in pyproject.toml. It's typically available as a transitive dependency of pip/setuptools, so this works in practice.

---

## Dependency Audit: pyproject.toml vs Actual Usage

### Core dependencies

| Declared | Actually imported | Verdict |
|----------|------------------|---------|
| typer>=0.9 | tools/cli.py (top-level) | OK |
| rich>=13.0 | tools/cli.py (top-level) | OK |
| neo4j>=5.0 | graph/driver.py (top-level) | OK |
| pyyaml>=6.0 | config.py, scaffold.py (top-level) | OK |
| pydantic>=2.0 | models.py, config.py (top-level) | OK |
| fastmcp>=2.0 | mcp_server.py (top-level) | OK |
| fastembed>=0.4 | search/embeddings.py (lazy) | CONCERN (see below) |
| numpy>=1.24 | search/embeddings.py (try/except) | CONCERN (see below) |

**fastembed and numpy as core deps**: Both `fastembed` and `numpy` are declared as core dependencies AND in the `[search]` optional group. The ARCHITECTURE.md says semantic search is optional (`pip install wheeler[search]`), but pyproject.toml installs them unconditionally. The code handles their absence gracefully (try/except ImportError), so they could be moved to `[search]` only. Currently they're in both places, which means `pip install wheeler` pulls in fastembed (which downloads a 33MB model on first use).

This appears to be an intentional decision (per commit "Make semantic search a default dependency, bump to v0.3.7"). The `[search]` extra is now redundant but kept for documentation clarity.

### Optional `[kuzu]`

| Declared | Actually imported | Verdict |
|----------|------------------|---------|
| kuzu>=0.8 | graph/kuzu_backend.py (try/except) | OK -- properly optional |

### No missing dependencies

All imported packages are covered by pyproject.toml declarations. No undeclared runtime dependencies exist.

---

## Key Files

```
wheeler/
+-- __init__.py                  # Version, logging setup
+-- models.py                    # Pydantic models, prefix mappings (source of truth)
+-- config.py                    # YAML config loader
+-- depscanner.py                # AST-based Python script dependency scanner
+-- workspace.py                 # File discovery + context formatting
+-- scaffold.py                  # Project directory detection + creation
+-- installer.py                 # Install/uninstall/update slash commands + MCP
+-- task_log.py                  # Structured task logging for headless runs
+-- log_summary.py               # Reconvene log summarizer
+-- validate_output.py           # Post-hoc citation validation for headless output
+-- knowledge/
|   +-- __init__.py              # Re-exports: write_node, read_node, render_node
|   +-- store.py                 # File I/O: read, write, list, delete (atomic)
|   +-- render.py                # Markdown rendering for wh show
|   +-- migrate.py               # Migrate existing graph nodes to files
+-- graph/
|   +-- __init__.py              # Re-exports: get_status, init_schema
|   +-- backend.py               # GraphBackend ABC + factory
|   +-- kuzu_backend.py          # Kuzu embedded backend
|   +-- neo4j_backend.py         # Neo4j backend
|   +-- driver.py                # Neo4j connection pool singleton
|   +-- schema.py                # Constraints, indexes, generate_node_id()
|   +-- context.py               # Size-limited graph context injection
|   +-- provenance.py            # File hashing, staleness detection
|   +-- trace.py                 # Provenance chain traversal
+-- search/
|   +-- __init__.py              # Conditional re-export of EmbeddingStore
|   +-- embeddings.py            # EmbeddingStore (fastembed + numpy)
|   +-- backfill.py              # Batch embedding for existing nodes
+-- validation/
|   +-- __init__.py              # Re-exports: citations + ledger
|   +-- citations.py             # Regex extraction + Cypher validation
|   +-- ledger.py                # Provenance ledger (L-prefix nodes)
+-- tools/
|   +-- __init__.py              # (empty docstring)
|   +-- cli.py                   # Typer CLI (show, migrate, graph ops)
|   +-- graph_tools/             # MCP tool handlers (mutations + queries)
|       +-- __init__.py          # Tool registry + execute_tool() dispatch
|       +-- _common.py           # _now() timestamp helper
|       +-- mutations.py         # add_*, link_nodes, set_tier
|       +-- queries.py           # query_*, graph_gaps
+-- mcp_server.py                # FastMCP server (28 tools)

.claude/commands/wh/*.md         # Slash commands (acts)
bin/wh                           # Headless task runner
wheeler.yaml                     # Project config
.mcp.json                        # MCP server definitions
```

---

## Design Principles

1. **Three layers, clear boundaries** -- acts operate, files store, graph connects
2. **Files are source of truth** -- graph is an index, not a database
3. **Everything is a reference** -- claims cite graph nodes `[F-3a2b]`
4. **Deterministic validation** -- regex + Cypher, not LLM self-judgment
5. **Structure scales with presence** -- loose when interactive, strict when independent
6. **Task routing** -- scientist thinks, Wheeler grinds, never the reverse
7. **Zero-config by default** -- Kuzu backend, no Docker required
8. **Provenance is cryptographic** -- script hashes, not self-reports
9. **No orchestration code** -- Claude Code is the orchestrator
10. **No API calls** -- runs on Max subscription, `claude -p` for headless

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Content storage | JSON files in `knowledge/` | Browsable, git-trackable, AI-readable, no query language needed |
| Graph role | Metadata + relationships only | Graphs are good at connections, bad as document stores |
| Orchestration | Claude Code slash commands | Zero Python orchestration code, YAML tool restrictions |
| Graph backend | Neo4j (default) / Kuzu (optional) | Neo4j for browser UI; Kuzu for zero-config embedded |
| Headless work | `claude -p` subprocess | No API key, Max subscription billing |
| Search | fastembed + numpy (default) | 33MB model, no PyTorch, file-based persistence |
| Models | Pydantic v2 | Schema validation, JSON serialization, discriminated unions |
| Config | YAML (`wheeler.yaml`) | Human-readable, per-project |

---

## Architectural Recommendations

### Currently Sound

- **models.py and config.py are true leaf nodes** with zero internal dependencies. This is the right foundation.
- **knowledge/store.py and knowledge/render.py** depend only on models, as documented. Clean.
- **Lazy import strategy** is consistent and well-applied. No circular imports at load time.
- **Dual-write pattern** in tools/graph_tools/__init__.py ensures graph and filesystem stay in sync.
- **Backend abstraction** (GraphBackend ABC) cleanly separates Kuzu and Neo4j implementations.

### Worth Watching

- **graph/context.py and graph/provenance.py bypass the backend ABC** and use the Neo4j driver directly. These will not work with the Kuzu backend. If Kuzu becomes the primary backend, these modules need to be rewritten to use the backend abstraction (or have Kuzu-specific implementations).
- **validation/ledger.py's upward dependency on tools** is the one true layering violation. It works via lazy import but makes the dependency graph harder to reason about.
- **fastembed/numpy as core deps** means every `pip install wheeler` pulls in the embedding model. This is intentional but worth documenting prominently for users who don't want search.
