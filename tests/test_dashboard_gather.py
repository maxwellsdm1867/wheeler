"""Tests for the dashboard gather helpers (pure functions + local state I/O).

These do not touch Neo4j. The async gather_dashboard_data path is exercised by
the optional live smoke test.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from wheeler.dashboard.gather import (
    _figure_from_id,
    attach_notes,
    rank_results,
    read_notes,
    read_pins,
    select_figures,
    select_open_plans,
    split_pinned,
    write_notes,
    write_pins,
)


def _config(tmp_path, ptag=""):
    return SimpleNamespace(
        project_root=str(tmp_path),
        knowledge_path="knowledge",
        neo4j=SimpleNamespace(project_tag=ptag),
    )


def test_rank_results_orders_fresh_high_confidence_first():
    findings = [
        {"id": "F-a", "confidence": 0.2, "stability": 0.5, "stale": False},
        {"id": "F-b", "confidence": 0.9, "stability": 0.5, "stale": False},
        {"id": "F-c", "confidence": 0.9, "stability": 0.5, "stale": True},
    ]
    ranked = [f["id"] for f in rank_results(findings)]
    assert ranked == ["F-b", "F-a", "F-c"]  # stale sinks; high conf rises


def test_select_open_plans_filters_status():
    plans = [
        {"id": "PL-1", "status": "in-progress"},
        {"id": "PL-2", "status": "completed"},
        {"id": "PL-3", "status": "approved"},
        {"id": "PL-4", "status": "draft"},
    ]
    assert [p["id"] for p in select_open_plans(plans)] == ["PL-1", "PL-3"]


def test_select_figures_requires_type_and_existing_path(tmp_path):
    (tmp_path / "real.png").write_bytes(b"x")
    findings = [
        {"id": "F-1", "artifact_type": "figure", "path": "real.png"},
        {"id": "F-2", "artifact_type": "figure", "path": "missing.png"},
        {"id": "F-3", "artifact_type": "number", "path": "real.png"},
        {"id": "F-4", "artifact_type": "figure", "path": ""},
    ]
    assert [f["id"] for f in select_figures(findings, tmp_path)] == ["F-1"]


def test_split_pinned_preserves_pin_order_and_drops_dangling():
    figures = [{"id": "F-1"}, {"id": "F-2"}, {"id": "F-3"}]
    hero, rest = split_pinned(figures, ["F-3", "F-ghost", "F-1"])
    assert [f["id"] for f in hero] == ["F-3", "F-1"]
    assert [f["id"] for f in rest] == ["F-2"]


def test_attach_notes_sets_note():
    figs = [{"id": "F-1"}, {"id": "F-2"}]
    attach_notes(figs, {"F-1": "hello"})
    assert figs[0]["note"] == "hello"
    assert "note" not in figs[1]


def test_attach_notes_does_not_alias_results():
    # The same finding dict can sit in both the figures list and the results
    # list; attaching a note must not mutate the shared object in results.
    shared = {"id": "F-1", "artifact_type": "figure"}
    figures = [shared]
    results = [shared]
    attach_notes(figures, {"F-1": "a note"})
    assert figures[0]["note"] == "a note"
    assert "note" not in results[0]  # results untouched
    assert results[0] is shared


def test_read_pins_rejects_other_project_tag(tmp_path):
    write_pins(_config(tmp_path, ptag="alpha"), ["F-1"])
    # Same tag: visible.
    assert read_pins(_config(tmp_path, ptag="alpha")) == ["F-1"]
    # Different tag: hidden (do not render another namespace's pins).
    assert read_pins(_config(tmp_path, ptag="beta")) == []


def test_read_pins_legacy_file_without_tag(tmp_path):
    d = Path(tmp_path) / ".wheeler" / "dashboard"
    d.mkdir(parents=True)
    (d / "pins.json").write_text('{"pins": ["F-9"]}', encoding="utf-8")
    assert read_pins(_config(tmp_path, ptag="anything")) == ["F-9"]


def test_figure_from_id_loads_pinned_figure(tmp_path):
    kp = tmp_path / "knowledge"
    kp.mkdir()
    (tmp_path / "fig.png").write_bytes(b"x")
    (kp / "F-old.json").write_text(
        '{"id": "F-old", "type": "Finding", "artifact_type": "figure", '
        '"path": "fig.png", "title": "Old fig"}',
        encoding="utf-8",
    )
    f = _figure_from_id(kp, "F-old", Path(tmp_path))
    assert f is not None and f["id"] == "F-old" and f["title"] == "Old fig"
    # A non-figure or missing-file id returns None.
    assert _figure_from_id(kp, "F-missing", Path(tmp_path)) is None


def test_pins_roundtrip_atomic(tmp_path):
    config = _config(tmp_path, ptag="proj")
    assert read_pins(config) == []
    write_pins(config, ["F-1", "F-2"])
    assert read_pins(config) == ["F-1", "F-2"]
    pins_file = Path(tmp_path) / ".wheeler" / "dashboard" / "pins.json"
    assert pins_file.exists()
    assert '"project_tag": "proj"' in pins_file.read_text()


def test_notes_roundtrip(tmp_path):
    config = _config(tmp_path)
    assert read_notes(config) == {}
    write_notes(config, {"F-1": "a note"})
    assert read_notes(config) == {"F-1": "a note"}


def test_read_state_tolerates_corrupt_file(tmp_path):
    config = _config(tmp_path)
    d = Path(tmp_path) / ".wheeler" / "dashboard"
    d.mkdir(parents=True)
    (d / "pins.json").write_text("{ not json", encoding="utf-8")
    assert read_pins(config) == []
