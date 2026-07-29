"""Model-free driver CLI for LLM-SR equation discovery: ``wheeler llmsr ...``.

Inverts the upstream blocking ``pipeline.main()`` into four verbs so Claude Code
can step the SAME evolutionary loop, in the same order, generating candidates via
a sub-agent (or an external CLI) rather than an API key:

    init   --spec S --data D --metric M [--generator claude|codex]  -> run dir
    prompt --run R                        -> next prompt (from buffer.get_prompt)
    submit --run R --body-file B ...      -> fit + score + register in the buffer
    best   --run R                        -> best.json (equation + constants + metrics)

The buffer, island model, and program manipulation are the vendored upstream code
called unchanged; only the outer wiring and the fit/score seam (``fit.py`` +
``metrics.py``) are Wheeler's. State persists by replaying ``submissions.jsonl``
through the vendored ``register_program`` on each call (no pickles). The CLI never
calls a model: generation happens in the act.

This module is the verbs and their wiring. The pieces they lean on live next
door: ``runs.py`` (run dir, submissions log, progress), ``data.py`` (loading a
table in the shape its metric declares), ``selection.py`` (picking a winner and
scoring it on held-out splits).
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Optional

import typer

from . import data as data_mod
from . import fit as fit_mod
from . import loaders as loaders_mod
from . import metrics as metrics_mod
from . import optimizers as optimizers_mod
from . import recipes as recipes_mod
from . import runs as runs_mod
from . import transfer as transfer_mod
from .runs import (
    _RUNS_ROOT,
    _append_submission,
    _n_constraint_rejected,
    _now,
    _read_meta,
    _read_submissions,
    _run_dir,
    _scores_per_test,
    _timing,
    _write_heartbeat,
    status_payload,
)
from .selection import (
    _SELECT_MODES,
    _equation_complexity,
    _runnable_program,
    _select_winner,
    _split_metrics,
)
from .vendor import buffer as buffer_mod
from .vendor import code_manipulation, config as config_lib, evaluator

logger = logging.getLogger(__name__)

llmsr_app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="LLM-SR equation discovery: drive the evolutionary search from Claude Code.",
)

_GENERATORS = ("claude", "codex")

# Static on purpose: a help string is frozen when the command is declared, so it
# can only ever name the built-ins truthfully. `wheeler llmsr metrics` is the
# listing that reflects what is actually registered right now.
_METRIC_HELP = (
    "scoring metric; built in: "
    + ", ".join(sorted(metrics_mod.BUILTIN_METRICS))
    + " (run `wheeler llmsr metrics` for every registered metric, yours included)"
)


_DATA_HELP = (
    "training table, repeatable. `--data path` or `--data NAME=path`, where NAME "
    "is what the score key calls it. Every scored dataset refits the candidate's "
    "OWN constants, so scoring a form on a table it was not extracted from tests "
    "the FORM rather than the parameterization. A single unnamed --data is named "
    f"{fit_mod.UNGROUPED!r}, exactly as before."
)

_SEED_FROM_HELP = (
    "which dataset shapes the prompt (default: the first --data). This is where "
    "the FORM comes from; --score-on is what it is judged on. Naming them apart "
    "is how a law extracted from one cell gets tested on cells it never saw."
)

_SCORE_ON_HELP = (
    "which datasets enter the objective, by name, comma-separated or repeated "
    "(default: all of them). A dataset named here IS optimized against: 40 rounds "
    "scored on it makes its error a training number, not a generalization claim."
)


_OPTIMIZER_HELP = (
    "constant-fit optimizer; built in: "
    + ", ".join(sorted(optimizers_mod.BUILTIN_OPTIMIZERS))
    + f", plus {optimizers_mod.AUTO} (the default: BFGS, escalating to "
    "Nelder-Mead when no start moves off its init, which is what a flat "
    "gradient looks like). Run `wheeler llmsr optimizers` for every "
    "registered one, yours included."
)


def _metric_for(key: str) -> metrics_mod.Metric:
    """Resolve a metric by name, importing the scientist's metric modules first."""
    metrics_mod.load_user_metrics()
    try:
        return metrics_mod.get_metric(key)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _optimizer_for(key: str) -> str:
    """Validate an optimizer choice, importing the scientist's modules first.

    Returns the canonical key to bind into the run. Checked HERE, at ``init``,
    because a name the fit cannot resolve would otherwise invalidate every
    candidate in the search rather than failing one command.
    """
    optimizers_mod.load_user_optimizers()
    try:
        return optimizers_mod.canonical(key)
    except KeyError as exc:
        raise typer.BadParameter(str(exc).strip("'")) from exc


# ---------------------------------------------------------------- search state

def _extract_names(spec: str) -> tuple[str, str]:
    evolve = list(code_manipulation.yield_decorated(spec, "equation", "evolve"))
    run = list(code_manipulation.yield_decorated(spec, "evaluate", "run"))
    if len(evolve) != 1 or len(run) != 1:
        raise typer.BadParameter(
            "spec must have exactly one @equation.evolve and one @evaluate.run"
        )
    return evolve[0], run[0]


def _rebuild_buffer(run_dir: Path, meta: dict):
    """Replay submissions through the vendored register_program to restore state."""
    spec = Path(meta["spec_path"]).read_text()
    fte = meta["function_to_evolve"]
    template = code_manipulation.text_to_program(spec)
    db = buffer_mod.ExperienceBuffer(
        config_lib.Config().experience_buffer, template, fte
    )
    for sub in _read_submissions(run_dir):
        if not sub.get("valid"):
            continue
        fn, _program = evaluator._sample_to_program(
            sub["body"], sub.get("version_generated"), template, fte
        )
        db.register_program(
            fn, sub.get("island_id"), _scores_per_test(sub)
        )
    return template, db, fte


