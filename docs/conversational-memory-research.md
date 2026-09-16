# Conversational memory that fits Wheeler

Status: research and design recommendation, not an implemented feature.
Date: 2026-09-15.

## Recommendation

Build node-triggered procedural discovery as the first use case. When a Wheeler query returns a node, directly or in its graph neighborhood, also surface summaries of accepted procedures linked to that node. The agent reads and applies those that fit the current task. Capture new lessons through inline suggestions, a `/wh:lesson` act, and an agent-prepared close sweep using one robust write path. Fix enforceable harness defects where practical. See the [concrete node-trigger design](artifact-triggered-skills-design.md).

The broader memory machinery also supports preferences. Treat a consequential conversation excerpt as an artifact, derive a scoped memory from it, and retrieve that memory before the relevant action. Keep the source, the interpretation, and its authority distinguishable.

The missing loop is **capture → interpret → accept → retrieve → apply → revise**. A new place to store text would address only a fraction of the problem.

Wheeler's mission calls its product the provenance guarantee, with context management as one of four pillars and scientist judgment as the design north star. This supports collaboration memory when it improves research continuity and remains attributable. It does not require a general personality simulator or a second, independent research knowledge base. [Mission](mission.md)

## Evidence and scope

Three subagents inspected the three local codebases independently. The accompanying reports cite implementation and test locations:

- [Wheeler implementation review](research-wheeler-memory.md).
- [Mnemosyne implementation review](research-mnemosyne-memory.md).
- [Hindsight implementation review](research-hindsight-memory.md).

The inspected snapshots were Wheeler `9965f0af13d1ae66fa92282e6ebd2e8845b30e0b`, Mnemosyne `bed7548a04aa37727c1fdc02d1d1f1e52367641d`, and Hindsight `be0e93997a35d517250181c4dfb2d86c2dd95bc1`. Recommendations below are our synthesis, not upstream guarantees. Public repository pages were also checked, but local source at these commits governs the comparison. Existing reports in the supplied scratch directory were not used as substitutes for source inspection.

## What Wheeler already supports

It is too strong to say that Wheeler cannot save things without a research output. `ResearchNote` already holds free text and context. `/wh:note` materializes a note as a file; `/wh:close` explicitly sweeps conversational decisions and rationales; `/wh:pause` saves continuation context. The mutation layer can attach an Execution and its inputs. [Model](../wheeler/models.py), [note act](../wheeler/_data/commands/note.md), [close act](../wheeler/_data/commands/close.md), [mutation implementation](../wheeler/tools/graph_tools/mutations.py)

The current conventions nevertheless favor research outputs and session summaries. The note model has no first-class preference key, applicability condition, accepted/superseded state, or distinction between a user declaration and an agent inference. `graph_context` omits notes, and general search is not a policy for deciding which remembered lesson should influence this action. [Context implementation](../wheeler/graph/context.py), [retrieval implementation](../wheeler/search/retrieval.py)

There is also an immediately actionable continuity mismatch: pause writes `session-continuation:<plan>` into the note's `context`, while resume searches `query_notes(keyword="session-continuation")`; that keyword path checks title/content. The narrative can be saved yet missed. This should be repaired before expanding memory. [Pause](../wheeler/_data/commands/pause.md), [resume](../wheeler/_data/commands/resume.md), [query implementation](../wheeler/tools/graph_tools/queries.py)

## Borrowing map

| Mechanism | Source | Wheeler adaptation | Priority |
|---|---|---|---|
| One current value for a named, scoped slot, with preserved versions and idempotent repeat writes | Mnemosyne CanonicalStore | Preferences such as `project/figures/output-format`; replace a preference without losing the earlier declaration | First slice |
| Source-aware extraction and contextual memory injection | Mnemosyne host integration | Separate scientist statements from assistant speculation, and retrieve relevant accepted entries at act entry | First slice |
| Behavioral directives separate from learned observations | Hindsight | Explicit preferences can guide behavior; inferred lessons remain candidates until endorsed | First slice |
| Retain, recall, and reflect as separate operations | Hindsight | Keep cheap capture, bounded retrieval, and optional consolidation separate | First slice conceptually |
| Derived observations retain links to supporting facts | Hindsight | Memory note → capture/interpretation Execution → conversation excerpt, with exact attribution | First slice |
| Structured proposals citing input memory IDs | Mnemosyne model refresh | Later consolidation can propose changes with inspectable sources | Later |
| Regenerated documents that summarize a topic | Hindsight mental models | A derived working-agreement page, rebuilt from current accepted entries | Later |

