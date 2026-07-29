"""Worked ``evaluate`` recipes, and the scaffolder that fills one into a spec.

A spec is the one thing a scientist has to WRITE before an LLM-SR run can start:
a docstring stating the problem, a ``MAX_NPARAMS`` budget, an ``@equation.evolve``
skeleton the search mutates, and an ``@evaluate.run`` that says what a good fit
means. Everything else in this subtree is a flag. So the spec is where a run gets
stuck, and this module is what unsticks it: a small closed registry of recipes,
each one a REAL spec template under ``wheeler/_data/llmsr/recipes/``, rendered
against a scientist's own CSV header by ``scaffold``.

Two things a reader must hold onto, because they decide which recipe applies:

**Which door scores the run.** By default Wheeler NEVER calls the spec's
``evaluate``: it scores through ``fit.py`` + ``metrics.py``, which is what makes
the metric pluggable, the constants recoverable, and the per-unit refit possible.
``--use-spec-evaluate`` takes the other door, and then the spec's own ``evaluate``
owns the loss, the optimizer and whatever it imports. A recipe therefore declares
its ``door``: recipes whose point is the LOSS (``shape_only``, ``chi_squared``,
``robust``, ``torch_adam``, ``numpy_adam``) only mean anything through the spec
door and say so in their flags; recipes whose point is the OBJECTIVE'S SHAPE
(``pooled``, ``refit_per_group``, ``transfer``) are flag combinations on the
default door, and their ``evaluate`` is written to say the same thing so the spec
stays portable to upstream and gives the same answer through either door.

**A recipe is executable, not prose.** Every entry here points at a file that is
rendered, written, and RUN by ``tests/integrations/llmsr/test_recipes.py`` against
a tiny synthetic table. A recipe whose ``evaluate`` stopped working would fail the
suite rather than rot quietly in a document.

The registry is deliberately CLOSED, unlike ``metrics`` / ``loaders`` /
``optimizers``. Those are extension points where a scientist's own object has to
reach the engine at runtime. A recipe is a starting text: extending it means
editing the spec the scaffolder just wrote, which needs no registry at all.
"""

from __future__ import annotations

import ast
import keyword
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Mapping, Sequence

logger = logging.getLogger(__name__)

# Which door a recipe is written for.
#
# ``DOOR_DEFAULT``
#     Wheeler's own fit/metric seam scores the run and the spec's ``evaluate`` is
#     never called. The recipe is a FLAG COMBINATION; its ``evaluate`` is written
#     to compute the same quantity anyway, so the spec is portable to upstream and
#     answers the same through either door.
# ``DOOR_SPEC``
#     ``--use-spec-evaluate``. The spec's own ``evaluate`` scores every candidate,
#     owning the loss and the optimizer. The recipe is the ``evaluate`` BODY, and
#     it means nothing without the flag, which is why every such recipe carries it
#     in ``cli``.
DOOR_DEFAULT = "default"
DOOR_SPEC = "spec"

DEFAULT_RECIPE = "pooled"

# The default free-constant budget, which is upstream's. A skeleton uses one
# constant per input plus an intercept and leaves the rest for the search to
# reach for.
DEFAULT_MAX_NPARAMS = 10

_TOKEN_RE = re.compile(r"%%([A-Z_0-9]+)%%")

# A syntactically valid filling of every token, used ONLY to find out what names
# a template binds (see ``_bound_names``). The stand-in column name starts with
# an underscore, which ``_identifier`` can never produce, so it cannot collide
# with a real column and cannot pollute the answer.
_PROBE_COLUMN = "_probe_column"
_PROBE_TOKENS: dict[str, str] = {
    "DOCSTRING": "probe",
    "MAX_NPARAMS": "1",
    "UNPACK": f"{_PROBE_COLUMN} = inputs[:, 0]",
    "EQ_ARGS": _PROBE_COLUMN,
    "EQ_SIGNATURE": f"{_PROBE_COLUMN}: np.ndarray, params: np.ndarray",
    "EQ_ARG_DOCS": f"        {_PROBE_COLUMN}: probe.",
    "EQ_RETURN": f"params[0] * {_PROBE_COLUMN}",
    "EQ_DOC": "probe",
    "TARGET": "'probe'",
    "SIGMA": _PROBE_COLUMN,
    "SIGMA_COLUMN": "probe",
}


