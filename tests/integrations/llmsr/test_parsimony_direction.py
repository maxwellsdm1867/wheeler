"""``--select parsimony`` must implement Occam in BOTH metric directions.

The comparability band ("among candidates that fit comparably well, take the
simplest") is computed on ``-score``, and ``score`` is the maximize-me buffer
score ``metric.score_from_value`` produces. For a metric declaring
``lower_is_better=False`` that quantity is NEGATIVE, and multiplying a negative
number by the band factor moves the threshold TOWARD the best instead of away
from it. That does not weaken Occam, it inverts it.

Measured through the CLI before the fix, with a registered R2 metric and two
candidates, R2 0.99 at complexity 1 against R2 0.995 at complexity 4:

    best_err  = -0.994999999999999
    threshold = -0.994999999998999      (band factor 10.0, times a negative)
    admitted    1 of 2, and the admitted one was the COMPLEX form

so ``best --select parsimony`` wrote the fit-ranked answer into ``best.json``
while recording ``"mode": "parsimony"`` beside it. The lower-is-better control on
the SAME table and the SAME two forms at the same relative gap (1 - R2 of 0.01
against 0.005) admitted 2 of 2 and picked the simple form.

That control is why 439 green tests could not see this. ``lower_is_better=False``
appears once in this directory, in ``test_held_out_scoring.py`` for ``ood``
ranking, so the parsimony band had no coverage in that direction at all. Every
test below therefore names its metric's direction and asserts both of them.

No live model and no Neo4j: the directory ``conftest.py`` gives every test a
scratch cwd and restores the process-wide metric registry.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.llmsr.selection import (
    _PARSIMONY_TOL,
    _comparability_threshold,
    _equation_complexity,
    _select_winner,
)

runner = CliRunner()


# ------------------------------------------------------------------- fixtures

# One law, two forms for it. The richer one spans a component the simple one
# cannot reach, so it always fits at least as well: exactly the tension parsimony
# exists to resolve.
SIMPLE_BODY = "    return params[0]*x\n"
RICHER_BODY = "    return params[0]*x + params[1]*x**3\n"


def _r2(pred, target) -> float:
    """Coefficient of determination. 1.0 is perfect, so HIGHER is better."""
    yp = np.asarray(pred, dtype=float).reshape(-1)
    yt = np.asarray(target, dtype=float).reshape(-1)
    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - yt.mean()) ** 2))
    return 1.0 - ss_res / ss_tot


def _one_minus_r2(pred, target) -> float:
    """The same quantity, stated as an error, so LOWER is better.

    The control metric throughout: 1 - R2 of 0.01 against 0.005 is R2 0.99
    against 0.995, the identical relative gap read from the other side.
    """
    return 1.0 - _r2(pred, target)


def _register(key: str, *, lower_is_better: bool, report) -> metrics_mod.Metric:
    """Register a scientist-style metric. ``loss`` is always minimize-me."""
    return metrics_mod.register_metric(metrics_mod.Metric(
        key=key, label=key, data_shape=metrics_mod.REGRESSION,
        lower_is_better=lower_is_better,
        loss=report if lower_is_better else (lambda p, t: -report(p, t)),
        report=report,
    ))


def _cand(body: str, value: float, metric: metrics_mod.Metric) -> dict:
    """One entry of the ``valid`` list ``best`` selects over.

    ``score`` is derived through ``metric.score_from_value``, which is what
    ``fit.py`` stores on every submission, because the SIGN of that number is the
    whole subject of this file.
    """
    return {
        "body": body,
        "program": "",
        "params": [],
        "value": value,
        "score": metric.score_from_value(value),
    }


def _meta(metric_key: str, where: str = "no_ood") -> dict:
    """A run whose training file has no sibling ``test_ood.csv``.

    ``_candidate_ood`` checks for that sibling before anything else and returns
    None when it is absent, so selection here rests on the training scores alone,
    which is what the parsimony band reads.
    """
    Path(where).mkdir(exist_ok=True)
    return {
        "data_path": str((Path(where) / "train.csv").resolve()),
        "function_to_evolve": "equation",
        "metric": metric_key,
        "group_by": "",
    }


# =========================================================================
# 1. The band itself: one rule, stated so that it holds in both directions
# =========================================================================

class TestTheBandIsOneRuleInBothDirections:
    """A candidate may be worse than the best by up to ``(TOL - 1)`` times the
    MAGNITUDE of the best. For a nonnegative error that is the historic
    ``best_err * TOL``; for a negative one it is the mirror of it, never the
    product, which points the wrong way."""

    @pytest.mark.parametrize("best_err", [0.0, 1e-9, 0.005, 0.01, 1.0, 42.0])
    def test_a_nonnegative_best_keeps_the_historic_threshold(self, best_err):
        """MSE / NMSE runs keep their threshold bit for bit, not just to approx.

        ``best_err + 9 * best_err`` is a different float from ``best_err * 10``
        for some inputs (0.1 gives 1.0000000000000002 against 1.0), and a
        candidate sitting on the band edge would change side. So the nonnegative
        arm must compute the product, and this asserts equality rather than
        closeness.
        """
        assert _comparability_threshold(best_err) == max(
            best_err * _PARSIMONY_TOL, best_err + 1e-12
        )

    def test_a_negative_best_widens_away_from_the_best_not_toward_it(self):
        """The measured defect, in one line of arithmetic.

        With R2 as the metric, the best candidate's pseudo-error was
        -0.994999999999999. The old expression returned -0.994999999998999, which
        is ABOVE the best by one epsilon and below every other candidate, so the
        band held the best alone.
        """
        best_err = -0.994999999999999
        assert best_err * _PARSIMONY_TOL < best_err, (
            "the premise: multiplying a negative best by the band factor moves "
            "the threshold to the wrong side of it"
        )
        threshold = _comparability_threshold(best_err)
        assert threshold == pytest.approx(7.96, abs=1e-9)
        # The R2 0.99 candidate's pseudo-error. It is 0.005 of R2 off the best, so
        # it fits comparably well by any reading, and the old threshold excluded it.
        near_tie_err = -0.99
        assert near_tie_err <= threshold
        assert not near_tie_err <= best_err * _PARSIMONY_TOL

    @pytest.mark.parametrize("magnitude", [0.005, 0.995, 3.0])
    def test_the_slack_is_the_same_relative_width_either_way(self, magnitude):
        """One rule: the band's width is ``(TOL - 1) * |best|`` on both sides."""
        expected = (_PARSIMONY_TOL - 1.0) * magnitude
        assert _comparability_threshold(magnitude) - magnitude == pytest.approx(expected)
        assert _comparability_threshold(-magnitude) - -magnitude == pytest.approx(expected)

    @pytest.mark.parametrize(
        "best_err", [-1e6, -0.995, -1e-12, 0.0, 1e-12, 0.005, 1e6]
    )
    def test_the_best_candidate_is_always_inside_its_own_band(self, best_err):
        """A band that excludes the best is what the inversion produced, and it is
        never right: the best fit is by definition comparable with itself."""
        assert _comparability_threshold(best_err) > best_err


