"""Generate the `wh` plugin tree for Claude Code and Codex from one source.

Why this exists
---------------
Wheeler ships 39 acts. Historically they were installed by copying markdown into
`~/.claude/commands/wh/`, which only Claude Code can read. Supporting a second host
(OpenAI Codex) by copying them again would mean maintaining act content twice, so
instead:

* the act BODY is served over MCP by `wheeler_core.get_act()` (see `wheeler/acts.py`),
* each host gets a thin generated SKILL.md stub that calls it.

Everything here is generated from `wheeler/_data/commands/*.md` and
`wheeler/_data/agents/*.md`. Nothing is authored twice, and nothing in the emitted
tree should ever be hand-edited.

The plugin is named `wh`, and that is load-bearing
--------------------------------------------------
Claude Code namespaces plugin skills as `/<plugin-name>:<skill-name>`. Verified by
canary: a plugin named `wh` with `skills/zzprobe/SKILL.md` loaded via
`claude --plugin-dir` responds to `/wh:zzprobe`. So plugin `wh` plus a skill directory
`plan/` yields `/wh:plan`, byte-identical to the pre-plugin slash command, and the
migration is invisible to existing users.

Three consequences the emitter must respect:

* Skill directories are named by the act id with the `wh:` prefix STRIPPED
  (`name: wh:chat` -> `skills/chat/`). Emitting `skills/wh-chat/` would produce
  `/wh:wh-chat`.
* `allowed-tools` is carried through, and Claude Code honours it in plugin-shipped
  skills, which is how CHAT/WRITE/EXECUTE mode enforcement survives the move.
  Codex accepts the key but does not enforce it, hence the mode profiles. Two
  entries are ADDED rather than copied: `get_act` (the stub cannot read its own
  instructions through a gate that omits the tool it is told to call), and a
  plugin-scoped alias for every Wheeler MCP grant, because a plugin's servers are
  namespaced and the tool ids therefore change. See `skill_allowed_tools`: getting
  that second one wrong denies every Wheeler tool to every act.
* Frontmatter goes FIRST in the file, and the generated-file banner after it.
  Frontmatter parsers require the document to open with `---`; a leading comment
  makes the whole block invisible, which would silently drop `description` and
  `allowed-tools` (checked against every SKILL.md installed on a real machine: all
  of them open with `---`).

Zero-install MCP servers
------------------------
Neither host can run a postinstall hook, so a plugin cannot `pip install`. It does not
need to: `wheeler` is on PyPI with all four MCP console scripts, and `uvx` runs them
with no prior install. Measured cost is 13 s once to populate the uv cache, then
~370 ms per launch, which matches running the console script directly.

The emitted MCP config uses a `wheeler>=<version>` FLOOR rather than `==`. The floor
is the contract: the stubs call `get_act`, which only exists from the release that
added `wheeler/acts.py`, so anything older silently yields 39 inert skills. Allowing
newer is the safe direction, and it means a plugin installed from an older commit
keeps working after the package moves on. An `==` pin also created a window where a
freshly pushed bump referenced a version PyPI had not published yet.

The emitted tree is COMMITTED
-----------------------------
`claude --plugin-dir <clone>` and a marketplace install from a clone both read the
tree straight off disk, so gitignoring it would make a fresh clone an empty plugin.
Committed generated output can go stale silently, so `--check` compares disk against
what the generator would produce and `tests/test_build_plugin.py` runs it.

    python -m wheeler.build_plugin            # write
    python -m wheeler.build_plugin --check    # fail on drift, write nothing
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from importlib import resources
from pathlib import Path

from wheeler.acts import Act, load_acts

# The plugin name IS the slash-command namespace. Do not change it without
# re-running the canary check described in the module docstring: renaming it to
# "wheeler" would turn every /wh:plan into /wheeler:plan overnight.
PLUGIN_NAME = "wh"
DISPLAY_NAME = "Wheeler"
MARKETPLACE_NAME = "wheeler"
REPO = "maxwellsdm1867/wheeler"
AUTHOR = "Arthur Hong"

# The plugin root is this repository root, and `.mcp.json` there is already the
# DEV config (editable install via .venv). So the generated plugin MCP config gets
# its own filename and both manifests reference it explicitly. Both hosts accept
# `mcpServers` as a path, so neither needs the conventional filename.
MCP_JSON_NAME = ".mcp-plugin.json"

SKILLS_DIR = "skills"
AGENTS_DIR = "agents"
HOOKS_DIR = "hooks"
PROFILES_DIR = "codex-profiles"

CLAUDE_MANIFEST = ".claude-plugin/plugin.json"
MARKETPLACE_MANIFEST = ".claude-plugin/marketplace.json"
INSTALL_DOC = ".claude-plugin/INSTALL.md"
CODEX_MANIFEST = ".codex-plugin/plugin.json"
CODEX_AGENT_META = f"{AGENTS_DIR}/openai.yaml"
HOOKS_CONFIG = f"{HOOKS_DIR}/hooks.json"
SHADOW_HOOK = f"{HOOKS_DIR}/wheeler-legacy-shadow-check.js"

REGEN_CMD = "python -m wheeler.build_plugin"

# server name -> (console script, one-line role for the Codex dependency block)
MCP_SERVERS: tuple[tuple[str, str, str], ...] = (
    (
        "wheeler_core",
        "wheeler-core-mcp",
        "Graph health, status, context, semantic search, raw Cypher, acts",
    ),
    ("wheeler_query", "wheeler-query-mcp", "Read-only typed graph listings"),
    (
        "wheeler_mutations",
        "wheeler-mutations-mcp",
        "Graph writes: add_*, link_nodes, update_node, set_tier",
    ),
    (
        "wheeler_ops",
        "wheeler-ops-mcp",
        "Validators, scanners, consistency and provenance operations",
    ),
)

SERVER_NAMES = tuple(name for name, _script, _role in MCP_SERVERS)

# Which servers each mode may reach. Mode is enforced on Claude Code by the
# per-skill `allowed-tools` carried through from the act; on Codex it is enforced
# here, by which servers are registered at all.
MODE_SERVERS: dict[str, tuple[str, ...]] = {
    "chat": ("wheeler_core", "wheeler_query"),
    "write": ("wheeler_core", "wheeler_query", "wheeler_mutations"),
    "execute": ("wheeler_core", "wheeler_query", "wheeler_mutations", "wheeler_ops"),
}

MODE_BLURB: dict[str, str] = {
    "chat": "read-only: the graph can be read and searched, never written",
    "write": "reads plus graph writes, without the ops and validator surface",
    "execute": "the full surface, including validators and scanners",
}

# The stub body calls this, so the gate must permit it even for acts whose
# `allowed-tools` predates the tool.
GET_ACT_TOOL = "mcp__wheeler_core__get_act"
CORE_WILDCARD = "mcp__wheeler_core__*"

# Claude Code namespaces a plugin's MCP servers, so `wheeler_core` shipped by
# plugin `wh` registers as `plugin:wh:wheeler_core` and its tools as
# `mcp__plugin_wh_wheeler_core__<tool>`. Read off the CLI's own init event; see
# `skill_allowed_tools` for why it is load-bearing.
PLUGIN_TOOL_NAMESPACE = f"plugin_{PLUGIN_NAME}_"

GENERATED_BANNER = (
    "<!-- GENERATED FILE. Do not edit.\n"
    "     Source: wheeler/_data/commands/{filename}\n"
    f"     Regenerate: {REGEN_CMD}\n"
    "     The act body is served over MCP by wheeler_core.get_act(), so it is\n"
    "     deliberately absent here: there is exactly one copy of it. -->"
)
GENERATED_HASH = (
    f"# GENERATED FILE. Do not edit. Regenerate: {REGEN_CMD}"
)


def _repo_root() -> Path:
    """Return the repository root (the directory holding pyproject.toml)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repository root from " + str(here))


