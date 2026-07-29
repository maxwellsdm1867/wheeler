"""Multi-dataset runs: naming, roles, per-dataset refit, and the regime labels.

Upstream LLM-SR scores each candidate against MANY named inputs
(``vendor/evaluator.py`` loops ``self._inputs`` and builds ``scores_per_test``).
Wheeler had bound exactly one, which is why ``fit.UNGROUPED`` was a single
hardcoded key. These tests cover reopening that seam.

The scientific point they are protecting: **a candidate refits its own constants
on every dataset it is scored against**, so scoring a form on a table it was not
extracted from is a genuine test of the FORM rather than of one lucky
parameterization. That is fair precisely because the same law is assumed across
tables and only the constants differ, which is the same argument ``--group-by``
rests on, one level up.

Four things are checked, in order of how loudly they would fail:

1. **Backward compatibility.** An unnamed single ``--data`` is byte-for-byte what
   it was. Delegated to ``parity_singledata.py``, which compares against a golden
   captured from the pre-change code, so the claim is evidence and not assertion.
2. **The combination matrix.** Each ``--score-on`` shape scores the datasets it
   named AND NO OTHERS. ``SCORE_ON_MATRIX`` and ``walk_case`` below are the
   reusable surface for that (S6 reuses them); keep them importable.
3. **Per-dataset refit.** Each scored dataset really does get its OWN constants.
4. **Regime labels.** ``best.json`` says which tables the search optimized
   against, including the case where the seed dataset is neither.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import data as data_mod
from wheeler.integrations.llmsr import fit as fit_mod
from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.llmsr.discover import REGIME_HELD_OUT, REGIME_SCORED

runner = CliRunner()


# --------------------------------------------------------------- the fixtures

# One shared FORM, y = a*x + b*x**2, with a different (a, b) per table. That is
# exactly the situation multi-dataset scoring exists for: a single law whose
# constants vary, which a pooled fit would charge the form for.
CONSTANTS = {"a": (2.0, 0.5), "b": (-1.5, 3.0), "c": (0.75, -2.0)}

SPEC = '''"""toy"""
import numpy as np

MAX_NPARAMS = 3


@evaluate.run
def evaluate(data: dict) -> float:
    return 0.0


@equation.evolve
def equation(x: np.ndarray, params: np.ndarray) -> np.ndarray:
    return params[0]*x
'''

# The true form, so every scored table can reach its own constants exactly.
TRUE_BODY = "    return params[0]*x + params[1]*x**2\n"


def _write_table(path: Path, a: float, b: float, seed: int, cells: int = 0) -> None:
    """Write y = a*x + b*x**2, optionally split into ``cells`` labelled groups.

    ``float()`` before ``repr``: numpy 2 reprs a scalar as ``np.float64(1.0)``,
    which is not a CSV cell.
    """
    rng = np.random.default_rng(seed)
    if not cells:
        rows = ["x,y"]
        for xi in (float(v) for v in rng.uniform(-2.0, 2.0, 30)):
            rows.append(f"{xi!r},{float(a * xi + b * xi**2)!r}")
    else:
        rows = ["cell,x,y"]
        for c in range(cells):
            # Each cell scales the shared form differently, so a per-unit refit
            # is the only thing that can fit them all.
            scale = 1.0 + c
            for xi in (float(v) for v in rng.uniform(-2.0, 2.0, 20)):
                y = scale * a * xi + scale * b * xi**2
                rows.append(f"c{c:02d},{xi!r},{float(y)!r}")
    path.write_text("\n".join(rows) + "\n")


@pytest.fixture()
def project(tmp_path):
    """A scratch project with a spec, three tables, and a candidate body."""
    (tmp_path / "spec.txt").write_text(SPEC)
    for seed, (name, (a, b)) in enumerate(CONSTANTS.items()):
        _write_table(tmp_path / f"{name}.csv", a, b, seed=seed)
    (tmp_path / "body.py").write_text(TRUE_BODY)
    return tmp_path


# ------------------------------------------------------------- the CLI harness

def _out(result) -> dict:
    assert result.exit_code == 0, result.output + str(result.exception)
    return json.loads(result.output.strip().splitlines()[-1])


def _init(project: Path, run_id: str, *args: str) -> dict:
    return _out(runner.invoke(llmsr_app, [
        "init", "--spec", str(project / "spec.txt"),
        "--metric", "mse", "--run-id", run_id, *args,
    ]))


def walk_case(project: Path, run_id: str, args: list[str], body: str = TRUE_BODY) -> dict:
    """init -> submit one body -> best, and hand back everything it wrote.

    The reusable surface: ``{"init":..., "submit":..., "meta":..., "best":...,
    "submissions": [...]}``. A fixed island id keeps the walk reproducible (the
    vendored buffer picks one at random), which matters because these tests
    assert on the score KEYS a submission recorded.
    """
    init = _init(project, run_id, *args)
    run_dir = Path(".wheeler/llmsr/runs") / run_id
    body_file = project / f"{run_id}_body.py"
    body_file.write_text(body)
    submit = _out(runner.invoke(llmsr_app, [
        "submit", "--run", str(run_dir), "--body-file", str(body_file),
        "--island-id", "0", "--version-generated", "0",
    ]))
    _out(runner.invoke(llmsr_app, ["best", "--run", str(run_dir)]))
    return {
        "init": init,
        "submit": submit,
        "run_dir": run_dir,
        "meta": json.loads((run_dir / "meta.json").read_text()),
        "best": json.loads((run_dir / "best.json").read_text()),
        "submissions": [
            json.loads(line)
            for line in (run_dir / "submissions.jsonl").read_text().splitlines()
            if line.strip()
        ],
    }


def scored_keys(walked: dict) -> set[str]:
    """The score keys the LAST submission actually presented to the buffer.

    Read off the recorded per-group vector rather than off the declaration, so
    this reports what was scored and not what was asked for.
    """
    return set((walked["submissions"][-1].get("per_group") or {}))


def scored_datasets(walked: dict) -> set[str]:
    """Which DATASETS those keys belong to."""
    scheme = walked["meta"]["score_key_scheme"]
    if scheme == data_mod.SCHEME_GROUP:
        return {fit_mod.UNGROUPED}
    return {k.split(data_mod.KEY_SEP)[0] for k in scored_keys(walked)}


# The four shapes from the slice brief. Each entry is
# ``(id, cli args, expected scored datasets, expected seed dataset)``, and every
# one of them asserts BOTH halves: the datasets it named are scored and the ones
# it did not name are not. S6 reuses this table; keep it a plain data structure.
SCORE_ON_MATRIX = [
    pytest.param(
        ["--data", "A=a.csv"],
        {"A"}, "A",
        id="single-named-scores-itself",
    ),
    pytest.param(
        ["--data", "A=a.csv", "--data", "B=b.csv", "--score-on", "B"],
        {"B"}, "A",
        id="extract-from-A-score-on-B",
    ),
    pytest.param(
        ["--data", "A=a.csv", "--data", "B=b.csv", "--score-on", "A,B"],
        {"A", "B"}, "A",
        id="score-on-both",
    ),
    pytest.param(
        ["--data", "A=a.csv", "--data", "B=b.csv", "--data", "C=c.csv",
         "--seed-from", "A", "--score-on", "B,C"],
        {"B", "C"}, "A",
        id="seed-from-A-score-on-B-and-C",
    ),
]


# ------------------------------------------------------------ backward compat

class TestBackwardCompat:
    """An unnamed single ``--data`` is what it always was.

    Non-negotiable because the vendored buffer clusters candidates on the score
    signature: a changed key set would silently invalidate the buffer state of
    every run already on disk, without raising anything.
    """

    def test_byte_for_byte_against_the_pre_change_golden(self):
        from tests.integrations.llmsr import parity_singledata

        failures = parity_singledata.check_all()
        assert not failures, "\n".join(failures)

    def test_the_score_key_is_the_word_data(self, project, monkeypatch):
        monkeypatch.chdir(project)
        walked = walk_case(project, "compat", ["--data", "a.csv"])
        assert scored_keys(walked) == {fit_mod.UNGROUPED}
        assert walked["meta"]["score_key_scheme"] == data_mod.SCHEME_GROUP
        assert walked["meta"]["datasets"] == [
            {"name": fit_mod.UNGROUPED, "path": str(project / "a.csv")}
        ]
        # `data_path` still points at the table the constants were fitted on.
        assert walked["meta"]["data_path"] == str(project / "a.csv")

    def test_a_grouped_run_keeps_bare_group_labels(self, project, monkeypatch):
        monkeypatch.chdir(project)
        _write_table(project / "cells.csv", 2.0, 0.5, seed=9, cells=3)
        walked = walk_case(
            project, "compat-grouped", ["--data", "cells.csv", "--group-by", "cell"]
        )
        assert scored_keys(walked) == {"c00", "c01", "c02"}
        assert walked["meta"]["score_key_scheme"] == data_mod.SCHEME_GROUP

    def test_best_json_gains_no_dataset_block(self, project, monkeypatch):
        monkeypatch.chdir(project)
        walked = walk_case(project, "compat-best", ["--data", "a.csv"])
        assert "datasets" not in walked["best"]

    def test_a_run_dir_written_before_S2_still_replays(self, project, monkeypatch):
        """An older ``meta.json`` has ``data_path`` and no dataset names at all."""
        monkeypatch.chdir(project)
        walked = walk_case(project, "legacy", ["--data", "a.csv"])
        meta = dict(walked["meta"])
        for key in ("datasets", "seed_from", "score_on", "score_key_scheme"):
            meta.pop(key)
        (walked["run_dir"] / "meta.json").write_text(json.dumps(meta))

        assert data_mod.scheme_from_meta(meta) == data_mod.SCHEME_GROUP
        assert [d.name for d in data_mod.datasets_from_meta(meta)] == [fit_mod.UNGROUPED]
        # and the verbs still run against it
        out = _out(runner.invoke(llmsr_app, [
            "submit", "--run", str(walked["run_dir"]),
            "--body-file", str(project / "legacy_body.py"),
            "--island-id", "0", "--version-generated", "0",
        ]))
        assert out["valid"] is True
        subs = [
            json.loads(line)
            for line in (walked["run_dir"] / "submissions.jsonl").read_text().splitlines()
            if line.strip()
        ]
        assert set(subs[-1]["per_group"]) == {fit_mod.UNGROUPED}


# -------------------------------------------------------- the combination matrix

class TestScoreOnMatrix:
    """Each shape scores the datasets it named, and no others."""

    @pytest.mark.parametrize("args,expect_scored,expect_seed", SCORE_ON_MATRIX)
    def test_scores_what_it_named_and_nothing_else(
        self, project, monkeypatch, args, expect_scored, expect_seed
    ):
        monkeypatch.chdir(project)
        walked = walk_case(project, "matrix", args)
        declared = {d["name"] for d in walked["meta"]["datasets"]}

        assert scored_datasets(walked) == expect_scored
        assert set(walked["meta"]["score_on"]) == expect_scored
        assert walked["meta"]["seed_from"] == expect_seed
        # the other half of the claim: what was NOT named never reached the buffer
        assert (declared - expect_scored) & scored_datasets(walked) == set()

    @pytest.mark.parametrize("args,expect_scored,expect_seed", SCORE_ON_MATRIX)
    def test_the_declared_data_path_is_a_scored_table(
        self, project, monkeypatch, args, expect_scored, expect_seed
    ):
        """``data_path`` means "what the constants were fitted on", still.

        It feeds the held-out split scoring and the runnable footer, so pointing
        it at a table the run never trained on would label a held-out number
        ``train``.
        """
        monkeypatch.chdir(project)
        walked = walk_case(project, "matrix-path", args)
        by_name = {d["name"]: d["path"] for d in walked["meta"]["datasets"]}
        assert walked["meta"]["data_path"] in {by_name[n] for n in expect_scored}

    def test_score_on_accepts_a_repeated_flag_as_well_as_a_list(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        walked = walk_case(project, "repeat", [
            "--data", "A=a.csv", "--data", "B=b.csv", "--data", "C=c.csv",
            "--score-on", "B", "--score-on", "C",
        ])
        assert scored_datasets(walked) == {"B", "C"}

    def test_score_on_order_follows_declaration_not_the_command_line(
        self, project, monkeypatch
    ):
        """So the key set is a property of the run, not of how it was typed."""
        monkeypatch.chdir(project)
        walked = walk_case(project, "order", [
            "--data", "A=a.csv", "--data", "B=b.csv", "--score-on", "B,A",
        ])
        assert walked["meta"]["score_on"] == ["A", "B"]


# ------------------------------------------------------------ per-dataset refit

class TestPerDatasetRefit:
    """One FORM, one theta per dataset. The whole point of the slice."""

    def test_each_scored_dataset_recovers_its_own_constants(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        walked = walk_case(project, "refit", [
            "--data", "A=a.csv", "--data", "B=b.csv", "--data", "C=c.csv",
            "--score-on", "A,B,C",
        ])
        table = walked["submissions"][-1]["params_per_group"]
        assert set(table) == {"A", "B", "C"}
        for name, (a, b) in zip("ABC", CONSTANTS.values()):
            assert table[name][0] == pytest.approx(a, abs=1e-6)
            assert table[name][1] == pytest.approx(b, abs=1e-6)
        # and they are genuinely different vectors, not one fit copied out
        assert len({tuple(round(v, 6) for v in p) for p in table.values()}) == 3

    def test_the_flat_params_vector_is_empty_for_a_multi_unit_run(
        self, project, monkeypatch
    ):
        """Same construction as a grouped run: there IS no single vector.

        Anything reading ``params`` alone on such a run records nothing, which is
        the honest failure. The table is in ``best.json["datasets"]``.
        """
        monkeypatch.chdir(project)
        walked = walk_case(project, "flat", [
            "--data", "A=a.csv", "--data", "B=b.csv", "--score-on", "A,B",
        ])
        assert walked["best"]["params"] == []
        entries = {e["name"]: e for e in walked["best"]["datasets"]["entries"]}
        assert entries["A"]["params_per_key"]["A"]
        assert entries["B"]["params_per_key"]["B"]

    def test_datasets_and_groups_compose_into_one_unit_per_pair(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        _write_table(project / "p.csv", 2.0, 0.5, seed=21, cells=2)
        _write_table(project / "q.csv", -1.5, 3.0, seed=22, cells=2)
        walked = walk_case(project, "cross", [
            "--data", "P=p.csv", "--data", "Q=q.csv", "--group-by", "cell",
        ])
        assert scored_keys(walked) == {"P:c00", "P:c01", "Q:c00", "Q:c01"}
        # every unit refit its own constants, and no two are the same
        table = walked["submissions"][-1]["params_per_group"]
        assert len({tuple(round(v, 6) for v in p) for p in table.values()}) == 4

    def test_the_progress_ping_names_the_dataset_under_the_needle(
        self, project, monkeypatch
    ):
        """S0b left ``dataset`` hardcoded for S2 to fill in. This is that."""
        monkeypatch.chdir(project)
        walked = walk_case(project, "ping", [
            "--data", "A=a.csv", "--data", "B=b.csv", "--score-on", "A,B",
        ])
        ping = json.loads((walked["run_dir"] / "progress.json").read_text())
        # the last unit fitted is the last scored dataset, in declaration order
        assert ping["dataset"] == "B"
        assert ping["done"] == ping["total"] == 2


# --------------------------------------------------------------- regime labels

class TestRegimeLabels:
    """``best.json`` says which tables the search optimized against.

    Forty rounds scored on a table makes that table's error a training number
    however good it looks. A split that scores the search is not a holdout, and
    the artifact must never let one be read as the other.
    """

    def test_scored_and_held_out_are_labelled_apart(self, project, monkeypatch):
        monkeypatch.chdir(project)
        walked = walk_case(project, "regime", [
            "--data", "A=a.csv", "--data", "B=b.csv", "--data", "C=c.csv",
            "--seed-from", "A", "--score-on", "B,C",
        ])
        block = walked["best"]["datasets"]
        assert block["seed_from"] == "A"
        assert block["score_on"] == ["B", "C"]
        assert block["score_key_scheme"] == data_mod.SCHEME_DATASET

        entries = {e["name"]: e for e in block["entries"]}
        assert set(entries) == {"A", "B", "C"}
        # A seeded the prompt and was never scored: held out, and flagged as the
        # seed so a reader knows the generator did see it.
        assert entries["A"]["regime"] == REGIME_HELD_OUT
        assert entries["A"]["seed"] is True
        assert "shaped the prompt only" in entries["A"]["regime_reason"]
        assert entries["A"]["value"] is None
        for name in ("B", "C"):
            assert entries[name]["regime"] == REGIME_SCORED
            assert entries[name]["seed"] is False
            assert entries[name]["value"] is not None
            assert entries[name]["keys"] == [name]

    def test_a_declared_but_unscored_table_is_held_out_without_being_the_seed(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        walked = walk_case(project, "regime-2", [
            "--data", "A=a.csv", "--data", "B=b.csv", "--data", "C=c.csv",
            "--seed-from", "A", "--score-on", "A,B",
        ])
        entries = {e["name"]: e for e in walked["best"]["datasets"]["entries"]}
        assert entries["A"]["regime"] == REGIME_SCORED  # seeded AND scored
        assert entries["C"]["regime"] == REGIME_HELD_OUT
        assert entries["C"]["seed"] is False
        assert "shaped the prompt" not in entries["C"]["regime_reason"]

    def test_a_grouped_multi_dataset_entry_reports_its_whole_key_set(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        _write_table(project / "p.csv", 2.0, 0.5, seed=31, cells=2)
        _write_table(project / "q.csv", -1.5, 3.0, seed=32, cells=2)
        walked = walk_case(project, "regime-grouped", [
            "--data", "P=p.csv", "--data", "Q=q.csv", "--group-by", "cell",
        ])
        entries = {e["name"]: e for e in walked["best"]["datasets"]["entries"]}
        assert entries["P"]["keys"] == ["P:c00", "P:c01"]
        # the dataset's reported value is the mean over its own units
        assert entries["P"]["value"] == pytest.approx(
            sum(entries["P"]["value_per_key"].values()) / 2
        )

    def test_a_failed_run_still_says_what_it_would_have_scored(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        (project / "spec.txt").write_text(SPEC)
        init = _init(project, "fail", "--data", "A=a.csv", "--data", "B=b.csv")
        assert init["seed_valid"] is True
        run_dir = Path(".wheeler/llmsr/runs/fail")
        # Drop every valid candidate, so `best` takes the failure branch.
        (run_dir / "submissions.jsonl").write_text("")
        res = runner.invoke(llmsr_app, ["best", "--run", str(run_dir)])
        assert res.exit_code == 1
        best = json.loads((run_dir / "best.json").read_text())
        assert best["status"] == "failed"
        block = best["datasets"]
        assert [e["name"] for e in block["entries"]] == ["A", "B"]
        assert all(e["value"] is None for e in block["entries"])


# ------------------------------------------------------------- naming and roles

class TestDatasetNaming:
    def test_a_named_single_dataset_qualifies_its_keys(self, project, monkeypatch):
        monkeypatch.chdir(project)
        walked = walk_case(project, "named", ["--data", "A=a.csv"])
        assert scored_keys(walked) == {"A"}
        assert walked["meta"]["score_key_scheme"] == data_mod.SCHEME_DATASET

    def test_an_unnamed_dataset_among_several_takes_its_file_stem(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        walked = walk_case(project, "stems", ["--data", "a.csv", "--data", "b.csv"])
        assert {d["name"] for d in walked["meta"]["datasets"]} == {"a", "b"}

    def test_seed_from_defaults_to_the_first_data(self, project, monkeypatch):
        monkeypatch.chdir(project)
        walked = walk_case(project, "seed-default", [
            "--data", "B=b.csv", "--data", "A=a.csv",
        ])
        assert walked["meta"]["seed_from"] == "B"

    def test_prompt_reports_the_dataset_the_form_should_come_from(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        _init(project, "prompt-roles",
              "--data", "A=a.csv", "--data", "B=b.csv",
              "--seed-from", "A", "--score-on", "B")
        p = _out(runner.invoke(
            llmsr_app, ["prompt", "--run", ".wheeler/llmsr/runs/prompt-roles"]
        ))
        assert p["seed_from"] == {"name": "A", "path": str(project / "a.csv")}
        assert p["score_on"] == ["B"]

    @pytest.mark.parametrize("args,fragment", [
        (["--data", "A=a.csv", "--data", "A=b.csv"], "declared twice"),
        (["--data", "A=a.csv", "--data", "B=nope.csv"], "no readable file"),
        (["--data", "A=a.csv", "--score-on", "Z"], "not a declared dataset"),
        (["--data", "A=a.csv", "--seed-from", "Z"], "not a declared dataset"),
        (["--data", "A:1=a.csv"], "is not usable"),
        (["--data", "a.csv", "--data", "sub/a.csv"], "declared twice"),
    ])
    def test_a_declaration_that_could_collide_is_refused_at_init(
        self, project, monkeypatch, args, fragment
    ):
        monkeypatch.chdir(project)
        (project / "sub").mkdir(exist_ok=True)
        _write_table(project / "sub" / "a.csv", 1.0, 1.0, seed=99)
        res = runner.invoke(llmsr_app, [
            "init", "--spec", str(project / "spec.txt"), "--metric", "mse",
            "--run-id", "bad", *args,
        ])
        assert res.exit_code != 0
        assert fragment in res.output

    def test_a_path_containing_an_equals_sign_is_still_a_path(
        self, project, monkeypatch
    ):
        monkeypatch.chdir(project)
        odd = project / "runs=2024"
        odd.mkdir()
        _write_table(odd / "rec.csv", 2.0, 0.5, seed=41)
        walked = walk_case(project, "eqpath", ["--data", f"{odd}/rec.csv"])
        assert walked["meta"]["datasets"][0]["path"] == str(odd / "rec.csv")
        assert walked["meta"]["datasets"][0]["name"] == fit_mod.UNGROUPED


# ------------------------------------------------------------------- the units

class TestUnitAssembly:
    """``data.load_units`` composes with the loader registry rather than around it."""

    def test_it_goes_through_the_registered_loader(self, project, monkeypatch):
        monkeypatch.chdir(project)
        seen = []

        from wheeler.integrations.llmsr import loaders as loaders_mod

        original = loaders_mod.get_loader("csv")

        def spy(request):
            seen.append(request.path)
            return original.load(request)

        loaders_mod.register_loader(
            loaders_mod.Loader(key="csv", label="spy", load=spy), replace=True
        )
        walk_case(project, "loader", ["--data", "A=a.csv", "--data", "B=b.csv"])
        assert [Path(p).name for p in seen[:2]] == ["a.csv", "b.csv"]

    def test_a_loader_returning_a_duplicate_name_is_refused(self, project):
        """Two units under one key would be averaged into one by the buffer.

        Names are checked unique and the built-in loader returns sorted-unique
        groups, so this is only reachable through a scientist's own loader. It is
        checked because the failure it prevents is silent.
        """
        from wheeler.integrations.llmsr import loaders as loaders_mod
        from wheeler.integrations.llmsr import metrics as metrics_mod

        csv = loaders_mod.get_loader("csv")

        def twice(request):
            groups = csv.load(request)
            return list(groups) + list(groups)

        loaders_mod.register_loader(
            loaders_mod.Loader(key="doubling", label="doubling", load=twice)
        )
        with pytest.raises(Exception, match="same score key"):
            data_mod.load_units(
                [data_mod.DatasetSpec("A", str(project / "a.csv"))],
                metrics_mod.get_metric("mse"),
                scheme=data_mod.SCHEME_DATASET,
                loader="doubling",
            )

    def test_the_key_scheme_is_a_pure_function_of_the_scored_set(self):
        default = data_mod.DatasetSpec(fit_mod.UNGROUPED, "/x.csv")
        named = data_mod.DatasetSpec("A", "/x.csv")
        assert data_mod.key_scheme([default]) == data_mod.SCHEME_GROUP
        assert data_mod.key_scheme([named]) == data_mod.SCHEME_DATASET
        assert data_mod.key_scheme([default, named]) == data_mod.SCHEME_DATASET

    def test_keys_read_back_apart_without_ambiguity(self):
        keys = ["A", "A:c01", "AB", "AB:c01", "B:c01"]
        assert data_mod.keys_for("A", keys, data_mod.SCHEME_DATASET) == ["A", "A:c01"]
        assert data_mod.keys_for("AB", keys, data_mod.SCHEME_DATASET) == ["AB", "AB:c01"]
