"""Every shipped recipe is RUN here, not described.

A cookbook of scoring strategies is worth having only if the strategies work, and
prose about an ``evaluate`` body rots the moment the engine around it moves. So
each recipe is a real spec template under ``wheeler/_data/llmsr/recipes/``, and
this file fills every one of them against a tiny synthetic table, runs it through
the actual CLI with the flag combination the recipe itself declares, and asserts
a finite score came back.

Four claims, in order of how badly each would fail:

1. **Every recipe runs.** ``TestEveryRecipeExecutes`` walks the whole registry.
   The argv comes from ``Recipe.cli``, which is also what the cookbook quotes and
   what ``scaffold-spec`` prints, so a flag combination cannot drift away from
   the recipe claiming it.
2. **Every recipe's evaluate BODY runs.** Three recipes are flag combinations on
   Wheeler's default door, where the spec's ``evaluate`` is never called. Their
   text would be dead weight if nothing executed it, so each is also run once
   with ``--use-spec-evaluate``.
3. **The torch recipe is not a permanently-skipped test.** torch is absent here,
   so ``torch_adam`` skips. ``numpy_adam`` covers the same claim (the spec can run
   a whole optimizer loop of its own) with no optional dependency, and
   ``TestTheOptimizerLoopReallyRan`` proves the loop RAN rather than being
   compiled and faked, by scoring a 400-step spec against a 1-step one.
4. **The scaffolder generates something that cannot silently be wrong.** A column
   whose name would shadow a variable the recipe binds is renamed; the group
   column and the sigma column are kept out of the equation exactly as the fit
   keeps them out; a recipe that needs data the table cannot supply refuses.

Fixtures are tiny on purpose (30 rows, a 4-constant budget): these tests are about
the plumbing of a scoring strategy, and the numerics of the fit itself are
covered in ``test_optimizers.py`` and ``test_grouped_fit.py``.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr import recipes as recipes_mod
from wheeler.integrations.llmsr import spec_eval as spec_eval_mod
from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.llmsr.vendor import code_manipulation, evaluator

runner = CliRunner()

# The one law every fixture table obeys, so a correct skeleton can reach it and a
# finite score means something. Each table gets its own constants.
#   y = a*x + b*t + c
FORMS = {
    "plain": (2.0, -0.5, 1.0),
    "second": (-1.25, 0.75, -0.5),
    "heldout": (0.4, 1.6, 3.0),
}

# Small enough that numpy_adam's finite-difference gradient stays quick, wide
# enough that the skeleton (one constant per input plus an intercept) fits.
BUDGET = 4


def _rows(a: float, b: float, c: float, n: int = 30, sigma: float = 0.0):
    """``n`` rows of ``(x, t, y)`` on a deterministic grid, exactly on the law."""
    for i in range(n):
        x = -2.0 + 4.0 * i / (n - 1)
        t = (i % 7) / 7.0
        yield x, t, a * x + b * t + c + sigma * ((i % 5) - 2) * 0.01


def _write(path: Path, header: str, lines) -> Path:
    path.write_text("\n".join([header, *lines]) + "\n")
    return path


@pytest.fixture()
def tables(tmp_path) -> dict[str, Path]:
    """One table per role a recipe can ask for: plain, grouped, sigma, extra."""
    out: dict[str, Path] = {}
    for name in ("plain", "second", "heldout"):
        a, b, c = FORMS[name]
        out[name] = _write(
            tmp_path / f"{name}.csv", "x,t,y",
            (f"{x!r},{tt!r},{y!r}" for x, tt, y in _rows(a, b, c)),
        )

    # Two cells sharing the FORM and differing in their constants: what
    # --group-by exists for.
    lines = []
    for cell, (a, b, c) in enumerate([(2.0, -0.5, 1.0), (-3.0, 1.5, 0.25)]):
        for x, tt, y in _rows(a, b, c, n=20):
            lines.append(f"c{cell:02d},{x!r},{tt!r},{y!r}")
    out["grouped"] = _write(tmp_path / "grouped.csv", "cell,x,t,y", lines)

    # A per-point standard deviation, which is the thing a two-argument metric
    # has nowhere to receive.
    a, b, c = FORMS["plain"]
    out["sigma"] = _write(
        tmp_path / "sigma.csv", "x,t,sigma,y",
        (
            f"{x!r},{tt!r},{0.05 + 0.01 * (i % 4)!r},{y!r}"
            for i, (x, tt, y) in enumerate(_rows(a, b, c))
        ),
    )
    return out


def table_for(recipe: recipes_mod.Recipe, tables: dict[str, Path]) -> Path:
    """The fixture table a recipe's declared needs call for."""
    if recipe.grouped:
        return tables["grouped"]
    if recipe.sigma:
        return tables["sigma"]
    return tables["plain"]


