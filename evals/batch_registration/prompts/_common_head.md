You are registering the provenance of one completed analysis run into the Wheeler knowledge graph.

Project directory (your cwd): {PROJECT_DIR}

Read `BRIEF.md` first. It describes one execution (kind `script_run`), every file the run produced (23 files: scripts, data tables, figures, documents, each with a title and a one-line description), six findings stated verbatim (each with a confidence and the ONE figure it appears in), and the two graph nodes the run consumed, which already exist in the graph:

- open question: {QUESTION_ID}
- raw dataset: {DATASET_ID}

Target graph state (this is the complete contract):

1. One Execution node, kind `script_run`, with the description given in the brief.
2. One node per produced file (23), registered from its path with the title and description from the brief. Scripts become Script nodes, CSVs Dataset nodes, PNGs figure Finding nodes, markdown Document nodes.
3. One Finding node per finding (6), description = the finding text verbatim, confidence as stated.
4. Edges (43 in total):
   - every file node `WAS_GENERATED_BY` the execution (23)
   - every finding `WAS_GENERATED_BY` the execution (6)
   - every finding `APPEARS_IN` its one figure node (6)
   - every finding `RELEVANT_TO` {QUESTION_ID} (6)
   - the execution `USED` {DATASET_ID} and `USED` {QUESTION_ID} (2)

Do not create anything not listed above. Do not modify {QUESTION_ID} or {DATASET_ID}. Do not run the analysis scripts.
