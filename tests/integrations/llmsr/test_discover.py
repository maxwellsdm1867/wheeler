"""Tests for the LLM-SR equation-discovery marshal-out adapter.

Five layers:
  1. parse_discover: a real captured best.json fixture plus shape-drift /
     garbage tolerance (never raises), and the REGIME labelling that keeps a
     search-optimized number from reading as a generalization claim.
  2. the shapes the post-#107 engine produces that the pre-#107 ingest dropped
     on the floor: a MULTI-DATASET run (per-unit constants, one Dataset node per
     table), the REFIT numbers (``metrics_refit``, a claim about the FORM alone),
     and the spec-evaluate door (held-out numbers measured by other machinery).
  3. live-Neo4j e2e: ingest the fixture, assert the winner subgraph (Script +
     Finding + Document, BOTH provenance sides), then re-ingest and assert
     idempotency. Skipped automatically when Neo4j is unreachable.
  4. live-Neo4j e2e for a GROUPED run, driven from a real search: the Script must
     carry the per-group constant table, and the .py it points at must RUN.
  5. live-Neo4j e2e for a MULTI-DATASET run and for a run with held-out siblings,
     both driven from real searches: the per-unit table, one Dataset per declared
     table on the USED side, and the refit Finding beside the fixed-theta one.

Run: python -m pytest tests/integrations/llmsr/test_discover.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from wheeler.integrations.llmsr.discover import (
    CLAIM_CONSTANTS,
    CLAIM_FORM,
    MEASURED_BY_FIT,
    REGIME_HELD_OUT,
    REGIME_HELD_OUT_FORM,
    REGIME_SCORED,
    REGIME_UNKNOWN,
    SCORED_BY_SPEC_EVALUATE,
    RunMeta,
    _finding_id,
    _is_grouped,
    _is_multi,
    _no_constants,
    parse_discover,
)

FIXTURE = Path(__file__).parent / "fixtures" / "best_completed.json"
SERVICE_TAG = "llmsr:discover"
WORKTREE = str(Path(__file__).resolve().parents[3])

# A noiseless linear law, one form, three cells with three different constants.
CELLS = {"c01": (2.5, -1.0), "c02": (-4.0, 8.0), "c03": (0.5, 3.0)}
N_PER_CELL = 25


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _subprocess_env() -> dict:
    return {**os.environ, "PYTHONPATH": WORKTREE}


def _splits(doc: dict) -> dict[str, dict]:
    records, _ = parse_discover(doc)
    return {entry["split"]: entry for entry in records[0]["splits"]}


def _completed(**extra) -> dict:
    """A minimal completed best.json, so a test states only what it is about."""
    doc = {
        "status": "completed",
        "run_id": "r1",
        "generator": "claude",
        "metric": "nmse",
        "equation": "    return params[0] * x",
        "program": "def equation(x, params):\n    return params[0] * x\n",
        "params": [1.0],
        "data_path": "/data/bactgrow/train.csv",
    }
    doc.update(extra)
    return doc


# ---------------------------------------------------------------------------
# 1. Defensive parse
# ---------------------------------------------------------------------------


class TestParseDiscover:
    def test_non_dict_is_empty(self):
        records, run_meta = parse_discover("not a dict")
        assert records == []
        assert isinstance(run_meta, RunMeta)

    def test_empty_doc_is_empty(self):
        records, run_meta = parse_discover({})
        assert records == []
        assert isinstance(run_meta, RunMeta)

    def test_failed_status_yields_no_records(self):
        records, run_meta = parse_discover(
            {"status": "failed", "run_id": "r1", "generator": "claude"}
        )
        assert records == []
        assert run_meta.run_id == "r1"  # metadata still lifted for the failed run

    def test_completed_but_missing_equation_yields_no_records(self):
        records, _ = parse_discover(
            {"status": "completed", "run_id": "r1", "program": ""}
        )
        assert records == []

    def test_parses_real_fixture(self):
        doc = _load_fixture()
        records, run_meta = parse_discover(doc)
        assert len(records) == 1
        assert run_meta.run_id == doc["run_id"]
        assert run_meta.generator == doc["generator"]
        rec = records[0]
        assert rec["metric"] == "mse"
        assert isinstance(rec["value"], float)
        assert rec["equation"] and rec["program"]
        assert len(rec["params"]) == 10
        # an ungrouped run: no table, and the flat params are the answer
        assert rec["group_by"] == ""
        assert rec["params_per_group"] == {}
        assert rec["value_is_group_mean"] is False


class TestParseGroupedRun:
    """A grouped run's answer is the TABLE. The flat `params` is empty for it by
    construction, so a parser that reads only `params` records no constants."""

    def _grouped(self, **extra) -> dict:
        fields = {
            "params": [],
            "group_by": "cell_id",
            "params_per_group": {"c01": [2.5, -1.0], "c02": [-4.0, 8.0]},
            "value_per_group": {"c01": 0.02, "c02": 0.04},
        }
        fields.update(extra)
        return _completed(**fields)

    def test_table_and_coverage_are_lifted(self):
        rec = parse_discover(self._grouped())[0][0]
        assert rec["group_by"] == "cell_id"
        assert rec["params_per_group"] == {"c01": [2.5, -1.0], "c02": [-4.0, 8.0]}
        assert rec["value_per_group"] == {"c01": 0.02, "c02": 0.04}

    def test_value_is_the_group_mean_and_says_so(self):
        # a grouped run reports no scalar in `metrics`; the mean over groups is
        # what fit.py aggregates to, so it is derived and LABELLED, not invented
        rec = parse_discover(self._grouped())[0][0]
        assert rec["value"] == pytest.approx(0.03)
        assert rec["value_is_group_mean"] is True

    def test_a_partial_table_is_tolerated(self):
        rec = parse_discover(
            self._grouped(params_per_group={"c01": [1.0], "c02": "not a list"})
        )[0][0]
        assert rec["params_per_group"] == {"c01": [1.0]}

    def test_ungrouped_run_reports_no_mean(self):
        rec = parse_discover(_completed(metrics={"nmse_train": 0.1}))[0][0]
        assert rec["value"] == pytest.approx(0.1)
        assert rec["value_is_group_mean"] is False


class TestShapeIsAPropertyOfTheRun:
    """Which of the three constant shapes a run has is asked of its UNITS.

    The constants are what the fit chose to hand back, and upstream's bare-float
    ``evaluate`` hands back none. Reading the shape off the constants alone
    therefore filed a grouped or a multi-dataset run as a flat one-unit run
    whenever the spec door returned a bare float: the graph then recorded
    ``params "[]"`` with no ``group_by``, no ``n_groups`` and no per-group
    values, presenting a many-cell discovery as a single pooled fit.
    """

    def _bare_float_grouped(self, **extra) -> dict:
        """What a grouped run scored through the spec door with a bare float writes."""
        fields = {
            "params": [],
            "group_by": "cell_id",
            "params_per_group": {},  # upstream's contract returns none
            "value_per_group": {"c01": 0.02, "c02": 0.04, "c03": 0.06},
        }
        fields.update(extra)
        return _completed(**fields)

    def test_a_grouped_bare_float_run_is_still_grouped(self):
        rec = parse_discover(self._bare_float_grouped())[0][0]
        assert _is_grouped(rec) is True
        assert _is_multi(rec) is False
        assert _no_constants(rec) is True
        # the mean over the three cells, derived and labelled as one
        assert rec["value"] == pytest.approx(0.04)
        assert rec["value_is_group_mean"] is True

    def test_a_multi_dataset_bare_float_run_is_still_multi(self):
        rec = parse_discover(_completed(
            params=[],
            datasets={
                "seed_from": "A", "score_on": ["A", "B"], "score_key_scheme": "dataset",
                "entries": [
                    {"name": "A", "path": "/d/a.csv", "regime": "scored",
                     "keys": ["A"], "value_per_key": {"A": 0.1}, "params_per_key": {}},
                    {"name": "B", "path": "/d/b.csv", "regime": "scored",
                     "keys": ["B"], "value_per_key": {"B": 0.3}, "params_per_key": {}},
                ],
            },
        ))[0][0]
        assert _is_multi(rec) is True
        assert _no_constants(rec) is True
        assert rec["value"] == pytest.approx(0.2)
        assert rec["value_is_unit_mean"] is True

    def test_a_genuine_one_unit_run_is_still_flat(self):
        rec = parse_discover(_completed(metrics={"nmse_train": 0.1}))[0][0]
        assert _is_grouped(rec) is False
        assert _is_multi(rec) is False
        assert _no_constants(rec) is False


class TestRegimeLabelling:
    """Every metric Finding says whether the search optimized against its data.
    Forty rounds scored on a split makes that split's error a TRAINING number,
    however good it looks, and the graph must never offer it as generalization."""

    def test_train_is_scored(self):
        entry = _splits(_completed(metrics={"nmse_train": 0.1}))["train"]
        assert entry["regime"] == REGIME_SCORED
        assert "fitted the constants" in entry["regime_reason"]

    def test_test_id_is_held_out(self):
        entry = _splits(
            _completed(metrics={"nmse_train": 0.1, "nmse_test_id": 0.2})
        )["test_id"]
        assert entry["regime"] == REGIME_HELD_OUT

    def test_ood_is_held_out_under_parsimony(self):
        doc = _completed(
            metrics={"nmse_train": 0.1, "nmse_test_ood": 0.3},
            selection={"mode": "parsimony"},
            n_valid=9,
        )
        assert _splits(doc)["test_ood"]["regime"] == REGIME_HELD_OUT

    def test_ood_is_scored_when_it_chose_the_winner(self):
        # --select ood ranks candidates by their OOD error: that split is a
        # SELECTION set, so its number is not a clean generalization claim
        doc = _completed(
            metrics={"nmse_train": 0.1, "nmse_test_ood": 0.3},
            selection={"mode": "ood"},
            n_valid=9,
        )
        entry = _splits(doc)["test_ood"]
        assert entry["regime"] == REGIME_SCORED
        assert "--select ood" in entry["regime_reason"]

    def test_ood_stays_held_out_when_there_was_nothing_to_select_between(self):
        doc = _completed(
            metrics={"nmse_train": 0.1, "nmse_test_ood": 0.3},
            selection={"mode": "ood"},
            n_valid=1,
        )
        assert _splits(doc)["test_ood"]["regime"] == REGIME_HELD_OUT

    def test_ood_regime_is_unknown_without_a_recorded_selection_mode(self):
        # an artifact that predates the selection block cannot say whether OOD
        # picked the winner: record that, do not pick the flattering answer
        doc = _completed(metrics={"nmse_train": 0.1, "nmse_test_ood": 0.3})
        entry = _splits(doc)["test_ood"]
        assert entry["regime"] == REGIME_UNKNOWN
        assert "cannot be determined" in entry["regime_reason"]

    def test_an_unplaceable_metric_key_is_unknown_not_guessed(self):
        entry = _splits(_completed(metrics={"score": 0.5}))[""]
        assert entry["regime"] == REGIME_UNKNOWN
        assert entry["value"] == pytest.approx(0.5)

    def test_a_held_out_number_never_stands_in_for_the_train_number(self):
        rec = parse_discover(_completed(metrics={"nmse_test_ood": 0.3}))[0][0]
        assert rec["value"] is None  # the run reported no train number
        assert _splits(_completed(metrics={"nmse_test_ood": 0.3}))["test_ood"][
            "value"
        ] == pytest.approx(0.3)

    def test_the_companion_metric_rides_along_on_its_own_split(self):
        doc = _completed(metrics={"nmse_train": 0.1, "mse_train": 0.9})
        entry = _splits(doc)["train"]
        assert entry["metric"] == "nmse"  # the run's own metric is the headline
        assert entry["others"] == {"mse": 0.9}


# ---------------------------------------------------------------------------
# 2. What the post-#107 engine produces that the pre-S8 ingest dropped
# ---------------------------------------------------------------------------


def _dataset_entry(name: str, regime: str, **extra) -> dict:
    """One entry of ``best.json["datasets"]``, in the shape `cli.py` writes it."""
    entry = {
        "name": name,
        "path": f"/data/{name}.csv",
        "seed": False,
        "regime": regime,
        "regime_reason": "because the test says so",
        "value": None,
        "keys": [],
        "value_per_key": {},
        "params_per_key": {},
    }
    entry.update(extra)
    return entry


def _multi(entries: list[dict], **extra) -> dict:
    """A completed MULTI-DATASET best.json: flat `params` empty, `metrics` empty.

    Both emptinesses are what the real CLI writes, not a simplification: a run
    with more than one fittable unit has no single parameter vector, so
    ``evaluate_fixed`` has no vector to apply and ``_split_metrics`` reports
    nothing at all for it.
    """
    fields = {
        "params": [],
        "metrics": {},
        "datasets": {
            "seed_from": "A",
            "score_on": [e["name"] for e in entries if e["regime"] == REGIME_SCORED],
            "score_key_scheme": "dataset",
            "entries": entries,
        },
    }
    fields.update(extra)
    return _completed(**fields)


class TestParseMultiDataset:
    """A multi-dataset discovery must land WITH its answer.

    Before S8 it landed with ``value=None``, ``params=[]`` and no per-unit table:
    ``metrics`` is empty for any multi-unit run, and the ``value_per_group``
    fallback only fires when ``--group-by`` was declared, which an ungrouped
    multi-dataset run does not. So the number that answers the scientist's
    question reached the graph as nothing at all.
    """

    def _two_scored(self, **extra) -> dict:
        return _multi([
            _dataset_entry("A", REGIME_HELD_OUT, seed=True),
            _dataset_entry(
                "B", REGIME_SCORED, value=0.02, keys=["B"],
                value_per_key={"B": 0.02}, params_per_key={"B": [1.0, 2.0]},
            ),
            _dataset_entry(
                "C", REGIME_SCORED, value=0.04, keys=["C"],
                value_per_key={"C": 0.04}, params_per_key={"C": [3.0, 4.0]},
            ),
        ], **extra)

    def test_the_value_is_the_mean_over_scored_units_and_says_so(self):
        rec = parse_discover(self._two_scored())[0][0]
        # exactly what `fit.py` aggregates to: sum(per_unit) / len(per_unit)
        assert rec["value"] == pytest.approx(0.03)
        assert rec["value_is_unit_mean"] is True
        assert rec["value_is_group_mean"] is False

    def test_every_scored_unit_keeps_its_own_constants(self):
        rec = parse_discover(self._two_scored())[0][0]
        assert rec["params_per_key"] == {"B": [1.0, 2.0], "C": [3.0, 4.0]}
        assert rec["value_per_key"] == {"B": 0.02, "C": 0.04}
        assert rec["params"] == []  # the flat vector really is empty

    def test_a_held_out_table_enters_neither_the_mean_nor_the_constants(self):
        """It has no value BECAUSE the run never computed one for it.

        Folding it in would either invent a number or quietly shrink the
        denominator of a mean the reader will take at face value.
        """
        rec = parse_discover(self._two_scored())[0][0]
        assert "A" not in rec["params_per_key"]
        assert "A" not in rec["value_per_key"]
        entries = {e["name"]: e for e in rec["datasets"]["entries"]}
        assert entries["A"]["regime"] == REGIME_HELD_OUT
        assert entries["A"]["seed"] is True

    def test_a_grouped_multi_dataset_run_keys_its_table_by_unit(self):
        rec = parse_discover(_multi([
            _dataset_entry(
                "P", REGIME_SCORED, value=0.1, keys=["P:c00", "P:c01"],
                value_per_key={"P:c00": 0.1, "P:c01": 0.1},
                params_per_key={"P:c00": [1.0], "P:c01": [2.0]},
            ),
            _dataset_entry(
                "Q", REGIME_SCORED, value=0.3, keys=["Q:c00"],
                value_per_key={"Q:c00": 0.3}, params_per_key={"Q:c00": [3.0]},
            ),
        ], group_by="cell", params_per_group={}, value_per_group={}))[0][0]
        assert set(rec["params_per_key"]) == {"P:c00", "P:c01", "Q:c00"}
        # the mean is over UNITS, matching `fit.py`, not over datasets
        assert rec["value"] == pytest.approx((0.1 + 0.1 + 0.3) / 3)
        assert rec["value_is_unit_mean"] is True

    def test_a_reported_train_number_is_never_displaced_by_the_derived_mean(self):
        rec = parse_discover(self._two_scored(metrics={"nmse_train": 0.5}))[0][0]
        assert rec["value"] == pytest.approx(0.5)
        assert rec["value_is_unit_mean"] is False

    def test_a_single_default_dataset_run_carries_no_dataset_block(self):
        """`best.json` omits it, so an older artifact takes the path it always did."""
        rec = parse_discover(_completed(metrics={"nmse_train": 0.1}))[0][0]
        assert rec["datasets"] == {}
        assert rec["params_per_key"] == {}
        assert rec["value_is_unit_mean"] is False

    def test_a_regime_this_version_does_not_know_is_unknown_not_coerced(self):
        rec = parse_discover(_multi([
            _dataset_entry("A", "sort-of-held-out", value=0.1, keys=["A"]),
        ]))[0][0]
        entry = rec["datasets"]["entries"][0]
        assert entry["regime"] == REGIME_UNKNOWN
        assert "sort-of-held-out" in entry["regime_reason"]
        # and an unlabelled table contributes nothing to the answer
        assert rec["params_per_key"] == {}

    def test_a_shape_drifted_dataset_block_never_raises(self):
        for drift in ("not a dict", {"entries": "nope"}, {"entries": [1, None, {}]}):
            rec = parse_discover(_multi([], datasets=drift))[0][0]
            assert rec["datasets"] == {}
            assert rec["value"] is None


class TestParseRefitSplits:
    """``metrics_refit`` answers "does the FORM transfer" and never reached the graph.

    S3 wrote it into ``best.json`` and deliberately did NOT smuggle it into
    ``metrics`` under a suffix, because the regime labeller would have called a
    refit number a clean held-out number. It is a claim about the FORM alone: a
    refit fits its constants on the very split it reports.
    """

    def _both(self, **extra) -> dict:
        fields = {
            "metrics": {"nmse_train": 0.1, "nmse_test_ood": 8.6},
            "metrics_refit": {"nmse_test_ood": 0.001},
            "selection": {"mode": "fit"},
            "n_valid": 9,
        }
        fields.update(extra)
        return _completed(**fields)

    def _refits(self, doc: dict) -> dict[str, dict]:
        rec = parse_discover(doc)[0][0]
        return {e["split"]: e for e in rec["refit_splits"]}

    def test_the_refit_number_lands_at_all(self):
        entry = self._refits(self._both())["test_ood"]
        assert entry["value"] == pytest.approx(0.001)
        assert entry["claim"] == CLAIM_FORM

    def test_its_regime_is_refit_aware_and_not_plain_held_out(self):
        """`held_out` unqualified would claim the CONSTANTS transferred too."""
        entry = self._refits(self._both())["test_ood"]
        assert entry["regime"] == REGIME_HELD_OUT_FORM
        assert entry["regime"] != REGIME_HELD_OUT
        assert "FORM only, never for the constants" in entry["regime_reason"]

    def test_the_fixed_theta_number_on_the_same_split_is_untouched(self):
        rec = parse_discover(self._both())[0][0]
        fixed = {e["split"]: e for e in rec["splits"]}["test_ood"]
        assert fixed["value"] == pytest.approx(8.6)
        assert fixed["claim"] == CLAIM_CONSTANTS
        assert fixed["regime"] == REGIME_HELD_OUT

    def test_a_split_the_search_optimized_against_stays_scored_when_refitted(self):
        """Refitting on data the search steered by does not make it a holdout."""
        entry = self._refits(self._both(selection={"mode": "ood"}))["test_ood"]
        assert entry["regime"] == REGIME_SCORED

    def test_the_two_claims_on_one_split_are_two_distinct_nodes(self):
        fixed = _finding_id("r1", "nmse", "test_ood", CLAIM_CONSTANTS)
        refit = _finding_id("r1", "nmse", "test_ood", CLAIM_FORM)
        assert fixed != refit

    def test_the_fixed_theta_finding_id_is_the_historic_one(self):
        """Ids minted before the refit numbers were ingested must still resolve."""
        assert _finding_id("r1", "nmse", "test_ood") == _finding_id(
            "r1", "nmse", "test_ood", CLAIM_CONSTANTS
        )
        assert _finding_id("r1", "nmse") == _finding_id("r1", "nmse", "train")

    def test_a_run_without_refit_numbers_reports_none(self):
        rec = parse_discover(_completed(metrics={"nmse_train": 0.1}))[0][0]
        assert rec["refit_splits"] == []


class TestSpecEvaluateMeasurement:
    """Under ``--use-spec-evaluate`` NEITHER side of the seam is unremarkable.

    The spec's own ``@evaluate.run`` scored the search, owning the loss and the
    optimizer. Held-out split scoring still runs through ``fit.py`` under the
    run's DECLARED metric, so those numbers were computed by different machinery
    than the search used: a SECOND OPINION, not the run's own objective measured
    again.

    And the numbers the spec door itself produced are not the declared metric
    either. The spec owns its loss and never reports what it computed, and
    nothing checks that it equals the declared metric, so those travel under the
    SPEC'S name with a caveat of their own. This class used to assert the
    opposite for that half (``measurement_note == ""``, on the reasoning that a
    number the search produced is the run's own objective), and that reasoning
    is how a stock recipe's MSE reached the graph labelled ``nmse``.
    """

    def _spec_run(self, **extra) -> dict:
        return _completed(
            optimizer={
                "requested": SCORED_BY_SPEC_EVALUATE,
                "used": SCORED_BY_SPEC_EVALUATE,
                "restarts": None, "seed": None,
                "scored_by": SCORED_BY_SPEC_EVALUATE,
                "declared_optimizer": "auto",
            },
            **extra,
        )

    def test_a_default_run_says_wheeler_fit_and_adds_no_caveat(self):
        rec = parse_discover(_completed(
            metrics={"nmse_train": 0.1, "nmse_test_id": 0.2}
        ))[0][0]
        assert rec["scored_by"] == ""
        for entry in rec["splits"]:
            assert entry["measured_by"] == MEASURED_BY_FIT
            assert entry["measurement_note"] == ""

    def test_a_spec_scored_runs_held_out_number_is_flagged_as_a_second_opinion(self):
        rec = parse_discover(self._spec_run(
            metrics={"nmse_train": 0.1, "nmse_test_ood": 0.3},
            metrics_refit={"nmse_test_ood": 0.2},
        ))[0][0]
        entries = {e["split"]: e for e in rec["splits"] + rec["refit_splits"]}
        for entry in entries.values():
            assert entry["measured_by"] == MEASURED_BY_FIT
            assert "second opinion" in entry["measurement_note"]
            assert "DECLARED metric" in entry["measurement_note"]

    def _grouped_spec_run(self, **extra) -> dict:
        """A grouped spec-door run: `metrics` is empty, so the train number is DERIVED."""
        return self._spec_run(
            params=[], metrics={},
            group_by="cell_id",
            params_per_group={"c01": [1.0], "c02": [2.0]},
            value_per_group={"c01": 0.02, "c02": 0.04},
            scored_metric={
                "name": "spec:evaluate",
                "declared": "nmse",
                "measured_by": SCORED_BY_SPEC_EVALUATE,
                "note": "the spec owns its loss",
            },
            **extra,
        )

    def test_a_number_the_spec_door_produced_is_named_after_the_spec(self):
        """The per-unit vector is the SPEC'S objective, and never the declared metric.

        This is the shape every grouped and every multi-dataset spec-door run
        takes (``metrics`` is empty, so the train number is the mean over the
        per-unit table the spec produced). The mean is genuinely the run's own
        objective; what it is NOT is the run's declared ``nmse``, because a stock
        recipe minimizes mean squared error and nothing checks the two agree.
        """
        rec = parse_discover(self._grouped_spec_run())[0][0]
        train = rec["splits"][0]
        assert train["value"] == pytest.approx(0.03)
        assert train["measured_by"] == SCORED_BY_SPEC_EVALUATE
        # named after what produced it, not after what the run declared
        assert train["metric"] == "spec:evaluate"
        assert rec["metric"] == "nmse"
        assert rec["value_metric"] == "spec:evaluate"
        assert rec["scored_metric"] == "spec:evaluate"
        assert "spec's own @evaluate.run" in train["measurement_note"]
        assert "declared metric" in train["measurement_note"]

    def test_a_spec_run_whose_train_number_fit_py_computed_keeps_the_declared_metric(self):
        """The other half of the same rule: where fit.py DID compute it, it is `nmse`.

        An ungrouped single-table spec run still gets ``<metric>_train`` out of
        ``fit.py``, under the declared metric. That number is the declared metric
        and says so; it is only a second opinion about which machinery measured
        it, which is the caveat it already carried.
        """
        rec = parse_discover(self._spec_run(
            metrics={"nmse_train": 0.1},
            scored_metric={
                "name": "spec:evaluate", "declared": "nmse",
                "measured_by": SCORED_BY_SPEC_EVALUATE, "note": "...",
            },
        ))[0][0]
        train = rec["splits"][0]
        assert train["metric"] == "nmse"
        assert rec["value_metric"] == "nmse"
        assert train["measured_by"] == MEASURED_BY_FIT
        assert "second opinion" in train["measurement_note"]

    def test_an_artifact_with_no_scored_metric_block_falls_back_to_the_declared_one(self):
        """A best.json written before the block existed is a DEFAULT-door run.

        Never guessed: the parser reads the name out of the artifact, and an
        artifact that does not carry one can only be a run whose numbers were the
        declared metric, which is every run the block is absent from.
        """
        rec = parse_discover(_completed(
            params=[], metrics={},
            group_by="cell_id",
            params_per_group={"c01": [1.0]},
            value_per_group={"c01": 0.02},
        ))[0][0]
        assert rec["scored_metric"] == "nmse"
        assert rec["splits"][0]["metric"] == "nmse"

    def test_the_two_doors_mint_different_finding_ids_for_the_train_number(self):
        """Two different quantities are two nodes, never one overwriting the other."""
        from wheeler.integrations.llmsr.discover import _finding_id

        assert _finding_id("r1", "nmse", "train") != _finding_id(
            "r1", "spec:evaluate", "train"
        )


# ---------------------------------------------------------------------------
# 3. Live-Neo4j e2e (per-run e2e_tag, hermetic teardown)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def e2e_config():
    from wheeler.config import Neo4jConfig, ProjectMeta, WheelerConfig

    return WheelerConfig(
        neo4j=Neo4jConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="research-graph",
            database="neo4j",
        ),
        project=ProjectMeta(name="Integrations-E2E-Test"),
    )


@pytest.fixture(scope="module")
def neo4j_available(e2e_config) -> bool:
    import asyncio

    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _check():
        driver = AsyncGraphDatabase.driver(
            e2e_config.neo4j.uri,
            auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )
        try:
            async with driver.session(database=e2e_config.neo4j.database) as s:
                await s.run("RETURN 1")
            return True
        except Exception:
            return False
        finally:
            await driver.close()

    return asyncio.run(_check())


@pytest.fixture(autouse=True)
def _reset_driver_singleton():
    import wheeler.graph.driver as drv

    drv._async_driver = None
    drv._async_driver_uri = None
    yield
    drv._async_driver = None
    drv._async_driver_uri = None


def _cleanup_discover(e2e_config, e2e_tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged.

    EXACTLY ``MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n`` and nothing
    else. NEVER delete by ``service``: the e2e config runs on the SHARED default
    namespace where production nodes carry the same service tag, so a
    service-scoped delete would wipe real user data.
    """
    import asyncio

    from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity

    async def _run():
        driver = AsyncGraphDatabase.driver(
            e2e_config.neo4j.uri,
            auth=(e2e_config.neo4j.username, e2e_config.neo4j.password),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
        )
        try:
            async with driver.session(database=e2e_config.neo4j.database) as s:
                await s.run(
                    "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
                    tag=e2e_tag,
                )
        finally:
            await driver.close()

    asyncio.run(_run())


class TestIngestDiscoverE2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        # Temp cwd so the on-disk indices, the durable raw store, and the written
        # discovery .py all land in a sandbox; per-run unique tag so teardown
        # never touches another test or production data.
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        _cleanup_discover(e2e_config, self._e2e_tag)
        yield
        _cleanup_discover(e2e_config, self._e2e_tag)

    async def _tag_ids(self, e2e_config, ids):
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        ids = [i for i in ids if i]
        if not ids:
            return
        async with driver.session(database=e2e_config.neo4j.database) as s:
            await s.run(
                "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                ids=ids, tag=self._e2e_tag,
            )

    async def _tag_run(self, e2e_config, report):
        """Tag ONLY the nodes THIS run created: the report ids plus the run's
        WAS_GENERATED_BY fan-in (Script, Finding, Document). NEVER by service."""
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        await self._tag_ids(e2e_config, [report.execution_id, report.artifact])
        if report.execution_id:
            async with driver.session(database=db) as s:
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                )

    @pytest.mark.asyncio
    async def test_held_out_splits_land_as_their_own_labelled_findings(
        self, e2e_config
    ):
        """A run that scored held-out splits gets one Finding per split, and the
        graph says which of them the search was steered by. Reading the train
        number as a generalization claim is the failure this prevents."""
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.llmsr.discover import ingest_discover

        doc = _load_fixture()
        doc["run_id"] = f"splits{uuid.uuid4().hex[:8]}"
        doc["metrics"] = {
            "mse_train": 0.0167, "nmse_train": 0.11,
            "mse_test_id": 0.0201, "nmse_test_id": 0.13,
            "mse_test_ood": 0.4400, "nmse_test_ood": 0.52,
        }
        doc["selection"] = {"mode": "ood", "complexity": 5, "candidates": 9}
        doc["n_valid"] = 9
        artifact_path = self._tmp / "best_splits.json"
        artifact_path.write_text(json.dumps(doc))

        report = await ingest_discover(
            doc, config=e2e_config, artifact_path=str(artifact_path)
        )
        await self._tag_run(e2e_config, report)
        assert report.failed is False
        assert report.created == 4  # the Script + one Finding per split

        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            r = await s.run(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.custom_split AS split, n.custom_regime AS regime, "
                "n.custom_value AS value, n.title AS title, "
                "n.description AS description",
                x=report.execution_id,
            )
            found = {rec["split"]: dict(rec) async for rec in r}

        assert set(found) == {"train", "test_id", "test_ood"}
        assert found["train"]["regime"] == REGIME_SCORED
        assert found["test_id"]["regime"] == REGIME_HELD_OUT
        # --select ood picked the winner BY the OOD error, so that split is a
        # selection set: it is not a clean generalization number either
        assert found["test_ood"]["regime"] == REGIME_SCORED
        assert "--select ood" in found["test_ood"]["description"]
        assert found["test_id"]["value"] == pytest.approx(0.0201)
        assert found["test_id"]["title"] == "mse_test_id"
        assert "Held out" in found["test_id"]["description"]

    @pytest.mark.asyncio
    async def test_ingest_buckets_and_is_idempotent(self, e2e_config):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.llmsr.discover import ingest_discover
        from wheeler.tools.graph_tools import execute_tool

        doc = _load_fixture()
        artifact_path = self._tmp / "best.json"
        artifact_path.write_text(json.dumps(doc))

        # Seed a Dataset input so the run has something to USE (input side), and a
        # Question as the link target. Tag both for hermetic cleanup.
        csv = self._tmp / "data.csv"
        csv.write_text("x,y\n1,2\n3,4\n")
        ds = json.loads(await execute_tool("add_dataset", {
            "path": str(csv), "type": "csv", "description": "e2e input",
            "service": SERVICE_TAG,
        }, e2e_config))
        q = json.loads(await execute_tool("add_question", {
            "question": "E2E: does LLM-SR discover a growth law?", "priority": 5,
        }, e2e_config))
        ds_id, question_id = ds["node_id"], q["node_id"]
        await self._tag_ids(e2e_config, [ds_id, question_id])

        # --- First ingest ---
        report1 = await ingest_discover(
            doc, link_to=question_id, config=e2e_config,
            artifact_path=str(artifact_path), used_inputs=[ds_id, question_id],
        )
        await self._tag_run(e2e_config, report1)
        assert report1.execution_id
        assert report1.failed is False
        assert report1.created == 2  # exactly the Script + the Finding

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        xid = report1.execution_id
        async with driver.session(database=db) as s:
            async def count(cypher, **kw):
                r = await s.run(cypher, **kw)
                rec = await r.single()
                return rec[0] if rec else None

            # OUTPUT side: Script + Finding + Document each WAS_GENERATED_BY the run
            assert await count(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(n)", x=xid
            ) == 1
            assert await count(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(n)", x=xid
            ) == 1
            assert await count(
                "MATCH (n:Document)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(n)", x=xid
            ) == 1
            # INPUT side: the run USED the seeded inputs
            assert await count(
                "MATCH (x:Execution {id:$x})-[:USED]->(n) RETURN count(n)", x=xid
            ) >= 1
            # Papers are reference entities: NEVER WAS_GENERATED_BY
            assert await count(
                "MATCH (p:Paper)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(p)", x=xid
            ) == 0
            # Execution status is honest
            assert await count(
                "MATCH (x:Execution {id:$x}) RETURN x.status", x=xid
            ) == "completed"
            # the Script is the FULL program on disk, with the equation queryable
            script_path = await count(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN n.path", x=xid
            )
            assert script_path and Path(script_path).exists()
            assert await count(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.custom_equation", x=xid
            )

        # --- Re-ingest: idempotent ---
        report2 = await ingest_discover(
            doc, link_to=question_id, config=e2e_config,
            artifact_path=str(artifact_path), used_inputs=[ds_id, question_id],
        )
        await self._tag_run(e2e_config, report2)
        assert report2.created == 0
        assert report2.execution_id == xid
        async with driver.session(database=db) as s:
            r = await s.run(
                "MATCH (x:Execution {service:$svc, session_id:$sid}) RETURN count(x)",
                svc=SERVICE_TAG, sid=doc["run_id"],
            )
            assert (await r.single())[0] == 1  # exactly one Execution, reused
            r = await s.run(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) RETURN count(n)",
                x=xid,
            )
            assert (await r.single())[0] == 1  # no duplicate Script


