"""The spec's own ``@evaluate.run`` as a selectable scoring door.

Wheeler's default substitutes its own fit/metric seam for the spec's
``@evaluate.run``: it parses the name into ``meta["function_to_run"]`` and never
calls it. That substitution is what makes the metric pluggable and the constants
recoverable, so it stays the default. ``--use-spec-evaluate`` makes it a CHOICE.

What these tests are actually defending, in order of how badly each would fail:

1. **The default did not move.** Nothing here changes how a run without the flag
   is scored, and the spec's ``evaluate`` is never called on that path. Proven
   with a spec whose ``evaluate`` leaves a trace on disk and returns an
   unmistakable non-answer.
2. **Opt-in by flag, never by sniffing.** The same spec text scores two different
   ways depending only on the flag, and nothing inspects the body of ``evaluate``
   to guess. Detection would silently change scoring when somebody edited a
   comment.
3. **The door is as wide as upstream claims.** Upstream's
   ``specification_oscillator2_torch.txt`` defines a ``torch.nn.Module``, an Adam
   optimizer and a 10,000-step gradient loop INSIDE the spec, and the unmodified
   package runs it. ``TestWidth`` proves the same class of spec runs here, in
   pure numpy so the gate is never skipped, and again under torch when torch is
   importable.
4. **One call per UNIT.** The unit of fitting is a (dataset, group) pair, so the
   spec's ``evaluate`` is called once per pair. Calling it once per candidate
   would silently lose the per-unit refit the per-group protocol exists for.
5. **The score keys are the run's, never the spec's.** A spec that could name
   its own keys would silently invalidate the vendored buffer's signature
   clustering.
6. **A failure is a failure.** A spec that raises, returns ``None``, returns
   garbage or returns a non-finite number yields an INVALID candidate with a
   truthful error, never a fabricated score.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import data as data_mod
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr import spec_eval as spec_eval_mod
from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.llmsr.vendor import code_manipulation, evaluator

from .test_multidata import _write_table

runner = CliRunner()

MSE = metrics_mod.get_metric("mse")


# ------------------------------------------------------------------- harness

def _program(spec_text: str, body: str) -> tuple[str, str, str]:
    """``(program, function_to_evolve, function_to_run)`` for a spec + a body.

    The same two vendored calls the CLI makes, so what these tests hand the door
    is what a real submit hands it.
    """
    fte = list(code_manipulation.yield_decorated(spec_text, "equation", "evolve"))[0]
    ftr = list(code_manipulation.yield_decorated(spec_text, "evaluate", "run"))[0]
    template = code_manipulation.text_to_program(spec_text)
    _fn, program = evaluator._sample_to_program(body, None, template, fte)
    return program, fte, ftr


def _score(spec_text: str, body: str, X, y, **kwargs):
    """Score one candidate through the spec's own ``evaluate``, one unit."""
    program, _fte, ftr = _program(spec_text, body)
    return spec_eval_mod.evaluate_spec_grouped(
        program, ftr, [("data", "data", X, y)], MSE, **kwargs
    )


def _linear_xy(a: float = 2.0, b: float = -0.5, c: float = 1.0, n: int = 40):
    """``y = a*x + b*x**2 + c`` exactly, so a correct form can reach zero error."""
    x = np.linspace(-2.0, 2.0, n)
    return x.reshape(-1, 1), a * x + b * x**2 + c


def _out(result) -> dict:
    assert result.exit_code == 0, result.output + str(result.exception)
    return json.loads(result.output.strip().splitlines()[-1])


# -------------------------------------------------------------------- specs

# A spec whose `evaluate` is impossible to confuse with a real fit: it records
# that it ran, and returns a score no least-squares fit could produce.
_SHOUTING_SPEC = '''"""a spec that says when it ran"""
import numpy as np

MAX_NPARAMS = 3


@evaluate.run
def evaluate(data: dict) -> float:
    with open("evaluate_ran.log", "a") as fh:
        fh.write("called\\n")
    return 12345.0


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''

# Upstream's own contract, reproduced: fit inside `evaluate`, return `-loss` as a
# bare float, discard the constants (`result.x` is computed and thrown away, as
# in every upstream spec).
_UPSTREAM_SPEC = '''"""upstream's shape: a bare float, constants discarded"""
import numpy as np

