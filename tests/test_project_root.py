"""Project-root resolution: explicit env var, marker walk-up, cwd fallback.

The bug these pin down: a server or CLI spawned from a subdirectory used to
bind every path (knowledge/, synthesis/, .wheeler/) to that subdirectory,
because `project_root` defaulted to "." and call sites did a bare
`Path(config.knowledge_path)`.
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from wheeler.config import (
    find_config_file,
    find_project_root,
    load_config,
    project_knowledge_dir,
    project_search_store_dir,
    project_synthesis_dir,
    project_wheeler_dir,
    WheelerConfig,
)

MARKERS = ("wheeler.yaml", ".wheeler")


@pytest.fixture()
def no_root_env(monkeypatch: pytest.MonkeyPatch):
    """Drop WHEELER_PROJECT_ROOT so walk-up/fallback behaviour is under test."""
    monkeypatch.delenv("WHEELER_PROJECT_ROOT", raising=False)


def _assert_no_marker_above(path: Path) -> None:
    """Guard the fallback tests: nothing above `path` may look like a project."""
    polluted = [
        str(parent / marker)
        for parent in path.parents
        for marker in MARKERS
        if (parent / marker).exists()
    ]
    assert not polluted, (
        f"temp dir has project markers in its ancestry, so the walk-up cannot "
        f"be tested from here: {polluted}"
    )


class TestFindProjectRoot:
    def test_env_var_wins(self, tmp_path, monkeypatch):
        """WHEELER_PROJECT_ROOT beats a marker sitting in the cwd itself."""
        explicit = tmp_path / "explicit"
        explicit.mkdir()
        cwd = tmp_path / "elsewhere"
        cwd.mkdir()
        (cwd / "wheeler.yaml").write_text("max_turns: 1\n")

        monkeypatch.chdir(cwd)
        monkeypatch.setenv("WHEELER_PROJECT_ROOT", str(explicit))

        assert find_project_root() == explicit.resolve()

    def test_env_var_is_expanded_and_absolutized(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("WHEELER_PROJECT_ROOT", ".")

        assert find_project_root() == tmp_path.resolve()
        assert find_project_root().is_absolute()

    def test_walk_up_finds_wheeler_yaml_in_parent(self, tmp_path, no_root_env):
        root = tmp_path / "proj"
        deep = root / "analysis" / "scripts"
        deep.mkdir(parents=True)
        (root / "wheeler.yaml").write_text("max_turns: 3\n")

        assert find_project_root(deep) == root.resolve()

    def test_walk_up_finds_dot_wheeler_in_parent(self, tmp_path, no_root_env):
        root = tmp_path / "proj"
        deep = root / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (root / ".wheeler").mkdir()

        assert find_project_root(deep) == root.resolve()

    def test_marker_in_start_dir_itself_is_the_root(self, tmp_path, no_root_env):
        (tmp_path / ".wheeler").mkdir()

        assert find_project_root(tmp_path) == tmp_path.resolve()

    def test_nearest_marker_wins_over_a_higher_one(self, tmp_path, no_root_env):
        outer = tmp_path / "outer"
        inner = outer / "inner"
        deep = inner / "sub"
        deep.mkdir(parents=True)
        (outer / "wheeler.yaml").write_text("max_turns: 1\n")
        (inner / "wheeler.yaml").write_text("max_turns: 2\n")

        assert find_project_root(deep) == inner.resolve()

    def test_falls_back_to_cwd_when_no_marker(self, tmp_path, monkeypatch, no_root_env):
        deep = tmp_path / "nothing" / "here"
        deep.mkdir(parents=True)
        _assert_no_marker_above(deep)

        monkeypatch.chdir(deep)

        assert find_project_root() == deep.resolve()

    def test_defaults_to_cwd_when_start_is_omitted(self, tmp_path, monkeypatch, no_root_env):
        root = tmp_path / "proj"
        deep = root / "sub"
        deep.mkdir(parents=True)
        (root / "wheeler.yaml").write_text("max_turns: 3\n")

        monkeypatch.chdir(deep)

        assert find_project_root() == root.resolve()


class TestFindConfigFile:
    def test_finds_yaml_from_a_subdirectory(self, tmp_path, no_root_env):
        root = tmp_path / "proj"
        deep = root / "sub" / "deeper"
        deep.mkdir(parents=True)
        config_path = root / "wheeler.yaml"
        config_path.write_text("max_turns: 7\n")

        assert find_config_file(deep) == config_path.resolve()

    def test_returns_none_when_only_dot_wheeler_marks_the_root(self, tmp_path, no_root_env):
        root = tmp_path / "proj"
        deep = root / "sub"
        deep.mkdir(parents=True)
        (root / ".wheeler").mkdir()

        assert find_config_file(deep) is None

    def test_returns_none_when_nothing_is_found(self, tmp_path, no_root_env):
        deep = tmp_path / "bare"
        deep.mkdir()
        _assert_no_marker_above(deep)

        assert find_config_file(deep) is None


class TestLoadConfigWalksUp:
    def test_load_config_finds_parent_yaml_from_subdirectory(
        self, tmp_path, monkeypatch, no_root_env
    ):
        root = tmp_path / "proj"
        deep = root / "analysis"
        deep.mkdir(parents=True)
        (root / "wheeler.yaml").write_text(yaml.dump({"max_turns": 77}))

        monkeypatch.chdir(deep)
        config = load_config()

        assert config.max_turns == 77
        assert config.resolved_project_root == root.resolve()

    def test_load_config_uses_defaults_when_no_project_is_found(
        self, tmp_path, monkeypatch, no_root_env
    ):
        deep = tmp_path / "bare"
        deep.mkdir()
        _assert_no_marker_above(deep)

        monkeypatch.chdir(deep)
        config = load_config()

        assert config.max_turns == WheelerConfig().max_turns
        assert config.resolved_project_root == deep.resolve()

    def test_env_project_root_redirects_config_discovery(self, tmp_path, monkeypatch):
        """WHEELER_PROJECT_ROOT points load_config() at another tree's yaml."""
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "wheeler.yaml").write_text(yaml.dump({"max_turns": 99}))
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        (cwd / "wheeler.yaml").write_text(yaml.dump({"max_turns": 11}))

        monkeypatch.chdir(cwd)
        monkeypatch.setenv("WHEELER_PROJECT_ROOT", str(elsewhere))

        assert load_config().max_turns == 99