def _score_body(
    body: str,
    version_generated: Optional[int],
    template,
    fte: str,
    units: list[data_mod.Unit],
    metric,
    max_nparams: int,
    timeout: int,
    progress_path: Optional[Path] = None,
    optimizer: str = optimizers_mod.AUTO,
    restarts: int = fit_mod.DEFAULT_RESTARTS,
    seed: int = fit_mod.DEFAULT_SEED,
    use_spec_evaluate: bool = False,
    function_to_run: str = "",
    grouped: bool = False,
) -> tuple[fit_mod.FitResult, str, object]:
    """Build the program from a body, fit + score it. Returns (result, program, fn).

    ``units`` are the (dataset, group) pairs this run scores against. Each refits
    its OWN constants under the one shared form, so a candidate is judged on how
    the FORM travels rather than on one lucky parameterization.

    ``progress_path`` is the during-the-fit channel: the fit refreshes it as each
    unit lands, so ``status`` can answer where a long refit has got to and which
    table it is on.

    ``optimizer``, ``restarts`` and ``seed`` are the run's fit knobs, bound at
    ``init`` and read back off ``meta.json`` for every later submit, so one run
    fits every candidate the same way.

    ``use_spec_evaluate`` picks the OTHER scoring door: the spec's own
    ``@evaluate.run``, called once per unit (``spec_eval.py``). It is a declared
    choice bound at ``init``, never sniffed off the spec text, and both doors
    return the same ``FitResult`` so nothing downstream changes. The candidate is
    built and guarded identically either way: ``_sample_to_program`` and
    ``_calls_ancestor`` are upstream's and run before either door.
    """
    fn, program = evaluator._sample_to_program(body, version_generated, template, fte)
    if evaluator._calls_ancestor(program, fte):
        return (
            fit_mod.FitResult(
                valid=False,
                error="calls an ancestor version",
                rejection_reason="numeric",
            ),
            program,
            fn,
        )
    if use_spec_evaluate:
        # Lazy, like the other seams here: the default path must not pay for a
        # module it never calls.
        from . import spec_eval as spec_eval_mod

        result = spec_eval_mod.evaluate_spec_grouped(
            program,
            function_to_run,
            data_mod.as_spec_units(units),
            metric,
            timeout_seconds=timeout,
            progress_path=progress_path,
            dataset_of=data_mod.dataset_of(units),
            grouped=grouped,
        )
        return result, program, fn
    result = fit_mod.evaluate_body_grouped(
        program,
        fte,
        data_mod.as_groups(units),
        metric,
        max_nparams=max_nparams,
        timeout_seconds=timeout,
        progress_path=progress_path,
        optimizer=optimizer,
        restarts=restarts,
        seed=seed,
        dataset_of=data_mod.dataset_of(units),
    )
    return result, program, fn


def _units_for(meta: dict, metric) -> list[data_mod.Unit]:
    """Load the units a run scores against, exactly as its ``meta.json`` declares.

    Everything that decides the key set (which datasets, which grouping column,
    which scheme) is read back off the run rather than re-derived from the command
    line, because every candidate in one run must present the buffer with
    identical keys. A run dir written before datasets were nameable reads back as
    its single ``data_path`` under the old scheme, so it keeps replaying.
    """
    return data_mod.load_units(
        data_mod.scored_from_meta(meta),
        metric,
        group_by=str(meta.get("group_by", "") or ""),
        scheme=data_mod.scheme_from_meta(meta),
        loader=str(meta.get("loader", "") or ""),
    )


def _optimizer_report(meta: dict, winner: Optional[dict]) -> dict:
    """What produced the winning constants, and under which knobs.

    ``requested`` is the run's declared choice; ``used`` is the CONCRETE optimizer
    behind the number. The two differ exactly when ``auto`` escalated, and that
    difference is the whole point: a reader of ``best.json`` must never have to
    guess whether a silent fallback happened. Empty ``used`` means the winner was
    fitted before the optimizer was recorded.

    A run scored through the spec's own ``@evaluate.run`` reports something
    different, because none of these knobs touched its number: the spec owns the
    loss AND the optimizer. It reports ``scored_by`` (present only on that path,
    so an existing reader of a default run sees the block it always saw),
    ``restarts``/``seed`` as ``None`` because none were drawn, and the run's
    declared optimizer under ``declared_optimizer`` so the choice it recorded is
    still visible without being credited for a fit it did not do.
    """
    knobs = _fit_knobs(meta)
    if meta.get("use_spec_evaluate"):
        from .spec_eval import SPEC_EVALUATE

        return {
            "requested": SPEC_EVALUATE,
            "used": (winner or {}).get("optimizer", "") or SPEC_EVALUATE,
            "restarts": None,
            "seed": None,
            "scored_by": SPEC_EVALUATE,
            "declared_optimizer": knobs["optimizer"],
        }
    return {
        "requested": knobs["optimizer"],
        "used": (winner or {}).get("optimizer", ""),
        "restarts": knobs["restarts"],
        "seed": knobs["seed"],
    }


