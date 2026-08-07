"""Aura onboarding: credentials-file parsing, the management API, validation.

No network and no keychain. `wheeler.aura._urlopen` is the single seam over
`urllib`, so every HTTP test stubs that; the CLI tests stub the validator and the
credential store.
"""

from __future__ import annotations

import base64
import io
import json
import urllib.error

import pytest
from typer.testing import CliRunner

from wheeler import aura, credentials
import wheeler.tools.cli as cli

runner = CliRunner()


# A verbatim-shaped Aura download: leading comment, blank line, AURA_* extras.
AURA_FILE = """\
# Wait 60 seconds before connecting using these details, or login to
# https://console.neo4j.io to validate the Aura Instance is available
NEO4J_URI=neo4j+s://abcd1234.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=Xy7-pass_word
NEO4J_DATABASE=neo4j
AURA_INSTANCEID=abcd1234
AURA_INSTANCENAME=Instance01
"""


class FakeResponse(io.BytesIO):
    """Context-manager BytesIO, which is all `_read_json` needs of a response."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def json_response(payload: dict) -> FakeResponse:
    return FakeResponse(json.dumps(payload).encode())


def http_error(code: int, body: str = "") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        aura.AURA_TOKEN_URL, code, "denied", {}, io.BytesIO(body.encode())
    )


# ── Credentials file ────────────────────────────────────────────────


class TestCredentialsFile:
    def test_parses_the_standard_aura_download(self):
        creds = aura.parse_credentials_text(AURA_FILE)
        assert creds.uri == "neo4j+s://abcd1234.databases.neo4j.io"
        assert creds.username == "neo4j"
        assert creds.password == "Xy7-pass_word"
        assert creds.database == "neo4j"
        assert creds.instance_id == "abcd1234"
        assert creds.instance_name == "Instance01"
        assert creds.label() == "Instance01 (abcd1234)"

    def test_parses_the_export_and_quoted_variant(self):
        text = """
        export NEO4J_URI="neo4j+s://zzz.databases.neo4j.io"
        export NEO4J_USER='neo4j'
        export NEO4J_PASSWORD="quoted-pass"
        """
        creds = aura.parse_credentials_text(text)
        assert creds.uri == "neo4j+s://zzz.databases.neo4j.io"
        assert creds.username == "neo4j"
        assert creds.password == "quoted-pass"
        # Absent database falls back rather than failing the whole parse.
        assert creds.database == "neo4j"

    def test_parses_a_colon_separated_yaml_ish_file(self):
        text = "uri: neo4j+s://c.databases.neo4j.io\nusername: neo4j\npassword: colon-pass\n"
        creds = aura.parse_credentials_text(text)
        assert creds.uri == "neo4j+s://c.databases.neo4j.io"
        assert creds.password == "colon-pass"

    def test_parses_the_connection_url_key_name(self):
        text = "CONNECTION_URL=neo4j+s://d.databases.neo4j.io\nUSERNAME=neo4j\nPASSWORD=p\n"
        assert aura.parse_credentials_text(text).uri == "neo4j+s://d.databases.neo4j.io"

    def test_a_hash_in_a_password_is_not_a_comment(self):
        text = "NEO4J_URI=bolt://x:7687\nNEO4J_USERNAME=neo4j\nNEO4J_PASSWORD=ab#cd=ef\n"
        assert aura.parse_credentials_text(text).password == "ab#cd=ef"

    def test_missing_password_is_a_hard_error(self):
        text = "NEO4J_URI=neo4j+s://x.databases.neo4j.io\nNEO4J_USERNAME=neo4j\n"
        with pytest.raises(aura.AuraCredentialsFileError, match="password"):
            aura.parse_credentials_text(text)

    def test_malformed_file_names_the_keys_it_did_see(self):
        text = "SOME_OTHER_THING=1\njust some prose\n"
        with pytest.raises(aura.AuraCredentialsFileError) as excinfo:
            aura.parse_credentials_text(text)
        message = str(excinfo.value)
        assert "SOME_OTHER_THING" in message
        assert "uri" in message and "password" in message

    def test_empty_file_is_a_clear_error(self):
        with pytest.raises(aura.AuraCredentialsFileError, match="no key=value lines"):
            aura.parse_credentials_text("\n\n# only comments\n")

    def test_error_message_never_leaks_a_value(self):
        text = "NEO4J_PASSWORD=leak-me-not\nNEO4J_USERNAME=neo4j\n"
        with pytest.raises(aura.AuraCredentialsFileError) as excinfo:
            aura.parse_credentials_text(text)
        assert "leak-me-not" not in str(excinfo.value)

    def test_reads_from_disk(self, tmp_path):
        path = tmp_path / "Instance01-credentials.txt"
        path.write_text(AURA_FILE)
        assert aura.parse_credentials_file(path).instance_name == "Instance01"

    def test_missing_file_is_reported_by_path(self, tmp_path):
        with pytest.raises(aura.AuraCredentialsFileError, match="no such file"):
            aura.parse_credentials_file(tmp_path / "nope.txt")

    def test_directory_is_rejected(self, tmp_path):
        with pytest.raises(aura.AuraCredentialsFileError, match="directory"):
            aura.parse_credentials_file(tmp_path)


class TestUriNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("  neo4j+s://x.databases.neo4j.io  ", "neo4j+s://x.databases.neo4j.io"),
            ("bolt://localhost:7687/", "bolt://localhost:7687"),
            ("neo4j+ssc://x:7687", "neo4j+ssc://x:7687"),
        ],
    )
    def test_accepts_and_trims_valid_uris(self, raw, expected):
        assert aura.normalize_uri(raw) == expected

    def test_rejects_a_bare_hostname(self):
        with pytest.raises(aura.AuraError, match="no scheme"):
            aura.normalize_uri("abcd1234.databases.neo4j.io")

    def test_rejects_the_console_url_with_a_pointed_hint(self):
        with pytest.raises(aura.AuraError, match="web console"):
            aura.normalize_uri("https://console.neo4j.io/projects/x/instances")

    def test_rejects_an_empty_uri(self):
        with pytest.raises(aura.AuraError, match="empty"):
            aura.normalize_uri("   ")


# ── Management API ──────────────────────────────────────────────────


class TestTokenRequest:
    def test_sends_client_credentials_with_basic_auth(self, monkeypatch):
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            seen["method"] = request.method
            seen["auth"] = request.get_header("Authorization")
            seen["body"] = request.data.decode()
            return json_response({"access_token": "tok-123", "expires_in": 3600})

        monkeypatch.setattr(aura, "_urlopen", fake_urlopen)

        assert aura.request_token("id-1", "secret-1") == "tok-123"
        assert seen["url"] == aura.AURA_TOKEN_URL
        assert seen["method"] == "POST"
        assert seen["body"] == "grant_type=client_credentials"
        expected = base64.b64encode(b"id-1:secret-1").decode()
        assert seen["auth"] == f"Basic {expected}"

    def test_blank_credentials_are_refused_before_any_request(self, monkeypatch):
        def fail(*a, **k):
            raise AssertionError("should not have made a request")

        monkeypatch.setattr(aura, "_urlopen", fail)
        with pytest.raises(aura.AuraApiError, match="Client ID"):
            aura.request_token("", "secret")

    def test_401_explains_the_free_tier_billing_gate(self, monkeypatch):
        monkeypatch.setattr(
            aura, "_urlopen", lambda request, timeout: (_ for _ in ()).throw(http_error(401))
        )
        with pytest.raises(aura.AuraApiError) as excinfo:
            aura.request_token("id", "secret")
        assert "billing information" in str(excinfo.value)
        assert "--aura-file" in str(excinfo.value)

    def test_500_reports_the_status(self, monkeypatch):
        monkeypatch.setattr(
            aura,
            "_urlopen",
            lambda request, timeout: (_ for _ in ()).throw(http_error(500, "boom")),
        )
        with pytest.raises(aura.AuraApiError, match="HTTP 500"):
            aura.request_token("id", "secret")

    def test_unreachable_host_is_reported_as_such(self, monkeypatch):
        def unreachable(request, timeout):
            raise urllib.error.URLError("no route to host")

        monkeypatch.setattr(aura, "_urlopen", unreachable)
        with pytest.raises(aura.AuraApiError, match="cannot reach"):
            aura.request_token("id", "secret")

    def test_response_without_a_token_is_an_error(self, monkeypatch):
        monkeypatch.setattr(aura, "_urlopen", lambda request, timeout: json_response({"x": 1}))
        with pytest.raises(aura.AuraApiError, match="access_token"):
            aura.request_token("id", "secret")

    def test_non_json_response_is_an_error(self, monkeypatch):
        monkeypatch.setattr(
            aura, "_urlopen", lambda request, timeout: FakeResponse(b"<html>oops</html>")
        )
        with pytest.raises(aura.AuraApiError, match="non-JSON"):
            aura.request_token("id", "secret")


class TestListInstances:
    PAYLOAD = {
        "data": [
            {
                "id": "abcd1234",
                "name": "Instance01",
                "connection_url": "neo4j+s://abcd1234.databases.neo4j.io",
                "type": "free-db",
                "region": "us-central1",
                "cloud_provider": "gcp",
            },
            {
                "id": "efgh5678",
                "name": "Instance02",
                "connection_url": "neo4j+s://efgh5678.databases.neo4j.io",
            },
        ]
    }

    def test_parses_instances_and_sends_a_bearer_token(self, monkeypatch):
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            seen["auth"] = request.get_header("Authorization")
            return json_response(self.PAYLOAD)

        monkeypatch.setattr(aura, "_urlopen", fake_urlopen)
        instances = aura.list_instances("tok-123")

        assert seen["url"] == f"{aura.AURA_API_BASE}/instances"
        assert seen["auth"] == "Bearer tok-123"
        assert [i.id for i in instances] == ["abcd1234", "efgh5678"]
        assert instances[0].connection_url == "neo4j+s://abcd1234.databases.neo4j.io"
        assert instances[0].tier == "free-db"
        assert "Instance01" in instances[0].describe()

    def test_no_data_array_is_an_error(self, monkeypatch):
        monkeypatch.setattr(aura, "_urlopen", lambda request, timeout: json_response({}))
        with pytest.raises(aura.AuraApiError, match="'data' array"):
            aura.list_instances("tok")

    def test_empty_listing_is_an_empty_list(self, monkeypatch):
        monkeypatch.setattr(aura, "_urlopen", lambda request, timeout: json_response({"data": []}))
        assert aura.list_instances("tok") == []

    def test_the_listing_never_carries_a_password(self, monkeypatch):
        """Documents the API limit the login flow is built around."""
        monkeypatch.setattr(aura, "_urlopen", lambda request, timeout: json_response(self.PAYLOAD))
        for instance in aura.list_instances("tok"):
            assert not hasattr(instance, "password")


# ── Validation ──────────────────────────────────────────────────────


class FakeSession:
    def __init__(self, value=1):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, _query):
        class _Result:
            def __init__(self, value):
                self.value = value

            def single(self):
                return {"ok": self.value} if self.value is not None else None

        return _Result(self.value)


class FakeDriver:
    def __init__(self, *, connect_error=None, value=1):
        self.connect_error = connect_error
        self.value = value
        self.closed = False
        self.sessions: list[str] = []

    def verify_connectivity(self):
        if self.connect_error:
            raise self.connect_error

    def session(self, database=None):
        self.sessions.append(database)
        return FakeSession(self.value)

    def close(self):
        self.closed = True


class TestValidateConnection:
    def test_runs_a_trivial_query_and_closes_the_driver(self, monkeypatch):
        driver = FakeDriver()
        monkeypatch.setattr(aura, "get_sync_driver", lambda cfg: driver, raising=False)
        monkeypatch.setattr(
            "wheeler.graph.driver.get_sync_driver", lambda cfg: driver, raising=True
        )

        detail = aura.validate_connection("neo4j+s://x.databases.neo4j.io", "neo4j", "pw", "neo4j")
        assert "RETURN 1" in detail
        assert driver.sessions == ["neo4j"]
        assert driver.closed is True

    def test_connection_failure_becomes_a_validation_error(self, monkeypatch):
        driver = FakeDriver(connect_error=RuntimeError("auth failed"))
        monkeypatch.setattr(
            "wheeler.graph.driver.get_sync_driver", lambda cfg: driver, raising=True
        )
        with pytest.raises(aura.ConnectionValidationError, match="auth failed"):
            aura.validate_connection("neo4j+s://x.databases.neo4j.io", "neo4j", "pw")
        assert driver.closed is True

    def test_empty_result_is_a_validation_error(self, monkeypatch):
        driver = FakeDriver(value=None)
        monkeypatch.setattr(
            "wheeler.graph.driver.get_sync_driver", lambda cfg: driver, raising=True
        )
        with pytest.raises(aura.ConnectionValidationError, match="came back empty"):
            aura.validate_connection("neo4j+s://x.databases.neo4j.io", "neo4j", "pw")

    def test_a_bad_uri_fails_before_dialling(self, monkeypatch):
        def fail(cfg):
            raise AssertionError("should not have built a driver")

        monkeypatch.setattr("wheeler.graph.driver.get_sync_driver", fail, raising=True)
        with pytest.raises(aura.AuraError, match="scheme"):
            aura.validate_connection("https://console.neo4j.io", "neo4j", "pw")


# ── CLI ─────────────────────────────────────────────────────────────


@pytest.fixture
def stub_store(monkeypatch):
    """Record what the CLI would have stored, without touching any keychain."""
    saved: list[tuple] = []

    def fake_save(profile, uri, username, password, database="neo4j"):
        saved.append((profile or "default", uri, username, password, database))
        return profile or "default"

    monkeypatch.setattr(credentials, "save", fake_save)
    monkeypatch.setattr(credentials, "delete", lambda profile=None: True)
    monkeypatch.setattr(credentials, "keyring_status", lambda: (True, "fake.backend"))
    monkeypatch.setattr(credentials, "list_profiles", lambda: ["default"])
    monkeypatch.setattr(credentials, "load", lambda profile=None: None)
    return saved


class TestLoginCli:
    def test_help_works_without_keyring_installed(self, monkeypatch):
        def no_keyring():
            raise credentials.KeyringUnavailable("not installed")

        monkeypatch.setattr(credentials, "_import_keyring", no_keyring)
        result = runner.invoke(cli.app, ["login", "--help"])
        assert result.exit_code == 0
        assert "--aura-file" in result.stdout

    def test_logout_help_works(self):
        result = runner.invoke(cli.app, ["logout", "--help"])
        assert result.exit_code == 0

    def test_status_reports_the_precedence_chain(self, stub_store):
        result = runner.invoke(cli.app, ["login", "--status"])
        assert result.exit_code == 0
        assert "env > keychain > wheeler.yaml > default" in result.stdout

    def test_aura_file_path_validates_then_saves(self, tmp_path, stub_store, monkeypatch):
        monkeypatch.setattr(aura, "validate_connection", lambda *a, **k: "ok")
        path = tmp_path / "creds.txt"
        path.write_text(AURA_FILE)

        result = runner.invoke(cli.app, ["login", "--aura-file", str(path)])
        assert result.exit_code == 0, result.stdout
        assert stub_store == [
            (
                "default",
                "neo4j+s://abcd1234.databases.neo4j.io",
                "neo4j",
                "Xy7-pass_word",
                "neo4j",
            )
        ]
        # The password must never reach the terminal.
        assert "Xy7-pass_word" not in result.stdout

    def test_validation_failure_does_not_save(self, tmp_path, stub_store, monkeypatch):
        def refuse(*a, **k):
            raise aura.ConnectionValidationError("could not connect to neo4j+s://x")

        monkeypatch.setattr(aura, "validate_connection", refuse)
        path = tmp_path / "creds.txt"
        path.write_text(AURA_FILE)

        result = runner.invoke(cli.app, ["login", "--aura-file", str(path)])
        assert result.exit_code == 1
        assert "Not saved" in result.stdout
        assert stub_store == []
        # An Aura URI earns the warm-up hint.
        assert "60 seconds" in result.stdout

    def test_a_local_failure_omits_the_aura_warmup_hint(self, stub_store, monkeypatch):
        def refuse(*a, **k):
            raise aura.ConnectionValidationError("auth failed")

        monkeypatch.setattr(aura, "validate_connection", refuse)
        result = runner.invoke(
            cli.app,
            ["login", "--uri", "bolt://localhost:7687", "--username", "neo4j"],
            input="pw\nneo4j\n",
        )
        assert result.exit_code == 1
        assert "60 seconds" not in result.stdout
        assert stub_store == []

    def test_unparseable_file_does_not_save(self, tmp_path, stub_store):
        path = tmp_path / "creds.txt"
        path.write_text("nothing useful here\n")
        result = runner.invoke(cli.app, ["login", "--aura-file", str(path)])
        assert result.exit_code == 1
        assert stub_store == []

    def test_both_aura_flags_is_a_usage_error(self, tmp_path, stub_store):
        path = tmp_path / "creds.txt"
        path.write_text(AURA_FILE)
        result = runner.invoke(cli.app, ["login", "--aura-file", str(path), "--aura"])
        assert result.exit_code == 2
        assert stub_store == []

    def test_no_keychain_refuses_with_the_install_hint(self, monkeypatch):
        monkeypatch.setattr(
            credentials, "keyring_status", lambda: (False, "no backend on this host")
        )
        result = runner.invoke(cli.app, ["login"])
        assert result.exit_code == 1
        assert "wheeler[login]" in result.stdout

    def test_prompt_path_reads_the_password_without_echo(self, stub_store, monkeypatch):
        monkeypatch.setattr(aura, "validate_connection", lambda *a, **k: "ok")
        result = runner.invoke(
            cli.app,
            ["login", "--uri", "bolt://localhost:7687", "--username", "neo4j"],
            input="typed-pass\nneo4j\n",
        )
        assert result.exit_code == 0, result.stdout
        assert stub_store[0][3] == "typed-pass"
        assert "typed-pass" not in result.stdout

    def test_aura_api_path_picks_the_only_instance(self, stub_store, monkeypatch):
        monkeypatch.setattr(aura, "validate_connection", lambda *a, **k: "ok")
        monkeypatch.setattr(aura, "request_token", lambda cid, secret: "tok")
        monkeypatch.setattr(
            aura,
            "list_instances",
            lambda token: [
                aura.AuraInstance(
                    id="abcd1234",
                    name="Instance01",
                    connection_url="neo4j+s://abcd1234.databases.neo4j.io",
                )
            ],
        )
        # client id, client secret, password, username, database
        result = runner.invoke(
            cli.app,
            ["login", "--aura"],
            input="client-id\nclient-secret\napi-pass\nneo4j\nneo4j\n",
        )
        assert result.exit_code == 0, result.stdout
        assert stub_store[0][1] == "neo4j+s://abcd1234.databases.neo4j.io"
        assert stub_store[0][3] == "api-pass"

    def test_aura_api_failure_does_not_save(self, stub_store, monkeypatch):
        def refuse(cid, secret):
            raise aura.AuraApiError(aura.BILLING_NOTE)

        monkeypatch.setattr(aura, "request_token", refuse)
        result = runner.invoke(
            cli.app, ["login", "--aura"], input="client-id\nclient-secret\n"
        )
        assert result.exit_code == 1
        assert "billing information" in result.stdout
        assert stub_store == []


class TestLogoutCli:
    def test_removes_the_active_profile(self, stub_store, monkeypatch):
        removed: list[str] = []

        def fake_delete(profile=None):
            removed.append(profile)
            return True

        monkeypatch.setattr(credentials, "delete", fake_delete)
        result = runner.invoke(cli.app, ["logout"])
        assert result.exit_code == 0
        assert removed == ["default"]
        assert "Removed" in result.stdout

    def test_reports_when_nothing_was_stored(self, stub_store, monkeypatch):
        monkeypatch.setattr(credentials, "delete", lambda profile=None: False)
        result = runner.invoke(cli.app, ["logout", "--profile", "ghost"])
        assert result.exit_code == 0
        assert "Nothing stored" in result.stdout

    def test_all_removes_every_stored_profile(self, stub_store, monkeypatch):
        removed: list[str] = []
        monkeypatch.setattr(credentials, "list_profiles", lambda: ["aura", "local"])
        monkeypatch.setattr(
            credentials, "delete", lambda profile=None: bool(removed.append(profile)) or True
        )
        result = runner.invoke(cli.app, ["logout", "--all"])
        assert result.exit_code == 0
        assert removed == ["aura", "local"]

    def test_no_keychain_is_not_a_failure(self, monkeypatch):
        monkeypatch.setattr(credentials, "keyring_status", lambda: (False, "not installed"))
        result = runner.invoke(cli.app, ["logout"])
        assert result.exit_code == 0
        assert "Nothing to remove" in result.stdout
