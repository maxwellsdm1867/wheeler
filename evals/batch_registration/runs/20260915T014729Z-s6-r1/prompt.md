You are registering the provenance of one completed analysis run into the Wheeler knowledge graph.

Project directory (your cwd): /Users/maxwellsdm/Documents/GitHub/wheeler/.worktrees/batch/evals/batch_registration/runs/20260915T014729Z-s6-r1/project

Read `BRIEF.md` first. It describes one execution (kind `script_run`), every file the run produced (23 files: scripts, data tables, figures, documents, each with a title and a one-line description), six findings stated verbatim (each with a confidence and the ONE figure it appears in), and the two graph nodes the run consumed, which already exist in the graph:

- open question: Q-97609993
- raw dataset: D-c72d9851

Target graph state (this is the complete contract):

1. One Execution node, kind `script_run`, with the description given in the brief.
2. One node per produced file (23), registered from its path with the title and description from the brief. Scripts become Script nodes, CSVs Dataset nodes, PNGs figure Finding nodes, markdown Document nodes.
3. One Finding node per finding (6), description = the finding text verbatim, confidence as stated.
4. Edges (43 in total):
   - every file node `WAS_GENERATED_BY` the execution (23)
   - every finding `WAS_GENERATED_BY` the execution (6)
   - every finding `APPEARS_IN` its one figure node (6)
   - every finding `RELEVANT_TO` Q-97609993 (6)
   - the execution `USED` D-c72d9851 and `USED` Q-97609993 (2)

Do not create anything not listed above. Do not modify Q-97609993 or D-c72d9851. Do not run the analysis scripts.

## Method (strategy 6: batch MCP tools, split form)

The mutations server exposes batch tools. Use the SPLIT form, not `register_batch`:

1. `add_execution` once (kind `script_run`, description from the brief, status `completed`). Note the id.
2. `ensure_artifacts` once, with all 23 files in one list (each item: absolute `path`, `title`, `description`). It returns the node id of every file in input order.
3. `add_finding` once per finding (6 calls) with `description` = the finding text verbatim and `confidence` as stated. Note each id.
4. `link_nodes_batch` once, with all 43 edges in one list as `[source_id, relationship, target_id]` triples using the literal ids you collected.

Do NOT use `register_batch`. Do NOT call `link_nodes` or `ensure_artifact` one item at a time. Do NOT write files or use Bash.

When finished, reply with exactly one line and nothing else:

DONE <n_nodes> <n_edges>

where n_nodes is the number of graph nodes you created (execution + files + findings, expected 30) and n_edges the number of edges you created (expected 43).

