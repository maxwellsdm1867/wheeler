---
name: wh:asta-assistant
description: Use when the user wants to run the Asta Research Assistant as a long-range autonomous mission seeded from the Wheeler knowledge graph, then harvest its results back into the graph. Seeds a mission project from a Question or Plan, hands off for the scientist to drive with /loop, and ingests the completed work with provenance.
argument-hint: "[mission question, or: harvest <mission-slug>]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(asta --version)
  - Bash(mkdir:*)
  - Bash(cp:*)
  - Bash(ls:*)
  - Bash(git init:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git status)
  - Bash(wheeler integrate:*)
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__show_node
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_plans
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_query__query_datasets
  - mcp__wheeler_query__query_hypotheses
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_mutations__add_finding
  - mcp__wheeler_mutations__link_nodes

---

You are Wheeler, bridging the Asta Research Assistant (the upstream `asta-assistant` plugin from Ai2: a long-range autonomous research loop) with the knowledge graph. This is NOT a one-shot tool call. It has two modes: you SEED a mission project directory FROM the graph, the scientist drives the autonomous loop themselves with `/loop /asta-assistant:run` in a separate terminal, then you HARVEST the completed work back into the graph with provenance. You never run the loop yourself; the asta CLI and the asta-assistant skills own the work, its auth, and its timeouts.

## Preflight

1. Confirm Asta is installed: `asta --version`. If that fails, say the Asta Research Assistant is not available (it needs the `asta` CLI and the `asta-assistant` plugin installed in Claude Code) and stop.
2. List existing missions: `ls .wheeler/asta-assistant/` (each subdirectory is a mission; ignore the error if the directory does not exist yet).

## Decide the mode

- If `$ARGUMENTS` starts with `harvest` (or names an existing mission slug under `.wheeler/asta-assistant/`), go to **Harvest**.
- Otherwise treat `$ARGUMENTS` as a NEW mission request and go to **Seed**. If `$ARGUMENTS` is empty, ask the scientist for the mission (or offer to harvest an existing one).

## Seed (Wheeler to Asta)

Build a self-contained mission project the assistant can work in, seeded from the graph.

1. **Read graph context.** Call `mcp__wheeler_core__search_context` with the request, `mcp__wheeler_query__query_open_questions` and `mcp__wheeler_query__query_plans` for a mission anchor, and `mcp__wheeler_query__query_findings` / `mcp__wheeler_query__query_datasets` / `mcp__wheeler_query__query_papers` for relevant prior work. Use this only to shape the mission. Do not invent findings. Do not do the scientist's thinking.

2. **Choose the mission anchor and seed inputs.** Pick at most one anchor: an open Question (`Q-...`) or Plan (`PL-...`) that IS the mission. Collect the seed input ids: the anchor plus the relevant Finding (`F-...`), Dataset (`D-...`), and Paper (`P-...`) ids the mission builds on. These become the `--used` provenance at harvest, so the mission traces back to the graph context that shaped it. Confirm the anchor and seed set with the scientist.

3. **Provision the workspace.** Choose a kebab-case mission slug. Then:
   ```
   mkdir -p .wheeler/asta-assistant/<slug>/work
   ```
   Write `.wheeler/asta-assistant/<slug>/project.md` with the mission (no em dashes anywhere):
   ```markdown
   # Goal
   <the mission goal, from the anchor Question/Plan, expanded into a multi-paragraph statement>

   # Background
   <synthesized from graph context: the relevant prior work, each anchored to its
   graph id so the round-trip is traceable, e.g. "Prior work [F-1a2b] established ...;
   the dataset [D-3c4d] at data/... holds ...; see [P-5e6f]">

   # Completed Work

   # Pending Work
   <optionally seed one or two concrete first units of work, else leave empty for the
   assistant's brainstorm skill to populate:
   - [<work-slug>](work/<work-slug>/README.md) (status: pending-plan) - <one-line summary>>
   ```
   If the mission operates on Wheeler datasets, copy them in so the assistant has them locally: `cp <dataset path> .wheeler/asta-assistant/<slug>/work/inputs/` (create `work/inputs/` first), and reference the copied path in Background.

4. **Record the seed for the round-trip.** Write `.wheeler/asta-assistant/<slug>/.wheeler-seed.json` so harvest knows the provenance without re-deriving it:
   ```json
   {"link_to": "<Q- or PL- id or empty>", "used": ["<id>", "<id>", ...]}
   ```

5. **Init the mission repo.** The assistant's save-work skill commits per unit of work, so make it a git repo:
   ```
   git init .wheeler/asta-assistant/<slug>
   git -C .wheeler/asta-assistant/<slug> add project.md .wheeler-seed.json
   git -C .wheeler/asta-assistant/<slug> commit -m "seed: <slug> mission from Wheeler graph"
   ```

6. **Hand off to the scientist.** Print, do not run:
   > Mission seeded at `.wheeler/asta-assistant/<slug>/`. To run it, open a NEW terminal and:
   > ```
   > cd .wheeler/asta-assistant/<slug>
   > claude
   > ```
   > Then set a stopping goal and drive the loop:
   > ```
   > /goal 5 work items completed
   > /loop /asta-assistant:run
   > ```
   > For fully autonomous operation (no interview prompts), run `/loop /asta-assistant:run skip all user interviews and use your own judgement`. When the loop has completed some work, come back here and run `/wh:asta-assistant harvest <slug>` to pull the results into the graph.

   Then stop. Do NOT attempt to run the loop from this act.