def _dataset_report(meta: dict, winner: Optional[dict]) -> dict:
    """Per-dataset breakdown of the winner, every entry LABELLED by regime.

    ``scored`` means the search optimized against that dataset: it refitted the
    candidate's constants on it and ranked every candidate by the result. Forty
    rounds against a table makes that table's error a training number however good
    it looks, so it is never a generalization claim. ``held_out`` means the search
    did neither.

    A dataset that only ever SEEDED the prompt is held out by that rule, and its
    entry says so in ``regime_reason`` and carries ``seed: true``, because a
    generator that was shown a table did use it to choose the form even though the
    search never scored against it. The reader is told; nothing is inferred for
    them.

    Held-out entries carry no value: this run did not compute one. Reporting a
    number here would mean refitting the winner on data the run never touched,
    which is a separate act with its own provenance, not a footnote on this one.

    The vocabulary is ``discover.py``'s, imported rather than restated so the two
    cannot drift. Lazy, because ``discover`` pulls in the graph adapter stack and
    nothing about writing ``best.json`` needs it loaded.
    """
    from .discover import REGIME_HELD_OUT, REGIME_SCORED

    datasets = data_mod.datasets_from_meta(meta)
    scored = {d.name for d in data_mod.scored_from_meta(meta)}
    scheme = data_mod.scheme_from_meta(meta)
    seed_name = data_mod.resolve_seed_from(
        datasets, str(meta.get("seed_from", "") or "")
    ).name

    values = (winner or {}).get("per_group_value") or {}
    params = (winner or {}).get("params_per_group") or {}

    entries = []
    for spec in datasets:
        is_seed = spec.name == seed_name
        if spec.name in scored:
            keys = data_mod.keys_for(spec.name, list(values), scheme)
            per_key = {k: values[k] for k in keys}
            entries.append({
                "name": spec.name,
                "path": spec.path,
                "seed": is_seed,
                "regime": REGIME_SCORED,
                "regime_reason": (
                    "the search refitted this dataset's own constants and ranked "
                    "every candidate on the result"
                ),
                # The mean over this dataset's units, which is what the fit
                # aggregates to, alongside the vector it is a mean of.
                "value": (sum(per_key.values()) / len(per_key)) if per_key else None,
                "keys": keys,
                "value_per_key": per_key,
                "params_per_key": {k: params[k] for k in keys if k in params},
            })
            continue
        entries.append({
            "name": spec.name,
            "path": spec.path,
            "seed": is_seed,
            "regime": REGIME_HELD_OUT,
            "regime_reason": (
                "the search never refitted constants on this dataset or ranked a "
                "candidate by it; it shaped the prompt only"
                if is_seed
                else "the search never refitted constants on this dataset or "
                "ranked a candidate by it"
            ),
            "value": None,
            "keys": [],
            "value_per_key": {},
            "params_per_key": {},
        })
    return {
        "seed_from": seed_name,
        "score_on": [d.name for d in data_mod.scored_from_meta(meta)],
        "score_key_scheme": scheme,
        "entries": entries,
    }


def _fit_knobs(meta: dict) -> dict:
    """The optimizer knobs this run was created with, as ``_score_body`` kwargs.

    Every default is what the fit used before these were declarable, so a run
    created by an older Wheeler replays identically, save for the escalation
    ``auto`` adds where BFGS could not move off its inits at all.
    """
    restarts = meta.get("restarts")
    seed = meta.get("seed")
    return {
        "optimizer": meta.get("optimizer") or optimizers_mod.AUTO,
        "restarts": fit_mod.DEFAULT_RESTARTS if restarts is None else int(restarts),
        "seed": fit_mod.DEFAULT_SEED if seed is None else int(seed),
    }


def _spec_knobs(meta: dict) -> dict:
    """Which scoring door this run uses, and what that door needs off the run.

    Read back off ``meta.json`` and never re-derived from a command line, for the
    same reason the key scheme is: every candidate in one run must be scored the
    same way, or the scores in the buffer are not comparable with each other. A
    run dir written before the door existed answers False, which is the
    substitution Wheeler has always done.
    """
    return {
        "use_spec_evaluate": bool(meta.get("use_spec_evaluate")),
        "function_to_run": str(meta.get("function_to_run") or ""),
        "grouped": bool(str(meta.get("group_by", "") or "").strip()),
    }


# --------------------------------------------------------------------- verbs

@llmsr_app.command()
def metrics() -> None:
    """List every registered metric: the built-ins plus the scientist's own.

    This is the truthful listing the act offers from, because it is computed at
    call time after the user metric modules are imported.
    """
    failures = metrics_mod.load_user_metrics()
    typer.echo(json.dumps({
        "metrics": [
            {
                "key": key,
                "label": m.label,
                "data_shape": m.data_shape,
                "lower_is_better": m.lower_is_better,
                "builtin": key in metrics_mod.BUILTIN_METRICS,
            }
            for key, m in sorted(metrics_mod.METRICS.items())
        ],
        "sources": metrics_mod.user_metric_sources(),
        "errors": [{"source": f.source, "error": f.error} for f in failures],
    }, indent=2))


@llmsr_app.command()
def loaders() -> None:
    """List every registered data loader: the built-in csv plus the scientist's own.

    Computed at call time after the user loader modules are imported, so it is
    the truthful listing of what could read a recording right now. A loader is
    also where a bad group gets EXCLUDED before the strict per-group fit sees it.
    """
    failures = loaders_mod.load_user_loaders()
    typer.echo(json.dumps({
        "loaders": [
            {
                "key": key,
                "label": ldr.label,
                "builtin": key in loaders_mod.BUILTIN_LOADERS,
            }
            for key, ldr in sorted(loaders_mod.LOADERS.items())
        ],
        "sources": loaders_mod.user_loader_sources(),
        "errors": [{"source": f.source, "error": f.error} for f in failures],
    }, indent=2))


