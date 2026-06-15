"""External-tool integrations (marshal-in act prose, marshal-out Python).

Public surface:
  - ``ingest_paper_finder``: deterministic marshal-out for Asta Paper Finder.
  - ``ImportReport``: the outcome of one ingest run.

The chokepoint rule: ``ingest`` is the only module that imports
``execute_tool`` (lazily), and ``transport`` is the only module that shells
out to the asta CLI. ``transport`` has no graph dependency; nothing here
imports anthropic.
"""

from __future__ import annotations

from .ingest import ImportReport, ingest_paper_finder

__all__ = ["ImportReport", "ingest_paper_finder"]
