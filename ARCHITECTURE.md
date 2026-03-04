# Wheeler: Architecture

## Vision

A co-scientist that runs natively inside Claude Code via `/wh:*` slash commands, backed by a knowledge graph, MCP servers, and a fluid workflow cycle. No custom orchestration layer — Claude Code *is* the orchestrator. Wheeler adds domain-specific modes, citation validation, provenance tracking, and structured independent work.

### The Wheeler-Bohr Dynamic

Named after John Archibald Wheeler, Bohr's thinking partner on nuclear fission. The real Bohr-Wheeler collaboration had three patterns our tool must embody:

1. **The "discharge" pattern** — Bohr came to Wheeler with half-formed ideas, not polished conclusions. Wheeler should accept messy thinking and help structure it, challenge it, shape it into something testable.

2. **Library-first** — The first thing they did was run to Princeton's library to grab Rayleigh's papers and ground their nuclear fission theory in prior work. Our knowledge graph is that library. Before reasoning, check the graph.

3. **"It from bit"** — Wheeler's later philosophy that nothing is real until you ask a question and get a definite answer. In our system: a finding doesn't exist until there's a graph node, a claim isn't grounded until the validator checks it.

The "Copenhagen Spirit" means informal debate, flat hierarchy, and the premise that arguing is productive. Wheeler should challenge assumptions, flag sparse graph areas, and ask questions rather than pad thin answers.

### Wheeler vs. Kosmos Philosophy

Kosmos (Edison Scientific, arxiv 2511.02824, $70M, 37 authors) asks "what can AI discover autonomously?" Wheeler asks "what question should we be asking?" Kosmos gives you a 30-page report and you spend hours figuring out whether to trust it. Wheeler sits with you while you think out loud, helps you sharpen the question, then you both know exactly what you're looking for and why. The thinking happens in the conversation, not in the report. This is the Bohr discharge pattern — Bohr needed to TALK through fission, not receive a report about it.

Kosmos's 57.9% accuracy on interpretation/synthesis statements (vs 85.5% on data analysis) proves the point: the machine is good at grinding through data, bad at deciding what matters. Wheeler keeps humans at the decision points and lets the machine do the grinding. This is architecturally faster AND more trustworthy — a scientist's 5-second judgment call at a fork prevents the 3-hour rabbit hole Kosmos goes down (Edison admits Kosmos "often goes down rabbit holes or chases statistically significant yet scientifically irrelevant findings" and they run it multiple times to compensate).

Kosmos VALIDATES Wheeler's core architecture (structured knowledge model, citation tracing, parallel agents, fresh context) while being philosophically opposite (autonomous vs collaborative).

### Why Wheeler (Competitive Positioning)

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
    │       ├── wheeler (FastMCP) — 18 domain tools
    │       ├── matlab (matlab-mcp-tools) — MATLAB execution
    │       └── papers (paper-search-mcp) — literature search
    │
    └── bin/wh (headless independent work)
            └── claude -p with structured logging
```

### Why Slash Commands, Not Agent SDK

The original plan called for a Python orchestration layer using `claude-agent-sdk` with
programmatic hooks for mode enforcement. In practice, Claude Code's native slash command
system does everything we need:

- **Mode enforcement**: YAML `allowed-tools` frontmatter restricts tools per command —
  `/wh:chat` can't write files, `/wh:plan` can't run code, `/wh:execute` gets everything.
- **System prompts**: The markdown body of each slash command IS the system prompt.
- **Context injection**: CLAUDE.md is loaded automatically. Graph context comes from MCP tools.
- **No custom code for orchestration**: Zero Python needed to wire modes together.

This eliminated ~1500 lines of planned orchestration code (mode state machine, hook
enforcement, system prompt injection, permission control) in favor of ~12 markdown files.

### Wheeler MCP Server

Claude Code accesses Wheeler's core functionality via MCP:

```
Claude Code ──(stdio)──> wheeler-mcp ──> wheeler.graph.context
                                     ──> wheeler.validation.citations
                                     ──> wheeler.tools.graph_tools
                                     ──> wheeler.workspace
                                     ──> wheeler.graph.provenance
                                     ──> wheeler.graph.schema
