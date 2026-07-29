# The LLM-SR spec cookbook

A spec is the one thing you have to write before an equation search can start.
Everything else in `wheeler llmsr` is a flag. This is what goes in it, and seven
worked ways of answering the only question a spec really asks: **what does a good
fit mean here?**

Every recipe in this document is a real file under
`wheeler/_data/llmsr/recipes/`, filled against your CSV by
`wheeler llmsr scaffold-spec`, and executed by
`tests/integrations/llmsr/test_recipes.py` against a synthetic table on every test
run. Prose about an `evaluate` body rots; an executed one cannot.

Method attribution: the search is **LLM-SR** (Shojaee et al., ICLR 2025,
arXiv:2404.18400), built on **FunSearch** (Romera-Paredes et al., Nature 2023).
Cite those, not Wheeler. BibTeX is in
`wheeler/integrations/llmsr/vendor/NOTICE.md`.

---

## 1. What a spec is

Four parts, in this order:

```python
"""The problem statement. THIS IS WHAT THE GENERATOR READS."""   # 1

import numpy as np
MAX_NPARAMS = 10                                                 # 2

@evaluate.run
def evaluate(data: dict):                                        # 3
    ...

@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:   # 4
    return params[0] * x
```

1. **The docstring.** The single highest-value thing you can edit. The generator
   proposes forms from it, so "growth rises with substrate and saturates, and
   falls away from an optimum temperature" buys more than any flag on this page.
   Say what the variables mean, what their units are, and roughly how big the
   measurement error is, so the search knows where the noise floor is.
2. **`MAX_NPARAMS`.** The length of `params`. A form may use fewer. It is also
   what `--max-nparams` writes.
3. **`@evaluate.run`.** What a good fit means. Sections 3 to 5 are entirely about
   this function.
4. **`@equation.evolve`.** The skeleton the search mutates. Start dull. A
   skeleton that already encodes your guess is you doing the discovering.

The tabular convention is upstream's: **the last column of the CSV is the target,
the leading columns are the inputs, in order.** A `--group-by` column is removed
from the inputs (it names who the row belongs to, it is not an input to the law).

---

## 2. The two doors: read this before choosing a recipe

There are two places a candidate can be scored, and which one runs is a flag you
set at `init` and can never change afterwards.

| | default | `--use-spec-evaluate` |
|---|---|---|
| who scores | Wheeler's `fit.py` + your `--metric` | the spec's own `evaluate` |
| who owns the loss | the metric registry | the spec |
| who owns the optimizer | `--optimizer` / `--restarts` / `--seed` | the spec |
| constants recoverable | always | only if `evaluate` returns them |
| per-unit refit | yes | yes (one call per unit) |
| can see a third array (per-point sigma) | no | yes |

**By default, your spec's `evaluate` is never called.** Wheeler parses its name
and scores through its own fit seam instead. That substitution is deliberate: it
is what makes the metric pluggable, the constants recoverable for `best.json`,
and the per-group refit possible. It is also why the recipes below still write a
sensible `evaluate` even when the flag is off: the spec stays portable to
upstream LLM-SR unmodified, and turning the flag on then changes who computed the
number, not what the number means.

The door is never sniffed from the spec text. Nothing inspects the body of
`evaluate` to guess whether it looks stock, because a scoring change nobody asked
for is the exact failure this engine exists to remove.

**Rule of thumb.** If the thing you want is a different LOSS and it can be
written as `(y_pred, y_true) -> float`, register a `Metric` instead of reaching
for `--use-spec-evaluate`: you keep the pluggable seam, the constants land in
`best.json`, and the per-group protocol still applies. Take the spec door when
the loss needs something a two-argument scorer cannot see (a per-point sigma, a
nuisance gain), or when the spec has to own the optimizer too.

---

## 3. The flag map

