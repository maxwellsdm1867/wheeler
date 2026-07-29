"""Tests for the Asta mission harvest brief (the HTML page every harvest writes).

The Research Assistant is the long-horizon adapter: one harvest lands a whole
batch of outcomes, more than anyone can judge from a terminal summary. So the
harvest renders a page the scientist READS before deciding anything. It is a
pure, stdlib-only function over already-parsed values, so all of this runs
without Neo4j and without an assistant run.

Run: python -m pytest tests/integrations/asta/test_harvest_brief.py -q
"""

from __future__ import annotations

import struct
import zlib

from wheeler.integrations.asta.harvest_brief import (
    BRIEF_FILENAME,
    render_harvest_brief,
    write_harvest_brief,
)


def _png_bytes(width: int = 4, height: int = 4) -> bytes:
    """A minimal valid PNG, built in-process so no fixture binary is needed."""

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _item(**over):
    item = {
        "slug": "analyze-widget",
        "title": "Analyze the widget response under load",
        "verdict": "accomplished",
        "status": "done",
        "summary": "The widget response scales linearly with load.",
        "root_cause": "",
        "document_id": "W-aaaa1111",
        "data_ids": [],
        "data_files": [],
        "review_state": "undiscussed",
    }
    item.update(over)
    return item


def _render(**over):
    kwargs = {
        "title": "Investigate the widget response under load",
        "slug": "widget-mission-ab12cd34",
        "goal": "Investigate the widget response under load.",
        "background": "Prior work established a baseline.",
        "items": [_item()],
        "execution_id": "X-bbbb2222",
        "mission_document": "W-cccc3333",
        "link_to": "Q-dddd4444",
        "generated": "2026-07-25T12:00:00+00:00",
    }
    kwargs.update(over)
    return render_harvest_brief(**kwargs)


class TestSelfContained:
    """The page must open offline from anywhere: no external requests."""

    def test_is_a_complete_document(self):
        html = _render()
        assert html.startswith("<!doctype html>")
        assert html.rstrip().endswith("</html>")
        assert "<title>" in html

    def test_no_external_references(self):
        html = _render()
        for scheme in ("http://", "https://", "//cdn", "src=\"/"):
            assert scheme not in html, f"external reference {scheme!r} in the brief"

    def test_styles_are_inlined(self):
        html = _render()
        assert "<style>" in html
        assert "<link" not in html

    def test_renders_for_both_color_schemes(self):
        html = _render()
        assert "prefers-color-scheme:dark" in html


class TestContent:
    def test_leads_with_the_mission(self):
        html = _render()
        assert "Investigate the widget response under load" in html

    def test_shows_verdict_and_review_state(self):
        html = _render()
        assert "accomplished" in html
        assert "not discussed" in html

    def test_discussed_items_are_not_flagged_pending(self):
        html = _render(items=[_item(review_state="discussed")])
        # The CSS always defines the classes; what matters is that no element
        # USES them, so the card carries no pending pill or accent.
        assert 'class="pill pill-todo"' not in html
        assert 'class="card card-todo"' not in html
        assert "<b>0</b> not discussed" in html

    def test_counts_the_backlog(self):
        html = _render(items=[_item(), _item(slug="b", document_id="W-eeee5555")])
        assert "<b>2</b> work items" in html
        assert "<b>2</b> not discussed" in html

    def test_carries_the_node_ids(self):
        html = _render()
        for node_id in ("W-aaaa1111", "X-bbbb2222", "W-cccc3333", "Q-dddd4444"):
            assert node_id in html

    def test_batch_key_is_visible(self):
        assert "widget-mission-ab12cd34" in _render()

    def test_points_at_the_review_pass(self):
        html = _render()
        assert "/wh:discuss widget-mission-ab12cd34" in html

    def test_says_nothing_is_a_finding_yet(self):
        """The page must not imply the outcomes are endorsed results."""
        html = _render()
        assert "not an endorsed result" in html

    def test_fully_discussed_batch_changes_the_next_step(self):
        html = _render(items=[_item(review_state="discussed")])
        assert "has been discussed" in html

    def test_root_cause_is_collapsed_not_dropped(self):
        html = _render(items=[_item(verdict="partial", root_cause="The db lacked rows.")])
        assert "Root cause" in html
        assert "The db lacked rows." in html

    def test_empty_batch_says_so(self):
        html = _render(items=[])
        assert "nothing to review" in html

    def test_no_em_dashes(self):
        """Wheeler style: never an em dash in generated writing."""
        assert "—" not in _render()


