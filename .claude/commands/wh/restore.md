---
name: wh:restore
description: Verify, fresh-restore, or merge a Wheeler backup archive into a project. Supports --verify, --fresh, and --merge modes.
argument-hint: "<path/to/backup.tar.gz> [--verify | --fresh --target DIR | --merge] [options]"
allowed-tools:
  - Bash
  - Read
---

Restore from a Wheeler backup archive. Three modes are supported:

- `--verify` (or `--dry-run`): replay into a scratch namespace, compare
  against the manifest, then clean up. Live data is never touched.
- `--fresh --target DIR`: extract the full project tree and replay all
  graph nodes and relationships into a fresh (empty or clean) directory.
- `--merge`: merge archive nodes into the current (possibly populated)
  project using a configurable conflict policy.

`--fresh` and `--merge` require `manifest_version >= 2` (archives created
by Wheeler v0.8+). v1 archives still pass `--verify`.

## Step 1: Validate input

Parse `$ARGUMENTS`. The first non-flag argument is the archive path.

If no archive path is given, ask the user for one. Do not guess.

If the path does not exist on disk, tell the user. Do not invoke the CLI.

Determine which mode the user wants: verify (default), fresh, or merge.

## Step 2: Run the appropriate restore command

### Verify mode (default / --dry-run)

```
wheeler restore <archive_path> --verify [--keep-scratch]
```

### Fresh mode

```
wheeler restore <archive_path> --fresh --target <dir> [--force]
    [--accept-signature-mismatch]
    [--neo4j-uri URI] [--neo4j-password PW]
    [--neo4j-database DB] [--project-tag TAG]
```

`--target DIR` is required. The target must be empty or contain only a
clean project shell (just `.git/`, `.gitignore`, or a pristine
`wheeler init` output) unless `--force` is passed.

### Merge mode

```
wheeler restore <archive_path> --merge
    [--conflict skip|replace|prefix] [--prefix STR]
    [--accept-signature-mismatch]
    [--neo4j-uri URI] [--neo4j-password PW]
    [--neo4j-database DB] [--project-tag TAG]
```

`--conflict` governs what happens when an incoming node ID already exists
in the recipient graph: `skip` (default), `replace` (overwrite via
update_node), or `prefix` (rewrite incoming IDs to `<prefix>__<id>`).
`--prefix STR` is required when `--conflict=prefix`.

If `wheeler` is not on PATH, fall back to:

```
python -m wheeler.tools.cli restore <archive_path> [flags]
```

## Step 3: Present the result

### Verify

The CLI prints `Verdict: PASS` or `Verdict: FAIL` followed by per-check
diagnostics. Forward those to the user verbatim. If FAIL, highlight the
`First failure:` line and ask whether they want to investigate
(re-run with `--keep-scratch` to inspect the scratch namespace in Neo4j
Browser).

On PASS, remind the user they can read the bundled recipient instructions:

```bash
tar -xOzf <archive_path> HANDOFF.md
```

### Fresh / Merge

The CLI prints a summary: target_root, archive_uuid, nodes restored,
relationships restored, failure count, externally rooted paths count, and
any warnings. Surface these to the user. If there are failures, suggest
inspecting `.wheeler/restore_log.jsonl` for details.

## Notes

- Config overrides (`--neo4j-uri`, `--neo4j-password`, `--neo4j-database`,
  `--project-tag`) are written into the recipient's `wheeler.yaml` before
  graph replay begins. The `NEO4J_PASSWORD` environment variable on the
  recipient is also honoured.
- An `Execution(kind="restore")` node is added to the recipient graph and
  `.wheeler/restore_log.jsonl` is appended on success (best-effort: does
  not flip a successful restore to failure).
- Embeddings are copied only if the archive's embedder model matches the
  recipient's `config.search.model`. Otherwise a warning is emitted and
  the user is advised to run `wheeler embeddings rebuild`.
- Nodes whose `path` field resolves outside the archive's project tree
  (external references) are noted in `externally_rooted_paths` and in
  the restore log.
- This command is deterministic: it shells out to a Typer command and
  reports its output. Do NOT add extra graph-mutation tools to the
  allowed-tools list. Restore-verify must not write to the user's live
  namespace.

$ARGUMENTS
