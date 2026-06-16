"""Unit tests for the wheeler-service-creator scaffolder.

The script lives under .claude/skills/wheeler-service-creator/ (a dev-only,
gitignored-except-negated skill), so these tests skip cleanly on a checkout that
does not include it (mirroring tests/test_render_brief.py). The scaffolder is
deterministic and stdlib-only; pinning it here keeps the contract-to-skeleton
emission from drifting silently.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".claude/skills/wheeler-service-creator/assets/scaffold_service.py"

pytestmark = pytest.mark.skipif(
    not SCRIPT.exists(),
    reason="wheeler-service-creator skill not present in this checkout",
)


def _load_module():
    spec = importlib.util.spec_from_file_location("scaffold_service", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve cls.__module__ (its
    # field/InitVar type resolution walks sys.modules).
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _contract(mod, **overrides):
    base = dict(
        provider="MyOrg",
        tool="Paper-Finder",
        name="Paper Finder",
        description="literature search",
        raw_node="dataset",
        nodes=["Paper"],
        cost="free",
        when="literature search",
        available="myorg auth status",
        cli_invocation='myorg find "$QUERY" -o /tmp/paper-finder.json',
    )
    base.update(overrides)
    return mod.ServiceContract(**base)


# ---------------------------------------------------------------------------
# Identity derivation
# ---------------------------------------------------------------------------


def test_identity_derivation_is_slug_safe():
    mod = _load_module()
    c = _contract(mod)
    assert c.provider_slug == "myorg"
    assert c.tool_slug == "paper-finder"
    assert c.tool_ident == "paper_finder"
    assert c.tool_camel == "PaperFinder"
    assert c.service_id == "myorg-paper-finder"
    assert c.service_tag == "myorg:paper-finder"
    assert c.act_name == "wh:myorg-paper-finder"


def test_invalid_raw_node_rejected():
    mod = _load_module()
    with pytest.raises(ValueError):
        _contract(mod, raw_node="banana")


def test_missing_provider_rejected():
    mod = _load_module()
    with pytest.raises(ValueError):
        _contract(mod, provider="   ")


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def test_services_entry_carries_contract():
    mod = _load_module()
    c = _contract(mod)
    text = mod.render_services_entry(c)
    assert "id: myorg-paper-finder" in text
    assert "act: /wh:myorg-paper-finder" in text
    assert "raw_node: dataset" in text
    assert "nodes: [Paper]" in text
    assert 'cost: "free"' in text
    assert 'available: "myorg auth status"' in text


def test_ingest_skeleton_has_the_load_bearing_pieces():
    mod = _load_module()
    c = _contract(mod)
    text = mod.render_ingest(c)
    # Lazy, function-local execute_tool import (the only graph-write chokepoint).
    assert "from wheeler.tools.graph_tools import _get_backend, execute_tool" in text
    # INPUT-side provenance + idempotent Execution + raw artifact registration.
    assert "_record_used" in text
    assert "_find_execution" in text
    assert "register_output_artifact" in text
    assert '_SERVICE_TAG = "myorg:paper-finder"' in text
    assert '_RAW_NODE_TYPE = "dataset"' in text
    # OUTPUT-side provenance: produced nodes WAS_GENERATED_BY the Execution.
    assert "_record_generated" in text
    assert "WAS_GENERATED_BY" in text
    assert "produced_ids" in text
    # Both sides are explained so the chain is transitive.
    assert "input  -[USED]<-  Execution  ->[WAS_GENERATED_BY]  output" in text
    # Parser + ingest fn named off the tool ident.
    assert "def parse_paper_finder(" in text
    assert "async def ingest_paper_finder(" in text
    # The parser is a TODO stub returning empty, never raises.
    assert "return [], RunMeta()" in text


def test_act_is_a_marshal_in_prompt():
    mod = _load_module()
    c = _contract(mod)
    text = mod.render_act(c)
    assert "name: wh:myorg-paper-finder" in text
    assert "Bash(myorg:*)" in text
    assert "Bash(wheeler integrate:*)" in text
    assert "search_context" in text
    assert "--used" in text
    assert "wheeler integrate ingest paper_finder" in text


def test_act_has_the_semantic_wiring_step():
    """Part 3 of the three-part model: the generated act must carry a post-ingest
    semantic-wiring step that links NEW outputs to the EXISTING graph (judgment in
    the act, via link_nodes, NOT in the mechanical parser)."""
    mod = _load_module()
    c = _contract(mod)
    text = mod.render_act(c)
    # The step exists and is explicitly post-ingest / judgment.
    assert "Wire semantics to the existing graph" in text
    # It uses the mutation link tool, granted in allowed-tools.
    assert "mcp__wheeler_mutations__link_nodes" in text
    # It reads the existing graph to find the edges.
    assert "mcp__wheeler_query__query_open_questions" in text
    assert "mcp__wheeler_query__query_hypotheses" in text
    # It names the Wheeler semantic relationships that wire new -> existing.
    assert "SUPPORTS" in text
    assert "CONTRADICTS" in text
    assert "RELEVANT_TO" in text
    assert "CITES" in text
    # It is judgment, not mechanical: confirmed with the scientist.
    assert "judgment" in text.lower()


def test_test_stub_follows_e2e_tag_convention():
    mod = _load_module()
    c = _contract(mod)
    text = mod.render_test(c)
    # Hermetic teardown is EXACTLY the e2e_tag delete, never by service/corpus_id.
    assert "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n" in text
    assert "integrations_e2e_" in text
    assert "_cleanup_paper_finder" in text
    assert "class TestParsePaperFinder" in text
    assert "class TestIngestPaperFinderE2E" in text
    # Idempotency assertion present.
    assert "report2.created == 0" in text
    # Both provenance sides are asserted in the e2e stub.
    assert "[:USED]->" in text  # input side
    assert "[:WAS_GENERATED_BY]->" in text  # output side
    assert "used_inputs=[question_id]" in text  # the run is given an input to USE
    assert "MATCH (p:Paper)-[:WAS_GENERATED_BY]" in text  # papers carry none


def test_no_em_dashes_in_any_rendered_file():
    mod = _load_module()
    c = _contract(mod)
    for text in (
        mod.render_services_entry(c),
        mod.render_service_file(c),
        mod.render_ingest(c),
        mod.render_act(c),
        mod.render_test(c),
    ):
        assert "—" not in text  # no em dash


# ---------------------------------------------------------------------------
# Scaffold writer (filesystem, isolated tmp)
# ---------------------------------------------------------------------------


def test_service_file_is_a_bare_mapping():
    mod = _load_module()
    c = _contract(mod)
    text = mod.render_service_file(c)
    # Bare top-level mapping (no services: wrapper): the per-id folder shape.
    assert "services:" not in text
    assert text.startswith("id: myorg-paper-finder")
    assert "act: /wh:myorg-paper-finder" in text
    assert "raw_node: dataset" in text
    assert "nodes: [Paper]" in text


def test_scaffold_writes_all_four_pieces(tmp_path: Path):
    mod = _load_module()
    c = _contract(mod, provider="acme", tool="widget", raw_node="document")
    notes = mod.scaffold(c, tmp_path)
    # The contract lands as its own enabled-folder file (folder-based registry).
    assert any(".wheeler/services/acme-widget.yaml" in n for n in notes)

    service = tmp_path / ".wheeler" / "services" / "acme-widget.yaml"
    ingest = tmp_path / "wheeler" / "integrations" / "acme" / "widget.py"
    act = tmp_path / ".claude" / "commands" / "wh" / "acme-widget.md"
    test = tmp_path / "tests" / "integrations" / "acme" / "test_widget.py"

    for path in (service, ingest, act, test):
        assert path.exists(), f"missing {path}"

    # Provider package __init__ files created.
    assert (tmp_path / "wheeler" / "integrations" / "acme" / "__init__.py").exists()
    assert (tmp_path / "tests" / "integrations" / "acme" / "__init__.py").exists()

    # One file per service, bare mapping (no services: wrapper).
    service_text = service.read_text()
    assert service_text.startswith("id: acme-widget")
    assert "services:" not in service_text
    assert '_RAW_NODE_TYPE = "document"' in ingest.read_text()


def test_scaffold_service_file_not_overwritten_without_flag(tmp_path: Path):
    mod = _load_module()
    c = _contract(mod, provider="acme", tool="widget")
    mod.scaffold(c, tmp_path)
    service = tmp_path / ".wheeler" / "services" / "acme-widget.yaml"
    first = service.read_text()
    # Re-scaffold: a curated enabled file is not clobbered without --overwrite.
    notes = mod.scaffold(c, tmp_path)
    assert service.read_text() == first
    assert any("skip (exists)" in n for n in notes)


def test_scaffold_each_service_is_its_own_file(tmp_path: Path):
    mod = _load_module()
    mod.scaffold(_contract(mod, provider="acme", tool="widget"), tmp_path)
    mod.scaffold(_contract(mod, provider="acme", tool="gadget"), tmp_path)
    folder = tmp_path / ".wheeler" / "services"
    # One file per service: enabling/disabling one never touches the other.
    assert (folder / "acme-widget.yaml").exists()
    assert (folder / "acme-gadget.yaml").exists()
    assert (folder / "acme-widget.yaml").read_text().startswith("id: acme-widget")
    assert (folder / "acme-gadget.yaml").read_text().startswith("id: acme-gadget")


def test_dry_run_writes_nothing(tmp_path: Path):
    mod = _load_module()
    c = _contract(mod, provider="acme", tool="widget")
    notes = mod.scaffold(c, tmp_path, dry_run=True)
    assert any("would" in n for n in notes)
    assert not (tmp_path / "wheeler" / "integrations" / "acme" / "widget.py").exists()
    assert not (tmp_path / ".wheeler" / "services" / "acme-widget.yaml").exists()


def test_existing_file_not_overwritten_without_flag(tmp_path: Path):
    mod = _load_module()
    c = _contract(mod, provider="acme", tool="widget")
    ingest = tmp_path / "wheeler" / "integrations" / "acme" / "widget.py"
    ingest.parent.mkdir(parents=True)
    ingest.write_text("# hand-edited, keep me\n")
    mod.scaffold(c, tmp_path)
    assert ingest.read_text() == "# hand-edited, keep me\n"
    # With overwrite the skeleton replaces it.
    mod.scaffold(c, tmp_path, overwrite=True)
    assert "ingest_widget" in ingest.read_text()


def test_main_dry_run_smoke(tmp_path: Path, capsys):
    mod = _load_module()
    rc = mod.main(
        [
            "--provider", "acme",
            "--tool", "widget",
            "--name", "Widget",
            "--raw-node", "dataset",
            "--repo-root", str(tmp_path),
            "--dry-run",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "would" in out
