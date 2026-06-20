"""Offline, dict-driven tests for the dashboard renderer (no Neo4j needed)."""
from __future__ import annotations

import base64

from wheeler.dashboard.render import (
    alt_text,
    embed_figure,
    linkify_nodes,
    node_badge,
    render,
)

# 1x1 transparent PNG (same trick as test_render_brief.py).
PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _base_data(**over):
    data = {
        "schema_version": 1,
        "title": "Test Dashboard",
        "generated": "2026-06-20T14:00:00Z",
        "project": "",
        "meta": {"project_root": "."},
        "counts": {"Finding": 3, "OpenQuestion": 2, "Plan": 1},
        "hero": [],
        "questions": [],
        "plans": [],
        "results": [],
        "figures": [],
        "notes": {},
    }
    data.update(over)
    return data


def test_renders_four_zones():
    html, missing = render(
        _base_data(
            questions=[{"id": "Q-1111", "question": "Why?", "priority": 9}],
            plans=[{"id": "PL-2222", "title": "My plan", "status": "in-progress", "updated": ""}],
            results=[{"id": "F-3333", "description": "A result", "confidence": 0.8}],
        )
    )
    assert "Open Questions" in html
    assert "Open Plans" in html
    assert "Major Results" in html
    assert "Figures" in html
    assert "Q-1111" in html and "PL-2222" in html and "F-3333" in html
    assert missing == []


def test_empty_graph_empty_states():
    html, missing = render(_base_data())
    assert "No open questions recorded yet." in html
    assert "No open plans" in html
    assert "No findings recorded yet." in html
    assert "No result figures yet." in html
    assert missing == []


def test_escapes_html_and_xss():
    html, _ = render(
        _base_data(results=[{"id": "F-9999", "description": "<script>alert('x')</script> & <b>", "confidence": 0.5}])
    )
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_node_ids_become_badges():
    html, _ = render(
        _base_data(questions=[{"id": "Q-1111", "question": "See [F-abcd] for context", "priority": 5}])
    )
    assert 'class="node-id t-F"' in html
    assert "F-abcd" in html


def test_embeds_png_as_base64(tmp_path):
    fig = tmp_path / "result.png"
    fig.write_bytes(PNG_1x1)
    html, missing = render(
        _base_data(
            meta={"project_root": str(tmp_path)},
            figures=[{"id": "F-7777", "title": "Result", "path": "result.png", "description": "cap"}],
        )
    )
    assert "data:image/png;base64," in html
    assert missing == []


def test_missing_figure_placeholder():
    html, missing = render(
        _base_data(figures=[{"id": "F-8888", "title": "Gone", "path": "nope.png"}])
    )
    assert "Figure file not found" in html
    assert "nope.png" in missing


def test_interactive_html_figure_is_sandboxed_iframe(tmp_path):
    fig = tmp_path / "plot.html"
    fig.write_text("<html><body><script>1+1</script>plot</body></html>", encoding="utf-8")
    html, missing = render(
        _base_data(
            meta={"project_root": str(tmp_path)},
            hero=[{"id": "F-aaaa", "title": "Live plot", "path": "plot.html"}],
        )
    )
    assert "<iframe" in html
    assert 'sandbox="allow-scripts"' in html
    assert "srcdoc=" in html
    # the inner double-quote-free content is preserved; ampersands escaped
    assert missing == []


def test_svg_is_data_uri_not_inlined(tmp_path):
    svg = tmp_path / "fig.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>evil()</script></svg>', encoding="utf-8")
    html, _ = render(
        _base_data(
            meta={"project_root": str(tmp_path)},
            figures=[{"id": "F-bbbb", "title": "vec", "path": "fig.svg"}],
        )
    )
    assert "data:image/svg+xml;base64," in html
    # raw <script> from the SVG must not appear unescaped in the page
    assert "<script>evil()" not in html


def test_hero_section_only_when_pinned(tmp_path):
    fig = tmp_path / "h.png"
    fig.write_bytes(PNG_1x1)
    html_no, _ = render(_base_data())
    assert "Main Figures" not in html_no
    html_yes, _ = render(
        _base_data(
            meta={"project_root": str(tmp_path)},
            hero=[{"id": "F-cccc", "title": "Hero", "path": "h.png"}],
        )
    )
    assert "Main Figures" in html_yes


def test_figure_note_rendered_and_escaped(tmp_path):
    fig = tmp_path / "n.png"
    fig.write_bytes(PNG_1x1)
    html, _ = render(
        _base_data(
            meta={"project_root": str(tmp_path)},
            figures=[{"id": "F-dddd", "title": "N", "path": "n.png", "note": "key <result>"}],
        )
    )
    assert 'data-figid="F-dddd"' in html
    assert "key &lt;result&gt;" in html


def test_byte_stability():
    data = _base_data(
        questions=[{"id": "Q-1", "question": "q", "priority": 3}],
        results=[{"id": "F-1", "description": "d", "confidence": 0.7}],
    )
    h1, _ = render(data)
    h2, _ = render(data)
    assert h1 == h2


def test_theme_supports_auto():
    html, _ = render(_base_data())
    assert 'data-theme="auto"' in html
    assert "prefers-color-scheme: dark" in html


def test_refresh_button_and_graph_provenance():
    html, _ = render(_base_data())
    # A refresh control that reloads the file from disk.
    assert 'id="refresh"' in html
    assert "location.reload()" in html
    # Clear that the page is generated from the graph, with the regenerate command.
    assert "Snapshot of the knowledge graph" in html
    assert "<code>wheeler dashboard</code>" in html


def test_node_badges_are_copyable():
    html, _ = render(
        _base_data(questions=[{"id": "Q-1111", "question": "q?", "priority": 5}])
    )
    # Badge carries the id and copy affordances; the JS wires click + right-click.
    assert 'data-nodeid="Q-1111"' in html
    assert 'role="button"' in html and 'tabindex="0"' in html
    assert "Copy reference" in html and "Copy node id" in html
    assert 'id="nodemenu"' in html and 'id="toast"' in html


def test_helpers():
    assert 'data-nodeid="Q-1234"' in node_badge("Q-1234")
    assert 'class="node-id t-Q"' in node_badge("Q-1234")
    assert "&lt;b&gt;" in linkify_nodes("<b>")
    assert alt_text({"title": "T"}) == "T"
    assert alt_text({"description": "d" * 300}) == "d" * 120
    assert alt_text({"id": "F-1"}) == "Figure F-1"


def test_embed_figure_missing_appends(tmp_path):
    missing: list[str] = []
    out = embed_figure("ghost.png", tmp_path, "alt", "title", {"used": 0}, missing)
    assert "not found" in out
    assert missing == ["ghost.png"]
