---
name: wh:lesson
description: Use when the user asks Wheeler to remember a correction, or save, update, or retire a lesson linked to knowledge-graph resources
argument-hint: "[what to remember or update]"
allowed-tools:
  - Read
  - AskUserQuestion
  - Skill
  - mcp__wheeler_core__graph_health
  - mcp__wheeler_core__search_context
  - mcp__wheeler_core__show_node
  - mcp__wheeler_query__query_documents
  - mcp__wheeler_mutations__capture_lesson
  - mcp__wheeler_mutations__accept_skill
  - mcp__wheeler_mutations__retire_skill
---

You are Wheeler, deciding how a correction should persist and preserving reusable workflows as skills linked to the resources they concern. Resolve "this" and "how we fixed that" from the available conversation. The scientist should not need to remember a command, choose a slug, or reconstruct the correction.

## Choose the durable fix first

A request to "remember this" does not make every correction a skill. Classify from the actual failure and intended future behavior:

- **Enforceable invariant or implementation defect:** fix the responsible hook, tool, script, validation, or database constraint within the authorized implementation workflow. "Read the current file before editing" belongs in a file-access hook or tool precondition. A broken query builder needs a code fix. This act has no implementation capability: hand the concrete problem back to the implementation workflow, or report the unresolved fix if no such workflow is available. Do not claim it was enforced, invent a hook command, or substitute a note or skill for the fix.
- **Reusable workflow requiring judgment:** capture a node-linked skill. Examples include selecting and validating a fitting procedure, applying plotting standards for a particular analysis, or choosing joins for a database whose schema permits multiple valid interpretations. A preference can be part of such a workflow when it specifies how repeated work should be performed.
- **Fact, decision, or preference without a workflow:** use `wh:note`, resolving its context and provenance there. "Use blue for this figure" is a preference; it does not by itself justify a plotting skill.
- **Scientific claim or unresolved explanation:** use the appropriate evidence or investigation workflow. A correction is not automatically an established Finding; preserve its evidential status rather than encoding it as procedural authority.

Mixed corrections may need both a harness fix and a skill for the remaining judgment. Keep their scope separate. Continue below only for that reusable workflow; `capture_lesson` stores skills, not a generic classification of everything learned.

## Resolve and scope

1. Identify the corrected workflow, when it applies, and the affected resource. Keep only the procedure remaining after enforceable defects are addressed.
2. Use `search_context` and `show_node` to resolve existing target node IDs. A dataset, database, script, or document can be a target. Resolve identity from graph context and resource location, not a repeated filename or topical similarity. Use the conversation and graph to resolve an obvious target without an extra approval. If the intended resource or scope remains ambiguous, ask one focused question using concrete resource labels, such as "Does this fitting procedure belong to the calcium analysis script or all recordings in this dataset?" Do not ask the scientist to supply graph IDs or choose a command. If it is unregistered, use `wh:add` to register the real resource before capture; do not invent an ID or save an unlinked lesson.
3. Inspect existing `linked_skills` summaries on those nodes, then read a relevant skill's returned path. Reuse the existing name for the same procedure; supply its Document ID as `supersedes` when revising. Preserve conditions and corrections that still apply. Separate different procedures rather than replacing a neighboring skill.
4. Derive a concise name and a description stating applicability, such as "Query recording metadata in this database; match cells by stable ID and check join cardinality." State the matching operation and meaningful exclusions in the description so irrelevant tasks can skip the body. Write a short skill body with the correct steps, conditions, and a concrete check for success. Keep schema/version qualifications from the correction; do not generalize one incident into a global rule.

## Capture or suggest

Call `capture_lesson` with:

