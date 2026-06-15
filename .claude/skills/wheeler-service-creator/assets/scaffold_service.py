"""Stdlib-only scaffolder for a new Wheeler service adapter.

Given a small CONTRACT dict, emit the four skeleton files the
``wheeler-service-creator`` skill describes:

  1. a ``.wheeler/services.yaml`` entry (appended, never overwriting),
  2. a marshal-out ingest skeleton ``wheeler/integrations/<provider>/<tool>.py``,
  3. a marshal-in act ``.claude/commands/wh/<provider>-<tool>.md``,
  4. a parse-unit + live-Neo4j e2e test stub
     ``tests/integrations/<provider>/test_<tool>.py``.

This is a MECHANICAL boilerplate writer, not the adapter. The one thing it can
NOT write is the parser body (``parse_<tool>``): that is tool-specific and only a
real captured output can teach it, so the skeleton leaves it a clearly-marked
TODO returning ``([], RunMeta())``. The skill's prose is the source of truth; this
helper just saves the human from hand-copying boilerplate. Markdown-driven
scaffolding (the model writing the files itself) is equally valid.

Stdlib only (no PyYAML): the services.yaml entry is emitted as hand-rolled YAML
text, mirroring the shape in ``docs/asta-engine-spec.md`` section 2. Pure I/O;
no graph dependency, no LLM-provider import.

Run as a module for a smoke scaffold::

    python scaffold_service.py --provider myorg --tool widget \\
        --name Widget --raw-node dataset --dry-run
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

# Valid raw-node types (the raw output node). document = synthesized WRITING
# (W-), dataset = structured reference RECORDS (D-). Never call everything a
# Dataset; reserve it for genuine data / records.
_RAW_NODE_TYPES = {"document", "dataset"}


def _slug(value: str) -> str:
    """Lower-case, filesystem-and-id-safe slug (letters, digits, hyphens)."""
    s = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    return s.strip("-")


def _ident(value: str) -> str:
    """Python-identifier-safe token (slug with hyphens -> underscores)."""
    return _slug(value).replace("-", "_") or "tool"


def _camel(value: str) -> str:
    """CamelCase token for class names (e.g. 'paper-finder' -> 'PaperFinder')."""
    return "".join(part.capitalize() for part in _slug(value).split("-") if part)


@dataclass
class ServiceContract:
    """The minimal contract that drives the scaffold.

    Identity + ports + output shape, NOT a field-map language: the parser stays
    tool-specific Python. ``raw_node`` is ``document`` (synthesized writing) or
    ``dataset`` (structured records).
    """

    provider: str
    tool: str
    name: str = ""
    description: str = ""
    kind: str = "shell-out"
    cli_invocation: str = ""
    available: str = ""
    cost: str = "unknown"
    when: str = ""
    raw_node: str = "dataset"
    nodes: list[str] = field(default_factory=lambda: ["Paper"])
    inputs: list[dict] = field(default_factory=list)

    # --- derived identity ---
    @property
    def provider_slug(self) -> str:
        return _slug(self.provider) or "provider"

    @property
    def tool_slug(self) -> str:
        return _slug(self.tool) or "tool"

    @property
    def tool_ident(self) -> str:
        return _ident(self.tool)

    @property
    def tool_camel(self) -> str:
        return _camel(self.tool) or "Tool"

    @property
    def service_id(self) -> str:
        return f"{self.provider_slug}-{self.tool_slug}"

    @property
    def service_tag(self) -> str:
        return f"{self.provider_slug}:{self.tool_slug}"

    @property
    def act_name(self) -> str:
        return f"wh:{self.provider_slug}-{self.tool_slug}"

    @property
    def display_name(self) -> str:
        return self.name or self.tool_camel

    @property
    def cli_binary(self) -> str:
        """The CLI command the act invokes; drives the ``Bash(<binary>:*)`` grant.

        Taken from the first token of ``cli_invocation`` (e.g. ``asta`` from
        ``asta literature find ...``), so the allowed-tools Bash prefix matches
        the real binary the act runs, mirroring ``Bash(asta:*)`` in the Asta
        acts. Falls back to the tool slug when no invocation is given.
        """
        head = (self.cli_invocation or "").strip().split()
        return head[0] if head else self.tool_slug

    def __post_init__(self) -> None:
        if (self.raw_node or "").lower() not in _RAW_NODE_TYPES:
            raise ValueError(
                f"raw_node must be one of {sorted(_RAW_NODE_TYPES)}, "
                f"got {self.raw_node!r}"
            )
        self.raw_node = self.raw_node.lower()
        # Reject a blank provider/tool BEFORE the slug fallback masks it: an empty
        # or whitespace-only input is a genuine error, not a "provider"/"tool"
        # default.
        if not _slug(self.provider) or not _slug(self.tool):
            raise ValueError("provider and tool are required and must be slug-safe")


# ---------------------------------------------------------------------------
# Renderers (each returns the file text; pure, no I/O)
# ---------------------------------------------------------------------------


def render_services_entry(c: ServiceContract) -> str:
    """Render one ``services.yaml`` list entry (hand-rolled YAML, stdlib only)."""
    inputs = c.inputs or [{"name": "query", "source": "query", "required": True}]
    lines = [
        f"  - id: {c.service_id}",
        f"    provider: {c.provider_slug}",
        f"    name: {c.display_name}",
        f"    description: {c.description or c.display_name}",
        f"    kind: {c.kind}",
        f"    act: /{c.act_name}",
        f'    cost: "{c.cost}"',
        f'    available: "{c.available or c.tool_slug + " --version"}"',
        f'    when: "{c.when or c.description or c.display_name}"',
        "    inputs:",
    ]
    for port in inputs:
        name = port.get("name", "query")
        source = port.get("source", "query")
        required = "true" if port.get("required") else "false"
        lines.append(
            f"      - {{ name: {name}, source: {source}, required: {required} }}"
        )
    node_list = ", ".join(c.nodes) if c.nodes else "Paper"
    lines += [
        "    output:",
        f"      raw_node: {c.raw_node}",
        f"      nodes: [{node_list}]",
        f"    # implemented by wheeler/integrations/{c.provider_slug}/{c.tool_ident}.py",
    ]
    return "\n".join(lines) + "\n"


def render_ingest(c: ServiceContract) -> str:
    """Render the marshal-out ingest skeleton (parser left a TODO stub)."""
    return f'''"""Marshal-out (deterministic): ingest a {c.display_name} artifact.

