"""What breaks when a run has more than one writer, or a damaged log.

Upstream LLM-SR is one long-lived process. Wheeler inverted its loop into CLI
verbs and rebuilds the experience buffer by replaying ``submissions.jsonl`` on
every call, so the log's LINE COUNT is the next ``sample_order`` and the run dir is
the only state there is. The driver draws upstream's ``samples_per_prompt`` (4)
candidates from one prompt, so "several writers at one run dir" is the normal path
rather than an exotic one.

Every defect pinned here was found by execution, and none of them was reachable
from the existing suite, which drives ``init`` then ``submit`` in ONE process
through ``CliRunner``. That hides two whole classes of failure: anything that
needs a COLD process (a registry loaded as a side effect, a module-level cache)
and anything that needs REAL concurrency (a count read before an append). So the
tests here spawn real subprocesses wherever the defect needs one, and say in each
case what was measured before the fix.

The numbers in the docstrings are measurements, not illustrations.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import cli as cli_mod
from wheeler.integrations.llmsr import runs as runs_mod
from wheeler.integrations.llmsr.cli import llmsr_app

runner = CliRunner()

RUNS_ROOT = Path(".wheeler/llmsr/runs")

# The form the fixture table really follows, so a submitted candidate is valid and
# the parallel batch below is a batch of accepted submissions rather than of
# rejections (a rejected candidate is still appended, but a valid one exercises
# the live `register_program` too).
TRUE_BODY = "    return params[0]*x1 + params[1]*x2\n"

# A body that cannot fit anything, for the runs that need an INVALID candidate.
BROKEN_BODY = "    return no_such_name * x1\n"

_SPEC = (
    '"""toy"""\n'
    "import numpy as np\n\n"
    "MAX_NPARAMS = 2\n\n\n"
    "@evaluate.run\n"
    "def evaluate(data: dict):\n"
    "    return 0.0\n\n\n"
    "@equation.evolve\n"
    "def equation(x1: np.ndarray, x2: np.ndarray, params: np.ndarray) -> np.ndarray:\n"
    "    return {seed_body}\n"
)


def _write_spec(path: str = "spec.txt", *, seed_body: str = "params[0]*x1") -> str:
    """A runnable spec. ``seed_body`` decides whether ``init``'s seed fit lands.

    An unfittable seed is not a contrivance: it is the state N9 and N8 live in,
    and ``init`` used to exit 0 on it without saying anything.
    """
    Path(path).write_text(_SPEC.format(seed_body=seed_body))
    return path


def _write_csv(path: str = "train.csv", n: int = 6) -> str:
    """A tiny exact table, y = 2.5*x1 - 1.0*x2. Small because these tests fit a
    lot of candidates and none of them is about fit quality."""
    rng = np.random.default_rng(11)
    lines = ["x1,x2,y"]
    for _ in range(n):
        x1, x2 = (float(v) for v in rng.uniform(-3.0, 3.0, 2))
        lines.append(f"{x1:.17g},{x2:.17g},{2.5 * x1 - 1.0 * x2:.17g}")
    Path(path).write_text("\n".join(lines) + "\n")
    return path


# ------------------------------------------------------------------- harnesses

def _squash(text: str) -> str:
    """CLI output with Rich's box drawing and line wrapping taken back out.

    A ``typer.BadParameter`` is rendered inside a bordered panel wrapped to the
    terminal width, so a message this asserts on arrives split across lines with
    ``|`` characters in the middle of it. Matching the raw text would make these
    tests pass or fail on the width of the box.
    """
    return " ".join(text.replace("│", " ").split())


def _text(result) -> str:
    """Everything a caller could read off an invocation, error paths included.

    click 8.4 puts a ``UsageError`` on stderr and mixes stderr into
    ``result.output``, and a crash lands in ``result.exception`` instead of in
    either. Asserting on one of the three is how a test passes because the message
    went somewhere it was not looking.
    """
    return _squash(f"{result.output} {result.stderr} {result.exception!r}")


def _out(result) -> dict:
    assert result.exit_code == 0, _text(result)
    return json.loads(result.output.strip().splitlines()[-1])


def _cli(*args: str) -> subprocess.CompletedProcess:
    """One `wheeler llmsr ...` in a REAL, cold process."""
    return subprocess.run(
        [sys.executable, "-m", "wheeler.tools.cli", "llmsr", *args],
        capture_output=True, text=True,
    )


def _spawn(*args: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "wheeler.tools.cli", "llmsr", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def _init(run_id: str, *extra: str, seed_body: str = "params[0]*x1") -> Path:
    """A run in the scratch cwd, through the real CLI. Returns its run dir."""
    _write_spec(seed_body=seed_body)
    _write_csv()
    result = _cli("init", "--run-id", run_id, "--spec", "spec.txt",
                  "--data", "train.csv", "--metric", "mse", *extra)
    assert result.returncode == 0, result.stdout + result.stderr
    return RUNS_ROOT / run_id


def _submissions(run_dir: Path) -> list[dict]:
    """The log read WITHOUT going through `runs._read_submissions`.

    Deliberately independent: these tests assert things about what that function
    does, so they must not read the log through it.
    """
    return [
        json.loads(line)
        for line in (run_dir / runs_mod.SUBMISSIONS_FILE).read_text().splitlines()
        if line.strip()
    ]


# ===========================================================================
# N1. Concurrent submits must not collide, and must not tear a line
# ===========================================================================

class TestConcurrentSubmitsGetDistinctSampleOrders:
    """The count-then-append was two steps, so a parallel batch collided.

    Measured before the lock, with four real ``submit`` subprocesses against one
    run: ``sample_order`` came out ``[0, 1, 2, 3, 4, 4, 4, 4]``. Every member of
    the batch read the same line count and then appended under it.

    This is not a run-dir-local untidiness. ``transfer_ingest._transfer_key``
    digests ``f"{run_id}|{data_path}|{sample_order}"`` into the transfer
    Execution's ``session_id``, and ``discover._finding_id`` is deterministic too,
    so two DIFFERENT candidates sharing an order mint the same graph ids and
    silently overwrite each other's numbers. An overwrite reads as an update,
    which is worse than a duplicate. ``transfer.resolve_candidate`` also takes
    ``named[0]`` of a ``--candidate`` lookup, quietly transferring the first of two
    different forms.

    Real subprocesses, because that is the only way to get real concurrency: the
    existing suite drives the same verbs through ``CliRunner`` in one process,
    where a collision cannot happen.
    """

    def test_four_concurrent_submits_write_four_distinct_orders(self):
        run_dir = _init("conc-submit", "--islands", "4")
        Path("body.py").write_text(TRUE_BODY)

        procs = [
            _spawn("submit", "--run", str(run_dir), "--body-file", "body.py",
                   "--island-id", str(i), "--version-generated", "1")
            for i in range(4)
        ]
        outs = [p.communicate() for p in procs]
        for (out, err), proc in zip(outs, procs):
            assert proc.returncode == 0, out + err

        subs = _submissions(run_dir)
        orders = [s["sample_order"] for s in subs]
        # The seed plus four candidates, every order distinct and contiguous.
        assert len(subs) == 5, orders
        assert sorted(orders) == [0, 1, 2, 3, 4], orders
        # And each subprocess was TOLD the order it actually got, since the act
        # passes that number on to `transfer --candidate`.
        reported = sorted(json.loads(out.strip().splitlines()[-1])["sample_order"]
                          for out, _err in outs)
        assert reported == [1, 2, 3, 4], reported

    def test_no_line_is_torn_and_every_candidate_survives(self):
        """The other half of the invariant: 4 writers, 4 records, 0 damage.

        A record here is around 1 KB and real bodies run to several, well past the
        512 bytes POSIX guarantees an ``O_APPEND`` write is atomic within. Under
        the lock only one writer is inside the append at a time, so the guarantee
        is not being relied on.
        """
        run_dir = _init("conc-tear", "--islands", "4")
        Path("body.py").write_text(TRUE_BODY)
        procs = [
            _spawn("submit", "--run", str(run_dir), "--body-file", "body.py",
                   "--island-id", "0", "--version-generated", "1")
            for _ in range(4)
        ]
        for p in procs:
            out, err = p.communicate()
            assert p.returncode == 0, out + err

        raw = [x for x in (run_dir / runs_mod.SUBMISSIONS_FILE)
               .read_text().splitlines() if x.strip()]
        assert len(raw) == 5
        for lineno, line in enumerate(raw, start=1):
            json.loads(line)  # raises here rather than being counted as torn
        # `_read_submissions` agrees with a byte-level read, which is what a
        # skipped line would break.
        assert len(runs_mod._read_submissions(run_dir)) == len(raw)


class TestTheClaimAndTheAppendAreOneCriticalSection:
    """The invariant at library level: N processes, N distinct orders, no gaps.

    Beside the CLI test rather than instead of it. This one can afford enough
    writers to make a collision overwhelmingly likely if the lock were removed
    (16 claims against a 5-record log), where spawning 16 real CLI processes would
    cost a minute of test time for the same information.
    """

    @staticmethod
    def _claim(run_dir: str) -> int:
        return runs_mod.append_next_submission(
            Path(run_dir), {"body": "b", "valid": True, "score": -1.0}
        )

    def test_sixteen_racing_claims_are_sixteen_distinct_orders(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / runs_mod.SUBMISSIONS_FILE).touch()
        with mp.Pool(8) as pool:
            claimed = pool.map(self._claim, [str(run_dir)] * 16)

        assert sorted(claimed) == list(range(16)), claimed
        on_disk = [s["sample_order"] for s in _submissions(run_dir)]
        assert sorted(on_disk) == list(range(16)), on_disk

    def test_sample_order_is_the_first_key_in_the_record(self, tmp_path):
        """``parity_singledata.py`` compares ``submissions.jsonl`` with NO
        tolerance, so key order is part of the bytes it gates on."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        runs_mod.append_next_submission(run_dir, {"body": "b", "valid": True})
        line = (run_dir / runs_mod.SUBMISSIONS_FILE).read_text().strip()
        assert list(json.loads(line)) == ["sample_order", "body", "valid"]

    def test_a_caller_passed_order_is_never_second_guessed(self, tmp_path):
        """``init``'s seed is order 0 by definition and keeps its own path."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        runs_mod._append_submission(run_dir, {"sample_order": 0, "seed": True})
        assert [s["sample_order"] for s in _submissions(run_dir)] == [0]


class TestConcurrentPromptsClaimDistinctFiles:
    """Two ``prompt`` calls both wrote ``prompts/0.txt``.

    Measured before the fix: 4 concurrent calls, 4 identical reported paths, ONE
    file on disk. Three prompts were overwritten by whichever writer finished
    last, so a submission's ``--version-generated`` referred to a context nobody
    could read back.
    """

    def test_four_concurrent_prompts_get_four_files(self):
        run_dir = _init("conc-prompt", "--islands", "4")
        procs = [_spawn("prompt", "--run", str(run_dir)) for _ in range(4)]
        reported = []
        for p in procs:
            out, err = p.communicate()
            assert p.returncode == 0, out + err
            reported.append(json.loads(out.strip().splitlines()[-1])["prompt_file"])

        assert len(set(reported)) == 4, reported
        on_disk = sorted(p.name for p in (run_dir / runs_mod.PROMPTS_DIR).glob("*.txt"))
        assert on_disk == ["0.txt", "1.txt", "2.txt", "3.txt"], on_disk
        # Every reported path is a file that still holds that prompt's own text.
        for path in reported:
            assert Path(path).read_text().strip(), path

    def test_an_existing_prompt_file_is_never_overwritten(self, tmp_path):
        """``O_EXCL`` as well as the lock, so anything else in the directory (a
        stale file, an editor) costs a skipped index rather than a lost prompt."""
        run_dir = tmp_path / "run"
        (run_dir / runs_mod.PROMPTS_DIR).mkdir(parents=True)
        (run_dir / runs_mod.PROMPTS_DIR / "0.txt").write_text("not ours")

        path = runs_mod.claim_prompt(
            run_dir, "ours", island_id=1, version_generated=2)

        assert path.name == "1.txt"
        assert (run_dir / runs_mod.PROMPTS_DIR / "0.txt").read_text() == "not ours"
        assert path.read_text() == "ours"


# ===========================================================================
# N11. A torn line must be loud, because skipping it loses data twice
# ===========================================================================

class TestATornSubmissionLineIsLoud:
    """Skipping an unparseable line looked conservative and was destructive.

    The log is the run's only state and the ORDER was the line count, so a dropped
    line drops that program from every future replay AND shifts every later id.
    Measured on a five-record log with the middle record truncated:
    ``_read_submissions`` returned orders ``[0, 1, 3, 4]``, and the next
    ``sample_order`` would have been 4, which was already on disk.
    """

    def _torn_log(self, tmp_path) -> Path:
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        lines = [
            json.dumps({"sample_order": i, "valid": True, "score": -1.0 * i,
                        "body": "b" * 40})
            for i in range(5)
        ]
        lines[2] = lines[2][:30]  # an append interrupted partway through
        (run_dir / runs_mod.SUBMISSIONS_FILE).write_text("\n".join(lines) + "\n")
        return run_dir

    def test_reading_a_torn_log_raises_rather_than_skipping(self, tmp_path):
        run_dir = self._torn_log(tmp_path)
        with pytest.raises(runs_mod.TornSubmissionLog) as exc:
            runs_mod._read_submissions(run_dir)
        message = str(exc.value)
        # The message has to be actionable: which file, which line, how much
        # survived. The bytes are still there, so this is repairable by hand.
        assert runs_mod.SUBMISSIONS_FILE in message
        assert "line 3" in message
        assert "Records that parsed before it: 2" in message

    def test_the_next_order_can_no_longer_collide_with_a_used_one(self, tmp_path):
        """The consequence, pinned directly: claiming an order off a damaged log
        would have handed out 4 when 4 was already taken."""
        run_dir = self._torn_log(tmp_path)
        with pytest.raises(runs_mod.TornSubmissionLog):
            runs_mod.append_next_submission(run_dir, {"body": "b"})
        # And nothing was appended on top of the damage, which would have made
        # the repair harder.
        assert len((run_dir / runs_mod.SUBMISSIONS_FILE).read_text().splitlines()) == 5

    def test_every_verb_that_replays_the_log_refuses(self):
        """Through the real CLI, because this is a message a scientist reads."""
        run_dir = _init("torn-cli")
        Path("body.py").write_text(TRUE_BODY)
        assert _cli("submit", "--run", str(run_dir), "--body-file", "body.py",
                    "--island-id", "0", "--version-generated", "0").returncode == 0

        log = run_dir / runs_mod.SUBMISSIONS_FILE
        lines = log.read_text().splitlines()
        lines[-1] = lines[-1][: len(lines[-1]) // 2]
        log.write_text("\n".join(lines) + "\n")

        for verb in ("best", "prompt"):
            result = _cli(verb, "--run", str(run_dir))
            blob = _squash(result.stdout + result.stderr)
            assert result.returncode != 0, blob
            assert "not valid JSON" in blob, blob

    def test_an_intact_log_with_blank_lines_still_reads(self, tmp_path):
        """A trailing newline is not damage, and never was."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / runs_mod.SUBMISSIONS_FILE).write_text(
            '{"sample_order": 0}\n\n{"sample_order": 1}\n\n')
        assert [s["sample_order"] for s in runs_mod._read_submissions(run_dir)] == [0, 1]


