# Getting Started with Wheeler

Wheeler is a research knowledge graph that turns Claude Code into a provenance-tracked co-scientist. It records how every result was produced (what script ran, what data it consumed, what papers informed the approach) so your AI-assisted research is reproducible and auditable.

This guide walks you through setting up Wheeler from scratch.

**What you'll have when done:** A running knowledge graph, Claude Code connected to Wheeler's 46 tools, and the ability to use `/wh:*` commands to discuss, plan, execute, and write up research with full provenance tracking.

## What you need

- **macOS or Linux** (Windows via WSL works but is untested)
- **Python 3.11+** (check with `python3 --version`)
- **Node.js** (for Claude Code; check with `node --version`)
- **Claude Code** with a Max subscription (no API keys needed). Claude Code is Anthropic's terminal-based AI assistant.
- **Neo4j Desktop** (free graph database with a visual browser; instructions below)

If your Python version is below 3.11, install a newer one. On macOS: `brew install python@3.13`. Then use `python3.13` instead of `python3` in the commands below.

## Step 1: Install Neo4j Desktop

Neo4j Desktop bundles the database, a JVM, and a visual browser into a single app. No separate Java install needed. It is the easiest way to run Neo4j locally.

### Important: check for existing Neo4j installations first

Neo4j Desktop, Homebrew `neo4j`, and Docker containers all compete for the same two ports: **7474** (HTTP browser) and **7687** (Bolt protocol, what Wheeler connects to). Only one process can bind each port. If another Neo4j is already running, Desktop will fail to start with a "port already in use" error.

Check before you install:

```bash
# See if anything is already on Neo4j's ports
lsof -i :7474
lsof -i :7687

# Check for a Homebrew Neo4j service
brew services list 2>/dev/null | grep neo4j

# Check for a Docker Neo4j container
docker ps 2>/dev/null | grep neo4j
```

If you find an existing installation:
- **Homebrew**: stop it with `brew services stop neo4j`. You can use it instead of Desktop if you prefer, but Desktop is easier for first-time users.
- **Docker**: stop it with `docker stop <container-name>`. Same as above.
- **Another Neo4j Desktop DBMS**: only one DBMS can run at a time in Desktop. Stop the other one first.

You only need one of these. Desktop is recommended because it gives you a visual browser for exploring your graph.

### Install and configure

1. **Download** Neo4j Desktop from https://neo4j.com/download/ (free, requires registration with an email address).

2. **Install and open it.**
   - **macOS Gatekeeper warning**: you will likely see "Neo4j Desktop cannot be opened because the developer cannot be verified." This is normal. Go to **System Settings > Privacy & Security**, scroll down, and click **Open Anyway**. (Or right-click the app > Open.)
   - **First launch is slow** (30-60 seconds) as it unpacks bundled components. This is a one-time cost.
   - **Apple Silicon (M1/M2/M3/M4)**: Desktop 1.5+ includes a native ARM build. No Rosetta needed.

3. **Create a project.** When Desktop opens, you see the main screen. Click **New** (or **New Project**) in the left sidebar. Name it something like "Wheeler Research". A project is just a folder for organizing databases; it does not create a database yet.

4. **Create a database (DBMS).** Inside your new project, click the **Add** button (blue button, top-right of the project panel) > **Local DBMS**.
   - **Name**: `wheeler` (or anything you like)
   - **Password**: **`research-graph`** (this is Wheeler's default; if you pick something else, you will update `wheeler.yaml` in Step 3)
   - **Version**: select the latest **5.x**. Do not use Neo4j 4.x.
   - If asked about plugins (APOC, Graph Data Science), skip them. Wheeler does not need any plugins.
   - Click **Create**. This takes a few seconds.

5. **Start the database.** Your new DBMS appears in the project panel in a **Stopped** state (it does not start automatically). Click the **Start** button. Wait for the status to change to a green **Running** indicator. This can take 30-60 seconds on the first start.

6. **Verify it works.** Once running, click **Open** > **Neo4j Browser**. A browser window opens with a query prompt (`neo4j$`). Type `:server status` and press Enter. You should see connection details confirming the database is active.

### Connection details

These are the defaults Wheeler expects. You will enter them in `wheeler.yaml` in Step 3:

| Setting | Value |
|---------|-------|
| URI | `bolt://localhost:7687` |
| Username | `neo4j` |
| Password | `research-graph` |
| Database | `neo4j` |

### A note on Neo4j Desktop concepts

- A **Project** is just a folder for grouping databases. It does not run anything.
- A **DBMS** (inside a project) is the actual database instance. This is what you start and stop.
- You can have multiple DBMSs in a project, but only one can run at a time (Community Edition limitation).
- Neo4j Desktop is different from Neo4j Community Server (a standalone install you manage yourself) and Neo4j Aura (a cloud-hosted service). Wheeler works with all three, but Desktop is the simplest for local use.

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
/wh:start                # begin every session here
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

Check that Neo4j is listening on port 7687:

```bash
lsof -i :7687
```

If nothing shows up, the database is not running. Open Neo4j Desktop and click Start on your DBMS.

If something other than Neo4j Desktop is on the port (Homebrew `neo4j`, a Docker container), you have a conflict. Stop the other process first:

```bash
brew services stop neo4j        # if Homebrew
docker stop <container-name>    # if Docker
```

If you changed the port in Desktop (DBMS Settings > `server.bolt.listen_address`), update `wheeler.yaml` to match.

### Neo4j authentication failed

The password in `wheeler.yaml` does not match the one you set when creating the DBMS in Neo4j Desktop.

**To fix**: update the `password` field in `wheeler.yaml`.

**If you forgot the password**: the simplest fix is to delete the DBMS in Neo4j Desktop and create a new one. Alternatively, find the DBMS folder (click "..." on the DBMS > "Open folder"), delete `data/dbms/auth`, and restart. The next connection will prompt for a new password.

Note: Neo4j Desktop sets the password you chose at creation time. There is no "neo4j/neo4j" forced-change flow (that is a Neo4j Community Server behavior, not Desktop).

### Neo4j DBMS won't start

Common causes:

- **Port conflict**: another Neo4j installation (Homebrew, Docker, another Desktop DBMS) is already running on ports 7474/7687. Check with `lsof -i :7474` and `lsof -i :7687`.
- **Corrupted after crash**: if your machine lost power or Desktop was force-quit, the database store may be corrupted. Check logs: click "..." on the DBMS > "Open folder" > `logs/neo4j.log`. If the log mentions store corruption, the fastest fix is to delete and recreate the DBMS (Wheeler's graph can be rebuilt with `/wh:ingest`).
- **Stale lock file**: a `store_lock` file in the data directory can persist after a crash. Delete it and restart the DBMS.
- **Disk space**: Neo4j needs several hundred MB free for transaction logs. A full disk produces opaque Java errors.

### Semantic search not working

The fastembed model (33MB) downloads on first use. If you're offline, run a search query once while connected to trigger the download. After that, everything is local.