@llmsr_app.command()
def optimizers() -> None:
    """List every registered optimizer: the built-ins plus the scientist's own.

    Computed at call time, after the user optimizer modules are imported, so it
    is the truthful listing the act offers from. ``escalation`` states the rule
    ``auto`` applies, because a default that silently changes which optimizer
    produced a number would be the opposite of what this engine is for.
    """
    failures = optimizers_mod.load_user_optimizers()
    typer.echo(json.dumps({
        "optimizers": [
            {
                "key": key,
                "label": o.label,
                "builtin": key in optimizers_mod.BUILTIN_OPTIMIZERS,
                "escalates_to": o.escalates_to,
            }
            for key, o in sorted(optimizers_mod.OPTIMIZERS.items())
        ],
        "choices": optimizers_mod.choices(),
        "default": optimizers_mod.AUTO,
        "escalation": {
            "strategy": optimizers_mod.AUTO,
            "primary": optimizers_mod.AUTO_PRIMARY,
            "escalates_to": optimizers_mod.AUTO_ESCALATION,
            "when": "no start moved off its init",
        },
        "sources": optimizers_mod.user_optimizer_sources(),
        "errors": [{"source": f.source, "error": f.error} for f in failures],
    }, indent=2))


@llmsr_app.command()
def recipes() -> None:
    """List the worked scoring recipes: what each measures, assumes and costs.

    A recipe is a spec TEMPLATE plus the flag combination it pairs with, and
    ``scaffold-spec`` fills one against a real CSV. ``door`` is the thing to read
    first: ``spec`` recipes only mean anything with ``--use-spec-evaluate``,
    because Wheeler's default door never calls the spec's own ``evaluate``.

    ``ready`` reports whether the recipe's declared dependency is importable HERE.
    A recipe whose dependency is missing is still listed: it may be one install
    away, and hiding it would be the same invisibility the open registries exist
    to remove.
    """
    typer.echo(json.dumps({
        "recipes": [
            {
                **entry,
                "ready": all(
                    recipes_mod.is_importable(m) for m in entry["needs"]
                ),
            }
            for entry in recipes_mod.describe()
        ],
        "default": recipes_mod.DEFAULT_RECIPE,
        "doors": {
            recipes_mod.DOOR_DEFAULT: (
                "Wheeler's fit seam scores the run under the declared metric; the "
                "spec's own evaluate is never called. The recipe is a flag "
                "combination."
            ),
            recipes_mod.DOOR_SPEC: (
                "--use-spec-evaluate: the spec's own evaluate scores every "
                "candidate and owns the loss and the optimizer. The recipe is the "
                "evaluate body."
            ),
        },
    }, indent=2))


@llmsr_app.command()
def specs() -> None:
    """List the worked specs that ship with Wheeler, and their demo tables.

    These are what an act means by "the matching bundled spec". They are starting
    points modelled on the LLM-SR problem families, not copies of upstream's
    files, and every demo table is SYNTHETIC (generated by the script beside it,
    not the paper's data), which is why every entry says so.
    """
    typer.echo(json.dumps({
        "specs": recipes_mod.describe_specs(),
        "specs_dir": str(recipes_mod.specs_dir()),
        "data_dir": str(recipes_mod.demo_data_dir()),
        "note": (
            "Wheeler-written starting points modelled on the LLM-SR problem "
            "families, with synthetic demo tables. Neither upstream's spec files "
            "nor their datasets are reproduced here."
        ),
    }, indent=2))


@llmsr_app.command("scaffold-spec")
def scaffold_spec(
    data: Path = typer.Option(
        ..., exists=True, readable=True,
        help="the CSV the equation will be fitted to; its header names the inputs",
    ),
    recipe: str = typer.Option(
        recipes_mod.DEFAULT_RECIPE,
        help=(
            "which scoring recipe to fill in; run `wheeler llmsr recipes` for what "
            "each one measures, assumes and costs"
        ),
    ),
    group_by: str = typer.Option(
        "", "--group-by",
        help=(
            "column naming who each row belongs to. Excluded from the equation's "
            "inputs here exactly as the fit excludes it, so the generated "
            "signature matches what the run will actually pass."
        ),
    ),
    sigma_col: str = typer.Option(
        "", "--sigma-col",
        help=(
            "column holding each point's own standard deviation. Kept out of the "
            "equation (it describes the measurement, not the law) and read "
            "directly by the recipes that weight by it. Required by chi_squared."
        ),
    ),
    max_nparams: int = typer.Option(
        recipes_mod.DEFAULT_MAX_NPARAMS,
        help="free-constant budget written into the spec as MAX_NPARAMS",
    ),
    metric: str = typer.Option(
        "nmse",
        help="named only so the command line this prints is complete and runnable",
    ),
    docstring: str = typer.Option(
        "",
        help=(
            "the problem statement, which is what the generator actually reads. "
            "Default: a mechanical one naming the columns. Replacing it with real "
            "physics is the single highest-value edit to a scaffolded spec."
        ),
    ),
    out: Optional[Path] = typer.Option(
        None, "--out", help="also write the spec to this path",
    ),
) -> None:
    """Fill a recipe against a real CSV header and emit a runnable spec.

    The spec is the one thing that has to be WRITTEN before a run can start, and
    this writes the mechanical parts of it: the input names read off the header,
    the ``MAX_NPARAMS`` budget, a skeleton ``equation``, and the chosen recipe's
    ``evaluate``. It also prints the exact ``wheeler llmsr init`` command the
    recipe pairs with, because a scoring strategy and the flags that select it
    are one decision, not two.

    What it deliberately does NOT do is guess the science. The skeleton is the
    dullest form that uses every column, and the docstring is mechanical unless
    ``--docstring`` replaces it. Both are meant to be edited before the run.
    """
    try:
        scaffolded = recipes_mod.scaffold(
            recipe,
            data,
            group_by=group_by.strip(),
            sigma_col=sigma_col.strip(),
            max_nparams=max_nparams,
            docstring=docstring,
            metric=metric,
            spec_path=str(out.resolve()) if out is not None else "",
        )
    except KeyError as exc:
        raise typer.BadParameter(str(exc).strip("'")) from exc
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(scaffolded.text)

    typer.echo(json.dumps({
        **scaffolded.as_dict(),
        "spec_path": str(out.resolve()) if out is not None else "",
        "door": recipes_mod.get_recipe(recipe).door,
    }, indent=2))


