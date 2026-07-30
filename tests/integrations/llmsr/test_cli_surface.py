"""The seam between what the LIBRARY can do and what the CLI actually exposes.

An adversarial audit found two HIGH defects that 364 green tests and two clean
parity gates had all missed, and both of them lived here. The loader registry was
fully built, fully unit-tested at library level, and UNREACHABLE: ``init`` had no
``--loader`` flag, so ``meta["loader"]`` was never written and every run silently
fell back to csv. The emitted ``.py`` published the spec door's own loss under the
run's declared metric name, a number 19x away from the one the same run's
``best.json`` recorded under that name.

Neither is findable by testing a module. Both are findable by two rules, which
this file exists to keep:

**1. Every open registry is reachable THROUGH `wheeler llmsr init`.** A registry a
scientist can add to but not select is a feature that does not exist. Checked
structurally (the flag is on the command) and behaviourally (a registration made
the standard way changes what the run does).

**2. Every emitted METRIC label is checked against the same run's own best.json.**
A number is never published under the name of a metric that did not produce it.
The .py is the durable, re-runnable half of a discovery, so a wrong label there
outlives everything else in the run.

No live model and no Neo4j: everything runs against the scratch project the
directory's ``conftest.py`` gives every test.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import loaders as loaders_mod
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr import optimizers as optimizers_mod
from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.llmsr.discover import SCORED_BY_SPEC_EVALUATE

runner = CliRunner()


# --------------------------------------------------------------- CLI harness

def _out(result) -> dict:
    assert result.exit_code == 0, result.output + str(result.exception)
    return json.loads(result.output.strip().splitlines()[-1])


def _walk(run_id: str, args: list[str], body: str = "", run_best: bool = True) -> dict:
    """``init`` (-> ``submit``) -> ``best``, handing back what the run wrote.

    A candidate body is optional: ``init`` already scores the spec's own seed, so
    a run with no submission still has a winner and still writes a ``best.json``
    and a program. A fixed island id keeps the walk reproducible, since the
    vendored buffer picks one at random.

    ``run_best=False`` is for a run that is EXPECTED to find nothing valid, where
    ``best`` exits non-zero by design. That case is a control, not a failure.
    """
    init = _out(runner.invoke(llmsr_app, ["init", "--run-id", run_id, *args]))
    run_dir = Path(".wheeler/llmsr/runs") / run_id
    if body:
        body_file = Path(f"{run_id}_body.py")
        body_file.write_text(body)
        _out(runner.invoke(llmsr_app, [
            "submit", "--run", str(run_dir), "--body-file", str(body_file),
            "--island-id", "0", "--version-generated", "0",
        ]))
    if run_best:
        _out(runner.invoke(llmsr_app, ["best", "--run", str(run_dir)]))
    return {
        "init": init,
        "run_dir": run_dir,
        "meta": json.loads((run_dir / "meta.json").read_text()),
        "best": (
            json.loads((run_dir / "best.json").read_text()) if run_best else {}
        ),
        "submissions": [
            json.loads(line)
            for line in (run_dir / "submissions.jsonl").read_text().splitlines()
            if line.strip()
        ],
    }


# ---------------------------------------------------------------- the fixtures

# One shared law, y = a*x1 + b*x2, three cells with DIFFERENT constants, so a
# per-cell refit is the only thing that fits them all.
CELLS = {"c01": (2.5, -1.0), "c02": (-4.0, 8.0), "c03": (0.5, 3.0)}

TRUE_BODY = "    return params[0]*x1 + params[1]*x2\n"


def _write_grouped_csv(path: str = "train.csv", dead_cell: str = "", n: int = 20) -> str:
    """A grouped table. ``dead_cell`` names a cell whose target is missing.

    An empty target reads back as NaN, which is what a dropped channel or an
    aborted trial looks like by the time it reaches a table, and it is the case
    the per-group fit is STRICT about: one such cell invalidates a correct law.
    """
    rng = np.random.default_rng(11)
    lines = ["x1,x2,cell,y"]
    for name, (a, b) in CELLS.items():
        for _ in range(n):
            x1, x2 = (float(v) for v in rng.uniform(-3.0, 3.0, 2))
            y = "" if name == dead_cell else f"{a * x1 + b * x2:.17g}"
            lines.append(f"{x1:.17g},{x2:.17g},{name},{y}")
    Path(path).write_text("\n".join(lines) + "\n")
    return path


def _spec(evaluate_body: str, signature: str = "x1: np.ndarray, x2: np.ndarray") -> str:
    """A runnable spec whose ``evaluate`` is whatever the caller needs it to be."""
    return (
        '"""toy"""\n'
        "import numpy as np\n\n"
        "MAX_NPARAMS = 2\n\n\n"
        "@evaluate.run\n"
        "def evaluate(data: dict):\n"
        + evaluate_body
        + "\n\n@equation.evolve\n"
        f"def equation({signature}, params: np.ndarray) -> np.ndarray:\n"
        "    return params[0]*x1\n"
    )


# An ``evaluate`` that minimizes MEAN SQUARED ERROR, which is what every bundled
# recipe and every upstream spec does. Paired with ``--metric nmse`` it is the
# exact configuration the audit reproduced: the spec's loss and the run's
# declared metric are different quantities, and nothing checks that they agree.
_MSE_EVALUATE = """    from scipy.optimize import minimize

    inputs, outputs = data['inputs'], data['outputs']
    x1, x2 = inputs[:, 0], inputs[:, 1]

    def loss(params):
        return float(np.mean((equation(x1, x2, params) - outputs) ** 2))

    result = minimize(loss, [1.0] * MAX_NPARAMS, method='BFGS')
    if not np.isfinite(result.fun):
        return None
    return {'score': -float(result.fun), 'params': [float(p) for p in result.x]}
