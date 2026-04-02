<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">Reliable, trustworthy, trackable AI workflows for science.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/v0.5.1-blue" alt="v0.5.1">
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

Wheeler makes every AI-produced research artifact traceable. When a finding appears in your manuscript, you can trace it back to the exact script, data, and parameters that produced it — automatically, without manual bookkeeping.

Built natively on Claude Code. Runs 100% locally. No API keys, no cloud services. Your data never leaves your machine.

> Named after great physicist John Archibald Wheeler — Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

---

## Why Wheeler

Science requires reproducibility. As AI becomes embedded in research workflows — data analysis, literature review, manuscript drafting — the gap between "AI helped me" and "here's the auditable chain of how this result was produced" becomes a credibility problem.

Wheeler solves this with two guarantees:

**Every result is traceable.** When Wheeler creates a finding, it automatically records what script ran, what data it consumed, what papers informed the approach, and when it happened. One tool call builds the full provenance chain — the agent focuses on science, infrastructure handles bookkeeping.

**Changes propagate.** When a script changes or data is updated, Wheeler flags every downstream finding as stale and reduces its stability score. You always know what to trust and what needs re-verification.

---

## How It Works

Wheeler wraps every AI action in [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) provenance. The core primitive is the **provenance-completing tool call**:

```python
add_finding(
    description="Calcium oscillation frequency scales with cell density",
    confidence=0.85,
    execution_kind="script",                    # auto-creates Execution activity
    used_entities="D-abc123,S-def456",          # auto-links inputs
    execution_description="cold exposure run"
)
```

One call. Wheeler internally:
1. Creates the Finding entity
2. Creates an Execution activity node (what process produced this)
3. Links Finding --WAS_GENERATED_BY--> Execution (output provenance)
4. Links Execution --USED--> Dataset, Script (input provenance)
5. Sets stability score (0.3 for LLM-generated, 0.9 for papers, 1.0 for primary data)
6. Persists to both Neo4j and JSON file (dual-write, no single point of failure)

The provenance chain is always complete because the agent never had to remember to create it.

### Stability Scoring

Every entity carries a stability score (0.0-1.0) encoding epistemic trust:

| Type | Score | Meaning |
|------|-------|---------|
| Primary data (recordings) | 1.0 | Immutable source data |
| Published papers | 0.9 | Peer-reviewed, unlikely to change |
| Verified findings | 0.8 | Human-checked, reproducible |
| Validated scripts | 0.7 | Tested code |
| LLM-generated findings | 0.3 | Plausible but unverified |

When an upstream entity changes, stability decays downstream: `new = source * (0.8 ^ hops)`. A script edit at stability 0.3 reduces a 2-hop-away document to 0.19. Everything downstream is flagged stale.

### The Provenance Chain

```text
(:Paper {title: "Bhatt 2024"})
  <-[:USED]- (:Execution {kind: "script"})
(:Script {path: "scripts/spike_gen.py", hash: "a3f2..."})
  <-[:USED]- (:Execution)
(:Dataset {path: "data/cell_042.mat"})
  <-[:USED]- (:Execution)

(:Finding {description: "Ca freq scales with density"})
  -[:WAS_GENERATED_BY]-> (:Execution)
  -[:SUPPORTS]-> (:Hypothesis)
  -[:APPEARS_IN]-> (:Document)
```

Every entity traces back through PROV relationships (USED, WAS_GENERATED_BY, WAS_DERIVED_FROM, WAS_INFORMED_BY) to its sources. Semantic relationships (SUPPORTS, CONTRADICTS, CITES, APPEARS_IN) carry scientific meaning on top.

---

## The Workflow

Wheeler gives you a fluid cycle — not a rigid pipeline. Enter at any point, skip stages, repeat them.

```text
 ┌─────────────────────────────────────────────────────┐
 │  TOGETHER          you + wheeler, thinking out loud  │
 │  discuss  plan  chat  pair  write  note  ask         │
 └────────────────────────┬────────────────────────────┘
                          │ remaining work is grinding
                          v
 ┌─────────────────────────────────────────────────────┐
 │  HANDOFF            propose independent tasks        │
 │  handoff            you approve, modify, or keep     │
 │                     talking                          │
 └────────────────────────┬────────────────────────────┘
                          │
                          v
 ┌─────────────────────────────────────────────────────┐
 │  INDEPENDENT        wheeler works alone              │
 │  wh queue "..."     logged, stops at decision points │
 └────────────────────────┬────────────────────────────┘
                          │
                          v
 ┌─────────────────────────────────────────────────────┐
 │  RECONVENE          results + flags + surprises      │
 │  reconvene          back to TOGETHER                 │
 └─────────────────────────────────────────────────────┘
```

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
| `/wh:close` | End-of-session provenance sweep |
| `/wh:pause` / `/wh:resume` | Save and restore investigation state |
| `/wh:status` | Show progress, suggest next action |

**Wheeler never does your thinking.** Every task gets tagged — SCIENTIST (judgment calls), WHEELER (grinding), or PAIR (collaborative). Decision points are flagged as checkpoints, not guessed at.

---

## The Knowledge Graph

Two kinds of files: **graph metadata** (JSON, the provenance index) and **research artifacts** (markdown, the actual writing).

**Graph metadata** — `knowledge/*.json`. One file per entity, dual-written to Neo4j:

```
knowledge/
  F-3a2b1c4d.json   # Finding: {description, confidence, stability: 0.3, ...}
  S-2f4a7b8c.json   # Script: {path, hash, language, stability: 0.5, ...}
  X-9c1d3e5f.json   # Execution: {kind: "script", agent_id: "wheeler", ...}
  P-a4f20e91.json   # Paper: {title, authors, doi, stability: 0.9, ...}
  D-7e8f9a0b.json   # Dataset: {path, data_type, stability: 1.0, ...}
```

