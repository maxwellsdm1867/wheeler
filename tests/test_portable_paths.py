"""Portable file identity: a stored path must still open a real file.

The failure this guards against is not "the string looks wrong", it is "the string
looks right and the file cannot be opened". So almost every test here writes a
real file, stores a node for it, resolves the stored value back, and READS THE
FILE, rather than asserting on path strings.

The second theme is the hybrid: the graph holds absolute (legacy) and portable
(current) spellings of the same file at once, indefinitely. Tests here pin the
three properties that make that survivable: lookups find a node under either
spelling, a legacy node still resolves, and a graph written on another machine
does not invalidate itself when opened here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wheeler import config as config_mod
from wheeler import machine
from wheeler.config import WheelerConfig
from wheeler.portability import is_portable, resolve, to_portable

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point $HOME at a scratch dir so the real machine id and roots are untouched.

    Both `machine` and `config` cache per process, so the caches are cleared on
    the way in AND on the way out: a leaked machine id would make the staleness
    tests below assert against whatever the previous test happened to write.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("WHEELER_MACHINE_ID", raising=False)
    monkeypatch.delenv("WHEELER_MACHINE_LABEL", raising=False)
    machine.reset_cache()
    config_mod.reset_roots_cache()
    yield home
    machine.reset_cache()
    config_mod.reset_roots_cache()


def write_roots(home: Path, **roots: str) -> None:
    """Write ~/.wheeler/config.yaml with the given named roots."""
    wheeler_dir = home / ".wheeler"
    wheeler_dir.mkdir(parents=True, exist_ok=True)
    body = "roots:\n" + "".join(f"  {name}: {path}\n" for name, path in roots.items())
    (wheeler_dir / "config.yaml").write_text(body)
    config_mod.reset_roots_cache()


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project tree with a real file in it, plus a config anchored on it."""
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "knowledge").mkdir()
    (root / "synthesis").mkdir()
    script = root / "src" / "analysis.py"
    script.write_text("# real content\nx = 1\n")
    monkeypatch.setenv("WHEELER_PROJECT_ROOT", str(root))
    cfg = WheelerConfig()
    cfg.search.enabled = False
    return cfg, root, script


