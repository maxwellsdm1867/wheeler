# Wheeler Project Specification

## 0. Project Summary

**Problem:** Scientists using AI assistants for research have no guarantee that results are traceable, reproducible, or trustworthy. AI-generated analyses, findings, and drafts lack provenance — you can't answer "where did this come from?" or "what breaks if this data changes?"

**Why it matters:** Science requires reproducibility. As AI becomes embedded in research workflows (data analysis, literature review, manuscript drafting), the gap between "AI helped me" and "here's the auditable chain of how this result was produced" becomes a credibility problem. Labs need traceable AI workflows to publish with confidence.

**Proposed approach:** Wheeler is a Claude Code-native orchestration layer that wraps every AI action in W3C PROV-DM provenance. MCP tools are "provenance-completing" — one call creates the entity, the activity that produced it, and all dependency links. The agent focuses on science; infrastructure handles bookkeeping.

**Primary success metric:** Every entity in the knowledge graph has a complete provenance chain (WAS_GENERATED_BY → Execution → USED → inputs). Target: 0% orphan entities during normal workflow.

**Key risks / unknowns:**
- Prompt-based protocol compliance is unreliable (mitigated: provenance-completing tools handle it at infrastructure level)
- Knowledge graph noise as projects grow (mitigated: stability scoring + invalidation propagation)
- Claude Code's context window limits for large projects (mitigated: graph_context provides filtered summaries)
- No empirical validation yet that provenance tracking improves research quality (open research question)

---

## 1. Problem Framing & Success Metrics

### Business / User Problem

Scientists using Claude Code for research (data analysis, literature review, code writing, manuscript drafting) face three problems:

1. **Lost context across sessions** — the AI doesn't remember what was found last week, what scripts were run, or what hypotheses are active
2. **Untraceable results** — when a finding appears in a draft, there's no chain linking it to the specific script, data, and parameters that produced it
3. **Cascading invalidation** — when a script changes or data is updated, nothing flags which downstream findings are now stale

AI engineering is the right approach because: (a) the provenance must be captured at the tool level, not by asking the human to log it manually; (b) the dependency graph requires structured storage and traversal that plain text can't support; (c) stability scoring and invalidation propagation are computational, not cognitive tasks.

### Goal

Build a system where every AI-produced research artifact is automatically linked to its provenance chain, and changes propagate through dependency relationships. "Solved" means: a scientist can point to any finding in their manuscript and trace it back to the exact script, data, and parameters that produced it, without manual bookkeeping.

### Stakeholders

| Role | Who | Ownership |
|------|-----|-----------|
| Creator / Lead | Arthur Hong | Architecture, implementation, research direction |
| Primary user | The creator (physicist) | Domain requirements, workflow validation |
| Community | Open source (MIT) | Feedback, contributions, use cases |

### Prior Work

- **Computational notebooks (Jupyter)** — implicit provenance via cell execution order, but no structured graph, no cross-session persistence, no dependency tracking
- **Electronic Lab Notebooks (ELN)** — manual logging, no AI integration, no automatic provenance
- **Flowcept / PROV-AGENT (ORNL)** — W3C PROV for HPC workflows, but no Neo4j backend, no epistemic scoring, no single-user desktop design. Research documented in `docs/prov-agent-research.md`
- **GraphRAG (Microsoft)** — graph-structured retrieval, but for QA over documents, not for research provenance
- **Mem0 / Zep / Graphiti** — agent memory systems, but general-purpose, not research-specific. Evaluated in memory research (session 2026-04-01)

### Constraints

| Constraint | Target | Notes |
|------------|--------|-------|
| Latency (tool call) | < 25ms for provenance-completing call | Benchmarked: 21ms with Neo4j. Imperceptible vs 2-10s LLM inference |
| Cost per request | $0 (runs on Claude Max subscription) | No API keys. `claude -p` for headless work |
| Privacy / compliance | 100% local. No data leaves machine | No cloud services. Neo4j local Docker. All files in project dir |
| Availability | Depends on local Neo4j + Claude Code | Single-user desktop tool, not a service |
| Graph size | Tested to ~1000 nodes | No stress testing beyond this yet |

