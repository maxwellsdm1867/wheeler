"""Marshal-out (deterministic): durably save + register a service's raw output.

Every service output is an artifact, and it must be trackable and reachable
from Wheeler and from Claude Code WITHOUT re-running the service. So the raw
``-o`` JSON dump a service writes is:

  1. COPIED into a durable raw store (``.wheeler/asta/raw/<service>/<key>.json``)
     so it survives the ephemeral CLI temp path. The key is the service run_id
     when present, else a content sha. Re-saving the same content is a no-op.
  2. REGISTERED as a first-class graph node pointing at the saved path. The
     NODE is the quick first-pass index (queryable metadata + a path pointer);
     the FILE it points to holds the full raw output.

The node TYPE is per-adapter and matches the artifact nature (do NOT call
everything a Dataset):
  - Theorizer output is synthesized WRITING, so its raw node is a Document (W-).
  - Paper Finder output is structured reference records, so its raw node is a
    Dataset (D-).
Reserve Dataset for genuine data or recordings (databases, .mat, .csv). The
caller declares the node type via ``node_type`` ("document" or "dataset"); the
triple-write renders a browsable synthesis md either way.

The raw node points at the saved path, is service-tagged, and carries benchmark
metadata in its custom bag (run_id, cost, time, model, service). The same fields
are stamped on the run Execution (by the caller) so runs are benchmarkable later.

This module is a marshal-out caller: it imports ``execute_tool`` lazily
(function-local), mirroring ``wheeler/validation/ledger.py`` and ``ingest.py``.
Every graph write routes through ``execute_tool`` so the triple-write, write
receipt, trace id, and embedding wiring all fire. Edge creation reuses the
``_link_once`` / ``_edge_exists`` helpers in ``_marshal.py`` so re-registering
the same artifact never duplicates the ``WAS_GENERATED_BY`` edge.

Invariants:
  - Best-effort. ANY failure returns ``None`` and logs a warning, never raises:
    a failed artifact registration must not break the surrounding ingest.
  - Idempotent. The durable save dedupes on path; ``ensure_artifact`` dedupes on
    path; ``_link_once`` guards the edge. Re-ingest creates no duplicate.
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses
    one cached backend singleton and Neo4j forbids concurrent queries.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from wheeler.config import WheelerConfig

from ._marshal import _link_once

logger = logging.getLogger(__name__)

# Durable raw store. The ephemeral CLI ``-o`` path lives in /tmp and is gone on
# the next run; the raw output is copied here so it is reachable forever.
_RAW_STORE_REL = ".wheeler/asta/raw"

# Accepted node types for the raw output node, mapped to ensure_artifact's
# artifact_type override (Document -> W-, Dataset -> D-).
_NODE_TYPE_MAP = {"document": "document", "dataset": "dataset"}


def _service_slug(service: str) -> str:
    """Turn a provider:service tag into a filesystem-safe directory name."""
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in service)
    return safe.strip("-") or "asta"


def _content_sha(path: Path) -> str:
    """Return a short content sha of a file (the fallback durable-store key)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _save_raw_durably(
    src_path: Path, *, service: str, run_id: str
) -> Path | None:
    """Copy the ephemeral raw output into the durable store, return its path.

    The store key is the service run_id when present (stable across re-ingest of
    the same run), else a content sha (so identical content lands on the same
    durable path). Idempotent: an existing destination is reused without
    re-copying. ASSUMPTION: a service run_id uniquely identifies its content
    (true for real Asta runs, whose ids are minted per run). If a run_id were
    ever reused for DIFFERENT content, the path-dedupe would keep the first save;
    the content-sha fallback has no such risk. Best-effort: returns None on any
    OS error.
    """
    try:
        slug = _service_slug(service)
        key = "".join(
            c if c.isalnum() or c in "-_" else "-" for c in (run_id or "")
        ).strip("-")
        if not key:
            key = _content_sha(src_path)
        store_dir = Path(_RAW_STORE_REL) / slug
        store_dir.mkdir(parents=True, exist_ok=True)
        dest = store_dir / f"{key}.json"
        if dest.exists():
            # Same run already saved: reuse it (path-dedupe), do not re-copy.
            return dest
        shutil.copyfile(src_path, dest)
        return dest
    except OSError:
        logger.warning(
            "register_output_artifact: durable save failed for %s (best-effort)",
            src_path,
            exc_info=True,
        )
        return None