# =========================================================================
# 2. Selection: the simpler form wins whichever way the metric points
# =========================================================================

class TestParsimonyPrefersTheSimplerForm:
    def test_a_higher_is_better_metric_admits_the_near_tie(self):
        """The reproduction, at selection level: R2 0.99 / complexity 1 against
        R2 0.995 / complexity 4. Before the fix the band admitted 1 of 2 and the
        winner was the RICHER form, which is the fit-ranked answer."""
        r2 = _register("r2-hib", lower_is_better=False, report=_r2)
        assert r2.lower_is_better is False
        valid = [_cand(SIMPLE_BODY, 0.99, r2), _cand(RICHER_BODY, 0.995, r2)]
        assert _equation_complexity(SIMPLE_BODY) == 1
        assert _equation_complexity(RICHER_BODY) == 4

        winner = _select_winner([dict(c) for c in valid], _meta("r2-hib"), "parsimony")

        assert winner["body"] == SIMPLE_BODY
        assert winner["value"] == 0.99  # the WORSE fit, which is the point
        # `fit` mode is the control on the same candidates: it must still take the
        # better fit, or this test would pass for the wrong reason.
        assert _select_winner(
            [dict(c) for c in valid], _meta("r2-hib"), "fit"
        )["body"] == RICHER_BODY

    def test_the_lower_is_better_control_at_the_same_relative_gap(self):
        """1 - R2 of 0.01 against 0.005: the same two candidates, the same gap,
        read from the other side. This direction was always correct, and it is
        asserted here so a future change cannot fix one side by breaking it."""
        err = _register("omr2-lib", lower_is_better=True, report=_one_minus_r2)
        valid = [_cand(SIMPLE_BODY, 0.01, err), _cand(RICHER_BODY, 0.005, err)]

        winner = _select_winner([dict(c) for c in valid], _meta("omr2-lib"), "parsimony")

        assert winner["body"] == SIMPLE_BODY
        assert winner["value"] == 0.01

    def test_a_negative_valued_lower_is_better_metric_inverts_the_same_way(self):
        """Why the fix branches on the SIGN and not on ``lower_is_better``.

        A lower-is-better metric whose value goes negative (a log-likelihood
        shaped loss, a negated score) produces a negative pseudo-error too, and
        the old product inverted for it identically, with nothing about its
        declaration to warn anyone.
        """
        neg = _register(
            "negscore-lib", lower_is_better=True, report=lambda p, t: -_r2(p, t)
        )
        valid = [_cand(SIMPLE_BODY, -0.99, neg), _cand(RICHER_BODY, -0.995, neg)]
        assert min(-c["score"] for c in valid) < 0.0  # the negative arm is taken

        winner = _select_winner([dict(c) for c in valid], _meta("negscore-lib"), "parsimony")

        assert winner["body"] == SIMPLE_BODY

    # (lower_is_better, the richer form's value, a simple form INSIDE the band,
    #  a simple form OUTSIDE it). The edges are the band arithmetic: for R2 0.995
    #  the widened threshold is a pseudo-error of 7.96, so R2 -7.0 is comparable
    #  and R2 -9.0 is not; for an error of 0.005 the threshold is 0.05.
    BAND_EDGES = (
        pytest.param(False, 0.995, -7.0, -9.0, id="higher-is-better"),
        pytest.param(True, 0.005, 0.04, 0.06, id="lower-is-better"),
    )

    @pytest.mark.parametrize("lower_is_better,richer,inside,outside", BAND_EDGES)
    def test_a_form_that_does_not_fit_comparably_is_still_excluded(
        self, lower_is_better, richer, inside, outside
    ):
        """The band must still DISCRIMINATE in both directions.

        A fix that admitted everything would pass every test above while turning
        parsimony into "always take the simplest form", which answers a different
        question: Occam applies among candidates that fit comparably, and a form
        that fits far worse is not a rival explanation.
        """
        key = f"edge-{'lib' if lower_is_better else 'hib'}"
        metric = _register(
            key, lower_is_better=lower_is_better,
            report=_one_minus_r2 if lower_is_better else _r2,
        )
        meta = _meta(key)

        near = [_cand(SIMPLE_BODY, inside, metric), _cand(RICHER_BODY, richer, metric)]
        far = [_cand(SIMPLE_BODY, outside, metric), _cand(RICHER_BODY, richer, metric)]

        assert _select_winner(near, meta, "parsimony")["body"] == SIMPLE_BODY
        assert _select_winner(far, meta, "parsimony")["body"] == RICHER_BODY


