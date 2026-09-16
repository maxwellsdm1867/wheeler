# Node-linked skills and lesson capture

Status: first implementation built in the checkout on 2026-09-15. The design below includes later extensions; the implemented boundary is described here.

## Implemented first slice

- `capture_lesson` creates an immutable skill Document, source Document, capture Execution, and `APPLIES_TO` links to existing target nodes. It requires a problem statement and benchmark task. Optional harness IDs are linked as inputs, with their recorded hashes/paths snapshotted. Each version records `author_model`/`author_environment` separately from `tested_model`/`tested_environment`; claiming a recorded evaluation requires existing benchmark-result node IDs. Unknown author metadata stays explicitly unknown.
- Learned files live under `.notes/lessons/<name>/<capture-id>/`, outside native skill catalogs. `SKILL.md` holds the procedure, problem and benchmark case; `source.md` holds the source episode. `capture.json` enables retry/acceptance without reconstructing the original conversation. A completion receipt is published only after required storage and links succeed.
- `show_node`, `search_context`, `search_findings`, typed `query_*` listings and `graph_context` disclose bounded metadata for linked accepted skills, including skills attached to returned neighbors. Raw Cypher results also discover skills for actual project-scoped Neo4j Node/Path values. Scalar-only results explicitly report discovery as not checked; prose, nested metadata and lookalike node dictionaries cannot trigger it. Full instructions and benchmark text are not injected. Historical skill neighbors are omitted from ordinary expansion; only current accepted guidance is disclosed.
- `accept_skill(node_id)` activates a saved endorsed candidate. `capture_lesson(..., supersedes=<id>)` creates a revision. `retire_skill(node_id, reason)` removes guidance from discovery while retaining history and never reviving an older version.
- Wheeler Voice and Start forward natural remember/update/retire requests to `/wh:lesson`. The lesson act owns triage: enforceable fixes go to the implementation workflow, facts and simple preferences to notes, scientific claims to evidence work, and reusable workflows to node-linked skills. It resolves the artifact from context and asks a focused scope question only when ambiguous. Close prepares lesson candidates. Research acts compare linked descriptions to the current intent and read only relevant files.
- Failed or missing files/receipts are visible as unavailable, not silently reported as no guidance. Per-lineage locks serialize local concurrent captures and retirement. Cross-machine concurrent writers are not serialized by these local locks.

Read/write/revision/retirement and partial-write recovery are tested with isolated graph fixtures; a separate opt-in Neo4j test exercises actual queries and persistence. A SQLite fixture checks that a saved stable-ID join avoids duplicate-basename contamination. These establish implementation behavior, not a statistical benchmark of autonomous agent adherence.

An independent synthetic decision exercise matched the expected choices in 12 of 12 cases, including same-resource skips, selection among competing skills, and lesson triage. This was two fresh-context agents each receiving six cases, not twelve independent trials or completed research tasks. Exact evaluator model IDs were unavailable and recorded as unknown. The [evaluation record](../evals/node_linked_skills/README.md) preserves inputs, outputs, expected decisions and instruction snapshots.

A subsequent [executed-task probe](../evals/node_linked_skills/executed-task-probe.md) connects real isolated Neo4j discovery to fresh-agent skill selection and read-only SQLite execution. Eight tasks passed: six original cases covering competing skills on the same node, irrelevant operations, neighbor discovery and a different database with the same filename, plus two changed-data follow-ups. The audit preserves actual skill reads and query results. Changed-data follow-ups distinguish executing a procedure from copying its benchmark example. Seed selection is fixed, so these checks do not evaluate search ranking or voice routing.

The tool records a benchmark task; it does not execute arbitrary benchmark prose. The lesson act can route a small authorized validation through an execution workflow and must record an unrun benchmark honestly. Automated benchmark reruns, arbitrary SQL/shell interception, raw-Cypher scalar identity inference, global preference catalogs, and native dynamic skill installation remain outside this slice. Existing script staleness machinery can follow the harness provenance links when invoked; no new background watcher is installed.

To rerun the isolated tests:

```bash
.venv/bin/pytest -q tests/test_lesson_flow.py tests/test_lesson_recovery.py tests/test_skill_discovery.py tests/test_skill_trigger_boundaries.py tests/test_skill_raw_results.py
# Only with a separate test Neo4j instance, never the research server:
WHEELER_LESSON_TEST_URI=bolt://127.0.0.1:17687 .venv/bin/pytest -q tests/test_lesson_live.py
```

