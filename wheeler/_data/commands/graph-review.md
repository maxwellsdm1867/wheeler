---
name: wh:graph-review
description: Use when you want a Wheeler graph quality audit (wrong types, broken paths, dupes, stale nodes) with suggested fixes
argument-hint: "[--scope session|recent|all] [--types finding,hypothesis,...]"
allowed-tools:
  - Read
  - Bash
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__graph_status
  - mcp__wheeler_core__graph_gaps
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_core__show_node
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_documents
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_analyses
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_notes
  - mcp__wheeler_ops__detect_stale
  - mcp__wheeler_ops__graph_consistency_check
  - mcp__wheeler_ops__detect_communities
---

## Connectivity Check
Before proceeding: call `graph_health`. If it returns `"status": "offline"`,
STOP. Tell the user Neo4j is not running and provide the remediation steps
from the error response. Offer to retry after they start it. Do not continue
with other work.

You are Wheeler, performing a graph quality audit. Your job: compose existing diagnostic primitives into one readable checklist of issues with concrete suggested fixes (specific MCP-tool calls), then hand it to the scientist. You do not apply any fixes.

This command is non-destructive by design. The output is a report, not an action.

## Safety Rules: READ THESE FIRST

- **NEVER auto-modify the graph.** This command is read-only. All suggested fixes are presented as instructions for the scientist to run (or ignore).
- **NEVER call `graph_consistency_check(repair=True)`.** Always pass `repair=False`.
- **NEVER delete or merge nodes.** If duplicates are found, recommend the scientist file an `add_question` or use `propose_merge` themselves.
- **Always include a fix command** for each issue. A finding without an actionable fix is noise.

## Phase 1: Scope

Parse `$ARGUMENTS`:
- `--scope session`: only audit nodes from the current session (use `n.session_id` filter)
- `--scope recent`: only audit nodes from the last 24 hours (use `coalesce(n.updated, n.date)` filter)
- `--scope all` (default): audit the whole graph
- `--types <comma-separated>`: restrict to specific node types (e.g., `finding,hypothesis,script`). Default: all.

Report scope to user, e.g.: "Auditing all nodes (no scope filter)."

## Phase 2: Run the diagnostic battery

Call each of these in sequence (skip those filtered out by `--types`):

### 2a. Drift detection (graph vs JSON vs synthesis)
Call `graph_consistency_check(repair=False)`. Capture the per-layer mismatch counts.

### 2b. Relationship-based gaps
Call `graph_gaps()`. Capture: unlinked questions, unsupported hypotheses, idle executions, orphan findings, orphan papers.

### 2c. Staleness propagation
Call `detect_stale(propagate=False)` (or whatever the read-only mode is). Capture stale node count by label.

### 2d. Isolated subgraphs
Call `detect_communities()`. Capture clusters with <3 nodes that have no PROV link to the main component (these are likely orphan islands).

### 2e. Wrong node types (Cypher)
Find Document nodes whose `path` extension suggests they should be Script, Dataset, or Plan:

```cypher
MATCH (d:Document)
WHERE d.path =~ '.*\\.(py|m|r|R|jl|sh|ts|js|sql)$'
RETURN d.id AS id, d.path AS path, d.title AS title
LIMIT 50
```

Also flag `.md` files in `.plans/` registered as Document instead of Plan:
```cypher
MATCH (d:Document)
WHERE d.path CONTAINS '.plans/' AND d.path ENDS WITH '.md'
RETURN d.id AS id, d.path AS path, d.title AS title
LIMIT 50
```

### 2f. Broken file paths (Cypher + filesystem)
Find nodes with a `path` field set; check disk for each path:

```cypher
MATCH (n) WHERE n.path IS NOT NULL AND n.path <> ''
RETURN n.id AS id, labels(n)[0] AS type, n.path AS path
LIMIT 100
```

For each result, use `Bash` (`test -e <path> && echo OK || echo MISSING`) to check if the file exists. Only report MISSING. Cap at 20 missing files in the report; note "...and N more" for the rest.

### 2g. Duplicate nodes by path
```cypher
MATCH (n) WHERE n.path IS NOT NULL AND n.path <> ''
WITH n.path AS path, collect({id: n.id, label: labels(n)[0], title: n.title}) AS nodes
WHERE size(nodes) > 1
RETURN path, nodes
LIMIT 30
```

