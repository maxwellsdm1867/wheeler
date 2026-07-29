"""Ask whether the FORM transfers to new data, not whether the CONSTANTS do.

Two different questions hide behind the phrase "does it generalize", and until
this verb existed Wheeler could only answer the second one:

``the CONSTANTS transfer``
    apply the source run's own fitted constants, unchanged, to the new data.
    This is what ``fit.evaluate_fixed`` does, and it is what ``--select ood`` and
    the held-out splits in ``best.json`` have always measured.
``the FORM transfers``
    refit the constants from scratch on the new data, under the SAME functional
    form, and see whether the form still fits.

Symbolic regression is looking for the FORM. A law that governs a new cell with
different constants is the SAME law; charging it for the constants it was never
claimed to share is charging the form for something that belongs to the
parameters (the argument in ``docs/llmsr-objective-formulation.md``, applied to
held-out data instead of to the training groups).

Both numbers are interesting, they are just different. So this reports them SIDE
BY SIDE, each labelled with what it is a claim about, and never derives one from
the other. Nothing here writes ``submissions.jsonl`` or the experience buffer: a
number that fed back into the search would stop being a holdout, and this file
exists to produce holdouts.

The regime vocabulary is the one the graph already speaks (``scored`` /
``held_out`` / ``unknown``, each with a reason), so a transfer number reads the
same way in ``transfer.json`` as it does on a Finding.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import fit as fit_mod
from . import runs as runs_mod
from .selection import (
    _equation_complexity,
    _fixed_theta_per_group,
    _load_groups,
    _strict_mean,
)

logger = logging.getLogger(__name__)

TRANSFER_FILE = "transfer.json"

# What each number is a claim ABOUT. Carried on every block so the two can never
# be read as two measurements of one thing.
CLAIM_FORM = "form"
CLAIM_CONSTANTS = "constants"

# The regime vocabulary, matching `discover.py`. Duplicated as literals rather
# than imported because `discover.py` is the graph writer and this is not: a
# reporting module importing the ingest would invert the dependency for four
# strings. `REGIME_HELD_OUT_FORM` is not a synonym for `REGIME_HELD_OUT`: see
# `_refit_regime`.
REGIME_SCORED = "scored"
REGIME_HELD_OUT = "held_out"
REGIME_HELD_OUT_FORM = "held_out_form"
REGIME_UNKNOWN = "unknown"

_REFIT_LABEL = (
    "the FORM transfers: the constants were refitted from scratch on this data "
    "under the same functional form"
)
_FIXED_LABEL = (
    "the CONSTANTS transfer: the source run's own fitted constants were applied "
    "to this data unchanged, with no refit"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_candidate(
    subs: list[dict], meta: dict, mode: str, sample_order: int | None
) -> tuple[dict, str]:
    """The candidate to transfer, and how it was chosen.

    An explicit ``sample_order`` names one submission and is checked for validity
    here: transferring a candidate the search rejected would produce numbers for
    a form that never fitted anything. Otherwise the run's own selection rules
    pick the winner, so ``transfer`` asks about the same form ``best`` reports.
    """
    # Lazy: `selection` imports `cli`, which imports this module's siblings.
    from .selection import _select_winner

    valid = [s for s in subs if s.get("valid") and s.get("score") is not None]
    if sample_order is not None:
        named = [s for s in subs if s.get("sample_order") == sample_order]
        if not named:
            raise LookupError(
                f"no submission with sample_order {sample_order} in this run "
                f"({len(subs)} recorded)"
            )
        cand = named[0]
        if not cand.get("valid"):
            raise LookupError(
                f"submission {sample_order} is not a valid candidate "
                f"({cand.get('error') or 'no error recorded'}); there is no form "
                "to transfer"
            )
        return cand, "explicit"
    if not valid:
        raise LookupError("this run has no valid candidate to transfer")
    return _select_winner([dict(c) for c in valid], meta, mode), mode


def _regime(meta: dict, data_path: Path, mode: str, n_valid: int) -> tuple[str, str]:
    """Label the transfer data by regime, for the FIXED-THETA claim.

    Two things count as the search optimizing against data: FITTING the constants
    and CHOOSING THE WINNER. Transferring onto the run's own training file is the
    first. Transferring onto ``test_ood.csv`` while selecting with ``--select
    ood`` is the second, unless there was only one candidate and nothing was
    actually selected between. Everything else is genuinely held out.
    """
    train = Path(str(meta.get("data_path", ""))).resolve()
    here = data_path.resolve()
    if here == train:
        return REGIME_SCORED, (
            "this is the run's own training data: the search fitted the "
            "constants here"
        )
    if mode == "ood" and here == train.parent / "test_ood.csv":
        if n_valid > 1:
            return REGIME_SCORED, (
                "--select ood chose this form by its error on this data"
            )
        return REGIME_HELD_OUT, (
            "--select ood was asked for, but there was only one valid candidate, "
            "so nothing was selected between"
        )
    return REGIME_HELD_OUT, (
        "the search neither fitted constants nor selected the winner on this data"
    )


def _refit_regime(regime: str, reason: str) -> tuple[str, str]:
    """The regime of the REFIT number, which is never simply the data's regime.

    A refit fits constants on the data it reports, so the number is held out for
    the FORM and not for the constants. Saying ``held_out`` unqualified would
    claim more than the measurement supports, which is the failure mode the
    regime labels exist to prevent, so it gets its own label as well as its own
    reason. ``discover._refit_regime`` applies the same rule to the refit numbers
    in ``best.json``, so a transfer number and a Finding read the same way.
    """
    if regime == REGIME_HELD_OUT:
        return REGIME_HELD_OUT_FORM, (
            reason + ", but the constants WERE refitted on it, so this number is "
            "held out for the FORM only, never for the constants"
        )
    return regime, reason


def transfer_report(
    meta: dict,
    cand: dict,
    data_path: Path,
    group_by: str,
    *,
    selected_by: str,
    n_valid: int,
    run_dir: Path | None = None,
) -> dict:
    """Refit the candidate on ``data_path`` and report both quantities.

    The refit uses the run's own fit knobs (optimizer, restarts, seed), read off
    ``meta.json``, because a transfer fitted differently from the search that
    produced the form is not comparable with it.

    ``run_dir``, when given, is where the during-the-fit progress pings go
    (S0b's channel), so a transfer that refits forty groups can be asked where
    it has got to instead of being silent for minutes. Nothing else in the run
    dir is written from here: ``submissions.jsonl`` and the buffer stay
    untouched, because a holdout that fed back into the search would stop being
    a holdout.
    """
    # Lazy, to break the cycle: `cli` imports `selection`, which this imports.
    from .cli import _fit_knobs, _metric_for

    metric = _metric_for(meta["metric"])
    knobs = _fit_knobs(meta)
    fte = meta["function_to_evolve"]
    program = cand["program"]
    regime, reason = _regime(meta, data_path, selected_by, n_valid)

    groups = _load_groups(str(data_path), metric, group_by)
    if groups is None:
        return _failed(
            meta, cand, data_path, group_by, selected_by, regime, reason,
            f"{data_path} could not be read as {metric.data_shape} data"
            + (f" grouped by {group_by!r}" if group_by else ""),
        )
    labels = [label for label, _gX, _gy in groups]

    progress_path = None
    if run_dir is not None:
        progress_path = Path(run_dir) / runs_mod.PROGRESS_FILE
        runs_mod.write_progress(Path(run_dir), {
            "phase": "transfer",
            "dataset": data_path.name,
            "group": None,
            "done": 0,
            "total": len(groups),
            "at": _now(),
        })

    result = fit_mod.evaluate_body_grouped(
        program, fte, groups, metric,
        max_nparams=int(meta.get("max_nparams") or 10),
        timeout_seconds=int(meta.get("timeout") or 30),
        progress_path=progress_path,
        **knobs,
    )

    # The fixed-theta side, whatever the refit did: the two are independent
    # measurements and a form that fails to refit on a new cell is exactly when
    # you want to know what its old constants scored there.
    fixed_values, fixed_thetas, fixed_reasons = _fixed_theta_per_group(
        program, fte, groups, cand, metric
    )
    fixed_agg = _strict_mean(fixed_values)
    refit_regime, refit_reason = _refit_regime(regime, reason)

    payload: dict[str, Any] = {
        "status": "completed" if result.valid else "failed",
        "run_id": meta.get("run_id", ""),
        "metric": metric.key,
        "data_path": str(data_path.resolve()),
        "source_data_path": str(meta.get("data_path", "")),
        "group_by": group_by,
        "groups": labels,
        "candidate": {
            "sample_order": cand.get("sample_order"),
            "selected_by": selected_by,
            "equation": str(cand.get("body", "")).strip("\n"),
            "complexity": _equation_complexity(str(cand.get("body", ""))),
        },
        "refit": {
            "claim": CLAIM_FORM,
            "label": _REFIT_LABEL,
            "valid": result.valid,
            "value": result.value if result.valid else None,
            "value_per_group": result.per_group_value if result.valid else {},
            "params_per_group": result.params_per_group if result.valid else {},
            "optimizer": result.optimizer,
            "optimizer_per_group": result.optimizer_per_group,
            "regime": refit_regime,
            "regime_reason": refit_reason,
            "error": result.error,
        },
        "fixed_theta": {
            "claim": CLAIM_CONSTANTS,
            "label": _FIXED_LABEL,
            "value": fixed_agg,
            "value_per_group": fixed_values,
            "params_per_group": fixed_thetas,
            "source_per_group": fixed_reasons,
            "regime": regime,
            "regime_reason": reason,
            "error": "" if fixed_agg is not None else (
                "no fixed-theta aggregate: at least one group produced no number, "
                "and a mean over the rest is not the number it would be read as. "
                "source_per_group says which group and why"
            ),
        },
        "optimizer": {
            "requested": knobs["optimizer"],
            "used": result.optimizer,
            "restarts": knobs["restarts"],
            "seed": knobs["seed"],
        },
        # What the SOURCE SEARCH's own numbers are in, present exactly when that
        # is not the declared metric, which is the spec door. Both numbers above
        # were computed HERE by `fit.py` under the DECLARED metric, so on that
        # door they are a second opinion measured by different machinery than
        # the search used, and a reader who did not know that would compare them
        # against a `best.json` headline that is a different quantity. The block
        # is absent on a default-door run, which is the file this verb has
        # always written. `runs.scored_metric_report` is the ONE place that
        # question is answered; it is never reconstructed here.
        **runs_mod.scored_metric_report(meta),
        "written": _now(),
    }
    payload["comparison"] = _comparison(
        payload["refit"]["value"], fixed_agg, metric.key
    )

    if run_dir is not None:
        # Close the DURING channel out. `_phase` reads "a progress ping the
        # heartbeat has not overtaken" as a fit in flight, so a transfer that
        # left the last word to its own pings would make `status` report
        # `fitting` forever after it finished. The heartbeat is recomputed from
        # `submissions.jsonl`, which this verb did not touch, so its content is
        # the same snapshot it already held.
        runs_mod.write_progress(Path(run_dir), {
            "phase": "transfer",
            "dataset": data_path.name,
            "group": labels[-1] if labels else None,
            "done": len(groups),
            "total": len(groups),
            "at": _now(),
        })
        runs_mod._write_heartbeat(Path(run_dir), meta)
    return payload


def _comparison(refit: float | None, fixed: float | None, metric_key: str) -> dict:
    """State the two numbers next to each other, without ranking them.

    No verdict: whether a form "transferred" is the scientist's call and depends
    on what counts as close for this metric on this data. The ratio is arithmetic
    on two numbers that are already reported, and it is omitted rather than
    guessed when either is missing or when the divisor is zero.
    """
    out: dict[str, Any] = {
        "metric": metric_key,
        "refit_value": refit,
        "fixed_theta_value": fixed,
        "note": (
            "the two answer different questions: refit asks whether the FORM "
            "fits this data, fixed-theta asks whether the source CONSTANTS do. "
            "Neither substitutes for the other."
        ),
    }
    if refit is not None and fixed is not None and fixed != 0.0:
        out["refit_over_fixed"] = refit / fixed
    return out


def _failed(
    meta: dict, cand: dict, data_path: Path, group_by: str, selected_by: str,
    regime: str, reason: str, error: str,
) -> dict:
    """A transfer that never got to a fit, recorded truthfully and with no numbers."""
    return {
        "status": "failed",
        "run_id": meta.get("run_id", ""),
        "metric": meta.get("metric", ""),
        "data_path": str(data_path),
        "source_data_path": str(meta.get("data_path", "")),
        "group_by": group_by,
        "groups": [],
        "candidate": {
            "sample_order": cand.get("sample_order"),
            "selected_by": selected_by,
            "equation": str(cand.get("body", "")).strip("\n"),
            "complexity": _equation_complexity(str(cand.get("body", ""))),
        },
        "refit": {
            "claim": CLAIM_FORM, "label": _REFIT_LABEL, "valid": False,
            "value": None, "value_per_group": {}, "params_per_group": {},
            "optimizer": "", "optimizer_per_group": {},
            "regime": REGIME_UNKNOWN,
            "regime_reason": "nothing was measured on this data",
            "error": error,
        },
        "fixed_theta": {
            "claim": CLAIM_CONSTANTS, "label": _FIXED_LABEL, "value": None,
            "value_per_group": {}, "params_per_group": {}, "source_per_group": {},
            "regime": regime, "regime_reason": reason, "error": error,
        },
        "comparison": _comparison(None, None, str(meta.get("metric", ""))),
        # Present only on the spec door, exactly as in the completed payload, so
        # the two shapes do not diverge and the ingest reads one field.
        **runs_mod.scored_metric_report(meta),
        "written": _now(),
    }
