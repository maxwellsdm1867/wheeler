# Wheeler: Architecture & Stack Plan

## Vision

A CLI-based co-scientist that wraps Claude Code with an orchestration layer, knowledge graph, and pluggable MCP servers. Think "Claude Code for Scientists" — persistent research context, interactive planning mode, writing mode, and composable execution through swappable MCP backends.

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
┌──────────────────────────────────────────────┐
│              Orchestration Layer              │
│         (Python CLI — Typer + Rich)          │
│                                              │
│  • Mode state machine (chat/plan/write/exec) │
│  • Graph context injection (pre-query)       │
│  • Plan & task DAG management                │
│  • Session history & provenance logging      │
│  • Pre/post hooks for tool enforcement       │
└──────────────────┬───────────────────────────┘
                   │
                   │ Claude Agent SDK (Python)
                   │ (runs on Max subscription)
                   │
┌──────────────────▼───────────────────────────┐
│             Claude Agent Loop                │
│      (same engine as Claude Code)            │
│                                              │
│  • LLM reasoning + tool use                  │
│  • Built-in: Bash, Read, Write, Grep, Glob   │
│  • MCP tool discovery + invocation           │
│  • Streaming responses                       │
└──────────┬───────┬──────────┬────────────────┘
           │       │          │
     ┌─────▼──┐ ┌──▼────┐ ┌──▼──────────┐
     │Knowledge│ │Code   │ │Literature   │
     │Graph   │ │Exec   │ │Search       │
     │MCP     │ │MCP(s) │ │MCP          │
     └────────┘ └───────┘ └─────────────┘

### Wheeler MCP Server (parallel access path)

Claude Code can also access Wheeler's core functionality directly via MCP,
bypassing the CLI/Agent SDK layer entirely:

```
Claude Code ──(stdio)──> wheeler-mcp ──> wheeler.graph.context
                                     ──> wheeler.validation.citations
                                     ──> wheeler.tools.graph_tools
                                     ──> wheeler.workspace
                                     ──> wheeler.graph.provenance
                                     ──> wheeler.graph.schema
```

This is a thin FastMCP wrapper (`wheeler/mcp_server.py`) over the same modules
the CLI uses. 18 tools: graph CRUD, citation validation, workspace scanning,
and provenance. Config loaded once at startup from `wheeler.yaml`. No engine/SDK
dependency — imports only data modules.
```

---

## Component 1: Claude Agent SDK (The Engine)

### What It Is

The `claude-agent-sdk` (Python) is the successor to `claude-code-sdk`. It gives you the same agent loop, tools, and context management that power Claude Code, but programmable from Python.

### Key Capabilities

- **In-process MCP servers**: Define Python functions as tools directly — no separate server process needed. Uses `create_sdk_mcp_server()` to register tools.
- **Hooks**: Python callbacks that fire at specific points in the agent loop — `PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`, `PreCompact`, etc. This is how we enforce modes.
- **Streaming**: `ClaudeSDKClient` streams messages as Claude works, enabling real-time terminal output.
- **Permission control**: `allowed_tools` restricts which tools are available per query. This is how planning mode prevents execution.
- **System prompts**: Fully customizable per-query, enabling mode-specific instructions.
- **CLAUDE.md support**: Set `setting_sources=["project"]` to load project-level context automatically.

### Installation

```bash
pip install claude-agent-sdk
# Requires Claude Code CLI installed (npm install -g @anthropic-ai/claude-code)
# Authenticates via your existing Max subscription
```

### Why This Over Raw API

- Runs on your Max subscription (confirmed: no per-token API costs — `total_cost_usd` field is informational only)
- Gets all Claude Code improvements automatically
- Built-in file ops, bash, web search — no need to reimplement
- In-process MCP servers, Python hooks, ClaudeSDKClient for full control
- Spawns Claude Code CLI as subprocess internally — same engine either way

### Example: Custom Tool + Hook

```python
from claude_agent_sdk import (
    ClaudeAgentOptions, ClaudeSDKClient, HookMatcher,
    tool, create_sdk_mcp_server
)

# Define a custom tool
@tool("query_graph", "Query the research knowledge graph", {
    "cypher": str,
    "description": str
})
async def query_graph(args):
    # Run Cypher query against Neo4j
    result = await neo4j_driver.execute(args["cypher"])
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

# Create in-process MCP server
graph_server = create_sdk_mcp_server(
    name="knowledge-graph",
    tools=[query_graph]
)

# Hook to enforce planning mode (block execution tools)
async def enforce_planning_mode(input_data, tool_use_id, context):
    if current_mode == "planning" and input_data["tool_name"] == "Bash":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "In planning mode. Switch to execute mode first."
            }
        }
    return {}

