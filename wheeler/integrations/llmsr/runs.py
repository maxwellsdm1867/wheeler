"""On-disk state for an LLM-SR run: the run dir, its append-only log, progress.

A run owns a directory under ``.wheeler/llmsr/runs/<run_id>`` holding ``meta.json``
(what the run is bound to), ``submissions.jsonl`` (every candidate, in order),
``heartbeat.json`` (a snapshot so a ping mid-search does not replay the whole log),
and ``progress.json`` (where the work happening RIGHT NOW is). There are no
pickles: state is whatever replaying the log reconstructs.

The two status files are deliberately separate and answer different questions.
``heartbeat.json`` is written AFTER a fit completes and says what the search has
achieved. ``progress.json`` is written DURING a fit and says where that fit has
got to. Only the second one can answer "is it wedged?", because a submit that
refits forty groups is otherwise silent for minutes.

Split out of ``cli.py`` so the verbs stay readable; the layout itself is unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import typer

from . import fit as fit_mod

logger = logging.getLogger(__name__)

_RUNS_ROOT = Path(".wheeler/llmsr/runs")

PROGRESS_FILE = "progress.json"
HEARTBEAT_FILE = "heartbeat.json"


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


# How the SPEC's own objective is named when it is the thing that scored a run.
# A prefix rather than a bare word, so the name says where the number came from
# and can never be confused with a registered metric key (a metric key holds no
# colon; ``data.KEY_SEP`` reserves it for the same reason).
SPEC_METRIC_PREFIX = "spec:"

# Why the spec door's numbers do not travel under the declared metric's name.
# Carried onto ``best.json``, and (in the graph writer's own copy of the wording)
# onto every Finding the spec door produced.
SPEC_METRIC_NOTE = (
    "This run scored through the spec's own @evaluate.run, which owns its loss "
    "and does not report what it computed. Every per-unit number the SEARCH "
    "produced (value_per_group, datasets[*].value / value_per_key, the winner's "
    "own value) is therefore the SPEC'S objective read back under the declared "
    "metric's orientation, not the declared metric measured again, and nothing "
    "checks that the two are equal. The declared metric appears only where "
    "Wheeler's fit seam computed it: the `metrics` and `metrics_refit` blocks."
)


def scored_metric(meta: dict) -> str:
    """The name of the quantity a run's OWN numbers are in. Never assumed.

    This is the one question every value a run reports has to answer, and the two
    doors answer it differently.

    On the DEFAULT door ``fit.py`` minimizes ``metric.loss`` and reports
    ``metric.report``, so the number IS the declared metric and this returns its
    key, exactly as before.

    Through the spec door (``--use-spec-evaluate``) the spec's own
    ``@evaluate.run`` owns the loss. It returns upstream's maximize-me score and
    never says what it computed, and NOTHING checks that the quantity equals the
    run's declared metric: a stock recipe minimizing mean squared error under a
    run declaring ``--metric nmse`` returns an MSE. So the number is the SPEC'S
    objective and is named after it, ``spec:<function_to_run>``. Calling it the
    declared metric would publish a number under a name that did not produce it,
    which is the exact failure this engine exists to remove.

    The declared metric is still the run's declared metric, and still labels
    every number ``fit.py`` computed (``best.json``'s ``metrics`` /
    ``metrics_refit``, which run through the fit seam on BOTH doors). The two
    names coexist because they name two different quantities.
    """
    if meta.get("use_spec_evaluate"):
        return SPEC_METRIC_PREFIX + (str(meta.get("function_to_run") or "").strip() or "evaluate")
    return str(meta.get("metric") or "")


def scored_metric_report(meta: dict) -> dict:
    """The ``scored_metric`` block for ``best.json``, or ``{}`` on the default door.

    Absent on the default door because there is nothing to disambiguate there:
    the search's numbers and the declared metric are the same quantity, and every
    existing reader of a default run sees the file it always saw.
    """
    if not meta.get("use_spec_evaluate"):
        return {}
    return {
        "scored_metric": {
            "name": scored_metric(meta),
            "declared": str(meta.get("metric") or ""),
            "measured_by": "spec-evaluate",
            "note": SPEC_METRIC_NOTE,
        }
    }


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


def _write_json_atomic(path: Path, payload: dict) -> None:
    """Write JSON via tmp + rename, the same atomic style the knowledge store uses.

    The tmp name carries the pid because the only writer of ``progress.json`` is
    a forked fit child: two of them sharing one tmp path could interleave into it
    and then both rename, publishing a file neither of them wrote.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(path)
    finally:
        # Only reachable when the rename did not happen: a successful replace
        # consumed the tmp. Keeps a failing writer from silting up the run dir.
        tmp.unlink(missing_ok=True)


def write_progress(run_dir: Path, payload: dict) -> None:
    """Refresh ``progress.json``: where the work happening RIGHT NOW has got to.

    This is the DURING channel. ``heartbeat.json`` is the AFTER channel and is
    untouched by this. Atomic, so a reader never sees half a payload.
    """
    _write_json_atomic(Path(run_dir) / PROGRESS_FILE, payload)