# ===========================================================================
# N6. The island id: validated before the fit, at BOTH ends, and recorded
# ===========================================================================

class TestTheIslandIdIsValidatedBeforeAnythingExpensive:
    """Two measured holes, on a run configured for 4 islands.

    ``--island-id 99`` reached the vendored ``register_program`` AFTER the fit had
    finished and raised a bare ``IndexError: list index out of range``. Exit 1, no
    append: the candidate and the model call that produced it were both lost.

    ``--island-id -1`` was ACCEPTED, recorded as ``-1``, and registered on the LAST
    island, because a negative index is a valid list index and the only guard
    tested ``>= num_islands``. Nothing said the candidate had gone somewhere other
    than where the caller asked.
    """

    @pytest.mark.parametrize("island_id", [-1, 4, 99, -100])
    def test_an_out_of_range_id_is_refused(self, island_id):
        run_dir = _init(f"island-bad{abs(island_id)}", "--islands", "4")
        Path("body.py").write_text(TRUE_BODY)

        result = _cli("submit", "--run", str(run_dir), "--body-file", "body.py",
                      "--island-id", str(island_id), "--version-generated", "0")
        blob = _squash(result.stdout + result.stderr)

        assert result.returncode != 0, blob
        assert "--island-id must be between 0 and 3" in blob, blob
        # Refused, so nothing was recorded: only the seed is on disk.
        assert [s["sample_order"] for s in _submissions(run_dir)] == [0]

    @pytest.mark.parametrize("island_id", [0, 3])
    def test_the_whole_valid_range_is_accepted(self, island_id):
        """The other half of "accept the full valid range only": the last island
        is a legal answer, and ``prompt`` really does hand it out."""
        run_dir = _init(f"island-ok{island_id}", "--islands", "4")
        Path("body.py").write_text(TRUE_BODY)
        result = _cli("submit", "--run", str(run_dir), "--body-file", "body.py",
                      "--island-id", str(island_id), "--version-generated", "0")
        assert result.returncode == 0, result.stdout + result.stderr
        assert _submissions(run_dir)[-1]["island_id"] == island_id

    def test_the_check_happens_before_the_fit_runs(self, monkeypatch):
        """The point of the fix, not a side effect of it.

        A fit costs a model call upstream of it and minutes of compute; failing
        after one throws both away. Proved by making the fit itself fatal: if the
        id were still checked downstream, this is what the test would see.
        """
        run_dir = _init("island-order", "--islands", "4")
        Path("body.py").write_text(TRUE_BODY)

        def never(*_args, **_kwargs):
            raise AssertionError("the fit ran before the island id was checked")

        monkeypatch.setattr(cli_mod, "_score_body", never)
        result = runner.invoke(llmsr_app, [
            "submit", "--run", str(run_dir), "--body-file", "body.py",
            "--island-id", "99", "--version-generated", "0",
        ])

        assert result.exit_code != 0
        assert "--island-id must be between 0 and 3" in _text(result)

    def test_a_negative_id_already_on_disk_is_refused_by_the_replay(self):
        """The ids index a list, so one recorded before the guard existed routed
        somewhere nobody chose. The replay now says so instead of using it."""
        run_dir = _init("island-legacy", "--islands", "4")
        meta = json.loads((run_dir / "meta.json").read_text())
        runs_mod._append_submission(run_dir, {
            "sample_order": 1, "body": TRUE_BODY, "valid": True, "score": -1.0,
            "island_id": -1, "version_generated": 0,
        })

        with pytest.raises(Exception) as exc:
            cli_mod._rebuild_buffer(run_dir, meta)
        assert "island -1" in str(exc.value)


