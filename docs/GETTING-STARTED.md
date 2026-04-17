# Getting Started with Wheeler

This guide walks you through setting up Wheeler from scratch. Takes about 10 minutes.

## What you need

- **macOS or Linux** (Windows via WSL works but is untested)
- **Python 3.11+**
- **Claude Code** with a Max subscription (no API keys needed)
- **Neo4j** (we recommend Neo4j Desktop, instructions below)

## Step 1: Install Neo4j Desktop (recommended)

Neo4j Desktop is the easiest way to run Neo4j locally. It gives you a GUI for managing databases, a built-in browser for visualizing your knowledge graph, and one-click start/stop.

1. Download Neo4j Desktop from https://neo4j.com/download/ (free, requires registration)
2. Install and open Neo4j Desktop
3. Create a new project (e.g., "Wheeler Research")
4. Click **Add Database** > **Local DBMS**
   - Name: `wheeler` (or anything you like)
   - Password: `research-graph` (Wheeler's default; change it in `wheeler.yaml` if you pick something else)
   - Version: **5.x** (latest 5.x is fine)
5. Click **Start** on the database
6. Verify it's running: click **Open** > **Neo4j Browser**, you should see a query prompt

Your connection details (these are the defaults Wheeler expects):
- **URI**: `bolt://localhost:7687`
- **Username**: `neo4j`
- **Password**: `research-graph`
- **Database**: `neo4j`

### Alternative: Docker

If you prefer Docker over Neo4j Desktop:

```bash
docker run -d --name wheeler-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/research-graph \
  neo4j:5-community
```

Browse at http://localhost:7474.

### Alternative: One-line setup

If Docker is installed and you just want everything done for you:

```bash
bash bin/setup.sh
```

This creates the venv, installs Wheeler, starts Neo4j in Docker, initializes the schema, and installs git hooks. Skip to Step 5 if you use this.

## Step 2: Install Wheeler

```bash
git clone https://github.com/maxwellsdm1867/wheeler.git
cd wheeler
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

This installs Wheeler in editable mode with all dependencies, including fastembed for semantic search (downloads a 33MB model on first use, runs locally).

## Step 3: Configure Wheeler

Copy the example config:

```bash
cp wheeler.yaml.example wheeler.yaml
```

The defaults work out of the box if you used `research-graph` as the Neo4j password. If you chose a different password or port, edit `wheeler.yaml`:

```yaml
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: research-graph    # change if you picked something else
  database: neo4j
```

## Step 4: Initialize the graph schema

With Neo4j running:

```bash
source .venv/bin/activate
wheeler-tools graph init
```

This creates uniqueness constraints and indexes in Neo4j. Safe to run multiple times.

Verify it worked:

```bash
wheeler-tools graph status
```

You should see node counts (all zeros if this is a fresh graph, which is expected).

## Step 5: Set up Claude Code

Make sure Claude Code is installed:

```bash
npm install -g @anthropic-ai/claude-code
```

Wheeler communicates with Claude Code through MCP (Model Context Protocol) servers. The `.mcp.json` file in the Wheeler repo configures these automatically. When you open Claude Code in the Wheeler directory, it picks up the MCP servers.

Verify MCP servers are connected:

```bash
cd /path/to/wheeler   # or your project directory
claude                 # opens Claude Code
```

Inside Claude Code, type `/mcp` to check server status. You should see `wheeler_core`, `wheeler_query`, `wheeler_mutations`, and `wheeler_ops` listed as connected.

## Step 6: Install Wheeler in your project

To use Wheeler in your own research project (not the Wheeler repo itself):

```bash
# From the Wheeler repo
source .venv/bin/activate
wheeler install
```

This copies the `/wh:*` slash commands to `~/.claude/` so they're available in any Claude Code session. It also sets up the MCP server configuration.

Then in your project directory:

```bash
cd ~/my-research-project
claude                    # opens Claude Code
/wh:init                  # creates wheeler.yaml, knowledge/, synthesis/, .wheeler/
```

## Step 7: Start using Wheeler

The basic workflow:

```
/wh:discuss              # sharpen the research question
/wh:plan                 # structure the investigation
/wh:execute              # run analyses with full provenance
/wh:write                # draft findings with strict citations
```

### Quick orientation

| Command | What it does |
|---------|-------------|
| `/wh:init` | Set up a new project (creates config, directories, graph schema) |
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

Click **Open** > **Neo4j Browser** in Neo4j Desktop. Useful queries:

```cypher
// See everything
MATCH (n) RETURN n LIMIT 50

// All findings
MATCH (f:Finding) RETURN f ORDER BY f.date DESC

// Provenance chain for a specific finding
MATCH path = (f:Finding {id: "F-xxxx"})-[*1..4]-(connected)
RETURN path

// What scripts produced what findings
MATCH (s:Script)-[:WAS_GENERATED_BY]-(f:Finding)
RETURN s.id, s.path, f.id, f.description
```

### Synthesis files (Obsidian-compatible)

Every node gets a `synthesis/{id}.md` file with YAML frontmatter and `[[backlinks]]`. Open the `synthesis/` directory in Obsidian for a browsable, linked view of your entire knowledge graph.

### CLI

```bash
wheeler show F-xxxx          # show a specific node
wheeler graph status          # node counts
```

## Headless mode (background tasks)

Wheeler can run tasks without you present:

```bash
wh queue "search for papers on retinal ganglion cell models"   # sonnet, 10 turns
wh quick "check graph health"                                   # haiku, 3 turns
wh dream                                                        # graph consolidation
```

Results are logged to `.logs/` and findings are added to the knowledge graph with full provenance.

## Troubleshooting

### "graph_status returns all zeros"

Make sure Neo4j is running. In Neo4j Desktop, check the database shows "Running" status. If using Docker: `docker start wheeler-neo4j`.

### "MCP server not connected"

Restart Claude Code (`/exit` then `claude` again). Check that `.mcp.json` exists in your working directory and points to the correct Python path.

### "knowledge/ directory does not exist"

Run `/wh:init` in your project to create the required directories.

### Neo4j connection refused

Check that Neo4j is listening on port 7687. In Neo4j Desktop, click the database and check the connection details. Default is `bolt://localhost:7687`. If you changed the port, update `wheeler.yaml`.

### Semantic search not working

The fastembed model (33MB) downloads on first use. If you're offline, run a search query once while connected to trigger the download. After that, everything is local.
