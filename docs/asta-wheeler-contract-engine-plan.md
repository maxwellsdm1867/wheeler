# Asta x Wheeler integration plan (v2, post-review)

Status: DRAFT, revised 2026-06-15 after two multi-agent reviews (capability map + invariant
review, and a code-grounded adversarial review). Supersedes v1. Not yet implemented.

This plan integrates external tools (Asta's plugins first) with the Wheeler provenance graph.
v2 reverses v1's sequencing on verified evidence: build two concrete adapters by hand, then
extract the shared engine on the third pull (rule of three). The contract engine is the
destination, not the starting point.

> Supersedes docs/asta-integration.md, which analyzed the older agent-baselines repo. The one
> instinct carried forward from it: per-tool vertical-slice adapters, Paper Finder first,
> add_paper(corpus_id=...).

## 1. Framing (the sandwich, renamed)

Wheeler is the core. Any external tool is wrapped in two thin layers:

```
  [ MARSHAL IN ]   act prose reads the graph and shapes the tool's input (a skill, not Python)
        |
  [ THE TOOL ]     shell out to the asta CLI (which owns auth, retries, timeouts)
        |
  [ MARSHAL OUT ]  one deterministic Python ingest function writes the result to the graph
```

Avoid the word "compile": `/wh:compile` already means graph -> synthesis Document.

Hard rule: **Claude Code and the Asta skills are the orchestrator. This integration is
plumbing (a contract data file plus one ingest function per tool plus acts), never a workflow
engine, daemon, or router.** Marshal-in is act prose. Marshal-out is one thin deterministic
function per tool. The LLM appears only at authoring time and in the marshal-in act prose; once
authored, running an adapter is deterministic, idempotent, schema-validated code.

Confirmed constraints: inside Claude Code only; bidirectional (informed by the graph, registers
back); asta-plugins untouched; all integration code in `wheeler/integrations/`; first targets
Paper Finder then Theorizer.

## 2. Architecture (Phase-0 + per-tool, no premature engine)

```
wheeler/integrations/
  transport.py    the single boundary that shells out to the asta CLI. Captures exit code +
                  stderr + the -o JSON artifact. Maps non-zero exit OR any non-COMPLETED
                  terminal state to "no artifact, write nothing." Owns the subprocess + timeout.
                  No graph dependency, no LLM-provider SDK.
  ingest.py       MARSHAL OUT. The ONLY module that imports execute_tool (lazily, mirroring
                  validation/ledger.py:175). One deterministic function per tool
                  (ingest_paper_finder, later ingest_theorizer). Loops artifact["entities"],
                  calls add_paper / ensure_artifact / add_hypothesis / link_nodes sequentially
                  via execute_tool, upsert-by-key. Holds link_once (edge-existence guard) and
                  the on-disk (contract, task_id, external-id) -> node-id map.
  cli.py          Typer sub-app `wheeler integrate`. One verb: `ingest <tool> <artifact.json>`.
                  No "send/dispatch" verb (that would make Wheeler invoke Asta = a second router).
  CLAUDE.md       graduated-disclosure doc.
```

Later, after two adapters exist (Phase 3), a small `contract.py` + minimal `registry.py` are
extracted from what the two ingest functions actually share. Not before.

Chokepoint: `transport.py` has zero graph dependency; `ingest.py` is the sole caller of
`execute_tool`. This keeps `graph_tools/` asta-free and preserves strict layering. Confirmed
cycle-free: `graph_tools/__init__.py` imports nothing from validation/contracts/integrations, so
an `integrations/` package using a function-local `from wheeler.tools.graph_tools import
execute_tool` (exactly like `validation/ledger.py:175`) is safe.

CLI registration in `wheeler/tools/cli.py`, guarded so a missing package never breaks the CLI:

```python
try:
    from wheeler.integrations.cli import integrate_app
    app.add_typer(integrate_app, name="integrate")
except ImportError:
    pass
```

Acts live in `.claude/commands/wh/`, mirrored to `wheeler/_data/commands/` via
`python -c "from wheeler.installer import sync_data; sync_data()"` (enforced by
`tests/test_installer.py::test_package_data_in_sync`). Each act runs `asta --version` first and
degrades silently if Asta is absent. `allowed-tools` scope Bash to `asta` and `wheeler integrate`
only, never general Bash.

## 3. Marshal in (informed-by-graph), all act prose

No graph-reading synthesis logic in any Python module. The act calls Wheeler read tools
(`search_context`, `graph_context`, `graph_gaps`, `query_papers`/`query_open_questions`/
`query_hypotheses`), decides what matters, shapes the asta query or the Theorizer
`extraction_results`, and writes a typed payload. The surfaced ids become link targets and the
`session_id` for provenance, so no orphans survive to `/wh:close`.

The data-seeding seam (graph Findings -> Theorizer `extraction_results`) is Phase 2 and gated:
the exact shape is describe-gated and unverified, so capture one real `find-and-extract`
artifact and `asta generate-theories describe form-theory` before wiring, and fall back to
`task_id` mode if a Finding lacks required columns.

## 4. Marshal out (deterministic), idempotent + provenance + tags

Per-tool ingest function, sequential (never `asyncio.gather`; `execute_tool` reuses one cached
backend singleton and Neo4j forbids concurrent queries). Steps:

1. Assert the artifact `schemaVersion` / required-key fingerprint before any field map. Mismatch
   fails loud (anti-corruption guard). Asta's wire format is forward-compat by design, so a
   renamed key must fail, not silently write a wrong `PaperModel.title`.
2. Upsert-by-key: persist `(contract, task_id, external entity id) -> Wheeler node id` under
   `.wheeler/integrations/`. Papers key on `corpus_id`; Hypotheses (no external id) key on
   `(task_id, entity id)` or a content hash. Re-ingest is a no-op.
3. `link_once`: guard every edge with an existence check, because `create_relationship` is bare
   `CREATE` (mutations side), so `link_nodes` duplicates edges on re-ingest.
4. Provenance + tags: one Execution node per tool RUN (not per output node), tagged
   `service = provider:service:version` (e.g. `asta:paper-finder`). Generated nodes
   `WAS_GENERATED_BY` that single Execution; inputs `USED`; bind the asta `thread_id`/`task_id`
   as the `session_id` every `add_*` handler already writes (mutations.py:324), so
   `validate_contract`'s `WHERE n.session_id = $sid` audit works for free and all nodes from one
   turn correlate in `request_log.jsonl`. Stamp a `service` property on generated nodes for cheap
   filtering ("everything from asta:theorizer").

Edge directions (Paper Finder): Paper `RELEVANT_TO` the linked Plan/Question; citation contexts
-> `CITES`. (Theorizer): Paper `SUPPORTS`/`CONTRADICTS` Hypothesis.

## 5. Validation (two phases, two types, never conflated)

- Pre-dispatch payload validation: NEW code (jsonschema or a Pydantic model). Checks the
  marshalled-in payload before the tool runs. Does NOT route through `contracts.py`.
- Post-ingest subgraph validation: construct a session-scoped `TaskContract`
  (required_nodes / required_links / must_reference) and `await validate_contract(config,
  contract, session_id)`. The function is `validate_contract` (contracts.py:255), output-only and
  session-scoped. There is no `validate_task_contract`; v1's "reuse" claim was wrong.

## 6. Invariants

- Every write via `execute_tool()` triple-write. Never the backend or files directly.
- Ingest is sequential (no `asyncio.gather`, one cached backend session).
- A failed/canceled CLI run writes nothing (failure isolation by construction). Retries, auth,
  timeouts stay inside the asta CLI; Wheeler builds no httpx/tenacity/backoff (wrong layer).
- Validate declared node types/relationships against `NODE_LABELS` / `ALLOWED_RELATIONSHIPS` at
  contract-load time; assert artifact `schemaVersion` before mapping.
- `integrations/` imports `execute_tool` lazily (validation/ledger.py:175 pattern).
- Dual-tree act sync enforced by tests. Add no LLM-provider SDK. Never use em dashes.

## 7. Settled decisions (were v1 open questions)

1. Sequencing -> rule of three, vertical slice first. Phase 0 is the transport/ingest seam only.
2. Paper fields -> promote-plus-custom (refines Option A; raised by the user 2026-06-15).
   Services return more fields than Wheeler models (Asta Paper = 11 fields vs Wheeler's 4).
   Do not drop them, and do not add a fixed field per service (does not scale).
   - Promote the first-class fields. `corpus_id: str` goes on `PaperModel` and is INDEXED: it is
     the dedupe key and must be reliably queryable. Thread it into add_paper's create_node dict
     (`extra="allow"` does NOT reach Neo4j; the field must be written explicitly). `update_node`
     picks it up since its allow-list derives from `model_fields`.
   - Generic queryable custom bag for the long tail. Add `custom: dict[str, str|int|float|bool]
     = {}` to `NodeBase`. Neo4j cannot store a nested map as one property, so the backend
     FLATTENS `custom` on write into discrete `custom_<key>` scalar props and reassembles
     `custom` from `custom_*` on read. Result: every service's extra scalars are stored AND
     queryable (`WHERE p.custom_relevance_score > 0.8`), for all node types, with no per-service
     schema churn. The adapter parks any returned scalar that has no promoted model field into
     `custom`.
   - Non-scalar fields (snippets, citationContexts, relevanceJudgement) are not flat props:
     represent them as edges where meaningful (citationContexts -> CITES) or leave them in the
     knowledge JSON (always preserved via triple-write + `extra="allow"`); optionally summarize
     to a scalar (`custom_snippet_count`). 
   - Collisions: the node carries the `service` tag; keep custom keys flat (`custom_<field>`)
     for v1 and namespace by provider only if a second service writes colliding keys to one node.
   - Reject B (encode into `doi`: corrupts the DOI index) and C (sidecar: a fourth write target,
     breaks the triple-write source-of-truth).
3. Layer placement -> `wheeler/integrations/`, lazy upward import, cycle-free.
4. Judgment-port boundary -> file handoff, non-negotiable. Act synthesizes and writes a typed
   payload JSON; the deterministic ingest function consumes it. No CLI callback into a skill.
5. A2A failure handling -> pushed out of Wheeler. transport.py maps non-zero exit / non-COMPLETED
   to "no artifact, no mutation," and asserts schemaVersion before mapping.
6. Surface (MCP vs CLI vs skill) -> no new MCP tools. Marshal-out is one CLI verb the act shells
   out to; it reuses `execute_tool` under the hood. Reconsider MCP wrappers only after three
   adapters exist.
7. Session tagging -> keep the `service` tag (cheap, correct) and store the asta
   `thread_id`/`--thread-dir` path on the Execution/Plan node. Demote the cross-service
   session-sharing registry and `sessions.json` index to "later, when a second same-provider
   service forces it." Tracking is in now; the sharing registry is YAGNI at n=1.

## 8. Build sequence

- Phase 0: `transport.py` (subprocess + timeout + terminal-state mapping + no-artifact-no-write)
  and the lazy-import sequential `execute_tool` wrapper. Nothing else.
- Phase 1: Paper Finder vertical slice end to end. Land corpus_id Option A first. One
  `/wh:asta-papers` (or `lit.md`) act runs `asta ...` via Bash; one ~50-line hardcoded
  `ingest_paper_finder()` upserts by corpus_id; one `wheeler integrate ingest paper_finder`
  verb; post-ingest `validate_contract`. E2e: ingest the same artifact twice, assert one Paper.
- Phase 2: Theorizer vertical slice end to end. Node types decided up front: each theory = a
  parent Finding (`artifact_type="theory"`) or ResearchNote linked `CONTAINS` to its law
  Hypotheses; novelty verdict (established/derivable/new) goes in a declared field, NEVER
  `Hypothesis.status` (acts rely on its open/supported/rejected enum). Marshal-in is act prose
  calling `search_context`, not a Python module.
- Phase 3: extract the genuinely shared ~20% (execute_tool wrapper, schema-fingerprint guard,
  upsert-by-key, session binding, validate_contract adapter) into a tiny `ToolContract` + minimal
  `registry.py`. No meta/skill-creator scaffold yet.
- Phase 4: remaining skills on demand (Semantic Scholar suite, DataVoyager/analyze-data,
  research-step beads, etc.). Author a contract + act only when a researcher reaches for it; each
  act doubles the dual-tree maintenance burden.

## 9. SWE patterns adopted

Ports-and-adapters (port = execute_tool; each tool = one driven adapter). Anti-corruption layer
(thin per-tool ingest mirroring asta's own `parse_artifact`, dropping unmodeled s2Metadata
fields). Schema-fingerprint guard. Transport boundary with failure isolation. Idempotency /
upsert-by-key. Session-id as correlation key. Two-phase two-type validation. Sanctioned lazy
upward import. Testability split (FakeBackend unit tests + live-Neo4j e2e over a checked-in real
artifact fixture for each tool).
