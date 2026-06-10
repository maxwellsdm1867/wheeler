<p align="center">
  <h1 align="center">WHEELER</h1>
  <p align="center">Reliable, trustworthy, trackable AI workflows for science.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/v0.9.7-blue" alt="v0.9.7">
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

### Commands

| Command | What it does |
|---------|-------------|
| `/wh:start` | Route to the right command (or type your task) |
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

**50 MCP tools** across 5 servers (mutations, queries, search, ops, legacy monolith).

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete technical spec: module dependency map, PROV schema, MCP tool listing, hardening patterns, design decisions.

---

## What's New

<details open>
<summary><b>v0.9.7</b> (2026-06-10): bug queue cleared</summary>

- **Nine reported bugs fixed (#56 through #64)**: every open issue reproduced, fixed, and verified end-to-end against a live graph.
- **`show_node` and `graph_gaps` hardened**: `show_node` returns an actionable error instead of crashing when a packaged environment is missing `wheeler.knowledge`; `graph_gaps` gains `limit`/`offset`/`summary` parameters and per-bucket counts so its default response stays under the token cap on mature graphs.
- **`/wh:close` made robust**: close Executions always carry a non-empty `started_at` across all three triple-write layers, the session-boundary query ignores malformed timestamps and warns instead of silently falling back, and session-synthesis Documents validate via their close-Execution provenance.
- **Mutation fixes**: `update_node` field validation, figure titles, path dedup, and dataset type defaults (`#57`, `#59`, `#61`, `#62`); triple-write drift is now surfaced proactively in `graph_health` and the consistency summary (`#60`).
- **DOI badge fixed**: the citation badge is now served through shields.io so it renders reliably alongside the other badges.

</details>

<details>
<summary><b>v0.9.6</b> (2026-06-01) — Software citation</summary>

- **Cite this repository**: Added `CITATION.cff` so GitHub renders a one-click "Cite this repository" button (APA and BibTeX export), plus a Citation section in the README with a ready-to-paste BibTeX entry.
- **Authorship recorded**: Arthur Hong and Fred Rieke are now listed as authors and copyright holders across `pyproject.toml`, `LICENSE`, and the citation metadata.

</details>

<details>
<summary><b>v0.9.5</b> (2026-05-25) — Acts grounded in the graph</summary>

- **Acts sweep intermediate work to the graph**: `/wh:pause`, `/wh:close`, `/wh:reconvene`, `/wh:write`, `/wh:pair`, `/wh:discuss`, `/wh:chat`, `/wh:note`, and `/wh:compile` now register conversational artifacts (findings, decisions, sub-questions) as Findings, Notes, and OpenQuestions instead of losing them in prose summaries.
- **Open threads surface on resume**: `/wh:resume` queries OpenQuestion nodes linked to the active plan and surfaces them with `[Q-xxxx]` labels so the scientist sees what's still unresolved across sessions.
- **UPDATE existing graph state**: acts now mark answered OpenQuestions, link new findings to relevant hypotheses (`SUPPORTS`/`CONTRADICTS`) on confirm, and update plan status when criteria are met.
- **Close prompts at natural session ends**: acts that reach a wrap-up moment now suggest `/wh:close` so the orphan sweep and synthesis actually runs.
- **CRUD-at-right-time pattern codified**: `.claude/commands/wh/CLAUDE.md` documents the pattern so future acts inherit it (READ at start, CREATE on emergence, UPDATE on conversation, prompt close at natural ends).

</details>

<details>
<summary><b>v0.9.4</b> (2026-05-20) — PyPI show_node fix, triple-write completeness, act prompt polish</summary>

- **PyPI `show_node` works again**: anchored two unanchored `.gitignore` lines (`knowledge/`, `synthesis/`) that caused hatch to silently drop the `wheeler.knowledge` subpackage from every published wheel since v0.9.0. Any tool that imports `wheeler.knowledge` (most notably `show_node`) raised `ModuleNotFoundError` in installs; this release ships the full subpackage. (#54)
- **Triple-write completeness**: `migrate` and provenance paths now fan out `Execution` writes to JSON and synthesis alongside the graph node, Finding nodes carry an optional `title` field so figure triple-lock can label artifacts cleanly, and synthesis is regenerated on every provenance-completing mutation. (#37, #47)
- **Slash-command prompt fixes**: plan-mode execute renders anchor figures inline, `/wh:dream` runs a framing-divergence detection phase before consolidation, the researcher agent can write and edit notes during research, act prompts include a human-readable label alongside `[NODE_ID]` references, and scientific-reasoning prose and canonical export paths are tightened across acts. (#38, #43, #44, #45, #52)
- **Hooks and dev workflow**: pre-commit and pre-push hooks isolate the pytest subprocess environment so host vars (including `ANTHROPIC_API_KEY`) cannot leak into the test runner. `.gitignore` excludes dev-only `.claude/skills/`, `.claude/agents/issue-*.md`, and `.worktrees/`.
- **Test suite at 1661** (was 1553 in v0.9.3).

</details>

<details>
<summary><b>v0.9.3</b> (2026-05-17) — Hands-free release pipeline</summary>

- **`release.yml` reads `RELEASE_PAT`**: PAT-backed release creation so the resulting `release: published` event propagates to `publish.yml`. Version bump → `git push` → PyPI is now end-to-end automatic (gated on a single reviewer click for the `pypi` environment).

</details>

<details>
<summary><b>v0.9.2</b> (2026-05-17) — Packaging rewrite</summary>

- **One-liner install**: `uvx wheeler init my-project` scaffolds a project and wires Claude Code in under 10 seconds (well under 30 with a warm cache).
- **`wheeler init` command**: creates `.plans/`, `.wheeler/`, `wheeler.yaml`, and a project-local `.mcp.json` pointing at the installed MCP servers, then registers slash commands and agents in `~/.claude/`.
- **`wheeler serve` and `wheeler doctor`**: explicit MCP-server boot for debugging, and a tabular sanity check covering Python, deps, console scripts, Claude Code, slash commands, and Neo4j connectivity.
- **`wheeler --version` flag**: now works at the root level (the `wheeler version` subcommand is also retained).
- **hatchling build backend**: replaces setuptools for simpler wheel builds. `dev` and `all` extras added.
- **uv as the primary dev workflow**: `uv sync --extra dev` replaces the manual venv + pip dance. `uv.lock` is checked in.
- **Test suite at 1553** (was 1545 in v0.9.1).

</details>

<details>
<summary><b>v0.9.1</b> (2026-05-12) — Post-handoff bug sweep</summary>

- **Restore verify on same Neo4j**: `wheeler restore --verify` now prefixes scratch-namespace node IDs so it works against the same Neo4j the archive was packed from (#29).
- **Version stamping on bump**: `/wh:bump` now refreshes installed package metadata so `wheeler.__version__` (and HANDOFF.md / backup manifest) reflect the new version immediately (#30).
- **Cypher error visibility**: The Neo4j circuit breaker no longer masks deterministic schema and syntax errors behind a generic "circuit breaker open" message; the original exception surfaces directly (#31).
- **Embedder dimension in backups**: HANDOFF.md and the manifest report `dim 384` for fresh projects with no on-disk vectors, by reading the model registry instead of failing silently (#32).
- **No more pydantic warning**: `DatasetModel.schema` was renamed to `column_schema` to stop shadowing pydantic's reserved attribute; the MCP/CLI parameter `schema` is unchanged for back-compat (#33).
- **Test suite at 1545** (was 1534 in v0.9.0).

</details>

<details>
<summary><b>v0.9.0</b> (2026-05-12) — Portable handoff and migration</summary>

- **Portable archives**: `wheeler backup` now packs the full project tree (`.plans/`, `.notes/`, scripts, data) and rewrites artifact paths to a `${PROJECT}/` sentinel, so archives move cleanly between machines. Use `--scope graph-only` for the smaller v1-style metadata-only archive.
- **Real restore**: `wheeler restore --fresh --target DIR` reconstitutes a Wheeler project on a new machine; `--merge --conflict {skip|replace|prefix}` imports into an existing one. `--verify` keeps its existing semantics.
- **Manifest v2**: archives carry `archive_uuid`, SHA-256 `manifest_signature`, embedder identity, schema version, source machine info, and an `external_references` table for files outside the project root. Old (v1) archives still verify; restore requires v2.
- **Self-documenting archives**: every archive ships a `HANDOFF.md` at its root with templated recipient instructions, readable without unpacking (`tar -xOzf <archive> HANDOFF.md`).
- **Safety**: secret scan runs on every packed file; `wheeler.yaml` password is stripped to `${NEO4J_PASSWORD}`; `--allow-secrets` records offenders in the manifest.
- **Test suite at 1534** (was 1379 in v0.8.0).

</details>

<details>
<summary><b>v0.8.0</b> (2026-05-10) — Backup/restore, graph quality agents, provenance fixes</summary>

- **Backup and restore (#27, #28)**: New `wheeler backup` Typer subcommand snapshots canonical state (knowledge/, synthesis/, .wheeler/, wheeler.yaml + live Neo4j dump) to a single tar.gz archive with manifest.json. New `wheeler restore --verify` validates restorability via project-tag isolation, no Docker required.
- **Graph quality agents (#21)**: `/wh:graph-link` batch-proposes grouped Execution provenance for session orphans (companion to /wh:close). `/wh:graph-review` runs a non-destructive quality audit (wrong types, broken paths, duplicates, isolated subgraphs) with concrete suggested fixes.
- **`ensure_artifact` auto-provenance (#24)**: passes `execution_kind`, `used_entities`, `execution_description` through to handlers so PL- and other artifact-type nodes get auto-created Executions with proper WAS_GENERATED_BY links instead of being born orphan. Same kwargs pass-through fixes a latent drop affecting all label branches; `add_script` and `add_paper` now also wire to `_complete_provenance`.
- **`add_dataset` reference metadata (#17)**: optional `schema`, `source`, `parent_dataset`, `size`, `format_details` fields. `parent_dataset` automatically creates a `WAS_DERIVED_FROM` edge.
- **/wh:close orphan-Cypher fix (#25)**: replaces broken `n.created`/epochMillis Cypher with `coalesce(n.updated, n.date)` ISO comparison. Previously the documented primary path silently returned zero rows on every session.
- **/wh:handoff pre-flight (#26)**: handoff now runs a close-readiness check (`graph_gaps` + `graph_consistency_check`) before queueing background workers, prompts the user if drift exists, supports `--skip-close` opt-out.
- **Test suite at 1379** (was 1276 in v0.7.0).

</details>

<details>
<summary><b>v0.7.0</b> (2026-04-20) — Graph-as-source-of-truth enforcement</summary>

- **Graph-first plan lifecycle**: Every `/wh:*` act now queries the graph first for plan identity, status, and session state. Filesystem files (STATE.md, .continue-here.md) become rendered views, not authoritative sources.
- **`query_plans` tool**: New MCP tool to search Plan nodes by keyword and status (draft/approved/in-progress/completed), available on all servers. 49 tools total.
- **Read-before-mutate hooks**: Claude Code PreToolUse hook blocks file-bearing mutations unless the file was Read or Written first in the session, enforcing grounded provenance.
- **Process provenance**: Pause, handoff, and close events are recorded as Execution nodes in the graph, making the research process itself auditable.
- **Session continuation notes**: `/wh:pause` writes continuation context as graph-backed ResearchNote nodes linked to the active plan, not just a flat file.

</details>

<details>
<summary><b>v0.6.3</b> (2026-04-19) — Proactive context, cleaner search results</summary>

- **Proactive graph context**: Research acts (plan, execute, pair, chat) now call `search_context` automatically when the input is about research topics, returning clean summarized results instead of raw model dumps.
- **Neo4j connection diagnostics**: Helpful error messages when Neo4j Desktop isn't running, auth fails, or the database is unreachable.
- **Execution tracking**: `add_execution` and `query_executions` MCP tools wired up across all five servers. 46 tools total.
- **`/wh:bump` skill**: Version bump workflow that updates version strings, doc counts, and changelog in one command.

</details>

<details>
<summary><b>v0.6.2</b> (2026-04-18) — Auto-routing, /wh:start entry point</summary>

- **Auto-routing**: 20 command descriptions rewritten with narrow triggers requiring explicit Wheeler/knowledge-graph vocabulary. Commands auto-fire only for unambiguous Wheeler actions, never for general coding.
- **`/wh:start` router**: User-invoked entry point that analyzes your task and routes to the best `/wh:*` command. Accepts optional argument for immediate routing or asks interactively.
- **Routing test suite**: 137 new tests covering tree sync, trigger patterns, domain anchoring, router structure, and false-positive resistance. Total: 1018 tests.

</details>

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
    │       ├── /wh:start: intent router (invokes other commands)
    │       ├── YAML frontmatter: tool restrictions per mode
    │       └── System prompt: workflow + provenance protocol
    │
    ├── MCP Servers (50 tools)
    │       ├── wheeler_core (12): health, status, context, search, cypher
    │       ├── wheeler_query (10): read-only query_* tools
    │       ├── wheeler_mutations (18): add_*, link, delete, update, merge
    │       ├── wheeler_ops (10): staleness, citations, consistency
    │       └── wheeler (legacy monolith): same 50 tools, one server
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

tests/                        # 1707 tests
docs/                         # Getting started, architecture, project spec
```

</details>

---

## Contributing

**Bug reports:** Use `/wh:dev-feedback` from inside a session to file structured issues, or report at [GitHub Issues](https://github.com/maxwellsdm1867/wheeler/issues).

**Tests:** `python -m pytest tests/ -v` (1707 tests). E2E tests require a running Neo4j: `python -m pytest tests/e2e/ -v`.

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

## License

[MIT](LICENSE)
