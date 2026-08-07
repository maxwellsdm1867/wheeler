"""Neo4j Aura onboarding: credentials files, the management API, validation.

Three ways to learn where a remote graph lives, in the order a user should reach
for them:

1. **The credentials file** (`login --aura-file`). Aura offers a download at
   instance creation holding `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD`.
   One drag and drop, nothing typed, and it is the ONLY route that works on a
   Free instance, so it is the default.
2. **The management API** (`login --aura`). Authenticates with OAuth 2.0
   `client_credentials` against `api.neo4j.io`: a Client ID and Secret created in
   the Aura Console under Account Details. `GET /v1/instances` then reports each
   instance's `connection_url`, so the URI stops being something to copy by hand.
   Two limits are structural, not oversights:
   - There is **no interactive or device-code browser flow**. `client_credentials`
     is the whole grant surface, so "paste one API key once" is the best
     achievable, and this module does not pretend otherwise.
   - `GET /v1/instances` does **not** return passwords. A password is returned
     exactly once, in the `POST /v1/instances` response at creation, and is
     unrecoverable afterwards. So this flow still prompts for the password.
   And one gate worth naming up front: an account holding only Free instances
   must have billing information on file (or belong to a marketplace project)
   before it can create API credentials at all. See `BILLING_NOTE`.
3. **Prompts** (`login`, no flags). Works against anything, including a local
   Desktop instance.

All HTTP here is stdlib `urllib.request` on purpose: a login helper is not worth
a new runtime dependency.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

AURA_TOKEN_URL = "https://api.neo4j.io/oauth/token"
AURA_API_BASE = "https://api.neo4j.io/v1"
AURA_CONSOLE_URL = "https://console.neo4j.io"

# Generous enough for a cold TLS handshake to api.neo4j.io, short enough that a
# hung request fails while the user is still looking at the terminal.
_HTTP_TIMEOUT = 20.0

BILLING_NOTE = (
    "Aura rejected those API credentials. Two things to check: the Client ID and "
    "Secret come from Account Details in the Aura Console, and an account with "
    "only Free instances must have billing information on file (or belong to a "
    "marketplace project) before it can create API credentials at all. If that "
    "is you, run 'wheeler login --aura-file <path>' with the credentials file "
    "Aura gave you when the instance was created: it needs no API key."
)

# Schemes the Neo4j driver can actually dial. A console URL or a bare hostname
# pasted into the URI prompt is the most common typo, and it produces a driver
# error that reads like a network problem, so reject it here with a real message.
_VALID_SCHEMES = (
    "neo4j",
    "neo4j+s",
    "neo4j+ssc",
    "bolt",
    "bolt+s",
    "bolt+ssc",
)

# Key aliases seen in Aura credentials files across formats: the current
# `NEO4J_URI=` dump, older `NEO4J_USER=` variants, and hand-edited `.env` files.
# Keys are compared upper-cased with surrounding whitespace stripped.
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "uri": (
        "NEO4J_URI",
        "URI",
        "NEO4J_CONNECTION_URI",
        "CONNECTION_URI",
        "CONNECTION_URL",
        "NEO4J_URL",
        "NEO4J_BOLT_URL",
        "BOLT_URL",
    ),
    "username": ("NEO4J_USERNAME", "USERNAME", "NEO4J_USER", "USER"),
    "password": ("NEO4J_PASSWORD", "PASSWORD", "NEO4J_PASS", "PASS"),
    "database": ("NEO4J_DATABASE", "DATABASE", "NEO4J_DB", "DB"),
    "instance_id": ("AURA_INSTANCEID", "AURA_INSTANCE_ID", "INSTANCEID"),
    "instance_name": ("AURA_INSTANCENAME", "AURA_INSTANCE_NAME", "INSTANCENAME"),
}


class AuraError(RuntimeError):
    """Base class for Aura onboarding failures."""


class AuraCredentialsFileError(AuraError):
    """A credentials file could not be parsed into a usable connection."""


class AuraApiError(AuraError):
    """The Aura management API refused or could not be reached."""


class ConnectionValidationError(AuraError):
    """Credentials did not produce a working Neo4j connection."""


@dataclass(frozen=True)
class AuraCredentials:
    """One connection's worth of credentials, however it was obtained."""

    uri: str
    username: str
    password: str
    database: str = "neo4j"
    instance_id: str = ""
    instance_name: str = ""

    def label(self) -> str:
        """Short human label for the instance. Never includes the password."""
        if self.instance_name and self.instance_id:
            return f"{self.instance_name} ({self.instance_id})"
        return self.instance_name or self.instance_id or self.uri


