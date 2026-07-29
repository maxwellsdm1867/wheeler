"""Per-group refit: one FORM, one theta per group (issue #107, slice 1).

The scientific claim under test: when the same law governs several individuals
with DIFFERENT constants, a single pooled fit charges the FORM for variation that
belongs to the PARAMETERS, and rejects a correct law. Refitting per group does
not.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr import metrics as metrics_mod

LINEAR = (
    "import numpy as np\n"
    "def equation(x1, params):\n"
    "    return params[0] * x1 + params[1]\n"
)

# The same law y = a*x + b, three cells, three different (a, b).
CELLS = {"c01": (2.5, -1.0), "c02": (-4.0, 8.0), "c03": (0.5, 3.0)}


def _dataset(n_per_cell: int = 40):
    rng = np.random.default_rng(3)
    xs, ys, labels = [], [], []
    for name, (a, b) in CELLS.items():
        x = rng.uniform(-3.0, 3.0, n_per_cell)
        xs.append(x)
        ys.append(a * x + b)
        labels += [name] * n_per_cell
    return np.concatenate(xs).reshape(-1, 1), np.concatenate(ys), labels


def _groups(X, y, labels):
    out = []
    for name in sorted(CELLS):
        mask = np.array([label == name for label in labels])
        out.append((name, X[mask], y[mask]))
    return out


class TestPerGroupRefit:
    def test_pooled_fit_rejects_the_correct_form(self):
        """The baseline that motivates the feature: one theta cannot serve three cells."""
        X, y, _labels = _dataset()
        pooled = fit_mod.evaluate_body(LINEAR, "equation", X, y, metrics_mod.MSE)
        assert pooled.valid
        # The form is EXACTLY right, yet pooling makes it look badly wrong.
        assert pooled.value > 1.0

    def test_per_group_refit_recovers_every_cell(self):
        X, y, labels = _dataset()
        result = fit_mod.evaluate_body_grouped(
            LINEAR, "equation", _groups(X, y, labels), metrics_mod.MSE
        )
        assert result.valid
        assert result.value < 1e-12  # mean over groups, versus >1.0 pooled

        # Each cell recovered ITS OWN constants, not a compromise.
        for name, (a, b) in CELLS.items():
            got = result.params_per_group[name]
            assert got[0] == pytest.approx(a, abs=1e-6)
            assert got[1] == pytest.approx(b, abs=1e-6)

    def test_score_vector_is_keyed_by_group(self):
        X, y, labels = _dataset()
        result = fit_mod.evaluate_body_grouped(
            LINEAR, "equation", _groups(X, y, labels), metrics_mod.MSE
        )
        assert sorted(result.per_group) == ["c01", "c02", "c03"]
        assert sorted(result.per_group_value) == ["c01", "c02", "c03"]
        # The scalar is the mean over the vector, which is what the vendored
        # buffer's own _reduce_score computes.
        assert result.score == pytest.approx(
            sum(result.per_group.values()) / len(result.per_group)
        )

    def test_group_order_is_deterministic_so_signatures_compare(self):
        """The buffer keys clusters on the score signature; order must be stable."""
        X, y, labels = _dataset()
        shuffled = list(reversed(_groups(X, y, labels)))
        a = fit_mod.evaluate_body_grouped(
            LINEAR, "equation", _groups(X, y, labels), metrics_mod.MSE
        )
        b = fit_mod.evaluate_body_grouped(LINEAR, "equation", shuffled, metrics_mod.MSE)
        assert sorted(a.per_group.items()) == sorted(b.per_group.items())


class TestStrictValidity:
    def test_one_failing_group_invalidates_and_names_it(self):
        """Strict by design: the signature is only comparable over the same groups."""
        X, y, labels = _dataset()
        groups = _groups(X, y, labels)
        # Give c02 a target that no real-valued a*x+b can reach finitely.
        label, gX, _gy = groups[1]
        groups[1] = (label, gX, np.full(gX.shape[0], np.inf))
        result = fit_mod.evaluate_body_grouped(
            LINEAR, "equation", groups, metrics_mod.MSE
        )
        assert not result.valid
        assert "c02" in result.error

    def test_ungrouped_failure_message_is_unprefixed(self):
        """An ungrouped run has no group to blame, so the old message is preserved."""
        X, y, _labels = _dataset()
        bad = (
            "import numpy as np\n"
            "def equation(x1, params):\n"
            "    return np.log(x1) * params[0]\n"
        )
        result = fit_mod.evaluate_body(bad, "equation", X, y, metrics_mod.MSE)
        assert not result.valid
        assert "group" not in result.error


class TestUngroupedIsUnchanged:
    def test_single_group_publishes_flat_params(self):
        """Every existing caller reads .params; one group means one theta."""
        X, y, _labels = _dataset()
        result = fit_mod.evaluate_body(LINEAR, "equation", X, y, metrics_mod.MSE)
        assert result.valid
        assert result.params  # not empty
        assert result.params_per_group[fit_mod.UNGROUPED] == result.params
        assert result.value == result.per_group_value[fit_mod.UNGROUPED]


class TestGroupedCli:
    """The CLI path: --group-by threads through init and lands in submissions."""

    def _write_csv(self, path: Path) -> None:
        X, y, labels = _dataset(n_per_cell=25)
        lines = ["cell_id,x1,y"]
        for label, xi, yi in zip(labels, X[:, 0], y):
            # float(), not repr(): numpy 2.x reprs a scalar as "np.float64(1.5)",
            # which is not a parseable CSV cell.
            lines.append(f"{label},{float(xi):.17g},{float(yi):.17g}")
        path.write_text("\n".join(lines) + "\n")

    def _spec(self, path: Path) -> None:
        path.write_text(
            "import numpy as np\n\n"
            "MAX_NPARAMS = 4\n\n"
            "@evaluate.run\n"
            "def evaluate(data):\n"
            "    return 0.0\n\n"
            "@equation.evolve\n"
            "def equation(x1, params):\n"
            "    return params[0] * x1 + params[1]\n"
        )

    def test_group_by_produces_a_per_group_vector(self, tmp_path):
        self._write_csv(tmp_path / "train.csv")
        self._spec(tmp_path / "spec.txt")
        wt = str(Path(__file__).resolve().parents[3])
        out = subprocess.run(
            [
                sys.executable, "-m", "wheeler.tools.cli", "llmsr", "init",
                "--spec", "spec.txt", "--data", "train.csv",
                "--metric", "mse", "--group-by", "cell_id",
            ],
            cwd=tmp_path, capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "PYTHONPATH": wt, "HOME": str(tmp_path)},
        )
        assert out.returncode == 0, out.stderr
        run_dir = Path(json.loads(out.stdout)["run_dir"])
        if not run_dir.is_absolute():
            run_dir = tmp_path / run_dir

        meta = json.loads((run_dir / "meta.json").read_text())
        assert meta["group_by"] == "cell_id"

        sub = json.loads((run_dir / "submissions.jsonl").read_text().splitlines()[0])
        assert sub["valid"] is True
        # The seed body IS the true form, so every cell fits once refitted.
        assert sorted(sub["per_group"]) == ["c01", "c02", "c03"]
        assert sorted(sub["params_per_group"]) == ["c01", "c02", "c03"]
        for name, (a, b) in CELLS.items():
            assert sub["params_per_group"][name][0] == pytest.approx(a, abs=1e-6)
            assert sub["params_per_group"][name][1] == pytest.approx(b, abs=1e-6)

    def test_group_by_rejects_an_unknown_column(self, tmp_path):
        self._write_csv(tmp_path / "train.csv")
        self._spec(tmp_path / "spec.txt")
        wt = str(Path(__file__).resolve().parents[3])
        out = subprocess.run(
            [
                sys.executable, "-m", "wheeler.tools.cli", "llmsr", "init",
                "--spec", "spec.txt", "--data", "train.csv",
                "--metric", "mse", "--group-by", "nope",
            ],
            cwd=tmp_path, capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "PYTHONPATH": wt, "HOME": str(tmp_path)},
        )
        assert out.returncode != 0
        assert "nope" in (out.stderr + out.stdout)