"""

# The same thing under UPSTREAM'S contract: a bare float, with the fitted
# constants computed and thrown away, which is what every upstream spec does.
_BARE_FLOAT_EVALUATE = _MSE_EVALUATE.replace(
    "    return {'score': -float(result.fun), 'params': [float(p) for p in result.x]}",
    "    return -float(result.fun)",
)


# ===========================================================================
# 1. Every open registry is reachable THROUGH `wheeler llmsr init`
# ===========================================================================

# Each open registry, the ``init`` flag that selects from it, and the listing
# verb that reports it. Adding a registry without adding its row here is the
# thing this table exists to make impossible to do quietly.
OPEN_REGISTRIES = (
    pytest.param("metric", metrics_mod.available, "metrics", id="metric"),
    pytest.param("loader", loaders_mod.available, "loaders", id="loader"),
    pytest.param("optimizer", optimizers_mod.choices, "optimizers", id="optimizer"),
)


def _init_option_names() -> set[str]:
    """Every long option ``wheeler llmsr init`` actually accepts.

    Read off the built click command rather than grepped out of ``--help``,
    because help text is wrapped for a terminal and a wrapped flag would make
    this pass for the wrong reason.
    """
    from typer.main import get_command

    init_cmd = get_command(llmsr_app).commands["init"]  # type: ignore[attr-defined]
    return {opt for param in init_cmd.params for opt in param.opts}


class TestEveryOpenRegistryIsReachableFromInit:
    """A registry a scientist can register into but not SELECT does not exist.

    This is the rule the loader registry broke: ``loaders.py``,
    ``load_groups``, the userland source convention, the ``loaders`` listing
    verb and the ``options_from`` port in ``services.default.yaml`` were all
    built and all green, and ``init`` had no ``--loader``, so ``cli.py`` read a
    ``meta["loader"]`` that nothing ever wrote.
    """

    @pytest.mark.parametrize("flag,available,listing", OPEN_REGISTRIES)
    def test_the_registry_has_an_init_flag(self, flag, available, listing):
        assert f"--{flag}" in _init_option_names(), (
            f"the {flag!r} registry can be registered into and listed "
            f"(`wheeler llmsr {listing}`) but not selected at init"
        )

    @pytest.mark.parametrize("flag,available,listing", OPEN_REGISTRIES)
    def test_every_choice_the_listing_offers_is_one_init_accepts(
        self, flag, available, listing
    ):
        """The listing is what the act and the service contract offer FROM.

        ``services.default.yaml`` points each port at ``available()`` through
        ``options_from``, so an offered answer that ``init`` rejects would put an
        unanswerable question in the interview. Checked by actually running
        ``init`` once per offered choice rather than by comparing two lists,
        because two lists agreeing is what the audit found was not enough.

        The registries are restored to the built-ins by this directory's
        ``conftest.py``, so what this covers is what SHIPS.
        """
        data = _write_grouped_csv(n=4)
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        offered = available()
        assert offered, f"`wheeler llmsr {listing}` reports nothing registered"

        for i, choice in enumerate(offered):
            args = ["init", "--spec", "spec.txt", "--data", data,
                    "--run-id", f"{flag}-{i}", f"--{flag}", choice]
            if flag != "metric":
                args += ["--metric", "mse"]
            res = runner.invoke(llmsr_app, args)
            assert res.exit_code == 0, (
                f"`wheeler llmsr {listing}` offers {choice!r}, which init "
                f"rejected:\n{res.output}"
            )

    def test_a_registered_metric_is_selectable_at_init(self):
        """The registered metric is what the run's own numbers are in.

        Deliberately a SCALED mse (x1000) rather than something like MAE: it
        keeps the fit well behaved while making the reported value unmistakably
        the scientist's metric, since a silent fallback to the built-in mse would
        report a number a thousand times smaller. The seed body is used rather
        than the true form precisely so the error is non-zero and the factor is
        visible.
        """
        Path(".wheeler/llmsr").mkdir(parents=True)
        Path(".wheeler/llmsr/metrics.py").write_text(
            "import numpy as np\n"
            "from wheeler.integrations.llmsr.metrics import (\n"
            "    REGRESSION, Metric, register_metric)\n"
            "def _kilo_mse(pred, target):\n"
            "    d = np.asarray(pred, dtype=float) - np.asarray(target, dtype=float)\n"
            "    return 1000.0 * float(np.mean(d ** 2))\n"
            "register_metric(Metric(key='kilo-mse', label='mse x 1000',\n"
            "    data_shape=REGRESSION, lower_is_better=True,\n"
            "    loss=_kilo_mse, report=_kilo_mse))\n"
        )
        data = _write_grouped_csv()
        Path("spec.txt").write_text(_spec("    return 0.0\n"))

        walk = _walk("reg-metric", [
            "--spec", "spec.txt", "--data", data, "--metric", "kilo-mse",
        ])

        assert walk["meta"]["metric"] == "kilo-mse"
        assert walk["best"]["metric"] == "kilo-mse"
        # The number really came from the scientist's metric: it is exactly a
        # thousand times the mse the same run reports beside it.
        seed_value = walk["submissions"][0]["value"]
        assert seed_value > 0
        assert seed_value == pytest.approx(
            1000.0 * walk["best"]["metrics"]["mse_train"]
        )

    def test_a_registered_loader_is_selectable_at_init_and_really_excludes(self):
        """The F2 regression test: a loader chosen at init EXCLUDES the bad cell.

        The exclusion is the point, not the plumbing. Per-group validity is
        strict, so the dead cell invalidates a form that is exactly right;
        selecting the loader is the only way to keep that law, and until
        ``--loader`` existed it could not be selected.
        """
        Path(".wheeler/llmsr").mkdir(parents=True)
        Path(".wheeler/llmsr/loaders.py").write_text(
            "import numpy as np\n"
            "from wheeler.integrations.llmsr.loaders import (\n"
            "    Loader, get_loader, register_loader)\n"
            "def healthy_cells(request):\n"
            "    groups = get_loader('csv').load(request)\n"
            "    return [g for g in groups\n"
            "            if np.isfinite(np.asarray(g.y, dtype=float)).all()]\n"
            "register_loader(Loader(key='healthy-cells',\n"
            "    label='CSV, excluding cells with missing targets',\n"
            "    load=healthy_cells))\n"
        )
        data = _write_grouped_csv(dead_cell="c02")
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        args = ["--spec", "spec.txt", "--data", data, "--metric", "mse",
                "--group-by", "cell"]

        # The control: the default csv loader hands the dead cell to the fit, and
        # the correct form is rejected because of it. `best` is not walked here,
        # because there is deliberately nothing valid for it to find.
        control = _walk("loader-csv", args, body=TRUE_BODY, run_best=False)
        assert control["init"]["score_keys"] == ["c01", "c02", "c03"]
        assert control["meta"]["loader"] == "csv"
        assert control["submissions"][-1]["valid"] is False
        assert "c02" in control["submissions"][-1]["error"]

        chosen = _walk("loader-chosen", [*args, "--loader", "healthy-cells"],
                       body=TRUE_BODY)

        # 1. the choice is bound to the run, so every later verb reads it back
        assert chosen["meta"]["loader"] == "healthy-cells"
        assert chosen["init"]["loader"] == "healthy-cells"
        # 2. the excluded cell really was excluded: it is not a unit at all
        assert chosen["init"]["score_keys"] == ["c01", "c03"]
        # 3. and that is what saves the law the strict fit had thrown out
        winner = chosen["submissions"][-1]
        assert winner["valid"] is True
        assert sorted(winner["params_per_group"]) == ["c01", "c03"]
        for name in ("c01", "c03"):
            np.testing.assert_allclose(
                winner["params_per_group"][name], CELLS[name], atol=1e-6
            )
        assert sorted(chosen["best"]["value_per_group"]) == ["c01", "c03"]

    def test_a_registered_optimizer_is_selectable_at_init(self):
        Path(".wheeler/llmsr").mkdir(parents=True)
        Path(".wheeler/llmsr/optimizers.py").write_text(
            "from scipy import optimize as opt\n"
            "from wheeler.integrations.llmsr.optimizers import (\n"
            "    Optimizer, register_optimizer)\n"
            "def _cg(loss, x0):\n"
            "    res = opt.minimize(loss, x0, method='CG')\n"
            "    return (res.x, float(res.fun))\n"
            "register_optimizer(Optimizer(key='cg', label='conjugate gradient',\n"
            "    minimize=_cg))\n"
        )
        data = _write_grouped_csv()
        Path("spec.txt").write_text(_spec("    return 0.0\n"))

        walk = _walk("reg-optimizer", [
            "--spec", "spec.txt", "--data", data, "--metric", "mse",
            "--optimizer", "cg",
        ], body=TRUE_BODY)

        assert walk["meta"]["optimizer"] == "cg"
        assert walk["best"]["optimizer"]["requested"] == "cg"
        # the CONCRETE optimizer behind the number, not just the request
        assert walk["best"]["optimizer"]["used"] == "cg"

    @pytest.mark.parametrize("flag,value", [
        ("--loader", "no-such-loader"),
        ("--metric", "no-such-metric"),
        ("--optimizer", "no-such-optimizer"),
    ])
    def test_an_unknown_choice_fails_at_init_not_at_every_candidate(self, flag, value):
        """One failed command beats a run whose every candidate is invalid.

        A name nothing can resolve is caught where the run is BOUND. Deferring it
        would surface as a search that rejects everything, which reads as "no law
        was found" rather than as "you named something that does not exist".
        """
        data = _write_grouped_csv()
        Path("spec.txt").write_text(_spec("    return 0.0\n"))

        res = runner.invoke(llmsr_app, [
            "init", "--spec", "spec.txt", "--data", data, "--metric", "mse",
            "--run-id", "bad", flag, value,
        ])

        assert res.exit_code != 0
        assert value in res.output
        assert not (Path(".wheeler/llmsr/runs") / "bad" / "meta.json").exists()


# ===========================================================================
# 2. Every emitted METRIC label is checked against the same run's best.json
# ===========================================================================

def _emitted_metric(program: str) -> dict:
    """The ``METRIC`` dict the written .py publishes.

    Parsed with ``ast.literal_eval`` rather than pattern-matched, so this asserts
    on the value a reader of the file would actually get.
    """
    for line in program.splitlines():
        if line.startswith("METRIC = "):
            return ast.literal_eval(line[len("METRIC = "):])
    raise AssertionError("the emitted program published no METRIC")


def _per_unit_values(best: dict) -> dict[str, float]:
    """Every per-unit number the run recorded, whichever shape it is in."""
    per_group = best.get("value_per_group") or {}
    if per_group:
        return {str(k): float(v) for k, v in per_group.items()}
    out: dict[str, float] = {}
    for entry in (best.get("datasets") or {}).get("entries", []):
        if entry.get("regime") == "scored":
            out.update({str(k): float(v) for k, v in (entry.get("value_per_key") or {}).items()})
    return out


def assert_metric_label_is_earned(best: dict) -> None:
    """The rule: the .py's METRIC name is the name of what produced its value.

    Three checks, and the audit's two HIGH numbers fail one each:

    1. the NAME is the run's scored metric, which is the declared metric only
       when the declared metric is what scored it;
    2. wherever ``best.json`` records a number under that same name, the .py's
       number IS it (this is what caught ``METRIC = {'name': 'nmse', 'value':
       1.7185}`` sitting beside ``"nmse_train": 0.0790``);
    3. wherever the run has a per-unit table, the .py's number is its mean, which
       is what ``fit.py`` aggregates to.
    """
    emitted = _emitted_metric(best["program"])
    scored = (best.get("scored_metric") or {}).get("name") or best["metric"]

    assert emitted["name"] == scored, (
        f"the emitted .py publishes its number as {emitted['name']!r}, but this "
        f"run's numbers are in {scored!r}"
    )

    train_key = f"{scored}_train"
    if train_key in (best.get("metrics") or {}):
        assert emitted["value"] == pytest.approx(best["metrics"][train_key]), (
            f"the .py says {scored} = {emitted['value']!r} and the same run's "
            f"best.json says {scored} = {best['metrics'][train_key]!r}"
        )

    per_unit = _per_unit_values(best)
    if per_unit:
        assert emitted["value"] == pytest.approx(
            sum(per_unit.values()) / len(per_unit)
        )

    # Through the spec door the number is the SPEC'S objective, so it must not
    # wear the declared metric's name, and the declared metric must still be
    # visible: a reader has to be able to tell which is which.
    if (best.get("optimizer") or {}).get("scored_by") == SCORED_BY_SPEC_EVALUATE:
        assert emitted["name"] != best["metric"]
        assert emitted["declared_metric"] == best["metric"]
    else:
        assert "declared_metric" not in emitted


class TestEmittedMetricLabelMatchesBestJson:
    """The .py is the durable half of a discovery: its label outlives the run.

    One case per shape ``selection._runnable_program`` can emit, because the
    label is written by four different footers and the audit found the bug in
    all of them at once.
    """

    def _grouped_project(self, evaluate_body: str) -> str:
        Path("spec.txt").write_text(_spec(evaluate_body))
        return _write_grouped_csv()

    def test_flat_default_door(self):
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        data = _write_grouped_csv()
        walk = _walk("label-flat", [
            "--spec", "spec.txt", "--data", data, "--metric", "nmse",
        ], body=TRUE_BODY)
        assert _emitted_metric(walk["best"]["program"])["name"] == "nmse"
        assert_metric_label_is_earned(walk["best"])

    def test_grouped_default_door(self):
        data = self._grouped_project("    return 0.0\n")
        walk = _walk("label-grouped", [
            "--spec", "spec.txt", "--data", data, "--metric", "nmse",
            "--group-by", "cell",
        ], body=TRUE_BODY)
        assert _emitted_metric(walk["best"]["program"])["name"] == "nmse"
        assert_metric_label_is_earned(walk["best"])

    def test_flat_spec_door_publishes_the_spec_s_own_objective(self):
        """The reproduction, minimized: an MSE-minimizing spec under --metric nmse.

        Before the fix this .py said ``{'name': 'nmse', 'value': <an MSE>}`` while
        the same run's ``best.json`` recorded ``nmse_train`` as a number an order
        of magnitude away. Both were called nmse; only one was.
        """
        data = self._grouped_project(_MSE_EVALUATE)
        walk = _walk("label-flat-spec", [
            "--spec", "spec.txt", "--data", data, "--metric", "nmse",
            "--use-spec-evaluate",
        ])
        best = walk["best"]
        emitted = _emitted_metric(best["program"])

        assert emitted["name"] == "spec:evaluate"
        assert emitted["declared_metric"] == "nmse"
        # the two quantities really are different numbers, which is the whole
        # reason they may not share a name
        assert emitted["value"] != pytest.approx(best["metrics"]["nmse_train"])
        assert emitted["value"] == pytest.approx(best["metrics"]["mse_train"])
        assert_metric_label_is_earned(best)

    def test_grouped_spec_door(self):
        data = self._grouped_project(_MSE_EVALUATE)
        walk = _walk("label-grouped-spec", [
            "--spec", "spec.txt", "--data", data, "--metric", "nmse",
            "--group-by", "cell", "--use-spec-evaluate",
        ])
        assert _emitted_metric(walk["best"]["program"])["name"] == "spec:evaluate"
        assert_metric_label_is_earned(walk["best"])

    def test_no_constants_spec_door(self):
        """Upstream's bare float: no constants to write, and still a label to earn."""
        data = self._grouped_project(_BARE_FLOAT_EVALUATE)
        walk = _walk("label-bare-spec", [
            "--spec", "spec.txt", "--data", data, "--metric", "nmse",
            "--group-by", "cell", "--use-spec-evaluate",
        ])
        assert "FITTED_PARAMS = None" in walk["best"]["program"]
        assert walk["best"]["params_per_group"] == {}
        assert_metric_label_is_earned(walk["best"])

    def test_multi_dataset_default_door(self):
        """The fourth footer, reached through the reusable multi-dataset walk."""
        from tests.integrations.llmsr.test_multidata import SPEC, TRUE_BODY as MD_BODY
        from tests.integrations.llmsr.test_multidata import _write_table, walk_case

        project = Path.cwd()
        (project / "spec.txt").write_text(SPEC)
        _write_table(project / "a.csv", 2.0, 0.5, seed=0)
        _write_table(project / "b.csv", -1.5, 3.0, seed=1)

        walk = walk_case(project, "label-multi", [
            "--data", f"A={project / 'a.csv'}", "--data", f"B={project / 'b.csv'}",
        ], body=MD_BODY)

        assert _emitted_metric(walk["best"]["program"])["name"] == "mse"
        assert_metric_label_is_earned(walk["best"])

    def test_the_run_report_and_the_py_never_disagree_about_the_scored_metric(self):
        """One run, three surfaces, one answer: best.json, the .py, and `status`."""
        data = self._grouped_project(_MSE_EVALUATE)
        walk = _walk("label-agree", [
            "--spec", "spec.txt", "--data", data, "--metric", "nmse",
            "--group-by", "cell", "--use-spec-evaluate",
        ])
        best = walk["best"]
        status = _out(runner.invoke(
            llmsr_app, ["status", "--run", str(walk["run_dir"])]
        ))

        name = best["scored_metric"]["name"]
        assert _emitted_metric(best["program"])["name"] == name
        assert status["best_value_metric"] == name
        assert status["best_value"] == pytest.approx(
            _emitted_metric(best["program"])["value"]
        )
        # and the declared metric is still reported as the declared metric
        assert best["metric"] == status["metric"] == "nmse"
        assert best["scored_metric"]["declared"] == "nmse"


