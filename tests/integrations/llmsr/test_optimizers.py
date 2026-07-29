"""The optimizer registry, its escalation default, and the parity it must keep.

Two claims, and they pull in opposite directions, which is why both are tested
here rather than trusted.

The first is that nothing moved. Replacing a hardcoded
``opt.minimize(loss, x0, method="BFGS")`` with a declarable registry is only
allowed if, WHERE BFGS MOVED, every number is exactly what it was. That claim is
gated by ``parity_bfgs.py`` against hex-float constants captured on ``main``, run
from here so it fires on every test run.

The second is that something DID move, deliberately. BFGS steers by a numerical
gradient, and on a piecewise-constant objective that gradient is identically
zero: no start ever leaves its init and the reported best is merely whichever
init sat lowest. Under ``--group-by`` a single such group invalidates the whole
candidate, so a CORRECT form gets rejected for an optimizer's blindness. The
escalation tests below pin that down on an objective where BFGS provably does not
move: the fitted constants come back bit-identical to an init.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr import optimizers as optimizers_mod
from wheeler.integrations.llmsr.cli import llmsr_app

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
SPEC = FIX / "spec_bactgrow.txt"
DATA = FIX / "train_small.csv"

runner = CliRunner()


def _parity_module():
    """Load the checked-in parity gate as a module (it is a script, not a test)."""
    spec = importlib.util.spec_from_file_location(
        "wheeler_llmsr_parity_bfgs", HERE / "parity_bfgs.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# An objective that is piecewise constant in the free parameter: the prediction
# only ever changes at a multiple of 0.001, so a numerical gradient taken at the
# default step (~1.5e-8) is identically zero everywhere. BFGS is blind to it. The
# form is otherwise trivially correct, and the true constant (3.0) is exactly
# representable on the grid, so a working optimizer reaches a loss of exactly 0.
QUANTIZED = (
    "import numpy as np\n"
    "def equation(x1, params):\n"
    "    return np.round(params[0] * 1000.0) / 1000.0 * x1\n"
)

# The same FORM meeting a quantized objective in one group and a smooth one in
# the other, which is the per-group case the escalation exists for: whether an
# optimizer can see the objective is a property of THAT group's data.
PER_GROUP = (
    "import numpy as np\n"
    "def equation(x1, params):\n"
    "    if x1.size % 2 == 0:\n"
    "        return np.round(params[0] * 1000.0) / 1000.0 * x1\n"
    "    return params[0] * x1\n"
)

SMOOTH = (
    "import numpy as np\n"
    "def equation(x1, params):\n"
    "    return params[0] * np.exp(params[1] * x1) + params[2]\n"
)


def _quantized_group(n: int = 40, slope: float = 3.0):
    x = np.linspace(-2.0, 2.0, n)
    return x.reshape(-1, 1), slope * x


def _inits(max_nparams: int = 1, restarts: int = fit_mod.DEFAULT_RESTARTS,
           seed: int = fit_mod.DEFAULT_SEED) -> list[np.ndarray]:
    """The starts the fit draws, by the recipe it documents.

    Reproduced rather than imported because it is the evidence: a fitted constant
    that is bit-identical to one of these is a fit that never moved.
    """
    rng = np.random.default_rng(seed)
    return [np.ones(max_nparams)] + [
        rng.uniform(-12.0, 12.0, max_nparams) for _ in range(restarts)
    ]


def _fit(body: str, groups, optimizer: str, **kw):
    return fit_mod.evaluate_body_grouped(
        body, "equation", groups, metrics_mod.MSE, max_nparams=1,
        optimizer=optimizer, **kw,
    )


# ------------------------------------------------------------------ the parity

class TestBfgsParityWithMain:
    """`--optimizer bfgs` reproduces main's numbers exactly, or this is a bug."""

    def test_every_case_is_bit_for_bit_identical(self):
        failures = _parity_module().check_all()
        assert failures == [], "\n".join(failures)

    def test_the_gate_runs_as_a_script(self):
        """It is checked in to be RUNNABLE, not only importable from a test."""
        assert _parity_module().main(["parity_bfgs.py", "check"]) == 0


# --------------------------------------------------------------- the escalation

class TestBfgsIsBlindToAPiecewiseConstantObjective:
    """The measurement this whole slice rests on, made a standing test."""

    def test_not_one_start_moves_off_its_init(self):
        result = _fit(QUANTIZED, [("data", *_quantized_group())], "bfgs")
        assert result.valid
        # The fitted constant IS one of the starts, to the bit: BFGS returned
        # every start exactly where it began and the "best" is just the luckiest
        # init. Nothing here is a fit.
        assert [p.hex() for p in result.params] in [
            [float(v).hex() for v in x0] for x0 in _inits()
        ]

    def test_a_correct_form_is_scored_as_a_bad_one(self):
        """Why it matters: the law is exactly right and BFGS reports error."""
        result = _fit(QUANTIZED, [("data", *_quantized_group())], "bfgs")
        assert result.value is not None and result.value > 0.1


