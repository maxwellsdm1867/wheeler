"""Tests for the isolation model chosen by wheeler.graph.schema.ensure_database.

Two isolation models exist: a dedicated Neo4j database (Enterprise, paid Aura)
and property-tag namespacing on the shared `neo4j` database (Community, Aura
Free). `ensure_database` silently downgraded from the first to the second
whenever `CREATE DATABASE` raised for any reason, including a bad password.
These tests pin the downgrade being announced at WARNING with the real cause.
"""

from __future__ import annotations

import logging

from neo4j.exceptions import ClientError
import pytest

from wheeler.config import WheelerConfig
import wheeler.graph.driver as drv
from wheeler.graph.schema import (
    CONSTRAINTS,
    INDEXES,
    PROJECT_INDEXES,
    ensure_database,
    init_schema,
)


class _FakeSession:
    def __init__(self, recorder: _FakeDriver, database: str | None) -> None:
        self._recorder = recorder
        self._database = database

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc_info) -> bool:
        return False

    async def run(self, query: str, *args, **kwargs):
        self._recorder.statements.append((self._database, query))
        error = self._recorder.raise_on_run
        if error is not None:
            raise error
        return None


class _FakeDriver:
    """Async-driver stand-in that records every statement it is handed."""

    def __init__(self, raise_on_run: BaseException | None = None) -> None:
        self.statements: list[tuple[str | None, str]] = []
        self.raise_on_run = raise_on_run

    def session(self, database: str | None = None, **_kwargs) -> _FakeSession:
        return _FakeSession(self, database)


@pytest.fixture(autouse=True)
def _isolate_driver_state():
    drv.invalidate_async_driver()
    yield
    drv.invalidate_async_driver()


@pytest.fixture
def fake_driver(monkeypatch):
    """Install a fake driver; the returned callable sets the failure mode."""

    holder: dict[str, _FakeDriver] = {}

    def install(raise_on_run: BaseException | None = None) -> _FakeDriver:
        driver = _FakeDriver(raise_on_run=raise_on_run)
        holder["driver"] = driver
        monkeypatch.setattr(drv, "get_async_driver", lambda config: driver)
        return driver

    return install


def _config(*, database: str = "neo4j", project_name: str = "") -> WheelerConfig:
    config = WheelerConfig()
    config.neo4j.database = database
    config.neo4j.project_tag = ""
    config.project.name = project_name
    return config


class TestDefaultDatabase:
    async def test_project_name_enables_tag_isolation(self, fake_driver):
        fake_driver()
        config = _config(database="neo4j", project_name="wheeler-dev")

        assert await ensure_database(config) == "neo4j"
        assert config.neo4j.project_tag == "wheeler-dev"

    async def test_no_project_name_means_no_tag(self, fake_driver):
        fake_driver()
        config = _config(database="neo4j", project_name="")

        assert await ensure_database(config) == "neo4j"
        assert config.neo4j.project_tag == ""

    async def test_an_existing_tag_is_left_alone(self, fake_driver):
        fake_driver()
        config = _config(database="neo4j", project_name="wheeler-dev")
        config.neo4j.project_tag = "explicitly-chosen"

        await ensure_database(config)

        assert config.neo4j.project_tag == "explicitly-chosen"

    async def test_no_statements_are_run_for_the_default_database(self, fake_driver):
        driver = fake_driver()
        await ensure_database(_config(database="neo4j", project_name="p"))

        assert driver.statements == []


class TestDedicatedDatabase:
    async def test_successful_create_keeps_database_isolation(self, fake_driver):
        driver = fake_driver()
        config = _config(database="my-project", project_name="my-project")

        assert await ensure_database(config) == "my-project"
        assert config.neo4j.database == "my-project"
        # No tag: real database isolation is in force.
        assert config.neo4j.project_tag == ""
        assert driver.statements == [
            ("system", "CREATE DATABASE `my-project` IF NOT EXISTS")
        ]

    async def test_no_warning_when_create_succeeds(self, fake_driver, caplog):
        fake_driver()
        with caplog.at_level(logging.WARNING, logger="wheeler.graph.schema"):
            await ensure_database(_config(database="my-project"))

        assert caplog.records == []


class TestSilentDowngradeIsNowLoud:
    async def test_failed_create_downgrades_the_config_as_documented(self, fake_driver):
        fake_driver(ClientError("Unsupported administration command"))
        config = _config(database="my-project", project_name="my-project")

        assert await ensure_database(config) == "neo4j"
        assert config.neo4j.database == "neo4j"
        assert config.neo4j.project_tag == "my-project"

    async def test_downgrade_warns_and_names_the_underlying_cause(
        self, fake_driver, caplog
    ):
        fake_driver(ClientError("Unsupported administration command: CREATE DATABASE"))
        config = _config(database="my-project", project_name="my-project")

        with caplog.at_level(logging.WARNING, logger="wheeler.graph.schema"):
            await ensure_database(config)

        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        # The real exception, not just "Community Edition?"
        assert "ClientError" in message
        assert "Unsupported administration command" in message
        # Which isolation model is now in force, stated outright.
        assert "DOWNGRADED" in message
        assert "_wheeler_project='my-project'" in message
        assert "neo4j" in message

    async def test_bad_credentials_are_not_reported_as_an_edition_limit(
        self, fake_driver, caplog
    ):
        """A mistyped password used to look identical to Community Edition."""
        fake_driver(ClientError("The client is unauthorized due to authentication failure"))

        with caplog.at_level(logging.WARNING, logger="wheeler.graph.schema"):
            await ensure_database(_config(database="my-project", project_name="proj"))

        message = caplog.records[0].getMessage()
        assert "authentication failure" in message
        assert "credentials" in message

    async def test_tag_falls_back_to_the_database_name_without_a_project_name(
        self, fake_driver
    ):
        fake_driver(ClientError("nope"))
        config = _config(database="my-project", project_name="")

        await ensure_database(config)

        assert config.neo4j.project_tag == "my-project"


class TestInitSchemaHonoursTheIsolationModel:
    async def test_project_indexes_added_only_when_tagging(self, fake_driver):
        driver = fake_driver()
        config = _config()
        config.neo4j.project_tag = "wheeler-dev"

        applied = await init_schema(config)

        assert len(applied) == len(CONSTRAINTS) + len(INDEXES) + len(PROJECT_INDEXES)
        assert all(stmt in applied for stmt in PROJECT_INDEXES)
        assert {db for db, _ in driver.statements} == {"neo4j"}

    async def test_no_project_indexes_without_a_tag(self, fake_driver):
        fake_driver()
        config = _config()

        applied = await init_schema(config)

        assert len(applied) == len(CONSTRAINTS) + len(INDEXES)
        assert not any(stmt in applied for stmt in PROJECT_INDEXES)

    async def test_init_schema_retries_a_transient_failure(self, monkeypatch):
        """Schema statements are all IF NOT EXISTS, so replay is safe."""
        from neo4j.exceptions import ServiceUnavailable

        attempts: list[int] = []

        class _FlakyDriver(_FakeDriver):
            def session(self, database: str | None = None, **kwargs):
                attempts.append(1)
                self.raise_on_run = (
                    ServiceUnavailable("wan blip") if len(attempts) == 1 else None
                )
                return _FakeSession(self, database)

        driver = _FlakyDriver()
        monkeypatch.setattr(drv, "get_async_driver", lambda config: driver)
        monkeypatch.setenv(drv._ENV_RETRY_BASE_DELAY, "0")

        applied = await init_schema(_config())

        assert len(attempts) == 2
        assert len(applied) == len(CONSTRAINTS) + len(INDEXES)
