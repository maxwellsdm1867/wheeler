<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">Reliable, trustworthy, trackable AI workflows for science.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/v0.12.0-blue" alt="v0.12.0">
  <img src="https://img.shields.io/badge/status-beta-yellow" alt="Status: Beta">
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-native-orange" alt="Claude Code Native"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://doi.org/10.5281/zenodo.20498885"><img src="https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20498885-blue.svg" alt="DOI"></a>
</p>
Wheeler is a thinking partner for scientists, built natively on Claude Code. It gives you slash commands for each stage of research: discuss the question, plan the investigation, execute analyses, write up results. Every action is wrapped in a knowledge graph that tracks how research artifacts (papers, code, data, findings, drafts) depend on each other, making every AI-produced result traceable back to the exact script, data, and parameters that produced it.

Runs 100% locally. No API keys, no cloud services. Your data never leaves your machine.

> Named after great physicist John Archibald Wheeler, Niels Bohr's longtime collaborator. Wheeler and Bohr worked by talking. Bohr would pace, thinking out loud. Wheeler would push back, sharpen the question, sketch the math. The best ideas emerged from the conversation, not from either person alone. That's the model here.

---

## Quick Start

```bash
uvx wheeler init my-research-project
cd my-research-project && claude
/wh:start
```

That's it. The first command scaffolds the project (`.plans/`, `.wheeler/`, `wheeler.yaml`, `.mcp.json`) and installs slash commands and agents to `~/.claude/`. The second drops you into Claude Code with Wheeler's MCP servers wired up. The third routes you to the right `/wh:*` command for what you want to do.

For long-lived use install Wheeler globally (faster startup, stable paths in `.mcp.json`):

```bash
uv tool install wheeler
wheeler init my-research-project
```

