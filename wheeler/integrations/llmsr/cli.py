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

import dataclasses
import json
import logging
import math
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
    append_next_submission,
    claim_prompt,
    scored_metric,
    scored_metric_report,
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

# The island model's default seed. Equal to `fit.DEFAULT_SEED`, which is what the
# founder draw was seeded with back when `--seed` drove both, so a run created
# with the default fit seed replays exactly as it always did. See `_island_seed`.
DEFAULT_ISLAND_SEED = 0

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


_LOADER_HELP = (
    "how a recording is READ off disk; built in: "
    + ", ".join(sorted(loaders_mod.BUILTIN_LOADERS))
    + ". A loader is also where a bad unit gets EXCLUDED before the fit sees it, "
    "which matters because the per-group fit is strict: one unfittable cell "
    "invalidates an otherwise correct law. Run `wheeler llmsr loaders` for every "
    "registered one, yours included."
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


def _loader_for(key: str) -> str:
    """Validate a loader choice, importing the scientist's modules first.

    Returns the canonical key to bind onto the run. Checked HERE, at ``init``,
    for the same reason ``_optimizer_for`` checks the optimizer: a name nothing
    can resolve would otherwise surface at whatever later verb first reaches for
    the tables. It is worse than that for a loader, in fact. The loader is what
    decides which units even exist, and the per-group fit is STRICT, so a run
    that silently fell back to csv when a registered loader was asked for would
    hand the search the very cells the scientist meant to exclude, and one
    unfittable cell invalidates a correct law.
    """
    loaders_mod.load_user_loaders()
    try:
        return loaders_mod.get_loader(key).key
    except KeyError as exc:
        raise typer.BadParameter(str(exc).strip("'")) from exc


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


def _quantize_scores(scores: dict, tolerance: float) -> dict:
    """Snap each unit's score to a log-magnitude bucket `tolerance` wide.

    **This is WHEELER'S, not the paper's protocol, and it is off by default.**
    Do not describe it as reproducing upstream. LLM-SR clusters on the raw
    continuous score with no discretization step, in the code
    (`_get_signature` returns `tuple(scores_per_test[k] for k in sorted(...))`,
    and `Signature = Tuple[float, ...]`) and in the paper, which says programs are
    "clustered based on their signature (defined by their score)" over a
    continuous `s = -MSE`. Nothing upstream rounds, bins, or buckets a score.

    Why it is offered anyway, and why upstream does not need it. The buffer keys a
    cluster on the score tuple, so with continuous scores every candidate gets a
    unique signature, every cluster holds one program, and
    `Cluster.sample_program` never has a choice: the length bias, which is
    upstream's only parsimony pressure, cannot act. That is equally true of the
    paper's own runs. It costs them almost nothing because their budget is
    ~10,000 candidates per problem over 10 islands (Appendix B: m=10, k=2, b=4,
    ~2,500 iterations), so an island holds ~1,000 singleton clusters and the
    score-weighted softmax over those clusters carries the selection on its own.
    At a stepped-loop budget of tens of candidates there is no such crowd, and
    the lost length pressure is a material fraction of the machinery.

    So: a small-budget accommodation, and a deviation to declare in any writeup.

    Two things were measured before settling on this shape, both on a real
    26-submission run whose signature is a tuple of FIVE per-unit scores:

    Rounding to significant figures does not work. A collision needs all five
    units to round identically, a conjunction whose probability collapses with
    the unit count: 3 significant figures gave 26 distinct signatures out of 26,
    2 gave 22, and only 1 significant figure did anything much. Log-magnitude
    bucketing at 0.25 decades gave 17 distinct signatures with 5 holding more
    than one program and no cluster larger than 5, which is the balance wanted.
    Wider is worse, not better: 0.5 decades put 11 of 26 in a single cluster, and
    one big cluster is as useless as all singletons.

    `tolerance` is a FACTOR, not a bucket index, because that is the question a
    scientist can answer: "two errors within 1.8x of each other are the same
    result." Internally it is a width in decades.

    The snapped value stays in ERROR UNITS rather than becoming a bucket number.
    That matters: the vendored buffer derives both the signature AND the cluster's
    selection score from this same dict, so returning small integers would leave
    the score-weighted softmax operating on bucket indices, whose spread divided
    by the 0.1 temperature makes selection almost deterministic. Snapping to the
    bucket's representative magnitude coarsens the score without rescaling it.

    `submissions.jsonl` keeps the raw values, so nothing is lost on disk and the
    tolerance can be changed by starting a new run.
    """
    width = math.log10(tolerance)
    out = {}
    for key, value in scores.items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            out[key] = value
            continue
        magnitude = abs(number)
        if number != number or not math.isfinite(number) or magnitude == 0.0:
            out[key] = number
            continue
        # A FIXED reference of 1.0, so bucket edges are the same for every
        # candidate in the run. That is the whole mechanism: two candidates
        # collide only if their scores land in the same absolute bucket.
        #
        # A per-candidate reference was tried here and destroyed the feature.
        # Deriving the reference from the dict being quantized buckets each
        # candidate against ITSELF, so its own largest-magnitude unit always
        # returns exactly. Measured: on a single-key signature the function was
        # the IDENTITY at every tolerance from 1.2 to 100.0, and on a three-unit
        # signature the other units collapsed onto that candidate's own maximum,
        # so (-0.718, -0.713, -0.755) became (-0.755, -0.755, -0.755) while a
        # different candidate became (-0.749, -0.749, -0.749): values changed,
        # signatures stayed unique, and a wider tolerance was strictly worse.
        # Cluster counts were identical to raw at 1.8, 3.2 and 10.0.
        #
        # It was introduced to fix a supposed singularity at |v| = 1, where
        # -0.99, -0.995, -0.80 and -0.999 all snap to -1.0. That is not a
        # singularity, it is the tolerance working: at 1.8 the bucket centred on
        # 1.0 spans |v| in [0.7454, 1.3416], a ratio of exactly 1.8000, and
        # 0.999 / 0.80 = 1.25 is inside it. 0.50 lands in the next bucket down,
        # correctly, since 0.999 / 0.50 = 2.0 is outside. Nor does the collapse
        # flatten selection: candidates sharing a signature are ONE cluster, and
        # the softmax runs over clusters, not within one. Inside a cluster
        # `sample_program` picks by LENGTH, which is the parsimony pressure this
        # option exists to restore.
        steps = round(math.log10(magnitude) / width)
        snapped = 10.0 ** (steps * width)
        out[key] = -snapped if number < 0 else snapped
    return out


# The replay quantizes only ABOVE this, because the tolerance is a FACTOR between
# two errors and a factor of 1 is a bucket of zero width. Validated at `init`
# rather than silently ignored at replay: see `_check_cluster_tolerance`.
MIN_CLUSTER_TOLERANCE = 1.0

# Beyond this the buckets are wide enough to be worth a word, without refusing:
# deliberate coarseness is a legitimate thing to ask for, and refusing it would
# be Wheeler choosing the science.
COARSE_CLUSTER_TOLERANCE = 10.0


def _check_cluster_tolerance(tolerance: Optional[float]) -> None:
    """Validate `--cluster-tolerance` AT init, where it is bound to the run.

    `0.5` and `1.0` were both accepted, written to `meta.json`, and then ignored
    by the replay, which quantizes only above 1.0. So a run's clustering was raw
    while its own metadata said otherwise, with no error and no warning. Both are
    plausible misreadings: `0.5` as a fraction, `1.0` as "off".

    Checked here for the same reason `--metric`, `--loader` and `--optimizer` are:
    a bad choice must fail one command rather than invalidate every candidate in
    the search.
    """
    if tolerance is None:
        return
    if tolerance <= MIN_CLUSTER_TOLERANCE:
        raise typer.BadParameter(
            f"--cluster-tolerance is a FACTOR between two errors, so it must be "
            f"greater than {MIN_CLUSTER_TOLERANCE} to widen a bucket at all; "
            f"{tolerance} would be recorded on the run and then ignored by the "
            f"replay, leaving the clustering raw while the metadata claimed "
            f"otherwise. Omit the flag for raw scores."
        )
    if tolerance > COARSE_CLUSTER_TOLERANCE:
        typer.echo(
            f"warning: --cluster-tolerance {tolerance} buckets more than a decade "
            f"of error into one cluster, which can collapse most of a run into a "
            f"single signature. Measured on a 26-submission run, half a decade "
            f"already put 11 of 26 together.",
            err=True,
        )


def _buffer_config(meta: dict):
    """The vendored buffer config, with this run's island settings applied.

    Read off `meta`, never off a later command line, for the same reason the key
    scheme is: the buffer is REPLAYED from `submissions.jsonl` on every verb, so a
    config that changed between calls would silently reassign islands and produce
    a different search state from the same submissions.

    A run dir written before these keys existed answers the vendored defaults, so
    it replays bit for bit as it always did.

    Why they are configurable at all: the defaults are `num_islands=10` and
    `reset_period=4*60*60`. Island reset (kill the weakest half, reseed from the
    survivors) is the whole diversity mechanism, and on a run shorter than four
    hours it NEVER FIRES. With 25 submissions over 10 islands, measured on the
    pilot's round 1, each island held 1 to 8 programs, median 2 to 3, so most had
    no population to evolve either. The result was 25 nearly-independent samples
    presented as an evolutionary search. Neither knob was reachable from the CLI,
    so there was no way to match the configuration to the budget.
    """
    base = config_lib.Config().experience_buffer
    islands = meta.get("islands")
    reset_period = meta.get("reset_period")
    changes = {}
    if islands:
        changes["num_islands"] = int(islands)
    if reset_period:
        changes["reset_period"] = int(reset_period)
    return dataclasses.replace(base, **changes) if changes else base


def _scores_for_buffer(
    meta: dict, scores: dict, tolerance: Optional[float] = None
) -> dict:
    """The score vector as the vendored buffer should see it, on EVERY path.

    One place, because there were two and they disagreed. The replay quantized
    (``cluster_tolerance > 1.0``) and ``submit``'s own live ``register_program``
    did not, so the buffer a reader inspects and the buffer a write builds were
    keyed differently for the same run. Harmless today only because ``submit``
    discards its buffer immediately after registering, which is a property of the
    caller and not of this seam: the moment anything reads state back out of
    ``submit``'s buffer, an unquantized signature would cluster differently from
    the same candidate on replay.

    ``tolerance`` is accepted so the replay can pass the value it already read off
    ``meta`` rather than re-reading it per submission.
    """
    if tolerance is None:
        tolerance = float(meta.get("cluster_tolerance") or 0.0)
    if tolerance and tolerance > MIN_CLUSTER_TOLERANCE:
        return _quantize_scores(scores, tolerance)
    return scores


def _island_seed(meta: dict) -> int:
    """The seed for the island model's own randomness, which is not the fit's.

    ``--seed`` is documented as the seed for the optimizer's random restarts, and
    that is all a reader expects it to touch. The replay also used it to seed the
    founder draw in ``reset_islands``, so varying ``--seed`` to probe whether a
    fit is robust to its starting points ALSO changed which islands got reset and
    which program reseeded them: two different experiments driven by one flag,
    with no surface saying so.

    So a run now records ``island_seed`` separately. A run dir written before that
    key existed falls back to ``seed``, which is what it replayed under, because
    the buffer is rebuilt from the log on every verb and a changed founder draw
    would silently reshape the search state of a run already on disk.
    """
    if "island_seed" in meta:
        return int(meta.get("island_seed") or 0)
    return int(meta.get("seed") or 0)


def _reset_islands_safely(db, run_dir: Path) -> None:
    """Reset the weakest islands, unless the buffer was never fully seeded.

    ``vendor/buffer.py::reset_islands`` draws a founder island from the survivors
    and registers ``self._best_program_per_island[founder]`` with no None check.
    Every island holds a program in a healthy run, because ``init`` registers the
    spec's seed candidate with ``island_id=None`` and the vendored
    ``register_program`` then loops every island. When the seed candidate is
    INVALID that never happens, and an island only gains a program when a
    submission names it.

    Measured in that state: 4 islands, one valid submission on island 0,
    ``--island-seed 1``, one reset due, and the draw picked an empty survivor:
    ``AttributeError: 'NoneType' object has no attribute 'keys'`` from inside
    vendored code. Safe at seed 0 purely by luck of the draw.

    ``vendor/`` is upstream's and is not forked, so the guard lives here. It skips
    rather than raises: a reset over a half-empty buffer is meaningless anyway
    (the weakest half is the empty islands), and raising would strand a run that
    can still be repaired by submitting to the islands that have nothing. Loud,
    on stderr, because a skipped reset is a real difference in the search.
    """
    unseeded = [
        i for i, program in enumerate(db._best_program_per_island) if program is None
    ]
    if not unseeded:
        db.reset_islands()
        return
    typer.echo(
        f"warning: skipping an island reset in run {run_dir}: islands {unseeded} "
        "hold no program, so the founder draw upstream makes could pick an empty "
        "one. This run's seed candidate was invalid, so the buffer was never "
        "seeded across all islands; a valid submission populates only the island "
        "it names. Fix the spec's seed body (or the data) and start a new run.",
        err=True,
    )


def _seed_error(subs: list[dict]) -> str:
    """Why the run's seed candidate failed, if it did. For the guards' messages."""
    for sub in subs:
        if sub.get("seed"):
            return "" if sub.get("valid") else str(sub.get("error") or "no error recorded")
    return ""


def _require_prompt_ready(db, run_dir: Path, subs: list[dict]) -> None:
    """Refuse to draw a prompt from a buffer that has empty islands.

    ``vendor/buffer.py::get_prompt`` picks an island uniformly at random and then
    asks it for a prompt; an island with no clusters gives ``_softmax`` an empty
    array. Measured on a run whose seed candidate was invalid: ``ValueError:
    zero-size array to reduction operation maximum which has no identity``, out of
    numpy, four frames inside vendored code.

    That is not a corner. ``init`` exits 0 when its seed fails, and an act hands
    the run straight to a generator sub-agent, so a numpy traceback is the first
    thing that agent sees and nothing in it names the actual problem. With one
    valid submission on island 0 of 4 the draw fails three times in four, which is
    worse than failing every time: it looks intermittent.

    All islands, not just the one about to be drawn, because the draw happens
    inside vendored code. In a healthy run every island holds a program from
    submission 0 onward (the seed registers on all of them), so this refuses
    exactly the runs that were already broken.
    """
    empty = [
        i for i, program in enumerate(db._best_program_per_island) if program is None
    ]
    if not empty:
        return
    seed_error = _seed_error(subs)
    n_valid = sum(1 for s in subs if s.get("valid"))
    raise typer.BadParameter(
        f"run {run_dir} cannot produce a prompt: islands {empty} hold no program, "
        f"and the prompt's island is drawn at random inside the vendored buffer. "
        f"{n_valid} of {len(subs)} recorded candidates were valid."
        + (
            f" The spec's own seed candidate failed to fit ({seed_error}), so the "
            "buffer was never seeded: normally that one candidate registers on "
            "every island. Fix the seed body in the spec (or the data it is fitted "
            "to) and start a new run."
            if seed_error
            else " Submit a valid candidate naming each empty island to populate "
            "them, or start a new run."
        )
    )


def _check_island_id(island_id: int, meta: dict) -> None:
    """Validate an island id BEFORE anything expensive runs. Both ends of it.

    Two measured holes, on a run configured for 4 islands:

    ``--island-id 99`` reached ``db.register_program`` after the fit had already
    completed and raised a bare ``IndexError: list index out of range`` from
    vendored code. Exit 1, no append, so the candidate AND the model call that
    produced it were both lost with no way to retry them.

    ``--island-id -1`` was ACCEPTED, recorded as ``-1``, and registered on the
    LAST island, because a negative index is a valid list index in Python and the
    only guard tested ``>= num_islands``. Nothing anywhere said the candidate had
    gone somewhere other than where the caller asked.

    Checked against the run's OWN island count, read off ``meta.json``, since
    ``--islands`` is bound at init and the recorded ids index it.
    """
    num_islands = _buffer_config(meta).num_islands
    if not 0 <= island_id < num_islands:
        raise typer.BadParameter(
            f"--island-id must be between 0 and {num_islands - 1} for this run "
            f"({num_islands} islands); got {island_id}. Take the id from "
            "`wheeler llmsr prompt`, which reports the island it drew."
        )


def _rebuild_buffer(run_dir: Path, meta: dict):
    """Replay submissions through the vendored register_program to restore state.

    Island reset is driven from the submissions' OWN timestamps, not from the wall
    clock, and that is a correctness fix rather than a refinement.

    Upstream runs as one long-lived process: the buffer sets
    ``_last_reset_time = time.time()`` once at construction, and
    ``register_program`` resets the weakest half of the islands whenever
    ``time.time() - _last_reset_time`` exceeds ``reset_period``. Wheeler inverted
    that loop into CLI verbs, so the buffer is CONSTRUCTED FRESH on every call and
    the timer restarts from zero each time. A replay finishes in milliseconds.
    The consequence, measured rather than reasoned about: with ``reset_period``
    forced to 1 second and 26 submissions replayed, ``reset_islands()`` was called
    ZERO times. Island reset was unreachable at any period, so the entire
    diversity half of the search silently did not exist, and no configuration
    could switch it on.

    Replaying with each submission's recorded ``at_epoch`` puts the resets back
    where a continuously running upstream process would have had them, following
    upstream's own rule: at most one reset per registration, re-anchored to the
    current stamp rather than to the last boundary.
    Submissions written before ``at_epoch`` existed simply never trigger one,
    and with the default four-hour period a short run does not either, so every
    run dir already on disk replays as it always did.

    numpy is seeded for the duration, because ``reset_islands`` draws its founder
    island at random and the buffer is replayed on every verb: unseeded,
    ``prompt`` and ``submit`` would rebuild DIFFERENT search states from identical
    submissions. The seed it uses is ``--island-seed``, which is NOT the fit's
    ``--seed``: see ``_island_seed`` for why the two were separated.
    """
    # Function-local, like the other heavy imports here: every `wheeler` CLI
    # invocation pays for a top-level one.
    import numpy as np

    spec = Path(meta["spec_path"]).read_text()
    fte = meta["function_to_evolve"]
    template = code_manipulation.text_to_program(spec)
    config = _buffer_config(meta)
    db = buffer_mod.ExperienceBuffer(config, template, fte)
    period = config.reset_period
    reset_every = int(meta.get("reset_every") or 0)
    cluster_tolerance = float(meta.get("cluster_tolerance") or 0.0)
    logical_reset_at: Optional[float] = None
    registered = 0

    state = np.random.get_state()
    np.random.seed(_island_seed(meta))
    try:
        for sub in _read_submissions(run_dir):
            if not sub.get("valid"):
                continue
            fn, _program = evaluator._sample_to_program(
                sub["body"], sub.get("version_generated"), template, fte
            )
            island_id = sub.get("island_id")
            # The island count is BAKED INTO the recorded ids, so it cannot change
            # after the first submission: the vendored buffer indexes a list and a
            # stale id raises IndexError several frames down, where it reads like a
            # corrupt run rather than an edited setting. Say what actually happened.
            #
            # A NEGATIVE id is the same class of defect wearing a disguise: it
            # indexes the list from the far end, so a recorded -1 registers on the
            # LAST island without raising anything at all. `submit` refuses one now
            # (`_check_island_id`); this catches the ones already on disk, which
            # were routed somewhere nobody chose.
            if island_id is not None and not 0 <= island_id < config.num_islands:
                raise typer.BadParameter(
                    f"submission {sub.get('sample_order')} was registered on island "
                    f"{island_id}, but this run is configured for "
                    f"{config.num_islands} islands (0 to {config.num_islands - 1}). "
                    "The island count is fixed once a run has submissions, because "
                    "the recorded ids index it. Start a new run to change it."
                )
            scores = _scores_for_buffer(meta, _scores_per_test(sub), cluster_tolerance)
            db.register_program(fn, island_id, scores)

            registered += 1

            # SAMPLE COUNT is the right clock for a stepped loop, and it takes
            # precedence when set. Upstream's period is wall clock because its
            # sampler runs continuously and emits thousands of candidates an
            # hour, so four hours is thousands of samples. Here a candidate costs
            # one model call and arrives roughly every two minutes, so the same
            # period in seconds is a wildly different number of samples.
            # Measured on this run: replaying 26 submissions spanning 48 minutes
            # of wall clock fired 48 resets at a 60-second period and 2905 at one
            # second, and every island collapsed to a single program, because a
            # reset wipes an island and reseeds it from one founder. Matching
            # upstream's clock does not match upstream's behaviour.
            if reset_every:
                if registered % reset_every == 0:
                    _reset_islands_safely(db, run_dir)
                continue

            at = sub.get("at_epoch")
            if at is None or not period:
                continue
            if logical_reset_at is None:
                logical_reset_at = float(at)
                continue
            # At most ONE reset per registration, re-anchored to THIS stamp, which
            # is what vendor/buffer.py:177-180 does: it re-anchors to time.time()
            # rather than to last + period, so a long idle gap costs one reset, not
            # a backlog of them. A catch-up `while` loop was here and over-fired:
            # measured against upstream's own code driven by a fake clock, at the
            # default 14400s period with one 14h pause it produced 3 resets where
            # upstream produced 1, and on a 31-submission run with two 13h pauses
            # 6 against 2, wiping populations upstream would have kept.
            if float(at) - logical_reset_at > period:
                _reset_islands_safely(db, run_dir)
                logical_reset_at = float(at)
    finally:
        np.random.set_state(state)
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
    islands: Optional[int] = typer.Option(
        None,
        help=(
            "islands in the experience buffer (default: upstream's 10). Match this "
            "to the sample budget: 25 samples over 10 islands leaves 2 to 3 "
            "programs each, which is no population to evolve."
        ),
    ),
    reset_period: Optional[int] = typer.Option(
        None,
        help=(
            "seconds of LOGICAL elapsed time between weakest-island resets "
            "(default: upstream's 14400). Upstream's clock, kept for fidelity, "
            "but mis-scaled for a stepped loop: prefer --reset-every."
        ),
    ),
    reset_every: Optional[int] = typer.Option(
        None,
        help=(
            "reset the weakest half of the islands every N accepted "
            "submissions. The right clock for a stepped loop, and it takes "
            "precedence over --reset-period. Aim for a handful of resets across "
            "the whole run: N around a third of the sample budget."
        ),
    ),
    cluster_tolerance: Optional[float] = typer.Option(
        None,
        help=(
            "two per-unit errors within this FACTOR of each other count as the "
            "same result when keying a cluster. Continuous scores otherwise give "
            "every candidate a unique signature, one program per cluster, and no "
            "clustering at all, which disables upstream's only parsimony "
            "pressure. 1.8 is a measured starting point; wider collapses "
            "everything into one cluster. Must be greater than 1.0, since it is a "
            "factor between two errors. Absent means raw, as before."
        ),
    ),
    group_by: str = typer.Option(
        "",
        help=(
            "column naming who each row belongs to (cell, trial, subject). Each "
            "group refits its OWN constants under the same form, so a law whose "
            "constants vary across individuals is not charged for that variation. "
            "Default: ungrouped, one shared parameter set."
        ),
    ),
    loader: str = typer.Option(loaders_mod.DEFAULT_LOADER, help=_LOADER_HELP),
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
        help=(
            "RNG seed for the FIT's random restarts, and nothing else; fixed, so a "
            "run replays exactly. It used to seed the island model's founder draw "
            "too, so probing whether a fit was robust to its starting points also "
            "changed which islands got reset: that is --island-seed now."
        ),
    ),
    island_seed: int = typer.Option(
        DEFAULT_ISLAND_SEED,
        help=(
            "RNG seed for the ISLAND MODEL's own randomness (which survivor "
            "reseeds a reset island). Separate from --seed because they answer "
            "different questions, and the buffer is replayed from the log on every "
            "verb, so this has to be fixed for a run to replay at all."
        ),
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
    loader_key = _loader_for(loader)
    opt_key = _optimizer_for(optimizer)
    gen = generator.strip().lower()
    if gen not in _GENERATORS:
        raise typer.BadParameter(f"generator must be one of {_GENERATORS}")
    if restarts < 0:
        raise typer.BadParameter("restarts must be >= 0")
    _check_cluster_tolerance(cluster_tolerance)

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
        # The island model, bound to the run. Absent means upstream's defaults,
        # so a run dir written before these existed replays unchanged. See
        # `_buffer_config` for why they must be read from here and not from a
        # later command line.
        "islands": islands,
        "reset_period": reset_period,
        "reset_every": reset_every,
        # Precision at which two candidates count as the same result for
        # clustering. Bound to the run: it changes the buffer's shape, and the
        # buffer is replayed on every verb.
        "cluster_tolerance": cluster_tolerance,
        # How the tables are READ, bound to the run for the same reason the key
        # scheme is: the loader decides which units exist, and two candidates
        # scored over different unit sets are not comparable. `_units_for` reads
        # it back off here for every later verb rather than re-deriving it.
        "loader": loader_key,
        # The fit knobs, bound to the run so every later submit fits the same way.
        "optimizer": opt_key,
        "restarts": restarts,
        "seed": seed,
        # The island model's own seed, recorded separately from the fit's. See
        # `_island_seed`: one flag was driving both, so a fit-robustness sweep
        # silently reshaped the search. Written even at its default, so a reader of
        # the run never has to infer which of the two seeds applied.
        "island_seed": island_seed,
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
            loader=loader_key,
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

    # A run whose seed candidate did not fit is a DEAD run dir, and it used to say
    # so only by printing `"seed_valid": false` among fifteen other keys. The seed
    # is the one candidate that registers on every island (the vendored
    # `register_program` loops them all for `island_id=None`), so without it the
    # buffer has empty islands and the very next `prompt` drew one and died inside
    # numpy. An act hands the fresh run to a generator sub-agent immediately, so
    # that traceback was the first thing the agent saw.
    #
    # Still exit 0: the run dir is legitimately created and a scientist can repair
    # it by submitting a candidate per island. The warning goes on stderr AND into
    # the payload, because the reader here is as often an act as a human.
    seed_warning = ""
    if not result.valid:
        seed_warning = (
            "the spec's own seed candidate did not fit "
            f"({result.error or 'no error recorded'}), so the experience buffer "
            "has no program on any island. `wheeler llmsr prompt` will refuse "
            "until that is fixed, because the prompt's island is drawn at random. "
            "Fix the seed body in the spec (or the data it is fitted to) and run "
            "init again."
        )
        typer.echo(f"warning: {seed_warning}", err=True)

    typer.echo(json.dumps({
        "run_id": rid,
        "run_dir": str(run_dir),
        "metric": metric_obj.key,
        "generator": gen,
        "loader": loader_key,
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
        **({"seed_warning": seed_warning} if seed_warning else {}),
        # `seed_value` is the seed candidate's own score, so it is named by what
        # produced it and not by the `metric` two lines up. They differ exactly
        # on the spec door, where the spec owns the loss.
        **(
            {"seed_value_metric": scored_metric(meta)}
            if scored_metric(meta) != metric_obj.key
            else {}
        ),
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
    _require_prompt_ready(db, run_dir, _read_submissions(run_dir))
    p = db.get_prompt()

    # Claimed under the run lock, and the routing recorded beside the text: two
    # concurrent `prompt` calls both wrote `prompts/0.txt`, and `island_id` /
    # `version_generated` lived on stdout only, so nothing on disk said where a
    # prompt had routed once the terminal scrolled. See `runs.claim_prompt`.
    prompt_file = claim_prompt(
        run_dir, p.code,
        island_id=p.island_id, version_generated=p.version_generated,
    )

    datasets = data_mod.datasets_from_meta(meta)
    seed_ds = data_mod.resolve_seed_from(datasets, str(meta.get("seed_from", "") or ""))
    typer.echo(json.dumps({
        "island_id": p.island_id,
        "version_generated": p.version_generated,
        "prompt_file": str(prompt_file),
        "function_to_evolve": meta["function_to_evolve"],
        "seed_from": seed_ds.as_dict(),
        "score_on": [d.name for d in data_mod.scored_from_meta(meta)],
        # How many candidates upstream draws from ONE prompt. It is
        # `Config.samples_per_prompt`, default 4, and the paper uses 4 (Appendix
        # B: m=10, k=2, b=4). Wheeler had never read it and generated exactly one
        # body per prompt, so every run did a quarter of the paper's exploration
        # per context. The four completions share an island and a version, and
        # differ only in the sampler's own randomness, which is the point: four
        # continuations of the same context rather than one.
        #
        # Reported rather than enforced, because generation lives in the act and
        # this CLI never calls a model. `submit` already accepts repeated calls
        # carrying the same `--island-id` and `--version-generated`, which is
        # exactly how a batch is recorded.
        "samples_per_prompt": config_lib.Config().samples_per_prompt,
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
    # Before the fit, which is the whole point: an out-of-range id used to raise a
    # bare IndexError from the vendored buffer AFTER the fit had finished, losing
    # the candidate and the model call that wrote it. See `_check_island_id`.
    _check_island_id(island_id, meta)
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
        # Quantized on the same rule the replay uses, through the one seam that
        # owns that question. The two disagreed: this register did not quantize and
        # the replay did, so the buffer written here and the buffer every reader
        # rebuilds were keyed differently. See `_scores_for_buffer`.
        db.register_program(
            fn, island_id,
            _scores_for_buffer(
                meta, result.per_group or {fit_mod.UNGROUPED: result.score}
            ),
        )

    # The order is claimed and the record appended in ONE critical section. As two
    # steps, four concurrent submits (which is the normal path: one prompt, four
    # bodies) all read the same count and wrote sample_orders
    # [0, 1, 2, 3, 4, 4, 4, 4]. A duplicate order reaches the graph, where
    # `transfer_ingest` keys an Execution on it. See `runs.append_next_submission`.
    sample_order = append_next_submission(run_dir, {
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
            **scored_metric_report(meta),
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
    # What the winner's own numbers are IN, which is not always the declared
    # metric: through the spec door the spec's `@evaluate.run` owns the loss and
    # never says what it computed. Everything derived from the search's own
    # values (the emitted .py's METRIC, the echo below) is labelled with this,
    # never with `metric_key`. See `runs.scored_metric`.
    scored_key = scored_metric(meta)
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
    program = _runnable_program(winner["program"], winner["params"], scored_key,
                                winner["value"], meta["data_path"], meta["function_to_evolve"],
                                _metric_for(metric_key).data_shape,
                                group_by=str(meta.get("group_by", "") or ""),
                                params_per_group=winner.get("params_per_group") or {},
                                value_per_group=winner.get("per_group_value") or {},
                                dataset_report=None if one_file else report,
                                no_constants=no_constants,
                                declared_metric="" if scored_key == metric_key else metric_key)

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
        # Spec door only, and placed here so it reads beside the declared metric
        # it is NOT. Names the quantity every number the SEARCH produced is in,
        # because through that door the spec owns the loss and nothing checks it
        # equals the declared metric. Absent on the default door, where the two
        # are the same quantity. See `runs.scored_metric_report`.
        **scored_metric_report(meta),
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
        # `value` is a number, so it carries the name of what produced it, which
        # on the spec door is not `metric`. Emitted only when they differ.
        **({"value_metric": scored_key} if scored_key != metric_key else {}),
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