def package_version(root: Path | None = None) -> str:
    """Read the version from pyproject.toml so manifests cannot drift from it."""
    root = root if root is not None else _repo_root()
    data = tomllib.loads((root / "pyproject.toml").read_text())
    return str(data["project"]["version"])


def agent_data_dir() -> Path:
    """Return the packaged subagent directory, `wheeler/_data/agents/`."""
    return Path(str(resources.files("wheeler") / "_data" / AGENTS_DIR))


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


def _yaml_scalar(value: str) -> str:
    """Quote a frontmatter scalar when it could otherwise be misparsed.

    Act descriptions routinely contain colons, which is exactly what breaks naive
    YAML emission, so this is not defensive padding.
    """
    if value == "":
        return '""'
    needs_quotes = any(ch in value for ch in ':#{}[]&*!|>%@`"\'\n') or value[0] in "-? "
    if not needs_quotes:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def plugin_scoped_tool(tool: str) -> str | None:
    """Return the plugin-namespaced alias of a Wheeler MCP tool id, or None.

    `mcp__wheeler_core__graph_status` -> `mcp__plugin_wh_wheeler_core__graph_status`.
    Non-MCP tools (`Read`, `Bash`) and third-party MCP tools have no alias.
    """
    for server in SERVER_NAMES:
        prefix = f"mcp__{server}__"
        if tool.startswith(prefix):
            return f"mcp__{PLUGIN_TOOL_NAMESPACE}{server}__{tool[len(prefix) :]}"
    return None


