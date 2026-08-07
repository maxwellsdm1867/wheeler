---
name: restore
description: Verify, fresh-restore, or merge a Wheeler backup archive into a project. Supports --verify, --fresh, and --merge modes.
argument-hint: "<path/to/backup.tar.gz> [--verify | --fresh --target DIR | --merge] [options]"
allowed-tools:
  - Bash
  - Read
  - mcp__wheeler_core__get_act
  - mcp__plugin_wh_wheeler_core__get_act
---

<!-- GENERATED FILE. Do not edit.
     Source: wheeler/_data/commands/restore.md
     Regenerate: python -m wheeler.build_plugin
     The act body is served over MCP by wheeler_core.get_act(), so it is
     deliberately absent here: there is exactly one copy of it. -->

Call `get_act` on the `wheeler_core` MCP server with `name="restore"`,
then follow the returned instructions exactly. They are the authoritative
definition of this act. Do not improvise the workflow or substitute your own
plan for it.

Pass `host="codex"` when running under Codex so the orchestration guidance
matches the tools this host actually has.

Mode: `chat`. Orchestration: `none`.

If `get_act` is unavailable, the Wheeler MCP servers are not connected. Say so
rather than guessing at the workflow: acting without the act text is how
provenance gets silently skipped.