class TestAutoEscalates:
    def test_it_escalates_and_beats_plain_bfgs(self):
        groups = [("data", *_quantized_group())]
        bfgs = _fit(QUANTIZED, groups, "bfgs")
        auto = _fit(QUANTIZED, groups, "auto")

        assert auto.valid and bfgs.valid
        assert auto.value is not None and bfgs.value is not None
        # Nelder-Mead lands on the true constant, which sits exactly on the grid.
        assert auto.value == 0.0
        assert auto.value < bfgs.value

    def test_the_optimizer_that_produced_the_number_is_recorded(self):
        auto = _fit(QUANTIZED, [("data", *_quantized_group())], "auto")
        # The CONCRETE optimizer, never the strategy that chose it.
        assert auto.optimizer == "nelder-mead"
        assert auto.optimizer_per_group == {"data": "nelder-mead"}

    def test_it_does_not_escalate_where_bfgs_can_see(self):
        """No movement means no gradient. Movement means leave it alone."""
        x = np.linspace(-1.0, 1.0, 30)
        groups = [("data", x.reshape(-1, 1), 2.0 * np.exp(0.3 * x) - 1.0)]
        forced = fit_mod.evaluate_body_grouped(
            SMOOTH, "equation", groups, metrics_mod.MSE, optimizer="bfgs"
        )
        auto = fit_mod.evaluate_body_grouped(
            SMOOTH, "equation", groups, metrics_mod.MSE, optimizer="auto"
        )
        assert auto.optimizer == "bfgs"
        assert auto.score is not None and forced.score is not None
        assert auto.score.hex() == forced.score.hex()
        assert [p.hex() for p in auto.params] == [p.hex() for p in forced.params]

    def test_escalation_is_decided_per_group(self):
        even, odd = _quantized_group(40, 3.0), _quantized_group(41, -1.5)
        groups = [("quantized", *even), ("smooth", *odd)]
        auto = _fit(PER_GROUP, groups, "auto")
        bfgs = _fit(PER_GROUP, groups, "bfgs")

        assert auto.optimizer_per_group == {
            "quantized": "nelder-mead", "smooth": "bfgs",
        }
        # No single name is true of this candidate, and inventing one would be a
        # claim the fit never made. `optimizer_per_group` is what resolves it.
        assert auto.optimizer == fit_mod.MIXED
        # The group BFGS could see is untouched, to the bit.
        assert (auto.per_group_value["smooth"].hex()
                == bfgs.per_group_value["smooth"].hex())
        assert auto.per_group_value["quantized"] < bfgs.per_group_value["quantized"]

    def test_a_forced_optimizer_never_escalates(self):
        """`--optimizer bfgs` means BFGS, including its blindness. No surprises."""
        result = _fit(QUANTIZED, [("data", *_quantized_group())], "bfgs")
        assert result.optimizer == "bfgs"


class TestMovementIsMeasuredOnUsableStarts:
    """A start that came back NaN did not explore anywhere: it failed.

    Counting it as movement would suppress the escalation in exactly the case
    that needs it most, where the primary optimizer produced nothing at all.
    """

    def test_a_start_that_wandered_to_nan_does_not_pass_for_movement(self):
        optimizers_mod.register_optimizer(optimizers_mod.Optimizer(
            key="nan-walker", label="moves, produces nothing",
            minimize=lambda loss, x0: (np.asarray(x0) + 1.0, float("nan")),
            escalates_to="powell",
        ))
        result = _fit(QUANTIZED, [("data", *_quantized_group())], "nan-walker")
        assert result.optimizer == "powell"
        assert result.value is not None and result.value < 1e-8


class TestForcedOptimizers:
    @pytest.mark.parametrize("key", ["nelder-mead", "powell"])
    def test_a_derivative_free_optimizer_solves_what_bfgs_cannot(self, key):
        result = _fit(QUANTIZED, [("data", *_quantized_group())], key)
        assert result.valid
        assert result.optimizer == key
        assert result.value is not None and result.value < 1e-8

    def test_an_unknown_optimizer_is_named_rather_than_silently_invalidating(self):
        result = _fit(QUANTIZED, [("data", *_quantized_group())], "gradient-descent")
        assert not result.valid
        assert "unknown optimizer" in result.error
        assert "nelder-mead" in result.error  # says what IS valid


