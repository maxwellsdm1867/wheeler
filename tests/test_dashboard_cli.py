"""Typer CliRunner tests for the `wheeler dashboard` command surface.

Pin/unpin/note touch only local files (no Neo4j). The render callback's graph
read is monkeypatched so the wiring is testable offline.
"""
from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

import wheeler.tools.cli as cli

runner = CliRunner()


def _patch_config(monkeypatch, tmp_path, ptag=""):
    config = SimpleNamespace(
        project_root=str(tmp_path),
        knowledge_path="knowledge",
        neo4j=SimpleNamespace(project_tag=ptag),
    )
    monkeypatch.setattr(cli, "load_config", lambda *a, **k: config)
    return config


def test_dashboard_pin_unpin_pins(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)

    r = runner.invoke(cli.app, ["dashboard", "pin", "F-1234"])
    assert r.exit_code == 0
    assert "Pinned" in r.stdout

    r = runner.invoke(cli.app, ["dashboard", "pins"])
    assert "F-1234" in r.stdout

    r = runner.invoke(cli.app, ["dashboard", "unpin", "F-1234"])
    assert r.exit_code == 0
    assert "Unpinned" in r.stdout

    r = runner.invoke(cli.app, ["dashboard", "pins"])
    assert "No pinned figures" in r.stdout


def test_dashboard_note_records_graph_note(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)
    import wheeler.dashboard.gather as g

    captured = {}

    async def fake_record(config, figure_id, text):
        captured["args"] = (figure_id, text)
        return "N-7"

    monkeypatch.setattr(g, "record_figure_note", fake_record)
    r = runner.invoke(cli.app, ["dashboard", "note", "F-9", "headline result"])
    assert r.exit_code == 0, r.stdout
    assert captured["args"] == ("F-9", "headline result")
    assert "N-7" in r.stdout and "F-9" in r.stdout


def test_dashboard_notes_lists_graph_notes(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)
    import wheeler.dashboard.gather as g

    async def fake_list(config):
        return [{"nid": "N-1", "fid": "F-9", "content": "a durable note"}]

    monkeypatch.setattr(g, "list_all_figure_notes", fake_list)
    r = runner.invoke(cli.app, ["dashboard", "notes"])
    assert r.exit_code == 0
    assert "N-1" in r.stdout and "F-9" in r.stdout


def test_dashboard_serves_live(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)
    import wheeler.dashboard.serve as serve_mod

    calls = {}

    def fake_render_live(config, limit=12):
        return "<!DOCTYPE html><html></html>"

    def fake_serve(config, *, host, port, limit, open_browser, on_start=None):
        calls["served"] = (host, port, limit)
        if on_start:
            on_start(f"http://{host}:{port}/")

    monkeypatch.setattr(serve_mod, "render_live", fake_render_live)
    monkeypatch.setattr(serve_mod, "serve", fake_serve)

    r = runner.invoke(cli.app, ["dashboard", "--no-open", "--port", "0"])
    assert r.exit_code == 0, r.stdout
    assert calls["served"][1] == 0
    assert "live at" in r.stdout.lower()


def test_dashboard_neo4j_down_does_not_serve(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)
    import wheeler.dashboard.serve as serve_mod

    def boom(config, limit=12):
        raise RuntimeError("connection refused")

    served = {"called": False}

    def fake_serve(*a, **k):
        served["called"] = True

    monkeypatch.setattr(serve_mod, "render_live", boom)
    monkeypatch.setattr(serve_mod, "serve", fake_serve)

    r = runner.invoke(cli.app, ["dashboard", "--no-open"])
    assert r.exit_code == 1
    assert served["called"] is False
    assert "Neo4j" in r.stdout or "graph" in r.stdout
