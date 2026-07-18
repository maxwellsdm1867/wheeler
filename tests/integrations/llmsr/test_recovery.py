"""Recovery tests: fabricate data from a KNOWN law and confirm the pipeline
recovers it. Validates the fit + metric numerics (the "is the number right"
check) and the out-of-domain generalization protocol, deterministically and with
no model call.

Ground truth: dv = 2*x - 0.5*v + 0.3*x^3 (a Duffing-like oscillator term). It is
linear in the free constants, so an exact-form fit is exact least squares:
recovered constants match ground truth and NMSE collapses to ~0, mirroring the
paper's near-zero in-domain NMSE for the oscillator benchmarks.
"""

from __future__ import annotations

import numpy as np
import pytest

from wheeler.integrations.llmsr import fit, metrics

_TRUE = (2.0, -0.5, 0.3)
TRUE_FORM = (
    "import numpy as np\n"
    "def equation(x, v, params):\n"
    "    return params[0]*x + params[1]*v + params[2]*x**3\n"
)
WRONG_FORM = (  # missing the cubic term
    "import numpy as np\n"
    "def equation(x, v, params):\n"
    "    return params[0]*x + params[1]*v\n"
)


def _data(n=400, lo=-2.0, hi=2.0, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.uniform(lo, hi, n)
    v = rng.uniform(lo, hi, n)
    y = _TRUE[0] * x + _TRUE[1] * v + _TRUE[2] * x**3  # noiseless
    return np.column_stack([x, v]), y


def test_recovers_constants_and_zero_error():
    X, y = _data()
    r = fit.evaluate_body(TRUE_FORM, "equation", X, y, metrics.get_metric("mse"), max_nparams=3)
    assert r.valid
    assert r.value < 1e-6  # near-exact recovery of a noiseless law
    assert r.params[0] == pytest.approx(_TRUE[0], abs=1e-3)
    assert r.params[1] == pytest.approx(_TRUE[1], abs=1e-3)
    assert r.params[2] == pytest.approx(_TRUE[2], abs=1e-3)


def test_nmse_near_zero_on_recovery():
    X, y = _data()
    r = fit.evaluate_body(TRUE_FORM, "equation", X, y, metrics.get_metric("nmse"), max_nparams=3)
    assert r.valid
    assert r.value < 1e-6  # paper's NMSE ~ 0 when the equation is recovered


def test_metric_discriminates_wrong_form():
    X, y = _data()
    mse = metrics.get_metric("mse")
    good = fit.evaluate_body(TRUE_FORM, "equation", X, y, mse, max_nparams=3)
    bad = fit.evaluate_body(WRONG_FORM, "equation", X, y, mse, max_nparams=3)
    assert good.value < 1e-6
    assert bad.value > 0.1  # dropping the cubic term costs a lot
    assert good.score > bad.score  # the island model keeps the true form


def test_recovered_form_generalizes_out_of_domain():
    """Fit on [-2, 2], apply the fitted constants to a DISJOINT [5, 8] range.

    The exact form generalizes (NMSE ~ 0), exercising evaluate_fixed and the
    train-fit / test-apply OOD protocol the paper reports.
    """
    X, y = _data()
    fitted = fit.evaluate_body(TRUE_FORM, "equation", X, y, metrics.get_metric("mse"), max_nparams=3)
    Xo, yo = _data(n=200, lo=5.0, hi=8.0, seed=1)
    nmse_ood = fit.evaluate_fixed(
        TRUE_FORM, "equation", Xo, yo, fitted.params, metrics.get_metric("nmse")
    )
    assert nmse_ood is not None
    assert nmse_ood < 1e-6
