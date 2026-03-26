<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">A lightweight orchestration layer for scientists co-working with Claude Code.</p>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/built%20on-Claude%20Code-orange" alt="Claude Code"></a>
</p>

Slash commands, a knowledge graph, citation validation, and a fluid workflow cycle — all running inside your terminal. Wheeler adds structure where you need it (provenance, citations, task handoff) and stays out of the way where you don't (thinking, discussing, exploring).

You bring the scientific judgment. Wheeler handles the grinding.

> Named after John Archibald Wheeler — Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

---

**Every claim cites a graph node.** You ask a question, Wheeler answers with citations. Every citation is deterministically validated — regex extraction, Cypher lookup, full provenance chain. Not LLM self-judgment.

```text
you: "What do we know about ON parasol contrast responses?"

wheeler: The parasol ON cells show a contrast response index of 0.73 +/- 0.04
[F-3a2b], derived from Naka-Rushton fits [A-7e2d] on the March 2024
recordings [D-9f1c]. This is consistent with the hypothesis that ON-pathway
cells have higher contrast sensitivity than OFF [H-1b4c], though we only
have data from one prep so far.

  citations  F-3a2b ✓  A-7e2d ✓  D-9f1c ✓  H-1b4c ✓
```

**Structure scales with presence.** Loose and creative when you're there. Structured and auditable when Wheeler works alone.

**Wheeler never does your thinking.** Every task gets tagged — SCIENTIST (judgment calls), WHEELER (grinding), or PAIR (collaborative). Wheeler flags decision points as checkpoints instead of guessing.

---

## Setup

**Prerequisites:** Python 3.11+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code), Docker (for Neo4j)

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
/wh:pause       # capture state for later
/wh:resume      # restore context from previous session
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

## Citation Validation

| Flag | Meaning |
| ---- | ------- |
| VALID | Node exists with full provenance chain |
| WEAK | Node exists but missing provenance links |
| STALE | Node exists but upstream script changed since execution |
| INVALID | Node ID not found (hallucinated) |
| UNGROUNDED | Non-trivial claim with zero citations |

Enforced on all paths: interactive (MCP tool), headless (post-hoc validation appended to logs), and manual (`validate_citations`).

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

## MCP Servers

| Server | Purpose |
| ------ | ------- |
| `neo4j` | Knowledge graph (Cypher read/write) |
| `wheeler` | 18 tools: graph CRUD, citations, workspace, provenance |
| `matlab` | MATLAB execution (optional) |
| `papers` | Literature search: PubMed, arXiv, Semantic Scholar (optional) |

## Stack

Python 3.11+ / Neo4j Community (Docker) / Typer + Rich / Pydantic / FastMCP

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Pre-commit hooks enforce: no API key leaks, tests pass, type checking, linting. See [CONTRIBUTING.md](CONTRIBUTING.md).

No API keys. No per-token costs. Runs on Claude Max subscription.

## License

[MIT](LICENSE)

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/tests-185%20passing-brightgreen" alt="tests 185 passing">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="license MIT">
  <img src="https://img.shields.io/badge/neo4j-knowledge%20graph-008CC1?logo=neo4j&logoColor=white" alt="Neo4j">
  <img src="https://img.shields.io/badge/MCP-18%20tools-orange" alt="MCP 18 tools">
  <img src="https://img.shields.io/badge/Claude%20Code-native-cc785c?logo=anthropic&logoColor=white" alt="Claude Code native">
</p>
