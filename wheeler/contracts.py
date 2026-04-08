"""Task output contracts for Wheeler's handoff system.

Contracts specify what a task must produce: node types, provenance links,
quality thresholds. Validated at reconvene to check task completion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

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
    for req in contract.required_nodes:
        checks += 1
        try:
            records = await backend.run_cypher(
                f"MATCH (n:{req.type}) WHERE n.session_id = $sid RETURN n.id AS id, n.confidence AS confidence",
                {"sid": session_id},
            )
            count = len(records)
            if count < req.min_count:
                violations.append(
                    f"Expected >= {req.min_count} {req.type} nodes, got {count}"
                )
            # Check confidence threshold for nodes that have it
            if req.confidence_min > 0:
                for rec in records:
                    conf = rec.get("confidence")
                    if conf is not None and conf < req.confidence_min:
                        violations.append(
                            f"{req.type} {rec['id']} confidence {conf:.2f} < {req.confidence_min:.2f}"
                        )
        except Exception as exc:
            violations.append(f"Failed to query {req.type} nodes: {exc}")

    # Check required links
    for req in contract.required_links:
        checks += 1
        try:
            records = await backend.run_cypher(
                f"MATCH (a:{req.from_type})-[:{req.relationship}]->(b:{req.to_type}) "
                "WHERE a.session_id = $sid RETURN a.id AS aid",
                {"sid": session_id},
            )
            if not records:
                violations.append(
                    f"No {req.from_type}-[{req.relationship}]->{req.to_type} links found"
                )
        except Exception as exc:
            violations.append(f"Failed to check {req.relationship} links: {exc}")

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
