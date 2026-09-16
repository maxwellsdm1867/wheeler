"""Progressive disclosure of accepted skills attached to encountered nodes.

Graph links establish relevance; canonical JSON and artifact hashes establish
that a completed, usable revision exists on this machine. Reads never activate
candidate lessons or silently fall back to superseded instructions.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import TYPE_CHECKING, Protocol

from wheeler.config import project_knowledge_dir

if TYPE_CHECKING:
    from wheeler.config import WheelerConfig


class SkillReadBackend(Protocol):
    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]: ...


# Only these structured result rows carry encountered node identities. Never
# infer triggers from citations in prose, roll-ups, or arbitrary nested metadata.
QUERY_RESULT_KEYS = {
    "query_findings": "findings", "query_hypotheses": "hypotheses",
    "query_open_questions": "questions", "query_datasets": "datasets",
    "query_papers": "papers", "query_documents": "documents",
    "query_plans": "plans", "query_notes": "notes", "query_scripts": "scripts",
    "query_executions": "executions", "query_review_queue": "items",
}

logger = logging.getLogger(__name__)

_CONSISTENT_FIELDS = (
    "skill_name", "skill_description", "skill_version", "skill_state",
    "skill_supersedes", "skill_source_ids", "skill_target_ids", "path", "hash",
    "skill_capture_key",
)

_MODEL_CONTEXT_DEFAULTS = {
    "skill_author_model": "unknown", "skill_author_environment": "unknown",
    "skill_tested_model": "", "skill_tested_environment": "",
    "skill_benchmark_result_ids": [],
}


def _usable_skill(skill: dict, config: WheelerConfig, *, require_receipt: bool = True) -> tuple[dict | None, str]:
    """Check the canonical copy and bounded artifact without disclosing its body."""
    from wheeler.knowledge.store import read_node
    from wheeler.portability import resolve

    try:
        canonical = read_node(project_knowledge_dir(config), skill["id"]).model_dump()
        if canonical.get("type") != "Document" or any(
            canonical.get(key) != skill.get(key) for key in _CONSISTENT_FIELDS
        ):
            return None, "canonical_metadata_mismatch"
        if any(canonical.get(key, default) != skill.get(key, default)
               for key, default in _MODEL_CONTEXT_DEFAULTS.items()):
            return None, "canonical_metadata_mismatch"
        if canonical.get("stale") or skill.get("stale"):
            return None, "stale"
        if not skill.get("path") or not skill.get("hash"):
            return None, "missing_artifact_metadata"
        path = resolve(skill["path"], config.resolved_roots)
        if path is None:
            return None, "unresolved_artifact_root"
        if not path.is_absolute():
            path = config.resolved_project_root / path
        # Graph acceptance alone cannot certify all local writes succeeded.
        # Capture publishes this receipt last, after its required links and
        # graph/JSON/synthesis writes have completed successfully.
        if require_receipt:
            try:
                with path.with_name("capture-complete.json").open("rb") as handle:
                    receipt = json.loads(handle.read(4097))
                if not skill.get("skill_capture_key") or receipt != {
                    "node_id": skill["id"],
                    "capture_key": skill["skill_capture_key"],
                    "hash": skill["hash"],
                }:
                    return None, "incomplete_capture"
            except (OSError, ValueError, TypeError):
                return None, "incomplete_capture"
        # Capture produces small SKILL.md files. Bound reads even if a path is
        # later replaced with a huge file; failed validation is visible.
        with path.open("rb") as handle:
            body = handle.read(256 * 1024 + 1)
        if len(body) > 256 * 1024:
            return None, "artifact_too_large"
        expected = skill["hash"].removeprefix("sha256:")
        if hashlib.sha256(body).hexdigest() != expected:
            return None, "artifact_hash_mismatch"
        return {
            "id": skill["id"],
            "name": skill["skill_name"],
            "description": skill["skill_description"],
            "version": skill["skill_version"],
            "path": str(path.resolve()),
            "target_ids": skill["skill_target_ids"],
            "author_model": skill.get("skill_author_model", "unknown"),
            "tested_model": skill.get("skill_tested_model", ""),
        }, ""
    except FileNotFoundError:
        return None, "missing_local_copy"
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        logger.debug("Linked skill validation failed", exc_info=True)
        return None, "invalid_local_copy"


async def discover_skills(
    node_ids: list[str],
    config: WheelerConfig,
    backend: SkillReadBackend | None = None,
    *,
    limit: int = 20,
    node_limit: int = 200,
    offset: int = 0,
    inventory: bool = False,
) -> dict:
    """Return descriptions of active skills linked to a batch of encountered IDs.

    Full instructions stay in the returned SKILL.md paths. An empty complete
    result means no linked accepted skills; unavailable and truncated explicitly
    distinguish failures or partial discovery from that absence.
    """
    ids = list(dict.fromkeys(nid for nid in node_ids if isinstance(nid, str) and nid))
    key = "skill_inventory" if inventory else "linked_skills"
    result: dict = {key: [], f"{key}_status": "complete"}
    if not ids:
        return result
    limit = max(1, min(limit, 100))
    node_limit = max(1, min(node_limit, 1000))
    if offset < 0:
        raise ValueError("Skill offset must be non-negative")
    truncated = len(ids) > node_limit
    try:
        if backend is None:
            from wheeler.tools.graph_tools import _get_backend

            backend = await _get_backend(config)
        params: dict = {"node_ids": ids[:node_limit], "limit": limit + 1, "offset": offset}
        project_tag = config.neo4j.project_tag
        scoped = isinstance(project_tag, str) and bool(project_tag)
        skill_scope = " AND skill._wheeler_project = $ptag AND target._wheeler_project = $ptag" if scoped else ""
        lineage_scope = " AND revision._wheeler_project = $ptag" if scoped else ""
        if scoped:
            params["ptag"] = project_tag
        current = (
            "NOT EXISTS { MATCH lineage=(successor:Document)-[:WAS_DERIVED_FROM*1..]->(skill) "
            "WHERE successor.skill_state IN ['accepted', 'retracted'] "
            + ("AND successor._wheeler_project = $ptag " if scoped else "")
            +
            "AND all(revision IN nodes(lineage) WHERE revision:Document "
            "AND revision.skill_name = skill.skill_name "
            "AND revision.skill_target_ids = skill.skill_target_ids" + lineage_scope + ") "
            "AND all(edge IN relationships(lineage) "
            "WHERE startNode(edge).skill_supersedes = endNode(edge).id) }"
        )
        records = await backend.run_cypher(
            "MATCH (skill:Document)-[:APPLIES_TO]->(target) "
            "WHERE (target.id IN $node_ids OR skill.id IN $node_ids) "
            "AND skill.skill_name <> ''"
            + skill_scope
            + ("" if inventory else " AND skill.skill_state = 'accepted' AND " + current)
            + " RETURN skill, collect(DISTINCT target.id) AS matched_target_ids, "
            + current + " AS is_current ORDER BY skill.id SKIP $offset LIMIT $limit",
            params,
        )
        truncated = truncated or len(records) > limit
        unavailable: list[dict] = []
        for record in records[:limit]:
            skill = dict(record["skill"])
            item, reason = await asyncio.to_thread(
                _usable_skill, skill, config,
                require_receipt=not inventory or skill.get("skill_state") == "accepted",
            )
            if item is None:
                unavailable.append({"id": skill.get("id", ""), "reason": reason})
                if inventory:
                    # Keep the identity visible for deduplication/repair, but
                    # do not offer an unvalidated local file as instructions.
                    item = {"id": skill.get("id", ""), "name": skill.get("skill_name", ""),
                            "description": skill.get("skill_description", ""),
                            "version": skill.get("skill_version", 0),
                            "target_ids": skill.get("skill_target_ids", []),
                            "unavailable_reason": reason}
            if item is not None:
                item["matched_target_ids"] = record.get("matched_target_ids", [])
                if inventory:
                    item.update(state=skill.get("skill_state", ""), supersedes=skill.get("skill_supersedes", ""),
                                active=not reason and skill.get("skill_state") == "accepted" and bool(record.get("is_current")))
                result[key].append(item)
        if unavailable:
            result[f"{key}_unavailable"] = unavailable
            result[f"{key}_status"] = "unavailable"
        if truncated:
            result[f"{key}_truncated"] = True
            result[f"{key}_status"] = "truncated"
        if len(records) > limit:
            # Offset counts accepted graph records, including unusable local
            # copies, so a damaged entry cannot strand subsequent valid skills.
            result[f"{key}_next_page"] = {
                "node_ids": ids[:node_limit], "skills_only": True,
                "skill_offset": offset + limit,
                **({"skill_inventory": True} if inventory else {}),
            }
            result[f"{key}_guidance"] = (
                "More linked descriptions remain. Call show_node with the exact "
                f"{key}_next_page arguments before assuming no skill applies. "
                "Pages are ordered by skill ID; restart at offset 0 if skills change."
            )
        if len(ids) > node_limit:
            result[f"{key}_unchecked_node_count"] = len(ids) - node_limit
            result[f"{key}_scope_guidance"] = (
                f"Only the first {node_limit} unique encountered IDs were checked. "
                f"Use show_node(skills_only=true{', skill_inventory=true' if inventory else ''}) on the remaining artifact IDs "
                "in batches of at most 200, then follow each batch's next page."
            )
        if inventory:
            result["skill_inventory_guidance"] = (
                "Writer inventory, not activation. Review state and supersedes before updating. "
                "Candidates need endorsement; retracted history must not be reinstated silently. "
                + result.get("skill_inventory_guidance", "")
            )
        return result
    except Exception:
        logger.debug("Linked skill discovery unavailable", exc_info=True)
        return {**result, f"{key}_status": "unavailable"}


async def enrich_query_result(
    payload: dict, result_key: str, config: WheelerConfig,
    backend: SkillReadBackend | None = None, *, id_key: str = "id",
) -> dict:
    """Enrich a known node-bearing response without walking arbitrary content."""
    if payload.get("error"):
        return payload
    rows = payload.get(result_key)
    if not isinstance(rows, list):
        return {**payload, "linked_skills": [], "linked_skills_status": "unavailable"}
    ids = [row[id_key] for row in rows if isinstance(row, dict)
           and isinstance(row.get(id_key), str) and row[id_key]]
    discovery = await discover_skills(ids, config, backend)
    if len(ids) != len(rows):
        discovery["linked_skills_status"] = "unavailable"
        discovery["linked_skills_coverage"] = "Some returned rows lack a usable node identity."
    return {**payload, **discovery}


async def enrich_gap_result(
    payload: dict, config: WheelerConfig, backend: SkillReadBackend | None = None,
) -> dict:
    """Discover for returned gap rows and duplicate endpoints, not incidental IDs.

    The MCP wrapper adds capped duplicate pairs after the typed gap query, so
    it calls this on the final envelope. Direct dispatch callers use the same
    helper for the ordinary gap buckets.
    """
    if payload.get("error"):
        return payload
    rows: list = []
    malformed = False
    for key in (
        "unlinked_questions", "unsupported_hypotheses", "executions_without_outputs",
        "unreported_findings", "orphaned_papers",
    ):
        bucket = payload.get(key, [])
        if isinstance(bucket, list):
            rows.extend(bucket)
        else:
            malformed = True
    pairs = payload.get("potential_duplicates", [])
    if isinstance(pairs, list):
        for pair in pairs:
            if isinstance(pair, dict):
                rows.extend([pair.get("node_a"), pair.get("node_b")])
            else:
                malformed = True
    else:
        malformed = True
    enriched = await enrich_query_result({"rows": rows}, "rows", config, backend)
    discovery = {key: value for key, value in enriched.items() if key.startswith("linked_skills")}
    if malformed:
        discovery["linked_skills_status"] = "unavailable"
        discovery["linked_skills_coverage"] = "Some returned gap rows lack a usable node identity."
    return {**payload, **discovery}


def format_skill_context(discovery: dict, *, max_chars: int = 2400) -> str:
    """Compact descriptions for text context. Full bodies are never injected."""
    skills = discovery.get("linked_skills", [])
    status = discovery.get("linked_skills_status", "unavailable")
    if not skills and status == "complete":
        return ""
    lines = ["### Linked skills (consider applicability; read only when relevant)"]
    read_guidance = "Use show_node on a selected skill ID to find its full file and version context."
    recovery = "use show_node(node_ids=[encountered IDs], skills_only=true) for complete descriptors and paging."
    tail_budget = len(read_guidance) + len(f"Skill discovery is unavailable; {recovery}") + 2
    for skill in skills:
        # Applicability exclusions can occur anywhere in the description. Keep
        # the complete descriptor or explicitly report that it was omitted.
        line = f"- [{skill['id']}] {skill['name']}: {skill['description']}"
        if sum(len(s) + 1 for s in lines) + len(line) > max_chars - tail_budget:
            status = "truncated"
            break
        lines.append(line)
    lines.append(read_guidance)
    if status != "complete":
        lines.append(f"Skill discovery is {status}; {recovery}")
    return "\n".join(lines)
