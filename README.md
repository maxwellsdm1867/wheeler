# Wheeler

A thinking partner for scientists. Named after John Archibald Wheeler, Bohr's collaborator on nuclear fission theory.

Wheeler is a CLI co-scientist that wraps Claude Code with a knowledge graph, citation validation, and a fluid workflow cycle. Every factual claim traces to a graph node. Every graph node traces to data. Every interaction is logged.

## How it works

```
you: "What do we know about ON parasol contrast responses?"

wheeler: The parasol ON cells show a contrast response index of 0.73 +/- 0.04
[F-3a2b], derived from Naka-Rushton fits [A-7e2d] on the March 2024
recordings [D-9f1c]. This is consistent with the hypothesis that ON-pathway
cells have higher contrast sensitivity than OFF [H-1b4c], though we only
have data from one prep so far.

  citations  F-3a2b  A-7e2d  D-9f1c  H-1b4c
```

Every response gets deterministic citation validation — regex extracts node IDs, Cypher checks they exist with full provenance chains. Not LLM self-judgment.

## Together -> Handoff -> Independent -> Reconvene

Wheeler operates in a fluid cycle. Structure scales with presence — loose and creative when the scientist is present, structured and auditable when working independently.

### Together (interactive)

The scientist and Wheeler thinking through a problem in conversation. This is where the science happens.

```bash
wh              # planning mode (opus) — default
wh plan         # same as above
wh chat         # quick discussion (sonnet)
wh write        # draft text with strict citations (opus)
wh execute      # run analyses, update graph (sonnet)
wh ingest       # bootstrap graph from data (sonnet)
```

Freeform. No forced structure. The graph, MCP tools, and citation system are all available but optional. If you want to just think out loud about a weird spike pattern, do that. If you want to query the graph, do that.

The existing modes (chat, plan, write, execute) are all flavors of Together — they're tools within this phase, not separate workflows.

### Handoff (the transition)

When context saturation is reached — the question is sharp and remaining work is grinding that doesn't need your judgment.

```
/handoff          # from inside a session (keeps conversation context)
wh handoff        # standalone (opus)
```

Wheeler proposes tasks explicitly:

```
I have enough context to run these 3 tasks independently:

1. Search for papers on HC feedback in primate retina (~5 min)
   Checkpoint if: lit search contradicts our HC hypothesis
   wh queue "Search PubMed and Semantic Scholar for papers on horizontal cell
   feedback mechanisms in primate retina. Add relevant papers as REF nodes,
   link to H-004. Focus on marmoset and macaque."

2. Run contrast model comparison on June dataset (~10 min)
   Checkpoint if: neither model clearly wins (ambiguous R^2)
   wh queue "Load June dataset D-9f1c, run Naka-Rushton and gain control
   models on all ON parasol cells. Create Finding nodes with confidence
   scores. Compare R^2 values."

3. Update graph with today's hypotheses (~2 min)
   wh queue "Add hypothesis: ON-pathway cells have higher contrast
   sensitivity due to HC feedback. Link to F-3a2b and F-7c1d as
   supporting evidence."

Go?
```

On approval, Wheeler writes `.logs/handoff-queue.sh` — a runnable script. No copy-paste.

```bash
source .logs/handoff-queue.sh
```

### Independent (background)

Wheeler works alone. Structure is mandatory because you're not watching.

```bash
wh queue "task description"    # sonnet, 10 turns, logged
wh quick "task description"    # haiku, 3 turns, fast
wh status                      # graph status check
```

Every task produces a structured log in `.logs/`:

```json
{
  "task_id": "T-20260303-143000",
  "timestamp": "2026-03-03T14:30:00Z",
  "task_description": "Search for papers on HC feedback in primate",
  "status": "completed",
  "model": "sonnet",
  "duration_seconds": 312,
  "checkpoint_flags": [],
  "result": "Found 5 papers, 2 directly relevant...",
  "citation_validation": {"total": 4, "valid": 4, "pass_rate": 1.0},
  "token_usage": {"input": 4500, "output": 2100}
}
```

Checkpoint system — Wheeler stops and flags instead of making decisions:

| Trigger | Example |
|---------|---------|
| Fork decision | "Two models fit similarly. Which should I pursue?" |
| Interpretation needed | "3 papers support HC feedback in mouse but none in primate" |
| Anomaly | "2 cells have inverted contrast responses" |
| Judgment call | "3 of 23 cells have noisy baselines. Exclude?" |
| Unexpected result | "Surround is STRONGER at high contrast, not weaker" |
| Rabbit hole risk | "HC feedback search pulling up gap junction literature" |

Flagged tasks get `status: "flagged"` in the log and surface during reconvene.

### Reconvene (back to interactive)

```bash
wh reconvene    # opus, reads .logs/ + queries graph
```

Wheeler presents a structured synthesis:

1. **COMPLETED** — tasks that finished, key results with citations
2. **FLAGGED** — checkpoints needing your judgment (with context for fast decisions)
3. **SURPRISES** — anything unexpected
4. **NEXT** — what this suggests we explore

Back to Together. Cycle repeats.

## The Core Rule

**Everything is a reference.** If Wheeler makes a factual claim about your research, it must cite a graph node using `[NODE_ID]` format. If it can't, the claim is flagged as ungrounded.

Citation validation is deterministic (regex + Cypher), never LLM self-judgment:

| Flag | Meaning |
|------|---------|
| VALID | Node exists with full provenance chain |
| WEAK | Node exists but missing provenance links |
| STALE | Node exists but upstream script changed since execution |
| INVALID | Node ID not found (hallucinated) |
| UNGROUNDED | Non-trivial claim with zero citations |

Enforced on all paths:
- **Interactive (REPL)** — validated after every response
- **Headless (queue/quick)** — validated post-hoc, appended to structured log
- **MCP** — `validate_citations` tool available for manual checks

## Architecture

```
bin/wh (bash launcher)
    |
    |-- Interactive: claude --model opus/sonnet --prompt <mode>.md
    |       |
    |       |-- .claude/commands/*.md (system prompts per mode)
    |       |-- wheeler/cli.py (REPL with /commands, citation validation)
    |       |-- wheeler/engine.py (Agent SDK, mode enforcement, context injection)
    |       |
    |       MCP Servers: Neo4j, MATLAB, papers, wheeler-mcp
    |
    |-- Headless: claude -p "task" --output-format json
    |       |
    |       |-- .claude/commands/queue.md (background task protocol)
    |       |-- wheeler/task_log.py (structured logging, checkpoint detection)
    |       |-- .logs/*.json (structured task logs)
    |
    |-- Reconvene: wheeler/log_summary.py -> inject into prompt
```

### Key principle: Structure scales with presence

| Scientist present (Together) | Scientist away (Independent) |
|------------------------------|------------------------------|
| Loose, creative, freeform | Structured, validated, logged |
| Graph optional | Graph mandatory |
| Citation validation informational | Citation validation enforced |
| Logging optional | Every action logged |
| Scientist is quality control | System is quality control |

## Task Routing

Every task gets tagged by who does it:

- **SCIENTIST** — math, conceptual modeling, experimental design, interpretation, judgment calls
- **WHEELER** — lit search, boilerplate code, graph ops, data wrangling, writing drafts, running scripts
- **PAIR** — walkthroughs, debugging, revision, planning discussions

Wheeler never tries to do the scientist's thinking.

## Modes (tool enforcement)

| Mode | Can do | Can't do |
|------|--------|----------|
| **chat** | Read, query graph | Write, execute |
| **plan** | Read, write, graph, paper search | Execute code |
| **write** | Read, write, edit, graph reads | Execute code |
| **execute** | Everything | — |

## Setup

```bash
git clone https://github.com/yourusername/wheeler.git
cd wheeler
bash bin/setup.sh
```

Setup handles: Python venv, pip install, Neo4j Docker, graph schema, `.logs/` directory, zsh completions, `wh` launcher.

Or manually:

```bash
docker run -d -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/research-graph neo4j:community

python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
wheeler-tools graph init
sudo ln -sf $(pwd)/bin/wh /usr/local/bin/wh
```

## MCP Servers

The project `.mcp.json` configures all MCP servers. After setup, restart Claude Code and verify with `/mcp`.

| Server | Purpose |
|--------|---------|
| `neo4j` | Knowledge graph (Cypher read/write) |
| `wheeler` | 18 tools: graph CRUD, citations, workspace, provenance |
| `matlab` | MATLAB execution, plot capture, workspace inspection |
| `papers` | Literature search (PubMed, arXiv, Semantic Scholar) |

Wheeler MCP server (`wheeler/mcp_server.py`) is a thin FastMCP wrapper over the same modules the CLI uses. Run standalone: `python -m wheeler.mcp_server`

## Data Integration

Wheeler connects to MATLAB via `matlab-mcp-tools` for electrophysiology analysis. Results flow into the knowledge graph with full provenance (script hash, parameters, output hash).

Configure in `wheeler.yaml`:

```yaml
data_sources:
  epicTreeGUI_root: "/path/to/epicTreeGUI"
  data_dir: "/path/to/your/data"
```

## Key Files

```
bin/wh                          Bash launcher (routes interactive/headless)
bin/setup.sh                    One-time setup
.claude/commands/*.md           System prompts per mode
wheeler/cli.py                  Interactive REPL (/commands, citations, sessions)
wheeler/engine.py               Agent SDK wrapper, mode enforcement, context injection
wheeler/task_log.py             Structured logging for independent tasks
wheeler/log_summary.py          Log reader for reconvene injection
wheeler/validate_output.py      Post-hoc citation validation (legacy, used by REPL)
wheeler/mcp_server.py           FastMCP server (18 tools)
wheeler/modes/state.py          Mode state machine
wheeler/validation/citations.py Citation extraction (regex) + validation (Cypher)
wheeler/validation/ledger.py    Provenance ledger
wheeler/graph/context.py        Graph context injection (< 500 tokens)
wheeler/graph/schema.py         Neo4j schema constraints
wheeler/graph/provenance.py     File hashing, staleness detection
wheeler/workspace.py            Workspace scanner
wheeler/tools/graph_tools.py    In-process graph tools
wheeler/config.py               YAML config loader
```

## Stack

- **Engine**: Claude Agent SDK (Python) on Max subscription
- **Graph**: Neo4j Community (Docker)
- **CLI**: Typer + Rich
- **Models**: Pydantic
- **MCP**: mcp-neo4j-cypher, matlab-mcp-tools, paper-search-mcp, wheeler-mcp (FastMCP)
- **Launcher**: bash (`bin/wh`)

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -v    # 220 tests
```

## License

MIT
