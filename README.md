<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">Context engineering for scientific research with Claude Code.</p>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/built%20on-Claude%20Code-orange" alt="Claude Code"></a>
</p>

Wheeler gives Claude a structured memory for your research — a knowledge graph where findings trace back to data, analyses carry cryptographic receipts, and every conversation builds on the last. Different tools extract different kinds of context depending on what's needed: provenance chains for verification, tier-separated findings for writing, gap analysis for planning, citation validation for drafts.

You bring the scientific judgment. Wheeler handles the grinding.

> Named after John Archibald Wheeler — Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

---

### The graph is the context

Without Wheeler, Claude starts every session cold. With Wheeler, Claude sees:

```text
## Research Context (from knowledge graph)

### Established Knowledge (reference)
- [F-3a2b] Parasol ON Rin = 142 +/- 23 MOhm (confidence: 0.92)
- [F-7c1d] Midget ON Rin = 312 +/- 45 MOhm (confidence: 0.88)
- [P-9e0f] Gerstner 1995 — Spike Response Model framework

### Recent Work (generated)
- [F-a1b2] Cross-prediction VP loss at q=200Hz: parasol 0.15, midget 0.22
- [H-c3d4] Parasol and midget may share spike generation (status: open)

### Open Questions
- [Q-e5f6] Is the VP difference biologically meaningful or within noise? (priority: 9)
```

This is context engineering — the graph provides **typed, tiered, provenance-tracked context** that Claude can't get from just reading files. Different tools extract different slices:

| Tool | What context it provides | When you need it |
|------|------------------------|-----------------|
| `graph_context` | Recent findings (split by tier), open questions, hypotheses | Every session start |
| `query_findings` | Search findings by keyword | Looking up specific results |
| `graph_gaps` | Orphaned papers, unreported findings, stale analyses | Planning next investigation |
| `validate_citations` | Provenance chain verification for each cited node | Writing drafts, verification |
| `graph_status` | Node counts by type | Quick health check |
| `detect_stale` | Analyses whose scripts changed since execution | Before relying on old results |
| `query_papers` | Literature nodes in the graph | Connecting methods to sources |

### Claims have different levels

Not every statement needs a citation. Wheeler distinguishes:

| Claim type | Example | Citation needed? |
|-----------|---------|-----------------|
| **Graph-grounded fact** | "Parasol Rin = 142 MOhm [F-3a2b]" | Yes — cite the Finding node |
| **Interpretation** | "This suggests shared spike generation" | No node yet — marked with epistemic status |
| **Method reference** | "We used the SRM from Gerstner [P-9e0f]" | Yes — cite the Paper node |
| **Provenance claim** | "Derived from March recordings [D-9f1c]" | Yes — cite the Dataset node |
| **Speculation** | "Maybe the frequency dependence is an artifact" | No — this is thinking out loud |
| **Common knowledge** | "RGCs project to the LGN" | No — textbook facts don't need graph nodes |

In **writing mode**, every factual claim about *your research* must cite a node — interpretations are marked explicitly. In **chat/discuss mode**, citation is encouraged but not enforced — the conversation is exploratory.

When citations are present, they're validated deterministically (regex + Cypher, not LLM self-judgment):

| Status | Meaning |
| ------ | ------- |
| **VALID** | Node exists, full provenance chain verified (Finding <- Analysis <- Dataset) |
| **MISSING_PROVENANCE** | Node exists but lacks upstream links |
| **STALE** | Node exists but upstream script modified — results may not reproduce |
| **NOT_FOUND** | Node ID not in graph |

### Runs 100% locally

Wheeler uses Claude Code (your Max subscription) for reasoning, a local Neo4j instance (Docker) for the knowledge graph, and local MCP servers for tool execution. No API keys are needed or allowed — the codebase strips `ANTHROPIC_API_KEY` at startup and pre-commit hooks block any direct API imports. Your data never leaves your machine.

---

## Setup

**Prerequisites:** Python 3.11+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Max subscription), Docker (for Neo4j)

Everything runs locally. No cloud accounts, no API keys, no data leaves your machine.

> **Flat-file backend coming soon.** Right now Wheeler requires Neo4j for the knowledge graph. A markdown-based backend that needs zero infrastructure is on the roadmap — follow the repo for updates.

```bash
git clone https://github.com/maxwellsdm1867/wheeler.git
cd wheeler
bash bin/setup.sh
```

Or manually:

