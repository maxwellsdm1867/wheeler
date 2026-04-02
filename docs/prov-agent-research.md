# Wheeler Provenance Redesign

Research date: 2026-03-31

Sources:
- Souza et al. (2508.02866) — PROV-AGENT: Unified Provenance for AI Agent Interactions
- Souza et al. (2509.13978) — LLM Agents for Interactive Workflow Provenance
- Flowcept codebase (github.com/ORNL/flowcept)
- Wheeler codebase audit

---

## 1. What the Papers Tell Us

### PROV-AGENT (2508.02866)

Extends W3C PROV with AI-agent subclasses: AIAgent, AgentTool,
AIModelInvocation, Prompt, ResponseData, DomainData. Implemented on
Flowcept (ORNL). Key design choice: **no new relationship types** — everything
uses standard PROV relationships (used, wasGeneratedBy, wasDerivedFrom,
wasInformedBy, wasAttributedTo, wasAssociatedWith).

The class hierarchy has two branches:
- **Activity branch**: Campaign → Workflow → Task → AgentTool → AIModelInvocation
- **Entity branch**: DataObject → DomainData, Prompt, ResponseData, AIModel

Five provenance query patterns:
1. Complete lineage of an entity
2. What tools did an agent use?
3. Hallucination investigation (trace bad output → exact prompt/response)
4. Downstream impact (paper retracted → what depends on it?)
5. Error propagation (bad data → all contaminated results)

Queries 3-5 are directly relevant to Wheeler.

### LLM Agents for Workflow Provenance (2509.13978)

Uses LLMs to *query* existing provenance, not to build knowledge graphs.
Key architectural idea: **Dynamic Dataflow Schema** — a compact, auto-maintained
metadata summary injected into prompts instead of raw provenance data. Makes
performance independent of data volume.

Three-part Context Manager: (a) recent buffer, (b) schema summary,
(c) natural language guidelines. This maps to Wheeler's existing structure:
(a) `graph_context`, (b) graph schema, (c) `.plans/STATE.md` + act prompts.

Also validates **self-provenance**: the agent's own actions recorded as
provenance using the same schema.

### What Neither Paper Solves

Both papers track *computational workflow provenance* — what code ran on
what data. Wheeler needs **epistemic provenance**: how scientific
understanding is constructed through dialogue, interpretation, and
judgment. Neither paper models:

- Confidence levels or epistemic uncertainty
- Knowledge evolution across sessions (findings refined over time)
- Scientist-in-the-loop judgment calls
- Literature provenance (claims derived from reading papers, not running code)
- Branching hypothesis exploration

These are Wheeler-specific problems we must solve ourselves.

---

## 2. What to Trim

The current Wheeler schema has accumulated redundancy. The provenance
redesign is a good opportunity to clean up.

### Degenerate Relationship Types

16 relationship types is too many. Several overlap or are never used
distinctly:

```
REMOVE (merge into standard PROV names):
  USED_DATA      → USED           (generalized: any entity, not just datasets)
  RAN_SCRIPT     → USED           (script is an entity used by execution)
  GENERATED      → WAS_GENERATED_BY (standard PROV name, flip direction)
  PRODUCED       → WAS_GENERATED_BY (duplicate of GENERATED)
  BASED_ON       → WAS_DERIVED_FROM (standard PROV name)
  INFORMED       → WAS_INFORMED_BY  (standard PROV name)
  REFERENCED_IN  → merge into CITES (same concept, two names)
  STUDIED_IN     → merge into RELEVANT_TO (same concept, two names)

KEEP (semantic relationships, Wheeler-specific):
  SUPPORTS       — evidential: finding supports hypothesis
  CONTRADICTS    — evidential: finding contradicts hypothesis
  CITES          — citation: entity cites paper
  APPEARS_IN     — containment: entity appears in document
  RELEVANT_TO    — topical: entity related to entity
  AROSE_FROM     — generative: question arose from finding/note
  DEPENDS_ON     — structural dependency
  CONTAINS       — structural containment
```

Result: **14 relationships** (6 PROV standard + 8 semantic). Down from 16,
and the provenance ones are now a recognized standard.

### Degenerate Node Type: Analysis

Analysis currently fuses the code (entity) with the act of running it
(activity). This makes it impossible to:
- Track two runs of the same script with different parameters
- Ask "which executions used this script?" without string matching
- Distinguish "the code" from "running the code"

**Split Analysis → Script (entity) + Execution (activity).**