@llmsr_app.command()
def init(
    spec: Path = typer.Option(..., exists=True, readable=True, help="spec .txt (skeleton + evaluate)"),
    data: list[str] = typer.Option(..., "--data", help=_DATA_HELP),
    metric: str = typer.Option(..., help=_METRIC_HELP),
    seed_from: str = typer.Option("", "--seed-from", help=_SEED_FROM_HELP),
    score_on: Optional[list[str]] = typer.Option(None, "--score-on", help=_SCORE_ON_HELP),
    generator: str = typer.Option("claude", help="candidate generator: claude | codex"),
    run_id: Optional[str] = typer.Option(None, help="explicit run id (default: random)"),
    max_nparams: Optional[int] = typer.Option(None, help="free-constant budget (default: spec MAX_NPARAMS or 10)"),
    timeout: int = typer.Option(30, help="per-fit timeout seconds"),
    group_by: str = typer.Option(
        "",
        help=(
            "column naming who each row belongs to (cell, trial, subject). Each "
            "group refits its OWN constants under the same form, so a law whose "
            "constants vary across individuals is not charged for that variation. "
            "Default: ungrouped, one shared parameter set."
        ),
    ),
    optimizer: str = typer.Option(optimizers_mod.AUTO, help=_OPTIMIZER_HELP),
    restarts: int = typer.Option(
        fit_mod.DEFAULT_RESTARTS,
        help=(
            "extra optimizer starts beyond the all-ones init. More starts means "
            "a form whose constants live far from 1 is less likely to be rejected "
            "for a fit that never left a flat region, at linear cost in fit time."
        ),
    ),
    seed: int = typer.Option(
        fit_mod.DEFAULT_SEED,
        help="RNG seed for the random restarts; fixed, so a run replays exactly",
    ),
    use_spec_evaluate: bool = typer.Option(
        False,
        "--use-spec-evaluate",
        help=(
            "score every candidate by calling the SPEC'S OWN @evaluate.run, which "
            "is what upstream LLM-SR does, instead of Wheeler's fit/metric seam. "
            "The spec then owns the loss, the optimizer and any framework it "
            "imports (upstream's torch spec trains a module for 10,000 steps "
            "inside evaluate). Off by default, because Wheeler's seam is what "
            "makes the metric pluggable, the constants recoverable and the "
            "per-unit refit possible. Never inferred from the spec text: a "
            "scoring change nobody asked for is exactly what this flag exists to "
            "prevent."
        ),
    ),
) -> None:
    """Create a run: bind spec + data + metric + generator + optimizer, seed the buffer."""
    metric_obj = _metric_for(metric)
    opt_key = _optimizer_for(optimizer)
    gen = generator.strip().lower()
    if gen not in _GENERATORS:
        raise typer.BadParameter(f"generator must be one of {_GENERATORS}")
    if restarts < 0:
        raise typer.BadParameter("restarts must be >= 0")

    # The dataset roles, resolved once and frozen onto the run. The key SCHEME in
    # particular: two candidates in one run must present the vendored buffer with
    # identical keys, so it is decided here and read back from meta.json forever
    # after, never re-derived from a later command line.
    datasets = data_mod.parse_datasets(data)
    scored = data_mod.resolve_score_on(datasets, score_on or [])
    seed_ds = data_mod.resolve_seed_from(datasets, seed_from)
    scheme = data_mod.key_scheme(scored)

    spec_text = spec.read_text()
    fte, ftr = _extract_names(spec_text)
    template = code_manipulation.text_to_program(spec_text)

    if max_nparams is None:
        m = re.search(r"MAX_NPARAMS\s*=\s*(\d+)", spec_text)
        max_nparams = int(m.group(1)) if m else 10

    rid = (run_id or uuid.uuid4().hex[:12]).strip()
    run_dir = _RUNS_ROOT / rid
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "run_id": rid,
        "spec_path": str(spec.resolve()),
        # The first SCORED dataset. `data_path` has always meant "the table this
        # run's constants are fitted on", and the scored datasets are exactly
        # that, so held-out scoring and the runnable footer keep pointing at a
        # table the run really trained on. Identical to the old value whenever
        # there is one dataset.
        "data_path": scored[0].path,
        # The dataset roles, in full. `datasets` is every declaration in order,
        # `score_on` is the objective, `seed_from` is where the FORM came from,
        # and `score_key_scheme` is how a unit is named in the score vector.
        "datasets": [d.as_dict() for d in datasets],
        "seed_from": seed_ds.name,
        "score_on": [d.name for d in scored],
        "score_key_scheme": scheme,
        "metric": metric_obj.key,
        "generator": gen,
        "function_to_evolve": fte,
        "function_to_run": ftr,
        "max_nparams": max_nparams,
        "timeout": timeout,
        "group_by": group_by.strip(),
        # The fit knobs, bound to the run so every later submit fits the same way.
        "optimizer": opt_key,
        "restarts": restarts,
        "seed": seed,
        # Which scoring door. Bound here so every candidate in the run is scored
        # the same way, and recorded even when False so a reader of the run never
        # has to infer it from an absence.
        "use_spec_evaluate": bool(use_spec_evaluate),
        "created": _now(),
        "created_epoch": time.time(),
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # seed the buffer with the spec's initial equation body (submission 0, all islands)
    units = _units_for(meta, metric_obj)
    # A declared-but-not-scored dataset is read once here and thrown away, purely
    # so a typo or an unreadable file fails at `init` rather than at whatever
    # later step first reaches for it.
    held_out = [d for d in datasets if d not in scored]
    if held_out:
        data_mod.load_units(
            held_out, metric_obj, group_by=group_by.strip(), scheme=scheme,
        )
    seed_body = template.get_function(fte).body
    _t0 = time.time()
    result, program, _fn = _score_body(
        seed_body, None, template, fte,
        units, metric_obj, max_nparams, timeout,
        progress_path=run_dir / runs_mod.PROGRESS_FILE,
        **_fit_knobs(meta), **_spec_knobs(meta),
    )
    _append_submission(run_dir, {
        "sample_order": 0,
        "body": seed_body,
        "program": program,
        "valid": result.valid,
        "score": result.score,
        "value": result.value,
        "params": result.params,
        "per_group": result.per_group,
        "per_group_value": result.per_group_value,
        "params_per_group": result.params_per_group,
        "optimizer": result.optimizer,
        "optimizer_per_group": result.optimizer_per_group,
        "island_id": None,
        "version_generated": None,
        "seed": True,
        "error": result.error,
        "rejection_reason": result.rejection_reason,
        "fit_seconds": round(time.time() - _t0, 4),
        "at_epoch": time.time(),
    })
    _write_heartbeat(run_dir, meta)

    typer.echo(json.dumps({
        "run_id": rid,
        "run_dir": str(run_dir),
        "metric": metric_obj.key,
        "generator": gen,
        "optimizer": opt_key,
        "function_to_evolve": fte,
        "datasets": [d.as_dict() for d in datasets],
        "seed_from": seed_ds.name,
        "score_on": [d.name for d in scored],
        "score_key_scheme": scheme,
        "score_keys": [u.key for u in units],
        "use_spec_evaluate": bool(use_spec_evaluate),
        "seed_valid": result.valid,
        "seed_value": result.value,
    }))