```bash
docker compose up -d                    # start Neo4j
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
wheeler-tools graph init
```

After setup, restart Claude Code and verify MCP servers with `/mcp`.

## Getting Started

```bash
cd ~/my-project && claude    # open Claude Code in your project
/wh:init                     # set up paths, config, knowledge graph
/wh:discuss                  # sharpen the question
/wh:plan                     # structure the investigation
```

`/wh:init` walks you through describing your project, pointing to your code/data/results directories, and seeding your first research question. Then you're working.

```bash
/wh:chat        # quick discussion, no execution
/wh:pair        # live analysis co-work
/wh:write       # draft text with strict citations
/wh:execute     # run analyses, update graph
/wh:ask         # query the graph, trace provenance
/wh:dream       # graph consolidation (promote tiers, link orphans)
/wh:ingest      # bootstrap graph from existing code, data, papers
/wh:pause       # capture state for later
/wh:resume      # restore context from previous session
```

For headless/independent work (no Claude Code needed):

```bash
wh queue "search for papers on SRM models"   # sonnet, 10 turns, logged
wh quick "check graph status"                 # haiku, 3 turns, fast
wh dream                                      # graph consolidation, sonnet, 15 turns
wh status                                     # quick status check
```

## The Workflow

```text
 ┌─────────────────────────────────────────────────────┐
 │  TOGETHER          you + wheeler, thinking out loud  │
 │  /wh:discuss /wh:plan /wh:pair /wh:write            │
 └────────────────────────┬────────────────────────────┘
                          │ context saturation reached
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  HANDOFF            wheeler proposes independent     │
 │  /wh:handoff        tasks, you approve               │
 └────────────────────────┬────────────────────────────┘
                          │ source .logs/handoff-queue.sh
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  INDEPENDENT        wheeler works alone, logged      │
 │  wh queue "..."     stops at decision points         │
 └────────────────────────┬────────────────────────────┘
                          │ tasks complete or flagged
                          ▼
 ┌─────────────────────────────────────────────────────┐
 │  RECONVENE          results + flags + surprises      │
 │  /wh:reconvene      back to TOGETHER                 │
 └─────────────────────────────────────────────────────┘
```

**Together** — freeform conversation. Graph and tools are available but optional. Say something interesting and Wheeler will *suggest* recording it. Never automatically.

**Handoff** — when the remaining work is grinding. Wheeler proposes tasks in dependency waves with checkpoint conditions. You approve, modify, or keep talking.

**Independent** — Wheeler works via `claude -p` (headless). Every action logged to `.logs/`. Stops and flags instead of making judgment calls: fork decisions, anomalies, interpretation needed, unexpected results.

**Reconvene** — Wheeler reads the logs, presents: completed (with citations), flagged (needs your judgment), surprises, next steps. Cycle repeats.

**Wheeler never does your thinking.** Every task gets tagged — SCIENTIST (judgment calls), WHEELER (grinding), or PAIR (collaborative). Wheeler flags decision points as checkpoints instead of guessing.

## Context Tiers

Every graph node is tagged as `reference` (established knowledge) or `generated` (new work from the current investigation).

- **Reference** — papers, verified findings, validated analyses, existing datasets. The foundation you build on.
- **Generated** — fresh findings, new hypotheses, draft documents. Work in progress.

When Wheeler injects graph context, it separates these so the agent (and you) can distinguish what's established from what's new. Papers are always reference-tier. Use `set_tier` to promote generated findings after verification.

## Full Provenance Chain

Wheeler tracks a complete chain from literature through analysis to written output:

```text
Paper (reference)
  ──INFORMED──> Analysis (script_hash, params)
                  ──USED_DATA──> Dataset (path, hash)
                  ──GENERATED──> Finding (generated → reference after verification)
                                   ──SUPPORTS──> Hypothesis
                                   ──APPEARS_IN──> Document (draft/revision/final)
```

Every link is queryable. "What went into this draft?" "Where did this finding come from?" "Which papers informed our methods?" "Is anything stale?"

## Architecture

```text
Claude Code (interactive)
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       ├── YAML frontmatter (allowed-tools per mode)
    │       └── MCP Servers: Neo4j, MATLAB, papers, wheeler-mcp
    │
bin/wh (headless)
    └── wh queue/quick/dream: claude -p with structured logging
            └── .logs/*.json (structured task logs)
```

