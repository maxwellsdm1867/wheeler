# Wheeler: Architecture

## Vision

Wheeler is a research operating system that runs inside Claude Code. It gives scientists a thinking partner with a memory — a knowledge graph where every claim traces to data, every analysis has a cryptographic receipt, and every conversation builds on the last.

No custom orchestration layer. Claude Code *is* the orchestrator. Wheeler adds the research layer: `/wh:*` slash commands for domain-specific modes, MCP servers for the knowledge graph and tool execution, citation validation that's deterministic (regex + Cypher, never LLM self-judgment), and a fluid workflow cycle that's loose when the scientist is present and structured when Wheeler works independently.

### The Wheeler-Bohr Dynamic

Named after John Archibald Wheeler, Bohr's thinking partner on nuclear fission. The real Bohr-Wheeler collaboration had three patterns our tool must embody:

1. **The "discharge" pattern** — Bohr came to Wheeler with half-formed ideas, not polished conclusions. Wheeler should accept messy thinking and help structure it, challenge it, shape it into something testable.

2. **Library-first** — The first thing they did was run to Princeton's library to grab Rayleigh's papers and ground their nuclear fission theory in prior work. Our knowledge graph is that library. Before reasoning, check the graph.

3. **"It from bit"** — Wheeler's later philosophy that nothing is real until you ask a question and get a definite answer. In our system: a finding doesn't exist until there's a graph node, a claim isn't grounded until the validator checks it.

The "Copenhagen Spirit" means informal debate, flat hierarchy, and the premise that arguing is productive. Wheeler should challenge assumptions, flag sparse graph areas, and ask questions rather than pad thin answers.

### Wheeler vs. Kosmos

Kosmos (Edison Scientific, arxiv 2511.02824, $70M, 37 authors) asks "what can AI discover autonomously?" Wheeler asks "what question should we be asking?" Kosmos gives you a 30-page report and you spend hours figuring out whether to trust it. Wheeler sits with you while you think out loud, helps you sharpen the question, then you both know exactly what you're looking for and why. The thinking happens in the conversation, not in the report. This is the Bohr discharge pattern — Bohr needed to TALK through fission, not receive a report about it.

Kosmos's 57.9% accuracy on interpretation/synthesis statements (vs 85.5% on data analysis) proves the point: the machine is good at grinding through data, bad at deciding what matters. Wheeler keeps humans at the decision points and lets the machine do the grinding. This is architecturally faster AND more trustworthy — a scientist's 5-second judgment call at a fork prevents the 3-hour rabbit hole Kosmos goes down (Edison admits Kosmos "often goes down rabbit holes or chases statistically significant yet scientifically irrelevant findings" and they run it multiple times to compensate).

Kosmos VALIDATES Wheeler's core architecture (structured knowledge model, citation tracing, parallel agents, fresh context) while being philosophically opposite (autonomous vs collaborative).

### Competitive Positioning

| Tool | What it does | What it lacks |
|------|-------------|---------------|
| **Google AI Co-Scientist** | Multi-agent Gemini system, generates hypotheses from published literature | Doesn't have YOUR unpublished data, experiments, or local analyses |
| **Edison Kosmos** | $70M autonomous AI scientist, 12-hour runs, structured world model, 79.4% overall accuracy | No private data access, rabbit holes on interpretation (57.9%), post-hoc human review instead of inline validation, no task routing by cognitive type |
| **ELNs (Sapio ELaiN, etc.)** | Document what happened | Don't reason about it — no hypothesis tracking, no provenance chains |
| **Neo4j LLM Graph Builder** | Generic graph construction from text | Building blocks, not a research workflow — no modes, no citation validation |
| **Standard RAG** | Retrieves text chunks by similarity | No typed provenance chains (Finding → Analysis → Dataset → Experiment) |

Wheeler's differentiator: typed provenance from raw data to published claim, deterministic citation validation (not post-hoc human review), mode-based execution control, task routing by cognitive type (scientist vs machine), queue-based execution preserving trust, anchor figures for visual checksumming, and a personality that challenges rather than complies.

---

## Core Architecture

```
Claude Code (interactive, Max subscription)
    │
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       │
    │       ├── YAML frontmatter: allowed-tools per mode
    │       ├── Markdown body: system prompt + protocol
    │       └── Mode enforcement via tool restrictions
    │
    ├── CLAUDE.md (project context, workflow rules, personality)
    │
    ├── MCP Servers (.mcp.json)
    │       ├── neo4j (mcp-neo4j-cypher) — raw Cypher read/write
    │       ├── wheeler (FastMCP) — 23 domain tools
    │       ├── matlab (matlab-mcp-tools) — MATLAB execution
    │       └── papers (paper-search-mcp) — literature search
    │
    └── bin/wh (headless independent work)
            └── claude -p with structured logging
```