def skill_allowed_tools(act: Act) -> tuple[str, ...]:
    """The act's `allowed-tools`, plus `get_act`, plus plugin-scoped aliases.

    Claude Code enforces this list for plugin-shipped skills, and two things about
    it are not obvious.

    First, `get_act`. An act granted explicit `mcp__wheeler_core__*` tool NAMES but
    not `get_act` would be told to fetch its own instructions through a gate that
    blocks the fetch, leaving the skill inert.

    Second, and worse: **a plugin's MCP servers are namespaced, so the tool ids
    change.** Verified from the CLI's own init event under `--plugin-dir`: the four
    servers register as `plugin:wh:wheeler_core` and friends, and their tools as
    `mcp__plugin_wh_wheeler_core__graph_status`. An act's own
    `mcp__wheeler_core__graph_status` matches only a server configured OUTSIDE the
    plugin (a user-scope `~/.claude.json` entry, or the repo's dev `.mcp.json`). So
    carrying `allowed-tools` through verbatim would deny every Wheeler tool to
    every act as soon as the servers come from the plugin, which is the whole point
    of shipping one.

    Both forms are therefore emitted. Each entry still names one specific tool, so
    mode enforcement is unchanged: this widens nothing, it just spells the same
    grant for both places the server can come from.
    """
    tools = list(act.allowed_tools)
    if not tools:
        return ()
    if not (GET_ACT_TOOL in tools or CORE_WILDCARD in tools):
        tools.append(GET_ACT_TOOL)
    aliases: list[str] = []
    for tool in tools:
        alias = plugin_scoped_tool(tool)
        if alias is not None and alias not in tools and alias not in aliases:
            aliases.append(alias)
    return (*tools, *aliases)