```

Thin FastMCP wrapper (`wheeler/mcp_server.py`) over the same modules the CLI uses.
18 tools: graph CRUD, citation validation, workspace scanning, and provenance.
Config loaded once at startup from `wheeler.yaml`.

### Headless / Independent Work

For background tasks (`wh queue`, `wh quick`), Wheeler uses `claude -p` (headless mode)
with structured JSON output. This runs on the Max subscription without API keys.
The `bin/wh` bash launcher handles invocation, logging, and checkpoint detection.

```bash
wh queue "task description"    # sonnet, 10 turns, logged to .logs/
wh quick "task description"    # haiku, 3 turns, fast
```

No Agent SDK dependency — just subprocess calls to the Claude CLI.

---

## Component 2: Knowledge Graph

### Recommendation: Neo4j (Community Edition) in Docker

**Foundation: `neo4j-agent-memory`** (Neo4j Labs, `pip install neo4j-agent-memory`)

Rather than writing graph memory from scratch, we extend `neo4j-agent-memory` which provides:
- Graph-native memory with provenance tracking
- Entity resolution (exact, fuzzy, and semantic matching)
- Vector + graph hybrid search
- Short-term / long-term memory layers

We extend its `MemoryClient` with Wheeler's domain schema (Findings, Analyses, Hypotheses, etc.) and citation validation. This gives us the memory infrastructure for free while we focus on the research-specific logic.

**Why Neo4j over alternatives:**

- **Official MCP server exists** (`mcp-neo4j-cypher`): Already built, maintained by Neo4j Labs. Supports schema inspection, read/write Cypher queries. Can be added to Claude Code with one config line.
- **`neo4j-agent-memory`**: Graph-native agent memory with entity resolution and provenance — our foundation layer.
- **Cypher query language**: Expressive enough for complex provenance queries ("show me all analyses that used data from experiment X and led to findings about ON-pathway nonlinearities").
- **Docker one-liner**: `docker run -p 7687:7687 -p 7474:7474 neo4j:community`
- **Browser UI**: Neo4j comes with a visual graph explorer at localhost:7474 — great for visually inspecting your research state.
- **Free**: Community Edition is fully open source (GPLv3).

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| FalkorDB | Fastest for AI/GraphRAG, low latency | Less community, newer |
| NetworkX + JSON | Zero dependencies, pure Python | In-memory only, no persistence, no query language |
| SQLite + graph schema | Simple, zero-config | Awkward graph queries, no traversal optimization |
| Memgraph | Fast, Python-friendly, C++ core | Smaller ecosystem than Neo4j |

### MCP Integration (Implemented)

Wheeler uses **both** access patterns:

1. **`mcp-neo4j-cypher`** server — raw Cypher for ad-hoc graph queries. Available as
   `mcp__neo4j__read_neo4j_cypher` and `mcp__neo4j__write_neo4j_cypher`.

2. **Wheeler MCP server** (`wheeler/mcp_server.py`) — 18 domain-specific tools like
   `add_finding`, `query_open_questions`, `link_nodes`, `validate_citations` that
   internally call Neo4j but expose a science-friendly interface. Claude doesn't
   need to write Cypher for common operations.

### Proposed Schema

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
```

**Analysis node provenance** (content-addressable, inspired by Git/W3C PROV): Analysis nodes store `script_hash` (SHA256 of file contents at execution time), `language_version` (e.g., "R2024a"), and `parameters` (JSON) alongside `script_path`. This is a cryptographic receipt — not "the scientist says they used gamma=2.2" but "the system proves exactly what ran." If the current script on disk has a different hash than what's stored, downstream findings are flagged as potentially stale. The xKG paper (arxiv 2510.17795) reinforces the principle that code should be a first-class graph citizen with executability as a quality gate, though our specific schema is our own design.

