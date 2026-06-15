"""Transport boundary: the single place that shells out to the asta CLI.

This module owns the subprocess, the timeout, and the failure-isolation
contract. It has ZERO graph dependency and imports no LLM-provider SDK. The asta
CLI owns auth, retries, and remote timeouts; Wheeler builds no httpx/backoff.

Contract (``run_asta``):
  - run the given argv with a wall-clock timeout
  - on non-zero exit, timeout, or missing/empty ``-o`` output: return None
    (a failed run writes nothing; failure isolation by construction)
  - otherwise load and return the JSON the CLI wrote to ``output_path``
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def run_asta(
    argv: list[str],
    *,
    output_path: str | Path,
    timeout: int = 600,
) -> dict[str, Any] | None:
    """Run an asta CLI invocation and return its ``-o`` JSON artifact.

    Args:
        argv: Full command line, e.g.
            ``["asta", "literature", "find", "QUERY", "-o", path]``.
        output_path: The ``-o`` path the CLI is expected to write.
        timeout: Wall-clock seconds before the subprocess is killed.

    Returns:
        The parsed JSON dict on success, or None on any failure
        (non-zero exit, timeout, missing/empty output, unparseable JSON).
    """
    out = Path(output_path)

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("run_asta: %s timed out after %ds", argv[:3], timeout)
        return None
    except (FileNotFoundError, OSError) as exc:
        logger.warning("run_asta: could not launch %s: %s", argv[:1], exc)
        return None

    if proc.returncode != 0:
        logger.warning(
            "run_asta: %s exited %d; stderr: %s",
            argv[:3], proc.returncode, (proc.stderr or "").strip()[:500],
        )
        return None

    if not out.exists():
        logger.warning("run_asta: output file %s does not exist after run", out)
        return None

    try:
        raw = out.read_text()
    except OSError as exc:
        logger.warning("run_asta: could not read output %s: %s", out, exc)
        return None

    if not raw.strip():
        logger.warning("run_asta: output file %s is empty", out)
        return None

    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("run_asta: output %s is not valid JSON: %s", out, exc)
        return None

    if not isinstance(doc, dict):
        logger.warning("run_asta: output %s did not contain a JSON object", out)
        return None

    return doc
