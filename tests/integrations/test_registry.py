"""Unit tests for the light service-extension registry.

No Neo4j, no live asta. Availability probes are stubbed with a ``python -c``
command that exits 0 or 1, so the subprocess path is exercised without any
external dependency.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from wheeler.config import WheelerConfig
from wheeler.integrations.registry import (
    ServiceContract,
    available_services,
    load_services,
)


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