@dataclass(frozen=True)
class AuraInstance:
    """An instance as reported by `GET /v1/instances`. No password: see module docs."""

    id: str
    name: str
    connection_url: str
    tier: str = ""
    region: str = ""
    cloud_provider: str = ""

    def describe(self) -> str:
        bits = [b for b in (self.tier, self.cloud_provider, self.region) if b]
        suffix = f"  [{', '.join(bits)}]" if bits else ""
        return f"{self.name or self.id}  {self.connection_url}{suffix}"


# ── URI handling ────────────────────────────────────────────────────


def normalize_uri(uri: str) -> str:
    """Trim and validate a Neo4j URI, raising with a usable message.

    Rejects what people actually paste: the Aura Console URL, an `https://`
    endpoint, or a bare hostname.
    """
    candidate = (uri or "").strip().strip("/")
    if not candidate:
        raise AuraError("connection URI must not be empty")
    if "://" not in candidate:
        raise AuraError(
            f"{candidate!r} has no scheme: an Aura URI looks like "
            "neo4j+s://xxxxxxxx.databases.neo4j.io"
        )
    scheme = candidate.split("://", 1)[0].lower()
    if scheme not in _VALID_SCHEMES:
        hint = (
            f" ({AURA_CONSOLE_URL} is the web console, not a database endpoint)"
            if scheme in ("http", "https")
            else ""
        )
        raise AuraError(
            f"unsupported URI scheme {scheme!r}{hint}: expected one of "
            + ", ".join(_VALID_SCHEMES)
        )
    return candidate


# ── Credentials file ────────────────────────────────────────────────


def _split_line(line: str) -> tuple[str, str] | None:
    """Parse one `KEY=value` / `KEY: value` line, or None when it is not one."""
    text = line.strip()
    if not text or text.startswith("#") or text.startswith("//"):
        return None
    if text.lower().startswith("export "):
        text = text[len("export ") :].lstrip()
    for sep in ("=", ":"):
        if sep in text:
            key, value = text.split(sep, 1)
            key = key.strip()
            if not key:
                return None
            value = value.strip()
            # Strip one matched pair of quotes. Values are NOT comment-stripped:
            # '#' is a legal character in a generated Aura password.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            return key, value
    return None


def parse_credentials_text(text: str, *, origin: str = "credentials file") -> AuraCredentials:
    """Parse an Aura credentials file's contents.

    Tolerant by design: key aliases, `export ` prefixes, `:` or `=`, quoted
    values, comments, and blank lines. Deliberately strict about the outcome, a
    file missing the password is a failure rather than a half-filled prompt.
    """
    found: dict[str, str] = {}
    seen: list[str] = []
    for line in text.splitlines():
        parsed = _split_line(line)
        if parsed is None:
            continue
        key, value = parsed
        seen.append(key)
        upper = key.upper()
        for field, aliases in _FIELD_ALIASES.items():
            if upper in aliases and field not in found and value:
                found[field] = value

    missing = [f for f in ("uri", "username", "password") if f not in found]
    if missing:
        # Key names only, never values: this file holds a password.
        detail = f"keys present: {', '.join(sorted(set(seen)))}" if seen else "no key=value lines"
        raise AuraCredentialsFileError(
            f"{origin} is missing {', '.join(missing)} ({detail}). Expected an Aura "
            "credentials file with NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD."
        )

    return AuraCredentials(
        uri=normalize_uri(found["uri"]),
        username=found["username"],
        password=found["password"],
        database=found.get("database") or "neo4j",
        instance_id=found.get("instance_id", ""),
        instance_name=found.get("instance_name", ""),
    )


def parse_credentials_file(path: str | Path) -> AuraCredentials:
    """Read and parse an Aura credentials file from disk."""
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise AuraCredentialsFileError(f"no such file: {file_path}")
    if file_path.is_dir():
        raise AuraCredentialsFileError(f"{file_path} is a directory, not a credentials file")
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise AuraCredentialsFileError(f"could not read {file_path}: {exc}") from exc
    return parse_credentials_text(text, origin=str(file_path))


# ── Management API ──────────────────────────────────────────────────


def _urlopen(request: urllib.request.Request, timeout: float) -> Any:
    """Single seam over urllib so tests can stub the network. Do not inline."""
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (fixed https hosts)