def scaffold_for(
    recipe: recipes_mod.Recipe, tables: dict[str, Path], out: Path
) -> recipes_mod.Scaffolded:
    """Fill a recipe against the table its own declaration asks for."""
    data = table_for(recipe, tables)
    scaffolded = recipes_mod.scaffold(
        recipe.key,
        data,
        group_by="cell" if recipe.grouped else "",
        sigma_col="sigma" if recipe.sigma else "",
        max_nparams=BUDGET,
        metric="mse",
        spec_path=str(out),
    )
    out.write_text(scaffolded.text)
    return scaffolded


def init_argv(
    recipe: recipes_mod.Recipe, tables: dict[str, Path], spec: Path
) -> list[str]:
    """The ``init`` argv the recipe itself declares, with real paths filled in.

    Built from ``Recipe.cli`` and nowhere else. That is the anti-drift device: the
    cookbook quotes the same tuple, ``scaffold-spec`` prints the same tuple, and
    this runs it, so a recipe cannot claim a flag combination it was never tried
    with.
    """
    values = {
        "spec": str(spec),
        "data": str(table_for(recipe, tables)),
        "data2": str(tables["second"]),
        "data3": str(tables["heldout"]),
        "group": "cell",
        "metric": "mse",
        "run": "",
    }
    return [token.format(**values) for token in recipe.cli]


def _json(result) -> dict:
    assert result.exit_code == 0, result.output + str(result.exception)
    return json.loads(result.output)


def _last_json(result) -> dict:
    assert result.exit_code == 0, result.output + str(result.exception)
    return json.loads(result.output.strip().splitlines()[-1])


ALL_RECIPES = [
    pytest.param(key, id=key) for key in recipes_mod.available()
]
DEFAULT_DOOR = [
    pytest.param(r.key, id=r.key)
    for r in recipes_mod.RECIPES.values()
    if r.door == recipes_mod.DOOR_DEFAULT
]


# --------------------------------------------------------- 1. every recipe runs

