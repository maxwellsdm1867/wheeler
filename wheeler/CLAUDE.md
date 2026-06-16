# wheeler/ -- Python package

## Module Architecture

```
models.py              <- zero internal deps (leaf node, source of truth)
  ^
config.py              <- zero internal deps (YAML loader)
  ^
knowledge/store.py     <- models only
knowledge/render.py    <- models only (incl. render_synthesis for Obsidian)
  ^
graph/*                <- models + config
provenance.py          <- config + graph.driver (stability, invalidation)
  ^
tools/graph_tools/*    <- graph + knowledge (lazy imports)
integrations/*         <- config + lazy execute_tool (external-service adapters; Asta)
mcp_core.py, mcp_query.py, mcp_mutations.py, mcp_ops.py   <- four split MCP servers (canonical surface)
mcp_server.py          <- DEPRECATED legacy monolith (scheduled for removal)
```

## Key Modules

- `models.py` -- Pydantic v2 models for all node types + prefix mappings. Finding has path, artifact_type, source fields.
- `config.py` -- YAML config loader (`wheeler.yaml`), includes `knowledge_path` and `synthesis_path`
- `provenance.py` -- Stability scoring, invalidation propagation (W3C PROV-DM), detect_and_propagate_stale
- `mcp_core.py`, `mcp_query.py`, `mcp_mutations.py`, `mcp_ops.py` -- four split FastMCP servers (the canonical MCP surface). Each registers a role-specific subset of tools. Register new tools in the matching server only.
- `mcp_server.py` -- DEPRECATED legacy monolith. Logs a deprecation warning at startup. Do NOT add new tools here.
- `workspace.py` -- File discovery + context formatting for system prompts
- `depscanner.py` -- AST-based dependency scanner (imports, data files)
- `request_log.py` -- Append-only JSONL request logging
- `integrations/` -- external-service adapters (Asta first). The marshal-out ingest modules are the only `execute_tool` callers here (lazy, function-local). To add a NEW external service, use the `wheeler-service-creator` skill (it scaffolds the adapter with the external-call failsafe baked in and an auditor), do NOT hand-write one. See `integrations/asta/CLAUDE.md`.

## Config (`wheeler.yaml`)

Sections: `neo4j`, `graph` (backend selection), `search`, `project`,
`paths`, `workspace`, `models` (per-mode model assignment), `knowledge_path`,
`synthesis_path`.

## Triple-Write

Every `add_*` mutation writes three things:
1. Graph node (Neo4j)
2. `knowledge/{node_id}.json` (machine metadata)
3. `synthesis/{node_id}.md` (human-readable, Obsidian-compatible)

`link_nodes` re-renders synthesis files for both endpoints.
`set_tier` updates both JSON and synthesis.

## Conventions

- `from __future__ import annotations` in every module
- Stdlib logging with `logging.getLogger(__name__)`
- Async where graph I/O happens, sync for file I/O
- Lazy imports in `tools/` to avoid circular deps with `knowledge/`
- Never use em dashes. Use colons, commas, periods, parentheses.
