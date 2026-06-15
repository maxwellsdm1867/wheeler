"""Unit tests for the light service-extension registry.

No Neo4j, no live asta. Availability probes are stubbed with a ``python -c``
command that exits 0 or 1, so the subprocess path is exercised without any
external dependency.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wheeler.config import WheelerConfig
from wheeler.integrations.registry import (
    ServiceContract,
    available_services,
    catalog_services,
    load_services,
)
from wheeler.integrations.services_cli import services_app


def _config_for(project_root: Path) -> WheelerConfig:
    return WheelerConfig(project_root=str(project_root))


def _exit_zero() -> str:
    """A probe command that always exits 0 (available)."""
    return f"{sys.executable} -c \"import sys; sys.exit(0)\""


def _exit_one() -> str:
    """A probe command that always exits 1 (unavailable)."""
    return f"{sys.executable} -c \"import sys; sys.exit(1)\""


def _write_user_manifest(project_root: Path, body: str) -> Path:
    wheeler_dir = project_root / ".wheeler"
    wheeler_dir.mkdir(parents=True, exist_ok=True)
    path = wheeler_dir / "services.yaml"
    path.write_text(textwrap.dedent(body))
    return path


# ---------------------------------------------------------------------------
# load_services: default manifest
# ---------------------------------------------------------------------------


class TestLoadDefault:
    def test_default_manifest_parses_into_contracts(self) -> None:
        # No user override present -> bundled default is used.
        contracts = load_services(None)
        assert contracts, "default manifest should yield contracts"
        assert all(isinstance(c, ServiceContract) for c in contracts)

    def test_default_has_the_three_asta_services_plus_a_local(self) -> None:
        contracts = load_services(None)
        by_id = {c.id: c for c in contracts}

        assert {"paper-finder", "theorizer", "semantic-scholar"} <= set(by_id)

        # The three live Asta services are shell-out + asta provider.
        for sid in ("paper-finder", "theorizer", "semantic-scholar"):
            assert by_id[sid].provider == "asta"
            assert by_id[sid].kind == "shell-out"

        # Acts and cost hints are wired correctly.
        assert by_id["paper-finder"].act == "/wh:asta-lit"
        assert by_id["semantic-scholar"].act == "/wh:asta-scholar"
        assert by_id["theorizer"].act == "/wh:asta-theorize"
        assert "expensive" in by_id["theorizer"].cost.lower()
        assert "$7" in by_id["theorizer"].cost

        # At least one local-kind example ships in the default.
        local = [c for c in contracts if c.kind == "local"]
        assert local, "default manifest should include a local example"

    def test_contract_has_all_required_fields(self) -> None:
        contracts = load_services(None)
        c = next(c for c in contracts if c.id == "paper-finder")
        assert c.id
        assert c.provider
        assert c.name
        assert c.description
        assert c.kind in ("shell-out", "local")
        assert c.act
        assert c.cost
        assert c.available
        assert c.when

    def test_default_used_when_user_file_absent(self, tmp_path: Path) -> None:
        # Config points at a project with no .wheeler/services.yaml.
        config = _config_for(tmp_path)
        contracts = load_services(config)
        ids = {c.id for c in contracts}
        # Falls back to the bundled default.
        assert "paper-finder" in ids


# ---------------------------------------------------------------------------
# load_services: user override
# ---------------------------------------------------------------------------


class TestUserOverride:
    def test_user_manifest_is_preferred_over_default(self, tmp_path: Path) -> None:
        _write_user_manifest(
            tmp_path,
            """
            services:
              - id: my-custom-tool
                provider: local
                name: Custom Tool
                description: a project-specific local tool
                kind: local
                act: /wh:custom
                cost: "free"
                available: "true"
                when: "anytime"
            """,
        )
        config = _config_for(tmp_path)
        contracts = load_services(config)
        ids = {c.id for c in contracts}

        # The user file wins; the default asta entries are NOT merged in.
        assert ids == {"my-custom-tool"}
        assert "paper-finder" not in ids

    def test_empty_user_manifest_yields_no_services(self, tmp_path: Path) -> None:
        # The user file ships empty in some setups; that means "no services",
        # not "fall back to default".
        _write_user_manifest(tmp_path, "services: []\n")
        config = _config_for(tmp_path)
        assert load_services(config) == []


# ---------------------------------------------------------------------------
# load_services: malformed / defensive
# ---------------------------------------------------------------------------


class TestMalformed:
    def test_malformed_entries_are_skipped_not_raised(self, tmp_path: Path) -> None:
        _write_user_manifest(
            tmp_path,
            """
            services:
              - id: good
                provider: local
                name: Good
                description: a valid entry
                kind: local
                act: /wh:good
                cost: "free"
                available: "true"
                when: "anytime"
              - id: missing-fields
                provider: local
              - id: bad-kind
                provider: local
                name: Bad Kind
                description: unknown kind value
                kind: not-a-kind
                act: /wh:bad
                cost: "free"
                available: "true"
                when: "anytime"
              - not-a-mapping
            """,
        )
        config = _config_for(tmp_path)
        contracts = load_services(config)
        ids = {c.id for c in contracts}

        # Only the well-formed entry survives; nothing raised.
        assert ids == {"good"}

    def test_garbage_yaml_falls_back_to_empty(self, tmp_path: Path) -> None:
        _write_user_manifest(tmp_path, "::: not valid yaml :::\n[\n")
        config = _config_for(tmp_path)
        # Defensive: malformed file -> empty list, no exception.
        assert load_services(config) == []

    def test_services_key_not_a_list(self, tmp_path: Path) -> None:
        _write_user_manifest(tmp_path, "services:\n  id: oops\n")
        config = _config_for(tmp_path)
        assert load_services(config) == []


# ---------------------------------------------------------------------------
# available_services: stubbed probes
# ---------------------------------------------------------------------------


class TestAvailability:
    def test_filters_out_failing_probe(self, tmp_path: Path) -> None:
        _write_user_manifest(
            tmp_path,
            f"""
            services:
              - id: up
                provider: local
                name: Up
                description: probe exits 0
                kind: local
                act: /wh:up
                cost: "free"
                available: {_exit_zero()!r}
                when: "anytime"
              - id: down
                provider: local
                name: Down
                description: probe exits 1
                kind: local
                act: /wh:down
                cost: "free"
                available: {_exit_one()!r}
                when: "anytime"
            """,
        )
        config = _config_for(tmp_path)

        # Both load; only the one whose probe exits 0 is available.
        assert {c.id for c in load_services(config)} == {"up", "down"}
        assert {c.id for c in available_services(config)} == {"up"}

    def test_missing_binary_is_unavailable(self, tmp_path: Path) -> None:
        _write_user_manifest(
            tmp_path,
            """
            services:
              - id: ghost
                provider: local
                name: Ghost
                description: probe binary does not exist
                kind: local
                act: /wh:ghost
                cost: "free"
                available: "this-binary-does-not-exist-wheeler-test"
                when: "anytime"
            """,
        )
        config = _config_for(tmp_path)
        assert available_services(config) == []

    def test_all_probes_passing_returns_all(self, tmp_path: Path) -> None:
        _write_user_manifest(
            tmp_path,
            f"""
            services:
              - id: a
                provider: local
                name: A
                description: ok
                kind: local
                act: /wh:a
                cost: "free"
                available: {_exit_zero()!r}
                when: "anytime"
              - id: b
                provider: local
                name: B
                description: ok
                kind: local
                act: /wh:b
                cost: "free"
                available: {_exit_zero()!r}
                when: "anytime"
            """,
        )
        config = _config_for(tmp_path)
        assert {c.id for c in available_services(config)} == {"a", "b"}


# ---------------------------------------------------------------------------
# catalog_services + the enabled-services FOLDER (the ENABLE/DISABLE layer)
# ---------------------------------------------------------------------------


def _services_dir(project_root: Path) -> Path:
    return project_root / ".wheeler" / "services"


def _write_enabled_file(project_root: Path, service_id: str, body: str) -> Path:
    folder = _services_dir(project_root)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{service_id}.yaml"
    path.write_text(textwrap.dedent(body))
    return path


class TestCatalog:
    def test_catalog_is_the_bundled_default(self) -> None:
        # catalog_services is always the bundled default regardless of config.
        catalog = catalog_services(None)
        ids = {c.id for c in catalog}
        assert {"paper-finder", "theorizer", "semantic-scholar"} <= ids

    def test_catalog_ignores_enabled_folder(self, tmp_path: Path) -> None:
        # Even when a curated folder exists, the catalog stays the full default.
        _write_enabled_file(
            tmp_path,
            "paper-finder",
            """
            id: paper-finder
            provider: asta
            name: Paper Finder
            description: only this one enabled
            kind: shell-out
            act: /wh:asta-lit
            cost: "cheap"
            available: "asta auth status"
            when: "broad literature discovery"
            """,
        )
        config = _config_for(tmp_path)
        catalog = catalog_services(config)
        # Catalog still has everything; only load_services is filtered.
        assert {"paper-finder", "theorizer", "semantic-scholar"} <= {
            c.id for c in catalog
        }


class TestEnabledFolder:
    def test_folder_absent_falls_back_to_catalog(self, tmp_path: Path) -> None:
        # No .wheeler/services/ folder -> backward-compat: all defaults enabled.
        config = _config_for(tmp_path)
        ids = {c.id for c in load_services(config)}
        assert {"paper-finder", "theorizer", "semantic-scholar"} <= ids

    def test_folder_is_source_of_truth(self, tmp_path: Path) -> None:
        # A folder with one file -> only that contract is enabled.
        _write_enabled_file(
            tmp_path,
            "paper-finder",
            """
            id: paper-finder
            provider: asta
            name: Paper Finder
            description: enabled
            kind: shell-out
            act: /wh:asta-lit
            cost: "cheap"
            available: "asta auth status"
            when: "broad literature discovery"
            """,
        )
        config = _config_for(tmp_path)
        ids = {c.id for c in load_services(config)}
        assert ids == {"paper-finder"}

    def test_empty_folder_yields_no_enabled_services(self, tmp_path: Path) -> None:
        # An existing-but-empty folder means "nothing enabled", not "fall back".
        _services_dir(tmp_path).mkdir(parents=True)
        config = _config_for(tmp_path)
        assert load_services(config) == []

    def test_folder_accepts_services_wrapper_shape(self, tmp_path: Path) -> None:
        # A file may also use the catalog-style ``services:`` list wrapper.
        _write_enabled_file(
            tmp_path,
            "theorizer",
            """
            services:
              - id: theorizer
                provider: asta
                name: Theorizer
                description: enabled via wrapper
                kind: shell-out
                act: /wh:asta-theorize
                cost: "expensive"
                available: "asta auth status"
                when: "theory generation"
            """,
        )
        config = _config_for(tmp_path)
        assert {c.id for c in load_services(config)} == {"theorizer"}

    def test_folder_wins_over_legacy_single_file(self, tmp_path: Path) -> None:
        # When BOTH the folder and the legacy services.yaml exist, folder wins.
        _write_user_manifest(
            tmp_path,
            """
            services:
              - id: legacy-only
                provider: local
                name: Legacy
                description: from the single-file override
                kind: local
                act: /wh:legacy
                cost: "free"
                available: "true"
                when: "anytime"
            """,
        )
        _write_enabled_file(
            tmp_path,
            "paper-finder",
            """
            id: paper-finder
            provider: asta
            name: Paper Finder
            description: enabled via folder
            kind: shell-out
            act: /wh:asta-lit
            cost: "cheap"
            available: "asta auth status"
            when: "broad literature discovery"
            """,
        )
        config = _config_for(tmp_path)
        assert {c.id for c in load_services(config)} == {"paper-finder"}

    def test_garbage_file_in_folder_is_skipped(self, tmp_path: Path) -> None:
        _write_enabled_file(tmp_path, "broken", "::: not valid yaml :::\n[\n")
        _write_enabled_file(
            tmp_path,
            "paper-finder",
            """
            id: paper-finder
            provider: asta
            name: Paper Finder
            description: enabled
            kind: shell-out
            act: /wh:asta-lit
            cost: "cheap"
            available: "asta auth status"
            when: "broad literature discovery"
            """,
        )
        config = _config_for(tmp_path)
        # The garbage file is skipped, not raised; the good one survives.
        assert {c.id for c in load_services(config)} == {"paper-finder"}

    def test_missing_required_field_in_folder_is_skipped(self, tmp_path: Path) -> None:
        _write_enabled_file(
            tmp_path,
            "incomplete",
            """
            id: incomplete
            provider: local
            """,
        )
        config = _config_for(tmp_path)
        assert load_services(config) == []


# ---------------------------------------------------------------------------
# `wheeler services` CLI: enable / disable / list (seed-on-first-curate)
# ---------------------------------------------------------------------------


@pytest.fixture()
def _cli_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run the CLI inside tmp_path so load_config() resolves project_root there.

    project_root defaults to "." (cwd) and there is no wheeler.yaml, so chdir
    into tmp_path makes .wheeler/services/ land under the temp project.
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    return runner, tmp_path


class TestServicesCli:
    def test_enable_seeds_then_creates_file_and_loads(self, _cli_project) -> None:
        runner, root = _cli_project
        # paper-finder is already a default; enable a different one to prove the
        # file is written and seed kept the others.
        result = runner.invoke(services_app, ["enable", "paper-finder"])
        assert result.exit_code == 0, result.output

        folder = _services_dir(root)
        assert folder.is_dir(), "folder should be seeded on first curate"
        assert (folder / "paper-finder.yaml").is_file()
        # Seed-on-first-curate keeps the OTHER defaults enabled too.
        assert (folder / "theorizer.yaml").is_file()
        assert (folder / "semantic-scholar.yaml").is_file()

        config = _config_for(root)
        ids = {c.id for c in load_services(config)}
        assert "paper-finder" in ids
        # All defaults still enabled after first enable (seed preserved them).
        assert {"theorizer", "semantic-scholar"} <= ids

    def test_disable_seeds_then_removes_file_and_excludes(self, _cli_project) -> None:
        runner, root = _cli_project
        result = runner.invoke(services_app, ["disable", "theorizer"])
        assert result.exit_code == 0, result.output

        folder = _services_dir(root)
        assert folder.is_dir(), "folder should be seeded on first curate"
        # Disable from the default state: theorizer file is gone, others remain.
        assert not (folder / "theorizer.yaml").exists()
        assert (folder / "paper-finder.yaml").is_file()
        assert (folder / "semantic-scholar.yaml").is_file()

        config = _config_for(root)
        ids = {c.id for c in load_services(config)}
        assert "theorizer" not in ids
        # The other defaults stay enabled (seed-on-first-curate decision).
        assert {"paper-finder", "semantic-scholar"} <= ids

    def test_enable_then_disable_roundtrip(self, _cli_project) -> None:
        runner, root = _cli_project
        runner.invoke(services_app, ["disable", "paper-finder"])
        config = _config_for(root)
        assert "paper-finder" not in {c.id for c in load_services(config)}

        # Re-enable: the file reappears and load_services includes it again.
        result = runner.invoke(services_app, ["enable", "paper-finder"])
        assert result.exit_code == 0, result.output
        assert (_services_dir(root) / "paper-finder.yaml").is_file()
        assert "paper-finder" in {c.id for c in load_services(config)}

    def test_enable_unknown_id_errors(self, _cli_project) -> None:
        runner, root = _cli_project
        result = runner.invoke(services_app, ["enable", "does-not-exist"])
        assert result.exit_code == 1
        # No folder created on a rejected enable (validation happens first).
        assert not _services_dir(root).exists()

    def test_disable_unknown_id_errors_without_side_effects(self, _cli_project) -> None:
        # A typo'd / unknown id must NOT silently materialise the whole folder.
        # It is validated against the catalog first (mirroring enable) and
        # rejected with exit 1 before any seeding.
        runner, root = _cli_project
        result = runner.invoke(services_app, ["disable", "does-not-exist"])
        assert result.exit_code == 1, result.output
        # No folder created on a rejected disable (validation happens first).
        assert not _services_dir(root).exists()
        # Defaults remain enabled via fallback (the project is untouched).
        config = _config_for(root)
        ids = {c.id for c in load_services(config)}
        assert {"paper-finder", "theorizer", "semantic-scholar"} <= ids

    def test_disable_known_id_twice_is_a_clean_noop(self, _cli_project) -> None:
        # Disabling a real catalog id that is already disabled is a friendly
        # exit-0 no-op (it must NOT be confused with the unknown-id error).
        runner, root = _cli_project
        first = runner.invoke(services_app, ["disable", "theorizer"])
        assert first.exit_code == 0, first.output
        second = runner.invoke(services_app, ["disable", "theorizer"])
        assert second.exit_code == 0, second.output
        assert "already disabled" in second.output
        config = _config_for(root)
        ids = {c.id for c in load_services(config)}
        assert "theorizer" not in ids
        assert {"paper-finder", "semantic-scholar"} <= ids

    def test_disable_handles_hand_added_non_catalog_id(self, _cli_project) -> None:
        # A contract added by hand beyond the catalog can still be disabled,
        # because validation also accepts an already-enabled file on disk.
        runner, root = _cli_project
        _write_enabled_file(
            root,
            "my-custom-tool",
            """
            id: my-custom-tool
            provider: local
            name: Custom Tool
            description: a hand-added contract beyond the catalog
            kind: local
            act: /wh:custom
            cost: "free"
            available: "true"
            when: "anytime"
            """,
        )
        config = _config_for(root)
        assert "my-custom-tool" in {c.id for c in load_services(config)}
        result = runner.invoke(services_app, ["disable", "my-custom-tool"])
        assert result.exit_code == 0, result.output
        assert not (_services_dir(root) / "my-custom-tool.yaml").exists()
        assert "my-custom-tool" not in {c.id for c in load_services(config)}

    def test_list_shows_loaded_and_available(self, _cli_project) -> None:
        runner, root = _cli_project
        # Curate: enable only paper-finder by disabling the rest.
        runner.invoke(services_app, ["disable", "theorizer"])
        runner.invoke(services_app, ["disable", "semantic-scholar"])
        runner.invoke(services_app, ["disable", "graph-status"])

        result = runner.invoke(services_app, ["list"])
        assert result.exit_code == 0, result.output
        out = result.output
        # Loaded section shows paper-finder; available section shows a disabled one.
        assert "paper-finder" in out
        assert "Loaded services" in out
        assert "Available to enable" in out
        assert "theorizer" in out
