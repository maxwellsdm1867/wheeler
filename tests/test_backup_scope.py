"""Tests that ``wheeler backup`` dumps only the project it was run for.

Wheeler simulates per-project isolation on Neo4j Community Edition with a
``_wheeler_project`` property (``config.neo4j.project_tag``). Two projects
therefore share one physical database, and an unscoped ``MATCH (n)`` in the
backup dump packs every other project's nodes into the archive.

The live test here puts two tagged projects on the local Neo4j, backs up one of
them, and asserts nothing from the other made it into the archive. It runs
against real Neo4j on purpose: a fake backend cannot show a cross-project leak,
because there is no second project inside the fake.

Data safety: every node written here carries a unique per-run
``backup_scope_tag`` and teardown deletes by that tag only. No query in this
module ever deletes without it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import tarfile
import uuid
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.backup import (
    _node_dump_cypher,
    _rel_dump_cypher,
    create_backup,
)
from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig

# Unique per run, so teardown can delete exactly what this module created and
# nothing else. Also used as the project_tag suffix so the two namespaces
# cannot collide with a concurrent run or with real project data.
RUN_TAG = f"backup_scope_{uuid.uuid4().hex}"
PROJECT_A = f"{RUN_TAG}_A"
PROJECT_B = f"{RUN_TAG}_B"

_NEO4J_URI = "bolt://localhost:7687"
_NEO4J_USER = "neo4j"
_NEO4J_PASSWORD = "research-graph"
_NEO4J_DB = "neo4j"


def _neo4j_config(project_tag: str) -> WheelerConfig:
    """Config pointed at the local Neo4j, namespaced to *project_tag*."""
    return WheelerConfig(
        neo4j=Neo4jConfig(
            uri=_NEO4J_URI,
            username=_NEO4J_USER,
            password=_NEO4J_PASSWORD,
            database=_NEO4J_DB,
            project_tag=project_tag,
        ),
        project=ProjectMeta(
            name=project_tag,
            description="backup project-scope test",
        ),
    )


def _run_cypher(statement: str, **params) -> list[dict]:
    """Run one statement on a throwaway driver, outside any event loop."""
    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _go() -> list[dict]:
        driver = AsyncGraphDatabase.driver(
            _NEO4J_URI,
            auth=(_NEO4J_USER, _NEO4J_PASSWORD),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
            connection_acquisition_timeout=5,
        )
        try:
            async with driver.session(database=_NEO4J_DB) as session:
                result = await session.run(statement, parameters=params)
                return [dict(r) async for r in result]
        finally:
            await driver.close()

    return asyncio.run(_go())


def _neo4j_reachable() -> bool:
    """True when the local Neo4j answers, False on any failure."""
    try:
        _run_cypher("RETURN 1")
        return True
    except Exception:
        return False


# Node ids per project. Prefixes match Wheeler's own (F = Finding,
# D = Dataset), but these are written with plain Cypher: this module tests the
# dump query, not the mutation path. The ids carry the run suffix so a run
# whose teardown was interrupted cannot collide with the id uniqueness
# constraints init_schema applies.
_SUFFIX = RUN_TAG[-8:]
A_F1 = f"F-a1{_SUFFIX}"
A_F2 = f"F-a2{_SUFFIX}"
A_D1 = f"D-a1{_SUFFIX}"
B_F1 = f"F-b1{_SUFFIX}"
B_D1 = f"D-b1{_SUFFIX}"

A_NODES = [("Finding", A_F1), ("Finding", A_F2), ("Dataset", A_D1)]
B_NODES = [("Finding", B_F1), ("Dataset", B_D1)]
A_IDS = {node_id for _, node_id in A_NODES}
B_IDS = {node_id for _, node_id in B_NODES}

# Intra-A edges: the only ones a project-A backup may contain.
A_EDGES = [
    (A_F1, "SUPPORTS", A_F2),
    (A_F1, "USED", A_D1),
]
# Cross-project edges. A dump that filters only the source endpoint would emit
# the first of these and leave restore with a target absent from
# graph_nodes.jsonl.
CROSS_EDGES = [
    (A_F2, "CITES", B_F1),
    (B_F1, "CITES", A_F1),
]
B_EDGES = [
    (B_F1, "USED", B_D1),
]


@pytest.fixture(scope="module")
def two_projects() -> Iterator[None]:
    """Write projects A and B into one Neo4j, then delete only what we wrote."""
    if not _neo4j_reachable():
        pytest.skip("Neo4j not available -- skipping backup project-scope test")

    create_node = (
        "CREATE (n:%s {id: $id, title: $title, "
        "_wheeler_project: $ptag, backup_scope_tag: $run})"
    )
    for project_tag, nodes in ((PROJECT_A, A_NODES), (PROJECT_B, B_NODES)):
        for label, node_id in nodes:
            _run_cypher(
                create_node % label,
                id=node_id,
                title=f"scope test {node_id}",
                ptag=project_tag,
                run=RUN_TAG,
            )
    create_edge = (
        "MATCH (a {id: $source, backup_scope_tag: $run}), "
        "(b {id: $target, backup_scope_tag: $run}) "
        "CREATE (a)-[:%s {backup_scope_tag: $run}]->(b)"
    )
    for source, rel_type, target in A_EDGES + CROSS_EDGES + B_EDGES:
        _run_cypher(
            create_edge % rel_type,
            source=source,
            target=target,
            run=RUN_TAG,
        )

    yield

    # Teardown deletes by this run's tag ONLY. Never a bare MATCH (n).
    # Best-effort, matching tests/e2e/conftest.py: a Neo4j hiccup at teardown
    # must not turn a passing run into an ERROR. Leftovers stay identifiable by
    # their backup_scope_tag.
    try:
        _run_cypher(
            "MATCH (n) WHERE n.backup_scope_tag = $run DETACH DELETE n",
            run=RUN_TAG,
        )
    except Exception:
        logging.getLogger(__name__).warning(
            "backup-scope test cleanup failed; nodes tagged %s may remain",
            RUN_TAG,
            exc_info=True,
        )


@pytest.fixture(autouse=True)
def reset_driver_singleton() -> Iterator[None]:
    """Drop the cached async driver around every test in this module.

    Each async test gets its own event loop, so a driver singleton left over
    from another module would be bound to a dead one.
    """
    import wheeler.graph.driver as drv

    drv._async_driver = None
    drv._async_driver_uri = None
    yield
    drv._async_driver = None
    drv._async_driver_uri = None


def _setup_project_dir(root: Path) -> None:
    """Minimal graph-only project layout under *root*."""
    (root / "knowledge").mkdir()
    (root / "synthesis").mkdir()
    (root / ".wheeler").mkdir()
    (root / "wheeler.yaml").write_text("knowledge_path: knowledge\n")


async def _backup_project(project_tag: str, tmp_path: Path) -> dict:
    """Back up *project_tag* into tmp_path, return the parsed archive.

    Returns ``{"manifest": dict, "nodes": list[dict], "rels": list[dict]}``.
    """
    root = tmp_path / f"proj-{project_tag}"
    root.mkdir()
    _setup_project_dir(root)

    cfg = _neo4j_config(project_tag)
    cfg.project_root = str(root)
    cfg.knowledge_path = str(root / "knowledge")
    cfg.synthesis_path = str(root / "synthesis")

    # The Execution record is a write, and it would land outside this run's
    # cleanup tag. Stub it: this test is about the dump, not the audit trail.
    with patch(
        "wheeler.backup._record_backup_execution", new_callable=AsyncMock
    ):
        archive = await create_backup(
            cfg,
            destination=root / "out",
            scope="graph-only",
        )

    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())
        node_lines = tar.extractfile("graph_nodes.jsonl").read().decode()
        rel_lines = tar.extractfile("graph_relationships.jsonl").read().decode()

    return {
        "manifest": manifest,
        "nodes": [json.loads(ln) for ln in node_lines.splitlines() if ln.strip()],
        "rels": [json.loads(ln) for ln in rel_lines.splitlines() if ln.strip()],
    }


async def test_backup_dumps_only_its_own_project_nodes(two_projects, tmp_path):
    """graph_nodes.jsonl holds project A's nodes and no other project's."""
    dump = await _backup_project(PROJECT_A, tmp_path)

    assert dump["manifest"]["graph_available"] is True

    dumped_ids = {entry["props"].get("id") for entry in dump["nodes"]}
    leaked = dumped_ids & B_IDS
    assert not leaked, f"backup of {PROJECT_A} leaked project-B nodes: {sorted(leaked)}"
    assert dumped_ids == A_IDS, (
        "backup of a tagged project must dump exactly that project's nodes, got "
        f"{len(dumped_ids)} ids"
    )

    tags = {entry["props"].get("_wheeler_project") for entry in dump["nodes"]}
    assert tags == {PROJECT_A}, f"foreign project tags in the dump: {sorted(tags)}"


async def test_backup_manifest_counts_only_its_own_project(two_projects, tmp_path):
    """Manifest counts describe project A alone, so verification compares clean."""
    dump = await _backup_project(PROJECT_A, tmp_path)
    manifest = dump["manifest"]

    assert manifest["total_nodes"] == len(A_NODES), (
        f"total_nodes {manifest['total_nodes']} != {len(A_NODES)} project-A nodes "
        "(other projects were counted)"
    )
    assert manifest["total_relationships"] == len(A_EDGES), (
        f"total_relationships {manifest['total_relationships']} != {len(A_EDGES)} "
        "intra-project-A edges"
    )
    assert manifest["node_counts_by_label"] == {"Dataset": 1, "Finding": 2}


async def test_backup_relationships_have_both_endpoints_in_project(
    two_projects, tmp_path
):
    """Every dumped edge names two nodes that are also in graph_nodes.jsonl."""
    dump = await _backup_project(PROJECT_A, tmp_path)

    dumped_ids = {entry["props"].get("id") for entry in dump["nodes"]}
    for rel in dump["rels"]:
        source, target = rel["source_id"], rel["target_id"]
        assert source in dumped_ids, f"edge source {source} missing from node dump"
        assert target in dumped_ids, (
            f"edge target {target} missing from node dump: restore would fail on "
            "the dangling target"
        )

    dumped_edges = {
        (rel["source_id"], rel["rel_type"], rel["target_id"]) for rel in dump["rels"]
    }
    assert dumped_edges == set(A_EDGES)
    for cross in CROSS_EDGES:
        assert cross not in dumped_edges, f"cross-project edge {cross} was dumped"


async def test_backup_of_the_other_project_is_symmetric(two_projects, tmp_path):
    """Backing up B gets B's nodes only: the scoping is not A-specific."""
    dump = await _backup_project(PROJECT_B, tmp_path)

    dumped_ids = {entry["props"].get("id") for entry in dump["nodes"]}
    assert dumped_ids == B_IDS
    assert not (dumped_ids & A_IDS)
    assert dump["manifest"]["total_relationships"] == len(B_EDGES)