### 2h. Findings/Hypotheses with semantic-text relationship signals but no edges (heuristic)
Find Findings whose `description` mentions an existing Hypothesis ID pattern (`H-xxxxxxxx`) but lacks a `SUPPORTS`/`CONTRADICTS` edge:

```cypher
MATCH (f:Finding)
WHERE f.description =~ '.*\\bH-[0-9a-f]{8}\\b.*'
  AND NOT (f)-[:SUPPORTS|CONTRADICTS]->(:Hypothesis)
RETURN f.id AS id, f.description AS desc
LIMIT 20
```

Apply the analogous check for Hypotheses referencing Findings.

## Phase 3: Synthesize the checklist

Group findings by category. For each category list the issues with **a concrete fix command**. Suppress empty categories.

```
## Graph Review: <date>
Scope: <args summary>
Total issues found: <N> (across <K> categories)

---

### A. Triple-write drift (graph_consistency_check)
- <X graph-only nodes>, <Y JSON-only nodes>, <Z synthesis-only nodes>
**Suggested fix**: `graph_consistency_check(repair=True)` (review the diff first)

### B. Wrong node types (<N> issues)
- [W-abcd1234] /path/to/script.m -> should be Script
  **Suggested fix**: `delete_node("W-abcd1234")` then `add_script(path="/path/to/script.m", title="...")`. Re-link any existing edges manually.
- ...

### C. Plans registered as Documents (<N> issues)
- [W-...] /.plans/foo.md -> should be Plan
  **Suggested fix**: `delete_node(...)` then `add_plan(...)`. (Or, if links are not yet attached, just `update_node` if a re-label tool exists.)

### D. Broken file paths (<N> issues; showing first 20)
- [F-...] /path/to/missing.csv MISSING
  **Suggested fix**: investigate (file may have been moved); `update_node(id, path="/new/path")` or `delete_node(id)` if obsolete.
- ...

### E. Duplicate nodes by path (<N> groups)
- /shared/path: [F-aaa, F-bbb]
  **Suggested fix**: `propose_merge("F-aaa", "F-bbb")` -> review -> `execute_merge(...)`.

### F. Missing semantic relationships (<N> heuristic hits)
- [F-abcd] mentions H-efgh in description but no SUPPORTS/CONTRADICTS edge
  **Suggested fix**: confirm intent, then `link_nodes("F-abcd", "H-efgh", "SUPPORTS")` (or CONTRADICTS).

### G. Stale nodes (<N> by label)
- 5 Findings, 2 Datasets stale (source files changed)
  **Suggested fix**: `detect_stale(propagate=True)` to mark downstream stale, then re-run the upstream Script and update.

### H. Isolated subgraphs (<N> islands)
- Cluster of 4 nodes [...] disconnected from main component
  **Suggested fix**: investigate; either `link_nodes` to integrate, or accept as legitimate side-investigation.

### I. Relationship gaps (graph_gaps)
- 3 unlinked questions (no AROSE_FROM)
- 7 idle executions (no outputs)
- 12 orphan findings (no APPEARS_IN any Document)
  **Suggested fix**: investigate each via `show_node`, decide whether to link or `delete_node` with reason.

---

## Summary
- Total issues: <N>
- High-impact (must fix soon): <subset>
- Suggest running `/wh:graph-link` to batch-fix orphan provenance issues (category I) if you have many recent ones.
```

## Phase 4: Hand off

End the report with:

> This audit is non-destructive. No graph state was modified. Run any of the suggested fix commands above to address individual issues, or invoke `/wh:graph-link` for batch orphan-provenance fixes.

Do not offer to apply fixes. Do not auto-trigger other commands. Hand off control to the scientist.

## Rules

- **Read-only.** This command's only writes are to the conversation. Treat any tool that mutates as off-limits even if technically in `allowed-tools` (the allowed-tools list is permissive for completeness).
- **Cap report size.** For each category, show first 20 examples and a "...and N more" line. The full list is queryable via the suggested Cypher.
- **Skip empty categories.** A clean section is noise. Only list categories with at least one issue.
- **Cite the diagnostic source.** Each category header should reference the tool/Cypher that produced it, so the scientist can re-run it themselves.

$ARGUMENTS
