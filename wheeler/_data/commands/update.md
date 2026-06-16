---
name: wh:update
description: Check for Wheeler updates and upgrade if available
argument-hint: ""
allowed-tools:
  - Read
  - Bash
  - AskUserQuestion
---

Check for a new Wheeler version and offer to upgrade.

## Step 0: Resolve the Wheeler venv

Wheeler registers its MCP servers in `~/.claude/settings.json` under `mcpServers`.
A modern install uses the SPLIT servers (`wheeler_core`, `wheeler_query`,
`wheeler_mutations`, `wheeler_ops`); the legacy monolith used a single `wheeler`
key (now removed by the installer). Each command resolves to an absolute path in
the same venv bin, e.g. `/Users/me/wheeler-user-test/.venv/bin/wheeler-core-mcp`,
so derive `WHEELER_BIN` from whichever Wheeler key is present:

```bash
python3 -c "
import json, pathlib, os, shutil
def load(p):
    try: return json.loads(pathlib.Path(os.path.expanduser(p)).read_text())
    except Exception: return {}
# Search a project .mcp.json (the session override) BEFORE the global settings,
# so we resolve the install actually serving this session. Split keys first (the
# current shape), then the legacy monolith key.
KEYS = ('wheeler_core', 'wheeler_query', 'wheeler_mutations', 'wheeler_ops', 'wheeler')
bin_dir = ''
for cfg in (load('.mcp.json'), load('~/.claude/settings.json')):
    servers = cfg.get('mcpServers', cfg)  # .mcp.json may keep servers at top level
    for key in KEYS:
        cmd = (servers.get(key) or {}).get('command', '') if isinstance(servers, dict) else ''
        if cmd and os.path.isabs(cmd) and pathlib.Path(cmd).exists():
            bin_dir = str(pathlib.Path(cmd).parent); break
    if bin_dir: break
# Last resort: a Wheeler console script on PATH.
if not bin_dir:
    for name in ('wheeler-core-mcp', 'wheeler'):
        found = shutil.which(name)
        if found: bin_dir = str(pathlib.Path(found).parent); break
print(bin_dir or 'NOT_FOUND')
"
```

Save this as `WHEELER_BIN`. All subsequent commands MUST use `$WHEELER_BIN/python` and
`$WHEELER_BIN/wheeler` instead of bare `python` or `wheeler`. Never use `source .venv/bin/activate`
— that activates whatever venv is in the CWD, which may not be Wheeler's.

If `NOT_FOUND`, tell the user Wheeler is not registered (no Wheeler MCP server in
`~/.claude/settings.json` and no `wheeler-core-mcp` on PATH).

## Step 1: Read cache and get current version

Read the update cache at `~/.cache/wheeler/version-check.json` if it exists. Also run:

```bash
$WHEELER_BIN/wheeler version
```

## Step 2: Fresh check

Regardless of cache state, run a fresh version check:

```bash
$WHEELER_BIN/python -c "
from wheeler.installer import check_version
installed, latest, update_available = check_version()
print(f'installed={installed}')
print(f'latest={latest}')
print(f'update_available={update_available}')
"
```

## Step 3: Report and confirm

Detect the install source:
```bash
$WHEELER_BIN/python -c "
from wheeler.installer import _detect_install_source
print(_detect_install_source())
"
```

**If source is "editable"**: always offer to update — editable installs pull the latest commits even without a version bump. Show:
```
Wheeler X.Y.Z (editable install)
Pulling latest commits...
```
Use AskUserQuestion to confirm:
> Pull latest Wheeler changes and reinstall?

Options: "Yes, update now" / "No, cancel"

**If source is "pypi" or "github"**: check by version number.

If no update is available:
```
Wheeler X.Y.Z — already up to date.
```
Stop here.

If an update IS available, show:
```
Wheeler X.Y.Z -> A.B.C available

Install source: <pypi|github>
```

Use AskUserQuestion to confirm:
> Update Wheeler from X.Y.Z to A.B.C?

Options: "Yes, update now" / "No, cancel"

## Step 4: Run update

If confirmed, run:

```bash
$WHEELER_BIN/wheeler update --yes
```

Show the result. If the source is "editable", note that `git pull` will run first.

## Step 5: Clear the cache so the update badge disappears

The statusline badge (`⬆ /wh:update`) is driven entirely by the cache file
`~/.cache/wheeler/version-check.json`: an absent cache, or a cache with
`update_available: false`, shows no badge. `wheeler update` already deletes it,
but delete it explicitly so the badge drops immediately on the next statusline
render. Do NOT use `$WHEELER_BIN/python` for this: a uv-tool install puts the
`wheeler` shim in `$WHEELER_BIN` but its python elsewhere, so that path may not
exist. A plain `rm -f` works for every install type:

```bash
rm -f ~/.cache/wheeler/version-check.json
$WHEELER_BIN/wheeler version
```

The badge stays gone as long as the install the SessionStart check hook finds is
current. That hook probes `wheeler` on PATH, then `~/.local/bin/wheeler`. If the
badge returns after a restart, the hook is tracking a DIFFERENT Wheeler install
than the one you just updated (`$WHEELER_BIN`): tell the user that other install
(whatever `which wheeler` resolves to) is genuinely still outdated and should be
updated too, or removed. For a single-install user they are the same and the
badge stays cleared.

Report the version transition and suggest restarting the session if slash commands changed.

$ARGUMENTS
