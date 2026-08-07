# Getting Started with Wheeler

Wheeler is a research knowledge graph that turns Claude Code into a provenance-tracked co-scientist. It records how every result was produced (what script ran, what data it consumed, what papers informed the approach) so your AI-assisted research is reproducible and auditable.

This guide walks you through setting up Wheeler from scratch.

**What you'll have when done:** A running knowledge graph, Claude Code connected to Wheeler's 50 tools, and the ability to use `/wh:*` commands to discuss, plan, execute, and write up research with full provenance tracking.

## What you need

- **macOS or Linux** (Windows via WSL works but is untested)
- **[uv](https://docs.astral.sh/uv/)** (the Python toolchain Wheeler ships with). Install: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `brew install uv` on macOS). uv brings its own managed Python, so no separate `python3` install is needed.
- **Node.js** (for Claude Code; check with `node --version`)
- **Claude Code** with a Max subscription (no API keys needed). Claude Code is Anthropic's terminal-based AI assistant.
- **Neo4j Desktop** (free graph database with a visual browser; instructions below)

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

### Alternative: Neo4j Aura (hosted, no local database)

If you would rather not run a database on your laptop, Wheeler connects to a remote Neo4j Aura instance over the encrypted Bolt scheme. Create an instance at https://console.neo4j.io.

| Setting | Value |
|---------|-------|
| URI | `neo4j+s://<instance-id>.databases.neo4j.io` |
| Username | `neo4j` |
| Password | from the credentials file Aura gives you at creation |
| Database | `neo4j` |

**Save the credentials file Aura offers when the instance is created.** The password is displayed exactly once, on that screen and in that file, and Aura cannot recover it afterwards. Lose it and your only options are resetting the password from the console or creating a new instance. The file is a plain `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` list, usually downloaded as something like `Instance01-credentials.txt`.

#### `wheeler login`: hand Wheeler that file

```bash
pip install 'wheeler[login]'          # or: uv tool install wheeler --with keyring
wheeler login --aura-file ~/Downloads/Instance01-credentials.txt
```

That is the whole setup. Nothing typed, no API key, and it works on the free tier, which is why it is the recommended route.

What it does, in order: parses the file, connects to the instance and runs a trivial query, and only then stores the credentials in your operating system's keychain (macOS Keychain, libsecret on Linux, Windows Credential Manager). Consequences worth knowing:

- **The password never touches a file.** Not `wheeler.yaml`, not a shell profile, not your shell history. It is not echoed while you type it and `wheeler login --status` prints it masked.
- **A credential that does not work is never stored.** If validation fails, nothing is saved and the command exits non-zero. This is deliberate: a stored-but-broken credential sends you debugging Neo4j when the problem was the credential.
- **`wheeler logout`** removes it again (`--profile <name>` for one profile, `--all` for every one).

The `wheeler[login]` extra pulls in `keyring`. Wheeler works without it: the keychain layer simply reports itself unavailable and environment variables and `wheeler.yaml` behave exactly as they always have.

#### The two other routes

`wheeler login` with no flags prompts for URI, username, password (read without echo), and database. It works against anything, hosted or local, and is the fallback when you have no credentials file.

`wheeler login --aura` asks the Aura management API where your instances live, so you do not copy a URI by hand. It needs a Client ID and Secret created in the Aura Console under Account Details, then lists your instances and reads the `connection_url` of the one you pick (auto-selected when there is only one).

Two properties of Aura, not of Wheeler, decide whether that path is available to you:

- **There is no browser sign-in.** Aura's management API supports OAuth 2.0 `client_credentials` and nothing else: no device-code flow, no interactive end-user login. Pasting an API key once is the best that exists, and Wheeler does not pretend otherwise.
- **Aura will not issue API credentials until billing information is on file.** An account holding only Free instances, outside a marketplace project, cannot create a Client ID at all. If the token request is rejected, that is usually why, and Wheeler says so. `--aura-file` is the way through, because it needs no API key. This is exactly why the file is the primary route and the API is the power route.

One more limit: `GET /v1/instances` does not return passwords (Aura hands a password out only in the creation response), so `--aura` still prompts for it. It saves you the URI, not the secret.

#### Where each setting comes from

Four layers can supply a Neo4j setting. Highest precedence first:

```
environment variables  >  OS keychain  >  wheeler.yaml  >  built-in default
```

Environment variables stay on top deliberately. CI jobs, containers, and one-off invocations like `NEO4J_URI=bolt://other:7687 wheeler graph status` keep working exactly as before, and a credential stored on a laptop never silently overrides a deployment that sets its own.

That ordering has one trap, and it is the likeliest thing to confuse you: **an exported `NEO4J_URI` outranks the credential you just stored**, so a stale export in a shell profile makes a successful `wheeler login` look as though it did nothing. Ask instead of guessing:

```bash
wheeler login --status
```

It prints one row per field naming the layer that won (`env`, `keychain`, `yaml`, or `default`), where that layer is (the variable name, the profile, the path to `wheeler.yaml`), and the value, with the password masked. When an environment variable is shadowing a stored credential it says so outright and names the variable to unset. It also reports whether a keychain is available at all and which profiles are stored.

#### More than one instance: named profiles

```bash
wheeler login --aura-file ~/Downloads/prod-credentials.txt --profile prod
export WHEELER_PROFILE=prod          # select it for this shell
```

With no `--profile`, everything reads and writes the profile named `default`. `wheeler login --status` shows which profile is active and which ones are stored.

#### Environment variables: CI, containers, and the `neo4j` MCP server

The four variables are still the right tool for a non-interactive environment, and there is one case where you need them even on a laptop:

```bash
export NEO4J_URI="neo4j+s://abc12345.databases.neo4j.io"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="<from the credentials file>"
export NEO4J_DATABASE="neo4j"
```

Wheeler's own four MCP servers read the full precedence chain, so `wheeler login` is enough for them. The fifth entry in `.mcp.json` is not Wheeler's: the `neo4j` server runs the third-party `mcp-neo4j-cypher` (the raw-Cypher tool), and its templated `env` block (`"NEO4J_URI": "${NEO4J_URI:-bolt://localhost:7687}"`, and so on) reads environment variables only. It cannot see your keychain. So if you want that server pointed at a hosted instance too, export the four variables as well. Because env outranks the keychain, Wheeler and that server then agree by construction.

#### macOS: a possible one-time access prompt

macOS binds a stored keychain item to the program that created it. `wheeler login` runs as one binary and the MCP servers may be launched by `uvx` as another, so macOS can ask once per program whether it may read the item. Click "Always Allow" and it does not come back.

Wheeler is built so a blocked or slow prompt degrades instead of hanging: the keychain read runs with a five-second watchdog (tunable via `WHEELER_KEYCHAIN_TIMEOUT`) and falls through to `wheeler.yaml` and the built-in defaults if it does not answer, because a wedged MCP server would look like a dead one. To take the keychain out of the picture entirely, set `WHEELER_NO_KEYCHAIN=1` and use environment variables.

#### Isolation on Aura Free

**On Aura Free you get property-tag isolation, not a dedicated database.** Wheeler tries `CREATE DATABASE <your project>` first. Aura Free does not grant access to the `system` database, so that command fails, and Wheeler falls back to the shared `neo4j` database: every node gets a `_wheeler_project=<project name>` property and every query filters on it. The fallback is announced at WARNING with the underlying error:

```
CREATE DATABASE 'my-project' failed (ClientError: Unsupported administration command ...).
Isolation model DOWNGRADED: Wheeler will use the shared 'neo4j' database with
property-tag isolation (_wheeler_project='my-project'), not a dedicated database.
```

That warning is expected on Aura Free and on Neo4j Community Edition. If you see it on Enterprise or a paid Aura tier, read the exception in the message: it is usually a wrong password or a missing privilege, not an edition limit.

Two more things to know about a remote instance:

- **Aura Free instances pause when left idle.** Resume the instance from the console before a session, or every graph call will fail on connect.
- **Connection tuning is env-driven.** The defaults below work locally and remotely; raise the timeouts on a slow link.

| Variable | Default | What it controls |
|----------|---------|------------------|
| `WHEELER_NEO4J_POOL_SIZE` | `50` | Max pooled connections |
| `WHEELER_NEO4J_CONNECT_TIMEOUT` | `15` | Seconds to establish a connection (TLS handshake included) |
| `WHEELER_NEO4J_ACQUISITION_TIMEOUT` | `30` | Seconds to wait for a free connection from the pool |
| `WHEELER_NEO4J_MAX_LIFETIME` | `1800` | Seconds before a pooled connection is recycled |
| `WHEELER_NEO4J_RETRY_ATTEMPTS` | `3` | Attempts for a transient failure |
| `WHEELER_NEO4J_RETRY_BASE_DELAY` | `0.25` | Backoff base in seconds (doubles per attempt) |

### A note on Neo4j Desktop concepts

- A **Project** is just a folder for grouping databases. It does not run anything.
- A **DBMS** (inside a project) is the actual database instance. This is what you start and stop.
- You can have multiple DBMSs in a project, but only one can run at a time (Community Edition limitation).
- Neo4j Desktop is different from Neo4j Community Server (a standalone install you manage yourself) and Neo4j Aura (a cloud-hosted service). Wheeler works with all three, but Desktop is the simplest for local use.

## Step 2: Install Wheeler and scaffold your project

One command does both, installing the Wheeler tool and scaffolding a new project directory wired up to Claude Code:

```bash
uv tool install wheeler           # persistent install, ~10 seconds
wheeler init my-research-project
```

(For a one-off trial without installing, you can also run `uvx wheeler init my-research-project` instead. Persistent install is recommended once you decide to stick with Wheeler, because the `.mcp.json` paths Wheeler writes are stable across sessions.)

What `wheeler init` does:

- Creates `my-research-project/` (or uses it if it already exists).
- Scaffolds `.plans/`, `.logs/`, `.wheeler/` for Wheeler's session and state files.
- Writes a minimal `wheeler.yaml` with sensible defaults (project name = directory name; Neo4j at `bolt://localhost:7687` with username `neo4j` and password `research-graph`).
- Writes a project-local `.mcp.json` registering the four Wheeler MCP servers (`wheeler_core`, `wheeler_query`, `wheeler_mutations`, `wheeler_ops`) and the Neo4j MCP server, so Claude Code picks them up automatically when run inside this project.
- Installs the `/wh:*` slash commands and Wheeler agents to `~/.claude/` so they work in any Claude Code session, and registers the same MCP servers globally as a fallback.

The Wheeler install pulls in `fastembed` for semantic search over the knowledge graph. It downloads a 33MB embedding model on first use (runs entirely locally, no network after the initial fetch).

## Step 3: Adjust the config if your Neo4j password is non-default

If you used `research-graph` as the Neo4j password in Step 1, you can skip this step entirely.

If you chose a different password (or a different URI / database), edit the generated `wheeler.yaml`:

```yaml
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: <your password>     # change to what you set in Neo4j Desktop
  database: neo4j
```

Or export the four environment variables instead, which override `wheeler.yaml` field by field and keep the password out of the project directory:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="<your password>"
export NEO4J_DATABASE="neo4j"
```

The `neo4j` MCP server entry in `.mcp.json` reads the same four names (its `env` block is templated as `${NEO4J_URI:-bolt://localhost:7687}` and so on), so exporting them covers both Wheeler and that server. If you edited `wheeler.yaml` rather than exporting, set `env.NEO4J_PASSWORD` in `.mcp.json` to match, or the Neo4j MCP server will still try the default.

Or, if you would rather the password lived in neither the file nor your shell profile, `wheeler login` stores it in your OS keychain and validates it by connecting first:

```bash
pip install 'wheeler[login]'
wheeler login --uri bolt://localhost:7687 --username neo4j   # prompts for the password, no echo
wheeler login --status                                        # which layer is supplying what
```

The full precedence chain is env > keychain > `wheeler.yaml` > default. See "Where each setting comes from" under the Aura section in Step 1 for the details, including the one trap: an exported `NEO4J_URI` outranks a stored credential.

## Step 4: Initialize the graph schema

Make sure Neo4j Desktop shows the database as "Running" (green dot), then from inside your project directory:

```bash
cd my-research-project
wheeler graph init
```

This sets up the database structure Wheeler needs (uniqueness constraints and indexes). Safe to run multiple times. If you see "connection refused" or a timeout, Neo4j is not running; click Start in Neo4j Desktop and retry.

Verify it worked:

```bash
wheeler graph status
```

You should see node counts (all zeros on a fresh graph, which is expected).

## Step 5: Verify with `wheeler doctor`

Wheeler ships a sanity-check command that reports the state of every part of the install:

```bash
wheeler doctor
```

You should see a table with green checks for Python, deps, MCP server scripts, Claude Code, slash commands, and Neo4j. If Neo4j shows a warning (`⚠`), recheck Step 4. If `Claude Code CLI` shows a warning, install it (next step).

## Step 6: Install Claude Code (if not already)

```bash
npm install -g @anthropic-ai/claude-code
```

(If `npm` is not found, install Node.js first: https://nodejs.org/ or `brew install node` on macOS.)

Then verify the connection by opening Claude Code in your project:

```bash
cd my-research-project
claude
```

Inside Claude Code, type `/mcp`. You should see `wheeler_core`, `wheeler_query`, `wheeler_mutations`, `wheeler_ops`, and `neo4j` listed as connected. If a server shows "disconnected", run `wheeler doctor` in a separate terminal to diagnose.

## Step 7: Start using Wheeler

The basic workflow:

```
/wh:start                # begin every session here (routes to the right command)
/wh:discuss              # sharpen the research question
/wh:plan                 # structure the investigation
/wh:execute              # run analyses with full provenance
/wh:write                # draft findings with strict citations
```

You can also just describe your task and Wheeler will auto-route to the right command if your intent is unambiguous (e.g., "add this DOI to the knowledge graph" fires `/wh:add` directly).

`wheeler init` (Step 2) already scaffolded your project mechanically. If you want a guided in-session walkthrough that adds your first hypothesis, registers your primary datasets, and bootstraps the knowledge graph from existing files, run `/wh:init` inside Claude Code. It's optional but useful on day one.

### Quick orientation

| Command | What it does |
|---------|-------------|
| `/wh:init` | Interactive setup: adds first hypothesis/dataset, scans workspace, can also restore from a backup |
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
| `/wh:asta` | Route a research task to an external Asta service (literature, citations, theories) and ingest the result with provenance |

### External research services (Asta)

Wheeler can pull external research tools into the graph as provenance-tracked nodes. The AllenAI [Asta](https://github.com/allenai/asta-plugins) services (Paper Finder, Semantic Scholar, Theorizer, Literature Reports) ship enabled: install the `asta` CLI and run `asta auth login`, then `/wh:asta` routes a task to the right one (or use `/wh:asta-lit`, `/wh:asta-scholar`, `/wh:asta-theorize`, `/wh:asta-report` directly). Each run is recorded as one Execution with its inputs and outputs wired into the graph; a failed call is recorded as failed rather than silently lost. Curate which services are enabled with `wheeler services list` / `wheeler services enable <id>` / `wheeler services disable <id>`.

To integrate a NEW external tool (yours or a third party), use the `wheeler-service-creator` skill: it scaffolds the adapter, bakes in the provenance and failsafe wiring, and audits it before it lands. Do not hand-write an adapter.

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

## Two volumes: node content and edges

Wheeler's state lives in two places that do not overlap. This is easy to get half-right, and half-right means half a graph.

**Volume 1: node content lives only in `knowledge/*.json`.** The Neo4j node holds `id`, `type`, `tier`, a title truncated to roughly 100 characters, a file pointer, timestamps, and a few filterable fields. The description, the full text, the numbers, the parameters: those live in the JSON file and nowhere else. Regenerating a node's JSON from the graph is not something Wheeler can do in general, which is why `graph_consistency_check` refuses to try (`wheeler/consistency.py:128` marks the graph-only case "warn only (regenerating JSON from graph is complex)"). Lose `knowledge/` and you keep an index pointing at content that no longer exists.

**Volume 2: edges live only in Neo4j.** A node's JSON has no relationships field. Every `USED`, `WAS_GENERATED_BY`, `SUPPORTS`, `CITES`, `CONTRADICTS` edge exists as a Neo4j relationship and nowhere else. Lose the database and you keep every finding with no provenance chain connecting any of them.

**`synthesis/*.md` is derived and rebuildable.** It is rendered from the JSON (plus the graph, for backlinks). It is there for Obsidian and for humans, never as a source of truth: `graph_consistency_check --repair` regenerates a missing synthesis file from the JSON without asking.

So: persist both volumes or lose half the graph.

- `wheeler backup` writes one archive containing both: the project tree (including `knowledge/`) plus a live Neo4j dump and a manifest. This is the safe default.
- Committing `knowledge/` to git captures all the content and none of the edges.
- A Neo4j dump alone captures all the edges and none of the content.

The same asymmetry explains what a "restore" has to do: replay the JSON to rebuild node content, then replay the graph to rebuild the relationships between those nodes.

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

**Note:** the headless launcher `bin/wh` is currently a bash script and only ships with the source repo, not the PyPI wheel. If you installed Wheeler via `uv tool install wheeler` and want these commands, clone the repo and add `bin/wh` to your `$PATH` (e.g. `sudo ln -sf $PWD/bin/wh /usr/local/bin/wh`). A native `wheeler queue / quick / dream` is on the roadmap; for now use the bash launcher or invoke `claude -p "..."` directly.

## Troubleshooting

Run `wheeler doctor` first. It surfaces nearly every issue below as a single `⚠`/`✗` row with the missing detail.

### "command not found: wheeler"

The `~/.local/bin` directory (where `uv tool install` places binaries) is not on your `$PATH`. Run `uv tool update-shell` and open a new terminal. Verify with `which wheeler`.

### "graph status returns all zeros"

That is the expected state on a fresh graph. If you ran `/wh:ingest` and still see zeros, make sure Neo4j is running (Neo4j Desktop should show a green "Running" indicator) and that `wheeler doctor` reports `Neo4j reachable: ✓`.

### "MCP server not connected"

Restart Claude Code (`/exit` then `claude` again). Wheeler writes MCP servers to two places: the project-local `.mcp.json` (which Claude Code prefers when run inside the project) and `~/.claude/settings.json` (the global fallback). If `wheeler doctor` shows the four `wheeler-*-mcp` scripts present on PATH but Claude Code says disconnected, the most common cause is that the paths in `.mcp.json` are stale (e.g., you initially ran `uvx wheeler init` and uv has since evicted that cache entry). Re-run `wheeler init .` from inside the project to refresh the paths, or upgrade to a persistent install with `uv tool install wheeler`.

### "knowledge/ or synthesis/ directory does not exist"

Both directories are created lazily on first write. If you want them present up front, run `/wh:init` inside Claude Code.

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

### Remote (Aura) instance not reachable

For a hosted instance the port check above is the wrong probe. Check three things in order:

1. **The instance is running.** Aura Free pauses idle instances. Resume it from https://console.neo4j.io.
2. **The scheme is `neo4j+s://`.** Aura requires encryption. `bolt://` against an Aura host fails at the handshake, not at DNS, so the error can look like an auth problem.
3. **The URI actually in use.** Four layers can supply it, so ask rather than infer:

```bash
wheeler login --status
```

One row per field, naming the winning layer (`env`, `keychain`, `yaml`, `default`) and where it came from. `bin/wh` also prints which host and port it probed when the probe fails.

If you get a WARNING about `CREATE DATABASE` failing and the isolation model being downgraded, that is expected on Aura Free: see the Aura section under Step 1.

### `wheeler login` worked but Wheeler still connects to localhost

An environment variable is outranking the stored credential. Precedence is env > keychain > `wheeler.yaml` > default, so a `NEO4J_URI` exported in `.zshrc` months ago wins over the credential you stored a minute ago.

```bash
wheeler login --status
```

It names the offending variables explicitly when a stored credential is being shadowed. Unset them (`unset NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD NEO4J_DATABASE`) and remove the exports from your shell profile.

Two other possibilities the same output rules out:

- **Nothing was stored.** The "Stored profiles" line is empty. `wheeler login` exits non-zero and stores nothing when validation fails, so check that it actually reported `Saved to the OS keychain`.
- **The wrong profile is active.** If you logged in with `--profile prod`, set `WHEELER_PROFILE=prod`. The status table shows which profile it read.

If the `neo4j` MCP server (raw Cypher) is the one pointed at the wrong place, that is expected: it is the third-party `mcp-neo4j-cypher`, and its `env` block in `.mcp.json` reads environment variables only. It cannot see the keychain. Export the four variables to point it at the same instance.

### "No usable OS keychain"

`wheeler login` needs the optional `keyring` package and a keychain backend:

```bash
pip install 'wheeler[login]'
```

On a headless Linux box there may be no backend at all (no libsecret, no D-Bus session), which the message says explicitly. Use the four environment variables there: that is what they are for. Nothing else in Wheeler is affected, since the keychain layer reports itself unavailable and the other three layers behave as usual.

If a keychain access prompt appears and you would rather not deal with it, `WHEELER_NO_KEYCHAIN=1` skips the keychain entirely.

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