class TestThePromptToSubmitBindingIsRecorded:
    """``prompt`` persisted only the prompt TEXT.

    ``island_id`` and ``version_generated`` are the ROUTING: they decide which
    island a candidate evolves on and which ancestors it may not call. They
    existed on stdout alone, so once a terminal scrolled there was nothing on disk
    saying where a prompt had routed, and no way to audit after a run whether a
    batch of four submissions went where its prompt said.
    """

    def test_the_routing_lands_on_disk_and_matches_what_was_printed(self):
        run_dir = _init("prompt-audit", "--islands", "4")
        printed = [
            json.loads(_cli("prompt", "--run", str(run_dir)).stdout.strip()
                       .splitlines()[-1])
            for _ in range(3)
        ]

        recorded = [
            json.loads(line)
            for line in (run_dir / runs_mod.PROMPTS_FILE).read_text().splitlines()
            if line.strip()
        ]
        assert len(recorded) == 3
        for want, got in zip(printed, recorded):
            assert got["island_id"] == want["island_id"]
            assert got["version_generated"] == want["version_generated"]
            assert got["prompt_file"] == want["prompt_file"]
            assert Path(got["prompt_file"]).exists()
            assert got["at"] and got["at_epoch"]
        # Indices are dense and ordered, so the island SEQUENCE of a whole run is
        # reconstructable from this file alone.
        assert [r["prompt_index"] for r in recorded] == [0, 1, 2]

    def test_the_recorded_island_is_one_submit_would_accept(self):
        """A prompt that routed somewhere `submit` refuses would be a trap."""
        run_dir = _init("prompt-inrange", "--islands", "2")
        for _ in range(8):
            got = json.loads(_cli("prompt", "--run", str(run_dir)).stdout.strip()
                             .splitlines()[-1])
            assert 0 <= got["island_id"] < 2, got