@dataclass(frozen=True)
class Recipe:
    """One worked ``evaluate`` strategy: what it measures, and how it is run.

    ``answers`` / ``assumes`` / ``costs`` are the three things the cookbook has to
    state about any scoring choice, and they live HERE rather than only in the
    document so ``wheeler llmsr recipes`` can say them truthfully at the terminal
    (a shipped user has the package, not the repository's ``docs/``).

    ``cli`` is the ``wheeler llmsr init`` argv this recipe pairs with, carrying
    ``{spec}`` / ``{data}`` / ``{data2}`` / ``{group}`` / ``{metric}``
    placeholders. It is ONE source: ``scaffold`` renders it into the command it
    prints, the cookbook quotes it, and the test builds the argv it actually runs
    from it, so a flag combination cannot drift away from the recipe that claims
    it. ``then`` is an optional follow-up verb (``transfer`` uses it).
    """

    key: str
    title: str
    answers: str
    assumes: str
    costs: str
    door: str
    cli: tuple[str, ...]
    then: tuple[str, ...] = ()
    # Third-party imports the recipe's own ``evaluate`` needs. Empty for every
    # recipe that runs on the base install.
    needs: tuple[str, ...] = ()
    # What the recipe needs from the DATA, so a caller (the scaffolder, the test,
    # the act) can tell whether the table in hand can carry it.
    sigma: bool = False
    grouped: bool = False
    datasets: int = 1

    @property
    def template_path(self) -> Path:
        return recipes_dir() / f"{self.key}.txt"

    def template(self) -> str:
        """The recipe's spec template, as shipped. Raises if it is missing."""
        return self.template_path.read_text()

    def flags(self) -> tuple[str, ...]:
        """The flag NAMES this recipe's command line carries, for a listing."""
        return tuple(tok for tok in self.cli if tok.startswith("--"))

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "title": self.title,
            "answers": self.answers,
            "assumes": self.assumes,
            "costs": self.costs,
            "door": self.door,
            "uses_spec_evaluate": self.door == DOOR_SPEC,
            "flags": list(self.flags()),
            "cli": list(self.cli),
            "then": list(self.then),
            "needs": list(self.needs),
            "needs_sigma_column": self.sigma,
            "needs_group_column": self.grouped,
            "n_datasets": self.datasets,
            "template": str(self.template_path),
        }


def _data_root() -> Path:
    """``wheeler/_data/llmsr``, the bundled recipe/spec/data tree."""
    return Path(str(resources.files("wheeler") / "_data" / "llmsr"))


def recipes_dir() -> Path:
    return _data_root() / "recipes"


def specs_dir() -> Path:
    return _data_root() / "specs"


def demo_data_dir() -> Path:
    return _data_root() / "data"


_INIT = ("--spec", "{spec}", "--data", "{data}", "--metric", "{metric}")


