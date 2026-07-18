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
"""

from __future__ import annotations

import ast
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import typer

from . import fit as fit_mod
from . import metrics as metrics_mod
from .vendor import buffer as buffer_mod
from .vendor import code_manipulation, config as config_lib, evaluator

logger = logging.getLogger(__name__)

llmsr_app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="LLM-SR equation discovery: drive the evolutionary search from Claude Code.",
)

_GENERATORS = ("claude", "codex")
_RUNS_ROOT = Path(".wheeler/llmsr/runs")


# --------------------------------------------------------------------------- io

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_dir(run: str) -> Path:
    """Accept either a run id or a run-dir path; return the run dir."""
    p = Path(run)
    if p.is_dir() and (p / "meta.json").exists():
        return p
    candidate = _RUNS_ROOT / run
    if (candidate / "meta.json").exists():
        return candidate
    raise typer.BadParameter(f"no run found for {run!r} (looked at {p} and {candidate})")


def _read_meta(run_dir: Path) -> dict:
    return json.loads((run_dir / "meta.json").read_text())


def _load_xy(data_path: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.genfromtxt(data_path, delimiter=",", skip_header=1)
    return data[:, :-1], data[:, -1].reshape(-1)


def _read_submissions(run_dir: Path) -> list[dict]:
    path = run_dir / "submissions.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # Tolerate a torn/partial line (an interrupted append, a crash mid-write)
            # instead of bricking every subsequent verb that replays the log.
            logger.warning("skipping unparseable submissions line in %s", path)
    return out


def _append_submission(run_dir: Path, record: dict) -> None:
    with (run_dir / "submissions.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")


def _progress(run_dir: Path, meta: dict) -> dict:
    """Current run state: how many samples, how many valid, and the best so far."""
    subs = _read_submissions(run_dir)
    valid = [s for s in subs if s.get("valid") and s.get("score") is not None]
    best = max(valid, key=lambda s: s["score"]) if valid else None
    created_epoch = meta.get("created_epoch")
    elapsed = round(time.time() - created_epoch, 2) if created_epoch else None
    return {
        "run_id": meta["run_id"],
        "metric": meta["metric"],
        "generator": meta["generator"],
        "n_samples": len(subs),
        "n_valid": len(valid),
        "best_value": best["value"] if best else None,
        "best_equation": best["body"].strip("\n") if best else None,
        "best_sample_order": best["sample_order"] if best else None,
        "elapsed_seconds": elapsed,
        "fit_seconds_total": round(sum(s.get("fit_seconds", 0.0) for s in subs), 3),
    }


def _write_heartbeat(run_dir: Path, meta: dict) -> None:
    """Refresh heartbeat.json: a single timestamped snapshot of run progress so a
    ping during a long search shows where it is without replaying the whole log."""
    prog = _progress(run_dir, meta)
    prog["updated"] = _now()
    (run_dir / "heartbeat.json").write_text(json.dumps(prog, indent=2))


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
        db.register_program(fn, sub.get("island_id"), {"data": sub["score"]})
    return template, db, fte


def _score_body(
    body: str,
    version_generated: Optional[int],
    template,
    fte: str,
    X: np.ndarray,
    y: np.ndarray,
    metric,
    max_nparams: int,
    timeout: int,
) -> tuple[fit_mod.FitResult, str, object]:
    """Build the program from a body, fit + score it. Returns (result, program, fn)."""
    fn, program = evaluator._sample_to_program(body, version_generated, template, fte)
    if evaluator._calls_ancestor(program, fte):
        return fit_mod.FitResult(valid=False, error="calls an ancestor version"), program, fn
    result = fit_mod.evaluate_body(
        program, fte, X, y, metric, max_nparams=max_nparams, timeout_seconds=timeout
    )
    return result, program, fn


# --------------------------------------------------------------------- verbs

@llmsr_app.command()
def init(
    spec: Path = typer.Option(..., exists=True, readable=True, help="spec .txt (skeleton + evaluate)"),
    data: Path = typer.Option(..., exists=True, readable=True, help="training CSV (last column = target)"),
    metric: str = typer.Option(..., help=f"scoring metric; wired: {metrics_mod.available()}"),
    generator: str = typer.Option("claude", help="candidate generator: claude | codex"),
    run_id: Optional[str] = typer.Option(None, help="explicit run id (default: random)"),
    max_nparams: Optional[int] = typer.Option(None, help="free-constant budget (default: spec MAX_NPARAMS or 10)"),
    timeout: int = typer.Option(30, help="per-fit timeout seconds"),
) -> None:
    """Create a run: bind spec + data + metric + generator, seed the buffer."""
    try:
        metric_obj = metrics_mod.get_metric(metric)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc
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
        "created": _now(),
        "created_epoch": time.time(),
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # seed the buffer with the spec's initial equation body (submission 0, all islands)
    X, y = _load_xy(str(meta["data_path"]))
    seed_body = template.get_function(fte).body
    _t0 = time.time()
    result, program, _fn = _score_body(
        seed_body, None, template, fte, X, y, metric_obj, max_nparams, timeout
    )
    _append_submission(run_dir, {
        "sample_order": 0,
        "body": seed_body,
        "program": program,
        "valid": result.valid,
        "score": result.score,
        "value": result.value,
        "params": result.params,
        "island_id": None,
        "version_generated": None,
        "seed": True,
        "error": result.error,
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
    and when progress last advanced. Safe to ping mid-run: it only reads.
    """
    run_dir = _run_dir(run)
    meta = _read_meta(run_dir)
    hb = run_dir / "heartbeat.json"
    if hb.exists():
        typer.echo(hb.read_text().strip())
    else:
        typer.echo(json.dumps(_progress(run_dir, meta)))


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
    metric_obj = metrics_mod.get_metric(meta["metric"])
    template, db, fte = _rebuild_buffer(run_dir, meta)
    X, y = _load_xy(str(meta["data_path"]))

    body = body_file.read_text()
    _t0 = time.time()
    result, program, fn = _score_body(
        body, version_generated, template, fte, X, y,
        metric_obj, meta["max_nparams"], meta["timeout"],
    )
    fit_seconds = time.time() - _t0
    if result.valid:
        db.register_program(fn, island_id, {"data": result.score})

    sample_order = len(_read_submissions(run_dir))
    _append_submission(run_dir, {
        "sample_order": sample_order,
        "body": body,
        "program": program,
        "valid": result.valid,
        "score": result.score,
        "value": result.value,
        "params": result.params,
        "island_id": island_id,
        "version_generated": version_generated,
        "seed": False,
        "error": result.error,
        "fit_seconds": round(fit_seconds, 4),
        "at_epoch": time.time(),
    })
    _write_heartbeat(run_dir, meta)
    typer.echo(json.dumps({
        "valid": result.valid,
        "value": result.value,
        "score": result.score,
        "error": result.error,
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
            "error": "no valid equation was found",
        }
        (run_dir / "best.json").write_text(json.dumps(payload, indent=2))
        typer.echo(json.dumps({"status": "failed", "n_samples": len(subs), "n_valid": 0}))
        raise typer.Exit(code=1)

    winner = _select_winner(valid, meta, mode)
    metric_key = meta["metric"]
    program = _runnable_program(winner["program"], winner["params"], metric_key,
                                winner["value"], meta["data_path"], meta["function_to_evolve"])

    # Generalization: apply the TRAIN-fitted equation (no re-fit) to the sibling
    # in-domain / out-of-domain test sets, reporting both MSE and NMSE per split
    # (the paper's protocol). Train + any test_id.csv / test_ood.csv alongside the
    # training file.
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
    }
    (run_dir / "best.json").write_text(json.dumps(payload, indent=2))
    typer.echo(json.dumps({
        "status": "completed",
        "metric": metric_key,
        "value": winner["value"],
        "n_samples": len(subs),
        "n_valid": len(valid),
        "best_json": str(run_dir / "best.json"),
    }))


def _runnable_program(program: str, params, metric_key: str, value, data_path: str, fte: str) -> str:
    """Append fitted constants + a runnable main so the .py reproduces the answer."""
    footer = (
        "\n\n# --- Fitted result (discovered by LLM-SR via Wheeler) ---\n"
        f"FITTED_PARAMS = {list(params)!r}\n"
        f"METRIC = {{'name': {metric_key!r}, 'value': {value!r}}}\n\n"
        "if __name__ == '__main__':\n"
        "    import numpy as _np\n"
        f"    _d = _np.genfromtxt(r{data_path!r}, delimiter=',', skip_header=1)\n"
        "    _X, _y = _d[:, :-1], _d[:, -1].reshape(-1)\n"
        f"    _n = {fte}.__code__.co_argcount - 1\n"
        "    _cols = [_X[:, i] for i in range(_n)]\n"
        f"    _pred = {fte}(*_cols, _np.array(FITTED_PARAMS))\n"
        "    print('metric', METRIC)\n"
        "    print('prediction[:5]', _np.asarray(_pred).reshape(-1)[:5])\n"
    )
    return program + footer


def _timing(meta: dict, subs: list[dict]) -> dict:
    """How long the run took: total wall-clock (init to now), the active search
    window (first to last submit), and pure fit compute (sum of per-fit seconds).
    The difference between search and fit is generator (LLM) thinking time."""
    now = time.time()
    created = meta.get("created_epoch", now)
    epochs = [s["at_epoch"] for s in subs if "at_epoch" in s]
    search = round(max(epochs) - min(epochs), 2) if len(epochs) >= 2 else 0.0
    return {
        "created": meta.get("created"),
        "finished": _now(),
        "duration_seconds": round(now - created, 2),
        "search_seconds": search,
        "fit_seconds_total": round(sum(s.get("fit_seconds", 0.0) for s in subs), 3),
        "n_samples": len(subs),
    }


_SELECT_MODES = ("fit", "ood", "parsimony")
_PARSIMONY_TOL = 10.0  # a candidate within this factor of the best error is "as good"


def _equation_complexity(body: str) -> int:
    """Structural complexity of an equation body: the count of operations (BinOp,
    UnaryOp, Call, Attribute, Compare). A compact law scores low; a many-term
    polynomial or a NN-like blob scores high. Drives parsimony selection: among
    forms that fit comparably, the SIMPLEST is the more likely true law (Occam).
    """
    try:
        tree = ast.parse("def _f():\n" + body)
    except SyntaxError:
        return 10**6
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Call, ast.Attribute, ast.Compare))
    )