### Overengineered: Tier System

The current binary tier system (`reference` vs `generated`) is too coarse.
The PROV-AGENT papers don't have weighting either. But Wheeler needs
something richer because LLM outputs are fundamentally different from
experimental data.

**Replace tier with stability (0.0–1.0).** Tier becomes derivable:
`stability >= 0.7` is "reference", below is "generated". One property
instead of two concepts.

Actually: **keep tier as a human-readable label, add stability as the
machine-readable score.** Tier is useful for display and context injection
(`graph_context` separates by tier). Stability adds the quantitative layer.

### PROV-AGENT Classes We Don't Need

The PROV-AGENT paper defines AIModelInvocation, Prompt, ResponseData as
separate entity types. Wheeler can't capture these because Claude Code
doesn't expose LLM call internals. **Skip these entirely.** Don't build
infrastructure for data we can't collect.

What we CAN capture:
- Which act (slash command) created each entity → Execution node
- What entities were inputs to that act → USED relationships
- What entities were outputs → WAS_GENERATED_BY relationships
- Which session this happened in → session_id property

This is the PROV-AGENT model minus the LLM-internal layer, which is
exactly right for Wheeler's architecture.

---

## 3. The Redesigned Schema

### 3.1 Entity Types

```
EXISTING (unchanged):
  Dataset        {id, path, data_type, description, tier, stability}
  Paper          {id, title, authors, doi, year, tier, stability}
  Finding        {id, description, confidence, tier, stability}
  Hypothesis     {id, statement, status, tier, stability}
  OpenQuestion   {id, question, priority, tier}
  Document       {id, title, path, status, tier, stability}
  ResearchNote   {id, title, content, context, tier}
  Plan           {id, status, tier}
  Ledger         {id, mode, pass_rate, tier}

NEW (split from Analysis):
  Script         {id, path, hash, language, version}

COMMON PROPERTIES (all entities via NodeBase):
  id             String    -- unique, prefixed (F-xxxx, S-xxxx, etc.)
  tier           String    -- "reference" or "generated" (display)
  stability      Float     -- 0.0-1.0 epistemic trust (machine)
  stale          Boolean   -- true if upstream changed
  stale_since    String    -- ISO timestamp
  session_id     String    -- session that created this
  created        String    -- ISO timestamp
  updated        String    -- ISO timestamp
```

### 3.2 Activity Type

One activity type: **Execution**. Designed so new functionality is new
values under existing fields, never new fields.

```
  Execution {
    id           String    -- unique, X-prefixed
    kind         String    -- what type of process (see below)
    agent_id     String    -- who performed it (see below)
    status       String    -- "running", "completed", "failed"
    started_at   String    -- ISO timestamp
    ended_at     String    -- ISO timestamp
    session_id   String    -- which conversation session
    description  String    -- human-readable summary of what happened
  }
```

**`kind`** — the type of process. New functionality = new kind value:

```
  TODAY:
    "script"       — running code on data (/wh:execute)
    "discuss"      — discussion that produced insights (/wh:discuss)
    "write"        — drafting session (/wh:write)
    "plan"         — planning session (/wh:plan)
    "pair"         — live co-work (/wh:pair)
    "ingest"       — data ingestion (/wh:ingest)
    "note"         — note creation (/wh:note)

  FUTURE (no schema change needed):
    "lit_review"   — literature search agent
    "data_analysis"— automated data analysis agent
    "code_gen"     — code generation agent
    "validation"   — result validation agent
    "manual"       — scientist's own action (not via Wheeler)
```

**`agent_id`** — who performed the activity. New agents = new values:

```
  TODAY:
    "wheeler"      — Wheeler main session (default)

  FUTURE (no schema change needed):
    "lit-reviewer"       — literature search sub-agent
    "data-analyst"       — data analysis sub-agent
    "scientist"          — human scientist (manual work)
    "external-tool"      — third-party tool integration
```

**Kind-specific data lives in the entities, not in Execution.**
Script path and hash live on the Script entity. Output path and hash
live on the output Dataset entity. Parameters are either a property
on the Execution `description` or a linked entity. This keeps Execution
general — it doesn't need fields that only apply to one kind.

Not every act creates an Execution. `/wh:chat`, `/wh:ask`, `/wh:dream`
are read-only — no provenance needed.

### 3.3 Prefix Mappings

