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


def _usable_skill(skill: dict, config: WheelerConfig) -> tuple[dict | None, str]:
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
) -> dict:
    """Return descriptions of active skills linked to a batch of encountered IDs.

    Full instructions stay in the returned SKILL.md paths. An empty complete
    result means no linked accepted skills; unavailable and truncated explicitly
    distinguish failures or partial discovery from that absence.
    """
    ids = list(dict.fromkeys(nid for nid in node_ids if isinstance(nid, str) and nid))
    result: dict = {"linked_skills": [], "linked_skills_status": "complete"}
    if not ids:
        return result
    limit = max(1, min(limit, 100))
    node_limit = max(1, min(node_limit, 1000))
    truncated = len(ids) > node_limit
    try:
        if backend is None:
            from wheeler.tools.graph_tools import _get_backend

            backend = await _get_backend(config)
        params: dict = {"node_ids": ids[:node_limit], "limit": limit + 1}
        project_tag = config.neo4j.project_tag
        scoped = isinstance(project_tag, str) and bool(project_tag)
        skill_scope = " AND skill._wheeler_project = $ptag AND target._wheeler_project = $ptag" if scoped else ""
        successor_scope = " AND successor._wheeler_project = $ptag" if scoped else ""
        if scoped:
            params["ptag"] = project_tag
        records = await backend.run_cypher(
            "MATCH (skill:Document)-[:APPLIES_TO]->(target) "
            "WHERE (target.id IN $node_ids OR skill.id IN $node_ids) "
            "AND skill.skill_state = 'accepted' AND skill.skill_name <> ''"
            + skill_scope
            + " AND NOT EXISTS { MATCH (successor:Document) "
            "WHERE successor.skill_supersedes = skill.id "
            "AND successor.skill_state IN ['accepted', 'retracted']"
            + successor_scope
            + " } RETURN skill, collect(DISTINCT target.id) AS matched_target_ids "
            "ORDER BY skill.id LIMIT $limit",
            params,
        )
        truncated = truncated or len(records) > limit
        unavailable: list[dict] = []
        for record in records[:limit]:
            skill = dict(record["skill"])
            item, reason = await asyncio.to_thread(_usable_skill, skill, config)
            if item is None:
                unavailable.append({"id": skill.get("id", ""), "reason": reason})
            else:
                item["matched_target_ids"] = record.get("matched_target_ids", [])
                result["linked_skills"].append(item)
        if unavailable:
            result["linked_skills_unavailable"] = unavailable
            result["linked_skills_status"] = "unavailable"
        if truncated:
            result["linked_skills_truncated"] = True
            result["linked_skills_status"] = "truncated"
        return result
    except Exception:
        logger.debug("Linked skill discovery unavailable", exc_info=True)
        return {**result, "linked_skills_status": "unavailable"}


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


def format_skill_context(discovery: dict, *, max_chars: int = 2400) -> str:
    """Compact descriptions for text context. Full bodies are never injected."""
    skills = discovery.get("linked_skills", [])
    status = discovery.get("linked_skills_status", "unavailable")
    if not skills and status == "complete":
        return ""
    lines = ["### Linked skills (consider applicability; read only when relevant)"]
    for skill in skills:
        line = f"- [{skill['id']}] {skill['name']}: {skill['description'][:240]}"
        if sum(len(s) + 1 for s in lines) + len(line) > max_chars - 180:
            status = "truncated"
            break
        lines.append(line)
    lines.append("Use show_node on a selected skill ID to find its full file and version context.")
    if status != "complete":
        lines.append(f"Skill discovery is {status}; this is not evidence that no other skills apply.")
    return "\n".join(lines)