@llmsr_app.command()
def prompt(
    run: str = typer.Option(..., help="run id or run dir"),
) -> None:
    """Emit the next prompt (best-so-far skeletons) for the generator sub-agent.

    The prompt TEXT is the vendored buffer's, untouched. What is emitted beside it
    is the run's dataset roles, because the generator has to be shown a table to
    propose a form from, and which table that is (``seed_from``) is a declared
    choice rather than whichever one happens to be scored.
    """
    run_dir = _run_dir(run)
    meta = _read_meta(run_dir)
    template, db, _fte = _rebuild_buffer(run_dir, meta)
    p = db.get_prompt()

    prompts_dir = run_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    n = len(list(prompts_dir.glob("*.txt")))
    prompt_file = prompts_dir / f"{n}.txt"
    prompt_file.write_text(p.code)

    datasets = data_mod.datasets_from_meta(meta)
    seed_ds = data_mod.resolve_seed_from(datasets, str(meta.get("seed_from", "") or ""))
    typer.echo(json.dumps({
        "island_id": p.island_id,
        "version_generated": p.version_generated,
        "prompt_file": str(prompt_file),
        "function_to_evolve": meta["function_to_evolve"],
        "seed_from": seed_ds.as_dict(),
        "score_on": [d.name for d in data_mod.scored_from_meta(meta)],
        "prompt": p.code,
    }))


@llmsr_app.command()
def status(
    run: str = typer.Option(..., help="run id or run dir"),
) -> None:
    """Heartbeat: where a running (or finished) search is right now.

    Prints samples so far, how many were valid, the best metric value + equation,
    plus ``phase`` (init | fitting | idle | done), ``seconds_since_update``, and
    the in-flight ``progress`` ping when a fit is mid-flight. Together those three
    answer "is it wedged?": a fit stuck on group 7 of 40 reports ``fitting`` with
    a ``seconds_since_update`` that keeps climbing. Safe to ping mid-run: it only
    reads.
    """
    run_dir = _run_dir(run)
    meta = _read_meta(run_dir)
    typer.echo(json.dumps(status_payload(run_dir, meta)))


@llmsr_app.command()
def submit(
    run: str = typer.Option(..., help="run id or run dir"),
    body_file: Path = typer.Option(..., exists=True, readable=True, help="file with the equation body"),
    island_id: int = typer.Option(..., help="island id from `prompt`"),
    version_generated: int = typer.Option(..., help="version from `prompt`"),
) -> None:
    """Fit + score one candidate body and register it into the buffer."""
    run_dir = _run_dir(run)
    meta = _read_meta(run_dir)
    metric_obj = _metric_for(meta["metric"])
    template, db, fte = _rebuild_buffer(run_dir, meta)
    units = _units_for(meta, metric_obj)

    body = body_file.read_text()
    _t0 = time.time()
    result, program, fn = _score_body(
        body, version_generated, template, fte, units,
        metric_obj, meta["max_nparams"], meta["timeout"],
        progress_path=run_dir / runs_mod.PROGRESS_FILE,
        **_fit_knobs(meta), **_spec_knobs(meta),
    )
    fit_seconds = time.time() - _t0
    if result.valid:
        # result.valid, so score is not None.
        assert result.score is not None
        db.register_program(
            fn, island_id, result.per_group or {fit_mod.UNGROUPED: result.score}
        )

    sample_order = len(_read_submissions(run_dir))
    _append_submission(run_dir, {
        "sample_order": sample_order,
        "body": body,
        "program": program,
        "valid": result.valid,
        "score": result.score,
        "value": result.value,
        "params": result.params,
        "per_group": result.per_group,
        "per_group_value": result.per_group_value,
        "params_per_group": result.params_per_group,
        "optimizer": result.optimizer,
        "optimizer_per_group": result.optimizer_per_group,
        "island_id": island_id,
        "version_generated": version_generated,
        "seed": False,
        "error": result.error,
        "rejection_reason": result.rejection_reason,
        "fit_seconds": round(fit_seconds, 4),
        "at_epoch": time.time(),
    })
    _write_heartbeat(run_dir, meta)
    typer.echo(json.dumps({
        "valid": result.valid,
        "value": result.value,
        "score": result.score,
        "optimizer": result.optimizer,
        "error": result.error,
        "rejection_reason": result.rejection_reason,
        "sample_order": sample_order,
    }))


