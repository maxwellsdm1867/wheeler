"""Guard tests for the single Cypher write-detection rule.

`mcp_core.run_cypher` is the read-only boundary an agent in a read-only mode
runs against. Its previous local guard scanned for keywords with literal
trailing spaces and was simultaneously too weak and too strong: it permitted
`CREATE(n:Finding {id:'x'})`, `CREATE\\n(...)`, `CALL apoc.*` and `LOAD CSV`,
while refusing `MATCH (d:Dataset {name: $n}) RETURN d` because uppercased
"DATASET " contains the literal "SET ".

The correct implementation already existed 200 lines away in the backend, with
a comment explaining exactly this failure. These tests exist so a third copy
cannot appear and so the specific bypasses stay closed.
"""

from __future__ import annotations

import pytest

from wheeler.graph.cypher_guard import is_read_only_cypher

# Every one of these PASSED the old substring guard.
BYPASSES_MUST_BLOCK = [
    pytest.param("CREATE(n:Finding {id:'x'}) RETURN n", id="create-no-space"),
    pytest.param("CREATE\n(n:Finding {id:'x'}) RETURN n", id="create-newline"),
    pytest.param("MATCH (n) CALL apoc.refactor.rename.label('A','B')", id="call-apoc"),
    pytest.param("LOAD CSV FROM 'file:///x.csv' AS row CREATE(n:X)", id="load-csv"),
    pytest.param("MERGE(n:X {id:'y'}) RETURN n", id="merge-no-space"),
    pytest.param("MATCH (n) FOREACH (x IN [1] | SET n.a = 1)", id="foreach"),
    # These the old guard did catch; they must stay caught.
    pytest.param("MATCH (n) DETACH DELETE n", id="detach-delete"),
    pytest.param("MATCH (n) SET n.x = 1", id="set"),
    pytest.param("DROP INDEX foo", id="drop"),
    pytest.param("MATCH (n) REMOVE n.x", id="remove"),
]

# Every one of these was REFUSED by the old substring guard. The first two are
# ordinary Wheeler reads, which is what made the false positive a live bug
# rather than a curiosity.
READS_MUST_PASS = [
    pytest.param("MATCH (d:Dataset {name: $n}) RETURN d", id="dataset-inline-props"),
    pytest.param("MATCH (n:Analysis) RETURN n.dataset AS d", id="dataset-property"),
    pytest.param(
        "MATCH (f:Finding)-[:SUPPORTS]->(h:Hypothesis) RETURN f.id, h.id",
        id="provenance-traversal",
    ),
    pytest.param("MATCH (n) RETURN count(n) AS total", id="count"),
    pytest.param("MATCH (p:Paper) WHERE p.year > 2020 RETURN p.title", id="filter"),
]


@pytest.mark.parametrize("query", BYPASSES_MUST_BLOCK)
def test_write_forms_are_refused(query):
    assert not is_read_only_cypher(query), f"write slipped through: {query!r}"


@pytest.mark.parametrize("query", READS_MUST_PASS)
def test_legitimate_reads_are_allowed(query):
    assert is_read_only_cypher(query), f"legitimate read refused: {query!r}"


class TestSingleDefinition:
    """One guard, two consumers. The audit traced repeated defects to helpers
    existing in several copies with several signatures; this is the assertion
    that keeps this one singular."""

    def test_backend_reuses_the_shared_rule(self):
        from wheeler.graph import cypher_guard, neo4j_backend

        assert neo4j_backend._is_read_only_cypher is cypher_guard.is_read_only_cypher
        assert neo4j_backend._CYPHER_WRITE_RE is cypher_guard.CYPHER_WRITE_RE

    def test_mcp_core_holds_no_private_keyword_list(self):
        """The specific shape of the old bug: a local tuple of keywords."""
        import inspect
        import re

        from wheeler import mcp_core

        src = inspect.getsource(mcp_core)
        # A tuple/list literal of quoted SQL-ish keywords near a `for` loop is
        # what the old guard looked like.
        assert not re.search(r"[\"']CREATE\s*[\"']", src), (
            "mcp_core carries its own CREATE keyword literal again; "
            "use graph.cypher_guard.is_read_only_cypher"
        )

    def test_no_third_copy_anywhere(self):
        import pathlib
        import re

        pattern = re.compile(r"CREATE\|MERGE\|DELETE|[\"']CREATE\s[\"']")
        offenders = []
        for path in pathlib.Path("wheeler").rglob("*.py"):
            if path.name == "cypher_guard.py":
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if pattern.search(line):
                    offenders.append(f"{path}:{lineno}")
        assert offenders == [], (
            f"a second write-keyword list appeared: {offenders}"
        )


class TestMcpToolRefusal:
    """The boundary itself, through the tool rather than the helper."""

    async def test_tool_refuses_a_write_that_bypassed_the_old_guard(self):
        from wheeler.mcp_core import run_cypher

        result = await run_cypher("CREATE(n:Finding {id:'pwned'}) RETURN n")
        assert "error" in result
        assert "not allowed" in result["error"]

    async def test_tool_does_not_refuse_an_ordinary_dataset_read(self, monkeypatch):
        """The false-positive half: this used to be blocked outright."""
        import wheeler.mcp_core as core

        class StubBackend:
            async def run_cypher(self, query, params=None):
                return [{"d": "ok"}]

        async def fake_get_backend(config):
            return StubBackend()

        monkeypatch.setattr(core.graph_tools, "_get_backend", fake_get_backend)

        result = await core.run_cypher("MATCH (d:Dataset {name: $n}) RETURN d")
        assert "error" not in result, result
        assert result["count"] == 1