def render_skill(act: Act) -> str:
    """Render one `SKILL.md` stub for *act*.

    The stub carries the routing metadata (so both hosts can match it) and defers
    the actual instructions to `get_act`. It stays short on purpose: duplicating the
    body here is the thing this whole module exists to avoid.

    Frontmatter comes first. A parser that does not see `---` on line 1 treats the
    whole block as prose, which would drop `description` and `allowed-tools` and
    take Claude Code's mode enforcement with them.
    """
    lines = [
        "---",
        f"name: {act.act_id}",
        f"description: {_yaml_scalar(act.description)}",
    ]
    if act.argument_hint:
        lines.append(f"argument-hint: {_yaml_scalar(act.argument_hint)}")
    tools = skill_allowed_tools(act)
    if tools:
        lines.append("allowed-tools:")
        lines.extend(f"  - {tool}" for tool in tools)
    lines += [
        "---",
        "",
        GENERATED_BANNER.format(filename=act.filename),
        "",
        f'Call `get_act` on the `wheeler_core` MCP server with `name="{act.act_id}"`,',
        "then follow the returned instructions exactly. They are the authoritative",
        "definition of this act. Do not improvise the workflow or substitute your own",
        "plan for it.",
        "",
        'Pass `host="codex"` when running under Codex so the orchestration guidance',
        "matches the tools this host actually has.",
        "",
        f"Mode: `{act.mode}`. Orchestration: `{act.orchestration}`.",
        "",
        "If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so",
        "rather than guessing at the workflow: acting without the act text is how",
        "provenance gets silently skipped.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------


def render_mcp_json(version: str) -> dict:
    """The plugin's bundled MCP server config: zero-install via uvx, version pinned.

    Emitted as a bare server map, not wrapped in `mcpServers`. Both shapes appear
    in plugins in the wild, but the bare map is what Anthropic's own
    `example-plugin/.mcp.json` ships and what the plugin reference describes for
    the object form ("keys are MCP server names"), so it is the form a
    path-valued `mcpServers` is most likely read as. Verified by canary against
    the real CLI: see `tests/test_build_plugin.py`.
    """
    return {
        name: {
            "type": "stdio",
            "command": "uvx",
            "args": ["--from", f"wheeler>={version}", script],
        }
        for name, script, _role in MCP_SERVERS
    }


def render_claude_plugin(version: str) -> dict:
    return {
        "name": PLUGIN_NAME,
        "displayName": DISPLAY_NAME,
        "version": version,
        "description": (
            "Provenance-tracked research assistant: a Neo4j knowledge graph over your "
            "files, with 39 research acts and 51 MCP tools."
        ),
        "author": {"name": AUTHOR},
        "homepage": f"https://github.com/{REPO}",
        "repository": f"https://github.com/{REPO}.git",
        "license": "MIT",
        "keywords": ["science", "research", "knowledge-graph", "provenance", "neo4j"],
        # Explicit path rather than the conventional `.mcp.json`, because the plugin
        # root IS this repository root and `.mcp.json` there is the DEV config
        # (it launches `.venv/bin/python -m wheeler.mcp_core` against a local
        # checkout). Overwriting it would break every contributor's editable
        # install. Both host manifests point at the generated file instead.
        "mcpServers": f"./{MCP_JSON_NAME}",
    }


def render_marketplace(version: str) -> dict:
    """Catalog entry.

    The catalog and the plugin share this one repo, so the entry's `source` is the
    marketplace root itself. That is the form proven to work on a local checkout;
    `metadata.pluginRoot` exists to let sources be written bare when plugins sit in
    subdirectories, and is carried here as the explicit no-op `"."` so the intent is
    on the record rather than inferred from its absence.
    """
    return {
        "name": MARKETPLACE_NAME,
        "owner": {"name": AUTHOR, "url": f"https://github.com/{REPO}"},
        "metadata": {
            "description": "Wheeler: provenance-tracked research assistant.",
            "version": version,
            "pluginRoot": ".",
        },
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": "./",
                "description": (
                    "Provenance-tracked research assistant over a Neo4j knowledge graph."
                ),
                "version": version,
                "author": {"name": AUTHOR},
                "homepage": f"https://github.com/{REPO}",
                "license": "MIT",
                "category": "Education & Research",
                "tags": ["research", "knowledge-graph", "provenance"],
            }
        ],
    }


def render_codex_plugin(version: str) -> dict:
    """`.codex-plugin/plugin.json`.

    Component paths are plugin-root relative and must begin with `./`. The same
    `skills/` tree serves both hosts, which is the point of the build.
    """
    return {
        "name": PLUGIN_NAME,
        "version": version,
        "description": (
            "Provenance-tracked research assistant: a Neo4j knowledge graph over your files."
        ),
        "author": {"name": AUTHOR, "url": f"https://github.com/{REPO}"},
        "homepage": f"https://github.com/{REPO}",
        "license": "MIT",
        "mcpServers": f"./{MCP_JSON_NAME}",
        "skills": f"./{SKILLS_DIR}/",
        "hooks": f"./{HOOKS_CONFIG}",
        "interface": {
            "displayName": DISPLAY_NAME,
            "shortDescription": "Research with a provenance-tracked knowledge graph",
            "longDescription": (
                "Wheeler records research as a graph: findings, hypotheses, datasets, "
                "scripts and executions, wired together with W3C PROV relationships. "
                "Claims cite graph nodes, a script whose hash stops matching disk marks "
                "everything downstream of it stale, and each act is a mode with its own "
                "tool access."
            ),
            "developerName": AUTHOR,
            "category": "Developer Tools",
            "capabilities": ["Interactive", "Read", "Write"],
            "websiteURL": f"https://github.com/{REPO}",
            "defaultPrompt": [
                "Start a Wheeler research session",
                "What does the knowledge graph say about this dataset?",
            ],
        },
    }