---

## Component 3: MATLAB Execution

### Existing MCP Servers

Three MATLAB MCP servers already exist on GitHub:

1. **`jigarbhoye04/MatlabMCP`** — Uses FastMCP framework, connects to shared MATLAB session via Engine API. Tools: `runMatlabCode`, `getVariable`. Async execution via `asyncio.to_thread`.

2. **`Tsuchijo/matlab-mcp`** — Creates and executes MATLAB scripts/functions. Saves scripts to disk. Requires Python 3.11 (MATLAB Engine limitation).

3. **`neuromechanist/matlab-mcp-tools`** — Most full-featured. Supports section execution (MATLAB cells via `%%`), workspace inspection, plot capture, new script creation. BSD-3-Clause license.

### Recommendation: Start with `neuromechanist/matlab-mcp-tools`

Best fit because:
- Cell-based execution (%%): matches how electrophysiology analysis scripts are typically structured
- Plot/figure capture: critical for your visual analyses
- Workspace variable inspection: lets Claude see what's loaded
- Active development, clean license

### Setup

```bash
git clone https://github.com/neuromechanist/matlab-mcp-tools
cd matlab-mcp-tools
./setup-matlab-mcp.sh
```

Config for Claude Code:
```json
{
  "mcpServers": {
    "matlab": {
      "command": "matlab-mcp-server",
      "env": {
        "MATLAB_PATH": "/Applications/MATLAB_R2024a.app"
      }
    }
  }
}
```

### MATLAB Licensing Note

- UW likely has a network license server — check with IT
- MATLAB Engine API for Python requires Python 3.10 or 3.11 (not 3.12+)
- The Engine connects to a shared MATLAB session: run `matlab.engine.shareEngine` in MATLAB first

### Swappability

The key architectural point: when you transition analyses to Python, you just swap the MCP server config. The graph, the plans, the provenance — none of it breaks. You can even run both simultaneously during the transition period.

---

## Component 4: Literature Search

### Existing MCP Servers

The MCP ecosystem has extensive coverage for academic literature:

| Server | Sources | Key Features |
|--------|---------|-------------|
| `openags/paper-search-mcp` | arXiv, PubMed, bioRxiv, medRxiv, Semantic Scholar, Google Scholar | Multi-source, PDF download, MIT license |
| `JackKuo666/semanticscholar-mcp-server` | Semantic Scholar | Paper search, author details, citation/reference graphs |
| `aeghnnsw/pubmed-mcp` | PubMed | E-utilities API, batch operations, full metadata |
| `JackKuo666/pubmed-mcp-server` | PubMed | Search, filter, retrieve, PDF download, analysis |

### Recommendation: `openags/paper-search-mcp`

Best for your use case because:
- Covers all the sources you'd need (PubMed for neuroscience, bioRxiv for preprints, Semantic Scholar for citation graphs)
- Single server, multiple sources — no need to manage 3 separate servers
- PDF download capability — can pull full texts for deeper analysis
- Simple Docker deployment: `docker run -i --rm mcp/paper-search`

### Setup

```json
{
  "mcpServers": {
    "papers": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp/paper-search"]
    }
  }
}
```

