# Wheeler boundary audit and refactor plan

**Status:** findings complete (2026-08-08). Tiered implementation plans are
being drafted and will be appended as "Part II" below.

**Method.** Six independent readers, one per boundary (content storage,
workspace observer, process state, graph backend, MCP surface, method layer),
each asked a single question and required to cite `file:line` and to declare
what it did not check. Their claims were then cross-checked: entries marked
**[VERIFIED]** were re-read directly against source rather than taken on the
reader's word. Nothing here was produced by running the test suite, and no
reader executed anything against a live Neo4j, so unscoped queries were
identified by reading Cypher rather than by observing cross-project results.
The per-reader "not checked" lists are consolidated at the end; treat them as
the known edges of this map.

**How to use this document.** Part I is a map of where Wheeler's boundaries
actually are, as distinct from where its documentation says they are. It is
organized by tier because the findings sort naturally into work of very
different cost and urgency, but Part I is a description of the codebase, not a
commitment to do the work. Tier 0 is a list of live defects and is worth acting
on regardless of any deployment decision.

## Why the audit was run

Design question: can Wheeler be separated into three products so it can be
served from different hosts (local stdio MCP, remote HTTP MCP, hosts with no
filesystem, Claude Code / Codex / others) **without maintaining parallel
versions of anything**?