def render_openai_yaml() -> str:
    """Codex interface + dependency declaration.

    `dependencies.tools` is what makes Codex auto-wire the servers. Without it users
    hit "The following MCP servers are required by the selected skills but are not
    installed yet."
    """
    lines = [
        GENERATED_HASH,
        "interface:",
        f"  display_name: {DISPLAY_NAME}",
        "  short_description: Provenance-tracked research assistant",
        "  long_description: >-",
        "    A Neo4j knowledge graph indexed over your research files, with 39 acts",
        "    covering the research loop (discuss, plan, execute, write) and 51 MCP",
        "    tools. Every claim traces to a node; every artifact carries provenance.",
        "policy:",
        "  # Acts carry narrow descriptions, so implicit selection is wanted: it is how",
        "  # /wh:ask fires on a provenance question without the user naming a command.",
        "  allow_implicit_invocation: true",
        "dependencies:",
        "  tools:",
    ]
    for name, _script, role in MCP_SERVERS:
        lines += [
            '    - type: "mcp"',
            f'      value: "{name}"',
            f'      description: "{role}"',
            '      transport: "stdio"',
        ]
    return "\n".join(lines) + "\n"


def render_mode_profile(mode: str, version: str) -> str:
    """Render a Codex profile-v2 file for *mode*.

    Two traps encoded here:

    1. Profile merge is RECURSIVE, so a profile cannot un-declare a server: the base
       table survives. There is no `mcp_servers = {}` reset. So the profile must write
       `enabled = false` for every server NOT in the mode. Emitting only the positive
       set would leave "chat" holding write access, silently.
    2. Top-level keys only. A legacy `[profiles.<name>]` table and the
       `profile = "..."` selector are both dead as of Codex 0.134.0.
    """
    allowed = MODE_SERVERS[mode]
    disabled = tuple(n for n in SERVER_NAMES if n not in allowed)
    lines = [
        GENERATED_HASH,
        "#",
        f"# Wheeler {mode.upper()} mode: {MODE_BLURB[mode]}.",
        "#",
        f"# Install:  cp {PROFILES_DIR}/wheeler-{mode}.config.toml $CODEX_HOME/",
        f"# Select:   codex --profile wheeler-{mode}",
        "#",
        "# Mode is enforced by CAPABILITY, not by instructions: the servers below are",
        "# either registered or absent, so a disallowed tool is not in the tool list at",
        "# all rather than merely discouraged. Codex filters at registration time.",
        "#",
        f"# Reachable: {', '.join(allowed)}",
        f"# Disabled:  {', '.join(disabled) if disabled else '(none)'}",
        "",
    ]
    for name, script, _role in MCP_SERVERS:
        lines.append(f"[mcp_servers.{name}]")
        if name in allowed:
            lines += [
                'command = "uvx"',
                f'args = ["--from", "wheeler>={version}", "{script}"]',
                "enabled = true",
            ]
        else:
            # The explicit false is the whole point: omitting the table would let the
            # base config's enabled server survive the merge.
            lines.append("enabled = false")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def render_hooks_json() -> dict:
    """One SessionStart hook, reporting a legacy install that shadows the plugin.

    `wheeler install` puts act files in `~/.claude/commands/wh/`, and user-level
    commands WIN over plugin skills of the same name, so a machine carrying both
    silently runs the legacy copies and the plugin looks broken. `wheeler doctor`
    and `wheeler migrate-to-plugin` handle it from the CLI side; this covers the
    case where nobody thinks to run either, because the symptom is invisible.
    """
    return {
        "description": (
            "Warn when a legacy `wheeler install` is shadowing the plugin's /wh:* skills."
        ),
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'node "${{CLAUDE_PLUGIN_ROOT}}/{SHADOW_HOOK}"',
                            "timeout": 5,
                        }
                    ]
                }
            ]
        },
    }


