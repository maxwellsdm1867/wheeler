# Workflow creator trial: 2026-09-22

The creator completed a simulated workflow interview and authored a personal lab-meeting skill. That skill was then exercised against a disposable Neo4j Community instance through the checkout's real FastMCP serialization and graph mutation/read implementations. A separate trial correctly reused `wh:ask` for a fully specified read-only paper-lookup workflow instead of inventing another skill.

## What changed after testing

1. The creator required live graph-write verification but its capability grants allowed only graph reads. Its grants now include mutations, read-only relationship inspection, indexing, and consistency checks, with the instructions limiting test writes to an isolated graph/project.
2. The authored skill incorrectly used `query_documents(keyword=<absolute path>)` to resolve identity. A live probe returned zero matches for an existing path and one match for its title; the implementation filters titles only. The generated skill was corrected to inspect project-scoped listings, resolve portable paths, and reuse exact IDs. The creator now requires checking query semantics against an existing record and testing recovery without local receipts.

A temporary execution helper also misclassified `error: null` as failure. This was recorded and corrected before continuing; it was not a graph defect and did not justify adding a universal skill rule.

## Observed outcomes

| Case | Outcome |
| --- | --- |
| Workflow interview | Asked about a recent real example, parameter rationale, and current-plot identification; used follow-up answers to define artifacts and readiness |
| Existing skill fits | Selected `wh:ask`, respected the request for no further interview, no files, and no graph writes; this case was contract inspection, not live paper retrieval |
| Draft preparation | Retrieved the recorded parameter decision, used manifest-selected plots, kept the guess tentative; no new nodes or links |
| First readiness | Created one brief snapshot and one source-manifest Document plus one producing Execution; fresh reads verified files, hashes and directed provenance |
| Interrupted capture | Recovered two Documents, one Execution and three already-written links; completed only missing operations |
| Repeated readiness, local receipt removed | Recovered the same IDs; no graph writes, extra versions, or duplicate links |
| Revised readiness | Registered v002 while preserving v001 bytes and records |
| Refused graph connection | Preserved v003 artifacts and pending receipt; correctly reported incomplete registration; graph unchanged |
| Connection restored | Registered pending v003 without duplicate nodes/links; all earlier artifacts preserved |
| Missing run manifest | Asked for the intended manifest before selecting plots, creating a draft, or calling graph tools; restored fixture afterward |

Final storage check: **17 Neo4j nodes, 17 knowledge JSON records, 17 synthesis files, zero divergence**. All **74 relationships were unique**. The independent scorer checked actual graph/file state across six checkpoints (3, 33, 33, 61, 63 and 89 assertions respectively); these are repeated assertions within one workflow trial, not independent statistical samples. The command, routing, generator and installer suite passed **359 tests**.

## Evidence and limits

- [Interview and execution transcript](2026-09-22/interview.md)
- [Initial authored skill](2026-09-22/initial-skill/SKILL.md) and [corrected skill](2026-09-22/final-skill/SKILL.md)
- [Verification record](2026-09-22/final-skill/verification.md)
- [Audited MCP calls](2026-09-22/calls.jsonl), [scored checks](2026-09-22/checks.json), and [final graph checkpoint](2026-09-22/checkpoint-recovery.json)
- [Final consistency report](2026-09-22/consistency-recovery.json) and [missing-manifest record](2026-09-22/missing-manifest-result.json)
- [Creator instructions tested](2026-09-22/creator-tested.md) and [final creator instructions](2026-09-22/creator-final.md)

The parent supplied synthetic user answers one turn at a time. The executing agent started without the development conversation or scorer, authored the skill and ran it; the parent independently checked graph/file state. A second agent reviewed reuse and artifact-lifecycle behavior. Exact agent model identifiers were unavailable and remain unknown. Environment: Codex, this local checkout and its Python environment, isolated loopback Neo4j Community container. No research graph was used.

This is a small behavioral and storage-integration trial, not proof of general interview quality or future compliance. It does not test native plugin reload/UI invocation, concurrent writers, every graph operation, or preservation of historical source bytes (the user explicitly selected source paths and hashes). Search was exercised on a small seeded graph; it is not a retrieval-ranking benchmark. Archival artifact links and execution-script snapshots retain the temporary paths used during the run; the copied artifact files preserve their original bytes. The generated personal skill remains an evaluation artifact, not a globally installed user skill.
