---
name: wh:dream
description: Use when the Wheeler knowledge graph needs consolidation (tier promotion, orphan linking, staleness detection)
argument-hint: "[--report-only]"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Agent
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
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_query__query_executions
  - mcp__wheeler_mutations__set_tier
  - mcp__wheeler_mutations__link_nodes
  - mcp__wheeler_mutations__add_question
  - mcp__wheeler_mutations__add_document
  - mcp__wheeler_mutations__add_execution
  - mcp__wheeler_ops__detect_stale
  - mcp__wheeler_ops__validate_citations
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

## Phase 0: Graph-Activity Gate (run first, may exit early)

Before doing any consolidation, check whether anything has changed in the graph since the last dream run. If nothing has changed, exit immediately. Re-running consolidation on an unchanged graph produces the same result, and re-generating the morning brief on the same sessions wastes effort. This also handles the "user away for days" case: no activity → no new brief → the previous one still applies.

1. Query for the last dream Execution:

   ```cypher
   MATCH (x:Execution {kind: "dream"})
   RETURN x.id AS id, x.started_at AS last_dream
   ORDER BY x.started_at DESC LIMIT 1
   ```

2. Query for the most recent non-dream activity:

   ```cypher
   MATCH (x:Execution)
   WHERE x.kind <> "dream"
   RETURN max(x.started_at) AS last_activity
   ```

3. Decision:
   - If `last_dream` is null (first ever dream), continue to Phase 1.
   - If `last_activity` is null (no work has ever happened), exit. Report: "No graph activity yet. Nothing to dream about."
   - If `last_activity <= last_dream`, exit. Report: "No new graph activity since last dream at {last_dream}. The previous morning brief (synthesis/MORNING-{date}.md) still applies. No new synthesis needed."
   - If `last_activity > last_dream`, continue to Phase 1.

The same signal serves two purposes: it gates consolidation AND it gates the morning brief. If the scientist hasn't touched the graph, the previous brief is by definition unread/unacted-on and remains the right summary.

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

6. **Framing divergence between linked Findings**:scan recent Findings (last 30 days) that are linked via `RELEVANT_TO` or `AROSE_FROM` from an even-newer Finding. The newer Finding's description may have reframed the older one (a follow-up trace subsumed or contradicted the original framing), leaving the older Finding's description stale. Flag these pairs for human review; do not auto-revise.

   ```cypher
   MATCH (newer:Finding)-[r:RELEVANT_TO|AROSE_FROM]->(older:Finding)
   WHERE newer.date IS NOT NULL AND older.date IS NOT NULL
     AND newer.date > older.date
     AND duration.between(date(older.date), date()).days <= 30
     AND newer.description IS NOT NULL AND older.description IS NOT NULL
     AND size(newer.description) > 40 AND size(older.description) > 40
   RETURN older.id AS older_id, older.description AS older_desc, older.date AS older_date,
          newer.id AS newer_id, newer.description AS newer_desc, newer.date AS newer_date,
          type(r) AS rel
   ORDER BY newer.date DESC LIMIT 20
   ```

   For each returned pair, compare framings. Cheap heuristics: low keyword overlap (under 30% shared content words) combined with the newer description introducing a relationship word the older one lacks ("inversely", "single", "continuous", "same line", "subsumes", "consequence of") suggests the newer trace reframed rather than merely added evidence. When uncertain, treat as a candidate. The bar is "is this worth a human look", not "definitely reframed".

7. Read `.plans/STATE.md` and any recent `*-SUMMARY.md` for context on what happened recently.

## Phase 3: Consolidate

Act on what you found. For each action, log it for the report.

