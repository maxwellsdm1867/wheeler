"""On-disk state for an LLM-SR run: the run dir, its append-only log, progress.

A run owns a directory under ``.wheeler/llmsr/runs/<run_id>`` holding ``meta.json``
(what the run is bound to), ``submissions.jsonl`` (every candidate, in order), and
``heartbeat.json`` (a snapshot so a ping mid-search does not replay the whole log).
There are no pickles: state is whatever replaying the log reconstructs.

Split out of ``cli.py`` so the verbs stay readable; the layout itself is unchanged.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import typer

from . import fit as fit_mod

logger = logging.getLogger(__name__)

_RUNS_ROOT = Path(".wheeler/llmsr/runs")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_dir(run: str) -> Path:
    """Accept either a run id or a run-dir path; return the run dir."""
    p = Path(run)
    if p.is_dir() and (p / "meta.json").exists():
        return p
    candidate = _RUNS_ROOT / run
    if (candidate / "meta.json").exists():
        return candidate
    raise typer.BadParameter(f"no run found for {run!r} (looked at {p} and {candidate})")


def _read_meta(run_dir: Path) -> dict:
    return json.loads((run_dir / "meta.json").read_text())


def _scores_per_test(sub: dict) -> dict[str, float]:
    """The score vector a submission contributes to the vendored buffer.

    Submissions written before per-group scoring carry only a scalar `score`, so
    they replay under the single ``UNGROUPED`` key exactly as they always did.
    """
    per_group = sub.get("per_group")
    if per_group:
        return {str(k): float(v) for k, v in per_group.items()}
    return {fit_mod.UNGROUPED: sub["score"]}


def _read_submissions(run_dir: Path) -> list[dict]:
    path = run_dir / "submissions.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # Tolerate a torn/partial line (an interrupted append, a crash mid-write)
            # instead of bricking every subsequent verb that replays the log.
            logger.warning("skipping unparseable submissions line in %s", path)
    return out


def _append_submission(run_dir: Path, record: dict) -> None:
    with (run_dir / "submissions.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")


def _n_constraint_rejected(subs: list[dict]) -> int:
    """Candidates a hard constraint threw out, whatever they scored. Reported so
    a frontier truncated by the guard is visible rather than silent."""
    return sum(1 for s in subs if s.get("rejection_reason") == "constraint")


def _progress(run_dir: Path, meta: dict) -> dict:
    """Current run state: how many samples, how many valid, and the best so far."""
    subs = _read_submissions(run_dir)
    valid = [s for s in subs if s.get("valid") and s.get("score") is not None]
    rejected = _n_constraint_rejected(subs)
    best = max(valid, key=lambda s: s["score"]) if valid else None
    created_epoch = meta.get("created_epoch")
    elapsed = round(time.time() - created_epoch, 2) if created_epoch else None
    return {
        "run_id": meta["run_id"],
        "metric": meta["metric"],
        "generator": meta["generator"],
        "n_samples": len(subs),
        "n_valid": len(valid),
        "n_constraint_rejected": rejected,
        "n_failed": len(subs) - len(valid) - rejected,
        "best_value": best["value"] if best else None,
        "best_equation": best["body"].strip("\n") if best else None,
        "best_sample_order": best["sample_order"] if best else None,
        "elapsed_seconds": elapsed,
        "fit_seconds_total": round(sum(s.get("fit_seconds", 0.0) for s in subs), 3),
    }


def _write_heartbeat(run_dir: Path, meta: dict) -> None:
    """Refresh heartbeat.json: a single timestamped snapshot of run progress so a
    ping during a long search shows where it is without replaying the whole log."""
    prog = _progress(run_dir, meta)
    prog["updated"] = _now()
    (run_dir / "heartbeat.json").write_text(json.dumps(prog, indent=2))


def _timing(meta: dict, subs: list[dict]) -> dict:
    """How long the run took: total wall-clock (init to now), the active search
    window (first to last submit), and pure fit compute (sum of per-fit seconds).
    The difference between search and fit is generator (LLM) thinking time."""
    now = time.time()
    created = meta.get("created_epoch", now)
    epochs = [s["at_epoch"] for s in subs if "at_epoch" in s]
    search = round(max(epochs) - min(epochs), 2) if len(epochs) >= 2 else 0.0
    return {
        "created": meta.get("created"),
        "finished": _now(),
        "duration_seconds": round(now - created, 2),
        "search_seconds": search,
        "fit_seconds_total": round(sum(s.get("fit_seconds", 0.0) for s in subs), 3),
        "n_samples": len(subs),
    }