MAX_NPARAMS = 3


@evaluate.run
def evaluate(data: dict) -> float:
    inputs, outputs = data['inputs'], data['outputs']
    x = inputs[:, 0]

    from scipy.optimize import minimize
    def loss(params):
        return np.mean((equation(x, params) - outputs) ** 2)

    result = minimize(loss, [1.0]*MAX_NPARAMS, method='BFGS')
    optimized_params = result.x  # computed, then discarded: upstream's contract
    if np.isnan(result.fun) or np.isinf(result.fun):
        return None
    return -result.fun


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''

# The same fit, returning Wheeler's additive dict so the constants survive.
_DICT_SPEC = _UPSTREAM_SPEC.replace(
    "    return -result.fun\n",
    "    return {'score': -result.fun, 'params': [float(v) for v in optimized_params]}\n",
).replace('"""upstream\'s shape: a bare float, constants discarded"""',
          '"""the additive dict: the same score, plus the constants"""')

_BODY = "    return params[0]*x + params[1]*x**2 + params[2]\n"


def _returning(expression: str) -> str:
    """A spec whose ``evaluate`` returns ``expression``, whatever that is."""
    return f'''"""a spec that returns {expression}"""
import numpy as np

MAX_NPARAMS = 3


@evaluate.run
def evaluate(data: dict):
    return {expression}


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''


_RAISING_SPEC = '''"""a spec whose evaluate blows up"""
import numpy as np

MAX_NPARAMS = 3


@evaluate.run
def evaluate(data: dict) -> float:
    raise RuntimeError("the solver did not converge")


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''


# ------------------------------------------------------- the default is unmoved

class TestTheDefaultDoorIsUnmoved:
    """Without the flag, the spec's ``evaluate`` is never called. As always."""

    def test_default_run_never_calls_the_specs_evaluate(self, tmp_path):
        (tmp_path / "spec.txt").write_text(_SHOUTING_SPEC)
        _write_table(tmp_path / "a.csv", 2.0, 0.5, seed=0)
        (tmp_path / "body.py").write_text(_BODY)
        out = _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"),
            "--data", str(tmp_path / "a.csv"), "--metric", "mse",
            "--run-id", "default-door",
        ]))

        assert out["use_spec_evaluate"] is False
        assert not Path("evaluate_ran.log").exists()
        # Wheeler's seam fitted it: a real MSE, not the spec's 12345.
        assert out["seed_valid"] is True
        assert 0.0 <= out["seed_value"] < 1e4

    def test_the_flag_is_what_switches_doors_not_the_spec_text(self, tmp_path):
        """Identical spec text, opposite doors. Nothing is inferred from the body.

        This is the whole safety argument for the feature: were the door chosen by
        sniffing whether ``evaluate`` "looks stock", editing a comment inside it
        would silently change how every candidate in the run is scored.
        """
        (tmp_path / "spec.txt").write_text(_SHOUTING_SPEC)
        _write_table(tmp_path / "a.csv", 2.0, 0.5, seed=0)
        out = _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"),
            "--data", str(tmp_path / "a.csv"), "--metric", "mse",
            "--run-id", "spec-door", "--use-spec-evaluate",
        ]))

        assert out["use_spec_evaluate"] is True
        assert Path("evaluate_ran.log").read_text().count("called") == 1
        # The spec's number, taken verbatim as upstream's maximize-me score.
        meta = json.loads(Path(".wheeler/llmsr/runs/spec-door/meta.json").read_text())
        assert meta["use_spec_evaluate"] is True
        sub = json.loads(
            Path(".wheeler/llmsr/runs/spec-door/submissions.jsonl").read_text().strip()
        )
        assert sub["score"] == 12345.0
        assert sub["value"] == -12345.0  # read back under mse's orientation
        assert sub["optimizer"] == spec_eval_mod.SPEC_EVALUATE

    def test_a_run_dir_written_before_the_door_existed_uses_the_default(self):
        """No ``use_spec_evaluate`` key at all means the substitution, as before."""
        from wheeler.integrations.llmsr.cli import _spec_knobs

        assert _spec_knobs({"function_to_run": "evaluate"})["use_spec_evaluate"] is False


