"""Citation extraction (regex) and validation (Cypher provenance checks)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from wheeler.config import WheelerConfig

logger = logging.getLogger(__name__)
from wheeler.graph.schema import PREFIX_TO_LABEL

# Matches [F-3a2b], [PL-0012abcd], etc.
CITATION_PATTERN = re.compile(
    r"\[((?:PL|F|H|Q|E|A|D|P|C|T|W|N)-[0-9a-f]{4,8})\]"
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
    "Document": [("APPEARS_IN", "Finding|Paper|Analysis|Hypothesis")],
}


async def validate_citations(
    text: str, config: WheelerConfig
) -> list[CitationResult]:
    """Validate all citations in text against Neo4j.

    Batched for performance: single query checks all node existence,
    single query per label checks provenance rules.

    Returns partial results if Neo4j fails mid-validation — never crashes
    the caller. Citations that couldn't be checked get NOT_FOUND status.
    """
    node_ids = extract_citations(text)
    if not node_ids:
        return []

    from wheeler.graph.driver import get_async_driver
    driver = get_async_driver(config)
    results: list[CitationResult] = []

    # Separate valid IDs from unknown prefixes
    valid_ids: list[tuple[str, str]] = []  # (node_id, label)
    for node_id in node_ids:
        label = _label_from_id(node_id)
        if label is None:
            results.append(CitationResult(
                node_id=node_id,
                status=CitationStatus.NOT_FOUND,
                details=f"Unknown prefix: {_prefix_from_id(node_id)}",
            ))
        else:
            valid_ids.append((node_id, label))

    if not valid_ids:
        return results

    try:
        async with driver.session(database=config.neo4j.database) as session:
            # Step 1: Batch existence check — one query for all nodes
            by_label: dict[str, list[str]] = {}
            for node_id, label in valid_ids:
                by_label.setdefault(label, []).append(node_id)

            found_nodes: dict[str, dict] = {}
            for label, ids in by_label.items():
                result = await session.run(
                    f"MATCH (n:{label}) WHERE n.id IN $ids RETURN n.id AS id, n",
                    ids=ids,
                )
                records = [r async for r in result]
                for rec in records:
                    found_nodes[rec["id"]] = dict(rec["n"])

            # Step 2: Process each citation
            for node_id, label in valid_ids:
                if node_id not in found_nodes:
                    results.append(CitationResult(
                        node_id=node_id,
                        status=CitationStatus.NOT_FOUND,
                        label=label,
                        details=f"{label} node not found in graph",
                    ))
                    continue

                # Step 3: Provenance check — single query per rule
                prov_status = CitationStatus.VALID
                prov_detail = ""
                if label in _PROVENANCE_RULES:
                    for rel_pattern, target_pattern in _PROVENANCE_RULES[label]:
                        check = await session.run(
                            f"MATCH (n:{label} {{id: $id}})"
                            f"<-[:{rel_pattern}]-(t) "
                            f"WHERE any(lbl IN labels(t) WHERE lbl IN $targets) "
                            f"RETURN count(t) AS cnt",
                            id=node_id,
                            targets=target_pattern.split("|"),
                        )
                        rec = await check.single()
                        if not rec or rec["cnt"] == 0:
                            prov_status = CitationStatus.MISSING_PROVENANCE
                            prov_detail = (
                                f"{label} lacks required provenance: "
                                f"{rel_pattern} from {target_pattern}"
                            )

                # Step 4: Staleness check for Analysis nodes
                if prov_status == CitationStatus.VALID and label == "Analysis":
                    try:
                        from wheeler.graph.provenance import hash_file
                        node_data = found_nodes[node_id]
                        sp = node_data.get("script_path")
                        sh = node_data.get("script_hash")
                        if sp and sh:
                            p = Path(sp)
                            if not p.exists():
                                prov_status = CitationStatus.STALE
                                prov_detail = f"Script file not found: {sp}"
                            elif hash_file(p) != sh:
                                prov_status = CitationStatus.STALE
                                prov_detail = "Script has been modified since analysis ran"
                    except Exception:
                        pass

                results.append(CitationResult(
                    node_id=node_id,
                    status=prov_status,
                    label=label,
                    details=prov_detail,
                ))
    except Exception as exc:
        logger.warning("Citation validation failed mid-batch: %s", exc)
        # Graph failed mid-validation — mark unchecked citations as NOT_FOUND
        checked = {r.node_id for r in results}
        for node_id, label in valid_ids:
            if node_id not in checked:
                results.append(CitationResult(
                    node_id=node_id,
                    status=CitationStatus.NOT_FOUND,
                    label=label,
                    details="Graph unavailable during validation",
                ))
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
