"""Suite-wide fixtures.

One job so far: keep the test suite away from the developer's real OS keychain.

`load_config()` consults the keychain (see `wheeler.config._apply_keychain_overrides`),
so without this guard a machine where someone had actually run `wheeler login`
would feed real Aura credentials into every config test, and precedence
assertions would pass or fail depending on whose laptop ran them. Setting
`WHEELER_NO_KEYCHAIN` makes `wheeler.credentials` refuse to touch any backend at
all, so no real credential is ever read and none is ever written.

Tests that need the store exercised patch `wheeler.credentials._load_keyring`
with an in-memory stub, which bypasses this switch deliberately. Tests that need
the switch itself under test override the env var with their own monkeypatch,
which wins because this fixture is function-scoped and runs first.
"""

from __future__ import annotations

import pytest

from wheeler import credentials
from wheeler.config import reset_keychain_cache


@pytest.fixture(autouse=True)
def _no_real_keychain(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(credentials.DISABLE_ENV, "1")
    monkeypatch.delenv(credentials.PROFILE_ENV, raising=False)
    # The keychain lookup is cached per process, so a record read (or stubbed) by
    # one test must not survive into the next.
    reset_keychain_cache()
    yield
    reset_keychain_cache()