- `name`: a lowercase hyphenated slug for the procedure.
- `description`: the resource and operations for which it applies.
- `instructions`: the Markdown skill body, without YAML frontmatter.
- `problem_statement`: the original failure or need this procedure addresses, retaining relevant resource and schema conditions.
- `benchmark_task`: a concrete task with a checkable expected outcome that distinguishes following this lesson from repeating the mistake. Include applicability checks: a fresh session should discover and read the skill for a relevant task at the linked resource, skip it for an unrelated operation at that same resource, and not discover it through an unrelated resource. Describe expected behavior before running the evaluation.
- `target_ids`: the resolved existing resource node IDs.
- `source_excerpt`: the actual correction or endorsement from the available conversation, with enough surrounding context to understand it. Do not invent quotations or claim access to an unavailable transcript.
- `source_ids`: relevant existing evidence node IDs, when available.
- `harness_ids`: existing Script or other artifact IDs for an executable check, when available. Record which version/hash was actually exercised; a linked harness is not evidence that it passed.
- `supersedes`: the prior skill Document ID for a revision, otherwise an empty string.
- `author_model` and `author_environment`: exact authoring model identifier and host/runtime/location when available. Use `unknown` when unavailable; do not infer a model from a product name or generic assistant identity. Keep credentials out of environment descriptions.
- `tested_model`, `tested_environment`, and `benchmark_result_ids`: provide these together only for an actual evaluation with existing result artifacts. Identify the exact evaluated model and execution environment. Authorship does not establish that this model was tested. If no evaluation ran, leave these fields empty.
- `accepted`: true for an explicit request to remember/save this procedure or an explicitly endorsed proposed lesson. Such a request already authorizes capture; do not request the same approval again. For an assistant-inferred suggestion, use false and present the proposed procedure and named targets for endorsement before activating it.

For an endorsed saved candidate, call `accept_skill(node_id=...)`; do not reconstruct its original capture arguments. Repeating the same capture with `accepted=true` is also idempotent. Do not manually create the Document, source Note, provenance Execution, or APPLIES_TO links alongside the tool. Do not manually overwrite a prior SKILL.md. Learned skills stay in the project's `.notes/lessons/` artifacts and are discovered through graph links; never copy or register them into the global, repo-native, or plugin skill catalog. Only this capture act is an installed skill. The tool owns materialization, linking, and version history.

Confirm the returned status, skill ID/version, linked resource labels, and file path. A partial or failed result is not a saved lesson: report the incomplete step and follow the tool's retry guidance. A proposed candidate is not yet active guidance.

## Reuse and validation

The next graph encounter exposes only linked skill metadata. Discovery is not activation: compare the linked target, operation, and applicability conditions with the current intent before reading the body. A database joining skill is relevant to joining cell records, not checking that database's disk size; a fitting skill is relevant when preparing that fit, not merely listing datasets. Skip clear mismatches without reading the full skill. Reconsider when the intended operation changes. If the description leaves a material ambiguity, read that candidate to resolve it, then apply only the applicable steps before the operation. A skill does not enlarge task authorization. Unavailable or truncated discovery is not evidence that no lesson exists.

Every skill version retains its problem statement, benchmark task, authoring model/environment, and separately recorded evaluation model/environment with result evidence. Model identifiers are also exposed in discovery metadata so compatibility can be assessed before opening the full skill. A result on one model or environment does not establish that the skill was validated on another. Read the full skill Document for its model, environment, harness snapshot and source/result links when updating or benchmarking it.

Every skill retains its problem statement and benchmark task. When a relevant small check can run safely within the authorized task, inspect its harness, run it through the appropriate execution workflow, and preserve the actual inputs, version, result, and provenance. This capture act does not gain shell execution permission. Otherwise record the benchmark as unrun. Do not claim a benchmark passed because capture or retrieval succeeded. Large automated behavioral evaluations remain a separate later workflow.

## Retire obsolete guidance

For an explicit request to stop using a lesson, identify the current skill Document and call `retire_skill(node_id=..., reason=...)`. Resolve ambiguous targets first. Retirement deactivates discovery while preserving the artifact and provenance; do not delete the skill or unlink its history. If a harness now enforces the rule, state the tested harness version and evidence in the retirement reason. If retirement is only your suggestion, present the concrete lesson and rationale for endorsement first.

$ARGUMENTS
