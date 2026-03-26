<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">A thinking partner for scientists. Built on Claude Code.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/v0.2.0-blue" alt="v0.2.0">
  <img src="https://img.shields.io/badge/status-beta-yellow" alt="Status: Beta">
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-native-orange" alt="Claude Code Native"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey" alt="macOS | Linux">
  <img src="https://img.shields.io/badge/local%20only-no%20data%20leaves%20your%20machine-brightgreen" alt="Local Only">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome">
</p>

Wheeler is two things:

**A workflow framework** — slash commands that guide you through the scientific process. Discuss the question, plan the investigation, execute analyses, write up results. Each mode gives Claude the right tools and constraints for that stage of work. Hand off grinding tasks to run independently while you do something else. Come back and reconvene.

**A memory and context system** — a knowledge graph that ties the workflow together. Findings trace back to analyses, analyses carry script hashes, papers link to the methods they informed, documents record what they cited. Every session builds on the last because the graph remembers what you found, what you asked, and what's still open.

The workflow is the skeleton. The graph is the connective tissue.

> Named after John Archibald Wheeler — Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

Runs 100% locally on your machine. No API keys, no cloud services. Your data never leaves your machine. Zero-config graph backend (Kuzu) -- no Docker required. Powered by Claude Max subscription.

---

## The Workflow

Wheeler gives you a fluid cycle — not a rigid pipeline. You can enter at any point, skip stages, or repeat them.

```text
 ┌─────────────────────────────────────────────────────┐
 │  TOGETHER          you + wheeler, thinking out loud  │
 │  discuss  plan  chat  pair  write  ask               │
 └────────────────────────┬────────────────────────────┘
                          │ remaining work is grinding
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  HANDOFF            propose independent tasks        │
 │  handoff            you approve, modify, or keep     │
 │                     talking                          │
 └────────────────────────┬────────────────────────────┘
                          │
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  INDEPENDENT        wheeler works alone              │
 │  wh queue "..."     logged, stops at decision points │
 └────────────────────────┬────────────────────────────┘
                          │
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  RECONVENE          results + flags + surprises      │
 │  reconvene          back to TOGETHER                 │
 └─────────────────────────────────────────────────────┘
```

Each stage has its own slash command with specific tools and constraints:

| Command | Stage | What it does | Tools |
|---------|-------|-------------|-------|
| `/wh:discuss` | Sharpen | Refine the research question through structured dialogue | Read, write, graph, search |
| `/wh:plan` | Design | Structure tasks with waves, assignees, checkpoints | Read, write, graph |
| `/wh:execute` | Run | Execute analyses, log findings to graph with provenance | Everything |
| `/wh:write` | Draft | Write text with strict citation enforcement | Read, write, graph, validation |
| `/wh:pair` | Co-work | Live analysis — scientist drives, Wheeler assists | Full access + MATLAB |
| `/wh:chat` | Think | Quick discussion, no execution | Read, graph queries |
| `/wh:ask` | Query | Look up graph nodes, trace provenance chains | Read, graph queries |
| `/wh:handoff` | Delegate | Propose tasks for independent background execution | Graph, agents, tasks |
| `/wh:reconvene` | Review | Synthesize results from independent work | Read, graph, tasks |
| `/wh:ingest` | Bootstrap | Populate graph from existing code, data, papers | Read, write, graph, search |
| `/wh:dream` | Consolidate | Promote tiers, link orphans, flag duplicates | Graph reads/writes |
| `/wh:pause` | Save | Capture investigation state for later | Read, write, graph |
| `/wh:resume` | Restore | Pick up where you left off | Read, graph, tasks |
| `/wh:status` | Check | Show progress, suggest next action | Read, graph |

**Wheeler never does your thinking.** Every task gets tagged — SCIENTIST (judgment calls), WHEELER (grinding), or PAIR (collaborative). Decision points are flagged as checkpoints, not guessed at.

## The Memory

