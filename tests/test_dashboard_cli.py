"""Typer CliRunner tests for the `wheeler dashboard` command surface.

Pin/unpin/note touch only local files (no Neo4j). The render callback's graph
read is monkeypatched so the wiring is testable offline.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import wheeler.dashboard as dashboard_pkg
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


def test_dashboard_note_set_and_clear(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)

    r = runner.invoke(cli.app, ["dashboard", "note", "F-9", "headline result"])
    assert r.exit_code == 0
    notes_file = Path(tmp_path) / ".wheeler" / "dashboard" / "notes.json"
    assert "headline result" in notes_file.read_text()

    r = runner.invoke(cli.app, ["dashboard", "notes"])
    assert "F-9" in r.stdout

    r = runner.invoke(cli.app, ["dashboard", "note", "F-9"])
    assert r.exit_code == 0
    assert "headline result" not in notes_file.read_text()


def test_dashboard_render_writes_file(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)

    async def fake_gather(config, *, limit=12, plan_id=None):
        return {
            "schema_version": 1,
            "title": "Wheeler Research Dashboard",
            "generated": "2026-06-20T14:00:00Z",
            "project": "",
            "meta": {"project_root": str(tmp_path)},
            "counts": {"Finding": 0, "OpenQuestion": 0, "Plan": 0},
            "hero": [],
            "questions": [],
            "plans": [],
            "results": [],
            "figures": [],
            "notes": {},
        }

    monkeypatch.setattr(dashboard_pkg, "gather_dashboard_data", fake_gather)

    out = tmp_path / "dash.html"
    r = runner.invoke(cli.app, ["dashboard", "-o", str(out)])
    assert r.exit_code == 0, r.stdout
    assert out.exists()
    assert "<!DOCTYPE html>" in out.read_text()


def test_dashboard_render_neo4j_down_writes_nothing(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)

    async def boom(config, *, limit=12, plan_id=None):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(dashboard_pkg, "gather_dashboard_data", boom)

    out = tmp_path / "dash.html"
    r = runner.invoke(cli.app, ["dashboard", "-o", str(out)])
    assert r.exit_code == 1
    assert not out.exists()
    assert "Neo4j" in r.stdout or "graph" in r.stdout