```
UPDATED PREFIX_TO_LABEL:
  S  → Script        (NEW)
  X  → Execution     (NEW — replaces A for Analysis)
  F  → Finding
  H  → Hypothesis
  Q  → OpenQuestion
  D  → Dataset
  P  → Paper
  W  → Document
  PL → Plan
  N  → ResearchNote
  L  → Ledger

REMOVED:
  A  → Analysis      (split into S + X)
```

### 3.4 Relationship Types

```
PROVENANCE (W3C PROV standard — type-agnostic):
  USED                 — activity consumed entity
  WAS_GENERATED_BY     — entity produced by activity
  WAS_DERIVED_FROM     — entity from entity (shortcut, implicit activity)
  WAS_INFORMED_BY      — activity caused by prior activity
  WAS_ATTRIBUTED_TO    — entity created by session/agent
  WAS_ASSOCIATED_WITH  — activity belongs to session

SEMANTIC (Wheeler-specific — carry scientific meaning):
  SUPPORTS             — evidential: finding supports hypothesis
  CONTRADICTS          — evidential: finding contradicts hypothesis
  CITES                — citation: entity cites paper
  APPEARS_IN           — containment: entity in document
  RELEVANT_TO          — topical: entity related to entity
  AROSE_FROM           — generative: question from finding/note
  DEPENDS_ON           — structural dependency
  CONTAINS             — structural containment
```

14 total. The PROV relationships work uniformly across all entity types.
The semantic relationships carry scientific meaning that PROV can't express.

### 3.5 Migration from Old Names

```
OLD                → NEW                     ACTION
─────────────────────────────────────────────────────
Analysis           → Script + Execution      Split node type
A- prefix          → S- and X- prefixes      New ID generation
USED_DATA          → USED                    Rename
RAN_SCRIPT         → USED                    Rename + merge
GENERATED          → WAS_GENERATED_BY        Rename (flip direction)
PRODUCED           → WAS_GENERATED_BY        Rename + merge
BASED_ON           → WAS_DERIVED_FROM        Rename
INFORMED           → WAS_INFORMED_BY         Rename
REFERENCED_IN      → CITES                   Rename + merge
STUDIED_IN         → RELEVANT_TO             Rename + merge
```

### 3.6 PROV-DM Direction Rule (Critical)

W3C PROV-DM uses **dependency-pointing** convention: arrows point from
the dependent back toward its cause/source. This means:

```
(Execution)-[:USED]->(Entity)                  — activity → input (forward)
(Entity)-[:WAS_GENERATED_BY]->(Execution)      — output → activity (backward)
(Entity2)-[:WAS_DERIVED_FROM]->(Entity1)       — derived → source (backward)
(Exec2)-[:WAS_INFORMED_BY]->(Exec1)            — informed → informer (backward)
```

**Implication for invalidation propagation**: to find downstream dependents
of a changed entity, you cannot simply follow edges forward. You need a
two-hop pattern:
1. Find executions that USED the changed entity: `(exec)-[:USED]->(changed)`
2. Find entities generated by those executions: `(output)-[:WAS_GENERATED_BY]->(exec)`
3. Recurse through WAS_DERIVED_FROM: `(derived)-[:WAS_DERIVED_FROM]->(changed)`

**PROV-DM concepts we skip**: Bundles (git handles this), Collections
(CONTAINS covers it), alternateOf, specializationOf, Start/End triggers,
Influence (too generic). Delegation (actedOnBehalfOf) deferred until
multi-agent.

### 3.7 Provenance Chain Example

A real workflow through the new schema:

```cypher
// A paper informed the approach → script was written
(:Paper {title: "Bhatt & Bhalla 2024"})
  <-[:USED]- (:Execution {kind: "script", parameters: "dt=0.1ms"})

// Execution used a script and dataset
(:Script {path: "scripts/spike_gen.py", hash: "a3f2..."})
  <-[:USED]- (:Execution)
(:Dataset {path: "data/cell_042.mat"})
  <-[:USED]- (:Execution)

// Execution produced results
(:Finding {description: "Ca freq scales with density"})
  -[:WAS_GENERATED_BY]-> (:Execution)
(:Dataset {path: "results/freq.csv", tier: "generated"})
  -[:WAS_GENERATED_BY]-> (:Execution)

// Semantic: finding supports a hypothesis
(:Finding) -[:SUPPORTS]-> (:Hypothesis)

// /wh:discuss produced hypothesis from data + findings + paper
(:Execution {kind: "discuss"})
  -[:USED]-> (:Dataset {path: "data/cell_042.mat"})
  -[:USED]-> (:Finding)
  -[:USED]-> (:Paper)
(:Hypothesis) -[:WAS_GENERATED_BY]-> (:Execution {kind: "discuss"})

// /wh:write produced document from findings + papers
(:Execution {kind: "write"})
  -[:USED]-> (:Finding)
  -[:USED]-> (:Paper)
(:Document {title: "Results: Temperature Dependence"})
  -[:WAS_GENERATED_BY]-> (:Execution {kind: "write"})
```