class TestEveryRecipeExecutes:
    """The whole registry, filled and run against a real table."""

    @pytest.mark.parametrize("key", ALL_RECIPES)
    def test_it_scores_under_the_flags_it_declares(self, key, tables, tmp_path):
        recipe = recipes_mod.get_recipe(key)
        for module in recipe.needs:
            pytest.importorskip(module)

        spec = tmp_path / f"{key}_spec.txt"
        scaffold_for(recipe, tables, spec)
        argv = init_argv(recipe, tables, spec)

        out = _last_json(runner.invoke(
            llmsr_app, ["init", *argv, "--run-id", f"r-{key}"]
        ))
        assert out["seed_valid"] is True, out
        assert math.isfinite(out["seed_value"]), out
        # The declared door is the door the run actually took.
        assert out["use_spec_evaluate"] is (recipe.door == recipes_mod.DOOR_SPEC)

    @pytest.mark.parametrize("key", DEFAULT_DOOR)
    def test_its_evaluate_body_is_live_code(self, key, tables, tmp_path):
        """A default-door recipe's ``evaluate`` is never called by its own run.

        Wheeler scores those through its own fit seam, so without this the text
        of three shipped recipes would never execute and could rot unnoticed.
        Running the same spec once through the other door fixes that, and doubles
        as the check that a recipe written for the default door still answers
        when the flag is on.
        """
        recipe = recipes_mod.get_recipe(key)
        spec = tmp_path / f"{key}_door_spec.txt"
        scaffold_for(recipe, tables, spec)
        argv = init_argv(recipe, tables, spec)

        out = _last_json(runner.invoke(llmsr_app, [
            "init", *argv, "--run-id", f"door-{key}", "--use-spec-evaluate",
        ]))
        assert out["seed_valid"] is True, out
        assert math.isfinite(out["seed_value"]), out

    def test_the_transfer_recipe_reaches_a_table_the_search_never_scored(
        self, tables, tmp_path
    ):
        """The follow-up verb is part of the recipe, so it is part of the test."""
        recipe = recipes_mod.get_recipe("transfer")
        spec = tmp_path / "transfer_spec.txt"
        scaffold_for(recipe, tables, spec)
        run_id = "transfer-recipe"
        _last_json(runner.invoke(
            llmsr_app, ["init", *init_argv(recipe, tables, spec), "--run-id", run_id]
        ))
        run_dir = Path(".wheeler/llmsr/runs") / run_id

        values = {"run": str(run_dir), "data3": str(tables["heldout"])}
        argv = [token.format(**values) for token in recipe.then]
        out = _last_json(runner.invoke(llmsr_app, argv))
        assert out["status"] == "completed", out
        # Both questions, side by side: does the FORM carry over (refit) and do
        # the CONSTANTS (fixed theta).
        assert math.isfinite(out["refit_value"])
        assert out["fixed_theta_value"] is None or math.isfinite(
            out["fixed_theta_value"]
        )

    def test_the_grouped_recipe_really_refits_each_cell(self, tables, tmp_path):
        """The claim ``refit_per_group`` makes, checked on the score vector."""
        recipe = recipes_mod.get_recipe("refit_per_group")
        spec = tmp_path / "grouped_spec.txt"
        scaffold_for(recipe, tables, spec)
        run_id = "grouped-recipe"
        _last_json(runner.invoke(
            llmsr_app, ["init", *init_argv(recipe, tables, spec), "--run-id", run_id]
        ))
        run_dir = Path(".wheeler/llmsr/runs") / run_id
        seed = json.loads(
            (run_dir / "submissions.jsonl").read_text().splitlines()[0]
        )
        assert set(seed["per_group"]) == {"c00", "c01"}
        table = seed["params_per_group"]
        # Two cells, two DIFFERENT constant vectors under one shared form.
        assert len({tuple(round(v, 6) for v in p) for p in table.values()}) == 2


# --------------------------------------------------- 2. the registry and files

