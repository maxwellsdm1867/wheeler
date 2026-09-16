"""The act's window queries must survive a node with an empty timestamp.

One node with `started_at = ""` aborts an entire Cypher query with
`Cannot parse '' as a DateTime`, and `<> ''` in the same WHERE does not save it
because the planner does not evaluate conditions in order. That is not a
hypothetical: phase 1.1 of /wh:close exists to WARN about malformed close
Executions, and the unguarded phase 2.1 then crashed on the very node it had
just warned about. The local instance already carries one.

These tests extract the Cypher straight from the shipped act files and run it,
so the guard is verified where it actually lives rather than in a paraphrase.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

_TEST_PASSWORD = "research-graph"
ACTS = Path(__file__).resolve().parents[1] / ".claude" / "commands" / "wh"


def _local_uri() -> str | None:
    import os

    if uri := os.environ.get("WHEELER_TEST_NEO4J_URI"):
        return uri
    from neo4j import GraphDatabase

    for port in (7717, 7687, 7697, 7707):
        uri = f"bolt://localhost:{port}"
        try:
            d = GraphDatabase.driver(uri, auth=("neo4j", _TEST_PASSWORD))
            with d.session(database="neo4j") as s:
                s.run("RETURN 1").consume()
            d.close()
            return uri
        except Exception:
            continue
    return None


_URI = _local_uri()
needs_neo4j = pytest.mark.skipif(_URI is None, reason="no local Neo4j answering the test password")


def _cypher_blocks(act: str) -> list[str]:
    return re.findall(r"```cypher\n(.*?)```", (ACTS / act).read_text(), re.S)


def _timestamp_queries() -> list[tuple[str, str]]:
    """Every act query that parses a node property as a datetime."""
    out = []
    for act in ("close.md", "dream.md", "graph-link.md"):
        for i, block in enumerate(_cypher_blocks(act)):
            if re.search(r"\b(?:datetime|date)\(\s*(?:coalesce\()?[a-z]+\.", block):
                out.append((f"{act}#{i}", block.strip()))
    return out


def test_the_acts_still_contain_timestamp_queries_to_guard():
    """If this drops to zero the suite below is vacuous."""
    found = _timestamp_queries()
    assert len(found) >= 8, [n for n, _ in found]


def test_no_act_parses_a_timestamp_without_a_case_guard():
    """Static check: every datetime() over a node property sits inside a CASE."""
    offenders = []
    for name, q in _timestamp_queries():
        # strip the guarded form, then look for anything left
        stripped = re.sub(
            r"CASE WHEN [^\n]*IS NULL OR [^\n]*= ''[^\n]*\n\s*ELSE (?:datetime|duration|date)[^\n]*END",
            "", q, flags=re.S,
        )
        if re.search(r"\b(?:datetime|date)\(\s*(?:coalesce\()?[a-z]+\.", stripped):
            offenders.append(name)
    assert offenders == [], f"unguarded datetime() over a node property in: {offenders}"


@pytest.fixture
def poisoned_graph():
    """A tag holding one good node and one node per empty-timestamp field."""
    from neo4j import GraphDatabase

    tag = f"dtguard-{uuid.uuid4().hex[:8]}"
    d = GraphDatabase.driver(_URI, auth=("neo4j", _TEST_PASSWORD))
    with d.session(database="neo4j") as s:
        s.run(
            "CREATE (:Finding {id:'F-ok', date:'2026-09-14T10:00:00+00:00', title:'ok', _wheeler_project:$t}) "
            "CREATE (:Finding {id:'F-empty', date:'', title:'empty', _wheeler_project:$t}) "
            "CREATE (:Hypothesis {id:'H-empty', updated:'', date:'', _wheeler_project:$t}) "
            "CREATE (:OpenQuestion {id:'Q-empty', date:'', date_added:'', _wheeler_project:$t}) "
            "CREATE (:Plan {id:'PL-empty', updated:'', _wheeler_project:$t}) "
            "CREATE (:Execution {id:'X-empty', kind:'close', started_at:'', _wheeler_project:$t}) "
            "CREATE (:Document {id:'W-empty', date:'', section:'session-synthesis', _wheeler_project:$t})",
            t=tag,
        ).consume()
    yield tag, d
    with d.session(database="neo4j") as s:
        s.run("MATCH (n {_wheeler_project:$t}) DETACH DELETE n", t=tag).consume()
    d.close()


@needs_neo4j
@pytest.mark.parametrize("name,query", _timestamp_queries(), ids=lambda v: v if isinstance(v, str) else "")
def test_each_act_query_survives_empty_timestamps(name, query, poisoned_graph):
    _tag, driver = poisoned_graph
    # Run the act's Cypher VERBATIM. Rewriting it to scope by tag is how a test
    # ends up proving something about the rewrite instead of about the act, and
    # these are read-only MATCH queries, so touching the whole database is safe.
    # The fixture's poisoned nodes are in it, which is the point.
    params = {
        "since": "2026-09-13T00:00:00+00:00",
        "last_dream_at": "2026-09-13T00:00:00+00:00",
        "hours": 48,
    }
    with driver.session(database="neo4j") as s:
        try:
            s.run(query, **params).data()
        except Exception as exc:  # noqa: BLE001
            if "Cannot parse" in str(exc) or "DateTime" in str(exc):
                pytest.fail(f"{name} still dies on an empty timestamp: {str(exc).splitlines()[0][:120]}")
            raise


def test_every_guard_excludes_the_bad_row_rather_than_including_it():
    """Guard POLARITY, which "does not crash" cannot detect.

    `CASE WHEN <missing> THEN true ELSE ... END` passes both the static shape
    check and the live query, because it never raises: it just silently treats
    every unstamped node as in-window. The window queries must exclude them.
    The one deliberate exception is the phase 1.3 orphan sweep, which surfaces
    unstamped nodes as suspects on purpose and says so in its prose.
    """
    offenders = []
    for name, q in _timestamp_queries():
        for guard in re.finditer(r"CASE WHEN .*?THEN (true|false)", q, re.S):
            if guard.group(1) == "true":
                offenders.append((name, guard.group(0)[:70]))
    assert offenders == [], f"guard admits unstamped rows instead of excluding them: {offenders}"