1. **The graph service** (MCP tools + storage)
2. **The method** (39 act prompt bodies)
3. **The workspace observer** (hashing the scientist's files, staleness)

## Headline conclusion

The coupling is BETTER than feared where fixing it would be expensive, and
WORSE than documented where it is cheap. The core is genuinely
context-parameterized. The real problem is that Wheeler's invariants are
documented but not mechanically enforced, so they have silently decayed.

**Eight instances of "the system says X, the code does Y":**

| Documented | Actual | Evidence |
|---|---|---|
| Change propagation via transitive decay | `detect_and_propagate_stale` has ZERO production callers | **[VERIFIED]** only `tests/e2e/test_provenance_chain.py:427,464,560,647`, `tests/regression/test_issue_37.py`, and its own docstring `provenance.py:24-26` |
| Triple-write keeps 3 layers consistent | Checker compares presence only, never content | **[VERIFIED]** `consistency.py:27-37` (4 id lists + 3 counts), `:70-79` (4 set differences) |
| All mutations route through `execute_tool` | 3 CLI verbs write bare Cypher; `execute_merge` also bypasses | **[VERIFIED]** `tools/cli.py` never imports `execute_tool`; 0 hits for `write_node\|write_synthesis\|WriteReceipt\|trace_id`; bare `CREATE` at `cli.py:223-226`, `:266-269`, `:325,331`. `execute_merge` bypass at `mcp_mutations.py:610-622` |
| `scan_dependencies(link_to_graph=True)` links deps | TypeError, swallowed; never created an edge | **[VERIFIED]** `mcp_ops.py:107,119` pass `parameters={...}`; signature is `run_cypher(self, query, params=None)` at `neo4j_backend.py:455-457`; blanket `except Exception` at `mcp_ops.py:132` |
| `run_cypher` is read-only | Substring guard, bypassable | **[VERIFIED]** `mcp_core.py:293-296` |
| `TOOL_DEFINITIONS` is the registration source | No runtime consumer at all | **[VERIFIED]** grep outside `tests/` returns only its own definition `__init__.py:101` and a false docstring `__init__.py:4` |
| `add_paper` supports the dedupe key | Live surface cannot set `corpus_id` | **[VERIFIED]** `models.py:116` declares it indexed, `mutations.py:325` honors it, `__init__.py:259` declares it, but `mcp_mutations.py:196` is `add_paper(title, authors, doi, year)` |
| `mode` describes an act's power | Derived from Wheeler MCP prefixes only | `acts.py:74-85`; 9 acts classify `chat` while holding bare `Bash` |

**Design principle that follows: every seam ships with its guard test.** The
repo already knows this shape (`test_monolith_is_gone`,
`test_committed_tree_matches_generator`). An unguarded interface decays.

---

## What is genuinely clean (do not "fix" these)

- **The core is context-parameterized for real.** `execute_tool(tool_name,
  args, config)` at `graph_tools/__init__.py:938` threads config into every
  triple-write helper (`:496, :577, :623, :706, :754, :787, :37`).
  `Neo4jBackend` reads `project_tag` PER CALL (`neo4j_backend.py:124`), not
  once. `consistency.py`, `provenance.py`, `merge.py`, `contracts.py`,
  `communities.py` contain zero `load_config()` calls. Only **5 ambient
  `load_config()` sites** in library/server code, only **1 on the hot path**
  (`mcp_shared.py:19`). The others: `mutations.py:750`, `:791`,
  `integrations/invocation.py:251,263`, `hooks/auto_register.py:103`.
- **Disk interleaving is the EXCEPTION.** Only `ensure_artifact` is genuinely
  un-splittable (`mutations.py:707-818`: `hash_file` at `:714` drives the
  create payload, the created/unchanged/updated signal at `:778`, and the
  invalidation gate at `:801-808`).
- **No MCP tool uses subprocess.** Zero hits across all four servers,
  `mcp_shared`, `graph_tools/`, `consistency`, `communities`, `contracts`,
  `merge`, `depscanner`, `workspace`, `validation/`, `search/`,
  `graph/provenance`. Subprocess is CLI-only (`integrations/asta/transport.py`).
- **Act bodies are single-source and byte-identical** across hosts
  (`acts.py:117-118`); only `orchestration_note` varies, via one dict
  `_NOTES` at `acts.py:257-262`.
- **The ingest half of every integration is portable**: lazy function-local
  `execute_tool` imports at `asta/ingest.py:90`, `asta/theorizer.py:979`,
  `asta/_marshal.py:333`, `llmsr/discover.py:745`,
  `llmsr/transfer_ingest.py:378`. Pure parse-then-write.
- **Three tools require NOTHING**: `list_acts`, `get_act` (read packaged
  `_data/commands/`), `extract_citations` (pure regex). No DB, no project dir.
- **`backup.py`'s formerly-unscoped dump is FIXED**: `_node_dump_cypher:251-252`
  and `_rel_dump_cypher:263-268` both branch on the tag, and the relationship
  dump filters BOTH endpoints, reasoning at `:259-261`.

---

## TIER 0: live defects (small, unconditional, not deployment prep)

| # | Defect | Location | Fix size |
|---|---|---|---|
| 0.1 | `run_cypher` write guard is a substring scan with literal trailing spaces. `CREATE(n:Finding {id:'x'})` passes, `CREATE\n(...)` passes, `CALL`/`LOAD` absent entirely. Also false-blocks reads containing `DATASET ` (contains `SET `), and that
half is **live and common, not theoretical**: `MATCH (d:Dataset {name: $n})
RETURN d` and `MATCH (n:Analysis) RETURN n.dataset AS d` are both refused
today, because the uppercased text contains the literal `SET `. Note
`LOAD CSV ... CREATE (n:X)` IS caught today via `CREATE `; only the
no-space form slips. The guard is simultaneously too weak and too strong. The CORRECT implementation exists at `neo4j_backend.py:50-56` (`_CYPHER_WRITE_RE`, `\b` word boundaries, includes CALL/LOAD) with a comment explaining exactly this failure. | `mcp_core.py:293-296` | 1 line, reuse existing regex |
| 0.2 | `scan_dependencies(link_to_graph=True)` has never created a `DEPENDS_ON` edge. `parameters=` vs `params=`. | `mcp_ops.py:107,119` | 1 line |
| 0.3 | Atomic-write tmp path is a fixed function of node id (`target.with_suffix(".json.tmp")`), so two concurrent writers write into ONE tmp file and both rename. tmp+rename atomicity is defeated by the shared name. Same defect for synthesis. | `knowledge/store.py:27`, `:118` | 2 lines (unique suffix) |
| 0.4 | `_get_backend` caches ONE backend and IGNORES its `config` argument after the first call (`if _backend_instance is None`). Highest-severity multi-tenant bug and it SURVIVES fixing the config boundary: graph write lands in tenant A's namespace while JSON write lands in tenant B's directory. Also means one shared circuit breaker. **Test impact is small: exactly ONE file touches the global** (`tests/test_triple_write_project_root.py:126,129`); most files referencing `_get_backend` `mock.patch` it wholesale, so keying is invisible to them. The real cost driver is `initialize()` (`neo4j_backend.py:169-173`), which runs 33 DDL statements: naive keying moves that from once-per-process to once-per-KEY, and the e2e sandbox mints a fresh project root per test. Constraints are database-scoped, so gate init on the connection triple while keying the backend on the full tuple. | `graph_tools/__init__.py:869-880` | small; key on `(uri, username, database, project_tag, resolved_project_root)` |
| 0.5 | `EmbeddingStore(config.search.store_path)` uses the RAW relative string while `mcp_shared.py:41` uses `resolved_search_store_path`. Live bug today: `search_findings` and `index_node` read different files when cwd != project root. **Second instance:** `backup.py:693-694` reads the raw string the same way (milder: wrong/absent `dim` in the backup manifest, not data loss). Fix both with `project_search_store_dir(config)` (`config.py:243-252`), which is what the other four sites already use. | `search/retrieval.py:92`, `backup.py:693-694` | 1 line each |
| 0.6 | `EmbeddingStore.save()` writes `embeddings.npy` and `metadata.json` IN PLACE as two separate files, not tmp+rename. A mismatched pair silently assigns EVERY node the wrong vector (`load()` indexes `matrix[i]` by `meta["__ids__"]`). Also: multiple live copies in one process (singleton `mcp_shared.py:32-43` plus fresh instances at `graph_tools/__init__.py:741`, `:1141`, `retrieval.py:92`); a `save()` from the stale singleton overwrites every per-call write since startup. **The obvious tmp+rename fix does NOT work here**: two files renamed back to back is still two commit points, and dying between them leaves the old id list with the new matrix, which `load()` maps positionally, so every node silently gets another node's vector. A length check cannot catch it (the old id list can be the same length). Fix is to collapse to a single `.npz` (matrix + ids + meta) with ONE rename, plus a legacy-pair read path that migrates. The multiple-live-copies half is Tier 1 shaped and is NOT fixed by atomicity. | `search/embeddings.py:165-193`, `:210-213` | medium; format change with a compat path |
| 0.7 | `add_paper` cannot set `corpus_id`, the indexed Semantic Scholar dedupe key. | `mcp_mutations.py:196` | 1 line |
| 0.8 | 3 CLI verbs bypass triple-write, producing `graph_only` nodes: precisely the drift class `consistency.py` CANNOT repair (`:168-171` warns only; regenerating JSON from a ~100-char graph node is unsupported). | `tools/cli.py:207-232`, `:250-275`, `:283-346` | route through `execute_tool` |
| 0.9 | `_logged` appends to `.wheeler/request_log.jsonl` inside the try (`mcp_shared.py:54-73`); on failure the handler at `:74` re-logs at `:76` and THAT raise escapes. A read-only/absent filesystem fails all 52 logged tools on every server regardless of what they need. **This single decorator is what makes a fileless deployment inexpressible.** | `mcp_shared.py:62`, `:74-76` | 1 line, make non-fatal |
| 0.10 | `TOOL_DEFINITIONS`: 395 lines, 30 entries, zero runtime consumers. Description drift 29/29 (100%), param drift 11/29 (38%). `add_script` param NAMES disagree (`path`/`hash`/`version` vs live `script_path`/`script_hash`/`language_version`). Decide: delete it, or make the servers generate from it. Do NOT add capability metadata to it. | `graph_tools/__init__.py:101-495` | decision then mechanical |

Also in scope if cheap: `graph_gaps` is registered at `mcp_core.py:185` but
`CLAUDE.md` and `mcp_query.py:23` both claim it is in `mcp_query`. Module
docstrings state wrong tool counts (`mcp_query.py:3` says 8, is 11;
`mcp_mutations.py:3` says 12, is 18; `mcp_ops.py:3` says 6, is 10).
`request_log_summary` (`mcp_core.py:503`) is the only tool missing `@_logged`.

---

## TIER 1: the ContentStore seam + node versioning

### Why these are ONE project
They touch the same call sites, and versioning supplies the content digest the
consistency checker has never had.

### Current boundary
Six free functions in `knowledge/store.py`, all taking a `Path` first arg, no
object, no state:
`write_node:18`, `read_node:37`, `list_nodes:55`, `delete_node:94`,
`node_exists:104`, `write_synthesis:109`.

Three structural facts:
1. **Asymmetric.** JSON gets write/read/list/delete/exists. Synthesis gets
   **write only**. Every synthesis read/delete/inventory is raw `Path` I/O BY
   CONSTRUCTION: `consistency.py:63-67`, `graph_tools/__init__.py:726-728`,
   `merge.py:181-183`.
2. **Fully synchronous**, and every production writer except `tools/cli.py:1747`
   calls it from inside `async def`.
3. **Return values are dead.** All 5 `write_node` and all 4 `write_synthesis`
   call sites discard the returned `Path`.

Filename convention lives in `models.py:49-51` (`NodeBase.file_name`), i.e. in
the declared zero-dependency leaf, and `store.py:45,96,106,117` re-derives it by
string interpolation instead of calling it.

### Blast radius
- **34 store-routed call sites across 13 files.** 17 of those funnel through ONE
  helper (`queries.py:87-102`), so that file is a one-line change plus deleting
  `_QueryContext.knowledge_path`.
- **6 more files reach around the store entirely** with raw `Path` I/O:
  `merge.py`, `consistency.py`, `mcp_core.py:120-123`,
  `graph/migration_prov.py:354-426`, `backup.py:813-823,870,917-931,956-972`,
  `restore.py:718-761`.

### The four hard spots
1. **`merge.py:110-186` uses `rename()` as its COMMIT POINT.** Phase 2:
   redirect relationships, delete graph node, then rename both tmp files;
   rollback is `tmp.unlink()`. **[VERIFIED]** A ContentStore with only
   write/delete cannot express this. Needs a staged-write primitive
   (`prepare()` / `commit()`) or merge stops being atomic. Object stores have
   no rename.
2. **`consistency.py:40-79` derives node identity from `Path.stem` over a
   glob** (`:57`, `:64`). Any versioned on-disk naming makes every historical
   version read as `json_only` divergence. Versioning MUST ship with
   store-owned current-version resolution, and `consistency.py` must ask the
   store for ids rather than globbing. Existing proof of the fragility:
   `_SYNTHESIS_INDEX_FILES` (`consistency.py:21`) excludes
   `INDEX`/`OPEN_QUESTIONS`/`EVIDENCE_MAP` but NOT `MORNING-*`, which
   `dream.md:372` writes every run.
3. **`backup.py`/`restore.py` treat the two-directory layout as a wire format**
   and rewrite stored BYTES (`backup.py:591-634` parses knowledge JSON bytes
   and regex-substitutes over synthesis markdown; `restore.py:733,738`
   dispatches on `rel_str.startswith("knowledge/"|"synthesis/")`). A
   ContentStore does not help. They need a separate export/import contract
   (`iter_raw()`/`put_raw()`).
4. **`/wh:dream` writes 4 synthesis files with the AGENT's own Write tool**
   (`dream.md:198-372`), outside Python entirely. No Python interface reaches
   it. Either dream gets an MCP tool that writes through the store, or
   synthesis indexes do not exist on a filesystem-less host.

`graph/migration_prov.py:343-440` is a one-shot legacy migration; leave it
filesystem-only and gate it.

### The async fork in the road
Store is sync; a remote/object backend wants async. Of 34 sites, those already
inside `async def` convert mechanically. The ones that would BECOME async and
infect callers: `queries.py:_read_knowledge_node:87` (17 awaits),
`search/retrieval.py:227,242` (called at `:451,:479,:555`),
`search/backfill.py:31`, `dashboard/gather.py:358,381`, and
`tools/cli.py:1747` (sync Typer, needs `asyncio.run`). ~6 helpers, ~25 awaits.
Keeping it sync makes insertion nearly free but puts blocking network I/O on
the event loop. THIS IS A DECISION TO MAKE EXPLICITLY.

### Versioning: fits the interface, fights the surroundings
Fits for free:
- `write_node -> version`: all 5 call sites already discard the return
  (`provenance.py:312`, `graph_tools/__init__.py:561,609,687`,
  `knowledge/migrate.py:107`).
- `read_node(id, version=None)`: all 20 call sites are positional-two-arg.
- `history(id)` is new surface.
- Synthesis is DERIVED (`render.py` is pure), so it need not be versioned; any
  version can be re-rendered.

Fights:
- **`write_receipt.py:21-30`** hardcodes bare `json: bool` / `synthesis: bool`
  and a `complete` property ANDing exactly three flags. No place for a version.
- **No compare-and-swap anywhere.** `_update_knowledge_tier`
  (`graph_tools/__init__.py:589-613`) and `_update_knowledge_node` (`:643-692`)
  are read-modify-write with no expected-version token.
- **`change_log` is already an overlapping history** embedded in the current
  snapshot (`models.py:41`; written at `graph_tools/__init__.py:554,603,679`,
  `merge.py:127`, `provenance.py:299`). Decide which is authoritative or
  `history(id)` and `read_node(id).change_log` will disagree.
- **Two reach-around writers produce unversioned files the store never sees**:
  `merge.py:137-171`, `graph/migration_prov.py:410-423`. Convert first.
- **`models.py:49-51`** encodes one-file-per-node in the zero-dependency leaf.

### The concurrency bug this fixes
`change_log` lives in `knowledge/{id}.json` ONLY. It is explicitly excluded
from graph writes (`_UPDATE_IMMUTABLE_FIELDS` at `mutations.py:963`) and
nothing writes it to Neo4j. There is no second copy.

Concrete interleaving, two writers on `F-3a2b` via `update_node`
(`graph_tools/__init__.py:623-687`): both graph SETs commit (per-field
last-writer-wins, so BOTH survive in Neo4j); both then `read_node` at `:648`
getting change_log length N; both append at `:685`; both `write_node` at
`:687`. Final state: Neo4j has `confidence=0.9` AND `status="final"`; the JSON
has `status="final"` only. `confidence=0.9` exists in the graph and is ABSENT
from the file that is supposed to be the content source of truth. change_log
has N+1 entries where it should have N+2, and the lost entry is unrecoverable.

`graph_consistency_check` reports `total_divergent == 0` for this. It cannot
see content drift at all.

Same read-modify-write-whole-file shape, unsynchronized, at
`graph_tools/__init__.py:603` (set_tier), `provenance.py:299` (invalidation),
`merge.py:127` (merge).

Other concurrency defects in the same family: `create_relationship` has no
uniqueness constraint so concurrent `link_nodes` duplicates edges;
`ensure_artifact` is check-then-act (`mutations.py:726-740`) so two writers
create two nodes for one path, defeating the path dedup everything else relies
on; `_update_synthesis_for_link` (`__init__.py:787-863`) re-renders from a live
query with no coordination.

---

## TIER 2: portable mode enforcement

### The problem
Mode (CHAT/WRITE/EXECUTE) is enforced two different ways and NEITHER ports:
- **Claude Code**: per-skill `allowed-tools` plus plugin-namespace aliases
  (`build_plugin.py:224-258`, `plugin_scoped_tool:211-221` emitting both
  `mcp__wheeler_core__x` and `mcp__plugin_wh_wheeler_core__x`).
- **Codex**: accepts `allowed-tools` but does NOT enforce it, so mode becomes
  which servers exist (`MODE_SERVERS:135-139`, `render_mode_profile:462-505`
  writing `enabled = false` EXPLICITLY because profile merge is recursive).

**There is no server-side mode enforcement anywhere in the codebase.** A host
that cannot vary its tool set per act has no third option.

### The proposed model and what blocks it
Proposal: generalize Codex's model. Mode = which servers a connection can
reach, enforced server-side by token scope (remote) or registration (local).
`allowed-tools` demotes to a UX hint.

The four-server split is ALMOST isomorphic to modes (query = read, mutations =
write, ops = execute) but has **five disqualifying exceptions**:
1. **`run_cypher` lives in `mcp_core`** (`:278`), which every mode needs for
   health/context/search, and its write guard is bypassable (Tier 0.1).
   Reach is **20 acts** (16 by explicit name, 4 more via `mcp__wheeler_core__*`
   wildcards in `execute`, `ingest`, `pair`, `queue`).

   **CORRECTION, 2026-08-08.** An earlier draft of this document claimed
   "CHAT-mode read-only enforcement is defeated today" because five acts
   (`ask`, `graph-review`, `report`, `resume`, `status`) grant `run_cypher`
   while granting zero mutation tools. **That claim was false**, and the
   inference behind it ("no mutation grants" implies "chat mode") was wrong.
   Zero chat-mode acts reach `run_cypher`.

   **The real defect is the inverse, and it is worse. [VERIFIED end to end]**
   Those same five acts derive **`execute`**, the WIDEST mode, because each
   grants an ops-prefixed tool and `derive_mode` (`acts.py:74-85`) returns
   `execute` on any ops prefix. The chain:

   ```
   ask.md grants mcp__wheeler_ops__{validate_citations,extract_citations,detect_stale}
     -> derive_mode() returns "execute"                       acts.py:74-85
     -> skills/ask/SKILL.md:55 states  Mode: `execute`
     -> MODE_SERVERS["execute"] includes wheeler_mutations     build_plugin.py:135-139
     -> codex-profiles/wheeler-execute.config.toml enables it
   ```

   So on Codex today, `/wh:ask` (a pure read act granting zero mutation tools)
   runs with all 18 write tools registered and reachable. Same for `report`,
   `resume`, `status`, `graph-review`.

   This disqualifies server-as-mode independently of the five exceptions listed
   below: "read + `detect_stale`" is not a subset of any chat -> write ->
   execute ladder. **`derive_mode` produces a total order; capability need is a
   lattice.** Re-partitioning servers cannot express it.
2. `init_schema` (`mcp_core.py:309`) applies DDL from core.
3. `index_node` (`mcp_core.py:411-432`) writes the embedding store from core,
   with no `execute_tool` and no receipt.
4. `graph_consistency_check(repair=True)` (`mcp_ops.py:243-271`) deletes and
   rewrites `synthesis/*.md` (`consistency.py:137-165`).
5. `scan_dependencies(link_to_graph=True)` (`mcp_ops.py:58-134`) creates edges
   via `execute_tool`.

4 and 5 are writes behind default-False FLAGS, which server-level gating
structurally cannot see.

`test_mcp_surface.py::test_query_server_is_read_only_by_name` only checks name
prefixes, so it catches none of these.

### The mechanism trap: FastMCP's `tool.auth` is INERT on stdio

**[VERIFIED by source read AND by canary. Do not skip this section: the wrong
choice here yields a mode system that is inert in 100% of today's
deployments while looking correct in review.]**

FastMCP 3.3.1 has native per-tool authorization. Tools carry `tool.auth`,
checked via `run_auth_checks(tool.auth, AuthContext(...))`, and it is applied
in BOTH `list_tools` (`server.py:651-662`) and `_get_tool` (`:684-691`), the
latter returning `None` so invocation fails too. Reading only those two sites
suggests it is exactly the enforcement point Wheeler needs.

It is not, because of the guard one line above each of them:

```python
# fastmcp/server/server.py:165-181
def _get_auth_context() -> tuple[bool, Any]:
    #   - skip_auth=True means auth checks should be skipped (STDIO transport)
    is_stdio = _current_transport.get() == "stdio"
    if is_stdio:
        return (True, None)
    return (False, get_access_token())
```

Both sites read `if not skip_auth and tool.auth is not None:` (`:653`, `:686`).
**On stdio, `skip_auth` is unconditionally True, so `tool.auth` is never
evaluated.** This is deliberate and systemic: FastMCP's own
`AuthorizationMiddleware` carries EIGHT `# STDIO has no auth concept, skip`
branches (`fastmcp/server/middleware/authorization.py:93,119,164,189,236,263,288`).

Every Wheeler deployment today is stdio: `.mcp-plugin.json` is `"type":
"stdio"` throughout, `codex-profiles/*.config.toml` use `command = "uvx"`, and
every server's `main()` calls `mcp.run(transport="stdio")` (e.g.
`wheeler/mcp_core.py:519`).

