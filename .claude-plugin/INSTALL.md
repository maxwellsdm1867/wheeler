<!-- GENERATED FILE. Do not edit.
     Source: wheeler/build_plugin.py
     Regenerate: python -m wheeler.build_plugin -->

# Wheeler as a plugin

39 research acts and the four Wheeler MCP servers, for Claude Code and
OpenAI Codex. Pinned to Wheeler `0.15.0`.

> **The pinned version must be on PyPI before this plugin works.** The skills fetch
> their instructions by calling the `get_act` MCP tool, so `uvx --from
> wheeler>=0.15.0` has to resolve to a release that actually provides it. If
> `0.15.0` is not published yet, every skill will load and then report that
> `get_act` is unavailable. Publish first, then install.
>
> Developers: `uv` can satisfy `wheeler>=0.15.0` from a locally built artifact of
> the source tree, so the plugin appears to work on the machine it was built on and
> fails everywhere else. Verify against a clean `UV_CACHE_DIR` outside the repo.

## Prerequisites

- **`uv`** (provides `uvx`). The MCP servers launch as
  `uvx --from wheeler>=0.15.0 wheeler-<role>-mcp`, so nothing is installed into
  your environment and the plugin cannot drift from the package. Install it with
  `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`. The first
  launch resolves the package once (about 13 s); after that the launch overhead is
  around 370 ms, which matches running the console script directly.
- **Neo4j**, reachable at `bolt://localhost:7687` by default. Wheeler stores graph
  metadata there; see the repository README for the container recipe.

## Claude Code

```bash
claude plugin marketplace add maxwellsdm1867/wheeler
claude plugin install wh@wheeler
```

From a clone, or to try it before adding the marketplace:

```bash
claude --plugin-dir /path/to/wheeler
```

Acts are then `/wh:plan`, `/wh:execute`, `/wh:chat`
and so on. The plugin name supplies the `wh:` namespace, so every command
is spelled exactly as it was before.

### If the `/wh:` commands are missing on first launch

Start a new session before concluding the install is broken. Skill registration
has been observed to lose the race with session startup: in one run out of three,
the four MCP servers connected but no `/wh:` command was registered.
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
codex plugin marketplace add maxwellsdm1867/wheeler
codex plugin add wh@wheeler
```

There is no `codex plugin install`: the subcommands are `add`, `list`, `marketplace`
and `remove`, and `add` takes a `PLUGIN@MARKETPLACE` selector rather than a URL. The
marketplace source may be a local path, `owner/repo[@ref]`, or an HTTPS or SSH Git
URL, so from a clone this also works:

```bash
codex plugin marketplace add /path/to/wheeler
codex plugin add wh@wheeler
```

Verified end to end against `codex-cli 0.146.0`: the marketplace resolves, the plugin
lists as `wh@wheeler`, and installing it lands all the skills
plus the MCP config.

Codex reads `.codex-plugin/plugin.json`, the same `skills/` tree, and the same
MCP config. It also reads this repository's `.claude-plugin/marketplace.json` as a
legacy-compatible marketplace, which is why one catalog file serves both hosts and
there is no separate `.agents/plugins/marketplace.json` here.

Acts are invoked as `${act}` (for example `$plan`), or picked from the `/skills`
browser. Start a new session after installing, or the bundled skills and MCP servers
will not be loaded yet.

### Mode profiles

Claude Code enforces Wheeler's modes through each skill's `allowed-tools`. Codex has
no per-skill tool gate, so modes are profiles instead: Codex filters tools when it
registers an MCP server, which removes the capability rather than asking the model
not to use it.

| Profile | Servers | Effect |
| --- | --- | --- |
| `wheeler-chat` | wheeler_core, wheeler_query | read-only: the graph can be read and searched, never written |
| `wheeler-write` | wheeler_core, wheeler_query, wheeler_mutations | reads plus graph writes, without the ops and validator surface |
| `wheeler-execute` | wheeler_core, wheeler_query, wheeler_mutations, wheeler_ops | the full surface, including validators and scanners |

```bash
cp codex-profiles/wheeler-chat.config.toml $CODEX_HOME/
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
python -m wheeler.build_plugin           # write
python -m wheeler.build_plugin --check   # fail on drift, write nothing
```
