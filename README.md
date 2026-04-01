<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">Your scientific operating system in Claude Code.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/v0.5.0-blue" alt="v0.5.0">
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

Wheeler is three layers:

**Acts** — slash commands that guide you through the scientific process. Discuss the question, plan the investigation, execute analyses, capture notes, write up results. Each mode gives Claude the right tools and constraints for that stage. Hand off grinding tasks to run independently. Come back and reconvene.

**File system** — your data, scripts, analysis outputs, notes, and drafts. Wheeler works with your existing project layout — point it at your directories (local, NAS, wherever) and it knows where to find things. Agents know where data lives, where scripts are, and where results go.

**Knowledge graph** — the index that connects everything. `knowledge/` holds JSON metadata for each node. The graph database stores relationships, embeddings, and file pointers. Which finding came from which analysis, which paper informed which method, what questions are still open. The graph is the library catalog. The files are the books.

> Named after great physicist John Archibald Wheeler — Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

Runs 100% locally on your machine. No API keys, no cloud services. Your data never leaves your machine. Powered by Claude Max subscription.

---

## The Workflow

Wheeler gives you a fluid cycle — not a rigid pipeline. You can enter at any point, skip stages, or repeat them.

```text
 ┌─────────────────────────────────────────────────────┐
 │  TOGETHER          you + wheeler, thinking out loud  │
 │  discuss  plan  chat  pair  write  note  ask         │
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

| Command | What it does |
|---------|-------------|
| `/wh:discuss` | Sharpen the research question through structured dialogue |
| `/wh:plan` | Structure tasks with waves, assignees, checkpoints |
| `/wh:execute` | Run analyses, log findings to graph with provenance |
| `/wh:write` | Draft text with strict citation enforcement |
| `/wh:note` | Quick-capture an insight, observation, or idea |
| `/wh:pair` | Live co-work — scientist drives, Wheeler assists |
| `/wh:chat` | Quick discussion, no execution |
| `/wh:ask` | Query the graph, trace provenance chains |
| `/wh:handoff` | Propose tasks for independent execution |
| `/wh:reconvene` | Review results from independent work |
| `/wh:ingest` | Bootstrap graph from existing code, data, papers |
| `/wh:dream` | Consolidate: promote tiers, link orphans, flag stale |
| `/wh:pause` / `/wh:resume` | Save and restore investigation state |
| `/wh:status` | Show progress, suggest next action |

**Wheeler never does your thinking.** Every task gets tagged — SCIENTIST (judgment calls), WHEELER (grinding), or PAIR (collaborative). Decision points are flagged as checkpoints, not guessed at.

## The Knowledge

Two kinds of files: **graph metadata** (JSON, the index) and **research artifacts** (markdown, the actual writing).

**Graph metadata** — `knowledge/*.json`. Structured data the system indexes:

```
knowledge/
  F-3a2b1c4d.json   # Finding: {description, confidence, tier, ...}
  N-4e5f6a7b.json   # Note: {title, file_path: ".notes/N-4e5f6a7b.md", ...}
  P-a4f20e91.json   # Paper: {title, authors, doi, year, ...}
  S-2f4a7b8c.json   # Script: {path, hash, language, ...}
  X-9c1d3e5f.json   # Execution: {kind, agent_id, status, ...}
```

**Research artifacts** — your actual writing, as natural files:

```
.notes/
  N-4e5f6a7b.md     # the actual research note (markdown + YAML frontmatter)
docs/
  spike-generation.md  # a draft from /wh:write
```

```markdown
---
id: N-4e5f6a7b
title: "Temperature dependence of calcium oscillations"
created: 2026-03-26
context: "Reviewing cell_042 recordings"
---

The oscillation frequency drops when we cool the bath below 30C.
Could this be a channel gating effect?
```

The graph node is the index card. The markdown file is the real work. When you need connections ("what findings came from this dataset?"), ask the graph. When you need content, read the file.

`wh show F-3a2b` renders any node as readable markdown. `search_findings "calcium dynamics"` finds related nodes by meaning, not just keywords.

### Tiers

Every node is tagged `reference` (established) or `generated` (new work). Papers are always reference. Findings start as generated and get promoted after verification.

### Provenance

Every link is tracked using W3C PROV standard relationships. Scripts carry file hashes. Executions record what ran, when, and what it consumed. If a script changes after an execution, downstream findings are flagged as STALE with reduced stability scores.

```text
Execution ──USED──> Script (path, hash)
Execution ──USED──> Dataset (path)
Execution ──USED──> Paper (reference)
Finding ──WAS_GENERATED_BY──> Execution
Finding ──APPEARS_IN──> Document
```

### Citations

In write mode, research claims are validated deterministically (regex + Cypher). Cite your data: `[F-3a2b]`. Mark interpretations. No citation needed for speculation or textbook knowledge.

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

**Graph backend** — Neo4j via Docker:

```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/research-graph \
  neo4j:5
```

Browse your graph at http://localhost:7474.

**Semantic search** (optional):

```bash
pip install -e ".[search]"             # adds fastembed (~33MB model, local-only)
```

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
┌─────────────────────────────────────────────────────┐
│  ACTS          /wh:* slash commands                 │  What you DO
│                bin/wh headless runner                │
├─────────────────────────────────────────────────────┤
│  FILE SYSTEM   .notes/*.md (prose)                  │  What you KNOW
│                .plans/*.md, docs/, scripts/          │  (real artifacts)
├─────────────────────────────────────────────────────┤
│  GRAPH         knowledge/*.json (index)             │  How things CONNECT
│                metadata + relationships              │
└─────────────────────────────────────────────────────┘
```

```text
Claude Code (interactive)
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       ├── YAML frontmatter: tool restrictions per mode
    │       └── System prompt: workflow protocol
    │
    ├── MCP Servers
    │       ├── wheeler (30 tools) — graph, knowledge, citations, search, provenance, raw Cypher
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
├── models.py                # Pydantic v2 models, prefix mappings (source of truth)
├── config.py                # YAML loader, Pydantic config models
├── mcp_server.py            # FastMCP — 28 tools exposed to Claude Code
├── knowledge/
│   ├── store.py             # File I/O: read, write, list, delete (atomic)
│   ├── render.py            # Markdown rendering for wh show
│   └── migrate.py           # Migrate existing graph nodes to files
├── graph/
│   ├── backend.py           # GraphBackend ABC + get_backend() factory
│   ├── neo4j_backend.py     # Neo4j backend (default)
│   ├── schema.py            # Constraints, indexes, generate_node_id()
│   ├── context.py           # Tier-separated context injection
│   ├── provenance.py        # Script hashing, staleness detection
│   └── migration_prov.py    # PROV schema migration (Analysis → Script + Execution)
├── search/
│   └── embeddings.py        # EmbeddingStore (fastembed + numpy)
├── tools/
│   ├── graph_tools/         # Mutations + queries + dual-write dispatch
│   └── cli.py               # CLI: show, migrate, graph ops, citations
├── validation/
│   └── citations.py         # Regex extraction + Cypher validation
└── workspace.py             # Project file scanner

knowledge/                    # Graph metadata (JSON index)
.notes/                       # Research notes (markdown artifacts)
.plans/                       # Investigation state, plans, summaries
.logs/                        # Headless task output
.claude/commands/wh/          # Slash commands (acts)
bin/wh                        # Headless launcher
tests/                        # 490 tests
```

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -v                 # unit tests
python -m pytest tests/e2e/ -v             # e2e tests (requires Neo4j)
```

Set `WHEELER_LOG_LEVEL=DEBUG` for verbose output.

## License

[MIT](LICENSE)
