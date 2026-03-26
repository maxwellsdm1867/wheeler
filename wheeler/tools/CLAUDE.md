# tools/ — CLI and MCP tool handlers

## CLI (`cli.py`)

Typer app with commands: `show`, `migrate`, `graph init`, `graph status`,
`graph add-finding`, `graph add-question`, `graph link`, `graph trace`,
`graph stale`, `validate`, `install`, `uninstall`, `update`, `version`.

## Graph Tools (`graph_tools/`)

MCP tool handlers, split into:
- `mutations.py` — `add_finding`, `add_hypothesis`, `add_question`, `add_dataset`, `add_paper`, `add_document`, `link_nodes`, `set_tier`
- `queries.py` — `query_findings`, `query_hypotheses`, `query_open_questions`, `query_datasets`, `query_papers`, `query_documents`, `graph_gaps`
- `_common.py` — `_now()` timestamp helper
- `__init__.py` — Tool registry + `execute_tool()` dispatch

## Dual-Write

Every `add_*` mutation writes to both graph AND `knowledge/*.json`.
The hook is in `__init__.py`'s `execute_tool()` — after graph write
succeeds, builds a Pydantic model and calls `store.write_node()`.

## Query Fallback

Query functions read content from JSON files first, fall back to graph
data if the file doesn't exist (pre-migration nodes). Config is passed
via `args["_config"]` key, popped before Cypher execution.