# ------------------------------------------------------------ upstream contract

class TestUpstreamsContract:
    """A bare float behaves exactly as it does upstream; the dict adds to it."""

    def test_a_bare_float_is_the_maximize_me_score(self):
        X, y = _linear_xy()
        result = _score(_UPSTREAM_SPEC, _BODY, X, y)

        assert result.valid
        # The true form is reachable, so upstream's `-loss` lands at ~0 from above.
        assert result.score == pytest.approx(0.0, abs=1e-6)
        assert result.score <= 0.0
        assert result.value == pytest.approx(-result.score)
        # Upstream's contract has nowhere to return the constants.
        assert result.params == []
        assert result.params_per_group == {}
        assert result.optimizer == spec_eval_mod.SPEC_EVALUATE

    def test_the_dict_carries_the_constants_through(self):
        X, y = _linear_xy(a=2.0, b=-0.5, c=1.0)
        result = _score(_DICT_SPEC, _BODY, X, y)

        assert result.valid
        assert result.score == pytest.approx(0.0, abs=1e-6)
        # The constants the spec fitted and upstream would have discarded.
        assert len(result.params) == 3
        assert result.params == pytest.approx([2.0, -0.5, 1.0], abs=1e-3)
        assert result.params_per_group == {"data": result.params}

    def test_the_two_shapes_agree_on_the_score(self):
        """The dict adds constants; it does not change the number."""
        X, y = _linear_xy()
        bare = _score(_UPSTREAM_SPEC, _BODY, X, y)
        rich = _score(_DICT_SPEC, _BODY, X, y)
        assert bare.score == pytest.approx(rich.score, abs=1e-9)


# --------------------------------------------------------------- truthful failure

class TestAFailureIsAFailure:
    """No fabricated score, ever. Every rejection names itself."""

    @pytest.mark.parametrize("expression,fragment", [
        ("None", "returned NoneType"),
        ("'nope'", "returned str"),
        ("np.zeros(3)", "returned ndarray"),
        ("float('nan')", "returned float"),
        ("float('inf')", "returned float"),
        ("True", "returned bool"),
        ("{'params': [1.0]}", "no 'score'"),
        ("{'score': 'x'}", "'score' is not a finite number"),
        ("{'score': float('nan')}", "'score' is not a finite number"),
        ("{'score': 1.0, 'params': ['a']}", "'params' is not a numeric sequence"),
        ("{'score': 1.0, 'params': [float('nan')]}", "'params' holds a non-finite"),
        ("{'score': 1.0, 'loss': 2.0}", "unknown key(s) ['loss']"),
    ], ids=lambda v: str(v)[:28])
    def test_a_bad_return_is_invalid_and_says_why(self, expression, fragment):
        X, y = _linear_xy()
        result = _score(_returning(expression), _BODY, X, y)

        assert not result.valid
        assert result.score is None
        assert result.value is None
        assert result.rejection_reason == "numeric"
        assert fragment in result.error, result.error

    def test_a_raising_evaluate_reports_its_own_exception(self):
        X, y = _linear_xy()
        result = _score(_RAISING_SPEC, _BODY, X, y)

        assert not result.valid
        assert result.score is None
        assert "RuntimeError" in result.error
        assert "the solver did not converge" in result.error

    def test_a_missing_evaluate_callable_is_named(self):
        X, y = _linear_xy()
        program, _fte, _ftr = _program(_UPSTREAM_SPEC, _BODY)
        result = spec_eval_mod.evaluate_spec_grouped(
            program, "not_a_function", [("data", "data", X, y)], MSE
        )
        assert not result.valid
        assert "no callable 'not_a_function'" in result.error

    def test_a_wedged_evaluate_is_bounded_by_the_sandbox(self):
        """The spec's code runs in the SAME forked, timeout-bounded child the fit
        uses, so a spec that never returns cannot wedge the driver."""
        X, y = _linear_xy()
        spec = _returning("__import__('time').sleep(30) or 1.0")
        result = _score(spec, _BODY, X, y, timeout_seconds=1)

        assert not result.valid
        assert result.error == "timeout after 1s"
        assert result.rejection_reason == "numeric"


