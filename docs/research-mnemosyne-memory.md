# Mnemosyne memory mechanisms: lessons for Wheeler

Reviewed 2026-09-15 against local Mnemosyne commit `bed7548a04aa37727c1fdc02d1d1f1e52367641d`. The external checkout was clean before and after inspection. This is a bounded primary-source code investigation, not a full security audit or reproduction of benchmark claims. No external checkout source files or Wheeler graph state were changed.

## Conclusion

Borrow the small, explicit canonical-slot mechanism and the capture/retrieval lifecycle. The primary Wheeler target is a corrected procedure attached to the artifact it governs, such as a database, and loaded on future access to that artifact even for a different task. First eliminate the failure in the querying harness where possible; preserve residual guidance with source, authority, scope, and version history. Mnemosyne provides useful slot and injection components, but its reviewed model-slot injection is query-overlap driven, not a deterministic artifact-access trigger. Do not transplant the full persona, sleep, or memory-ranking architecture.

This extends Wheeler's context-management pillar while retaining its actual product, the provenance guarantee. Research interpretation remains the scientist's decision. Wheeler's [mission](/Users/maxwellsdm/Documents/GitHub/wheeler/docs/mission.md:7) also rejects becoming an agent framework or generic knowledge base.

## What is implemented

| Concern | Concrete implementation | Relevance to Wheeler |
| --- | --- | --- |
| Durable preference or instruction | Memory types include preference, instruction, learning, and error; classification uses regex patterns. | An ordinary conversation can supply durable material even without a paper, dataset, or script. Classification alone does not establish correctness. |
| Single current value | CanonicalStore keys a free-text slot by owner, category, and name; maintains history with validity dates and monotonically increasing versions. | A preference such as presentation style needs an explicit identity and replacement rule, not merely semantic similarity. |
| Conversation capture | Hermes provider sync_turn saves user turns by default; assistant turns are optional and lower importance. | Separate what the scientist said from what the assistant inferred or generated. |
| Distillation | Sleep asks the configured LLM for structured user/workflow/project/agent model updates with evidence IDs. | Save small candidates linked to exact source turns, not an opaque profile summary. |
| Retrieval and application | Preturn prefetch combines recall with relevant canonical slots; identity has a separate deterministic injection path. | Storage is insufficient: accepted corrections must return before the relevant action. |
| Correction | invalidate records expiry and a replacement ID; conflict handling can persist its validation in the same transaction. | Keep old wording, replacement, authority, and reason together. |

Sources: [types and classifiers](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/typed_memory.py:35), [canonical schema](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/canonical.py:104), [role defaults](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:1852), [turn capture](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:2421), [proposal schema](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/model_refresh.py:108), [prefetch](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:2109), [invalidation](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/beam.py:6057).

## Mechanisms worth borrowing

### 1. Canonical slots with version history

The database enforces at most one current row per `(owner_id, category, name)` through a partial unique index. Repeating identical content is a no-op. Changed content closes the previous row, inserts the next version, and preserves history. The operation uses `BEGIN IMMEDIATE`, and versions continue upward after retirement and re-creation. Exact-key reads avoid requiring vector retrieval for a known preference. [constraint](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/canonical.py:124); [transactional replacement](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/canonical.py:196).

For Wheeler, borrow the invariant, not necessarily SQLite or this schema. An operational-memory slot might be `project/wheeler, presentation, derivation_detail`. Scope must distinguish a general user preference from a project, task, or method-specific rule. A task instruction should not silently become a global preference.

Direct user instructions already carry authority. If the scientist says, “For this project, always show the units,” Wheeler can store and apply that scoped preference without asking for the same approval again. If the assistant infers a broad rule from frustration or repeated behavior, it should retain a candidate and source excerpt for review. The review distinction is about inferred authority, not mandatory confirmation for every memory.

### 2. Source episodes and derived candidates are different objects

Model-refresh proposals have category, name, body, confidence, evidence IDs, action, and reason. Persisted metadata adds status and source working-memory IDs. Proposal rows are marked inferred/derived and excluded from recursively triggering another sleep cycle. [proposal validation](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/model_refresh.py:108); [proposal persistence](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/model_refresh.py:310); [derived proposal rows](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/beam.py:11541).

This maps well to Wheeler: a local conversation excerpt is an input artifact; a capture or consolidation act is an Execution; a preference or lesson is its derived artifact. Store host/session/turn identifiers when available, the exact relevant quote, timestamp, attribution, and any referenced code/artifacts. If only a manually pasted excerpt is available, record that limitation rather than claiming a complete transcript.

A useful lesson has more structure than “avoid this mistake”: trigger, observed failure, corrected behavior, applicability, and evidence. “Do not pool these cells before fitting because parameters vary by cell” should cite the actual correction and scope to the relevant analysis. It must not become an unsupported scientific Finding merely because it is remembered.

### 3. Retrieval is a product feature separate from persistence