class TestTheRegistryMatchesWhatShips:
    def test_every_registered_recipe_has_a_template_on_disk(self):
        for recipe in recipes_mod.RECIPES.values():
            assert recipe.template_path.is_file(), recipe.key

    def test_every_template_on_disk_is_registered(self):
        """An unregistered template is invisible, so it is a packaging mistake."""
        shipped = {p.stem for p in recipes_mod.recipes_dir().glob("*.txt")}
        assert shipped == set(recipes_mod.RECIPES)

    @pytest.mark.parametrize("key", ALL_RECIPES)
    def test_a_filled_template_is_valid_python_the_engine_can_parse(
        self, key, tables, tmp_path
    ):
        """Rendered, parsed by the vendored AST tooling, and compiled.

        This is the failure a scientist would otherwise hit at ``init``: a
        template with a stray token or a broken docstring produces a spec that
        does not parse, and the error would point at their file rather than ours.
        """
        recipe = recipes_mod.get_recipe(key)
        spec_text = scaffold_for(recipe, tables, tmp_path / f"{key}.txt").text
        assert "%%" not in spec_text

        fte = list(code_manipulation.yield_decorated(spec_text, "equation", "evolve"))
        ftr = list(code_manipulation.yield_decorated(spec_text, "evaluate", "run"))
        assert len(fte) == len(ftr) == 1
        template = code_manipulation.text_to_program(spec_text)
        _fn, program = evaluator._sample_to_program(
            template.get_function(fte[0]).body, None, template, fte[0]
        )
        compile(program, "spec.py", "exec")

    def test_a_template_naming_an_unknown_token_is_refused(self):
        """Rather than shipping a spec with a literal ``%%FOO%%`` in it."""
        with pytest.raises(ValueError, match="does not supply"):
            recipes_mod._render("x = %%NOT_A_TOKEN%%", {"DOCSTRING": "d"})

    def test_the_declared_door_matches_the_declared_flags(self):
        """A spec-door recipe that forgot ``--use-spec-evaluate`` is inert.

        Its ``evaluate`` would simply never be called, and the run would be scored
        by the default seam while the scientist believed otherwise. That is a
        silent wrong answer, so it is checked rather than trusted.
        """
        for recipe in recipes_mod.RECIPES.values():
            carries = "--use-spec-evaluate" in recipe.cli
            assert carries is (recipe.door == recipes_mod.DOOR_SPEC), recipe.key

    def test_every_recipe_states_what_it_assumes_and_what_it_costs(self):
        for recipe in recipes_mod.RECIPES.values():
            assert recipe.answers.strip()
            assert recipe.assumes.strip()
            assert recipe.costs.strip()

    def test_unknown_recipe_names_the_ones_that_exist(self):
        with pytest.raises(KeyError, match="pooled"):
            recipes_mod.get_recipe("no-such-recipe")


# ------------------------------------------- 3. the optimizer loop really ran

class TestTheOptimizerLoopReallyRan:
    """The door is only as wide as upstream claims if the loop actually executes.

    ``numpy_adam`` could be compiled, ignored, and its return value faked, and a
    finite-score assertion would not notice. Scoring a 400-step spec against a
    1-step one does notice: the only difference between the two texts is the step
    count, so a better score is evidence the steps happened. This is the same
    device ``test_spec_evaluate.py::TestTheDoorIsAsWideAsUpstreamClaims`` uses,
    and it is why ``numpy_adam`` exists beside ``torch_adam``: torch is not
    installed here, and a claim nothing can check is not a claim.
    """

    def _score(self, spec_text: str, X, y):
        fte = list(code_manipulation.yield_decorated(spec_text, "equation", "evolve"))[0]
        ftr = list(code_manipulation.yield_decorated(spec_text, "evaluate", "run"))[0]
        template = code_manipulation.text_to_program(spec_text)
        _fn, program = evaluator._sample_to_program(
            template.get_function(fte).body, None, template, fte
        )
        return spec_eval_mod.evaluate_spec_grouped(
            program, ftr, [("data", "data", X, y)],
            metrics_mod.get_metric("mse"), timeout_seconds=120,
        )

    def test_more_adam_steps_score_better_than_one(self, tables, tmp_path):
        recipe = recipes_mod.get_recipe("numpy_adam")
        spec = scaffold_for(recipe, tables, tmp_path / "adam.txt").text
        assert "STEPS = 400" in spec, "the step count this test varies moved"
        one_step = spec.replace("STEPS = 400", "STEPS = 1")

        rows = np.genfromtxt(tables["plain"], delimiter=",", skip_header=1)
        X, y = rows[:, :-1], rows[:, -1]

        trained = self._score(spec, X, y)
        untrained = self._score(one_step, X, y)

        assert trained.valid and untrained.valid, (trained.error, untrained.error)
        # Higher is better: the score is upstream's maximize-me `-loss`.
        assert trained.score > untrained.score
        # And it got somewhere real, rather than merely somewhere different.
        assert -trained.score < 0.1 * -untrained.score

    def test_the_torch_recipe_runs_when_torch_is_available(self, tables, tmp_path):
        """Skips here (torch is not installed), which is why numpy_adam exists.

        Kept anyway: the recipe ships, so where torch IS installed the shipped
        text is checked rather than assumed.
        """
        pytest.importorskip("torch")

        recipe = recipes_mod.get_recipe("torch_adam")
        spec = scaffold_for(recipe, tables, tmp_path / "torch.txt").text
        rows = np.genfromtxt(tables["plain"], delimiter=",", skip_header=1)
        result = self._score(spec, rows[:, :-1], rows[:, -1])
        assert result.valid, result.error
        assert result.params