# ------------------------------------------------------------------- per unit

# One shared FORM whose constants differ per (dataset, group). Only a per-unit
# refit can fit them all, which is exactly what would be lost if the spec's
# `evaluate` were called once per candidate instead of once per unit.
_PER_UNIT_SPEC = '''"""per-unit spec: fits, and records which unit it was handed"""
import numpy as np

MAX_NPARAMS = 3


@evaluate.run
def evaluate(data: dict) -> dict:
    inputs, outputs = data['inputs'], data['outputs']
    groups = data.get('groups')
    with open("units_seen.log", "a") as fh:
        fh.write(f"{len(outputs)},{'' if groups is None else groups[0]}\\n")

    x = inputs[:, 0]
    from scipy.optimize import minimize
    def loss(params):
        return np.mean((equation(x, params) - outputs) ** 2)

    result = minimize(loss, [1.0]*MAX_NPARAMS, method='BFGS')
    if not np.isfinite(result.fun):
        return None
    return {'score': -result.fun, 'params': [float(v) for v in result.x]}


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''


class TestOneCallPerUnit:
    """The unit of fitting is a (dataset, group) pair, and so is the unit of call."""

    def _walk(self, tmp_path, args: list[str], run_id: str) -> dict:
        (tmp_path / "spec.txt").write_text(_PER_UNIT_SPEC)
        _write_table(tmp_path / "a.csv", 2.0, 0.5, seed=0, cells=2)
        _write_table(tmp_path / "b.csv", -1.5, 3.0, seed=1, cells=2)
        (tmp_path / "body.py").write_text(_BODY)
        _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"), "--metric", "mse",
            "--run-id", run_id, "--use-spec-evaluate", *args,
        ]))
        run_dir = Path(".wheeler/llmsr/runs") / run_id
        return json.loads(
            (run_dir / "submissions.jsonl").read_text().strip().splitlines()[0]
        )

    def test_evaluate_is_called_once_per_dataset_and_group(self, tmp_path):
        sub = self._walk(tmp_path, [
            "--data", f"A={tmp_path / 'a.csv'}",
            "--data", f"B={tmp_path / 'b.csv'}",
            "--group-by", "cell",
        ], "per-unit")

        seen = Path("units_seen.log").read_text().strip().splitlines()
        assert len(seen) == 4  # 2 datasets x 2 cells
        # The group label the SCIENTIST'S column carries, not Wheeler's key.
        assert sorted({line.split(",")[1] for line in seen}) == ["c00", "c01"]
        # And the score keys are the run's own, qualified by dataset.
        assert set(sub["per_group"]) == {"A:c00", "A:c01", "B:c00", "B:c01"}

    def test_every_unit_refits_its_own_constants(self, tmp_path):
        sub = self._walk(tmp_path, [
            "--data", f"A={tmp_path / 'a.csv'}",
            "--data", f"B={tmp_path / 'b.csv'}",
            "--group-by", "cell",
        ], "per-unit-theta")

        table = sub["params_per_group"]
        assert set(table) == {"A:c00", "A:c01", "B:c00", "B:c01"}
        # Four genuinely different constant vectors: the whole point of the unit.
        assert len({tuple(round(v, 6) for v in vec) for vec in table.values()}) == 4
        assert sub["valid"] is True

    def test_groups_is_absent_when_the_run_is_not_grouped(self, tmp_path):
        self._walk(tmp_path, ["--data", f"A={tmp_path / 'a.csv'}"], "per-unit-flat")

        seen = Path("units_seen.log").read_text().strip().splitlines()
        assert len(seen) == 1
        # `data['groups']` is Wheeler's addition and appears only under grouping,
        # so an upstream spec reading only inputs/outputs sees upstream's dict.
        assert seen[0].endswith(",")


class TestTheSpecCannotNameScoreKeys:
    """Score keys are fixed at ``init``; the vendored buffer clusters on them."""

    def test_a_stray_per_group_key_is_refused_loudly(self):
        X, y = _linear_xy()
        result = _score(_returning("{'score': 1.0, 'per_group': {'mine': 2.0}}"), _BODY, X, y)

        assert not result.valid
        assert "'per_group' names ['mine']" in result.error
        assert "score keys belong to the run" in result.error

    def test_per_group_naming_this_unit_supplies_its_score(self):
        X, y = _linear_xy()
        result = _score(_returning("{'per_group': {'data': -3.5}}"), _BODY, X, y)

        assert result.valid
        assert result.score == -3.5
        assert result.per_group == {"data": -3.5}

    def test_per_group_that_is_not_a_mapping_is_refused(self):
        X, y = _linear_xy()
        result = _score(_returning("{'score': 1.0, 'per_group': [1.0]}"), _BODY, X, y)

        assert not result.valid
        assert "'per_group' is not a mapping" in result.error


# ------------------------------------------------------------------- the width

# The gate that always runs. A spec that does its OWN imports, defines its OWN
# optimizer, and runs a multi-thousand-step training loop, entirely in numpy.
# Structurally this is upstream's torch spec (a module, an Adam, a long loop
# inside `evaluate`) without the 2GB dependency, so the claim "the door is as
# wide as upstream's" is checked on every test run rather than skipped.
_WIDTH_SPEC = '''"""a spec that trains its own model, its own way"""
import numpy as np