# ---------------------------------------------------------------------------
# 3. Live-Neo4j e2e for a GROUPED run, driven from a real search
# ---------------------------------------------------------------------------


class TestIngestGroupedDiscoverE2E:
    """A grouped discovery must land in the graph WITH its constants, and the
    Script it registers must point at a .py that actually runs.

    Driven from a real ``wheeler llmsr init`` + ``best`` rather than a fixture,
    because the two defects this covers (an empty flat ``params`` reaching the
    footer, and an empty ``params`` reaching the graph) both come from the shape
    ``fit.py`` really produces for more than one group.
    """

    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        _cleanup_discover(e2e_config, self._e2e_tag)
        yield
        _cleanup_discover(e2e_config, self._e2e_tag)

    async def _tag_run(self, e2e_config, report):
        """Tag ONLY the nodes THIS run created. NEVER by service."""
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        ids = [i for i in [report.execution_id, report.artifact] if i]
        async with driver.session(database=db) as s:
            if ids:
                await s.run(
                    "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                    ids=ids, tag=self._e2e_tag,
                )
            if report.execution_id:
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                )

    # An ``evaluate`` returning UPSTREAM's bare float: it fits this unit's
    # constants and throws them away, which is what every upstream spec does
    # (``optimized_params = result.x``, then discarded). Reached only with
    # ``--use-spec-evaluate``.
    _BARE_FLOAT_EVALUATE = (
        "    from scipy.optimize import minimize\n"
        "    inputs, outputs = data['inputs'], data['outputs']\n"
        "    def loss(params):\n"
        "        return float(np.mean((equation(inputs[:, 0], params) - outputs) ** 2))\n"
        "    result = minimize(loss, [1.0] * MAX_NPARAMS, method='BFGS')\n"
        "    if not np.isfinite(result.fun):\n"
        "        return None\n"
        "    return -float(result.fun)\n"
    )

    def _grouped_best_json(
        self, run_id: str = "e2egrouped", evaluate_body: str = "    return 0.0\n",
        extra: tuple[str, ...] = (),
    ) -> dict:
        """Run a real grouped search and return its best.json."""
        import numpy as np

        rng = np.random.default_rng(3)
        lines = ["cell_id,x1,y"]
        for name, (a, b) in CELLS.items():
            for x in rng.uniform(-3.0, 3.0, N_PER_CELL):
                lines.append(f"{name},{float(x):.17g},{a * float(x) + b:.17g}")
        (self._tmp / "train.csv").write_text("\n".join(lines) + "\n")
        (self._tmp / "spec.txt").write_text(
            "import numpy as np\n\n"
            "MAX_NPARAMS = 4\n\n"
            "@evaluate.run\n"
            "def evaluate(data):\n"
            + evaluate_body
            + "\n@equation.evolve\n"
            "def equation(x1, params):\n"
            "    return params[0] * x1 + params[1]\n"
        )
        for argv in (
            ["init", "--spec", "spec.txt", "--data", "train.csv",
             "--metric", "mse", "--group-by", "cell_id", "--run-id", run_id,
             *extra],
            ["best", "--run", run_id],
        ):
            out = subprocess.run(
                [sys.executable, "-m", "wheeler.tools.cli", "llmsr", *argv],
                cwd=self._tmp, capture_output=True, text=True, env=_subprocess_env(),
            )
            assert out.returncode == 0, out.stderr or out.stdout
        best = json.loads(
            (self._tmp / f".wheeler/llmsr/runs/{run_id}/best.json").read_text()
        )
        assert best["params"] == []  # the defect's precondition, from real output
        return best

    @pytest.mark.asyncio
    async def test_grouped_run_lands_with_its_constants_and_a_runnable_script(
        self, e2e_config
    ):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.llmsr.discover import ingest_discover

        doc = self._grouped_best_json()
        artifact_path = self._tmp / "best.json"
        artifact_path.write_text(json.dumps(doc))

        report = await ingest_discover(
            doc, config=e2e_config, artifact_path=str(artifact_path),
        )
        await self._tag_run(e2e_config, report)
        assert report.failed is False
        assert report.created == 2  # the Script + the train Finding

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        xid = report.execution_id
        async with driver.session(database=db) as s:
            async def one(cypher, **kw):
                r = await s.run(cypher, **kw)
                rec = await r.single()
                return dict(rec) if rec else None

            script = await one(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.path AS path, n.custom_group_by AS group_by, "
                "n.custom_n_groups AS n_groups, n.custom_groups AS groups, "
                "n.custom_params_per_group AS table, n.custom_params AS flat",
                x=xid,
            )
            finding = await one(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.custom_regime AS regime, n.custom_split AS split, "
                "n.custom_value AS value, n.custom_group_by AS group_by, "
                "n.custom_n_groups AS n_groups, "
                "n.custom_value_is_group_mean AS is_mean, n.description AS description",
                x=xid,
            )

        # the graph carries the ANSWER: one constant vector per group
        assert script["group_by"] == "cell_id"
        assert script["n_groups"] == len(CELLS)
        assert json.loads(script["groups"]) == sorted(CELLS)
        table = json.loads(script["table"])
        assert sorted(table) == sorted(CELLS)
        for name, (a, b) in CELLS.items():
            assert table[name][0] == pytest.approx(a, abs=1e-6)
            assert table[name][1] == pytest.approx(b, abs=1e-6)
        # the empty flat list is NOT what got recorded
        assert script["flat"] is None

        # the Finding is honest about how its number was earned
        assert finding["split"] == "train"
        assert finding["regime"] == REGIME_SCORED
        assert finding["is_mean"] is True
        assert finding["n_groups"] == len(CELLS)
        assert finding["group_by"] == "cell_id"
        assert "not a generalization claim" in finding["description"]
        assert "mean over 3" in finding["description"]

        # and the registered Script RUNS: the whole defect is that it did not
        script_path = Path(script["path"])
        assert script_path.exists()
        run = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=self._tmp, capture_output=True, text=True, env=_subprocess_env(),
        )
        assert run.returncode == 0, run.stderr
        for name in CELLS:
            assert f"group {name} n_rows {N_PER_CELL}" in run.stdout

    @pytest.mark.asyncio
    async def test_a_grouped_run_with_no_constants_keeps_its_grouping(
        self, e2e_config
    ):
        """A three-group discovery is not a one-unit run because of a return type.

        Through the spec door with upstream's bare-float ``evaluate``, BOTH
        constant tables come back empty: the contract has nowhere to put them.
        The shape used to be read off the constants alone, so this run fell to
        the FLAT arm and landed as ``params "[]"`` with no ``group_by``, no
        ``n_groups`` and no ``value_per_group``: a discovery over three cells
        presented as a single pooled fit with an empty constant vector.

        The grouping is a property of the RUN, so it is read off whichever
        per-group table the run reported, and the absence of constants is
        recorded as the fact it is rather than as an empty list.
        """
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.llmsr.discover import ingest_discover

        doc = self._grouped_best_json(
            run_id="e2egroupedbare",
            evaluate_body=self._BARE_FLOAT_EVALUATE,
            extra=("--use-spec-evaluate",),
        )
        # the precondition, from real output: no constants of EITHER shape
        assert doc["params_per_group"] == {}
        assert sorted(doc["value_per_group"]) == sorted(CELLS)

        artifact_path = self._tmp / "best_bare.json"
        artifact_path.write_text(json.dumps(doc))
        report = await ingest_discover(
            doc, config=e2e_config, artifact_path=str(artifact_path),
        )
        await self._tag_run(e2e_config, report)
        assert report.failed is False

        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            res = await s.run(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.custom_group_by AS group_by, "
                "n.custom_n_groups AS n_groups, n.custom_groups AS groups, "
                "n.custom_value_per_group AS values, n.custom_params AS flat, "
                "n.custom_params_per_group AS table, "
                "n.custom_no_constants AS no_constants, "
                "n.custom_no_constants_reason AS reason",
                x=report.execution_id,
            )
            rec = await res.single()
            script = dict(rec) if rec else None

        assert script["group_by"] == "cell_id"
        assert script["n_groups"] == len(CELLS)
        assert json.loads(script["groups"]) == sorted(CELLS)
        assert sorted(json.loads(script["values"])) == sorted(CELLS)
        # no constants exist, and that is RECORDED, never faked as an empty list
        assert script["flat"] is None
        assert script["table"] is None
        assert script["no_constants"] is True
        assert "nowhere to put them" in script["reason"]


