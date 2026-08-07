"""Keychain-backed credential store for Wheeler's Neo4j connection.

Why a keychain and not a file: the alternative is four ``NEO4J_*`` exports in a
shell profile, which parks a database password in a dotfile that gets backed up,
synced between machines, and grepped. ``keyring`` hands the secret to the OS
store instead (macOS Keychain, libsecret on Linux, Windows Credential Manager),
so nothing readable ever lands on disk.

``keyring`` is an OPTIONAL dependency (``pip install 'wheeler[login]'``). The
base install has to stay small because the ``wh`` plugin resolves the MCP
servers with ``uvx`` on a cold cache, and every megabyte shows up in that
resolve. So the import is function-local, and every READ path degrades to "no
stored credentials" instead of raising: a missing, locked, or broken keychain
must never be the reason Wheeler will not start. Write paths (``save``,
``delete``) do raise, because there the user asked for storage explicitly and
silence would be a lie.

Storage layout, one keyring entry per profile plus an index:

    service "wheeler", account "neo4j:<profile>"  -> JSON blob of the 4 fields
    service "wheeler", account "__profiles__"     -> JSON list of profile names

The index exists because ``keyring``'s portable API can get, set, and delete a
password but cannot enumerate accounts. ``load`` never consults the index, so a
lost index degrades ``list_profiles`` and nothing else.

This module imports nothing from ``wheeler``. That is deliberate: ``config.py``
reads it through a function-local import, and a leaf module cannot close a
cycle.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Keyring "service" for every entry Wheeler owns. Changing this orphans every
# credential a user has already stored, so treat it as a wire format.
SERVICE = "wheeler"

DEFAULT_PROFILE = "default"

# Account name that holds the profile index rather than a credential. Reserved:
# `save("__profiles__", ...)` is rejected.
_INDEX_ACCOUNT = "__profiles__"
_ACCOUNT_PREFIX = "neo4j:"

# Fields a stored record can carry. Order is display order.
FIELDS: tuple[str, ...] = ("uri", "username", "password", "database")

# Which of those must never be printed, logged, or echoed.
SECRET_FIELDS: frozenset[str] = frozenset({"password"})

# Selects the profile when a caller does not name one.
PROFILE_ENV = "WHEELER_PROFILE"

# Kill switch. Set it when a keychain prompt or a hung agent is worse than
# losing stored credentials (CI images, shared machines, headless containers).
DISABLE_ENV = "WHEELER_NO_KEYCHAIN"

INSTALL_HINT = "pip install 'wheeler[login]'"

_FALSEY = frozenset({"", "0", "false", "no", "off"})


class CredentialStoreError(RuntimeError):
    """Base class for credential-store failures."""


class KeyringUnavailable(CredentialStoreError):
    """No usable OS keychain: package missing, or no backend on this host."""


# ── Keyring access ──────────────────────────────────────────────────


def keychain_disabled() -> bool:
    """Whether ``WHEELER_NO_KEYCHAIN`` asks us to skip the keychain entirely."""
    return os.environ.get(DISABLE_ENV, "").strip().lower() not in _FALSEY


def _import_keyring() -> Any:
    """Import ``keyring``, the one place in Wheeler that touches the module.

    Tests monkeypatch this (or ``_load_keyring``) so the real OS keychain is
    never read or written by the suite.
    """
    try:
        import keyring  # noqa: PLC0415 (deliberately lazy: optional dependency)
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise KeyringUnavailable(
            f"the 'keyring' package is not installed ({INSTALL_HINT})"
        ) from exc
    return keyring


def _is_fail_backend(backend: object) -> bool:
    """Whether ``backend`` is keyring's null backend.

    On a headless Linux box with no libsecret, ``get_keyring()`` returns
    ``keyring.backends.fail.Keyring``, which raises on every operation. Catch it
    up front so the message names the real problem. Matched by module name to
    avoid importing ``keyring.backends.fail`` just to compare classes.
    """
    return type(backend).__module__.rsplit(".", 1)[-1] == "fail"


def _load_keyring() -> Any:
    """Return the ``keyring`` module with a usable backend, or raise."""
    if keychain_disabled():
        raise KeyringUnavailable(f"the keychain is disabled by {DISABLE_ENV}")
    module = _import_keyring()
    backend = module.get_keyring()
    if _is_fail_backend(backend):
        raise KeyringUnavailable(
            "no OS keychain backend is available on this host "
            "(macOS Keychain, libsecret, or Windows Credential Manager)"
        )
    return module


def keyring_status() -> tuple[bool, str]:
    """``(available, detail)`` for a status display. Never raises."""
    try:
        module = _load_keyring()
    except KeyringUnavailable as exc:
        return False, str(exc)
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"{type(exc).__name__}: {exc}"
    try:
        return True, type(module.get_keyring()).__module__
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"{type(exc).__name__}: {exc}"


# ── Profiles ────────────────────────────────────────────────────────


def active_profile() -> str:
    """Profile to use when the caller does not name one: env var, else default."""
    return os.environ.get(PROFILE_ENV, "").strip() or DEFAULT_PROFILE


def _check_profile(profile: str) -> str:
    """Normalise and validate a profile name."""
    name = (profile or "").strip()
    if not name:
        raise CredentialStoreError("profile name must not be empty")
    if name == _INDEX_ACCOUNT:
        raise CredentialStoreError(f"profile name {_INDEX_ACCOUNT!r} is reserved")
    if any(ch in name for ch in "\r\n\x00"):
        raise CredentialStoreError("profile name must not contain control characters")
    return name


def _account(profile: str) -> str:
    return f"{_ACCOUNT_PREFIX}{profile}"


def _read_index(module: Any) -> list[str]:
    """Stored profile names. Returns [] on any failure: the index is a cache."""
    try:
        raw = module.get_password(SERVICE, _INDEX_ACCOUNT)
    except Exception as exc:
        logger.debug("keychain index unreadable: %s", exc)
        return []
    if not raw:
        return []
    try:
        names = json.loads(raw)
    except (TypeError, ValueError):
        logger.debug("keychain index is not valid JSON, ignoring it")
        return []
    if not isinstance(names, list):
        return []
    return [str(n) for n in names if isinstance(n, str) and n]


def _write_index(module: Any, names: list[str]) -> None:
    ordered = sorted(set(names))
    try:
        if ordered:
            module.set_password(SERVICE, _INDEX_ACCOUNT, json.dumps(ordered))
        else:
            module.delete_password(SERVICE, _INDEX_ACCOUNT)
    except Exception as exc:
        # The index is a convenience for `list_profiles`; a failure here must
        # not undo a credential that stored fine.
        logger.debug("could not update keychain profile index: %s", exc)


def list_profiles() -> list[str]:
    """Sorted profile names known to the keychain. Never raises."""
    try:
        module = _load_keyring()
    except Exception:
        return []
    return sorted(_read_index(module))


# ── Read / write ────────────────────────────────────────────────────


def save(
    profile: str | None,
    uri: str,
    username: str,
    password: str,
    database: str = "neo4j",
) -> str:
    """Store one Neo4j credential set in the OS keychain.

    Returns the profile name written. Raises :class:`KeyringUnavailable` when
    there is nowhere to write: callers must surface that rather than pretend the
    credential was saved.
    """
    name = _check_profile(profile or active_profile())
    for field, value in (("uri", uri), ("username", username), ("password", password)):
        if not (value or "").strip():
            raise CredentialStoreError(f"{field} must not be empty")

    record = {
        "uri": uri.strip(),
        "username": username.strip(),
        "password": password,
        "database": (database or "neo4j").strip() or "neo4j",
    }
    module = _load_keyring()
    # Never log `record`: it holds the password.
    module.set_password(SERVICE, _account(name), json.dumps(record))
    _write_index(module, [*_read_index(module), name])
    logger.info("stored Neo4j credentials for profile %r in the OS keychain", name)
    return name


def load(profile: str | None = None) -> dict[str, str] | None:
    """Stored credentials for ``profile``, or None.

    Never raises. A missing ``keyring``, a locked keychain, a corrupt record, and
    "nothing stored" all return None, because every caller's next move is the
    same: fall through to the next configuration layer.
    """
    try:
        name = _check_profile(profile or active_profile())
        module = _load_keyring()
        raw = module.get_password(SERVICE, _account(name))
    except Exception as exc:
        logger.debug("keychain lookup skipped: %s", exc)
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("keychain record for profile %r is not valid JSON, ignoring", name)
        return None
    if not isinstance(data, dict):
        return None
    record = {
        field: str(data[field])
        for field in FIELDS
        if isinstance(data.get(field), str) and data[field]
    }
    return record or None


def delete(profile: str | None = None) -> bool:
    """Remove one profile's credentials. True when something was removed."""
    name = _check_profile(profile or active_profile())
    module = _load_keyring()
    removed = False
    try:
        module.delete_password(SERVICE, _account(name))
        removed = True
    except Exception as exc:
        # keyring raises PasswordDeleteError when the entry is simply absent,
        # which is not an error worth propagating from a logout.
        logger.debug("no keychain entry to delete for profile %r: %s", name, exc)
    remaining = [n for n in _read_index(module) if n != name]
    _write_index(module, remaining)
    if removed:
        logger.info("removed Neo4j credentials for profile %r", name)
    return removed


# ── Display ─────────────────────────────────────────────────────────


def mask(field: str, value: str) -> str:
    """Render a field value for display, hiding the secret ones."""
    if field in SECRET_FIELDS:
        return "(set, hidden)" if value else "(empty)"
    return value