### Why Slash Commands, Not Agent SDK

The original plan called for a Python orchestration layer using `claude-agent-sdk` with programmatic hooks for mode enforcement. In practice, Claude Code's native slash command system does everything we need:

- **Mode enforcement**: YAML `allowed-tools` frontmatter restricts tools per command — `/wh:chat` can't write files, `/wh:plan` can't run code, `/wh:execute` gets everything.
- **System prompts**: The markdown body of each slash command IS the system prompt.
- **Context injection**: CLAUDE.md is loaded automatically. Graph context comes from MCP tools.
- **No custom code for orchestration**: Zero Python needed to wire modes together.

This eliminated ~1500 lines of planned orchestration code (mode state machine, hook enforcement, system prompt injection, permission control) in favor of ~12 markdown files.

### Two MCP Access Patterns

Wheeler uses both raw and domain-specific graph access:

1. **`mcp-neo4j-cypher`** — raw Cypher for ad-hoc graph queries. Available as `mcp__neo4j__read_neo4j_cypher` and `mcp__neo4j__write_neo4j_cypher`.

2. **Wheeler MCP server** (`wheeler/mcp_server.py`) — 23 domain-specific tools like `add_finding`, `add_paper`, `add_document`, `set_tier`, `query_open_questions`, `link_nodes`, `validate_citations` that internally call Neo4j but expose a science-friendly interface. Claude doesn't need to write Cypher for common operations.

### Headless / Independent Work

For background tasks (`wh queue`, `wh quick`), Wheeler uses `claude -p` (headless mode) with structured JSON output. This runs on the Max subscription without API keys. The `bin/wh` bash launcher handles invocation, logging, and checkpoint detection.

No Agent SDK dependency — just subprocess calls to the Claude CLI.

### MCP Swappability

MCP servers are swappable by design. When transitioning analyses from MATLAB to Python, swap the server config. The graph, the plans, the provenance chains — none of it breaks. You can run both simultaneously during the transition.

---

## Knowledge Graph

### Why Neo4j

- **Official MCP server** (`mcp-neo4j-cypher`): maintained by Neo4j Labs, schema inspection, read/write Cypher
- **Cypher query language**: expressive enough for provenance queries ("show me all analyses that used data from experiment X and led to findings about ON-pathway nonlinearities")
- **Browser UI**: visual graph explorer at localhost:7474 for inspecting research state
- **Docker one-liner**: `docker run -p 7687:7687 -p 7474:7474 neo4j:community`

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| FalkorDB | Fastest for AI/GraphRAG, low latency | Less community, newer |
| NetworkX + JSON | Zero dependencies, pure Python | In-memory only, no persistence, no query language |
| SQLite + graph schema | Simple, zero-config | Awkward graph queries, no traversal optimization |
| Memgraph | Fast, Python-friendly, C++ core | Smaller ecosystem than Neo4j |

### Schema

```
Node Types:
  (:Experiment {id, name, date, dataset, status, description})
  (:Finding {id, description, confidence, date})
  (:Hypothesis {id, statement, status: open|supported|rejected})
  (:OpenQuestion {id, question, priority, date_added})
  (:Paper {id, title, authors, doi, year})
  (:CellType {name, classification})
  (:Analysis {id, description, script_path, script_hash: sha256, language: matlab|python,
              language_version: "R2024a"|"3.11", parameters: json, executed_at, duration_seconds,
              output_path, output_hash: sha256,
              anchor_figure: string (path to PNG), anchor_figure_hash: sha256})
  (:Dataset {id, path, type, description, date_collected,
             anchor_figure: string (path to PNG), anchor_figure_hash: sha256})
  (:Document {id, title, path, section, status: draft|revision|final, date, updated})
  (:Plan {id, objective, status, created_date})
  (:Task {id, description, status, execution_type, depends_on,
          assignee: "scientist"|"wheeler"|"pair",
          cognitive_type: "math"|"conceptual"|"literature"|"code_interactive"|
            "code_boilerplate"|"data_wrangling"|"graph_ops"|"writing_draft"|
            "writing_revision"|"interpretation"|"experimental_design",
          execution_mode: "interactive"|"queued"|"background",
          checkpoint_reason: null|"fork_decision"|"interpretation"|"judgment"|
            "anomaly"|"anchor_review",
          queued_at, completed_at})

Relationship Types:
  (Experiment)-[:PRODUCED]->(Finding)
  (Finding)-[:SUPPORTS|CONTRADICTS]->(Hypothesis)
  (Analysis)-[:USED_DATA]->(Dataset)
  (Analysis)-[:GENERATED]->(Finding)
  (Analysis)-[:RAN_SCRIPT {path, params, output}]->(Experiment)
  (Paper)-[:CITES]->(Paper)
  (Paper)-[:RELEVANT_TO]->(Hypothesis)
  (Finding)-[:REFERENCED_IN]->(Paper)
  (CellType)-[:STUDIED_IN]->(Experiment)
  (Plan)-[:CONTAINS]->(Task)
  (Task)-[:DEPENDS_ON]->(Task)
  (OpenQuestion)-[:AROSE_FROM]->(Finding)
  (Paper)-[:INFORMED]->(Analysis)
  (Finding)-[:BASED_ON]->(Paper)
  (Finding|Paper|Analysis|Hypothesis)-[:APPEARS_IN]->(Document)
```

