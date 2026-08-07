# graph/ -- Knowledge graph backends and schema

The graph is an **index layer**: metadata, relationships, embeddings,
and file pointers. Content lives in `knowledge/*.json` files.
Human-readable synthesis in `synthesis/*.md`.

## Backend

Neo4j is the active backend. Kuzu is deprecated.

- **Neo4j** (`neo4j_backend.py`): primary, via Neo4j Desktop or Docker
- Connection: `bolt://localhost:7687`
- Browser: `http://localhost:7474`

Selected by `config.graph.backend` ("neo4j").
Factory: `get_backend(config)`.

## What the Graph Stores Per Node

`id`, `type`, `tier`, `title` (~100 chars), `file_path`, `created`,
plus type-specific filterable fields (confidence, priority, status, doi).

## Node Types and Prefixes

Defined in `wheeler/models.py` (canonical), re-exported by `schema.py`:

F=Finding, H=Hypothesis, Q=OpenQuestion, D=Dataset, P=Paper,
W=Document, S=Script, X=Execution, PL=Plan, N=ResearchNote, L=Ledger

Finding has additional fields: path, artifact_type, source.

## Relationships (14 types)

PROV (W3C standard):
  USED, WAS_GENERATED_BY, WAS_DERIVED_FROM, WAS_INFORMED_BY,
  WAS_ATTRIBUTED_TO, WAS_ASSOCIATED_WITH

Semantic (Wheeler-specific):
  SUPPORTS, CONTRADICTS, CITES, APPEARS_IN, RELEVANT_TO,
  AROSE_FROM, DEPENDS_ON, CONTAINS

## Key Modules

- `backend.py`: `GraphBackend` ABC (create/get/update/delete node, relationships, queries)
- `schema.py`: Constraints, indexes, `generate_node_id()`. Imports prefixes from `models.py`
- `context.py`: `fetch_context()` returns size-limited markdown for prompt injection
- `provenance.py`: `hash_file()`, `detect_stale_scripts()`, staleness detection
- `driver.py`: Neo4j connection pool singleton, connection settings, `run_with_retry()`

## Provenance

Top-level `wheeler/provenance.py` handles stability scoring and
invalidation propagation. `propagate_invalidation()` uses transitive
traversal through WAS_GENERATED_BY|USED chains with exponential decay.

## Neo4j Session Constraint

Neo4j sessions don't support concurrent queries. Never use `asyncio.gather`
inside a session. Run queries sequentially.

`run_with_retry()` is built to satisfy this rather than work around it: it takes
an async **factory**, not a coroutine, and calls it once per attempt. Every
attempt therefore opens its own session, and attempts are strictly sequential.
Do not turn that loop into a gather.

## Transient Retry

`driver.py::run_with_retry(operation, *, breaker, attempts, base_delay, label)`.
A remote database (Aura) drops connections a local one never does, so a
transient failure must not surface as a hard error.

Classification is delegated, never duplicated:

- `CircuitOpenError`: stop. The breaker is checked before every attempt and the
  error propagates immediately instead of being retried.
- `is_deterministic_neo4j_error()` (`circuit_breaker.py`): do not retry. Syntax,
  type, parameter and schema errors are caller bugs; replaying repeats the bug.
- Otherwise the neo4j driver's own `Neo4jError.is_retryable()` decides. Note it
  returns False for `IncompleteCommit`, because a commit whose outcome is
  unknown must not be replayed.

`Neo4jBackend` wraps it two ways:

| Wrapper | Meaning |
|---------|---------|
| `_retry(op, label=)` | Safe to replay |
| `_once(op, label=)` | Must not be replayed. Literally `attempts=1` |

`_once` is the one-attempt case of the same wrapper so the replayed and
unreplayed paths cannot drift in how they check the breaker or record failures,
and so "do not replay here" is explicit and greppable instead of implicit in the
absence of a wrapper.

### Which backend methods replay

| Replayed | Not replayed |
|----------|--------------|
| `get_node`, `query_nodes` | `create_node` |
| `update_node` | `create_relationship` |
| `delete_node` | `count_all` |
| `run_cypher` (read-only query) | `run_cypher` (query that can write) |

**Rule for a NEW method**: replay reads, and writes that assign fixed values
(`MATCH ... SET`). Do not replay anything whose second application differs from
its first. The hazard is usually not duplication:

- `create_node` **cannot** duplicate: the `id` uniqueness constraint forbids it,
  and the id is generated before the retry boundary so a replay reuses it. It is
  excluded because a committed-but-unacked write replays into
  ConstraintValidationFailed, so the method would report failure for a write
  that landed and the caller would file a repair receipt for a node that exists.
- `create_relationship` is the one that really duplicates. Relationships carry
  no uniqueness constraint, so a replay creates a second parallel edge, and a
  doubled provenance edge is invisible until someone counts. Switching it to
  MERGE would make it replay-safe but changes what linking means to callers, so
  that is its own change.
- `count_all` delegates to `get_status`, which catches its own exceptions and
  returns `_status: offline` rather than raising, so there is no failure to
  retry. `get_status` is un-retried at its own definition too: it is a probe
  that must stay fast when Neo4j is simply down.
- `run_cypher` is decided per query by `_is_read_only_cypher()`, because
  `merge.py` and `restore.py` send real writes through it. Whole-word matching
  is load-bearing: a substring test sees `SET` inside `Dataset` and would refuse
  to retry almost every read.

**`delete_node`'s `existed` flag is not optional.** `DETACH DELETE` is
idempotent but its return value is not. If attempt 1's delete commits and only
the ack is lost, the replayed existence check finds nothing and would report
False for a delete that succeeded, leaving the node's `knowledge/*.json` and
`synthesis/*.md` behind as orphans: the retry would cause the exact triple-write
drift this layer exists to prevent. The flag carries across attempts, so once
any attempt has seen the node, a later one still reports success.

## Connection Settings

`driver.py::connection_settings()` returns one kwargs dict used by BOTH the
async and sync drivers, so the two cannot drift. Defaults work locally and
against Aura; all six are env-overridable:

| Env var | Default | Note |
|---------|---------|------|
| `WHEELER_NEO4J_POOL_SIZE` | 50 | Under Aura Free's connection cap |
| `WHEELER_NEO4J_ACQUISITION_TIMEOUT` | 30s | Wait for a pooled connection |
| `WHEELER_NEO4J_MAX_LIFETIME` | 1800s | Aura's load balancer drops long-lived connections |
| `WHEELER_NEO4J_CONNECT_TIMEOUT` | 15s | Enough for a TLS handshake over a WAN |
| `WHEELER_NEO4J_RETRY_ATTEMPTS` | 3 | Total attempts, not extra retries |
| `WHEELER_NEO4J_RETRY_BASE_DELAY` | 0.25s | Doubles per attempt, plus jitter |

These live in env vars rather than `Neo4jConfig` for reasons of timing, not
design. Folding them into the config schema is a known follow-up.

The async driver singleton is keyed on
`(uri, username, database, sha256(password)[:16])`. Keying on the URI alone was
a latent bug: rotating the password silently reused a driver still holding the
old credentials. The password is a digest so rotation invalidates the cache
without parking the secret in a module global.