class TestTheIslandModelIsConfigurableFromInit:
    """The experience buffer's own settings, reachable and bound to the run.

    Same rule as rule 1 above, applied to something that is not a registry. The
    buffer was constructed from `config_lib.Config().experience_buffer` with no
    override path at all, so upstream's `num_islands=10` and
    `reset_period=4*60*60` were the only configuration any run could ever have.

    That is not cosmetic. Island reset (kill the weakest half, reseed from the
    survivors) IS the diversity mechanism, and it fires on a four-hour timer: a
    run shorter than that gets none of it. Measured on the pilot's round 1, 25
    submissions over 10 islands left 1 to 8 programs per island, median 2 to 3,
    so most islands had no population to evolve either. Twenty-five
    near-independent samples were being reported as an evolutionary search, and
    there was no flag with which to fix it.
    """

    def test_both_knobs_are_on_the_init_command(self):
        names = _init_option_names()
        assert "--islands" in names
        assert "--reset-period" in names

    def test_they_are_bound_to_the_run_not_to_a_later_command_line(self):
        """Recorded in meta.json, because the buffer is REPLAYED every verb.

        A config read from a later command line would silently reassign islands
        and rebuild a different search state from identical submissions.
        """
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        data = _write_grouped_csv()
        walk = _walk("islands-bound", [
            "--spec", "spec.txt", "--data", data, "--metric", "mse",
            "--islands", "3", "--reset-period", "300",
        ], body=TRUE_BODY)
        assert walk["meta"]["islands"] == 3
        assert walk["meta"]["reset_period"] == 300

    def test_the_island_count_really_constrains_the_buffer(self):
        """Behavioural, not structural: the vendored buffer picks islands at
        random over `num_islands`, so asking for 2 must make id 2 impossible."""
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        data = _write_grouped_csv()
        run_id = "islands-effective"
        _out(runner.invoke(llmsr_app, [
            "init", "--run-id", run_id, "--spec", "spec.txt", "--data", data,
            "--metric", "mse", "--islands", "2",
        ]))
        run_dir = Path(".wheeler/llmsr/runs") / run_id
        seen = set()
        for _ in range(12):
            got = _out(runner.invoke(llmsr_app, ["prompt", "--run", str(run_dir)]))
            seen.add(got["island_id"])
        assert seen, "prompt never reported an island"
        assert max(seen) <= 1, f"asked for 2 islands, buffer offered {sorted(seen)}"

    def test_a_run_without_the_keys_gets_upstreams_defaults(self):
        """Backward compatibility is load-bearing here: every run dir on disk
        predates these keys, and a changed island count would invalidate its
        replayed buffer state without raising anything."""
        from wheeler.integrations.llmsr import cli as cli_mod
        from wheeler.integrations.llmsr.vendor import config as config_lib

        upstream = config_lib.Config().experience_buffer
        for meta in ({}, {"islands": None, "reset_period": None}):
            cfg = cli_mod._buffer_config(meta)
            assert cfg.num_islands == upstream.num_islands
            assert cfg.reset_period == upstream.reset_period

        tuned = cli_mod._buffer_config({"islands": 3, "reset_period": 300})
        assert (tuned.num_islands, tuned.reset_period) == (3, 300)
        # And the vendored default object is not mutated in the process.
        assert config_lib.Config().experience_buffer.num_islands == upstream.num_islands


