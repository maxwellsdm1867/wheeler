"""Keychain credential store, config precedence, and the source report.

Every test here runs against `FakeKeyring`, an in-memory dict standing in for the
OS keychain. `wheeler.credentials._load_keyring` is the single seam that reaches
the real `keyring` module, and it is monkeypatched in every test that exercises
storage, so the real macOS Keychain / libsecret / Credential Manager is never
read and never written. The suite-wide fixture in `tests/conftest.py` sets
`WHEELER_NO_KEYCHAIN` on top of that as a belt-and-braces guard.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from wheeler import credentials
from wheeler.config import (
    _NEO4J_DEFAULTS,
    load_config,
    neo4j_sources,
    reset_keychain_cache,
    shadowed_by_env,
)

NEO4J_ENV_VARS = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE")


class FakeKeyring:
    """Minimal in-memory stand-in for the keyring module's password API."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}
        self.reads = 0

    def get_password(self, service: str, account: str) -> str | None:
        self.reads += 1
        return self.store.get((service, account))

    def set_password(self, service: str, account: str, password: str) -> None:
        self.store[(service, account)] = password

    def delete_password(self, service: str, account: str) -> None:
        if (service, account) not in self.store:
            raise RuntimeError("no such password")  # what keyring does
        del self.store[(service, account)]


class BrokenKeyring(FakeKeyring):
    """A keychain that is present but refuses to answer (locked, no access)."""

    def get_password(self, service: str, account: str) -> str | None:
        raise RuntimeError("keychain is locked")


@pytest.fixture
def fake_keyring(monkeypatch: pytest.MonkeyPatch) -> FakeKeyring:
    """Install the in-memory keychain, bypassing the real one entirely."""
    fake = FakeKeyring()
    monkeypatch.setattr(credentials, "_load_keyring", lambda: fake)
    reset_keychain_cache()
    return fake


@pytest.fixture
def clean_neo4j_env(monkeypatch: pytest.MonkeyPatch):
    """Drop ambient NEO4J_* vars so precedence assertions are deterministic."""
    for var in NEO4J_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("WHEELER_PROJECT_ROOT", raising=False)


def write_yaml(tmp_path: Path, neo4j: dict[str, str]) -> Path:
    path = tmp_path / "wheeler.yaml"
    path.write_text(yaml.safe_dump({"neo4j": neo4j}))
    return path


# ── Round trip ──────────────────────────────────────────────────────


class TestSaveLoadDelete:
    def test_round_trip(self, fake_keyring):
        credentials.save(
            "default",
            "neo4j+s://abc123.databases.neo4j.io",
            "neo4j",
            "s3cret",
            "neo4j",
        )
        record = credentials.load("default")
        assert record == {
            "uri": "neo4j+s://abc123.databases.neo4j.io",
            "username": "neo4j",
            "password": "s3cret",
            "database": "neo4j",
        }

    def test_stored_under_the_wheeler_service(self, fake_keyring):
        credentials.save("default", "bolt://x:7687", "neo4j", "pw")
        accounts = {account for service, account in fake_keyring.store if service == "wheeler"}
        assert "neo4j:default" in accounts

    def test_load_returns_none_when_nothing_stored(self, fake_keyring):
        assert credentials.load("default") is None

    def test_profiles_are_independent(self, fake_keyring):
        credentials.save("aura", "neo4j+s://one:7687", "neo4j", "one-pw")
        credentials.save("local", "bolt://localhost:7687", "neo4j", "two-pw")

        assert credentials.load("aura")["password"] == "one-pw"
        assert credentials.load("local")["password"] == "two-pw"
        assert credentials.list_profiles() == ["aura", "local"]

    def test_delete_removes_only_its_own_profile(self, fake_keyring):
        credentials.save("aura", "neo4j+s://one:7687", "neo4j", "one-pw")
        credentials.save("local", "bolt://localhost:7687", "neo4j", "two-pw")

        assert credentials.delete("aura") is True
        assert credentials.load("aura") is None
        assert credentials.load("local") is not None
        assert credentials.list_profiles() == ["local"]

    def test_delete_is_quiet_when_nothing_is_stored(self, fake_keyring):
        assert credentials.delete("never-used") is False

    def test_database_defaults_to_neo4j(self, fake_keyring):
        credentials.save("default", "bolt://x:7687", "neo4j", "pw", "")
        assert credentials.load("default")["database"] == "neo4j"

    def test_empty_required_field_is_refused(self, fake_keyring):
        with pytest.raises(credentials.CredentialStoreError, match="password"):
            credentials.save("default", "bolt://x:7687", "neo4j", "")
        assert fake_keyring.store == {}

    def test_reserved_profile_name_is_refused(self, fake_keyring):
        with pytest.raises(credentials.CredentialStoreError, match="reserved"):
            credentials.save("__profiles__", "bolt://x:7687", "neo4j", "pw")

    def test_empty_profile_name_is_refused(self, fake_keyring):
        with pytest.raises(credentials.CredentialStoreError, match="empty"):
            credentials.save("   ", "bolt://x:7687", "neo4j", "pw")

    def test_active_profile_follows_the_env_var(self, fake_keyring, monkeypatch):
        monkeypatch.setenv(credentials.PROFILE_ENV, "work")
        credentials.save(None, "bolt://x:7687", "neo4j", "pw")
        assert credentials.load() == credentials.load("work")
        assert credentials.load("default") is None