def render_shadow_hook() -> str:
    """The SessionStart script.

    node rather than a shell one-liner: the host itself runs on node, so it is the
    one interpreter guaranteed present on every platform the host supports.
    """
    return f"""#!/usr/bin/env node
// GENERATED FILE. Do not edit. Regenerate: {REGEN_CMD}
//
// SessionStart: report a legacy `wheeler install` that is shadowing this plugin's
// skills. User-level commands in ~/.claude/commands/wh/ win over plugin skills of
// the same name, so a machine carrying both runs the legacy copies and the plugin
// looks broken. Silent when there is no legacy install, which is the normal case.

const fs = require('fs');
const os = require('os');
const path = require('path');

const legacyDir = path.join(os.homedir(), '.claude', 'commands', 'wh');

let files = [];
try {{
  files = fs
    .readdirSync(legacyDir)
    .filter((f) => f.endsWith('.md') && f !== 'CLAUDE.md');
}} catch (err) {{
  process.exit(0);
}}

if (files.length === 0) {{
  process.exit(0);
}}

const shadowed = files
  .map((f) => '/{PLUGIN_NAME}:' + f.replace(/\\.md$/, ''))
  .sort()
  .join(', ');

process.stdout.write(
  '[wheeler] A legacy `wheeler install` is present at ' +
    legacyDir +
    ' (' +
    files.length +
    ' command files). User-level commands shadow plugin skills of the same ' +
    'name, so these resolve to the legacy copies rather than the {PLUGIN_NAME} ' +
    'plugin: ' +
    shadowed +
    '. Run `wheeler migrate-to-plugin` to remove them and let the plugin take ' +
    'over. Tell the user once, then continue with their request.\\n'
);
"""


# ---------------------------------------------------------------------------
# Install doc
# ---------------------------------------------------------------------------


