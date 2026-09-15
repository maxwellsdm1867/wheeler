The project directory is `{PROJECT_DIR}` and it is the current working directory.

This project shares one Neo4j database with other projects, so EVERY Cypher
`MATCH` must be scoped: add `WHERE n._wheeler_project = $ptag` (using the
pattern variable of that match). `$ptag` is already bound for you by
`run_cypher`; do not try to set it. An unscoped query reads other projects'
nodes and the answer will be wrong.

The session window start is:

    $since = {SINCE}

Substitute that literal string wherever a query below says `$since`.

Run these seven steps and collect the results. Use the Wheeler MCP tools only;
do not guess, do not stop early, and do not ask any questions.

**Step 1 (window and malformed closes).** Two `run_cypher` calls:

```cypher
MATCH (x:Execution {kind: "close"})
WHERE x._wheeler_project = $ptag
  AND x.started_at IS NOT NULL AND x.started_at <> ""
RETURN x.started_at AS last_close
ORDER BY x.started_at DESC LIMIT 1
```

```cypher
MATCH (x:Execution {kind: "close"})
WHERE x._wheeler_project = $ptag
  AND (x.started_at IS NULL OR x.started_at = "")
RETURN x.id AS id, x.description AS description
```

Record the number of rows the second query returns as `malformed_closes`.

**Step 2 (recent entities).** One `run_cypher` call:

```cypher
MATCH (n)
WHERE n._wheeler_project = $ptag
  AND coalesce(n.updated, n.date) IS NOT NULL
  AND datetime(coalesce(n.updated, n.date)) >= datetime($since)
  AND NOT n:Execution AND NOT n:Paper
RETURN n.id AS id, labels(n)[0] AS type
ORDER BY id
```

Record every `id` as `window_ids`.

**Step 3 (orphans).** One `run_cypher` call:

```cypher
MATCH (n)
WHERE n._wheeler_project = $ptag
  AND (coalesce(n.updated, n.date) IS NULL
       OR datetime(coalesce(n.updated, n.date)) >= datetime($since))
  AND NOT n:Execution AND NOT n:Paper
  AND NOT (n)-[:WAS_GENERATED_BY]->(:Execution)
RETURN n.id AS id, labels(n)[0] AS type
ORDER BY id
```

Record every `id` as `orphan_ids`.

**Step 4 (staleness).** Call `detect_stale`. Record the `node_id` of every row
whose `reason` is `changed`, as `stale`.

**Step 5 (inventory).** Six `run_cypher` calls, one per type, each scoped and
run exactly as written. Record the ROW COUNT of each as `inventory`.

```cypher
MATCH (f:Finding) WHERE f._wheeler_project = $ptag AND datetime(f.date) >= datetime($since) RETURN f.id
MATCH (h:Hypothesis) WHERE h._wheeler_project = $ptag AND datetime(coalesce(h.updated, h.date)) >= datetime($since) RETURN h.id
MATCH (q:OpenQuestion) WHERE q._wheeler_project = $ptag AND datetime(coalesce(q.date, q.date_added)) >= datetime($since) RETURN q.id
MATCH (pl:Plan) WHERE pl._wheeler_project = $ptag AND datetime(pl.updated) >= datetime($since) RETURN pl.id
MATCH (x:Execution) WHERE x._wheeler_project = $ptag AND datetime(x.started_at) >= datetime($since) RETURN x.id
MATCH (w:Document) WHERE w._wheeler_project = $ptag AND datetime(w.date) >= datetime($since) RETURN w.id
```

Report the counts under the keys `Finding`, `Hypothesis`, `OpenQuestion`,
`Plan`, `Execution`, `Document`. Report what the queries actually return; do
not adjust a count because a row looks like it should not be there.

**Step 6 (citations).** Read `docs/DRAFT-SESSION.md` and pass its full text to
`validate_citations`. Record `total` and `valid` from the result.

**Step 7 (consistency).** Call `graph_consistency_check` with `repair=false`.
Set `consistency_ok` to `true` when `json_only`, `synthesis_missing` and
`synthesis_orphaned` are ALL empty, otherwise `false`. Ignore `graph_only`
entirely: this database is shared, so `graph_only` lists thousands of other
projects' nodes and says nothing about this project.
