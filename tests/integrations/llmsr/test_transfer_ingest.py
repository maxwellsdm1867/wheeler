"""Tests for the LLM-SR transfer marshal-out adapter.

Three layers:
  1. ``parse_transfer``: the two claims come back as TWO records with different
     regimes and different Finding ids, the vocabulary is the one ``discover.py``
     already speaks, and a shape-drifted or garbage artifact never raises.
  2. the CLI wiring: ``wheeler integrate ingest transfer`` and
     ``record-failure transfer`` both know the tool.
  3. live-Neo4j e2e driven from a REAL run: search on cell A, ingest the
     discovery, transfer the winning form onto held-out cells B and C, ingest
     that, and assert the graph carries TWO Findings in the right regimes with
     distinct ids, an Execution with BOTH provenance sides wired, and the raw
     report registered. Plus a FAILED transfer (failed Execution, zero Findings)
     and idempotency. Skipped automatically when Neo4j is unreachable.

The scientific claim under test is the one issue #107 exists for: three cells
share ``y = a*x + b`` with DIFFERENT ``(a, b)``. Refitting recovers each held-out
cell's own constants (the FORM transfers); cell A's constants applied unchanged
score far worse (the CONSTANTS do not). Both numbers must reach the graph,
labelled, and neither may stand in for the other.

Run: python -m pytest tests/integrations/llmsr/test_transfer_ingest.py -q
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from wheeler.integrations.llmsr import transfer as transfer_mod
from wheeler.integrations.llmsr.cli import llmsr_app
from wheeler.integrations.llmsr.discover import (
    CLAIM_CONSTANTS,
    CLAIM_FORM,
    MEASURED_BY_FIT,
    REGIME_HELD_OUT,
    REGIME_HELD_OUT_FORM,
    REGIME_SCORED,
    REGIME_UNKNOWN,
    _SECOND_OPINION_NOTE,
    _finding_id,
)
from wheeler.integrations.llmsr.transfer_ingest import (
    TransferMeta,
    _transfer_key,
    parse_transfer,
)

runner = CliRunner()

SERVICE_TAG = "llmsr:transfer"
DISCOVER_TAG = "llmsr:discover"

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
    x, y = _rows(cell, n, seed)
    lines = ["x1,y"] + [f"{float(xi):.17g},{float(yi):.17g}" for xi, yi in zip(x, y)]
    path.write_text("\n".join(lines) + "\n")


def _write_grouped(path: Path, cells: list[str], n: int = 40, seed: int = 7) -> None:
    lines = ["cell_id,x1,y"]
    for i, cell in enumerate(cells):
        x, y = _rows(cell, n, seed + i)
        lines += [
            f"{cell},{float(xi):.17g},{float(yi):.17g}" for xi, yi in zip(x, y)
        ]
    path.write_text("\n".join(lines) + "\n")


def _completed(**extra) -> dict:
    """A minimal completed transfer.json, so a test states only what it is about."""
    doc = {
        "status": "completed",
        "run_id": "r1",
        "metric": "mse",
        "data_path": "/data/cellsBC.csv",
        "source_data_path": "/data/cellA.csv",
        "group_by": "cell_id",
        "groups": ["c02", "c03"],
        "candidate": {
            "sample_order": 2,
            "selected_by": "fit",
            "equation": "    return params[0] * x1 + params[1]",
            "complexity": 7,
        },
        "refit": {
            "claim": "form",
            "label": "the FORM transfers: ...",
            "valid": True,
            "value": 2.6e-16,
            "value_per_group": {"c02": 1.0e-16, "c03": 4.2e-16},
            "params_per_group": {"c02": [-4.0, 8.0], "c03": [0.5, 3.0]},
            "optimizer": "bfgs",
            "optimizer_per_group": {},
            "regime": REGIME_HELD_OUT_FORM,
            "regime_reason": (
                "the search neither fitted constants nor selected the winner on "
                "this data, but the constants WERE refitted on it, so this "
                "number is held out for the FORM only, never for the constants"
            ),
            "error": "",
        },
        "fixed_theta": {
            "claim": "constants",
            "label": "the CONSTANTS transfer: ...",
            "value": 134.35,
            "value_per_group": {"c02": 210.0, "c03": 58.7},
            "params_per_group": {"c02": [2.5, -1.0], "c03": [2.5, -1.0]},
            "source_per_group": {
                "c02": "the source has a single constant vector",
                "c03": "the source has a single constant vector",
            },
            "regime": REGIME_HELD_OUT,
            "regime_reason": (
                "the search neither fitted constants nor selected the winner on "
                "this data"
            ),
            "error": "",
        },
        "comparison": {
            "metric": "mse",
            "refit_value": 2.6e-16,
            "fixed_theta_value": 134.35,
            "refit_over_fixed": 1.9e-18,
            "note": "the two answer different questions: ...",
        },
        "optimizer": {"requested": "auto", "used": "bfgs", "restarts": 1, "seed": 0},
        "written": "2026-07-29T00:00:00+00:00",
    }
    doc.update(extra)
    return doc


def _by_claim(doc: dict) -> dict[str, dict]:
    records, _meta = parse_transfer(doc)
    return {record["claim"]: record for record in records}


# ---------------------------------------------------------------------------
# 1. Defensive parse + the labelling that keeps the two claims apart
# ---------------------------------------------------------------------------


class TestParseTransfer:
    def test_non_dict_is_empty(self):
        records, meta = parse_transfer("not a dict")
        assert records == []
        assert isinstance(meta, TransferMeta)

    def test_empty_doc_is_empty_but_keyed(self):
        records, meta = parse_transfer({})
        assert records == []
        # Still keyed, so the failsafe can record a failed Execution for it.
        assert meta.session_id
        assert meta.split_token.startswith("transfer:")

    def test_failed_status_yields_no_records(self):
        """A failed transfer fabricates nothing, even when a block has numbers."""
        doc = _completed(status="failed")
        doc["refit"]["valid"] = False
        doc["refit"]["value"] = None
        records, meta = parse_transfer(doc)
        assert records == []
        assert meta.run_id == "r1"

    def test_garbage_blocks_are_skipped_not_fatal(self):
        doc = _completed(refit="not a dict")
        records, _meta = parse_transfer(doc)
        assert [r["claim"] for r in records] == [CLAIM_CONSTANTS]

    def test_both_blocks_missing_yields_no_records(self):
        doc = _completed()
        doc.pop("refit")
        doc.pop("fixed_theta")
        assert parse_transfer(doc)[0] == []

    def test_two_claims_come_back_as_two_records(self):
        by_claim = _by_claim(_completed())
        assert set(by_claim) == {CLAIM_FORM, CLAIM_CONSTANTS}
        assert by_claim[CLAIM_FORM]["value"] == pytest.approx(2.6e-16)
        assert by_claim[CLAIM_CONSTANTS]["value"] == pytest.approx(134.35)

    def test_the_two_regimes_are_different_and_the_refit_is_not_plain_held_out(self):
        """The scientific core: a refit is held out for the FORM only."""
        by_claim = _by_claim(_completed())
        assert by_claim[CLAIM_FORM]["regime"] == REGIME_HELD_OUT_FORM
        assert by_claim[CLAIM_FORM]["regime"] != REGIME_HELD_OUT
        assert by_claim[CLAIM_CONSTANTS]["regime"] == REGIME_HELD_OUT
        assert "FORM only" in by_claim[CLAIM_FORM]["regime_reason"]

    def test_a_refit_labelled_plain_held_out_is_repaired(self):
        """Drift tolerance: `held_out` on a refit claims the constants transferred."""
        doc = _completed()
        doc["refit"]["regime"] = REGIME_HELD_OUT
        doc["refit"]["regime_reason"] = "the search never touched this data"
        assert _by_claim(doc)[CLAIM_FORM]["regime"] == REGIME_HELD_OUT_FORM

    def test_a_scored_table_stays_scored_on_both_claims(self):
        """Refitting on data the search optimized against is still not a holdout."""
        doc = _completed()
        for block in ("refit", "fixed_theta"):
            doc[block]["regime"] = REGIME_SCORED
            doc[block]["regime_reason"] = "this is the run's own training data"
        by_claim = _by_claim(doc)
        assert by_claim[CLAIM_FORM]["regime"] == REGIME_SCORED
        assert by_claim[CLAIM_CONSTANTS]["regime"] == REGIME_SCORED

    def test_an_unknown_regime_is_not_coerced_into_the_flattering_answer(self):
        doc = _completed()
        doc["fixed_theta"]["regime"] = "definitely_generalizes"
        entry = _by_claim(doc)[CLAIM_CONSTANTS]
        assert entry["regime"] == REGIME_UNKNOWN
        assert "definitely_generalizes" in entry["regime_reason"]

    def test_both_numbers_ride_on_both_records(self):
        """A reader who lands on one must be shown the other, labelled."""
        for record in _by_claim(_completed()).values():
            assert record["refit_value"] == pytest.approx(2.6e-16)
            assert record["fixed_theta_value"] == pytest.approx(134.35)
            assert record["refit_over_fixed"] == pytest.approx(1.9e-18)
            assert "different questions" in record["comparison_note"]

    def test_a_withheld_fixed_theta_still_parses(self):
        doc = _completed()
        doc["fixed_theta"]["value"] = None
        doc["fixed_theta"]["error"] = "no fixed-theta aggregate: c03 produced none"
        doc["comparison"].pop("refit_over_fixed")
        doc["comparison"]["fixed_theta_value"] = None
        entry = _by_claim(doc)[CLAIM_CONSTANTS]
        assert entry["value"] is None
        assert "c03" in entry["error"]
        assert entry["refit_over_fixed"] is None

    def test_default_door_carries_no_measurement_note(self):
        for record in _by_claim(_completed()).values():
            assert record["measured_by"] == MEASURED_BY_FIT
            assert record["measurement_note"] == ""

    def test_spec_door_numbers_are_a_second_opinion(self):
        """These numbers came from `fit.py`, not from what scored the search."""
        doc = _completed(scored_metric={
            "name": "spec:evaluate", "declared": "mse",
            "measured_by": "spec-evaluate", "note": "...",
        })
        records, meta = parse_transfer(doc)
        assert meta.scored_metric == "spec:evaluate"
        for record in records:
            # measured HERE by the fit seam, whatever scored the search
            assert record["measured_by"] == MEASURED_BY_FIT
            assert record["measurement_note"] == _SECOND_OPINION_NOTE


class TestIdentity:
    """One transfer is (run, table, candidate). Two of them are two measurements."""

    def test_the_two_findings_of_one_transfer_have_distinct_ids(self):
        _records, meta = parse_transfer(_completed())
        refit_id = _finding_id(meta.run_id, meta.metric, meta.split_token, CLAIM_FORM)
        fixed_id = _finding_id(
            meta.run_id, meta.metric, meta.split_token, CLAIM_CONSTANTS
        )
        assert refit_id != fixed_id

    def test_a_transfer_finding_never_collides_with_a_discovery_finding(self):
        _records, meta = parse_transfer(_completed())
        discovery_ids = {
            _finding_id(meta.run_id, meta.metric, split, claim)
            for split in ("train", "test_id", "test_ood", "")
            for claim in (CLAIM_CONSTANTS, CLAIM_FORM)
        }
        for claim in (CLAIM_CONSTANTS, CLAIM_FORM):
            assert (
                _finding_id(meta.run_id, meta.metric, meta.split_token, claim)
                not in discovery_ids
            )

    def test_a_different_table_is_a_different_transfer(self):
        _r, a = parse_transfer(_completed())
        _r, b = parse_transfer(_completed(data_path="/data/cellD.csv"))
        assert a.session_id != b.session_id
        assert a.split_token != b.split_token

    def test_a_different_candidate_is_a_different_transfer(self):
        """Transferring two candidates onto one table is two measurements."""
        doc = _completed()
        doc["candidate"] = dict(doc["candidate"], sample_order=9)
        _r, a = parse_transfer(_completed())
        _r, b = parse_transfer(doc)
        assert a.session_id != b.session_id

    def test_the_same_artifact_always_keys_the_same(self):
        _r, a = parse_transfer(_completed())
        _r, b = parse_transfer(_completed())
        assert a.session_id == b.session_id
        assert a.split_token == b.split_token

    def test_the_key_does_not_depend_on_the_ingesting_cwd(self, tmp_path, monkeypatch):
        """A relative recorded path must not be re-resolved against this process."""
        before = _transfer_key("r1", "cellsBC.csv", 2)
        sub = tmp_path / "elsewhere"
        sub.mkdir()
        monkeypatch.chdir(sub)
        assert _transfer_key("r1", "cellsBC.csv", 2) == before

    def test_the_session_id_names_the_run_and_the_table(self):
        _records, meta = parse_transfer(_completed())
        assert meta.session_id.startswith("r1:cellsBC:")


class TestCliWiring:
    def test_the_ingest_verb_knows_the_transfer_tool(self):
        from wheeler.integrations.asta.cli import _FAILURE_META, _INGESTERS

        assert "transfer" in _INGESTERS
        assert _FAILURE_META["transfer"] == ("equation-transfer", SERVICE_TAG)

    def test_the_registry_carries_the_transfer_contract(self):
        from wheeler.integrations.invocation import input_ports
        from wheeler.integrations.registry import catalog_services

        contract = next(c for c in catalog_services() if c.id == "llmsr-transfer")
        assert contract.act == "/wh:llmsr-transfer"
        ports = {p.name for p in input_ports(contract)}
        assert {"run", "dataset", "group_by", "select", "candidate"} <= ports

    def test_the_dataset_port_is_single_valued(self):
        """`transfer --data` takes ONE table, unlike `init --data`."""
        from wheeler.integrations.invocation import input_ports
        from wheeler.integrations.registry import catalog_services

        contract = next(c for c in catalog_services() if c.id == "llmsr-transfer")
        port = next(p for p in input_ports(contract) if p.name == "dataset")
        assert port.multi is False
        assert port.required is True


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


def _cleanup_transfer(e2e_config, e2e_tag: str) -> None:
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


class _TransferE2E:
    """Drive a REAL search, a REAL transfer, ingest both, tear down by tag only.

    Driven from the CLI rather than a fixture because the numbers are the claim:
    a hand-written doc would carry whatever the author assumed, and what makes
    this test worth running is that the refit really does recover each held-out
    cell's own constants while the source constants really do not.
    """

    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{uuid.uuid4().hex}"
        _cleanup_transfer(e2e_config, self._e2e_tag)
        yield
        _cleanup_transfer(e2e_config, self._e2e_tag)

    async def _tag_run(self, e2e_config, report):
        """Tag ONLY the nodes THIS run touched: the report ids, the
        WAS_GENERATED_BY fan-in (Finding, Document) and the USED fan-out (the
        input Datasets and the source Script). NEVER by service.

        The USED side is narrowed, because an Execution's inputs are the one edge
        that can reach a node the test did not create, and teardown deletes
        whatever it tags.

        The narrowing accepts either spelling of "under this test's tree". The
        tmp-dir prefix alone was silently correct only while stored paths were
        absolute: a file under this tmp dir is now stored as
        `${PROJECT}/cellA.csv`, matching no tmp prefix, so the guard excluded the
        very Datasets it existed to catch and they outlived every teardown. This
        test's project root IS its tmp dir, so a portable-path node reachable
        from this run's freshly created Execution was created by this run.
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
                    "   OR n.path STARTS WITH '${PROJECT}/' "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                    under=str(self._tmp),
                )

    def _cli(self, *argv: str) -> dict:
        result = runner.invoke(llmsr_app, list(argv))
        assert result.exit_code == 0, result.output
        return json.loads(result.output.strip().splitlines()[-1])

    def _search_on_cell_a(self, run_id: str) -> Path:
        """init (seed = the true form) plus one submit of a decoy that fits worse."""
        spec = self._tmp / "spec.txt"
        spec.write_text(SPEC)
        train = self._tmp / "cellA.csv"
        _write_ungrouped(train, "c01")

        self._cli(
            "init", "--spec", str(spec), "--data", str(train),
            "--metric", "mse", "--run-id", run_id,
        )
        rd = Path(".wheeler/llmsr/runs") / run_id
        p = self._cli("prompt", "--run", str(rd))
        decoy = self._tmp / "decoy.py"
        decoy.write_text("    return params[0] * x1**3 + params[1]")
        self._cli(
            "submit", "--run", str(rd), "--body-file", str(decoy),
            "--island-id", str(p["island_id"]),
            "--version-generated", str(p["version_generated"]),
        )
        return rd

    async def _ingest_discovery(self, e2e_config, rd: Path) -> None:
        """Ingest the DISCOVERY first, so the discovered Script is on disk.

        The transfer's ``USED`` edge to that Script is what makes the chain back
        to the discovery a real edge, and it only exists once the discovery has
        been ingested.
        """
        from wheeler.integrations.llmsr.discover import ingest_discover

        self._cli("best", "--run", str(rd))
        best = json.loads((rd / "best.json").read_text())
        path = self._tmp / "best.json"
        path.write_text(json.dumps(best))
        report = await ingest_discover(
            best, config=e2e_config, artifact_path=str(path)
        )
        await self._tag_run(e2e_config, report)
        assert report.failed is False

    def _transfer(self, rd: Path, data: Path, *extra: str) -> tuple[dict, object]:
        result = runner.invoke(llmsr_app, [
            "transfer", "--run", str(rd), "--data", str(data), *extra,
        ])
        return json.loads((rd / transfer_mod.TRANSFER_FILE).read_text()), result

    async def _ingest_transfer(self, e2e_config, payload: dict, name: str):
        from wheeler.integrations.llmsr.transfer_ingest import ingest_transfer

        path = self._tmp / name
        path.write_text(json.dumps(payload))
        report = await ingest_transfer(
            payload, config=e2e_config, artifact_path=str(path)
        )
        await self._tag_run(e2e_config, report)
        return report

    async def _findings(self, e2e_config, exec_id: str) -> dict[str, dict]:
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            r = await s.run(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN n.id AS id, n.title AS title, n.description AS description, "
                "n.custom_claim AS claim, n.custom_regime AS regime, "
                "n.custom_value AS value, n.custom_metric AS metric, "
                "n.custom_measured_by AS measured_by, "
                "n.custom_refit_value AS refit_value, "
                "n.custom_fixed_theta_value AS fixed_theta_value, "
                "n.custom_refit_over_fixed AS refit_over_fixed, "
                "n.custom_params_per_group AS params_per_group, "
                "n.custom_value_per_group AS value_per_group, "
                "n.custom_n_groups AS n_groups, "
                "n.custom_transfer_data AS transfer_data, "
                "n.custom_source_data AS source_data",
                x=exec_id,
            )
            return {rec["claim"]: dict(rec) async for rec in r}


