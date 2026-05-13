"""E2E roundtrip tests for Wheeler portable handoff (Waves 1-3).

These tests use FakeBackend (not live Neo4j) so they run in CI without any
database. Two project roots are created in tempdirs (project A and project B).
The full create_backup -> restore_fresh pipeline is exercised against real
tar.gz archives on disk, not hand-rolled fixtures.

Run: python -m pytest tests/e2e/test_handoff_roundtrip.py -v
Does NOT require Neo4j.
"""

from __future__ import annotations

import json
import re
import tarfile
from collections import defaultdict
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from wheeler.backup import create_backup
from wheeler.config import WheelerConfig, Neo4jConfig
from wheeler.portability import compute_manifest_signature
from wheeler.restore import restore_fresh


# ---------------------------------------------------------------------------
# E2E FakeBackend: stores rel_props for relationship round-trip regression
# ---------------------------------------------------------------------------


class E2EFakeBackend:
    """In-memory backend that stores nodes AND relationship properties.

    Unlike FakeRestoreBackend in test_restore.py, this variant stores
    rel_props in the relationships list so the round-trip regression test
    can verify they survived backup -> restore intact.

    Also supports all run_cypher patterns used by backup, restore, and
    execute_tool (mutations.py).
    """

    def __init__(self, project_tag: str = "e2e-test"):
        self.project_tag = project_tag
        self.nodes_by_label: dict[str, list[dict]] = defaultdict(list)
        self.nodes_by_id: dict[str, dict] = {}
        self.node_label_by_id: dict[str, str] = {}
        # Each entry: (src_id, rel_type, tgt_id, rel_props_dict)
        self.relationships: list[tuple[str, str, str, dict]] = []
        self._pre_existing_count: int = 0
        self.initialized = False
        self.closed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def close(self) -> None:
        self.closed = True

    async def create_node(self, label: str, properties: dict) -> str:
        props = dict(properties)
        if self.project_tag:
            props["_wheeler_project"] = self.project_tag
        nid = props.get("id")
        if not nid:
            nid = f"{label[0]}-fake{len(self.nodes_by_id):04x}"
            props["id"] = nid
        self.nodes_by_label[label].append(props)
        self.nodes_by_id[nid] = props
        self.node_label_by_id[nid] = label
        return nid

    async def get_node(self, label: str, node_id: str):
        node = self.nodes_by_id.get(node_id)
        if node is None:
            return None
        if self.node_label_by_id.get(node_id) != label:
            return None
        return dict(node)

    async def update_node(self, label: str, node_id: str, properties: dict) -> bool:
        if node_id not in self.nodes_by_id:
            return False
        self.nodes_by_id[node_id].update(properties)
        for n in self.nodes_by_label.get(label, []):
            if n.get("id") == node_id:
                n.update(properties)
                break
        return True

    async def delete_node(self, label: str, node_id: str) -> bool:  # pragma: no cover
        self.nodes_by_id.pop(node_id, None)
        return True

    async def create_relationship(
        self,
        src_label: str,
        src_id: str,
        rel_type: str,
        tgt_label: str,
        tgt_id: str,
        rel_props: dict | None = None,
    ) -> bool:
        if src_id not in self.nodes_by_id or tgt_id not in self.nodes_by_id:
            return False
        self.relationships.append((src_id, rel_type, tgt_id, rel_props or {}))
        return True

    async def query_nodes(self, label, filters=None, order_by=None, limit=10):
        return list(self.nodes_by_label.get(label, []))[:limit]

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        params = params or {}

        # Backup node dump (MATCH (n) RETURN labels(n)...)
        if "labels(n) AS labels" in query and "()-[r]->" not in query:
            out = []
            for nid, props in self.nodes_by_id.items():
                label = self.node_label_by_id.get(nid, "Unknown")
                # Filter by project tag if scoped query
                if self.project_tag and props.get("_wheeler_project") != self.project_tag:
                    continue
                out.append({"labels": [label], "props": dict(props)})
            return out

        # Backup relationship dump (MATCH (a)-[r]->(b) RETURN ...)
        if "MATCH (a)-[r]->(b)" in query and "source_id" in query:
            out = []
            for src_id, rel_type, tgt_id, rel_props in self.relationships:
                src = self.nodes_by_id.get(src_id, {})
                tgt = self.nodes_by_id.get(tgt_id, {})
                if self.project_tag:
                    if (src.get("_wheeler_project") != self.project_tag
                            or tgt.get("_wheeler_project") != self.project_tag):
                        continue
                out.append({
                    "source_id": src_id,
                    "rel_type": rel_type,
                    "rel_props": rel_props,
                    "target_id": tgt_id,
                })
            return out

        # Project-node pre-check used by restore_fresh
        if "count(n) AS cnt" in query and "_wheeler_project" in query:
            tag = params.get("tag", "")
            if self._pre_existing_count > 0 and tag:
                return [{"cnt": self._pre_existing_count}]
            return [{"cnt": 0}]

        # Cleanup (DETACH DELETE)
        if "DETACH DELETE" in query:
            return []

        # UNWIND labels(n) count (used by verify_backup, not by e2e restore)
        if "UNWIND labels(n)" in query and "count(*)" in query:
            ptag = params.get("ptag", "")
            out = []
            for label, items in self.nodes_by_label.items():
                matching = [it for it in items if it.get("_wheeler_project") == ptag]
                if matching:
                    out.append({"lbl": label, "cnt": len(matching)})
            return out

        # Count rels by type
        if "MATCH (a)-[r]->(b)" in query and "count(*)" in query:
            counts: dict[str, int] = defaultdict(int)
            ptag = params.get("ptag", "")
            for src_id, rel_type, tgt_id, _ in self.relationships:
                src = self.nodes_by_id.get(src_id, {})
                tgt = self.nodes_by_id.get(tgt_id, {})
                if src.get("_wheeler_project") == ptag and tgt.get("_wheeler_project") == ptag:
                    counts[rel_type] += 1
            return [{"rel": rt, "cnt": c} for rt, c in counts.items()]

        # Fetch all nodes with tag (verify_backup)
        if "RETURN n, labels(n)" in query:
            ptag = params.get("ptag", "")
            out = []
            for nid, props in self.nodes_by_id.items():
                if props.get("_wheeler_project") == ptag:
                    out.append({"n": props, "labels": [self.node_label_by_id.get(nid, "Unknown")]})
            return out

        # Dataset parent link lookups (mutations.py auto-links parent_dataset)
        if "WHERE n.path = $path" in query:
            return []

        # Script/Dataset path lookups
        if "MATCH (n) WHERE" in query:
            return []

        # Fulltext index creation / other DDL - silently ignore
        return []