class TestFigures:
    def test_embeds_an_image_artifact_inline(self, tmp_path):
        fig = tmp_path / "response.png"
        fig.write_bytes(_png_bytes())
        html = _render(items=[_item(data_files=[str(fig)], data_ids=["D-ffff6666"])])
        assert "data:image/png;base64," in html
        assert "response.png" in html
        assert "D-ffff6666" in html

    def test_non_image_artifacts_are_listed_not_embedded(self, tmp_path):
        csv = tmp_path / "widget.csv"
        csv.write_text("a,b\n1,2\n")
        html = _render(items=[_item(data_files=[str(csv)], data_ids=["D-ffff6666"])])
        assert "widget.csv" in html
        assert "data:image" not in html
        assert "1 more artifact<" in html

    def test_oversized_image_is_listed_not_embedded(self, tmp_path):
        """A huge frame must not turn the page into an unopenable blob."""
        from wheeler.integrations.asta import harvest_brief

        fig = tmp_path / "huge.png"
        fig.write_bytes(_png_bytes())
        html = _render(items=[_item(data_files=[str(fig)])])
        assert "data:image/png;base64," in html  # baseline: it does embed

        original = harvest_brief._MAX_IMAGE_BYTES
        harvest_brief._MAX_IMAGE_BYTES = 1
        try:
            html = _render(items=[_item(data_files=[str(fig)])])
        finally:
            harvest_brief._MAX_IMAGE_BYTES = original
        assert "data:image/png;base64," not in html
        assert "huge.png" in html  # still listed, never silently dropped

    def test_embed_cap_still_lists_the_rest(self, tmp_path):
        figs = []
        for i in range(15):
            fig = tmp_path / f"frame{i}.png"
            fig.write_bytes(_png_bytes())
            figs.append(str(fig))
        html = _render(items=[_item(data_files=figs)])
        assert html.count("data:image/png;base64,") == 12
        assert "frame14.png" in html

    def test_missing_artifact_file_does_not_raise(self, tmp_path):
        html = _render(items=[_item(data_files=[str(tmp_path / "gone.png")])])
        assert "gone.png" in html


class TestDefensive:
    """A rendering problem must never cost the scientist a harvest."""

    def test_escapes_html_in_mission_text(self):
        html = _render(title="<script>alert(1)</script>")
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_missing_fields_render_empty(self):
        html = render_harvest_brief(
            title="", slug="", goal="", background="", items=[{}]
        )
        assert "<!doctype html>" in html

    def test_none_items_render(self):
        html = render_harvest_brief(
            title="t", slug="s", goal="", background="", items=None
        )
        assert "nothing to review" in html

    def test_item_with_no_summary_says_so(self):
        html = _render(items=[_item(summary="")])
        assert "No result summary recorded." in html


class TestWrite:
    def test_writes_the_brief_beside_the_manifest(self, tmp_path):
        written = write_harvest_brief(tmp_path, "<!doctype html><html></html>")
        assert written == str(tmp_path / BRIEF_FILENAME)
        assert (tmp_path / BRIEF_FILENAME).read_text().startswith("<!doctype html>")

    def test_unwritable_directory_returns_none(self, tmp_path):
        missing = tmp_path / "no" / "such" / "dir"
        assert write_harvest_brief(missing, "<html></html>") is None

    def test_roundtrips_utf8(self, tmp_path):
        write_harvest_brief(tmp_path, "<html>åäö μ</html>")
        assert "μ" in (tmp_path / BRIEF_FILENAME).read_text(encoding="utf-8")