# ---------------------------------------------------------------------------
# 5. Live-Neo4j e2e: the shapes the post-#107 engine produces
# ---------------------------------------------------------------------------


class _RealRunE2E:
    """Shared harness: drive a REAL search, ingest it, tear down by e2e_tag only.

    Driven from `wheeler llmsr init` + `best` rather than a fixture because every
    defect S8 closes comes from the shape the engine REALLY writes: an empty
    `metrics` for a multi-unit run, an empty flat `params`, a `metrics_refit`
    block nothing read. A hand-written doc would have been whatever the author
    assumed.
    """

    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        _cleanup_discover(e2e_config, self._e2e_tag)
        yield
        _cleanup_discover(e2e_config, self._e2e_tag)

    async def _tag_run(self, e2e_config, report):
        """Tag ONLY the nodes THIS run touched: the report ids, the
        WAS_GENERATED_BY fan-in (Script, Finding, Document) and the USED fan-out
        (the input Datasets). NEVER by service: the e2e config runs on the shared
        default namespace, so a service-scoped delete would wipe real user data.

        The USED side is narrowed further, to nodes whose path lies under THIS
        test's tmp dir. An Execution's inputs are the one edge that can reach a
        node the test did not create (an ingest is free to USE a Dataset that was
        already in the graph), and teardown deletes whatever it tags. The path
        guard makes that impossible by construction rather than by the caller
        remembering not to pass a production id.
        """
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        ids = [i for i in [report.execution_id, report.artifact] if i]
        async with driver.session(database=db) as s:
            if ids:
                await s.run(
                    "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                    ids=ids, tag=self._e2e_tag,
                )
            if report.execution_id:
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id: $xid}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                )
                await s.run(
                    "MATCH (x:Execution {id: $xid})-[:USED]->(n) "
                    "WHERE n.path STARTS WITH $under "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                    under=str(self._tmp),
                )

    def _spec(self) -> None:
        (self._tmp / "spec.txt").write_text(
            "import numpy as np\n\n"
            "MAX_NPARAMS = 4\n\n"
            "@evaluate.run\n"
            "def evaluate(data):\n"
            "    return 0.0\n\n"
            "@equation.evolve\n"
            "def equation(x1, params):\n"
            "    return params[0] * x1 + params[1]\n"
        )

    def _table(self, path: Path, a: float, b: float, seed: int) -> None:
        import numpy as np

        rng = np.random.default_rng(seed)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["x1,y"]
        for x in rng.uniform(-3.0, 3.0, N_PER_CELL):
            lines.append(f"{float(x):.17g},{a * float(x) + b:.17g}")
        path.write_text("\n".join(lines) + "\n")

    def _cli(self, *argv: str) -> None:
        out = subprocess.run(
            [sys.executable, "-m", "wheeler.tools.cli", "llmsr", *argv],
            cwd=self._tmp, capture_output=True, text=True, env=_subprocess_env(),
        )
        assert out.returncode == 0, out.stderr or out.stdout

    def _best(self, run_id: str) -> dict:
        return json.loads(
            (self._tmp / f".wheeler/llmsr/runs/{run_id}/best.json").read_text()
        )