The knowledge graph is what makes the workflow cohere. Without it, every session starts cold. With it, Wheeler knows what you've found, what methods you used, what questions are open, and what's been written up.

```text
## Research Context (from knowledge graph)

### Established Knowledge (reference)
- [F-3a2b] Parasol ON Rin = 142 +/- 23 MOhm (confidence: 0.92)
- [P-9e0f] Gerstner 1995 — Spike Response Model framework

### Recent Work (generated)
- [F-a1b2] Cross-prediction VP loss at q=200Hz: parasol 0.15, midget 0.22
- [H-c3d4] Parasol and midget may share spike generation (status: open)

### Open Questions
- [Q-e5f6] Is the VP difference biologically meaningful? (priority: 9)
```

Different workflow stages pull different context from the graph:

| Stage | What it needs from the graph |
|-------|----------------------------|
| **Discuss** | Existing findings and gaps — what do we already know? |
| **Plan** | Open questions, gap analysis — what should we investigate next? |
| **Execute** | Dataset locations, analysis provenance — what data to use, what scripts to run |
| **Write** | Findings with citations, paper references — what to cite, what to mark as interpretation |
| **Reconvene** | New findings from independent work — what did Wheeler produce while you were away? |
| **Dream** | Tier distribution, orphaned nodes, stale analyses — what needs cleanup? |

### Tiers

Every node is tagged `reference` (established) or `generated` (new work). Papers are always reference. Findings start as generated and get promoted after verification. This lets the workflow distinguish between what you're building on vs what you just produced.

### Provenance

Every link is tracked. Findings trace back to analyses, analyses carry script hashes, datasets have file paths. If a script changes after an analysis ran, the finding is flagged as STALE. You can trace any claim back to raw data:

```text
Paper ──INFORMED──> Analysis ──USED_DATA──> Dataset
                      └──GENERATED──> Finding ──APPEARS_IN──> Document
```

### Citations

Different claims need different treatment:

| Claim type | Citation? |
|-----------|----------|
| Fact about your data | Yes — cite the graph node `[F-3a2b]` |
| Interpretation | No node yet — marked as interpretation |
| Method from a paper | Cite the Paper node `[P-xxxx]` |
| Speculation | No — this is thinking out loud |
| Textbook knowledge | No — doesn't need a graph node |

In write mode, research claims are validated deterministically (regex + Cypher, not LLM self-judgment). In chat/discuss mode, citation is encouraged but not enforced.

---

## Setup

**Prerequisites:** Python 3.11+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Max subscription)

Everything runs locally. No cloud accounts, no API keys, no data leaves your machine.

```bash
git clone https://github.com/maxwellsdm1867/wheeler.git
cd wheeler
bash bin/setup.sh
```

Or manually:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
wheeler-tools graph init
```

**Graph backend** — Wheeler supports two backends, configured in `wheeler.yaml`:

| Backend | Setup | Best for |
|---------|-------|----------|
| **Kuzu** (recommended) | Zero-config. ~4MB pip package, data in `.kuzu/` | Solo research, laptops, getting started |
| **Neo4j** | `docker compose up -d` | Multi-user, existing Neo4j workflows |

Set `graph.backend: kuzu` or `graph.backend: neo4j` in `wheeler.yaml`. Kuzu needs no Docker, no server, no configuration.

**Semantic search** (optional):

```bash
pip install -e ".[search]"             # adds fastembed (~33MB model, local-only)
```

Enables `search_findings` and `index_node` MCP tools for meaning-based search across the graph. Configure via `search.enabled`, `search.store_path`, and `search.model` in `wheeler.yaml`. Embeddings persist to `.wheeler/embeddings/`.

After setup, restart Claude Code and verify MCP servers with `/mcp`.

## Getting Started

```bash
cd ~/my-project && claude    # open Claude Code in your project
/wh:init                     # set up paths, config, knowledge graph
/wh:discuss                  # sharpen the question
/wh:plan                     # structure the investigation
```

For headless/independent work:

```bash
wh queue "search for papers on SRM models"   # sonnet, 10 turns, logged
wh quick "check graph status"                 # haiku, 3 turns, fast
wh dream                                      # graph consolidation
wh status                                     # quick status check
```

## Architecture

```text
Claude Code (interactive)
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       ├── YAML frontmatter: tool restrictions per mode
    │       └── System prompt: workflow protocol
    │
    ├── MCP Servers
    │       ├── wheeler (25 tools) — graph CRUD, context, citations, search, provenance
    │       ├── neo4j — raw Cypher for ad-hoc queries
    │       ├── matlab — MATLAB execution (optional)
    │       └── papers — literature search (optional)
    │
