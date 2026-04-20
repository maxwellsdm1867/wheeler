"""Entity resolution: propose and execute node merges.

Two-phase merge:
  Phase 1 (propose): compare nodes, compute merged state, list relationship redirects
  Phase 2 (execute): graph transaction for redirects + delete, then atomic file operations
"""

from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime, timezone

from wheeler.config import WheelerConfig
from wheeler.models import PREFIX_TO_LABEL, title_for_node

logger = logging.getLogger(__name__)


async def propose_merge(
    config: WheelerConfig,
    node_id_a: str,
    node_id_b: str,
) -> dict:
    """Compare two nodes and propose which to keep.

    Keeps the node with more graph relationships. Returns field
    conflicts, relationships to redirect, and proposed merged metadata.
    """
    from wheeler.tools.graph_tools import _get_backend
    from wheeler.knowledge.store import read_node

    backend = await _get_backend(config)
    knowledge_dir = Path(config.knowledge_path)

    # Load both nodes
    try:
        model_a = read_node(knowledge_dir, node_id_a)
        model_b = read_node(knowledge_dir, node_id_b)
    except FileNotFoundError as exc:
        return {"error": f"Node not found: {exc}"}

    if model_a.type != model_b.type:
        return {"error": f"Cannot merge different types: {model_a.type} vs {model_b.type}"}

    # Count relationships for each
    label = model_a.type
    count_a = await _count_relationships(backend, label, node_id_a)
    count_b = await _count_relationships(backend, label, node_id_b)

    # Keep the one with more relationships (tie: keep earlier created)
    if count_a > count_b:
        keep_id, merge_from_id = node_id_a, node_id_b
        keep_model, merge_model = model_a, model_b
    elif count_b > count_a:
        keep_id, merge_from_id = node_id_b, node_id_a
        keep_model, merge_model = model_b, model_a
    else:
        # Tie: keep earlier created
        if model_a.created <= model_b.created:
            keep_id, merge_from_id = node_id_a, node_id_b
            keep_model, merge_model = model_a, model_b
        else:
            keep_id, merge_from_id = node_id_b, node_id_a
            keep_model, merge_model = model_b, model_a

    # Find relationships to redirect
    rels_to_redirect = await _get_relationships(backend, label, merge_from_id)

    # Identify field conflicts
    conflicts = _find_conflicts(keep_model, merge_model)

    return {
        "keep": keep_id,
        "merge_from": merge_from_id,
        "label": label,
        "keep_relationships": count_a if keep_id == node_id_a else count_b,
        "merge_from_relationships": count_b if keep_id == node_id_a else count_a,
        "relationships_to_redirect": rels_to_redirect,
        "field_conflicts": conflicts,
        "keep_title": title_for_node(keep_model),
        "merge_from_title": title_for_node(merge_model),
    }


