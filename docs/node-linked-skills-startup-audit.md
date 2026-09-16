# Startup audit: learned node-linked skills

Audited Wheeler main commit `51228d68fc47c12f55a6d35ffb118d56fae7fe33` on 2026-09-15. No production loading defect found. Learned procedures are outside both hosts' native skill catalogs, so creating more lessons does not add their names, descriptions or bodies to startup context.

## What is visible, and when

| Stage | Content visible to the agent |
| --- | --- |
| Fresh host session | Metadata for installed Wheeler acts, including the small `lesson` capture entry and voice router. No catalog entries for individual learned procedures. |
| A graph read encounters a linked resource | Bounded summaries of accepted skills linked to returned nodes: applicability, ID, version, path and short model metadata. No procedure body. |
| The agent selects a relevant procedure | The agent explicitly reads the returned `SKILL.md` path and receives the body. |

The `lesson` act is the capture/triage workflow, not an individual remembered procedure. Its generated stub defers its own detailed instructions to `get_act`. There is no separately installed skill for every learned workflow.

If a startup or resume flow explicitly fetches graph context, encountered nodes can disclose their associated summaries at that point. That is node-triggered metadata, not preloading the lesson library. A body already read earlier can remain in the conversation or resumed history; this audit concerns fresh startup.

## Native host evidence

**Codex CLI 0.146.0:** used the native `codex debug prompt-input` command to render the actual model-visible input without invoking a model. An isolated project contained a positive control under `.agents/skills`, a byte-identical copy of Wheeler's shipped `lesson` stub there, and a learned-procedure sentinel under `.notes/lessons/<name>/<version>/SKILL.md`.

All seven checks passed: the native control description and lesson description were present, while the native control body, lesson stub instructions, learned name, learned description and learned body were absent. This is direct prompt inspection, not a model's report about its context. Configured MCP servers were disabled for this invocation, and newer nonboolean feature configuration values were temporarily overridden for compatibility with this CLI; no persistent configuration changed. This tests local native skill loading, with the plugin catalog path separately verified from the shipped manifest and regression tests. It is not an inspection of a running desktop conversation's private prompt.

**Claude Code 2.1.271:** three isolated native sessions used runtime model `claude-opus-5[1m]`. The shipped plugin skills, agents and hook files were copied byte-for-byte; MCP registration was removed and hooks disabled for the catalog canary. Native initialization events listed the positive `.claude/skills` control and `wh:lesson`, but excluded the learned `.notes/lessons` procedure. In the final session, exactly one explicit `Read` opened that procedure; its unique body marker first appeared in the tool result. All 24 assertions passed. Claude does not expose the complete provider system prompt here, so this conclusion combines native catalog events, positive/negative canaries, the Read trace and source inspection.

The [machine-readable evidence](../evals/node_linked_skills/startup-audit-2026-09-15.json) preserves assertions, versions, scope and hashes of local raw evidence. Codex's full rendered prompt remains local because it includes unrelated personal skill metadata. No real research graph, installed plugin or persistent host setting was changed.

## Code and regression checks

- `wheeler/tools/graph_tools/lessons.py` writes learned bundles under `.notes/lessons/`, not `skills/`, `.claude/skills/`, `.agents/skills/` or `.codex/skills/`.
- `wheeler/build_plugin.py` generates the fixed act catalog and packaged router. It never enumerates project lesson directories. Claude uses the standard plugin `skills/` directory; Codex explicitly declares `./skills/`.
- `hooks/hooks.json` installs only a legacy-command shadow warning. Its implementation lists old command filenames; it does not load lesson files. Shipped subagents have no `skills:` preloads.
- `wheeler/workspace.py` collects file inventory and does not read Markdown bodies into workspace context.
- `wheeler/skill_discovery.py` returns summaries only for encountered node identities. Its backend reads files to verify hashes, but does not send those file bodies to the model.
- New `tests/test_skill_catalog_isolation.py` captures a real lesson against the isolated test backend, asserts its storage is outside native catalogs, proves both generated host catalogs remain byte-identical after capture, and verifies graph discovery returns metadata without the body.

Targeted validation: **119 tests passed**, including catalog isolation, plugin generation, graph disclosure and trigger boundaries. Ruff passed for the added test file. This audit added tests and evidence only; no production behavior change was needed.

## Host contracts

Codex documents that startup receives skill name, description and path, with full instructions loaded when selected; local repository discovery scans `.agents/skills`. [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills)

Claude documents that ordinary sessions initially receive skill descriptions and load full instructions on invocation. Its explicit subagent `skills:` preload is an exception, which Wheeler's shipped agents do not use. [Claude Code skill documentation](https://code.claude.com/docs/en/skills)