# ===========================================================================
# N9 + N8. A run whose seed candidate failed must say so, not crash in numpy
# ===========================================================================

class TestAnInvalidSeedIsAnnouncedAtInit:
    """``init`` exited 0 with ``seed_valid: false`` among fifteen other keys.

    The seed is the one candidate that registers on EVERY island (the vendored
    ``register_program`` loops them all when ``island_id`` is None), so without it
    the buffer has empty islands and the run is dead on arrival. An act hands the
    fresh run straight to a generator sub-agent, so the first thing that agent met
    was a numpy traceback from the next ``prompt``.
    """

    def test_init_says_so_on_stderr_and_in_its_payload(self):
        _write_spec(seed_body=BROKEN_BODY.strip().removeprefix("return "))
        _write_csv()
        result = _cli("init", "--run-id", "seed-bad", "--spec", "spec.txt",
                      "--data", "train.csv", "--metric", "mse")

        # Still exit 0: the run dir is legitimately created and repairable.
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert payload["seed_valid"] is False
        assert "seed_warning" in payload
        # The human channel and the machine channel say the same thing, and both
        # name the consequence rather than only the symptom.
        assert "prompt" in payload["seed_warning"]
        assert "warning:" in _squash(result.stderr)
        assert "seed candidate did not fit" in _squash(result.stderr)

    def test_a_valid_seed_gets_no_warning_at_all(self):
        """The signal has to stay rare to stay readable."""
        _write_spec()
        _write_csv()
        result = _cli("init", "--run-id", "seed-ok", "--spec", "spec.txt",
                      "--data", "train.csv", "--metric", "mse")
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert payload["seed_valid"] is True
        assert "seed_warning" not in payload
        assert "warning:" not in result.stderr