class TestTransferIngestE2E(_TransferE2E):
    @pytest.mark.asyncio
    async def test_both_numbers_land_as_two_labelled_findings(self, e2e_config):
        """The gate for the whole slice: the FORM answer and the CONSTANTS answer
        both reach the graph, in different regimes, as different nodes."""
        rd = self._search_on_cell_a("txfr")
        await self._ingest_discovery(e2e_config, rd)

        held_out = self._tmp / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])
        payload, result = self._transfer(rd, held_out, "--group-by", "cell_id")
        assert result.exit_code == 0, result.output
        assert payload["status"] == "completed"

        report = await self._ingest_transfer(e2e_config, payload, "transfer.json")
        assert report.failed is False
        assert report.execution_id

        found = await self._findings(e2e_config, report.execution_id)
        assert set(found) == {CLAIM_FORM, CLAIM_CONSTANTS}
        refit, fixed = found[CLAIM_FORM], found[CLAIM_CONSTANTS]

        # Two nodes, never one.
        assert refit["id"] != fixed["id"]
        assert refit["title"] == "mse_transfer_cellsBC_refit"
        assert fixed["title"] == "mse_transfer_cellsBC"

        # The regimes are the scientific core and they are NOT the same label.
        assert refit["regime"] == REGIME_HELD_OUT_FORM
        assert fixed["regime"] == REGIME_HELD_OUT
        assert "FORM only" in refit["description"]
        assert "whether the FORM transfers" in refit["description"]
        assert "whether the CONSTANTS transfer" in fixed["description"]
        # Each description names the OTHER number, so a reader who saw only one
        # node cannot take it for the answer to both questions.
        assert "The fixed-theta number on the same data is" in refit["description"]
        assert "The refit number on the same data is" in fixed["description"]

        # The FORM transfers (refit recovers each cell), the CONSTANTS do not.
        assert refit["value"] == pytest.approx(0.0, abs=1e-10)
        assert fixed["value"] > 1.0
        per_group = json.loads(refit["params_per_group"])
        for cell in ("c02", "c03"):
            a, b = CELLS[cell]
            assert per_group[cell][0] == pytest.approx(a, abs=1e-6)
            assert per_group[cell][1] == pytest.approx(b, abs=1e-6)
        assert refit["n_groups"] == 2
        assert json.loads(refit["value_per_group"]).keys() == {"c02", "c03"}

        # BOTH numbers ride on BOTH nodes, so neither reads as the answer to both.
        for entry in (refit, fixed):
            assert entry["refit_value"] == pytest.approx(refit["value"])
            assert entry["fixed_theta_value"] == pytest.approx(fixed["value"])
            assert entry["metric"] == "mse"
            assert entry["measured_by"] == MEASURED_BY_FIT
            assert entry["transfer_data"].endswith("cellsBC.csv")
            assert entry["source_data"].endswith("cellA.csv")

    @pytest.mark.asyncio
    async def test_both_provenance_sides_are_wired(self, e2e_config):
        """USED the table, the source Script and the source table;
        WAS_GENERATED_BY the two Findings and the raw report."""
        from wheeler.graph.driver import get_async_driver

        rd = self._search_on_cell_a("prov")
        await self._ingest_discovery(e2e_config, rd)
        held_out = self._tmp / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])
        payload, _result = self._transfer(rd, held_out, "--group-by", "cell_id")
        report = await self._ingest_transfer(e2e_config, payload, "transfer.json")

        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            r = await s.run(
                "MATCH (x:Execution {id:$x})-[:USED]->(n) "
                "RETURN labels(n) AS labels, n.path AS path, "
                "n.custom_regime AS regime",
                x=report.execution_id,
            )
            used = [dict(rec) async for rec in r]
            r = await s.run(
                "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN labels(n) AS labels, n.id AS id",
                x=report.execution_id,
            )
            generated = [dict(rec) async for rec in r]
            r = await s.run(
                "MATCH (x:Execution {id:$x}) RETURN x.status AS status, "
                "x.service AS service, x.kind AS kind, "
                "x.custom_run_id AS run_id, x.custom_group_by AS group_by",
                x=report.execution_id,
            )
            execution = [dict(rec) async for rec in r][0]

        by_path = {Path(u["path"]).name: u for u in used if u["path"]}
        # 1. the table the form was transferred ONTO, labelled held_out
        assert "cellsBC.csv" in by_path
        assert "Dataset" in by_path["cellsBC.csv"]["labels"]
        assert by_path["cellsBC.csv"]["regime"] == REGIME_HELD_OUT
        # 2. the source run's discovered Script: the real chain back
        assert "prov.py" in by_path
        assert "Script" in by_path["prov.py"]["labels"]
        # 3. the source run's own training table, labelled scored
        assert "cellA.csv" in by_path
        assert by_path["cellA.csv"]["regime"] == REGIME_SCORED

        gen_labels = [lab for g in generated for lab in g["labels"]]
        assert gen_labels.count("Finding") == 2
        assert "Document" in gen_labels  # transfer.json, the raw report
        assert report.artifact in {g["id"] for g in generated}

        assert execution["status"] == "completed"
        assert execution["service"] == SERVICE_TAG
        assert execution["kind"] == "equation-transfer"
        assert execution["run_id"] == "prov"
        assert execution["group_by"] == "cell_id"

    @pytest.mark.asyncio
    async def test_reingesting_the_same_transfer_creates_no_duplicates(
        self, e2e_config
    ):
        from wheeler.graph.driver import get_async_driver

        rd = self._search_on_cell_a("idem")
        await self._ingest_discovery(e2e_config, rd)
        held_out = self._tmp / "cellsBC.csv"
        _write_grouped(held_out, ["c02", "c03"])
        payload, _result = self._transfer(rd, held_out, "--group-by", "cell_id")

        first = await self._ingest_transfer(e2e_config, payload, "transfer.json")
        second = await self._ingest_transfer(e2e_config, payload, "transfer.json")

        assert second.execution_id == first.execution_id
        assert second.created == 0
        assert second.deduped >= 2  # both Findings, plus the input artifacts

        digest = _transfer_key(
            "idem", payload["data_path"], payload["candidate"]["sample_order"]
        )
        session_id = f"idem:cellsBC:{digest}"
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            r = await s.run(
                "MATCH (x:Execution {service:$svc, session_id:$sid}) "
                "RETURN count(x) AS n",
                svc=SERVICE_TAG, sid=session_id,
            )
            assert [rec["n"] async for rec in r] == [1]
            r = await s.run(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN count(n) AS n",
                x=first.execution_id,
            )
            assert [rec["n"] async for rec in r] == [2]
            # Edges are link_once-guarded, so no fan-in doubled either.
            r = await s.run(
                "MATCH (x:Execution {id:$x})-[u:USED]->(n) "
                "RETURN count(u) AS edges, count(DISTINCT n) AS nodes",
                x=first.execution_id,
            )
            counts = [dict(rec) async for rec in r][0]
            assert counts["edges"] == counts["nodes"]

    @pytest.mark.asyncio
    async def test_two_transfers_of_one_run_are_two_executions(self, e2e_config):
        """One discovery, two held-out tables, two independent answers."""
        rd = self._search_on_cell_a("twin")
        await self._ingest_discovery(e2e_config, rd)
        b = self._tmp / "cellB.csv"
        c = self._tmp / "cellC.csv"
        _write_ungrouped(b, "c02", seed=21)
        _write_ungrouped(c, "c03", seed=22)

        payload_b, _r = self._transfer(rd, b)
        report_b = await self._ingest_transfer(e2e_config, payload_b, "tb.json")
        payload_c, _r = self._transfer(rd, c)
        report_c = await self._ingest_transfer(e2e_config, payload_c, "tc.json")

        assert report_b.execution_id != report_c.execution_id
        found_b = await self._findings(e2e_config, report_b.execution_id)
        found_c = await self._findings(e2e_config, report_c.execution_id)
        assert set(found_b) == set(found_c) == {CLAIM_FORM, CLAIM_CONSTANTS}
        # Four distinct Findings: the second transfer did not overwrite the first.
        ids = {f["id"] for f in found_b.values()} | {
            f["id"] for f in found_c.values()
        }
        assert len(ids) == 4
        # And each recovered ITS OWN cell's constants.
        for found, cell in ((found_b, "c02"), (found_c, "c03")):
            a, bb = CELLS[cell]
            got = json.loads(found[CLAIM_FORM]["params_per_group"])
            vec = next(iter(got.values()))
            assert vec[0] == pytest.approx(a, abs=1e-6)
            assert vec[1] == pytest.approx(bb, abs=1e-6)