The remaining sections document the intended behavior and extension points.

## Product behavior

Encountering a Wheeler node automatically reveals its linked procedures. The agent reads their applicability summaries, opens relevant procedures, and decides whether to apply them to the current task. The scientist does not have to remember a command, a skill name, or the earlier correction.

This works when the node is returned directly or encountered as a neighbor during graph exploration. A database-query correction can therefore improve an unrelated future task that reaches the same database node. Artifact access through a tool is an additional discovery entry point; it is not the only trigger.

**Discovery is automatic; applicability is reasoned about.** Being adjacent to a procedure does not require executing it. It makes the procedure visible at the point where it might help.

## Two connected loops

```text
Use:
query or explore graph → encounter node → see linked procedure summaries
                      → read applicable procedure → apply or skip

Learn:
correction or useful discovery → suggest/capture lesson → identify target nodes
                              → save source and procedure → link for future discovery
```

These loops connect through explicit graph links. A stored lesson without target links cannot support reliable discovery. A surfaced procedure without its source cannot explain why it should be trusted.

## Use the skill format for the reusable procedure

The scientist's further clarification selects a skill as the procedure artifact. Use a normal skill folder with `SKILL.md` and optional references or executable helpers. The graph supplies node-based discovery and provenance; the skill supplies progressive disclosure and reusable instructions.