Run `wheeler doctor` any time to verify your setup (Python version, deps, Claude Code, Neo4j connectivity).

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Max subscription), and [Neo4j Desktop](https://neo4j.com/download/) (free). New to all this? Walk through the **[Getting Started Guide](docs/GETTING-STARTED.md)**.

### From source

```bash
git clone https://github.com/maxwellsdm1867/wheeler.git
cd wheeler
uv sync --extra dev              # editable install + tests + ruff + mypy + build
uv run wheeler init ~/my-research-project
```

`bin/setup.sh` is still around for the full bootstrap (Neo4j in Docker, schema init, git hooks, zsh completions).

---

## Why Wheeler

Science requires reproducibility. As AI gets embedded in research workflows, the gap between "AI helped me" and "here's the auditable chain of how this result was produced" becomes a credibility problem.

Wheeler is built on four pillars:

**Traceable results.** When Wheeler creates a finding, it automatically records what script ran, what data it consumed, what papers informed the approach, and when it happened. One tool call builds the full provenance chain. The agent focuses on science; infrastructure handles bookkeeping.

**Change propagation.** When a script changes or data is updated, Wheeler flags every downstream finding as stale and reduces its stability score. You always know what to trust and what needs re-verification.

**Context management.** All components read from and write to the same graph, so a finding from data analysis immediately informs subsequent literature searches, experimental design, and manuscript preparation. Information is progressively disclosed and retrieved only when relevant.

**Executable research artifact.** The knowledge graph moves beyond the static PDF. It is an executable map of discovery: any scientist can inherit the full experimental context of a project, explore how results connect, and build directly on top of prior work.

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

Every plan and execution renders a self-contained **visual brief**: the question and sub-questions, figure mockups (pre-registered sketches) paired with the real result figures, a pipeline flow chart, and the data sources. `/wh:discuss` reads that brief to interpret the results with you like a colleague, referencing figures by number and running quick checks against the data to strengthen or disprove a point.

### A typical session

The flow we design for, end to end:

1. **`/wh:discuss`** — talk through the question until it is sharp. Wheeler asks like a colleague, grounds the conversation in what the graph already knows, and locks the decisions.
2. **`/wh:plan`** — Wheeler structures the investigation into waves of tasks and, before any data is touched, **pre-registers the figures**: what each one plots and how competing hypotheses would look different in it. On approval it renders a **visual brief** (question, mockups, pipeline, data sources) so you react to a picture, not prose. Seeing the mockup often sends one more round of sharpening back into the plan.
3. **`/wh:execute`** — Wheeler runs the WHEELER-assigned tasks, logs findings with full provenance, then regenerates the brief as a **report**: each pre-registered mockup now sits beside its real result figure, success criteria are marked, and result tables tuck into dropdowns.
4. **`/wh:discuss`** (again, on the results) — hand Wheeler the brief and interpret together: what holds, what is fragile, what the next question is. Wheeler references figures by number, pulls related findings from the graph, and can run a quick check against the data to settle a contested point, registering whatever you endorse back into the graph.
5. **`/wh:write`** drafts from the endorsed findings with strict citations, or **`/wh:plan`** opens the follow-up investigation. **`/wh:close`** sweeps the session into a synthesis.

You can enter at any step, skip stages, or loop steps 2 to 4 as the work demands.

### Commands

| Command | What it does |
|---------|-------------|
| `/wh:start` | Route to the right command (or type your task) |
| `/wh:discuss` | Think like a colleague: sharpen the question, or interpret a plan's results from its brief (runs checks against the data, cites figures by number) |
| `/wh:plan` | Structure tasks with waves, assignees, checkpoints; render a visual brief with figure mockups |
| `/wh:execute` | Run analyses, log findings with provenance; pair mockups with the real result figures in a report |
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

The `wh` launcher is a bash script in `bin/wh` that ships only with the source tree, not the PyPI wheel. To enable it after a `uv tool install`, clone the repo and symlink it: `sudo ln -sf $PWD/bin/wh /usr/local/bin/wh`. A native `wheeler queue / quick / dream` is on the roadmap.

**Wheeler never does your thinking.** Every task gets tagged: SCIENTIST (judgment calls), WHEELER (grinding), or PAIR (collaborative). Decision points are flagged as checkpoints, not guessed at.

---

## How It Works

### Provenance-completing tool calls

The core primitive: one tool call creates a finding AND its full [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) provenance chain. You never write this directly; slash commands handle it. But under the hood, this is what happens:

```python
add_finding(
    description="Midget and parasol cells have similar clusters of fitted SRM parameters",
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

**51 MCP tools** across 5 servers (mutations, queries, search, ops, legacy monolith).

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete technical spec: module dependency map, PROV schema, MCP tool listing, hardening patterns, design decisions.

### Service integrations

External research tools land in the graph as provenance-tracked nodes. The model is a sandwich: an act reads graph context and shapes the request, the tool's own CLI runs (owning its auth and retries), and one deterministic Python ingest writes the result back through the triple-write. Every call is one Execution whose status is truthful: a failed or incomplete job is recorded as failed with no fabricated outputs (the external-call failsafe), never masquerading as a clean run. Four [Ai2 Asta](https://github.com/allenai/asta-plugins) services ship today (Paper Finder, Semantic Scholar, Theorizer, Literature Reports), routed by `/wh:asta`.

Adding a new service is its own loop: the **`wheeler-service-creator`** skill scaffolds the adapter (registry contract, ingest, act, and test) with the failsafe baked in, then a bundled auditor checks data-safety, provenance, and conventions before it lands. See ARCHITECTURE.md "Service Integrations".

---

## What's New

<details open>
<summary><b>v0.12.0</b> (2026-07-28): batch review and bring-your-own objectives</summary>

- **A harvested batch is reviewed, not endorsed inline**: an Asta Research Assistant harvest now renders a self-contained `harvest.html` (verdicts, summaries, the figures the assistant produced), tags every node with its batch, and queues the decisions for `/wh:discuss <batch>` later, instead of asking you to rule on a dozen outcomes from a terminal summary you have not read.
- **Bring your own LLM-SR error function**: the metric contract takes an arbitrary objective registered from your own module, a declared data shape (so a candidate can be a simulator returning variable-length output, not just a tabular predictor), and hard constraints that reject a candidate outright rather than penalizing it in the loss.
- **Per-group equation fitting**: `wheeler llmsr init --group-by <column>` refits each cell, trial, or subject's own constants under the same candidate form, so a law whose constants vary across individuals is scored on its FORM instead of being rejected by a single pooled fit.
- **`update_node` can clear a field**: an empty string is now a real value that clears a string field, so a dangling path is repairable; omitting an argument still means leave unchanged.
- **Asta and LLM-SR reliability**: Paper Finder sends positive-only queries, Theorizer surfaces real failure reasons, papers dedupe on normalized title, never-assessed work-logs are flagged rather than presented as reviewed, and the LLM-SR CLI no longer vanishes when scipy is absent.

</details>

<details>
<summary><b>v0.11.0</b> (2026-07-18): the Asta Research Assistant, seeded and harvested</summary>

- **Asta Research Assistant, into the graph**: seed a long-range autonomous research mission from a Question or Plan, drive it with the asta-assistant loop in a separate terminal, then harvest the completed work back into Wheeler with full provenance.
- **A work-log is not a finding**: harvested work-logs are saved as indexed Documents (their computed artifacts as Datasets and Scripts), and you decide which outcomes get promoted to Findings, so Wheeler never fabricates an unendorsed result.
- **Validated end to end**: the adapter ships with a live-Neo4j test that walks a real mission through seed, harvest, and re-harvest, checking both provenance sides, idempotency, and the curation manifest.
- **Semantic Scholar author lookup**: the Asta Semantic Scholar adapter gained an `author` sub-query, so an author's papers can be pulled into the graph.

</details>

<details>
<summary><b>v0.10.0</b> (2026-07-18): equation discovery + service invocation</summary>

- **LLM-SR equation discovery**: discover a closed-form equation from a dataset via LLM-guided evolutionary search, run on your Max subscription with no API keys, landed as a provenance-tracked Script plus a Finding with in-domain and out-of-domain metrics.
- **Discover the law, not the best fit**: the run selects the winner by parsimony or out-of-domain generalization, so it recovers the true equation instead of an overfit that merely scores lower training error.
- **Invoke services from a plan**: name a service (LLM-SR, Asta, ...) in `/wh:plan`; a cross-provider router interviews you for that service's inputs, shows the assembled request, and dispatches it, with the run wired into the plan's provenance.

</details>

---

## Architecture

```text
Claude Code (interactive)
    ├── /wh:* slash commands (.claude/commands/wh/*.md)
    │       ├── /wh:start: intent router (invokes other commands)
    │       ├── YAML frontmatter: tool restrictions per mode
    │       └── System prompt: workflow + provenance protocol
    │
    ├── MCP Servers (51 tools)
    │       ├── wheeler_core (12): health, status, context, search, cypher
    │       ├── wheeler_query (10): read-only query_* tools
    │       ├── wheeler_mutations (18): add_*, link, delete, update, merge
    │       ├── wheeler_ops (10): staleness, citations, consistency
    │       └── wheeler (legacy monolith): its original 50 tools, one server
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
├── mcp_server.py            # Legacy monolith: all 50 tools
├── mcp_core.py              # Split server: health, context, search (12)
├── mcp_query.py             # Split server: query_* read-only (10)
├── mcp_mutations.py         # Split server: add_*, link, delete, update (18)
├── mcp_ops.py               # Split server: staleness, citations (10)
├── mcp_shared.py            # Shared: trace IDs, decorators, config
├── knowledge/               # File I/O: read, write, list, render, migrate
├── graph/                   # Neo4j backend, circuit breaker, schema, context
├── search/                  # Embeddings, RRF fusion, graph-expanded search
├── validation/              # Citation validation, ledger quality metrics
├── tools/graph_tools/       # Provenance-completing mutations + queries
└── workspace.py             # Project file scanner

tests/                        # 2163 tests
docs/                         # Getting started, architecture, project spec
```

</details>

---

## Contributing

**Bug reports:** Use `/wh:dev-feedback` from inside a session to file structured issues, or report at [GitHub Issues](https://github.com/maxwellsdm1867/wheeler/issues).

**Tests:** `python -m pytest tests/ -v` (2163 tests). E2E tests require a running Neo4j: `python -m pytest tests/e2e/ -v`.

**Architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical spec (module dependency map, PROV schema, MCP tool listing, hardening patterns).

**Project docs:**
- [Mission](docs/mission.md) — four pillars, target audience, design north star
- [Tech stack](docs/tech-stack.md) — components, infrastructure patterns, current gaps
- [Roadmap](docs/roadmap.md) — shipped versions, v0.9.0 phases, v1.0 criteria
- [Getting started](docs/GETTING-STARTED.md) — install walkthrough with Neo4j Desktop
- [Project spec](docs/PROJECT-SPEC.md) — original design specification

## Citation

If you use Wheeler in your research, please cite it:

```bibtex
@software{hong_wheeler_2026,
  author    = {Hong, Arthur and Rieke, Fred},
  title     = {{Wheeler: Reliable, trustworthy, trackable AI workflows for science}},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20498885},
  url       = {https://doi.org/10.5281/zenodo.20498885}
}
```

## Integrations

Wheeler integrates with external research services so their output lands in the knowledge graph as provenance-tracked nodes, and so those services can act on Wheeler's own work and context. The first integration is [AllenAI Asta](https://github.com/allenai/asta-plugins): Wheeler ships tools (adapters) for four Asta services, **Paper Finder**, **Semantic Scholar**, **Theorizer**, and **Literature Reports**, routed by `/wh:asta`. Each call reads the current graph to shape the request, runs the Asta service, and writes the result back with full provenance (what it `USED`, what it `WAS_GENERATED_BY`, and how the new results connect to the existing graph). A failed call is recorded as failed rather than silently lost.

The integration layer is provider-agnostic and growing. Adding a new external tool is its own workflow: the `wheeler-service-creator` skill scaffolds the adapter, bakes in the provenance and failsafe wiring, and audits it before it lands. See [ARCHITECTURE.md](ARCHITECTURE.md) "Service Integrations" for the design, and the [roadmap](docs/roadmap.md) for where this is headed.

## Acknowledgments

Wheeler's Asta integration shells out to the [Asta toolkit](https://github.com/allenai/asta-plugins) from the [Allen Institute for AI (Ai2)](https://allenai.org). The Paper Finder, Semantic Scholar, Theorizer, and Literature Reports services are Ai2's work ([asta.allen.ai](https://asta.allen.ai)); Wheeler does not vendor or reimplement them, it invokes the upstream `asta` CLI and marshals the results into the knowledge graph with provenance. Credit and thanks to the Ai2 Asta team.

Wheeler's equation discovery is **a plug-in for [LLM-SR](https://github.com/deep-symbolic-mathematics/LLM-SR), not a method of Wheeler's own**. `/wh:llmsr-discover` is an adapter: it drives the LLM-SR pipeline from Claude Code and records the result with provenance. LLM-SR (MIT) is the work of Parshin Shojaee, Kazem Meidani, Shashank Gupta, Amir Barati Farimani, and Chandan K. Reddy, published at ICLR 2025 as ["LLM-SR: Scientific Equation Discovery via Programming with Large Language Models"](https://arxiv.org/abs/2404.18400), and it builds in turn on [**FunSearch**](https://github.com/google-deepmind/funsearch) (Apache-2.0) from Google DeepMind, published in Nature as ["Mathematical discoveries from program search with large language models"](https://doi.org/10.1038/s41586-023-06924-6).

The adapter exists because Wheeler runs on a Max subscription with no API keys, so upstream's sampler and its orchestration loop cannot be used as shipped. `wheeler/integrations/llmsr/vendor/` carries the six modules the driver needs, adapted from their pipeline; the substituted modules are the sampler and the loop. Every other change to their code is environmental (package-relative imports, Python 3.12 AST renames, dropping the `absl` and `torch` dependencies, a macOS `fork` context, and a numpy softmax so `scipy` stays optional). **The search algorithm, the island model, and the program-manipulation logic are theirs, untouched.** One further piece is substituted rather than changed, and only by default: the SCORING seam. A spec declares an `@evaluate.run` that fits a candidate's constants and returns its score, and by default the driver does not call it, scoring instead through Wheeler's own fit/metric seam so the metric is pluggable, the fitted constants are recoverable, and each group can refit its own. A run created with `wheeler llmsr init --use-spec-evaluate` calls the spec's own `@evaluate.run` instead, in upstream's data shape and reading upstream's bare-float return, so a spec that trains its own model inside `evaluate` runs unmodified. The door is a declared flag, never inferred from the spec text. Their scoring code is here unaltered; what changes is only whether the driver takes that path.

If you publish results from `/wh:llmsr-discover`, cite LLM-SR (and FunSearch where appropriate), not Wheeler. For the complete and actively maintained implementation, the benchmark problems, and the authors' own documentation, go upstream. Full per-file attribution, both licenses, and BibTeX entries are in [`wheeler/integrations/llmsr/vendor/NOTICE.md`](wheeler/integrations/llmsr/vendor/NOTICE.md). Credit and thanks to the LLM-SR authors and to the FunSearch team.

## License

[MIT](LICENSE)
