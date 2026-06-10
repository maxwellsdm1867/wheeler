"""Unit tests for the wheeler-brief render script.

The script lives under .claude/skills/wheeler-brief/ (a dev-only, gitignored skill),
so these tests skip cleanly on a checkout that does not include it. The script is
deterministic and stdlib-only, which is exactly what makes it worth pinning here: the
spec-to-HTML contract should not drift silently.
"""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".claude/skills/wheeler-brief/scripts/render_brief.py"

pytestmark = pytest.mark.skipif(
    not SCRIPT.exists(), reason="wheeler-brief skill not present in this checkout"
)

# A 1x1 transparent PNG, enough to exercise base64 embedding.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _load_module():
    spec = importlib.util.spec_from_file_location("render_brief", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_spec(tmp_path: Path) -> dict:
    return {
        "spec_version": 1,
        "mode": "plan",
        "investigation": "demo-investigation",
        "plan_path": ".plans/demo.md",
        "plan_node": "PL-abcd1234",
        "plan_status": "approved",
        "generated": "2026-06-10T12:00:00Z",
        "question": "Does the widget frobnicate under <stress> & load?",
        "rationale": {"summary": "Because [F-1111] suggests it might.", "scientific_reasoning": None},
        "data_sources": [
            {"id": "D-2222", "type": "Dataset", "title": "Bench runs", "path": "data/x.csv",
             "status": "active", "role": "upstream"}
        ],
        "relations": [{"source": "PL-abcd1234", "rel": "USED", "target": "D-2222", "note": None}],
        "game_plan": {
            "decisions": [{"text": "Pick the threshold", "task": 1, "resolution": None}],
            "tasks": [{"n": 1, "title": "Run the bench", "wave": 1, "assignee": "wheeler",
                       "type": "code", "depends_on": [], "checkpoint": None, "status": "pending"}],
        },
        "success_criteria": [{"text": "Frob rate > 0.5", "status": "PENDING", "evidence": None}],
        "figures": [
            {"id": "fig_A", "title": "Frob vs load", "caption": "One point per run.",
             "expected_trend": "Rises then saturates.",
             "mockup_svg": '<svg viewBox="0 0 480 320"><line x1="60" y1="270" x2="440" y2="270" stroke="currentColor"/></svg>',
             "image_path": None, "figure_node": None, "status": "planned"}
        ],
        "meta": {"project_root": str(tmp_path), "export_dir": None, "summary_path": None,
                 "history": [{"mode": "plan", "generated": "2026-06-10T12:00:00Z"}]},
    }


def test_renders_plan_brief(tmp_path):
    mod = _load_module()
    spec_path = tmp_path / "demo-investigation.json"
    spec_path.write_text(json.dumps(_base_spec(tmp_path)))

    rc = mod.main([str(spec_path)])
    assert rc == 0

    out = (tmp_path / "demo-investigation.html").read_text()
    # question is HTML-escaped (the & and angle brackets must not be raw)
    assert "&amp;" in out and "&lt;stress&gt;" in out
    assert "<script>alert" not in out
    # the inline mockup SVG is present, and a node id became a badge
    assert "<svg viewBox" in out
    assert "PL-abcd1234" in out
    # leads with question, then goes straight to figures, then the execution plan
    assert out.index('id="sec-question"') < out.index('id="sec-figures"') < out.index('id="sec-gameplan"')


def test_embeds_png_as_base64(tmp_path):
    mod = _load_module()
    png = tmp_path / "fig_a.png"
    png.write_bytes(PNG_1X1)
    spec = _base_spec(tmp_path)
    spec["mode"] = "execution"
    spec["figures"][0]["image_path"] = "fig_a.png"
    spec["figures"][0]["status"] = "produced"
    spec_path = tmp_path / "demo-investigation.json"
    spec_path.write_text(json.dumps(spec))

    rc = mod.main([str(spec_path)])
    assert rc == 0
    out = (tmp_path / "demo-investigation.html").read_text()
    assert "data:image/png;base64," in out
    assert "fig-body paired" in out  # mockup + actual shown side by side


def test_missing_image_exits_2_with_placeholder(tmp_path):
    mod = _load_module()
    spec = _base_spec(tmp_path)
    spec["mode"] = "execution"
    spec["figures"][0]["image_path"] = "does_not_exist.png"
    spec["figures"][0]["status"] = "produced"
    spec_path = tmp_path / "demo-investigation.json"
    spec_path.write_text(json.dumps(spec))

    rc = mod.main([str(spec_path)])
    assert rc == 2
    out = (tmp_path / "demo-investigation.html").read_text()
    assert "fig-placeholder" in out


def test_unknown_spec_version_exits_1_and_writes_nothing(tmp_path):
    mod = _load_module()
    spec = _base_spec(tmp_path)
    spec["spec_version"] = 99
    spec_path = tmp_path / "demo-investigation.json"
    spec_path.write_text(json.dumps(spec))

    rc = mod.main([str(spec_path)])
    assert rc == 1
    assert not (tmp_path / "demo-investigation.html").exists()


def test_sub_questions_render_under_question(tmp_path):
    mod = _load_module()
    spec = _base_spec(tmp_path)
    spec["sub_questions"] = [
        "Does A match B?",
        {"text": "Is the cost type-blind?", "node": "Q-9999"},
    ]
    spec_path = tmp_path / "demo-investigation.json"
    spec_path.write_text(json.dumps(spec))

    rc = mod.main([str(spec_path)])
    assert rc == 0
    out = (tmp_path / "demo-investigation.html").read_text()
    assert "subq-list" in out
    assert "Does A match B?" in out
    assert "Q-9999" in out
    # sub-questions sit inside the question section, before figures
    assert out.index("subq-list") < out.index('id="sec-figures"')


def test_panels_render_one_column_per_panel(tmp_path):
    mod = _load_module()
    spec = _base_spec(tmp_path)
    spec["figures"][0]["panels"] = [
        {"title": "1. What", "text": "the read-out"},
        {"title": "2. Test", "text": "the comparison"},
        {"title": "3. Power", "text": "the floor"},
    ]
    spec_path = tmp_path / "demo-investigation.json"
    spec_path.write_text(json.dumps(spec))

    rc = mod.main([str(spec_path)])
    assert rc == 0
    out = (tmp_path / "demo-investigation.html").read_text()
    assert "--panel-cols: 3" in out
    assert out.count('class="panel-card"') == 3
