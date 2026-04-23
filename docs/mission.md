# Mission

## One-liner

Reliable, trustworthy, trackable AI workflows for science.

## The guarantee

Wheeler's product is the provenance guarantee, not the knowledge graph. The
graph is infrastructure. The product is: every AI-produced research artifact
is automatically linked to the exact script, data, and parameters that
produced it, and changes propagate through dependency relationships.

## Four pillars

1. **Traceable results.** One tool call builds the full W3C PROV-DM provenance
   chain. The agent focuses on science; infrastructure handles bookkeeping.

2. **Change propagation.** When a script changes or data is updated, Wheeler
   flags every downstream finding as stale and reduces its stability score.

3. **Context management.** All components read from and write to the same graph.
   A finding from data analysis immediately informs subsequent literature
   searches, experimental design, and manuscript preparation.

4. **Executable research artifact.** The knowledge graph is an executable map
   of discovery: any scientist can inherit the full experimental context of a
   project, explore how results connect, and build on prior work.

## Target audience

Solo researchers who use Claude Code for their own research. The current
design reflects this: local-only, Max subscription, single-user Neo4j,
all data on the scientist's machine. Multi-user and institutional use
are not design goals for v1.0.

## What Wheeler is not

- Not an agent framework. Claude Code is the orchestrator. Wheeler provides
  MCP tools and slash commands, not orchestration code.
- Not a document store. The graph is an index over files.
- Not a cloud service. 100% local, no API keys, no data leaves the machine.
- Not a general-purpose knowledge base. Designed for active scientific
  investigation with provenance tracking, not static knowledge management.

## Design north star

Wheeler never does the scientist's thinking. Every task is tagged: SCIENTIST
(judgment calls), WHEELER (grinding), or PAIR (collaborative). Decision points
are checkpoints, not guesses.
