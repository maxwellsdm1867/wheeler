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
mcp_server.py          <- everything
```

## Key Modules

- `models.py` -- Pydantic v2 models for all node types + prefix mappings. Finding has path, artifact_type, source fields.
- `config.py` -- YAML config loader (`wheeler.yaml`), includes `knowledge_path` and `synthesis_path`
- `provenance.py` -- Stability scoring, invalidation propagation (W3C PROV-DM), detect_and_propagate_stale
- `mcp_server.py` -- FastMCP server, 44 tools. Entry point: `python -m wheeler.mcp_server`
- `workspace.py` -- File discovery + context formatting for system prompts
- `depscanner.py` -- AST-based dependency scanner (imports, data files)
- `request_log.py` -- Append-only JSONL request logging

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
