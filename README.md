# Wheeler

A thinking partner for scientists. Named after John Archibald Wheeler, Bohr's collaborator on nuclear fission theory.

Wheeler is a CLI co-scientist that wraps Claude with a knowledge graph, citation validation, and mode-based execution control. Every factual claim traces to a graph node. Every graph node traces to data. Every interaction is logged.

## What it does

```
you: "What do we know about ON parasol contrast responses?"

wheeler: The parasol ON cells show a contrast response index of 0.73 ± 0.04
[F-3a2b], derived from Naka-Rushton fits [A-7e2d] on the March 2024
recordings [D-9f1c]. This is consistent with the hypothesis that ON-pathway
cells have higher contrast sensitivity than OFF [H-1b4c], though we only
have data from one prep so far.

⚠️ Note: contrast_fit.m has been modified since analysis A-7e2d ran.
   Finding F-3a2b may be stale. Consider re-running.

✅ F-3a2b VALID  ✅ A-7e2d VALID (stale)  ✅ D-9f1c VALID  ✅ H-1b4c VALID
```

Every response gets deterministic citation validation — regex extracts node IDs, Cypher checks they exist with full provenance chains. Not LLM self-judgment.

## Why Wheeler

| Tool | What it does | What's missing |
| --- | --- | --- |
| Google AI Co-Scientist | Generates hypotheses from published literature | Doesn't have your unpublished data |
| ELNs (Sapio, Benchling) | Document what happened | Don't reason about it |
| Neo4j LLM Graph Builder | Generic graph construction | Not a research workflow |
| Standard RAG | Retrieves text chunks | No typed provenance chains |

Wheeler maintains typed provenance from raw data to published claim: Finding → Analysis → Dataset → Experiment. When you modify a script, it detects that downstream findings may be stale.

## Architecture

```
CLI (/chat, /plan, /write, /execute)
    ↓
Mode State Machine (constrains available tools)
    ↓
Claude Agent SDK (runs on Max subscription, no API charges)
    ↓
MCP Servers (Neo4j graph, MATLAB, paper search)
```

## Modes

| Mode | Can do | Can't do | Purpose |
| --- | --- | --- | --- |
| **chat** | Read, query graph | Write, execute | Discuss, ask questions |
| **plan** | Read, write, graph, paper search | Execute code | Design research plans |
| **write** | Read, write, edit, graph reads | Execute code | Draft papers with enforced citations |
| **execute** | Everything | — | Run analyses, update graph with provenance |

## Setup

### Prerequisites

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) with Max subscription
- Docker (for Neo4j)

### Install

```bash
# Start Neo4j
docker run -d -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/research-graph \
  neo4j:community

# Install Wheeler
git clone https://github.com/yourusername/wheeler.git
cd wheeler
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"

# Initialize the graph schema
wheeler-tools graph init
```

### Configure MCP servers

Create `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "uvx",
      "args": ["mcp-neo4j-cypher@latest"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "research-graph"
      }
    }
  }
}
```

## Usage

```bash
# Start Wheeler
wheeler

# Switch modes
/chat          # Discuss, query the graph
/plan          # Design research plans
/write         # Draft text with citation enforcement
/execute       # Run analyses, log to graph

# Tools
wheeler-tools graph status        # Node/edge counts
wheeler-tools graph stale         # Find findings with changed upstream scripts
wheeler-tools validate response.md  # Citation validation on a file
wheeler-tools ledger show         # Recent provenance entries
```

## The Core Rule

**Everything is a reference.** If Claude makes a factual claim about your research, it must cite a graph node using `[NODE_ID]` format. If it can't, the claim is flagged as ungrounded. Validation is deterministic (regex + Cypher), never LLM self-judgment.

Citation validation flags:
- **VALID** — node exists with full provenance chain
- **WEAK** — node exists but missing provenance links
- **STALE** — node exists but upstream script has changed since execution
- **INVALID** — node ID not found (hallucinated)
- **UNCITED** — factual claim with no citation

## Data Integration (Optional)

Wheeler can connect to external data sources like [epicTreeGUI](https://github.com/your-org/epicTreeGUI) for neurophysiology data. This is fully plug-and-play — if unconfigured, Wheeler works exactly as before.

### Setup

Add a `data_sources` section to `wheeler.yaml`:

```yaml
data_sources:
  epicTreeGUI_root: "/path/to/epicTreeGUI"
  data_dir: "/path/to/your/data"
```

The MATLAB wrapper functions in `matlab/` handle all communication between Wheeler and epicTreeGUI. They return structured JSON that the agent can parse, and are called via the existing `matlab-mcp-tools` MCP server.

### MATLAB Workflow

```
wheeler_setup(epicTreeGUI_root)          # Set up MATLAB paths
wheeler_list_data(data_dir)              # List available .mat files
wheeler_load_data(filepath, {splitters}) # Load data, build tree
wheeler_tree_info(var_name, node_path)   # Inspect a node
wheeler_get_responses(var_name, node_path, stream)  # Get response data
wheeler_run_analysis(var_name, node_path, type)     # Run analysis
```

Results flow into the knowledge graph via `add_dataset` and standard finding/analysis tools, maintaining full provenance.

## Stack

- **Engine**: Claude Agent SDK (Python) on Max subscription
- **Graph**: Neo4j Community (Docker) + neo4j-agent-memory
- **CLI**: Typer + Rich
- **Models**: Pydantic
- **MCP**: mcp-neo4j-cypher, matlab-mcp-tools, paper-search-mcp

## Development

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## License

MIT