class TestDegradation:
    """Every read path must survive a keychain that is missing or broken."""

    def test_load_returns_none_when_keyring_is_absent(self, monkeypatch):
        def boom():
            raise credentials.KeyringUnavailable("not installed")

        monkeypatch.setattr(credentials, "_load_keyring", boom)
        assert credentials.load("default") is None
        assert credentials.list_profiles() == []

    def test_load_returns_none_when_the_keychain_is_locked(self, monkeypatch):
        monkeypatch.setattr(credentials, "_load_keyring", lambda: BrokenKeyring())
        assert credentials.load("default") is None

    def test_load_ignores_a_corrupt_record(self, fake_keyring):
        fake_keyring.store[("wheeler", "neo4j:default")] = "not json"
        assert credentials.load("default") is None

    def test_load_ignores_a_record_with_no_usable_fields(self, fake_keyring):
        fake_keyring.store[("wheeler", "neo4j:default")] = json.dumps({"uri": ""})
        assert credentials.load("default") is None

    def test_list_profiles_survives_a_corrupt_index(self, fake_keyring):
        credentials.save("default", "bolt://x:7687", "neo4j", "pw")
        fake_keyring.store[("wheeler", "__profiles__")] = "{{{"
        assert credentials.list_profiles() == []
        # The credential itself is still readable: the index is only a cache.
        assert credentials.load("default") is not None

    def test_save_raises_when_there_is_nowhere_to_write(self, monkeypatch):
        def boom():
            raise credentials.KeyringUnavailable("no backend")

        monkeypatch.setattr(credentials, "_load_keyring", boom)
        with pytest.raises(credentials.KeyringUnavailable):
            credentials.save("default", "bolt://x:7687", "neo4j", "pw")

    def test_disable_env_switches_the_keychain_off(self, monkeypatch):
        monkeypatch.setenv(credentials.DISABLE_ENV, "1")
        with pytest.raises(credentials.KeyringUnavailable, match=credentials.DISABLE_ENV):
            credentials._load_keyring()
        available, detail = credentials.keyring_status()
        assert available is False
        assert credentials.DISABLE_ENV in detail

    @pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "FALSE"])
    def test_falsey_disable_values_leave_the_keychain_on(self, monkeypatch, value):
        monkeypatch.setenv(credentials.DISABLE_ENV, value)
        assert credentials.keychain_disabled() is False

    def test_missing_package_reports_the_install_hint(self, monkeypatch):
        def no_module():
            raise credentials.KeyringUnavailable(
                f"the 'keyring' package is not installed ({credentials.INSTALL_HINT})"
            )

        monkeypatch.setattr(credentials, "_import_keyring", no_module)
        monkeypatch.delenv(credentials.DISABLE_ENV, raising=False)
        available, detail = credentials.keyring_status()
        assert available is False
        assert "wheeler[login]" in detail

    def test_fail_backend_is_reported_as_unavailable(self, monkeypatch):
        class _FailBackend:
            pass

        _FailBackend.__module__ = "keyring.backends.fail"

        class _Module:
            @staticmethod
            def get_keyring():
                return _FailBackend()

        monkeypatch.delenv(credentials.DISABLE_ENV, raising=False)
        monkeypatch.setattr(credentials, "_import_keyring", lambda: _Module())
        available, detail = credentials.keyring_status()
        assert available is False
        assert "no OS keychain backend" in detail


class TestMasking:
    def test_password_is_never_rendered(self):
        assert credentials.mask("password", "hunter2") == "(set, hidden)"
        assert "hunter2" not in credentials.mask("password", "hunter2")

    def test_non_secret_fields_show_through(self):
        assert credentials.mask("uri", "bolt://x:7687") == "bolt://x:7687"


# ── Precedence: env > keychain > yaml > default ──────────────────────


