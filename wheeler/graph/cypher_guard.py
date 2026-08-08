"""The single definition of "does this Cypher write?".

Two consumers, one rule:

* ``Neo4jBackend.run_cypher`` uses it to decide whether a failed query is safe
  to REPLAY (``merge.py`` and ``restore.py`` send real writes through it).
* ``mcp_core.run_cypher`` uses it to decide whether to REFUSE the query at all.
  That is the read-only boundary an agent in a read-only mode runs against, so
  it is a correctness property, not a convenience.

The two roles have different costs for a misclassification, and both fall the
safe way. In the backend, a read misread as a write is merely not retried. In
the MCP tool it is refused, which is user-visible: hence whole-word matching
below, and hence this module rather than a second copy.

The MCP tool previously carried its own substring scan over keywords with
literal trailing spaces. It permitted ``CREATE(n:Finding {id:'x'})``,
``CREATE\\n(...)``, ``CALL apoc.*`` and ``LOAD CSV`` (the last two absent from
its list entirely), while refusing legitimate reads such as
``MATCH (d:Dataset {name: $n}) RETURN d``, because uppercased ``DATASET ``
contains the literal ``SET ``. It was simultaneously too weak and too strong,
200 lines from a correct implementation. Do not write a third one.

Zero internal dependencies: stdlib ``re`` only, so both layers can import it.
"""

from __future__ import annotations

import re

# Cypher clause keywords that can write.
#
# Every misclassification falls the safe way. A read whose text happens to
# contain one of these words, in a string literal or a property name, is merely
# not retried (backend) or refused (MCP tool). A write cannot hide from the
# list: every Cypher writing clause is here, and the indirect routes
# (``FOREACH``, ``CALL``, ``LOAD CSV``) can only write by being on the list
# themselves or by containing a clause that is.
#
# Whole-word matching is load-bearing: a substring test would see "SET" inside
# ``Dataset`` and refuse almost every read in the codebase.
#
# ``CALL`` is on the list even though read-only procedures exist (the fulltext
# index is queried with one). There is no reliable way to tell a reading
# procedure from a writing one by name, and apoc ships write procedures, so the
# conservative side is the correct side for a guard that gates writes. Internal
# callers are unaffected: they use the backend method, which has no refusal
# path. Verified at the time of extraction: no act in the shipped corpus uses
# CALL, FOREACH or LOAD through the MCP tool.
CYPHER_WRITE_RE = re.compile(
    r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|CALL|FOREACH|LOAD)\b",
    re.IGNORECASE,
)

# Human-readable for error messages, so a refused agent learns why rather than
# guessing. Kept next to the pattern so the two cannot drift.
WRITE_KEYWORDS = ("CREATE", "MERGE", "DELETE", "SET", "REMOVE", "DROP", "CALL", "FOREACH", "LOAD")


def is_read_only_cypher(query: str) -> bool:
    """Whether *query* provably only reads."""
    return CYPHER_WRITE_RE.search(query) is None