class TestIslandResetActuallyFires:
    """The diversity half of the search, which was unreachable by construction.

    Upstream runs as one long-lived process: the buffer stamps
    `_last_reset_time = time.time()` at construction and resets the weakest half
    of the islands once `reset_period` of WALL CLOCK has passed. Wheeler inverted
    that loop into CLI verbs, so the buffer is rebuilt on every call and the timer
    restarts from zero each time, while a replay finishes in milliseconds.

    Measured before the fix: `reset_period` forced to 1 second, 26 submissions
    replayed, `reset_islands()` called ZERO times. Not a mis-tuned default. The
    mechanism could not fire at any setting, so every run this CLI ever made had
    islands that only accumulated and never competed.

    Wall clock is the wrong clock here even once it works. Upstream's sampler
    emits thousands of candidates an hour, so four hours is thousands of samples;
    a stepped loop emits one per model call. Replaying 26 submissions that spanned
    48 real minutes fired 48 resets at a 60-second period and 2905 at one second,
    collapsing every island to a single program. Hence `--reset-every`, counted in
    accepted submissions, which is what this class mostly pins.
    """

    def _run(self, run_id: str, extra: list[str], n: int) -> tuple[Path, dict]:
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        data = _write_grouped_csv()
        _out(runner.invoke(llmsr_app, [
            "init", "--run-id", run_id, "--spec", "spec.txt",
            "--data", data, "--metric", "mse", *extra,
        ]))
        run_dir = Path(".wheeler/llmsr/runs") / run_id
        body = Path(f"{run_id}_b.py")
        body.write_text(TRUE_BODY)
        for i in range(n):
            _out(runner.invoke(llmsr_app, [
                "submit", "--run", str(run_dir), "--body-file", str(body),
                "--island-id", str(i % 2), "--version-generated", "0",
            ]))
        return run_dir, json.loads((run_dir / "meta.json").read_text())

    def _replay_resets(self, run_dir: Path, meta: dict) -> int:
        from wheeler.integrations.llmsr import cli as cli_mod
        from wheeler.integrations.llmsr.vendor import buffer as buffer_mod

        calls = {"n": 0}
        original = buffer_mod.ExperienceBuffer.reset_islands

        def spy(self, *a, **k):
            calls["n"] += 1
            return original(self, *a, **k)

        buffer_mod.ExperienceBuffer.reset_islands = spy
        try:
            cli_mod._rebuild_buffer(run_dir, meta)
        finally:
            buffer_mod.ExperienceBuffer.reset_islands = original
        return calls["n"]

    def test_reset_every_fires_on_submission_count(self):
        run_dir, meta = self._run(
            "reset-count", ["--islands", "2", "--reset-every", "3"], n=9)
        from wheeler.integrations.llmsr.runs import _read_submissions

        accepted = sum(1 for s in _read_submissions(run_dir) if s.get("valid"))
        assert accepted >= 3, "need enough accepted submissions to cross a boundary"
        assert self._replay_resets(run_dir, meta) == accepted // 3

    def test_upstreams_wall_clock_default_still_never_fires_on_a_short_run(self):
        """Not a bug to fix: a run lasting seconds SHOULD see no four-hourly
        reset. Pinned so the default stays backward compatible for every run dir
        already on disk."""
        run_dir, meta = self._run("reset-default", ["--islands", "2"], n=4)
        assert meta.get("reset_every") in (None, 0)
        assert self._replay_resets(run_dir, meta) == 0

    def test_the_replay_is_deterministic_across_calls(self):
        """reset_islands picks its founder island at random, and the buffer is
        replayed on EVERY verb. Unseeded, `prompt` and `submit` would rebuild
        different search states from identical submissions."""
        from wheeler.integrations.llmsr import cli as cli_mod

        run_dir, meta = self._run(
            "reset-determinism", ["--islands", "3", "--reset-every", "2"], n=6)

        def shape():
            _, db, _ = cli_mod._rebuild_buffer(run_dir, meta)
            return [
                sum(len(c._programs) for c in isl._clusters.values())
                for isl in db._islands
            ]

        assert shape() == shape()

    def test_changing_the_island_count_mid_run_is_refused_clearly(self):
        """The count is baked into the recorded island ids, which index a list, so
        a stale id raises IndexError several frames inside vendored code, where it
        reads as a corrupt run rather than an edited setting."""
        from wheeler.integrations.llmsr import cli as cli_mod

        run_dir, meta = self._run("reset-idguard", ["--islands", "3"], n=4)
        with pytest.raises(Exception) as exc:
            cli_mod._rebuild_buffer(run_dir, {**meta, "islands": 1})
        assert "island" in str(exc.value).lower()


