"""Contracts for Wheeler plans and handoff tasks.

Two contract types coexist:

1. `PlanContract`: declarative fields on a research plan's frontmatter that
   tell `/wh:execute` what success looks like (output type, citation mode,
   validators to run, section for Document outputs). Parsed and enforced by
   the execute slash command at plan-execution time.

2. `TaskContract`: the older handoff contract used at `/wh:reconvene` to
   verify a background task's outputs (required node types, links, citation
   pass rate). Validated by `validate_contract` below.

The two are intentionally separate. PlanContract is a forward-looking
declaration ("here is how this plan should run"); TaskContract is a
backward-looking audit ("did the task produce what it promised").
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)


@dataclass
class NodeRequirement:
    """Expected output node type with quality thresholds."""
    type: str           # "Finding", "Hypothesis", etc.
    min_count: int = 1
    confidence_min: float = 0.0


@dataclass
class LinkRequirement:
    """Required provenance link between output nodes."""
    from_type: str
    relationship: str
    to_type: str


@dataclass
class TaskContract:
    """Output contract for a single handoff task."""
    task_id: str
    required_nodes: list[NodeRequirement] = field(default_factory=list)
    required_links: list[LinkRequirement] = field(default_factory=list)
    citation_pass_rate: float = 0.8
    must_reference: list[str] = field(default_factory=list)


@dataclass
class ContractResult:
    """Result of validating a task against its contract."""
    passed: bool
    violations: list[str] = field(default_factory=list)
    checks_run: int = 0

    @property
    def summary(self) -> str:
        if self.passed:
            return f"all {self.checks_run} checks passed"
        return f"{len(self.violations)} of {self.checks_run} checks failed"


# ---------------------------------------------------------------------------
# PlanContract: declarative plan-level fields, parsed from frontmatter.
# ---------------------------------------------------------------------------

# Allowed enum values. Anything outside these is rejected at parse time so
# typos in the plan frontmatter surface as errors instead of silently falling
# through to the default branch.
_OUTPUT_TYPES = frozenset({"document", "script", "dataset", "finding", "mixed"})
_CITATION_MODES = frozenset({"strict", "flexible", "none"})


@dataclass
class PlanContract:
    """Declarative contract on a research plan.

    All fields optional. Defaults match the historical "do analysis, log
    findings, flexible citations" behavior so plans without any contract
    fields keep working exactly as before.

    Fields:
        output_type: kind of artifact this plan produces.
            Drives which `add_*` tool /wh:execute calls at the end:
              - "document"  -> add_document (prose: writeup, synthesis)
              - "script"    -> add_script
              - "dataset"   -> add_dataset
              - "finding"   -> findings logged inline, no terminal artifact
              - "mixed"     -> no automatic terminal registration (default)
        citation_mode: how strictly to enforce [NODE_ID] citations.
              - "strict"    -> every factual claim must cite; validators
                               that fail halt artifact registration.
              - "flexible"  -> encouraged but not enforced (default).
              - "none"      -> citations not expected (pure code/data).
        validation: ordered list of validator names from VALIDATOR_REGISTRY
            to run after task completion, before artifact registration.
            Empty list = no validation. Unknown names produce a violation.
        section: passed as the `section` arg to `add_document` when
            output_type=="document". Ignored otherwise. Default "draft".
    """
    output_type: str = "mixed"
    citation_mode: str = "flexible"
    validation: list[str] = field(default_factory=list)
    section: str = "draft"

    @classmethod
    def from_frontmatter(cls, fm: dict[str, Any]) -> "PlanContract":
        """Build a contract from a plan's parsed YAML frontmatter.

        Missing fields fall through to defaults. Out-of-range enum values
        raise ValueError so typos surface immediately. Validator names are
        NOT validated here (unknown names get caught at run time so the
        registry can be extended without breaking older plans).
        """
        output_type = str(fm.get("output_type", "mixed"))
        if output_type not in _OUTPUT_TYPES:
            raise ValueError(
                f"PlanContract.output_type must be one of {sorted(_OUTPUT_TYPES)}, "
                f"got {output_type!r}"
            )
        citation_mode = str(fm.get("citation_mode", "flexible"))
        if citation_mode not in _CITATION_MODES:
            raise ValueError(
                f"PlanContract.citation_mode must be one of {sorted(_CITATION_MODES)}, "
                f"got {citation_mode!r}"
            )
        raw_validation = fm.get("validation") or []
        if not isinstance(raw_validation, list):
            raise ValueError(
                f"PlanContract.validation must be a list, got {type(raw_validation).__name__}"
            )
        return cls(
            output_type=output_type,
            citation_mode=citation_mode,
            validation=[str(v) for v in raw_validation],
            section=str(fm.get("section", "draft")),
        )

    @property
    def is_default(self) -> bool:
        """True if this contract is fully defaulted (no plan-level intent declared)."""
        return (
            self.output_type == "mixed"
            and self.citation_mode == "flexible"
            and not self.validation
            and self.section == "draft"
        )


# ---------------------------------------------------------------------------
# Validator registry: name -> async runner.
# ---------------------------------------------------------------------------

# Runner signature: (artifact_path | None, config) -> (ok, message).
# Validators that need a file (validate_citations) fail cleanly when path is
# None; validators that ignore the path (graph_consistency_check) accept None.
ValidatorRunner = Callable[
    [Path | None, WheelerConfig], Awaitable[tuple[bool, str]]
]


async def _run_validate_citations(
    artifact_path: Path | None, config: WheelerConfig
) -> tuple[bool, str]:
    """Validator: all [NODE_ID] citations in an artifact file resolve in the graph."""
    from wheeler.validation.citations import CitationStatus, validate_citations

    if artifact_path is None:
        return False, "validate_citations requires an artifact path"
    if not artifact_path.exists():
        return False, f"artifact not found: {artifact_path}"
    text = artifact_path.read_text()
    results = await validate_citations(text, config)
    bad = [r for r in results if r.status != CitationStatus.VALID]
    if bad:
        details = ", ".join(f"{r.node_id}({r.status.value})" for r in bad[:5])
        more = f" (+{len(bad) - 5} more)" if len(bad) > 5 else ""
        return False, f"{len(bad)} citation(s) failed: {details}{more}"
    return True, f"all {len(results)} citation(s) resolve"


async def _run_graph_consistency_check(
    artifact_path: Path | None, config: WheelerConfig
) -> tuple[bool, str]:
    """Validator: graph/JSON/synthesis trees are not drifted."""
    from wheeler.consistency import check_consistency

    report = await check_consistency(config)
    issues = (
        len(report.graph_only)
        + len(report.json_only)
        + len(report.synthesis_missing)
        + len(report.synthesis_orphaned)
    )
    if issues:
        return False, (
            f"{issues} consistency issue(s): "
            f"graph_only={len(report.graph_only)}, "
            f"json_only={len(report.json_only)}, "
            f"synthesis_missing={len(report.synthesis_missing)}, "
            f"synthesis_orphaned={len(report.synthesis_orphaned)}"
        )
    return True, f"all {report.total_graph} nodes consistent across layers"


VALIDATOR_REGISTRY: dict[str, ValidatorRunner] = {
    "validate_citations": _run_validate_citations,
    "graph_consistency_check": _run_graph_consistency_check,
}


async def run_plan_validators(
    contract: PlanContract,
    artifact_path: Path | None,
    config: WheelerConfig,
) -> ContractResult:
    """Run every validator named in `contract.validation` against the artifact.

    Returns a ContractResult aggregating successes and failures. Unknown
    validator names are recorded as violations (rather than raising) so a
    typo in one plan does not crash the whole execute pipeline.
    """
    violations: list[str] = []
    checks = 0
    for name in contract.validation:
        checks += 1
        runner = VALIDATOR_REGISTRY.get(name)
        if runner is None:
            violations.append(
                f"unknown validator {name!r} "
                f"(known: {sorted(VALIDATOR_REGISTRY)})"
            )
            continue
        try:
            ok, msg = await runner(artifact_path, config)
            if not ok:
                violations.append(f"{name}: {msg}")
        except Exception as exc:  # validator must never crash execute
            violations.append(f"{name} crashed: {exc}")
    return ContractResult(
        passed=len(violations) == 0,
        violations=violations,
        checks_run=checks,
    )


async def validate_contract(
    config: WheelerConfig,
    contract: TaskContract,
    session_id: str,
) -> ContractResult:
    """Validate task output against its contract.

    Queries the graph for nodes created in the given session,
    checks counts, confidence thresholds, relationship existence,
    and reference requirements.
    """
    from wheeler.tools.graph_tools import _get_backend

    backend = await _get_backend(config)
    violations: list[str] = []
    checks = 0

    # Check required node types
    for node_req in contract.required_nodes:
        checks += 1
        try:
            records = await backend.run_cypher(
                f"MATCH (n:{node_req.type}) WHERE n.session_id = $sid RETURN n.id AS id, n.confidence AS confidence",
                {"sid": session_id},
            )
            count = len(records)
            if count < node_req.min_count:
                violations.append(
                    f"Expected >= {node_req.min_count} {node_req.type} nodes, got {count}"
                )
            # Check confidence threshold for nodes that have it
            if node_req.confidence_min > 0:
                for rec in records:
                    conf = rec.get("confidence")
                    if conf is not None and conf < node_req.confidence_min:
                        violations.append(
                            f"{node_req.type} {rec['id']} confidence {conf:.2f} < {node_req.confidence_min:.2f}"
                        )
        except Exception as exc:
            violations.append(f"Failed to query {node_req.type} nodes: {exc}")

    # Check required links
    for link_req in contract.required_links:
        checks += 1
        try:
            records = await backend.run_cypher(
                f"MATCH (a:{link_req.from_type})-[:{link_req.relationship}]->(b:{link_req.to_type}) "
                "WHERE a.session_id = $sid RETURN a.id AS aid",
                {"sid": session_id},
            )
            if not records:
                violations.append(
                    f"No {link_req.from_type}-[{link_req.relationship}]->{link_req.to_type} links found"
                )
        except Exception as exc:
            violations.append(f"Failed to check {link_req.relationship} links: {exc}")

    # Check must_reference (output nodes reference specific inputs)
    for ref_id in contract.must_reference:
        checks += 1
        try:
            records = await backend.run_cypher(
                "MATCH (n)-[]->(m {id: $mid}) WHERE n.session_id = $sid RETURN n.id AS nid",
                {"sid": session_id, "mid": ref_id},
            )
            if not records:
                violations.append(f"No task output references {ref_id}")
        except Exception as exc:
            violations.append(f"Failed to check reference to {ref_id}: {exc}")

    return ContractResult(
        passed=len(violations) == 0,
        violations=violations,
        checks_run=checks,
    )
