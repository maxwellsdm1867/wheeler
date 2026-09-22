# Executed verification: 2026-09-22

Real Wheeler MCP serialization and an isolated Neo4j database were exercised through `evals/workflow_creator/graph_probe.py`, using a temporary synthetic calcium-analysis project. Production graph was not touched. The exact temporary root is:
`/private/var/folders/41/tclkvrfs1v9386sxps6_w5t40000gn/T/wheeler-creator-test-9wdok3a1`.

## Outcomes

- Interview produced an actual Markdown-brief workflow rather than guessing from “lab meeting”. It established manifest-based plot selection, tentative-interpretation labeling, scientist review, readiness-only registration, immutable versions, and source hashes.
- Context retrieval via graph_health/search_context/show_node recovered the smoothing-window rationale and prior baseline-sensitivity question. The similarly named archive plot was inspected as a candidate and excluded by its path; only current-manifest plots were used. Draft remained unregistered with no Finding or Hypothesis creation.
- Readiness v001 registered two Documents and one Execution with 21 expected directed provenance edges. Fresh reads checked paths, SHA-256, types and final status; JSON and synthesis agreed.
- Unchanged readiness with the receipt moved away resolved the same IDs from fresh graph reads. No graph mutation/indexing calls, no duplicate links, no new version. Receipt was reconstructed.
- A requested new question created v002 with 24 expected edges, preserving v001 byte-for-byte and keeping earlier evidence reachable.
- An actual refused loopback Neo4j connection preserved v003 snapshot/source artifacts and pending receipt. No graph mutation was attempted during outage; the live isolated diagnostic snapshot confirmed unchanged nodes and links.
- Restored connection finished the pending v003 without rewriting the snapshot or earlier versions. Two new Documents and one Execution, 27 expected edges. `graph_consistency_check(repair=false)` reported 17 graph/JSON/synthesis records, zero divergence, all 12 artifact paths portable, resolvable and present, and no repair actions.
- Removing the manifest temporarily caused preparation for 2026-10-02 to stop before selecting any plots, writing a brief, or calling graph tools. Exact question: “I can’t find the run-manifest.json for this analysis. Where is the manifest you want me to use for the 2026-10-02 brief?” Manifest was restored byte-for-byte; knowledge/synthesis unchanged.

## Observed defects and fixes

The initial generated skill incorrectly used query_documents(keyword=<absolute path>) as path lookup. A live independent probe showed keyword filters title only, confirmed in the actual implementation. Before further mutations the executor stopped, preserved the original skill, and corrected lookup to a complete project-scoped listing, resolved/portable path comparison, and show_node. The partial v001 capture was reconciled with fresh reads and only missing links added.

The temporary execution runner incorrectly classified graph_health `error:null` as failure. That failed resume made no mutations; the runner was fixed to reject truthy errors. Both incidents remain in the transcript and call logs. The original generated skill and pre-test verification document are preserved one directory above this skill.

## Evidence

Within the temporary root: `checkpoint-ready.json`, `checkpoint-rerun.json`, `checkpoint-revision.json`, `checkpoint-offline.json`, `checkpoint-recovery.json`, `consistency-recovery.json`, `missing-manifest-result.json`, phase call/result logs, artifact-hash records, and actual `meetings/2026-09-25/` files. Interview and execution transcript is in the parent directory of this skill as `transcript.md`.

## Limits and maintenance

This validates the exercised paths on one synthetic fixture and isolated real backend, not guaranteed future agent behavior. Conflicting-but-present manifests, concurrent captures, missing half of a snapshot pair, ambiguous duplicate records, large catalogs at lookup bounds, changed source bytes without brief changes, and portability after moving the project were not executed. The graph-retrieval test and missing-manifest trial do not substitute for those checks. No external publishing, messaging, production activation or resource-linked skill registration occurred. Test resources are retained for the parent evaluator to inspect and clean up; the skill is staged only at the user-selected temporary destination.

After changes to graph behavior, repeat real isolated read/draft/readiness/readback, receipt-loss rerun, revision preservation, partial-write recovery and genuine connection-failure recovery. Verify correct context against a distractor, no pre-readiness writes, paths/contents/hashes/status, actual input provenance, absence of duplicates, and graph/JSON/synthesis agreement. Preserve failures, fix them, rerun affected checks, and state untested paths. Do not substitute mocks or a prose walkthrough. Clean up only resources created by that test once its owner no longer needs them.
