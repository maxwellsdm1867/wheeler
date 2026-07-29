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
