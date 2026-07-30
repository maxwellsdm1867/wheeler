"""On-disk state for an LLM-SR run: the run dir, its append-only log, progress.

A run owns a directory under ``.wheeler/llmsr/runs/<run_id>`` holding ``meta.json``
(what the run is bound to), ``submissions.jsonl`` (every candidate, in order),
``prompts/<n>.txt`` plus ``prompts.jsonl`` (every prompt handed out and where it
routed), ``heartbeat.json`` (a snapshot so a ping mid-search does not replay the
whole log), and ``progress.json`` (where the work happening RIGHT NOW is). There
are no pickles: state is whatever replaying the log reconstructs.

The two status files are deliberately separate and answer different questions.
``heartbeat.json`` is written AFTER a fit completes and says what the search has
achieved. ``progress.json`` is written DURING a fit and says where that fit has
got to. Only the second one can answer "is it wedged?", because a submit that
refits forty groups is otherwise silent for minutes.

Every mutation of that state goes through ``run_lock``, because the driver runs
SEVERAL candidates from one prompt at once (upstream's ``samples_per_prompt`` is
4) and the log's line count IS the next ``sample_order``. See ``run_lock`` and
``append_next_submission`` for what was measured before the lock existed.

Split out of ``cli.py`` so the verbs stay readable; the layout itself is unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import typer

from . import fit as fit_mod

# POSIX advisory locking, which is what serializes two `wheeler llmsr submit`
# PROCESSES against one run dir. Guarded because Windows has no `flock`; there,
# `run_lock` refuses rather than pretending to have locked anything, since the
# invariant it protects (no two submissions share a sample_order) cannot be
# honoured without it.
_HAVE_FLOCK = True
try:
    import fcntl
except ImportError:  # pragma: no cover - not reachable on darwin or linux
    _HAVE_FLOCK = False

logger = logging.getLogger(__name__)

_RUNS_ROOT = Path(".wheeler/llmsr/runs")

PROGRESS_FILE = "progress.json"
HEARTBEAT_FILE = "heartbeat.json"
SUBMISSIONS_FILE = "submissions.jsonl"
PROMPTS_DIR = "prompts"
PROMPTS_FILE = "prompts.jsonl"
LOCK_FILE = "run.lock"

# How long a writer waits for the lock before giving up. Generous by three orders
# of magnitude: the lock is held for a count plus one append (microseconds), never
# across a fit, which is the whole reason four candidates from one prompt can be
# fitted in parallel. So a wait this long means a crashed holder, not contention,
# and saying so beats blocking a scientist's terminal forever.
LOCK_TIMEOUT_SECONDS = 60.0
_LOCK_POLL_SECONDS = 0.02


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


@contextmanager
def run_lock(run_dir: Path) -> Iterator[None]:
    """Hold one run dir's write lock for the block. Exclusive, across processes.

    Why this exists, measured rather than reasoned about. ``submit`` computed its
    ``sample_order`` as the line count of ``submissions.jsonl`` and then appended,
    with no lock in between. Driving four real ``submit`` subprocesses at one run
    (which is the normal path: ``prompt`` reports upstream's
    ``samples_per_prompt`` of 4, and the act generates that many bodies from one
    context) produced sample_orders ``[0, 1, 2, 3, 4, 4, 4, 4]``: every candidate
    in the batch read the same count.

    That does not stay inside the run dir. ``transfer_ingest`` keys a transfer's
    Execution on ``f"{run_id}|{data_path}|{sample_order}"``, so two DIFFERENT
    candidates sharing an order mint the same session_id and the same Finding ids
    and silently overwrite each other's numbers, which reads as an update rather
    than as a collision. ``transfer.py`` also resolves ``--sample-order`` with
    ``named[0]``, quietly taking the first of two different forms.

    The lock covers the count-then-append and the prompt-file allocation, and
    nothing else. It is deliberately NOT held across a fit: a fit runs for minutes
    and holding it there would serialize the batch this lock exists to make safe.

    Advisory ``flock`` on a dedicated ``run.lock`` rather than on
    ``submissions.jsonl`` itself, because the lock also has to cover a file that
    does not exist yet (the next prompt) and a lock taken on a log that a verb may
    legitimately read is one more thing to reason about.
    """
    run_dir = Path(run_dir)
    if not _HAVE_FLOCK:  # pragma: no cover - not reachable on darwin or linux
        raise typer.BadParameter(
            "this platform has no fcntl.flock, so concurrent writes to one LLM-SR "
            "run cannot be made safe. Run one command at a time against a run."
        )
    run_dir.mkdir(parents=True, exist_ok=True)
    fd = os.open(run_dir / LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise typer.BadParameter(
                        f"another process has held the write lock on run "
                        f"{run_dir} for over {LOCK_TIMEOUT_SECONDS:.0f}s "
                        f"({run_dir / LOCK_FILE}). The lock is only ever held for "
                        "a single append, so this means a crashed writer rather "
                        "than a busy one. Check for a stuck `wheeler llmsr` "
                        "process before retrying."
                    ) from None
                time.sleep(_LOCK_POLL_SECONDS)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


class TornSubmissionLog(typer.BadParameter):
    """``submissions.jsonl`` holds a line that is not JSON, so the run is damaged.

    Raised rather than skipped, which is a reversal. Skipping looked
    conservative and was the more destructive choice: the log is the run's ONLY
    state, so a dropped line drops that program from every future replay AND
    shifts every later ``sample_order``, since the order was the line count.
    Measured on a five-line log with the middle line truncated:
    ``_read_submissions`` returned orders ``[0, 1, 3, 4]`` and the next submit
    would have claimed 4, which was already taken. One partial write became
    silent data loss plus a duplicate id.

    The bytes are still on disk, so this is recoverable by hand, which is the
    other reason to stop: a verb that keeps writing makes the repair harder.
    """


def _parse_submissions(path: Path) -> list[dict]:
    """Every record in the log, or a loud failure naming the damaged line."""
    out = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise TornSubmissionLog(
                f"{path} line {lineno} is not valid JSON ({exc}), so this run's "
                "log is incomplete. Every later sample_order was derived from the "
                "line count, so continuing would both lose that candidate and "
                "reuse an id. The bytes are still on disk, so repair or delete "
                f"that line and retry. Records that parsed before it: {len(out)}."
            ) from exc
    return out


def _read_submissions(run_dir: Path) -> list[dict]:
    """Every candidate this run recorded, in order.

    Unlocked on purpose. Appends are serialized by ``run_lock`` and each record is
    ONE buffered ``write()`` of a complete line, so a reader observes whole lines:
    measured with 8 concurrent writers appending through ``_append_line`` at
    record sizes from 460 bytes to 80 KB, 0 lines out of 1280 were torn. Should a
    platform ever split that write, ``_parse_submissions`` says so loudly instead
    of shifting every later id.
    """
    path = Path(run_dir) / SUBMISSIONS_FILE
    if not path.exists():
        return []
    return _parse_submissions(path)


def _append_line(path: Path, record: dict) -> None:
    """One JSON object as one line, in one write.

    The line is assembled before the call so the append is a single buffered
    write rather than two (the object, then the newline): a second write is a
    second opportunity for another writer's record to land in between.
    """
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def _append_submission(run_dir: Path, record: dict) -> None:
    """Append one record exactly as given. Caller owns ``sample_order``.

    For the seed at ``init``, which is order 0 by definition in a run dir that
    nothing else can be writing yet. Everything after it comes through
    ``append_next_submission``, which allocates the order under the same lock it
    appends under.
    """
    with run_lock(run_dir):
        _append_line(Path(run_dir) / SUBMISSIONS_FILE, record)


def append_next_submission(run_dir: Path, record: dict) -> int:
    """Claim the next ``sample_order``, append the record under it, return it.

    The claim and the append are ONE critical section, which is the fix for the
    measured ``[0, 1, 2, 3, 4, 4, 4, 4]`` collision: reading the count and
    appending as two steps let every member of a parallel batch read the same
    count. See ``run_lock`` for why a duplicate order is worse than it looks.

    ``sample_order`` is written FIRST in the record, whatever the caller's dict
    order, because ``parity_singledata.py`` compares ``submissions.jsonl`` with no
    tolerance at all and key order is part of the bytes.
    """
    log = Path(run_dir) / SUBMISSIONS_FILE
    with run_lock(run_dir):
        order = len(_parse_submissions(log)) if log.exists() else 0
        _append_line(log, {
            "sample_order": order,
            **{k: v for k, v in record.items() if k != "sample_order"},
        })
    return order


def claim_prompt(
    run_dir: Path, text: str, *, island_id: int, version_generated: int
) -> Path:
    """Write the next ``prompts/<n>.txt`` and record where that prompt routed.

    Two defects in one place. The name was allocated as
    ``len(glob("*.txt"))``, so four concurrent ``prompt`` calls all reported
    ``prompts/0.txt`` and three of the four prompts were overwritten by the last
    writer (measured: 1 distinct path from 4 calls, 1 file on disk). And the
    ROUTING (which island, which version) existed on stdout only, so once a
    terminal scrolled there was nothing on disk saying which island a submission
    was supposed to go to.

    So the allocation happens under the run lock AND with an exclusive create: the
    lock keeps Wheeler processes apart, and ``O_EXCL`` means that even without a
    lock (a stale file, an editor, anything else in the directory) an existing
    prompt is never overwritten, only skipped past.

    ``prompts.jsonl`` is the audit trail: one line per prompt handed out, so the
    island sequence of a whole run is reconstructable after the fact.
    """
    run_dir = Path(run_dir)
    prompts_dir = run_dir / PROMPTS_DIR
    prompts_dir.mkdir(parents=True, exist_ok=True)
    with run_lock(run_dir):
        n = len(list(prompts_dir.glob("*.txt")))
        while True:
            path = prompts_dir / f"{n}.txt"
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                n += 1
                continue
            break
        with os.fdopen(fd, "w") as f:
            f.write(text)
        _append_line(run_dir / PROMPTS_FILE, {
            "prompt_index": n,
            "prompt_file": str(path),
            "island_id": island_id,
            "version_generated": version_generated,
            "at": _now(),
            "at_epoch": time.time(),
        })
    return path


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

    Atomic (tmp + rename, pid-tagged) for the same reason ``progress.json`` is:
    several submits from one prompt finish at their own pace and each refreshes
    this file, so a plain ``write_text`` would let two of them interleave into one
    payload. ``status_payload`` survives that by falling back to a full log
    replay, which is exactly the cost the heartbeat exists to avoid.
    """
    prog = _progress_core(run_dir, meta)
    prog["updated"] = _now()
    _write_json_atomic(Path(run_dir) / HEARTBEAT_FILE, prog)


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
