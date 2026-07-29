# LLM-SR: the general Objective formulation

Status: design, partially implemented (slice 1).
Supersedes the metric contract shipped in #96, #97, #98 by generalizing it. Nothing here breaks
those; each is the degenerate case of what follows.

## The problem

Symbolic regression looks for a FUNCTIONAL FORM. The constants are usually a nuisance. Today the
fit path conflates the two:

```
score = m( f(X; θ*), y )          θ* = argmin_θ  l( f(X;θ), y )
```

One pooled dataset, one θ, one scalar. If the same law governs 40 cells with 40 different constant
sets, this scores the form against a single compromise θ and charges the FORM for a mismatch that
belongs to the PARAMETERS. A correct law loses to a wrong-but-flexible one.

What is actually wanted:

```
score = ⟨ m( f(X_i; θ*_i), y_i ) ⟩_i      θ*_i = argmin_θ  l( f(X_i;θ), y_i )
```

Each group i (cell, trial, subject, condition) refits its OWN constants under the SAME form. The
form is then judged on the vector of per-group results. This is profile likelihood: the per-group
constants are nuisance parameters profiled out, and what remains measures only the form.

## What shipped in #96 to #98, and what it does not do

Shipped: an arbitrary callable `(y_pred, y_true) -> float` registered from the scientist's own
module, `data_shape` dispatch so a candidate may be a simulator with variable-length output, and
`guard` for hard accept/reject separate from the scalar.

Not shipped, and not expressible: per-group refit, a score vector, any scorer that needs to refit
or rescale as part of computing the error, per-point weights, or parameter-dependent penalties.
The scorer signature sees neither `X` nor `θ` (though `Constraint.check` does see `θ`, an
asymmetry with no justification), so χ² with per-point σᵢ cannot be written. The only workaround
is closing over module-level data, which welds a metric to one dataset.

## The formulation

Five facets, each a plug-in point, defaults reproducing current behavior exactly:

```
partition:  Data              -> [Group]     # who gets their own θ   (default: one group)
bind:       (equation, Group) -> CallPlan    # how to call the candidate (today: a closed enum)
score:      (form, group, fit)-> float       # per-group score, MAY refit or rescale internally
constrain:  (pred, ctx)       -> bool        # hard gates, per group
optimize:   (loss_fn, ctx)    -> θ           # today: hardcoded BFGS
```

### The control inversion

The load-bearing change. Today the pipeline fits, then hands the metric a finished prediction, so
a metric can never refit and therefore can never profile out a nuisance parameter. Instead the
scorer receives the FORM and the GROUP plus a refit primitive it may call:

```python
def shape_error(form, group, fit):
    """Score this cell on FORM only: its own constants and its own gain are nuisances."""
    θ = fit(form, group, loss=lambda yp, yt: np.mean((yp - yt) ** 2))
    yp = form(*group.cols, θ)
    A = np.vstack([yp, np.ones_like(yp)]).T          # nuisance gain + offset,
    (a, b), *_ = np.linalg.lstsq(A, group.y, rcond=None)   # profiled out, not fitted
    return float(np.mean((a * yp + b - group.y) ** 2) / np.var(group.y))

register_objective(Objective(
    key="shape_per_cell",
    group_by="cell_id",
    score=shape_error,
    lower_is_better=True,
))
```

Every slot accepts a callable or a bare constant, with a constant promoted to `lambda *_: c`, so
thresholds and fixed weights read naturally.

### The score vector, and why no vendor fork is needed

The vendored FunSearch buffer is already vector-native:

```python
register_program(program, island_id, scores_per_test: ScoresPerTest)   # a DICT
_reduce_score(spt)  = mean over tests                       # island ranking signal
_get_signature(spt) = tuple(spt[k] for k in sorted(spt))    # CLUSTER KEY within an island
```

Wheeler calls it with `{"data": result.score}`, a single key, which is where the vector is
destroyed. Passing `{group_id: score_i}` instead recovers upstream's design at no cost:
`_reduce_score` supplies the island ranking for free, and `_get_signature` clusters forms by their
per-group profile. `vendor/` stays unforked, which matters given `d0b05b7` frames it as a plug-in
for LLM-SR rather than our code.

The distinction to keep straight: the island model needs SOME ordering to build prompts. That is a
property of FunSearch's algorithm, not of the science. The buffer is a search heuristic; the
winner is selected by Wheeler in `best` from `submissions.jsonl`, which stores the raw vector. So
the buffer may be fed a coarse signal without costing final-selection precision.

### Known caveat: signature degeneracy

`Signature` is a dict key. Raw per-group floats are all distinct, so every program lands in its own
cluster and the diversity mechanism does nothing. Note this is ALREADY true today: `{"data": score}`
gives `(score,)`, unique per program. Passing the raw vector is therefore no worse, but it does not
fix it either.

The fix is a declared `cluster_by` quantizer, deliberately deferred to slice 2 because the
scientifically right quantization is a per-group pass/fail at a threshold, which makes the
signature read "the set of groups this form explains" and preserves exactly the diversity axis
worth preserving. That threshold is the scientist's call, not a default worth inventing.

## Two consequences

**The optimizer becomes load-bearing.** `fit.py` hardcodes multi-start BFGS (`_N_RESTARTS = 6`).
BFGS uses a numerical gradient, identically zero on a piecewise-constant objective, so it
terminates at `x0`. Measured on a representative event-count objective:

```
BFGS starts that MOVED off x0: 0/13
best value found: 1.0        (0.0 is a perfect fit)
Nelder-Mead, same starts:    0.0     exact
```

Spike-distance and event-count losses are piecewise constant in θ, so the `spike_train` shape
opened by #97 is currently fitted by an optimizer that cannot fit it: it degrades to best-of-7
random search. Per-group refit multiplies this by the group count, and a scorer that refits
internally multiplies it again. `optimize` must become declarable with a gradient-free default for
non-smooth objectives.

**Failed groups need a policy.** A form that nails 38 of 40 and fails 2, versus one mediocre on all
40: the NaN policy picks the winner. That is a scientific call, not a default. It is also where the
#98 hard constraints land, since a guard may now fail on a subset of groups.

## Slices

1. **`--group-by` with per-group θ and the raw vector into `scores_per_test`.** No vendor change.
   Backward compatible: no `--group-by` means one group, byte-identical to today.
2. **The `score(form, group, fit)` inversion** with the refit primitive, plus `cluster_by`.
3. **Declarable `optimize`**, gradient-free default for non-smooth objectives, groups fanned out in
   parallel to recover the cost.
