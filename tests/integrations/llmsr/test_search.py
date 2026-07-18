"""Unit tests for the LLM-SR search CLI (init / prompt / submit / best).

No live model and no Neo4j: candidate bodies are scripted (the 'stub' generator),
so the whole mechanics path (seed, fit, score, register, best.json) runs offline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr.cli import llmsr_app

FIX = Path(__file__).parent / "fixtures"
SPEC = FIX / "spec_bactgrow.txt"
DATA = FIX / "train_small.csv"

runner = CliRunner()


def _out(result) -> dict:
    assert result.exit_code == 0, result.output
    return json.loads(result.output.strip().splitlines()[-1])


@pytest.fixture(autouse=True)
def _chdir(tmp_path, monkeypatch):
    # run dirs are created under cwd; isolate them per test
    monkeypatch.chdir(tmp_path)


def _init(metric="mse", generator="claude", run_id="t"):
    return _out(runner.invoke(llmsr_app, [
        "init", "--spec", str(SPEC), "--data", str(DATA),
        "--metric", metric, "--generator", generator, "--run-id", run_id,
    ]))


class TestInit:
    def test_seeds_run(self):
        m = _init()
        assert m["run_id"] == "t"
        assert m["metric"] == "mse"
        assert m["generator"] == "claude"
        assert m["seed_valid"] is True
        assert isinstance(m["seed_value"], float)
        assert Path(".wheeler/llmsr/runs/t/meta.json").exists()
        assert Path(".wheeler/llmsr/runs/t/submissions.jsonl").exists()

    def test_unknown_metric_rejected(self):
        res = runner.invoke(llmsr_app, [
            "init", "--spec", str(SPEC), "--data", str(DATA), "--metric", "bogus",
        ])
        assert res.exit_code != 0

    def test_unknown_generator_rejected(self):
        res = runner.invoke(llmsr_app, [
            "init", "--spec", str(SPEC), "--data", str(DATA),
            "--metric", "mse", "--generator", "gpt",
        ])
        assert res.exit_code != 0


class TestLoop:
    def test_prompt_submit_best(self):
        _init(run_id="loop")
        rd = ".wheeler/llmsr/runs/loop"

        p = _out(runner.invoke(llmsr_app, ["prompt", "--run", rd]))
        assert "island_id" in p and "version_generated" in p
        assert Path(p["prompt_file"]).exists()
        assert p["function_to_evolve"] == "equation"

        # a valid candidate body
        Path("good.py").write_text("    return params[0]*b*s/(params[1]+s) - params[2]*b")
        s = _out(runner.invoke(llmsr_app, [
            "submit", "--run", rd, "--body-file", "good.py",
            "--island-id", str(p["island_id"]),
            "--version-generated", str(p["version_generated"]),
        ]))
        assert s["valid"] is True
        assert isinstance(s["value"], float)

        # an invalid candidate: recorded invalid, never crashes
        Path("bad.py").write_text("    return nope * b")
        s2 = _out(runner.invoke(llmsr_app, [
            "submit", "--run", rd, "--body-file", "bad.py",
            "--island-id", str(p["island_id"]),
            "--version-generated", str(p["version_generated"]),
        ]))
        assert s2["valid"] is False
        assert s2["value"] is None

        b = _out(runner.invoke(llmsr_app, ["best", "--run", rd]))
        assert b["status"] == "completed"

        best = json.loads(Path(rd, "best.json").read_text())
        assert best["status"] == "completed"
        assert best["metric"] == "mse"
        assert best["equation"] and best["program"]
        assert len(best["params"]) == 10
        assert best["metrics"]["mse_train"] == pytest.approx(best["metrics"]["mse_train"])
        # the winning program is the FULL runnable artifact (skeleton + constants)
        assert "FITTED_PARAMS" in best["program"]
        assert "__main__" in best["program"]
        assert best["n_valid"] >= 1
        # the FINAL result only: no intermediate per-candidate trail in best.json
        assert "history" not in best


# a minimal valid 2-input spec for the selection test
_SEL_SPEC = '''"""oscillator"""
import numpy as np

MAX_NPARAMS = 10


@evaluate.run
def evaluate(data: dict) -> float:
    inputs, outputs = data['inputs'], data['outputs']
    x, v = inputs[:, 0], inputs[:, 1]
    return 0.0


@equation.evolve
def equation(x: np.ndarray, v: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x + params[1]*v
'''


class TestSelection:
    """Discovery-oriented selection recovers the TRUE law where pure fit picks an
    overfit. On NOISY data a flexible polynomial gets lower TRAINING error than
    the true form, but it does not generalize (OOD) and is not parsimonious."""

    def _candidates(self, tmp_path):
        import numpy as np

        from wheeler.integrations.llmsr import fit as fitmod
        from wheeler.integrations.llmsr import metrics
        from wheeler.integrations.llmsr.vendor import code_manipulation, evaluator

        template = code_manipulation.text_to_program(_SEL_SPEC)
        rng = np.random.default_rng(3)

        def gen(n, lo, hi):
            x = rng.uniform(lo, hi, n)
            v = rng.uniform(-2, 2, n)
            y = -3.2 * np.sin(x) - 0.45 * v + rng.normal(0, 0.05, n)
            return np.column_stack([x, v, y])

        tr, od = gen(60, -2.5, 2.5), gen(200, 2.5, 4.0)
        np.savetxt(tmp_path / "train.csv", tr, delimiter=",", header="x,v,y", comments="")
        np.savetxt(tmp_path / "test_ood.csv", od, delimiter=",", header="x,v,y", comments="")
        X, y = tr[:, :-1], tr[:, -1]
        nmse = metrics.get_metric("nmse")

        def cand(body):
            _fn, program = evaluator._sample_to_program(body, None, template, "equation")
            r = fitmod.evaluate_body(program, "equation", X, y, nmse)
            return {"body": body, "program": program, "params": r.params,
                    "score": r.score, "value": r.value}

        true_form = "    return params[0]*np.sin(x) + params[1]*v"
        poly = ("    return params[0]*x+params[1]*v+params[2]*x**3+params[3]*x**5"
                "+params[4]*x**7+params[5]*x**9+params[6]*x*v+params[7]*v**3")
        meta = {"data_path": str(tmp_path / "train.csv"),
                "function_to_evolve": "equation", "metric": "nmse"}
        return [cand(true_form), cand(poly)], meta

    def test_ood_and_parsimony_recover_true_law(self, tmp_path):
        from wheeler.integrations.llmsr.cli import _candidate_ood, _select_winner

        valid, meta = self._candidates(tmp_path)
        true_c, poly_c = valid

        # the overfit polynomial has LOWER training error but DIVERGES out of domain
        assert poly_c["value"] < true_c["value"]  # better fit
        poly_ood = _candidate_ood(meta, dict(poly_c))
        true_ood = _candidate_ood(meta, dict(true_c))
        assert poly_ood is None or (true_ood is not None and poly_ood > true_ood * 100)

        # pure fit picks the overfit; discovery-oriented modes recover the true law
        assert "sin" not in _select_winner([dict(c) for c in valid], meta, "fit")["body"]
        assert "sin" in _select_winner([dict(c) for c in valid], meta, "ood")["body"]
        assert "sin" in _select_winner([dict(c) for c in valid], meta, "parsimony")["body"]
