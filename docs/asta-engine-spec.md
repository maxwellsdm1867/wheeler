# Asta -> Wheeler engine spec: input-side provenance, service registry, skill-creator

Status 2026-06-15. Implementation spec. Three pieces, built in this order:
1. Input-side provenance (most important, concrete, build first).
2. The service registry / engine (light, contract + manifest + loader).
3. The skill-creator skill (scaffold an adapter from a contract).

The unifying idea: a tool is a declarative CONTRACT (one manifest entry); a command opts
in via a flag; a run is a step whose provenance reaches BACK to its graph inputs (USED) and
FORWARD to its graph outputs (WAS_GENERATED_BY). Asta is instance #1.

## 1. Input-side provenance (BUILD FIRST)

The marshal-in synthesizes the tool payload FROM graph nodes (the question, the Findings
seeded into Theorizer extraction_results, the gap that shaped the query, the Dataset paths
handed to DataVoyager). That synthesis is a provenance relationship: the run USED those nodes.

Record:
- `Execution -[USED]-> each graph node the marshal-in consumed` (link_once, existence-guarded).
- The chain is then complete and transitive without per-output edges:
  `output -[WAS_GENERATED_BY]-> Execution -[USED]-> input`. Any Asta result traces back to the
  exact graph context that shaped its request, not just the literature the service returned.

Implementation:
- Each ingest fn (`ingest_paper_finder`, `ingest_theorizer`, `ingest_semantic_scholar`) gains
  `used_inputs: list[str] | None = None`. After the run Execution is created, record
  `Execution -[USED]-> id` for every `used_inputs` id that exists in the graph (a generic
  `_node_exists` + `_record_used` in `_marshal.py`, project-aware, link_once).
- The CLI `ingest` verb gains `--used <comma-separated ids>` -> `used_inputs`.
- The marshal-in acts pass `--used` with the node ids the prose consulted to build the request
  (at minimum the `--link-to` question/plan; for theorize, the Finding ids seeded into
  extraction_results; for analyze-data, the Dataset ids).
- This is the INPUT half of the contract earning its keep (the output half already buckets).

## 2. The service registry / engine

A declarative manifest of available services; commands read it, never hardcode providers.

`.wheeler/services.yaml` (user-editable; ships empty; Asta entries optional):
```yaml
services:
  - id: asta-theorizer
    provider: asta
    name: Theorizer
    description: literature-grounded theory generation with supporting/contradicting evidence
    kind: shell-out                 # shell-out | local
    act: /wh:asta-theorize
    cost: "expensive (~$7, ~20min)"
    available: "asta auth status"   # availability probe; filtered out on non-zero exit
    when: "hypothesis or theory generation"
    inputs:                          # input ports (the USED set + the marshalling map)
      - { name: question, source: query, required: true }
      - { name: extraction_results, source: findings }
    output:
      raw_node: document             # document (synthesis) | dataset (records)
      nodes: [Finding, Hypothesis, Paper]
```

`wheeler/integrations/registry.py`: load `services.yaml`, run each `available` probe, return the
available contracts (id, description, act, cost, kind, when, inputs, output). Pure read; no graph
dependency.

Consumers:
- `/wh:asta` (generalize to `/wh:services`) reads the registry instead of its hardcoded routing
  table: lists only available services, suggests by `when`/`description`, warns on `cost`.
- Commands stay service-agnostic: an optional `--service <id>` / `--use <id>` resolves through the
  registry; with no flag the command is provider-free.

This is the light engine. The heavy generic marshalling DSL stays out (the parsers are
tool-specific); the contract carries identity + ports + output shape, not a field-map language.

## 3. The skill-creator skill

A meta-skill that scaffolds a new adapter from a contract, closing the loop with the original
skill-creator idea. `.claude/skills/wheeler-service-creator/` (or `/wh:service-new`): given a
tool (interview the user, or read its `--help` / agent card), it:
- drafts the `.wheeler/services.yaml` contract entry (identity, ports, output shape, availability),
- scaffolds the marshal-out ingest skeleton (`wheeler/integrations/<provider>/<tool>.py`) wired to
  `_marshal.py` + `register_output_artifact`,
- scaffolds the marshal-in act (`/wh:<provider>-<tool>`) that reads graph context, passes `--used`
  source ids, and shells out,
- scaffolds a parse-unit + live-Neo4j e2e test stub.
Then the human captures one real output, fills the parser against it, and the adversarial-review
workflow lands it. Adding a service becomes: run the creator -> fill the parser -> review -> land.

## Build order

1. Input-side provenance (this spec, section 1): a focused change to the three adapters + CLI +
   acts, adversarially reviewed. Lands now.
2. Registry/engine (section 2): contract dataclass + `services.yaml` + loader + `/wh:asta` reads it.
3. Skill-creator (section 3): the scaffolding meta-skill.