class TestClusterToleranceIsAWheelerDeviation:
    """Score quantization for clustering: OFF by default, and not the paper's.

    LLM-SR clusters on the raw continuous score. `_get_signature` returns
    `tuple(scores_per_test[k] for k in sorted(...))` with `Signature =
    Tuple[float, ...]`, and the paper describes programs "clustered based on
    their signature (defined by their score)" over a continuous `s = -MSE`.
    Nothing upstream rounds or bins. So the default must stay raw, and these
    tests exist mostly to keep it that way.

    The accommodation is for budget. With continuous scores every candidate gets
    a unique signature and every cluster holds one program, so
    `Cluster.sample_program` never chooses and the length bias, upstream's only
    parsimony pressure, cannot act. That is true of the paper's runs too, and
    costs them little: at ~10,000 candidates over 10 islands (Appendix B: m=10,
    k=2, b=4, ~2,500 iterations) an island holds ~1,000 singleton clusters and
    the score-weighted softmax across them carries selection alone. At tens of
    candidates there is no such crowd.

    Measured on a real 26-submission run at 10 islands: raw gives 0 clusters with
    more than one program, tolerance 1.8x gives 3, tolerance 3.2x gives 4.
    """

    def test_the_default_is_raw_scores_exactly_as_upstream(self):
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        data = _write_grouped_csv()
        walk = _walk("cluster-default", [
            "--spec", "spec.txt", "--data", data, "--metric", "mse",
        ], body=TRUE_BODY)
        assert walk["meta"].get("cluster_tolerance") in (None, 0, 0.0)

    def test_the_flag_exists_and_is_bound_to_the_run(self):
        assert "--cluster-tolerance" in _init_option_names()
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        data = _write_grouped_csv()
        walk = _walk("cluster-bound", [
            "--spec", "spec.txt", "--data", data, "--metric", "mse",
            "--cluster-tolerance", "1.8",
        ], body=TRUE_BODY)
        assert walk["meta"]["cluster_tolerance"] == pytest.approx(1.8)

    def test_scores_snap_to_error_units_not_to_bucket_indices(self):
        """The vendored buffer derives BOTH the signature and the cluster's
        selection score from this one dict. Returning bucket integers would leave
        the score-weighted softmax operating on indices, whose spread over the
        0.1 temperature makes selection nearly deterministic."""
        from wheeler.integrations.llmsr.cli import _quantize_scores

        raw = {"a": -0.00249, "b": -0.00251, "c": -0.0363, "d": -0.402}
        out = _quantize_scores(raw, 1.8)
        # Same order of magnitude as the inputs, not small integers.
        for key, value in out.items():
            assert value < 0, key
            assert abs(value) < 10, f"{key} left error units: {value}"
        # Values within the tolerance collide; values far apart do not.
        assert out["a"] == out["b"]
        assert len({out["a"], out["c"], out["d"]}) == 3

    def test_zero_and_nonfinite_scores_survive_untouched(self):
        from wheeler.integrations.llmsr.cli import _quantize_scores

        out = _quantize_scores(
            {"z": 0.0, "n": float("nan"), "i": float("-inf"), "ok": -0.5}, 1.8)
        assert out["z"] == 0.0
        assert out["n"] != out["n"]
        assert out["i"] == float("-inf")
        assert out["ok"] < 0


