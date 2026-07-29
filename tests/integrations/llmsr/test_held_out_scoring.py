"""Held-out scoring reports BOTH quantities, and ranks on the run's own metric.

Two wrong-quantity bugs, fixed at source in ``selection.py`` (issue #107, S3):

1. ``_split_metrics`` returned ``{}`` for ANY grouped run, so a grouped run
   reported no held-out number at all. It now applies each group's own source
   constants (fixed theta) AND refits per group (the form), in two labelled dicts.
2. ``_candidate_ood`` hardcoded NMSE for every regression run, so a run whose
   declared objective was a registered custom metric was ranked on a quantity it
   never chose. It now uses the run's own metric, through ``score_from_value`` so
   a metric where higher is better is not ranked backwards.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.llmsr.selection import _candidate_ood, _select_winner
from wheeler.integrations.llmsr.vendor import code_manipulation, evaluator

runner = CliRunner()

CELLS = {"c01": (2.5, -1.0), "c02": (-4.0, 8.0)}

SPEC = (
    "import numpy as np\n\n"
    "MAX_NPARAMS = 4\n\n"
    "@evaluate.run\n"
    "def evaluate(data):\n"
    "    return 0.0\n\n"
    "@equation.evolve\n"
    "def equation(x1, params):\n"
    "    return params[0] * x1 + params[1]\n"
)


def _out(result) -> dict:
    assert result.exit_code == 0, result.output
    return json.loads(result.output.strip().splitlines()[-1])


def _grouped_csv(path: Path, cells: dict[str, tuple[float, float]], seed: int) -> None:
    lines = ["cell_id,x1,y"]
    for i, (cell, (a, b)) in enumerate(cells.items()):
        x = np.random.default_rng(seed + i).uniform(-3.0, 3.0, 30)
        lines += [
            f"{cell},{float(xi):.17g},{float(a * xi + b):.17g}" for xi in x
        ]
    path.write_text("\n".join(lines) + "\n")


def _plain_csv(path: Path, a: float, b: float, seed: int) -> None:
    x = np.random.default_rng(seed).uniform(-3.0, 3.0, 30)
    lines = ["x1,y"] + [f"{float(xi):.17g},{float(a * xi + b):.17g}" for xi in x]
    path.write_text("\n".join(lines) + "\n")


class TestGroupedRunsGetHeldOutNumbers:
    def test_a_grouped_run_no_longer_reports_an_empty_metrics_dict(self, tmp_path):
        (tmp_path / "spec.txt").write_text(SPEC)
        _grouped_csv(tmp_path / "train.csv", CELLS, seed=1)
        _grouped_csv(tmp_path / "test_ood.csv", CELLS, seed=50)

        _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"),
            "--data", str(tmp_path / "train.csv"),
            "--metric", "mse", "--group-by", "cell_id", "--run-id", "g",
        ]))
        _out(runner.invoke(llmsr_app, ["best", "--run", ".wheeler/llmsr/runs/g"]))
        best = json.loads(Path(".wheeler/llmsr/runs/g/best.json").read_text())

        # Was `{}` for every grouped run before this slice.
        assert best["metrics"], "a grouped run must report its held-out splits"
        assert best["metrics"]["mse_test_ood"] == pytest.approx(0.0, abs=1e-10)
        assert best["metrics_refit"]["mse_test_ood"] == pytest.approx(0.0, abs=1e-12)

        # TRAIN stays out of `metrics` for a grouped run: its answer is the
        # per-group value TABLE, and the ingest labels the mean over it as a mean.
        assert not any(k.endswith("_train") for k in best["metrics"])
        assert best["value_per_group"]
        # and refit never duplicates train, grouped or not
        assert not any(k.endswith("_train") for k in best["metrics_refit"])

    def test_a_group_the_source_never_saw_gets_no_fixed_theta_number(self, tmp_path):
        """The refit still answers; the fixed-theta aggregate refuses to guess."""
        (tmp_path / "spec.txt").write_text(SPEC)
        _grouped_csv(tmp_path / "train.csv", CELLS, seed=1)
        # The held-out file contains a cell the training run never fitted, so no
        # source constant vector belongs to it.
        _grouped_csv(
            tmp_path / "test_ood.csv", {"c01": CELLS["c01"], "c99": (7.0, -2.0)}, seed=9
        )

        _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"),
            "--data", str(tmp_path / "train.csv"),
            "--metric", "mse", "--group-by", "cell_id", "--run-id", "gx",
        ]))
        _out(runner.invoke(llmsr_app, ["best", "--run", ".wheeler/llmsr/runs/gx"]))
        best = json.loads(Path(".wheeler/llmsr/runs/gx/best.json").read_text())

        assert "mse_test_ood" not in best["metrics"]
        # The FORM still transfers, and that number is reported.
        assert best["metrics_refit"]["mse_test_ood"] == pytest.approx(0.0, abs=1e-12)


class TestUngroupedIsUnchanged:
    def test_fixed_theta_keys_and_numbers_are_what_they_always_were(self, tmp_path):
        (tmp_path / "spec.txt").write_text(SPEC)
        _plain_csv(tmp_path / "train.csv", 2.5, -1.0, seed=1)
        _plain_csv(tmp_path / "test_ood.csv", 2.5, -1.0, seed=40)

        _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"),
            "--data", str(tmp_path / "train.csv"),
            "--metric", "mse", "--run-id", "u",
        ]))
        _out(runner.invoke(llmsr_app, ["best", "--run", ".wheeler/llmsr/runs/u"]))
        best = json.loads(Path(".wheeler/llmsr/runs/u/best.json").read_text())

        # The historic keys, still fixed theta, still present.
        for key in ("mse_train", "nmse_train", "mse_test_ood", "nmse_test_ood"):
            assert key in best["metrics"], key
        assert best["metrics"]["mse_train"] == pytest.approx(0.0, abs=1e-12)

        # The refit dict covers held-out splits only: on train the constants were
        # already fitted, so a refit reports the same number under a second name.
        assert "mse_test_ood" in best["metrics_refit"]
        assert "mse_train" not in best["metrics_refit"]

    def test_a_run_with_no_siblings_reports_train_only(self, tmp_path):
        (tmp_path / "spec.txt").write_text(SPEC)
        _plain_csv(tmp_path / "train.csv", 2.5, -1.0, seed=1)
        _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"),
            "--data", str(tmp_path / "train.csv"),
            "--metric", "mse", "--run-id", "solo",
        ]))
        _out(runner.invoke(llmsr_app, ["best", "--run", ".wheeler/llmsr/runs/solo"]))
        best = json.loads(Path(".wheeler/llmsr/runs/solo/best.json").read_text())
        assert set(best["metrics"]) == {"mse_train", "nmse_train"}
        assert best["metrics_refit"] == {}


def _mae(y_pred, y_true) -> float:
    yp = np.asarray(y_pred, dtype=float).reshape(-1)
    yt = np.asarray(y_true, dtype=float).reshape(-1)
    return float(np.mean(np.abs(yp - yt)))


def _neg_mse(y_pred, y_true) -> float:
    yp = np.asarray(y_pred, dtype=float).reshape(-1)
    yt = np.asarray(y_true, dtype=float).reshape(-1)
    return -float(np.mean((yp - yt) ** 2))


class TestOodRanksOnTheRunsOwnMetric:
    """The registry is restored by the directory conftest, so registering here
    cannot leak into another test."""

    def _candidates(self, tmp_path, bodies: list[str], metric):
        template = code_manipulation.text_to_program(SPEC)
        rng = np.random.default_rng(5)
        x_tr = rng.uniform(-1.0, 1.0, 40)
        x_ood = rng.uniform(3.0, 5.0, 40)
        np.savetxt(
            tmp_path / "train.csv", np.column_stack([x_tr, 2.0 * x_tr]),
            delimiter=",", header="x1,y", comments="",
        )
        np.savetxt(
            tmp_path / "test_ood.csv", np.column_stack([x_ood, 2.0 * x_ood]),
            delimiter=",", header="x1,y", comments="",
        )
        X, y = x_tr.reshape(-1, 1), 2.0 * x_tr
        out = []
        for body in bodies:
            _fn, program = evaluator._sample_to_program(body, None, template, "equation")
            r = fit_mod.evaluate_body(program, "equation", X, y, metric)
            out.append({
                "body": body, "program": program, "params": r.params,
                "params_per_group": r.params_per_group,
                "score": r.score, "value": r.value,
            })
        meta = {
            "data_path": str(tmp_path / "train.csv"),
            "function_to_evolve": "equation",
            "metric": metric.key,
            "group_by": "",
        }
        return out, meta

    def test_a_custom_metric_is_not_silently_replaced_by_nmse(self, tmp_path):
        mae = metrics_mod.register_metric(metrics_mod.Metric(
            key="mae", label="mean absolute error", data_shape="regression",
            lower_is_better=True, loss=_mae, report=_mae,
        ))
        (cand,), meta = self._candidates(tmp_path, ["    return params[0] * x1"], mae)

        got = _candidate_ood(meta, cand)
        X_ood = np.genfromtxt(tmp_path / "test_ood.csv", delimiter=",", skip_header=1)
        as_mae = fit_mod.evaluate_fixed(
            cand["program"], "equation", X_ood[:, :-1], X_ood[:, -1],
            cand["params"], mae,
        )
        as_nmse = fit_mod.evaluate_fixed(
            cand["program"], "equation", X_ood[:, :-1], X_ood[:, -1],
            cand["params"], metrics_mod.NMSE,
        )
        assert got == pytest.approx(as_mae)
        # The two really are different quantities, so ranking on the wrong one
        # would have been a silent substitution rather than a harmless alias.
        assert as_mae != pytest.approx(as_nmse)

    def test_a_higher_is_better_metric_is_not_ranked_backwards(self, tmp_path):
        neg = metrics_mod.register_metric(metrics_mod.Metric(
            key="negmse", label="negative MSE (higher is better)",
            data_shape="regression", lower_is_better=False,
            loss=lambda yp, yt: -_neg_mse(yp, yt), report=_neg_mse,
        ))
        bodies = [
            "    return params[0] * x1",       # the true law: extrapolates
            "    return params[0] * x1**3",    # diverges out of domain
        ]
        cands, meta = self._candidates(tmp_path, bodies, neg)
        true_c, cubic_c = cands
        assert _candidate_ood(meta, true_c) > _candidate_ood(meta, cubic_c)

        # `min` over the raw value would have picked the DIVERGING form, because
        # for this metric a lower number is a worse one.
        winner = _select_winner([dict(c) for c in cands], meta, "ood")
        assert winner["body"] == true_c["body"]


class TestBestReportsWhatItRankedOn:
    def test_selection_names_the_ranking_quantity(self, tmp_path):
        (tmp_path / "spec.txt").write_text(SPEC)
        _plain_csv(tmp_path / "train.csv", 2.5, -1.0, seed=1)
        _plain_csv(tmp_path / "test_ood.csv", 2.5, -1.0, seed=40)
        _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"),
            "--data", str(tmp_path / "train.csv"),
            "--metric", "mse", "--run-id", "r",
        ]))
        _out(runner.invoke(llmsr_app, [
            "best", "--run", ".wheeler/llmsr/runs/r", "--select", "ood",
        ]))
        best = json.loads(Path(".wheeler/llmsr/runs/r/best.json").read_text())
        assert best["selection"]["ranked_on"] == "test_ood fixed-theta mse"