class TestIngestMultiDatasetDiscoverE2E(_RealRunE2E):
    """A multi-dataset discovery must land with its ANSWER and its INPUTS.

    Before S8 it landed with no value, no constants, and one Dataset node for the
    first scored table only, which is the state the engine's whole multi-dataset
    slice was built to produce and the marshal-out never learned to read.
    """

    # Two scored tables with different constants under one shared form, plus a
    # third that only ever seeded the prompt.
    TABLES = {"A": (2.5, -1.0), "B": (-4.0, 8.0), "C": (0.5, 3.0)}

    def _multi_best_json(self) -> dict:
        self._spec()
        for i, (name, (a, b)) in enumerate(self.TABLES.items()):
            self._table(self._tmp / f"{name}.csv", a, b, seed=10 + i)
        self._cli(
            "init", "--spec", "spec.txt",
            "--data", "A=A.csv", "--data", "B=B.csv", "--data", "C=C.csv",
            "--seed-from", "A", "--score-on", "B,C",
            "--metric", "mse", "--run-id", "e2emulti",
        )
        self._cli("best", "--run", "e2emulti")
        best = self._best("e2emulti")
        # the defect's preconditions, from real output
        assert best["params"] == []
        assert best["metrics"] == {}
        return best

    @pytest.mark.asyncio
    async def test_multi_dataset_run_lands_with_per_unit_constants_and_datasets(
        self, e2e_config
    ):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.llmsr.discover import ingest_discover

        doc = self._multi_best_json()
        artifact_path = self._tmp / "best.json"
        artifact_path.write_text(json.dumps(doc))

        report = await ingest_discover(
            doc, config=e2e_config, artifact_path=str(artifact_path),
        )
        await self._tag_run(e2e_config, report)
        assert report.failed is False
        # the Script + the train Finding + one Dataset per DECLARED table
        assert report.created == 2 + len(self.TABLES)
        assert report.used == len(self.TABLES)

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        xid = report.execution_id
        async with driver.session(database=db) as s:
            r = await s.run(
                "MATCH (n:Script)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.path AS path, n.custom_params_per_key AS table, "
                "n.custom_n_keys AS n_keys, n.custom_keys AS keys, "
                "n.custom_datasets_scored AS scored, "
                "n.custom_datasets_held_out AS held_out, "
                "n.custom_seed_from AS seed_from, n.custom_params AS flat, "
                "n.custom_value AS value, n.custom_value_is_unit_mean AS is_mean",
                x=xid,
            )
            script = dict(await r.single())
            r = await s.run(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.custom_split AS split, n.custom_regime AS regime, "
                "n.custom_value AS value, n.custom_claim AS claim, "
                "n.custom_n_keys AS n_keys, n.custom_value_per_key AS per_key, "
                "n.custom_value_is_unit_mean AS is_mean, "
                "n.custom_n_datasets_scored AS n_scored, "
                "n.description AS description",
                x=xid,
            )
            findings = {rec["split"]: dict(rec) async for rec in r}
            r = await s.run(
                "MATCH (x:Execution {id:$x})-[:USED]->(n:Dataset) "
                "RETURN n.custom_dataset_name AS name, n.custom_regime AS regime, "
                "n.custom_seeded_the_prompt AS seed, n.path AS path, "
                "n.custom_value AS value, n.custom_params_per_key AS params",
                x=xid,
            )
            datasets = {rec["name"]: dict(rec) async for rec in r}
            r = await s.run(
                "MATCH (n:Dataset)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN count(n)",
                x=xid,
            )
            generated_datasets = (await r.single())[0]

        # 1. the graph carries the ANSWER: one constant vector per scored unit
        table = json.loads(script["table"])
        assert sorted(table) == ["B", "C"]
        for name in ("B", "C"):
            a, b = self.TABLES[name]
            assert table[name][0] == pytest.approx(a, abs=1e-6)
            assert table[name][1] == pytest.approx(b, abs=1e-6)
        assert script["n_keys"] == 2
        assert json.loads(script["keys"]) == ["B", "C"]
        assert json.loads(script["scored"]) == ["B", "C"]
        assert json.loads(script["held_out"]) == ["A"]
        assert script["seed_from"] == "A"
        assert script["flat"] is None  # the empty flat list is NOT what got recorded
        assert script["is_mean"] is True

        # 2. the number that answers the question is there, labelled as a mean
        train = findings["train"]
        assert train["value"] is not None
        assert train["value"] == pytest.approx(
            sum(json.loads(train["per_key"]).values()) / 2
        )
        assert train["is_mean"] is True
        assert train["n_keys"] == 2
        assert train["n_scored"] == 2
        assert train["claim"] == CLAIM_CONSTANTS
        assert train["regime"] == REGIME_SCORED
        assert "scored (dataset, group) units" in train["description"]

        # 3. one Dataset node per DECLARED table, on the INPUT side, each
        # carrying the regime the run assigned it
        assert set(datasets) == set(self.TABLES)
        assert datasets["A"]["regime"] == REGIME_HELD_OUT
        assert datasets["A"]["seed"] is True
        assert datasets["A"]["value"] is None
        assert datasets["A"]["params"] is None
        for name in ("B", "C"):
            assert datasets[name]["regime"] == REGIME_SCORED
            assert datasets[name]["seed"] is False
            assert datasets[name]["value"] is not None
            assert list(json.loads(datasets[name]["params"])) == [name]
            assert Path(datasets[name]["path"]).exists()
        # a Dataset is an INPUT: it is never generated BY the run
        assert generated_datasets == 0

        # 4. and the registered Script RUNS, applying each unit its own constants
        run = subprocess.run(
            [sys.executable, str(Path(script["path"]))],
            cwd=self._tmp, capture_output=True, text=True, env=_subprocess_env(),
        )
        assert run.returncode == 0, run.stderr
        for name in ("B", "C"):
            assert f"key {name} n_rows {N_PER_CELL}" in run.stdout
        assert "dataset A HELD OUT" in run.stdout

    @pytest.mark.asyncio
    async def test_re_ingesting_a_multi_dataset_run_creates_nothing_new(
        self, e2e_config
    ):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.llmsr.discover import ingest_discover

        doc = self._multi_best_json()
        artifact_path = self._tmp / "best.json"
        artifact_path.write_text(json.dumps(doc))

        first = await ingest_discover(
            doc, config=e2e_config, artifact_path=str(artifact_path)
        )
        await self._tag_run(e2e_config, first)
        second = await ingest_discover(
            doc, config=e2e_config, artifact_path=str(artifact_path)
        )
        await self._tag_run(e2e_config, second)

        assert second.created == 0
        assert second.execution_id == first.execution_id
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            r = await s.run(
                "MATCH (x:Execution {id:$x})-[u:USED]->(n:Dataset) RETURN count(u)",
                x=first.execution_id,
            )
            # link_once: no duplicate USED edges on the second pass
            assert (await r.single())[0] == len(self.TABLES)


