"""Shared infrastructure for all Wheeler MCP servers.

Contains config loading, request logging, the _logged decorator,
session ID, embedding store access, and similarity checking.
"""

from __future__ import annotations

import functools
import logging
import secrets
import time
from datetime import datetime, timezone

from wheeler.config import configure_logging, load_config, WheelerConfig
from wheeler.request_log import RequestLog, RequestLogger

logger = logging.getLogger(__name__)

# Configure logging and load config once at import time
configure_logging()
_config: WheelerConfig = load_config()

# Unique session ID generated once per MCP server process
_SESSION_ID: str = f"session-{secrets.token_hex(4)}"

# Request logger: append-only JSONL in .wheeler/. Resolved against the project
# root, not the cwd the server process happened to be spawned in.
_request_logger = RequestLogger(_config.resolved_wheeler_dir)

# Lazy-loaded singleton for semantic search
_embedding_store: object | None = None


def _get_embedding_store():
    """Return the singleton EmbeddingStore, creating it on first call."""
    global _embedding_store
    if _embedding_store is None:
        from wheeler.search.embeddings import EmbeddingStore

        # Project-root relative, so a server spawned in a subdirectory reads
        # and writes the same embeddings as one spawned at the root.
        store_path = str(_config.resolved_search_store_path)
        _embedding_store = EmbeddingStore(store_path)
        _embedding_store.load()
    return _embedding_store


def _safe_log(entry: RequestLog) -> None:
    """Write one request-log entry, never propagating a logging failure.

    The request log is observability, not a tool result, so a read-only or
    absent ``.wheeler/`` must not fail the tool that was actually asked for.
    Before this guard, ``RequestLogger.log`` (which does mkdir + open(..., "a")
    with no exception handling) could raise from inside ``_logged``, and the
    handler's re-log would raise again and escape -- replacing the tool's real
    return value, or its real exception, with the logging error, on every one
    of the logged tools across all four servers.

    Debug level, not warning: on a filesystem-less host this fires every call.
    """
    try:
        _request_logger.log(entry)
    except Exception:
        logger.debug(
            "request log write failed for %s (continuing)", entry.tool_name, exc_info=True
        )


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
            _safe_log(RequestLog(
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
            _safe_log(RequestLog(
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

    # Marker so a test can assert every registered tool is wrapped. A tool that
    # silently skips logging is invisible to request_log_summary and to trace
    # correlation, and `request_log_summary` itself was exactly that for a while.
    wrapper._wheeler_logged = True  # type: ignore[attr-defined]
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


# --- Result diet -------------------------------------------------------------
# Every byte a tool returns is re-read by the model on every later turn of the
# session, so a wrapper's result should carry what the caller acts on (ids,
# statuses, failures) and nothing it already knows or never uses. The full
# payload stays one flag away (verbose=True on writes, full=True on reads).
# Audit that motivated this: docs/mcp-token-audit.md.

TEXT_KEYS = ("description", "statement", "question", "content", "text", "summary", "abstract")
DEFAULT_TEXT_CHARS = 240


def _trim_text(value, max_chars: int = DEFAULT_TEXT_CHARS):
    """Cut a long string and say how much was cut, so the caller can ask for it."""
    if not isinstance(value, str) or len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + f"... [+{len(value) - max_chars} chars]"


def _trim_rows(obj, max_chars: int = DEFAULT_TEXT_CHARS):
    """Recursively trim the long text fields inside lists and dicts of rows."""
    if isinstance(obj, dict):
        return {
            k: (_trim_text(v, max_chars) if k in TEXT_KEYS else _trim_rows(v, max_chars))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_trim_rows(x, max_chars) for x in obj]
    return obj


def _strip_empty(d: dict) -> dict:
    """Drop keys whose value is empty: '', None, [] or {}."""
    return {k: v for k, v in d.items() if v not in ("", None, [], {})}


def _compact_write_result(parsed: dict) -> dict:
    """Shape an add_* result: provenance inputs as a count, similar-node hints short.

    The linked_inputs list repeats the ids the caller just passed in, and a
    near-duplicate hint only needs enough text to recognise the node.
    """
    if not isinstance(parsed, dict):
        return parsed
    prov = parsed.get("provenance")
    if isinstance(prov, dict) and isinstance(prov.get("linked_inputs"), list):
        prov = dict(prov)
        prov["linked_inputs_count"] = len(prov.pop("linked_inputs"))
        parsed["provenance"] = prov
    sim = parsed.get("similar_existing")
    if isinstance(sim, list):
        parsed["similar_existing"] = [
            {**m, "text": _trim_text(m.get("text", ""), 120)} if isinstance(m, dict) else m
            for m in sim
        ]
    return parsed