| flag | what it decides |
|---|---|
| `--spec` | the spec file |
| `--data` | a training table. **Repeatable**, and nameable: `--data B=cellB.csv` |
| `--seed-from` | which table shapes the prompt. **This is where the FORM comes from**, not `--data` order and not `data_path` |
| `--score-on` | which tables enter the objective. A table named here **is optimized against**: 40 rounds scored on it makes its error a training number |
| `--group-by` | the column naming who each row belongs to. Each group refits its OWN constants under the same form |
| `--metric` | the objective, from `wheeler llmsr metrics` (open registry: yours count) |
| `--optimizer` | from `wheeler llmsr optimizers`. Default `auto`: BFGS, escalating to Nelder-Mead when no start moved off its init |
| `--restarts` / `--seed` | the multi-start inits, so a form whose constants live far from 1 is not rejected for a fit that never left a flat region |
| `--loader` | how a recording is READ, from `wheeler llmsr loaders` |
| `--use-spec-evaluate` | take the other door (section 2) |

Three listings are computed at call time and are the truthful ones to offer from,
because all three registries are open and a scientist's own entry must be
offerable: `wheeler llmsr metrics`, `wheeler llmsr loaders`,
`wheeler llmsr optimizers`. Recipes are listed the same way with
`wheeler llmsr recipes`.

---

## 4. The fast path

```bash
wheeler llmsr scaffold-spec --data recording.csv --recipe refit_per_group \
    --group-by cell --out specs/mine.txt
```

It reads your header, names the equation's arguments after your columns, writes
`MAX_NPARAMS`, drops in the recipe's `evaluate`, and prints the exact
`wheeler llmsr init` command that recipe pairs with. Then **edit the docstring**
before you run it.

What it deliberately will not do is guess the science: the skeleton is the dullest
form that uses every column, and the docstring is mechanical unless you pass
`--docstring`.

---

## 5. The recipes

Listed cheapest first. `wheeler llmsr recipes` prints the same table at the
terminal with a `ready` flag saying whether each one's dependencies are actually
installed here.

### pooled

- **Answers**: Does one form with ONE constant vector explain the whole table?
- **Assumes**: every row was generated by the same law AND the same constants: one cell, one preparation, one condition, or a pooled fit you are willing to defend
- **Costs**: one fit per candidate; the cheapest thing here
- **Door**: the default seam. The `evaluate` shown is upstream's shape and is not
  called unless you add `--use-spec-evaluate`.
- **Run it**:

```bash
wheeler llmsr init --spec <SPEC.txt> --data <TABLE.csv> --metric nmse
```

This is the baseline everything else is a departure from. Note what it returns: a
bare float, which is upstream's contract, with the fitted constants computed and
thrown away (`result.x` is discarded, as in every upstream spec). Through
Wheeler's default door that loss is irrelevant anyway. Through the spec door it
means `best.json` gets a score and no constants, and `selection.py` then writes
the score and refuses to emit a runner rather than emitting one that raises.

Reach for `refit_per_group` the moment the table holds more than one cell. A
pooled fit charges the FORM for variation that belongs to the PARAMETERS, and
that is how a correct law gets rejected.

### refit_per_group

- **Answers**: Does one form explain every cell once each cell is allowed its own constants?
- **Assumes**: the same law across cells and only the constants differ, and that a column names which cell each row belongs to
- **Costs**: one fit per cell per candidate, so a 40-cell table is 40x a pooled run; one cell that cannot be fitted invalidates the whole candidate
- **Door**: the default seam. `--group-by` does the work.
- **Run it**:

```bash
wheeler llmsr init --spec <SPEC.txt> --data <TABLE.csv> --metric nmse --group-by cell
```

**The recipe is what is missing from the `evaluate`: there is no loop over
cells.** The unit of fitting is a (dataset, group) pair and the driver refits
every unit separately, calling your `evaluate` once per unit with that unit's
rows. Writing the loop yourself would fit the pooled data and throw the protocol
away.

The score is then a VECTOR, one entry per cell, and that vector is the primary
object: the vendored buffer ranks islands on it and clusters forms by their
per-cell profile. `best.json` carries `params_per_group` and `value_per_group`,
`params` is empty by construction, and the emitted `.py` filters rows by group
and applies that group's own constants.

