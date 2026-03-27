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

## Step 1: Read cache and get current version

Read the update cache at `~/.cache/wheeler/version-check.json` if it exists. Also run:

```bash
wheeler version
```

to get the current installed version.

## Step 2: Fresh check

Regardless of cache state, run a fresh version check:

```bash
source .venv/bin/activate && python -c "
from wheeler.installer import check_version
installed, latest, update_available = check_version()
print(f'installed={installed}')
print(f'latest={latest}')
print(f'update_available={update_available}')
"
```

## Step 3: Report and confirm

First detect the install source:
```bash
python -c "
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
source .venv/bin/activate && wheeler update --yes
```

Show the result. If the source is "editable", note that `git pull` will run first.

## Step 5: Clear cache

After a successful update, the cache is automatically invalidated. Confirm the new version:

```bash
wheeler version
```

Report the version transition and suggest restarting the session if slash commands changed.

$ARGUMENTS
