---
name: wh:report
description: Use when the user wants a work-log summary of recent Wheeler research activity over a time period
argument-hint: "[today | week | since YYYY-MM-DD]"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__graph_status
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_documents
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_ops__detect_stale
  - mcp__wheeler_query__query_plans
---

## Connectivity Check
Before proceeding: call `graph_health`. If it returns `"status": "offline"`,
STOP. Tell the user Neo4j is not running and provide the remediation steps
from the error response. Offer to retry after they start it. Do not continue
with other work.

You are Wheeler, generating a work log by scanning the knowledge graph for recent activity.

## Your Job

Query the graph for everything created or modified in the requested time period and produce a structured report. No manual input needed — the graph has timestamps on every node.

## Step 1: Determine Time Window

Parse `$ARGUMENTS`:
- `today` → last 24 hours
- `week` → last 7 days
- `since YYYY-MM-DD` → from that date to now
- No argument → default to `today`

## Step 2: Query Recent Activity

Run these Cypher queries to find everything created in the time window:

**Findings:**
```cypher
MATCH (f:Finding) WHERE f.date >= $since
RETURN f.id AS id, f.description AS desc, f.confidence AS conf, f.tier AS tier, f.date AS date
ORDER BY f.date DESC
```

**Hypotheses:**
```cypher
MATCH (h:Hypothesis) WHERE h.date >= $since
RETURN h.id AS id, h.statement AS stmt, h.status AS status, h.date AS date
ORDER BY h.date DESC
```

**Open Questions:**
```cypher
MATCH (q:OpenQuestion) WHERE q.date_added >= $since
RETURN q.id AS id, q.question AS question, q.priority AS priority, q.date_added AS date
ORDER BY q.priority DESC
```

**Executions (scripts run):**
```cypher
MATCH (x:Execution) WHERE x.started_at >= $since
OPTIONAL MATCH (x)-[:USED]->(s:Script)
RETURN x.id AS id, x.description AS desc, x.kind AS kind, s.path AS script, x.started_at AS date
ORDER BY x.started_at DESC
```

**Papers added:**
```cypher
MATCH (p:Paper) WHERE p.date_added >= $since
RETURN p.id AS id, p.title AS title, p.authors AS authors, p.date_added AS date
ORDER BY p.date_added DESC
```

**Documents written:**
```cypher
MATCH (w:Document) WHERE w.date >= $since
RETURN w.id AS id, w.title AS title, w.section AS section, w.status AS status, w.date AS date
ORDER BY w.date DESC
```

**Relationships created (provenance links):**
```cypher
MATCH (a)-[r]->(b)
WHERE a.date >= $since OR b.date >= $since
RETURN a.id AS from_id, type(r) AS rel, b.id AS to_id
LIMIT 50
```

## Step 3: Check Investigation State (graph-first)

- Call `query_plans()` to get all plans. For each plan with `updated` in the time window, include its status transitions. The `change_log` field on each plan node (available in `knowledge/PL-xxxx.json`) records status transitions with timestamps, so you can show "draft -> approved -> in-progress" progressions.
- Fall back to `.plans/STATE.md` and `*-SUMMARY.md` only if the graph returns no plans.
- Check `.logs/` for headless task results in the time window.

## Step 4: Generate Report

Write the report to `.plans/WORK-LOG-{date}.md`:

```markdown
# Work Log: {date range}
Generated: {timestamp}

## Summary
{One paragraph: what was the main focus, what was accomplished, what's next}

## Findings ({count})
{Group by tier — reference vs generated}

### New (generated)
- [{id}] {description} (confidence: {conf})
  ← from [{execution_id}] {script_name}

### Promoted to Reference
- [{id}] {description} (promoted from generated)

## Executions ({count})
- [{id}] ({kind}) {description}
  Script: [{script_id}]
  Used: [{dataset_ids}]
  Produced: [{finding_ids}]

## Hypotheses ({count})
### New
- [{id}] {statement} (status: {status})

### Updated
- [{id}] {statement} — status changed to {status}

## Open Questions ({count})
### New
- [{id}] (priority: {priority}) {question}

### Resolved
- [{id}] {question} — answered by [{finding_id}]

## Documents Written ({count})
- [{id}] {title} ({section}, {status})
  Cites: [{cited_node_ids}]

## Papers Added ({count})
- [{id}] {authors} ({year}) — {title}
  Used by: [{execution_ids}]

## Graph Health
- Total nodes: {count}
- Stale scripts: {count}
- Orphaned papers: {count}
- Unreported findings: {count}

## Active Investigation
{From STATE.md — name, status, progress}

## Next Steps
{Based on open questions, incomplete plans, and graph gaps}
```

## Step 5: Present

Show the report to the scientist. If there's nothing to report (no new nodes in the time window), say so.

## Rules
- Query the graph — don't rely on memory or conversation history
- Every claim cites a [NODE_ID]
- If a time window returns too many results (>50 nodes), summarize by category rather than listing all
- The report should be useful for: lab meetings, progress updates, PI check-ins, personal tracking

$ARGUMENTS
