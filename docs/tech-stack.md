# Tech Stack

## Core

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Type hints, async, Pydantic v2 |
| Graph database | Neo4j (Community Edition) | Local Docker, free, Cypher, fulltext indexes |
| MCP framework | FastMCP | Claude Code native, stdio transport |
| Embeddings | fastembed (BAAI/bge-small-en-v1.5) | Local, no API, 33MB model, cosine similarity |
| LLM | Claude (Max subscription) | No API keys. Opus for reasoning, Sonnet for grinding, Haiku for quick queries |
| CLI | Typer | `wh` console script for headless tasks and graph operations |
| Models | Pydantic v2 | 11 node types, strict validation, `extra="allow"` for forward compat |

## Runtime

| Component | Detail |
|-----------|--------|
| MCP servers | 5 (core, query, mutations, ops, legacy monolith). 50 tools total |
| Slash commands | 22 acts in `.claude/commands/wh/*.md` |
| Graph protocol | W3C PROV-DM (6 standard + 8 Wheeler semantic relationship types) |
| Storage | Triple-write: Neo4j + knowledge/*.json + synthesis/*.md |
| Search | 4-channel RRF: semantic + keyword + temporal + fulltext |
| Headless | `claude -p` subprocess, structured JSON logs in `.logs/` |

## Infrastructure

| Pattern | Module |
|---------|--------|
| Circuit breaker | `graph/circuit_breaker.py` (3-state, 60s recovery) |
| Consistency checker | `consistency.py` (cross-layer drift detection + repair) |
| Trace IDs | `mcp_shared.py` (per-request correlation) |
| Write receipts | `write_receipt.py` (tracks triple-write layer success) |
| Change log | `models.ChangeEntry` (field-level diffs on mutations) |
| Task contracts | `contracts.py` (handoff output validation) |

## Testing

| Layer | Count | Notes |
|-------|-------|-------|
| Unit + integration | ~1370 | All pass, <10s |
| E2E (live Neo4j) | ~20 | Skipped without Neo4j |
| Surface parity | 1 | Monolith = split server tool sets |
| Pre-commit hook | API safety, test suite, lint |
| Pre-push hook | Full test suite |

## Current gaps (prioritized)

1. **Adversarial / task-completion tests.** No systematic evaluation of whether
   acts produce correct graph mutations end-to-end. No representative task
   suite measuring act effectiveness. This is the highest-priority gap.

2. **Prompt quality evaluation.** No LLM-as-judge scoring of act prompt
   effectiveness. Currently validated through usage and functional tests only.

3. **Centralized request logging.** No per-tool latency, error rate, or
   provenance completion metrics. Trace IDs exist but are not aggregated.

4. **Containerization.** No Dockerfile or docker-compose for one-command
   setup. Users must install Neo4j Desktop manually.

## Constraints

- **No direct API usage.** Pre-commit hook blocks API key patterns and
  direct SDK imports. All LLM work runs through `claude -p` or interactive
  Claude Code sessions.
- **Neo4j Community Edition.** No GDS library, no enterprise features.
  Multi-project isolation is simulated via `_wheeler_project` property.
- **Single user.** No auth, no multi-tenant, no shared graph.