Or with Semantic Scholar API key for better rate limits:
```json
{
  "mcpServers": {
    "papers": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/paper-search-mcp", "-m", "paper_search_mcp.server"],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Component 5: Slash Command Architecture

Modes are implemented as slash commands in `.claude/commands/wh/*.md`. Each file has:
1. **YAML frontmatter** — `allowed-tools` list that restricts what Claude can use
2. **Markdown body** — system prompt defining Wheeler's behavior in that mode

### Mode Enforcement via Frontmatter

```yaml
# .claude/commands/wh/chat.md
---
name: wh:chat
allowed-tools:
  - Read
  - Glob
  - Grep
  - mcp__wheeler__query_*
  - mcp__wheeler__graph_context
  - mcp__neo4j__read_neo4j_cypher
---
```

No Python hooks needed. Claude Code's native `allowed-tools` frontmatter blocks
disallowed tools at the framework level.

### Available Slash Commands

| Command | Mode | Can do | Can't do |
|---------|------|--------|----------|
| `/wh:init` | Setup | Scaffold project, write config, seed graph | — |
| `/wh:chat` | Chat | Read files, query graph | Write, execute |
| `/wh:discuss` | Discussion | Read, query graph, structured reasoning | Write, execute |
| `/wh:plan` | Planning | Read, write plans, graph, paper search | Execute code |
| `/wh:write` | Writing | Read, write, edit, graph reads | Execute code |
| `/wh:execute` | Execute | Everything, full provenance logging | — |
| `/wh:handoff` | Transition | Propose independent tasks, write queue | — |
| `/wh:queue` | Background | Independent task protocol | Judgment calls |
| `/wh:ingest` | Bootstrap | Scan workspace, populate graph | — |
| `/wh:reconvene` | Review | Read logs, query graph, present results | — |
| `/wh:status` | Status | Query graph, read plans/logs | — |
| `/wh:pause` | State | Capture context to `.plans/CONTEXT/` | — |
| `/wh:resume` | Restore | Read context files, restore state | — |

### Bundled Commands (Installation)

Slash commands live in two places:
- `.claude/commands/wh/*.md` — active commands used by Claude Code
- `wheeler/_data/commands/*.md` — bundled copies shipped with the pip package

`wheeler install` copies from `_data/` to `~/.claude/commands/wh/`.
`wheeler install --link` creates symlinks instead (for development).
The installer (`wheeler/installer.py`) tracks file hashes in a manifest for updates.

### Workspace Context Injection

Before every query, the engine scans the project directory (`wheeler/workspace.py`) and injects a compact summary into the system prompt:

```
## Workspace: /path/to/project
Scripts (14): wheeler/ (8 files), tests/ (6 files)
Data files (2): data/ (epochs.mat, responses.csv)
Key paths: wheeler/, tests/, data/
```

This gives Wheeler awareness of what scripts and data files exist — like Claude Code knowing the codebase — without requiring the graph to be populated first. The `/wh:init` slash command walks the scientist through configuring project paths and displays the full scan results.

Configuration in `wheeler.yaml`:
```yaml
project:
  name: "retinal-circuits"
  description: "Horizontal cell feedback in primate retina"
paths:
  code: ["scripts", "~/MATLAB/shared-lib"]
  data: ["data", "/shared/ephys/2024"]
  results: ["results"]
  figures: ["figures"]
  docs: ["writing"]
workspace:
  project_dir: "."
  scan_patterns: ["*.py", "*.m", "*.mat", "*.h5", "*.hdf5", "*.csv"]
  exclude_dirs: [".venv", "__pycache__", ".git", "node_modules", ".wheeler"]
```

The `paths` section (configured by `/wh:init`) tells the workspace scanner where to look beyond the project root. Directories in `paths.code` and `paths.data` are scanned in addition to `workspace.project_dir`. This lets Wheeler discover scripts on a shared drive or data on a network mount.

### Graph Context Injection

Before every query, the orchestrator pulls relevant context:

```python
async def inject_graph_context(user_input: str) -> str:
    """Pre-query: pull relevant graph context and prepend to prompt."""
    
    # Get recent findings
    recent = await graph.query(
        "MATCH (f:Finding) RETURN f ORDER BY f.date DESC LIMIT 5"
    )
    
    # Get open questions
    questions = await graph.query(
        "MATCH (q:OpenQuestion) RETURN q ORDER BY q.priority DESC LIMIT 5"
    )
    
    # Get active plan if any
    plan = await graph.query(
        "MATCH (p:Plan {status: 'active'})-[:CONTAINS]->(t:Task) RETURN p, t"
    )
    
    context = f"""
    ## Research Context (from knowledge graph)
    
    ### Recent Findings
    {format_findings(recent)}
    
    ### Open Questions  
    {format_questions(questions)}
    
    ### Active Plan
    {format_plan(plan)}
    
    ## Scientist's Request
    {user_input}
    """
    return context
```

### Provenance Capture (Execute Mode)

When code runs through Wheeler, a post-execution hook automatically captures provenance:

```python
async def capture_analysis_provenance(script_path: str, params: dict, output_path: str):
    """Post-execution: create Analysis node with cryptographic provenance."""
    import hashlib

    script_hash = hashlib.sha256(Path(script_path).read_bytes()).hexdigest()
    output_hash = hashlib.sha256(Path(output_path).read_bytes()).hexdigest()

    # Detect language version from active MCP server
    lang_version = await detect_language_version()  # "R2024a" or "3.11"

    await graph.write("""
        CREATE (a:Analysis {
            id: $id,
            script_path: $script_path,
            script_hash: $script_hash,
            language_version: $lang_version,
            parameters: $params,
            executed_at: datetime(),
            output_path: $output_path,
            output_hash: $output_hash
        })
    """, ...)
```

**Staleness detection**: `wheeler-tools graph stale` walks all Analysis nodes, re-hashes the script at `script_path`, compares to stored `script_hash`. Mismatches flag the Analysis and all downstream Findings as STALE — the result may no longer be reproducible from the current code.

---

## Big Concepts

### Concept 6: Task Routing

Plans decompose into tasks tagged by who should do them:
- **"scientist"**: math derivations, conceptual modeling, experimental design, interpretation, interactive step-by-step coding
- **"wheeler"**: literature search, boilerplate code, graph ops, data wrangling, first-draft writing
- **"pair"**: analysis walkthroughs, debugging, writing revision

For v1 this is PLANNING MODE OUTPUT FORMAT ONLY — Wheeler generates tagged task lists, scientist decides when to act. No parallel execution yet.

Planning mode guidance: "When decomposing work, tag each task by assignee. The scientist is strong in math, physics intuition, conceptual reasoning, and wants interactive coding where they check every step. Wheeler handles literature search, boilerplate, graph ops, data wrangling, and drafts. Never try to do the scientist's thinking — route it to them."

### Concept 7: Anchor Figures

Every Dataset and Analysis node can have an `anchor_figure` — a canonical visualization the scientist recognizes at a glance. A VISUAL CHECKSUM. Programmatic validation catches file corruption; anchor figures catch semantic errors (wrong cell, wrong condition, flipped sign) that only a trained eye spots.

Behavior: display anchor figures whenever Wheeler references a Dataset or Analysis. Scientist flags "doesn't look right" = hard stop.

Anchor figure generation configured per data type in `wheeler.yaml`:
```yaml
anchor_figures:
  contrast_response: "scripts/plot_contrast_response.m"
  spike_raster: "scripts/plot_raster.m"
```

For v1: display only. v2+: auto-generation after analysis completion.

### Concept 8: Queue-Based Execution

The morning session produces a task queue. You and Wheeler talk through the problem, sharpen the question, approve tasks — then `/queue` kicks them off. Wheeler works in the background while you do other things. Decision points surface as flagged checkpoints rather than rabbit holes. You reconvene when there's something to review.

This is NOT Kosmos-style 12-hour autonomy. This is: plan together (15 min), queue approved tasks, Wheeler grinds (20 min), reconvene with results + flagged checkpoints. Human at every decision point, machine doing the grinding.

New CLI commands (Phase 2+):
- `/queue` — execute all approved tasks from current plan
- `/status` — show progress on queued tasks
- `/reconvene` — show completed results + flagged checkpoints

For v1: Task nodes get the schema fields. `/queue` is manual (you tell Wheeler to do each task). v2+: actual background execution with checkpoint surfacing.

---

## Kosmos-Inspired Improvements

### 1. Graph-Driven Task Proposal

In planning mode, Wheeler queries the graph for open questions without linked analyses, hypotheses without supporting findings, stale findings (old analysis, script hash changed), and PROPOSES investigation tasks based on what's MISSING. Kosmos's world model proposes next-cycle tasks from accumulated state — Wheeler's graph does the same but with human approval at every step.

### 2. Investigation Cycles (Human-Gated)

`/investigate` command (Phase 3). Given objective + dataset, Wheeler runs N cycles of: autonomous work (analysis + lit search + graph update) → checkpoint (surfaces results + anchor figures + flagged decisions to scientist) → scientist approves/steers → next cycle. NOT 20 autonomous cycles like Kosmos. More like 3-5 cycles with human gate at each checkpoint. This combines Kosmos's iterative depth with Wheeler's human-in-the-loop trust.

### 3. Discovery Synthesis

After a series of execute-mode analyses or an investigation run, Wheeler auto-generates a structured summary: findings discovered, how they connect to existing hypotheses, new open questions generated, graph changes made. This feeds directly into writing mode. Not a full Kosmos-style paper — a reconvene summary.

### 4. Epistemic Status Markers

In writing mode, visually distinguish validated claims (grounded in graph, provenance verified) from interpretive claims (reasoning, not graph-validated). Kosmos's data statements are 85.5% accurate but synthesis drops to 57.9% — Wheeler makes this distinction visible. Claims marked as ✅ graph-grounded or ⚠️ interpretation.

### 5. Scaling Metrics

Track findings per execute session, graph nodes per week, hypotheses validated over time. Kosmos's strongest result is linear scaling of findings with cycles. Wheeler should demonstrate similar compounding value.

---

## Component 6: Data Layer (Future)

Not needed for MVP but important for full vision.

### Recommendation: DuckDB

- Columnar, analytical queries, zero config
- Native Parquet support (great for large datasets)
- Python API is excellent
- Can query directly from file paths without import
- Free and open source

For your specific data types:
- **Spike recordings**: Store metadata in DuckDB, raw data stays as .mat or .h5 files on disk
- **Single-cell transcriptomics**: .h5ad files stay on disk, metadata in DuckDB
- **Stimulus parameters**: Directly in DuckDB tables

An MCP server wrapping DuckDB would expose tools like `query_data`, `list_datasets`, `get_dataset_info`.

---

## Implementation Status

### Done

- Neo4j schema with typed nodes and provenance constraints
- 12 slash commands covering the full workflow cycle (init, discuss, plan, execute, write, handoff, queue, reconvene, status, pause, resume, chat, ingest)
- Wheeler MCP server with 18 tools (graph CRUD, citations, workspace, provenance)
- Deterministic citation validation (regex + Cypher)
- Workspace scanner with configurable `ProjectPaths`
- Project scaffolding (`/wh:init`)
- Headless task runner (`bin/wh queue/quick`)
- Structured task logging with checkpoint detection
- Installer with manifest tracking (`wheeler install`)
- Pre-commit/pre-push hooks (API key safety, tests, mypy, ruff)
- MATLAB MCP server configured and available
- Config system with Pydantic models (`wheeler.yaml`)

### Next

- Literature search MCP integration (`paper-search-mcp`)
- DuckDB data layer for structured queries over large datasets
- Investigation cycles (`/wh:investigate`) — multi-cycle execution with human gates
- Scaling metrics — findings per session, graph growth over time
- Packaging for other scientists (getting-started guide, domain templates)

---

## MCP Server Config

The project `.mcp.json` configures all MCP servers. `/wh:init` creates this
file via `merge_mcp_config()` from `wheeler/installer.py`.

### Currently active

```json
{
  "mcpServers": {
    "neo4j": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-neo4j-cypher@latest"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "research-graph",
        "NEO4J_DATABASE": "neo4j"
      }
    },
    "wheeler": {
      "type": "stdio",
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "wheeler.mcp_server"]
    }
  }
}
```

- **neo4j** (`mcp-neo4j-cypher`): Raw Cypher read/write + schema inspection.
  Used by slash commands that need ad-hoc graph queries.
- **wheeler** (FastMCP, `wheeler/mcp_server.py`): 18 domain tools wrapping
  existing modules — graph CRUD, citation validation, workspace scanning,
  provenance. Loads config from `wheeler.yaml` at startup.

### Available (add when needed)

```json
{
  "matlab": {
    "command": "matlab-mcp-server",
    "env": { "MATLAB_PATH": "/Applications/MATLAB_R2024a.app" }
  },
  "papers": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "mcp/paper-search"]
  }
}
```

- **matlab** (`neuromechanist/matlab-mcp-tools`): MATLAB execution, plot
  capture, workspace inspection. Requires Python 3.10-3.11 for Engine API.
- **papers** (`openags/paper-search-mcp`): Literature search across PubMed,
  arXiv, bioRxiv, Semantic Scholar.

MCP servers are swappable — when transitioning analyses from MATLAB to Python,
swap the server config. The graph, plans, and provenance chains don't break.

---

## Key Design Decisions Summary

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Engine | Claude Code + slash commands | Runs on Max subscription, native mode enforcement via `allowed-tools`, zero orchestration code |
| Graph DB | Neo4j Community in Docker | Official MCP server, Cypher is expressive, visual browser at :7474, free |
| Mode enforcement | YAML frontmatter `allowed-tools` | Replaces ~1500 lines of planned Python hooks with ~12 markdown files |
| Independent work | `claude -p` via `bin/wh` | Headless mode, structured JSON output, no API key needed |
| MATLAB | `matlab-mcp-tools` server | Cell execution, plot capture, workspace inspection |
| Literature | `paper-search-mcp` | Multi-source (PubMed, arXiv, Semantic Scholar), PDF download |
| CLI | Typer + Rich | `wheeler-tools` deterministic CLI for graph ops, citations, workspace |
| Data models | Pydantic | Type-safe config, provenance, citations |
| Config | YAML (`wheeler.yaml`) | Human-readable, `ProjectPaths` for flexible project layout |
| Installation | `wheeler install` + manifest | Copies slash commands to `~/.claude/`, tracks hashes for updates |

---

## What Wheeler Built vs. What Already Existed

### Already existed (configured, not built)

- Claude Code — interactive agent with tool use, MCP support, slash commands
- Neo4j + `mcp-neo4j-cypher` — graph database with MCP server
- MATLAB MCP — `matlab-mcp-tools`
- Literature search MCP — `paper-search-mcp`

### Wheeler built (the unique parts)

- **Slash commands** (~12 markdown files) — mode-specific system prompts + tool restrictions
- **Wheeler MCP server** (`wheeler/mcp_server.py`) — 18 FastMCP tools wrapping graph, citations, workspace
- **Citation validation** (`wheeler/validation/`) — regex extraction + Cypher validation, deterministic
- **Knowledge graph schema** (`wheeler/graph/`) — typed nodes, provenance chains, staleness detection
- **Workspace scanner** (`wheeler/workspace.py`) — file discovery across configured `ProjectPaths`
- **Project scaffolding** (`wheeler/scaffold.py`) — `/wh:init` directory detection, config writing
- **Task logging** (`wheeler/task_log.py`) — structured logs for independent work, checkpoint detection
- **Config system** (`wheeler/config.py`) — Pydantic models, `ProjectPaths`, `ProjectMeta`
- **CLI tools** (`wheeler/tools/cli.py`) — deterministic graph ops, citation checks
- **Installer** (`wheeler/installer.py`) — install/update/sync slash commands with manifest tracking
- **Headless launcher** (`bin/wh`) — `claude -p` wrapper with logging and hooks