def _read_json(request: urllib.request.Request, *, what: str, timeout: float) -> dict[str, Any]:
    """Send `request` and decode a JSON object, mapping failures to AuraApiError."""
    try:
        with _urlopen(request, timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:  # pragma: no cover - defensive
            pass
        if exc.code in (401, 403):
            raise AuraApiError(BILLING_NOTE) from exc
        raise AuraApiError(f"{what} failed: HTTP {exc.code} {exc.reason} {detail}".strip()) from exc
    except urllib.error.URLError as exc:
        raise AuraApiError(f"{what} failed: cannot reach {AURA_API_BASE} ({exc.reason})") from exc
    except OSError as exc:  # timeouts land here
        raise AuraApiError(f"{what} failed: {exc}") from exc

    try:
        data = json.loads(body)
    except ValueError as exc:
        raise AuraApiError(f"{what} returned a non-JSON response") from exc
    if not isinstance(data, dict):
        raise AuraApiError(f"{what} returned {type(data).__name__}, expected an object")
    return data


def request_token(
    client_id: str,
    client_secret: str,
    *,
    timeout: float = _HTTP_TIMEOUT,
) -> str:
    """Exchange an Aura Client ID and Secret for a bearer token.

    OAuth 2.0 `client_credentials` with HTTP Basic `id:secret`, which is the only
    grant Aura's management API offers. The secret is never logged.
    """
    if not (client_id or "").strip() or not (client_secret or "").strip():
        raise AuraApiError("both a Client ID and a Client Secret are required")

    basic = base64.b64encode(f"{client_id.strip()}:{client_secret.strip()}".encode()).decode()
    request = urllib.request.Request(
        AURA_TOKEN_URL,
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        method="POST",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    payload = _read_json(request, what="Aura token request", timeout=timeout)
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise AuraApiError("Aura token response carried no access_token")
    logger.info("obtained an Aura management API token")
    return token


def list_instances(token: str, *, timeout: float = _HTTP_TIMEOUT) -> list[AuraInstance]:
    """List the instances this token can see.

    Passwords are absent from the response by design: Aura returns one only in
    the `POST /v1/instances` reply at creation time. Callers must prompt.
    """
    request = urllib.request.Request(
        f"{AURA_API_BASE}/instances",
        method="GET",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    payload = _read_json(request, what="Aura instance listing", timeout=timeout)
    raw = payload.get("data")
    if not isinstance(raw, list):
        raise AuraApiError("Aura instance listing carried no 'data' array")

    instances: list[AuraInstance] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        instances.append(
            AuraInstance(
                id=str(item.get("id") or ""),
                name=str(item.get("name") or ""),
                connection_url=str(item.get("connection_url") or ""),
                tier=str(item.get("type") or item.get("tier") or ""),
                region=str(item.get("region") or ""),
                cloud_provider=str(item.get("cloud_provider") or ""),
            )
        )
    return instances


# ── Validation ──────────────────────────────────────────────────────


def validate_connection(
    uri: str,
    username: str,
    password: str,
    database: str = "neo4j",
) -> str:
    """Connect and run a trivial query, returning a short detail string.

    Called before anything is stored. Saving a credential that does not work is
    worse than storing nothing, because the user then debugs the wrong layer:
    they trust the keychain and go looking at Neo4j.

    Reuses `wheeler.graph.driver`'s tuned connection settings (WAN-friendly
    timeouts, pool recycling) so validation fails or succeeds for the same
    reasons the real workload will.
    """
    from wheeler.config import Neo4jConfig, WheelerConfig  # noqa: PLC0415 (import cost)
    from wheeler.graph.driver import get_sync_driver  # noqa: PLC0415 (pulls in neo4j)

    checked_uri = normalize_uri(uri)
    db = (database or "neo4j").strip() or "neo4j"
    probe = WheelerConfig(
        neo4j=Neo4jConfig(
            uri=checked_uri,
            username=username,
            password=password,
            database=db,
        )
    )

    driver = None
    try:
        driver = get_sync_driver(probe)
        driver.verify_connectivity()
        with driver.session(database=db) as session:
            record = session.run("RETURN 1 AS ok").single()
        if record is None or record.get("ok") != 1:
            raise ConnectionValidationError(
                f"connected to {checked_uri} but 'RETURN 1' came back empty"
            )
    except ConnectionValidationError:
        raise
    except Exception as exc:
        raise ConnectionValidationError(
            f"could not connect to {checked_uri} as {username!r} "
            f"(database {db!r}): {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        if driver is not None:
            try:
                driver.close()
            except Exception:  # pragma: no cover - defensive
                pass
    return f"{checked_uri} database {db!r} answered 'RETURN 1'"