def _candidate_ood(meta: dict, cand: dict) -> float | None:
    """Held-out out-of-domain NMSE of a candidate (train-fitted, applied to
    test_ood). None when no OOD set exists. This is the extrapolation signal: the
    true law generalizes here, an overfit form does not."""
    sibling = Path(str(meta["data_path"])).parent / "test_ood.csv"
    if not sibling.exists():
        return None
    try:
        X, y = _load_xy(str(sibling))
    except OSError:
        return None
    return fit_mod.evaluate_fixed(
        cand["program"], meta["function_to_evolve"], X, y,
        cand["params"], metrics_mod.get_metric("nmse"),
    )


def _select_winner(valid: list[dict], meta: dict, mode: str) -> dict:
    """Choose the winning candidate. `fit` = lowest training error (best FITTER,
    the default, back-compatible). `ood` = best extrapolation (the discovery
    signal). `parsimony` = the SIMPLEST form among those that fit comparably well
    (Occam). The last two target the true LAW rather than the best fit."""
    if mode == "fit" or len(valid) == 1:
        return max(valid, key=lambda s: s["score"])

    for c in valid:
        c["_complexity"] = _equation_complexity(c["body"])
        c["_ood"] = _candidate_ood(meta, c)

    if mode == "ood":
        with_ood = [c for c in valid if c.get("_ood") is not None]
        if with_ood:
            return min(with_ood, key=lambda c: c["_ood"])
        return max(valid, key=lambda s: s["score"])  # no OOD set: fall back to fit

    # parsimony: among candidates whose training error is within a factor of the
    # best, pick the fewest operations (tie-break toward the better fit).
    best_err = min(-c["score"] for c in valid)
    threshold = max(best_err * _PARSIMONY_TOL, best_err + 1e-12)
    good = [c for c in valid if (-c["score"]) <= threshold] or valid
    return min(good, key=lambda c: (c["_complexity"], -c["score"]))


def _split_metrics(meta: dict, winner: dict) -> dict[str, float]:
    """Score the train-fitted winner on train + sibling test_id / test_ood sets.

    Both MSE and NMSE per split. The LLM-SR datasets store
    ``<problem>/{train,test_id,test_ood}.csv``, so the test splits are siblings of
    the training file. Applies the fitted constants without re-fitting.
    """
    out: dict[str, float] = {}
    fte = meta["function_to_evolve"]
    program = winner["program"]
    params = winner["params"]
    train_path = str(meta["data_path"])
    splits = {"train": train_path}
    for name, fname in (("test_id", "test_id.csv"), ("test_ood", "test_ood.csv")):
        sibling = Path(train_path).parent / fname
        if sibling.exists():
            splits[name] = str(sibling)
    for split, path in splits.items():
        try:
            X, y = _load_xy(path)
        except OSError:
            continue
        for mkey in ("mse", "nmse"):
            val = fit_mod.evaluate_fixed(
                program, fte, X, y, params, metrics_mod.get_metric(mkey)
            )
            if val is not None:
                out[f"{mkey}_{split}"] = val
    return out
