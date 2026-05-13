---
name: wh:backup
description: Snapshot Wheeler's canonical state to a single tar.gz archive (full project tree or graph-only metadata, plus a live Neo4j dump and manifest).
argument-hint: "[--destination <dir>] [--scope project|graph-only] [--yes]"
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

By default (`--scope project`) the full `project_root` tree is packed:

- `knowledge/` (all per-node JSON metadata)
- `synthesis/` (Obsidian-compatible markdown)
- `.plans/`, `.notes/`, `.logs/`, `docs/`, `scripts/`, and all other
  project directories
- `.wheeler/` (embeddings, request log, repair queue; excludes `.wheeler/backups/`
  to prevent recursion)
- `wheeler.yaml` (config; the Neo4j password is stripped to `${NEO4J_PASSWORD}`)
- `graph_nodes.jsonl` (one JSON object per node, full properties; paths rewritten
  to `${PROJECT}/...`)
- `graph_relationships.jsonl` (one per relationship, source + type + target + props)
- `manifest.json` (timestamp, version, counts, SHA-256 hashes, embedder info,
  manifest_version, archive_uuid, external_references, excluded_paths,
  manifest_signature)

Use `--scope graph-only` for the smaller v1-style metadata-only archive
(knowledge/, synthesis/, .wheeler/, wheeler.yaml plus graph JSONL, no full
project tree).

## Artifact safety

A secret scan runs over all packed files by default. If any file contains
patterns that look like Anthropic API keys, the backup is aborted and the
offending files and patterns are listed. The scanned pattern set lives in
`wheeler/portability.py`. Pass `--allow-secrets` to override (not recommended).
The `wheeler.yaml` password field is always stripped to `${NEO4J_PASSWORD}`
regardless.

## Path portability

Paths stored in graph nodes (Finding.path, Dataset.path, Script.path, etc.)
are rewritten from absolute to `${PROJECT}/...` inside the archive. Live
files on disk are never modified. On restore, `${PROJECT}/...` is expanded
back to the absolute path of the recipient's project root.

## Step 1: Run the backup

Pass through any user-supplied flags from `$ARGUMENTS`. If empty,
the CLI defaults to `--scope project` and `<project>/.wheeler/backups/`
as the destination.

```bash
wheeler backup $ARGUMENTS
```

If `wheeler` is not on PATH (no `pip install -e .` in this checkout), fall
back to:

```bash
python -m wheeler.tools.cli backup $ARGUMENTS
```

Key flags:

- `--destination DIR`: write the archive here (default: `.wheeler/backups/`)
- `--scope project|graph-only`: full project tree or v1 metadata-only archive
- `--max-artifact-size BYTES`: skip files larger than N bytes
- `--allow-secrets`: override the secret scan
- `--yes`: skip the size-readout confirmation prompt

## Step 2: Surface the result

The CLI prints `Backup created: <path>` and the size in MB. Echo that to
the user.

Every archive contains a top-level `HANDOFF.md` with recipient instructions.
To read it without extracting the archive:

```bash
tar -xOzf <archive_path> HANDOFF.md | less
```

To inspect the full archive layout:

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