async def execute_merge(
    config: WheelerConfig,
    keep_id: str,
    merge_from_id: str,
) -> dict:
    """Execute a node merge with two-phase commit.

    Phase 1: Prepare (validate, compute merged state, write temp files)
    Phase 2: Commit (redirect relationships, delete merge_from, atomic file ops)
    """
    from wheeler.tools.graph_tools import _get_backend
    from wheeler.knowledge.store import read_node
    from wheeler.knowledge.store import delete_node as delete_knowledge_file
    from wheeler.knowledge.render import render_synthesis
    from wheeler.models import ChangeEntry

    backend = await _get_backend(config)
    knowledge_dir = Path(config.knowledge_path)
    synthesis_dir = Path(config.synthesis_path)

    # --- Phase 1: Prepare ---
    try:
        keep_model = read_node(knowledge_dir, keep_id)
        merge_model = read_node(knowledge_dir, merge_from_id)
    except FileNotFoundError as exc:
        return {"error": f"Node not found: {exc}", "status": "failed"}

    if keep_model.type != merge_model.type:
        return {"error": "Type mismatch", "status": "failed"}

    label = keep_model.type

    # Merge metadata into keep_model
    _merge_metadata(keep_model, merge_model)

    # Record merge in change log
    now = datetime.now(timezone.utc).isoformat()
    keep_model.change_log.append(ChangeEntry(
        timestamp=now,
        action="merged",
        changes={"merged_from": [merge_from_id, keep_id]},
        actor="entity_resolution",
        reason=f"merged duplicate {merge_from_id}",
    ))
    keep_model.updated = now

    # Write merged state to temp files
    tmp_json = knowledge_dir / f"{keep_id}.json.merge-tmp"
    tmp_json.write_text(keep_model.model_dump_json(indent=2), encoding="utf-8")

    merged_synthesis = render_synthesis(keep_model)
    tmp_synth = synthesis_dir / f"{keep_id}.md.merge-tmp"
    synthesis_dir.mkdir(parents=True, exist_ok=True)
    tmp_synth.write_text(merged_synthesis, encoding="utf-8")

    # --- Phase 2: Commit ---
    actions = []

    # Step 1: Redirect relationships from merge_from to keep
    redirected = await _redirect_relationships(backend, label, keep_id, merge_from_id)
    actions.append({"step": "redirect_relationships", "count": redirected})

    # Step 2: Delete merge_from from graph (DETACH DELETE)
    prefix = merge_from_id.split("-", 1)[0]
    merge_label = PREFIX_TO_LABEL.get(prefix, label)
    try:
        await backend.delete_node(merge_label, merge_from_id)
        actions.append({"step": "delete_graph_node", "status": "ok"})
    except Exception as exc:
        # Rollback: remove temp files
        tmp_json.unlink(missing_ok=True)
        tmp_synth.unlink(missing_ok=True)
        return {"error": f"Graph delete failed: {exc}", "status": "failed", "actions": actions}

    # Step 3: Atomic file renames
    target_json = knowledge_dir / f"{keep_id}.json"
    tmp_json.rename(target_json)
    actions.append({"step": "update_keep_json", "status": "ok"})

    target_synth = synthesis_dir / f"{keep_id}.md"
    tmp_synth.rename(target_synth)
    actions.append({"step": "update_keep_synthesis", "status": "ok"})

    # Step 4: Delete merge_from files
    try:
        delete_knowledge_file(knowledge_dir, merge_from_id)
        actions.append({"step": "delete_merge_json", "status": "ok"})
    except Exception:
        actions.append({"step": "delete_merge_json", "status": "skipped"})

    try:
        synth_path = synthesis_dir / f"{merge_from_id}.md"
        if synth_path.exists():
            synth_path.unlink()
        actions.append({"step": "delete_merge_synthesis", "status": "ok"})
    except Exception:
        actions.append({"step": "delete_merge_synthesis", "status": "skipped"})

    # Step 5: Update embedding for keep node
    try:
        from wheeler.search.embeddings import EmbeddingStore
        store = EmbeddingStore(config.search.store_path)
        store.load()
        store.remove(merge_from_id)
        store.add(keep_id, label, title_for_node(keep_model))
        store.save()
        actions.append({"step": "update_embeddings", "status": "ok"})
    except (ImportError, Exception):
        actions.append({"step": "update_embeddings", "status": "skipped"})

    return {
        "status": "merged",
        "keep": keep_id,
        "merged_from": merge_from_id,
        "relationships_redirected": redirected,
        "actions": actions,
    }


async def _count_relationships(backend, label: str, node_id: str) -> int:
    """Count total relationships (in + out) for a node."""
    try:
        records = await backend.run_cypher(
            f"MATCH (n:{label} {{id: $id}})-[r]-() RETURN count(r) AS cnt",
            {"id": node_id},
        )
        return records[0]["cnt"] if records else 0
    except Exception:
        return 0


async def _get_relationships(backend, label: str, node_id: str) -> list[dict]:
    """Get all relationships for a node (for redirect planning)."""
    rels = []
    try:
        # Outgoing
        out = await backend.run_cypher(
            f"MATCH (n:{label} {{id: $id}})-[r]->(m) "
            "RETURN type(r) AS rel, m.id AS target, labels(m)[0] AS tlabel",
            {"id": node_id},
        )
        for rec in out:
            rels.append({"direction": "out", "relationship": rec["rel"],
                         "other_id": rec["target"], "other_label": rec["tlabel"]})

        # Incoming
        inc = await backend.run_cypher(
            f"MATCH (m)-[r]->(n:{label} {{id: $id}}) "
            "RETURN type(r) AS rel, m.id AS source, labels(m)[0] AS slabel",
            {"id": node_id},
        )
        for rec in inc:
            rels.append({"direction": "in", "relationship": rec["rel"],
                         "other_id": rec["source"], "other_label": rec["slabel"]})
    except Exception:
        pass
    return rels