options = ClaudeAgentOptions(
    mcp_servers={"graph": graph_server},
    allowed_tools=["Bash", "Read", "Write", "mcp__graph__query_graph"],
    hooks={
        "PreToolUse": [HookMatcher(matcher="Bash", hooks=[enforce_planning_mode])]
    },
    system_prompt="You are Wheeler, a co-scientist with access to a knowledge graph..."
)
```

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

### MCP Integration Options

**Option A: Use existing `mcp-neo4j-cypher` server (fastest to start)**

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "uvx",
      "args": ["mcp-neo4j-cypher@latest"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "research-graph",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

This gives Claude tools: `read-neo4j-cypher` and `write-neo4j-cypher`, plus automatic schema discovery.

**Option B: Custom in-process MCP server via Agent SDK (more control)**

Build domain-specific tools like `add_finding`, `log_experiment`, `query_open_questions`, `link_hypothesis_to_data` that internally call Neo4j but expose a science-friendly interface to Claude. Better UX for the LLM — it doesn't need to write Cypher.

**Recommendation**: Start with Option A for the MVP (zero code needed). Migrate to Option B when you want richer, domain-specific tools.

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

## Component 5: Orchestration Layer

This is the only part you need to build from scratch. Everything else has existing tooling.

### Technology Stack

- **Typer**: CLI framework (you know Click, Typer is built on it but cleaner)
- **Rich**: Terminal formatting, progress bars, panels, markdown rendering
- **claude-agent-sdk**: The Claude Code engine
- **Pydantic**: Data models for plans, tasks, sessions

### Mode State Machine

```python
from enum import Enum

class Mode(Enum):
    CHAT = "chat"           # Query graph, discuss, no execution
    PLANNING = "planning"   # Propose/refine research plans
    WRITING = "writing"     # Draft papers, responses, documents
    EXECUTE = "execute"     # Run analyses, update graph

# Mode determines:
# 1. Which system prompt Claude gets
# 2. Which tools are allowed (via allowed_tools)
# 3. Whether graph context is auto-injected
# 4. Whether results auto-update the graph
```

### System Prompts Per Mode

```python
SYSTEM_PROMPTS = {
    Mode.CHAT: """You are Wheeler, a co-scientist with full access to the scientist's
    knowledge graph. Before answering any question, query the graph for relevant 
    context. Reference specific experiments, findings, and papers by their IDs.
    Do NOT execute any code or analyses — discuss only.""",
    
    Mode.PLANNING: """You are helping plan a research investigation. You have access
    to the knowledge graph showing all past experiments, findings, and open questions.

    Before proposing new work, query the graph for: open questions without linked
    analyses, hypotheses without supporting findings, stale findings. Propose
    investigation tasks based on what's MISSING.

    For each plan, output structured JSON with:
    - objective: string
    - tasks: [{id, description, execution_type: matlab|python|literature,
               depends_on: [task_ids], estimated_time,
               assignee: "scientist"|"wheeler"|"pair",
               cognitive_type: "math"|"conceptual"|"literature"|...}]
    - rationale: why this approach

    When decomposing work, tag each task by assignee. The scientist is strong in
    math, physics intuition, conceptual reasoning, and wants interactive coding
    where they check every step. Wheeler handles literature search, boilerplate,
    graph ops, data wrangling, and drafts. Never try to do the scientist's
    thinking — route it to them.

    Do NOT execute any code. Propose only. Wait for scientist approval.""",
    
    Mode.WRITING: """You are helping write scientific text. You have access to the
    knowledge graph for facts, findings, and citations. Always ground claims in
    specific data from the graph. Use formal scientific writing style.

    EPISTEMIC STATUS: Mark every claim as either ✅ graph-grounded (node exists
    with verified provenance) or ⚠️ interpretation (reasoning not validated by
    graph). This distinction must be visible in drafts.

    Current context: {active_plan} {relevant_findings}""",
    
    Mode.EXECUTE: """You are executing approved research tasks. For each task:
    1. Log what you're about to do
    2. Execute the analysis (MATLAB or Python)
    3. Capture all outputs, figures, and results
    4. Create Analysis node with full provenance (script_hash, language_version,
       parameters, output_hash — the post-execution hook captures these automatically)
    5. Create Finding nodes linked to the Analysis node
    6. Report results and flag anything unexpected

    Active plan: {plan}
    Current task: {task}"""
}
```

### Hook-Based Mode Enforcement

```python
async def mode_enforcement_hook(input_data, tool_use_id, context):
    tool = input_data["tool_name"]
    
    if current_mode == Mode.PLANNING:
        # Block all execution tools
        if tool in ["Bash", "mcp__matlab__runMatlabCode"]:
            return deny("Planning mode — propose tasks, don't execute.")
    
    if current_mode == Mode.CHAT:
        # Block execution, allow graph reads
        if tool in ["Bash", "Write"]:
            return deny("Chat mode — discuss only.")
    
    if current_mode == Mode.WRITING:
        # Allow graph reads and file writes, block execution
        if tool == "Bash":
            return deny("Writing mode — draft text, don't run code.")
    
    # Execute mode: allow everything
    return {}
