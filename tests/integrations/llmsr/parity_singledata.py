"""The single-dataset parity gate: reopening the dataset seam must not move a bit.

Slice S2 turned one bound dataset into a repeatable, nameable ``--data``, and the
score keys the vendored buffer clusters on became a SCHEME rather than a single
hardcoded ``fit.UNGROUPED``. The claim that buys that change its licence is
narrow and checkable: **an unnamed single ``--data`` is what it always was.**
Same score keys, same constants, same ``best.json``, byte for byte, both
ungrouped and under ``--group-by``.

That property is not cosmetic. The vendored buffer clusters candidates on the
score SIGNATURE (``buffer._get_signature`` sorts the keys and tuples the values)
and ranks islands on ``_reduce_score`` (a mean taken in insertion order, so even
the key ORDER is load bearing in floating point). A changed key set would
silently invalidate every existing run's buffer state, and it would do it without
raising anything.

So this walks the whole CLI, not just the fit: ``init`` (which seeds the buffer),
``prompt``, ``submit``, ``best``. It records ``meta.json``, every
``submissions.jsonl`` record, and ``best.json``, with floats as hex literals and
absolute paths normalized. Only genuinely volatile fields are dropped (wall-clock
timestamps and durations); everything a rerun can reproduce is compared exactly.

``tests/integrations/llmsr/test_multidata.py`` runs ``check_all()``, so the gate
fires on every test run.

Regenerating the golden file, from the repo root (``git archive`` reads the
commit, so it touches no working tree and no sibling worktree)::

    rm -rf /tmp/wheeler-main && mkdir -p /tmp/wheeler-main
    git archive main | tar -x -C /tmp/wheeler-main
    cp tests/integrations/llmsr/parity_singledata.py \\
       /tmp/wheeler-main/tests/integrations/llmsr/
    cd /tmp/wheeler-main && PYTHONPATH=/tmp/wheeler-main python \\
        tests/integrations/llmsr/parity_singledata.py capture > /tmp/golden.json
    cp /tmp/golden.json <repo>/tests/integrations/llmsr/parity_singledata_golden.json

The script is copied IN rather than read from the archive because it postdates
the commit it captures from. It leans only on the four verbs and their options,
which predate this slice, so it runs unchanged on either side.

Then ``python tests/integrations/llmsr/parity_singledata.py check`` here.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from typer.testing import CliRunner

from wheeler.integrations.llmsr.cli import llmsr_app

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
GOLDEN = HERE / "parity_singledata_golden.json"

SPEC = FIX / "spec_bactgrow.txt"
DATA = FIX / "train_small.csv"

# A candidate the search would plausibly propose: Monod growth minus decay. Fixed
# text, because the body is part of what is compared.
CANDIDATE = "    return params[0]*b*s/(params[1]+s) - params[2]*b + params[3]*temp\n"

# Fields no rerun can reproduce: wall clock and elapsed time. Everything else is
# compared, including every fitted constant and the full generated program text.
_VOLATILE = frozenset({
    "created", "created_epoch", "at_epoch", "fit_seconds", "timing", "updated",
})


def _grouped_csv(path: Path) -> None:
    """Write a deterministic two-group table: one form, two constant sets.

    Written by hand rather than through ``np.savetxt`` because the group column
    holds TEXT labels (``c01``), which is the case ``data.py`` reads separately
    so a label is not silently NaN.
    """
    rng = np.random.default_rng(7)
    rows = ["cell,x,y"]
    for cell, (a, b) in {"c01": (2.0, -0.5), "c02": (-1.25, 3.0)}.items():
        # `float()` before `repr`: numpy 2 reprs a scalar as `np.float64(1.0)`,
        # which is not a CSV cell. `repr` of a Python float round-trips exactly.
        for xi in (float(v) for v in rng.uniform(-2.0, 2.0, 24)):
            rows.append(f"{cell},{xi!r},{float(a * xi + b * xi**2)!r}")
    path.write_text("\n".join(rows) + "\n")


_GROUP_SPEC = '''"""two-group toy"""
import numpy as np

MAX_NPARAMS = 4


@evaluate.run
def evaluate(data: dict) -> float:
    return 0.0


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''

_GROUP_CANDIDATE = "    return params[0]*x + params[1]*x**2\n"


# ------------------------------------------------------------------ the payload

def _hexify(value, subs: dict[str, str]):
    """Floats as hex literals, absolute paths as placeholders, recursively.

    Hex because a decimal repr can round two different doubles to the same text,
    and this gate is about bits. Paths because the run dir is a scratch directory
    and the fixtures live wherever the checkout is.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value.hex()
    if isinstance(value, str):
        for raw, placeholder in subs.items():
            value = value.replace(raw, placeholder)
        return value
    if isinstance(value, dict):
        return {
            _hexify(k, subs): _hexify(v, subs)
            for k, v in value.items()
            if k not in _VOLATILE
        }
    if isinstance(value, list):
        return [_hexify(v, subs) for v in value]
    return value


def _record(run_dir: Path, subs: dict[str, str]) -> dict:
    """Everything the run wrote that a rerun must reproduce exactly."""
    submissions = [
        json.loads(line)
        for line in (run_dir / "submissions.jsonl").read_text().splitlines()
        if line.strip()
    ]
    return _hexify({
        "meta": json.loads((run_dir / "meta.json").read_text()),
        "submissions": submissions,
        "best": json.loads((run_dir / "best.json").read_text()),
    }, subs)