# =========================================================================
# 3. The neighbourhood: the other two modes must not assume a direction either
# =========================================================================

class TestTheOtherModesDoNotAssumeADirection:
    """``fit`` and the no-OOD fallback both rank on ``score``, which is maximize-me
    by construction, so both are already direction-free. Confirmed by execution
    rather than by reading, because that is how the parsimony band read correct
    too. ``ood`` ranking through ``metric.score_from_value`` is covered from the
    metric side by ``test_held_out_scoring.py::TestOodRanksOnTheRunsOwnMetric``.
    """

    @pytest.mark.parametrize(
        "lower_is_better,better,worse",
        [
            pytest.param(False, 0.995, 0.99, id="higher-is-better"),
            pytest.param(True, 0.005, 0.01, id="lower-is-better"),
        ],
    )
    def test_fit_mode_takes_the_better_fit_whichever_direction(
        self, lower_is_better, better, worse
    ):
        key = f"fit-{'lib' if lower_is_better else 'hib'}"
        metric = _register(
            key, lower_is_better=lower_is_better,
            report=_one_minus_r2 if lower_is_better else _r2,
        )
        valid = [_cand(SIMPLE_BODY, worse, metric), _cand(RICHER_BODY, better, metric)]

        winner = _select_winner(valid, _meta(key), "fit")

        assert winner["value"] == better

    def test_ood_mode_falls_back_to_the_better_fit_with_no_ood_split(self):
        """With no ``test_ood.csv`` there is nothing to rank on, and the fallback
        is `fit`. It must not hand back the worse fit for a higher-is-better
        metric, which a `min` over the raw value would."""
        r2 = _register("ood-fallback-hib", lower_is_better=False, report=_r2)
        valid = [_cand(SIMPLE_BODY, 0.99, r2), _cand(RICHER_BODY, 0.995, r2)]

        winner = _select_winner(valid, _meta("ood-fallback-hib"), "ood")

        assert winner["value"] == 0.995


# =========================================================================
# 4. End to end: the answer a scientist actually reads is in best.json
# =========================================================================

SPEC = '''"""occam probe"""
import numpy as np

MAX_NPARAMS = 3


@evaluate.run
def evaluate(data: dict):
    return 0.0


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''

# The metric module a scientist writes, in the place the convention says to write
# it. Registering through this path rather than in-process is what proves the
# whole CLI walk resolves a higher-is-better metric.
METRICS_MODULE = '''
import numpy as np
from wheeler.integrations.llmsr.metrics import REGRESSION, Metric, register_metric


