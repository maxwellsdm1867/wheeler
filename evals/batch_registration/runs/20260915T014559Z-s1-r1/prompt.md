You are registering the provenance of one completed analysis run into the Wheeler knowledge graph.

Project directory (your cwd): /Users/maxwellsdm/Documents/GitHub/wheeler/.worktrees/batch/evals/batch_registration/runs/20260915T014559Z-s1-r1/project

Read `BRIEF.md` first. It describes one execution (kind `script_run`), every file the run produced (23 files: scripts, data tables, figures, documents, each with a title and a one-line description), six findings stated verbatim (each with a confidence and the ONE figure it appears in), and the two graph nodes the run consumed, which already exist in the graph:

- open question: Q-754c7ff0
- raw dataset: D-75178bb7

Target graph state (this is the complete contract):

1. One Execution node, kind `script_run`, with the description given in the brief.
2. One node per produced file (23), registered from its path with the title and description from the brief. Scripts become Script nodes, CSVs Dataset nodes, PNGs figure Finding nodes, markdown Document nodes.
3. One Finding node per finding (6), description = the finding text verbatim, confidence as stated.
4. Edges (43 in total):
   - every file node `WAS_GENERATED_BY` the execution (23)
   - every finding `WAS_GENERATED_BY` the execution (6)
   - every finding `APPEARS_IN` its one figure node (6)
   - every finding `RELEVANT_TO` Q-754c7ff0 (6)
   - the execution `USED` D-75178bb7 and `USED` Q-754c7ff0 (2)

Do not create anything not listed above. Do not modify Q-754c7ff0 or D-75178bb7. Do not run the analysis scripts.

## Method (strategy 1: one call per item, the status quo)

Use the Wheeler MCP tools one item at a time, in this order:

1. `add_execution` once (kind `script_run`, description from the brief, status `completed`).
2. `ensure_artifact` once per produced file (23 calls), passing the absolute path, `title` and `description` from the brief. Note the node id each call returns.
3. `add_finding` once per finding (6 calls) with `description` = the finding text verbatim and `confidence` as stated.
4. `link_nodes` once per edge (43 calls): `source_id`, `relationship`, `target_id`.

Do NOT batch. Do NOT use any batch or multi-item tool even if one is offered. Do NOT write scripts, manifests or files of any kind. Do NOT use Bash. Every node and every edge is its own MCP tool call.

When finished, reply with exactly one line and nothing else:

DONE <n_nodes> <n_edges>

where n_nodes is the number of graph nodes you created (execution + files + findings, expected 30) and n_edges the number of edges you created (expected 43).

