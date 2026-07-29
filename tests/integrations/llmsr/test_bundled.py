"""The bundled specs and their demo tables, run rather than described.

The ``/wh:llmsr-discover`` act told the scientist to use "the matching bundled
spec" for a long while during which nothing was bundled at all. These tests hold
the other end of that promise: every spec named in the registry exists, parses,
and actually scores against the table shipped beside it.

The demo tables are SYNTHETIC and say so everywhere. That claim is the one worth
protecting, so it is checked two ways: the generator that produced them is rerun
and compared against what is checked in, and the oscillator table is fitted with
the law its own generator used, which must come back with an error at the noise
floor. Data whose provenance is a script in the repository is data a reader can
audit; data that merely claims to be synthetic is not.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import recipes as recipes_mod
from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.llmsr.vendor import code_manipulation

runner = CliRunner()

GENERATOR = recipes_mod.demo_data_dir() / "make_demo_data.py"


def _last_json(result) -> dict:
    assert result.exit_code == 0, result.output + str(result.exception)
    return json.loads(result.output.strip().splitlines()[-1])


def _load_generator():
    """Import ``make_demo_data.py`` by path: ``_data`` is not an import package."""
    spec = importlib.util.spec_from_file_location("_llmsr_demo_data", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ALL_SPECS = [pytest.param(key, id=key) for key in sorted(recipes_mod.BUNDLED_SPECS)]


class TestWhatShips:
    def test_every_registered_spec_and_table_is_on_disk(self):
        for spec in recipes_mod.BUNDLED_SPECS.values():
            assert spec.path.is_file(), spec.key
            assert spec.demo_path.is_file(), spec.demo

    def test_every_spec_file_on_disk_is_registered(self):
        """An unlisted spec is invisible to the act, so it is a packaging mistake."""
        shipped = {p.stem for p in recipes_mod.specs_dir().glob("*.txt")}
        assert shipped == set(recipes_mod.BUNDLED_SPECS)

    def test_the_bundled_tree_lives_inside_the_wheeler_package(self):
        """Which is the whole reason it ships, so it is checked rather than assumed.

        Hatchling includes every file inside a listed package by default and
        ``packages = ["wheeler"]`` is what pyproject lists, so no package-data
        glob is involved. The property that could silently break is the location:
        moving these trees to a sibling directory would stop them shipping, and
        the only symptom would be an act telling a user to run a spec that is not
        on their disk.
        """
        import wheeler

        root = Path(wheeler.__file__).resolve().parent
        for tree in (
            recipes_mod.recipes_dir(),
            recipes_mod.specs_dir(),
            recipes_mod.demo_data_dir(),
        ):
            assert tree.resolve().is_relative_to(root), tree

    @pytest.mark.parametrize("key", ALL_SPECS)
    def test_the_spec_declares_exactly_one_of_each_decorated_function(self, key):
        text = recipes_mod.get_spec(key).path.read_text()
        assert len(list(
            code_manipulation.yield_decorated(text, "equation", "evolve")
        )) == 1
        assert len(list(
            code_manipulation.yield_decorated(text, "evaluate", "run")
        )) == 1

    @pytest.mark.parametrize("key", ALL_SPECS)
    def test_the_declared_inputs_are_the_equation_arguments_and_the_table_columns(
        self, key
    ):
        """The registry, the spec signature and the CSV header must agree.

        They are three separate files, and a mismatch would surface as every
        candidate being rejected for arity, which reads like a broken engine
        rather than a mislabelled listing.
        """
        from wheeler.integrations.llmsr import data as data_mod

        bundled = recipes_mod.get_spec(key)
        program = code_manipulation.text_to_program(bundled.path.read_text())
        args = [
            a.split(":")[0].strip()
            for a in program.get_function("equation").args.split(",")
        ]
        assert tuple(args[:-1]) == bundled.inputs
        assert args[-1] == "params"

        columns = data_mod.input_columns(str(bundled.demo_path), bundled.group_by)
        assert columns == bundled.inputs
        header = recipes_mod.read_header(bundled.demo_path)
        assert header[-1] == bundled.target

    @pytest.mark.parametrize("key", ALL_SPECS)
    def test_it_scores_against_the_table_shipped_beside_it(self, key):
        bundled = recipes_mod.get_spec(key)
        argv = [
            "init", "--spec", str(bundled.path), "--data", str(bundled.demo_path),
            "--metric", "nmse", "--run-id", f"bundled-{key}",
        ]
        if bundled.group_by:
            argv += ["--group-by", bundled.group_by]
        out = _last_json(runner.invoke(llmsr_app, argv))
        assert out["seed_valid"] is True, out
        assert math.isfinite(out["seed_value"]), out

    def test_the_grouped_demo_really_has_several_groups(self):
        """Otherwise the spec that exists to demonstrate --group-by demonstrates
        nothing."""
        bundled = recipes_mod.get_spec("bactgrow_strains")
        out = _last_json(runner.invoke(llmsr_app, [
            "init", "--spec", str(bundled.path), "--data", str(bundled.demo_path),
            "--metric", "nmse", "--group-by", bundled.group_by,
            "--run-id", "bundled-groups",
        ]))
        assert set(out["score_keys"]) == {"K12", "B", "W3110"}


class TestTheDemoDataIsWhatItSaysItIs:
    """Synthetic, reproducible, and carrying the law the README claims."""

    def test_the_generator_reproduces_every_shipped_table(self, tmp_path):
        """Rerun the shipped script and compare against the checked-in tables.

        Compared numerically rather than byte for byte on purpose: the laws use
        ``exp``, and a last-bit difference in some other platform's libm is not a
        provenance failure. The header and the row count ARE compared exactly,
        because those cannot drift for a numerical reason.
        """
        written = _load_generator().write_all(tmp_path)
        assert written, "the generator wrote nothing"

        for produced in written:
            shipped = recipes_mod.demo_data_dir() / produced.name
            assert shipped.is_file(), produced.name
            fresh_lines = produced.read_text().splitlines()
            shipped_lines = shipped.read_text().splitlines()
            assert fresh_lines[0] == shipped_lines[0]
            assert len(fresh_lines) == len(shipped_lines)

            for fresh_row, shipped_row in zip(fresh_lines[1:], shipped_lines[1:]):
                fresh_cells = fresh_row.split(",")
                shipped_cells = shipped_row.split(",")
                assert len(fresh_cells) == len(shipped_cells)
                for fresh_cell, shipped_cell in zip(fresh_cells, shipped_cells):
                    try:
                        value = float(fresh_cell)
                    except ValueError:  # a label column, compared verbatim
                        assert fresh_cell == shipped_cell, produced.name
                        continue
                    assert value == pytest.approx(
                        float(shipped_cell), rel=1e-9, abs=1e-9
                    ), produced.name

    def test_the_oscillator_table_carries_the_law_its_generator_used(self):
        """Fit the true form and land at the noise floor, not below it.

        The generator writes ``a = -2.5x - 0.35v - 0.6x**3`` plus a bounded
        error. Recovering that from the shipped CSV is what makes "synthetic, and
        here is the law" an auditable statement rather than a comment.
        """
        from wheeler.integrations.llmsr import fit as fit_mod
        from wheeler.integrations.llmsr import metrics as metrics_mod

        bundled = recipes_mod.get_spec("oscillator")
        rows = np.genfromtxt(bundled.demo_path, delimiter=",", skip_header=1)
        X, y = rows[:, :-1], rows[:, -1]

        text = bundled.path.read_text()
        template = code_manipulation.text_to_program(text)
        true_body = (
            "    return params[0]*x + params[1]*v + params[2]*x**3\n"
        )
        from wheeler.integrations.llmsr.vendor import evaluator

        _fn, program = evaluator._sample_to_program(
            true_body, None, template, "equation"
        )
        result = fit_mod.evaluate_body(
            program, "equation", X, y, metrics_mod.get_metric("nmse"),
        )
        assert result.valid, result.error
        # The recovered constants are the ones the generator used.
        assert result.params[0] == pytest.approx(-2.5, abs=0.05)
        assert result.params[1] == pytest.approx(-0.35, abs=0.05)
        assert result.params[2] == pytest.approx(-0.6, abs=0.05)
        # And the residual is the added error, not zero: there IS a floor here.
        assert 0.0 < result.value < 0.01

    def test_the_strain_table_shares_a_form_and_differs_in_constants(self):
        """The claim ``--group-by`` rests on, checked on the shipped table.

        Each strain is generated with its own gain and its own temperature
        optimum, so a pooled fit is worse than a per-strain refit of the SAME
        form. If that were not true of the demo data, the demo would teach the
        opposite of the protocol.
        """
        generator = _load_generator()
        first = np.asarray(generator.bactgrow_rows(60, seed=11, gain=1.0, temp_opt=37.0))
        second = np.asarray(generator.bactgrow_rows(60, seed=22, gain=0.62, temp_opt=33.5))
        # Same input grid, different response: the constants, not the form, moved.
        assert np.allclose(first[:, :4], second[:, :4], rtol=1e-9)
        assert not np.allclose(first[:, 4], second[:, 4], rtol=1e-2)
