<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">A lightweight orchestration layer for scientists co-working with Claude Code.</p>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/built%20on-Claude%20Code-orange" alt="Claude Code"></a>
</p>

Slash commands, a knowledge graph, citation validation, and a fluid workflow cycle — all running locally on your machine inside your terminal. No API keys. No cloud services. No per-token costs. Wheeler runs entirely on your Claude Max subscription.

You bring the scientific judgment. Wheeler handles the grinding.

> Named after John Archibald Wheeler — Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

---

**Every claim cites a graph node.** Wheeler answers with `[NODE_ID]` citations. Every citation is deterministically validated — regex extraction, batched Cypher lookup, provenance chain verification. Not LLM self-judgment. The validation is tiered:

```text
you: "What do we know about ON parasol contrast responses?"

wheeler: The parasol ON cells show a contrast response index of 0.73 +/- 0.04
[F-3a2b], derived from Naka-Rushton fits [A-7e2d] on the March 2024
recordings [D-9f1c]. This is consistent with the hypothesis that ON-pathway
cells have higher contrast sensitivity than OFF [H-1b4c], though we only
have data from one prep so far.

  citations  F-3a2b ✓ valid    A-7e2d ✓ valid    D-9f1c ✓ valid    H-1b4c ~ weak
```

| Status | Meaning |
| ------ | ------- |
| **VALID** | Node exists, full provenance chain verified (e.g., Finding ← Analysis ← Dataset) |
| **MISSING_PROVENANCE** | Node exists but lacks required upstream links (e.g., Finding without a source Analysis) |
| **STALE** | Node exists but upstream script has been modified since execution — results may not be reproducible |
| **NOT_FOUND** | Node ID not in graph — hallucinated or deleted |

**Runs 100% locally.** Wheeler uses Claude Code (your Max subscription) for reasoning, a local Neo4j instance (Docker) for the knowledge graph, and local MCP servers for tool execution. No API keys are needed or allowed — the codebase strips `ANTHROPIC_API_KEY` at startup and pre-commit hooks block any direct API imports. Your data never leaves your machine.

**Structure scales with presence.** Loose and creative when you're there. Structured and auditable when Wheeler works alone.

**Wheeler never does your thinking.** Every task gets tagged — SCIENTIST (judgment calls), WHEELER (grinding), or PAIR (collaborative). Wheeler flags decision points as checkpoints instead of guessing.

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

**Together** — freeform conversation. Graph and tools are available but optional. Say something interesting and Wheeler will *suggest* recording it. Never automatically. Use `/wh:ask` to query the graph and trace provenance chains. Use `/wh:dream` to consolidate the graph (promote tiers, link orphans, flag duplicates).

**Handoff** — when the remaining work is grinding. Wheeler proposes tasks in dependency waves with checkpoint conditions. You approve, modify, or keep talking.

**Independent** — Wheeler works via `claude -p` (headless). Every action logged to `.logs/`. Stops and flags instead of making judgment calls: fork decisions, anomalies, interpretation needed, unexpected results.

**Reconvene** — Wheeler reads the logs, presents: completed (with citations), flagged (needs your judgment), surprises, next steps. Cycle repeats.

## Context Tiers

Every graph node is tagged as `reference` (established knowledge -- papers, verified data) or `generated` (Wheeler's own findings). When Wheeler injects graph context, it separates these into **Established Knowledge** and **Recent Work** sections. Papers are always reference-tier. Use `set_tier` to promote generated findings after verification.

## Full Provenance Chain

Wheeler tracks provenance from literature through analysis to written output:

```text
Paper (reference)
  -> Analysis (script_hash, params)
       -> Dataset (path, hash)
       -> Finding (generated)
            -> Document (draft/revision/final)
```

New node types: **Document** (prefix W) for written artifacts, **Paper** (prefix P) for literature. New relationships: INFORMED (paper informed an analysis), BASED_ON (finding based on paper), APPEARS_IN (node cited in a document).

## Architecture

```text
Claude Code (interactive)
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       ├── YAML frontmatter (allowed-tools per mode)
    │       └── MCP Servers: Neo4j, MATLAB, papers, wheeler-mcp
    │
bin/wh (headless)
    └── wh queue/quick: claude -p with structured logging
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

| Mode | Can do | Can't do |
| ---- | ------ | -------- |
| **chat** | Read, query graph | Write, execute |
| **plan** | Read, write, graph, paper search | Execute code |
| **write** | Read, write, edit, graph reads | Execute code |
| **pair** | Full read/write/execute + MATLAB | Agents, auto graph writes |
| **execute** | Everything | -- |
| **ask** | Read, graph reads, provenance tracing | Write, execute |
| **dream** | Graph reads/writes, tier promotion | Bash, agents |
| **ingest** | Read, write, graph, web search, agents | MATLAB |

## MCP Servers

| Server | Purpose |
| ------ | ------- |
| `neo4j` | Knowledge graph (Cypher read/write) |
| `wheeler` | 23 tools: graph CRUD, citations, workspace, provenance, papers, documents, tiers |
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
