# Node-linked skill evaluations

See the [extensive evaluation report](../../docs/node-linked-skills-evaluation.md)
and [case-level evidence](extensive-results-2026-09-15.json) for measured results,
mechanism repairs, native routing checks, and writer iterations.

The extensive native-host evaluation uses `trigger_benchmark_cases.json`,
`benchmark.py`, `fixture_actions.py`, `host_runner.py`, and `benchmark_score.py`.
It separates graph discovery, selective full-body reads, executed procedures,
task outcomes, and host/permission failures. Cases include SQL joins, weighting,
fitting, plotting, exports, unrelated operations, changed intent, lifecycle states,
and bounded context. Expected outcomes are kept outside the model's task context.

Use a disposable local Neo4j instance and a new output directory:

```sh
uv sync --extra dev --frozen
.venv/bin/python evals/node_linked_skills/benchmark.py /private/tmp/trigger-run prepare --uri bolt://localhost:7687
.venv/bin/python evals/node_linked_skills/benchmark.py /private/tmp/trigger-run run --phase development-v1 --split development --workers 4
.venv/bin/python evals/node_linked_skills/benchmark_score.py /private/tmp/trigger-run /private/tmp/trigger-run/development-score.json --phase development-v1
```

Freeze guidance and scoring after development, then run `--split heldout
--repeats 2` in a new phase. Repeats vary data values, but remain correlated
observations of the same scenario. The scorer reports raw counts, descriptive
Wilson intervals, and case-level rates. It retains semantic checks requiring
human adjudication rather than assuming a nonempty answer is correct.

`live_host_probe.py` tests native hosts against production MCP and actual skill
files. `writer_probe.py` tests lesson creation/revision against isolated graph
namespaces and snapshots before and after each task. Their `setup`, `run`, and
`cleanup` subcommands keep fixture lifecycle explicit. Run each script with
`--help` for arguments. These probes use native subscription authentication,
exclude ambient API keys, and do not alter saved host configuration. Exact model
IDs are recorded only when exposed by the runtime; `unknown` remains unknown.

Keep raw native logs private: they may contain unrelated installed skill
metadata. Publish sanitized observations and artifact hashes with the report.
Controlled CLI task replay, live MCP transport, and native router/act selection
are different evaluation surfaces and must be reported separately.

## Earlier decision smoke test

For graph discovery followed by real agent task execution, see the newer [executed-task probe](executed-task-probe.md). The earlier exercise below tested decisions only.

[Recorded inputs, outputs and checks](trigger-smoke-2026-09-15.json), captured 2026-09-15 against a modified checkout based on `9965f0af13d1ae66fa92282e6ebd2e8845b30e0b`.

Two subagents started without the development conversation or expected answers. One evaluated six use cases using linked metadata and could read the supplied skill files. The other classified six corrections using the lesson act. Cases within each batch shared agent context. All 12 decisions matched the withheld expectations.

| Case | Expected and observed decision |
| --- | --- |
| Join recording metadata and responses | Read the linked joining procedure |
| Check the same database's disk size | Skip the procedures |
| Fit adaptation parameters per cell | Read the fitting procedure |
| Inspect fitting script filename and timestamp | Skip the fitting procedure |
| Query a different database with the same basename | No skill supplied or selected |
| Plot response curves with fitting and plotting candidates | Select only the plotting procedure |
| Enforce read-before-edit | Harness fix |
| Preserve a reusable fitting procedure with a known script | Skill; no target clarification |
| Use blue for one figure | Note |
| Preserve fitting guidance with two possible target scripts | Skill; ask a concrete target question |
| Untested temperature explanation | Evidence work |
| Repeated plotting standard with a known dataset | Skill; no target clarification |

This is a small synthetic decision exercise, not a reliability estimate, model comparison, or benchmark of executed scientific tasks. Tool tests separately establish graph discovery, persistence, versioning and isolation. A different-resource case with no supplied metadata tests agent behavior; graph scoping is established by the implementation tests.

Both evaluators reported their exact runtime model ID as `unknown`; the recorded environment is `Codex subagent on local host; synthetic decision-only exercise`. Do not attribute these results to a specific model. Future model-specific runs must record the exact exposed model ID and execution environment.

The JSON preserves the cases, expected choices, evaluator outputs, complete skill bodies and hashes, and the exact lesson-act snapshot supplied to the evaluator. Temporary paths identify the original fixture locations; embedded contents make the record inspectable after those paths disappear. A subsequent frontmatter-only edit narrowed the installed lesson trigger to Wheeler requests; the tested act snapshot remains unchanged in this record.