Validity is strict: a candidate is valid only if EVERY cell fitted. That
reproduces the ungrouped semantics exactly and keeps the score signatures
comparable, but it does mean one pathological cell throws away a good form.
Exclude such a cell in a `--loader` rather than loosening the rule.

This recipe returns Wheeler's additive dict, `{'score': ..., 'params': [...]}`,
rather than upstream's bare float, so the constants survive.

### transfer

- **Answers**: Does the LAW carry over to data the search never scored?
- **Assumes**: the same law governs both tables and only the constants differ, which is exactly what makes refitting on B a fair test rather than a second training run
- **Costs**: one fit per scored table per candidate, plus one `transfer` call at the end; the seed table is spent on the prompt and never scored
- **Door**: the default seam. The roles are everything here.
- **Run it**:

```bash
wheeler llmsr init --spec <SPEC.txt> --data A=<CELL_A.csv> --data B=<CELL_B.csv> \
    --metric nmse --seed-from A --score-on B
# ... run the search, then:
wheeler llmsr transfer --run <RUN_ID> --data <HELD_OUT.csv>
```

The `evaluate` body is identical to `refit_per_group`. The recipe is entirely in
the roles: `--seed-from` names the table the generator is SHOWN, which is where
the FORM comes from; `--score-on` names the tables the objective is taken over,
which is what the form is JUDGED on. Keeping them apart means a form extracted
from one cell is scored by refitting it on cells it never saw.

Two things this recipe exists to keep straight:

- **A scored table is not a holdout.** Forty rounds ranked on B means the search
  optimized against B, however good B's number looks. `best.json` labels every
  table `scored` or `held_out` with a `regime_reason` for exactly this reason,
  and a table that only ever seeded the prompt is held out but flagged `seed`,
  because the generator did see it.
- **"Does it generalize" is two questions.** Applying the winner's constants
  unchanged asks whether the CONSTANTS transfer. Refitting them under the same
  form asks whether the FORM transfers, which is what symbolic regression is
  actually looking for: a law that governs a new cell with different constants is
  the same law. `transfer.json` reports both, each stamped with its `claim`, and
  neither is ever derived from the other.

### shape_only

- **Answers**: Does the form have the right SHAPE, ignoring an unknown scale and baseline?
- **Assumes**: the recording carries an unknown gain and offset (an uncalibrated amplifier, an arbitrary fluorescence unit), and that you accept the constants coming back unidentifiable: the gain and params[0] are confounded by construction
- **Costs**: a least-squares solve inside every loss evaluation, so roughly 2x a plain fit, and a score that can never distinguish y from 3*y + 5
- **Door**: `--use-spec-evaluate`.
- **Run it**:

```bash
wheeler llmsr init --spec <SPEC.txt> --data <TABLE.csv> --metric nmse --use-spec-evaluate
```

The core of it:

```python
design = np.column_stack([pred, np.ones_like(pred)])
gain_offset = np.linalg.lstsq(design, y, rcond=None)[0]
return float(np.mean((design @ gain_offset - y) ** 2))
```

For every candidate constant vector the best-fitting scale and baseline are
solved in closed form and removed before the error is measured, so a form that is
right up to an unknown gain scores as if it were right.

Read the FORM out of this run, not the constants. Two caveats that matter for the
write-up: the reported constants are one member of a family (`params[0]` and the
free gain are confounded), and a baseline that carries real signal is destroyed
by this recipe rather than accounted for.

This one COULD be a registered `Metric`, since it only needs `(y_pred, y_true)`.
It is written as a recipe because the gain is a property of the recording, not of
the objective, and folding it into a metric would silently apply it to every run
that names that metric.

### chi_squared

- **Answers**: Does the form fit within the measurement error of each point?
- **Assumes**: a column of per-point standard deviations that are real (independent, Gaussian, correctly scaled); a wrong sigma column silently reweights the whole fit
- **Costs**: one extra column of data, and a score that is not comparable with any MSE-family number from another run
- **Door**: `--use-spec-evaluate`. **This one has no alternative.**
- **Run it**:

```bash
wheeler llmsr scaffold-spec --data <TABLE.csv> --recipe chi_squared --sigma-col sigma --out <SPEC.txt>
wheeler llmsr init --spec <SPEC.txt> --data <TABLE.csv> --metric nmse --use-spec-evaluate
```

