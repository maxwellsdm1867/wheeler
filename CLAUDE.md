# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this codebase is

Wheeler is a Python package that turns Claude Code into a provenance-tracked research assistant. It is not an agent framework: there is no orchestration layer. Claude Code is the orchestrator; Wheeler provides (a) MCP tools that mutate a Neo4j knowledge graph, and (b) `/wh:*` slash commands that act as mode-restricted system prompts. Everything runs locally on a Max subscription via `claude -p` subprocess. No API keys are used, ever.

Version is `0.7.0`. 1276 tests, 49 MCP tools across 5 servers.

## Commands

```bash
# Environment (Python 3.11+)
source .venv/bin/activate
pip install -e ".[test]"       # core + test deps (fastembed + numpy are in core)
pip install -e ".[search]"     # redundant with core but kept for doc clarity

# Tests
python -m pytest tests/ -q                                   # full suite, quiet
python -m pytest tests/test_merge.py -v                      # one file
python -m pytest tests/test_merge.py::TestExecuteMerge -v    # one class
python -m pytest tests/ -k "consistency"                     # by keyword
python -m pytest tests/e2e/ -v                               # e2e, needs running Neo4j

# Lint + type check (run by pre-commit hook)
.venv/bin/ruff check wheeler/
.venv/bin/mypy wheeler/ --ignore-missing-imports

# Git hooks (strongly recommended — block commits with API key leaks, broken tests, lint errors)
wh hooks install    # copies .githooks/pre-commit + pre-push into .git/hooks/
wh hooks test       # runs pre-commit checks without committing

# Headless Claude runs (for background tasks)
wh queue "prompt"   # sonnet, 10 turns, structured JSON log to .logs/
wh quick "prompt"   # haiku, 3 turns, one-shot
wh dream            # graph consolidation (promotes tiers, detects communities, flags stale)

# MCP servers (launched by Claude Code via .mcp.json — not typically invoked by hand)
python -m wheeler.mcp_server       # legacy monolith (49 tools in one process)
python -m wheeler.mcp_core         # split: health/context/search/cypher/schema (12)
python -m wheeler.mcp_query        # split: read-only query_* (10)
python -m wheeler.mcp_mutations    # split: add_*, link, unlink, delete, merge, update (14)
python -m wheeler.mcp_ops          # split: staleness, citations, consistency, ops (10)
```

The `wheeler` and `wheeler-tools` console scripts both point at the Typer CLI (`wheeler.tools.cli:app`): `wheeler show F-3a2b`, `wheeler graph status`, `wheeler validate ...`, `wheeler install`, etc.

## Architecture (what you need to hold in your head)

### The four-layer model

```
ACTS         .claude/commands/wh/*.md      slash commands = system prompts
FILE SYSTEM  .notes/, .plans/, docs/       prose artifacts live as real files
SYNTHESIS    synthesis/*.md                Obsidian-compatible, auto-generated
GRAPH        knowledge/*.json + Neo4j      metadata + relationships only
```

The graph is an **index over files**, not a document store. A node stores `id`, `type`, `tier`, `title` (~100 chars), `path`, timestamps, and filterable metadata. Full content lives in `knowledge/{id}.json`. Human-browsable rendering lives in `synthesis/{id}.md` with YAML frontmatter and Obsidian `[[backlinks]]`. When a query needs content, it reads the JSON file; when it needs connections, it queries Neo4j.

### Triple-write (load-bearing invariant)

Every mutation (`add_finding`, `link_nodes`, `set_tier`, etc.) writes **three places** through `wheeler/tools/graph_tools/__init__.py::execute_tool()`:

1. Neo4j graph node (via `GraphBackend` ABC)
2. `knowledge/{id}.json` (atomic tmp-rename)
3. `synthesis/{id}.md` (atomic tmp-rename, Obsidian-compatible)

Plus an embedding in `.wheeler/embeddings/` if search is enabled, plus a `WriteReceipt` in `.wheeler/repair_queue.jsonl` if any layer fails, plus a `trace_id` in `.wheeler/request_log.jsonl` for correlation.

**New mutation tools must route through `execute_tool()`.** Do not write directly to the backend or to files. The triple-write + receipt + trace_id + embedding wiring all lives in that dispatch path.

