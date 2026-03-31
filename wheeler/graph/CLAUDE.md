# graph/ — Knowledge graph backends and schema

The graph is an **index layer** — metadata, relationships, embeddings,
and file pointers. Content lives in `knowledge/*.json` files.

## Backends

Two interchangeable backends via `GraphBackend` ABC in `backend.py`:
- **Kuzu** (`kuzu_backend.py`) — embedded, zero-config, no Docker
- **Neo4j** (`neo4j_backend.py`) — Docker, browser UI at :7474

Selected by `config.graph.backend` ("kuzu" or "neo4j").
Factory: `get_backend(config)`.

## What the Graph Stores Per Node

`id`, `type`, `tier`, `title` (~100 chars), `file_path`, `created`,
plus type-specific filterable fields (confidence, priority, status, doi).

## Node Types and Prefixes

Defined in `wheeler/models.py` (canonical), re-exported by `schema.py`:

F=Finding, H=Hypothesis, Q=OpenQuestion, D=Dataset, P=Paper,
W=Document, S=Script, X=Execution, PL=Plan, N=ResearchNote, L=Ledger

## Relationships (14 types)

PROV (W3C standard):
  USED, WAS_GENERATED_BY, WAS_DERIVED_FROM, WAS_INFORMED_BY,
  WAS_ATTRIBUTED_TO, WAS_ASSOCIATED_WITH

Semantic (Wheeler-specific):
  SUPPORTS, CONTRADICTS, CITES, APPEARS_IN, RELEVANT_TO,
  AROSE_FROM, DEPENDS_ON, CONTAINS

## Key Modules

- `backend.py` — `GraphBackend` ABC (create/get/update/delete node, relationships, queries)
- `schema.py` — Constraints, indexes, `generate_node_id()`. Imports prefixes from `models.py`
- `context.py` — `fetch_context()` returns size-limited markdown for prompt injection
- `provenance.py` — `hash_file()`, `detect_stale()`, staleness detection
- `driver.py` — Neo4j connection pool singleton

## Neo4j Session Constraint

Neo4j sessions don't support concurrent queries. Never use `asyncio.gather`
inside a session — run queries sequentially.