def render_install_doc(version: str, act_count: int) -> str:
    """The plugin's own README.

    Lives under `.claude-plugin/` rather than at the plugin root, because the root
    README.md is the repository's.
    """
    modes = "\n".join(
        f"| `wheeler-{m}` | {', '.join(MODE_SERVERS[m])} | {MODE_BLURB[m]} |"
        for m in ("chat", "write", "execute")
    )
    return f"""<!-- GENERATED FILE. Do not edit.
     Source: wheeler/build_plugin.py
     Regenerate: {REGEN_CMD} -->

# Wheeler as a plugin

{act_count} research acts and the four Wheeler MCP servers, for Claude Code and
OpenAI Codex. Pinned to Wheeler `{version}`.

> **The pinned version must be on PyPI before this plugin works.** The skills fetch
> their instructions by calling the `get_act` MCP tool, so `uvx --from
> wheeler>={version}` has to resolve to a release that actually provides it. If
> `{version}` is not published yet, every skill will load and then report that
> `get_act` is unavailable. Publish first, then install.
>
> Developers: `uv` can satisfy `wheeler>={version}` from a locally built artifact of
> the source tree, so the plugin appears to work on the machine it was built on and
> fails everywhere else. Verify against a clean `UV_CACHE_DIR` outside the repo.

## Prerequisites

- **`uv`** (provides `uvx`). The MCP servers launch as
  `uvx --from wheeler>={version} wheeler-<role>-mcp`, so nothing is installed into
  your environment and the plugin cannot drift from the package. Install it with
  `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`. The first
  launch resolves the package once (about 13 s); after that the launch overhead is
  around 370 ms, which matches running the console script directly.
- **Neo4j**, reachable at `bolt://localhost:7687` by default. Wheeler stores graph
  metadata there; see the repository README for the container recipe.

## Claude Code

```bash
claude plugin marketplace add {REPO}
claude plugin install {PLUGIN_NAME}@{MARKETPLACE_NAME}
```

From a clone, or to try it before adding the marketplace:

```bash
claude --plugin-dir /path/to/wheeler
```

Acts are then `/{PLUGIN_NAME}:plan`, `/{PLUGIN_NAME}:execute`, `/{PLUGIN_NAME}:chat`
and so on. The plugin name supplies the `{PLUGIN_NAME}:` namespace, so every command
is spelled exactly as it was before.

### If the `/{PLUGIN_NAME}:` commands are missing on first launch

Start a new session before concluding the install is broken. Skill registration
has been observed to lose the race with session startup: in one run out of three,
the four MCP servers connected but no `/{PLUGIN_NAME}:` command was registered.
A fresh session picked them all up. If they are still missing in a second
session, check the legacy-install note above, since a shadowed skill also
presents as a missing one.

### If you previously ran `wheeler install`

User-level commands in `~/.claude/commands/wh/` **shadow** plugin skills of the same
name, so a machine with both keeps running the old copies and nothing says so. Run
`wheeler migrate-to-plugin` to clear them. A SessionStart hook in this plugin also
reports the situation when it finds one.

## OpenAI Codex

```bash
codex plugin marketplace add {REPO}
codex plugin add {PLUGIN_NAME}@{MARKETPLACE_NAME}
```

There is no `codex plugin install`: the subcommands are `add`, `list`, `marketplace`
and `remove`, and `add` takes a `PLUGIN@MARKETPLACE` selector rather than a URL. The
marketplace source may be a local path, `owner/repo[@ref]`, or an HTTPS or SSH Git
URL, so from a clone this also works:

```bash
codex plugin marketplace add /path/to/wheeler
codex plugin add {PLUGIN_NAME}@{MARKETPLACE_NAME}
```

Verified end to end against `codex-cli 0.146.0`: the marketplace resolves, the plugin
lists as `{PLUGIN_NAME}@{MARKETPLACE_NAME}`, and installing it lands all the skills
plus the MCP config.

Codex reads `.codex-plugin/plugin.json`, the same `{SKILLS_DIR}/` tree, and the same
MCP config. It also reads this repository's `.claude-plugin/marketplace.json` as a
legacy-compatible marketplace, which is why one catalog file serves both hosts and
there is no separate `.agents/plugins/marketplace.json` here.

Acts are invoked as `${{act}}` (for example `$plan`), or picked from the `/skills`
browser. Start a new session after installing, or the bundled skills and MCP servers
will not be loaded yet.

### Mode profiles

Claude Code enforces Wheeler's modes through each skill's `allowed-tools`. Codex has
no per-skill tool gate, so modes are profiles instead: Codex filters tools when it
registers an MCP server, which removes the capability rather than asking the model
not to use it.

| Profile | Servers | Effect |
| --- | --- | --- |
{modes}

```bash
cp {PROFILES_DIR}/wheeler-chat.config.toml $CODEX_HOME/
codex --profile wheeler-chat
```

Each profile also writes `enabled = false` for every server outside its mode. That is
deliberate: profile merge is recursive, so a profile cannot un-declare a server it
inherits from the base config, and a profile listing only its positive set would
silently keep write access.

For finer control than whole servers, Codex also accepts `enabled_tools` /
`disabled_tools` per server in the same tables.

## Regenerating

Everything here is generated from `wheeler/_data/commands/*.md` and
`wheeler/_data/agents/*.md`:

```bash
{REGEN_CMD}           # write
{REGEN_CMD} --check   # fail on drift, write nothing
```
"""


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------