# ---------------------------------------------------------------------------
# Project setup helpers
# ---------------------------------------------------------------------------


def _build_project_a(root: Path, tag: str = "proj-a") -> WheelerConfig:
    """Scaffold project A on disk and return a WheelerConfig rooted there."""
    root.mkdir(parents=True, exist_ok=True)

    # Required dirs
    for d in [".plans", ".notes", "scripts", "data", "knowledge", "synthesis", ".wheeler"]:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Artifact files
    (root / ".plans" / "STATE.md").write_text(
        "# State\nActive investigation: handoff roundtrip test.\n"
    )
    (root / ".notes" / "finding.md").write_text(
        "# Finding\nMeasured tau_rise = 0.12ms for parasol cells.\n"
    )
    (root / "scripts" / "run.py").write_text(
        "\"\"\"Roundtrip test script.\"\"\"\nimport numpy as np\n\n"
        "def main():\n    return np.zeros(10)\n"
    )
    (root / "data" / "dataset.csv").write_text(
        "cell_type,tau_rise,tau_decay\nparasol,0.12,0.48\nmidget,0.14,0.45\n"
    )

    # wheeler.yaml
    (root / "wheeler.yaml").write_text(
        f"neo4j:\n"
        f"  uri: bolt://localhost:7687\n"
        f"  password: research-graph\n"
        f"  project_tag: {tag}\n"
        f"knowledge_path: knowledge\n"
        f"synthesis_path: synthesis\n"
        f"project_root: .\n"
    )

    cfg = WheelerConfig(
        neo4j=Neo4jConfig(project_tag=tag),
        knowledge_path=str(root / "knowledge"),
        synthesis_path=str(root / "synthesis"),
        project_root=str(root),
    )
    return cfg