**Action-prompt labeling rule.** OpenQuestions created here are shown to the scientist as user-facing prompts (they will be answered from the morning brief or `/wh:status`). Include a short quoted label (first 80-120 chars of the referenced node's `description`, `statement`, `question`, or `title`, coalesced) alongside each `[NODE_ID]` so the scientist can act without a separate lookup. Bare `[NODE_ID]` remains correct for factual claims in synthesis prose; the rule applies to OpenQuestion text and any other approval-style content.

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
- If uncertain, create an OpenQuestion: `Should [P-xxx] "<paper title>" be linked to [X-yyy] "<execution description>"?`

### Duplicate Flagging
For each pair of findings with >70% word overlap:
- Create an OpenQuestion: `Potential duplicate findings: [F-xxx] "<F-xxx description, ~100 chars>" and [F-yyy] "<F-yyy description, ~100 chars>": should these be merged?`
- Set priority 5 (medium)

### Hypothesis Review
For each open hypothesis with 3+ supporting findings:
- Create an OpenQuestion: `[H-xxx] "<hypothesis statement, ~100 chars>" has N supporting findings and 0 contradictions: should this be marked as supported?`
- Set priority 6

### Staleness Handling
For each stale script from `detect_stale`:
- Create an OpenQuestion: `[S-xxx] "<script title or path>" is stale (script modified since last execution): re-run needed?`
- Set priority 7

### Framing-Divergence Review
For each candidate pair from Phase 2 step 6 (an older Finding that a newer RELEVANT_TO Finding appears to have reframed):
- Create an OpenQuestion citing both Findings and quoting the description-diff in compact form. Template:
  `Framing divergence: [F-older] "<first 80-120 chars of older.description>" may have been reframed by [F-newer] "<first 80-120 chars of newer.description>" (linked RELEVANT_TO). Revise [F-older]'s description to cite [F-newer], or accept the divergence?`
- Set priority 6 (medium: chronic, not acute, per issue context).
- Do not call `update_node` on the older Finding automatically. The flag is the deliverable; the scientist edits the description (typically via `update_node`) if they agree.
- If the same older Finding is reframed by multiple newer Findings, consolidate into a single OpenQuestion listing each newer Finding rather than spawning one question per pair.

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

## Phase 3.6: Morning Brief (independent panel review)

After consolidation, produce a short morning brief by dispatching an independent panel of reviewers. The reviewers are spawned via `Agent` with fresh context: they read the sessions and the graph cold, without the conversation history that led to the work. This is the adversarial check, a critical third party who does not have to agree.

The brief is written to `synthesis/MORNING-{date}.md` and registered as a Document node. Same provenance pattern as close: the Document is generated by an Execution(kind="dream"), and that Execution USED every SESSION node it summarized.

### Step 1: Find sessions to review

Query for SESSION documents created since the last dream:

```cypher
MATCH (w:Document {section: "session-synthesis"})
WHERE datetime(w.date) > datetime($last_dream_at)
RETURN w.id AS id, w.path AS path, w.date AS date, w.title AS title
ORDER BY w.date DESC
```

If no previous dream exists, take the most recent 7 days of session syntheses. If there are zero SESSION documents in the window, skip Phase 3.6 entirely (consolidation already happened, but there is nothing for the panel to review). Report this in Phase 4.

Read each SESSION file from its `path`. These are the raw material for the panel.

### Step 2: Dispatch the panel (three Agents in parallel)

Spawn three `Agent` calls in a single message so they run concurrently. Each is a `wheeler-worker` with a different framing. All three:

- Are read-only (no graph mutations)
- Get the same input: the list of SESSION file paths, the dream consolidation log produced in Phases 1-3, and a graph context summary you assemble (top open questions by priority, in-progress plans, latest tier promotions and flags)
- Return ≤150 words of skeptical-but-constructive prose with `[NODE_ID]` citations for any specific claim

**Reviewer A: Methodologist**

> You are a critical methodologist reviewing yesterday's research sessions. Read the SESSION files at these paths: {list}. Also read this graph context summary: {summary}. Focus only on whether the analytical approaches make sense given what was attempted: parameter choices, statistical reasoning, comparison baselines, sample sizes, claims that outrun the evidence. In under 150 words, name the strongest methodological concern (if any) and one concrete suggestion to address it. Cite `[NODE_ID]` for anything specific. Skeptical but constructive. If the methods look solid, say that briefly and move on.

**Reviewer B: Skeptic**

> You are a skeptical PI reviewing yesterday's research sessions. Read the SESSION files at these paths: {list}. Also read this graph context summary: {summary}. Focus on what is underdetermined: which claims rest on thin evidence, which conclusions outrun the data, which open questions still are not really answered, what alternative explanations were not ruled out. In under 150 words, name the strongest gap and one suggestion to close it. Cite `[NODE_ID]` for anything specific. Push back where warranted. Always end with a constructive suggestion.

**Reviewer C: Planner**

> You are a research planner reviewing yesterday's research sessions. Read the SESSION files at these paths: {list}. Also read this graph context summary: {summary}. Focus on what comes next: given what was learned, what is the single highest-leverage move tomorrow? It might be an analysis, a literature check, a discussion, a re-run of a stale script. In under 150 words, name the suggested move and why. Cite `[NODE_ID]` for anything specific. Be concrete enough that the scientist can act on it immediately.

Run all three in parallel via three concurrent `Agent` calls in a single message. Wait for all three to return.

### Step 3: Combine into the morning brief

Take the three returned prose blocks and write `synthesis/MORNING-{YYYY-MM-DD}.md`. Create `synthesis/` if it does not exist. The total file should be under 600 words.

```markdown
---
morning: {YYYY-MM-DD}
generated_at: {timestamp}
graph_node: ""
based_on_sessions: [W-xxxx, W-yyyy, ...]
source_nodes: [<every node ID cited across the three reviews>]
panel: [methodologist, skeptic, planner]
---

# Morning Brief: {date}

Based on {N} session(s) since last dream ({date range}). {One-line headline of what was accomplished, citing the most important [NODE_ID] of the period.}

## Methodologist
{Reviewer A's prose, ≤150 words, with [NODE_ID] citations}

## Skeptic
{Reviewer B's prose, ≤150 words, with [NODE_ID] citations}

## Planner
{Reviewer C's prose, ≤150 words, with [NODE_ID] citations}

## Pick Up Here
- /wh:execute [PL-xxxx] — "{title}" (in-progress)
- {top 2-3 open questions by priority, with [Q-xxxx] citations}
```

### Step 4: Register the brief in the graph (mandatory)

The file on disk is the rendered view. The graph is the authoritative record. Wire it in:

1. Call `add_document` with:
   - `title="Morning Brief: {YYYY-MM-DD}"`
   - `path={absolute path to MORNING file}`
   - `section="morning-brief"`
   - `status="final"`

   Returns `W-xxxx`. Write back into the file's `graph_node:` frontmatter.

2. Create the dream Execution that future Phase 0 checks will see:

   ```
   add_execution(
     kind="dream",
     description="Morning brief: panel review of {N} sessions on {YYYY-MM-DD}"
   )
   ```

   Returns `X-yyyy`.

3. Link the Document to the dream Execution:
   `link_nodes(source_id=W-xxxx, target_id=X-yyyy, relationship="WAS_GENERATED_BY")`

4. Link the dream Execution to every SESSION it reviewed:
   For each SESSION `W-zzzz` in `based_on_sessions`:
   `link_nodes(source_id=X-yyyy, target_id=W-zzzz, relationship="USED")`

5. Link the dream Execution to every node cited in the panel prose (the `source_nodes` frontmatter list):
   For each `NODE_ID`: `link_nodes(source_id=X-yyyy, target_id=NODE_ID, relationship="USED")`

6. Call `validate_citations(path={absolute path to MORNING file})`. Every `[NODE_ID]` in the prose must resolve. If any do not, fix them before reporting Phase 3.6 complete.

### Step 5: Update STATE.md

If `.plans/STATE.md` exists, append to the "Session Continuity" section: "Dream ran at {timestamp}. Morning brief: synthesis/MORNING-{date}.md ([W-xxxx]). Panel reviewed {N} session(s)."

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
- [Q-jjjj] Framing divergence: [F-older] may have been reframed by [F-newer]

## Synthesis Files Generated
- synthesis/INDEX.md: N nodes indexed
- synthesis/OPEN_QUESTIONS.md: N questions (X critical, Y important, Z background)
- synthesis/EVIDENCE_MAP.md: N hypotheses mapped

## Morning Brief
- synthesis/MORNING-{date}.md ([W-xxxx])
- Panel: methodologist, skeptic, planner
- Sessions reviewed: N ({list of W-xxxx})
- Source nodes cited: M
- Citation validation: pass | fail with details
- (Or: "Skipped — no SESSION documents in window")

## No Action Needed
- All papers linked
- No orphaned nodes
- No low-confidence unreported findings
```

2. **Update STATE.md** -- add a note in Session Continuity: "Dream consolidation ran at <timestamp>. N promotions, M flags. Synthesis indexes regenerated. Morning brief: synthesis/MORNING-{date}.md ([W-xxxx])."

3. Present the report to the scientist, leading with the morning brief: "Read synthesis/MORNING-{date}.md — three reviewers weighed in, here's the headline."

## If `--report-only` Flag

Skip Phase 3, Phase 3.5, and Phase 3.6 (don't make any changes, regenerate indexes, or generate the morning brief). Just run Phase 0 + Orient + Gather Signal and present what WOULD be done. Useful for previewing before committing changes. The Phase 0 gate still applies: if there is no new graph activity, exit early even in `--report-only`.

$ARGUMENTS