### Success Metrics

**User-facing:**
- Provenance coverage: % of entities with complete WAS_GENERATED_BY chain (target: 100% for provenance-completing calls)
- Time to trace: can trace any finding to source in < 3 tool calls
- Session continuity: `/wh:resume` restores full context from previous session

**Technical:**
- Orphan rate: % of entities with no provenance after `/wh:close` (target: < 5%)
- Invalidation accuracy: when a script changes, all downstream entities are flagged stale
- Stability score correctness: Papers=0.9, primary data=1.0, LLM findings=0.3

**System:**
- Tool call latency: < 25ms p99 for provenance-completing mutations
- Test suite: 518 tests, all passing
- Zero data loss: dual-write (Neo4j + JSON files) ensures no single point of failure

---

## 2. Prompt Engineering & Systematic Tracking

### Prompt Architecture

Wheeler uses **20 slash command prompts** (`.claude/commands/wh/*.md`), each a self-contained system prompt with YAML frontmatter controlling tool access. These are NOT traditional LLM prompts — they are Claude Code act definitions that set the agent's mode, available tools, and behavioral constraints.

| Prompt Type | Count | Role |
|-------------|-------|------|
| Research acts | 8 | discuss, plan, execute, write, note, pair, chat, ask |
| Coordination | 4 | handoff, reconvene, close, dream |
| Session management | 4 | init, pause, resume, status |
| Infrastructure | 2 | ingest, update |
| Meta | 2 | queue (headless), report |

Each prompt includes mandatory provenance protocol instructions that tell the agent to use provenance-completing tool parameters.

### Prompt Organization

```
.claude/commands/wh/
  ├── ask.md           # Graph query mode
  ├── chat.md          # Casual discussion
  ├── close.md         # Session provenance sweep
  ├── discuss.md       # Sharpen research question
  ├── dream.md         # Graph consolidation
  ├── execute.md       # Run analyses with provenance
  ├── handoff.md       # Delegate independent tasks
  ├── ingest.md        # Bootstrap from existing data
  ├── init.md          # Project setup
  ├── note.md          # Quick insight capture
  ├── pair.md          # Live co-work
  ├── plan.md          # Investigation design
  ├── pause.md         # Save state
  ├── queue.md         # Background headless execution
  ├── reconvene.md     # Review independent results
  ├── report.md        # Generate work log
  ├── resume.md        # Restore context
  ├── status.md        # Show progress
  ├── update.md        # Check for updates
  ├── write.md         # Draft with citations
  └── CLAUDE.md        # Meta-documentation
```

Prompts are versioned via git (checked into the repo). Package data copies live in `wheeler/_data/commands/` and are synced via `wheeler.installer.sync_data()`.

### Evaluation Framework

| Aspect | Approach |
|--------|----------|
| Test set size | N/A — prompts are not evaluated via traditional NLP metrics |
| Evaluation method | Functional: does the act produce the expected graph mutations with correct provenance? |
| Evaluation tooling | 518 unit/integration tests, including e2e provenance chain tests |
| Update cadence | Prompts updated alongside schema changes (e.g., PROV-DM migration updated all 10 act prompts) |

**Gap:** No systematic prompt quality evaluation (e.g., LLM-as-judge scoring of act prompt effectiveness). Currently validated through usage and functional tests only.

---

## 3. Model Selection & Evaluation

### Candidate Models

| Model | Provider | Cost | Latency | Quality Notes | License |
|-------|----------|------|---------|---------------|---------|
| Claude Opus 4.6 | Anthropic (Max sub) | $0 (subscription) | 2-10s | Primary. Best reasoning, tool use | Proprietary (Max) |
| Claude Sonnet 4.6 | Anthropic (Max sub) | $0 (subscription) | 1-3s | Headless tasks, background work | Proprietary (Max) |
| Claude Haiku 4.5 | Anthropic (Max sub) | $0 (subscription) | 0.5-1s | Quick queries, status checks | Proprietary (Max) |