# ----------------------------------------------------------- 4. the scaffolder

class TestTheScaffolder:
    """What it reads off the header, and what it refuses to emit."""

    def test_the_equation_takes_every_input_column_in_order(self, tables, tmp_path):
        out = recipes_mod.scaffold("pooled", tables["plain"], max_nparams=BUDGET)
        assert out.inputs == ("x", "t")
        assert out.target == "y"
        assert "def equation(x: np.ndarray, t: np.ndarray, params: np.ndarray)" in out.text

    def test_the_group_column_is_excluded_exactly_as_the_fit_excludes_it(
        self, tables
    ):
        """Same source as ``data.input_columns``, so the signature cannot drift.

        If the scaffolder counted columns itself, a spec for a grouped run would
        declare one argument too many and every candidate would be rejected for
        arity before the search started.
        """
        out = recipes_mod.scaffold(
            "refit_per_group", tables["grouped"], group_by="cell", max_nparams=BUDGET
        )
        assert out.inputs == ("x", "t")
        assert "cell" not in out.text.split('"""')[0]

    def test_the_sigma_column_is_read_but_never_passed_to_the_equation(
        self, tables
    ):
        """It describes the MEASUREMENT, not the law."""
        out = recipes_mod.scaffold(
            "chi_squared", tables["sigma"], sigma_col="sigma", max_nparams=BUDGET
        )
        assert out.inputs == ("x", "t")
        assert out.sigma == "sigma"
        # unpacked from the array, so the recipe can weight by it
        assert "x, t, sigma = inputs[:, 0], inputs[:, 1], inputs[:, 2]" in out.text
        assert "equation(x, t, params)" in out.text

    def test_a_recipe_that_needs_sigma_refuses_without_it(self, tables):
        with pytest.raises(ValueError, match="--sigma-col"):
            recipes_mod.scaffold("chi_squared", tables["sigma"])

    def test_a_recipe_that_does_not_read_sigma_refuses_to_set_a_column_aside(
        self, tables
    ):
        """Because the resulting spec would be silently wrong, not merely useless.

        Setting a column aside drops it from the equation's arguments but not
        from the input array, and Wheeler's default fit binds the leading columns
        POSITIONALLY. Unless the set-aside column happened to be the last one,
        the equation would receive the wrong arrays and still fit, still score,
        and still report a number.
        """
        with pytest.raises(ValueError, match="does not read a per-point error"):
            recipes_mod.scaffold("pooled", tables["sigma"], sigma_col="sigma")

    @pytest.mark.parametrize("bad,fragment", [
        ({"group_by": "nope"}, "not a column"),
        ({"group_by": "y"}, "is the target column"),
        ({"sigma_col": "nope"}, "not an input column"),
        ({"max_nparams": 0}, "at least 1"),
    ])
    def test_it_refuses_rather_than_emitting_a_spec_that_cannot_run(
        self, tables, bad, fragment
    ):
        with pytest.raises(ValueError, match=fragment):
            recipes_mod.scaffold("pooled", tables["plain"], **bad)

    def test_a_table_with_no_input_column_is_refused(self, tmp_path):
        only_target = _write(tmp_path / "one.csv", "y", ["1.0", "2.0"])
        with pytest.raises(ValueError, match="at least one input column"):
            recipes_mod.scaffold("pooled", only_target)

    def test_a_header_that_is_not_a_python_name_becomes_one(self, tmp_path):
        odd = _write(
            tmp_path / "odd.csv", "Temp (C),2nd probe,class,y",
            ["1,2,3,4", "5,6,7,8"],
        )
        out = recipes_mod.scaffold("pooled", odd, max_nparams=BUDGET)
        assert out.inputs == ("Temp_C", "x1_2nd_probe", "class_")
        assert out.columns == ("Temp (C)", "2nd probe", "class")

    def test_a_column_that_would_shadow_the_recipe_is_renamed(self, tmp_path):
        """The silent failure this prevents, spelled out.

        Every recipe binds ``y`` for the target array partway through
        ``evaluate``. A column also called ``y`` would be unpacked first and then
        overwritten, so the call to ``equation`` would pass the TARGET where an
        input belongs and the fit would be scored against the wrong array without
        raising anything. The reserved set is read off the template itself, so it
        cannot fall behind a recipe that gains a local.
        """
        shadow = _write(tmp_path / "shadow.csv", "y,pred,target", ["1,2,3", "4,5,6"])
        out = recipes_mod.scaffold("robust", shadow, max_nparams=BUDGET)
        assert out.inputs == ("y_2", "pred_2")
        assert "y_2, pred_2 = inputs[:, 0], inputs[:, 1]" in out.text
        # and the recipe's own binding is untouched
        assert "y = np.asarray(outputs, dtype=float).reshape(-1)" in out.text

    def test_the_printed_command_is_the_recipe_it_filled(self, tables, tmp_path):
        spec = tmp_path / "s.txt"
        out = recipes_mod.scaffold(
            "refit_per_group", tables["grouped"], group_by="cell",
            metric="nmse", spec_path=str(spec),
        )
        assert out.command == (
            "--spec", str(spec), "--data", str(tables["grouped"]),
            "--metric", "nmse", "--group-by", "cell",
        )

    def test_an_unfilled_role_shows_as_a_placeholder_not_a_wrong_path(
        self, tables
    ):
        """``transfer`` needs a second table the scaffolder cannot know about."""
        out = recipes_mod.scaffold("transfer", tables["plain"])
        assert "B=<SECOND_TABLE.csv>" in out.command
        assert "<HELD_OUT.csv>" in out.then