def _json_doc(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_plugin_files(root: Path | None = None) -> dict[str, str]:
    """Render the whole plugin tree as {relative path: file content}.

    Pure: renders to memory so `--check` and the drift test can compare against
    disk without writing anything.
    """
    root = Path(root) if root is not None else _repo_root()
    version = package_version(root)
    acts = load_acts()

    files: dict[str, str] = {
        MCP_JSON_NAME: _json_doc(render_mcp_json(version)),
        CLAUDE_MANIFEST: _json_doc(render_claude_plugin(version)),
        MARKETPLACE_MANIFEST: _json_doc(render_marketplace(version)),
        CODEX_MANIFEST: _json_doc(render_codex_plugin(version)),
        CODEX_AGENT_META: render_openai_yaml(),
        HOOKS_CONFIG: _json_doc(render_hooks_json()),
        SHADOW_HOOK: render_shadow_hook(),
        INSTALL_DOC: render_install_doc(version, len(acts)),
    }

    for act in acts:
        files[f"{SKILLS_DIR}/{act.act_id}/SKILL.md"] = render_skill(act)

    # Subagents ship verbatim. Unlike acts they are not fetched over MCP: the host
    # reads their frontmatter directly to decide what to spawn. Read through the
    # package, like `acts.act_data_dir()`, so `root` is only ever consulted for the
    # version and the emitted tree.
    for agent in sorted(agent_data_dir().glob("*.md")):
        files[f"{AGENTS_DIR}/{agent.name}"] = agent.read_text()

    for mode in MODE_SERVERS:
        rel = f"{PROFILES_DIR}/wheeler-{mode}.config.toml"
        files[rel] = render_mode_profile(mode, version)

    return files


def _owned_on_disk(root: Path) -> set[str]:
    """Paths under generator-owned directories, so leftovers can be found.

    An act deleted upstream must not leave its skill directory behind: a host
    would still happily load it.
    """
    owned: set[str] = set()
    for rel in (".claude-plugin", ".codex-plugin", SKILLS_DIR, HOOKS_DIR, PROFILES_DIR):
        base = root / rel
        if not base.is_dir():
            continue
        owned.update(
            p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file()
        )
    if (root / MCP_JSON_NAME).is_file():
        owned.add(MCP_JSON_NAME)
    agents = root / AGENTS_DIR
    if agents.is_dir():
        for p in agents.iterdir():
            if p.is_file() and (p.suffix == ".md" or p.name == "openai.yaml"):
                owned.add(p.relative_to(root).as_posix())
    return owned


def check_plugin(root: Path | None = None) -> list[str]:
    """Return one message per drift between the committed tree and the build.

    An empty list means the committed tree is exactly what the generator produces.
    """
    root = Path(root) if root is not None else _repo_root()
    expected = build_plugin_files(root)
    problems: list[str] = []
    for rel, content in sorted(expected.items()):
        path = root / rel
        if not path.is_file():
            problems.append(f"missing: {rel}")
        elif path.read_text() != content:
            problems.append(f"stale: {rel}")
    problems.extend(
        f"leftover: {rel}" for rel in sorted(_owned_on_disk(root) - set(expected))
    )
    return problems


def write_plugin(root: Path | None = None) -> tuple[list[str], list[str]]:
    """Write the tree. Returns (written, pruned) relative paths.

    Only changed files are rewritten, so mtimes stay meaningful and a no-op run
    reports nothing.
    """
    root = Path(root) if root is not None else _repo_root()
    expected = build_plugin_files(root)

    written: list[str] = []
    for rel, content in sorted(expected.items()):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_text() != content:
            path.write_text(content)
            written.append(rel)

    pruned: list[str] = []
    for rel in sorted(_owned_on_disk(root) - set(expected)):
        (root / rel).unlink()
        pruned.append(rel)
    skills = root / SKILLS_DIR
    if skills.is_dir():
        for sub in sorted(skills.iterdir()):
            if sub.is_dir() and not any(sub.iterdir()):
                sub.rmdir()

    return written, pruned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=REGEN_CMD,
        description="Generate the `wh` plugin tree for Claude Code and Codex.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit non-zero; write nothing",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="plugin root (defaults to the repository containing this module)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else _repo_root()

    if args.check:
        problems = check_plugin(root)
        if problems:
            print(f"plugin tree is out of date ({len(problems)} problems):")
            for problem in problems:
                print(f"  {problem}")
            print(f"\nRegenerate with: {REGEN_CMD}")
            return 1
        print(
            f"plugin tree is up to date "
            f"({len(build_plugin_files(root))} files)"
        )
        return 0

    written, pruned = write_plugin(root)
    acts = load_acts()
    print(f"wheeler plugin '{PLUGIN_NAME}' v{package_version(root)} -> {root}")
    print(f"  {len(acts)} acts, {len(build_plugin_files(root))} files")
    for rel in written:
        print(f"  wrote   {rel}")
    for rel in pruned:
        print(f"  pruned  {rel}")
    if not written and not pruned:
        print("  (already up to date)")
    print(f"  slash commands: /{PLUGIN_NAME}:{acts[0].act_id} ... /{PLUGIN_NAME}:{acts[-1].act_id}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
