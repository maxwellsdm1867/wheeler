<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">Reliable, trustworthy, trackable AI workflows for science.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/v0.14.0-blue" alt="v0.14.0">
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

That's it. The first command scaffolds the project (`.plans/`, `.wheeler/`, `wheeler.yaml`, `.mcp.json`) and installs slash commands and agents to `~/.claude/` unless the `wh` plugin is already providing them. The second drops you into Claude Code with Wheeler's MCP servers wired up. The third routes you to the right `/wh:*` command for what you want to do.

For long-lived use install Wheeler globally (faster startup, stable paths in `.mcp.json`):

```bash
uv tool install wheeler
wheeler init my-research-project
```

Run `wheeler doctor` any time to verify your setup: Python version, deps, Claude Code, Neo4j connectivity and whether the connection is TLS, which project-isolation model is in force, and whether a legacy install is shadowing the plugin.

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Max subscription), and [Neo4j Desktop](https://neo4j.com/download/) (free). New to all this? Walk through the **[Getting Started Guide](docs/GETTING-STARTED.md)**.

### Installing the acts

Wheeler's `/wh:*` acts ship as a plugin. In Claude Code:

```
/plugin marketplace add maxwellsdm1867/wheeler
/plugin install wh@wheeler
```

Codex is supported as a host too, with the same two steps:

```bash
codex plugin marketplace add maxwellsdm1867/wheeler
codex plugin add wh@wheeler
```

The plugin updates itself and works in every project. It ships from v0.14.0. To try it from a clone instead, point your host at the checkout: `claude --plugin-dir <path-to-clone>`, or pass that path to `codex plugin marketplace add` (it takes a local path as well as `owner/repo`).

`wheeler install` is the LEGACY path: it copies the act files into `~/.claude/commands/wh/`. Those files SHADOW the plugin. Claude Code resolves `/wh:plan` to a file in `~/.claude/commands/wh/` before it looks at the plugin's skills, with no error and no warning, so a machine with both keeps running stale local copies of every act and never sees a plugin update.

If you installed Wheeler before the plugin existed, switch over with:

```bash
wheeler migrate-to-plugin
```

It lists exactly what it will remove (act files, agents, hooks, the statusLine entry, the `wheeler_*` MCP registrations), asks once, then prints the commands above. It is idempotent and safe to run when there is nothing to migrate. `wheeler install` now refuses to run while the plugin is present rather than silently shadowing it, and `wheeler doctor` reports the collision if you ever end up in it.

### Neo4j credentials

`wheeler login` stores them in the OS keychain instead of a shell profile. Easiest route is Aura's own credentials file:

```bash
wheeler login --aura-file neo4j-credentials.txt   # or bare `wheeler login` to type the fields
wheeler login --status                            # which of env, keychain, wheeler.yaml, or default supplies each setting
```

The credential is validated by connecting before it is stored, and the password is never written to a file or echoed. Environment variables still win over the keychain, so existing setups keep working. See the [Getting Started Guide](docs/GETTING-STARTED.md) for the full walkthrough.

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

**51 MCP tools** across 4 servers (core, queries, mutations, ops).

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete technical spec: module dependency map, PROV schema, MCP tool listing, hardening patterns, design decisions.

### Service integrations

External research tools land in the graph as provenance-tracked nodes. The model is a sandwich: an act reads graph context and shapes the request, the tool's own CLI runs (owning its auth and retries), and one deterministic Python ingest writes the result back through the triple-write. Every call is one Execution whose status is truthful: a failed or incomplete job is recorded as failed with no fabricated outputs (the external-call failsafe), never masquerading as a clean run. Four [Ai2 Asta](https://github.com/allenai/asta-plugins) services ship today (Paper Finder, Semantic Scholar, Theorizer, Literature Reports), routed by `/wh:asta`.

Adding a new service is its own loop: the **`wheeler-service-creator`** skill scaffolds the adapter (registry contract, ingest, act, and test) with the failsafe baked in, then a bundled auditor checks data-safety, provenance, and conventions before it lands. See ARCHITECTURE.md "Service Integrations".

---

## What's New

<details open>
<summary><b>v0.14.0</b> (2026-08-07): two hosts, one plugin, no install step</summary>

- **Wheeler runs in OpenAI Codex as well as Claude Code.** The 39 acts exist in exactly one place: their bodies are served over MCP by `get_act`, and each host gets a generated `SKILL.md` stub that fetches them. No act content is authored twice, and mode plus orchestration are derived from each act's existing `allowed-tools` rather than declared, so the two can never disagree.
- **Install is two commands, and nothing Python-shaped.** `/plugin marketplace add maxwellsdm1867/wheeler` then `/plugin install wh@wheeler` (`codex plugin marketplace add` / `codex plugin add` on Codex). The MCP servers launch through `uvx`, so there is no `pip install` and no venv: 13 s once to warm the cache, then about 370 ms per launch, which matches running the console script directly. The plugin is named `wh`, so `/wh:plan` is spelled exactly as before.
- **Remote Neo4j, and credentials that are not your problem.** `neo4j+s://` (Aura) works, with connection pooling, timeouts and transient retry the driver previously had none of. `wheeler login --aura-file` reads the credentials file Aura hands you and stores it in the OS keychain, so nothing lands in a dotfile; `wheeler login --status` says which of env, keychain, `wheeler.yaml` or the built-in default is supplying each field.
- **Paths anchor on the project, not the shell.** Roughly thirty call sites resolved `knowledge/`, `synthesis/` and `.wheeler/` against the current directory, so a server or CLI started in a subdirectory read and wrote the wrong tree. Most visibly: `wheeler services enable` returned exit code 0 while the router never saw the change, and search returned nothing rather than erroring.
- **The deprecated MCP monolith is gone** (1,639 lines), with no loss of tool surface: all 50 of its tools were already covered by the four split servers, which carry 53. `wheeler install` still works but is the legacy path, and now refuses when the plugin is present rather than silently shadowing it.

</details>

<details>
<summary><b>v0.13.0</b> (2026-07-29): score the FORM, not the parameterization</summary>

- **One law, many recordings**: `--data` is now repeatable and nameable, and `--seed-from` / `--score-on` keep two roles apart, so a form extracted from one cell can be scored on cells it never saw, each refitting its own constants. That is a test of the FORM rather than of one lucky parameterization.
- **`wheeler llmsr transfer`**: asks whether the LAW carries over to a recording the search never scored, and reports it beside the different question of whether the CONSTANTS carry over, both labelled and both landing in the graph with provenance.
- **Declarable optimizer that notices when it is stuck**: `--optimizer` takes your own, and the default `auto` escalates from BFGS to Nelder-Mead when no start moved off its init, which is what a flat gradient looks like. Optimizer failure on one cell used to be indistinguishable from the form being wrong there.
- **Bring your own metric, loader, optimizer or recipe**: four open registries, all offerable by the interview, plus `wheeler llmsr scaffold-spec` and a cookbook of executed recipes. A loader is also how one dead cell gets excluded before strict per-group validity rejects a correct law.
- **Upstream's own scoring door, selectable**: `--use-spec-evaluate` runs the spec's `@evaluate.run`, so a spec that trains its own model inside `evaluate` runs unmodified. Every number now travels named after the quantity that produced it rather than after the metric you declared.

</details>

<details>
<summary><b>v0.12.0</b> (2026-07-28): batch review and bring-your-own objectives</summary>

- **A harvested batch is reviewed, not endorsed inline**: an Asta Research Assistant harvest now renders a self-contained `harvest.html` (verdicts, summaries, the figures the assistant produced), tags every node with its batch, and queues the decisions for `/wh:discuss <batch>` later, instead of asking you to rule on a dozen outcomes from a terminal summary you have not read.
- **Bring your own LLM-SR error function**: the metric contract takes an arbitrary objective registered from your own module, a declared data shape (so a candidate can be a simulator returning variable-length output, not just a tabular predictor), and hard constraints that reject a candidate outright rather than penalizing it in the loss.
- **Per-group equation fitting**: `wheeler llmsr init --group-by <column>` refits each cell, trial, or subject's own constants under the same candidate form, so a law whose constants vary across individuals is scored on its FORM instead of being rejected by a single pooled fit.
- **`update_node` can clear a field**: an empty string is now a real value that clears a string field, so a dangling path is repairable; omitting an argument still means leave unchanged.
- **Asta and LLM-SR reliability**: Paper Finder sends positive-only queries, Theorizer surfaces real failure reasons, papers dedupe on normalized title, never-assessed work-logs are flagged rather than presented as reviewed, and the LLM-SR CLI no longer vanishes when scipy is absent.

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
    │       ├── wheeler_query (11): read-only query_* tools
    │       ├── wheeler_mutations (18): add_*, link, delete, update, merge
    │       └── wheeler_ops (10): staleness, citations, consistency
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
├── mcp_core.py              # Split server: health, context, search (12)
├── mcp_query.py             # Split server: query_* read-only (11)
├── mcp_mutations.py         # Split server: add_*, link, delete, update (18)
├── mcp_ops.py               # Split server: staleness, citations (10)
├── mcp_shared.py            # Shared: trace IDs, decorators, config
├── knowledge/               # File I/O: read, write, list, render, migrate
├── graph/                   # Neo4j backend, circuit breaker, schema, context
├── search/                  # Embeddings, RRF fusion, graph-expanded search
├── validation/              # Citation validation, ledger quality metrics
├── tools/graph_tools/       # Provenance-completing mutations + queries
└── workspace.py             # Project file scanner

tests/                        # 2567 tests
docs/                         # Getting started, architecture, project spec
```

</details>

---

## Contributing

**Bug reports:** Use `/wh:dev-feedback` from inside a session to file structured issues, or report at [GitHub Issues](https://github.com/maxwellsdm1867/wheeler/issues).

**Tests:** `python -m pytest tests/ -v` (2567 tests). E2E tests require a running Neo4j: `python -m pytest tests/e2e/ -v`.

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