RECIPES: dict[str, Recipe] = {r.key: r for r in (
    Recipe(
        key="pooled",
        title="one theta for everything",
        answers="Does one form with ONE constant vector explain the whole table?",
        assumes=(
            "every row was generated by the same law AND the same constants: one "
            "cell, one preparation, one condition, or a pooled fit you are willing "
            "to defend"
        ),
        costs="one fit per candidate; the cheapest thing here",
        door=DOOR_DEFAULT,
        cli=_INIT,
    ),
    Recipe(
        key="refit_per_group",
        title="one theta per cell, the FORM judged on the vector",
        answers=(
            "Does one form explain every cell once each cell is allowed its own "
            "constants?"
        ),
        assumes=(
            "the same law across cells and only the constants differ, and that a "
            "column names which cell each row belongs to"
        ),
        costs=(
            "one fit per cell per candidate, so a 40-cell table is 40x a pooled "
            "run; one cell that cannot be fitted invalidates the whole candidate"
        ),
        door=DOOR_DEFAULT,
        cli=(*_INIT, "--group-by", "{group}"),
        grouped=True,
    ),
    Recipe(
        key="transfer",
        title="extract on A, refit and score on B",
        answers="Does the LAW carry over to data the search never scored?",
        assumes=(
            "the same law governs both tables and only the constants differ, which "
            "is exactly what makes refitting on B a fair test rather than a "
            "second training run"
        ),
        costs=(
            "one fit per scored table per candidate, plus one `transfer` call at "
            "the end; the seed table is spent on the prompt and never scored"
        ),
        door=DOOR_DEFAULT,
        cli=(
            "--spec", "{spec}", "--data", "A={data}", "--data", "B={data2}",
            "--metric", "{metric}", "--seed-from", "A", "--score-on", "B",
        ),
        then=("transfer", "--run", "{run}", "--data", "{data3}"),
        datasets=2,
    ),
    Recipe(
        key="shape_only",
        title="a nuisance gain and offset regressed out before the error is measured",
        answers=(
            "Does the form have the right SHAPE, ignoring an unknown scale and "
            "baseline?"
        ),
        assumes=(
            "the recording carries an unknown gain and offset (an uncalibrated "
            "amplifier, an arbitrary fluorescence unit), and that you accept the "
            "constants coming back unidentifiable: the gain and params[0] are "
            "confounded by construction"
        ),
        costs=(
            "a least-squares solve inside every loss evaluation, so roughly 2x a "
            "plain fit, and a score that can never distinguish y from 3*y + 5"
        ),
        door=DOOR_SPEC,
        cli=(*_INIT, "--use-spec-evaluate"),
    ),
    Recipe(
        key="chi_squared",
        title="per-point sigma, which a 2-argument scorer cannot express",
        answers="Does the form fit within the measurement error of each point?",
        assumes=(
            "a column of per-point standard deviations that are real (independent, "
            "Gaussian, correctly scaled); a wrong sigma column silently reweights "
            "the whole fit"
        ),
        costs=(
            "one extra column of data, and a score that is not comparable with any "
            "MSE-family number from another run"
        ),
        door=DOOR_SPEC,
        cli=(*_INIT, "--use-spec-evaluate"),
        sigma=True,
    ),
    Recipe(
        key="robust",
        title="Huber loss, for cells with artifacts",
        answers="Does the form fit the bulk of the data, ignoring a few bad points?",
        assumes=(
            "the outliers are ARTIFACTS and not signal, and that HUBER_DELTA is "
            "set in the units of the residual (the default 1.0 is a placeholder, "
            "not a calibration)"
        ),
        costs=(
            "about the same as a plain fit, plus the standing risk of downweighting "
            "the very points a correct law predicts and a wrong one does not"
        ),
        door=DOOR_SPEC,
        cli=(*_INIT, "--use-spec-evaluate"),
    ),
    Recipe(
        key="numpy_adam",
        title="a hand-rolled Adam, proving the door takes a whole optimizer",
        answers=(
            "Can the spec run its OWN optimizer loop rather than handing the fit "
            "to scipy?"
        ),
        assumes=(
            "nothing beyond the base install: the gradient is a central finite "
            "difference, not autograd, so it is honest about being a stand-in for "
            "torch_adam"
        ),
        costs=(
            "2*MAX_NPARAMS extra evaluations per step, so hundreds of steps times "
            "a wide parameter budget is the slowest recipe here"
        ),
        door=DOOR_SPEC,
        cli=(*_INIT, "--use-spec-evaluate"),
    ),
    Recipe(
        key="torch_adam",
        title="a differentiable optimizer inside the spec",
        answers=(
            "Can the spec train the constants with autograd, the way upstream's "
            "torch specification does?"
        ),
        assumes=(
            "torch is installed, AND the generated equation body is written in "
            "operations torch understands: a body calling np.exp on a tensor "
            "raises, and the candidate is recorded invalid"
        ),
        costs=(
            "a torch install and STEPS gradient steps per unit per candidate; "
            "upstream's own torch spec runs 10,000"
        ),
        door=DOOR_SPEC,
        cli=(*_INIT, "--use-spec-evaluate"),
        needs=("torch",),
    ),
)}


def get_recipe(key: str) -> Recipe:
    """Return the recipe for ``key`` or raise with the list of what exists."""
    normalized = (key or "").strip().lower().replace("-", "_")
    if normalized not in RECIPES:
        raise KeyError(
            f"unknown recipe {key!r}; recipes: {sorted(RECIPES)}. "
            "Run `wheeler llmsr recipes` for what each one measures."
        )
    return RECIPES[normalized]


def available() -> list[str]:
    """The recipe keys, sorted. What an ``options_from`` port may offer."""
    return sorted(RECIPES)


def describe() -> list[dict]:
    """Every recipe as a plain dict, in registry order (cheapest first)."""
    return [r.as_dict() for r in RECIPES.values()]


def is_importable(module: str) -> bool:
    """Whether a recipe's declared dependency can actually be imported here.

    Used only to LABEL a listing. A recipe whose dependency is absent is still
    listed, because the scientist may be about to install it; it is simply not
    offered as ready.
    """
    from importlib.util import find_spec

    try:
        return find_spec(module) is not None
    except (ImportError, ValueError):
        return False


