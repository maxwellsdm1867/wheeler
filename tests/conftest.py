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

import os

import pytest

from wheeler import credentials
from wheeler.config import reset_keychain_cache


# The e2e tests run against this project's real graph, which is the cloud
# instance the `aura-wheeler` keychain slot names. It is a sandbox holding no
# research data, and an e2e test that exercises the real deployment (TLS, WAN
# latency, the transient-retry path a local instance never triggers) is worth
# more than one against a local stand-in.
#
# Unit tests still get no keychain. Not for data safety, but because a unit test
# is supposed to be hermetic and fast: without this, importing any mcp_* module
# resolves the real config at module scope (`mcp_shared.py` calls `load_config()`
# there), and hundreds of mocked tests start opening TLS connections over the
# WAN. Live tests opt in through `e2e_neo4j_config()` below.
os.environ[credentials.DISABLE_ENV] = "1"


@pytest.fixture(autouse=True)
def _no_real_keychain(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(credentials.DISABLE_ENV, "1")
    monkeypatch.delenv(credentials.PROFILE_ENV, raising=False)
    # The keychain lookup is cached per process, so a record read (or stubbed) by
    # one test must not survive into the next.
    reset_keychain_cache()
    yield
    reset_keychain_cache()


def stored_path_on_disk(stored: str):
    """Resolve a path as stored in the graph, for reachability assertions.

    Graph paths are portable (``${PROJECT}/...``) whenever they sit under a
    configured root, so ``Path(node["path"]).exists()`` is False for a file that
    is perfectly reachable. That is the contract, not a bug: nothing may touch
    disk with a stored path without resolving it first. Tests assert reachability
    through here so they check the property they actually mean.

    Returns the resolved ``Path``, or ``None`` when the value names a root this
    machine does not configure.
    """
    from wheeler.config import load_config
    from wheeler.portability import resolve

    return resolve(stored, load_config().resolved_roots)


def e2e_neo4j_config():
    """The graph an e2e test runs against: this project's real one.

    Reads the keychain directly rather than through the process env, because the
    blanket `WHEELER_NO_KEYCHAIN` above keeps unit tests hermetic and would
    otherwise send e2e to a localhost that this project no longer uses.
    """
    from wheeler import credentials
    from wheeler.config import load_config

    was_disabled = os.environ.pop(credentials.DISABLE_ENV, None)
    try:
        from wheeler.config import reset_keychain_cache

        reset_keychain_cache()
        return load_config()
    finally:
        if was_disabled is not None:
            os.environ[credentials.DISABLE_ENV] = was_disabled
        from wheeler.config import reset_keychain_cache as _reset

        _reset()