### Model Routing

Wheeler uses per-mode model assignment via `wheeler.yaml`:

```yaml
models:
  chat: haiku          # Quick discussion
  planning: sonnet     # Investigation design
  writing: opus        # Manuscript drafting (needs best reasoning)
  execute: sonnet      # Analysis execution
```

Configurable per project. No dynamic routing — the mode determines the model.

### Evaluation Approach

N/A — Wheeler runs on Claude Max subscription with fixed model options. No model comparison needed; the choice is which Claude tier for which task.

---

## 4. RAG Implementation

### Data Sources

| Source | Type | Volume | Update Frequency | Notes |
|--------|------|--------|-----------------|-------|
| Knowledge graph (Neo4j) | Structured (nodes + relationships) | ~100-1000 nodes per project | Every tool call | Primary provenance store |
| Knowledge files (JSON) | Semi-structured | 1 file per node | Every tool call (dual-write) | File-based backup, git-trackable |
| Embeddings (.wheeler/embeddings/) | Vector | 1 embedding per node | On node creation | fastembed, file-based numpy arrays |
| Workspace files | Unstructured | Project-dependent | External (scientist manages) | Scripts, data, papers, notes |

### Chunking Strategy

N/A — Wheeler does not chunk documents. Each knowledge node IS the atomic unit. Embeddings are generated per-node from the node's primary text field (description, statement, question, etc.).

### Embedding Model & Vector Store

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Embedding model | fastembed (default model, ~33MB) | Local, no API calls, fast |
| Vector store | File-based numpy arrays in `.wheeler/embeddings/` | Zero infrastructure, git-ignorable |

### Retrieval Strategy

Three retrieval channels (not yet fused):

1. **Semantic search** (`search_findings`) — cosine similarity over fastembed embeddings
2. **Graph queries** (`query_findings`, `query_hypotheses`, etc.) — structured Cypher with keyword filtering
3. **Context injection** (`graph_context`) — tier-separated recent nodes by timestamp

**Gap:** No multi-channel fusion (Reciprocal Rank Fusion). No graph-distance ranking. No temporal boosting. Research identified Hindsight's TEMPR (4-channel retrieval) as the target architecture. Not yet implemented.

### RAG Evaluation

| Metric | Description | Baseline | Current |
|--------|-------------|----------|---------|
| Retrieval accuracy | N/A | N/A | Not measured |
| Answer accuracy | N/A | N/A | Not measured |

**Gap:** No retrieval evaluation framework. No test set of questions with known answer locations. This is a significant gap for validating that the graph actually helps the LLM perform better. Research (GraphRAG-Bench) found that graph-based retrieval underperforms naive RAG on simple queries and only helps on multi-hop reasoning.

---

## 5. Agent Systems

### Agent Architecture

**Framework:** Claude Code native (slash commands + MCP tools). No LangChain, no CrewAI, no custom agent framework. Claude Code IS the orchestrator.

**Control flow:**

```
Scientist → Claude Code (interactive)
  ├── /wh:discuss → sharpen question (graph reads)
  ├── /wh:plan → design investigation (graph reads + writes)
  ├── /wh:execute → run analysis (full tool access + provenance)
  ├── /wh:write → draft text (citation enforcement)
  └── /wh:close → provenance sweep (orphan detection)

Scientist → wh queue "task" (headless)
  └── claude -p → structured output → .logs/*.json
       └── /wh:reconvene → review results
```

**Subagent support:** Claude Code's native subagent system (`.claude/agents/`) enables specialized agents (data scout, code writer, executor, literature reviewer). Not yet implemented — current acts run in the main conversation context.

### Tools

