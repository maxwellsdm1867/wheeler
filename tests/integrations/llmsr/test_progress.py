"""The during-the-fit progress channel (issue #107, slice 0b).

The problem: ``heartbeat.json`` is written only AFTER a fit completes, so a
submit that refits forty groups is silent for minutes and there is no way to ask
where it is, or whether it is wedged. ``progress.json`` is the channel that
answers that, and ``status`` is where the answer surfaces.

Two claims are under test. The first is that the heartbeat actually beats: while
a fit is IN FLIGHT, ``status`` reports ``phase == "fitting"`` and a rising
``done`` count. A check made after the fit finished would prove nothing, so the
in-flight assertions here run against a fit held open by sentinel files (see
``TestStatusWhileTheFitIsInFlight``) rather than against a race with the clock.
The second is that this is pure telemetry: a caller that passes no
``progress_path`` gets bit-for-bit the same numbers it got before the channel
existed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr import runs as runs_mod

# ------------------------------------------------------------------ helpers

LINEAR = (
    "import numpy as np\n"
    "def equation(x1, params):\n"
    "    return params[0] * x1\n"
)

# An equation body whose groups can be held open on demand: a group whose first
# input row carries a gate value blocks until the matching sentinel file appears.
# This is what lets the in-flight assertions be a proof rather than a race, on
# any machine at any speed: the fit physically cannot advance past a gate until
# the test opens it.
GATE_BODY = (
    "    import os, time\n"
    "    gate = {41.0: 'gate-a', 42.0: 'gate-b'}.get(float(x1[0]))\n"
    "    while gate is not None and not os.path.exists(gate):\n"
    "        time.sleep(0.01)\n"
    "    return params[0] * x1\n"
)

_N_CELLS = 5


def _gated_project(tmp_path: Path) -> None:
    """A runnable project whose first and last group each sit behind a gate."""
    (tmp_path / "spec.txt").write_text(
        "import numpy as np\n\n"
        "MAX_NPARAMS = 1\n\n"
        "@evaluate.run\n"
        "def evaluate(data):\n"
        "    return 0.0\n\n"
        "@equation.evolve\n"
        "def equation(x1, params):\n" + GATE_BODY
    )
    rows = ["cell_id,x1,y"]
    for cell in range(_N_CELLS):
        # The gate value has to be the group's FIRST row, since that is the
        # element the body looks at.
        xs = [0.5 + 0.25 * i for i in range(6)]
        if cell == 0:
            xs[0] = 41.0
        elif cell == _N_CELLS - 1:
            xs[0] = 42.0
        rows += [f"c{cell},{x:.17g},{3.0 * x:.17g}" for x in xs]
    (tmp_path / "train.csv").write_text("\n".join(rows) + "\n")


# A minimally complete submission record: `_progress_core` reads `body` and
# `sample_order` off the best one.
def _submission(**over) -> dict:
    return {"valid": True, "score": 1.0, "value": 0.5, "body": "x\n",
            "sample_order": 0, **over}


def _seed_run(run_id: str = "r1") -> tuple[Path, dict]:
    """A run dir that already has a heartbeat, as any run past its first submit does."""
    run_dir = runs_mod._RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": run_id,
        "metric": "mse",
        "generator": "claude",
        "created_epoch": time.time(),
    }
    (run_dir / "meta.json").write_text(json.dumps(meta))
    runs_mod._write_heartbeat(run_dir, meta)
    return run_dir, meta


# -------------------------------------------------------------- the file itself

class TestProgressFile:
    def test_round_trips(self, tmp_path):
        runs_mod.write_progress(tmp_path, {"phase": "fit", "done": 3, "total": 9})
        assert runs_mod.read_progress(tmp_path) == {"phase": "fit", "done": 3, "total": 9}

    def test_leaves_no_temp_file_behind(self, tmp_path):
        runs_mod.write_progress(tmp_path, {"done": 1})
        assert [p.name for p in tmp_path.iterdir()] == [runs_mod.PROGRESS_FILE]

    def test_creates_a_missing_run_dir(self, tmp_path):
        target = tmp_path / "nested" / "deeper"
        runs_mod.write_progress(target, {"done": 1})
        assert runs_mod.read_progress(target) == {"done": 1}

    def test_absent_reads_as_none(self, tmp_path):
        assert runs_mod.read_progress(tmp_path) is None

    def test_a_torn_write_reads_as_none_rather_than_raising(self, tmp_path):
        """A status ping landing mid-write must not brick the verb reporting on it."""
        (tmp_path / runs_mod.PROGRESS_FILE).write_text('{"phase": "fi')
        assert runs_mod.read_progress(tmp_path) is None

    def test_a_non_object_payload_reads_as_none(self, tmp_path):
        (tmp_path / runs_mod.PROGRESS_FILE).write_text("[1, 2, 3]")
        assert runs_mod.read_progress(tmp_path) is None


# --------------------------------------------------------------------- parity

class TestNoPathIsUnchanged:
    """Telemetry must not perturb numerics: the whole S1 slice rests on this."""

    BODY = (
        "import numpy as np\n"
        "def equation(x1, params):\n"
        "    return params[0] * np.exp(params[1] * x1) + params[2]\n"
    )

    # Captured by running this exact fit on main (81d75d1), BEFORE the progress
    # channel existed. Hex float literals, so the comparison is bit-for-bit and
    # not to within some tolerance that could hide a perturbed optimizer path.
    GOLD_SCORE = "-0x1.b0f27c5277af6p-8"
    GOLD_PARAMS = {
        "g1": [
            "0x1.fff52285e3123p+0", "0x1.333a06382d256p-2", "-0x1.ffeafe2492e2ep-1",
            "0x1.5434c25979320p+2", "0x1.378dcd5895438p-1", "-0x1.2377ee3fbf5c5p+2",
            "-0x1.5c1c3777655d0p-2", "0x1.2b206c94280e1p+3", "0x1.4d586d763805ep+3",
            "-0x1.b4da68699fb68p+1",
        ],
        "g2": [
            "0x1.1936c32750810p+9", "-0x1.f66ba8c2c71c0p-10", "-0x1.1809616985360p+9",
            "-0x1.f1efcc91f26d4p+1", "-0x1.4cf24942df414p+1", "0x1.2bbb0f4efc09ep+3",
            "-0x1.a315ffec6a9bbp+2", "0x1.7a6e500491f00p+1", "-0x1.3f79e94cdab76p+3",
            "0x1.fef1004c4348fp+2",
        ],
    }

    def _groups(self):
        rng = np.random.default_rng(11)
        out = []
        for name, (a, b, c) in {"g1": (2.0, 0.3, -1.0), "g2": (-1.5, 0.7, 4.0)}.items():
            x = rng.uniform(-1.0, 1.0, 30)
            out.append((name, x.reshape(-1, 1), a * np.exp(b * x) + c))
        return out

    def test_matches_the_values_recorded_before_this_channel_existed(self):
        result = fit_mod.evaluate_body_grouped(
            self.BODY, "equation", self._groups(), metrics_mod.MSE
        )
        assert result.valid
        assert result.score is not None
        assert result.score.hex() == self.GOLD_SCORE
        for label, gold in self.GOLD_PARAMS.items():
            assert [p.hex() for p in result.params_per_group[label]] == gold

    def test_passing_a_path_changes_no_number(self, tmp_path):
        """The pings are written; the fit that wrote them is identical regardless."""
        without = fit_mod.evaluate_body_grouped(
            self.BODY, "equation", self._groups(), metrics_mod.MSE
        )
        with_path = fit_mod.evaluate_body_grouped(
            self.BODY, "equation", self._groups(), metrics_mod.MSE,
            progress_path=tmp_path / runs_mod.PROGRESS_FILE,
        )
        assert with_path.score == without.score
        assert with_path.value == without.value
        assert with_path.per_group == without.per_group
        assert with_path.per_group_value == without.per_group_value
        assert with_path.params_per_group == without.params_per_group
        assert runs_mod.read_progress(tmp_path) is not None

    def test_no_path_writes_no_file(self, tmp_path):
        fit_mod.evaluate_body_grouped(
            self.BODY, "equation", self._groups(), metrics_mod.MSE
        )
        assert list(tmp_path.iterdir()) == []

    def test_an_unwritable_progress_path_does_not_invalidate_the_candidate(self, tmp_path):
        """The fit is the product; progress is commentary on it.

        A full disk, or a run dir pulled out from under a running fit, must cost
        the telemetry and nothing else. Here the ping's parent directory is a
        FILE, so every write attempt fails.
        """
        (tmp_path / "blocked").write_text("not a directory")
        result = fit_mod.evaluate_body_grouped(
            self.BODY, "equation", self._groups(), metrics_mod.MSE,
            progress_path=tmp_path / "blocked" / runs_mod.PROGRESS_FILE,
        )
        assert result.valid
        assert result.score is not None
        assert result.score.hex() == self.GOLD_SCORE

    def test_evaluate_body_still_takes_no_progress_path(self):
        """The ungrouped wrapper keeps the surface it had; nothing to opt out of."""
        X = np.linspace(-1.0, 1.0, 20).reshape(-1, 1)
        result = fit_mod.evaluate_body(LINEAR, "equation", X, 3.0 * X[:, 0], metrics_mod.MSE)
        assert result.valid


# ------------------------------------------------------------- the ping payload

class TestPingPayload:
    def test_reports_the_group_that_just_landed_and_the_total(self, tmp_path):
        groups = [
            (f"g{i}", np.linspace(0.5, 2.0, 6).reshape(-1, 1), 3.0 * np.linspace(0.5, 2.0, 6))
            for i in range(3)
        ]
        fit_mod.evaluate_body_grouped(
            LINEAR, "equation", groups, metrics_mod.MSE, max_nparams=1,
            progress_path=tmp_path / runs_mod.PROGRESS_FILE,
        )
        ping = runs_mod.read_progress(tmp_path)
        assert ping is not None
        assert ping["phase"] == "fit"
        assert ping["group"] == "g2"
        assert ping["done"] == 3
        assert ping["total"] == 3
        # Placeholder until S2 gives a run more than one dataset to score against.
        assert ping["dataset"] == fit_mod.UNGROUPED
        assert ping["at"]


# ------------------------------------------------------------------- the phases

class TestPhase:
    """The rule: fitting > done > init > idle. Documented on runs._phase."""

    def test_no_submission_yet_is_init(self):
        run_dir, meta = _seed_run()
        (run_dir / runs_mod.HEARTBEAT_FILE).unlink()
        assert runs_mod._progress(run_dir, meta)["phase"] == "init"

    def test_a_finished_fit_is_idle(self):
        run_dir, meta = _seed_run()
        runs_mod._append_submission(run_dir, _submission())
        runs_mod.write_progress(run_dir, {"done": 3, "total": 3})
        runs_mod._write_heartbeat(run_dir, meta)  # written after, so it wins
        _stamp(run_dir / runs_mod.PROGRESS_FILE, -10)
        _stamp(run_dir / runs_mod.HEARTBEAT_FILE, -5)
        assert runs_mod._progress(run_dir, meta)["phase"] == "idle"

    def test_a_progress_ping_newer_than_the_heartbeat_is_fitting(self):
        run_dir, meta = _seed_run()
        runs_mod._append_submission(run_dir, _submission())
        runs_mod.write_progress(run_dir, {"done": 1, "total": 40})
        _stamp(run_dir / runs_mod.HEARTBEAT_FILE, -30)
        _stamp(run_dir / runs_mod.PROGRESS_FILE, -20)
        state = runs_mod._progress(run_dir, meta)
        assert state["phase"] == "fitting"
        # The wedged signature: still fitting, and visibly not moving.
        assert state["seconds_since_update"] >= 19

    def test_a_concluded_run_is_done(self):
        run_dir, meta = _seed_run()
        runs_mod._append_submission(run_dir, _submission())
        (run_dir / "best.json").write_text("{}")
        assert runs_mod._progress(run_dir, meta)["phase"] == "done"

    def test_an_in_flight_fit_outranks_a_concluded_run(self):
        """Submitting after picking a winner is legal; the live fit is the truth."""
        run_dir, meta = _seed_run()
        runs_mod._append_submission(run_dir, _submission())
        (run_dir / "best.json").write_text("{}")
        runs_mod.write_progress(run_dir, {"done": 2, "total": 9})
        assert runs_mod._progress(run_dir, meta)["phase"] == "fitting"

    def test_a_reported_ping_is_never_contradicted_by_the_phase(self, monkeypatch):
        """The first ping of a fit appears between two syscalls of one status read.

        Reading the mtime before the payload made that window observable: the
        reader published a live ``progress`` block under ``phase: init``, because
        the file had not existed yet when it was stat-ed. Existence therefore
        comes from the payload, and the stat only measures staleness. Simulated
        here by failing the stat of the file that reads back fine.
        """
        run_dir, meta = _seed_run()
        runs_mod._append_submission(run_dir, _submission())
        runs_mod.write_progress(run_dir, {"done": 1, "total": 9})
        real = runs_mod._mtime
        monkeypatch.setattr(
            runs_mod, "_mtime",
            lambda p: None if p.name == runs_mod.PROGRESS_FILE else real(p),
        )
        state = runs_mod._progress(run_dir, meta)
        assert state["progress"]["done"] == 1
        assert state["phase"] == "fitting"

    def test_seconds_since_update_is_none_when_nothing_has_been_written(self):
        run_dir, meta = _seed_run()
        (run_dir / runs_mod.HEARTBEAT_FILE).unlink()
        assert runs_mod._progress(run_dir, meta)["seconds_since_update"] is None


class TestStatusPayload:
    def test_keeps_the_heartbeat_snapshot_and_overlays_the_live_state(self):
        run_dir, meta = _seed_run()
        runs_mod._append_submission(run_dir, _submission())
        runs_mod._write_heartbeat(run_dir, meta)
        runs_mod.write_progress(run_dir, {"done": 4, "total": 40})

        payload = runs_mod.status_payload(run_dir, meta)
        assert payload["n_samples"] == 1          # from the heartbeat snapshot
        assert payload["best_value"] == 0.5       # from the heartbeat snapshot
        assert payload["phase"] == "fitting"      # recomputed, not from the file
        assert payload["progress"]["done"] == 4
        assert payload["seconds_since_update"] is not None

    def test_the_heartbeat_file_stays_a_snapshot(self):
        """The live fields are recomputed per read; freezing a phase into a file
        would make it wrong the moment the run moved."""
        run_dir, meta = _seed_run()
        stored = json.loads((run_dir / runs_mod.HEARTBEAT_FILE).read_text())
        assert "phase" not in stored
        assert "seconds_since_update" not in stored
        assert "progress" not in stored


# --------------------------------------------------------- the in-flight claim

class TestStatusWhileTheFitIsInFlight:
    """The point of the slice: ask a RUNNING fit where it is and get an answer.

    Every assertion here fires against a real ``wheeler llmsr status`` process
    while a real ``wheeler llmsr init`` / ``submit`` process is still fitting. A
    post-hoc reading of ``progress.json`` would prove nothing, and a check timed
    against the clock would be flaky, so the fit is PINNED instead: group ``c0``
    blocks until this test creates ``gate-a`` and group ``c4`` blocks until it
    creates ``gate-b``. The fit holds at a known position for as long as the
    assertions need, however slow the machine.
    """

    def test_init_reports_fitting_and_a_rising_done(self, tmp_path):
        _gated_project(tmp_path)
        proc = _spawn(tmp_path, [
            "llmsr", "init", "--run-id", "gated", "--spec", "spec.txt",
            "--data", "train.csv", "--metric", "mse", "--group-by", "cell_id",
        ])
        seen = []
        try:
            # Pinned on c0: the fit has started and nothing has completed yet.
            start = _await_status(tmp_path, "gated", lambda s: s["progress"]["done"] == 0)
            seen.append(start)
            assert proc.poll() is None
            assert start["phase"] == "fitting"
            # The start ping, written before the fork: it is what makes a fit
            # wedged on its FIRST group visible as a fit rather than as an idle run.
            assert start["progress"]["group"] is None
            assert start["progress"]["total"] == _N_CELLS
            assert start["seconds_since_update"] is not None

            (tmp_path / "gate-a").touch()

            # Pinned on c4, the last group: every earlier one has landed.
            late = _await_status(
                tmp_path, "gated", lambda s: s["progress"]["done"] == _N_CELLS - 1
            )
            seen.append(late)
            assert proc.poll() is None, "the fit finished before we could observe it"
            assert late["phase"] == "fitting"
            assert late["progress"]["group"] == f"c{_N_CELLS - 2}"

            # Staleness is visible: no ping was written while the fit sat on the
            # gate, so the counter climbs. That is the wedged signature, and it
            # is the difference between "slow" and "stuck".
            later = _cli_status(tmp_path, "gated")
            assert later["phase"] == "fitting"
            assert later["seconds_since_update"] > late["seconds_since_update"]
        finally:
            _release(tmp_path)
            assert proc.wait(timeout=120) == 0

        # Sampled more than once, and `done` only ever went up.
        dones = [s["progress"]["done"] for s in seen]
        assert dones == sorted(dones)
        assert len(set(dones)) >= 2, f"done never rose: {dones}"
        assert dones == [0, _N_CELLS - 1]

    def test_submit_reports_fitting_over_an_existing_heartbeat(self, tmp_path):
        """The case a heartbeat-only status could not answer.

        After the first fit there IS a heartbeat, and it describes the search as
        of the last COMPLETED fit. Echoing it would report a finished run while a
        forty-group refit is grinding away underneath.
        """
        _gated_project(tmp_path)
        _release(tmp_path)  # let init through unhindered
        _cli(tmp_path, [
            "llmsr", "init", "--run-id", "gated", "--spec", "spec.txt",
            "--data", "train.csv", "--metric", "mse", "--group-by", "cell_id",
        ])
        run_dir = tmp_path / ".wheeler/llmsr/runs/gated"
        assert (run_dir / runs_mod.HEARTBEAT_FILE).exists()
        assert _cli_status(tmp_path, "gated")["phase"] == "idle"

        # Re-close the gates, then submit the same gated body as a candidate.
        for gate in ("gate-a", "gate-b"):
            (tmp_path / gate).unlink()
        (tmp_path / "body.txt").write_text(GATE_BODY)
        proc = _spawn(tmp_path, [
            "llmsr", "submit", "--run", "gated", "--body-file", "body.txt",
            "--island-id", "0", "--version-generated", "0",
        ])
        try:
            state = _await_status(tmp_path, "gated", lambda s: s["progress"]["done"] == 0)
            assert proc.poll() is None
            assert state["phase"] == "fitting"
            # The snapshot fields still come from the heartbeat; the live ones do not.
            assert state["n_samples"] == 1
            assert state["best_value"] is not None
        finally:
            _release(tmp_path)
            assert proc.wait(timeout=120) == 0

        assert _cli_status(tmp_path, "gated")["n_samples"] == 2


# -------------------------------------------------------------------- the CLI

class TestCliRun:
    """A real run through the CLI: init writes pings, status reports the phase."""

    def _project(self, tmp_path: Path) -> None:
        (tmp_path / "spec.txt").write_text(
            "import numpy as np\n\n"
            "MAX_NPARAMS = 2\n\n"
            "@evaluate.run\n"
            "def evaluate(data):\n"
            "    return 0.0\n\n"
            "@equation.evolve\n"
            "def equation(x1, params):\n"
            "    return params[0] * x1 + params[1]\n"
        )
        rows = ["cell_id,x1,y"]
        for cell, (a, b) in {"c01": (2.0, 1.0), "c02": (-3.0, 4.0)}.items():
            for i in range(12):
                x = -2.0 + 0.35 * i
                rows.append(f"{cell},{x:.17g},{a * x + b:.17g}")
        (tmp_path / "train.csv").write_text("\n".join(rows) + "\n")

    def test_init_leaves_a_ping_and_status_reports_idle(self, tmp_path):
        self._project(tmp_path)
        out = _cli(tmp_path, [
            "llmsr", "init", "--spec", "spec.txt", "--data", "train.csv",
            "--metric", "mse", "--group-by", "cell_id",
        ])
        run_id = json.loads(out)["run_id"]
        run_dir = tmp_path / ".wheeler/llmsr/runs" / run_id

        ping = runs_mod.read_progress(run_dir)
        assert ping is not None
        assert ping["done"] == ping["total"] == 2  # both cells were fitted

        status = _cli_status(tmp_path, run_id)
        # The heartbeat was written after the last ping, so the fit is over.
        assert status["phase"] == "idle"
        assert status["seconds_since_update"] is not None
        assert status["n_samples"] == 1
        assert status["progress"]["done"] == 2

    def test_status_reports_done_once_a_winner_is_picked(self, tmp_path):
        self._project(tmp_path)
        run_id = json.loads(_cli(tmp_path, [
            "llmsr", "init", "--spec", "spec.txt", "--data", "train.csv",
            "--metric", "mse", "--group-by", "cell_id",
        ]))["run_id"]
        _cli(tmp_path, ["llmsr", "best", "--run", run_id])
        assert _cli_status(tmp_path, run_id)["phase"] == "done"


# ------------------------------------------------------------------ test utils

def _stamp(path: Path, offset: float) -> None:
    """Force an mtime relative to now, so the phase rule is tested, not write speed."""
    when = time.time() + offset
    os.utime(path, (when, when))


def _await_status(cwd: Path, run_id: str, accept, timeout: float = 60.0) -> dict:
    """Poll a real ``llmsr status`` until it reports the position we are waiting for.

    Tolerates a failing call, because the run dir does not exist for the first
    moments of ``init``. Fails loudly rather than hanging: the gate holding the
    fit means the awaited position, once reached, is held indefinitely, so a
    timeout here is a real failure and never just a slow machine.
    """
    deadline = time.time() + timeout
    last: dict | None = None
    while time.time() < deadline:
        state = _status_or_none(cwd, run_id)
        if state is not None:
            last = state
            if "progress" in state and accept(state):
                return state
        time.sleep(0.02)
    raise AssertionError(f"status never reached the expected position (last: {last})")


def _release(cwd: Path) -> None:
    """Open every gate, so a failed assertion cannot leave a fit pinned forever."""
    for gate in ("gate-a", "gate-b"):
        (cwd / gate).touch()


def _env(cwd: Path) -> dict:
    root = str(Path(__file__).resolve().parents[3])
    return {"PATH": "/usr/bin:/bin", "PYTHONPATH": root, "HOME": str(cwd)}


def _cli(cwd: Path, args: list[str]) -> str:
    out = subprocess.run(
        [sys.executable, "-m", "wheeler.tools.cli", *args],
        cwd=cwd, capture_output=True, text=True, env=_env(cwd),
    )
    assert out.returncode == 0, out.stderr
    return out.stdout


def _spawn(cwd: Path, args: list[str]) -> subprocess.Popen:
    """Start a verb without waiting, so the test can question it while it works."""
    return subprocess.Popen(
        [sys.executable, "-m", "wheeler.tools.cli", *args],
        cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=_env(cwd),
    )


def _status_or_none(cwd: Path, run_id: str) -> dict | None:
    """One ``llmsr status`` reading, or None while the run dir is not there yet."""
    out = subprocess.run(
        [sys.executable, "-m", "wheeler.tools.cli", "llmsr", "status", "--run", run_id],
        cwd=cwd, capture_output=True, text=True, env=_env(cwd),
    )
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except ValueError:
        return None


def _cli_status(cwd: Path, run_id: str) -> dict:
    return json.loads(_cli(cwd, ["llmsr", "status", "--run", run_id]))


@pytest.fixture(autouse=True)
def _open_the_gates(tmp_path):
    """Belt and braces: no gated fit outlives its test, whatever went wrong."""
    yield
    _release(tmp_path)
