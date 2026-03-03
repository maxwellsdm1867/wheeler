# Wheeler

A thinking partner for scientists. CLI research assistant with knowledge graph,
citation validation, and mode-based execution control.

## Architecture

Four layers: CLI → Mode State Machine → Claude Agent SDK → MCP Servers (Neo4j, MATLAB, papers)

Agent SDK runs on Max subscription (confirmed: no API charges). It spawns Claude Code CLI
as subprocess internally.

## The Core Rule

**Everything is a reference.** Every factual claim about our research must cite a graph
node using [NODE_ID] format (e.g., [F-3a2b]). Every response gets deterministic citation
validation (regex + Cypher, never LLM self-judgment). Every interaction is logged to the
provenance ledger.

If a claim can't cite a node, it must be flagged as ungrounded.

## Key Files

- `ARCHITECTURE.md` — Full technical spec, read this for detailed design decisions
- `wheeler/engine.py` — WheelerEngine wrapping Agent SDK with mode-aware config
- `wheeler/modes/state.py` — Mode state machine, tool restrictions per mode
- `wheeler/validation/citations.py` — Citation extraction (regex) + validation (Cypher)
- `wheeler/validation/ledger.py` — Provenance ledger, logs every interaction
- `wheeler/graph/context.py` — Size-limited graph context injection (< 500 tokens)
- `wheeler/graph/schema.py` — Neo4j schema constraints and indexes
- `wheeler/prompts/system.py` — System prompts per mode (all include citation rule)
- `wheeler/tools/cli.py` — wheeler-tools deterministic CLI
- `wheeler/config.py` — YAML config loader

## Modes

CHAT: Read + graph reads only. Discuss, query, no execution.
PLANNING: Read + Write + graph + paper search. No bash/MATLAB.
WRITING: Read + Write + Edit + graph reads. No execution. Strict citation enforcement.
EXECUTE: Everything. Must log all findings to graph with provenance.

Enforce via `allowed_tools` in ClaudeAgentOptions, not hooks.

## Design Principles

1. Thin orchestrator — CLI coordinates, never does heavy lifting
2. Everything is a reference — all claims cite graph nodes
3. Deterministic validation — Cypher queries, not LLM self-judgment
4. Size-limited context — max 5 findings + 5 questions + 3 hypotheses injected
5. Fresh agent contexts — subagents in execute mode get clean 200k windows
6. Provenance ledger — every interaction logged with citation audit results
7. Wheeler-Bohr spirit — accept messy thinking, challenge assumptions, flag sparse graph areas, ask questions rather than pad thin answers. A finding doesn't exist until there's a graph node; a claim isn't grounded until the validator checks it.

## Stack

Python 3.11+, claude-agent-sdk, Neo4j Community (Docker), neo4j-agent-memory, Typer + Rich, Pydantic
MCP: mcp-neo4j-cypher, matlab-mcp-tools, paper-search-mcp

## Environment Setup

```bash
source .venv/bin/activate
pip install -e ".[test]"
```

The `.venv` was created with `/opt/homebrew/bin/python3.14`. The system default Python (anaconda) is 3.9 and too old for the SDK.

## Testing

**Run tests after every major update.** This is the regression suite that guards against breakage.

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Tests cover: mode definitions, tool enforcement per mode, CLI command parsing, and SDK options construction. All tests must pass before considering a change complete.

## Constraints

- MATLAB Engine API requires Python 3.10 or 3.11 (not 3.12+) — separate from the main venv if needed
- Cannot run `claude -p` or Agent SDK from inside a Claude Code session (nested session detection)