| Tool | Purpose | Input / Output | Error Handling |
|------|---------|----------------|----------------|
| add_finding | Create Finding with auto-provenance | description, confidence, execution_kind?, used_entities? → node_id + provenance | Returns error JSON, never crashes |
| add_hypothesis | Create Hypothesis with auto-provenance | statement, execution_kind?, used_entities? → node_id | Same |
| add_script | Register code file | path, language → node_id | Auto-computes hash if file exists |
| add_execution | Record activity | kind, description → node_id | Always succeeds |
| link_nodes | Create relationship | source_id, target_id, relationship → status | Validates relationship type against whitelist |
| search_findings | Semantic search | query → ranked results | Returns empty list if no embeddings |
| detect_stale | Find changed scripts + propagate | (none) → stale scripts + affected nodes | Tolerates missing files |
| validate_citations | Check provenance | text → citation statuses | On-demand, not blocking |
| graph_context | Inject context | (none) → markdown summary | Returns empty string if graph offline |
| run_cypher | Raw graph query | query, params → results | Returns error, never crashes |

33 MCP tools total. All return JSON. All handle errors gracefully (return error dict, never raise).

### Safety & Robustness

| Concern | Approach |
|---------|----------|
| Error handling | All MCP tools catch exceptions and return `{"error": ...}`. Graph failures don't crash the server. |
| Security | All Cypher queries use `$props.key` parameterized queries (no injection). No API keys in code. Git hooks check for API key leaks. |
| Infinite loop prevention | Headless tasks (`wh queue`) have configurable `max_turns` (default 10). Background agents have `maxTurns` in subagent definitions. |
| Guardrails | Citation validation is deterministic (regex + Cypher, not LLM self-judgment). Stability scores are policy-based, not LLM-assessed. |
| Cost monitoring | $0 — runs on Max subscription. No per-token billing. |

### Agent Evaluation

| Test Type | # Tests | Description |
|-----------|---------|-------------|
| Unit tests (tools) | ~200 | Individual MCP tool behavior, graph mutations, queries |
| Integration tests (workflows) | ~50 | E2e provenance chains, citation validation, graph gaps |
| Provenance-completing tests | 4 | Auto-creation of Execution + links |
| Migration tests | 11 | Analysis → Script + Execution conversion |
| Stability/session tests | ~15 | Stability scoring, session_id propagation, invalidation |

**Gap:** No adversarial tests. No representative task suite measuring end-to-end task completion rate. No agent trace logging and analysis. These are important for validating that the system works in real research workflows.

---

## 6. Deployment & User Interface

### API Design

| Aspect | Approach |
|--------|----------|
| Framework | FastMCP (MCP protocol over stdio) |
| Streaming | No (MCP tools return complete responses) |
| Authentication | N/A — local process, no network API |
| Rate limiting | N/A — single user, local |
| Error handling | All tools return JSON with error field. MCP server never crashes. |

### User Interface

| Aspect | Approach |
|--------|----------|
| UI framework | Claude Code CLI (terminal) + Neo4j Browser (localhost:7474) for graph visualization |
| Key interactions | Slash commands (`/wh:*`), MCP tool calls (automatic), `wh` CLI for headless tasks |
| Feedback mechanism | `/wh:close` session sweep (user approves/rejects provenance links). `set_tier` for promoting findings. |

### Infrastructure

| Aspect | Approach |
|--------|----------|
| Hosting | Local machine only. No cloud deployment. |
| Containerization | Neo4j runs in Docker. Wheeler itself is a pip-installed Python package. |
| CI/CD | GitHub Actions: auto-release on version bump. Pre-commit hooks: API safety + tests + mypy + ruff. Pre-push hooks: full test suite. |

**Gap:** No Dockerfile for Wheeler itself. No docker-compose for one-command setup (Neo4j + Wheeler). Setup requires manual steps (venv, pip install, docker run neo4j).

---

## 7. System Monitoring & Error Analysis

