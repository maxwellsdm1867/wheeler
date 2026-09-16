# Node-linked lessons: package validation

Validated on macOS with Python 3.12.12 in a fresh worktree based on main commit `0507aeea7f632164609799fa629790449b6eb6ac`. The working implementation was integrated with main's content versions, compact MCP responses and optional synthesis layer before testing.

## Checks

- Final full-suite result: **3,423 passed, 3 skipped**, in 71.09 seconds. The skipped cases are the three optional Torch checks described below; all selected Neo4j integration tests ran.
- Full suite uses `uv sync --extra dev --frozen`, with an explicitly selected local Neo4j test instance. `WHEELER_TEST_NEO4J_URI` now takes precedence over automatic local-instance selection in the live test fixtures.
- The lesson integration test exercises real Neo4j capture, neighbor discovery, typed listings, raw node/scalar results, MCP serialization, revision and retirement.
- Additional regressions cover compact and trimmed skill descriptions, cached node reads with new neighboring guidance, result truncation, candidate state, immutable content versions, replay without duplicate edges, disabled synthesis, and generated UTF-8 artifact size limits.
- Ruff, mypy and generated-plugin drift checks pass.
- Wheel and source distribution builds pass. Both include the lesson code, canonical act and voice router. A separate environment installed from the wheel successfully loads the lesson act and all 57 MCP tools, including the three lesson lifecycle tools and main's existing bulk-registration tool.
- Earlier [executed task evaluations](../evals/node_linked_skills/executed-task-probe.md) preserve eight fresh-agent runs with actual graph discovery, selected skill reads and SQLite task execution. Their source snapshots identify the earlier checkout they evaluated; the integration regressions above exercise the updated main interfaces.

Reproduction command, after starting a separate test server:

```bash
NEO4J_URI=bolt://localhost:7687 \
NEO4J_USERNAME=neo4j NEO4J_PASSWORD=research-graph NEO4J_DATABASE=neo4j \
WHEELER_TEST_NEO4J_URI=bolt://localhost:7687 \
WHEELER_LESSON_TEST_URI=bolt://localhost:7687 \
.venv/bin/python -m pytest tests/ -q
```

## Optional Torch limitation

Torch is not a declared test/development dependency. An additional experiment installed Torch 2.14.0 and attempted the three normally skipped Torch recipe tests. The combined suite aborted those child workers during macOS Objective-C `MPSGraphObject` initialization after `fork`, while 3,423 other tests passed. This is not a lesson/discovery failure, but it is an unresolved optional runtime limitation.

A diagnostic availability check that avoided importing Torch in the parent allowed all three Torch checks and the 68-test recipe module to pass in isolation. It did not fix the combined run, and import auditing found no remaining parent Torch import explaining that failure. The isolated successes therefore do not establish combined-suite compatibility. No native safety checks were disabled, and no numerical execution changes or diagnostic test modifications are included in this feature. The declared dependency environment was restored for the final package run; its three Torch tests are explicitly skipped.

## Distribution boundary

This change updates main and validates locally built distributions. It does not bump the existing `0.16.0` version or publish a new PyPI release. An already installed/released backend does not gain lesson tools merely because the repository changed; release the updated package before relying on these tools through a package-managed plugin installation.