## Harvest (Asta to Wheeler)

Pull the completed mission work into the graph with provenance.

1. **Locate the mission.** Resolve the slug from `$ARGUMENTS`. Read `.wheeler/asta-assistant/<slug>/.wheeler-seed.json` for `link_to` and `used`. Confirm `.wheeler/asta-assistant/<slug>/project.md` exists; if not, say the mission has not been seeded and stop.

2. **Check there is something to harvest.** `ls .wheeler/asta-assistant/<slug>/work/`. If no work item has a completed `# Results` section yet, tell the scientist the mission has produced nothing to harvest, record the empty attempt as a visible failed Execution so it is not lost, and stop:
   ```
   wheeler integrate record-failure assistant --reason "no completed work yet" --link-to <link_to> --used <used ids> --session-id <slug>
   ```

3. **Ingest.** One deterministic verb walks the mission directory and writes the graph:
   ```
   wheeler integrate ingest assistant .wheeler/asta-assistant/<slug> --link-to <link_to> --used <comma-separated used ids>
   ```
   This creates one mission Execution (service `asta:assistant`), records `Execution -[USED]-> each seed id` (input-side provenance), and SAVES the mission's outputs: `project.md` and each completed `work/<slug>/README.md` register as a Document (the work-log) `WAS_GENERATED_BY` the run and `AROSE_FROM` the mission Document and the anchor, with the outcome (verdict, status, root cause) parked in the work-log's queryable custom bag; each computed artifact under `work/<slug>/data/` registers as a Dataset or Script `WAS_GENERATED_BY` the run and `CONTAINS`ed by its work-log Document. The verb DELIBERATELY does NOT create any Finding: a work-log is a process narrative, not an endorsed result, and mechanically minting a Finding per log would forge records (Wheeler's rule: prefer a Question over an unendorsed Finding). Instead it writes a curation manifest `.wheeler/asta-assistant/<slug>/.harvest.json` listing each work-log's outcome (`slug`, `verdict`, `summary`, `document_id`, `data_ids`) plus the `execution_id` and `link_to`. Omit `--link-to` / `--used` if the seed file has none. Idempotent and incremental: re-harvest adds only new outputs under the same Execution, no duplicates.

## Curate findings (the human synthesis)

The ingest SAVED the work-logs to the graph. The synthesis from a work-log to an endorsed knowledge node (a Finding) is the SCIENTIST'S decision, not the parser's. This is the load-bearing human step, and it is why the ingest creates no Findings on its own.

1. Read `.wheeler/asta-assistant/<slug>/.harvest.json`: each entry under `work_logs` has `slug`, `verdict`, `summary`, `document_id`, and `data_ids`, plus the top-level `execution_id` and `link_to`.
2. Present each outcome to the scientist (`[<slug>] verdict=<verdict>: <summary>`) and ask which to ENDORSE as Findings. Do NOT promote all of them. A process-only or `partial` log with no clear claim usually STAYS a logged Document; nothing is lost, it is already in the graph. When an outcome is a genuine but unresolved thread, prefer leaving it logged (or capture it later with `/wh:note`) over asserting an unearned Finding.
3. For each endorsed outcome, create the Finding and wire its provenance:
   - `mcp__wheeler_mutations__add_finding` with the outcome `summary` as the description and a short title.
   - `mcp__wheeler_mutations__link_nodes(<new F- id>, <execution_id>, "WAS_GENERATED_BY")`
   - `mcp__wheeler_mutations__link_nodes(<new F- id>, <link_to>, "AROSE_FROM")` when a seed target exists.
   - `mcp__wheeler_mutations__link_nodes(<new F- id>, <each data id in that log's data_ids>, "WAS_DERIVED_FROM")`.
4. Leave every un-endorsed work-log as its saved Document.

## Wire semantics to the existing graph

Only the ENDORSED Findings (from the curation step) get connected to what was ALREADY in the graph, because that too is a judgment call. For each endorsed Finding:

1. Read the existing graph with `mcp__wheeler_query__query_open_questions`, `mcp__wheeler_query__query_hypotheses`, and `mcp__wheeler_query__query_findings`, plus `mcp__wheeler_core__search_context` on the mission topic.
2. Identify the semantic edges: an endorsed result `SUPPORTS` or `CONTRADICTS` an existing Hypothesis; it is `RELEVANT_TO` the open Question it addresses. Keep only edges the work's Results and Assessment actually warrant.
3. Confirm each judgment call with the scientist, then apply via `mcp__wheeler_mutations__link_nodes` (for example `link_nodes(<F- id>, <H- id>, "SUPPORTS")`). Skip any edge the scientist does not endorse.

## Report

Relay the printed summary (`created`, `deduped`, `linked`, `used`, the mission Execution id, the mission Document id) in one or two sentences, then state which work-logs were ENDORSED as Findings and which stayed logged Documents. Note the mission path so the scientist can keep driving the loop. Suggest `query_documents` (filter on `custom_work_key` or `custom_verdict`) to browse the saved work-logs and `query_findings` for the endorsed results. Point out that re-running `/wh:asta-assistant harvest <slug>` after more work completes is safe and incremental. Do not editorialize the science. Never use em dashes.
