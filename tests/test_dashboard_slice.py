"""End-to-end vertical slice for the dashboard.

This exercises the whole render pipeline against a realistic payload, the same
dict shape ``gather_dashboard_data`` produces (inferred from the function's
return value): counts, hero (pinned) figures, open questions, open plans, ranked
results, unpinned figures, and durable notes. It writes a real HTML file so the
artifact can be opened and eyeballed, and asserts the full slice end to end:

  payload  ->  render()  ->  self-contained HTML on disk

It covers both figure kinds the renderer supports: a static PNG (base64 data
URI) and an interactive HTML figure (sandboxed iframe), with one pinned as a
hero figure and a durable note attached.
"""
from __future__ import annotations

import base64
from pathlib import Path

from wheeler.dashboard.render import render

PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

# A minimal but real standalone interactive figure (what a Plotly/Bokeh export
# looks like in spirit: self-contained HTML with an inline script).
INTERACTIVE_HTML = (
    "<!doctype html><html><body>"
    "<div id='chart'>interactive</div>"
    "<script>document.getElementById('chart').title = 'live';</script>"
    "</body></html>"
)


def _realistic_payload(root: Path) -> dict:
    """Build the exact dict shape gather_dashboard_data returns, with real files."""
    figdir = root / "analysis_exports" / "pilot_2026-06-20" / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    png = figdir / "pilot_2026-06-20_fig_A_scaling.png"
    png.write_bytes(PNG_1x1)
    interactive = figdir / "pilot_2026-06-20_fig_B_interactive.html"
    interactive.write_text(INTERACTIVE_HTML, encoding="utf-8")

    hero_fig = {
        "id": "F-aaaa1111",
        "title": "fig_A scaling curve",
        "path": str(png.relative_to(root)),
        "confidence": 0.86,
        "description": "Adaptation index scales 2x with firing rate. See [F-bbbb2222].",
        "note": "Headline figure for the pilot.",
    }
    interactive_fig = {
        "id": "F-cccc3333",
        "title": "fig_B interactive explorer",
        "path": str(interactive.relative_to(root)),
        "confidence": 0.72,
        "description": "Interactive sweep across stimulus conditions.",
    }
    return {
        "schema_version": 1,
        "title": "Wheeler Research Dashboard",
        "generated": "2026-06-20T14:00:00Z",
        "project": "pilot",
        "meta": {"project_root": str(root)},
        "counts": {"Finding": 42, "OpenQuestion": 7, "Plan": 3},
        "hero": [hero_fig],
        "questions": [
            {"id": "Q-1111aaaa", "question": "Does density set oscillation frequency?", "priority": 9, "tier": "generated"},
            {"id": "Q-2222bbbb", "question": "Is the 2x scaling robust to noise [F-aaaa1111]?", "priority": 6, "tier": "generated"},
        ],
        "plans": [
            {"id": "PL-3333cccc", "title": "Operating margin pilot", "status": "in-progress",
             "path": ".plans/operating_margin_pilot.md", "updated": "2026-06-18T10:00:00Z", "tier": "generated"},
            {"id": "PL-4444dddd", "title": "Noise robustness sweep", "status": "approved",
             "path": ".plans/noise_sweep.md", "updated": "2026-06-15T09:00:00Z", "tier": "generated"},
        ],
        "results": [
            {"id": "F-aaaa1111", "title": "fig_A scaling curve", "description": "2x scaling confirmed.",
             "confidence": 0.86, "tier": "generated", "stale": False, "stability": 0.4},
            {"id": "F-bbbb2222", "title": "baseline drift", "description": "Baseline drifts under 1%.",
             "confidence": 0.6, "tier": "reference", "stale": True, "stability": 0.8},
        ],
        "figures": [interactive_fig],
        "notes": {"F-aaaa1111": "Headline figure for the pilot."},
    }


def test_vertical_slice_renders_full_dashboard(tmp_path):
    payload = _realistic_payload(tmp_path)
    html, missing = render(payload)

    # Nothing missing: both figure files resolved and embedded.
    assert missing == [], missing

    # All four zones + hero present and populated.
    assert "Main Figures" in html
    assert "Open Questions" in html and "Q-1111aaaa" in html
    assert "Open Plans" in html and "PL-3333cccc" in html
    assert "Major Results" in html and "F-bbbb2222" in html
    assert "Figures" in html

    # Both figure kinds embedded the right way.
    assert "data:image/png;base64," in html          # static PNG hero
    assert "<iframe" in html and 'sandbox="allow-scripts"' in html  # interactive

    # Counts strip, project label, theme, durable note, and node badges.
    assert "42" in html and "findings" in html
    assert "project: pilot" in html
    assert 'data-theme="auto"' in html
    assert "Headline figure for the pilot." in html
    assert 'class="node-id t-F"' in html

    # Determinism: identical bytes on a second render.
    again, _ = render(payload)
    assert again == html

    # Write the real artifact so it can be opened/inspected.
    out = tmp_path / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    assert out.exists() and out.stat().st_size > 2000


if __name__ == "__main__":
    # Manual run: emit a sample artifact next to this file for eyeballing.
    import tempfile

    d = Path(tempfile.mkdtemp())
    html, _ = render(_realistic_payload(d))
    out = Path("dashboard_sample.html")
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out.resolve()}")