MAX_NPARAMS = 3
STEPS = __STEPS__


@evaluate.run
def evaluate(data: dict) -> dict:
    """Fit the candidate with a hand-rolled Adam over a numeric gradient."""
    import math
    from collections import OrderedDict

    inputs, outputs = data['inputs'], data['outputs']
    x = inputs[:, 0]

    class Adam:
        """An optimizer defined INSIDE the spec, as upstream's torch spec does."""

        def __init__(self, n, lr=0.1, b1=0.9, b2=0.999, eps=1e-8):
            self.m, self.v = np.zeros(n), np.zeros(n)
            self.lr, self.b1, self.b2, self.eps, self.t = lr, b1, b2, eps, 0

        def step(self, theta, grad):
            self.t += 1
            self.m = self.b1 * self.m + (1 - self.b1) * grad
            self.v = self.b2 * self.v + (1 - self.b2) * grad * grad
            mhat = self.m / (1 - self.b1 ** self.t)
            vhat = self.v / (1 - self.b2 ** self.t)
            denom = np.array([math.sqrt(u) for u in vhat]) + self.eps
            return theta - self.lr * mhat / denom

    def loss(theta):
        return float(np.mean((equation(x, theta) - outputs) ** 2))

    def grad(theta, h=1e-6):
        g = np.zeros_like(theta)
        for i in range(len(theta)):
            up, dn = theta.copy(), theta.copy()
            up[i] += h
            dn[i] -= h
            g[i] = (loss(up) - loss(dn)) / (2 * h)
        return g

    theta = np.zeros(MAX_NPARAMS)
    opt = Adam(MAX_NPARAMS)
    history = OrderedDict()
    for step in range(STEPS):
        theta = opt.step(theta, grad(theta))
        history[step] = loss(theta)

    final = loss(theta)
    if not np.isfinite(final):
        return None
    return {'score': -final, 'params': [float(v) for v in theta]}


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''


def _width_spec(steps: int) -> str:
    return _WIDTH_SPEC.replace("__STEPS__", str(steps))