def _invoke(args: list[str]) -> dict:
    runner = CliRunner()
    result = runner.invoke(llmsr_app, args)
    if result.exit_code != 0:
        raise SystemExit(f"{args!r} failed:\n{result.output}\n{result.exception!r}")
    return json.loads(result.output.strip().splitlines()[-1])


def _walk(run_id: str, spec: Path, data: Path, body: str, extra: list[str]) -> dict:
    """init -> prompt -> submit -> best, then record everything it wrote.

    ``prompt`` is walked for its side effects but its island choice is NOT used:
    the vendored buffer picks an island at random, so submitting into it would
    make the recorded run non-deterministic for a reason that has nothing to do
    with the dataset seam this gate is about. Submitting into a fixed island
    exercises the same registration path with a reproducible result.
    """
    _invoke([
        "init", "--spec", str(spec), "--data", str(data),
        "--metric", "mse", "--run-id", run_id, *extra,
    ])
    run_dir = Path(".wheeler/llmsr/runs") / run_id
    _invoke(["prompt", "--run", str(run_dir)])
    body_file = Path(f"{run_id}_body.py")
    body_file.write_text(body)
    _invoke([
        "submit", "--run", str(run_dir), "--body-file", str(body_file),
        "--island-id", "0", "--version-generated", "0",
    ])
    _invoke(["best", "--run", str(run_dir)])
    return _record(run_dir, {
        str(spec.resolve()): f"<SPEC:{spec.name}>",
        str(data.resolve()): f"<DATA:{data.name}>",
    })


def capture() -> dict:
    """Walk every case in a scratch cwd and emit the normalized record."""
    out: dict[str, dict] = {}
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as scratch:
        try:
            os.chdir(scratch)
            # The historic shape: one unnamed --data, no grouping. Its score key
            # must stay `data` verbatim.
            out["ungrouped"] = _walk("parity-ungrouped", SPEC, DATA, CANDIDATE, [])

            # The grouped shape: one unnamed --data plus --group-by. Its score
            # keys must stay the bare group labels, NOT qualified by a dataset.
            spec_path = Path(scratch) / "group_spec.txt"
            spec_path.write_text(_GROUP_SPEC)
            data_path = Path(scratch) / "two_cells.csv"
            _grouped_csv(data_path)
            out["grouped"] = _walk(
                "parity-grouped", spec_path, data_path, _GROUP_CANDIDATE,
                ["--group-by", "cell"],
            )
        finally:
            os.chdir(cwd)
    return out


# ------------------------------------------------------------------- the checks

def _diff(want, got, path: str = "") -> list[str]:
    """Every leaf that differs, named by its path. Empty means identical."""
    if type(want) is not type(got):
        return [f"{path or '<root>'}: type {type(want).__name__} -> {type(got).__name__}"]
    if isinstance(want, dict):
        out = []
        for key in sorted(set(want) | set(got)):
            if key not in want:
                out.append(f"{path}.{key}: ADDED ({got[key]!r})")
            elif key not in got:
                out.append(f"{path}.{key}: REMOVED (was {want[key]!r})")
            else:
                out.extend(_diff(want[key], got[key], f"{path}.{key}"))
        return out
    if isinstance(want, list):
        if len(want) != len(got):
            return [f"{path}: length {len(want)} -> {len(got)}"]
        out = []
        for i, (w, g) in enumerate(zip(want, got)):
            out.extend(_diff(w, g, f"{path}[{i}]"))
        return out
    return [] if want == got else [f"{path}: {want!r} -> {got!r}"]


def _compare(want: dict, got: dict) -> list[str]:
    """Diff one case: ``meta`` may GAIN keys, the result may not change at all.

    ``meta.json`` is the run's own bookkeeping and every slice adds to it (the
    score-key scheme has to be recorded there, by construction). So its golden
    keys are compared exactly and additions are tolerated: a new key is fine, a
    changed or vanished one is not.

    ``submissions.jsonl`` and ``best.json`` are the RESULT, and they are compared
    with no tolerance at all. An added field there is a failure, because the claim
    this gate defends is that an unnamed single ``--data`` produces the file it
    always produced.
    """
    meta_want, meta_got = want["meta"], got["meta"]
    failures = _diff(
        meta_want, {k: v for k, v in meta_got.items() if k in meta_want}, ".meta"
    )
    for part in ("submissions", "best"):
        failures.extend(_diff(want[part], got[part], f".{part}"))
    return failures


def check_all() -> list[str]:
    """Every parity failure, as human-readable lines. Empty means identical."""
    golden = json.loads(GOLDEN.read_text())
    got = capture()
    failures: list[str] = []
    for name in sorted(set(golden) | set(got)):
        if name not in golden:
            failures.append(f"{name}: no golden record (regenerate the golden file)")
        elif name not in got:
            failures.append(f"{name}: case disappeared from the script")
        else:
            failures.extend(f"{name}{line}" for line in _compare(golden[name], got[name]))
    return failures


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "check"
    if mode == "capture":
        print(json.dumps(capture(), indent=2, sort_keys=True))
        return 0
    if mode != "check":
        print(f"usage: {argv[0]} capture|check", file=sys.stderr)
        return 2
    failures = check_all()
    for line in failures:
        print(f"FAIL {line}")
    if failures:
        return 1
    print("OK  an unnamed single --data is byte-for-byte what it was")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
