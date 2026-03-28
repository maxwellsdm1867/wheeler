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

The Wheeler MCP server path in `~/.claude/settings.json` → `mcpServers.wheeler.command` stores
the absolute path to `wheeler-mcp`. Derive the venv from it:

```bash
python3 -c "
import json, pathlib, os
settings = json.loads(pathlib.Path(os.path.expanduser('~/.claude/settings.json')).read_text())
mcp_cmd = settings.get('mcpServers', {}).get('wheeler', {}).get('command', '')
if mcp_cmd:
    # e.g. /Users/me/wheeler-user-test/.venv/bin/wheeler-mcp → /Users/me/wheeler-user-test/.venv/bin
    print(str(pathlib.Path(mcp_cmd).parent))
else:
    print('NOT_FOUND')
"
```

Save this as `WHEELER_BIN`. All subsequent commands MUST use `$WHEELER_BIN/python` and
`$WHEELER_BIN/wheeler` instead of bare `python` or `wheeler`. Never use `source .venv/bin/activate`
— that activates whatever venv is in the CWD, which may not be Wheeler's.

If `NOT_FOUND`, fall back to `which wheeler` or tell the user Wheeler isn't registered.

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

## Step 5: Clear cache

After a successful update, the cache is automatically invalidated. Confirm the new version:

```bash
$WHEELER_BIN/wheeler version
```

Report the version transition and suggest restarting the session if slash commands changed.

$ARGUMENTS
