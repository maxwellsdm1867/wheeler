---
name: weekly-lab-brief
description: Prepare and revise the scientist’s weekly calcium-analysis lab-meeting brief from notebooks, run manifests, plots, and previous meeting decisions; capture immutable versions only on “ready for meeting”.
---

# Weekly lab meeting brief

Help the scientist prepare Friday’s meeting. Preserve their notebooks, PNGs, parameter choices, and personal review. The scientist controls interpretation and readiness. An unrelated plot lookup or parameter question alone does not invoke this full workflow.

## Entry and context

Resolve the project root, meeting date, notebook, its `run-manifest.json`, and last meeting notes from supplied paths or the working context; ask only for materially missing identity. Do not assume similarly named projects or runs are the same.

Read the manifest’s actual schema: identify its run ID, parameter values, and exactly two plot paths. Resolve relative paths by the manifest’s documented convention; if ambiguous, ask. Verify files exist, inspect the notebook’s run/parameter evidence and available manifest hash metadata, and view the plots. Missing manifest, mismatching paths/hashes/run evidence, or unverifiable conflicting run claims require a focused question; never select the newest filename. Do not rerun the notebook or alter sources merely to resolve uncertainty.

Call `graph_health()`, then `search_context(query=<project/run identity plus last meeting decisions and parameter reasons>, limit=5, hops=2)`. Resolve candidate resources using `show_node(node_id=...)`, checking project, paths, run identity, dates, and provenance before accepting context. Summarize **Relevant context** with node citations and **Gaps** with uncertainty; absence is not evidence no decision exists. Read only applicable linked skills. Refresh when the run/topic changes or a new decision needs context, not every edit. If disconnected, continue file drafting with graph context explicitly unavailable; do not invent citations.

## Draft artifact

Maintain `<project>/meetings/YYYY-MM-DD/brief.md` as editable Markdown. Link the actual notebook and two manifest-selected PNGs where they live, plus last meeting notes. Separate “What changed / results”, “What I think it means / tentative interpretations”, and “Questions for the group”. Include run ID, parameter values and supported reasons, with source links or graph citations and explicit unknowns. Preserve the scientist’s uncertainty; guesses never become Findings or Hypotheses. Show the draft for their own review and keep iterating. Save draft edits locally, with no graph registration and no rough-note logging.

## Readiness and artifact contract

Only the scientist saying “ready for meeting” authorizes snapshot registration and the provenance below. It does not authorize publishing, messages, new scientific findings, or unrelated source registrations.

At readiness revalidate the manifest and files. Capture SHA-256 hashes from the actual bytes. Avoid concurrent source changes: reread hashes before committing the pair and stop if they changed.

- `brief.md`: editable working brief, never registered by this workflow.
- `brief-v001.md`, then `brief-v002.md`, etc.: immutable byte-for-byte readiness snapshots, registered as Document with `status="final"`. Final means the scientist approved this meeting artifact, not that its interpretations are established findings.
- `sources-v001.json` alongside the matching brief: immutable source record, also a Document. Save meeting date, run ID, copied parameter values, the snapshot hash, and a list of role, absolute source path, and SHA-256 for the notebook, run manifest, two PNGs, and meeting notes actually used. Include actual graph input IDs and a concise description of how they were used. These JSON fields are artifact contents, not invented Wheeler tool parameters.

Compare the draft’s bytes with the latest existing snapshot. Unchanged readiness reuses that snapshot and source record and repairs pending registration only; no new version. If source hashes changed with identical brief text, flag that discrepancy for the scientist rather than rewriting the old source record or silently asserting it describes current files. Changed brief content creates the next unused version and a fresh source record. Never overwrite an existing snapshot or its sources. Preserve older files and graph records. Paths and hashes preserve source identity, not recoverable historical source bytes; report a later source mismatch rather than pretending old bytes remain available.

Use exclusive creation and avoid concurrent readiness runs. If one file of a snapshot pair exists after interruption, inspect it and recover the other only if the original exact content and source metadata are known. Otherwise stop for resolution; do not silently replace it with current data.

## Custom graph registration

This is an explicit custom stage using Wheeler tools. Reviewed `wh:add` classifies images as Findings and JSON as data, and `wh:compile` produces a different synthesis artifact; neither matches this authorized two-Document capture. `wh:ask` stops all work when offline, whereas this workflow preserves local drafting. Do not claim to invoke those acts while changing their rules.

Before mutation inspect current tool schemas. All paths below are absolute, existing snapshot paths. If required tools are unavailable, retain artifacts and mark registration pending.

1. Resolve previous registrations by exact path: `query_documents(keyword=<absolute snapshot path>, limit=100)` then `show_node` for candidates. Repeat for the source record. Check complete identity and hash, not a title match. If conflicting records or incomplete search coverage prevent resolution, stop instead of guessing. Keep returned IDs in a small local `registration-vNNN.json` receipt separate from immutable source contents. This operational receipt is not a research artifact and is not registered.
2. Call `ensure_artifact(path=<snapshot>, artifact_type="document", title=<meeting date and version>, description=<meeting brief; interpretations tentative>, status="final")` and the same for `sources-vNNN.json` with a source-record title/description. Do not set automatic execution fields: one shared explicit Execution below supports partial recovery. Do not register notebook, plots, rough notes, or chat. Hash mismatches on a previously registered immutable path stop the workflow; never use ensure_artifact to overwrite historical evidence. Capture returned IDs and check success.
3. Use a stable capture key equal to the canonical snapshot path. Resolve the Execution with `query_executions(keyword=<capture key>, kind="write", limit=100)`, then `show_node`. If absent and absence is established, call `add_execution(kind="write", description="Weekly lab meeting capture: <capture key>", status="completed")`. Record its ID immediately. An uncertain mutation result requires a fresh lookup before retry; ambiguity stops creation.
4. `link_nodes(source_id=<brief ID>, target_id=<execution ID>, relationship="WAS_GENERATED_BY")`; same for source-record ID. Link `brief ID -> source-record ID` with `WAS_DERIVED_FROM`. For existing graph nodes actually used (not merely retrieved), link `execution ID -> input ID` with `USED` and derived Documents to those inputs with `WAS_DERIVED_FROM` where justified. If a previous brief was actually used for the correction, include its Document as an input. Do not fabricate graph IDs for unregistered file sources; their concrete provenance is in the source record. Link an active Plan with `AROSE_FROM` only if this work really belongs to it.
5. Inspect relationships before retrying links via read-only `run_cypher(query=...)`, using safely serialized literal IDs from tool results; never raw Cypher writes. Repair only missing edges. Index the two Documents via `index_node(node_id=..., label="Document", text=<title plus concise description>)`.
6. Fresh `show_node` and relationship reads must resolve both paths, expected hashes, and expected directions. Verify files still match. Report file paths, both Document IDs, Execution ID, and any incomplete registration/index/provenance operations. A saved file is not a registered file until readback succeeds.

## Failure and maintenance

Preserve artifacts if graph access fails. Record known IDs, pending operations and the capture key in the local receipt; resume by inspecting files and fresh graph reads. Never blindly retry non-idempotent creation. A partial registration is not completion. Do not directly edit `knowledge/` or `synthesis/`.

Graph integration is currently **unverified**. Before claiming this skill complete and verified, follow [verification.md](verification.md) against real Wheeler tools in an isolated graph and temporary project. Repeat affected end-to-end checks after graph-behavior changes. A prose walkthrough or mock cannot replace that test. In a normal installed personal-skill directory invoke `$weekly-lab-brief`; this evaluation copy is only staged at its user-selected temporary destination and is not automatically installed in the host catalog.
