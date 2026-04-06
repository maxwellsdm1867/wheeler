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
- `driver.py`: Neo4j connection pool singleton

## Provenance

Top-level `wheeler/provenance.py` handles stability scoring and
invalidation propagation. `propagate_invalidation()` uses transitive
traversal through WAS_GENERATED_BY|USED chains with exponential decay.

## Neo4j Session Constraint

Neo4j sessions don't support concurrent queries. Never use `asyncio.gather`
inside a session. Run queries sequentially.
