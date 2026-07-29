"""The loader registry: how a recording becomes the groups the search fits.

Three claims under test. (1) The built-in ``csv`` loader IS today's convention,
not a lookalike: its output is asserted equal to calling ``data.py`` directly.
(2) The registry is open the same way the metric registry is, through the one
shared ``$WHEELER_LLMSR_*`` convention. (3) A loader can EXCLUDE a bad group, and
that is what saves a correct law from the strict per-group validity rule.

No live model and no Neo4j: everything runs against a scratch project.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import _userland
from wheeler.integrations.llmsr import data as data_mod
from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr import loaders as loaders_mod
from wheeler.integrations.llmsr import metrics as metrics_mod
from wheeler.integrations.llmsr.cli import llmsr_app

runner = CliRunner()

# One law, y = a*x1 + b*x2, three cells with DIFFERENT constants. The whole point
# of grouping: the FORM is shared, theta is not.
CELLS = {"c01": (2.5, -1.0), "c02": (-4.0, 8.0), "c03": (0.5, 3.0)}

LINEAR = (
    "import numpy as np\n"
    "def equation(x1, x2, params):\n"
    "    return params[0] * x1 + params[1] * x2\n"
)


def _write_grouped_csv(path: str = "train.csv", n: int = 25, dead_cell: str = "") -> str:
    """Write a grouped training table. ``dead_cell`` names a cell with no target.

    An empty target cell reads back as NaN, which is what a dropped channel or an
    aborted trial looks like once it reaches the table.
    """
    rng = np.random.default_rng(7)
    lines = ["x1,x2,cell,y"]
    for name, (a, b) in CELLS.items():
        for _ in range(n):
            x1, x2 = (float(v) for v in rng.uniform(-3.0, 3.0, 2))
            y = "" if name == dead_cell else f"{a * x1 + b * x2:.17g}"
            lines.append(f"{x1:.17g},{x2:.17g},{name},{y}")
    Path(path).write_text("\n".join(lines) + "\n")
    return path


def _write_flat_csv(path: str = "flat.csv") -> str:
    """Ungrouped, three inputs and a target: the plain tabular convention."""
    Path(path).write_text(
        "a,b,c,target\n"
        "1.0,2.0,3.0,6.0\n"
        "2.0,3.0,4.0,9.0\n"
        "3.0,4.0,5.0,12.0\n"
    )
    return path


def _assert_same_groups(got: list[loaders_mod.Group], want: list[tuple]) -> None:
    """The loader's groups ARE the tuples ``data.py`` produces, in the same order."""
    assert [g.name for g in got] == [label for label, _x, _y in want]
    for group, (_label, want_x, want_y) in zip(got, want):
        np.testing.assert_array_equal(group.X, want_x)
        if isinstance(want_y, np.ndarray):
            np.testing.assert_array_equal(np.asarray(group.y), want_y)
        else:
            assert group.y == want_y


class TestCsvLoaderIsTodaysConvention:
    """The built-in loader must be the existing rules, preserved by construction."""

    def test_ungrouped_output_is_identical_to_the_data_module(self):
        path = _write_flat_csv()
        want = data_mod._as_groups(*data_mod._load_data(path, metrics_mod.MSE, ""))

        got = loaders_mod.load_groups(path, metrics_mod.MSE)

        _assert_same_groups(got, want)
        assert [g.name for g in got] == [fit_mod.UNGROUPED]

    def test_grouped_output_is_identical_to_the_data_module(self):
        path = _write_grouped_csv()
        want = data_mod._as_groups(*data_mod._load_data(path, metrics_mod.MSE, "cell"))

        got = loaders_mod.load_groups(path, metrics_mod.MSE, group_by="cell")

        _assert_same_groups(got, want)
        assert [g.name for g in got] == sorted(CELLS)

    def test_cols_name_the_x_columns_in_order(self):
        path = _write_grouped_csv()

        got = loaders_mod.load_groups(path, metrics_mod.MSE, group_by="cell")

        # The group column identifies the row, it is not an input, and the last
        # column is the target: both are excluded, exactly as X is.
        assert all(g.cols == ("x1", "x2") for g in got)
        assert all(g.X.shape[1] == len(g.cols) for g in got)

    def test_ungrouped_cols_are_every_column_but_the_target(self):
        got = loaders_mod.load_groups(_write_flat_csv(), metrics_mod.MSE)
        assert got[0].cols == ("a", "b", "c")

    def test_a_non_regression_shape_passes_its_target_through_untouched(self):
        """The metric declares the target's shape; the loader does not reinterpret it."""
        Path("spikes.csv").write_text("stim,events\n0.0,0.2\n1.0,0.35\n2.0,\n3.0,\n")
        spike = metrics_mod.Metric(
            key="spike_stub", label="stub", data_shape=metrics_mod.SPIKE_TRAIN,
            lower_is_better=True, loss=lambda p, t: 0.0, report=lambda p, t: 0.0,
        )

        got = loaders_mod.load_groups("spikes.csv", spike)

        assert len(got) == 1
        assert got[0].y == [0.2, 0.35]  # padded, shorter than the stimulus

    def test_a_bad_group_by_still_fails_the_way_it_always_did(self):
        path = _write_grouped_csv()
        with pytest.raises(Exception, match="not a column"):
            loaders_mod.load_groups(path, metrics_mod.MSE, group_by="nope")

    def test_meta_records_where_the_group_came_from(self):
        got = loaders_mod.load_groups(_write_grouped_csv(), metrics_mod.MSE, group_by="cell")
        assert got[0].meta["loader"] == "csv"
        assert got[0].meta["group_by"] == "cell"


