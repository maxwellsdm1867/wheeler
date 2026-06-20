"""Live local server for the research dashboard.

``wheeler dashboard`` serves the dashboard from a tiny stdlib HTTP server that
re-queries the knowledge graph and re-renders on every request, so the browser's
Refresh always shows current data. No web framework dependency: it reuses the
same pure ``gather_dashboard_data`` + ``render`` used everywhere else.

The page embeds all figures as data URIs / sandboxed iframes, so a single HTML
response is fully self-contained: no separate asset routes are needed.
"""
from __future__ import annotations

import asyncio
import html
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)

# The Neo4j async driver is a process-global singleton bound to whatever event
# loop created it (graph/driver.py). Each request runs its own asyncio.run (a
# fresh loop), so we serialize graph access and discard the cached driver after
# every run, matching the MCP servers' invalidate_async_driver() idiom. This is
# why the server is single-threaded (HTTPServer, not ThreadingHTTPServer): a
# localhost single-user tool gains nothing from concurrency and the driver is
# not safe to share across loops/threads.
_RENDER_LOCK = threading.Lock()


def render_live(config: WheelerConfig, limit: int = 12) -> str:
    """Query the graph and render the dashboard HTML for one request."""
    from wheeler.dashboard import gather_dashboard_data, render
    from wheeler.graph.driver import invalidate_async_driver

    with _RENDER_LOCK:
        try:
            data = asyncio.run(gather_dashboard_data(config, limit=limit))
            out, _missing = render(data)
            return out
        finally:
            invalidate_async_driver()


def make_server(config: WheelerConfig, host: str, port: int, limit: int) -> HTTPServer:
    """Build (but do not start) the dashboard HTTP server."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if path not in ("/", "/index.html"):
                self.send_response(404)
                self.end_headers()
                return
            try:
                body = render_live(config, limit).encode("utf-8")
                status = 200
            except Exception as exc:  # graph down mid-session: show it, keep serving
                logger.warning("dashboard render failed: %s", exc)
                body = (
                    "<!DOCTYPE html><html><body style='font-family:sans-serif;padding:2rem'>"
                    "<h1>Dashboard could not read the graph</h1>"
                    f"<pre>{html.escape(str(exc))}</pre>"
                    "<p>Is Neo4j running? Check wheeler.yaml, then Refresh.</p>"
                    "</body></html>"
                ).encode("utf-8")
                status = 503
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:  # keep the console quiet
            return

    return HTTPServer((host, port), Handler)


def serve(
    config: WheelerConfig,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    limit: int = 12,
    open_browser: bool = True,
    on_start=None,
) -> None:
    """Serve the dashboard until interrupted (Ctrl+C). Blocking.

    ``on_start(url)`` is called once the server is bound (used by the CLI to
    print the URL). Raises ``OSError`` if the address cannot be bound.
    """
    import webbrowser

    httpd = make_server(config, host, port, limit)
    bound_port = httpd.server_address[1]
    url = f"http://{host}:{bound_port}/"
    if on_start is not None:
        on_start(url)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            logger.debug("could not open browser", exc_info=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