class TestFailedTransferE2E(_TransferE2E):
    """The external-call failsafe: a failed transfer fabricates NO Findings."""

    @pytest.mark.asyncio
    async def test_a_failed_transfer_records_a_failed_execution_and_no_findings(
        self, e2e_config
    ):
        from wheeler.graph.driver import get_async_driver

        rd = self._search_on_cell_a("failed")
        await self._ingest_discovery(e2e_config, rd)

        # c02's rows are fine; c03's target is unreachable by any real a*x+b, so
        # the refit fails on it and one blind group invalidates the candidate.
        bad = self._tmp / "bad.csv"
        lines = ["cell_id,x1,y"]
        x, y = _rows("c02", 20, 4)
        lines += [f"c02,{float(a):.17g},{float(b):.17g}" for a, b in zip(x, y)]
        lines += [f"c03,{float(v):.17g},inf" for v in x]
        bad.write_text("\n".join(lines) + "\n")

        payload, result = self._transfer(rd, bad, "--group-by", "cell_id")
        assert result.exit_code == 1
        assert payload["status"] == "failed"
        # The failed payload DOES carry partial fixed-theta numbers. Promoting
        # them would answer the CONSTANTS question while silently dropping the
        # FORM one the transfer was run for.
        assert payload["fixed_theta"]["value_per_group"]["c02"] is not None

        report = await self._ingest_transfer(e2e_config, payload, "transfer.json")
        assert report.failed is True
        assert report.job_state == "failed"
        # The raw report is still registered, so the attempt is debuggable.
        assert report.artifact

        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            r = await s.run(
                "MATCH (x:Execution {id:$x}) RETURN x.status AS status, "
                "x.custom_job_state AS job_state, x.custom_error AS error",
                x=report.execution_id,
            )
            execution = [dict(rec) async for rec in r][0]
            r = await s.run(
                "MATCH (n:Finding)-[:WAS_GENERATED_BY]->(x:Execution {id:$x}) "
                "RETURN count(n) AS n",
                x=report.execution_id,
            )
            n_findings = [rec["n"] async for rec in r][0]

        assert execution["status"] == "failed"
        assert execution["job_state"] == "failed"
        assert "c03" in (execution["error"] or "")
        assert n_findings == 0

    @pytest.mark.asyncio
    async def test_a_transfer_onto_the_runs_own_training_data_is_labelled_scored(
        self, e2e_config
    ):
        """The control. Refitting on data the search fitted is not a holdout of
        any kind, and the graph must say so rather than flattering it."""
        from wheeler.graph.driver import get_async_driver

        rd = self._search_on_cell_a("control")
        await self._ingest_discovery(e2e_config, rd)
        payload, _result = self._transfer(rd, self._tmp / "cellA.csv")
        report = await self._ingest_transfer(e2e_config, payload, "transfer.json")

        found = await self._findings(e2e_config, report.execution_id)
        for entry in found.values():
            assert entry["regime"] == REGIME_SCORED
            assert "SCORED, not held out" in entry["description"]
        # And the source constants DO fit here, which is what makes the held-out
        # comparison in the other test mean something.
        assert found[CLAIM_CONSTANTS]["value"] == pytest.approx(0.0, abs=1e-10)

        # The target and the source are ONE table here, so it lands ONCE and
        # keeps the reason the TARGET write recorded, not the general source one.
        driver = get_async_driver(e2e_config)
        async with driver.session(database=e2e_config.neo4j.database) as s:
            r = await s.run(
                "MATCH (x:Execution {id:$x})-[:USED]->(n:Dataset) "
                "RETURN n.path AS path, n.custom_regime_reason AS reason",
                x=report.execution_id,
            )
            datasets = [dict(rec) async for rec in r]
        assert len(datasets) == 1
        assert datasets[0]["path"].endswith("cellA.csv")
        assert "the run's own training data" in datasets[0]["reason"]