### Provenance Design

**Content-addressable analysis nodes** (inspired by Git/W3C PROV): Analysis nodes store `script_hash` (SHA256 of file contents at execution time), `language_version` (e.g., "R2024a"), and `parameters` (JSON) alongside `script_path`. This is a cryptographic receipt — not "the scientist says they used gamma=2.2" but "the system proves exactly what ran."

**Provenance capture** in `/wh:execute` mode: Wheeler calls MCP tools to build the chain — `hash_file` before execution, then `add_finding`/`add_dataset` for results, then `link_nodes` to connect Analysis → Dataset (USED_DATA) and Analysis → Finding (GENERATED).

**Staleness detection**: The `detect_stale` MCP tool walks all Analysis nodes, re-hashes the script at `script_path`, and compares to stored `script_hash`. Mismatches flag the Analysis and all downstream Findings as STALE — the result may no longer be reproducible from the current code.

The xKG paper (arxiv 2510.17795) reinforces the principle that code should be a first-class graph citizen with executability as a quality gate, though our specific schema is our own design.

### Graph Context Injection

Slash commands instruct Wheeler to call the `graph_context` MCP tool, which returns a size-limited summary (max 5 findings + 5 questions + 3 hypotheses, configured in `wheeler.yaml`). The implementation lives in `wheeler/graph/context.py`:

```
graph_context MCP tool
    → fetch_context(config)
        → Cypher: recent findings, open questions, active hypotheses
        → format as compact markdown (< 500 tokens)
        → return to Claude as tool result
```

No programmatic prompt injection — Claude calls the tool when the slash command tells it to, and incorporates the result into its reasoning naturally.

### Context Tiers