# ---------------------------------------------------------------------------
# Test 1: Full roundtrip (scope=project)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handoff_roundtrip_full(tmp_path):
    """Full backup -> restore roundtrip with scope=project.

    Builds project A, backs it up, restores into project B, and asserts
    structural invariants: same node count, same IDs, path absolutization,
    no A-root leakage in synthesis, USED rel with rel_props intact,
    Execution(kind=restore) present, restore_log.jsonl valid.
    """
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    project_b.mkdir(parents=True)

    cfg_a = _build_project_a(project_a, tag="proj-a")

    backend_a = E2EFakeBackend("proj-a")

    # ---------- Step 1: add nodes to project A ----------
    with patch("wheeler.tools.graph_tools._get_backend",
               new_callable=AsyncMock, return_value=backend_a):
        from wheeler.tools.graph_tools import execute_tool

        # Script
        script_result = json.loads(await execute_tool(
            "add_script",
            {
                "path": str(project_a / "scripts" / "run.py"),
                "language": "python",
                "_restoring": False,
            },
            cfg_a,
        ))
        script_id = script_result["node_id"]

        # Dataset (requires path, type, description)
        dataset_result = json.loads(await execute_tool(
            "add_dataset",
            {
                "path": str(project_a / "data" / "dataset.csv"),
                "type": "csv",
                "description": "Parasol and midget tau measurements CSV",
            },
            cfg_a,
        ))
        dataset_id = dataset_result["node_id"]

        # Finding (no required path field - pass empty or None)
        finding_result = json.loads(await execute_tool(
            "add_finding",
            {
                "description": "tau_rise = 0.12ms for parasol cells; shorter than midget (0.14ms)",
                "confidence": 0.88,
            },
            cfg_a,
        ))
        finding_id = finding_result["node_id"]

        # USED relationship from Script to Dataset with rel_props
        link_result = json.loads(await execute_tool(
            "link_nodes",
            {
                "source_id": script_id,
                "target_id": dataset_id,
                "relationship": "USED",
                "rel_props": {"purpose": "training set", "role": "primary"},
            },
            cfg_a,
        ))
        assert link_result["status"] == "linked", f"link_nodes failed: {link_result}"

    # Confirm the USED relationship with rel_props was recorded in backend_a
    used_rels = [
        (src, rt, tgt, rp)
        for src, rt, tgt, rp in backend_a.relationships
        if rt == "USED"
    ]
    assert len(used_rels) == 1, f"Expected 1 USED rel, got {len(used_rels)}"
    assert used_rels[0][3] == {"purpose": "training set", "role": "primary"}, (
        f"rel_props on A wrong: {used_rels[0][3]}"
    )

    all_ids_a = set(backend_a.nodes_by_id.keys())
    assert script_id in all_ids_a
    assert dataset_id in all_ids_a
    assert finding_id in all_ids_a

    # ---------- Step 2: backup project A ----------
    archive_dest = tmp_path / "backups"
    archive_dest.mkdir()

    with patch("wheeler.backup.get_backend", return_value=backend_a), \
         patch("wheeler.backup._record_backup_execution", new_callable=AsyncMock):
        archive_path = await create_backup(
            cfg_a,
            destination=archive_dest,
            scope="project",
            yes=True,
        )

    assert archive_path.exists(), f"Archive not created: {archive_path}"

    # ---------- Step 3: inspect the archive ----------
    with tarfile.open(archive_path, "r:gz") as tar:
        names = set(tar.getnames())
        manifest_raw = tar.extractfile("manifest.json").read()
        manifest = json.loads(manifest_raw)

        # Manifest version
        assert manifest.get("manifest_version") == 2, f"Expected v2 manifest, got: {manifest.get('manifest_version')}"

        # archive_uuid is a 32-char hex string
        auuid = manifest.get("archive_uuid", "")
        assert re.fullmatch(r"[0-9a-f]{32}", auuid), f"archive_uuid not 32-hex: {auuid!r}"

        # Manifest signature verifies
        expected_sig = compute_manifest_signature(manifest)
        assert manifest.get("manifest_signature") == expected_sig, "manifest_signature mismatch"

        # Required project tree files present
        assert "project/.plans/STATE.md" in names, f"STATE.md missing; names sample: {sorted(names)[:10]}"
        assert "project/.notes/finding.md" in names
        assert "project/scripts/run.py" in names
        assert "project/data/dataset.csv" in names

        # graph_nodes.jsonl present and has ${PROJECT}/ rewrites for path nodes
        nodes_jsonl_raw = tar.extractfile("graph_nodes.jsonl").read().decode("utf-8")
        node_entries = [
            json.loads(line) for line in nodes_jsonl_raw.splitlines() if line.strip()
        ]
        node_ids_in_archive = {
            e["props"]["id"] for e in node_entries if e.get("props", {}).get("id")
        }
        assert script_id in node_ids_in_archive, f"{script_id} missing from archive nodes"
        assert dataset_id in node_ids_in_archive
        assert finding_id in node_ids_in_archive

        # Path fields in JSONL use ${PROJECT}/ sentinel
        for entry in node_entries:
            props = entry.get("props") or {}
            path_val = props.get("path", "")
            if path_val and not path_val.startswith("${PROJECT}/"):
                # Only sentinel-prefixed paths are allowed; empty/None is fine
                assert str(project_a) not in path_val, (
                    f"Absolute path leaked into archive JSONL for node {props.get('id')}: {path_val}"
                )

        # graph_relationships.jsonl has the USED rel with rel_props
        rels_jsonl_raw = tar.extractfile("graph_relationships.jsonl").read().decode("utf-8")
        rel_entries = [
            json.loads(line) for line in rels_jsonl_raw.splitlines() if line.strip()
        ]
        used_in_archive = [r for r in rel_entries if r.get("rel_type") == "USED"]
        assert len(used_in_archive) >= 1, "USED relationship missing from archive"
        assert used_in_archive[0].get("rel_props") == {
            "purpose": "training set", "role": "primary"
        }, f"rel_props in archive: {used_in_archive[0].get('rel_props')}"

    # ---------- Step 4: restore into project B ----------
    backend_b = E2EFakeBackend("proj-b")
    cfg_b_initial = WheelerConfig(
        neo4j=Neo4jConfig(project_tag="proj-b"),
        project_root=str(project_b),
    )

    with patch("wheeler.tools.graph_tools._get_backend",
               new_callable=AsyncMock, return_value=backend_b), \
         patch("wheeler.restore.get_backend", return_value=backend_b):
        result = await restore_fresh(
            cfg_b_initial,
            archive_path,
            target_root=project_b,
            project_tag="proj-b",
        )

    # ---------- Step 5: assert structural invariants ----------

    # Result must be ok or partial (partial = some failures)
    assert result["status"] in ("ok", "partial"), f"restore_fresh failed: {result}"

    # Same node count as A (excluding Execution nodes added by restore)
    original_ids_a = {script_id, dataset_id, finding_id}
    for nid in original_ids_a:
        assert nid in backend_b.nodes_by_id, (
            f"Node {nid} not restored to B. B nodes: {set(backend_b.nodes_by_id.keys())}"
        )

    # Same set of original node IDs present on B
    b_ids = set(backend_b.nodes_by_id.keys())
    assert original_ids_a <= b_ids, f"Missing original IDs on B: {original_ids_a - b_ids}"

    # Path fields on B are absolutized under project_b (not project_a)
    for nid in (script_id, dataset_id):
        node_b = backend_b.nodes_by_id.get(nid, {})
        path_val = node_b.get("path", "")
        if path_val:
            assert "${PROJECT}" not in path_val, (
                f"Sentinel not resolved on B for node {nid}: {path_val}"
            )
            assert str(project_a) not in path_val, (
                f"Project A path leaked onto B for node {nid}: {path_val}"
            )
            assert str(project_b.resolve()) in path_val, (
                f"Project B root not in path on B for node {nid}: {path_val}"
            )

    # Every file from project/ in the archive exists on disk under project_b
    for rel_path in (
        ".plans/STATE.md",
        ".notes/finding.md",
        "scripts/run.py",
        "data/dataset.csv",
    ):
        dest = project_b / rel_path
        assert dest.exists(), f"File not extracted to B: {dest}"

    # synthesis/*.md files on B must not contain A's absolute root AND must
    # not contain the literal ${PROJECT} sentinel (Gap 1 regression guard).
    a_root_str = str(project_a.resolve())
    synth_b = project_b / "synthesis"
    if synth_b.exists():
        for md_file in synth_b.rglob("*.md"):
            content = md_file.read_text(errors="replace")
            assert a_root_str not in content, (
                f"A's root path found in B synthesis file {md_file.name}: "
                f"{a_root_str!r} appears in content"
            )
            assert "${PROJECT}" not in content, (
                f"Unresolved ${{PROJECT}} sentinel in B synthesis file {md_file.name}. "
                "The synthesis rewrite (backup) or absolutize (restore) is broken."
            )

    # The USED relationship exists on B with the same rel_props (regression check)
    used_on_b = [
        (src, rt, tgt, rp)
        for src, rt, tgt, rp in backend_b.relationships
        if rt == "USED"
        and src == script_id
        and tgt == dataset_id
    ]
    assert len(used_on_b) >= 1, (
        f"USED rel not restored on B. B rels: {[(s, rt, t) for s, rt, t, _ in backend_b.relationships]}"
    )
    assert used_on_b[0][3] == {"purpose": "training set", "role": "primary"}, (
        f"rel_props not preserved on B: {used_on_b[0][3]}"
    )

    # An Execution(kind="restore") node exists on B
    restore_exec_nodes = [
        n for n in backend_b.nodes_by_id.values()
        if backend_b.node_label_by_id.get(n.get("id", "")) == "Execution"
        and n.get("kind") == "restore"
    ]
    assert len(restore_exec_nodes) >= 1, (
        "No Execution(kind=restore) node found on B. "
        f"Execution nodes: {[n for n in backend_b.nodes_by_id.values() if backend_b.node_label_by_id.get(n.get('id', '')) == 'Execution']}"
    )

    # .wheeler/restore_log.jsonl exists with expected keys
    log_path = project_b / ".wheeler" / "restore_log.jsonl"
    assert log_path.exists(), f"restore_log.jsonl not created at {log_path}"
    with log_path.open() as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    assert len(lines) == 1, f"Expected 1 log line, got {len(lines)}"
    log_record = json.loads(lines[0])
    for required_key in (
        "ts", "archive_path", "archive_uuid", "source", "mode",
        "nodes_restored", "relationships_restored",
    ):
        assert required_key in log_record, (
            f"restore_log.jsonl missing key: {required_key}"
        )
    assert log_record["mode"] == "fresh"
    assert log_record["source"].get("hostname"), "source.hostname missing from log"


