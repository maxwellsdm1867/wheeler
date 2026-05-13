"""Wheeler: A thinking partner for scientists."""

import logging
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("wheeler")
except Exception:
    __version__ = "0.0.0"

# Incremented when the knowledge JSON schema changes in a backwards-incompatible way.
# Restore gates on this: archive schema_version must equal the recipient's value.
KNOWLEDGE_SCHEMA_VERSION = "1"

# Library pattern: NullHandler prevents "No handlers found" warnings
# when Wheeler is imported without configuring logging.
logging.getLogger("wheeler").addHandler(logging.NullHandler())