If layers drift (graph deleted but file survives, or vice versa), `graph_consistency_check` detects it and `repair=True` reconciles using whichever layer survived as the source of truth.

### The strict layering

```
models.py, config.py           <- zero internal deps (leaf nodes)
  |
knowledge/store.py, render.py  <- models only
  |
graph/*                        <- models + config
  |
provenance.py, merge.py,
consistency.py, contracts.py,
communities.py, write_receipt  <- config ± models ± graph (layer 2-3)
  |
tools/graph_tools/*            <- graph + knowledge (lazy imports to knowledge/)
  |
mcp_server.py,                 <- everything
mcp_core/query/mutations/ops,
tools/cli.py
```

Rules:
- **Never add imports to `models.py` or `config.py`.** They are the foundation.
- **Lazy imports in `tools/graph_tools/__init__.py` are intentional** to break cycles with `knowledge/` and `provenance`. Keep them lazy.
- **`mcp_server.py` lazily imports** `consistency`, `communities`, `contracts`, `merge`, `search.retrieval`, `depscanner` to keep server startup fast. Do not promote these to top-level.
- **`knowledge/migrate.py` is the one documented cross-layer exception**: it imports from `graph/` at top level because it bridges the two by design.
- **`validation/ledger.py` has a lazy upward import** to `tools.graph_tools.execute_tool` to persist ledger entries via the same triple-write path. This is the one real layering violation; keep it lazy.

See `ARCHITECTURE.md` for the full per-module dependency map.

### The MCP tool surface is duplicated

The same underlying implementation in `wheeler/tools/graph_tools/` is exposed through:

- `mcp_server.py` (the legacy monolith, all 49 tools in one process)
- `mcp_core.py`, `mcp_query.py`, `mcp_mutations.py`, `mcp_ops.py` (4 split servers)

All five share `mcp_shared.py` for trace ID generation, the `@_logged` decorator, config loading, and backend access. **When you add or change a tool, the authoritative implementation goes in `tools/graph_tools/`**, not in any `mcp_*.py` file. The server files are thin FastMCP wrappers that call `execute_tool()`. If a new tool needs to appear in the split-server surface, add it to both `mcp_server.py` (monolith) and the appropriate `mcp_*.py` split file.

### Provenance, stability, and staleness

Wheeler uses W3C PROV-DM relationships: `USED`, `WAS_GENERATED_BY`, `WAS_DERIVED_FROM`, `WAS_INFORMED_BY`, `WAS_ATTRIBUTED_TO`, `WAS_ASSOCIATED_WITH`, plus 8 Wheeler semantic relationships (`SUPPORTS`, `CONTRADICTS`, `CITES`, `APPEARS_IN`, `RELEVANT_TO`, `AROSE_FROM`, `DEPENDS_ON`, `CONTAINS`).

Every node carries a `stability` score (0.0–1.0) set by type and tier (Paper=0.9, primary Dataset=1.0, LLM-generated Finding=0.3, etc.). When a script's SHA-256 hash stops matching disk, `detect_and_propagate_stale()` in `provenance.py` traverses `WAS_GENERATED_BY|USED*2..N` transitively with exponential decay (default 0.8 per hop) and marks downstream nodes `stale=true`. The Cypher is entity-to-entity so `max_edges = max_hops * 2` to account for each hop crossing `WAS_GENERATED_BY` and then `USED`.

### Retrieval is multi-channel RRF

`search_findings` fuses four channels via Reciprocal Rank Fusion:

1. Semantic (fastembed cosine on BAAI/bge-small-en-v1.5, stored in `.wheeler/embeddings/`)
2. Keyword (graph substring queries over metadata)
3. Temporal (recency boost via `updated` timestamp)
4. Fulltext (Neo4j fulltext index on `_search_text`, populated via triple-write in v0.6.0)

Any channel can be unavailable (no embeddings, no fulltext index, empty graph) and the survivors still produce results. `search_context` (v0.6.0) wraps this and expands each seed via 1-hop (all rels) + 2-hop (PROV only) so callers get provenance chains alongside matches.

