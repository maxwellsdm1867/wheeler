# Getting Started with Wheeler

Wheeler is a research knowledge graph that turns Claude Code into a provenance-tracked co-scientist. It records how every result was produced (what script ran, what data it consumed, what papers informed the approach) so your AI-assisted research is reproducible and auditable.

This guide walks you through setting up Wheeler from scratch.

**What you'll have when done:** A running knowledge graph, Claude Code connected to Wheeler's 44 tools, and the ability to use `/wh:*` commands to discuss, plan, execute, and write up research with full provenance tracking.

## What you need

- **macOS or Linux** (Windows via WSL works but is untested)
- **Python 3.11+** (check with `python3 --version`)
- **Node.js** (for Claude Code; check with `node --version`)
- **Claude Code** with a Max subscription (no API keys needed). Claude Code is Anthropic's terminal-based AI assistant.
- **Neo4j Desktop** (free graph database with a visual browser; instructions below)

If your Python version is below 3.11, install a newer one. On macOS: `brew install python@3.13`. Then use `python3.13` instead of `python3` in the commands below.

## Step 1: Install Neo4j Desktop

Neo4j Desktop gives you a GUI for managing databases, a built-in browser for visualizing your knowledge graph, and one-click start/stop. It is the easiest way to run Neo4j locally.

