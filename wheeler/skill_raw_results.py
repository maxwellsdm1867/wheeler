"""Discover skills for typed graph entities in otherwise unscoped raw results.

Scalar projections cannot establish resource identity or project membership.
Only actual Neo4j nodes (including path nodes) can activate a linked skill.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any

from neo4j.graph import Node, Path

from wheeler.models import PREFIX_TO_LABEL
from wheeler.skill_discovery import discover_skills

if TYPE_CHECKING:
    from wheeler.config import WheelerConfig
    from wheeler.skill_discovery import SkillReadBackend


async def discover_raw_result_skills(
    records: list[dict], config: WheelerConfig, backend: SkillReadBackend,
    *, max_values: int = 2000, max_depth: int = 12,
) -> dict:
    """Inspect bounded result values without changing the caller's result shape.

    Mapping keys, projected IDs, and node properties never become triggers.
    Namespace checks happen before IDs reach the project-scoped resolver, since
    different projects may legitimately have nodes with the same Wheeler ID.
    """
    ids: list[str] = []
    seen_ids: set[str] = set()
    seen_containers: set[int] = set()
    stack: list[tuple[Iterator[Any], int]] = [(iter(records), 0)]
    examined = 0
    truncated = False
    project_tag = config.neo4j.project_tag
    scoped = isinstance(project_tag, str) and bool(project_tag)

    while stack:
        iterator, depth = stack[-1]
        try:
            value = next(iterator)
        except StopIteration:
            stack.pop()
            continue
        if examined >= max_values:
            truncated = True
            break
        examined += 1
        if isinstance(value, Node):
            node_id = value.get("id")
            if not isinstance(node_id, str):
                continue
            prefix, separator, suffix = node_id.partition("-")
            label = PREFIX_TO_LABEL.get(prefix)
            if not separator or not suffix or label not in value.labels:
                continue
            if scoped and value.get("_wheeler_project") != project_tag:
                continue
            if node_id not in seen_ids:
                seen_ids.add(node_id)
                ids.append(node_id)
            continue
        if not isinstance(value, (Path, Mapping, list, tuple)):
            continue
        if id(value) in seen_containers:
            continue
        if depth >= max_depth:
            truncated = True
            continue
        seen_containers.add(id(value))
        if isinstance(value, Path):
            children = iter(value.nodes)
        elif isinstance(value, Mapping):
            children = iter(value.values())
        else:
            children = iter(value)
        stack.append((children, depth + 1))

    result = await discover_skills(ids, config, backend)
    result["linked_skills_coverage"] = (
        "Returned Neo4j nodes and path nodes with valid Wheeler IDs and labels, "
        "restricted to the configured project when set. Scalar projections and "
        "map IDs are not checked."
    )
    if not ids and records:
        result["linked_skills_status"] = "not_checked"
    if truncated:
        result["linked_skills_truncated"] = True
        result["linked_skills_status"] = "truncated"
    if records:
        result["linked_skills_guidance"] = (
            "Compare linked skill descriptions with your intent; read full instructions "
            "only when relevant. For projected or omitted resources, use show_node "
            "after confirming their identity in the current project."
        )
    return result