class TestExclusion:
    """The reason the registry exists: per-group validity is STRICT.

    ``fit.evaluate_body_grouped`` accepts a candidate only if EVERY group fitted.
    So one dead cell rejects a correct law, and there is nowhere else to say
    "that cell is not admissible" without editing the installed package.
    """

    def _fit(self, groups: list[loaders_mod.Group]) -> fit_mod.FitResult:
        return fit_mod.evaluate_body_grouped(
            LINEAR, "equation",
            [(g.name, g.X, g.y) for g in groups],
            metrics_mod.MSE,
            max_nparams=2,
        )

    def test_one_dead_cell_rejects_the_correct_form(self):
        """The control: the form is EXACTLY right and the candidate is still invalid."""
        path = _write_grouped_csv(dead_cell="c02")

        groups = loaders_mod.load_groups(path, metrics_mod.MSE, group_by="cell")

        assert [g.name for g in groups] == sorted(CELLS)
        result = self._fit(groups)
        assert result.valid is False
        assert "c02" in result.error
        # The other two cells fitted perfectly. Strict validity throws the
        # candidate out anyway, which is exactly the problem a loader solves.
        assert sorted(result.per_group_value) == ["c01", "c03"]
        assert max(result.per_group_value.values()) < 1e-12

    def test_a_loader_that_excludes_the_dead_cell_recovers_the_law(self):
        path = _write_grouped_csv(dead_cell="c02")

        def healthy_only(request: loaders_mod.LoadRequest) -> list[loaders_mod.Group]:
            kept = []
            for group in loaders_mod.get_loader("csv").load(request):
                y = np.asarray(group.y, dtype=float)
                if np.isfinite(y).all():
                    kept.append(group)
                else:
                    # An excluded group is excluded, but not silently.
                    request.options.setdefault("excluded", []).append(group.name)
            return kept

        loaders_mod.register_loader(loaders_mod.Loader(
            key="healthy-cells", label="CSV, excluding cells with missing targets",
            load=healthy_only,
        ))
        excluded: list[str] = []

        groups = loaders_mod.load_groups(
            path, metrics_mod.MSE, group_by="cell",
            loader="healthy-cells", options={"excluded": excluded},
        )

        assert [g.name for g in groups] == ["c01", "c03"]
        assert excluded == ["c02"]
        result = self._fit(groups)
        assert result.valid is True
        # The same FORM, each surviving cell refitting its own constants.
        for name in ("c01", "c03"):
            a, b = CELLS[name]
            np.testing.assert_allclose(result.params_per_group[name], [a, b], atol=1e-6)

    def test_a_loader_that_excludes_everything_is_an_error_not_an_empty_fit(self):
        loaders_mod.register_loader(loaders_mod.Loader(
            key="nothing", label="excludes everything", load=lambda request: [],
        ))
        with pytest.raises(ValueError, match="no groups"):
            loaders_mod.load_groups(_write_flat_csv(), metrics_mod.MSE, loader="nothing")


_QC_LOADER_SOURCE = '''
import numpy as np

from wheeler.integrations.llmsr.loaders import Loader, get_loader, register_loader


def healthy_cells(request):
    groups = get_loader("csv").load(request)
    return [g for g in groups if np.isfinite(np.asarray(g.y, dtype=float)).all()]


register_loader(Loader(
    key="healthy-cells",
    label="CSV, excluding cells with missing targets",
    load=healthy_cells,
))
'''


