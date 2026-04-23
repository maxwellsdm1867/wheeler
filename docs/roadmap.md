# Roadmap

## Shipped

| Version | Date | Highlights |
|---------|------|------------|
| v0.1-0.4 | 2026-03 | Prototype, graph backends, search, hardening |
| v0.5 | 2026-04-02 | W3C PROV-DM schema, provenance-completing tools, stability scoring |
| v0.6 | 2026-04-08 | Infrastructure hardening, GraphRAG (search_context, fulltext, communities, entity resolution), split MCP servers |
| v0.6.1 | 2026-04-16 | update_node tool, stale driver fix, parameter discoverability, ingest data source detection |
| v0.6.2 | 2026-04-18 | Auto-routing, /wh:start entry point, 137 routing tests |
| v0.6.3 | 2026-04-19 | Proactive graph context, execution tracking, /wh:bump |
| v0.7.0 | 2026-04-20 | Graph-as-source-of-truth, plan lifecycle, read-before-mutate hooks, process provenance, Script node discoverability fixes |

## Next: v0.8.0 (act-graph interaction clarity + graph agents)

The two themes: (1) make clear how each command mode interacts with the graph,
and (2) automate the manual provenance and quality work.

### Phase 1: Act-graph interaction audit

Audit and document how each `/wh:*` command reads from and writes to the graph.
Currently this is implicit in each act's prompt and tool permissions. Make it
explicit: which tools does each mode call, what graph state does it expect,
what graph state does it produce?

- [ ] Map each act's allowed-tools to graph read/write patterns
- [ ] Document expected graph preconditions per act (e.g., execute expects an
  approved plan node)
- [ ] Document graph postconditions per act (e.g., execute produces Finding +
  Execution + provenance links)
- [ ] Identify acts that should query the graph but don't (coverage gaps)
- [ ] Write to `specs/act-graph-contract.md`

### Phase 2: Graph-review agent

A `/wh:review` command that audits graph quality. Non-destructive: proposes
fixes, doesn't auto-modify.

- [ ] Wrong node types (code files as Documents, etc.)
- [ ] Missing semantic relationships (descriptions mention hypotheses but no
  SUPPORTS/CONTRADICTS edges)
- [ ] Stale nodes (combines existing `detect_stale`)
- [ ] Duplicate nodes (combines existing `graph_gaps` near-duplicate detection)
- [ ] Broken file paths (path field points to nonexistent file)
- [ ] Isolated subgraphs (combines existing `detect_communities`)
- [ ] Output: structured checklist with suggested fixes

### Phase 3: Graph-link agent

A `/wh:link` or integration into `/wh:close` that auto-proposes provenance
groupings for orphan nodes at session end.

- [ ] Query nodes created in current session (by session_id or timestamp)
- [ ] Group related orphans by shared inputs, temporal proximity, or description
  similarity
- [ ] Propose Execution nodes and WAS_GENERATED_BY links for each group
- [ ] Present proposals for scientist approval (<2 manual steps)
- [ ] Integrate with or replace the manual orphan sweep in `/wh:close`

### Phase 4: Testing infrastructure

Build the adversarial and task-completion test suite flagged in PROJECT-SPEC.

- [ ] Define representative task suite (10-15 research scenarios spanning
  discuss, plan, execute, write, close)
- [ ] Build test harness that runs an act against a seeded graph and checks
  postconditions (graph state, file artifacts, provenance completeness)
- [ ] Add adversarial tests: malformed inputs, missing graph state, concurrent
  mutations, graph offline during act
- [ ] Add prompt quality scoring: do acts follow their own rules (citations in
  write mode, no execution in plan mode)?

## Later: v0.9.0+

- **Dataset metadata enrichment** (issue #17): structured schema, source,
  parent_dataset fields on add_dataset
- **Asta integration**: AllenAI agent-baselines using Wheeler's graph
  (docs/asta-integration.md, 850-line plan)
- **Domain skills**: electrophysiology, statistics, or other domain-specific
  extensions
- **Metrics dashboard**: aggregated per-tool latency, error rates, provenance
  coverage from trace IDs
- **Containerization**: Docker/docker-compose for one-command Neo4j + Wheeler

## v1.0 criteria

v1.0 means a solo researcher who is not the creator can install Wheeler, run
a multi-session research project, and produce a fully-provenance-tracked
knowledge graph without hitting blocking bugs or needing to read source code.

- [ ] Install story works end-to-end (setup.sh or pip install)
- [ ] All acts produce correct graph mutations (validated by task-completion
  tests)
- [ ] Graph agents handle routine provenance and quality (no 48-orphan sessions)
- [ ] Documentation covers all commands with examples
- [ ] 0% orphan rate during normal workflow (provenance-completing tools +
  graph-link agent)