class TestPromptRefusesAnUnseededBufferInsteadOfCrashing:
    """``vendor/buffer.py::get_prompt`` draws an island uniformly at random.

    An island with no clusters hands ``_softmax`` an empty array. Measured on a
    run whose seed failed: ``ValueError: zero-size array to reduction operation
    maximum which has no identity``, four frames inside vendored code, naming
    nothing about the actual problem. With one valid submission on island 0 of 4
    the draw fails three times in four, so it also looks intermittent.
    """

    def test_the_numpy_error_is_replaced_by_an_explanation(self):
        run_dir = _init("unseeded", "--islands", "4",
                        seed_body=BROKEN_BODY.strip().removeprefix("return "))
        result = _cli("prompt", "--run", str(run_dir))
        blob = _squash(result.stdout + result.stderr)

        assert result.returncode != 0, blob
        assert "zero-size array" not in blob, blob
        assert "cannot produce a prompt" in blob, blob
        # It names WHY (the seed's own error) and WHAT TO DO.
        assert "seed candidate failed to fit" in blob, blob
        assert "start a new run" in blob, blob

    def test_it_still_refuses_when_only_some_islands_are_populated(self):
        """The partially-seeded case is the intermittent one, so it is the one a
        guard has to cover: island 0 has a program, islands 1 to 3 do not."""
        run_dir = _init("half-seeded", "--islands", "4",
                        seed_body=BROKEN_BODY.strip().removeprefix("return "))
        Path("body.py").write_text(TRUE_BODY)
        assert _cli("submit", "--run", str(run_dir), "--body-file", "body.py",
                    "--island-id", "0", "--version-generated", "0").returncode == 0

        result = _cli("prompt", "--run", str(run_dir))
        blob = _squash(result.stdout + result.stderr)
        assert result.returncode != 0, blob
        assert "islands [1, 2, 3] hold no program" in blob, blob

    def test_a_healthy_run_is_untouched(self):
        run_dir = _init("seeded", "--islands", "4")
        assert _cli("prompt", "--run", str(run_dir)).returncode == 0

    def test_a_run_repaired_by_submitting_to_every_island_works_again(self):
        """The guard must not be a dead end: the recovery path it names has to
        actually recover, or refusing is just a nicer way to lose the run."""
        run_dir = _init("repaired", "--islands", "2",
                        seed_body=BROKEN_BODY.strip().removeprefix("return "))
        Path("body.py").write_text(TRUE_BODY)
        for island in (0, 1):
            assert _cli("submit", "--run", str(run_dir), "--body-file", "body.py",
                        "--island-id", str(island),
                        "--version-generated", "0").returncode == 0

        result = _cli("prompt", "--run", str(run_dir))
        assert result.returncode == 0, result.stdout + result.stderr