1. Download Neo4j Desktop from https://neo4j.com/download/ (free, requires registration)
2. Install and open it. On macOS, you may see a Gatekeeper warning ("cannot be opened because the developer cannot be verified"). Go to System Settings > Privacy & Security and click Allow.
3. Create a new project (e.g., "Wheeler Research")
4. Click **Add** (or **Add Database**) > **Local DBMS**
   - Name: `wheeler` (or anything you like)
   - Password: **`research-graph`** (Wheeler's default; change it in `wheeler.yaml` if you pick something else)
   - Version: **5.x** (latest 5.x is fine). Do not use Neo4j 4.x.
   - If asked about APOC plugins, skip them. Wheeler does not need APOC.
5. Click **Start** on the database. Wait for the green "Running" indicator (may take 30-60 seconds).
6. Verify it's running: click **Open** > **Neo4j Browser**. You should see a query prompt.

Your connection details (these are the defaults Wheeler expects):

| Setting | Value |
|---------|-------|
| URI | `bolt://localhost:7687` |
| Username | `neo4j` |
| Password | `research-graph` |
| Database | `neo4j` |

## Step 2: Install Wheeler

```bash
git clone https://github.com/maxwellsdm1867/wheeler.git
cd wheeler
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[test]"
```

This installs Wheeler with all dependencies. The `pip install -e` flag means changes to the source code take effect immediately (useful if you want to contribute). The install includes fastembed, which enables searching the knowledge graph by meaning, not just keywords. It downloads a 33MB model on first use (runs entirely locally).

If `pip install` fails on Apple Silicon (M1/M2/M3), make sure you ran `pip install --upgrade pip` first. Older pip versions can fail when building native packages.

## Step 3: Configure Wheeler

Copy the example config:

```bash
cp wheeler.yaml.example wheeler.yaml
```

The defaults work out of the box if you used `research-graph` as the Neo4j password in Step 1. If you chose a different password, edit `wheeler.yaml`:

```yaml
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: research-graph    # change if you picked something else
  database: neo4j
```

## Step 4: Initialize the graph schema

Make sure Neo4j Desktop shows the database as "Running" (green dot), then:

```bash
source .venv/bin/activate       # skip if already active
wheeler-tools graph init
```

This sets up the database structure Wheeler needs (uniqueness constraints and indexes). Safe to run multiple times.

If you see "connection refused" or a timeout, Neo4j is not running. Go back to Neo4j Desktop and click Start on your database.

Verify it worked:

```bash
wheeler-tools graph status
```

You should see node counts (all zeros on a fresh graph, which is expected).

## Step 5: Set up Claude Code

Install Claude Code if you don't have it:

```bash
npm install -g @anthropic-ai/claude-code
```

(If `npm` is not found, install Node.js first: https://nodejs.org/ or `brew install node` on macOS.)

Wheeler talks to Claude Code through MCP (Model Context Protocol), which lets Claude Code call Wheeler's graph tools directly. The `.mcp.json` file in the Wheeler repo configures this automatically.

Verify everything is connected:

```bash
cd /path/to/wheeler
claude                          # opens Claude Code
```

Inside Claude Code, type `/mcp` to check server status. You should see Wheeler servers listed as connected. In the Wheeler repo directory, you'll see `wheeler_core`, `wheeler_query`, `wheeler_mutations`, `wheeler_ops`, `wheeler` (legacy), and `neo4j`.

## Step 6: Install Wheeler in your research project

To use Wheeler in your own project (not the Wheeler repo itself), you need to register the tools globally so they're available from any directory.

**In a terminal where the Wheeler venv is active:**

```bash
cd /path/to/wheeler             # go to the Wheeler repo
source .venv/bin/activate       # activate the venv
wheeler install
```

This does two things:
1. Copies the `/wh:*` slash commands to `~/.claude/` so they work in any Claude Code session
2. Registers the `wheeler` MCP server in `~/.claude/settings.json` so Claude Code can reach the graph tools from any directory

**Now restart Claude Code** (type `/exit`, then `claude` again). This is required for the new MCP servers to be picked up.

**Then open your research project:**

```bash
cd ~/my-research-project
claude
```

Type `/mcp` to verify. You should see `wheeler` and `neo4j` listed. Then run:

```
/wh:init
```

This is an interactive setup wizard (takes 2-3 minutes). It creates `wheeler.yaml`, `knowledge/`, `synthesis/`, `.notes/`, `.plans/`, `.logs/`, and `.wheeler/` in your project, and initializes the graph schema.

## Step 7: Start using Wheeler

The basic workflow:

```
/wh:start                # not sure which command? start here
/wh:discuss              # sharpen the research question
/wh:plan                 # structure the investigation
/wh:execute              # run analyses with full provenance
/wh:write                # draft findings with strict citations
```

You can also just describe your task and Wheeler will auto-route to the right command if your intent is unambiguous (e.g., "add this DOI to the knowledge graph" fires `/wh:add` directly).

### Quick orientation

| Command | What it does |
|---------|-------------|
| `/wh:init` | Set up a new project (interactive wizard) |
| `/wh:discuss` | Sharpen the question through structured discussion |
| `/wh:plan` | Propose investigations, break work into tasks |
| `/wh:execute` | Run tasks with full provenance tracking |
| `/wh:ingest` | Bootstrap the graph from existing code, data, and papers |
| `/wh:add` | Add anything to the graph (finding, paper, dataset, note) |
| `/wh:ask` | Query the knowledge graph |
| `/wh:write` | Draft text with strict citation enforcement |
| `/wh:status` | Check investigation progress |
| `/wh:dream` | Consolidate the graph (promote tiers, link orphans, detect duplicates) |
| `/wh:compile` | Generate synthesis documents from the graph |

### Example: Ingesting an existing project

If you already have code, data, and papers in your project:

```
/wh:ingest all
```

Wheeler will scan your workspace, ask about primary data sources, create Script nodes for key code files (with hashes for change detection), Dataset nodes for data files, and run a linking pass to connect scripts to the data they read.

### Example: Adding a finding

During an analysis session:

```
Use add_finding to record: "Population mean firing rate is 12.3 Hz (n=45, SD=3.1)"
with confidence 0.85 and path to the script that produced it
```

Wheeler creates the finding node, links it to the script via provenance, writes the knowledge JSON, renders the synthesis markdown, and indexes the embedding. All in one tool call.

## Browsing your knowledge graph

### Neo4j Browser (built into Neo4j Desktop)

Click **Open** > **Neo4j Browser** in Neo4j Desktop. Useful queries (these will be empty until you start adding nodes):

```cypher
// See everything in the graph
MATCH (n) RETURN n LIMIT 50

// All findings, most recently updated first
MATCH (f:Finding) RETURN f ORDER BY f.updated DESC

// Provenance chain for a specific finding (replace F-xxxx with a real ID)
MATCH path = (f:Finding {id: "F-xxxx"})-[*1..4]-(connected)
RETURN path

// What scripts produced what findings (traces through Execution nodes)
MATCH (f:Finding)-[:WAS_GENERATED_BY]->(x:Execution)-[:USED]->(s:Script)
RETURN s.id, s.path, f.id, f.description
```

### Synthesis files (Obsidian-compatible)

Every node gets a `synthesis/{id}.md` file with YAML frontmatter and `[[backlinks]]`. Open the `synthesis/` directory in Obsidian for a browsable, linked view of your entire knowledge graph.

### CLI

```bash
wheeler show F-xxxx          # show a specific node
wheeler graph status          # node counts
```

## Running tasks in the background

Wheeler can run tasks without you present, logging results and adding findings to the graph:

```bash
wh queue "search for papers on retinal ganglion cell models"   # sonnet, 10 turns
wh quick "check graph health"                                   # haiku, 3 turns
wh dream                                                        # graph consolidation
```

Results are logged to `.logs/` with full provenance.

## Troubleshooting

### "command not found: wheeler-tools"

You need to activate the virtual environment first: `source .venv/bin/activate` (from the Wheeler repo directory).

### "graph_status returns all zeros"

Make sure Neo4j is running. In Neo4j Desktop, check the database shows a green "Running" indicator.

### "MCP server not connected"

Restart Claude Code (`/exit` then `claude` again). If you're in the Wheeler repo, MCP servers are configured by `.mcp.json` in the repo. If you're in your own project after running `wheeler install`, servers are configured in `~/.claude/settings.json`.

### "knowledge/ directory does not exist"

Run `/wh:init` in your project to create the required directories.

### Neo4j connection refused

Check that Neo4j is listening on port 7687. In Neo4j Desktop, click the database and check the connection details. Default is `bolt://localhost:7687`. If you changed the port, update `wheeler.yaml`.

### Neo4j authentication failed

The password in your `wheeler.yaml` doesn't match the one you set in Neo4j Desktop. Update the `password` field in `wheeler.yaml` to match.

### Semantic search not working

The fastembed model (33MB) downloads on first use. If you're offline, run a search query once while connected to trigger the download. After that, everything is local.
