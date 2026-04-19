---
name: wh:dream
description: Use when the Wheeler knowledge graph needs consolidation (tier promotion, orphan linking, staleness detection)
argument-hint: "[--report-only]"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__graph_status
  - mcp__wheeler_core__graph_context
  - mcp__wheeler_core__graph_gaps
  - mcp__wheeler_core__run_cypher
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_documents
  - mcp__wheeler_query__query_notes
  - mcp__wheeler_mutations__set_tier
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_mutations__add_question
  - mcp__wheeler_ops__detect_stale
---

## Connectivity Check
Before proceeding: call `graph_health`. If it returns `"status": "offline"`,
STOP. Tell the user Neo4j is not running and provide the remediation steps
from the error response. Offer to retry after they start it. Do not continue
with other work.

You are Wheeler, performing a dream:a reflective pass over the knowledge graph to consolidate, promote, and clean up.

Like REM sleep consolidates short-term memory into long-term storage, this pass transforms scattered session findings into organized, properly-tiered, well-linked knowledge.

## Safety Rules:READ THESE FIRST

- **NEVER delete nodes.** Only flag, promote, or link.
- **NEVER merge findings automatically.** If you find duplicates, create an OpenQuestion asking the scientist.
- **NEVER change hypothesis status.** Suggest promotions:the scientist decides.
- **ALWAYS log every action** in the dream report.

## Phase 1: Orient

Get the lay of the land:

1. Call `graph_status`:how many nodes of each type?
2. Call `graph_context`:what's in reference vs generated tiers?
3. Call `graph_gaps`:what's orphaned, unlinked, unreported?
4. Run Cypher to count tier distribution:
   ```cypher
   MATCH (f:Finding) RETURN f.tier AS tier, count(f) AS count
   ```
5. Run Cypher to find old generated findings (candidates for promotion):
   ```cypher
   MATCH (f:Finding)
   WHERE (f.tier IS NULL OR f.tier = 'generated')
   RETURN f.id AS id, f.description AS desc, f.confidence AS conf, f.date AS date
   ORDER BY f.date ASC LIMIT 20
   ```

Present a brief summary: "Graph has X findings (Y reference, Z generated), N papers, M open questions. Found K gaps."

## Phase 2: Gather Signal

Look for consolidation opportunities:

1. **Provenance completeness**:which generated findings have full chains?
   ```cypher
   MATCH (f:Finding {tier: 'generated'})-[:WAS_GENERATED_BY]->(x:Execution)-[:USED]->(d:Dataset)
   RETURN f.id AS id, f.description AS desc, f.confidence AS conf, x.id AS execution
   ```

2. **Duplicate detection**:findings with similar descriptions:
   ```cypher
   MATCH (f1:Finding), (f2:Finding)
   WHERE f1.id < f2.id
   AND f1.description IS NOT NULL AND f2.description IS NOT NULL
   AND size(f1.description) > 10 AND size(f2.description) > 10
   RETURN f1.id, f1.description, f2.id, f2.description
   LIMIT 20
   ```
   Then check keyword overlap:if >70% of words match, flag as potential duplicate.

3. **Hypothesis evidence**:hypotheses with accumulating support:
   ```cypher
   MATCH (f:Finding)-[:SUPPORTS]->(h:Hypothesis {status: 'open'})
   WITH h, count(f) AS support_count
   WHERE support_count >= 3
   RETURN h.id, h.statement, support_count
   ```

4. **Orphaned papers**:from `graph_gaps` output.

5. **Stale scripts**:call `detect_stale`.

6. Read `.plans/STATE.md` and any recent `*-SUMMARY.md` for context on what happened recently.

## Phase 3: Consolidate

Act on what you found. For each action, log it for the report.

### Tier Promotions
For each generated finding with:
- Full provenance chain (Finding → WAS_GENERATED_BY → Execution)
- Confidence ≥ 0.8
- Created more than 1 session ago (not brand new)

Call `set_tier(node_id, "reference")`. Log the promotion.

### Paper Linking
For each orphaned paper (no relationships):
- Search finding descriptions for keywords from the paper title
- Search execution descriptions for methodology matches
- If a reasonable match exists, call `link_nodes(execution_id, paper_id, "USED")`
- If uncertain, create an OpenQuestion: "Should [P-xxx] be linked to [X-yyy]?"

### Duplicate Flagging
For each pair of findings with >70% word overlap:
- Create an OpenQuestion: "Potential duplicate findings: [F-xxx] and [F-yyy]:should these be merged?"
- Set priority 5 (medium)

### Hypothesis Review
For each open hypothesis with 3+ supporting findings:
- Create an OpenQuestion: "[H-xxx] has N supporting findings and 0 contradictions:should this be marked as supported?"
- Set priority 6

### Staleness Handling
For each stale script from `detect_stale`:
- Create an OpenQuestion: "[S-xxx] is stale (script modified since last execution):re-run needed?"
- Set priority 7

## Phase 3.5: Generate Synthesis Index Files

After consolidation, regenerate the three index files in `synthesis/`. These are always rebuilt from scratch (never incrementally updated). Create `synthesis/` directory if it doesn't exist.

### 1. `synthesis/INDEX.md`

Query all node types and build a master index:

```markdown
<!-- Auto-generated by /wh:dream. Do not edit manually. -->
# Knowledge Graph Index

Generated: {timestamp}
Total nodes: {total_count}

## Findings ({count})

| ID | Description | Confidence | Tier | Date |
|----|------------|------------|------|------|
| [[F-xxxx]] | Description here | 0.88 | reference | 2026-04-05 |

## Hypotheses ({count})

| ID | Statement | Status | Support | Contradict |
|----|-----------|--------|---------|------------|
| [[H-xxxx]] | Statement | open | 3 | 1 |

## Open Questions ({count})

| ID | Question | Priority |
|----|----------|----------|
| [[Q-xxxx]] | Question here | 9 |

## Papers ({count})

| ID | Title | Authors | Year |
|----|-------|---------|------|
| [[P-xxxx]] | Title | Authors | 2020 |

## Datasets ({count})

| ID | Description | Path |
|----|------------|------|
| [[D-xxxx]] | Description | path/to/data |

## Research Notes ({count})

| ID | Title | Date |
|----|-------|------|
| [[N-xxxx]] | Title | 2026-04-05 |
```

Use [[node_id]] Obsidian backlinks so clicking opens the per-node synthesis file.

For hypothesis support/contradict counts, run:
```cypher
MATCH (h:Hypothesis)
OPTIONAL MATCH (sf:Finding)-[:SUPPORTS]->(h)
OPTIONAL MATCH (cf:Finding)-[:CONTRADICTS]->(h)
RETURN h.id AS id, h.statement AS statement, h.status AS status,
       count(DISTINCT sf) AS support, count(DISTINCT cf) AS contradict
```

### 2. `synthesis/OPEN_QUESTIONS.md`

Query all open questions and group by priority tier:

```markdown
<!-- Auto-generated by /wh:dream. Do not edit manually. -->
# Open Questions

Generated: {timestamp}
Total: {count}

## Critical (priority 8-10)

### [[Q-xxxx]] (priority 9)
Question text here

## Important (priority 5-7)

### [[Q-yyyy]] (priority 6)
Question text here

## Background (priority 1-4)

### [[Q-zzzz]] (priority 2)
Question text here
```

### 3. `synthesis/EVIDENCE_MAP.md`

Query all hypotheses with their evidence:

```cypher
MATCH (f:Finding)-[r:SUPPORTS|CONTRADICTS]->(h:Hypothesis)
RETURN h.id AS hyp_id, h.statement AS statement, h.status AS status,
       f.id AS finding_id, f.description AS description,
       f.confidence AS confidence, f.tier AS tier,
       type(r) AS rel
ORDER BY h.id, type(r), f.confidence DESC
```

Group results by hypothesis in Python/prompt logic:

```markdown
<!-- Auto-generated by /wh:dream. Do not edit manually. -->
# Evidence Map

Generated: {timestamp}

## [[H-xxxx]]: Statement here

Status: open

### Supporting ({count})
- [[F-aaaa]] (conf: 0.92, reference) Description
- [[F-bbbb]] (conf: 0.85, generated) Description

### Contradicting ({count})
- [[F-cccc]] (conf: 0.75, generated) Description

### Balance: +2/-1

---
```

Include hypotheses with NO evidence too (balance: 0/0, needs investigation).

Log in the dream report: "Generated INDEX.md ({N} nodes), OPEN_QUESTIONS.md ({N} questions), EVIDENCE_MAP.md ({N} hypotheses)"

## Phase 4: Prune & Report

1. **Write the dream report** to `.plans/DREAM-REPORT.md`:

```markdown
# Dream Report
Consolidated: <timestamp>

## Summary
- Findings: X total (Y reference, Z generated)
- Promotions: N findings promoted to reference
- Links created: N
- Flags raised: N new open questions
- Stale scripts: N
- Synthesis files: INDEX.md (N nodes), OPEN_QUESTIONS.md (N questions), EVIDENCE_MAP.md (N hypotheses)

## Tier Promotions
- [F-xxxx] -> reference (confidence: 0.92, provenance: complete)

## Links Created
- [X-aaaa] -USED-> [P-bbbb] (match: "spike response model")

## Flags Raised
- [Q-cccc] Potential duplicate: [F-dddd] and [F-eeee]
- [Q-ffff] Hypothesis [H-gggg] ready for review (4 supporting findings)
- [Q-hhhh] Stale script [S-iiii] needs re-run

## Synthesis Files Generated
- synthesis/INDEX.md: N nodes indexed
- synthesis/OPEN_QUESTIONS.md: N questions (X critical, Y important, Z background)
- synthesis/EVIDENCE_MAP.md: N hypotheses mapped

## No Action Needed
- All papers linked
- No orphaned nodes
- No low-confidence unreported findings
```

2. **Update STATE.md** -- add a note in Session Continuity: "Dream consolidation ran at <timestamp>. N promotions, M flags. Synthesis indexes regenerated."

3. Present the report to the scientist.

## If `--report-only` Flag

Skip Phase 3 and Phase 3.5 (don't make any changes or regenerate indexes). Just run Orient + Gather Signal and present what WOULD be done. Useful for previewing before committing changes.

$ARGUMENTS