Same pattern everywhere: activity USED entities, entities WAS_GENERATED_BY
activity. Entity types don't matter.

---

## 4. Stability Scoring

### 4.1 Defaults

```
Label          Tier         Stability   Rationale
─────          ────         ─────────   ─────────
Dataset        reference    1.0         Primary data (immutable recordings)
Paper          reference    0.9         Peer-reviewed
Script         reference    0.7         Validated code
Finding        reference    0.8         Verified result
Document       reference    0.7         Published/finalized

Dataset        generated    0.7         Derived data (reproducible)
Script         generated    0.5         Untested code
Finding        generated    0.3         LLM-generated or preliminary
Hypothesis     generated    0.3         Proposed, untested
Document       generated    0.3         Draft
OpenQuestion   generated    0.3         Knowledge gap marker
ResearchNote   generated    0.3         Quick observation
Plan           generated    0.3         Investigation plan
Ledger         generated    0.5         Validation record
```

### 4.2 Invalidation Propagation

When an upstream entity changes, propagate through PROV relationships:

```
new_stability = source_stability * (decay_factor ^ hops)
```

- decay_factor = 0.8 (20% per hop)
- Only reduces, never increases
- Sets `stale = true` on affected nodes

```cypher
// Propagate staleness from a changed node
MATCH (source {id: $changed_id})
SET source.stale = true, source.stale_since = datetime(),
    source.stability = $new_stability
WITH source
MATCH path = (source)-[:USED|WAS_GENERATED_BY|WAS_DERIVED_FROM|WAS_INFORMED_BY*1..10]->(downstream)
WHERE downstream.id <> source.id
WITH downstream, source.stability * (0.8 ^ length(path)) AS decayed,
     downstream.stability AS old_stab
WHERE decayed < old_stab
SET downstream.stale = true, downstream.stale_since = datetime(),
    downstream.prev_stability = old_stab,
    downstream.stability = decayed
RETURN downstream.id, labels(downstream)[0], old_stab, downstream.stability
```

---

## 5. Provenance Capture Strategy

Two layers, plus session management:

### Layer 1: Inline — Acts Create Provenance As They Go

Each act creates an Execution node and links inputs/outputs. The act
prompt includes: "after creating entities, create the Execution activity
and link everything you used and generated."

For script executions, `run_execution` (composite tool) creates Execution +
links Script + Dataset in one call. Complexity hidden from user.

### Layer 2: Close-Session Sweep — `/wh:close`

End-of-session command:
1. Query all entities with this `session_id`
2. Find orphans (no WAS_GENERATED_BY relationship)
3. Propose links: "F-3a2b has no provenance — you created it while
   discussing D-5678 and P-abcd. Link through an Execution?"
4. User approves/rejects batch

### Session Management

- `session_id` generated at session start (in `/wh:init` or first act)
- Every entity created during session gets `session_id` property
- `/wh:close` uses `session_id` to find everything — no conversation parsing

---

## 6. Codebase Impact Audit

### Files That Must Change

**Critical (model + schema):**
- `models.py` — remove AnalysisModel, add ScriptModel + ExecutionModel,
  add stability/stale/session_id to NodeBase, update PREFIX_TO_LABEL
- `graph/schema.py` — update ALLOWED_RELATIONSHIPS to new names,
  add Script/Execution constraints and indexes
- `provenance.py` — update DERIVATION_RELS to new names, add Script/Execution
  stability defaults

**High (tools + MCP):**
- `tools/graph_tools/mutations.py` — replace `add_analysis()` with
  `add_script()` + `add_execution()`, add `run_execution()` composite
- `tools/graph_tools/queries.py` — replace `query_analyses()` with
  `query_executions()`, update `graph_gaps()` Cypher
- `tools/graph_tools/__init__.py` — update tool registry + definitions
- `mcp_server.py` — update tool registrations and descriptions
- `graph/provenance.py` — rewrite `create_analysis_node()` →
  `create_execution_node()`, update `detect_stale_analyses()` to
  work with Script entities