class RecordingBackend:
    """Minimal backend that remembers what was written, keyed by node id."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}

    async def initialize(self) -> None:
        pass

    async def create_node(self, label: str, properties: dict) -> str:
        props = dict(properties)
        node_id = props.get("id") or f"{label[:1]}-generated"
        props["id"] = node_id
        self.nodes[node_id] = {"__label__": label, **props}
        return node_id

    async def get_node(self, label: str, node_id: str):
        return self.nodes.get(node_id)

    async def update_node(self, label: str, node_id: str, updates: dict) -> bool:
        if node_id not in self.nodes:
            return False
        self.nodes[node_id].update(updates)
        return True

    async def run_cypher(self, query: str, parameters: dict | None = None):
        """Answers the ensure_artifact path lookup and nothing more."""
        wanted = (parameters or {}).get("path")
        return [
            {"id": nid, "label": props["__label__"], "hash": props.get("hash", "")}
            for nid, props in self.nodes.items()
            if props.get("path") == wanted
        ][:2]


def patched_backend(backend: RecordingBackend):
    return patch(
        "wheeler.tools.graph_tools._get_backend",
        new_callable=AsyncMock,
        return_value=backend,
    )


# ---------------------------------------------------------------------------
# 1-8, 12: resolution against real files
# ---------------------------------------------------------------------------


class TestRuntimeResolution:
    async def test_project_file_round_trips_and_opens(self, project):
        """The whole point: portabilize, resolve, and read the actual bytes back."""
        cfg, root, script = project
        portable, root_id = to_portable(str(script), cfg.resolved_roots)

        assert portable == "${PROJECT}/src/analysis.py"
        assert root_id == "project"

        resolved = resolve(portable, cfg.resolved_roots)
        assert resolved is not None
        assert resolved.read_text() == "# real content\nx = 1\n"

    async def test_resolution_is_cwd_independent(self, project, tmp_path):
        """Resolving from another cwd must still open the file.

        The MCP servers are spawned separately from the CLI and do not share its
        cwd, so anything cwd-derived passes in-process and fails in production.
        """
        cfg, root, script = project
        portable, _ = to_portable(str(script), cfg.resolved_roots)

        elsewhere = tmp_path / "somewhere-else"
        elsewhere.mkdir()
        previous = Path.cwd()
        try:
            os.chdir(elsewhere)
            resolved = resolve(portable, cfg.resolved_roots)
            assert resolved is not None
            assert resolved.read_text() == "# real content\nx = 1\n"
        finally:
            os.chdir(previous)

    async def test_relocated_project_still_opens(self, project, tmp_path, monkeypatch):
        """Move the tree, remap the root: the same stored value must resolve.

        This is the second-computer case in miniature. An absolute path would be
        dead here; a portable one is the whole reason this change exists.
        """
        cfg, root, script = project
        portable, _ = to_portable(str(script), cfg.resolved_roots)

        moved = tmp_path / "relocated"
        root.rename(moved)
        monkeypatch.setenv("WHEELER_PROJECT_ROOT", str(moved))
        relocated_cfg = WheelerConfig()

        resolved = resolve(portable, relocated_cfg.resolved_roots)
        assert resolved is not None
        assert resolved == moved / "src" / "analysis.py"
        assert resolved.read_text() == "# real content\nx = 1\n"

    async def test_named_non_project_root_opens_and_hashes(
        self, project, tmp_path, isolated_home
    ):
        """A file under a configured `data:` root resolves and hashes identically."""
        from wheeler.graph.provenance import hash_file

        cfg, root, _ = project
        data_dir = tmp_path / "volumes" / "lab"
        data_dir.mkdir(parents=True)
        recording = data_dir / "cell01.mat"
        recording.write_bytes(b"\x00binary recording\x01")
        write_roots(isolated_home, data=str(data_dir))

        portable, root_id = to_portable(str(recording), cfg.resolved_roots)
        assert portable == "${DATA}/cell01.mat"
        assert root_id == "data"

        resolved = resolve(portable, cfg.resolved_roots)
        assert resolved is not None
        assert resolved.read_bytes() == b"\x00binary recording\x01"
        assert hash_file(resolved) == hash_file(recording)

    async def test_unconfigured_root_is_unresolvable_not_a_crash(self, project):
        """A root this machine does not have yields None, not an exception.

        None is a distinct answer from "the file is missing": it means the file
        lives on another computer, which must never be read as staleness.
        """
        cfg, _, _ = project
        assert resolve("${GDRIVE}/paper/fig1.png", cfg.resolved_roots) is None

    async def test_external_path_stays_absolute_and_opens(self, project, tmp_path):
        """A file outside every root is stored absolute and still opens."""
        cfg, _, _ = project
        outside = tmp_path / "outside.txt"
        outside.write_text("external")

        portable, root_id = to_portable(str(outside), cfg.resolved_roots)
        assert root_id == ""
        assert not is_portable(portable)

        resolved = resolve(portable, cfg.resolved_roots)
        assert resolved is not None
        assert resolved.read_text() == "external"

    async def test_symlinked_root_still_portabilizes(
        self, tmp_path, monkeypatch, isolated_home
    ):
        """A root reached through a symlink, which is what Google Drive looks like.

        If only one side is resolve()d, containment silently fails and the path is
        stored absolute forever, so this is the case that quietly breaks sync
        folders rather than erroring.
        """
        real = tmp_path / "real-drive"
        (real / "notes").mkdir(parents=True)
        target = real / "notes" / "draft.md"
        target.write_text("# draft")

        link = tmp_path / "My Drive"
        link.symlink_to(real)
        write_roots(isolated_home, gdrive=str(link))
        monkeypatch.setenv("WHEELER_PROJECT_ROOT", str(tmp_path / "proj"))
        cfg = WheelerConfig()

        portable, root_id = to_portable(str(link / "notes" / "draft.md"), cfg.resolved_roots)
        assert root_id == "gdrive", f"symlinked root was not matched: {portable}"
        assert portable == "${GDRIVE}/notes/draft.md"

        resolved = resolve(portable, cfg.resolved_roots)
        assert resolved is not None
        assert resolved.read_text() == "# draft"

    async def test_nested_roots_prefer_the_deepest(self, project, tmp_path, isolated_home):
        """With data/ inside the project, a file there belongs to ${DATA}."""
        cfg, root, _ = project
        nested = root / "data"
        nested.mkdir()
        f = nested / "x.csv"
        f.write_text("a,b\n")
        write_roots(isolated_home, data=str(nested))

        portable, root_id = to_portable(str(f), cfg.resolved_roots)
        assert (portable, root_id) == ("${DATA}/x.csv", "data")
        assert resolve(portable, cfg.resolved_roots).read_text() == "a,b\n"

    async def test_portabilizing_is_idempotent(self, project):
        """Applying to_portable twice equals once, so backup cannot double-encode."""
        cfg, _, script = project
        once, _ = to_portable(str(script), cfg.resolved_roots)
        twice, root_id = to_portable(once, cfg.resolved_roots)
        assert twice == once
        assert root_id == ""

    async def test_resolving_is_idempotent(self, project):
        """resolve() of an already-absolute value returns it unchanged."""
        cfg, _, script = project
        first = resolve(str(script), cfg.resolved_roots)
        second = resolve(str(first), cfg.resolved_roots)
        assert first == second
        assert second.read_text() == "# real content\nx = 1\n"


# ---------------------------------------------------------------------------
# The write path: both storage layers must agree
# ---------------------------------------------------------------------------


# label -> (tool, filename, extra required args). Mirrors
# portability.iter_path_fields, which is the definition of "carries a path".
# The filenames differ per label because the artifact-type guard rejects, for
# instance, registering a .py file as a Document.
_PATH_LABELS = {
    "Script": ("add_script", "src/analysis.py", {"language": "python"}),
    "Dataset": ("add_dataset", "src/table.csv", {"type": "csv", "description": "d"}),
    "Document": ("add_document", "src/notes.md", {"title": "T"}),
    "Plan": ("add_plan", "src/plan.md", {"title": "T"}),
    "Finding": ("add_finding", "src/fig.png", {"description": "d", "confidence": 0.9}),
}


class TestWritePath:
    async def test_every_path_bearing_label_stores_a_portable_path(self, project):
        """Drive the full label set, not just Script."""
        from wheeler.portability import iter_path_fields
        from wheeler.tools.graph_tools import execute_tool

        cfg, root, _ = project
        for label, (tool, rel, extra) in _PATH_LABELS.items():
            assert list(iter_path_fields(label)) == ["path"], label
            target = root / rel
            target.write_text(f"content for {label}\n")

            backend = RecordingBackend()
            with patched_backend(backend):
                result = json.loads(
                    await execute_tool(tool, {"path": str(target), **extra}, cfg)
                )
            assert "error" not in result, (label, result)

            stored = backend.nodes[result["node_id"]]["path"]
            assert stored == f"${{PROJECT}}/{rel}", label
            # The stored value must lead back to the real bytes on disk.
            resolved = resolve(stored, cfg.resolved_roots)
            assert resolved is not None, label
            assert resolved.read_text() == f"content for {label}\n", label

    async def test_knowledge_json_carries_the_same_path_and_the_origin(self, project):
        """The graph and the file layer must not disagree about where a file is."""
        from wheeler.tools.graph_tools import execute_tool

        cfg, root, script = project
        backend = RecordingBackend()
        with patched_backend(backend):
            result = json.loads(
                await execute_tool(
                    "add_script", {"path": str(script), "language": "python"}, cfg
                )
            )

        node_id = result["node_id"]
        record = json.loads((root / "knowledge" / f"{node_id}.json").read_text())

        assert record["path"] == backend.nodes[node_id]["path"] == "${PROJECT}/src/analysis.py"
        assert record["origin_machine"] == machine.machine_id()
        assert record["origin_host"] == machine.machine_label()
        # And the file layer alone is enough to reach the artifact.
        assert resolve(record["path"], cfg.resolved_roots).read_text().startswith("# real")

    async def test_external_file_is_stored_absolute(self, project, tmp_path):
        """Nothing is forced into a root that does not contain it."""
        from wheeler.tools.graph_tools import execute_tool

        cfg, _, _ = project
        outside = tmp_path / "elsewhere.py"
        outside.write_text("y = 2\n")

        backend = RecordingBackend()
        with patched_backend(backend):
            result = json.loads(
                await execute_tool(
                    "add_script", {"path": str(outside), "language": "python"}, cfg
                )
            )
        stored = backend.nodes[result["node_id"]]["path"]
        assert not is_portable(stored)
        assert resolve(stored, cfg.resolved_roots).read_text() == "y = 2\n"

    async def test_backend_stamps_origin_on_every_created_node(self, project):
        """The graph half of the stamp, which the add_* handlers cannot carry."""
        from wheeler.graph.neo4j_backend import Neo4jBackend

        cfg, _, _ = project
        session = AsyncMock()
        session.run = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        driver = MagicMock()
        driver.session = MagicMock(return_value=session)

        backend = Neo4jBackend(cfg)
        with patch.object(Neo4jBackend, "_driver", return_value=driver):
            await backend.create_node("Script", {"id": "S-abc12345", "path": "x.py"})

        props = session.run.await_args.kwargs["parameters"]["props"]
        assert props["origin_machine"] == machine.machine_id()
        assert props["origin_database"] == cfg.neo4j.database

    async def test_existing_origin_is_not_overwritten(self, project):
        """A restore replaying an archived node keeps the machine that wrote it."""
        from wheeler.graph.neo4j_backend import Neo4jBackend

        cfg, _, _ = project
        session = AsyncMock()
        session.run = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        driver = MagicMock()
        driver.session = MagicMock(return_value=session)

        backend = Neo4jBackend(cfg)
        with patch.object(Neo4jBackend, "_driver", return_value=driver):
            await backend.create_node(
                "Script", {"id": "S-abc12345", "origin_machine": "other-laptop"}
            )

        props = session.run.await_args.kwargs["parameters"]["props"]
        assert props["origin_machine"] == "other-laptop"

    async def test_field_validation_does_not_resolve_a_portable_path(self):
        """`${PROJECT}/a.py` must not become `<cwd>/${PROJECT}/a.py`."""
        from wheeler.tools.graph_tools._field_specs import validate_and_normalize

        args = {"node_id": "S-abc12345", "path": "${PROJECT}/src/analysis.py"}
        errors, _ = validate_and_normalize("update_node", args)
        assert errors == {}
        assert args["path"] == "${PROJECT}/src/analysis.py"


# ---------------------------------------------------------------------------
# 10, 11: the hybrid
# ---------------------------------------------------------------------------


class TestHybrid:
    async def test_legacy_absolute_node_is_found_not_duplicated(self, project):
        """The migration-boundary bug: one file must not end up with two nodes."""
        from wheeler.graph.provenance import hash_file
        from wheeler.knowledge.store import write_node
        from wheeler.models import ScriptModel
        from wheeler.tools.graph_tools import execute_tool

        cfg, root, script = project
        backend = RecordingBackend()
        # A node as it would have been written before portable paths existed.
        backend.nodes["S-legacy01"] = {
            "__label__": "Script",
            "id": "S-legacy01",
            "path": str(script),
            "hash": hash_file(script),
        }
        write_node(
            root / "knowledge",
            ScriptModel(id="S-legacy01", path=str(script), hash=hash_file(script)),
        )

        with patched_backend(backend):
            result = json.loads(
                await execute_tool(
                    "ensure_artifact", {"path": str(script), "language": "python"}, cfg
                )
            )

        assert result["node_id"] == "S-legacy01", "a duplicate node was created"
        assert result["action"] == "unchanged"
        assert len(backend.nodes) == 1

    async def test_legacy_node_is_upgraded_in_place(self, project):
        """Finding a node under an old spelling rewrites it to the portable one."""
        from wheeler.graph.provenance import hash_file
        from wheeler.knowledge.store import write_node
        from wheeler.models import ScriptModel
        from wheeler.tools.graph_tools import execute_tool

        cfg, root, script = project
        backend = RecordingBackend()
        backend.nodes["S-legacy01"] = {
            "__label__": "Script",
            "id": "S-legacy01",
            "path": str(script),
            "hash": hash_file(script),
        }
        write_node(
            root / "knowledge",
            ScriptModel(id="S-legacy01", path=str(script), hash=hash_file(script)),
        )

        with patched_backend(backend):
            result = json.loads(
                await execute_tool(
                    "ensure_artifact", {"path": str(script), "language": "python"}, cfg
                )
            )

        assert result["path_upgraded"] is True
        assert backend.nodes["S-legacy01"]["path"] == "${PROJECT}/src/analysis.py"
        # The caller still gets an absolute path it can open directly.
        assert Path(result["path"]).read_text().startswith("# real")

    async def test_legacy_node_still_resolves_before_any_upgrade(self, project):
        """An untouched absolute node keeps working on the machine that wrote it."""
        cfg, _, script = project
        resolved = resolve(str(script), cfg.resolved_roots)
        assert resolved is not None
        assert resolved.read_text() == "# real content\nx = 1\n"


# ---------------------------------------------------------------------------
# 9, 14: staleness classification and the cascade
# ---------------------------------------------------------------------------


def _driver_returning(records: list[dict]):
    """A mock async driver whose session.run yields `records`."""

    async def _aiter(self):
        for r in records:
            yield r

    result = AsyncMock()
    result.__aiter__ = _aiter
    session = AsyncMock()
    session.run = AsyncMock(return_value=result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    driver = MagicMock()
    driver.session = MagicMock(return_value=session)
    return driver


class TestStaleness:
    async def test_matching_hash_is_not_stale(self, project):
        from wheeler.graph.provenance import detect_stale_scripts, hash_file

        cfg, _, script = project
        records = [{
            "id": "S-1", "path": "${PROJECT}/src/analysis.py",
            "hash": hash_file(script),
            "origin_machine": machine.machine_id(), "origin_host": "here",
        }]
        with patch(
            "wheeler.graph.provenance.get_async_driver",
            return_value=_driver_returning(records),
        ):
            assert await detect_stale_scripts(cfg) == []

    async def test_own_changed_file_is_still_stale(self, project):
        """The original behaviour must survive: my edited script is stale."""
        from wheeler.graph.provenance import detect_stale_scripts

        cfg, _, _ = project
        records = [{
            "id": "S-1", "path": "${PROJECT}/src/analysis.py",
            "hash": "stale-digest",
            "origin_machine": machine.machine_id(), "origin_host": "here",
        }]
        with patch(
            "wheeler.graph.provenance.get_async_driver",
            return_value=_driver_returning(records),
        ):
            stale = await detect_stale_scripts(cfg)
        assert [s.reason for s in stale] == ["changed"]

    async def test_legacy_node_with_a_present_file_still_cascades(self, project):
        """A pre-stamp node whose file IS here is ours: presence is the evidence.

        Without this, adding origin stamping would silently switch staleness off
        for every node in an existing graph.
        """
        from wheeler.graph.provenance import detect_stale_scripts

        cfg, _, _ = project
        records = [{
            "id": "S-1", "path": "${PROJECT}/src/analysis.py",
            "hash": "stale-digest", "origin_machine": None, "origin_host": None,
        }]
        with patch(
            "wheeler.graph.provenance.get_async_driver",
            return_value=_driver_returning(records),
        ):
            stale = await detect_stale_scripts(cfg)
        assert [s.reason for s in stale] == ["changed"]

    async def test_legacy_node_with_a_missing_file_does_not_cascade(self, project):
        """The other half, and the one a real Aura copy exposed.

        A graph moved to another machine carries thousands of unattributed nodes
        whose files were never on this computer. Reading those as "my file was
        deleted" invalidated 1,359 of 1,452 Scripts on first contact.
        """
        from wheeler.graph.provenance import detect_stale_scripts

        cfg, _, _ = project
        records = [{
            "id": "S-1", "path": "${PROJECT}/src/never_here.py",
            "hash": "some-digest", "origin_machine": None, "origin_host": None,
        }]
        with patch(
            "wheeler.graph.provenance.get_async_driver",
            return_value=_driver_returning(records),
        ):
            stale = await detect_stale_scripts(cfg)
        assert [s.reason for s in stale] == ["absent"]

    async def test_our_own_deleted_file_still_cascades(self, project):
        """A node this machine positively wrote, whose file is gone, is stale."""
        from wheeler.graph.provenance import detect_stale_scripts

        cfg, _, _ = project
        records = [{
            "id": "S-1", "path": "${PROJECT}/src/deleted.py", "hash": "d",
            "origin_machine": machine.machine_id(), "origin_host": "here",
        }]
        with patch(
            "wheeler.graph.provenance.get_async_driver",
            return_value=_driver_returning(records),
        ):
            stale = await detect_stale_scripts(cfg)
        assert [s.reason for s in stale] == ["changed"]

    async def test_another_machines_differing_copy_is_diverged(self, project):
        from wheeler.graph.provenance import detect_stale_scripts

        cfg, _, _ = project
        records = [{
            "id": "S-1", "path": "${PROJECT}/src/analysis.py",
            "hash": "written-on-the-laptop",
            "origin_machine": "other-machine-uuid", "origin_host": "home-linux",
        }]
        with patch(
            "wheeler.graph.provenance.get_async_driver",
            return_value=_driver_returning(records),
        ):
            stale = await detect_stale_scripts(cfg)
        assert [(s.reason, s.origin_host) for s in stale] == [("diverged", "home-linux")]

    async def test_unconfigured_root_is_absent(self, project):
        from wheeler.graph.provenance import detect_stale_scripts

        cfg, _, _ = project
        records = [{
            "id": "S-1", "path": "${GDRIVE}/analysis.py", "hash": "whatever",
            "origin_machine": "other-machine-uuid", "origin_host": "home-linux",
        }]
        with patch(
            "wheeler.graph.provenance.get_async_driver",
            return_value=_driver_returning(records),
        ):
            stale = await detect_stale_scripts(cfg)
        assert [s.reason for s in stale] == ["absent"]
        assert stale[0].current_hash == "ROOT_NOT_CONFIGURED"

    async def test_a_shared_graph_does_not_invalidate_itself(self, project):
        """THE regression. Nothing another machine wrote may cascade.

        Before the reason split, opening a graph written elsewhere found every
        path missing, reported FILE_NOT_FOUND for each, and propagated reduced
        stability through everything downstream.
        """
        from wheeler.provenance import detect_and_propagate_stale

        cfg, _, _ = project
        records = [
            {
                "id": f"S-{i}", "path": "${GDRIVE}/pipeline.py", "hash": "theirs",
                "origin_machine": "other-machine-uuid", "origin_host": "home-linux",
            }
            for i in range(5)
        ]
        propagate = AsyncMock(return_value=[])
        with patch(
            "wheeler.graph.provenance.get_async_driver",
            return_value=_driver_returning(records),
        ), patch("wheeler.provenance.propagate_invalidation", propagate):
            report = await detect_and_propagate_stale(cfg)

        propagate.assert_not_awaited()
        assert report["changed"] == 0
        assert report["downstream_affected"] == 0
        assert report["by_reason"] == {"absent": 5}


# ---------------------------------------------------------------------------
# 13: the audit
# ---------------------------------------------------------------------------


class TestPathAudit:
    async def test_reports_the_mix(self, project, tmp_path):
        from wheeler.consistency import audit_paths

        cfg, root, script = project
        missing = root / "src" / "gone.py"

        backend = RecordingBackend()
        backend.nodes = {
            "S-1": {"__label__": "Script", "path": "${PROJECT}/src/analysis.py"},
            "S-2": {"__label__": "Script", "path": str(script)},
            "S-3": {"__label__": "Script", "path": "${PROJECT}/src/gone.py"},
            "S-4": {"__label__": "Script", "path": "${GDRIVE}/other.py"},
        }

        async def _all_paths(query, parameters=None):
            return [{"path": p["path"]} for p in backend.nodes.values()]

        backend.run_cypher = _all_paths  # type: ignore[assignment]
        with patched_backend(backend):
            audit = await audit_paths(cfg)

        assert not missing.exists()
        assert audit["total"] == 4
        assert audit["portable"] == 3
        assert audit["absolute"] == 1
        # ${GDRIVE} has no root here, so it cannot be resolved at all.
        assert audit["resolvable"] == 3
        # and gone.py resolves but is not on disk.
        assert audit["present"] == 2
        assert audit["by_root"]["(unconfigured)"] == 1
        assert "project" in audit["configured_roots"]


# ---------------------------------------------------------------------------
# machine identity
# ---------------------------------------------------------------------------


class TestMachineIdentity:
    async def test_id_is_persisted_and_stable(self, isolated_home):
        first = machine.machine_id()
        machine.reset_cache()
        assert machine.machine_id() == first
        stored = json.loads((isolated_home / ".wheeler" / "machine.json").read_text())
        assert stored["id"] == first

    async def test_unwritable_home_still_yields_a_stable_id(self, isolated_home, monkeypatch):
        """A read-only home must cost portability, never the ability to write."""
        monkeypatch.setattr(
            machine.Path, "mkdir", MagicMock(side_effect=OSError("read-only"))
        )
        first = machine.machine_id()
        machine.reset_cache()
        assert first and machine.machine_id() == first

    async def test_corrupt_record_does_not_raise(self, isolated_home):
        wheeler_dir = isolated_home / ".wheeler"
        wheeler_dir.mkdir(parents=True, exist_ok=True)
        (wheeler_dir / "machine.json").write_text("{not json")
        machine.reset_cache()
        assert machine.machine_id()

    async def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv("WHEELER_MACHINE_ID", "pinned-id")
        monkeypatch.setenv("WHEELER_MACHINE_LABEL", "ci-runner")
        assert machine.machine_id() == "pinned-id"
        assert machine.machine_label() == "ci-runner"


class TestReviewRegressions:
    """Bugs found by adversarial review of this change. Each defeated a stated
    guarantee, and three of them did so silently."""

    async def test_update_does_not_restamp_the_origin(self, project):
        """An update must record the WRITER, never the last toucher.

        Restamping defeated the staleness fix from the back door: machine B runs
        ensure_artifact on machine A's file, the hash-changed branch calls
        update_node, the node becomes B's, and A's own later edit is then
        classified `diverged` and never cascades.
        """
        from wheeler.tools.graph_tools import execute_tool

        cfg, root, script = project
        backend = RecordingBackend()
        backend.nodes["S-fromA"] = {
            "__label__": "Script",
            "id": "S-fromA",
            "path": "${PROJECT}/src/analysis.py",
            "hash": "old",
            "origin_machine": "MACHINE-A",
            "origin_host": "lab-workstation",
        }
        with patched_backend(backend):
            await execute_tool(
                "update_node", {"node_id": "S-fromA", "hash": "new"}, cfg
            )

        node = backend.nodes["S-fromA"]
        assert node["origin_machine"] == "MACHINE-A"
        assert node["origin_host"] == "lab-workstation"
        assert node["hash"] == "new"

    async def test_lookup_is_scoped_to_this_project(self, project):
        """Portable paths are unique WITHIN a project, not across a database.

        Two projects on one Community-Edition database both store the literal
        `${PROJECT}/src/analysis.py`, so an unscoped lookup matched the other
        project's node and overwrote its hash.
        """
        from wheeler.graph.provenance import hash_file
        from wheeler.tools.graph_tools import execute_tool

        cfg, root, script = project
        cfg.neo4j.project_tag = "alpha"

        backend = RecordingBackend()
        backend.nodes["S-beta"] = {
            "__label__": "Script",
            "id": "S-beta",
            "path": "${PROJECT}/src/analysis.py",
            "hash": "beta-hash",
            "_wheeler_project": "beta",
        }

        async def scoped(query, parameters=None):
            wanted = (parameters or {}).get("path")
            ptag = (parameters or {}).get("ptag")
            return [
                {"id": nid, "label": p["__label__"], "hash": p.get("hash", "")}
                for nid, p in backend.nodes.items()
                if p.get("path") == wanted
                and ("_wheeler_project" not in query or p.get("_wheeler_project") == ptag)
            ]

        backend.run_cypher = scoped  # type: ignore[assignment]
        with patched_backend(backend):
            result = json.loads(
                await execute_tool(
                    "ensure_artifact", {"path": str(script), "language": "python"}, cfg
                )
            )

        assert result["node_id"] != "S-beta", "matched another project's node"
        assert backend.nodes["S-beta"]["hash"] == "beta-hash", "clobbered beta"
        assert hash_file(script) != "beta-hash"

    async def test_a_bare_filename_match_is_not_upgraded(self, project):
        """A relative-suffix match can name a DIFFERENT file, so writing the
        guess into the node's path would make the mistake permanent."""
        from wheeler.tools.graph_tools import execute_tool

        cfg, root, script = project
        backend = RecordingBackend()
        backend.nodes["S-ambiguous"] = {
            "__label__": "Script",
            "id": "S-ambiguous",
            "path": "analysis.py",       # could be anyone's analysis.py
            "hash": "whatever",
        }
        with patched_backend(backend):
            result = json.loads(
                await execute_tool(
                    "ensure_artifact", {"path": str(script), "language": "python"}, cfg
                )
            )

        assert result.get("path_upgraded") is False
        assert backend.nodes["S-ambiguous"]["path"] == "analysis.py"