Canary result, real stdio subprocess, FastMCP 3.3.1, a tool carrying a
deny-all check (`def deny_all(ctx): return False`):

```
STDIO list_tools        -> ['dangerous_write', 'safe_read']    # listed
STDIO call deny-all     -> {'WROTE': 'PWNED'}                  # executed
```

The same denial expressed as custom middleware on tags:

```
STDIO list_tools        -> ['safe_read']
STDIO call              -> ToolError: not reachable in this mode
```

**Therefore:**
- **Custom middleware is the primary gate.** Transport-agnostic precisely
  because it does not inspect transport, which is why it works where FastMCP's
  own authorization does not. Carries host-capability everywhere, and mode on
  stdio.
- **`tool.auth` + `restrict_tag(tag, scopes=[...])`
  (`fastmcp/utilities/authorization.py:62`) is an additive SECOND layer on HTTP
  only**, free once tags are declared, and the natural home for per-connection
  token identity when Tier 3 lands.
- **`remove_tool` (`server.py:1605`) is the wrong mechanism** independently: it
  is deprecated in 3.3.1 in favour of `local_provider.remove_tool`, and more
  importantly it affects only registration, so a client can still invoke a tool
  it never listed. `on_list_tools` filtering is the UX half, never the gate.
  Ship both hooks or neither.

**Method note worth generalizing.** A source read established that the check
exists; only the canary established that it runs. For any enforcement claim,
the canary is the evidence, not the reading. This mirrors the repo's existing
rule in `reference_agent_seal_canary`.

Also: `execute_merge` (`mcp_mutations.py:610-622`) calls `wheeler.merge`
directly, bypassing `execute_tool`, so no WriteReceipt and no repair-queue entry
for a mutating op.

### Related: `derive_mode` is weaker than it looks
`acts.py:74-85` keys only on Wheeler MCP prefixes, so 9 acts classify as `chat`
while holding a bare `Bash` grant (`backup`, `restore`, `bump`, `triage`,
`dev-feedback`, `update`, `asta`, `service`, `start`). Mode describes graph
reach, not host power.

### Capability composition (the related design)
Tool registration is 100% static `@mcp.tool()` decorators; **zero conditional
registration exists anywhere**. `_TOOL_REGISTRY` (`graph_tools/__init__.py:64-96`)
is a plain dict, but it holds 29 names against 53 live tools and only 22 of 53
dispatch through it, so registry-level capability tags reach under half the
surface. Two hardcoded seams inside `execute_tool`: `ensure_artifact` is
special-cased at `:964-975`, and config injection sniffs name prefixes at `:978`
(`if tool_name.startswith("query_") or tool_name == "graph_gaps"`), so a new
read tool not named `query_*` silently loses knowledge-file enrichment.

The cheapest gating mechanism is a post-hoc `mcp.remove_tool(name)` loop in each
`main()`, needing no restructuring. `_MUTATION_TOOLS` (`:48-60`) is already in
effect a CONTENT_WRITE tag.

**Capability tally across 53 tools:** NONE 3; CONTENT_READ only 2; WORKSPACE_DISK
only 4; GRAPH only 6; GRAPH+CONTENT_READ 15; GRAPH+CONTENT_WRITE 18.
Straddlers needing a split or mode gate: `scan_dependencies`,
`graph_consistency_check` (both flag-escalated), `search_findings` (its `mode`
param selects among four capability profiles: `temporal` is pure CONTENT_READ
with no graph at all, `semantic` is pure embeddings, `keyword`/`fulltext` are
graph), `graph_health` (union of three unrelated things), and
`ensure_artifact`/`add_script`/`add_analysis`/`add_dataset` (WORKSPACE_DISK is
HARD-required, unlike the other 14 mutations).

**On a fileless host these 8 of 53 must disappear:** `hash_file`,
`scan_workspace`, `scan_dependencies`, `detect_stale`, `ensure_artifact`,
`add_script`, `add_analysis`, `add_dataset`. `add_script`/`add_dataset` COULD
survive in a client-supplies-hash form: `graph/provenance.py:48-75`
`create_script_node` already takes a hash as data; only the auto-hash at
`mcp_mutations.py:289-290` and `_PATH_MUST_EXIST` membership
(`_field_specs.py:107`) stand in the way.

### Why the gate is a CORRECTNESS requirement, not polish
On a fileless host the failures are confident FALSE POSITIVES, not errors:
- `detect_stale` treats `not exists()` as staleness with
  `current_hash="FILE_NOT_FOUND"` (`graph/provenance.py:138-145`), so EVERY
  Script reads stale. Nine acts consume it, and `dream.md:184` converts each
  into an OpenQuestion at priority 7: one spurious question per Script, every
  consolidation pass, forever.
- `validate_citations` marks every Script citation STALE
  (`validation/citations.py:212-214`), blocking drafting under WRITE/EXECUTE
  citation enforcement on a fabricated premise.
- `_check_path` resolves non-strictly (`_field_specs.py:117`), so `data/x.mat`
  silently becomes `<server-cwd>/data/x.mat` and renders as correct everywhere.
- `scan_workspace` returns `total_files: 0` with no error
  (`workspace.py:63-64`).

### LATENT HAZARD, gate before anyone connects it
`provenance.py:412`'s docstring explicitly invites wiring
`detect_and_propagate_stale` into the `detect_stale` tool. If that happens
while files are unreachable, it calls
`propagate_invalidation(..., new_stability=0.3)` for EVERY Script
(`provenance.py:419-425`), setting `stale=true` and decayed stability across the
whole transitive graph and persisting it into every `knowledge/*.json`
(`:297-320`). One line from a graph-wide destructive mutation driven by a false
`exists()`.