### Component-Level Monitoring

| Component | Metrics to Track | Status |
|-----------|-----------------|--------|
| MCP tools | Response time, error rate, provenance completion rate | **Gap:** not tracked |
| Graph | Node counts, relationship counts, orphan rate | Available via `graph_status` + `graph_gaps` |
| Provenance | Stale script count, invalidation propagation reach | Available via `detect_stale` |
| Stability | Distribution of stability scores across node types | **Gap:** no dashboard |
| Sessions | Nodes created per session, provenance coverage | **Gap:** session_id exists but no analysis tools |

### Logging

| Level | Approach |
|-------|----------|
| Basic | Python stdlib logging (`logging.getLogger(__name__)`) in every module |
| Headless tasks | Structured JSON logs in `.logs/` directory |
| Provenance | Every node creation logged with node_id, label, session_id |
| Validation | Citation validation results logged per document |

**Gap:** No centralized request logging (timestamp, tool, latency, cost). No Langfuse/LangSmith integration (and wouldn't make sense — Wheeler doesn't call the API directly). No metrics dashboard.

### Error Analysis Process

| Process | Status |
|---------|--------|
| Failure categorization | **Gap:** no systematic error taxonomy |
| Feedback loop | `/wh:close` catches orphans. `/wh:dream` flags stale/contradictory nodes. Both are manual triggers, not automatic. |
| Alerting | **Gap:** none |

---

## 8. Fine-Tuning

N/A — Wheeler uses Claude via Max subscription (no fine-tuning access). The system is designed to work with general-purpose Claude models via prompt engineering and structured tool interfaces.

---

## 9. Code Quality & Repository Structure

### Project Structure

```
wheeler/
├── models.py                  # Pydantic v2 models, prefix mappings (source of truth)
├── config.py                  # YAML config loader
├── provenance.py              # Stability scoring, invalidation propagation
├── mcp_server.py              # FastMCP server — 33 tools
├── workspace.py               # File discovery + context formatting
├── knowledge/
│   ├── store.py               # File I/O: read, write, list, delete (atomic)
│   ├── render.py              # Markdown rendering for wh show
│   └── migrate.py             # Graph ↔ filesystem migration
├── graph/
│   ├── backend.py             # GraphBackend ABC + factory
│   ├── neo4j_backend.py       # Neo4j backend
│   ├── schema.py              # Constraints, indexes, node ID generation
│   ├── context.py             # Size-limited context injection
│   ├── provenance.py          # Script hashing, staleness detection
│   ├── trace.py               # Provenance chain traversal
│   └── migration_prov.py      # PROV schema migration tool
├── search/
│   └── embeddings.py          # EmbeddingStore (fastembed + numpy)
├── validation/
│   └── citations.py           # Regex extraction + Cypher validation
├── tools/
│   ├── graph_tools/           # Mutations + queries + provenance-completing dispatch
│   └── cli.py                 # Typer CLI
├── __init__.py                # Version, logging setup
├── installer.py               # Install/uninstall/update slash commands + MCP
├── task_log.py                # Structured task logging
├── validate_output.py         # Post-hoc citation validation
└── log_summary.py             # Reconvene log summarizer

.claude/commands/wh/           # 20 slash commands (acts)
knowledge/                     # Graph metadata (JSON, one per node)
.notes/                        # Research notes (markdown artifacts)
.plans/                        # Investigation state
.logs/                         # Headless task output
tests/                         # 518 tests
docs/                          # Research docs, project spec
bin/wh                         # Headless launcher
```

### Code Standards

- `from __future__ import annotations` in every module
- Type hints on all function signatures
- Stdlib logging with `logging.getLogger(__name__)`
- Async for graph I/O, sync for file I/O
- Lazy imports in tools/ to avoid circular deps
- `$props.key` parameterized Cypher (no kwarg collision)
- All MCP tools return JSON, catch all exceptions
- `model_config = {"extra": "allow"}` on Pydantic models for forward compatibility