# ------------------------------------------------------------------ scaffolding


@dataclass(frozen=True)
class Scaffolded:
    """A filled spec, plus everything the caller needs to say what it is."""

    recipe: str
    text: str
    # The equation's argument names, in the order the fit binds columns.
    inputs: tuple[str, ...]
    # The header columns those names came from, same order, original spelling.
    columns: tuple[str, ...]
    target: str
    group_by: str
    sigma: str
    max_nparams: int
    command: tuple[str, ...]
    then: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "recipe": self.recipe,
            "spec": self.text,
            "inputs": list(self.inputs),
            "columns": list(self.columns),
            "target": self.target,
            "group_by": self.group_by,
            "sigma": self.sigma,
            "max_nparams": self.max_nparams,
            "command": ["wheeler", "llmsr", "init", *self.command],
            "then": (["wheeler", "llmsr", *self.then] if self.then else []),
        }


@lru_cache(maxsize=None)
def _bound_names(template: str) -> frozenset[str]:
    """Every name a recipe template BINDS, read off the template itself.

    A column called ``y`` in a recipe whose ``evaluate`` also binds ``y`` would
    be silently overwritten between the unpack line and the call to ``equation``,
    and the fit would then be scored against the wrong array without failing.
    Rather than keep a hand-written list of such names (which drifts the moment a
    recipe gains a local), the template is filled with stand-ins, parsed, and
    asked what it binds: assignment targets, loop targets, function names and
    their arguments, and imported names.

    Falls back to the empty set if a template cannot be parsed. The caller only
    loses collision-avoidance, and ``scaffold`` will fail loudly at the parse it
    does next anyway.
    """
    try:
        tree = ast.parse(_render(template, _PROBE_TOKENS))
    except (SyntaxError, ValueError):
        logger.warning("recipe template could not be parsed for its bound names")
        return frozenset()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            args = node.args
            names.update(
                a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)
            )
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(
                (alias.asname or alias.name).split(".")[0] for alias in node.names
            )
    return frozenset(names)


def _identifier(name: str, index: int, taken: set[str]) -> str:
    """Turn a CSV header cell into a Python argument name, without collisions.

    Case is PRESERVED (``pH`` stays ``pH``), because the scientist named the
    column and the generated equation is read by a human. Everything else is
    mechanical: non-identifier characters collapse to ``_``, a leading digit gets
    a positional prefix, and a keyword, a name the recipe already binds, or a
    repeat gets a numeric suffix. ``taken`` is seeded with the template's own
    bound names, so shadowing is impossible rather than merely unlikely.
    """
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", str(name).strip()).strip("_")
    if not cleaned:
        cleaned = f"x{index}"
    if cleaned[0].isdigit():
        cleaned = f"x{index}_{cleaned}"
    if keyword.iskeyword(cleaned):
        cleaned = f"{cleaned}_"
    base, n = cleaned, 2
    while cleaned in taken:
        cleaned = f"{base}_{n}"
        n += 1
    taken.add(cleaned)
    return cleaned


def _render(template: str, tokens: Mapping[str, str]) -> str:
    """Substitute every ``%%TOKEN%%``, refusing a token the renderer cannot fill.

    Refusing rather than leaving it in place is the point: a template that names
    something the scaffolder does not supply would otherwise ship a spec with a
    literal ``%%FOO%%`` in it, which is a syntax error a scientist has to debug
    for us.
    """
    unknown: list[str] = []

    def substitute(match: re.Match) -> str:
        name = match.group(1)
        if name not in tokens:
            unknown.append(name)
            return match.group(0)
        return tokens[name]

    out = _TOKEN_RE.sub(substitute, template)
    if unknown:
        raise ValueError(
            f"recipe template names token(s) {sorted(set(unknown))} that the "
            "scaffolder does not supply"
        )
    return out


def _unpack(names: Sequence[str]) -> str:
    """The ``a, b = inputs[:, 0], inputs[:, 1]`` line, for any column count."""
    lhs = ", ".join(names)
    rhs = ", ".join(f"inputs[:, {i}]" for i in range(len(names)))
    return f"{lhs} = {rhs}"


def _arg_docs(names: Sequence[str], columns: Sequence[str]) -> str:
    return "\n".join(
        f"        {name}: A numpy array of observations of {column!r}."
        for name, column in zip(names, columns)
    )