This is the recipe that cannot be written as a metric, and it is why the spec
door exists. Wheeler's metric contract is a two-argument scorer,
`(y_pred, y_true) -> float`, and a per-point sigma is a third array: there is
nowhere to pass it. Through the spec door the sigma column is read straight off
`data['inputs']`.

`scaffold-spec --sigma-col` keeps that column out of the equation's arguments: it
describes the MEASUREMENT, not the law. Non-positive sigmas are dropped rather
than clipped, so a bad column shows up as fewer points instead of as an enormous
weight.

Reported as the mean squared pull, not the reduced chi-squared: divide by
(n - k) yourself if you want the reduced statistic, noting that k varies from
candidate to candidate.

### robust

- **Answers**: Does the form fit the bulk of the data, ignoring a few bad points?
- **Assumes**: the outliers are ARTIFACTS and not signal, and that HUBER_DELTA is set in the units of the residual (the default 1.0 is a placeholder, not a calibration)
- **Costs**: about the same as a plain fit, plus the standing risk of downweighting the very points a correct law predicts and a wrong one does not
- **Door**: `--use-spec-evaluate`, but see below.
- **Run it**:

```bash
wheeler llmsr init --spec <SPEC.txt> --data <TABLE.csv> --metric nmse --use-spec-evaluate
```

Huber: quadratic near zero, linear in the tail, so one bad sweep cannot outrank a
correct law the way a squared error lets it. A trimmed alternative, when the
artifacts are a known fraction rather than a heavy tail, is in the recipe's
docstring.

**Set `HUBER_DELTA`.** The shipped 1.0 is a placeholder in the units of your
residual, not a calibration. A robust spread estimate of the residuals
(1.4826 times the median absolute deviation) is the usual starting point.

If a robust loss is ALL you want, prefer a registered `Metric`: `metrics.py`
documents this exact Huber as one, and going that way keeps Wheeler's fit seam so
the constants land in `best.json` and the per-group refit still applies. Come
here when the spec also has to own the optimizer.

### numpy_adam

- **Answers**: Can the spec run its OWN optimizer loop rather than handing the fit to scipy?
- **Assumes**: nothing beyond the base install: the gradient is a central finite difference, not autograd, so it is honest about being a stand-in for torch_adam
- **Costs**: 2*MAX_NPARAMS extra evaluations per step, so hundreds of steps times a wide parameter budget is the slowest recipe here
- **Door**: `--use-spec-evaluate`.
- **Run it**:

```bash
wheeler llmsr init --spec <SPEC.txt> --data <TABLE.csv> --metric nmse --use-spec-evaluate
```

The point is the DOOR, not the algorithm. `--use-spec-evaluate` admits an
arbitrary optimization loop inside the spec, and this proves it on the base
install: an Adam written out in numpy, gradients by central difference. The test
suite scores a 400-step version against a 1-step version, so "the loop ran" is
evidence rather than assertion.

For a smooth least-squares problem, `pooled` will beat this on both speed and
accuracy, because scipy is better at this than a hand-rolled Adam. Reach for it
when you want to see the shape of a gradient-descent fit without adding a
dependency, and for `torch_adam` when you have torch.

### torch_adam

- **Answers**: Can the spec train the constants with autograd, the way upstream's torch specification does?
- **Assumes**: torch is installed, AND the generated equation body is written in operations torch understands: a body calling np.exp on a tensor raises, and the candidate is recorded invalid
- **Costs**: a torch install and STEPS gradient steps per unit per candidate; upstream's own torch spec runs 10,000
- **Door**: `--use-spec-evaluate`.
- **Run it**:

```bash
wheeler llmsr init --spec <SPEC.txt> --data <TABLE.csv> --metric nmse --use-spec-evaluate
```

This is the widest thing the door admits, and it is upstream's own widest case:
their `specification_oscillator2_torch.txt` defines a `torch.nn.Module`, an Adam
optimizer and a 10,000-step gradient loop inside the spec, and the unmodified
LLM-SR package runs it because nothing ever looks inside `evaluate`. Wheeler's
default door cannot: it calls `equation(*cols, params)` under its own numpy
convention and fits the constants itself.

