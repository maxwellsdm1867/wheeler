# End-to-end check (pending isolated harness)

Use a temporary project and isolated test graph only. Seed synthetic calcium-run context, a previous meeting decision/parameter reason, and a similarly named unrelated run. Supply an actual notebook, run-manifest.json, two valid PNGs and last meeting notes. Never use production writes.

Execute the SKILL.md steps, not generic CRUD: retrieve with graph_health/search_context/show_node, show that the right reasons reach the brief and unrelated context does not. Draft and edit brief.md; assert no draft, rough-note, Finding or Hypothesis registrations. Missing or conflicting manifests must stop plot selection.

At simulated explicit readiness save brief-v001.md and sources-v001.json. Use ensure_artifact for both Documents, query_executions/add_execution for the write activity, link_nodes for directed provenance, and index_node for Documents. Fresh show_node and read-only run_cypher must verify types, status, hashes, paths, actual contents and edges. Inspect graph, knowledge JSON and synthesis consistency through the harness filesystem.

Repeat readiness unchanged and assert stable IDs, one Execution, no duplicate links or extra version. Change brief content, make v002, and verify v001 and its source record survive unchanged and old provenance remains reachable. Verify altered source bytes are detected by the preserved hash.

Simulate graph unavailability at capture, preserve local snapshot and source record, report pending state, restore graph, reconcile partial receipts and lookups, and complete without duplicates. Also interrupt after one Document/Execution creation and test recovery. Record exact calls, checks, failures, outcomes and untested paths. Clean up only isolated resources created for this test. Do not equate a successful trial with guaranteed future agent behavior.
