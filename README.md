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

Wheeler is three layers:

**Acts** — slash commands that guide you through the scientific process. Discuss the question, plan the investigation, execute analyses, write up results. Each mode gives Claude the right tools and constraints for that stage. Hand off grinding tasks to run independently. Come back and reconvene.

**File system** — your knowledge lives as plain JSON files in `knowledge/`. Findings, hypotheses, papers, notes — one file per node. Browse them, grep them, git-track them. No query language needed to read your own work.

**Knowledge graph** — an index that connects the files. Which finding came from which analysis, which paper informed which method, what questions are still open. The graph is the library catalog. The files are the books.

> Named after John Archibald Wheeler — Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

Runs 100% locally on your machine. No API keys, no cloud services. Your data never leaves your machine. Zero-config graph backend (Kuzu) -- no Docker required. Powered by Claude Max subscription.

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

Your knowledge lives as JSON files in `knowledge/`. Each node is a file you can read directly:

```
knowledge/
  F-3a2b1c4d.json   # Finding
  H-7c1d2e3f.json   # Hypothesis
  Q-1b8f4a2c.json   # Open Question
  P-a4f20e91.json   # Paper
  N-4e5f6a7b.json   # Research Note
  D-9e3b4c5d.json   # Dataset
  A-2f4a7b8c.json   # Analysis
  W-5d2a1b3c.json   # Document
```

```json
{
  "id": "F-3a2b1c4d",
  "type": "Finding",
  "tier": "generated",
  "description": "Calcium oscillation frequency scales with cell density...",
  "confidence": 0.85,
  "created": "2026-03-26T14:30:00+00:00",
  "tags": ["calcium", "oscillations"]
}
```

The graph indexes these files — it stores metadata, relationships, and embeddings, not the content itself. When you need connections ("what findings came from this dataset?"), ask the graph. When you need content, read the file.

`wh show F-3a2b` renders any node as readable markdown. `search_findings "calcium dynamics"` finds related nodes by meaning, not just keywords.

### Tiers

Every node is tagged `reference` (established) or `generated` (new work). Papers are always reference. Findings start as generated and get promoted after verification.

### Provenance

Every link is tracked. Findings trace to analyses, analyses carry script hashes, datasets have file paths. If a script changes after an analysis ran, the finding is flagged as STALE.

```text
Paper ──INFORMED──> Analysis ──USED_DATA──> Dataset
                      └──GENERATED──> Finding ──APPEARS_IN──> Document
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

**Graph backend** — two options, configured in `wheeler.yaml`:

| Backend | Setup | Best for |
|---------|-------|----------|
| **Kuzu** (recommended) | Zero-config. ~4MB pip package, data in `.kuzu/` | Solo research, laptops, getting started |
| **Neo4j** | `docker compose up -d` | Multi-user, existing Neo4j workflows |

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
│  FILE SYSTEM   knowledge/*.json                     │  What you KNOW
│                .plans/*.md, .logs/*.json             │
├─────────────────────────────────────────────────────┤
│  GRAPH         metadata + relationships             │  How things CONNECT
│                embeddings + file pointers            │
└─────────────────────────────────────────────────────┘
```

```text
Claude Code (interactive)
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       ├── YAML frontmatter: tool restrictions per mode
    │       └── System prompt: workflow protocol
    │
    ├── MCP Servers
    │       ├── wheeler (28 tools) — graph, knowledge, citations, search, provenance
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
├── models.py                # Pydantic v2 models, prefix mappings (source of truth)
├── config.py                # YAML loader, Pydantic config models
├── mcp_server.py            # FastMCP — 28 tools exposed to Claude Code
├── knowledge/
│   ├── store.py             # File I/O: read, write, list, delete (atomic)
│   ├── render.py            # Markdown rendering for wh show
│   └── migrate.py           # Migrate existing graph nodes to files
├── graph/
│   ├── backend.py           # GraphBackend ABC + get_backend() factory
│   ├── kuzu_backend.py      # Kuzu embedded (default, zero-config)
│   ├── neo4j_backend.py     # Neo4j backend
│   ├── schema.py            # Constraints, indexes, generate_node_id()
│   ├── context.py           # Tier-separated context injection
│   └── provenance.py        # Script hashing, staleness detection
├── search/
│   └── embeddings.py        # EmbeddingStore (fastembed + numpy)
├── tools/
│   ├── graph_tools/         # Mutations + queries + dual-write dispatch
│   └── cli.py               # CLI: show, migrate, graph ops, citations
├── validation/
│   └── citations.py         # Regex extraction + Cypher validation
└── workspace.py             # Project file scanner

knowledge/                    # JSON knowledge files (source of truth)
.plans/                       # Investigation state, plans, summaries
.logs/                        # Headless task output
.claude/commands/wh/          # Slash commands (acts)
bin/wh                        # Headless launcher
tests/                        # 413 tests
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
