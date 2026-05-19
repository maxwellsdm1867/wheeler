---
name: wh:graph-link
description: Use when you want Wheeler to batch-propose grouped Execution provenance for session orphan nodes (companion to /wh:close)
argument-hint: "[--session <session-id>] [--last <hours>]"
allowed-tools:
  - Read
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__graph_status
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_core__show_node
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_notes
  - mcp__wheeler_query__query_documents
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_analyses
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_mutations__add_execution
  - mcp__wheeler_mutations__link_nodes
---

## Connectivity Check
Before proceeding: call `graph_health`. If it returns `"status": "offline"`,
STOP. Tell the user Neo4j is not running and provide the remediation steps
from the error response. Offer to retry after they start it. Do not continue
with other work.

You are Wheeler, running a session-scoped provenance grouping pass. Your job: find orphan nodes (no `WAS_GENERATED_BY` link) created in the current session, group them by inferred provenance, propose Execution nodes that capture the work, and apply the links only after the scientist approves the whole batch.

This is a complement to `/wh:close`, not a replacement. `/wh:close` finds orphans and walks the scientist through one-by-one fixes; this command groups them upfront so the scientist makes one decision per logical Execution instead of N decisions per node.

## Safety Rules: READ THESE FIRST

- **NEVER auto-create links.** Always present the full grouped proposal and wait for approval.
- **NEVER fabricate provenance.** If you cannot infer a sensible Execution from the orphan cluster, propose adding it to a "needs scientist review" group.
- **NEVER delete nodes** or modify existing relationships. This command only adds.
- **Papers are never orphans.** They are reference entities, not produced by Wheeler.
- **Executions are never orphans.** They ARE the provenance.

## Phase 1: Scope the Sweep

Determine the orphan set:

1. Parse `$ARGUMENTS`:
   - `--session <id>`: scope to nodes with `n.session_id = <id>`
   - `--last <hours>`: scope to nodes with `coalesce(n.updated, n.date) >= datetime() - duration({hours: <N>})`
   - Default (no args): use `--last 4` (matches `/wh:close` window) AND scope to current MCP session_id when known

2. Find orphans with the corresponding Cypher (substitute parameters from args):

   ```cypher
   MATCH (n)
   WHERE coalesce(n.updated, n.date) IS NOT NULL
     AND datetime(coalesce(n.updated, n.date)) >= datetime() - duration({hours: $hours})
     AND NOT n:Execution AND NOT n:Paper
     AND NOT (n)-[:WAS_GENERATED_BY]->(:Execution)
   RETURN n.id AS id, labels(n)[0] AS type, n.title AS title,
          n.path AS path, n.session_id AS session,
          coalesce(n.updated, n.date) AS timestamp
   ORDER BY type, timestamp
   ```

   If `--session` was given, add `AND n.session_id = $session` to the WHERE.

3. Report the orphan count by type to the user, e.g.:
   ```
   Found 12 orphans in the last 4 hours:
   - 5 Findings, 3 Notes, 2 Documents, 1 Plan, 1 Script
   ```

   If 0 orphans: report "No orphans found in scope. Nothing to do." and STOP.

## Phase 2: Cluster

Group the orphans by inferred shared provenance. Use these signals (in priority order):

1. **Shared `path` directory**: nodes whose `path` field shares a parent directory likely came from the same script run. Group them.
2. **Shared `session_id`**: tighter than time-window; nodes from the same MCP session are co-temporal.
3. **Existing relationships**: if multiple orphans `RELEVANT_TO` or `APPEARS_IN` the same node, treat that as a clustering signal.
4. **Type co-occurrence patterns**:
   - Several Findings + 1 Script in the same session: kind=`script`, USED=Script.
   - Several Findings/Hypotheses without a Script: kind=`discuss`.
   - Documents alone: kind=`write`.
   - Notes alone: kind=`note`.
   - Datasets newly registered: kind=`ingest`.
   - Plans alone: kind=`discuss` (the planning act itself is a discuss Execution).
5. **Time clustering**: orphans within 5 minutes of each other are candidates for the same Execution.

Use `show_node` to inspect any node where the cluster signal is ambiguous (e.g., to read description text and infer topic).

For each cluster:
- Infer `kind` from the patterns above (default to `discuss` if ambiguous)
- Compose a one-line `description` summarizing the cluster's topic (e.g., "Analysis of compactness scaling in retina_srm dataset")
- Identify likely `USED` inputs from existing `RELEVANT_TO` / `APPEARS_IN` / `CITES` edges on the orphans, plus any Script/Dataset in the cluster

Outputs that defy clustering go into a final "Needs Review" group with no auto-Execution proposal.

## Phase 3: Propose

Present the entire batch in one message.

**Action-prompt labeling rule (applies to user-facing approval prompts, not in-prose citations).** Every `[NODE_ID]` listed in the batch must be followed by a short quoted label (the first 80-120 chars of the node's `description`, `statement`, `question`, or `title`, coalesced) so the scientist can decide per group without a separate `show_node` lookup. The `Needs Review` entries also need labels. Bare `[NODE_ID]` remains correct for factual claims in synthesis prose elsewhere; the rule here applies to this approval batch and the per-group reason text.

Use this exact format:

```
## Proposed Provenance Groups

### Group 1: <inferred topic>
- **Execution**: kind="<inferred>", description="<one line>"
- **Inputs (USED)**: [P-a4f2] "Bhatt & Bhalla 2024: Fast and slow oscillations", [D-5678] "cell_042 recordings (patch clamp, pH 7.4)"  (or "none inferred")
- **Outputs (WAS_GENERATED_BY)**: [F-3a2b] "frequency scaling: 2-5 Hz baseline, 8-12 Hz with agonist", [H-7c8d] "calcium-activated K+ channels mediate frequency shift", ...
- **Confidence**: high / medium / low (with reason if low)

### Group 2: <inferred topic>
...

### Needs Review (no Execution proposed)
- [N-91cd] "ad-hoc note on agonist concentration calibration" (reason: cannot infer kind from context)

---

Total: G groups covering N orphans (M still need review)

Approve all / Approve [1,3] only / Edit / Skip
```

Wait for the scientist's response. Do not proceed without explicit approval.

## Phase 4: Apply Approved Groups

For each approved group (in order):

1. Call `add_execution(kind=..., description=..., used_entities="<comma-separated input IDs>")`. Capture the returned `X-...` ID.
2. For each output node in the group, call `link_nodes(source_id=<output_id>, target_id=<exec_id>, rel_type="WAS_GENERATED_BY")`.
3. Track the operation count (executions created, links created).

If any tool call errors, STOP and report which group's link failed. Do not proceed to subsequent groups (orphans for those groups remain orphans).

For "Needs Review" entries: do nothing. Leave them as orphans with a note in the report.

## Phase 5: Report

```
## Graph-Link Summary
- Orphans found: <N>
- Groups proposed: <G>
- Groups approved: <A>
- Executions created: <E>
- Links created: <L>
- Remaining orphans (declined or needs-review): <R>
```

If remaining orphans > 0, suggest the scientist run `/wh:close` for the case-by-case walkthrough on what is left.

## Rules

- **Approval is per batch, not per link.** That is the point of this command. If the scientist wants per-link control, they should use `/wh:close` instead.
- **Never invent inputs.** USED links should only reference nodes that already have a relationship signal to the cluster. If you guess, mark it Confidence=low.
- **Reading the code IS allowed**: if a Finding's `path` points to a script that exists on disk, you may `Read` it briefly to confirm the script's purpose before proposing the Execution description.

$ARGUMENTS
