# wheeler/ — Python package

## Module Architecture

```
models.py              ← zero internal deps (leaf node, source of truth)
  ↑
knowledge/store.py     ← models only
knowledge/render.py    ← models only
  ↑
graph/*                ← models + config
  ↑
tools/graph_tools/*    ← graph + knowledge (lazy imports)
mcp_server.py          ← everything
```

## Key Modules

- `models.py` — Pydantic v2 models for all 11 node types + prefix mappings
- `config.py` — YAML config loader (`wheeler.yaml`), Pydantic models for config sections
- `mcp_server.py` — FastMCP server, 26 tools. Entry point: `python -m wheeler.mcp_server`
- `workspace.py` — File discovery + context formatting for system prompts

## Config (`wheeler.yaml`)

Sections: `neo4j`, `graph` (backend selection), `search`, `project`,
`paths`, `workspace`, `models` (per-mode model assignment), `knowledge_path`.

## Conventions

- `from __future__ import annotations` in every module
- Stdlib logging with `logging.getLogger(__name__)`
- Async where graph I/O happens, sync for file I/O
- Lazy imports in `tools/` to avoid circular deps with `knowledge/`