### Infrastructure hardening (v0.6.0)

Six patterns you may see referenced across the code:

- **Circuit breaker** (`graph/circuit_breaker.py`): 3-state breaker on Neo4j. After 3 consecutive failures it OPENs and fails fast in <1ms. After 60s it HALF_OPENs for a probe. Wraps every backend call. Never bypass.
- **Consistency checker** (`consistency.py`): detects drift between graph ↔ JSON ↔ synthesis, repairs from surviving layer.
- **Trace IDs** (`mcp_shared.py`, `request_log.py`): every MCP call gets a unique `trace_id` threaded through the log. Correlate multi-step operations by grouping on it.
- **Write receipts** (`write_receipt.py`): `WriteReceipt` tracks which layers succeeded per triple-write. Incomplete writes go to `.wheeler/repair_queue.jsonl`.
- **Change log on nodes** (`models.ChangeEntry`): `NodeBase.change_log: list[ChangeEntry]` records field-level diffs on `set_tier` and invalidation propagation. Default is empty list for backward compat.
- **Task contracts** (`contracts.py`): handoff tasks declare required output nodes, required links, citation pass rate; `validate_task_contract` checks them at reconvene.

### Acts = slash commands = system prompts

Each `.claude/commands/wh/*.md` file is a Claude Code slash command. YAML frontmatter sets `allowed-tools` (which enforces per-mode tool access); the markdown body IS the system prompt. Nothing Python reads these files at runtime. Mode enforcement (CHAT read-only, WRITE strict citations, EXECUTE full access) is entirely in the frontmatter.

`/wh:start` is a user-invoked router: it analyzes task intent and invokes the best `/wh:*` command via the Skill tool. Individual commands have narrow trigger descriptions requiring Wheeler/knowledge-graph vocabulary, so they auto-fire for unambiguous research actions but not for general coding.

The **same command files exist twice**: in `.claude/commands/wh/` (what Claude Code actually loads from this repo) and in `wheeler/_data/commands/` (what the PyPI package ships to users via `wheeler install`). **Keep these two trees in sync.** Edits to one should be mirrored to the other; tests check both paths.

## Non-obvious constraints

- **Neo4j sessions don't allow concurrent queries.** Never `asyncio.gather` inside a session; run sequentially. Backend helpers serialize inside a single session.
- **Community Edition isolation** is simulated via a `_wheeler_project` property on every node. When `config.neo4j.project_tag` is set, all `MATCH`/`CREATE` queries are namespace-scoped in Python. Enterprise/Aura users get real database isolation via the backend config.
- **`ANTHROPIC_API_KEY` is actively unset** by `bin/wh` before every headless run. The pre-commit hook greps for `ANTHROPIC_API_KEY`, `api.anthropic.com`, `import anthropic`, `from anthropic import`, `anthropic.Anthropic()`, and `sk-ant-*` patterns in staged content. Never add code that imports `anthropic`.
- **fastembed downloads a 33MB model on first use.** This happens at `EmbeddingStore.__init__`, not at package import. `pip install wheeler` does not trigger the download.
- **Graduated disclosure**: `wheeler/`, `wheeler/graph/`, `wheeler/knowledge/`, `wheeler/tools/`, and `.claude/commands/wh/` each have their own `CLAUDE.md`. Read the relevant one before editing that subtree. They are the authoritative per-directory reference.

## Style rules that apply to Wheeler-generated writing

- **Never use em dashes.** Use colons, commas, periods, or parentheses.
- **Citations are strict in write/execute modes**, flexible in chat/discuss/plan. Claims about our data cite `[F-xxxx]`, methods cite `[P-xxxx]`, interpretations are marked, speculation is free.
- **Never do the scientist's thinking.** Sharpen the question, flag sparse graph areas, ask questions rather than pad thin answers. Task routing: SCIENTIST does math/judgment, WHEELER does grinding/drafts, PAIR does walkthroughs.

## On startup

If `.plans/STATE.md` exists, read it. Call `graph_context` for recent findings before substantial work.

See `ARCHITECTURE.md` for the complete technical spec (930+ lines: module dependency map, MCP tool listing per server, PROV schema, hardening patterns, design decisions).