@llmsr_app.command()
def best(
    run: str = typer.Option(..., help="run id or run dir"),
    select: str = typer.Option(
        "fit",
        help="winner selection: fit (lowest error) | ood (best extrapolation) | "
        "parsimony (simplest good-enough form). ood/parsimony target the true LAW, "
        "not the best fit.",
    ),
) -> None:
    """Write best.json: the winning equation, its fitted constants, and metrics."""
    run_dir = _run_dir(run)
    meta = _read_meta(run_dir)
    mode = select.strip().lower()
    if mode not in _SELECT_MODES:
        raise typer.BadParameter(f"select must be one of {_SELECT_MODES}")
    subs = _read_submissions(run_dir)
    valid = [s for s in subs if s.get("valid") and s.get("score") is not None]
    # A candidate a hard constraint rejected is not in `valid`, so it can never
    # win however well it scored. The count is reported so that truncation of the
    # frontier is visible rather than silent.
    rejected = _n_constraint_rejected(subs)
    # Absent (not empty) on a run bound to one default-named dataset, so every
    # existing reader of best.json sees exactly the file it saw before. The block
    # appears the moment naming a dataset could matter, which is the same
    # condition that qualifies the score keys.
    scheme = data_mod.scheme_from_meta(meta)
    multi = scheme == data_mod.SCHEME_DATASET
    # `selection.py`'s footers address ONE file: the flat one applies a single
    # parameter vector to `data_path`, the grouped one filters that file's rows
    # by a group column. Both are correct exactly while the run's score keys are
    # names that file can supply, which is every run under `scheme=group` plus
    # the ungrouped single-scored-table case (one unit, one vector, one file).
    # Anything else gets the constants without a runner rather than a runner that
    # raises or, worse, quietly matches nothing.
    one_file = not multi or (
        not meta.get("group_by") and len(data_mod.scored_from_meta(meta)) == 1
    )

    # best.json is the FINAL result only. The full per-candidate search trail
    # (bodies, programs, params, scores) stays in submissions.jsonl in the run
    # dir; the graph adapter records the winner, never intermediate candidates.
    if not valid:
        payload = {
            "status": "failed",
            "run_id": meta["run_id"],
            "spec_path": meta["spec_path"],
            "data_path": meta["data_path"],
            "metric": meta["metric"],
            "generator": meta["generator"],
            "equation": None,
            "params": [],
            **({"datasets": _dataset_report(meta, None)} if multi else {}),
            "program": None,
            "metrics": {},
            "metrics_refit": {},
            "optimizer": _optimizer_report(meta, None),
            "timing": _timing(meta, subs),
            "n_samples": len(subs),
            "n_valid": 0,
            "n_constraint_rejected": rejected,
            "error": "no valid equation was found",
        }
        (run_dir / "best.json").write_text(json.dumps(payload, indent=2))
        typer.echo(json.dumps({
            "status": "failed",
            "n_samples": len(subs),
            "n_valid": 0,
            "n_constraint_rejected": rejected,
        }))
        raise typer.Exit(code=1)

    winner = _select_winner(valid, meta, mode)
    metric_key = meta["metric"]
    report = _dataset_report(meta, winner) if multi else None
    # A grouped run's constants are a TABLE, not a vector (`winner["params"]` is
    # empty for it by construction), so the per-group fields are passed through
    # and the written .py filters rows by group. Without them the "durable,
    # re-runnable" artifact does not run for a grouped run. A run whose keys span
    # SEVERAL files gets `dataset_report` instead, and the footer then emits the
    # constants without a runner rather than one that cannot address them.
    # A winner with NO constants at all, which only the spec-evaluate door can
    # produce: upstream's bare-float contract has nowhere to return them. Every
    # footer writes constants, so with none to write the flat one would emit a
    # runner that raises. Checked against the run's declared door as well as the
    # winner, so nothing on the default path can reach it.
    no_constants = (
        bool(meta.get("use_spec_evaluate"))
        and not winner["params"]
        and not (winner.get("params_per_group") or {})
    )
    program = _runnable_program(winner["program"], winner["params"], metric_key,
                                winner["value"], meta["data_path"], meta["function_to_evolve"],
                                _metric_for(metric_key).data_shape,
                                group_by=str(meta.get("group_by", "") or ""),
                                params_per_group=winner.get("params_per_group") or {},
                                value_per_group=winner.get("per_group_value") or {},
                                dataset_report=None if one_file else report,
                                no_constants=no_constants)

    # Generalization, asked BOTH ways on the sibling in-domain / out-of-domain
    # test sets. `metrics` applies the winner's constants unchanged (do the
    # CONSTANTS transfer), `metrics_refit` refits them from scratch under the same
    # form (does the FORM transfer, which is what symbolic regression is looking
    # for). They stay in separate labelled dicts so neither can be read as the
    # other. This split scoring is WHEELER'S addition, not upstream's: LLM-SR
    # ships the datasets as `<problem>/{train,test_id,test_ood}.csv`, but its own
    # `main.py` loads only `train.csv` and nothing in the pipeline opens the test
    # splits. The splits are theirs; scoring against them is ours.
    metrics_out, metrics_refit = _split_metrics(meta, winner)

    payload = {
        "status": "completed",
        "run_id": meta["run_id"],
        "spec_path": meta["spec_path"],
        "data_path": meta["data_path"],
        "metric": metric_key,
        "generator": meta["generator"],
        "equation": winner["body"].strip("\n"),
        "params": winner["params"],
        # Grouped runs only. `params` above is empty for them, because there IS no
        # single parameter vector: the whole point is that each group keeps its
        # own. Absent (not empty) on an ungrouped run, so existing readers are
        # untouched.
        **(
            {
                "group_by": meta.get("group_by", ""),
                "params_per_group": winner.get("params_per_group") or {},
                "value_per_group": winner.get("per_group_value") or {},
                # Escalation is per group, so a grouped winner can be "mixed";
                # this is what resolves that into which group used what.
                "optimizer_per_group": winner.get("optimizer_per_group") or {},
            }
            if meta.get("group_by")
            else {}
        ),
        # Multi-dataset runs only. Which tables the search optimized against and
        # which it merely declared, each labelled by regime so a held-out number
        # can never be read as a scored one or the other way round.
        **({"datasets": report} if multi else {}),
        "program": program,
        "metrics": metrics_out,
        # The same splits with the constants REFITTED. Kept apart from `metrics`
        # rather than folded in under a suffix, because a refit number had its
        # constants fitted on the split it reports, so it is a held-out claim
        # about the FORM only. The graph's regime labeller reads `metrics`.
        "metrics_refit": metrics_refit,
        "optimizer": _optimizer_report(meta, winner),
        "selection": {
            "mode": mode,
            "complexity": _equation_complexity(winner["body"]),
            "candidates": len(valid),
            # What `--select ood` ranked on, when it ranked. Named because the
            # quantity is a choice: fixed-theta extrapolation, under the run's own
            # metric, never a refit (see `selection._candidate_ood`).
            "ranked_on": (
                f"test_ood fixed-theta {metric_key}" if mode == "ood" else f"train {metric_key}"
            ),
        },
        "timing": _timing(meta, subs),
        "n_samples": len(subs),
        "n_valid": len(valid),
        "n_constraint_rejected": rejected,
    }
    (run_dir / "best.json").write_text(json.dumps(payload, indent=2))
    typer.echo(json.dumps({
        "status": "completed",
        "metric": metric_key,
        "optimizer": winner.get("optimizer", ""),
        "value": winner["value"],
        "n_samples": len(subs),
        "n_valid": len(valid),
        "n_constraint_rejected": rejected,
        "best_json": str(run_dir / "best.json"),
    }))