# ------------------------------------------------------------------- the knobs

class TestRestartsAndSeedAreReachable:
    """They were unreachable constants: a knob nobody can turn is a knob nobody
    can rule out as the reason a form was rejected."""

    def test_restarts_zero_leaves_only_the_all_ones_init(self):
        result = _fit(QUANTIZED, [("data", *_quantized_group())], "bfgs", restarts=0)
        assert [p.hex() for p in result.params] == [(1.0).hex()]

    def test_more_starts_reach_a_better_init(self):
        groups = [("data", *_quantized_group())]
        one = _fit(QUANTIZED, groups, "bfgs", restarts=0)
        many = _fit(QUANTIZED, groups, "bfgs")
        assert many.value is not None and one.value is not None
        assert many.value < one.value

    def test_the_seed_changes_which_starts_are_drawn(self):
        groups = [("data", *_quantized_group())]
        a = _fit(QUANTIZED, groups, "bfgs", seed=0)
        b = _fit(QUANTIZED, groups, "bfgs", seed=7)
        assert [p.hex() for p in a.params] != [p.hex() for p in b.params]
        # Each result is still exactly one of ITS OWN seed's starts.
        for result, seed in ((a, 0), (b, 7)):
            assert [p.hex() for p in result.params] in [
                [float(v).hex() for v in x0] for x0 in _inits(seed=seed)
            ]

    def test_the_defaults_are_what_the_fit_always_used(self):
        assert (fit_mod.DEFAULT_RESTARTS, fit_mod.DEFAULT_SEED) == (6, 0)

    def test_the_ungrouped_wrapper_forwards_them(self):
        X, y = _quantized_group()
        result = fit_mod.evaluate_body(
            QUANTIZED, "equation", X, y, metrics_mod.MSE,
            max_nparams=1, optimizer="nelder-mead",
        )
        assert result.optimizer == "nelder-mead"
        assert result.value == 0.0


# ---------------------------------------------------------------- the registry

class TestRegistry:
    def test_the_builtins_are_registered(self):
        assert optimizers_mod.available() == ["bfgs", "nelder-mead", "powell"]
        assert optimizers_mod.choices() == ["auto", "bfgs", "nelder-mead", "powell"]

    def test_auto_resolves_to_bfgs_with_nelder_mead_behind_it(self):
        primary, escalation = optimizers_mod.resolve("auto")
        assert primary is optimizers_mod.BFGS
        assert escalation is optimizers_mod.NELDER_MEAD

    def test_a_plain_choice_resolves_to_itself_with_no_fallback(self):
        primary, escalation = optimizers_mod.resolve("BFGS")
        assert primary is optimizers_mod.BFGS
        assert escalation is None

    def test_keys_are_normalized(self):
        assert optimizers_mod.canonical("  Nelder-Mead ") == "nelder-mead"

    def test_an_unknown_key_lists_every_valid_choice(self):
        with pytest.raises(KeyError, match="unknown optimizer"):
            optimizers_mod.get_optimizer("lbfgs")

    def test_builtin_is_not_silently_shadowed(self):
        clone = optimizers_mod.Optimizer(
            key="bfgs", label="not the real bfgs", minimize=optimizers_mod._powell,
        )
        with pytest.raises(ValueError, match="built in"):
            optimizers_mod.register_optimizer(clone)
        assert optimizers_mod.get_optimizer("bfgs") is optimizers_mod.BFGS
        optimizers_mod.register_optimizer(clone, replace=True)
        assert optimizers_mod.get_optimizer("bfgs") is clone

    def test_uncallable_minimize_is_rejected_at_registration(self):
        broken = optimizers_mod.Optimizer(
            key="broken", label="broken", minimize="not a function",
        )
        with pytest.raises(TypeError, match="minimize"):
            optimizers_mod.register_optimizer(broken)
        assert "broken" not in optimizers_mod.available()

    def test_auto_is_reserved(self):
        with pytest.raises(ValueError, match="STRATEGY"):
            optimizers_mod.register_optimizer(optimizers_mod.Optimizer(
                key="auto", label="mine", minimize=optimizers_mod._powell,
            ))

    def test_an_optimizer_cannot_escalate_to_itself(self):
        with pytest.raises(ValueError, match="itself"):
            optimizers_mod.register_optimizer(optimizers_mod.Optimizer(
                key="loop", label="loop", minimize=optimizers_mod._powell,
                escalates_to="loop",
            ))

    def test_escalation_is_one_hop_and_never_a_chain(self):
        """A second failure to move is information, not a licence to keep guessing."""
        optimizers_mod.register_optimizer(optimizers_mod.Optimizer(
            key="stuck", label="never moves", minimize=lambda loss, x0: (x0, loss(x0)),
            escalates_to="also-stuck",
        ))
        optimizers_mod.register_optimizer(optimizers_mod.Optimizer(
            key="also-stuck", label="also never moves",
            minimize=lambda loss, x0: (x0, loss(x0)), escalates_to="powell",
        ))
        primary, escalation = optimizers_mod.resolve("stuck")
        assert (primary.key, escalation.key) == ("stuck", "also-stuck")
        result = _fit(QUANTIZED, [("data", *_quantized_group())], "stuck")
        # It escalated once (to the equally stuck one) and stopped: `powell`,
        # which would have solved this, is never reached.
        assert result.optimizer == "stuck"
        assert result.value is not None and result.value > 0.1


