"""Read-only HTML research dashboard for a Wheeler investigation.

A live, interactive overview of the most recent progress across the whole
knowledge graph: open questions, open plans, major results, and result figures
(pinnable as hero figures, with copyable node badges, per-figure notes, and an
infinite canvas). ``wheeler dashboard`` serves it from a tiny local HTTP server
that re-queries the graph on every load, so Refresh always shows current data.

- ``gather_dashboard_data(config)`` reads the graph and builds the data dict.
- ``render(data)`` turns that dict into one self-contained HTML string (pure,
  stdlib-only, deterministic).
- ``serve`` (in ``serve.py``) wraps both in a stdlib server, no web framework.
"""
from __future__ import annotations

from wheeler.dashboard.gather import gather_dashboard_data
from wheeler.dashboard.render import render

__all__ = ["gather_dashboard_data", "render"]
