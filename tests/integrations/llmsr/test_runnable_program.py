"""The written .py must actually RUN, including for a grouped run (issue #107).

Wheeler advertises the discovered program as a durable, re-runnable artifact. For
a grouped run it was neither: the footer emitted the flat ``params``, which
``fit.py`` leaves EMPTY whenever there is more than one group, so the file called
the equation with an empty array. These tests execute the generated file as a
subprocess rather than inspecting its text, because "it looks right" is exactly
what the defect passed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# The same law y = a*x + b with three cells and three different (a, b): the form
# is shared, the constants are not, which is the whole point of grouping.
CELLS = {"c01": (2.5, -1.0), "c02": (-4.0, 8.0), "c03": (0.5, 3.0)}
N_PER_CELL = 25

_WORKTREE = str(Path(__file__).resolve().parents[3])
_FLOAT = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _env() -> dict:
    return {**os.environ, "PYTHONPATH": _WORKTREE}


def _write_inputs(tmp_path: Path, group_column: bool) -> tuple[Path, Path, list[float]]:
    """A noiseless linear dataset (+ spec). Returns (spec, csv, y in file order)."""
    import numpy as np

    rng = np.random.default_rng(3)
    header = "cell_id,x1,y" if group_column else "x1,y"
    lines, ys = [header], []
    for name, (a, b) in CELLS.items():
        for x in rng.uniform(-3.0, 3.0, N_PER_CELL):
            y = a * float(x) + b
            ys.append(y)
            row = f"{float(x):.17g},{y:.17g}"
            lines.append(f"{name},{row}" if group_column else row)
    csv = tmp_path / "train.csv"
    csv.write_text("\n".join(lines) + "\n")

    spec = tmp_path / "spec.txt"
    spec.write_text(
        "import numpy as np\n\n"
        "MAX_NPARAMS = 4\n\n"
        "@evaluate.run\n"
        "def evaluate(data):\n"
        "    return 0.0\n\n"
        "@equation.evolve\n"
        "def equation(x1, params):\n"
        "    return params[0] * x1 + params[1]\n"
    )
    return spec, csv, ys


def _cli(tmp_path: Path, *argv: str) -> dict:
    out = subprocess.run(
        [sys.executable, "-m", "wheeler.tools.cli", "llmsr", *argv],
        cwd=tmp_path, capture_output=True, text=True, env=_env(),
    )
    assert out.returncode == 0, out.stderr or out.stdout
    return json.loads(out.stdout.strip().splitlines()[-1])


def _run_discovery(tmp_path: Path, program: str) -> str:
    """Execute the generated program the way a scientist would. Returns stdout."""
    script = tmp_path / "discovery.py"
    script.write_text(program)
    out = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path, capture_output=True, text=True, env=_env(),
    )
    assert out.returncode == 0, (
        f"the discovered program does not run:\n{out.stderr}\n---\n{program}"
    )
    return out.stdout


class TestGroupedRunnable:
    def test_written_program_runs_and_predicts_per_group(self, tmp_path):
        spec, csv, ys = _write_inputs(tmp_path, group_column=True)
        _cli(
            tmp_path, "init", "--spec", str(spec), "--data", str(csv),
            "--metric", "mse", "--group-by", "cell_id", "--run-id", "g1",
        )
        _cli(tmp_path, "best", "--run", "g1")
        best = json.loads((tmp_path / ".wheeler/llmsr/runs/g1/best.json").read_text())

        # the grouped answer IS the table: the flat `params` is empty by design
        assert best["params"] == []
        assert sorted(best["params_per_group"]) == sorted(CELLS)
        for name, (a, b) in CELLS.items():
            assert best["params_per_group"][name][0] == pytest.approx(a, abs=1e-6)
            assert best["params_per_group"][name][1] == pytest.approx(b, abs=1e-6)

        program = best["program"]
        assert "FITTED_PARAMS_PER_GROUP" in program
        assert "GROUP_BY = 'cell_id'" in program
        # the empty flat list must not be what the file applies
        assert "FITTED_PARAMS = []" not in program

        stdout = _run_discovery(tmp_path, program)

        # one line per group, each covering that group's rows only
        for name in CELLS:
            assert f"group {name} n_rows {N_PER_CELL}" in stdout
        assert stdout.count("prediction[:5]") == len(CELLS)

        # and the numbers are the RIGHT ones: noiseless data, true form, so the
        # first cell's predictions reproduce its recorded y
        first = [
            line for line in stdout.splitlines() if line.startswith("group c01 ")
        ][0]
        printed = [float(m) for m in _FLOAT.findall(first.split("prediction[:5]")[1])]
        assert printed == pytest.approx(ys[:5], rel=1e-3)

    def test_ungrouped_footer_is_unchanged(self, tmp_path):
        spec, csv, ys = _write_inputs(tmp_path, group_column=False)
        _cli(
            tmp_path, "init", "--spec", str(spec), "--data", str(csv),
            "--metric", "mse", "--run-id", "u1",
        )
        _cli(tmp_path, "best", "--run", "u1")
        best = json.loads((tmp_path / ".wheeler/llmsr/runs/u1/best.json").read_text())

        program = best["program"]
        assert "FITTED_PARAMS = [" in program
        assert "FITTED_PARAMS_PER_GROUP" not in program
        assert "GROUP_BY" not in program
        assert "group_by" not in best  # absent, not empty, on an ungrouped run

        stdout = _run_discovery(tmp_path, program)
        assert "prediction[:5]" in stdout
        assert "group " not in stdout


class TestRunnableProgramUnit:
    """The footer builder itself, without a search run."""

    def _program(self) -> str:
        return (
            "import numpy as np\n\n"
            "def equation(x1, params):\n"
            "    return params[0] * x1 + params[1]\n"
        )

    def test_grouped_branch_emits_the_table(self):
        from wheeler.integrations.llmsr.selection import _runnable_program

        out = _runnable_program(
            self._program(), [], "mse", 0.5, "/tmp/train.csv", "equation",
            group_by="cell_id",
            params_per_group={"c01": [1.0, 2.0], "c02": [3.0, 4.0]},
            value_per_group={"c01": 0.4, "c02": 0.6},
        )
        assert "FITTED_PARAMS_PER_GROUP = {'c01': [1.0, 2.0], 'c02': [3.0, 4.0]}" in out
        assert "'per_group': {'c01': 0.4, 'c02': 0.6}" in out
        assert "FITTED_PARAMS =" not in out
        # the group column identifies the row, it is never an input column
        assert "_keep = [_i for _i in range(_d.shape[1] - 1) if _i != _gi]" in out

    def test_group_by_without_a_table_falls_back_to_the_flat_footer(self):
        """Defensive: a group_by with no per-group params is not a grouped answer,
        so it must not emit a table it does not have."""
        from wheeler.integrations.llmsr.selection import _runnable_program

        out = _runnable_program(
            self._program(), [1.0, 2.0], "mse", 0.5, "/tmp/train.csv", "equation",
            group_by="cell_id", params_per_group={},
        )
        assert "FITTED_PARAMS = [1.0, 2.0]" in out
        assert "FITTED_PARAMS_PER_GROUP" not in out