- `validation/citations.py` — update `_PROVENANCE_RULES` to new
  relationship names and node types

**Medium (backend + rendering):**
- `graph/neo4j_backend.py` — no code changes (generic), schema auto-applies
- `graph/trace.py` — update Cypher property projections
- `knowledge/render.py` — add Script/Execution renderers
- `tools/cli.py` — imports update automatically via PREFIX_TO_LABEL

**Medium (act prompts):**
- `.claude/commands/wh/ingest.md` — update examples to Script + Execution
- `.claude/commands/wh/execute.md` — update provenance section
- `.claude/commands/wh/report.md` — update Analysis → Execution in templates

**Low (tests):**
- `tests/test_schema.py` — update ALLOWED_RELATIONSHIPS expected set
- `tests/test_knowledge.py` — replace AnalysisModel with Script/Execution
- `tests/test_trace.py` — update relationship names in examples
- `tests/test_provenance.py` — update AnalysisProvenance → Script tests
- `tests/e2e/*` — update relationship names throughout

### What Gets Deleted

- `AnalysisModel` class in models.py
- `AnalysisProvenance` dataclass in graph/provenance.py
- `add_analysis()` in mutations.py
- `query_analyses()` in queries.py (replaced by `query_executions()`)
- `create_analysis_node()` in graph/provenance.py
- All references to USED_DATA, RAN_SCRIPT, PRODUCED, REFERENCED_IN, STUDIED_IN
  as relationship names

---

## 7. Implementation Order

### Phase 1: Schema (breaking change, do it all at once)

1. Update `models.py`: add ScriptModel, ExecutionModel, remove AnalysisModel,
   add stability/stale/stale_since/session_id to NodeBase
2. Update `graph/schema.py`: new ALLOWED_RELATIONSHIPS, new constraints/indexes
3. Update `provenance.py`: new relationship names in DERIVATION_RELS
4. Update `graph/kuzu_backend.py`: new schema definitions
5. Update all tests to match
6. Write migration tool: existing Analysis nodes → Script + Execution pairs

### Phase 2: Tools

1. New mutation tools: `add_script`, `add_execution`, `run_execution` (composite)
2. New query tools: `query_executions`, `query_scripts`
3. Update `graph_gaps()` for new schema
4. Update `detect_stale` to propagate invalidation downstream
5. Update validation rules in `citations.py`
6. Update MCP server tool registrations

### Phase 3: Acts + Session Management

1. Update act prompts (ingest, execute, report) for new schema
2. Add session_id generation to session start
3. Write `/wh:close` act (session-end provenance sweep)
4. Add orphan detection query

### Phase 4: UX (later)

1. `@` reference syntax for quick entity linking
2. Stability display in `graph_context`
3. Stale warnings in act prompts
4. Provenance chain visualization

---

## 8. Key Design Decisions

### Extensibility Principle

New functionality should be **new values under existing fields**, never
new fields or new node types. The schema has three extension points:

| Field | On | Extend by adding... |
|-------|----|---------------------|
| `kind` | Execution | New process types (agents, manual actions, external tools) |
| `agent_id` | Execution | New agents (sub-agents, human, external) |
| `tier` | All entities | New trust levels (if binary proves insufficient) |

Adding a literature review agent = adding `kind: "lit_review"` and
`agent_id: "lit-reviewer"`. No migration, no schema change, no new
indexes needed.

### Decision Log

| Decision | Choice | Why |
|----------|--------|-----|
| Relationship naming | W3C PROV standard | Universal, type-agnostic, recognized. New relationships only for new scientific semantics, not new agent types. |
| Activity type | Single Execution with `kind` + `agent_id` | One table, many uses. Multi-agent = new values, not new node types. |
| Kind-specific fields | Live on entities, not Execution | script_path on Script, output_path on Dataset. Keeps Execution general. |
| LLM call capture | Skip for now | Can't intercept Claude Code internals. When available: `kind: "llm_call"`, same Execution type. |
| Prompt/Response nodes | Skip for now | Same reason. When available: new entity types, linked via USED/WAS_GENERATED_BY. No Execution changes. |
| Agent node type | Property now, node later | `agent_id` on Execution is enough for single-agent. Promote to `(:Agent)` node with `WAS_ASSOCIATED_WITH` when 3+ agents exist. |
| Stability storage | Property on node | Avoids expensive traversal on every read. |
| Tier vs stability | Keep both | Tier for display, stability for computation. |
| Session tracking | Property now, node later | `session_id` on entities + Execution. Promote to `(:Session)` node when cross-session queries are needed. |

