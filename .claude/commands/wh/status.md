---
name: wh:status
description: Show current knowledge graph state
argument-hint: ""
allowed-tools:
  - mcp__wheeler__graph_status
  - mcp__wheeler__graph_gaps
  - mcp__wheeler__query_findings
  - mcp__wheeler__query_open_questions
  - mcp__wheeler__detect_stale
  - mcp__neo4j__read_neo4j_cypher
---

Show the current state of the knowledge graph. Be concise. Use wheeler MCP tools for all queries.

1. Call `graph_status` for node counts by type (Finding, Hypothesis, OpenQuestion, Dataset, Analysis, Experiment, Paper, CellType, Plan, Task)
2. Call `query_findings` for the 5 most recent findings with their confidence scores
3. Call `query_open_questions` for open questions sorted by priority (top 5)
4. Call `graph_gaps` for unsupported hypotheses and unlinked questions
5. Call `detect_stale` for stale analyses (script_hash doesn't match current file, or file missing)
6. Query total relationships via `read_neo4j_cypher`

Format as a compact summary, not a wall of text.

$ARGUMENTS