def _skeleton(names: Sequence[str], max_nparams: int) -> str:
    """The starting equation the search mutates: linear in every input, plus one.

    Deliberately the dullest form that uses every column: it is a starting point
    the generator is meant to leave behind, and a skeleton that already encoded a
    guess would be doing the scientist's thinking.
    """
    usable = min(len(names), max(max_nparams - 1, 1))
    terms = [f"params[{i}] * {name}" for i, name in enumerate(names[:usable])]
    if len(terms) < max_nparams:
        terms.append(f"params[{len(terms)}]")
    return " + ".join(terms)


def _fill(command: Sequence[str], values: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(token.format(**values) for token in command)


def read_header(data_path: str | Path) -> list[str]:
    """The CSV header, as a list of column names."""
    with open(data_path) as fh:
        line = fh.readline()
    return [cell.strip() for cell in line.strip().split(",")]


def scaffold(
    recipe_key: str,
    data_path: str | Path,
    *,
    group_by: str = "",
    sigma_col: str = "",
    max_nparams: int | None = None,
    docstring: str = "",
    metric: str = "nmse",
    spec_path: str = "",
) -> Scaffolded:
    """Fill a recipe against a real CSV header and return the spec plus its command.

    The column roles come from ``data.input_columns``, the same function the fit
    uses to decide what ``X`` holds, so the equation's arguments line up with the
    array positions by construction rather than by a second convention. The
    trailing column is the target (upstream's convention) and a named
    ``group_by`` column is excluded from the inputs, exactly as ``_load_xy``
    excludes it.

    Raises ``ValueError`` with a usable message rather than emitting a spec that
    cannot run: no input columns, a group or sigma column that is not in the
    header, or a recipe that needs a sigma column and was not given one.
    """
    from . import data as data_mod

    recipe = get_recipe(recipe_key)
    path = Path(data_path)
    header = read_header(path)
    if len(header) < 2:
        raise ValueError(
            f"{path} has {len(header)} column(s); a spec needs at least one input "
            "column and a target column (the last one)"
        )
    if group_by and group_by not in header:
        raise ValueError(
            f"--group-by {group_by!r} is not a column in {path}; columns: {header}"
        )
    # Refused HERE as well as at `init`, because the spec would otherwise be
    # written against a column set the run can never load, and the scientist
    # would meet the failure one step further from its cause.
    if group_by and group_by == header[-1]:
        raise ValueError(
            f"--group-by {group_by!r} is the target column (the last one); group "
            "by an identifier column instead"
        )

    columns = list(data_mod.input_columns(str(path), group_by))
    if not columns:
        raise ValueError(
            f"{path} leaves no input columns once the target and the group column "
            "are removed; there is nothing for the equation to take"
        )
    target = header[-1]

    template = recipe.template()
    taken: set[str] = set(_bound_names(template))
    names = [_identifier(c, i, taken) for i, c in enumerate(columns)]

    if sigma_col and sigma_col not in columns:
        raise ValueError(
            f"--sigma-col {sigma_col!r} is not an input column of {path}; input "
            f"columns: {columns}"
        )
    if recipe.sigma and not sigma_col:
        raise ValueError(
            f"recipe {recipe.key!r} weights every point by its own measurement "
            "error, so it needs --sigma-col <column>. Name the column holding the "
            f"per-point standard deviation; input columns: {columns}"
        )
    if sigma_col and not recipe.sigma:
        # Refused because the resulting spec would be silently wrong under the
        # DEFAULT door. Setting a column aside removes it from the equation's
        # arguments but not from the input array, and the default fit binds the
        # first n columns POSITIONALLY, so unless the set-aside column happened
        # to be the last one the equation would receive the wrong arrays and
        # still fit, still score, and still report.
        raise ValueError(
            f"recipe {recipe.key!r} does not read a per-point error column, so "
            f"--sigma-col {sigma_col!r} would set that column aside without "
            "anything using it. Wheeler's default fit binds the leading input "
            "columns positionally, so the equation could silently receive the "
            "wrong ones. Use --recipe chi_squared to weight by it, or drop the "
            "flag."
        )
    sigma_name = names[columns.index(sigma_col)] if sigma_col else ""
    # The equation never takes the sigma column: it is a property of the
    # MEASUREMENT, not an input to the law. The spec's own evaluate reads it
    # straight off `inputs`, which is precisely what the default door (whose
    # arity rule is positional) could not express.
    eq_names = [n for n in names if n != sigma_name]
    eq_columns = [c for c, n in zip(columns, names) if n != sigma_name]
    if not eq_names:
        raise ValueError(
            f"{path} has no input column left for the equation once {sigma_col!r} "
            "is set aside as the measurement error"
        )

    budget = DEFAULT_MAX_NPARAMS if max_nparams is None else int(max_nparams)
    if budget < 1:
        raise ValueError("--max-nparams must be at least 1")

    text = _render(template, {
        "DOCSTRING": docstring.strip() or (
            f"Find the mathematical function skeleton that represents {target!r} "
            f"given {', '.join(repr(c) for c in eq_columns)}."
        ),
        "MAX_NPARAMS": str(budget),
        "UNPACK": _unpack(names),
        "EQ_ARGS": ", ".join(eq_names),
        "EQ_SIGNATURE": ", ".join(
            [f"{n}: np.ndarray" for n in eq_names] + ["params: np.ndarray"]
        ),
        "EQ_ARG_DOCS": _arg_docs(eq_names, eq_columns),
        "EQ_RETURN": _skeleton(eq_names, budget),
        "EQ_DOC": f"Mathematical function for {target!r}",
        "TARGET": repr(target),
        "SIGMA": sigma_name,
        "SIGMA_COLUMN": sigma_col,
    })

    values = {
        "spec": spec_path or "<SPEC.txt>",
        "data": str(path),
        "data2": "<SECOND_TABLE.csv>",
        "data3": "<HELD_OUT.csv>",
        "group": group_by or "<GROUP_COLUMN>",
        "metric": metric,
        "run": "<RUN_ID>",
    }
    return Scaffolded(
        recipe=recipe.key,
        text=text,
        inputs=tuple(eq_names),
        columns=tuple(eq_columns),
        target=target,
        group_by=group_by,
        sigma=sigma_name,
        max_nparams=budget,
        command=_fill(recipe.cli, values),
        then=_fill(recipe.then, values),
    )


# ------------------------------------------------------------- bundled specs


@dataclass(frozen=True)
class BundledSpec:
    """One worked spec that ships with Wheeler, and the demo table it fits.

    These exist because the act tells the scientist to use "the matching bundled
    spec", and for a long while nothing was bundled at all. They are STARTING
    POINTS modelled on the LLM-SR problem family, not copies of upstream's files
    and not upstream's data: the tables are synthetic and regenerated by the
    script beside them.
    """

    key: str
    title: str
    models: str
    inputs: tuple[str, ...]
    target: str
    demo: str
    group_by: str = ""

    @property
    def path(self) -> Path:
        return specs_dir() / f"{self.key}.txt"

    @property
    def demo_path(self) -> Path:
        return demo_data_dir() / self.demo

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "title": self.title,
            "models": self.models,
            "inputs": list(self.inputs),
            "target": self.target,
            "path": str(self.path),
            "demo_data": str(self.demo_path),
            "group_by": self.group_by,
            "synthetic_demo_data": True,
        }