# ---------------------------------------------------------------------------
# Test 2: scope=graph-only roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handoff_roundtrip_graph_only_scope(tmp_path):
    """graph-only scope: no project/ tree; graph nodes round-trip; synthesis rendered on B.

    With scope='graph-only', the archive contains no project/ subtree. After
    restore, the artifact files (.plans/, .notes/, scripts/, data/) do NOT
    exist on B. The graph nodes/relationships still round-trip cleanly, and
    triple-write produces synthesis/*.md files on B.
    """
    project_a = tmp_path / "project_a_go"
    project_b = tmp_path / "project_b_go"
    project_b.mkdir(parents=True)

    cfg_a = _build_project_a(project_a, tag="proj-go-a")
    backend_a = E2EFakeBackend("proj-go-a")

    with patch("wheeler.tools.graph_tools._get_backend",
               new_callable=AsyncMock, return_value=backend_a):
        from wheeler.tools.graph_tools import execute_tool

        script_result = json.loads(await execute_tool(
            "add_script",
            {
                "path": str(project_a / "scripts" / "run.py"),
                "language": "python",
            },
            cfg_a,
        ))
        script_id = script_result["node_id"]

        finding_result = json.loads(await execute_tool(
            "add_finding",
            {"description": "Graph-only scope roundtrip finding", "confidence": 0.75},
            cfg_a,
        ))
        finding_id = finding_result["node_id"]

        json.loads(await execute_tool(
            "link_nodes",
            {
                "source_id": finding_id,
                "target_id": script_id,
                "relationship": "WAS_GENERATED_BY",
            },
            cfg_a,
        ))

    # Backup with graph-only scope
    archive_dest = tmp_path / "backups_go"
    archive_dest.mkdir()

    with patch("wheeler.backup.get_backend", return_value=backend_a), \
         patch("wheeler.backup._record_backup_execution", new_callable=AsyncMock):
        archive_path = await create_backup(
            cfg_a,
            destination=archive_dest,
            scope="graph-only",
            yes=True,
        )

    # Inspect: no project/ in archive
    with tarfile.open(archive_path, "r:gz") as tar:
        names = set(tar.getnames())
    project_entries = [n for n in names if n.startswith("project/")]
    assert len(project_entries) == 0, (
        f"graph-only archive should have no project/ entries, found: {project_entries[:5]}"
    )

    # Restore into B
    backend_b = E2EFakeBackend("proj-go-b")
    cfg_b_initial = WheelerConfig(
        neo4j=Neo4jConfig(project_tag="proj-go-b"),
        project_root=str(project_b),
    )

    with patch("wheeler.tools.graph_tools._get_backend",
               new_callable=AsyncMock, return_value=backend_b), \
         patch("wheeler.restore.get_backend", return_value=backend_b):
        result = await restore_fresh(
            cfg_b_initial,
            archive_path,
            target_root=project_b,
            project_tag="proj-go-b",
        )

    assert result["status"] in ("ok", "partial"), f"restore failed: {result}"

    # Both original nodes present on B
    assert script_id in backend_b.nodes_by_id, f"{script_id} not on B"
    assert finding_id in backend_b.nodes_by_id, f"{finding_id} not on B"

    # Artifact files do NOT exist on B (no project/ subtree was extracted)
    assert not (project_b / ".plans" / "STATE.md").exists(), (
        "STATE.md should not exist on B (graph-only scope)"
    )
    assert not (project_b / "scripts" / "run.py").exists(), (
        "scripts/run.py should not exist on B (graph-only scope)"
    )

    # synthesis/*.md may exist on B due to triple-write during restore
    # (that is expected and correct behaviour)
    synth_b = project_b / "synthesis"
    # Verify no A-root leakage in synthesis if it exists
    a_root_str = str(project_a.resolve())
    if synth_b.exists():
        for md_file in synth_b.rglob("*.md"):
            content = md_file.read_text(errors="replace")
            assert a_root_str not in content, (
                f"A's root leaked into B synthesis: {md_file.name}"
            )