class TestTheDoorIsAsWideAsUpstreamClaims:
    """Arbitrary Python inside ``evaluate``: own imports, own optimizer, own loop."""

    def test_a_spec_that_trains_its_own_model_scores(self):
        """Non-skippable: pure numpy, no optional dependency, runs every time.

        Three things are asserted, and the middle one is the point. That it scores
        at all proves the door opens. That 3000 steps beat 1 step proves the LOOP
        RAN inside the sandbox, rather than the spec being compiled and its
        return value faked. That the constants come back proves the additive dict
        survives the process boundary.
        """
        X, y = _linear_xy(a=2.0, b=-0.5, c=1.0)

        one_step = _score(_width_spec(1), _BODY, X, y)
        trained = _score(_width_spec(3000), _BODY, X, y)

        assert one_step.valid and trained.valid
        # Higher is better: the score is upstream's maximize-me `-loss`.
        assert trained.score > one_step.score
        # And the training actually converged on the true constants.
        assert trained.params == pytest.approx([2.0, -0.5, 1.0], abs=1e-2)
        assert -trained.score < 1e-4
        assert -one_step.score > 1.0

    def test_the_default_door_cannot_score_that_spec_the_same_way(self):
        """The contrast that makes the door worth having.

        Wheeler's own seam ignores everything inside ``evaluate``: it fits the
        constants itself under the run's declared metric. So the spec's optimizer,
        its schedule and its 3000 steps have no effect on the number at all. Both
        answers are legitimate; they are simply not the same measurement, which is
        why the door is a declared choice and not a detail.
        """
        from wheeler.integrations.llmsr import fit as fit_mod

        X, y = _linear_xy()
        program, fte, _ftr = _program(_width_spec(3000), _BODY)
        wheeler_side = fit_mod.evaluate_body_grouped(
            program, fte, [("data", X, y)], MSE, max_nparams=3
        )
        one_step = _score(_width_spec(1), _BODY, X, y)

        assert wheeler_side.valid
        # Wheeler's fit reaches the same law, by its own machinery.
        assert wheeler_side.params == pytest.approx([2.0, -0.5, 1.0], abs=1e-3)
        # The spec's own answer is the spec's: one step of Adam is one step.
        assert one_step.score < wheeler_side.score

    def test_a_torch_spec_runs_when_torch_is_available(self):
        """The torch gate, conditional on torch being importable.

        NOTE ON PROVENANCE: this is a spec that is EQUIVALENT IN STRUCTURE to
        upstream's ``specification_oscillator2_torch.txt`` (a ``torch.nn.Module``,
        a ``torch.optim.Adam``, and a gradient loop inside ``evaluate``). It is
        NOT upstream's literal file, which is not vendored in this repository, and
        no claim is made here about having run theirs. The step count is 400
        rather than their 10,000 so the gate stays a test.

        torch is not installed in this environment, so this SKIPS here. The
        always-runs proof of the same property is
        ``test_a_spec_that_trains_its_own_model_scores`` above, in numpy.
        """
        pytest.importorskip("torch")

        X, y = _linear_xy(a=2.0, b=-0.5, c=1.0)
        result = _score(_TORCH_SPEC, _BODY, X, y)

        assert result.valid, result.error
        assert result.params == pytest.approx([2.0, -0.5, 1.0], abs=5e-2)
        assert -result.score < 1e-2


# Equivalent in structure to upstream's torch specification, not a copy of it.
_TORCH_SPEC = '''"""a torch spec: a module, an Adam, and a gradient loop"""
import numpy as np

MAX_NPARAMS = 3
STEPS = 400


@evaluate.run
def evaluate(data: dict) -> dict:
    import torch
    import torch.nn as nn

    inputs, outputs = data['inputs'], data['outputs']
    x = torch.tensor(inputs[:, 0], dtype=torch.float64)
    y = torch.tensor(np.asarray(outputs), dtype=torch.float64)

    class Model(nn.Module):
        def __init__(self, n):
            super().__init__()
            self.params = nn.Parameter(torch.zeros(n, dtype=torch.float64))

        def forward(self, xs):
            return equation(xs, self.params)

    model = Model(MAX_NPARAMS)
    opt = torch.optim.Adam(model.parameters(), lr=0.1)
    for _step in range(STEPS):
        opt.zero_grad()
        loss = torch.mean((model(x) - y) ** 2)
        loss.backward()
        opt.step()

    final = float(loss.detach())
    if not np.isfinite(final):
        return None
    return {
        'score': -final,
        'params': [float(v) for v in model.params.detach().numpy()],
    }


@equation.evolve
def equation(x, params):
    return params[0]*x
'''