### README Contents

- [x] Problem and solution overview
- [x] Architecture diagram (three-layer: Acts / File System / Graph)
- [x] Key design decisions (in ARCHITECTURE.md)
- [x] Setup instructions (clone → run)
- [x] Command reference table
- [ ] **Gap:** Performance metrics and evaluation results not in README
- [x] Live demo: N/A (local tool, not a web service)

---

## 10. Project Timeline & Milestones

| Milestone | Date | Status |
|-----------|------|--------|
| v0.1 — Initial prototype | 2026-03 | Done |
| v0.2 — Graph backends + search | 2026-03 | Done |
| v0.3 — Kuzu, vector search, three-layer architecture | 2026-03-26 | Done |
| v0.4 — Hardening (kwarg fix, depscanner, dead code) | 2026-03-28 | Done |
| v0.5 — W3C PROV-DM schema, provenance-completing tools | 2026-04-02 | Done |
| v0.6 — Subagent team definitions | — | Planned |
| v0.6 — Domain skills (electrophysiology, statistics) | — | Planned |
| v0.6 — Multi-channel retrieval (semantic + graph + temporal) | — | Planned |
| v0.7 — Graph memory consolidation (smarter /wh:dream) | — | Planned |
| v0.7 — Temporal validity (valid_from / valid_to on entities) | — | Planned |
| v1.0 — Production-ready for lab use | — | Planned |

---

## 11. Appendix

### Key Documents

- `docs/prov-agent-research.md` — Full PROV-DM research, schema design, benchmarks, evidence
- `ARCHITECTURE.md` — Three-layer architecture, module dependency graph, design principles
- `CLAUDE.md` — Wheeler conventions for Claude Code
- `.claude/plans/ethereal-petting-hoare.md` — PROV-DM migration execution plan

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│  ACTS          /wh:* slash commands                 │  What you DO
│                bin/wh headless runner                │
├─────────────────────────────────────────────────────┤
│  FILE SYSTEM   .notes/*.md (prose)                  │  What you KNOW
│                .plans/*.md, docs/, scripts/          │  (real artifacts)
├─────────────────────────────────────────────────────┤
│  GRAPH         knowledge/*.json (index)             │  How things CONNECT
│                Neo4j: W3C PROV relationships         │
│                Stability scores + invalidation       │
└─────────────────────────────────────────────────────┘
```

### Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03 | Claude Code as orchestrator, not custom Python | Zero orchestration code. YAML tool restrictions + markdown prompts. |
| 2026-03 | Graph is index, files are source of truth | Graphs are good at connections, bad as document stores |
| 2026-03 | Dual-write (Neo4j + JSON) | No single point of failure. JSON is git-trackable. |
| 2026-03-31 | W3C PROV-DM standard relationships | Universal, type-agnostic, recognized. Validated by 6 workflow systems. |
| 2026-03-31 | Split Analysis → Script + Execution | Separate code (entity) from running it (activity). Enables multi-run tracking. |
| 2026-04-01 | Drop Kuzu backend, Neo4j only | Simplify. One backend done well. |
| 2026-04-02 | Provenance-completing tools | Infrastructure handles bookkeeping. ESAA paper: zero violations with enforcement. |
| 2026-04-02 | Mission: reliable, trustworthy, trackable AI workflows for science | Not "a knowledge graph" or "an agent framework." The product is the guarantee. |

### Gap Summary

| Gap | Priority | Section |
|-----|----------|---------|
| No retrieval evaluation framework | High | 4 |
| No multi-channel retrieval fusion | High | 4 |
| No adversarial or task-completion tests | Medium | 5 |
| No Dockerfile / docker-compose | Medium | 6 |
| No centralized request logging | Medium | 7 |
| No metrics dashboard | Low | 7 |
| No systematic error taxonomy | Low | 7 |
| No prompt quality evaluation | Low | 2 |