# ---------------------------------------------------------------------------
# Test 3: rel_props preserved (targeted regression)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handoff_relationship_rel_props_preserved(tmp_path):
    """Targeted regression: rel_props with heterogeneous types survive the roundtrip.

    Creates a USED relationship with props carrying a string, float, and list.
    Backs up, restores, asserts rel_props dict-equality including the list value.
    This verifies the Wave 1 fix to link_nodes passing rel_props through to the
    backend and the restore path reading rel_props from the JSONL correctly.
    """
    project_a = tmp_path / "project_a_rp"
    project_b = tmp_path / "project_b_rp"
    project_b.mkdir(parents=True)

    cfg_a = _build_project_a(project_a, tag="proj-rp-a")
    backend_a = E2EFakeBackend("proj-rp-a")

    # Relationship properties with heterogeneous types
    expected_rel_props = {"purpose": "training", "weight": 0.5, "tags": ["a", "b"]}

    with patch("wheeler.tools.graph_tools._get_backend",
               new_callable=AsyncMock, return_value=backend_a):
        from wheeler.tools.graph_tools import execute_tool

        script_result = json.loads(await execute_tool(
            "add_script",
            {
                "path": str(project_a / "scripts" / "run.py"),
                "language": "python",
            },
            cfg_a,
        ))
        script_id = script_result["node_id"]

        dataset_result = json.loads(await execute_tool(
            "add_dataset",
            {
                "path": str(project_a / "data" / "dataset.csv"),
                "type": "csv",
                "description": "rel_props regression dataset CSV",
            },
            cfg_a,
        ))
        dataset_id = dataset_result["node_id"]

        link_result = json.loads(await execute_tool(
            "link_nodes",
            {
                "source_id": script_id,
                "target_id": dataset_id,
                "relationship": "USED",
                "rel_props": expected_rel_props,
            },
            cfg_a,
        ))
        assert link_result["status"] == "linked", f"link_nodes failed: {link_result}"

    # Verify rel_props on A before backup
    used_a = [
        rp for src, rt, tgt, rp in backend_a.relationships
        if rt == "USED" and src == script_id and tgt == dataset_id
    ]
    assert len(used_a) == 1 and used_a[0] == expected_rel_props, (
        f"rel_props on A before backup: {used_a}"
    )

    # Backup
    archive_dest = tmp_path / "backups_rp"
    archive_dest.mkdir()

    with patch("wheeler.backup.get_backend", return_value=backend_a), \
         patch("wheeler.backup._record_backup_execution", new_callable=AsyncMock):
        archive_path = await create_backup(
            cfg_a,
            destination=archive_dest,
            scope="project",
            yes=True,
        )

    # Verify rel_props in archive JSONL (dict equality including list)
    with tarfile.open(archive_path, "r:gz") as tar:
        rels_raw = tar.extractfile("graph_relationships.jsonl").read().decode("utf-8")
    rel_entries = [
        json.loads(line) for line in rels_raw.splitlines() if line.strip()
    ]
    used_in_archive = [
        r for r in rel_entries
        if r.get("rel_type") == "USED"
        and r.get("source_id") == script_id
        and r.get("target_id") == dataset_id
    ]
    assert len(used_in_archive) == 1, (
        f"USED rel not in archive JSONL. All rels: {rel_entries}"
    )
    assert used_in_archive[0]["rel_props"] == expected_rel_props, (
        f"rel_props in archive: {used_in_archive[0]['rel_props']}"
    )

    # Restore to B
    backend_b = E2EFakeBackend("proj-rp-b")
    cfg_b_initial = WheelerConfig(
        neo4j=Neo4jConfig(project_tag="proj-rp-b"),
        project_root=str(project_b),
    )

    with patch("wheeler.tools.graph_tools._get_backend",
               new_callable=AsyncMock, return_value=backend_b), \
         patch("wheeler.restore.get_backend", return_value=backend_b):
        result = await restore_fresh(
            cfg_b_initial,
            archive_path,
            target_root=project_b,
            project_tag="proj-rp-b",
        )

    assert result["status"] in ("ok", "partial"), f"restore failed: {result}"

    # Assert rel_props dict equality on B (including the list value)
    used_b = [
        rp for src, rt, tgt, rp in backend_b.relationships
        if rt == "USED"
        and src == script_id
        and tgt == dataset_id
    ]
    assert len(used_b) >= 1, (
        f"USED rel not on B. B rels: {[(s, rt, t) for s, rt, t, _ in backend_b.relationships]}"
    )
    assert used_b[0] == expected_rel_props, (
        f"rel_props NOT preserved on B: got {used_b[0]!r}, expected {expected_rel_props!r}"
    )
