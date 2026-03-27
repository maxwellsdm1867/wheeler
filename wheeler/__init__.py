"""Wheeler: A thinking partner for scientists."""

import logging

__version__ = "0.3.0"

# Library pattern: NullHandler prevents "No handlers found" warnings
# when Wheeler is imported without configuring logging.
logging.getLogger("wheeler").addHandler(logging.NullHandler())