def read_progress(run_dir: Path) -> dict | None:
    """The last in-flight progress ping, or ``None``.

    ``None`` means absent, unreadable, or not a JSON object: this never raises,
    because a status ping that lands mid-write must not brick the verb it is
    reporting on. Note that a payload being present does NOT mean a fit is live;
    the ping survives the fit that wrote it on purpose, so a dead run still shows
    which group it died on. ``phase`` is what says whether it is live.
    """
    try:
        payload = json.loads((Path(run_dir) / PROGRESS_FILE).read_text())
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _phase(
    run_dir: Path,
    n_samples: int,
    has_progress: bool,
    progress_at: float | None,
    beat_at: float | None,
) -> str:
    """Which of ``init | fitting | idle | done`` the run is in.

    The rule, in order:

    ``fitting``
        A progress ping exists and ``heartbeat.json`` has not overtaken it.
        Progress is written during a fit and the heartbeat only after one, so a
        ping the heartbeat has not caught up with means a fit is in flight. This
        is a comparison, not a timeout, which is what lets a WEDGED fit keep
        reporting ``fitting`` (with a growing ``seconds_since_update``) instead
        of decaying to ``idle`` while a child is still alive. A fit that was
        killed outright leaves the same signature, which is honest: something
        started a fit and nothing ever finished it. ``>=`` rather than ``>`` so a
        coarse-resolution filesystem that stamps both files alike errs toward
        ``fitting``, never toward calling a live child idle. Existence comes from
        ``has_progress`` (the payload that was actually read) and not from the
        stat, so a missing ``progress_at`` cannot contradict a ping we are about
        to report: the file appears between the two syscalls the first time a fit
        pings, and the phase must not lag behind the payload.
    ``done``
        ``best.json`` exists, so the run was concluded by ``wheeler llmsr best``.
        Ranked below ``fitting`` because submitting again after picking a winner
        is legal, and an in-flight fit is the more immediate truth.
    ``init``
        No submission has been recorded yet: the run dir exists but its seed fit
        never landed.
    ``idle``
        Everything else: fits have finished and nothing is running.
    """
    if has_progress and (beat_at is None or progress_at is None or progress_at >= beat_at):
        return "fitting"
    if (run_dir / "best.json").exists():
        return "done"
    if n_samples == 0:
        return "init"
    return "idle"


def _live_state(run_dir: Path, n_samples: int) -> dict:
    """The is-it-wedged fields: which phase, how stale, and the in-flight ping.

    Kept apart from the log-replay snapshot because ``heartbeat.json`` stores the
    snapshot and these have to be recomputed at every read: a phase frozen into a
    file is a phase that is wrong the moment the file stops being written.

    The payload is read BEFORE the timestamps, so that the phase is derived from
    the same observation this reports. A fit writing its first ping publishes the
    file between any two syscalls here, and reading the mtime first would let a
    reader report a live ping under a phase that says nothing is running.
    """
    payload = read_progress(run_dir)
    progress_at = _mtime(run_dir / PROGRESS_FILE)
    beat_at = _mtime(run_dir / HEARTBEAT_FILE)
    newest = max((t for t in (progress_at, beat_at) if t is not None), default=None)
    state: dict = {
        "phase": _phase(run_dir, n_samples, payload is not None, progress_at, beat_at),
        "seconds_since_update": round(time.time() - newest, 2) if newest is not None else None,
    }
    if payload is not None:
        state["progress"] = payload
    return state


def _progress_core(run_dir: Path, meta: dict) -> dict:
    """Current run state: how many samples, how many valid, and the best so far.

    This is the part that costs a log replay, and it is what ``heartbeat.json``
    stores. The live fields (``_live_state``) are layered on at read time.
    """
    subs = _read_submissions(run_dir)
    valid = [s for s in subs if s.get("valid") and s.get("score") is not None]
    rejected = _n_constraint_rejected(subs)
    best = max(valid, key=lambda s: s["score"]) if valid else None
    created_epoch = meta.get("created_epoch")
    elapsed = round(time.time() - created_epoch, 2) if created_epoch else None
    # ``metric`` is the run's DECLARED metric, which is a property of the run.
    # ``best_value`` is a number, and a number carries the name of whatever
    # produced it: on the spec door that is the spec's own objective, not the
    # declared metric, so it is named here rather than left to be read off the
    # neighbouring field. Absent on the default door, where the two are the same
    # quantity and an extra key would only be noise.
    scored = scored_metric(meta)
    return {
        "run_id": meta["run_id"],
        "metric": meta["metric"],
        **({"best_value_metric": scored} if scored != meta["metric"] else {}),
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


def _progress(run_dir: Path, meta: dict) -> dict:
    """Everything ``status`` reports: the log-replay snapshot plus the live state."""
    core = _progress_core(run_dir, meta)
    core.update(_live_state(run_dir, core["n_samples"]))
    return core


def status_payload(run_dir: Path, meta: dict) -> dict:
    """What ``wheeler llmsr status`` prints.

    Prefers the ``heartbeat.json`` snapshot so a ping mid-search does not replay
    the whole submissions log, then overlays the live fields, which cannot come
    from a file: the heartbeat is by definition the state as of the last COMPLETED
    fit, so on its own it answers "how is the search doing" while reporting
    nothing at all about the fit running right now.
    """
    try:
        base = json.loads((run_dir / HEARTBEAT_FILE).read_text())
        if not isinstance(base, dict):
            raise ValueError("heartbeat is not an object")
    except (OSError, ValueError):
        base = _progress_core(run_dir, meta)
    base.update(_live_state(run_dir, base.get("n_samples", 0)))
    return base


def _write_heartbeat(run_dir: Path, meta: dict) -> None:
    """Refresh heartbeat.json: a single timestamped snapshot of run progress so a
    ping during a long search shows where it is without replaying the whole log.

    The snapshot only: the live fields are recomputed on every read instead,
    because a ``phase`` written into a file goes stale the instant the run moves.
    """
    prog = _progress_core(run_dir, meta)
    prog["updated"] = _now()
    (run_dir / HEARTBEAT_FILE).write_text(json.dumps(prog, indent=2))


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