# ---------------------------------------------------------------- the artifacts

class TestWhatBestJsonRecords:
    """Which door scored the run has to be readable off the result."""

    def _run(self, tmp_path, spec: str, run_id: str, *args: str) -> dict:
        (tmp_path / "spec.txt").write_text(spec)
        _write_table(tmp_path / "a.csv", 2.0, -0.5, seed=0)
        (tmp_path / "body.py").write_text(_BODY)
        _out(runner.invoke(llmsr_app, [
            "init", "--spec", str(tmp_path / "spec.txt"),
            "--data", str(tmp_path / "a.csv"), "--metric", "mse",
            "--run-id", run_id, *args,
        ]))
        run_dir = Path(".wheeler/llmsr/runs") / run_id
        body = tmp_path / "cand.py"
        body.write_text(_BODY)
        _out(runner.invoke(llmsr_app, [
            "submit", "--run", str(run_dir), "--body-file", str(body),
            "--island-id", "0", "--version-generated", "0",
        ]))
        _out(runner.invoke(llmsr_app, ["best", "--run", str(run_dir)]))
        return json.loads((run_dir / "best.json").read_text())

    def test_the_door_is_named_in_the_optimizer_block(self, tmp_path):
        best = self._run(tmp_path, _DICT_SPEC, "best-spec", "--use-spec-evaluate")

        assert best["status"] == "completed"
        block = best["optimizer"]
        assert block["scored_by"] == spec_eval_mod.SPEC_EVALUATE
        assert block["used"] == spec_eval_mod.SPEC_EVALUATE
        # None of the run's fit knobs touched this number, so none is credited.
        assert block["restarts"] is None and block["seed"] is None
        # The declared choice is still visible, just not credited.
        assert block["declared_optimizer"] == "auto"
        assert best["params"] == pytest.approx([2.0, -0.5, 0.0], abs=1e-3)

    def test_a_default_run_gains_no_new_keys(self, tmp_path):
        """The block a reader of a default run has always seen, unchanged."""
        best = self._run(tmp_path, _DICT_SPEC, "best-default")

        assert set(best["optimizer"]) == {"requested", "used", "restarts", "seed"}

    def test_a_winner_with_no_constants_refuses_to_emit_a_runner(self, tmp_path):
        """Upstream's bare float returns no constants, so there is nothing to run.

        Writing ``FITTED_PARAMS = []`` and a ``__main__`` that calls the equation
        with an empty array would hand the scientist an IndexError explaining
        nothing. Same rule as the multi-dataset footer: no answer beats a wrong
        one, and it exits non-zero so it cannot read as success.
        """
        best = self._run(tmp_path, _UPSTREAM_SPEC, "best-bare", "--use-spec-evaluate")

        assert best["params"] == []
        # And nothing downstream invents a number out of the missing constants:
        # held-out scoring needs a theta to apply, and there is none.
        assert best["metrics"] == {}
        assert best["metrics_refit"] == {}
        program = best["program"]
        assert "FITTED_PARAMS = None" in program
        assert "FITTED_PARAMS = []" not in program

        script = tmp_path / "bare.py"
        script.write_text(program)
        import subprocess
        import sys

        proc = subprocess.run(
            [sys.executable, str(script)], capture_output=True, text=True
        )
        assert proc.returncode != 0
        assert "no fitted constants" in proc.stderr

    def test_the_score_keys_still_come_from_the_run(self, tmp_path):
        """Not from the spec, under either door. The buffer clusters on them."""
        best = self._run(tmp_path, _DICT_SPEC, "best-keys", "--use-spec-evaluate")
        meta = json.loads(
            Path(".wheeler/llmsr/runs/best-keys/meta.json").read_text()
        )
        assert meta["score_key_scheme"] == data_mod.SCHEME_GROUP
        subs = [
            json.loads(line)
            for line in Path(
                ".wheeler/llmsr/runs/best-keys/submissions.jsonl"
            ).read_text().splitlines() if line.strip()
        ]
        assert all(set(s["per_group"]) == {"data"} for s in subs if s["valid"])
        assert best["metric"] == "mse"