---

## TIER 3: multi-tenant serving

### The good news
The core already takes config explicitly (see "genuinely clean" above). The
missing piece is the SUPPLY of context, which is two things:
1. `mcp_shared.py:19` `_config = load_config()` at module scope, import-time,
   cwd-derived. The four servers import it **BY VALUE**
   (`mcp_core.py:18`, `mcp_query.py:16`, `mcp_ops.py:20`,
   `mcp_mutations.py:17-18`), so rebinding `mcp_shared._config` would NOT reach
   them. ~60 references.
2. `_get_backend` ignoring config (Tier 0.4).

### Process-global state inventory (per-process, all of it)
`mcp_shared.py:19` `_config`; `:18` logging handler; `:22` `_SESSION_ID`;
`:26` `_request_logger`; `:29-43` `_embedding_store`;
`graph_tools/__init__.py:869` `_backend_instance`;
`neo4j_backend.py:107-112` `Neo4jBackend._cb` (circuit breaker);
`graph/driver.py:74,76,79` async driver singleton + key;
`config.py:277` `_keychain_cache`;
`workspace.py:16,17` `_cached_summary`/`_cache_key`;
`dashboard/render.py:45` `_EMBED_CACHE`; `dashboard/serve.py:32` `_RENDER_LOCK`;
`acts.py:174` `lru_cache` (project-independent, SAFE);
`integrations/llmsr/_userland.py:61` `_loaded_sources`, `:43` `PROJECT_DIR`;
`llmsr/metrics.py:197`, `loaders.py:166`, `optimizers.py:149` open registries;
`llmsr/runs.py:52`, `discover.py:94` relative roots;
`integrations/registry.py:63` (SAFE).

NOT a bug: `models.py:41,47` mutable defaults are deep-copied per instance by
Pydantic v2.

### Multi-tenant breakage, ranked
1. Split triple-write across tenants (Tier 0.4). **Survives fixing #2.**
2. One config, belonging to whichever dir the process launched in.
3. One circuit breaker: 3 failures from tenant B open it and tenant A fails
   fast for 60s (`circuit_breaker.py:91-100`).
4. Embedding singleton leaks node TEXT across tenants
   (`mcp_shared.py:92-105`, `mcp_core.py:206`, `:425`).
5. Workspace cache: key is `WorkspaceConfig.project_dir` which defaults to `"."`
   (`config.py:114`), so every tenant shares one key (`workspace.py:116-121`).
6. `_SESSION_ID` is one value for all tenants, landing in `change_log[].actor`
   (`graph_tools/__init__.py:558,607,683`) and on Execution nodes.
7. Node ids are 32 bits and the uniqueness constraint is database-wide, not per
   `project_tag` (`schema.py:20,23-26`). ~1% birthday collision at 10k nodes.
8. Any `backend.close()` closes the driver for every tenant
   (`neo4j_backend.py:175-179`); driver cache key omits the tenant dimension.
9. Keychain cache keyed on a process-global profile (`config.py:277,309-350`).
10. LLM-SR execs project-supplied `.py` into the shared interpreter
    (`_userland.py:89-103`) and mutates shared registries. Arguably must be
    refused outright in a multi-tenant process.
11. Logging: one handler, one level, stacks on repeated calls.