def _r2(pred, target):
    yp = np.asarray(pred, dtype=float).reshape(-1)
    yt = np.asarray(target, dtype=float).reshape(-1)
    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - yt.mean()) ** 2))
    return 1.0 - ss_res / ss_tot


register_metric(Metric(key="r2", label="coefficient of determination",
    data_shape=REGRESSION, lower_is_better=False,
    loss=lambda p, t: -_r2(p, t), report=_r2))

register_metric(Metric(key="one-minus-r2", label="1 - R2",
    data_shape=REGRESSION, lower_is_better=True,
    loss=lambda p, t: 1.0 - _r2(p, t), report=lambda p, t: 1.0 - _r2(p, t)))
'''


def _write_table(path: str = "train.csv") -> None:
    """A table on which the two forms score R2 0.99 and 0.995 by construction.

    ``y = 3x + a*u + b*v``, where ``u`` is the cubic component orthogonalized
    against ``x`` (reachable by the richer form, not by the simple one) and ``v``
    a wiggle neither form can reach. So the simple form's residual variance is
    ``a**2 + b**2`` and the richer form's is ``b**2``, and setting both to 0.5% of
    var(y) fixes R2 at 0.99 and 0.995: the audited configuration, not a number
    that happened to come out of a fit.
    """
    x = np.linspace(-3.0, 3.0, 400)
    x = x - x.mean()

    def unit_orth(vec: np.ndarray, against: list[np.ndarray]) -> np.ndarray:
        for w in against:
            vec = vec - (vec @ w) / (w @ w) * w
        vec = vec - vec.mean()
        return vec / vec.std()

    u = unit_orth(x ** 3, [x])
    v = unit_orth(np.sin(7.0 * x), [x, u])
    var_y = float((3.0 * x).var()) / 0.99  # var_s + a^2 + b^2, with the rest 1%
    amp = float(np.sqrt(0.005 * var_y))
    y = 3.0 * x + amp * u + amp * v
    Path(path).write_text(
        "x,y\n" + "\n".join(f"{xi:.17g},{yi:.17g}" for xi, yi in zip(x, y)) + "\n"
    )


def _out(result) -> dict:
    assert result.exit_code == 0, result.output + str(result.exception)
    return json.loads(result.output.strip().splitlines()[-1])


class TestTheCliRunHonoursOccam:
    """The band is reachable only through ``best --select parsimony``, and that is
    where the audit found it, so this drives the verb rather than the function."""

    def _walk(self, metric: str, run_id: str) -> dict:
        run_dir = Path(".wheeler/llmsr/runs") / run_id
        _out(runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", "train.csv",
            "--metric", metric, "--run-id", run_id,
        ]))
        # The seed is the spec's own simple form; this adds the richer one.
        _out(runner.invoke(llmsr_app, [
            "submit", "--run", str(run_dir), "--body-file", "richer_body.py",
            "--island-id", "0", "--version-generated", "0",
        ]))
        echoed = _out(runner.invoke(llmsr_app, [
            "best", "--run", str(run_dir), "--select", "parsimony",
        ]))
        return {
            "echoed": echoed,
            "best": json.loads((run_dir / "best.json").read_text()),
            "submissions": [
                json.loads(line)
                for line in (run_dir / "submissions.jsonl").read_text().splitlines()
                if line.strip()
            ],
        }

    @pytest.mark.parametrize(
        "metric,simple_value,richer_value",
        [
            pytest.param("r2", 0.99, 0.995, id="higher-is-better"),
            pytest.param("one-minus-r2", 0.01, 0.005, id="lower-is-better"),
        ],
    )
    def test_parsimony_writes_the_simpler_form_into_best_json(
        self, metric, simple_value, richer_value
    ):
        Path(".wheeler/llmsr").mkdir(parents=True, exist_ok=True)
        Path(".wheeler/llmsr/metrics.py").write_text(METRICS_MODULE)
        Path("spec.txt").write_text(SPEC)
        Path("richer_body.py").write_text(RICHER_BODY)
        _write_table()

        walk = self._walk(metric, f"occam-{metric}")

        # 1. the run really is the audited configuration: two candidates, the
        #    richer one fitting better, at the same relative gap either direction
        values = [s["value"] for s in walk["submissions"] if s["valid"]]
        assert len(values) == 2
        assert values[0] == pytest.approx(simple_value, abs=1e-4)
        assert values[1] == pytest.approx(richer_value, abs=1e-4)

        # 2. and Occam decided it: the simpler form, not the better fit
        best = walk["best"]
        assert best["equation"].strip() == SIMPLE_BODY.strip()
        assert best["selection"] == {
            "mode": "parsimony",
            "complexity": 1,
            "candidates": 2,
            "ranked_on": f"train {metric}",
        }
        assert walk["echoed"]["value"] == pytest.approx(simple_value, abs=1e-4)