class TestTheFounderDrawNeverReachesANoneProgram:
    """``reset_islands`` registers ``_best_program_per_island[founder]`` unchecked.

    Measured: 4 islands, ONE registered program, ``np.random.seed(1)``, and the
    draw picked a survivor that had none: ``AttributeError: 'NoneType' object has
    no attribute 'keys'`` from inside vendored code. Safe at seed 0 purely by luck
    of the draw, which is the worst kind of safe.

    ``vendor/`` is upstream's and is not forked, so the guard is on Wheeler's side
    of the call.
    """

    def _one_program_buffer(self, run_dir: Path):
        from wheeler.integrations.llmsr.vendor import buffer as buffer_mod
        from wheeler.integrations.llmsr.vendor import code_manipulation, evaluator

        meta = json.loads((run_dir / "meta.json").read_text())
        template = code_manipulation.text_to_program(
            Path(meta["spec_path"]).read_text())
        fte = meta["function_to_evolve"]
        db = buffer_mod.ExperienceBuffer(
            cli_mod._buffer_config(meta), template, fte)
        fn, _program = evaluator._sample_to_program(TRUE_BODY, 0, template, fte)
        db.register_program(fn, 0, {"data": -1.0})
        return db

    def test_the_vendored_draw_really_does_crash_in_that_state(self):
        """The control. A guard whose failure mode is not reproducible is a guard
        nobody can tell is load-bearing."""
        run_dir = _init("founder-control", "--islands", "4")
        db = self._one_program_buffer(run_dir)

        state = np.random.get_state()
        np.random.seed(1)
        try:
            with pytest.raises(AttributeError, match="NoneType"):
                db.reset_islands()
        finally:
            np.random.set_state(state)

    def test_wheeler_skips_that_reset_and_says_why(self, capsys):
        run_dir = _init("founder-guard", "--islands", "4")
        db = self._one_program_buffer(run_dir)

        state = np.random.get_state()
        np.random.seed(1)
        try:
            cli_mod._reset_islands_safely(db, run_dir)  # must not raise
        finally:
            np.random.set_state(state)

        warning = _squash(capsys.readouterr().err)
        assert "skipping an island reset" in warning
        assert "islands [1, 2, 3] hold no program" in warning

    def test_a_full_buffer_is_reset_exactly_as_before(self):
        """The guard must not change a healthy run: a seeded buffer resets."""
        run_dir = _init("founder-healthy", "--islands", "4")
        meta = json.loads((run_dir / "meta.json").read_text())
        _template, db, _fte = cli_mod._rebuild_buffer(run_dir, meta)
        assert all(p is not None for p in db._best_program_per_island)

        before = [len(isl._clusters) for isl in db._islands]
        cli_mod._reset_islands_safely(db, run_dir)
        # A reset really happened: every island still holds a program, which is
        # what the founder registration guarantees.
        assert all(p is not None for p in db._best_program_per_island)
        assert len(before) == len(db._islands)

    def test_a_run_in_that_state_survives_a_due_reset_end_to_end(self):
        """Through the real CLI, at the seed the crash was measured at."""
        run_dir = _init("founder-cli", "--islands", "4", "--island-seed", "1",
                        "--reset-every", "1",
                        seed_body=BROKEN_BODY.strip().removeprefix("return "))
        Path("body.py").write_text(TRUE_BODY)
        for _ in range(2):
            result = _cli("submit", "--run", str(run_dir), "--body-file",
                          "body.py", "--island-id", "0", "--version-generated", "0")
            assert result.returncode == 0, result.stdout + result.stderr
            assert "NoneType" not in result.stderr
        assert "skipping an island reset" in _squash(result.stderr)

        # And a read-only ping still works, which is what it is for.
        assert _cli("status", "--run", str(run_dir)).returncode == 0


