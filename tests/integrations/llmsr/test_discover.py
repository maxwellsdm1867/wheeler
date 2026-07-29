"""Tests for the LLM-SR equation-discovery marshal-out adapter.

Three layers:
  1. parse_discover: a real captured best.json fixture plus shape-drift /
     garbage tolerance (never raises), and the REGIME labelling that keeps a
     search-optimized number from reading as a generalization claim.
  2. live-Neo4j e2e: ingest the fixture, assert the winner subgraph (Script +
     Finding + Document, BOTH provenance sides), then re-ingest and assert
     idempotency. Skipped automatically when Neo4j is unreachable.
  3. live-Neo4j e2e for a GROUPED run, driven from a real search: the Script must
     carry the per-group constant table, and the .py it points at must RUN.

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
    REGIME_HELD_OUT,
    REGIME_SCORED,
    REGIME_UNKNOWN,
    RunMeta,
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
# 2. Live-Neo4j e2e (per-run e2e_tag, hermetic teardown)
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

    def _grouped_best_json(self) -> dict:
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
            "    return 0.0\n\n"
            "@equation.evolve\n"
            "def equation(x1, params):\n"
            "    return params[0] * x1 + params[1]\n"
        )
        for argv in (
            ["init", "--spec", "spec.txt", "--data", "train.csv",
             "--metric", "mse", "--group-by", "cell_id", "--run-id", "e2egrouped"],
            ["best", "--run", "e2egrouped"],
        ):
            out = subprocess.run(
                [sys.executable, "-m", "wheeler.tools.cli", "llmsr", *argv],
                cwd=self._tmp, capture_output=True, text=True, env=_subprocess_env(),
            )
            assert out.returncode == 0, out.stderr or out.stdout
        best = json.loads(
            (self._tmp / ".wheeler/llmsr/runs/e2egrouped/best.json").read_text()
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