_USER_SOURCE = '''
from wheeler.integrations.llmsr.optimizers import Optimizer, register_optimizer


def brute(loss, x0):
    """A grid over the one constant: crude, and blind to nothing."""
    best = min(((float(c), loss([c])) for c in [i * 0.5 for i in range(-24, 25)]),
               key=lambda pair: pair[1])
    return [best[0]], best[1]


register_optimizer(Optimizer(key="brute", label="grid search", minimize=brute))
'''


class TestUserOptimizerSources:
    def test_a_project_file_optimizer_is_listed_and_runnable(self):
        path = Path(".wheeler/llmsr/optimizers.py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_USER_SOURCE)

        res = runner.invoke(llmsr_app, ["optimizers"])
        assert res.exit_code == 0, res.output
        listing = json.loads(res.output)
        by_key = {o["key"]: o for o in listing["optimizers"]}
        assert by_key["brute"]["builtin"] is False
        assert by_key["bfgs"]["builtin"] is True
        assert listing["errors"] == []
        assert listing["default"] == "auto"
        assert listing["escalation"]["primary"] == "bfgs"
        assert listing["escalation"]["escalates_to"] == "nelder-mead"

        result = _fit(QUANTIZED, [("data", *_quantized_group())], "brute")
        assert result.optimizer == "brute"
        assert result.value == 0.0

    def test_an_env_var_source_is_loaded(self, monkeypatch):
        path = Path("my_optimizers.py").resolve()
        path.write_text(_USER_SOURCE)
        monkeypatch.setenv(optimizers_mod._USER_OPTIMIZERS_ENV, str(path))

        optimizers_mod.load_user_optimizers()
        assert "brute" in optimizers_mod.available()

    def test_a_broken_source_is_reported_not_raised(self):
        path = Path(".wheeler/llmsr/optimizers.py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("raise RuntimeError('boom')\n")

        failures = optimizers_mod.load_user_optimizers()
        assert len(failures) == 1
        assert "boom" in failures[0].error
        # The built-ins survive, so every verb still works.
        assert optimizers_mod.available() == ["bfgs", "nelder-mead", "powell"]


# --------------------------------------------------------------------- the CLI

def _quantized_project(tmp_path: Path) -> None:
    """A runnable project whose seed body is the piecewise-constant law."""
    (tmp_path / "spec.txt").write_text(
        "import numpy as np\n\n"
        "MAX_NPARAMS = 1\n\n"
        "@evaluate.run\n"
        "def evaluate(data):\n"
        "    return 0.0\n\n"
        "@equation.evolve\n"
        "def equation(x1, params):\n"
        "    return np.round(params[0] * 1000.0) / 1000.0 * x1\n"
    )
    x = np.linspace(-2.0, 2.0, 40)
    rows = ["x1,y"] + [f"{v:.17g},{3.0 * v:.17g}" for v in x]
    (tmp_path / "train.csv").write_text("\n".join(rows) + "\n")


class TestCli:
    def test_the_knobs_are_bound_to_the_run(self, tmp_path):
        res = runner.invoke(llmsr_app, [
            "init", "--spec", str(SPEC), "--data", str(DATA), "--metric", "mse",
            "--run-id", "k", "--optimizer", "powell", "--restarts", "2", "--seed", "5",
        ])
        assert res.exit_code == 0, res.output
        meta = json.loads(Path(".wheeler/llmsr/runs/k/meta.json").read_text())
        assert (meta["optimizer"], meta["restarts"], meta["seed"]) == ("powell", 2, 5)
        sub = json.loads(
            Path(".wheeler/llmsr/runs/k/submissions.jsonl").read_text().splitlines()[0]
        )
        assert sub["optimizer"] == "powell"

    def test_the_defaults_are_todays_values(self, tmp_path):
        res = runner.invoke(llmsr_app, [
            "init", "--spec", str(SPEC), "--data", str(DATA), "--metric", "mse",
            "--run-id", "d",
        ])
        assert res.exit_code == 0, res.output
        meta = json.loads(Path(".wheeler/llmsr/runs/d/meta.json").read_text())
        assert meta["optimizer"] == "auto"
        assert meta["restarts"] == fit_mod.DEFAULT_RESTARTS
        assert meta["seed"] == fit_mod.DEFAULT_SEED

    def test_an_unknown_optimizer_fails_at_init_not_per_candidate(self):
        res = runner.invoke(llmsr_app, [
            "init", "--spec", str(SPEC), "--data", str(DATA), "--metric", "mse",
            "--run-id", "bad", "--optimizer", "lbfgs",
        ])
        assert res.exit_code != 0
        assert "unknown optimizer" in res.output
        assert not Path(".wheeler/llmsr/runs/bad").exists()

    def test_negative_restarts_is_rejected(self):
        res = runner.invoke(llmsr_app, [
            "init", "--spec", str(SPEC), "--data", str(DATA), "--metric", "mse",
            "--run-id", "neg", "--restarts", "-1",
        ])
        assert res.exit_code != 0

    def test_best_json_says_which_optimizer_produced_the_winner(self, tmp_path):
        _quantized_project(tmp_path)
        res = runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv", "--metric", "mse",
            "--run-id", "q",
        ])
        assert res.exit_code == 0, res.output
        res = runner.invoke(llmsr_app, ["best", "--run", "q"])
        assert res.exit_code == 0, res.output

        best = json.loads(Path(".wheeler/llmsr/runs/q/best.json").read_text())
        # Requested the strategy, got a concrete answer: the reader never has to
        # guess whether a fallback happened.
        assert best["optimizer"] == {
            "requested": "auto", "used": "nelder-mead",
            "restarts": fit_mod.DEFAULT_RESTARTS, "seed": fit_mod.DEFAULT_SEED,
        }
        assert best["metrics"]["mse_train"] == 0.0

    def test_a_grouped_winner_reports_the_optimizer_per_group(self, tmp_path):
        _quantized_project(tmp_path)
        # Two cells, one of which has an odd row count, so the same form meets a
        # smooth objective there and a quantized one in the other.
        (tmp_path / "spec.txt").write_text(
            "import numpy as np\n\n"
            "MAX_NPARAMS = 1\n\n"
            "@evaluate.run\n"
            "def evaluate(data):\n"
            "    return 0.0\n\n"
            "@equation.evolve\n"
            "def equation(x1, params):\n"
            "    if x1.size % 2 == 0:\n"
            "        return np.round(params[0] * 1000.0) / 1000.0 * x1\n"
            "    return params[0] * x1\n"
        )
        rows = ["cell,x1,y"]
        rows += [f"a,{v:.17g},{3.0 * v:.17g}" for v in np.linspace(-2.0, 2.0, 40)]
        rows += [f"b,{v:.17g},{-1.5 * v:.17g}" for v in np.linspace(-2.0, 2.0, 41)]
        (tmp_path / "train.csv").write_text("\n".join(rows) + "\n")

        assert runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv", "--metric", "mse",
            "--run-id", "g", "--group-by", "cell",
        ]).exit_code == 0
        assert runner.invoke(llmsr_app, ["best", "--run", "g"]).exit_code == 0

        best = json.loads(Path(".wheeler/llmsr/runs/g/best.json").read_text())
        assert best["optimizer"]["used"] == fit_mod.MIXED
        assert best["optimizer_per_group"] == {"a": "nelder-mead", "b": "bfgs"}

    def test_a_run_created_before_the_knobs_existed_still_submits(self, tmp_path):
        """An older meta.json has no optimizer, no restarts, no seed."""
        _quantized_project(tmp_path)
        assert runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv", "--metric", "mse",
            "--run-id", "old",
        ]).exit_code == 0
        path = Path(".wheeler/llmsr/runs/old/meta.json")
        meta = json.loads(path.read_text())
        for key in ("optimizer", "restarts", "seed"):
            meta.pop(key)
        path.write_text(json.dumps(meta))

        (tmp_path / "body.txt").write_text(
            "    return np.round(params[0] * 1000.0) / 1000.0 * x1\n"
        )
        res = runner.invoke(llmsr_app, [
            "submit", "--run", "old", "--body-file", "body.txt",
            "--island-id", "0", "--version-generated", "0",
        ])
        assert res.exit_code == 0, res.output
        assert json.loads(res.output)["optimizer"] == "nelder-mead"
