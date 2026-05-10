---
name: wh:restore
description: Use when the user wants to verify (or eventually restore) a Wheeler backup archive. Currently only --verify (dry-run) mode is supported.
argument-hint: "<path/to/backup.tar.gz> [--keep-scratch]"
allowed-tools:
  - Bash
  - Read
---

Verify that a Wheeler backup archive is restorable. Restore-verify replays
the archive into an isolated scratch namespace inside the live Neo4j
instance (using the existing per-project tag isolation), compares the
result against the archive's manifest, then deletes the scratch
namespace. The user's live data is never touched.

## Step 1: Validate input

Parse `$ARGUMENTS`. The first non-flag argument is the archive path.
Recognized flags: `--keep-scratch` (skip cleanup, leave scratch nodes
behind for debugging).

If no archive path is given, ask the user for one. Do not guess.

If the path does not exist on disk, tell the user. Do not invoke the CLI.

## Step 2: Run wheeler restore --verify

Invoke the CLI via Bash:

```
wheeler restore <archive_path> --verify [--keep-scratch]
```

If `wheeler` is not on PATH, fall back to:

```
python -m wheeler.tools.cli restore <archive_path> --verify [--keep-scratch]
```

## Step 3: Present the verdict

The CLI prints a `Verdict: PASS` or `Verdict: FAIL` line followed by per-check
diagnostics. Forward those to the user verbatim. If FAIL, highlight the
`First failure:` line and ask whether they want to investigate (re-run with
`--keep-scratch` to inspect the scratch namespace in Neo4j Browser).

## Notes

- This command is deterministic: it shells out to a Typer command and
  reports its output. Do NOT add extra graph-mutation tools to the
  allowed-tools list. Restore-verify must not write to the user's
  live namespace.
- Only `--verify` / `--dry-run` mode is supported in this version. If the
  user asks for an actual destructive restore, tell them it is not yet
  implemented and stop.

$ARGUMENTS
