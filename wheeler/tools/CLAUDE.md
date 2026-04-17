# tools/ -- CLI and MCP tool handlers

## CLI (`cli.py`)

Typer app with commands: `show`, `migrate`, `graph init`, `graph status`,
`graph add-finding`, `graph add-question`, `graph link`, `graph trace`,
`graph stale`, `validate`, `install`, `uninstall`, `update`, `version`.

## Graph Tools (`graph_tools/`)

MCP tool handlers, split into:
- `mutations.py`: `add_finding`, `add_hypothesis`, `add_question`, `add_dataset`, `add_paper`, `add_document`, `add_note`, `add_script`, `add_execution`, `add_ledger`, `link_nodes`, `set_tier`, `update_node`
- `queries.py`: `query_findings`, `query_hypotheses`, `query_open_questions`, `query_datasets`, `query_papers`, `query_documents`, `query_notes`, `query_scripts`, `query_executions`, `graph_gaps`
- `_common.py`: `_now()` timestamp helper
- `__init__.py`: Tool registry + `execute_tool()` dispatch + triple-write hooks

## Triple-Write

Every `add_*` mutation writes to:
1. Graph (Neo4j) via backend
2. `knowledge/{node_id}.json` via `_write_knowledge_file()`
3. `synthesis/{node_id}.md` via `_write_synthesis_file()`

For `link_nodes`, `_update_synthesis_for_link()` re-renders both
endpoints' synthesis files with updated Relationships sections.

For `set_tier` and `update_node`, both JSON and synthesis are updated.
`update_node` also appends a `ChangeEntry` to the node's change_log.

All writes are best-effort: if synthesis fails, graph and JSON are fine.

## Query Fallback

Query functions read content from JSON files first, fall back to graph
data if the file doesn't exist (pre-migration nodes). Config is passed
via `args["_config"]` key, popped before Cypher execution.