SCAFFOLD. Fill ``parse_{c.tool_ident}`` against ONE real captured output, then
run the adversarial review. A marshal-out module mirroring the Asta adapters: it
imports ``execute_tool`` lazily (function-local) so every graph write routes
through the triple-write + write-receipt + trace-id + embedding wiring, and
reuses the shared helpers in ``_marshal.py`` plus ``register_output_artifact`` in
``artifacts.py``.

REAL output shape: TODO (capture one real run and document it here).

Provenance is TWO-SIDED. The run Execution sits between the graph inputs that
shaped the request and the graph outputs the parser produced:

    input  -[USED]<-  Execution  ->[WAS_GENERATED_BY]  output

  - INPUT side (``USED``): the marshal-in synthesized the tool payload FROM graph
    nodes (the question, seeded Findings, a Dataset path), so the run USED them.
    Recorded by ``_record_used(backend, config, exec_id, used_inputs)``,
    existence-guarded and link_once.
  - OUTPUT side (``WAS_GENERATED_BY``): every node the parser PRODUCED this run
    (Findings, Hypotheses, the raw artifact node) is generated by the Execution.
    Recorded by ``_record_generated(...)`` below and by
    ``register_output_artifact`` for the raw node.

Because both sides hang off ONE Execution, the chain is transitive without
per-input/per-output edges: ``output -[WAS_GENERATED_BY]-> Execution -[USED]->
input``. Any result traces back to the exact graph context that shaped its
request. EXCEPTION: Papers are REFERENCE ENTITIES (per /wh:close, /wh:graph-link)
and carry NO ``WAS_GENERATED_BY``; a paper the knowledge was derived from is an
INPUT, so it gets ``Execution -[USED]-> paper`` instead.

Invariants (verbatim from the template, keep them true):
  - Defensive: every step tolerates missing pieces, counts and skips, never
    raises. A partial or shape-drifted artifact never aborts ingest.
  - Sequential writes only. Never ``asyncio.gather``: ``execute_tool`` reuses
    one cached backend singleton and Neo4j forbids concurrent queries.
  - link_once: every edge is existence-guarded because the backend's
    ``create_relationship`` is a bare CREATE that duplicates on re-run.
  - One Execution per RUN, tagged service ``{c.service_tag}``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from wheeler.config import WheelerConfig