bin/wh (headless)
    └── claude -p with structured logging → .logs/*.json
```

| When you're here | When you're away |
| ---------------- | ---------------- |
| Loose, creative, freeform | Structured, validated, logged |
| Graph optional | Graph mandatory |
| You are quality control | System is quality control |

See [ARCHITECTURE.md](ARCHITECTURE.md) for full technical details.

## Code Structure

```text
wheeler/
├── config.py                # Pydantic models, YAML loader, logging config
├── mcp_server.py            # FastMCP — 25 tools exposed to Claude Code
├── graph/
│   ├── backend.py           # GraphBackend ABC + get_backend() factory
│   ├── driver.py            # Neo4j driver (legacy, used by neo4j backend)
│   ├── schema.py            # Node types, relationships, constraints
│   ├── context.py           # Tier-separated context injection
│   ├── provenance.py        # Script hashing, staleness detection
│   └── trace.py             # Provenance chain traversal
├── search/
│   ├── embeddings.py        # EmbeddingStore — fastembed + persistence
│   └── ...                  # Semantic search over graph nodes
├── tools/
│   ├── graph_tools/         # Mutations + queries + registry dispatch
│   └── cli.py               # CLI (Typer + Rich)
├── validation/
│   ├── citations.py         # Regex extraction + batched Cypher validation
│   └── ledger.py            # Provenance audit trail
├── workspace.py             # Project file scanner
├── scaffold.py              # Project initialization
├── task_log.py              # Headless task logging
└── installer.py             # Package install/update

.claude/commands/wh/          # 16 slash commands
bin/wh                        # Headless launcher
tests/                        # 317 unit + 18 e2e tests
```

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -v                 # unit tests
python -m pytest tests/e2e/ -v             # e2e tests (requires Neo4j)
python tests/e2e/setup_sandbox.py          # populate test data
```

Set `WHEELER_LOG_LEVEL=DEBUG` for verbose output.

## Coming Soon: Agentic Layer

The workflow and memory are in place. The next layer is agents that watch the graph and act on it automatically:

- **Auto work logs** (`/wh:report`) — scan the graph for everything created today/this week, generate a structured report. No manual input — timestamps are already on every node. *(Available now)*
- **Reactive triggers** — finding promoted? Hypothesis supported? Analysis stale? The graph fires events and Wheeler responds without being asked.
- **Smart context selection** — instead of always injecting the last 5 findings, adapt to the mode. Planning gets gaps and questions. Writing gets reference-tier findings. Discussion gets contradictions.
- **Investigation continuity** — after one investigation closes, suggest the next based on open questions and graph gaps. Build a research tree across investigations.

## License

[MIT](LICENSE)

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.0-blue" alt="v0.2.0">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="license MIT">
  <img src="https://img.shields.io/badge/local%20only-no%20cloud-2ea44f" alt="local only">
  <img src="https://img.shields.io/badge/graph-Neo4j%20%7C%20Kuzu-008CC1" alt="Neo4j | Kuzu">
  <img src="https://img.shields.io/badge/MCP-25%20tools-orange" alt="MCP 25 tools">
  <img src="https://img.shields.io/badge/Claude%20Code-native-cc785c?logo=anthropic&logoColor=white" alt="Claude Code native">
</p>
