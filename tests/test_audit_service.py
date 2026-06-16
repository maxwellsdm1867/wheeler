"""Unit tests for the wheeler-service-creator AUDITOR.

The auditor (``.claude/skills/wheeler-service-creator/assets/audit_service.py``)
is the mechanical half of the adversarial review: it checks a filled adapter for
data safety, two-sided provenance, the external-call failsafe, and the house
conventions. These tests pin two things: it PASSES the real shipped adapters (it
is calibrated, not noise), and it CATCHES the defects it claims to (an unsafe
teardown, a missing failsafe), so a regression in either direction is caught.

Skips cleanly when the skill is absent (mirrors test_scaffold_service.py).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".claude/skills/wheeler-service-creator/assets/audit_service.py"
SCAFFOLD = REPO_ROOT / ".claude/skills/wheeler-service-creator/assets/scaffold_service.py"

pytestmark = pytest.mark.skipif(
    not SCRIPT.exists(),
    reason="wheeler-service-creator skill not present in this checkout",
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _audit(provider: str, tool: str, root: Path = REPO_ROOT):
    mod = _load(SCRIPT, "audit_service")
    findings = mod.audit(provider, tool, root)
    return findings, [f for f in findings if f.level == "BLOCKER"]


# ---------------------------------------------------------------------------
# Calibration: the real shipped adapters must PASS (no blockers)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool", ["scholar-qa", "theorizer", "paper-finder", "semantic-scholar"]
)
def test_real_adapters_pass(tool):
    findings, blockers = _audit("asta", tool)
    assert blockers == [], f"{tool} should pass: {[str(b) for b in blockers]}"
    # And the audit actually ran meaningful checks (not a no-op).
    assert len(findings) >= 10


def test_real_adapter_data_safety_not_false_positive():
    # The scholar_qa test docstring legitimately mentions "DETACH DELETE" and
    # "corpus_id" in PROSE; the auditor must not flag that (only real cypher).
    _, blockers = _audit("asta", "scholar-qa")
    assert not any(b.check == "data-safety" for b in blockers)


# ---------------------------------------------------------------------------
# It CATCHES the defects it claims to (scaffold a clean adapter, then break it)
# ---------------------------------------------------------------------------


def _scaffold_clean(tmp_path: Path):
    ss = _load(SCAFFOLD, "scaffold_service_for_audit")
    c = ss.ServiceContract(
        provider="acme",
        tool="widget",
        raw_node="dataset",
        nodes=["Finding"],
        cli_invocation='acme run "$Q" -o /tmp/w.json',
    )
    ss.scaffold(c, tmp_path)
    return tmp_path


def test_catches_unsafe_service_scoped_teardown(tmp_path: Path):
    root = _scaffold_clean(tmp_path)
    test = root / "tests" / "integrations" / "acme" / "test_widget.py"
    test.write_text(
        test.read_text().replace(
            "MATCH (n) WHERE n.e2e_tag = $tag DETACH DELETE n",
            "MATCH (n) WHERE n.service = $svc DETACH DELETE n",
        )
    )
    _, blockers = _audit("acme", "widget", root)
    assert any(b.check == "data-safety" for b in blockers)


def test_catches_missing_failsafe(tmp_path: Path):
    root = _scaffold_clean(tmp_path)
    ing = root / "wheeler" / "integrations" / "acme" / "widget.py"
    ing.write_text(
        ing.read_text()
        .replace("outcome = job_outcome(doc)", "pass  # gate removed")
        .replace("mark_execution_failed", "noop")
    )
    _, blockers = _audit("acme", "widget", root)
    assert any(b.check == "failsafe" for b in blockers)


def test_catches_paper_was_generated_by(tmp_path: Path):
    root = _scaffold_clean(tmp_path)
    ing = root / "wheeler" / "integrations" / "acme" / "widget.py"
    # Inject the forbidden Paper-reference-entity violation.
    text = ing.read_text().replace(
        "    produced_ids: list[str] = []",
        '    produced_ids: list[str] = []\n'
        '    await _link_once(backend, config, paper_id, "WAS_GENERATED_BY", exec_id)',
    )
    ing.write_text(text)
    _, blockers = _audit("acme", "widget", root)
    assert any(
        b.check == "provenance" and "reference entit" in b.detail for b in blockers
    )


def test_catches_failsafe_imported_but_not_called(tmp_path: Path):
    # Importing mark_execution_failed but never CALLING it on the failure path is
    # not a real failsafe; the auditor requires the call form.
    root = _scaffold_clean(tmp_path)
    ing = root / "wheeler" / "integrations" / "acme" / "widget.py"
    # Remove every CALL but keep the import line.
    text = ing.read_text().replace(
        "await mark_execution_failed(", "await _noop_failed("
    )
    ing.write_text(text)
    _, blockers = _audit("acme", "widget", root)
    assert any(
        b.check == "failsafe" and "not called" in b.detail for b in blockers
    )


def test_catches_paper_was_generated_by_alt_varname(tmp_path: Path):
    # The reference-entity check catches paper-suggestive var names beyond
    # ``paper`` (e.g. ``pid``), not just the literal example.
    root = _scaffold_clean(tmp_path)
    ing = root / "wheeler" / "integrations" / "acme" / "widget.py"
    text = ing.read_text().replace(
        "    produced_ids: list[str] = []",
        '    produced_ids: list[str] = []\n'
        '    await _link_once(backend, config, pid, "WAS_GENERATED_BY", exec_id)',
    )
    ing.write_text(text)
    _, blockers = _audit("acme", "widget", root)
    assert any(
        b.check == "provenance" and "reference entit" in b.detail for b in blockers
    )


def test_catches_forbidden_provider_import(tmp_path: Path):
    root = _scaffold_clean(tmp_path)
    ing = root / "wheeler" / "integrations" / "acme" / "widget.py"
    # Assemble the forbidden import from fragments so this test file does not
    # itself carry the literal token the pre-commit hook blocks.
    forbidden = "import " + "anth" + "ropic"
    ing.write_text(forbidden + "\n" + ing.read_text())
    _, blockers = _audit("acme", "widget", root)
    assert any(b.check == "forbidden" for b in blockers)


def test_clean_scaffold_has_no_blockers_except_unfilled_parser(tmp_path: Path):
    # A freshly scaffolded (unfilled) adapter should already be data-safe and
    # carry the failsafe; the only gaps are WARNs (e.g. the parser is a stub),
    # never BLOCKERs. This is what makes "scaffold -> audit -> fill" safe.
    root = _scaffold_clean(tmp_path)
    _, blockers = _audit("acme", "widget", root)
    assert blockers == [], f"clean scaffold should have no blockers: {blockers}"