### Tenant scoping: the actual numbers
**78 real `run_cypher` invocations outside `wheeler/graph/`, 16 modules.**
(A regex for `run_cypher\s*\(` returns 80; two are non-invocations:
`mcp_core.py:278` is the tool's own `async def`, `queries.py:4` is a docstring.)
Per module: queries.py 33, merge.py 7, `asta/_marshal.py` 7, restore.py 6,
retrieval.py 3, contracts.py 3, `dashboard/gather.py` 3, mutations.py 3,
backup.py 2, mcp_ops.py 2, `graph_tools/__init__.py` 2, theorizer.py 2,
semantic_scholar.py 2, communities.py 1, consistency.py 1, mcp_core.py 1.

**Plus 12 sites that bypass `GraphBackend` entirely**, opening driver sessions
directly and skipping the circuit breaker AND the retry wrapper:
`provenance.py:193,263,392`; `validation/citations.py:134,142,178,188`;
`tools/cli.py:223,266,333`; `aura.py:396`; `cli.py:374`.

**Scoping audit of the 45 sites outside `queries.py`: 22 scoped, 23 unscoped
(20 reads, 3 writes).**

UNSCOPED WRITES (3): `merge.py:274`, `merge.py:295` (edge recreation, can
create a cross-tenant edge); `mutations.py:903` (`unlink_nodes`, id-keyed so
bounded).

UNSCOPED UNBOUNDED READS (10) = the disclosure surface, and the priority work:
- `consistency.py:48` `MATCH (n) RETURN n.id` : EVERY node id in the database
- `communities.py:76` `MATCH (a)-[r]->(b)` : EVERY edge; clusters across tenants
- `contracts.py:276,300,316` : filter on `session_id`, which is NOT a tenant key
- `mcp_ops.py:104,116` : predicate scans on path
- **`mutations.py:726,732`** : `ensure_artifact`'s create-or-update decision.

  **CORRECTION, 2026-08-08.** Earlier drafts called this "cross-tenant
  MUTATION". **That was wrong. [VERIFIED]** `ensure_artifact` binds
  `existing_id` from the unscoped lookup, then calls `execute_tool("update_node")`
  (`:790-794`), and `update_node` does `backend.get_node(label, node_id)` FIRST
  (`mutations.py:1018`). `get_node` **is** project-scoped
  (`neo4j_backend.py:222-232`), so it misses and returns `Node not found`. No
  cross-tenant write occurs.

  It remains the highest priority of the ten, because the real outcome is
  **silent create-suppression plus id disclosure**, which is worse in practice
  than a blocked write: on a hash match (`:776-784`) it returns
  `{"action": "unchanged", "node_id": <tenant B's id>}`, so tenant A creates
  **no node**, receives a foreign id, and the calling act proceeds to
  `link_nodes` against an id absent from its namespace. It looks like success.
  This is also the COMMON case: same absolute path plus same content is exactly
  what two tenants sharing a mounted dataset or base image produce. The label
  mismatch path (`:766-774`) additionally names tenant B's id and label in the
  error and permanently denies A that path.

  **Consequence for testing:** an e2e assertion phrased as "no cross-tenant
  write occurred" PASSES VACUOUSLY. It must assert `action: "unchanged"`
  carrying B's id.
- `mcp_core.py:300` : agent-supplied Cypher, unscoped by construction

ID-BOUNDED READS (10), lower risk since ids are globally unique:
`merge.py:212,226,236,266,287`; `retrieval.py:373,400`;
`graph_tools/__init__.py:815,835`; `_marshal.py:317` (unscoped ON PURPOSE, with
reasoning at `:314-315`). Note `retrieval.py:373,400` are `search_context`'s
1-hop and 2-hop expansions: seeds ARE scoped (`:187-189`) but neighbours are
not filtered, so combined with the `merge.py` cross-tenant edge write, a scoped
search can return out-of-tenant nodes.

SCOPED (22): `backup.py:489,508`; `dashboard/gather.py:184,206,229`;
`_marshal.py:171,247,279,307,374,417`; `semantic_scholar.py:686,709`;
`theorizer.py:916,937`; `restore.py:616,663,1571,1593,1613,1639`;
`retrieval.py:200`.

### Why there is no cheap chokepoint
`run_cypher` (`neo4j_backend.py:455-472`) is the ONLY ABC method that injects
nothing; the other six scope centrally (`:197-198, 226-231, 266-272, 291-296,
359-365, 411-413`). Injecting a scoping predicate into an opaque Cypher string
with unknown aliases and clause structure is a parser problem that FAILS OPEN
when wrong. Realistic path: move the 10 unbounded sites onto typed helpers and
declare `run_cypher` explicitly unscoped in its docstring.

**The mechanical cause of the misses: the scoping helper is written FIVE times
with five signatures**: `queries.py:62` `_project_where(alias, tag,
has_existing_where=)`; `graph/context.py:18` `_project_filter(alias, tag)`;
`backup.py:239/256` `_node_dump_cypher/_rel_dump_cypher(tag)`; inline branches
in `neo4j_backend.py`; hand-rolled concatenation everywhere else.

The codebase reached the right conclusion ONCE and did not generalize it:
`integrations/asta/CLAUDE.md` says the review queue must go through
`query_review_queue` because "raw `run_cypher` is NOT project-scoped and would
leak other projects' queues."

### GraphBackend is a transport seam, not a data seam
9 abstract methods (`graph/backend.py:21`), one implementation. `create_node`,
`get_node`, `update_node`, `delete_node`, `create_relationship`, `query_nodes`
are real abstractions and centrally scoped. But `query_nodes`' own docstring
(`:141`) routes callers to `run_cypher` for anything past equality filters, and
they went: 78 sites. `initialize()` delegates to hardcoded Cypher DDL;
`count_all()` returns int counts mixed with string sentinels; `run_cypher` is a
pass-through.

Neo4j leakage above the layer: the `neo4j` package import is well contained
(exactly one, `graph/driver.py:28`), but exception classes reach
`graph_tools/__init__.py:886-890` (branching at `:891`, `:901`),
`CircuitOpenError` reaches the agent wire format (`:1162-1164`),
`retrieval.py:181` calls the Neo4j procedure `db.index.fulltext.queryNodes` by
name, `schema.py:23-73` is Cypher DDL as schema definition, and
`schema.py:96-146` MUTATES config in place on a failed `CREATE DATABASE`
(`:134-136`; verified unreachable from the package, callers only in tests: a
landmine, not a live bug).

**Do NOT copy GraphBackend's shape for ContentStore.** Modeled on it,
ContentStore becomes `read_bytes(path)`/`write_bytes(path)` with 35 callers
still owning paths: no versioning chokepoint, no swappability. The interface
must be DOMAIN operations so callers never name a location.

---

## METHOD LAYER (context for Tier 2, no work item of its own yet)

39 acts. Sampling was honest: frontmatter machine-parsed for all 39, regex over
all 39 bodies, but only 4 read end to end, so the file/subprocess boundary is
the least certain and is given as ranges.

- **PURE_GRAPH: 3 confirmed** (`ask`, `chat`, `graph-link`, all read in full).
  A 4th (`queue`) was DEMOTED on full read: its protocol is graph-only but
  `queue.md:26` is "Execute the task completely" over an arbitrary payload.
- **NEEDS_FILES: 12-13.** Dependency is a path CONVENTION, and every one of
  those files has a graph analog the act already writes alongside it.
  `pause.md:137` is the porting recipe: it writes the continuation as an
  `add_note` and renders `.continue-here.md` "as a human-readable view, **not
  the authoritative source**." `note.md:91` is the counterexample where the file
  IS authoritative and porting would be a semantic change.
- **NEEDS_SUBPROCESS: 15-16.** 7 irreducible (Asta/LLM-SR: the external CLI
  owns auth, `transport.py:5` refuses to build an HTTP client); the rest are
  host maintenance (`backup`, `restore`, `update`, `bump`, `init`) or one-line
  conveniences (`graph-review.md:96` shells out to `test -e` for something
  `hash_file` already does server-side).
- **NEEDS_SUBAGENTS: 6 hard** (11 by derived metadata).

Roughly **6 of 39 usable close to as-written** on a graph-only host.

**"Which host am I on" is encoded in THREE unconnected places**: `acts.HOSTS`
(`acts.py:50`, generated), `llmsr/cli.py:81` `_GENERATORS` (hand-written), and
prose at `llmsr-discover.md:143-144`. `acts.py:47-49` acknowledges the
duplication. A third host branches all three; only the first is generated.

`build_plugin.py`'s premise is `dict[str, str]` of relative path -> content
written to disk (`:748-783`, `:830-857`), so a host with no filesystem has
nowhere to receive it. The routing metadata in `render_skill` (`:261-303`) is
already served by `list_acts`, so the DATA survives; only the delivery vehicle
dies.

Integrations: `subprocess` appears in exactly two files across all of
`integrations/`: `asta/transport.py:46` (the documented single boundary) and
`registry.py:408` (`_probe_passes`, only used by `available_services:430-440`).
So **the registry ports as-is if you drop availability probing.** The transport
does not: its contract is FILE-mediated (`transport.py:43,67-75`), nothing
returns over stdout.

---

## Cross-cutting duplication to collapse (feeds several tiers)

- Scoping helper: **5 copies, 5 signatures** (Tier 3).
- Neo4j error-diagnosis table: **3 copies** (`mcp_core.py:32-76`,
  `graph_tools/__init__.py:883-935`, inline `mcp_core.py:160-164`).
- Relationship enum: **3 copies** (`graph/schema.py:76-93`, verbatim
  `Literal[...]` at `mcp_mutations.py:516-521` and `:554-559`). Currently
  identical; nothing enforces it. The handler also accepts a `rel_props` dict
  (`mutations.py:857-862`) neither wrapper exposes.
- Atomic tmp+rename: **6 independent implementations**
  (`knowledge/store.py:27-31`, `:118-121`, `merge.py:137-143,166,170`,
  `graph/migration_prov.py:411-423`, `dashboard/gather.py:113-118`,
  `integrations/llmsr/runs.py:382`).
- Tool schemas: `TOOL_DEFINITIONS` vs live FastMCP signatures (Tier 0.10).
- Host identity: 3 places (method layer, above).

## Server thinness (context for Tier 2)

Thin-wrapper claim holds for **26 of 53**; 27 carry logic existing nowhere
else, 15 of those load-bearing. Notable: `_add_script_impl`
(`mcp_mutations.py:278-303`) hashes the file IN THE SERVER at `:286-290`, so
calling `mutations.add_script` through `execute_tool` directly yields an empty
hash. `add_analysis` (`:327-344`) accepts `parameters`, `output_path`,
`output_hash` and silently DISCARDS all three. `ensure_artifact`
(`:482-506`) has 10 `if <truthy>` guards, and `confidence != 0.0` at `:496`
makes confidence 0.0 unreachable. `validate_task_contract`
(`mcp_ops.py:299-361`) synthesizes contract objects from flat scalars,
hardcoding `Finding -[WAS_GENERATED_BY]-> Execution` at `:339-344`, a shape
existing in no other file.

Five tools reach Neo4j via `get_async_driver` rather than `GraphBackend`, so
they bypass the circuit breaker: `graph_context` (`graph/context.py:44`),
`graph_status`/`graph_health` (`graph/schema.py:193`), `init_schema`
(`schema.py:158`), `detect_stale` (`graph/provenance.py:116`),
`validate_citations` (`validation/citations.py:99`).

## What no reader checked

- The test suite was not run by anyone, and no reader read test bodies beyond
  greps. How much of the suite depends on the process-global backend is
  UNKNOWN and bears directly on Tier 0.4's disruptiveness.
- Whether FastMCP's HTTP transport supplies per-connection context, and what
  shape that object takes. This determines the exact mechanism for Tier 3 and
  is the one external unknown that could change the plan.
- 35 of 39 act bodies were not read end to end.
- `backup.py`/`restore.py` were not read in full by anyone.
- Whether Codex honours `allow_implicit_invocation` (`build_plugin.py:447-449`)
  was asserted in comments, not canaried.
- No reader executed anything against the live Neo4j. Unscoped queries were
  identified by reading Cypher, not by observing cross-project results.

---

# Part II: implementation plans

*Each tier was planned independently against Part I, required to re-verify the
cited lines and to say so loudly where the findings were wrong. Tiers 0, 1, and
2 are complete. Tier 3 is outstanding; see its section.*

## Measurements taken during planning (nobody had run anything before)

All verified independently on this checkout:

- **27,213 knowledge JSON files (107 MB), 25,088 synthesis files (98 MB)**, all
  gitignored, 0 tracked.
- **`list_nodes()` takes 3.74 s** on that store. `read_node()` is 0.13 ms;
  `glob("*.json")` is 33 ms. `list_nodes` costs ~113x the glob it wraps, and two
  production paths pay it on every call: `mcp_ops.py:230` and `retrieval.py:154`
  (`search_findings(mode="temporal")`). **A live performance defect, independent
  of any refactor.**
- **Two inventories of the same directory ALREADY disagree**: glob = 27,213,
  `list_nodes()` = 27,212. `knowledge/A-4d9c7c5d.json` fails model validation
  (bad `type` discriminator), `store.py:85-86` swallows it, `consistency.py:57`
  counts it. **Part I predicted versioning would break identity resolution; it
  is already broken, today, without versioning.**
- `neo4j_backend.update_node:251-287` is `MATCH ... SET n.k = $props.k`, so
  graph-side compare-and-swap is one extra `AND`.
- `NodeBase.file_name` has **2** production consumers (`store.py:26`,
  `migrate.py:135`). No `content_hash` exists anywhere in `wheeler/`.

The guard-test requirement is not ceremony. The central result of Part I is that
**eight documented invariants had silently decayed because nothing enforced
them.** A refactor that adds seams without adding guards reproduces exactly the
failure this audit was run to find. The repo already has the right pattern in
`tests/test_mcp_surface.py::test_monolith_is_gone` and
`tests/test_build_plugin.py::test_committed_tree_matches_generator`.

| Tier | Scope | Gating question |
|---|---|---|
| 0 | Live defects (0.1-0.10) | How to key `_get_backend` without breaking test fixtures that already work around the current global |
| 1 | `ContentStore` seam + node versioning | Sync vs async; the staged-write primitive `merge.py`'s rename-as-commit needs; `change_log` vs `history()` authority |
| 2 | Server-side mode enforcement + server re-partition | Where `run_cypher` goes, given 17 acts grant it and every act edit must flow through both command trees and the plugin generator |
| 3 | Per-connection context + tenant scoping | Whether FastMCP's HTTP transport supplies per-connection context at all |

Tiers 1-3 are deployment work and are optional in the sense that Wheeler runs
correctly today as a single-project local tool. Tier 0 is not: those are defects
in the shipped product.

---

## TIER 0 PLAN: 8 commits, ~13 h (2 days with review)

Commit order. 1-5 are independent and could land in parallel worktrees.

| # | Commit | Items | Why here |
|---|---|---|---|
| 1 | `fix(mcp): make request logging non-fatal` | 0.9 | First: unblocks read-only-FS testing for everything after, and commit 8 adds `@_logged` to a tool |
| 2 | `fix: two one-line boundary defects` | 0.2, 0.7 | Single-line, different files, zero interaction |
| 3 | `fix(search): one store path, one atomic write` | 0.5, 0.6 | **Must be together**: 0.5 makes `retrieval.py` a live reader of the pair 0.6 says can be torn |
| 4 | `fix(knowledge): unique tmp names` | 0.3 | Standalone |
| 5 | `fix(cypher): one write guard, word-boundary matched` | 0.1 | Separate: behavior changes in BOTH directions, needs its own bisect point |
| 6 | `fix(graph): key the backend cache on its config` | 0.4 | Alone. Highest blast radius, the one worth reverting cleanly |
| 7 | `refactor(cli): route 3 graph verbs through execute_tool` | 0.8 | After 6, so the new path exercises the keyed cache |
| 8 | `chore: delete TOOL_DEFINITIONS, fix doc drift` | 0.10 + drift | Deferrable without blocking the tier |

**Key implementation notes.**

- **0.1**: do NOT import the private `_CYPHER_WRITE_RE` from `neo4j_backend`
  into `mcp_core` (a private, backend-specific name for a backend-neutral fact,
  re-coupling the MCP surface to Neo4j). **Extract to a new
  `wheeler/graph/cypher_guard.py`** (zero internal deps, stdlib `re`) consumed
  by both. That makes "one guard, two consumers" structurally true and testable.
  Verified safe: **zero** `CALL`/`LOAD CSV`/`FOREACH` usages across all 40 act
  files, and internal callers use `backend.run_cypher` which has no guard. Cost
  accepted: an agent can no longer run a read-only `CALL` ad hoc. Name the loss
  in the docstring and error string.
- **0.4**: `initialize()` (`neo4j_backend.py:169-173`) runs 33 DDL statements.
  Key the backend on `(uri, username, database, project_tag,
  resolved_project_root)` but gate `initialize()` on the **connection triple
  only** — constraints are database-scoped, and the e2e sandbox mints a fresh
  project root per test, so naive keying would pay 33 round trips per test.
  Consider including `sha256(password)[:16]`, mirroring the driver key
  (`graph/driver.py:74-76`). Keep the name `_get_backend` and its single
  positional `config`: the service scaffolder pins that literal import
  (`tests/test_scaffold_service.py:104`). Add `reset_backend_cache()`; the one
  fixture at `tests/test_triple_write_project_root.py:123-130` switches to it.
- **0.6**: **tmp+rename does not fix this.** Two files renamed back to back is
  still two commit points. Collapse to a single `.npz` (matrix + ids + meta),
  one rename, with a legacy-pair read path that migrates. The
  multiple-live-copies half is Tier 1 shaped and is NOT addressed here; say so
  in the commit message rather than letting it look handled.
- **0.8**: `execute_tool` returns a JSON **string** and returns `{"error":...}`
  rather than raising, so the existing `try/except -> typer.Exit(1)` is
  insufficient; check the error field explicitly or failures print as
  successes. `cli.py` already uses `asyncio.run` 16 times (copy `:155`).
  Removing the verbs makes `get_sync_driver` (`cli.py:19`) and
  `PREFIX_TO_LABEL` (`:22`) unused, which will fail `ruff` in the pre-commit
  hook. Behavior change to expect: `validate_and_normalize` now runs, so inputs
  the bare Cypher accepted may be rejected.
- **0.10**: **delete it.** The `corpus_id` correctness is rot-shaped, not
  evidence of value: the entry was written when the field was added and never
  touched, while the live surface drifted independently and nothing compared
  them. Bank the *comparison* as a guard test against the live FastMCP schema,
  covering all 53 tools instead of 30. Option B (generate servers from it) is
  not viable at this cost: FastMCP derives schemas from signatures + docstrings,
  and 27 of 53 server functions carry logic existing nowhere else, so their
  signatures are not derivable from the handler registry.

**Two live defects found during Tier 1's verification, handed here:**
- **`repair_consistency(dry_run=False)` deletes `synthesis/MORNING-*.md`.**
  `_SYNTHESIS_INDEX_FILES` (`consistency.py:21`) exempts three names;
  `dream.md:372` writes a fourth every run with no matching `knowledge/*.json`,
  so it lands in `synthesis_orphaned` (`:75`) and is unlinked at `:154-165`.
  Mechanism verified; **not observed firing on this checkout** (zero `MORNING-*`
  files present, and "never ran" cannot be distinguished from "already
  deleted"). Destroys scientist-facing output in any project where dream runs
  and repair is then invoked.
- **`knowledge/A-4d9c7c5d.json` fails validation**, causing the 27,212 vs
  27,213 inventory split above. A legacy Analysis file that
  `migrate_knowledge_files` (`graph/migration_prov.py:343`) missed.

---

## TIER 1 PLAN: ContentStore + versioning, ~14-20 days (A-F)

### The four decisions, settled

1. **Async interface, synchronous local implementation.** `async def` methods
   doing inline blocking file I/O, no thread pool. The audit's "fork in the
   road" is not a fork: every helper is called only from `async def`, and there
   is **exactly one** genuinely sync entry point (`cli.py:1747`, one
   `asyncio.run`). Conversion is ~11 helpers / ~35 awaits, larger than Part I
   said, because it omitted five in `graph_tools/__init__.py` (`:496, 577, 623,
   706, 754`). Sync-plus-remote does not run slowly, it **stalls the server**:
   `_read_knowledge_node` runs inside `async def query_findings` on FastMCP's
   loop. Explicitly NOT `asyncio.to_thread` locally: measured `read_node` is
   0.13 ms, so a thread hop costs more than the read.
2. **Merge keeps cross-layer atomicity** via `store.transaction()`, shaped
   line-for-line on the existing staged writes. This also closes an unnamed
   gap: **today only graph-delete failure rolls back**; if the rename at
   `merge.py:166` succeeds and `:170` fails, knowledge is merged and synthesis
   is not, with no rollback and no error path. Honest limit: two renames are
   not atomic on POSIX, so `commit()` narrows the window rather than closing it.
   Two mandatory mitigations: order **content before view** (a crash leaves a
   stale view over correct content, the recoverable direction, since
   `render.py` is pure), and ship `check_consistency(deep=True)`'s view-hash
   dimension in the **same phase** so the residual failure is detected and
   auto-repaired. Shipping the primitive alone and calling merge atomic would
   manufacture a ninth row in Part I's table.
3. **`history(id)` is authoritative; `change_log` is demoted to a governance
   log** (envelope transitions only) joined by a new `ChangeEntry.version`.
   Authority cannot rest on the thing that gets lost. Migration discards
   nothing: existing entries are retained with `version=0`, a reserved
   "predates versioning" sentinel, acquiring real numbers only as nodes are
   naturally written. **No backfill pass over 27,213 files.** `change_log` gets
   capped at 200 entries, defensible only because `history()` now holds the
   content record.
4. **`models.py` LOSES a dependency.** Add three builtin-typed fields
   (`content_version: int`, `content_hash: str` on `NodeBase`; `version: int`
   on `ChangeEntry`) and **delete the `file_name` property** (`:49-51`), which
   has 2 production consumers and is where one-file-per-node is encoded in the
   leaf. Naming moves entirely into `LocalFileContentStore`.

### The design move that dissolves the `consistency.py` hard spot

**Versioning must NOT change on-disk naming.** Current content stays at
`knowledge/{id}.json`, byte-shape unchanged; history lives entirely under
`.wheeler/versions/{shard}/{id}/`. No historical version ever appears in
`knowledge/`, so `consistency.py:57`'s glob never sees one, the checker works
unmodified through the migration, the backup wire format is unchanged, and
**current-version resolution is free** because the version is a field inside the
current document. `shard` = two hex chars after the id prefix (256 buckets,
~106 nodes each at 27k), because a flat directory is already at the edge.

### Versioning policy: a `put` always persists, but mints a version only when the content hash changes

`_ENVELOPE_FIELDS` (declared in `content_store.py`, **not** `models.py`) covers
`updated, tier, stale, stale_since, stability, change_log, display_name,
content_version, content_hash`. Calibrated against the explosion hazards:
`wh dream` promoting 500 tiers writes 500 files and mints **0** versions;
`detect_stale` flagging every Script mints **0**; `link_nodes` writes the node
**0** times; `update_node(description=...)` mints 1. **OPEN, scientist's call:**
whether `custom_review_state` is content or envelope (currently placed on the
content side; one frozenset edit either way).

### The CAS primitive

Claim `versions/{shard}/{id}/{n:07d}.json` via `os.link(tmp, target)`, which
raises `FileExistsError` if another writer already took `n`. Atomic
compare-and-swap on any POSIX filesystem, no lock. The snapshot is claimed
**before** the current file is replaced, so a crash leaves an orphan snapshot
(harmless, detectable), never a lost version. Graph side gains an optional
`expected_version` -> one extra `AND` at `neo4j_backend.py:275-282`.
`_update_knowledge_node` and `_update_knowledge_tier` become
read-modify-write-**retry** (3 attempts on `VersionConflict`), which resolves
Part I's documented lost-update interleaving: both writers converge, and
`change_log` gets N+2 entries because each append happens against a re-read
snapshot.

### `list_nodes` does not survive

It is the shape that cannot port: parse-everything, 3.74 s locally, 27k round
trips remotely. It splits into three ops that are each ONE server-side call:
`list_ids` (glob+stem, 33 ms), `list_hashes` (the consistency checker's entire
input, via a `.wheeler/versions/hashes.idx` sidecar maintained on `put`), and
`list_summaries` (what `retrieval.py:141-160` and `mcp_ops.py:215-233` actually
want). `iter_nodes` streams true full scans. **This is a live ~113x fix on two
hot paths, independent of portability.**

### Synthesis stays in ONE interface

As a capability-flagged, explicitly-derived sub-namespace (`put_view`,
`get_view`, `list_view_ids`, plus `put_index_view`/`list_index_views`). Three
reasons against a second object: the merge transaction spans both layers; the
consistency checker's whole job is comparing the two inventories; and
`WriteReceipt`'s `json`/`synthesis` bools are one atom. The asymmetry survives
in method names and a capability flag, not an object boundary. `put_index_view`
is load-bearing: it replaces the hardcoded three-name frozenset at
`consistency.py:21` with a namespace, making the `MORNING-*` misclassification
impossible by construction.

### `/wh:dream` and backup/restore

- **dream gets an MCP tool**, `write_index_view(name, markdown)` in
  `mcp_mutations` -> `execute_tool` -> `store.put_index_view`. The decisive
  argument is not portability, it is the live deletion bug above.
- **backup/restore: model-level export, not `iter_raw()`/`put_raw()`, sequenced
  LAST.** Opaque bytes do not serve these callers: backup does not copy bytes,
  it **rewrites them semantically** (`_rewrite_knowledge_json_bytes:591-600`
  parses each file to install a `${PROJECT}` sentinel), so `iter_raw()` just
  relocates a parse it is already doing. Export via `iter_nodes()` makes path
  rewriting a model transform and deletes the regex-over-markdown. **Drop
  synthesis from the archive** (pure-derived; `restore.py:736-738` already says
  triple-write replay overwrites it): 98 MB off every archive here. History
  behind `--with-history`, default off. Interim if deferred: gate raw `Path`
  access on `"raw_export" in store.capabilities` so a non-filesystem deployment
  reports "backup unavailable" rather than silently writing an empty archive.

### Phases

**A** seam + guard + baseline suite run (2-3 d) · **B** the two reach-around
WRITERS first, plus `execute_merge` routed through `execute_tool` with two
receipts (2-3 d) · **C** 13 caller files, 13 commits, allowlist 30 -> 2 (3-4 d) ·
**D** async, one commit (1-2 d) · **E** versioning, CAS, hash, receipt, deep
consistency, `node_history` (5-7 d) · **F** `write_index_view` + dream (0.5 d) ·
**G** backup/restore export, deferred (4-6 d, least trustworthy estimate).

The guard test is `test_no_reach_around_content_store`: an AST walk asserting
`project_knowledge_dir` and `project_synthesis_dir` are called only from
`content_store.py` and `config.py`, with a **30-entry allowlist that only
shrinks** (`test_allowlist_only_shrinks` with a hardcoded ceiling lowered each
commit). Thirty is the migration's progress meter.

**Top risk, and it displaced the expected one:** a new cached global
reproducing the `_get_backend` defect. The suite's dominant idiom is
self-cleaning `patch()`, so fixtures are not the hazard, the *design* is.
`get_content_store(config)` must be keyed on resolved paths from day one.

---

## TIER 2 PLAN: ~8-9 days, and it does NOT need Tier 3 to start

### The mechanism is custom middleware, not `tool.auth`

See "The mechanism trap" in Part I. `tool.auth` is inert on stdio, which is
100% of today's deployments. Custom middleware (`on_list_tools` +
`on_call_tool`) is transport-agnostic **because it does not inspect transport**.
`tool.auth` + `restrict_tag` becomes an additive second layer on HTTP only,
free once tags exist.

### Do NOT re-partition the servers

Provably insufficient, independent of the five exceptions: five read-only acts
need `detect_stale`, and no subset of four servers expresses "read + one ops
tool". **`derive_mode` produces a total order; capability need is a lattice.**
Keep the four servers as a role partition for discoverability and carry mode on
capability tags.

- **`run_cypher`: never moves.** No valid destination exists (all 20 grantors
  would need it; only `ops` reaches all 20, which strips it from the four
  write-mode grantors). Avoids a 48-file blast radius.
- **`index_node` -> `mcp_mutations`: do it.** 2 acts, both already write-mode.
  A genuine write sitting in the one server chat mode always registers, so it
  is where an absent gate leaks.
- **`init_schema` -> ops: defer.** 1 act, cosmetic under tag gating.

### Split the flag-escalated writes rather than gating on arguments

Reading a typed boolean from a structured protocol object is **not** the same
class of check as substring-scanning opaque Cypher, so a middleware rule would
not repeat the `run_cypher` mistake. Split anyway, on a narrower decisive
ground: **a parameter rule fails open on rename.** Rename `repair` to
`do_repair` and the rule silently stops matching, the tool stays listed, the
write goes through, and nothing fails. A tool split cannot fail that way.
Nearly free, because the source is already half-split (`_link_dependencies` is
its own function at `mcp_ops.py:95`; `graph_consistency_check` already branches
`dry_run`). After the split, **no gate anywhere reads an argument.**

### Tags

New leaf module `wheeler/capabilities.py` (zero internal imports, same layer as
`models.py`/`config.py`), holding `TOOL_CAPABILITIES` for **all 53 tools by
name**. NOT in `TOOL_DEFINITIONS` (dead) and NOT in `_TOOL_REGISTRY` (29 names
against 53 tools, so it would give the appearance of coverage over half the
surface). Applied by a shared `apply_capability_tags(mcp)` in `mcp_shared.py`:
`Tool.tags` is assignable post-registration, so **one table, not 53 edited
decorators**. Two tags beyond the obvious: `RAW_CYPHER` on `run_cypher` alone
(separately deniable for multi-tenant, since `mcp_core.py:300` is unscoped by
construction) and `SCHEMA_ADMIN` on `init_schema`.

### Mode resolution per transport

- **stdio (both hosts today):** `WHEELER_MODE ∈ {chat, write, execute}`,
  resolved once in `main()`, defaulting to `execute` so existing deployments
  see zero change. Emitted into Codex profiles as `env = { WHEELER_MODE = ... }`
  alongside the existing `enabled = false`, so a hand-edited profile that
  re-enables `wheeler_mutations` still gets refused by the server.
  **UNVERIFIED: that Codex passes `env` through on `mcp_servers` entries.
  Canary before Phase 4 lands.**
- **HTTP (future):** mode comes from the token via `restrict_tag`. This is
  where Tier 3 plugs in.
- **Never:** per-*act* mode on a single stdio connection. The host never tells
  the server which skill is active; the enforceable unit is the **connection**.
  Inferring mode from the `get_act` call is agent-controlled input, i.e. a
  fourth "looks enforced, isn't".

### Fixing `derive_mode`

Replace the prefix test (`acts.py:74-85`) with capability-based derivation
reading the same table the middleware reads, so `ask`/`report`/`resume`/`status`
derive `chat` and `graph-review` derives `chat` after the split. **Hard ordering
constraint: split before re-deriving.** Then derive `MODE_SERVERS`
(`build_plugin.py:135-139`) from the capability table rather than hand-writing
it, so Codex profiles cannot drift from in-process enforcement. That is what
permanently closes the `/wh:ask` gap.

### Phases

**0** prerequisites: 0.1 guard, 0.9 `_logged`, 0.2 kwarg, hazard gate (~1.5 d) ·
**1** capability table, inert tags, tests 1 and 5 (~2 d) · **2** splits +
`index_node` move (~0.5 d) · **3** middleware gate, `WHEELER_MODE`, tests 2/3/6
(~2 d) · **4** generator + `derive_mode` (~1.5 d) · **5** fileless gate
conditions (~1.5 d) · **6 optional** `restrict_tag` for HTTP, after Tier 3
(~0.5 d).

Phases 1-3 are **behavior-preserving by construction** (inert tags, then a gate
defaulting open). Only Phase 4 changes what an existing user experiences, only
on Codex, and only by removing access that was never intended.

### Guard tests

Replace `test_query_server_is_read_only_by_name`
(`tests/test_mcp_surface.py:86-90`), which greps name prefixes and caught none
of the five misplacements. New `tests/test_capability_surface.py`: every tool
tagged and every tag key live; no `CONTENT_WRITE` tool reachable in chat mode
**by capability, not name**; **a hidden tool cannot be called** (the half that
matters, since `remove_tool`-style filtering alone is defeated by calling an
unlisted tool); `run_cypher` rejects every bypass form and passes the
`DATASET ` read; **`test_allowed_tools_never_widen_mode` across all 39 acts with
wildcards expanded, which fails today** on the five acts above; the fileless
surface excludes exactly the 8 disk tools; every `CONTENT_WRITE` tool routes
through `execute_tool` (`xfail` for `execute_merge`, citing Tier 1 Phase B1).

---

## TIER 3 PLAN: ~2.5 weeks full, but the first week is bug-fixing

### Phase A is NOT multi-tenant prep

**Wheeler already supports two projects on one Neo4j.** That is what
`project_tag` is for, it is shipped and documented. For that supported
configuration, `consistency.py:48`, `communities.py:76`, and `ensure_artifact`
are **broken today**. Phase A fixes a shipped feature; multi-tenant serving is
merely the thing that would make the breakage catastrophic rather than
confusing.

### The `_config` proxy: ~60 sites stay untouched [the cost-deciding answer]

Measured by shape, the ~60 references are **3 attribute reads** and **34
pass-by-reference into library functions**, so the risk is not the reference
count, it is whether anything STORES a config past the request.

> **`self._config = config` occurs EXACTLY ONCE in the whole codebase:
> `neo4j_backend.py:108`. [VERIFIED independently]**

That one site is the dangerous one: `Neo4jBackend._project_tag` (`:123-126`)
reads `self._config.neo4j.project_tag` per call, which with a proxy would
silently become "whichever tenant is current."

```python
_tenant_config: ContextVar[WheelerConfig | None] = ContextVar("wheeler_config", default=None)

def resolve_config() -> WheelerConfig:
    t = _tenant_config.get()
    if t is not None: return t
    if _REQUIRE_TENANT: raise RuntimeError("no tenant context bound to this request")
    return _ambient_config()          # today's behavior, byte for byte

class _ConfigProxy:
    def __getattr__(self, name): return getattr(resolve_config(), name)

_config = cast(WheelerConfig, _ConfigProxy())    # the ~60 sites stay untouched
```

**THE RULE, stated so it survives rather than as a list of sites:**

> **Any function that uses config as a CACHE KEY must unwrap it first.**

Today that is three functions: `_get_backend` (`graph_tools/__init__.py:869-880`),
`execute_tool` (`:938`, which injects config into `args["_config"]`, consumed at
`mutations.py:750,789` where it crosses `await` boundaries inside a dict), and
**Tier 1's new `get_content_store(config)`**. Stating it as a rule is what makes
it survive Tier 1 landing.

**Net: ~60 edits become 3 unwraps + 1 guard test.** Phase D drops from 4-5 days
to 2-3. Test blast radius is ~zero: tests never touch `mcp_shared._config`, they
pass `MagicMock()` straight into library functions. One `cast()` handles mypy;
do NOT subclass `WheelerConfig` (Pydantic v2 attribute access fights
`__pydantic_fields_set__` / `__pydantic_extra__`).

### What `MiddlewareContext` actually carries

Full dataclass (`server/middleware/middleware.py:47-63`): `message`,
`fastmcp_context`, `source`, `type`, `method`, `timestamp`. That is everything.

- **Connection identity:** indirectly, via `fastmcp_context.session_id`
  (`server/context.py:637-690`). Type is `Context | None`; handle `None`.
- **Tenant identity: ABSENT.** It must come from `get_access_token()`
  (`dependencies.py:467-530`) returning `AccessToken` with `.client_id`,
  `.scopes`, `.claims`.

**`session_id` identifies WHO IS CONNECTED; a connection is not a tenant.**
Binding config to `session_id` gives isolation with no authorization behind it.
The tenant key must be a validated token claim, and the claim -> `WheelerConfig`
mapping must be a **server-side registry**: if the client names a project root,
that is directory traversal into another tenant's `knowledge/`.

**Trap:** `get_http_headers()` strips `authorization` and `mcp-session-id` by
default (`dependencies.py:437-452`). Anyone reaching for headers finds the auth
header missing and is tempted to "fix" it with `include_all=True`. Wrong
direction.

**The clean boundary this yields:**

> **stdio has no tenant and must not pretend to have one. Multi-tenant serving
> is an HTTP-only deployment mode.**

That is designed degradation, not a limitation: stdio -> ContextVar unset ->
ambient config -> today's behavior exactly. `_REQUIRE_TENANT` is set only by the
HTTP entrypoint.

Verified supporting facts: FastMCP enters a `Context` around every request
handler, so **no tool signature changes**; the middleware chain composes with
`await call_next(context)` **in the same task**, so a ContextVar set in
`on_call_tool` reaches the tool body. **Caveat to record:** in Docket workers,
auth context is restored from a snapshot, not live, so a ContextVar set in
`on_call_tool` would NOT propagate into a background task. Wheeler is unaffected
(`pyproject.toml:51` pins `fastmcp>=3.3,<4` without `[tasks]`), but **do not
adopt FastMCP background tasks without revisiting tenant binding.**

**Tier 2 integration constraint:** tenant binding and the capability gate both
want middleware on all four servers. They must be **ONE middleware, or
explicitly ordered with tenant-binding FIRST** — a capability gate that varies
per tenant cannot evaluate before the tenant is bound. Recommend a single
`WheelerMiddleware` doing bind-then-gate in `on_call_tool`, with the gate also
applied in `on_list_tools`.

### Node ids: widen entropy, KEEP the constraint database-wide

The per-label `id IS UNIQUE` constraint (`schema.py:23-26`) is a **safety
property**, not only a hazard: `create_node` uses a bare `CREATE` through
`_once`, so a collision is a loud `ConstraintValidationFailed`, never a silent
bind. That same database-wide constraint is **exactly what makes the 10
id-bounded reads safe**. **Scoping the constraint per `project_tag` would
convert one loud availability bug into ten silent confidentiality bugs.**

Instead widen `token_hex(4)` -> `token_hex(8)` at `schema.py:20` (32 -> 64 bits;
at n=1e6, p ~= 2.7e-8). Ids grow 10 -> 18 chars. **Pre-check required:** verify
the `[F-xxxx]` citation regex is length-agnostic and sweep hardcoded test ids.
Deferred with a trigger: fire when one label in one database passes ~10k nodes.

### The 10 unbounded reads, priority ordered

**P0, must land before a second tenant shares a database:**
1. `mutations.py:726,732` — new typed helper `find_artifact_by_path(...)`, ~15
   lines, fixes all three bad outcomes at once (see the correction in Part I).
2. `consistency.py:48` — scoping clause. Beyond the leak, it compares
   database-wide graph ids against a project-scoped `knowledge/` glob, so every
   other tenant's node reports `graph_only`, **the one class repair cannot fix**.
   The report is unusable, not merely leaky.
3. `communities.py:76` — must filter **both endpoints**, exactly as
   `backup.py:_rel_dump_cypher:256-268` already does.

**Landing WITH P0 because they form one exploit path:**
4. `merge.py:266,287` (reads) and `:274,295` (**unscoped writes**) — today the
   reads faithfully enumerate a cross-tenant edge and the writes faithfully
   recreate it.
5. `retrieval.py:373,400` — `search_context` hop expansion; seeds are scoped
   (`:200`), neighbours are not. **Must land with #4**: #4 creates the edge, #5
   turns it into a returned result. Splitting them leaves the path open between
   commits.

**P1:**
6. `contracts.py:276,300,316` — two compounding problems: `session_id` is not a
   tenant key, AND `_SESSION_ID` is one value per process, so the filter selects
   across tenants by construction.
7. `mcp_ops.py:104,116` — **HARD SEQUENCING CONSTRAINT: bundle with Tier 0.2 in
   ONE commit.** These are the same lines as the `parameters=`/`params=` bug.
   They have never executed. **Fixing 0.2 alone converts a dead path into a live
   unscoped `CONTAINS` scan feeding `execute_tool("link_nodes")`.**
8. `mcp_core.py:300` — not fixable by scoping, and that is the point. Deny via
   Tier 2's `RAW_CYPHER` tag in multi-tenant; fix the guard (Tier 0.1) and
   document it unscoped in single-tenant.

### Collapse the five helpers

New `wheeler/graph/scoping.py` (layer 2, imports `config` only) exporting
`project_where`, **`project_where_all(aliases, ...)`**, and `inject_ptag`.
Naming the both-endpoints form is what makes "filter both endpoints" the
**default rather than something you remember** — that omission is precisely the
`communities.py:76` miss. Add `run_cypher_scoped(query, *, aliases, ...)` to the
backend: the caller declares the alias it knows, the backend owns the predicate
text. That is the safe version of the chokepoint, and it cannot fail open.

**Leave `neo4j_backend.py`'s inline branches alone.** They build `stmt` and
`params` together, are the reference implementation, are test-covered, and the
audit found zero defects in them. Collapse where it prevents a miss, not
everywhere it is possible.

### The 12 backend bypasses split three ways

- **7 are already tenant-scoped** (`provenance.py:193,263,392`;
  `validation/citations.py:134,142,178,188`). A **resilience** defect (no
  breaker, no retry), not a tenancy one; belongs in the remote-Neo4j workstream.
  **Required per-method check:** `provenance.py:263` is a `MATCH ... SET`
  computing `dep.stability` from `old_stab`; if that reads at match time, a
  replay double-decays, so it must be `_once`. Extend the decision table in
  `wheeler/graph/CLAUDE.md` per moved method.
- **2 are deliberate** (`aura.py:396`, `cli.py:374`): connectivity probes that
  must not sit behind a breaker. Add a one-line comment.
- **3 are subsumed by Tier 0.8** (`tools/cli.py:223,266,333`).

### REFUSE rather than fix: LLM-SR and the dashboard

`_userland.py:89-103` calls `spec.loader.exec_module()` on a path from env vars
or `.wheeler/llmsr/{kind}.py`: **arbitrary code execution in the server process,
selected by project-supplied content.** Tenant B's module would run with tenant
A's ContextVars, handles, and driver. No in-process containment exists, so no
dict key fixes it. **The refusal is nearly free:** zero `llmsr` references in
any of the four servers or in `tools/graph_tools/`. Enforce by capability (a tag
the multi-tenant profile denies), never a path guard on command text.

### Guard tests

**Static, AST-based, not grep.** The queries are multi-line implicit string
concatenations (`consistency.py:48`, `communities.py:76-80`,
`retrieval.py:374-379`), so **a line-based grep sees one fragment and would
greenlight `communities.py`.** Walk each `run_cypher` call, join every
`Constant` under the first positional arg, and require either a
`_wheeler_project` predicate, a `scoping.py` helper in the enclosing statement,
or an allowlist entry carrying its reason. **Assert the allowlist is EXACT** so
it cannot become a dumping ground, and assert `_marshal.py:313-315`'s
deliberate-exception comment still exists.

**Live, two-project e2e.** The audit's biggest gap: unscoped queries were found
by READING Cypher, never by observing a leak. Generalize
`tests/test_backup_scope.py`'s `two_projects` fixture (`:133-186`), which
already carries the repo's data-safety discipline (per-run `RUN_TAG`, teardown
deleting only by that tag, never a bare `MATCH (n)`). Give the two configs
**separate project roots**: half these bugs are the graph half and the file half
disagreeing, and a one-root fixture cannot see them. `check_consistency(A)`
reporting `graph_only == []` **fails today** and is the cheapest proof the suite
is blind. Assert positively that **`run_cypher` DOES leak**, so the deliberate
exception is documented by a passing test that fails if someone silently scopes
it. Fix a real defect in the precedent while generalizing: `:194-199` resets
`_async_driver` and `_async_driver_uri` but not `_async_driver_key`, which
`driver.py:76` calls authoritative.