# ===========================================================================
# N3. A --cluster-tolerance the replay ignores is refused at init
# ===========================================================================

class TestClusterToleranceIsValidatedWhereItIsBound:
    """``0.5`` and ``1.0`` were both written to ``meta.json`` and both ignored.

    The replay quantizes only above 1.0, because the tolerance is a FACTOR and a
    factor of 1 is a bucket of zero width. Measured: no error, no warning, and a
    run whose clustering was raw while its own metadata said otherwise. Both
    values are plausible misreadings (``0.5`` as a fraction, ``1.0`` as "off").

    This repo already validates ``--metric``, ``--loader`` and ``--optimizer`` AT
    init for the same reason: a bad choice must fail one command instead of
    invalidating every candidate in the search.
    """

    @pytest.mark.parametrize("tolerance", ["0.5", "1.0", "0", "-2"])
    def test_a_no_op_tolerance_fails_the_one_command(self, tolerance):
        _write_spec()
        _write_csv()
        run_id = f"tol{tolerance.replace('.', '').replace('-', 'neg')}"
        result = _cli("init", "--run-id", run_id, "--spec", "spec.txt",
                      "--data", "train.csv", "--metric", "mse",
                      "--cluster-tolerance", tolerance)
        blob = _squash(result.stdout + result.stderr)

        assert result.returncode != 0, blob
        assert "must be greater than 1.0" in blob, blob
        # And no run dir was left behind, matching every other init-time check.
        assert not (RUNS_ROOT / run_id / "meta.json").exists()

    def test_a_working_tolerance_is_still_accepted_silently(self):
        run_dir = _init("tol-ok", "--cluster-tolerance", "1.8")
        meta = json.loads((run_dir / "meta.json").read_text())
        assert meta["cluster_tolerance"] == pytest.approx(1.8)

    def test_the_default_is_still_raw_and_still_silent(self):
        run_dir = _init("tol-default")
        meta = json.loads((run_dir / "meta.json").read_text())
        assert meta["cluster_tolerance"] is None

    def test_an_absurdly_coarse_tolerance_warns_but_is_allowed(self):
        """Refusing would be Wheeler choosing the science. Measured on a real
        26-submission run, half a decade already put 11 of 26 in one cluster."""
        _write_spec()
        _write_csv()
        result = _cli("init", "--run-id", "tol-coarse", "--spec", "spec.txt",
                      "--data", "train.csv", "--metric", "mse",
                      "--cluster-tolerance", "1e9")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "buckets more than a decade" in _squash(result.stderr)
        meta = json.loads((RUNS_ROOT / "tol-coarse" / "meta.json").read_text())
        assert meta["cluster_tolerance"] == pytest.approx(1e9)


