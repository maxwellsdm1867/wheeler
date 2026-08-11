"""Tests for wheeler.scaffold module."""

from pathlib import Path

import pytest
import yaml

from wheeler.config import ProjectMeta, ProjectPaths, WheelerConfig
from wheeler.scaffold import (
    create_project_dirs,
    detect_project_dirs,
    scaffold_managed_dirs,
    scaffold_project,
    write_config,
)


class TestDetectProjectDirs:
    def test_detects_existing_dirs(self, tmp_path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "data").mkdir()
        (tmp_path / "figures").mkdir()
        found = detect_project_dirs(tmp_path)
        assert "code" in found
        assert "scripts" in found["code"]
        assert "data" in found
        assert "figures" in found

    def test_detects_multiple_matches(self, tmp_path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "src").mkdir()
        found = detect_project_dirs(tmp_path)
        assert set(found["code"]) == {"scripts", "src"}

    def test_empty_project(self, tmp_path):
        found = detect_project_dirs(tmp_path)
        assert found == {}

    def test_ignores_files(self, tmp_path):
        (tmp_path / "scripts").write_text("not a dir")
        found = detect_project_dirs(tmp_path)
        assert "code" not in found


class TestCreateProjectDirs:
    def test_creates_missing_dirs(self, tmp_path):
        created = create_project_dirs(tmp_path, ["foo", "bar/baz"])
        assert "foo" in created
        assert "bar/baz" in created
        assert (tmp_path / "foo").is_dir()
        assert (tmp_path / "bar" / "baz").is_dir()

    def test_skips_existing(self, tmp_path):
        (tmp_path / "existing").mkdir()
        created = create_project_dirs(tmp_path, ["existing", "new"])
        assert "existing" not in created
        assert "new" in created


class TestScaffoldManagedDirs:
    def test_creates_managed_dirs(self, tmp_path):
        created = scaffold_managed_dirs(tmp_path)
        assert ".plans" in created
        assert ".logs" in created
        assert ".wheeler" in created
        assert (tmp_path / ".plans").is_dir()
        assert (tmp_path / ".logs").is_dir()
        assert (tmp_path / ".wheeler").is_dir()

    def test_idempotent(self, tmp_path):
        scaffold_managed_dirs(tmp_path)
        created = scaffold_managed_dirs(tmp_path)
        assert created == []


class TestWriteConfig:
    def test_writes_yaml(self, tmp_path):
        meta = ProjectMeta(name="My Project", description="Testing scaffolding")
        paths = ProjectPaths(code=["scripts"], data=["data", "/shared/data"])
        config_path = write_config(tmp_path, project=meta, paths=paths)
        assert config_path == tmp_path / "wheeler.yaml"
        assert config_path.exists()

        data = yaml.safe_load(config_path.read_text())
        assert data["project"]["name"] == "My Project"
        assert data["paths"]["code"] == ["scripts"]
        assert data["paths"]["data"] == ["data", "/shared/data"]

    def test_merges_with_existing(self, tmp_path):
        existing = WheelerConfig(max_turns=20)
        paths = ProjectPaths(figures=["figs"])
        write_config(tmp_path, paths=paths, existing_config=existing)

        data = yaml.safe_load((tmp_path / "wheeler.yaml").read_text())
        assert data["max_turns"] == 20
        assert data["paths"]["figures"] == ["figs"]

    def test_excludes_defaults(self, tmp_path):
        write_config(tmp_path, project=ProjectMeta(name="Test"))
        data = yaml.safe_load((tmp_path / "wheeler.yaml").read_text())
        # Default neo4j settings should not appear
        assert "neo4j" not in data


class TestScaffoldProject:
    def test_full_scaffold(self, tmp_path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "data").mkdir()
        result = scaffold_project(tmp_path)
        assert "scripts" in result["detected"].get("code", [])
        assert "data" in result["detected"].get("data", [])
        assert ".plans" in result["created"]
        assert (tmp_path / ".plans").is_dir()


from wheeler.cli import LOCAL_CHOICE  # noqa: E402


