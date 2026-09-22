# Workflow creator trials

These probes exercise the interview-driven Wheeler skill creator and the graph behavior of a skill it authors. The synthetic user wants a weekly lab-meeting brief: draft locally, retrieve prior decisions, choose plots from a run manifest, and register immutable brief/source-manifest Documents only on explicit readiness.

The independent executor receives the creator skill and simulated user answers one turn at a time. The parent evaluator retains the scoring rules. A second trial asks for a read-only paper lookup that an existing skill can already handle.

`graph_probe.py` invokes the checkout's real FastMCP tools against an explicit loopback Neo4j test server. It does not use a fake graph or project credentials. Each call is logged. The `offline.flag` fault switches calls to a refused loopback connection on port 17688, while normal calls use the isolated server on port 17687. Use a temporary root whose `config.json` supplies `project_root` and a unique `neo4j.project_tag` beginning `creator-test-`.

Reproduction:

1. Start a disposable Neo4j Community container on `127.0.0.1:17687`, with authentication disabled only for that loopback test service. Do not point these probes at a research graph.
2. Run `graph_probe.py ROOT setup`, then `seed_fixture.py ROOT` with the checkout Python. Save `graph_probe.py ROOT snapshot` as the baseline.
3. Supply the creator instructions and interview turns in the saved trial record to a fresh agent. Save its generated skill. Give the agent the tool schemas from `graph_probe.py ROOT schema` and the `call SERVER TOOL ARGS_JSON_FILE` interface.
4. Execute draft, readiness, repeated readiness, and revised-readiness turns. Snapshot each checkpoint and run `score_probe.py ROOT BASELINE CHECKPOINT PHASE`. The grader checks observed graph/file state; it does not instruct the executing agent.
5. Test missing receipts, conflicting input manifests and a refused connection. Restore connectivity, resume, and compare graph counts, identities, source hashes and provenance.
6. Preserve the transcript, tool audit, skill versions and check results. Remove only the disposable test container and temporary fixture when finished.

A passing synthetic trial is evidence about these cases, not a reliability estimate for all interviews, all user workflows, or every host. The MCP calls run through the actual serialization and storage implementation; this does not test native plugin reload or UI invocation.
