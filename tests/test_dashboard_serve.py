"""Smoke test for the live dashboard server (real socket, no Neo4j).

Starts the actual ThreadingHTTPServer on an ephemeral port with ``render_live``
monkeypatched, makes a real HTTP request, and asserts the live page comes back.
This exercises the end-to-end serving path that ``wheeler dashboard`` uses.
"""
from __future__ import annotations

import threading
import urllib.request
from types import SimpleNamespace

import wheeler.dashboard.serve as serve_mod


def _config(tmp_path):
    return SimpleNamespace(
        project_root=str(tmp_path),
        knowledge_path="knowledge",
        neo4j=SimpleNamespace(project_tag=""),
    )


def test_live_server_serves_rendered_page(monkeypatch, tmp_path):
    monkeypatch.setattr(
        serve_mod,
        "render_live",
        lambda config, limit=12: "<!DOCTYPE html><html><body>live dashboard</body></html>",
    )

    httpd = serve_mod.make_server(_config(tmp_path), "127.0.0.1", 0, 12)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8")
        assert "<!DOCTYPE html>" in body
        assert "live dashboard" in body
        # favicon path is handled (no 500)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/favicon.ico")
        with urllib.request.urlopen(req, timeout=5) as resp2:
            assert resp2.status == 204
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_render_live_invalidates_driver(monkeypatch, tmp_path):
    # Each request runs its own asyncio.run (fresh loop); the cached Neo4j driver
    # must be discarded afterward so the next request does not reuse a driver
    # bound to a dead loop. Assert invalidate is called, even on error.
    import wheeler.dashboard as dashboard_pkg
    import wheeler.graph.driver as driver_mod

    calls = {"invalidated": 0}
    monkeypatch.setattr(driver_mod, "invalidate_async_driver", lambda: calls.__setitem__("invalidated", calls["invalidated"] + 1))

    async def fake_gather(config, *, limit=12, plan_id=None):
        return {"meta": {"project_root": "."}, "generated": "2026-06-20T14:00:00Z",
                "counts": {}, "hero": [], "questions": [], "plans": [], "results": [],
                "figures": [], "notes": {}, "project": "", "title": "T"}

    monkeypatch.setattr(dashboard_pkg, "gather_dashboard_data", fake_gather)

    cfg = _config(tmp_path)
    out = serve_mod.render_live(cfg, 5)
    assert "<!DOCTYPE html>" in out
    assert calls["invalidated"] == 1

    async def boom(config, *, limit=12, plan_id=None):
        raise RuntimeError("down")

    monkeypatch.setattr(dashboard_pkg, "gather_dashboard_data", boom)
    try:
        serve_mod.render_live(cfg, 5)
    except RuntimeError:
        pass
    assert calls["invalidated"] == 2  # invalidated even when gather raised


def test_live_server_renders_error_page_when_graph_down(monkeypatch, tmp_path):
    def boom(config, limit=12):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(serve_mod, "render_live", boom)
    httpd = serve_mod.make_server(_config(tmp_path), "127.0.0.1", 0, 12)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5)
            raise AssertionError("expected HTTP error")
        except urllib.error.HTTPError as e:
            assert e.code == 503
            assert b"could not read the graph" in e.read().lower()
    finally:
        httpd.shutdown()
        httpd.server_close()
