"""External-tool integration namespace.

This is the generic namespace package for external-tool adapters. Each tool
lives in its own self-contained sub-package (for example ``asta`` for the Asta
Paper Finder and Theorizer slices). A future generic contract engine will live
at this top level; for now the only sub-package is ``asta``.

No exports here on purpose: import from the concrete sub-package, for example
``from wheeler.integrations.asta import ImportReport, ingest_paper_finder``.
"""

from __future__ import annotations