class TestYamlBlockEditing:
    """`wheeler db use` edits wheeler.yaml in place; all three of these silently
    produced a wrong file or a bricked project."""

    def _write(self, tmp_path, body: str):
        p = tmp_path / "wheeler.yaml"
        p.write_text(body)
        return p

    def test_a_boolean_looking_database_name_survives(self, tmp_path):
        """`off`, `yes`, `true` and `null` are legal Neo4j names AND YAML
        literals; written bare they parse as bool/None and fail validation."""
        import yaml as _yaml

        from wheeler.cli import _set_yaml_neo4j_keys

        p = self._write(tmp_path, "neo4j:\n  uri: bolt://localhost:7687\n")
        for name in ("off", "yes", "true", "null", "no"):
            _set_yaml_neo4j_keys(p, {"database": name})
            assert _yaml.safe_load(p.read_text())["neo4j"]["database"] == name

    def test_a_column_zero_comment_does_not_split_the_block(self, tmp_path):
        import yaml as _yaml

        from wheeler.cli import _set_yaml_neo4j_keys

        p = self._write(
            tmp_path,
            "neo4j:\n  uri: bolt://x:7687\n# stray comment\n  database: old\nmax_turns: 10\n",
        )
        _set_yaml_neo4j_keys(p, {"database": "new"})
        data = _yaml.safe_load(p.read_text())
        assert data["neo4j"]["database"] == "new"
        assert p.read_text().count("database:") == 1, "duplicate key left behind"
        assert data["max_turns"] == 10

    def test_a_comment_on_the_block_header_is_tolerated(self, tmp_path):
        import yaml as _yaml

        from wheeler.cli import _set_yaml_neo4j_keys

        p = self._write(tmp_path, "neo4j:  # local instance\n  uri: bolt://x:7687\n")
        _set_yaml_neo4j_keys(p, {"database": "d"})
        assert p.read_text().count("neo4j:") == 1, "second neo4j block prepended"
        assert _yaml.safe_load(p.read_text())["neo4j"]["database"] == "d"