---

## 9. Provenance-Completing Tools

### The Enforcement Problem

The universal protocol (create Execution → link inputs → create entity →
link outputs) was originally enforced via system prompt guidance in act
files. A code audit (2026-04-02) found **zero programmatic enforcement**:
an agent could call `add_finding()` without any provenance and succeed.
Orphan nodes accumulated silently until `/wh:close` caught them.

Research (ESAA paper, AgentSpec) showed that infrastructure enforcement
produces zero protocol violations, while prompt-based guidance is
unreliable. Scientific workflow systems (Galaxy, CWL, Nextflow) all
enforce provenance at the infrastructure level, not by asking the tool
to self-report.

### The Solution: Provenance-Completing MCP Tools

Every `add_*` MCP tool now accepts optional provenance parameters:

```python
add_finding(
    description="Ca freq scales with density",
    confidence=0.85,
    execution_kind="script",                  # auto-creates Execution
    used_entities="D-abc123,S-def456",        # auto-links inputs
    execution_description="cold exposure run"
)
```

When `execution_kind` is set, the tool atomically:
1. Creates the entity node (Finding, Hypothesis, etc.)
2. Creates an Execution activity node
3. Links entity → WAS_GENERATED_BY → Execution
4. Links Execution → USED → each input entity

One call. Full provenance chain. Backward compatible — without the
provenance params, tools work exactly as before.

### Performance (benchmarked 2026-04-02, Neo4j 5.x local)

```
Without provenance:    9 ms per call  (1 node, 1 JSON file)
With provenance:      21 ms per call  (2 nodes, 1 rel, 2 JSON files)
Overhead:            +12 ms           (~4 ms per additional USED link)
```

Provenance overhead is imperceptible compared to LLM inference latency
(2-10 seconds per turn). Full provenance is essentially free.

### Evidence Basis

- ESAA (2602.23193): zero protocol violations with schema enforcement
  across 135 events, 4 LLM providers
- AgentSpec (ICSE 2026): >90% unsafe execution prevention with runtime
  constraints, millisecond overhead
- Galaxy/CWL/Nextflow: all enforce provenance at runner level, not tool
  level. The tool does not choose to log — the infrastructure does it.
- LbMAS (2510.01285): blackboard/shared-ledger pattern validated,
  13-57% improvement over alternatives

---

## Appendix A: Flowcept Codebase Findings

Flowcept collapses all PROV-AGENT classes into a single `TaskObject` with
`subtype` field discrimination. No Neo4j backend (MongoDB + LMDB only).
Streaming architecture (Redis/Kafka) designed for HPC scale. Not usable
as a dependency for Wheeler.

Useful patterns to adopt conceptually:
- Decorator-based provenance capture (`@flowcept_task`)
- `used`/`generated` as the core provenance fields
- Content hashing for entity identity
- Buffer + batch write for performance

Not useful:
- Message broker infrastructure (overkill)
- LangChain-coupled LLM wrapper (wrong framework)
- MongoDB document storage (Wheeler uses Neo4j)

## Appendix B: Papers — Detailed Analysis

### PROV-AGENT (2508.02866)

Activity subclass hierarchy: Campaign → Workflow → Task → AgentTool →
AIModelInvocation. Entity subclass hierarchy: DataObject → DomainData,
Prompt, ResponseData, AIModel. All relationships are standard PROV.

Five query patterns: complete lineage, agent tool usage, hallucination
investigation, downstream impact, error propagation. Q3-Q5 directly
relevant to Wheeler's invalidation propagation design.

Key limitation: no epistemic provenance. Tracks what happened, not why
it was believed or how confident we are.

### LLM Agents for Workflow Provenance (2509.13978)

Dynamic Dataflow Schema: compact auto-maintained metadata summary injected
into prompts. Performance independent of data volume. Validated with
GPT-4 and Claude Opus scoring 0.97.

Three-part Context Manager: (a) recent buffer, (b) schema summary,
(c) NL guidelines. Maps to Wheeler's (a) graph_context, (b) schema,
(c) .plans/STATE.md + act prompts.

Self-provenance: agent's own actions recorded as provenance using same
schema. Validates our Execution-per-act design.

Key limitation: queries existing provenance, doesn't build knowledge
graphs. No model for collaborative human-AI knowledge construction.