# ===========================================================================
# N4. The replay and the live register key the buffer the same way
# ===========================================================================

class TestTheTwoRegistrationPathsAgree:
    """The replay quantized and ``submit``'s own ``register_program`` did not.

    Harmless only because ``submit`` discards its buffer immediately, which is a
    property of that caller and not of the seam: the place a reader inspects
    disagreed with the path that set the state. The vendored buffer derives BOTH
    the cluster signature and the cluster's selection score from this one dict, so
    the disagreement is not cosmetic.
    """

    def test_submit_registers_the_same_scores_the_replay_would(self, monkeypatch):
        from wheeler.integrations.llmsr.vendor import buffer as buffer_mod

        run_dir = _init("quantize-agree", "--islands", "2",
                        "--cluster-tolerance", "1.8")
        Path("body.py").write_text(TRUE_BODY)
        meta = json.loads((run_dir / "meta.json").read_text())

        seen: list[dict] = []
        original = buffer_mod.ExperienceBuffer.register_program

        def spy(self, program, island_id, scores_per_test, **kwargs):
            seen.append(dict(scores_per_test))
            return original(self, program, island_id, scores_per_test, **kwargs)

        monkeypatch.setattr(buffer_mod.ExperienceBuffer, "register_program", spy)
        _out(runner.invoke(llmsr_app, [
            "submit", "--run", str(run_dir), "--body-file", "body.py",
            "--island-id", "0", "--version-generated", "0",
        ]))
        live = seen[-1]

        # Now what a replay of that same log hands the buffer for the same record.
        seen.clear()
        cli_mod._rebuild_buffer(run_dir, meta)
        replayed = seen[-1]

        assert live == replayed, (
            f"submit registered {live} and the replay of the same submission "
            f"registered {replayed}"
        )

    def test_the_seam_quantizes_exactly_when_the_replay_does(self):
        raw = {"a": -0.00249, "b": -0.00251, "c": -0.402}
        assert cli_mod._scores_for_buffer({}, raw) == raw
        assert cli_mod._scores_for_buffer({"cluster_tolerance": 1.0}, raw) == raw
        assert cli_mod._scores_for_buffer({"cluster_tolerance": 1.8}, raw) == (
            cli_mod._quantize_scores(raw, 1.8))


# ===========================================================================
# N10. --seed is the fit's seed, and only the fit's
# ===========================================================================

class TestTheFitSeedAndTheIslandSeedAreSeparate:
    """``--seed`` is documented as the seed for the optimizer's random restarts.

    The replay also used it to seed ``reset_islands``'s founder draw, so varying
    it to probe whether a fit was robust to its starting points ALSO changed which
    islands were reset and which program reseeded them. Two experiments, one flag,
    and no surface saying so.
    """

    def test_both_seeds_are_recorded_on_the_run(self):
        run_dir = _init("seeds", "--seed", "7", "--island-seed", "3")
        meta = json.loads((run_dir / "meta.json").read_text())
        assert meta["seed"] == 7
        assert meta["island_seed"] == 3

    def test_changing_the_fit_seed_leaves_the_island_model_alone(self):
        run_dir = _init("seed-fit", "--seed", "9")
        meta = json.loads((run_dir / "meta.json").read_text())
        assert cli_mod._island_seed(meta) == cli_mod.DEFAULT_ISLAND_SEED
        assert cli_mod._island_seed({**meta, "seed": 12345}) == (
            cli_mod.DEFAULT_ISLAND_SEED)

    def test_the_island_seed_is_what_moves_the_island_model(self):
        run_dir = _init("seed-island", "--island-seed", "4")
        meta = json.loads((run_dir / "meta.json").read_text())
        assert cli_mod._island_seed(meta) == 4

    def test_a_run_dir_written_before_the_split_replays_under_its_old_seed(self):
        """Backward compatibility is load-bearing: the buffer is rebuilt from the
        log on every verb, so a changed founder draw would silently reshape the
        search state of a run already on disk, without raising anything."""
        assert cli_mod._island_seed({"seed": 5}) == 5
        assert cli_mod._island_seed({"seed": None}) == 0
        assert cli_mod._island_seed({}) == 0
        # Present-but-null is a run created after the split, so the fit seed must
        # NOT leak back in.
        assert cli_mod._island_seed({"seed": 5, "island_seed": None}) == 0

    def test_the_flag_is_on_the_init_command(self):
        from typer.main import get_command

        init_cmd = get_command(llmsr_app).commands["init"]  # type: ignore[attr-defined]
        names = {opt for param in init_cmd.params for opt in param.opts}
        assert "--island-seed" in names
        assert "--seed" in names