# --- query construction: untagged behaviour must not change -----------------


def test_dump_cypher_unscoped_when_no_project_tag():
    """Empty tag means the database is the boundary: no filter, no parameter."""
    node_q = _node_dump_cypher("")
    rel_q = _rel_dump_cypher("")

    assert node_q == "MATCH (n) RETURN labels(n) AS labels, properties(n) AS props"
    assert "_wheeler_project" not in node_q
    assert "$ptag" not in node_q
    assert rel_q == (
        "MATCH (a)-[r]->(b) RETURN a.id AS source_id, type(r) AS rel_type, "
        "properties(r) AS rel_props, b.id AS target_id"
    )
    assert "_wheeler_project" not in rel_q
    assert "$ptag" not in rel_q


def test_dump_cypher_scoped_requires_both_relationship_endpoints():
    """A tagged relationship dump filters BOTH endpoints, not just the source."""
    rel_q = _rel_dump_cypher("proj-a")

    assert "a._wheeler_project = $ptag" in rel_q
    assert "b._wheeler_project = $ptag" in rel_q
    assert "n._wheeler_project = $ptag" in _node_dump_cypher("proj-a")


async def test_dump_graph_passes_the_tag_as_a_parameter():
    """_dump_graph binds $ptag when tagged and sends no params when untagged."""
    from wheeler.backup import _dump_graph

    class RecordingBackend:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict | None]] = []

        async def initialize(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def run_cypher(self, query: str, params: dict | None = None):
            self.calls.append((query, params))
            return []

    tagged = RecordingBackend()
    with patch("wheeler.backup.get_backend", return_value=tagged):
        await _dump_graph(_neo4j_config("proj-a"))
    assert [params for _, params in tagged.calls] == [{"ptag": "proj-a"}] * 2

    untagged = RecordingBackend()
    with patch("wheeler.backup.get_backend", return_value=untagged):
        await _dump_graph(_neo4j_config(""))
    assert [params for _, params in untagged.calls] == [None, None]