class TestResolvedPaths:
    def test_resolved_paths_hang_off_the_discovered_root(
        self, tmp_path, monkeypatch, no_root_env
    ):
        root = tmp_path / "proj"
        deep = root / "sub"
        deep.mkdir(parents=True)
        (root / "wheeler.yaml").write_text("max_turns: 3\n")

        monkeypatch.chdir(deep)
        config = load_config()

        assert config.resolved_knowledge_path == root.resolve() / "knowledge"
        assert config.resolved_synthesis_path == root.resolve() / "synthesis"
        assert config.resolved_wheeler_dir == root.resolve() / ".wheeler"
        assert config.resolved_search_store_path == root.resolve() / ".wheeler" / "embeddings"

    def test_resolved_paths_are_absolute(self, tmp_path, monkeypatch, no_root_env):
        monkeypatch.chdir(tmp_path)
        config = WheelerConfig()

        for path in (
            config.resolved_project_root,
            config.resolved_knowledge_path,
            config.resolved_synthesis_path,
            config.resolved_wheeler_dir,
            config.resolved_search_store_path,
        ):
            assert path.is_absolute(), path

    def test_absolute_relative_field_passes_through(self, tmp_path, no_root_env):
        """Call sites that pin an absolute knowledge_path keep working."""
        absolute = tmp_path / "somewhere" / "knowledge"
        config = WheelerConfig(knowledge_path=str(absolute))

        assert config.resolved_knowledge_path == absolute

    def test_explicit_project_root_field_is_honoured(self, tmp_path, monkeypatch, no_root_env):
        """A pinned project_root beats the walk-up but not the env var."""
        pinned = tmp_path / "pinned"
        pinned.mkdir()
        marked = tmp_path / "marked"
        marked.mkdir()
        (marked / "wheeler.yaml").write_text("max_turns: 1\n")

        monkeypatch.chdir(marked)
        config = WheelerConfig(project_root=str(pinned))

        assert config.resolved_project_root == pinned.resolve()
        assert config.resolved_knowledge_path == pinned.resolve() / "knowledge"

    def test_env_var_beats_explicit_project_root_field(self, tmp_path, monkeypatch):
        pinned = tmp_path / "pinned"
        pinned.mkdir()
        from_env = tmp_path / "from-env"
        from_env.mkdir()

        monkeypatch.setenv("WHEELER_PROJECT_ROOT", str(from_env))
        config = WheelerConfig(project_root=str(pinned))

        assert config.resolved_project_root == from_env.resolve()

    def test_dot_project_root_still_round_trips_through_yaml(self, no_root_env):
        """The serialised field stays relative: only the resolved views absolutize."""
        assert WheelerConfig().project_root == "."
        assert WheelerConfig().model_dump()["project_root"] == "."