# --------------------------------------------------------------- the CLI verbs

class TestTheVerbs:
    def test_recipes_lists_every_recipe_with_its_door(self):
        out = _json(runner.invoke(llmsr_app, ["recipes"]))
        listed = {r["key"]: r for r in out["recipes"]}
        assert set(listed) == set(recipes_mod.RECIPES)
        assert listed["chi_squared"]["uses_spec_evaluate"] is True
        assert listed["pooled"]["uses_spec_evaluate"] is False
        assert out["default"] == recipes_mod.DEFAULT_RECIPE

    def test_recipes_says_whether_a_dependency_is_actually_here(self):
        """A recipe needing torch is listed but not advertised as ready."""
        listed = {
            r["key"]: r for r in _json(runner.invoke(llmsr_app, ["recipes"]))["recipes"]
        }
        assert listed["pooled"]["ready"] is True
        assert listed["torch_adam"]["ready"] is recipes_mod.is_importable("torch")

    def test_specs_lists_the_bundled_specs_and_says_the_data_is_synthetic(self):
        out = _json(runner.invoke(llmsr_app, ["specs"]))
        keys = {s["key"] for s in out["specs"]}
        assert keys == set(recipes_mod.BUNDLED_SPECS)
        assert all(s["synthetic_demo_data"] for s in out["specs"])

    def test_scaffold_spec_writes_a_file_and_prints_the_command(
        self, tables, tmp_path
    ):
        out_path = tmp_path / "written" / "spec.txt"
        payload = _json(runner.invoke(llmsr_app, [
            "scaffold-spec", "--data", str(tables["plain"]),
            "--recipe", "pooled", "--max-nparams", str(BUDGET),
            "--metric", "mse", "--out", str(out_path),
        ]))
        assert out_path.read_text() == payload["spec"]
        assert payload["command"][:3] == ["wheeler", "llmsr", "init"]
        assert str(out_path.resolve()) in payload["command"]
        assert payload["inputs"] == ["x", "t"]
        assert payload["door"] == recipes_mod.DOOR_DEFAULT

    def test_scaffold_spec_output_is_runnable_as_printed(self, tables, tmp_path):
        """The command it prints is run verbatim, and the run scores.

        This is the whole promise of the verb: the scientist should not have to
        assemble anything after it. Dropping the leading ``wheeler llmsr``, which
        the in-process CLI runner supplies itself.
        """
        out_path = tmp_path / "runnable.txt"
        payload = _json(runner.invoke(llmsr_app, [
            "scaffold-spec", "--data", str(tables["plain"]),
            "--recipe", "shape_only", "--max-nparams", str(BUDGET),
            "--metric", "mse", "--out", str(out_path),
        ]))
        argv = payload["command"][2:] + ["--run-id", "as-printed"]
        result = _last_json(runner.invoke(llmsr_app, argv))
        assert result["seed_valid"] is True
        assert result["use_spec_evaluate"] is True

    def test_a_bad_recipe_name_is_a_usage_error_not_a_traceback(self, tables):
        result = runner.invoke(llmsr_app, [
            "scaffold-spec", "--data", str(tables["plain"]), "--recipe", "nope",
        ])
        assert result.exit_code != 0
        assert "unknown recipe" in result.output


