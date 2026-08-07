# wheeler/ -- Python package

## Module Architecture

```
models.py              <- zero internal deps (leaf node, source of truth)
credentials.py         <- zero internal deps (OS keychain, lazy `keyring`)
  ^
config.py              <- zero internal deps (YAML loader; lazy credentials.py)
  ^
knowledge/store.py     <- models only
knowledge/render.py    <- models only (incl. render_synthesis for Obsidian)
  ^
graph/*                <- models + config
provenance.py          <- config + graph.driver (stability, invalidation)
aura.py                <- stdlib urllib + lazy config/graph.driver (Aura onboarding)
  ^
tools/graph_tools/*    <- graph + knowledge (lazy imports)
integrations/*         <- config + lazy execute_tool (external-service adapters; Asta)
mcp_core.py, mcp_query.py, mcp_mutations.py, mcp_ops.py   <- four split MCP servers (the surface)
```

## Key Modules

- `models.py` -- Pydantic v2 models for all node types + prefix mappings. Finding has path, artifact_type, source fields.
- `config.py` -- YAML config loader (`wheeler.yaml`), includes `knowledge_path` and `synthesis_path`. Also the keychain overlay and `neo4j_sources()` (which layer supplied each Neo4j field)
- `credentials.py` -- OS keychain store behind `wheeler login` (macOS Keychain / libsecret / Credential Manager). `keyring` is an optional extra (`wheeler[login]`), imported lazily; every read path degrades to "no stored credentials" and never raises
- `aura.py` -- Neo4j Aura onboarding: tolerant credentials-file parser, management API (OAuth `client_credentials` only, no browser flow exists), connect-before-save validation. stdlib `urllib` only
- `acts.py` -- The one reader of the act corpus (`_data/commands/*.md`), served over MCP by `list_acts` / `get_act`. `mode` and `orchestration` are DERIVED from each act's `allowed-tools`, never declared separately
- `build_plugin.py` -- Generates the `wh` plugin tree for both hosts from the act corpus. Regenerate with `python -m wheeler.build_plugin`; never hand-edit the emitted tree
- `provenance.py` -- Stability scoring, invalidation propagation (W3C PROV-DM), detect_and_propagate_stale
- `mcp_core.py`, `mcp_query.py`, `mcp_mutations.py`, `mcp_ops.py` -- four split FastMCP servers (the canonical MCP surface). Each registers a role-specific subset of tools. Register new tools in the matching server only.
- `workspace.py` -- File discovery + context formatting for system prompts
- `depscanner.py` -- AST-based dependency scanner (imports, data files)
- `request_log.py` -- Append-only JSONL request logging
- `integrations/` -- external-service adapters (Asta first, then LLM-SR equation discovery, which inverts an evolutionary loop into CLI verbs because there is no service to call). The marshal-out ingest modules are the only `execute_tool` callers here (lazy, function-local). To add a NEW external service, use the `wheeler-service-creator` skill (it scaffolds the adapter with the external-call failsafe baked in and an auditor), do NOT hand-write one. See `integrations/asta/CLAUDE.md` and `integrations/llmsr/CLAUDE.md`.

## Config (`wheeler.yaml`)

Sections: `neo4j`, `graph` (backend selection), `search`, `project`,
`paths`, `workspace`, `models` (per-mode model assignment), `knowledge_path`,
`synthesis_path`.

Precedence for the four `neo4j` connection fields:
`NEO4J_*` env > OS keychain (`wheeler login`) > `wheeler.yaml` > `_NEO4J_DEFAULTS`.
Env stays highest so CI and containers keep working. `neo4j_sources()` reports
which layer won per field; `wheeler login --status` prints it.

Project root resolution: `WHEELER_PROJECT_ROOT` env > explicit `project_root` in
`wheeler.yaml` > nearest ancestor holding `wheeler.yaml` or `.wheeler/` > cwd.
Prefer the `resolved_*` properties over bare `Path(config.knowledge_path)`: a
relative path is resolved against whatever cwd the process happens to have.

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