The Hermes integration prefetches before a turn. Canonical model slots are selected by query overlap and capped at three by default; whole model cards are a display/debug surface rather than the normal injected context. The ordinary bank path filters weak fragments and assistant-derived noise. [relevant slots](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:2185); [bank filtering](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:2335).

Wheeler should assemble a compact applicable-memory block at act entry or immediately before a relevant tool action. Each item should expose why it applies and link to its source. Preferences essential to every relevant action should use deterministic scope routing; they should not depend on whether a short request happens to retrieve them semantically. The identity-specific prefetch branch illustrates that general design lesson, although Wheeler does not need its companion-persona behavior. [deterministic injection rationale](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:2134).

### 4. Supersession must commit together with its explanation

In the sleep conflict path, heuristic similarity only proposes a possible conflict. Invalidation and the validation record are one transaction, successful-resolution counters change only after durable success, and cache invalidation occurs after commit. Tests deliberately fail provenance writes and check that a separate database reader cannot observe supersession without its provenance. [atomic conflict handling](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/beam.py:11248); [failure-injection tests](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/tests/test_conflict_provenance_atomicity.py:38); [observer test](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/tests/test_conflict_provenance_atomicity.py:99).

This is directly aligned with Wheeler's guarantee. A replacement should not be treated as successful until its source and supersession history are durable, with Wheeler's existing receipt/repair behavior covering its multiple storage layers.

### 5. Keep raw role attribution and avoid assistant self-reinforcement

User-only automatic turn capture is the default. Optional assistant capture has lower importance. That is a useful default for operational memory because the assistant otherwise risks repeating and “learning” its own guesses. [role default](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:1852); [capture attribution](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:2448).

The opt-in verbatim ledger additionally tracks self-echo suppression around compression boundaries. It explicitly admits that it is best-effort provider-instance bookkeeping, not a durable checkpoint or a reliable live-context-membership oracle. Borrow the conservative behavior when evidence is missing, not the integration complexity in an initial Wheeler slice. [ledger contract](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/verbatim_ledger.py:1).

## What to avoid, with observed limits

### Automatically turning model confidence into user authority

Sleep refresh is enabled by default when its inference path is available. Auto-application also defaults on. New slots require nominal confidence 0.90 and two evidence entries; conflicting slots require 0.98 and three entries. These numbers are policy gates on the model's reported confidence, not demonstrated probability calibration or scientist approval. [enabled default](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/model_refresh.py:33); [auto-apply defaults](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/model_refresh.py:250); [application gates](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/model_refresh.py:431).

A targeted in-memory reproduction found that evidence `["one-turn", "one-turn"]` satisfies the two-evidence threshold and auto-applies. The gate counts list entries, then uses a set only for source-membership validation. This does not establish independent corroboration. For Wheeler, a single explicit correction can be authoritative; ten repetitions of an inferred claim need not be. Provenance and authorization are better distinctions than repetition counts.

### Copying the persona extraction path

A narrow defect exists in `PersonaExtractor.extract_candidates`: its working and episodic queries filter source and importance but do not filter expiry or supersession. Its topic fallback is `general`, and `deduplicate_by_topic` retains only one highest-importance candidate per topic. [candidate SQL](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/persona.py:65); [topic fallback and deduplication](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/persona.py:138).

An in-memory reproduction with an expired/superseded “Use dense paragraphs” (importance 0.9), its active replacement “Use concise lists” (0.8), and independent “Use SI units” (0.8) returned all three candidates, then retained only the expired first preference after topic deduplication.

This is a finding about this persona candidate extraction/deduplication path, not a claim that all Mnemosyne retrieval returns expired content. Beam and vector recall contain explicit currentness filters, and canonical reads select current rows. Stable explicit slot names are a simpler fit for Wheeler.

### Treating every provenance path as equally durable

The conflict-validation table intentionally trims each memory's validation history to three rows. That is acceptable as a lightweight operational audit log but unsuitable as Wheeler's permanent scientific provenance. [three-entry retention trigger](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/beam.py:1780).

Canonical refresh is also a different transaction path from the strong conflict path: it calls CanonicalStore.remember, which commits, and then marks proposal metadata applied in a later commit. A failure between those operations can leave the canonical update without the matching applied status. This is a code-level failure-window observation, not a reproduced crash. [refresh application](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/model_refresh.py:393); [canonical commit](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/canonical.py:276).

Canonical rows contain a generic source string, confidence, and validity history. The link back to evidence is in proposal metadata rather than a full script/data/parameter dependency graph. Mnemosyne's memory provenance is useful, but it is not Wheeler's research provenance guarantee.

### Adopting the entire engine or its privacy claims uncritically

The core Beam module has 12,249 lines and the main Hermes provider 4,061 at this snapshot, with separate persona, canonical, triples, extracted facts, episodic, and working-memory surfaces. That breadth creates several overlapping notions of identity, validity, and trust. The targeted persona inconsistency illustrates the cost of duplicating eligibility rules across paths.

