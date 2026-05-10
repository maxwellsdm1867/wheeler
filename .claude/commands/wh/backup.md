---
name: wh:backup
description: Snapshot Wheeler's canonical state to a single tar.gz archive (knowledge/, synthesis/, .wheeler/, wheeler.yaml, plus a live Neo4j dump and manifest).
argument-hint: "[--destination <dir>]"
allowed-tools:
  - Bash
  - Read
---

Snapshot the Wheeler knowledge graph plus all canonical files into a single
tar.gz archive. This shells out to the `wheeler backup` CLI subcommand on
purpose: the MCP transport caps tool results at ~235k chars and a real
graph dump saturates that immediately. The CLI runs in-process and is not
affected.

## What gets included

- `knowledge/` (all per-node JSON metadata)
- `synthesis/` (Obsidian-compatible markdown)
- `.wheeler/` (embeddings, request log, repair queue; excludes `.wheeler/backups/` to prevent recursion)
- `wheeler.yaml` (config)
- `graph_nodes.jsonl` (one JSON object per node, full properties)
- `graph_relationships.jsonl` (one per relationship, source + type + target + properties)
- `manifest.json` (timestamp, version, node counts by label, relationship counts by type, SHA-256 hashes per file, archive layout)

## Step 1: Run the backup

Pass through any user-supplied destination from `$ARGUMENTS`. If empty,
the CLI defaults to `<project>/.wheeler/backups/`.

```bash
wheeler backup $ARGUMENTS
```

If `wheeler` is not on PATH (no `pip install -e .` in this checkout), fall
back to:

```bash
python -m wheeler.tools.cli backup $ARGUMENTS
```

## Step 2: Surface the result

The CLI prints `Backup created: <path>` and the size in MB. Echo that to
the user. If they want to inspect the archive, suggest:

```bash
tar tzf <archive_path> | head -30
```

## Notes

- If Neo4j is offline, the file layers are still archived. `manifest.json`
  records `graph_available: false` and the JSONL graph dumps will be empty.
- The backup is also recorded as an `Execution(kind="backup")` node in the
  graph (best-effort: skipped silently if the graph is offline).
- Remote destinations (S3, Drive, GCS) are not yet wired. `--include-remote`
  is reserved as a no-op for forward compatibility.

$ARGUMENTS