async def register_output_artifact(
    path: str | None,
    *,
    execution_id: str,
    service: str,
    config: WheelerConfig,
    node_type: str = "dataset",
    run_id: str = "",
    benchmark: dict[str, Any] | None = None,
    description: str = "",
) -> str | None:
    """Durably save a service's raw output and register it as a graph node.

    The raw ``-o`` JSON dump is copied into the durable raw store, then
    registered via ``ensure_artifact`` as the node type the caller declares
    (Document for synthesized writing like Theorizer, Dataset for structured
    reference records like Paper Finder), tagged with ``service``, stamped with
    the benchmark bag, and linked ``-[WAS_GENERATED_BY]->`` the run Execution.
    The node points at the SAVED path (durable store), not the ephemeral input.
    The node id is returned so the caller can link each generated node
    ``WAS_DERIVED_FROM`` it.

    Args:
        path: Path to the ephemeral raw output file. ``None`` or a missing file
            is a no-op that returns ``None``.
        execution_id: The run Execution node id the artifact was generated by.
        service: The provider:service tag (e.g. ``asta:theorizer``).
        config: Active Wheeler config.
        node_type: "document" (W-, synthesized writing) or "dataset" (D-,
            structured data). Anything else defaults to "dataset".
        run_id: Service run id; the durable-store key when present, else a
            content sha. Also parked in the benchmark bag if not already there.
        benchmark: Benchmark scalars (run_id, cost, time, model, service) to
            stamp into the node's custom bag, so the node is benchmarkable.
        description: Human description. Falls back to a service default.

    Returns:
        The artifact node id on success, or ``None`` on any failure (best-effort).
    """
    if not path:
        return None
    src_path = Path(path)
    if not src_path.exists():
        logger.warning(
            "register_output_artifact: output file not found, skipping: %s", path,
        )
        return None

    artifact_type = _NODE_TYPE_MAP.get((node_type or "").lower(), "dataset")
    desc = description or f"{service} raw output"

    try:
        from wheeler.tools.graph_tools import _get_backend, execute_tool

        backend = await _get_backend(config)

        # 1. Durable save. Copy the ephemeral raw output into the durable store
        # so it is reachable without re-running. The registered node points here.
        saved = _save_raw_durably(src_path, service=service, run_id=run_id)
        registered_path = saved if saved is not None else src_path

        # 2. Register the saved file as the declared node type. A .json dump has
        # no extension rule in ensure_artifact (would default to Document), so
        # artifact_type routes it to the right label. ensure_artifact is
        # idempotent on path, so re-registering the same saved file is a no-op.
        ensure_result_str = await execute_tool(
            "ensure_artifact",
            {
                "path": str(registered_path),
                "artifact_type": artifact_type,
                "description": desc,
                "service": service,
                "tier": "generated",
            },
            config,
        )
        ensure_result = json.loads(ensure_result_str)
        if "error" in ensure_result:
            logger.warning(
                "register_output_artifact: ensure_artifact failed for %s: %s",
                registered_path, ensure_result,
            )
            return None
        artifact_id = ensure_result.get("node_id")
        if not artifact_id:
            logger.warning(
                "register_output_artifact: ensure_artifact returned no node_id for %s",
                registered_path,
            )
            return None

        # 3. Stamp the service tag + benchmark bag. ensure_artifact does not
        # forward service or custom, so apply them via update_node (service is a
        # first-class NodeBase field; benchmark scalars flatten to custom_<key>
        # and are queryable, e.g. WHERE w.custom_run_id = '...').
        bag: dict[str, Any] = dict(benchmark or {})
        if run_id and "run_id" not in bag:
            bag["run_id"] = run_id
        update_args: dict[str, Any] = {"node_id": artifact_id}
        if service:
            update_args["service"] = service
        # service may also be present in the bag; drop it (handled above).
        bag.pop("service", None)
        if bag:
            update_args["custom"] = bag
        if len(update_args) > 1:
            try:
                update_result_str = await execute_tool(
                    "update_node", update_args, config,
                )
                update_result = json.loads(update_result_str)
                if "error" in update_result:
                    logger.warning(
                        "register_output_artifact: benchmark/service update failed "
                        "for %s: %s",
                        artifact_id, update_result,
                    )
            except Exception:
                logger.warning(
                    "register_output_artifact: benchmark/service update raised for %s",
                    artifact_id, exc_info=True,
                )

        # 4. Provenance: Artifact WAS_GENERATED_BY the run Execution (link_once).
        if execution_id:
            await _link_once(
                backend, config, artifact_id, "WAS_GENERATED_BY", execution_id,
            )

        logger.info(
            "register_output_artifact: registered %s as %s (type=%s, service=%s)",
            registered_path, artifact_id, artifact_type, service,
        )
        return artifact_id
    except Exception:
        logger.warning(
            "register_output_artifact: failed for %s (best-effort)",
            path, exc_info=True,
        )
        return None