Storage is local SQLite, and optional embeddings can run locally, but inference can use a host backend or a configured remote backend. Model-refresh explicitly falls back to a remote call when no host path was attempted. Wheeler should retain its host-owned execution model and local artifact storage, not add a second background LLM service just to remember a correction. [host backend contract](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/llm_backends.py:1); [inference fallback](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/model_refresh.py:205).

## Verification and maturity

Executed six focused test modules from the external checkout using Wheeler's existing Python 3.14 environment, with bytecode writes and pytest's cache disabled, embeddings disabled, and a temporary Mnemosyne data directory:

```text
tests/test_canonical.py
tests/test_model_refresh_confidence_hardening.py
tests/test_persona_extractor.py
tests/test_memory_lifecycle.py
tests/test_sync_roles.py
tests/test_conflict_provenance_atomicity.py
126 passed in 6.99 seconds
```

Two warnings concerned unavailable pytest-timeout configuration support. They did not fail these short tests. The tests use isolated databases and mocked inference; this run does not establish model extraction quality, host integration behavior in a live Hermes session, vector retrieval quality, or performance at scale. The two additional in-memory reproductions above exercised actual extractor and auto-apply functions without changing the external repository.

The repository has substantial targeted regression tests, including concurrency, atomicity, scope isolation, source attribution, and malformed model output. CI declares Python 3.10 through 3.13, runs core and Hermes test suites, and checks generated documentation. [CI matrix](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/.github/workflows/ci.yml:141); [test commands](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/.github/workflows/ci.yml:209).

The package declares production/stable status, but that is metadata, not independent evidence. Its own historical documentation audit describes previously fictional tools and environment variables that were corrected. Treat README and benchmark claims as claims until linked to executed code and evaluated data. [package metadata](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/pyproject.toml:9); [historical documentation audit](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/docs/audit-report-2026-06-09.md:12).

## License observation

The root license is MIT, copyright 2026 Abdias J, and includes the notice-retention condition for copies or substantial portions. Package metadata also declares MIT. Only a root LICENSE was found by the inspected license-file inventory. This describes the repository evidence, not a determination about every dependency, model weight, image, or external service. Prefer adapting the small invariants and acknowledging provenance if code is copied. [license](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/LICENSE:1); [metadata and optional dependencies](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/pyproject.toml:13).

## Suggested Wheeler slice

### Priority from the scientist: artifact-triggered procedures

The concrete target is a database-querying correction that remains attached to the database artifact and loads when a later, different task accesses that same database. That is stronger than prompt-relevant preference retrieval. In the inspected Mnemosyne provider, canonical slots are selected by overlap between query text and slot category/name/body, and the storage key is owner/category/name. These mechanisms do not establish a deterministic "this database artifact is being accessed" trigger. The separate identity path demonstrates deterministic injection for an explicit known scope, but does not implement artifact access. [Query-overlap selection](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/hermes_memory_provider/__init__.py:2196); [slot key](/private/tmp/claude-501/-Users-maxwellsdm-Documents-GitHub-wheeler/e26d3ddc-83be-4673-bad2-87e382954104/scratchpad/memprov/mnemosyne/mnemosyne/core/canonical.py:124).

For Wheeler, first fix the querying harness or database interface when the failure can be eliminated mechanically. Record remaining contextual procedure against the stable database artifact ID, with applicability to operations such as querying, schema inspection, or export. At the artifact-access boundary, resolve that identity and load the active procedure before the operation. Do not rely on the later user prompt containing the vocabulary of the earlier correction. Include schema/version conditions where a procedure can become obsolete, and preserve the correction episode as its source.

This is an adaptation suggested by Mnemosyne's slot and injection separation, not an artifact-triggered capability demonstrated by its reviewed code. If Wheeler can only instruct an agent through an act today, describe that as prompted loading; a deterministic guarantee needs enforcement at the actual access path. Preferences then become a secondary special case, while the first end-to-end example should be "different question, same database, corrected procedure automatically available."

1. Introduce a small durable operational-memory artifact with kind, explicit slot key, scope, applicability, authority, status, and source excerpt references. Existing graph and file machinery should own its persistence.
2. Let an explicit “remember this correction/preference” capture and activate it in one act. Inferred durable lessons become reviewable candidates; direct scoped user instructions do not require redundant confirmation.
3. Retrieve active applicable items at act entry, show source IDs, and keep scientific Findings separate from interaction preferences.
4. Replace a slot without deleting its history; record withdrawal or supersession together with the reason and authority.
5. Verify the behavior end to end: one correction survives a fresh session, appears for the matching action, stays absent from unrelated work, and stops applying after explicit replacement.

The smallest useful capability is remembering one scientist-authorized correction and reliably applying it the next time it matters. Persona generation, whole-conversation ingestion, automatic sleep inference, and alternate storage backends can wait.
