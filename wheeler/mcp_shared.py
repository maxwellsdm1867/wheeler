"""Shared infrastructure for all Wheeler MCP servers.

Contains config loading, request logging, the _logged decorator,
session ID, embedding store access, and similarity checking.
"""

from __future__ import annotations

import functools
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from wheeler.config import configure_logging, load_config, WheelerConfig
from wheeler.request_log import RequestLog, RequestLogger

# Configure logging and load config once at import time
configure_logging()
_config: WheelerConfig = load_config()

# Unique session ID generated once per MCP server process
_SESSION_ID: str = f"session-{secrets.token_hex(4)}"

# Request logger: append-only JSONL in .wheeler/
_request_logger = RequestLogger(Path(".wheeler"))

# Lazy-loaded singleton for semantic search
_embedding_store: object | None = None


def _get_embedding_store():
    """Return the singleton EmbeddingStore, creating it on first call."""
    global _embedding_store
    if _embedding_store is None:
        from wheeler.search.embeddings import EmbeddingStore

        store_path = _config.search.store_path
        _embedding_store = EmbeddingStore(store_path)
        _embedding_store.load()
    return _embedding_store


def _logged(func):
    """Wrap an MCP tool handler with request logging."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        trace_id = f"t-{secrets.token_hex(6)}"
        start = time.perf_counter()
        tool_name = func.__name__
        try:
            result = await func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            node_id = ""
            label = ""
            if isinstance(result, dict):
                node_id = result.get("node_id", "") or ""
                label = result.get("label", "") or ""
            _request_logger.log(RequestLog(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_name=tool_name,
                latency_ms=round(elapsed, 1),
                status="ok",
                session_id=_SESSION_ID,
                node_id=str(node_id),
                label=str(label),
                error="",
                trace_id=trace_id,
            ))
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            _request_logger.log(RequestLog(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_name=tool_name,
                latency_ms=round(elapsed, 1),
                status="error",
                session_id=_SESSION_ID,
                node_id="",
                label="",
                error=str(exc),
                trace_id=trace_id,
            ))
            raise

    return wrapper


def _check_similar_nodes(text: str, label: str, exclude_id: str | None = None) -> list[dict]:
    """Check for similar existing nodes. Returns matches or empty list.

    Fails silently if embeddings aren't available: this is purely advisory.
    """
    try:
        store = _get_embedding_store()
        matches = store.check_similar(text, threshold=0.85, label_filter=label, exclude_id=exclude_id)
        return [
            {"node_id": m.node_id, "text": m.text, "similarity": round(m.score, 4)}
            for m in matches[:3]
        ]
    except (ImportError, Exception):
        return []


def _extract_display_text(node: dict) -> str:
    """Extract the best display text from a node dict.

    Tries common text fields in priority order.
    """
    for field in ("description", "statement", "question", "title", "content"):
        val = node.get(field)
        if val:
            return val
    return ""


async def _verify_backend() -> None:
    """Verify the graph backend initializes and can run a basic query.

    Logs a clear error if the database is unreachable so the user knows
    writes will fail silently.
    """
    import logging as _logging

    from wheeler.tools import graph_tools

    _log = _logging.getLogger("wheeler.health")
    try:
        backend = await graph_tools._get_backend(_config)
        counts = await backend.count_all()
        total = sum(counts.values())
        _log.info(
            "Graph backend OK (%s, %d nodes)",
            _config.graph.backend,
            total,
        )
    except Exception as exc:
        _log.error(
            "GRAPH BACKEND FAILED (%s): %s -- "
            "graph operations will not work until this is fixed. "
            "Ensure Neo4j is running (Desktop or Docker).",
            _config.graph.backend,
            exc,
        )