| Scientist present | Scientist away |
| ----------------- | -------------- |
| Loose, creative, freeform | Structured, validated, logged |
| Graph optional | Graph mandatory |
| Citation validation informational | Citation validation enforced |
| Scientist is quality control | System is quality control |

See [ARCHITECTURE.md](ARCHITECTURE.md) for full technical details and design rationale.

## Modes

| Mode | What it does | Tools available |
| ---- | ------------ | --------------- |
| **chat** | Quick discussion, no execution | Read, graph queries |
| **discuss** | Sharpen the question before planning | Read, write, graph, web search |
| **plan** | Structure an investigation | Read, write, graph, paper search |
| **write** | Draft text with strict citation enforcement | Read, write, edit, graph reads, validation |
| **pair** | Live analysis co-work | Full read/write/execute + MATLAB |
| **execute** | Run analyses with full provenance | Everything |
| **ask** | Query the graph, trace provenance | Read, graph reads |
| **dream** | Graph consolidation — promote, link, flag | Graph reads/writes, tier promotion |
| **ingest** | Bootstrap graph from code, data, papers | Read, write, graph, web search, agents |

## MCP Servers

| Server | Purpose |
| ------ | ------- |
| `neo4j` | Knowledge graph (Cypher read/write) |
| `wheeler` | 23 tools: context, graph CRUD, citations, provenance, papers, documents, tiers |
| `matlab` | MATLAB execution (optional) |
| `papers` | Literature search: PubMed, arXiv, Semantic Scholar (optional) |

## Code Structure

```text
wheeler/
├── __init__.py              # Version, NullHandler logging setup
├── config.py                # Pydantic models, YAML loader, configure_logging()
├── mcp_server.py            # FastMCP server — 23 tools exposed to Claude Code
├── graph/
│   ├── driver.py            # Centralized Neo4j driver (async singleton + sync factory)
│   ├── schema.py            # Node labels, constraints, indexes, generate_node_id()
│   ├── context.py           # Size-limited context injection (tier-separated)
│   ├── provenance.py        # File hashing, Analysis nodes, staleness detection
│   └── trace.py             # Provenance chain walking (backwards traversal)
├── tools/
│   ├── graph_tools/         # Graph operations package
│   │   ├── __init__.py      # Registry dispatch (tool name → function)
│   │   ├── mutations.py     # Write ops: add_finding, add_paper, link_nodes, set_tier...
│   │   ├── queries.py       # Read ops: query_findings, graph_gaps, query_documents...
│   │   └── _common.py       # Shared utilities
│   └── cli.py               # wheeler-tools CLI (Typer + Rich)
├── validation/
│   ├── citations.py         # Regex extraction + batched Cypher validation
│   └── ledger.py            # Provenance audit trail
├── workspace.py             # Project file scanner with caching
├── scaffold.py              # Project directory detection + creation
├── task_log.py              # Structured logging for headless tasks
├── log_summary.py           # Log summarization for /wh:reconvene
├── validate_output.py       # Post-hoc citation validation for logs
└── installer.py             # Package install/update with manifest

.claude/commands/wh/          # 16 slash commands (YAML frontmatter + system prompts)
bin/wh                        # Headless launcher (queue/quick/status/dream)
tests/                        # 191 unit tests
tests/e2e/                    # 18 end-to-end tests against live Neo4j
```

## Stack

Python 3.11+ / Neo4j Community (Docker) / Typer + Rich / Pydantic / FastMCP

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -v                 # 191 unit tests
python -m pytest tests/e2e/ -v             # 18 e2e tests (requires Neo4j)
python tests/e2e/setup_sandbox.py          # populate graph with test data
python tests/e2e/setup_sandbox.py --reset  # wipe test data
```

Pre-commit hooks enforce: no API key leaks, tests pass, type checking, linting.

**Logging:** Set `WHEELER_LOG_LEVEL=DEBUG` for verbose output. Default is INFO.

No API keys. No per-token costs. No data leaves your machine. Runs entirely on Claude Max subscription.

## License

[MIT](LICENSE)

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/tests-209%20passing-brightgreen" alt="tests 209 passing">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="license MIT">
  <img src="https://img.shields.io/badge/neo4j-knowledge%20graph-008CC1?logo=neo4j&logoColor=white" alt="Neo4j">
  <img src="https://img.shields.io/badge/MCP-23%20tools-orange" alt="MCP 23 tools">
  <img src="https://img.shields.io/badge/Claude%20Code-native-cc785c?logo=anthropic&logoColor=white" alt="Claude Code native">
</p>