The standard skill interaction starts with name and description, loads the body when selected, and exposes optional supporting resources. Implicit selection can match the task to the description. [Official skill documentation](https://learn.chatgpt.com/docs/build-skills)

Wheeler adds a discovery step before that interaction:

1. Encounter a node and return linked skill metadata: name, description, exact version/read location, and matched node ID.
2. Compare the user's intent and planned operation to the description.
3. Read the full `SKILL.md` when it plausibly applies. Reading can clarify applicability; it need not commit the agent to following an unsuitable workflow.
4. Load only relevant references or use the appropriate helpers while doing the task.

For example, a database node exposes “Querying cell types in this database,” with a description about annotation fields, ontology aliases, and joins. A cell-type selection task merits reading it. A database size check may not. These are illustrative capabilities, not claims about the current database schema.

A graph link does not itself register a skill with a host's native skill catalog. Wheeler must supply a working path or content-fetch operation and teach its acts to read applicable linked skills. The initial design can use skill files through normal file/content tools; a host-native installation adapter is optional. Do not depend on globally installing every learned skill or placing every description in every session's initial prompt.

The lesson explains what changed and why. Its reusable output is the skill, or a revision to an existing skill. Several lessons can improve one coherent database skill; avoid creating a new skill for every correction. Keep incidental source evidence in provenance rather than growing the skill into a conversation archive.

## Database example

A scientist corrects a query that joined recordings by filename. Names are not unique, so the corrected query uses a stable recording ID and checks join cardinality.

First fix the query helper, database view, schema constraint, or other harness where practical. A database can enforce a contract just as application code can. Preserve residual procedural knowledge when full enforcement is unavailable or would require a larger migration.

Capture a procedure attached to the database node:

> **Joining recording records.** Applies when selecting or joining recordings. Filenames are not unique; use the stable recording key and check join cardinality. Source: the corrected query and the scientist's explanation.

Later, a different task retrieves a dataset connected to that database. If the database appears in the returned graph neighborhood, Wheeler also returns its procedure summary. The agent sees that it is relevant, reads the full procedure, and follows it. If the task only concerns the database's ownership, the agent can skip the joining procedure.

The table/field names must come from the actual database. Duplicate basenames may be legitimate, so the lesson must not invent an unsupported global uniqueness requirement.

## Graph representation

The concepts are:

- **Target node:** the database, dataset, script, method, or other context to which the procedure applies.
- **Lesson:** what was learned, the corrected behavior, and its applicability.
- **Procedure artifact:** the readable instructions, examples, exceptions, and checks. A short lesson may contain its own procedure; do not require duplicate prose artifacts without a reason.
- **Source incident:** the correction, relevant query/result, or faithful conversation excerpt.
- **Capture Execution:** how the source was turned into the lesson/procedure.

Conceptual links:

```text
Procedure ──APPLIES_TO──► Target node
Procedure ──WAS_GENERATED_BY──► Capture Execution ──USED──► Source incident
```

`APPLIES_TO` is the explicit relation added by this implementation. Skills use Document nodes with dedicated skill metadata; source episodes are Documents and captures are Executions. An untyped `RELEVANT_TO` edge by itself is too broad to mean “consider using this procedure.”

Store at least a title, short applicability summary, actionable body or artifact path, accepted/candidate/superseded/retracted state, version, source IDs, and target IDs. Add operation and resource-version conditions when relevant. Explicit instructions and inferred suggestions must retain different authority. Do not use research tier or recall frequency as a substitute for that distinction.

## Automatic discovery in query results

Introduce a shared result-enrichment stage for supported node-bearing reads. Given the nodes already selected for a response, fetch their active procedure links and append compact procedure references. This is an identity-based graph lookup; the new question does not need to resemble the original mistake.

An illustrative response addition:

```json
{
  "procedures": [{
    "id": "procedure-recording-joins",
    "target_ids": ["database-recordings"],
    "title": "Joining recording records",
    "applies_when": "Selecting or joining recording records",
    "summary": "Use the stable recording key; filenames are not unique.",
    "version": 2,
    "status": "accepted",
    "read_ref": "procedure-recording-joins"
  }],
  "procedures_status": "complete"
}
```

These illustrative IDs and fields describe a proposed contract, not current APIs.

**The one-hop detail matters.** Suppose search returns seed A and its neighbor B. A procedure P attached to B may be two edges from A. Run procedure enrichment over both A and B after ordinary neighborhood selection. P should not disappear because ordinary semantic expansion stops at one hop. This is a bounded applicability lookup, not another unrestricted neighborhood expansion.

Deduplicate shared procedures while preserving all matched target IDs. Return brief summaries initially; load full bodies only when useful. For many matches, return an explicit count and continuation/reference rather than silently truncating procedures and claiming complete coverage. Never let ordinary relevance ranking hide the existence of directly attached accepted procedures.

Do not recursively follow procedures into more procedures indefinitely. Enrich the identified result-node set once; inspect sources only when the agent needs to verify a procedure.

If the lookup fails, report that procedures could not be checked. “No linked procedures” and “lookup unavailable” are different states. Preserve ordinary node reads where possible, including the existing filesystem-backed read path.

## Agent behavior after discovery

The working acts should teach one consistent behavior:

1. Notice the procedure summaries attached to returned nodes.
2. Compare their applicability conditions with the current operation.
3. Read full relevant procedures before relying on them. A summary is a discovery aid, not necessarily sufficient execution detail.
4. Apply the relevant steps, or skip procedures whose conditions do not match.
5. If a procedure fails or is outdated, fix the immediate task and propose a revision with evidence.

The scientist should not be interrupted just to approve reading or applying an already accepted, applicable procedure. Current explicit instructions still govern. Conflicting accepted procedures need resolution rather than choosing whichever scored highest in search.

Delivery, reading, application, and verification are separate events. A tool can guarantee that it returned a procedure reference; model behavior determines whether the agent uses it correctly. Mechanical checks should enforce what can be enforced. A research Execution can link the exact procedure version it actually used, without treating every surfaced procedure as a used input.

## Three routes into the same lesson-writing operation

### Natural-language routing through Wheeler Voice and Start

Include the general Wheeler router, including Wheeler Voice, in the first implementation. “Wheeler, remember this,” “remember how we fixed that query,” and “update what you learned about this database” should reach the lesson workflow without requiring the scientist to name a command.

Preserve the existing router's responsibility: select an installed act and forward the original request intact. The lesson act owns resolving “this,” inspecting target nodes and linked skills, distinguishing a preference from reusable procedure, choosing capture versus revision, and saving provenance. The router should not perform graph writes, author the skill, or invent its own benchmarking workflow.

Use intent to distinguish nearby routes:

- Remember a reusable correction/procedure or revise learned guidance: proposed `wh:lesson`.
- Save an ordinary research observation: existing `wh:note`, when that is clearly the requested outcome.
- Recall what Wheeler already remembers: existing `wh:ask`.
- Discuss what “Wheeler, remember this” would do: answer the design question without invoking capture.

Update the canonical Wheeler Voice source and generated/distributed copies through the repository's build process, and update `wh:start` routing consistently when `wh:lesson` is implemented. Do not advertise a working destination before its act and tool support exist. The current conversation records this routing requirement; it does not install the new route.

Routing cases should cover direct speech, references to the just-corrected operation, updating an existing skill, ordinary notes, recall questions, negation, and quoted/hypothetical commands. The lesson act should reuse available conversation context and ask only for materially missing scope or target information.

### Suggest during the work

When a correction reveals a reusable procedure, Wheeler proposes the actual lesson and its target:

> “The recording key issue applies to this database's joins. I can attach the corrected query procedure to that database so future work discovers it.”

Present the concrete target and scope, not a vague request to save a memory. If the scientist already explicitly asked to remember the correction, capture it without asking the same authorization again. Inferred generalizations remain candidates until endorsed. Do not generalize a one-off instruction into a permanent rule.

### An explicit lesson act

A proposed `/wh:lesson` accepts ordinary requests such as “save what we learned from that query.” It assembles the correction, the reusable steps, the source, and the node links. It should infer obvious targets from the work already performed and ask only when the choice or scope is materially ambiguous.

The act is a convenient entry point. The user does not need to invoke it for discovery, and does not need to remember it to benefit from suggestions or the close sweep.

### Sweep at session close

Extend close to inspect the available session evidence for corrected mistakes, repeated steering, effective procedures, and changes to earlier procedures. It should prepare concrete uncaptured candidates and suggested links itself, then present only unresolved judgments. Do not make “anything you want to remember?” the primary capture mechanism; that transfers the remembering burden back to the scientist.

Reuse existing accepted/candidate entries rather than duplicating a lesson suggested earlier. Skip rejected candidates unless new evidence changes them. If earlier conversation is unavailable after compaction, say what evidence is missing; do not invent the incident.

## Robust lesson writes

All three entry points use one validated capture operation:

1. Resolve actual target node IDs and inspect existing procedures for those targets.
2. Preserve a minimal faithful source artifact, or cite an existing source. Label reconstructed summaries as summaries.
3. Create or revise the lesson/procedure with explicit scope, source, and authority.
4. Persist the applicability links and the derivation provenance through Wheeler's mutation dispatch.
5. Verify the resulting links and readable artifact before reporting capture complete.

Use a stable capture identity derived from the source incident, target, and procedure identity so close can recognize work already captured. Handle compatible additional evidence, changed procedure versions, and conflicting proposals distinctly; similarity alone should not overwrite an accepted procedure.

A partial write must not leave an apparently active procedure whose applicability or source links were never persisted. Use an explicit incomplete state or an equivalent staged operation, graph transactions where appropriate, and receipts/repair for cross-store persistence. Activate only once required pieces exist. Retrying must not create a duplicate active version.

Retain superseded versions and why they changed. Link the harness fix when one exists, and record when that fix makes an older procedure redundant. Preferences, procedural revisions, and scientific invalidation have different downstream effects.

## Concrete Wheeler seams

`expand_search_results` already returns direct seeds and one-hop neighbors, plus deeper provenance. It currently gives ResearchNotes and Documents primarily title summaries and has no explicit procedure section. Add enrichment over the returned node set. [Retrieval](../wheeler/search/retrieval.py)

`show_node` currently reads full node JSON from the filesystem without querying neighbors. It needs the same procedure-discovery contract, with a visible fallback when graph lookup is unavailable. Typed listing results and graph-context results should use the shared enrichment path when they expose identifiable nodes. [Core tools](../wheeler/mcp_core.py)

The current close act asks the scientist to surface missing conversational artifacts. Extend this to agent-prepared lesson candidates and route them through the same capture operation as `/wh:lesson`. [Close act](../wheeler/_data/commands/close.md)

Wheeler's packaged acts are cached, MCP-served workflow definitions. A graph-linked procedure document does not need to be dynamically installed as a native host skill to be read and used. Keep discovery and full-content retrieval host-independent; the lesson act supplies capture behavior. [Act reader](../wheeler/acts.py)

Raw Cypher results containing only counts or arbitrary scalar columns do not reliably identify encountered nodes. Do not guess identities from arbitrary strings. Define supported node-bearing response shapes or request explicit node IDs before claiming automatic enrichment for raw queries. Likewise, a database not represented in the graph requires a stable registered resource descriptor before it can carry links.

## Resource identity and additional access triggers

Use stable node IDs, with project-qualified file locators or credential-free database aliases. A content hash or schema version is version information, not the entire resource identity. Identically named databases on different servers must remain distinct. Explicit aliases can map to the same logical resource.

Database-tool wrappers and verified pre-tool hooks can later resolve accessed resources into the same node-discovery mechanism. They extend coverage to direct resource access that bypasses graph exploration. They are not a prerequisite for proving the initial Wheeler-session interaction.

If guidance is delivered after a query has already been drafted, let the agent revise it before execution. Avoid recursively requiring a procedure to run the graph lookup that discovers that same procedure. A small tested lookup is the bootstrap path. Uninstrumented shell/database access remains outside the automatic discovery guarantee.

## Acceptance tests

The first slice should prove both loops together:

1. Capture a corrected database-query lesson and its target link through the lesson operation.
2. Start a fresh session with a different research question, with no reference to the earlier correction or skill name.
3. Return the database directly and verify its procedure summary appears automatically.
4. Return a dataset whose expanded neighborhood includes the database; verify the database procedure still appears despite the one-hop search boundary.
5. Verify that the agent reads and applies the procedure for a matching join, and reasonably skips it for an unrelated operation on the same database.
6. Run close after an inline capture and verify it does not duplicate the lesson. Run close with an uncaptured correction and verify it proposes the concrete lesson and links without a reminder from the scientist.
7. Simulate partial persistence and retry; verify no falsely active or duplicate procedure, and repairable provenance/link state.
8. Revise or retract a procedure; active discovery must show the current accepted version while history remains available.
9. Verify that another same-named database does not inherit the procedure, and an explicitly mapped alias does.
10. Verify lookup-unavailable and budget-overflow responses remain distinguishable from absence of procedures.

Structural tests establish reliable discovery and persistence. Fresh-agent replay establishes applicability judgment and reduced recurrence. Measure those separately rather than claiming that returning a skill reference proves the mistake cannot happen again.

## Updating and benchmarking the skill

Every version must distinguish the model/environment that authored it from those used to evaluate it. Use exact model identifiers when exposed by the host, with host/runtime/location context and referenced result artifacts. Record unknown values honestly. The recorded evaluation is specific to that version, model and environment; do not imply validation on another model. Discovery exposes only the short author/test model identifiers; detailed environments and result evidence are read with the selected skill.

Benchmark automation is a later phase, as requested by the scientist. The first slice is natural-language capture/revision, node linkage, progressive discovery, and session-close capture. Preserve exact skill versions and source evidence from the start so later benchmarks have reproducible inputs. Routine implementation checks still belong in the first slice; an automatic agent benchmark is not required every time the user says “remember this.”

Capture should inspect existing skills attached to the target before creating another. A new correction can revise the description (selection problem), the body (procedure problem), a reference (missing domain detail), or a helper (enforceable logic). Preserve the earlier skill version and link the revision to the correction that motivated it.

Benchmark both selection and task completion against an isolated database fixture with known expected results. The initial case set should include:

| Case | What it establishes |
|---|---|
| Original corrected query | The demonstrated mistake does not recur |
| Different cell type or differently worded request | The skill transfers beyond the correction's wording |
| Same database, unrelated operation | Discovery does not cause inappropriate application |
| Dataset lookup that returns the database as a neighbor | Graph-triggered discovery works without a direct database lookup |
| Different database with similar names | Skill scope remains correct |
| Old cases plus a newly corrected case | A skill revision fixes the new problem without losing prior behavior |

Compare a baseline without the linked skill, the current version, and the candidate revision. Start each replay in fresh context; keep the model, task, fixture, tools, and evaluation budget comparable. Include withheld task variations and repeat behavioral trials to avoid mistaking one favorable model response for reliable improvement.

Record skill-description delivery, full-skill reads, application/skip decisions, executed queries, correct result sets, repeated errors, and token/latency cost. Use deterministic fixture checks for query results where possible; loading the skill is not itself a successful result. Source inspection and frontmatter validation are separate from this benchmark.

Save benchmark cases and results as Wheeler artifacts. The evaluation Execution should reference the exact skill bundle version, including relevant references/helpers, database fixture, task cases, and evaluation settings. This makes an improvement claim traceable. A proposed revision's acceptance and its benchmark outcome are separate recorded facts; an LLM-generated success score is not scientist endorsement.

## Repository comparison

Borrow Mnemosyne's current-version/history discipline and Hindsight's separation of explicit guidance from inferred observations. Wheeler's graph provides the attachment point for node-triggered discovery and the provenance explaining each lesson. The distinctive work is the automatic procedure section on graph results, the applicability behavior, and the unified lesson-capture loop. See the [comparison](conversational-memory-research.md) and its source audits.