class TestUserLoaderSources:
    """A loader from outside the installed package, found the standard way."""

    def test_project_file_loader_is_listed_and_usable(self):
        Path(".wheeler/llmsr").mkdir(parents=True)
        Path(".wheeler/llmsr/loaders.py").write_text(_QC_LOADER_SOURCE)

        res = runner.invoke(llmsr_app, ["loaders"])
        assert res.exit_code == 0, res.output
        listing = json.loads(res.output)
        by_key = {ldr["key"]: ldr for ldr in listing["loaders"]}
        assert by_key["healthy-cells"]["builtin"] is False
        assert by_key["csv"]["builtin"] is True
        assert listing["errors"] == []
        assert listing["sources"] == [str(Path(".wheeler/llmsr/loaders.py").resolve())]

        groups = loaders_mod.load_groups(
            _write_grouped_csv(dead_cell="c02"), metrics_mod.MSE,
            group_by="cell", loader="healthy-cells",
        )
        assert [g.name for g in groups] == ["c01", "c03"]

    def test_env_var_source_is_loaded(self, monkeypatch):
        path = Path("my_loaders.py").resolve()
        path.write_text(_QC_LOADER_SOURCE)
        monkeypatch.setenv(loaders_mod._USER_LOADERS_ENV, str(path))

        loaders_mod.load_user_loaders()

        assert "healthy-cells" in loaders_mod.available()
        assert loaders_mod.get_loader("healthy-cells").label.startswith("CSV")

    def test_broken_source_is_reported_not_raised(self):
        Path(".wheeler/llmsr").mkdir(parents=True)
        Path(".wheeler/llmsr/loaders.py").write_text("raise RuntimeError('boom')\n")

        failures = loaders_mod.load_user_loaders()

        assert len(failures) == 1
        assert "boom" in failures[0].error
        # The built-in survives a broken user file, so every verb still works.
        assert loaders_mod.get_loader("csv") is loaders_mod.CSV
        res = runner.invoke(llmsr_app, ["loaders"])
        assert res.exit_code == 0, res.output
        assert {ldr["key"] for ldr in json.loads(res.output)["loaders"]} == {"csv"}


class TestRegistration:
    def test_builtin_is_not_silently_shadowed(self):
        clone = loaders_mod.Loader(key="csv", label="not the real csv", load=lambda r: [])
        with pytest.raises(ValueError, match="built in"):
            loaders_mod.register_loader(clone)
        assert loaders_mod.get_loader("csv") is loaders_mod.CSV

        loaders_mod.register_loader(clone, replace=True)
        assert loaders_mod.get_loader("csv") is clone

    def test_uncallable_load_is_rejected_at_registration(self):
        broken = loaders_mod.Loader(key="broken", label="broken", load="not a function")
        with pytest.raises(TypeError, match="load"):
            loaders_mod.register_loader(broken)
        assert "broken" not in loaders_mod.available()

    def test_a_duck_typed_loader_is_rejected(self):
        class Duck:
            key = "duck"
            label = "quacks"

            def load(self, request):
                return []

        with pytest.raises(TypeError, match="loaders.Loader"):
            loaders_mod.register_loader(Duck())

    def test_unknown_loader_names_what_is_registered(self):
        with pytest.raises(KeyError, match="csv"):
            loaders_mod.get_loader("mat")

    def test_keys_are_normalized_the_way_metric_keys_are(self):
        assert loaders_mod.get_loader("  CSV ") is loaders_mod.CSV


class TestSharedUserlandConvention:
    """Metrics and loaders use ONE importer and ONE env-var convention."""

    def test_env_vars_and_project_files_follow_the_same_pattern(self):
        assert metrics_mod._USER_METRICS_ENV == "WHEELER_LLMSR_METRICS"
        assert loaders_mod._USER_LOADERS_ENV == "WHEELER_LLMSR_LOADERS"
        assert metrics_mod._PROJECT_METRICS_FILE == Path(".wheeler/llmsr/metrics.py")
        assert loaders_mod._PROJECT_LOADERS_FILE == Path(".wheeler/llmsr/loaders.py")

    def test_metrics_still_exposes_the_names_its_callers_use(self):
        """The extraction is a re-export, not a rename: old accessors still work."""
        assert metrics_mod.MetricSourceError is _userland.SourceError
        # The SAME set object, so a caller that mutates it in place (the test
        # fixture does) is mutating the one the importer consults.
        assert metrics_mod._loaded_sources is _userland._loaded_sources

    def test_one_file_named_by_two_registries_is_imported_once(self, monkeypatch):
        """The unit is 'this file has run', which is a property of the process."""
        both = Path("both.py").resolve()
        both.write_text(
            "from wheeler.integrations.llmsr.metrics import Metric, register_metric\n"
            "from wheeler.integrations.llmsr.loaders import Loader, register_loader\n"
            "register_metric(Metric(key='k', label='k', data_shape='regression',\n"
            "                       lower_is_better=True, loss=lambda p, t: 0.0,\n"
            "                       report=lambda p, t: 0.0))\n"
            "register_loader(Loader(key='k', label='k', load=lambda r: []))\n"
        )
        monkeypatch.setenv(metrics_mod._USER_METRICS_ENV, str(both))
        monkeypatch.setenv(loaders_mod._USER_LOADERS_ENV, str(both))

        assert metrics_mod.load_user_metrics() == []
        # Running the module twice would raise "already registered" out of the
        # second register_* call and be reported as a failure here.
        assert loaders_mod.load_user_loaders() == []

        assert "k" in metrics_mod.available()
        assert "k" in loaders_mod.available()
