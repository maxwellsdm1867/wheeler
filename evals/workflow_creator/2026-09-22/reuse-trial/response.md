Use the existing `wh:ask` skill when you start reading a paper. Its instructions already cover graph lookups and provenance tracing, return concise answers with node citations, and prohibit graph changes.

Invoke it with:

> Use wh:ask: What does our graph already know about [paper title or DOI], and what is its provenance? Answer only in chat; create no files and make no graph writes.

Your workflow needs no new skill or durable output. This runs when invoked; it does not automatically detect when you open a paper. I inspected the local instructions, but have not executed a graph lookup or verified retrieval against a graph.
