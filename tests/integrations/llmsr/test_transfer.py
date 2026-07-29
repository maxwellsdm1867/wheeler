"""The `transfer` verb: does the FORM transfer, or only the CONSTANTS?

The scientific claim under test, and the gate for issue #107 slice S3: three
cells share the law ``y = a*x + b`` with DIFFERENT ``(a, b)``. A search is run on
cell A alone. Transferring that form onto held-out cells B and C must recover
each cell's OWN ``(a, b)`` (the FORM transfers), while cell A's constants applied
unchanged to B and C score far worse (the CONSTANTS do not). Both numbers land in
``transfer.json``, labelled, so neither can be read as the other.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import transfer as transfer_mod
from wheeler.integrations.llmsr.cli import llmsr_app

runner = CliRunner()

# One law, three cells, three different constant pairs.
CELLS = {"c01": (2.5, -1.0), "c02": (-4.0, 8.0), "c03": (0.5, 3.0)}

# The spec's seed body IS the true form, so the search starts from the law and
# the question under test is purely whether it transfers.
SPEC = (
    "import numpy as np\n\n"
    "MAX_NPARAMS = 4\n\n"
    "@evaluate.run\n"
    "def evaluate(data):\n"
    "    return 0.0\n\n"
    "@equation.evolve\n"
    "def equation(x1, params):\n"
    "    return params[0] * x1 + params[1]\n"
)


def _rows(cell: str, n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    a, b = CELLS[cell]
    x = np.random.default_rng(seed).uniform(-3.0, 3.0, n)
    return x, a * x + b


def _write_ungrouped(path: Path, cell: str, n: int = 40, seed: int = 1) -> None:
    """One cell, no group column: the shape a single-cell training file has."""
    x, y = _rows(cell, n, seed)
    lines = ["x1,y"] + [f"{float(xi):.17g},{float(yi):.17g}" for xi, yi in zip(x, y)]
    path.write_text("\n".join(lines) + "\n")


def _write_grouped(path: Path, cells: list[str], n: int = 40, seed: int = 7) -> None:
    """Several cells with a group column naming which cell each row belongs to."""
    lines = ["cell_id,x1,y"]
    for i, cell in enumerate(cells):
        x, y = _rows(cell, n, seed + i)
        lines += [
            f"{cell},{float(xi):.17g},{float(yi):.17g}" for xi, yi in zip(x, y)
        ]
    path.write_text("\n".join(lines) + "\n")


def _out(result) -> dict:
    assert result.exit_code == 0, result.output
    return json.loads(result.output.strip().splitlines()[-1])


def _short_search_on_cell_a(tmp_path: Path, run_id: str = "cellA") -> Path:
    """init (seed = the true form) plus one submit of a decoy that fits worse."""
    spec = tmp_path / "spec.txt"
    spec.write_text(SPEC)
    train = tmp_path / "cellA.csv"
    _write_ungrouped(train, "c01")

    _out(runner.invoke(llmsr_app, [
        "init", "--spec", str(spec), "--data", str(train),
        "--metric", "mse", "--run-id", run_id,
    ]))
    rd = Path(".wheeler/llmsr/runs") / run_id

    p = _out(runner.invoke(llmsr_app, ["prompt", "--run", str(rd)]))
    decoy = tmp_path / "decoy.py"
    decoy.write_text("    return params[0] * x1**3 + params[1]")
    _out(runner.invoke(llmsr_app, [
        "submit", "--run", str(rd), "--body-file", str(decoy),
        "--island-id", str(p["island_id"]),
        "--version-generated", str(p["version_generated"]),
    ]))
    return rd


class TestTheFormTransfers:
    """The gate: the refit recovers each held-out cell, fixed theta does not."""

    def test_refit_recovers_each_held_out_cell_and_fixed_theta_does_not(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path)
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])

        res = _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--group-by", "cell_id",
        ]))
        assert res["status"] == "completed"
        assert res["groups"] == ["c02", "c03"]

        payload = json.loads((rd / transfer_mod.TRANSFER_FILE).read_text())
        refit = payload["refit"]
        fixed = payload["fixed_theta"]

        # The FORM transfers: every held-out cell refits to ITS OWN constants.
        assert refit["valid"] is True
        for cell in ("c02", "c03"):
            a, b = CELLS[cell]
            got = refit["params_per_group"][cell]
            assert got[0] == pytest.approx(a, abs=1e-6)
            assert got[1] == pytest.approx(b, abs=1e-6)
            assert refit["value_per_group"][cell] == pytest.approx(0.0, abs=1e-12)
        assert refit["value"] == pytest.approx(0.0, abs=1e-12)

        # The CONSTANTS do not: cell A's theta applied to B and C is far worse.
        assert fixed["value"] is not None
        assert fixed["value"] > 1.0
        assert fixed["value"] > refit["value"] * 1e6 + 1.0

        # And the two are labelled as claims about different things, never one
        # standing in for the other.
        assert refit["claim"] == transfer_mod.CLAIM_FORM
        assert fixed["claim"] == transfer_mod.CLAIM_CONSTANTS
        assert "FORM" in refit["label"]
        assert "CONSTANTS" in fixed["label"]
        assert payload["comparison"]["refit_value"] == refit["value"]
        assert payload["comparison"]["fixed_theta_value"] == fixed["value"]

    def test_the_source_cell_is_the_one_fixed_theta_does_fit(self, tmp_path):
        """The control: applied back to cell A, the source constants are right.

        Without this, "fixed theta is far worse" could just mean the fixed-theta
        path is broken rather than that the constants are cell-specific.
        """
        rd = _short_search_on_cell_a(tmp_path, run_id="control")
        same = tmp_path / "cellA_again.csv"
        _write_ungrouped(same, "c01", seed=99)

        _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(same),
        ]))
        payload = json.loads((rd / transfer_mod.TRANSFER_FILE).read_text())
        assert payload["fixed_theta"]["value"] == pytest.approx(0.0, abs=1e-10)
        assert payload["refit"]["value"] == pytest.approx(0.0, abs=1e-12)


class TestTheHoldoutStaysClean:
    """A number that fed back into the search would stop being a holdout."""

    def test_submissions_and_buffer_are_byte_identical(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path, run_id="clean")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])

        from wheeler.integrations.llmsr.cli import _rebuild_buffer
        from wheeler.integrations.llmsr.runs import _read_meta

        def _shape(db):
            """What the buffer holds: per island, its clusters and their scores.

            The buffer has no persisted form of its own (it is replayed from the
            log on every call), so "unchanged" means replaying the log after the
            transfer reconstructs exactly the same islands.
            """
            return [
                sorted(
                    (sig, cluster.score)
                    for sig, cluster in island._clusters.items()
                )
                + [("_num_programs", island._num_programs)]
                for island in db._islands
            ]

        log = rd / "submissions.jsonl"
        before_bytes = log.read_bytes()
        meta = _read_meta(rd)
        _template, db_before, _fte = _rebuild_buffer(rd, meta)
        buffer_before = _shape(db_before)

        _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--group-by", "cell_id",
        ]))

        assert log.read_bytes() == before_bytes
        _template, db_after, _fte = _rebuild_buffer(rd, meta)
        assert _shape(db_after) == buffer_before

    def test_no_new_files_beyond_transfer_json_and_status(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path, run_id="files")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])
        before = {p.name for p in rd.iterdir()}

        _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--group-by", "cell_id",
        ]))
        after = {p.name for p in rd.iterdir()}
        # transfer.json is the product; progress.json is S0b's during-the-fit
        # channel. Nothing else appears, and best.json is NOT written.
        assert after - before <= {transfer_mod.TRANSFER_FILE, "progress.json"}
        assert "best.json" not in after

    def test_status_does_not_report_a_phantom_fit_afterwards(self, tmp_path):
        """The progress ping is the DURING channel; it must be closed out."""
        rd = _short_search_on_cell_a(tmp_path, run_id="phase")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])

        _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--group-by", "cell_id",
        ]))
        st = _out(runner.invoke(llmsr_app, ["status", "--run", str(rd)]))
        assert st["phase"] != "fitting"
        # and the search snapshot is unchanged by the transfer
        assert st["n_samples"] == 2


class TestCandidateResolution:
    def test_explicit_candidate_is_transferred(self, tmp_path):
        """--candidate names a sample_order, overriding selection."""
        rd = _short_search_on_cell_a(tmp_path, run_id="explicit")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])

        res = _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--group-by", "cell_id", "--candidate", "1",
        ]))
        assert res["sample_order"] == 1
        assert res["selected_by"] == "explicit"
        payload = json.loads((rd / transfer_mod.TRANSFER_FILE).read_text())
        # sample 1 is the decoy cubic, not the true linear form
        assert "x1**3" in payload["candidate"]["equation"]

    def test_default_selection_picks_the_winner(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path, run_id="winner")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])

        res = _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--group-by", "cell_id",
        ]))
        assert res["selected_by"] == "fit"
        payload = json.loads((rd / transfer_mod.TRANSFER_FILE).read_text())
        assert "x1**3" not in payload["candidate"]["equation"]

    def test_unknown_candidate_is_rejected(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path, run_id="unknown")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])
        res = runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--candidate", "99",
        ])
        assert res.exit_code != 0
        assert "99" in res.output

    def test_bad_select_mode_is_rejected(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path, run_id="badmode")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])
        res = runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--select", "vibes",
        ])
        assert res.exit_code != 0


class TestStrictness:
    def test_a_group_that_cannot_refit_exits_non_zero(self, tmp_path):
        """Strict, matching evaluate_body_grouped: one blind group fails the lot."""
        rd = _short_search_on_cell_a(tmp_path, run_id="strict")
        bad = tmp_path / "bad.csv"
        # c02's rows are fine; c03's target is unreachable by any real a*x+b.
        lines = ["cell_id,x1,y"]
        x, y = _rows("c02", 20, 4)
        lines += [f"c02,{float(a):.17g},{float(b):.17g}" for a, b in zip(x, y)]
        lines += [f"c03,{float(v):.17g},inf" for v in x]
        bad.write_text("\n".join(lines) + "\n")

        res = runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(bad),
            "--group-by", "cell_id",
        ])
        assert res.exit_code == 1
        payload = json.loads((rd / transfer_mod.TRANSFER_FILE).read_text())
        assert payload["status"] == "failed"
        assert payload["refit"]["valid"] is False
        assert "c03" in payload["refit"]["error"]
        # The fixed-theta number is INDEPENDENT and still reported: what the old
        # constants scored is exactly what you want when the refit fails.
        assert payload["fixed_theta"]["value_per_group"]["c02"] is not None

    def test_unreadable_group_column_fails_without_numbers(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path, run_id="nogroupcol")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])
        res = runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--group-by", "not_a_column",
        ])
        assert res.exit_code == 1
        payload = json.loads((rd / transfer_mod.TRANSFER_FILE).read_text())
        assert payload["status"] == "failed"
        assert payload["refit"]["value"] is None
        assert payload["fixed_theta"]["value"] is None


class TestRegimeLabels:
    def test_new_data_is_held_out(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path, run_id="regime_new")
        held_out = tmp_path / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])
        _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(held_out),
            "--group-by", "cell_id",
        ]))
        payload = json.loads((rd / transfer_mod.TRANSFER_FILE).read_text())
        assert payload["fixed_theta"]["regime"] == transfer_mod.REGIME_HELD_OUT
        # The refit fitted constants on this data, so it is held out for the FORM
        # ONLY, and it carries its own LABEL rather than borrowing the plain one:
        # `held_out` unqualified would claim the constants transferred too. S8
        # gave `discover.py` the same fourth label so a Finding reads the same.
        assert payload["refit"]["regime"] == transfer_mod.REGIME_HELD_OUT_FORM
        assert payload["refit"]["regime"] != transfer_mod.REGIME_HELD_OUT
        assert "FORM only" in payload["refit"]["regime_reason"]

    def test_the_two_modules_agree_on_the_refit_label(self):
        """`transfer.py` duplicates the vocabulary as literals; they must match."""
        from wheeler.integrations.llmsr import discover as discover_mod

        for name in (
            "REGIME_SCORED", "REGIME_HELD_OUT", "REGIME_HELD_OUT_FORM",
            "REGIME_UNKNOWN", "CLAIM_FORM", "CLAIM_CONSTANTS",
        ):
            assert getattr(transfer_mod, name) == getattr(discover_mod, name), name

    def test_the_runs_own_training_data_is_scored(self, tmp_path):
        rd = _short_search_on_cell_a(tmp_path, run_id="regime_train")
        _out(runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(tmp_path / "cellA.csv"),
        ]))
        payload = json.loads((rd / transfer_mod.TRANSFER_FILE).read_text())
        assert payload["fixed_theta"]["regime"] == transfer_mod.REGIME_SCORED
        assert "fitted the constants here" in payload["fixed_theta"]["regime_reason"]


class TestFixedThetaPolicy:
    """A source constant vector is applied only where one legitimately belongs."""

    def test_a_grouped_source_reports_nothing_for_an_unknown_group(self, tmp_path):
        from wheeler.integrations.llmsr.selection import _source_theta

        source = {"params_per_group": {"c01": [1.0], "c02": [2.0]}, "params": []}
        theta, why = _source_theta(source, "c99")
        assert theta is None
        assert "none of them belongs to this group" in why

    def test_a_grouped_source_uses_that_groups_own_constants(self):
        from wheeler.integrations.llmsr.selection import _source_theta

        source = {"params_per_group": {"c01": [1.0], "c02": [2.0]}, "params": []}
        assert _source_theta(source, "c02") == (
            [2.0], "the source fitted this same group"
        )

    def test_an_ungrouped_source_applies_its_one_vector_anywhere(self):
        from wheeler.integrations.llmsr.selection import _source_theta

        source = {"params_per_group": {"data": [3.0, 4.0]}, "params": [3.0, 4.0]}
        theta, why = _source_theta(source, "c07")
        assert theta == [3.0, 4.0]
        assert why == "the source has a single constant vector"

    def test_a_partial_aggregate_is_not_reported(self):
        from wheeler.integrations.llmsr.selection import _strict_mean

        assert _strict_mean({"a": 1.0, "b": None}) is None
        assert _strict_mean({"a": 1.0, "b": 3.0}) == 2.0
        assert _strict_mean({}) is None