**Research artifacts** — your actual writing, as natural files:

```
.notes/N-4e5f6a7b.md     # research note (markdown + YAML frontmatter)
docs/spike-generation.md  # draft from /wh:write
scripts/analyze_temp.py   # your analysis code
data/cell_042.mat         # your data
```

The graph is the index. The files are the work. When you need connections ("what findings came from this dataset?"), ask the graph. When you need content, read the file.

### 11 Entity Types

| Prefix | Type | What it tracks |
|--------|------|---------------|
| F | Finding | A result or observation with confidence score |
| H | Hypothesis | A proposed explanation (open/supported/rejected) |
| Q | OpenQuestion | A knowledge gap with priority |
| D | Dataset | A data file (path, type, hash) |
| P | Paper | A literature reference (always tier=reference) |
| S | Script | A code file (path, hash, language) |
| X | Execution | An activity: what ran, when, what it consumed/produced |
| W | Document | A draft or manuscript |
| N | ResearchNote | A quick insight or observation |
| PL | Plan | An investigation plan |
| L | Ledger | A validation record |

### 14 Relationship Types

**W3C PROV standard (6)** — how things were made:
- USED, WAS_GENERATED_BY, WAS_DERIVED_FROM, WAS_INFORMED_BY, WAS_ATTRIBUTED_TO, WAS_ASSOCIATED_WITH

**Wheeler semantic (8)** — what things mean to each other:
- SUPPORTS, CONTRADICTS, CITES, APPEARS_IN, RELEVANT_TO, AROSE_FROM, DEPENDS_ON, CONTAINS

### Citations

In write mode, research claims are validated deterministically (regex + Cypher). Cite your data: `[F-3a2b]`. Mark interpretations. No citation needed for speculation or textbook knowledge.

### Invalidation

When a script file changes:
1. `detect_stale` compares stored hashes against files on disk
2. Changed scripts get stability reduced to 0.3
3. All downstream entities (findings, documents) are flagged stale
4. Stability decays with distance: `source_stability * (0.8 ^ hops)`

You always know what's current and what needs re-verification.

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
# Quick start
docker compose up -d

# Or manually
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/research-graph \
  neo4j:5
```

Browse your graph at http://localhost:7474.

**Semantic search** (included by default):

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

---

## Architecture

```text
┌─────────────────────────────────────────────────────┐
│  ACTS          /wh:* slash commands                 │  What you DO
│                bin/wh headless runner                │
├─────────────────────────────────────────────────────┤
│  FILE SYSTEM   .notes/*.md, docs/, scripts/         │  What you KNOW
│                .plans/*.md (state)                   │  (real artifacts)
├─────────────────────────────────────────────────────┤
│  PROVENANCE    knowledge/*.json (dual-write)        │  What you can TRACE
│  ENGINE        Neo4j: W3C PROV relationships         │
│                Stability scores + invalidation       │
│                Provenance-completing MCP tools        │
└─────────────────────────────────────────────────────┘
```

```text
Claude Code (interactive)
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       ├── YAML frontmatter: tool restrictions per mode
    │       └── System prompt: workflow + provenance protocol
    │
    ├── MCP Servers
    │       ├── wheeler (34 tools) — provenance-completing mutations,
    │       │     queries, search, citations, staleness detection,
    │       │     request logging, raw Cypher
    │       ├── matlab — MATLAB execution (optional)
    │       └── papers — literature search (optional)
    │
bin/wh (headless)
    └── claude -p with structured logging → .logs/*.json
```

| When you're here | When you're away |
| ---------------- | ---------------- |
| Loose, creative, freeform | Structured, validated, logged |
| Provenance auto-captured | Provenance mandatory |
| You are quality control | System is quality control |

See [ARCHITECTURE.md](ARCHITECTURE.md) for full technical details.

## Code Structure

```text
wheeler/
├── models.py                # Pydantic v2: 11 node types, prefix mappings
├── config.py                # YAML loader, Pydantic config models
├── provenance.py            # Stability scoring, invalidation propagation
├── mcp_server.py            # FastMCP — 34 provenance-completing tools
├── request_log.py           # Structured request logging (JSONL)
├── knowledge/
│   ├── store.py             # File I/O: read, write, list, delete (atomic)
│   ├── render.py            # Markdown rendering for wh show
│   └── migrate.py           # Graph ↔ filesystem migration
├── graph/
│   ├── backend.py           # GraphBackend ABC + factory
│   ├── neo4j_backend.py     # Neo4j backend
│   ├── schema.py            # W3C PROV constraints, indexes, ID generation
│   ├── context.py           # Tier-separated context injection
│   ├── provenance.py        # Script hashing, staleness detection
│   ├── trace.py             # Provenance chain traversal
│   └── migration_prov.py    # PROV schema migration tool
├── search/
│   ├── embeddings.py        # EmbeddingStore (fastembed + numpy)
│   └── retrieval.py         # Multi-channel search with RRF fusion
├── validation/
│   └── citations.py         # Regex extraction + Cypher validation
├── tools/
│   ├── graph_tools/         # Provenance-completing mutations + queries
│   └── cli.py               # CLI: show, migrate, graph ops, citations
└── workspace.py             # Project file scanner

tests/                        # 665 tests
docs/                         # Research docs, project spec
```

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -v                 # unit + integration tests (665 tests)
python -m pytest tests/e2e/ -v             # e2e tests (requires Neo4j)
python tests/evaluation/eval_retrieval.py  # retrieval quality evaluation
```

Set `WHEELER_LOG_LEVEL=DEBUG` for verbose output.

## License

[MIT](LICENSE)