class TestDesktopPortAssignment:
    """`wheeler db assign-ports` rewrites config files, so its regressions are
    expensive: a wrong plan makes instances unstartable, and a silent one leaves
    projects pointed at ports nothing serves."""

    def _instances(self, tmp_path, count: int, ports=None):
        from wheeler import desktop

        made = []
        for i in range(count):
            path = tmp_path / f"dbms-{i:08x}-aaaa-bbbb-cccc-dddddddddddd"
            (path / "conf").mkdir(parents=True)
            (path / "conf" / "neo4j.conf").write_text(
                "# Neo4j config\n"
                "#server.bolt.listen_address=:7687\n"
                "#server.http.listen_address=:7474\n"
                "server.https.enabled=false\n"
            )
            made.append(
                desktop.Instance(
                    path=path,
                    ports=dict(ports or {n: b for n, _s, b in desktop.PORT_SETTINGS}),
                    databases=[f"db{i}"],
                )
            )
        return made

    def test_the_first_instance_keeps_the_stock_ports(self, tmp_path):
        """Anything already pointed at 7687 must keep working."""
        from wheeler import desktop

        plan = desktop.assign_ports(self._instances(tmp_path, 3))
        assert plan[0][1]["bolt"] == 7687
        assert plan[0][1]["http"] == 7474

    def test_every_port_is_unique_across_instances(self, tmp_path):
        """All seven, not just bolt: raft and backup are what actually kill a
        second instance, and they are the ones nobody thinks to move."""
        from wheeler import desktop

        plan = desktop.assign_ports(self._instances(tmp_path, 4))
        seen: set[int] = set()
        for _inst, ports in plan:
            assert len(ports) == len(desktop.PORT_SETTINGS)
            for port in ports.values():
                assert port not in seen, f"port {port} assigned twice"
                seen.add(port)

    def test_applying_is_idempotent(self, tmp_path):
        from wheeler import desktop

        made = self._instances(tmp_path, 2)
        plan = desktop.assign_ports(made)
        first = desktop.apply_ports(plan)
        assert any(changes for _i, changes in first)

        # Re-read from disk, then re-plan and re-apply: nothing should move.
        reread = [
            desktop.Instance(
                path=i.path,
                ports=desktop._parse_ports(i.path / "conf" / "neo4j.conf"),
                databases=i.databases,
            )
            for i in made
        ]
        second = desktop.apply_ports(desktop.assign_ports(reread))
        assert all(not changes for _i, changes in second), second

    def test_a_backup_is_taken_once(self, tmp_path):
        from wheeler import desktop

        made = self._instances(tmp_path, 1)
        conf = made[0].path / "conf" / "neo4j.conf"
        original = conf.read_text()
        desktop.apply_ports(desktop.assign_ports(made))

        backup = conf.with_suffix(".conf.wheeler-bak")
        assert backup.exists() and backup.read_text() == original

    def test_conflicts_are_detected_before_and_gone_after(self, tmp_path):
        from wheeler import desktop

        made = self._instances(tmp_path, 3)
        assert desktop.port_conflicts(made), "three identical instances must clash"

        desktop.apply_ports(desktop.assign_ports(made))
        reread = [
            desktop.Instance(
                path=i.path,
                ports=desktop._parse_ports(i.path / "conf" / "neo4j.conf"),
                databases=i.databases,
            )
            for i in made
        ]
        assert desktop.port_conflicts(reread) == []

    def test_stale_bindings_names_a_credential_left_behind(self, tmp_path, monkeypatch):
        """The regression the command itself creates: moving a port orphans any
        project pointed at the old one, and that surfaces later as an
        unreachable graph rather than as anything to do with ports."""
        from wheeler import credentials, desktop

        plan = desktop.assign_ports(self._instances(tmp_path, 2))
        monkeypatch.setattr(credentials, "list_profiles", lambda: ["old", "remote"])
        monkeypatch.setattr(
            credentials,
            "load",
            lambda name=None: {
                "old": {"uri": "bolt://localhost:7999"},        # nothing serves this
                "remote": {"uri": "neo4j+s://x.databases.neo4j.io"},  # not ours
            }.get(name),
        )
        stale = desktop.stale_bindings(plan)
        assert any("old" in s for s in stale)
        assert not any("remote" in s for s in stale), "a cloud URI is not stale"