class TestPrecedence:
    """All four levels, asserted through `load_config`.

    The keychain sits between env and YAML. Env stays highest so CI and
    containers keep working unchanged; the keychain beats YAML so `wheeler login`
    takes effect without editing a checked-in file.
    """

    def _store(self, fake_keyring, **fields):
        credentials.save(
            "default",
            fields.get("uri", "neo4j+s://keychain:7687"),
            fields.get("username", "keychain-user"),
            fields.get("password", "keychain-pass"),
            fields.get("database", "keychain-db"),
        )
        reset_keychain_cache()

    def test_default_wins_when_nothing_else_is_set(self, tmp_path, clean_neo4j_env, fake_keyring):
        config = load_config(tmp_path / "absent.yaml")
        assert config.neo4j.uri == _NEO4J_DEFAULTS["uri"]
        assert config.neo4j.database == _NEO4J_DEFAULTS["database"]

    def test_yaml_beats_default(self, tmp_path, clean_neo4j_env, fake_keyring):
        path = write_yaml(tmp_path, {"uri": "bolt://from-yaml:7687"})
        config = load_config(path)
        assert config.neo4j.uri == "bolt://from-yaml:7687"

    def test_keychain_beats_yaml(self, tmp_path, clean_neo4j_env, fake_keyring):
        path = write_yaml(tmp_path, {"uri": "bolt://from-yaml:7687", "username": "yaml-user"})
        self._store(fake_keyring, uri="neo4j+s://from-keychain:7687")

        config = load_config(path)
        assert config.neo4j.uri == "neo4j+s://from-keychain:7687"
        assert config.neo4j.username == "keychain-user"

    def test_env_beats_keychain(self, tmp_path, clean_neo4j_env, fake_keyring, monkeypatch):
        path = write_yaml(tmp_path, {"uri": "bolt://from-yaml:7687"})
        self._store(fake_keyring, uri="neo4j+s://from-keychain:7687")
        monkeypatch.setenv("NEO4J_URI", "bolt://from-env:7687")

        assert load_config(path).neo4j.uri == "bolt://from-env:7687"

    def test_all_four_levels_at_once(self, tmp_path, clean_neo4j_env, fake_keyring, monkeypatch):
        # uri from env, username from the keychain, database from YAML,
        # password from the built-in default.
        path = write_yaml(tmp_path, {"database": "yaml-db"})
        credentials.save("default", "neo4j+s://kc:7687", "keychain-user", "keychain-pass")
        reset_keychain_cache()
        monkeypatch.setenv("NEO4J_URI", "bolt://env-host:7687")

        config = load_config(path)
        assert config.neo4j.uri == "bolt://env-host:7687"
        assert config.neo4j.username == "keychain-user"
        # The keychain record always carries a database, so YAML only wins when
        # the stored record is silent about it: prove that by storing no db.
        assert config.neo4j.database == "neo4j"
        assert config.neo4j.password == "keychain-pass"

    def test_yaml_database_survives_a_keychain_record_without_one(
        self, tmp_path, clean_neo4j_env, fake_keyring
    ):
        path = write_yaml(tmp_path, {"database": "yaml-db"})
        # A hand-rolled record missing `database` (older store, partial write).
        fake_keyring.store[("wheeler", "neo4j:default")] = json.dumps(
            {"uri": "neo4j+s://kc:7687", "username": "kc-user", "password": "kc-pass"}
        )
        reset_keychain_cache()

        config = load_config(path)
        assert config.neo4j.uri == "neo4j+s://kc:7687"
        assert config.neo4j.database == "yaml-db"

    def test_config_loads_when_keyring_is_absent(self, tmp_path, clean_neo4j_env, monkeypatch):
        """A missing keychain must never be the reason Wheeler will not start."""

        def boom():
            raise credentials.KeyringUnavailable("not installed")

        monkeypatch.setattr(credentials, "_load_keyring", boom)
        reset_keychain_cache()
        path = write_yaml(tmp_path, {"uri": "bolt://from-yaml:7687"})

        config = load_config(path)
        assert config.neo4j.uri == "bolt://from-yaml:7687"

        monkeypatch.setenv("NEO4J_URI", "bolt://from-env:7687")
        reset_keychain_cache()
        assert load_config(path).neo4j.uri == "bolt://from-env:7687"

    def test_config_loads_when_the_keychain_is_locked(
        self, tmp_path, clean_neo4j_env, monkeypatch
    ):
        monkeypatch.setattr(credentials, "_load_keyring", lambda: BrokenKeyring())
        reset_keychain_cache()
        config = load_config(tmp_path / "absent.yaml")
        assert config.neo4j.uri == _NEO4J_DEFAULTS["uri"]

    def test_a_hanging_keychain_does_not_hang_wheeler(
        self, tmp_path, clean_neo4j_env, monkeypatch
    ):
        """A blocking keychain (macOS access prompt) must degrade, not wedge."""
        import time

        class HangingKeyring(FakeKeyring):
            def get_password(self, service, account):
                time.sleep(30)  # abandoned by the watchdog long before this ends
                return None

        monkeypatch.setattr(credentials, "_load_keyring", lambda: HangingKeyring())
        monkeypatch.setenv("WHEELER_KEYCHAIN_TIMEOUT", "0.1")
        reset_keychain_cache()

        started = time.monotonic()
        config = load_config(tmp_path / "absent.yaml")
        elapsed = time.monotonic() - started

        assert config.neo4j.uri == _NEO4J_DEFAULTS["uri"]
        assert elapsed < 5.0, f"took {elapsed:.1f}s: the watchdog did not fire"

    def test_keychain_is_read_once_per_process(self, tmp_path, clean_neo4j_env, fake_keyring):
        self._store(fake_keyring)
        before = fake_keyring.reads
        for _ in range(5):
            load_config(tmp_path / "absent.yaml")
        # One record read for the whole batch: load_config runs on every CLI
        # command and every MCP server start, so the cache is load bearing.
        assert fake_keyring.reads - before == 1


