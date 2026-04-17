<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">Reliable, trustworthy, trackable AI workflows for science.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/v0.6.1-blue" alt="v0.6.1">
  <img src="https://img.shields.io/badge/status-beta-yellow" alt="Status: Beta">
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-native-orange" alt="Claude Code Native"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>
Wheeler tracks how every research finding was produced: what script ran, what data it used, what papers informed the approach. It works as a set of slash commands inside [Claude Code](https://docs.anthropic.com/en/docs/claude-code), giving you a different tool for each stage of research (discuss, plan, execute, write). Every action is recorded in a knowledge graph that connects your papers, code, data, findings, and drafts with provenance chains, so any result can be traced back to exactly what produced it.

Runs 100% locally. No API keys, no cloud services. Your data never leaves your machine.

---

## Quick Start

**New to Wheeler?** See the **[Getting Started Guide](docs/GETTING-STARTED.md)** for a complete walkthrough with Neo4j Desktop setup.

**Already have Neo4j running?**

```bash
git clone https://github.com/maxwellsdm1867/wheeler.git
cd wheeler
bash bin/setup.sh                # creates venv, installs deps, inits schema
```

Then open Claude Code and start working:

```bash
cd ~/my-research-project
claude
/wh:init                         # set up project, create graph schema
/wh:discuss                      # sharpen the question
/wh:plan                         # structure the investigation
```

**Prerequisites:** Python 3.11+, Node.js, [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Max subscription), [Neo4j Desktop](https://neo4j.com/download/) (free)

---

## Why Wheeler

Science requires reproducibility. As AI gets embedded in research workflows, the gap between "AI helped me" and "here's the auditable chain of how this result was produced" becomes a credibility problem.

Wheeler solves this with two guarantees:

**Every result is traceable.** When Wheeler creates a finding, it automatically records what script ran, what data it consumed, what papers informed the approach, and when it happened. One tool call builds the full provenance chain. The agent focuses on science; infrastructure handles bookkeeping.

**Changes propagate.** When a script changes or data is updated, Wheeler flags every downstream finding as stale and reduces its stability score. You always know what to trust and what needs re-verification.

---

## The Workflow

Wheeler gives you a fluid cycle, not a rigid pipeline. Enter at any point, skip stages, repeat them.

```text
 TOGETHER         you + wheeler, thinking out loud
 discuss  plan  chat  pair  write  note  ask
                         |
                         v  remaining work is grinding
 HANDOFF          propose independent tasks
 handoff          you approve, modify, or keep talking
                         |
                         v
 INDEPENDENT      wheeler works alone
 wh queue "..."   logged, stops at decision points
                         |
                         v
 RECONVENE        results + flags + surprises
 reconvene        back to TOGETHER
```

### Commands

| Command | What it does |
|---------|-------------|
| `/wh:discuss` | Sharpen the research question through structured dialogue |
| `/wh:plan` | Structure tasks with waves, assignees, checkpoints |
| `/wh:execute` | Run analyses, log findings to graph with provenance |
| `/wh:write` | Draft text with strict citation enforcement |
| `/wh:ingest` | Bootstrap graph from existing code, data, papers |
| `/wh:add` | General-purpose ingest: text, DOI, file, URL |
| `/wh:note` | Quick-capture an insight, observation, or idea |
| `/wh:compile` | Compile graph into synthesis documents with citations |
| `/wh:dream` | Consolidate: promote tiers, detect communities, link orphans |
| `/wh:pair` | Live co-work: scientist drives, Wheeler assists |
| `/wh:ask` | Query the graph, trace provenance chains |
| `/wh:status` | Show progress, suggest next action |
| `/wh:handoff` | Propose tasks for independent execution |
| `/wh:reconvene` | Review results from independent work |

<details>
<summary>More commands</summary>

| Command | What it does |
|---------|-------------|
| `/wh:chat` | Quick discussion, no execution |
| `/wh:triage` | Triage GitHub issues against planned work |
| `/wh:report` | Generate work log from graph (time period) |
| `/wh:close` | End-of-session provenance sweep |
| `/wh:pause` / `/wh:resume` | Save and restore investigation state |
| `/wh:update` | Check for Wheeler updates |
| `/wh:dev-feedback` | File bugs from inside your session |

</details>

### Headless mode

Wheeler can run tasks without you present:

```bash
wh queue "search for papers on SRM models"   # sonnet, 10 turns, logged
wh quick "check graph status"                 # haiku, 3 turns, fast
wh dream                                      # graph consolidation
```

**Wheeler never does your thinking.** Every task gets tagged: SCIENTIST (judgment calls), WHEELER (grinding), or PAIR (collaborative). Decision points are flagged as checkpoints, not guessed at.

---

## How It Works

### Provenance-completing tool calls

The core primitive: one tool call creates a finding AND its full [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) provenance chain. You never write this directly; slash commands handle it. But under the hood, this is what happens:

```python
add_finding(
    description="Calcium oscillation frequency scales with cell density",
    confidence=0.85,
    execution_kind="script",                    # auto-creates Execution activity
    used_entities="D-abc123,S-def456",          # auto-links inputs
)
```

Wheeler internally creates the Finding, an Execution activity node, links inputs (Dataset, Script) via USED, links the output via WAS_GENERATED_BY, sets a stability score, and dual-writes to Neo4j and JSON. The provenance chain is always complete because the agent never had to remember to create it.

### Stability and invalidation

Every entity carries a stability score (0.0-1.0) encoding epistemic trust: primary data = 1.0, published papers = 0.9, validated scripts = 0.7, LLM-generated findings = 0.3. When an upstream entity changes, stability decays downstream: `new = source * (0.8 ^ hops)`. Changed scripts propagate stale flags through the entire dependency chain.

### The knowledge graph

The graph is an index over files, not a document store. Each node stores an ID, type, tier, title, path, and timestamps. Full content lives in `knowledge/{id}.json`. Human-browsable rendering lives in `synthesis/{id}.md` (Obsidian-compatible with YAML frontmatter and `[[backlinks]]`). When you need connections, ask the graph. When you need content, read the file.

**11 entity types:** Finding, Hypothesis, OpenQuestion, Dataset, Paper, Script, Execution, Document, ResearchNote, Plan, Ledger.

**14 relationship types:** 6 W3C PROV standard (USED, WAS_GENERATED_BY, WAS_DERIVED_FROM, WAS_INFORMED_BY, WAS_ATTRIBUTED_TO, WAS_ASSOCIATED_WITH) + 8 Wheeler semantic (SUPPORTS, CONTRADICTS, CITES, APPEARS_IN, RELEVANT_TO, AROSE_FROM, DEPENDS_ON, CONTAINS).

**44 MCP tools** across 5 servers (mutations, queries, search, ops, legacy monolith).

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete technical spec: module dependency map, PROV schema, MCP tool listing, hardening patterns, design decisions.

---

## What's New

<details>
<summary><b>v0.6.1</b> (2026-04-16) — Bug fixes, update_node, parameter discoverability</summary>

- **Stale driver fix (#9)**: MCP servers no longer return zeros on first `graph_status` call.
- **`update_node` tool (#16)**: update fields on existing nodes after creation. Full triple-write, field validation, change_log, embedding updates. 44 tools total.
- **`graph_context` topic filter (#10)**: optional `topic` parameter for filtered context injection.
- **Parameter discoverability (#11-14)**: `link_nodes` `relationship` parameter now uses `Literal` type (JSON schema enum). `add_note` docstring updated. Priority scale clarified.
- **Ingest data source discovery (#15)**: workspace scanner detects `.db`/`.sqlite`/`.sqlite3`. Phase 0 in `/wh:ingest` asks about primary data sources.

</details>

<details>
<summary><b>v0.6.0</b> (2026-04-08) — Infrastructure hardening, GraphRAG, split MCP servers</summary>

- **Infrastructure hardening**: circuit breaker, consistency checker, trace IDs, write receipts, node change log, task contracts.
- **GraphRAG enhancements**: graph-expanded local search (`search_context`), Neo4j fulltext index, community detection, entity resolution (`propose_merge` + `execute_merge`), retrieval quality metrics.
- **Split MCP servers**: monolith available as 4 focused servers (`wheeler_core`, `wheeler_query`, `wheeler_mutations`, `wheeler_ops`).

</details>

---

## Architecture

```text
Claude Code (interactive)
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       ├── YAML frontmatter: tool restrictions per mode
    │       └── System prompt: workflow + provenance protocol
    │
    ├── MCP Servers (44 tools)
    │       ├── wheeler_core (12): health, status, context, search, cypher
    │       ├── wheeler_query (8): read-only query_* tools
    │       ├── wheeler_mutations (14): add_*, link, delete, update, merge
    │       ├── wheeler_ops (10): staleness, citations, consistency
    │       └── wheeler (legacy monolith): same 44 tools, one server
    │
bin/wh (headless)
    └── claude -p with structured logging → .logs/*.json
```

<details>
<summary>Code structure</summary>

```text
wheeler/
├── models.py                # Pydantic v2: 11 node types, prefix mappings
├── config.py                # YAML loader, Pydantic config models
├── provenance.py            # Stability scoring, invalidation propagation
├── consistency.py           # Cross-layer drift detection and repair
├── mcp_server.py            # Legacy monolith: all 44 tools
├── mcp_core.py              # Split server: health, context, search (12)
├── mcp_query.py             # Split server: query_* read-only (8)
├── mcp_mutations.py         # Split server: add_*, link, delete, update (14)
├── mcp_ops.py               # Split server: staleness, citations (10)
├── mcp_shared.py            # Shared: trace IDs, decorators, config
├── knowledge/               # File I/O: read, write, list, render, migrate
├── graph/                   # Neo4j backend, circuit breaker, schema, context
├── search/                  # Embeddings, RRF fusion, graph-expanded search
├── validation/              # Citation validation, ledger quality metrics
├── tools/graph_tools/       # Provenance-completing mutations + queries
└── workspace.py             # Project file scanner

tests/                        # 881 tests
docs/                         # Getting started, architecture, project spec
```

</details>

---

## Contributing

**Bug reports:** Use `/wh:dev-feedback` from inside a session to file structured issues, or report at [GitHub Issues](https://github.com/maxwellsdm1867/wheeler/issues).

**Tests:** `python -m pytest tests/ -v` (881 tests). E2E tests require a running Neo4j: `python -m pytest tests/e2e/ -v`.

**Architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical spec (module dependency map, PROV schema, MCP tool listing, hardening patterns).

> Named after physicist John Archibald Wheeler, Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

## License

[MIT](LICENSE)
