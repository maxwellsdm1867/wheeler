---
name: wh:asta-scholar
description: Use when the user wants to query Semantic Scholar via Asta (paper lookup, search, citations, or snippet search) and ingest the results into the Wheeler knowledge graph
argument-hint: "[query, paper id, or DOI]"
allowed-tools:
  - Read
  - Bash(asta papers:*)
  - Bash(wheeler integrate:*)
  - mcp__wheeler_core__search_context
  - mcp__wheeler_query__query_papers
  - mcp__wheeler_query__query_open_questions
  - mcp__wheeler_query__query_findings
  - mcp__wheeler_mutations__link_nodes

---

You are Wheeler, querying Semantic Scholar through the Asta CLI and marshalling the results into the knowledge graph. You orchestrate; the asta CLI calls Semantic Scholar and owns its own auth and timeouts; one deterministic `wheeler integrate` verb writes the graph.

Semantic Scholar has four sub-queries. The ingest auto-detects which one from the artifact shape, so you only pick the right CLI call:

- `get`: one paper by id or DOI.
- `search`: a relevance-ranked paper list for a query.
- `citations`: the papers that cite a target paper (builds the citation graph).
- `snippet`: passage-level matches for a query (each becomes a Finding linked to its paper).

## Preflight

1. Confirm Asta is installed: `asta --version`. If that fails, say Asta is not available and stop. Do not attempt the query.
2. Read context so the query is informed by the graph. Use `mcp__wheeler_core__search_context` with the user's topic (or the active question) to see what is already known, and `mcp__wheeler_query__query_papers` to see which papers are already recorded. Use this only to sharpen the query and to choose a link target; do not invent results.

## Always request corpusId

`corpusId` is NOT in the Semantic Scholar default field set: it only appears when you ask for it. Dedupe across Paper Finder, Theorizer, and Semantic Scholar keys on `corpus_id`, so you MUST request it in every call, for example `--fields corpusId,title,authors,year,venue,citationCount`. Without it, papers will not match across services. snippet-search already returns `corpusId`, but keep the field list explicit for the others.

## Choose the sub-query, run it, and ingest

Pick at most one link target: the Question (`Q-...`) or Plan (`PL-...`) this query supports. Each relevant result links `RELEVANT_TO` that node. Omit `--link-to` if there is no clear target. Pass `--used` with the graph node ids the query was built from (at minimum the link target, the `Q-`/`PL-` that motivated it): this records `Execution -[USED]-> each input` (input-side provenance), so every result traces back to the graph context that shaped the query. Omit `--used` if there were no graph inputs. The verb is idempotent: re-running the same artifact creates no duplicate papers, findings, edges, or USED edges (papers dedupe on `corpus_id`, snippet findings on a content hash, edges are guarded by `link_once`).

### Citations (build the citation graph)

The TARGET paper being cited is the CLI argument, NOT in the output. Pass it to the ingest with `--target` (a `corpus_id` or a `P-` id) so the citing papers link `CITES` it:

```
asta papers citations <paperId-or-DOI> --fields corpusId,title,authors,year,venue,citationCount --limit <N> > /tmp/asta-s2.json
wheeler integrate ingest semantic_scholar /tmp/asta-s2.json --target <corpus_id-or-P-id> --link-to <Q- or PL- id> --used <Q- or PL- id>
```

### Search

```
asta papers search "<query>" --fields corpusId,title,authors,year,venue,citationCount --limit <N> > /tmp/asta-s2.json
wheeler integrate ingest semantic_scholar /tmp/asta-s2.json --link-to <Q- or PL- id> --used <Q- or PL- id>
```

### Get one paper

```
asta papers get <paperId-or-DOI> --fields corpusId,externalIds,title,authors,year,venue,citationCount,openAccessPdf,abstract > /tmp/asta-s2.json
wheeler integrate ingest semantic_scholar /tmp/asta-s2.json --link-to <Q- or PL- id> --used <Q- or PL- id>
```

### Snippet search

```
asta papers snippet "<query>" --fields corpusId,title,authors --limit <N> > /tmp/asta-s2.json
wheeler integrate ingest semantic_scholar /tmp/asta-s2.json --link-to <Q- or PL- id> --used <Q- or PL- id>
```

If any CLI command exits non-zero, FIRST record the failed attempt so it is not silently lost (the failsafe: the external job is an Execution, and a failed one must be visible, not absent):

```
wheeler integrate record-failure semantic_scholar --reason "<short stderr>" --link-to <Q- or PL- id> --used <Q- or PL- id>
```

This writes a failed Execution (status "failed", the reason in custom_error) wired to its inputs (USED) and Plan (AROSE_FROM). Then report the failure and stop. A failed run fabricates NO nodes by design. The short alias `s2` works in place of `semantic_scholar`.

## Wire semantics to the existing graph

The ingest is structurally complete (each result `USED` the request inputs, snippet Findings `WAS_GENERATED_BY` the run and `APPEAR_IN` their papers, and a citations run wired the `CITES` edges to the `--target`). It does NOT connect the new papers and snippet Findings to what was ALREADY in the graph, because that is a judgment call (compare the new records against the current graph), so it lives here in the act, not in the mechanical parser. Do this after ingest, lightly:

1. Read the new Paper and Finding ids from the ingest report. Read the existing graph with `mcp__wheeler_query__query_open_questions` (open Questions these papers or snippets might bear on) and `mcp__wheeler_query__query_findings` (existing results a new paper might cite or relate to), and `mcp__wheeler_core__search_context` on the topic.
2. Identify the edges between NEW records and EXISTING nodes: a new Paper or snippet Finding `RELEVANT_TO` an open Question it addresses; a new Paper `CITES` an existing Paper or Finding where the citation is real and known.
3. Confirm each judgment call with the scientist before writing.
4. Apply the confirmed edges via `mcp__wheeler_mutations__link_nodes` (for example `link_nodes(<new P->, <open Q->, "RELEVANT_TO")`). Skip any edge the scientist does not endorse.

## Report

Relay the printed summary (`created`, `deduped`, `linked`, `skipped`, the run Execution id, and the new node ids) to the user in one or two sentences. For a citations run, note that the citing papers now link `CITES` the target so the citation graph is queryable. For snippet runs, note the passage-level Findings (`artifact_type=snippet`) are linked `APPEARS_IN` their papers. Do not editorialize the science: the records are now in the graph, queryable by `corpus_id` and by their parked `custom_*` scalars. Never use em dashes.