class TestProjectDirHelpers:
    """The helpers call sites use, including their duck-typed fallback.

    Several modules are handed partial config stand-ins by tests (MagicMock in
    test_merge and test_synthesis), so the helpers must degrade to the raw
    relative field instead of raising or inventing a root.
    """

    def test_helpers_resolve_a_real_config_against_the_project_root(
        self, tmp_path, monkeypatch, no_root_env
    ):
        root = tmp_path / "proj"
        deep = root / "sub"
        deep.mkdir(parents=True)
        (root / "wheeler.yaml").write_text("max_turns: 3\n")

        monkeypatch.chdir(deep)
        config = load_config()

        assert project_knowledge_dir(config) == root.resolve() / "knowledge"
        assert project_synthesis_dir(config) == root.resolve() / "synthesis"
        assert project_wheeler_dir(config) == root.resolve() / ".wheeler"
        assert (
            project_search_store_dir(config)
            == root.resolve() / ".wheeler" / "embeddings"
        )

    def test_duck_typed_config_falls_back_to_the_raw_field(self, tmp_path, no_root_env):
        stand_in = SimpleNamespace(
            knowledge_path=str(tmp_path / "k"),
            synthesis_path=str(tmp_path / "s"),
            search=SimpleNamespace(store_path=str(tmp_path / "e")),
        )

        assert project_knowledge_dir(stand_in) == tmp_path / "k"
        assert project_synthesis_dir(stand_in) == tmp_path / "s"
        assert project_search_store_dir(stand_in) == tmp_path / "e"

    def test_duck_typed_config_with_relative_fields_keeps_old_behaviour(self, no_root_env):
        stand_in = SimpleNamespace(knowledge_path="knowledge", synthesis_path="synthesis")

        assert project_knowledge_dir(stand_in) == Path("knowledge")
        assert project_synthesis_dir(stand_in) == Path("synthesis")

    def test_config_without_the_fields_at_all_uses_the_conventional_names(self, no_root_env):
        assert project_knowledge_dir(object()) == Path("knowledge")
        assert project_synthesis_dir(object()) == Path("synthesis")

    def test_absolute_field_passes_through(self, tmp_path, no_root_env):
        config = WheelerConfig(knowledge_path=str(tmp_path / "abs" / "knowledge"))

        assert project_knowledge_dir(config) == tmp_path / "abs" / "knowledge"

    def test_wheeler_dir_without_a_config_uses_the_discovered_root(
        self, tmp_path, monkeypatch, no_root_env
    ):
        root = tmp_path / "proj"
        deep = root / "sub"
        deep.mkdir(parents=True)
        (root / ".wheeler").mkdir()

        monkeypatch.chdir(deep)

        assert project_wheeler_dir() == root.resolve() / ".wheeler"

    def test_search_store_falls_back_under_the_project_wheeler_dir(
        self, tmp_path, monkeypatch, no_root_env
    ):
        """No search config at all: still land under the project's .wheeler/."""
        (tmp_path / "wheeler.yaml").write_text("max_turns: 3\n")
        monkeypatch.chdir(tmp_path)

        assert (
            project_search_store_dir(object())
            == tmp_path.resolve() / ".wheeler" / "embeddings"
        )


