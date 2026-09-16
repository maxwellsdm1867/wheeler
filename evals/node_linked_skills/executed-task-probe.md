# Graph discovery followed by actual task execution

This probe tests the distinction between a skill being linked to a resource and being relevant to the current operation. It bypasses voice routing and supplies the graph seed directly so discovery and agent selection can be observed separately from search ranking.

An isolated Neo4j instance stores two accepted skills linked to the same database: `recording-joins` and `population-response`. The production `expand_search_results` implementation supplies descriptions and file references. Fresh agents can read a selected skill through an audited CLI and execute read-only queries against a real SQLite fixture. Each agent gets one task, no development conversation, no other cases and no evaluator oracle. They receive Wheeler's normal applicability guidance.

The audit records actual full-body reads and executed SQL with results, alongside the agent's final answer. Selection is checked from those reads, not just from the agent saying it selected correctly. The CLI contract is instruction-based rather than an OS sandbox.

| Task | Skills discovered | Body read | Observed result |
| --- | --- | --- | --- |
| Retrieve parasol measurements | Both | Joining only | `p1:10`, `p1:20`, `p2:40`; cardinality verified |
| Reach database through dataset neighbor; retrieve midget measurements | Both | Joining only | `m1:99`, `m1:101`; cardinality verified |
| Compute population summary | Both | Population summary only | Per-recording means 15, 40, 100; equal-weight mean 155/3 |
| Check database file size | Both | Neither | 16,384 bytes; no SQL issued |
| Inspect table names | Both | Neither | `measurements`, `recordings`; schema-only query |
| Inspect a different database with the same filename | None | None | Correct table names; no guidance leaked across resources |

All six original cases passed. The wrong basename join demonstrably returns two extra measurements from another cell; averaging all rows produces 54 rather than the required equal-weight result. These are deterministic fixture controls, not an agent-without-skills baseline.

The original numerical fixture also appears in the saved skill's benchmark example. Two additional fresh-agent runs use changed data with unchanged skill bodies, so a copied benchmark answer will fail. Both passed: the joining task returned `p1:12`, `p1:24`, `p2:45`, and the population task computed means 18, 45, 90 and an equal-weight mean of 51. Each read only the relevant skill. Across the original and changed-data cases, all eight executed tasks passed.

Evidence:

- [Six-case execution trace and source snapshots](executed-task-probe-2026-09-15.json)
- [Changed-data execution trace and source snapshots](executed-task-heldout-2026-09-15.json)
- [Fixture and audited task interface](task_probe.py)
- [Independent result scorer](score_task_probe.py)

The exact evaluator model IDs were unavailable and were recorded as `unknown`, alongside each agent's execution environment. This is one run per case with explicit applicability descriptions, not a reliability estimate, cross-model validation, or proof that uninstrumented database access will trigger Wheeler. No full skill body was present in the initial graph response. These runs test discovery through the production graph implementation, selection, reading, and execution; they do not test conversational lesson authorship or search ranking.

To reproduce, start a separate loopback Neo4j instance, then invoke `task_probe.py NEW_ROOT setup TEST_URI`. Give each fresh agent only its task and the `context/read/sql/stat/finish` action contract preserved in the JSON. Score with `score_task_probe.py ROOT OUTPUT_JSON`. Preserve the evidence, then run `task_probe.py ROOT cleanup` before setting up another fixture on the same server: fixture IDs are fixed and Neo4j enforces global ID uniqueness. For changed data, append `heldout` to setup and score the `join summary` cases. Never point this probe at the research database.