Every node gets a `tier` property — either `reference` (established knowledge from papers, verified data, published results) or `generated` (Wheeler's own findings, analyses, drafts). Papers are always `tier="reference"`.

`graph_context` splits findings by tier when injecting context, producing two sections:
- **Established Knowledge** — reference-tier findings (from literature, verified experiments)
- **Recent Work** — generated-tier findings (from current investigation)

The `set_tier` MCP tool allows promoting generated findings to reference (after verification) or demoting reference material.

### Full Provenance Chain

Wheeler tracks a complete chain from literature through analysis to written output:

```
Paper (reference)
  ──INFORMED──> Analysis (script_hash, params)
                  ──USED_DATA──> Dataset (path, hash)
                  ──GENERATED──> Finding (tier: generated)
                                   ──BASED_ON──> Paper
                                   ──APPEARS_IN──> Document (draft/revision/final)
```

Node types and their prefixes: Experiment (E), Finding (F), Hypothesis (H), OpenQuestion (Q), Paper (P), Analysis (A), Dataset (D), Document (W), Plan (PL), Task (T), CellType (no prefix).

### Driver Management

All Neo4j connections are centralized in `wheeler/graph/driver.py`. This replaced 5 different driver creation patterns across 7 files. The module provides:
- `get_driver()` — returns a singleton async driver with connection pooling
- `get_session()` — async context manager for database sessions
- Consistent configuration from `wheeler.yaml`

### Graph Tools Package

`wheeler/tools/graph_tools.py` was split into a package (`wheeler/tools/graph_tools/`):
- `mutations.py` — write operations (add_finding, add_paper, add_document, link_nodes, set_tier, etc.)
- `queries.py` — read operations (query_findings, query_papers, query_documents, graph_status, graph_gaps, etc.)
- `_common.py` — shared utilities
- `__init__.py` — registry dispatch (tool name → function mapping)

`generate_node_id()` is centralized in `wheeler/graph/schema.py` (was duplicated in 3 places).

### Fault Isolation

All MCP tool entry points catch exceptions and return error JSON instead of crashing:
- `execute_tool` — catches exceptions, returns `{"error": "..."}`
- `fetch_context` — returns empty string on failure
- `get_status` — returns zeroed counts on failure
- `validate_citations` — returns partial results on failure
- All former silent `except: pass` blocks now log at WARNING/ERROR level

### Logging

Stdlib logging with NullHandler library pattern. Each module creates its own named logger. Configuration:
- `configure_logging()` in `config.py`, called by MCP server at startup
- `WHEELER_LOG_LEVEL` env var (default INFO)
- Loggers in: config, driver, schema, context, provenance, graph_tools, mutations, citations

### Performance

Several hot paths were optimized:
- **`graph_status`**: 11 sequential Cypher queries consolidated into 1 UNION ALL query
- **`validate_citations`**: N x M sequential existence queries replaced with batched existence check + single provenance query per validation rule
- **`context.py` and `queries.py`**: removed `asyncio.gather` inside Neo4j sessions (was causing "read() called while another coroutine" errors — Neo4j sessions don't support concurrent queries)
- **`graph_gaps`**: fixed from buggy `asyncio.gather` to sequential queries (same Neo4j session constraint)

### E2E Testing

`tests/e2e/` contains end-to-end tests that run against a live Neo4j instance:
- `conftest.py` — test fixtures, Neo4j connection setup/teardown
- `test_workflow.py` — 18 tests covering the full provenance workflow
- `setup_sandbox.py` — populates graph with representative scientific data
- `tests/e2e/sandbox/` — gitignored workspace for sandbox data

Run with `python -m pytest tests/e2e/ -v` (requires running Neo4j).

---

## Design Concepts

### Task Routing

Every task gets tagged by who does it:

- **SCIENTIST**: math, conceptual modeling, experimental design, interpretation, judgment calls
- **WHEELER**: literature search, boilerplate code, graph ops, data wrangling, writing drafts
- **PAIR**: walkthroughs, debugging, revision, planning discussions

Wheeler never tries to do the scientist's thinking — route it to them. Planning mode generates tagged task lists; the scientist decides what to act on.

### Anchor Figures

Every Dataset and Analysis node can have an `anchor_figure` — a canonical visualization the scientist recognizes at a glance. A VISUAL CHECKSUM. Programmatic validation catches file corruption; anchor figures catch semantic errors (wrong cell, wrong condition, flipped sign) that only a trained eye spots.

Display anchor figures whenever Wheeler references a Dataset or Analysis. Scientist flags "doesn't look right" = hard stop.

### Queue-Based Execution

Plan together (15 min), queue approved tasks, Wheeler grinds (20 min), reconvene with results + flagged checkpoints. Human at every decision point, machine doing the grinding.

This is NOT Kosmos-style 12-hour autonomy. Decision points surface as flagged checkpoints rather than rabbit holes. The `/wh:handoff` → `wh queue` → `/wh:reconvene` cycle keeps the scientist in control while Wheeler does the work.

### Epistemic Status Markers

In writing mode, visually distinguish validated claims (grounded in graph, provenance verified) from interpretive claims (reasoning, not graph-validated). Claims marked as graph-grounded or interpretation. This distinction must be visible in drafts.

---

## Kosmos-Inspired Improvements

### Graph-Driven Task Proposal

In planning mode, Wheeler queries the graph for open questions without linked analyses, hypotheses without supporting findings, stale findings — and PROPOSES investigation tasks based on what's MISSING. Kosmos's world model proposes next-cycle tasks from accumulated state; Wheeler's graph does the same but with human approval at every step.

### Investigation Cycles (Human-Gated)

Given objective + dataset, Wheeler runs N cycles of: autonomous work → checkpoint → scientist approves/steers → next cycle. NOT 20 autonomous cycles like Kosmos. More like 3-5 cycles with human gate at each checkpoint. Combines Kosmos's iterative depth with Wheeler's human-in-the-loop trust.

### Discovery Synthesis

After a series of analyses, Wheeler auto-generates a structured summary: findings discovered, how they connect to existing hypotheses, new open questions generated, graph changes made. Feeds directly into writing mode via `/wh:reconvene`.

### Scaling Metrics

Track findings per execute session, graph nodes per week, hypotheses validated over time. Kosmos's strongest result is linear scaling of findings with cycles. Wheeler should demonstrate similar compounding value.

---

## Structured File Artifacts

Investigation artifacts in `.plans/` use YAML frontmatter for machine-readable metadata, enabling fast scanning by `/wh:status` and `/wh:resume` without parsing full documents.

### CONTEXT.md (`{name}-CONTEXT.md`)
Created by `/wh:discuss`. Frontmatter: `investigation`, `status` (locked), `created`. Body: research question, locked decisions, scope boundaries, success criteria.

### Plan Files (`{name}.md`)
Created by `/wh:plan`. Frontmatter: `investigation`, `status`, `created`, `updated`, `waves`, `tasks_total`, `tasks_wheeler`, `tasks_scientist`, `tasks_pair`, `graph_nodes`, `success_criteria_met`. Body: objective, tasks with wave/assignee/checkpoint metadata, success criteria.

### STATE.md
Created by `/wh:init`, updated by every workflow transition. Single file (<100 lines) read first by every command. Frontmatter: `investigation`, `status`, `plan`, `context`, `updated`, `paused`. Body: active investigation, graph snapshot, recent findings, session continuity, active teams.

### SUMMARY.md (`{name}-SUMMARY.md`)
Created by `/wh:execute` or `/wh:reconvene` after execution. Frontmatter: `investigation`, `plan`, `created`, `tasks_completed`, `tasks_skipped`, `checkpoints_hit`. Body: tasks completed with [NODE_ID] citations, graph nodes created, deviations, checkpoints, success criteria status, next steps.

### VERIFICATION.md (`{name}-VERIFICATION.md`)
Created when investigation completes. Frontmatter: `investigation`, `plan`, `created`, `criteria_met`, `criteria_partial`, `criteria_unmet`, `verdict`. Body: success criteria verification with evidence, citation audit via `validate_citations`, open questions, gaps, recommended next investigations.

### Design Principles
- **Don't duplicate the graph.** Files reference graph nodes via [NODE_ID], never copy graph data.
- **Frontmatter enables scanning.** Machine-readable metadata in first ~20 lines.
- **STATE.md < 100 lines.** Digest, not archive. Only tracks the current investigation.
- **Everything is a reference.** New files use [NODE_ID] citations for factual claims.

---

## Future: Data Layer (DuckDB)

Not needed yet but important for the full vision. DuckDB for structured queries over large datasets:

- Columnar, analytical queries, zero config
- Native Parquet support
- Can query directly from file paths without import
- **Spike recordings**: metadata in DuckDB, raw data stays as .mat/.h5
- **Single-cell transcriptomics**: .h5ad on disk, metadata in DuckDB
- **Stimulus parameters**: directly in DuckDB tables

An MCP server wrapping DuckDB would expose tools like `query_data`, `list_datasets`, `get_dataset_info`.

---

## Key Design Decisions

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Engine | Claude Code + slash commands | Runs on Max subscription, native mode enforcement via `allowed-tools`, zero orchestration code |
| Graph DB | Neo4j Community in Docker | Official MCP server, Cypher is expressive, visual browser at :7474, free |
| Mode enforcement | YAML frontmatter `allowed-tools` | Replaces ~1500 lines of planned Python hooks with ~12 markdown files |
| Independent work | `claude -p` via `bin/wh` | Headless mode, structured JSON output, no API key needed |
| MATLAB | `matlab-mcp-tools` server | Cell execution, plot capture, workspace inspection; swappable when migrating to Python |
| Literature | `paper-search-mcp` | Multi-source (PubMed, arXiv, Semantic Scholar), PDF download |
| CLI | Typer + Rich | `wheeler-tools` deterministic CLI for graph ops, citations, workspace |
| Data models | Pydantic | Type-safe config, provenance, citations |
| Config | YAML (`wheeler.yaml`) | Human-readable, `ProjectPaths` for flexible project layout |
| Installation | `wheeler install` + manifest | Copies slash commands to `~/.claude/`, tracks hashes for updates |
| Driver mgmt | Centralized `driver.py` | Single connection pool, consistent config, was 5 patterns across 7 files |
| Logging | stdlib + NullHandler | Library pattern, `WHEELER_LOG_LEVEL` env var, no third-party deps |
| Context tiers | `reference` vs `generated` | Separates established knowledge from investigation output in graph context |
| Data layer (future) | DuckDB | Zero-config, columnar, great for scientific data |
