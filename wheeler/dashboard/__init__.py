"""Read-only HTML research dashboard for a Wheeler investigation.

A static, self-contained, interactive overview of the most recent progress
across the whole knowledge graph: open questions, open plans, major results, and
result figures (pinnable as hero figures, with per-figure notes and an infinite
canvas). Rendered on demand by the ``wheeler dashboard`` CLI command.

- ``gather_dashboard_data(config)`` reads the graph and builds the data dict.
- ``render(data)`` turns that dict into one self-contained HTML string (pure,
  stdlib-only, deterministic).
"""
from __future__ import annotations

from wheeler.dashboard.gather import gather_dashboard_data
from wheeler.dashboard.render import render

__all__ = ["gather_dashboard_data", "render"]