@llmsr_app.command()
def transfer(
    run: str = typer.Option(..., help="run id or run dir"),
    data: Path = typer.Option(
        ..., exists=True, readable=True,
        help="held-out table to transfer the discovered form onto",
    ),
    candidate: Optional[int] = typer.Option(
        None,
        help=(
            "sample_order of an explicit candidate to transfer; default: the "
            "winner this run's own selection rules pick"
        ),
    ),
    select: str = typer.Option(
        "fit",
        help=(
            "how to pick the candidate when --candidate is not given: fit | ood | "
            "parsimony, the same rules as `best`"
        ),
    ),
    group_by: Optional[str] = typer.Option(
        None,
        help=(
            "column naming who each row of the TRANSFER data belongs to. Default: "
            "the run's own --group-by. Name it here when the held-out file is "
            "grouped and the training file was not (several held-out cells, one "
            "training cell), so each cell refits its own constants."
        ),
    ),
) -> None:
    """Refit the discovered FORM on held-out data: an on-demand generalization test.

    Reports TWO numbers side by side, labelled, because "does it generalize" is
    two questions. The refit asks whether the FORM still fits once its constants
    are fitted here; the fixed-theta number asks whether the source run's own
    CONSTANTS transfer. A law that governs a new cell with different constants is
    the same law, so the first is what symbolic regression is looking for, and
    until this verb existed only the second was ever measured.

    Writes ``transfer.json`` into the run dir. Never appends to
    ``submissions.jsonl`` and never registers into the experience buffer: a
    number that fed back into the search would stop being a holdout.

    Exits non-zero when the candidate fails to refit on any group, matching the
    strictness of the per-group fit itself: one blind group invalidates the
    candidate rather than being quietly dropped from an average.
    """
    run_dir = _run_dir(run)
    meta = _read_meta(run_dir)
    mode = select.strip().lower()
    if mode not in _SELECT_MODES:
        raise typer.BadParameter(f"select must be one of {_SELECT_MODES}")

    subs = _read_submissions(run_dir)
    n_valid = len([s for s in subs if s.get("valid") and s.get("score") is not None])
    try:
        cand, selected_by = transfer_mod.resolve_candidate(subs, meta, mode, candidate)
    except LookupError as exc:
        raise typer.BadParameter(str(exc)) from exc

    payload = transfer_mod.transfer_report(
        meta, cand, data,
        group_by if group_by is not None else str(meta.get("group_by", "") or ""),
        selected_by=selected_by,
        n_valid=n_valid,
        run_dir=run_dir,
    )
    out_path = run_dir / transfer_mod.TRANSFER_FILE
    out_path.write_text(json.dumps(payload, indent=2))

    typer.echo(json.dumps({
        "status": payload["status"],
        "metric": payload["metric"],
        "groups": payload["groups"],
        "refit_value": payload["refit"]["value"],
        "fixed_theta_value": payload["fixed_theta"]["value"],
        "sample_order": payload["candidate"]["sample_order"],
        "selected_by": selected_by,
        "error": payload["refit"]["error"],
        "transfer_json": str(out_path),
    }))
    if payload["status"] != "completed":
        raise typer.Exit(code=1)
