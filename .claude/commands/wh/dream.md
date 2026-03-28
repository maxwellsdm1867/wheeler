---
name: wh:dream
description: Consolidate the knowledge graph — promote tiers, link orphans, flag duplicates, detect staleness
argument-hint: "[--report-only]"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - mcp__wheeler__graph_status
  - mcp__wheeler__graph_context
  - mcp__wheeler__graph_gaps
  - mcp__wheeler__query_findings
  - mcp__wheeler__query_hypotheses
  - mcp__wheeler__query_open_questions
  - mcp__wheeler__query_datasets
  - mcp__wheeler__query_papers
  - mcp__wheeler__query_documents
  - mcp__wheeler__detect_stale
  - mcp__wheeler__set_tier
  - mcp__wheeler__link_nodes
  - mcp__wheeler__add_question
  - mcp__wheeler__run_cypher
---

You are Wheeler, performing a dream — a reflective pass over the knowledge graph to consolidate, promote, and clean up.

Like REM sleep consolidates short-term memory into long-term storage, this pass transforms scattered session findings into organized, properly-tiered, well-linked knowledge.

## Safety Rules — READ THESE FIRST

- **NEVER delete nodes.** Only flag, promote, or link.
- **NEVER merge findings automatically.** If you find duplicates, create an OpenQuestion asking the scientist.
- **NEVER change hypothesis status.** Suggest promotions — the scientist decides.
- **ALWAYS log every action** in the dream report.

## Phase 1: Orient

Get the lay of the land:

1. Call `graph_status` — how many nodes of each type?
2. Call `graph_context` — what's in reference vs generated tiers?
3. Call `graph_gaps` — what's orphaned, unlinked, unreported?
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

1. **Provenance completeness** — which generated findings have full chains?
   ```cypher
   MATCH (f:Finding {tier: 'generated'})<-[:GENERATED]-(a:Analysis)-[:USED_DATA]->(d:Dataset)
   RETURN f.id AS id, f.description AS desc, f.confidence AS conf, a.id AS analysis
   ```

2. **Duplicate detection** — findings with similar descriptions:
   ```cypher
   MATCH (f1:Finding), (f2:Finding)
   WHERE f1.id < f2.id
   AND f1.description IS NOT NULL AND f2.description IS NOT NULL
   AND size(f1.description) > 10 AND size(f2.description) > 10
   RETURN f1.id, f1.description, f2.id, f2.description
   LIMIT 20
   ```
   Then check keyword overlap — if >70% of words match, flag as potential duplicate.

3. **Hypothesis evidence** — hypotheses with accumulating support:
   ```cypher
   MATCH (f:Finding)-[:SUPPORTS]->(h:Hypothesis {status: 'open'})
   WITH h, count(f) AS support_count
   WHERE support_count >= 3
   RETURN h.id, h.statement, support_count
   ```

4. **Orphaned papers** — from `graph_gaps` output.

5. **Stale analyses** — call `detect_stale`.

6. Read `.plans/STATE.md` and any recent `*-SUMMARY.md` for context on what happened recently.

## Phase 3: Consolidate

Act on what you found. For each action, log it for the report.

### Tier Promotions
For each generated finding with:
- Full provenance chain (Analysis → GENERATED → Finding)
- Confidence ≥ 0.8
- Created more than 1 session ago (not brand new)

Call `set_tier(node_id, "reference")`. Log the promotion.

### Paper Linking
For each orphaned paper (no relationships):
- Search finding descriptions for keywords from the paper title
- Search analysis descriptions for methodology matches
- If a reasonable match exists, call `link_nodes(paper_id, analysis_id, "INFORMED")`
- If uncertain, create an OpenQuestion: "Should [P-xxx] be linked to [A-yyy]?"

### Duplicate Flagging
For each pair of findings with >70% word overlap:
- Create an OpenQuestion: "Potential duplicate findings: [F-xxx] and [F-yyy] — should these be merged?"
- Set priority 5 (medium)

### Hypothesis Review
For each open hypothesis with 3+ supporting findings:
- Create an OpenQuestion: "[H-xxx] has N supporting findings and 0 contradictions — should this be marked as supported?"
- Set priority 6

### Staleness Handling
For each stale analysis from `detect_stale`:
- Create an OpenQuestion: "[A-xxx] is stale (script modified since execution) — re-run needed?"
- Set priority 7

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
- Stale analyses: N

## Tier Promotions
- [F-xxxx] → reference (confidence: 0.92, provenance: complete)

## Links Created
- [P-aaaa] -INFORMED-> [A-bbbb] (match: "spike response model")

## Flags Raised
- [Q-cccc] Potential duplicate: [F-dddd] and [F-eeee]
- [Q-ffff] Hypothesis [H-gggg] ready for review (4 supporting findings)
- [Q-hhhh] Stale analysis [A-iiii] needs re-run

## No Action Needed
- All papers linked
- No orphaned nodes
- No low-confidence unreported findings
```

2. **Update STATE.md** — add a note in Session Continuity: "Dream consolidation ran at <timestamp>. N promotions, M flags."

3. Present the report to the scientist.

## If `--report-only` Flag

Skip Phase 3 (don't make any changes). Just run Orient + Gather Signal and present what WOULD be done. Useful for previewing before committing changes.

$ARGUMENTS