class TestInitGraphChoice:
    """`wheeler init` asks which graph a project uses, and records the answer.

    The choice is load-bearing rather than cosmetic: a project on a local
    instance stops working the moment that Neo4j is stopped or swapped and cannot
    be reached from a second computer, while a cloud project carries only a
    PROFILE NAME in wheeler.yaml and keeps working from anywhere.
    """

    def test_cloud_writes_a_profile_binding_and_no_secret(self, tmp_path, monkeypatch):
        import yaml as _yaml

        from wheeler.cli import _choose_graph
        from wheeler.scaffold import write_config

        monkeypatch.setattr(
            "wheeler.credentials.load", lambda slot=None: {"uri": "neo4j+s://x:7687"}
        )
        neo4j = _choose_graph("cloud", "aura-x", None, yes=True)
        assert neo4j.profile == "aura-x"

        write_config(tmp_path, neo4j=neo4j)
        written = _yaml.safe_load((tmp_path / "wheeler.yaml").read_text())
        assert written["neo4j"]["profile"] == "aura-x"
        # The credential stays in the keychain; nothing secret is serialised.
        assert "password" not in written["neo4j"]

    def test_local_writes_no_profile(self, tmp_path, monkeypatch):
        from wheeler import desktop
        from wheeler.cli import _choose_graph

        # Hermetic: without this the assertion depends on which Neo4j instances
        # the developer happens to have installed.
        monkeypatch.setattr(desktop, "instances", lambda: [])
        neo4j = _choose_graph("local", None, None, yes=True)
        assert neo4j.profile == ""

    def test_local_is_the_default_when_instances_exist(self, monkeypatch):
        """Local wins when the machine already has a Neo4j, because several can
        run at once through the CLI, needing no network and no keep-alive."""
        from wheeler import desktop
        from wheeler.cli import _choose_graph

        fake = desktop.Instance(
            path=Path("/tmp/dbms-abc12345"),
            ports={"bolt": 7697},
            databases=["neo4j", "retina_rgc"],
        )
        monkeypatch.setattr(desktop, "instances", lambda: [fake])
        monkeypatch.setattr("wheeler.credentials.load", lambda slot=None: None)

        neo4j = _choose_graph(None, None, None, yes=True)
        assert neo4j.uri == "bolt://localhost:7697"
        assert neo4j.database == "retina_rgc"

    def test_cloud_is_the_default_when_there_is_no_local_neo4j(self, monkeypatch):
        """With nothing installed, sending a user to a local instance they do
        not have is a dead end; the cloud route can be completed from here."""
        from wheeler import desktop
        from wheeler.cli import _choose_graph

        monkeypatch.setattr(desktop, "instances", lambda: [])
        monkeypatch.setattr("wheeler.credentials.load", lambda slot=None: None)
        assert _choose_graph(None, None, None, yes=True).profile == "wheeler-cloud"

    def test_the_choice_never_reads_the_developers_own_machine(self, monkeypatch):
        """Guards hermeticity: this used to enumerate the real Desktop install,
        so the suite's result depended on whose laptop it ran on."""
        from wheeler import desktop
        from wheeler.cli import _choose_graph

        monkeypatch.setattr(desktop, "instances", lambda: [])
        monkeypatch.setattr("wheeler.credentials.load", lambda slot=None: None)
        neo4j = _choose_graph(LOCAL_CHOICE, None, None, yes=True)
        # No instances visible, so the plain local default, not one of mine.
        assert neo4j.uri == "bolt://localhost:7687"
        assert neo4j.profile == ""

    def test_binding_is_written_even_without_a_stored_credential(self, monkeypatch):
        """Half-configured is normal: the file may arrive after init.

        Leaving the binding out would drop the project back to localhost with
        nothing saying so, which is the failure this whole mechanism prevents.
        """
        from wheeler.cli import _choose_graph

        monkeypatch.setattr("wheeler.credentials.load", lambda slot=None: None)
        assert _choose_graph("cloud", "not-stored-yet", None, yes=True).profile == (
            "not-stored-yet"
        )

    def test_an_unknown_choice_is_rejected(self):
        import typer

        from wheeler.cli import _choose_graph

        with pytest.raises(typer.BadParameter):
            _choose_graph("azure", None, None, yes=True)