class TestARegisteredOptimizerSurvivesAProcessBoundary:
    """A registered optimizer must work at SUBMIT, not merely validate at init.

    The existing registry test walks init -> submit -> best through `CliRunner`,
    all in ONE process. `init` calls `load_user_optimizers()` explicitly (via
    `_optimizer_for`), so the registry is already warm by the time submit
    resolves the name, and the walk passes.

    Across a process boundary it did not. `get_optimizer` checked
    `key not in OPTIMIZERS` before loading any userland module, while its own
    error message called `choices()` -> `available()` -> `load_user_optimizers()`.
    So the registry was populated as a side effect of BUILDING THE REJECTION and
    never before the lookup, producing a self-contradictory error that listed the
    optimizer it had just rejected. Measured on a real batch: 12 of 12 candidates
    lost to "unknown optimizer 'best-of-three'; valid choices: [... 'best-of-three'
    ...]" while `init` had accepted it minutes earlier.

    So this test spawns a real subprocess, which is the only way to start with a
    cold registry.
    """

    def test_submit_in_a_fresh_process_resolves_a_userland_optimizer(self, tmp_path):
        import subprocess
        import sys

        module = Path("my_optimizers.py").resolve()
        module.write_text(
            "from scipy.optimize import minimize\n"
            "from wheeler.integrations.llmsr.optimizers import (\n"
            "    Optimizer, register_optimizer)\n"
            "def _powellish(loss, x0):\n"
            "    res = minimize(loss, x0, method='Powell')\n"
            "    return res.x, float(res.fun)\n"
            "register_optimizer(Optimizer(key='userland-powell',\n"
            "                             label='userland', minimize=_powellish))\n"
        )
        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        data = _write_grouped_csv()

        env = dict(os.environ, WHEELER_LLMSR_OPTIMIZERS=str(module))
        run_id = "userland-crossprocess"
        init = subprocess.run(
            [sys.executable, "-m", "wheeler.tools.cli", "llmsr", "init",
             "--run-id", run_id, "--spec", "spec.txt", "--data", data,
             "--metric", "mse", "--optimizer", "userland-powell"],
            capture_output=True, text=True, env=env,
        )
        assert init.returncode == 0, init.stdout + init.stderr

        body = Path("crossproc_body.py")
        body.write_text(TRUE_BODY)
        run_dir = Path(".wheeler/llmsr/runs") / run_id
        submit = subprocess.run(
            [sys.executable, "-m", "wheeler.tools.cli", "llmsr", "submit",
             "--run", str(run_dir), "--body-file", str(body),
             "--island-id", "0", "--version-generated", "0"],
            capture_output=True, text=True, env=env,
        )
        assert submit.returncode == 0, submit.stdout + submit.stderr
        payload = json.loads(submit.stdout.strip().splitlines()[-1])
        assert payload["valid"] is True, payload
        assert "unknown optimizer" not in (payload.get("error") or "")

    def test_the_rejection_message_can_never_contradict_itself(self):
        """Whatever `choices()` offers, `get_optimizer` must accept. The two used
        to disagree because only one of them loaded userland sources."""
        optimizers_mod.load_user_optimizers()
        for key in optimizers_mod.choices():
            if key == optimizers_mod.AUTO:
                optimizers_mod.resolve(key)
            else:
                optimizers_mod.get_optimizer(key)