```

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

## Implementation Roadmap

### Phase 1: MVP (Week 1-2)
**Goal: Claude Code + Knowledge Graph + Mode Switching**

1. Install Neo4j in Docker
2. Install `neo4j-agent-memory` (`pip install neo4j-agent-memory`) and extend its MemoryClient with Wheeler schema
3. Configure `mcp-neo4j-cypher` server with Claude Code
4. Design and create initial graph schema (Analysis nodes with full provenance: script_hash, language_version, parameters as JSON, output_hash)
5. Build orchestration CLI skeleton (Typer + Rich)
6. Implement mode state machine with hook-based enforcement
7. Implement graph context injection (using neo4j-agent-memory's search as foundation)
8. Write CLAUDE.md with research context + mode instructions

**Deliverable**: A CLI where you can chat with Claude about your research, and it queries/updates your knowledge graph. Planning mode prevents execution.

### Phase 2: MATLAB + Literature (Week 3-4)
**Goal: Execute real analyses and search papers**

1. Set up `matlab-mcp-tools` server
2. Verify MATLAB Engine API + UW license
3. Set up `paper-search-mcp` server
4. Implement plan creation + task DAG storage in graph
5. Implement execute mode with automatic provenance capture (post-execution hook hashes script + output, records language version + parameters, creates Analysis node with full chain)
6. Implement staleness detection (`wheeler-tools graph stale` — compares current script hashes on disk to stored `script_hash` values, flags findings with changed upstream analyses)
7. Test end-to-end: plan → approve → execute → graph update → staleness check

**Deliverable**: Plan a contrast response analysis, approve it, watch it run in MATLAB, see results logged to the graph.

### Phase 3: Writing + Polish (Week 5-6)
**Goal: Full research workflow**

1. Implement writing mode with graph-grounded context
2. Add session management (save/resume conversations)
3. Add provenance queries ("show me how we got to this finding")
4. Build custom domain-specific MCP tools (replace raw Cypher)
5. Add configuration file support (wheeler.yaml)

**Deliverable**: Complete research workflow — plan, execute, analyze, write — all tracked in the graph.

### Phase 4: Productize (Month 2-3)
**Goal: Usable by other scientists**

1. Package as pip-installable CLI
2. Write getting-started guide
3. Build MCP server template for new domains
4. Add DuckDB data layer
5. Community MCP server registry
6. "Arthur Intelligence" launch

---

## Full MCP Server Config (Target State)

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "uvx",
      "args": ["mcp-neo4j-cypher@latest"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "research-graph"
      }
    },
    "matlab": {
      "command": "matlab-mcp-server",
      "env": {
        "MATLAB_PATH": "/Applications/MATLAB_R2024a.app"
      }
    },
    "papers": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp/paper-search"]
    },
    "wheeler": {
      "type": "stdio",
      "command": "/path/to/wheeler/.venv/bin/python",
      "args": ["-m", "wheeler.mcp_server"]
    }
  }
}
```

The `wheeler` MCP server exposes 18 tools wrapping existing modules. It uses
a singleton Neo4j driver (shared with `graph/context.py`) and loads config
from `wheeler.yaml` at startup. See `wheeler/mcp_server.py` for the full
tool list.

---

## Key Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Engine | Claude Agent SDK (Python) | Runs on Max subscription, same power as Claude Code, hooks for orchestration |
| Graph DB | Neo4j Community in Docker | Official MCP server exists, Cypher is expressive, visual browser, free |
| Graph memory | neo4j-agent-memory | Entity resolution, provenance tracking, vector+graph search — extend don't rebuild |
| MATLAB | `matlab-mcp-tools` server | Cell execution, plot capture, workspace inspection |
| Literature | `paper-search-mcp` | Multi-source (PubMed, arXiv, Semantic Scholar), PDF download |
| CLI framework | Typer + Rich | Clean API, beautiful terminal output, you know Click already |
| Data models | Pydantic | Type-safe plan/task/session models |
| Config | YAML | Human-readable, easy to swap MCP servers |
| Data layer (future) | DuckDB | Zero-config, columnar, great for scientific data |

---

## What You Need to Build vs. What Already Exists

### Already Exists (just configure)
- Claude Agent SDK — `pip install claude-agent-sdk`
- Neo4j + MCP server — `docker run neo4j:community` + `uvx mcp-neo4j-cypher`
- neo4j-agent-memory — `pip install neo4j-agent-memory` (graph memory with entity resolution + provenance)
- MATLAB MCP — `matlab-mcp-tools`
- Literature search MCP — `paper-search-mcp`

### You Build (the 20% that makes it unique)
- Orchestration CLI (~500-800 lines Python)
- Mode state machine + hooks (~200 lines)
- Graph context injection logic (~200 lines)
- Plan/task DAG management (~300 lines)
- System prompts per mode (~100 lines)
- Configuration loader (~100 lines)

**Total custom code estimate: ~1,500 lines of Python**

Everything else is existing infrastructure, configured and wired together.