BUNDLED_SPECS: dict[str, BundledSpec] = {s.key: s for s in (
    BundledSpec(
        key="bactgrow",
        title="bacterial growth rate",
        models=(
            "population growth rate from density, substrate, temperature and pH: "
            "the LLM-SR benchmark problem family"
        ),
        inputs=("b", "s", "temp", "pH"),
        target="growth",
        demo="bactgrow_demo.csv",
    ),
    BundledSpec(
        key="bactgrow_strains",
        title="bacterial growth rate, several strains",
        models=(
            "the same growth law across strains that share the FORM and differ in "
            "their constants: the run --group-by exists for"
        ),
        inputs=("b", "s", "temp", "pH"),
        target="growth",
        demo="bactgrow_strains_demo.csv",
        group_by="strain",
    ),
    BundledSpec(
        key="oscillator",
        title="damped nonlinear oscillator",
        models="acceleration from time, position and velocity",
        inputs=("t", "x", "v"),
        target="a",
        demo="oscillator_demo.csv",
    ),
)}


def get_spec(key: str) -> BundledSpec:
    normalized = (key or "").strip().lower().replace("-", "_")
    if normalized not in BUNDLED_SPECS:
        raise KeyError(
            f"unknown bundled spec {key!r}; bundled: {sorted(BUNDLED_SPECS)}. "
            "Run `wheeler llmsr specs` for what each one models."
        )
    return BUNDLED_SPECS[normalized]


def describe_specs() -> list[dict]:
    return [s.as_dict() for s in BUNDLED_SPECS.values()]