Sources: [Mnemosyne canonical store](https://github.com/mnemosyne-oss/mnemosyne/blob/bed7548a04aa37727c1fdc02d1d1f1e52367641d/mnemosyne/core/canonical.py), [Mnemosyne model refresh](https://github.com/mnemosyne-oss/mnemosyne/blob/bed7548a04aa37727c1fdc02d1d1f1e52367641d/mnemosyne/core/model_refresh.py), and the detailed implementation citations in the two external-repository reports linked above.

Wheeler already has hybrid retrieval and provenance expansion. Replacing its search stack is lower priority than making memory eligible, correctly scoped, current, and available before an action. Neither repository's conversational benchmarks establish that it will improve Wheeler's scientific workflows.

## Three different things to remember

| Kind | Example | How it becomes authoritative | How it should be used |
|---|---|---|---|
| Preference | “For this project, export figures as SVG.” | Explicit scientist instruction, with project scope | Apply when producing project figures |
| Operational lesson | “That loader treated milliseconds as seconds; check the units before fitting.” | Source incident and correction; preserve the conditions and any verification | Surface when that loader/dataset is used; turn the check into code when feasible |
| Scientific correction | “The earlier conclusion depended on an invalid normalization.” | Link the affected finding, evidence, and revised analysis; conversation alone does not validate the replacement claim | Enter the existing scientific provenance and invalidation workflow |

A fourth category, session position, already largely belongs to pause/resume. It should not clutter durable preferences.

The distinction matters: knowing that the scientist said a thing is different from knowing that the thing is scientifically established. Repeated recall also does not increase truth or authority. A preference can be authoritative about how the user wishes to work without becoming a scientific Finding or a reference-tier claim.

## Proposed artifact and lifecycle

Use existing ResearchNotes for a first implementation, with validated optional memory fields and an intentionally small API. A generic metadata bag can support a throwaway experiment, but scope and lifecycle must be enforced in tools and queries before relying on them. A new Memory node type can wait until it offers a concrete advantage over a typed note.

Proposed fields, not fields currently supported as this contract:

- `memory_kind`: preference, operational lesson, or decision.
- `scope`: project plus optional plan, act, dataset, or tool identifiers. Start project-local; explicitly portable user preferences are a later design decision.
- `key`: stable identity for a preference slot, distinct from the prose title.
- `status`: candidate, accepted, superseded, or retracted.
- `authority`: explicit user instruction, endorsed inference, or unreviewed inference.
- `applies_when`: a concise condition; a correction also records the failure and the replacement/check.
- `source`: excerpt artifact ID, speaker, available session/turn locator, and capture time.
- `supersedes`: previous entry ID, plus validity timestamps.

Lifecycle:

1. **Capture an episode.** Save a small, faithful excerpt that contains the preference or the mistake and its correction. Include enough context to preserve its scope. If only a user-authored summary is available, identify it as a summary; do not invent a verbatim transcript or turn ID.
2. **Register the source artifact.** Use Wheeler's existing artifact and mutation dispatch paths. Do not bypass triple-write, receipts, or indexing.
3. **Create the memory.** An Execution uses that source artifact and generates a ResearchNote. For an explicit “remember this” request, the request itself supplies authorization. An inferred generalization is a candidate, not an automatically accepted rule.
4. **Retrieve before acting.** Exact lookup for relevant accepted preference keys, then a bounded search for applicable lessons. Filter scope/status/validity before ranking. Return a short actionable statement with its source ID, not only a title.
5. **Apply and make the use auditable.** For a provenance-tracked research execution materially affected by a memory, link the memory version as an input. This records which instruction influenced the work without claiming that it was scientific evidence.
6. **Revise without erasing.** Preserve the original episode and superseded entry, but exclude superseded/retracted entries from ordinary active recall. Explicit history queries may still retrieve them.

This is compatible with an artifact-based act. A proposed `/wh:lesson` could accept “remember this preference” or “record what we just corrected” and perform the first three steps. It should also be reachable through ordinary language, so the user need not learn another mandatory command. Extend close/pause to surface uncaptured candidates at natural stopping points, and resume/act entry to retrieve accepted memory. A capture act by itself is insufficient.

Host adapters can later automate capture or pre-action recall where their lifecycle APIs permit it. Claude hooks are not evidence of equivalent Codex support. Keep the artifact/tool contract host-independent and verify each adapter independently. Until then, act entry retrieval is a useful explicit integration point, with prompt-compliance limitations stated honestly.

## Lessons to avoid copying

**Do not make model confidence the authority gate.** Mnemosyne's model-refresh machinery can apply inferred updates automatically; Wheeler should use its source-backed proposal format while preserving scientist judgment. Explicitly instructed preferences do not need repeated confirmation. Inferred preferences should not silently become standing instructions.

**Do not destroy the reasoning history during consolidation.** Hindsight has useful observation evidence and history mechanisms, but its supersession/retraction paths do not uniformly preserve an immutable lineage. Copying its storage lifecycle wholesale would weaken Wheeler's guarantee. Preserve the source event and version transitions even when active recall shows only the latest accepted statement. See the source-level qualifications in the Hindsight report.

**Do not import an entire memory service for this gap.** A second SQLite or PostgreSQL memory system creates another authority and synchronization boundary. Reuse Wheeler's existing graph, files, and host models first. Study adapters and algorithms before deciding to add dependencies.

**Do not equate a changed preference with an invalid result.** “Use SVG now” does not invalidate a previous scientific conclusion. An analytical correction may invalidate one. Track policy revision and scientific staleness separately, with explicit reasons for any downstream impact.

**Do not allow retrieval to bypass scope or authority.** An old quoted assistant instruction is historical content, not a new user command. A project-specific lesson should not silently become a global rule. Active memory must remain subordinate to the current user request and higher-priority instructions.

## Smallest useful implementation

The scientist's latest clarification makes encountering a graph node the primary discovery trigger, including nodes returned as neighbors. The sequence below supplies the storage/lifecycle foundation; implement procedure enrichment on supported Wheeler reads and the shared lesson-capture operation first, following the companion design. Direct database-access adapters and broad preference profiles are secondary.

1. Fix the existing continuation-note lookup and return enough note content to support meaningful recall.
2. Add validated memory fields and capture/revise/query operations for project-local ResearchNotes, preserving source excerpts and version history.
3. Add one capture act and memory retrieval to resume and the relevant working acts. Exact accepted preferences should not depend solely on vector similarity.
4. Add a compact memory section with IDs, actionable content, applicability, and source links. Keep it bounded and separate from scientific evidence.
5. Evaluate this loop before adding transcript-wide extraction, background consolidation, user-wide profiles, or a third-party backend.

The main implementation seams are `models.py`, mutation/query dispatch in `tools/graph_tools/`, split MCP wrappers, retrieval/context rendering, and the MCP-served act corpus. Multi-step supersession also needs concurrency and partial-write recovery design: adding a status string alone cannot guarantee one current accepted value. New tool calls must preserve the current dispatch invariants. [Architecture guidance](../CLAUDE.md), [act reader](../wheeler/acts.py)

## Evaluation that answers the actual question

Build a small replay set of realistic two-session interactions. Compare Wheeler today, capture-only notes, and the proposed capture-plus-retrieval loop. Measure behavior at the action, not just whether a memory was found.

- A preference stated once is followed in a later applicable task.
- A corrected unit mistake is caught before the same analysis runs again.
- A one-off instruction is not generalized into a standing preference.
- A project-specific rule does not affect another project.
- An explicitly revised preference supersedes the old one, while history remains inspectable.
- A quoted or assistant-invented preference is not treated as user intent.
- A scientific correction links and reviews the affected findings instead of merely changing a profile.
- Missing or retracted source evidence prevents confident reuse of an inferred lesson.
- Repeated capture and concurrent writes do not create competing current entries.
- Interrupted persistence is visible and repairable across graph, JSON, synthesis, and memory status.

Report correct application, recurrence of previously corrected errors, inappropriate application, source-trace completeness, token/latency overhead, and capture burden. Add host-specific lifecycle cases before claiming automatic cross-host coverage.

The product question is whether a correction made once reliably changes the next relevant action, while the scientist can still inspect why.