from wheeler.integrations.{c.provider_slug}._marshal import (  # type: ignore[import-not-found]
    ImportReport,
    _find_execution,
    _link_once,
    _record_used,
)

logger = logging.getLogger(__name__)

_SERVICE_TAG = "{c.service_tag}"
# document = synthesized WRITING (W-), dataset = structured RECORDS (D-).
_RAW_NODE_TYPE = "{c.raw_node}"


@dataclass
class RunMeta:
    """Benchmark fields lifted from the run (run_id, cost, time, model)."""

    run_id: str = ""
    cost: float | None = None
    time: float | None = None
    model: str = ""

    def custom_bag(self) -> dict[str, Any]:
        bag: dict[str, Any] = {{"service": _SERVICE_TAG}}
        if self.run_id:
            bag["run_id"] = self.run_id
        if self.cost is not None:
            bag["cost"] = self.cost
        if self.time is not None:
            bag["time"] = self.time
        if self.model:
            bag["model"] = self.model
        return bag


# --- defensive coercion helpers (copied from the template) ---


def _first(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in d and d[key] is not None:
            return d[key]
    return default


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


async def _record_generated(
    backend,
    config: WheelerConfig,
    exec_id: str,
    produced_ids: list[str],
    report: ImportReport,
) -> None:
    """OUTPUT-side provenance: each PRODUCED node -[WAS_GENERATED_BY]-> Execution.

    The mirror of ``_record_used`` (input side). Pass the ids of the nodes THIS
    run created, EXCLUDING Papers (reference entities carry no WAS_GENERATED_BY;
    a derived-from paper is an INPUT, recorded via ``_record_used`` instead).
    link_once-guarded so re-ingest never duplicates the edge; a blank or
    self-edge is skipped. Increments ``report.linked`` per new edge.
    """
    if not exec_id or not produced_ids:
        return
    seen: set[str] = set()
    for raw_id in produced_ids:
        node_id = (raw_id or "").strip()
        if not node_id or node_id == exec_id or node_id in seen:
            continue
        seen.add(node_id)
        if await _link_once(backend, config, node_id, "WAS_GENERATED_BY", exec_id):
            report.linked += 1


def parse_{c.tool_ident}(doc: Any) -> tuple[list[Any], RunMeta]:
    """Parse a {c.display_name} output into records + run metadata.

    TODO: fill against a real captured output. Defensive throughout: a doc that
    is not the expected shape yields ``([], RunMeta())`` so a partial artifact
    never aborts ingest.
    """
    if not isinstance(doc, dict):
        logger.warning(
            "parse_{c.tool_ident}: doc is not a dict, got %s", type(doc).__name__
        )
        return [], RunMeta()
    # TODO: walk the real shape into records and lift the run metadata.
    return [], RunMeta()


async def ingest_{c.tool_ident}(
    doc: dict[str, Any],
    *,
    link_to: str | None = None,
    config: WheelerConfig,
    artifact_path: str | None = None,
    used_inputs: list[str] | None = None,
) -> ImportReport:
    """Ingest a parsed {c.display_name} output into the knowledge graph.

    Args:
        doc: The raw {c.display_name} output dict.
        link_to: Optional node id (Question/Plan) each produced node links to.
        config: Active Wheeler config.
        artifact_path: Optional path to the raw output file; registered as the
            declared raw node ({c.raw_node}) WAS_GENERATED_BY the run Execution.
        used_inputs: Optional graph node ids the marshal-in consumed to build the
            request. The run Execution -[USED]-> each one that exists (input-side
            provenance, existence-guarded, link_once, never fabricated).

    Returns:
        An ImportReport with created / deduped / linked / skipped / used counts.
    """
    from wheeler.tools.graph_tools import _get_backend, execute_tool

    report = ImportReport()
    records, run_meta = parse_{c.tool_ident}(doc)
    if not records:
        logger.warning("ingest_{c.tool_ident}: no parseable records in artifact")
        return report

    backend = await _get_backend(config)

    # One Execution per RUN, tagged with the service. session_id correlates every
    # node written this turn and makes the run idempotent.
    session_id = run_meta.run_id or "TODO-stable-run-key"
    exec_id = await _find_execution(
        backend, config, service=_SERVICE_TAG, session_id=session_id
    )
    if not exec_id:
        import json

        exec_result = json.loads(
            await execute_tool(
                "add_execution",
                {{
                    "kind": "{c.tool_slug}",
                    "description": f"{c.display_name}: {{run_meta.run_id}}",
                    "agent_id": "{c.provider_slug}",
                    "status": "completed",
                    "session_id": session_id,
                    "service": _SERVICE_TAG,
                }},
                config,
            )
        )
        exec_id = exec_result.get("node_id", "")
    report.execution_id = exec_id

    # Input-side provenance: the marshal-in built this request FROM graph nodes,
    # so the run USED them. Existence-guarded; a missing id is skipped, never
    # fabricated; re-ingest dedupes via link_once.
    if exec_id and used_inputs:
        report.used += await _record_used(backend, config, exec_id, used_inputs)

    # The raw output is saved durably and registered as the declared node type,
    # linked WAS_GENERATED_BY the run Execution. Best-effort: never raises.
    try:
        from wheeler.integrations.{c.provider_slug}.artifacts import (  # type: ignore[import-not-found]
            register_output_artifact,
        )

        await register_output_artifact(
            artifact_path,
            execution_id=exec_id,
            service=_SERVICE_TAG,
            config=config,
            node_type=_RAW_NODE_TYPE,
            run_id=run_meta.run_id,
            benchmark=run_meta.custom_bag(),
            description=f"{{_SERVICE_TAG}} raw output",
        )
    except Exception:
        logger.warning(
            "ingest_{c.tool_ident}: artifact registration raised (best-effort)",
            exc_info=True,
        )

    # Bucket each record into its nodes. Every WRITE goes through execute_tool;
    # every edge through _link_once. Collect the ids of the nodes THIS run
    # PRODUCES (NOT Papers: they are reference entities) so the output side of
    # provenance can be wired in one pass below.
    produced_ids: list[str] = []
    for _record in records:
        # TODO: create this record's node(s) and wire its semantic edges.
        #
        #   import json
        #   created = json.loads(await execute_tool("add_finding", {{...,
        #       "session_id": session_id, "service": _SERVICE_TAG}}, config))
        #   node_id = created.get("node_id")
        #   if node_id:
        #       report.created += 1
        #       produced_ids.append(node_id)        # OUTPUT side, wired below
        #       if link_to:                         # the request's link target
        #           if await _link_once(backend, config, node_id,
        #                                "AROSE_FROM", link_to):
        #               report.linked += 1
        #
        # If the output references papers: dedupe on corpus_id, create with
        # add_paper, then paper -[SUPPORTS|CONTRADICTS|CITES]-> the produced node.
        # Papers carry NO WAS_GENERATED_BY; instead the run Execution -[USED]->
        # a paper the knowledge was derived from:
        #   if await _link_once(backend, config, exec_id, "USED", paper_id):
        #       report.linked += 1
        pass

    # OUTPUT-side provenance: every produced node -[WAS_GENERATED_BY]-> the run
    # Execution (the mirror of the input-side USED edges above). Papers are
    # excluded by construction (they are never appended to produced_ids).
    await _record_generated(backend, config, exec_id, produced_ids, report)

    logger.info(
        "ingest_{c.tool_ident}: created=%d deduped=%d linked=%d skipped=%d "
        "used=%d (exec=%s)",
        report.created,
        report.deduped,
        report.linked,
        report.skipped,
        report.used,
        exec_id,
    )
    return report
'''


def render_act(c: ServiceContract) -> str:
    """Render the marshal-in act (the system prompt) for the new tool."""
    cli = c.cli_invocation or f'{c.tool_slug} run "$ARGUMENTS" -o /tmp/{c.tool_slug}.json'
    probe = c.available or f"{c.cli_binary} --version"
    return f'''---
name: {c.act_name}
description: Use when the user wants to run {c.display_name} and ingest the results into the Wheeler knowledge graph
argument-hint: "[request]"
allowed-tools:
  - Read
  - Bash({c.cli_binary}:*)
  - Bash(wheeler integrate:*)
  - mcp__wheeler_core__search_context
  - mcp__wheeler_query__query_findings

---

You are Wheeler, running {c.display_name} over a request and marshalling the results into the knowledge graph. You orchestrate; the {c.tool_slug} CLI does the work and owns its own auth and timeouts; one deterministic `wheeler integrate` verb writes the graph.

## Preflight

1. Confirm the tool is installed: `{probe}`. If that fails, say {c.display_name} is not available and stop. Do not attempt the run.
2. Read context so the request is shaped by the graph. Use `mcp__wheeler_core__search_context` with the user's request (or the active question) to see what is already known, and the relevant `mcp__wheeler_query__query_*` for existing nodes. Use this only to sharpen the request and choose a link target. Do not invent results. Do not do the scientist's thinking.

## Choose the request and link target

- The request is `$ARGUMENTS` when provided. If empty, ask the user or derive one from the active investigation.
- Pick at most one link target: the Question (`Q-...`) or Plan (`PL-...`) this run supports. If there is no clear target, run without one.

## Run

Run the CLI, writing the artifact to a temp file:

```
{cli}
```

If the command exits non-zero (including a login or auth failure), report it and stop. A failed run writes nothing to the graph by design.

## Ingest

Marshal the artifact into the graph with the single integrate verb:

```
wheeler integrate ingest {c.tool_ident} /tmp/{c.tool_slug}.json --link-to <Q- or PL- id> --used <Q- or PL- id>,<source ids>
```

Omit `--link-to` if there is no target. Pass `--used` with the graph node ids the request was built FROM (at minimum the link target, plus any seeded source ids): this records `Execution -[USED]-> each input` (input-side provenance), so every result traces back to the graph context that shaped the request, not just what the tool returned. Omit `--used` if there were no graph inputs. The verb is idempotent: re-running the same artifact creates no duplicate nodes, edges, or USED edges.

## Report

Relay the printed summary (`created`, `deduped`, `linked`, `skipped`, the run Execution id, and the new node ids) to the user in one or two sentences. The results are now in the graph; suggest the relevant `query_*` filters to browse them. Do not editorialize the science. Never use em dashes.
'''


def render_test(c: ServiceContract) -> str:
    """Render the parse-unit + live-Neo4j e2e test stub for the new tool."""
    cleanup = f"_cleanup_{c.tool_ident}"
    return f'''"""Tests for the {c.display_name} adapter.

SCAFFOLD. Two layers, NEITHER making a live {c.tool_slug} call:
  1. parse_{c.tool_ident}: parse a trimmed REAL fixture plus shape-drift /
     garbage tolerance (never raises). Fill the fixture + expected counts.
  2. live-Neo4j e2e: ingest the real fixture, assert the bucketing subgraph,
     then re-ingest the SAME artifact and assert idempotency. Skipped
     automatically when Neo4j is not reachable.

Run: python -m pytest tests/integrations/{c.provider_slug}/test_{c.tool_ident}.py -q
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from wheeler.integrations.{c.provider_slug}.{c.tool_ident} import (  # type: ignore[import-not-found]
    RunMeta,
    parse_{c.tool_ident},
)

# Trimmed REAL output captured from one live run (TODO: capture + commit).
FIXTURE = Path(__file__).parent / "fixtures" / "{c.tool_ident}_real_sample.json"
SERVICE_TAG = "{c.service_tag}"

# TODO: fill expected bucketing totals derived from the fixture.
# N_NODES = ...


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


# ---------------------------------------------------------------------------
# 1. Defensive parse against the REAL shape
# ---------------------------------------------------------------------------


class TestParse{c.tool_camel}:
    def test_non_dict_is_empty(self):
        records, run_meta = parse_{c.tool_ident}("not a dict")
        assert records == []
        assert isinstance(run_meta, RunMeta)

    def test_empty_doc_is_empty(self):
        records, run_meta = parse_{c.tool_ident}({{}})
        assert records == []
        assert isinstance(run_meta, RunMeta)

    @pytest.mark.skipif(not FIXTURE.exists(), reason="real fixture not captured yet")
    def test_returns_records_and_run_meta(self):
        records, run_meta = parse_{c.tool_ident}(_load_fixture())
        assert isinstance(run_meta, RunMeta)
        # TODO: assert record count + run metadata against the fixture.
        assert records is not None


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


def {cleanup}(e2e_config, e2e_tag: str) -> None:
    """Hermetic teardown: delete ONLY the nodes THIS run tagged.

    EXACTLY ``MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n`` and nothing
    else. NEVER delete by ``service`` or ``corpus_id``: the e2e config runs on
    the SHARED default namespace where production nodes carry the same service
    tag and the same corpus_ids, so a service- or corpus_id-scoped delete would
    wipe real user data.
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


@pytest.mark.skipif(not FIXTURE.exists(), reason="real fixture not captured yet")
class TestIngest{c.tool_camel}E2E:
    @pytest.fixture(autouse=True)
    def _skip_and_cleanup(self, neo4j_available, e2e_config, tmp_path, monkeypatch):
        if not neo4j_available:
            pytest.skip("Neo4j not available -- skipping integrations e2e")
        # Temp cwd so the on-disk indices + durable raw store land in a sandbox
        # we delete; per-run unique tag so teardown never touches another test.
        monkeypatch.chdir(tmp_path)
        self._tmp = tmp_path
        self._e2e_tag = f"integrations_e2e_{{uuid.uuid4().hex}}"
        {cleanup}(e2e_config, self._e2e_tag)
        yield
        {cleanup}(e2e_config, self._e2e_tag)

    async def _tag_all(self, e2e_config, report):
        """Tag ONLY the nodes THIS run created, scoped off the report ids plus
        the run's WAS_GENERATED_BY fan-in. NEVER by service or corpus_id. Papers
        are reference entities (no WAS_GENERATED_BY); tag them via paper_ids."""
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        run_ids = [i for i in (report.execution_id, report.artifact) if i]
        run_ids += [pid for pid in report.paper_ids if pid]
        async with driver.session(database=db) as s:
            if run_ids:
                await s.run(
                    "MATCH (n) WHERE n.id IN $ids SET n.e2e_tag = $tag",
                    ids=run_ids, tag=self._e2e_tag,
                )
            if report.execution_id:
                await s.run(
                    "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {{id: $xid}}) "
                    "SET n.e2e_tag = $tag",
                    xid=report.execution_id, tag=self._e2e_tag,
                )

    @pytest.mark.asyncio
    async def test_ingest_buckets_and_is_idempotent(self, e2e_config):
        from wheeler.integrations.{c.provider_slug}.{c.tool_ident} import (  # type: ignore[import-not-found]
            ingest_{c.tool_ident},
        )

        doc = _load_fixture()
        artifact_path = self._tmp / "{c.tool_ident}_raw.json"
        artifact_path.write_text(json.dumps(doc))

        # Seed an input node so the run has something to USE (input side).
        from wheeler.tools.graph_tools import execute_tool  # type: ignore[import-not-found]

        q = json.loads(
            await execute_tool(
                "add_question",
                {{"question": "E2E: what does {c.display_name} address?", "priority": 5}},
                e2e_config,
            )
        )
        question_id = q["node_id"]

        # --- First ingest ---
        report1 = await ingest_{c.tool_ident}(
            doc,
            link_to=question_id,
            config=e2e_config,
            artifact_path=str(artifact_path),
            used_inputs=[question_id],
        )
        await self._tag_all(e2e_config, report1)
        assert report1.execution_id

        # BOTH provenance sides, scoped to THIS run's e2e_tag.
        from wheeler.graph.driver import get_async_driver

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as s:
            # INPUT side: the run USED the seeded question.
            used = await s.run(
                "MATCH (x:Execution {{id: $xid}})-[:USED]->(n) "
                "RETURN count(n) AS c",
                xid=report1.execution_id,
            )
            assert (await used.single())["c"] >= 1
            # OUTPUT side: produced nodes WAS_GENERATED_BY the run Execution.
            gen = await s.run(
                "MATCH (n)-[:WAS_GENERATED_BY]->(x:Execution {{id: $xid}}) "
                "RETURN count(n) AS c",
                xid=report1.execution_id,
            )
            assert (await gen.single())["c"] >= 1
            # Papers are reference entities: NO WAS_GENERATED_BY.
            papers_gen = await s.run(
                "MATCH (p:Paper)-[:WAS_GENERATED_BY]->(x:Execution {{id: $xid}}) "
                "RETURN count(p) AS c",
                xid=report1.execution_id,
            )
            assert (await papers_gen.single())["c"] == 0
        # TODO: also assert this tool's node + edge counts, scoped to
        # self._e2e_tag (e.g. MATCH (n) WHERE n.e2e_tag = self._e2e_tag ...).

        # --- Re-ingest: idempotent (no duplicate nodes OR provenance edges) ---
        report2 = await ingest_{c.tool_ident}(
            doc,
            link_to=question_id,
            config=e2e_config,
            artifact_path=str(artifact_path),
            used_inputs=[question_id],
        )
        await self._tag_all(e2e_config, report2)
        assert report2.created == 0  # nothing new on the second pass
'''


# ---------------------------------------------------------------------------
# Writers (idempotent-ish file emission)
# ---------------------------------------------------------------------------


def _write(path: Path, text: str, *, overwrite: bool, dry_run: bool) -> str:
    """Write ``text`` to ``path``; return a one-line action note."""
    if path.exists() and not overwrite:
        return f"skip (exists)  {path}"
    if dry_run:
        return f"would write    {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return f"wrote          {path}"


def _append_service_entry(
    path: Path, entry: str, *, dry_run: bool
) -> str:
    """Append a services.yaml entry, creating the file with a root if absent.

    Idempotent on the entry id: if an entry with the same ``id:`` line already
    exists, it is left untouched.
    """
    id_line = entry.splitlines()[0].strip()  # "- id: <provider>-<tool>"
    existing = path.read_text() if path.exists() else ""
    if id_line in existing:
        return f"skip (entry exists)  {path}"
    if not existing.strip():
        body = "services:\n" + entry
    elif "services:" in existing:
        sep = "" if existing.endswith("\n") else "\n"
        body = existing + sep + entry
    else:
        body = existing.rstrip("\n") + "\nservices:\n" + entry
    if dry_run:
        return f"would append   {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return f"appended       {path}"


def scaffold(
    contract: ServiceContract,
    repo_root: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> list[str]:
    """Emit all four skeleton files under ``repo_root``; return action notes.

    The ingest module, act, and test are written; the services.yaml entry is
    appended (never overwriting other services). The empty package ``__init__``
    files are created when the provider package is new.
    """
    notes: list[str] = []
    provider = contract.provider_slug
    tool = contract.tool_ident

    # 1. services.yaml entry (append).
    notes.append(
        _append_service_entry(
            repo_root / ".wheeler" / "services.yaml",
            render_services_entry(contract),
            dry_run=dry_run,
        )
    )

    # 2. ingest skeleton + package __init__.
    pkg_init = repo_root / "wheeler" / "integrations" / provider / "__init__.py"
    if not pkg_init.exists():
        notes.append(_write(pkg_init, "", overwrite=False, dry_run=dry_run))
    notes.append(
        _write(
            repo_root / "wheeler" / "integrations" / provider / f"{tool}.py",
            render_ingest(contract),
            overwrite=overwrite,
            dry_run=dry_run,
        )
    )

    # 3. marshal-in act.
    notes.append(
        _write(
            repo_root / ".claude" / "commands" / "wh"
            / f"{provider}-{contract.tool_slug}.md",
            render_act(contract),
            overwrite=overwrite,
            dry_run=dry_run,
        )
    )

    # 4. test stub + test package __init__.
    test_init = repo_root / "tests" / "integrations" / provider / "__init__.py"
    if not test_init.exists():
        notes.append(_write(test_init, "", overwrite=False, dry_run=dry_run))
    notes.append(
        _write(
            repo_root / "tests" / "integrations" / provider / f"test_{tool}.py",
            render_test(contract),
            overwrite=overwrite,
            dry_run=dry_run,
        )
    )
    return notes


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", required=True)
    p.add_argument("--tool", required=True)
    p.add_argument("--name", default="")
    p.add_argument("--description", default="")
    p.add_argument("--kind", default="shell-out")
    p.add_argument("--cli", dest="cli_invocation", default="")
    p.add_argument("--available", default="")
    p.add_argument("--cost", default="unknown")
    p.add_argument("--when", default="")
    p.add_argument("--raw-node", dest="raw_node", default="dataset")
    p.add_argument(
        "--nodes", default="Paper", help="comma-separated node types"
    )
    p.add_argument(
        "--repo-root", default=".", help="repo root to scaffold under"
    )
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    contract = ServiceContract(
        provider=args.provider,
        tool=args.tool,
        name=args.name,
        description=args.description,
        kind=args.kind,
        cli_invocation=args.cli_invocation,
        available=args.available,
        cost=args.cost,
        when=args.when,
        raw_node=args.raw_node,
        nodes=[n.strip() for n in args.nodes.split(",") if n.strip()],
    )
    notes = scaffold(
        contract,
        Path(args.repo_root),
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    for note in notes:
        print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