class TestWallClockResetMatchesUpstreamExactly:
    """Replaying with recorded timestamps must not fire MORE resets than upstream.

    The first version of the timestamp replay caught up with a `while` loop,
    firing one reset per elapsed period. Upstream fires at most ONE per
    registration and re-anchors `_last_reset_time` to `time.time()` rather than to
    last + period (vendor/buffer.py:177-180), so a long idle gap costs one reset,
    not a backlog. Measured against upstream's own code driven by a patched clock:
    at the default 14400s period with one 14h pause, the loop produced 3 resets
    where upstream produced 1, wiping populations upstream would have kept.

    A stepped loop idles for hours by construction, so the divergence was on the
    normal path and at the default period, not in a corner.
    """

    def _run(self, gaps: list[float], period: int) -> tuple[int, int]:
        from unittest import mock

        from wheeler.integrations.llmsr import cli as cli_mod
        from wheeler.integrations.llmsr.runs import (
            _read_submissions, _scores_per_test)
        from wheeler.integrations.llmsr.vendor import buffer as buffer_mod
        from wheeler.integrations.llmsr.vendor import code_manipulation, evaluator

        Path("spec.txt").write_text(_spec("    return 0.0\n"))
        data = _write_grouped_csv()
        run_id = f"resetclock{abs(hash(tuple(gaps))) % 10000}"
        _out(runner.invoke(llmsr_app, [
            "init", "--run-id", run_id, "--spec", "spec.txt",
            "--data", data, "--metric", "mse", "--islands", "4",
        ]))
        run_dir = Path(".wheeler/llmsr/runs") / run_id
        body = Path(f"{run_id}_b.py")
        body.write_text(TRUE_BODY)
        for i in range(6):
            _out(runner.invoke(llmsr_app, [
                "submit", "--run", str(run_dir), "--body-file", str(body),
                "--island-id", str(i % 2), "--version-generated", "0",
            ]))

        log = run_dir / "submissions.jsonl"
        subs = [json.loads(line)
                for line in log.read_text().strip().splitlines()]
        t = 1_000_000.0
        for i, s in enumerate(subs):
            if i:
                t += gaps[(i - 1) % len(gaps)]
            s["at_epoch"] = t
        log.write_text("\n".join(json.dumps(s) for s in subs) + "\n")

        meta = {**json.loads((run_dir / "meta.json").read_text()),
                "reset_period": period, "reset_every": 0}
        counts = {}
        original = buffer_mod.ExperienceBuffer.reset_islands

        def spy(self, *a, **k):
            counts["n"] = counts.get("n", 0) + 1
            return original(self, *a, **k)

        # Wheeler's replay.
        counts.clear()
        buffer_mod.ExperienceBuffer.reset_islands = spy
        try:
            cli_mod._rebuild_buffer(run_dir, meta)
        finally:
            buffer_mod.ExperienceBuffer.reset_islands = original
        wheeler = counts.get("n", 0)

        # Upstream's own branch, driven by a clock set to each at_epoch.
        template = code_manipulation.text_to_program(
            Path(meta["spec_path"]).read_text())
        fte = meta["function_to_evolve"]
        valid = [s for s in _read_submissions(run_dir) if s.get("valid")]
        clock = {"t": valid[0]["at_epoch"]}
        counts.clear()
        with mock.patch.object(buffer_mod, "time") as fake:
            fake.time = lambda: clock["t"]
            buffer_mod.ExperienceBuffer.reset_islands = spy
            try:
                db = buffer_mod.ExperienceBuffer(
                    cli_mod._buffer_config(meta), template, fte)
                for s in valid:
                    clock["t"] = s["at_epoch"]
                    fn, _ = evaluator._sample_to_program(
                        s["body"], s.get("version_generated"), template, fte)
                    db.register_program(
                        fn, s.get("island_id"), _scores_per_test(s))
            finally:
                buffer_mod.ExperienceBuffer.reset_islands = original
        return counts.get("n", 0), wheeler

    @pytest.mark.parametrize("gaps,label", [
        ([60, 60, 14 * 3600, 60, 60], "one long pause"),
        ([60, 13 * 3600, 60, 60, 13 * 3600], "two long pauses"),
        ([90], "a normal steady run"),
        ([5 * 3600], "steadily longer than the period"),
    ])
    def test_reset_count_equals_upstreams(self, gaps, label):
        upstream, wheeler = self._run(gaps, period=14400)
        assert wheeler == upstream, (
            f"{label}: upstream fired {upstream} resets, Wheeler fired {wheeler}")