### Phases and the stopping point

**A** live scoping bugs + create `scoping.py` (2-3 d) · **B** guard tests, static
+ live (2 d) · **C** remaining scoping + opportunistic collapse (2 d) · **D**
per-connection context, proxy + keyed globals + middleware + HTTP transport
(2-3 d) · **E** refusals + capability gating, **sequence WITH Tier 2, not
after** (2 d) · **F** id widening, deferred (1-2 d).

Prerequisites: Tier 0.4 before D; 0.9 before D's `_request_logger` half; 0.5+0.6
before D's `_embedding_store` half (six live construction sites, or per-tenant
keying multiplies them); **0.2 must not ship without the `mcp_ops.py` scoping in
the same commit.**

> **A+B is about one week and delivers correct two-projects-on-one-database
> behavior, which is a shipped and currently broken feature. That is the right
> place to stop if multi-tenant serving is speculative.**

**Alternative to keep on the table:** one server process per tenant, which is
what Wheeler does today via `uvx`, costs zero engineering and gives isolation at
the OS process boundary. D and E buy multi-tenancy WITHIN one process. Build
them only if the measured ~370 ms per-launch cost is actually the constraint.

### OPEN
1. Composite uniqueness on `(label, path, _wheeler_project)` would close
   `ensure_artifact`'s check-then-act race, but composite node-property
   uniqueness is **Enterprise-only**. Unverified against the target edition.
2. `provenance.py:263` retry classification needs the `old_stab` read-source
   checked before choosing `_once` vs `_retry`.
3. Citation-regex length-agnosticism, the pre-check for Phase F.
4. The full `repair_consistency` path was not read end to end (`:168-171` warns
   only, so it is safe today).