# ---------------------------------------------------------------- the cookbook

COOKBOOK = Path(__file__).resolve().parents[3] / "docs" / "llmsr-spec-cookbook.md"


def _sections() -> dict[str, str]:
    """The cookbook split into its ``### <key>`` recipe sections."""
    text = COOKBOOK.read_text()
    out: dict[str, str] = {}
    for chunk in text.split("\n### ")[1:]:
        heading, _, body = chunk.partition("\n")
        out[heading.strip()] = body
    return out


@pytest.mark.skipif(not COOKBOOK.is_file(), reason="cookbook is repo-only")
class TestTheCookbookMatchesTheRegistry:
    """The document and the registry are two files, so they are pinned together.

    The registry is the source: ``answers`` / ``assumes`` / ``costs`` are strings
    on the ``Recipe`` because ``wheeler llmsr recipes`` has to say them at the
    terminal (a shipped user has the package, not this repository's ``docs/``).
    The cookbook quotes them, and this checks the quotation. A recipe added,
    renamed or re-described without the document following fails here rather than
    misleading a scientist six months from now.
    """

    def test_every_recipe_has_a_section(self):
        assert set(_sections()) >= set(recipes_mod.RECIPES)

    @pytest.mark.parametrize("key", ALL_RECIPES)
    def test_the_section_quotes_the_registry_verbatim(self, key):
        section = _sections()[key]
        recipe = recipes_mod.get_recipe(key)
        assert recipe.answers in section
        assert recipe.assumes in section
        assert recipe.costs in section
        assert "- **Door**:" in section

    @pytest.mark.parametrize("key", ALL_RECIPES)
    def test_the_section_shows_the_flags_the_recipe_pairs_with(self, key):
        """The load-bearing half of a worked example.

        A recipe whose document showed a different flag combination from the one
        the test actually runs would be worse than no document: the scientist
        would run the shown command and get a different measurement from the one
        described above it.
        """
        section = _sections()[key]
        for flag in recipes_mod.get_recipe(key).flags():
            assert flag in section, f"{key} pairs with {flag}, the cookbook omits it"

    def test_the_document_does_not_invent_a_recipe(self):
        """A section for a recipe that does not exist is a command that fails."""
        headed = set(_sections())
        invented = {
            name for name in headed
            if name.replace("-", "_").islower() and " " not in name
        } - set(recipes_mod.RECIPES)
        assert not invented, invented
