You are answering a question about the Wheeler knowledge graph of this project. Use the Wheeler MCP tools. Prefer the fewest calls that answer correctly; read a node's full content only when you need it.

Question: Which figure nodes are downstream of the script scripts/fit_srm.py, that is, would go stale if that script changed? A figure counts as downstream when a chain of WAS_GENERATED_BY and USED edges leads from the figure back to the script, through any number of executions and intermediate datasets.

Answer shape: a sorted JSON list of figure node ids.

Reply with exactly one line: ANSWER <json>