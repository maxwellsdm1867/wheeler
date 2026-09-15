You are registering the provenance of one completed analysis run into the Wheeler knowledge graph.

Project directory (your cwd): /Users/maxwellsdm/Documents/GitHub/wheeler/.worktrees/batch/evals/batch_registration/runs/20260915T014322Z-s5-r1/project

Read `BRIEF.md` first. It describes one execution (kind `script_run`), every file the run produced (23 files: scripts, data tables, figures, documents, each with a title and a one-line description), six findings stated verbatim (each with a confidence and the ONE figure it appears in), and the two graph nodes the run consumed, which already exist in the graph:

- open question: Q-915abcde
- raw dataset: D-9f00c6ba

Target graph state (this is the complete contract):

1. One Execution node, kind `script_run`, with the description given in the brief.
2. One node per produced file (23), registered from its path with the title and description from the brief. Scripts become Script nodes, CSVs Dataset nodes, PNGs figure Finding nodes, markdown Document nodes.
3. One Finding node per finding (6), description = the finding text verbatim, confidence as stated.
4. Edges (43 in total):
   - every file node `WAS_GENERATED_BY` the execution (23)
   - every finding `WAS_GENERATED_BY` the execution (6)
   - every finding `APPEARS_IN` its one figure node (6)
   - every finding `RELEVANT_TO` Q-915abcde (6)
   - the execution `USED` D-9f00c6ba and `USED` Q-915abcde (2)

Do not create anything not listed above. Do not modify Q-915abcde or D-9f00c6ba. Do not run the analysis scripts.

## Method (strategy 5: delegate to one subagent)

Do NOT register anything yourself. Launch exactly ONE subagent with the Agent tool (`subagent_type: general-purpose`) and hand it the whole job. Its instructions must include, verbatim, the project directory, the two node ids, and this method:

- Read `BRIEF.md` in the project directory.
- Use the Wheeler MCP tools one item at a time: `add_execution` once; `ensure_artifact` once per produced file (23 calls, absolute path, `title`, `description`); `add_finding` once per finding (6 calls, description verbatim, confidence as stated); `link_nodes` once per edge (43 calls).
- Do not batch, do not write scripts or files, do not use Bash.
- Report back one line: `DONE <n_nodes> <n_edges>`.

When the subagent returns, relay its line. Do not verify with additional tool calls of your own.

When finished, reply with exactly one line and nothing else:

DONE <n_nodes> <n_edges>

where n_nodes is the number of graph nodes you created (execution + files + findings, expected 30) and n_edges the number of edges you created (expected 43).