class TestIngestRefitFindingsE2E(_RealRunE2E):
    """The number that answers "does the FORM transfer" must reach the graph.

    The fixture is built so the two claims disagree loudly: `test_ood` follows the
    SAME form with DIFFERENT constants, so the fixed-theta number is terrible and
    the refit number is ~0. Before S8 only the terrible one landed, and the graph
    could only say the discovery failed to extrapolate.
    """

    def _sibling_best_json(self) -> dict:
        self._spec()
        self._table(self._tmp / "prob" / "train.csv", 2.5, -1.0, seed=1)
        self._table(self._tmp / "prob" / "test_id.csv", 2.5, -1.0, seed=2)
        # same FORM, different CONSTANTS: the case the two claims are for
        self._table(self._tmp / "prob" / "test_ood.csv", 6.0, 4.0, seed=3)
        self._cli(
            "init", "--spec", "spec.txt", "--data", "prob/train.csv",
            "--metric", "mse", "--run-id", "e2erefit",
        )
        self._cli("best", "--run", "e2erefit")
        best = self._best("e2erefit")
        assert best["metrics_refit"], "the run must have produced refit numbers"
        return best

    @pytest.mark.asyncio
    async def test_refit_numbers_land_as_their_own_truthfully_labelled_findings(
        self, e2e_config
    ):
        from wheeler.graph.driver import get_async_driver
        from wheeler.integrations.llmsr.discover import ingest_discover

        doc = self._sibling_best_json()
        artifact_path = self._tmp / "best.json"
        artifact_path.write_text(json.dumps(doc))

        report = await ingest_discover(
            doc, config=e2e_config, artifact_path=str(artifact_path),
        )
        await self._tag_run(e2e_config, report)
        assert report.failed is False
        # Script + 3 fixed-theta Findings (train, test_id, test_ood)
        # + 2 refit Findings (test_id, test_ood)
        assert report.created == 6

        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            r = await s.run(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.id AS id, n.title AS title, n.custom_split AS split, "
                "n.custom_claim AS claim, n.custom_regime AS regime, "
                "n.custom_regime_reason AS reason, n.custom_value AS value, "
                "n.custom_measured_by AS measured_by, n.description AS description",
                x=report.execution_id,
            )
            found = {(rec["split"], rec["claim"]): dict(rec) async for rec in r}

        assert set(found) == {
            ("train", CLAIM_CONSTANTS),
            ("test_id", CLAIM_CONSTANTS), ("test_id", CLAIM_FORM),
            ("test_ood", CLAIM_CONSTANTS), ("test_ood", CLAIM_FORM),
        }

        fixed = found[("test_ood", CLAIM_CONSTANTS)]
        refit = found[("test_ood", CLAIM_FORM)]

        # the refit is NOT plain held_out: it fitted its constants on the very
        # split it reports, so it is a claim about the FORM alone
        assert refit["regime"] == REGIME_HELD_OUT_FORM
        assert refit["regime"] != REGIME_HELD_OUT
        assert "FORM only, never for the constants" in refit["reason"]
        assert "Held out for the FORM only" in refit["description"]
        assert "constants REFITTED here" in refit["description"]
        assert refit["title"] == "mse_test_ood_refit"
        assert refit["measured_by"] == MEASURED_BY_FIT

        # the fixed-theta number on the same split is a separate node, keeps the
        # plain label, and is a different number
        assert fixed["regime"] == REGIME_HELD_OUT
        assert fixed["title"] == "mse_test_ood"
        assert fixed["id"] != refit["id"]
        # same form, different constants: the constants do NOT transfer and the
        # form DOES, which is exactly the distinction the two Findings carry
        assert fixed["value"] > 1.0
        assert refit["value"] < 1e-6
