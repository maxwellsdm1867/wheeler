"""Asta integration slice (Paper Finder + Theorizer + Semantic Scholar).

Public surface:
  - ``ingest_paper_finder``: deterministic marshal-out for Asta Paper Finder.
  - ``ingest_theorizer``: deterministic marshal-out for Asta Theorizer.
  - ``ingest_semantic_scholar``: deterministic marshal-out for Asta Semantic
    Scholar REST output (get / search / citations / snippet, auto-detected).
  - ``register_output_artifact``: register a service's raw ``-o`` output file.
  - ``ImportReport``: the outcome of one ingest run.

The chokepoint rule: the marshal-out modules are the only ones that import
``execute_tool`` (lazily), and ``transport`` is the only module that shells
out to the asta CLI. ``transport`` has no graph dependency; nothing here
imports anthropic.
"""

from __future__ import annotations

from .artifacts import register_output_artifact
from .ingest import ImportReport, ingest_paper_finder
from .semantic_scholar import ingest_semantic_scholar
from .theorizer import ingest_theorizer

__all__ = [
    "ImportReport",
    "ingest_paper_finder",
    "ingest_semantic_scholar",
    "ingest_theorizer",
    "register_output_artifact",
]