class TestConnectionDiagnosis:
    """The three local failure modes are indistinguishable from the driver
    (`ServiceUnavailable` for all of them) and have completely different fixes.
    Getting this wrong sends a user to restart the wrong instance."""

    def _inst(self, tmp_path, short: str, bolt: int, dbs: list[str]):
        from wheeler import desktop

        return desktop.Instance(
            path=tmp_path / f"dbms-{short}-aaaa-bbbb-cccc-dddddddddddd",
            ports={n: b for n, _s, b in desktop.PORT_SETTINGS} | {"bolt": bolt},
            databases=dbs,
        )

    def test_a_remote_target_gets_no_local_advice(self):
        from wheeler import desktop

        assert desktop.explain_target("neo4j+s://x.databases.neo4j.io", "neo4j") == []

    def test_local_port_parsing(self):
        from wheeler import desktop

        assert desktop._local_port("bolt://localhost:7697") == 7697
        assert desktop._local_port("neo4j://127.0.0.1:7687") == 7687
        assert desktop._local_port("bolt://localhost") == 7687
        assert desktop._local_port("neo4j+s://x.databases.neo4j.io") is None
        assert desktop._local_port("") is None

    def test_a_stopped_instance_names_itself_and_the_command(self, tmp_path, monkeypatch):
        from wheeler import desktop

        inst = self._inst(tmp_path, "aa11bb22", 7697, ["neo4j", "wheelermasked"])
        monkeypatch.setattr(desktop, "instances", lambda: [inst])
        monkeypatch.setattr(desktop, "status", lambda i: False)

        lines = desktop.explain_target("bolt://localhost:7697", "wheelermasked")
        assert any("NOT running" in ln for ln in lines)
        assert any("wheeler db start aa11bb22" in ln for ln in lines)

    def test_an_unserved_port_lists_what_does_exist(self, tmp_path, monkeypatch):
        """The useful sentence is which ports ARE served, not that this one is not."""
        from wheeler import desktop

        insts = [
            self._inst(tmp_path, "aa11bb22", 7687, ["neo4j"]),
            self._inst(tmp_path, "cc33dd44", 7697, ["wheelermasked"]),
        ]
        monkeypatch.setattr(desktop, "instances", lambda: insts)

        lines = desktop.explain_target("bolt://localhost:7999", "neo4j")
        assert any("7999" in ln for ln in lines)
        assert any("aa11bb22:7687" in ln and "cc33dd44:7697" in ln for ln in lines)

    def test_a_running_instance_missing_the_database_says_so(self, tmp_path, monkeypatch):
        from wheeler import desktop

        inst = self._inst(tmp_path, "aa11bb22", 7687, ["neo4j", "other"])
        monkeypatch.setattr(desktop, "instances", lambda: [inst])
        monkeypatch.setattr(desktop, "status", lambda i: True)

        lines = desktop.explain_target("bolt://localhost:7687", "retina_rgc")
        assert any("no database 'retina_rgc'" in ln for ln in lines)
        assert any("wheeler db create retina_rgc" in ln for ln in lines)

    def test_no_desktop_at_all_does_not_pretend(self, monkeypatch):
        from wheeler import desktop

        monkeypatch.setattr(desktop, "instances", lambda: [])
        lines = desktop.explain_target("bolt://localhost:7687", "neo4j")
        assert any("no Neo4j Desktop instances" in ln for ln in lines)

    async def test_the_tool_error_carries_the_instance_advice(self, project, monkeypatch):
        """`execute_tool` must surface it, not just the driver's message."""
        from wheeler import desktop
        from wheeler.tools.graph_tools import _diagnose_neo4j_error

        inst = self._inst(Path("/tmp"), "aa11bb22", 7697, ["neo4j"])
        monkeypatch.setattr(desktop, "instances", lambda: [inst])
        monkeypatch.setattr(desktop, "status", lambda i: False)

        from neo4j.exceptions import ServiceUnavailable

        out = _diagnose_neo4j_error(
            ServiceUnavailable("nope"), "bolt://localhost:7697", "neo4j"
        )
        assert any("wheeler db start aa11bb22" in line for line in out["fix"])
        # And it must not still be telling people to press Start in Desktop.
        assert not any("click Start" in line for line in out["fix"])