class TestSearchFromSubdirectory:
    """Semantic search read path: the failure mode here is silence.

    `retrieval.py` looked for `knowledge/` relative to the cwd, so a server
    spawned in a subdirectory found no JSON files and returned an empty result
    set. That surfaces as "search returns nothing", not as a path error, which
    is why it is the hardest site in this sweep to diagnose from a bug report.

    `mode="temporal"` runs the one channel that reads only files, so this is a
    real end-to-end `multi_search` with no backend involved.
    """

    def _project_with_one_finding(self, tmp_path: Path) -> tuple[Path, Path, str]:
        from wheeler.knowledge.store import write_node
        from wheeler.models import FindingModel

        root = tmp_path / "project"
        nested = root / "analysis" / "scripts"
        nested.mkdir(parents=True)
        (root / "wheeler.yaml").write_text("knowledge_path: knowledge\n")

        model = FindingModel(
            id="F-abcd1234",
            description="Rod bipolar gain scales with background luminance",
            confidence=0.8,
        )
        write_node(root / "knowledge", model)
        return root, nested, model.id

    async def test_multi_search_from_subdirectory_finds_project_knowledge(
        self, tmp_path, monkeypatch, no_root_env
    ):
        from wheeler.search.retrieval import multi_search

        root, nested, node_id = self._project_with_one_finding(tmp_path)
        monkeypatch.chdir(nested)
        config = load_config()

        results = await multi_search("gain", config, limit=5, mode="temporal")

        assert [r["id"] for r in results] == [node_id], (
            "search from a subdirectory found nothing: knowledge/ was resolved "
            "against the cwd instead of the project root"
        )
        # `_enrich_node` falls back to a bare {"id": ...} stub when it cannot
        # read the JSON file, so the description proves the enrichment site
        # resolved too, not just the channel that produced the id.
        assert "luminance" in results[0]["description"]

    async def test_temporal_channel_from_subdirectory(
        self, tmp_path, monkeypatch, no_root_env
    ):
        from wheeler.search.retrieval import _temporal_channel

        root, nested, node_id = self._project_with_one_finding(tmp_path)
        monkeypatch.chdir(nested)
        config = load_config()

        assert await _temporal_channel(config, 10, "Finding") == [node_id]

    async def test_search_still_works_from_the_project_root(
        self, tmp_path, monkeypatch, no_root_env
    ):
        """The cwd-is-the-root case must keep working: that one was never broken."""
        from wheeler.search.retrieval import multi_search

        root, _nested, node_id = self._project_with_one_finding(tmp_path)
        monkeypatch.chdir(root)
        config = load_config()

        results = await multi_search("gain", config, limit=5, mode="temporal")

        assert [r["id"] for r in results] == [node_id]


class TestBackupAnchorsOnProjectRoot:
    """The archive's anchor decides both what is packed and what counts as external.

    `create_backup` derived `project_root` from `Path(config.project_root)`,
    which collapses the default "." to the cwd. Run from a subdirectory it
    packed the wrong tree and relativized against the wrong root, so files
    genuinely inside the project were recorded as `external_references`.
    """

    def _project(self, tmp_path: Path) -> tuple[Path, Path]:
        root = tmp_path / "project"
        nested = root / "analysis" / "scripts"
        nested.mkdir(parents=True)
        for name in ("knowledge", "synthesis", ".wheeler"):
            (root / name).mkdir()
        (root / "knowledge" / "F-test1234.json").write_text(
            json.dumps({"id": "F-test1234", "type": "Finding", "description": "x"})
        )
        (root / "synthesis" / "F-test1234.md").write_text("# F-test1234\n\nbody\n")
        (root / "wheeler.yaml").write_text("knowledge_path: knowledge\n")
        return root, nested

    async def test_backup_from_subdirectory_packs_the_project_root(
        self, tmp_path, monkeypatch, no_root_env
    ):
        from unittest.mock import AsyncMock, patch

        from wheeler.backup import create_backup

        root, nested = self._project(tmp_path)
        monkeypatch.chdir(nested)
        config = load_config()

        class _FakeBackend:
            async def initialize(self):
                return None

            async def close(self):
                return None

            async def run_cypher(self, query, params=None):
                return []

        with patch(
            "wheeler.backup.get_backend", return_value=_FakeBackend()
        ), patch(
            "wheeler.backup._record_backup_execution", new_callable=AsyncMock
        ):
            archive = await create_backup(
                config, destination=tmp_path / "out", scope="graph-only"
            )

        with tarfile.open(archive, "r:gz") as tar:
            names = tar.getnames()
            manifest = json.loads(tar.extractfile("manifest.json").read())

        assert manifest["project_root_at_pack"] == str(root.resolve()), (
            "the archive anchored on the cwd instead of the project root"
        )
        assert any(n.endswith("knowledge/F-test1234.json") for n in names), (
            f"knowledge file missing from the archive; got {names}"
        )
        assert any(n.endswith("synthesis/F-test1234.md") for n in names)


class TestMcpSharedUsesResolvedRoot:
    def test_request_logger_dir_is_absolute(self):
        """The MCP servers must not bind their request log to the spawn cwd."""
        from wheeler.mcp_shared import _request_logger

        assert _request_logger._log_dir.is_absolute()
        assert _request_logger._log_dir.name == ".wheeler"