**The constraint that catches people**: the search proposes ordinary numpy code,
and `np.exp(tensor)` raises rather than returning a tensor. Such a candidate is
recorded invalid with that error, never scored. Say so in your docstring, which is
what the generator reads: ask for torch operations, or for arithmetic that works
either way.

torch is not installed in Wheeler's own test environment, so this recipe's test
skips there and `numpy_adam` carries the same claim. Where torch IS installed the
shipped text is executed rather than assumed.

---

## 6. Choosing one

| your situation | recipe |
|---|---|
| one cell, one condition | `pooled` |
| many cells, one law, different constants | `refit_per_group` |
| you want to know whether it generalizes | `transfer` |
| the recording is in arbitrary units | `shape_only` |
| you have per-point error bars | `chi_squared` |
| a few sweeps are artifacts | `robust` |
| the fit itself needs a gradient optimizer | `torch_adam`, or `numpy_adam` without torch |

They compose. `--group-by` is orthogonal to every spec-door recipe: a chi-squared
run over 40 cells is `--group-by cell --use-spec-evaluate` with the
`chi_squared` spec, and each cell still refits its own constants.

---

## 7. What ships, and what does not

```bash
wheeler llmsr specs      # the bundled specs and their demo tables
wheeler llmsr recipes    # the recipes above, with a `ready` flag
```

`wheeler/_data/llmsr/specs/` holds worked specs for the problems the demo tables
carry (bacterial growth, the same growth law across three strains, a damped
nonlinear oscillator). They are **Wheeler-written starting points modelled on the
LLM-SR problem families, not copies of upstream's specification files.**

`wheeler/_data/llmsr/data/` holds small **synthetic** demo tables and
`make_demo_data.py`, the script that produces them. They are not the paper's
data, which is not vendored here. The generator uses no random number generator,
so the tables are reproducible, and the test suite reruns it and compares.

Run the whole loop end to end on shipped data before pointing it at a recording
that matters. `wheeler llmsr specs` prints each spec's `path` and its
`demo_data`; paste those two into `init`. For the grouped one:

```bash
wheeler llmsr specs          # copy the bactgrow_strains `path` and `demo_data`
wheeler llmsr init --spec <path> --data <demo_data> --metric nmse --group-by strain --run-id demo
wheeler llmsr status --run demo
```

The three strains in that table share one growth law and differ in two constants,
so it is a working demonstration of the per-group protocol rather than a toy.

---

## 8. Writing your own `evaluate`

The return contract is additive over upstream's:

| return | meaning |
|---|---|
| `float` / `int` | exactly upstream's contract: the MAXIMIZE-ME score (hence `return -loss`). No constants: upstream has nowhere to put them |
| `{'score': float, 'params': [...], 'per_group': {...}}` | the same score, plus the constants upstream discards. `per_group` may name ONLY the unit this call covered |
| anything else | an INVALID candidate with a truthful error, never a fabricated score |

Three rules that are not negotiable:

1. **One call per unit.** Your `evaluate` is called once per (dataset, group)
   pair with that pair's rows. Do not loop over cells yourself.
2. **The score keys belong to the run.** They are fixed at `init` and the vendored
   buffer clusters candidates on the sorted key signature, so a spec that named
   its own keys would silently make every candidate incomparable. A `per_group`
   naming anything other than the unit you were handed is a loud error.
3. **Failures are failures.** Raise, return `None`, return garbage, return a
   non-finite number: all become an invalid candidate with the reason recorded.
   Nothing is ever fabricated.

What the spec door does NOT reach: held-out split scoring (`test_id`/`test_ood`
siblings, and `wheeler llmsr transfer`) still runs through Wheeler's fit seam
under the run's DECLARED metric. Under `--use-spec-evaluate` those numbers are a
second opinion computed by different machinery, not the run's own objective
measured again. `best.json` records which door scored the run in
`optimizer.scored_by` so the two can be told apart.