async def _redirect_relationships(
    backend, label: str, keep_id: str, merge_from_id: str,
) -> int:
    """Redirect all relationships from merge_from to keep.

    Neo4j CREATE does not support dynamic relationship types, so we
    query existing relationships and recreate them one by one.
    """
    keep_prefix = keep_id.split("-", 1)[0]
    keep_label = PREFIX_TO_LABEL.get(keep_prefix, label)
    merge_prefix = merge_from_id.split("-", 1)[0]
    merge_label = PREFIX_TO_LABEL.get(merge_prefix, label)

    redirected = 0

    # Outgoing: (merge_from)-[r]->(target) => (keep)-[r]->(target)
    try:
        out_rels = await backend.run_cypher(
            f"MATCH (n:{merge_label} {{id: $id}})-[r]->(m) "
            "WHERE m.id <> $keep "
            "RETURN type(r) AS rel, m.id AS tid, labels(m)[0] AS tlabel",
            {"id": merge_from_id, "keep": keep_id},
        )
        for rec in out_rels:
            try:
                await backend.run_cypher(
                    f"MATCH (a:{keep_label} {{id: $keep}}), (b:{rec['tlabel']} {{id: $tid}}) "
                    f"CREATE (a)-[:{rec['rel']}]->(b)",
                    {"keep": keep_id, "tid": rec["tid"]},
                )
                redirected += 1
            except Exception:
                logger.warning("Failed to redirect outgoing %s to %s", rec["rel"], rec["tid"])
    except Exception:
        pass

    # Incoming: (source)-[r]->(merge_from) => (source)-[r]->(keep)
    try:
        in_rels = await backend.run_cypher(
            f"MATCH (m)-[r]->(n:{merge_label} {{id: $id}}) "
            "WHERE m.id <> $keep "
            "RETURN type(r) AS rel, m.id AS sid, labels(m)[0] AS slabel",
            {"id": merge_from_id, "keep": keep_id},
        )
        for rec in in_rels:
            try:
                await backend.run_cypher(
                    f"MATCH (a:{rec['slabel']} {{id: $sid}}), (b:{keep_label} {{id: $keep}}) "
                    f"CREATE (a)-[:{rec['rel']}]->(b)",
                    {"sid": rec["sid"], "keep": keep_id},
                )
                redirected += 1
            except Exception:
                logger.warning("Failed to redirect incoming %s from %s", rec["rel"], rec["sid"])
    except Exception:
        pass

    return redirected


def _find_conflicts(keep, merge) -> list[dict]:
    """Find fields where the two nodes have different non-empty values."""
    conflicts = []
    # Check common content fields
    for field in ("description", "statement", "question", "title", "content",
                  "confidence", "status", "priority", "path"):
        keep_val = getattr(keep, field, None)
        merge_val = getattr(merge, field, None)
        if keep_val and merge_val and keep_val != merge_val:
            conflicts.append({"field": field, "keep_value": keep_val, "merge_value": merge_val})
    # Tags
    keep_tags = set(getattr(keep, "tags", []))
    merge_tags = set(getattr(merge, "tags", []))
    if merge_tags - keep_tags:
        conflicts.append({"field": "tags", "keep_value": sorted(keep_tags), "merge_value": sorted(merge_tags)})
    return conflicts


def _merge_metadata(keep, merge) -> None:
    """Merge metadata from merge node into keep node (in-place).

    Strategy: keep's values take precedence. Union tags.
    Take higher confidence. Keep earlier created date.
    """
    # Union tags
    keep_tags = set(getattr(keep, "tags", []))
    merge_tags = set(getattr(merge, "tags", []))
    keep.tags = sorted(keep_tags | merge_tags)

    # Higher confidence
    keep_conf = getattr(keep, "confidence", 0)
    merge_conf = getattr(merge, "confidence", 0)
    if hasattr(keep, "confidence") and merge_conf > keep_conf:
        keep.confidence = merge_conf

    # Earlier created date
    if merge.created and keep.created and merge.created < keep.created:
        keep.created = merge.created

    # Higher tier wins (reference > generated)
    if merge.tier == "reference" and keep.tier == "generated":
        keep.tier = "reference"
