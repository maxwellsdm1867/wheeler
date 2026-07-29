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

import numpy as np
import typer

from . import fit as fit_mod
from . import metrics as metrics_mod
from . import runs as runs_mod
from .data import _as_groups, _load_data
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


def _metric_for(key: str) -> metrics_mod.Metric:
    """Resolve a metric by name, importing the scientist's metric modules first."""
    metrics_mod.load_user_metrics()
    try:
        return metrics_mod.get_metric(key)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc


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
    groups: list[tuple[str, np.ndarray, object]],
    metric,
    max_nparams: int,
    timeout: int,
    progress_path: Optional[Path] = None,
) -> tuple[fit_mod.FitResult, str, object]:
    """Build the program from a body, fit + score it. Returns (result, program, fn).

    ``progress_path`` is the during-the-fit channel: the fit refreshes it as each
    group lands, so ``status`` can answer where a long refit has got to.
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
    result = fit_mod.evaluate_body_grouped(
        program,
        fte,
        groups,
        metric,
        max_nparams=max_nparams,
        timeout_seconds=timeout,
        progress_path=progress_path,
    )
    return result, program, fn


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
def init(
    spec: Path = typer.Option(..., exists=True, readable=True, help="spec .txt (skeleton + evaluate)"),
    data: Path = typer.Option(..., exists=True, readable=True, help="training CSV (last column = target)"),
    metric: str = typer.Option(..., help=_METRIC_HELP),
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
) -> None:
    """Create a run: bind spec + data + metric + generator, seed the buffer."""
    metric_obj = _metric_for(metric)
    gen = generator.strip().lower()
    if gen not in _GENERATORS:
        raise typer.BadParameter(f"generator must be one of {_GENERATORS}")

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
        "data_path": str(data.resolve()),
        "metric": metric_obj.key,
        "generator": gen,
        "function_to_evolve": fte,
        "function_to_run": ftr,
        "max_nparams": max_nparams,
        "timeout": timeout,
        "group_by": group_by.strip(),
        "created": _now(),
        "created_epoch": time.time(),
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # seed the buffer with the spec's initial equation body (submission 0, all islands)
    X, y, labels = _load_data(
        str(meta["data_path"]), metric_obj, str(meta.get("group_by", ""))
    )
    seed_body = template.get_function(fte).body
    _t0 = time.time()
    result, program, _fn = _score_body(
        seed_body, None, template, fte,
        _as_groups(X, y, labels), metric_obj, max_nparams, timeout,
        progress_path=run_dir / runs_mod.PROGRESS_FILE,
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
        "function_to_evolve": fte,
        "seed_valid": result.valid,
        "seed_value": result.value,
    }))


@llmsr_app.command()
def prompt(
    run: str = typer.Option(..., help="run id or run dir"),
) -> None:
    """Emit the next prompt (best-so-far skeletons) for the generator sub-agent."""
    run_dir = _run_dir(run)
    meta = _read_meta(run_dir)
    template, db, _fte = _rebuild_buffer(run_dir, meta)
    p = db.get_prompt()

    prompts_dir = run_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    n = len(list(prompts_dir.glob("*.txt")))
    prompt_file = prompts_dir / f"{n}.txt"
    prompt_file.write_text(p.code)

    typer.echo(json.dumps({
        "island_id": p.island_id,
        "version_generated": p.version_generated,
        "prompt_file": str(prompt_file),
        "function_to_evolve": meta["function_to_evolve"],
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
    X, y, labels = _load_data(
        str(meta["data_path"]), metric_obj, str(meta.get("group_by", ""))
    )

    body = body_file.read_text()
    _t0 = time.time()
    result, program, fn = _score_body(
        body, version_generated, template, fte, _as_groups(X, y, labels),
        metric_obj, meta["max_nparams"], meta["timeout"],
        progress_path=run_dir / runs_mod.PROGRESS_FILE,
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
            "program": None,
            "metrics": {},
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
    # A grouped run's constants are a TABLE, not a vector (`winner["params"]` is
    # empty for it by construction), so the per-group fields are passed through
    # and the written .py filters rows by group. Without them the "durable,
    # re-runnable" artifact does not run for a grouped run.
    program = _runnable_program(winner["program"], winner["params"], metric_key,
                                winner["value"], meta["data_path"], meta["function_to_evolve"],
                                _metric_for(metric_key).data_shape,
                                group_by=str(meta.get("group_by", "") or ""),
                                params_per_group=winner.get("params_per_group") or {},
                                value_per_group=winner.get("per_group_value") or {})

    # Generalization: apply the TRAIN-fitted equation (no re-fit) to the sibling
    # in-domain / out-of-domain test sets, reporting both MSE and NMSE per split.
    # This split scoring is WHEELER'S addition, not upstream's: LLM-SR ships the
    # datasets as `<problem>/{train,test_id,test_ood}.csv`, but its own `main.py`
    # loads only `train.csv` and nothing in the pipeline opens the test splits.
    # The splits are theirs; scoring against them is ours.
    metrics_out = _split_metrics(meta, winner)

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
            }
            if meta.get("group_by")
            else {}
        ),
        "program": program,
        "metrics": metrics_out,
        "selection": {
            "mode": mode,
            "complexity": _equation_complexity(winner["body"]),
            "candidates": len(valid),
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
        "value": winner["value"],
        "n_samples": len(subs),
        "n_valid": len(valid),
        "n_constraint_rejected": rejected,
        "best_json": str(run_dir / "best.json"),
    }))
