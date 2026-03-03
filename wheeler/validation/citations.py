"""Citation extraction (regex) and validation (Cypher provenance checks)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from neo4j import AsyncGraphDatabase

from wheeler.config import WheelerConfig
from wheeler.graph.schema import PREFIX_TO_LABEL

# Matches [F-3a2b], [PL-0012abcd], etc.
CITATION_PATTERN = re.compile(
    r"\[((?:PL|F|H|Q|E|A|D|P|C|T)-[0-9a-f]{4,8})\]"
)


class CitationStatus(Enum):
    VALID = "valid"
    NOT_FOUND = "not_found"
    MISSING_PROVENANCE = "missing_provenance"
    STALE = "stale"


@dataclass
class CitationResult:
    node_id: str
    status: CitationStatus
    label: str | None = None
    details: str = ""


def extract_citations(text: str) -> list[str]:
    """Extract all node ID citations from text using regex.

    Returns a deduplicated list of node IDs (without brackets).
    """
    return list(dict.fromkeys(CITATION_PATTERN.findall(text)))


def _prefix_from_id(node_id: str) -> str:
    """Extract the prefix part of a node ID (e.g., 'F' from 'F-3a2b')."""
    return node_id.split("-", 1)[0]


def _label_from_id(node_id: str) -> str | None:
    """Map a node ID to its Neo4j label."""
    prefix = _prefix_from_id(node_id)
    return PREFIX_TO_LABEL.get(prefix)


# Provenance rules: what relationships a node label must have to be considered
# properly grounded. Label → list of (relationship, target_label) that should exist.
_PROVENANCE_RULES: dict[str, list[tuple[str, str]]] = {
    "Finding": [("GENERATED|PRODUCED", "Analysis|Experiment")],
    "Analysis": [("USED_DATA", "Dataset")],
    "Hypothesis": [("SUPPORTS|CONTRADICTS", "Finding")],
}


async def validate_citations(
    text: str, config: WheelerConfig
) -> list[CitationResult]:
    """Validate all citations in text against Neo4j.

    For each citation:
    1. Check the node exists
    2. Check provenance relationships (label-specific rules)
    """
    node_ids = extract_citations(text)
    if not node_ids:
        return []

    driver = AsyncGraphDatabase.driver(
        config.neo4j.uri,
        auth=(config.neo4j.username, config.neo4j.password),
    )
    results: list[CitationResult] = []
    try:
        async with driver.session(database=config.neo4j.database) as session:
            for node_id in node_ids:
                label = _label_from_id(node_id)
                if label is None:
                    results.append(CitationResult(
                        node_id=node_id,
                        status=CitationStatus.NOT_FOUND,
                        details=f"Unknown prefix: {_prefix_from_id(node_id)}",
                    ))
                    continue

                # Check node exists
                result = await session.run(
                    f"MATCH (n:{label} {{id: $id}}) RETURN n",
                    id=node_id,
                )
                record = await result.single()
                if record is None:
                    results.append(CitationResult(
                        node_id=node_id,
                        status=CitationStatus.NOT_FOUND,
                        label=label,
                        details=f"{label} node not found in graph",
                    ))
                    continue

                # Check provenance if rules exist for this label
                prov_status = CitationStatus.VALID
                prov_detail = ""
                if label in _PROVENANCE_RULES:
                    for rel_pattern, target_pattern in _PROVENANCE_RULES[label]:
                        rels = rel_pattern.split("|")
                        targets = target_pattern.split("|")
                        found = False
                        for rel in rels:
                            for target in targets:
                                check = await session.run(
                                    f"MATCH (n:{label} {{id: $id}})"
                                    f"<-[:{rel}]-(t:{target}) "
                                    f"RETURN count(t) AS cnt",
                                    id=node_id,
                                )
                                rec = await check.single()
                                if rec and rec["cnt"] > 0:
                                    found = True
                                    break
                            if found:
                                break
                        if not found:
                            prov_status = CitationStatus.MISSING_PROVENANCE
                            prov_detail = (
                                f"{label} lacks required provenance: "
                                f"{rel_pattern} from {target_pattern}"
                            )

                # Check staleness for Analysis nodes
                if prov_status == CitationStatus.VALID and label == "Analysis":
                    try:
                        from wheeler.graph.provenance import hash_file
                        node_data = record["n"]
                        sp = node_data.get("script_path")
                        sh = node_data.get("script_hash")
                        if sp and sh:
                            p = Path(sp)
                            if not p.exists():
                                prov_status = CitationStatus.STALE
                                prov_detail = f"Script file not found: {sp}"
                            elif hash_file(p) != sh:
                                prov_status = CitationStatus.STALE
                                prov_detail = f"Script has been modified since analysis ran"
                    except Exception:
                        pass  # staleness check failure shouldn't block validation

                results.append(CitationResult(
                    node_id=node_id,
                    status=prov_status,
                    label=label,
                    details=prov_detail,
                ))
    finally:
        await driver.close()
    return results


def keyword_overlap_score(text: str, description: str) -> float:
    """Simple keyword overlap between response text and node description.

    Returns a score between 0.0 and 1.0.
    """
    if not description:
        return 0.0
    text_words = set(text.lower().split())
    desc_words = set(description.lower().split())
    if not desc_words:
        return 0.0
    overlap = text_words & desc_words
    return len(overlap) / len(desc_words)