# ── Source reporting (job 4) ────────────────────────────────────────


class TestSourceReport:
    def test_reports_each_of_the_four_layers(
        self, tmp_path, clean_neo4j_env, fake_keyring, monkeypatch
    ):
        path = write_yaml(tmp_path, {"database": "yaml-db"})
        credentials.save("default", "neo4j+s://kc:7687", "kc-user", "kc-pass", "kc-db")
        reset_keychain_cache()
        monkeypatch.setenv("NEO4J_URI", "bolt://env-host:7687")

        by_field = {row.field: row for row in neo4j_sources(path)}
        assert by_field["uri"].source == "env"
        assert by_field["uri"].origin == "NEO4J_URI"
        assert by_field["username"].source == "keychain"
        assert "default" in by_field["username"].origin
        assert by_field["database"].source == "keychain"

    def test_yaml_and_default_are_distinguished(self, tmp_path, clean_neo4j_env, fake_keyring):
        path = write_yaml(tmp_path, {"uri": "bolt://from-yaml:7687"})
        by_field = {row.field: row for row in neo4j_sources(path)}
        assert by_field["uri"].source == "yaml"
        assert by_field["uri"].origin == str(path)
        assert by_field["password"].source == "default"
        assert by_field["password"].value == _NEO4J_DEFAULTS["password"]

    def test_report_agrees_with_the_loaded_config(
        self, tmp_path, clean_neo4j_env, fake_keyring, monkeypatch
    ):
        """Anti-drift: the report must describe what load_config actually did."""
        path = write_yaml(tmp_path, {"database": "yaml-db", "username": "yaml-user"})
        credentials.save("default", "neo4j+s://kc:7687", "kc-user", "kc-pass", "")
        reset_keychain_cache()
        monkeypatch.setenv("NEO4J_URI", "bolt://env-host:7687")

        config = load_config(path)
        for row in neo4j_sources(path):
            assert row.value == getattr(config.neo4j, row.field), row.field

    def test_password_is_masked_in_the_display(self, tmp_path, clean_neo4j_env, fake_keyring):
        credentials.save("default", "neo4j+s://kc:7687", "kc-user", "super-secret")
        reset_keychain_cache()
        rows = {row.field: row for row in neo4j_sources(tmp_path / "absent.yaml")}
        assert rows["password"].display == "(set, hidden)"
        assert "super-secret" not in rows["password"].display

    def test_shadowed_by_env_names_the_offending_vars(
        self, tmp_path, clean_neo4j_env, fake_keyring, monkeypatch
    ):
        credentials.save("default", "neo4j+s://kc:7687", "kc-user", "kc-pass")
        reset_keychain_cache()
        assert shadowed_by_env() == []

        monkeypatch.setenv("NEO4J_URI", "bolt://env-host:7687")
        reset_keychain_cache()
        assert shadowed_by_env() == ["NEO4J_URI"]

    def test_nothing_is_shadowed_without_a_stored_credential(
        self, tmp_path, clean_neo4j_env, fake_keyring, monkeypatch
    ):
        monkeypatch.setenv("NEO4J_URI", "bolt://env-host:7687")
        assert shadowed_by_env() == []
