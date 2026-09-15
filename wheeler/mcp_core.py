"""Wheeler Core MCP Server: graph health, status, context, gaps, node reads, cypher, schema, search, acts.

14 tools for reading and querying the knowledge graph, plus the act corpus.
Run: python -m wheeler.mcp_core
"""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP

from wheeler import acts as acts_corpus
from wheeler import config as wheeler_config
from wheeler.config import project_knowledge_dir
from wheeler.graph import context, schema
from wheeler.graph.cypher_guard import WRITE_KEYWORDS, is_read_only_cypher
from wheeler.tools import graph_tools
from wheeler.mcp_shared import (
    DISCLOSURE,
    _pointerize,
    _strip_empty,
    _trim_text,
    _config,
    _logged,
    _get_embedding_store,
    _extract_display_text,
    _request_logger,
    _verify_backend,
)

mcp = FastMCP(
    "wheeler_core",
    instructions="Graph infrastructure and semantic search: health checks, status, context, gaps, node reads, raw Cypher, schema init, search_findings and search_context (meaning-based, fuses semantic + keyword + fulltext + recency). Also serves Wheeler's acts (research workflows) via list_acts and get_act, so any host can run them from a single source. For typed keyword listings of a specific node type, use wheeler_query. For creating or modifying nodes, use wheeler_mutations.",
)


_PASSWORD_PRECEDENCE = (
    "Wheeler resolves the Neo4j password in precedence order: NEO4J_PASSWORD, then the "
    "OS keychain (wheeler login), then neo4j.password in wheeler.yaml, then the built-in "
    "default 'research-graph'."
)


def _neo4j_field_sources(config_path: Path | None) -> dict[str, dict[str, str]]:
    """Which layer supplied each Neo4j connection field.

    Reports the layer and its origin, never the values: a health report gets
    pasted into bug reports.
    """
    try:
        rows = wheeler_config.neo4j_sources(config_path)
    except Exception:
        return {}
    return {row.field: {"source": row.source, "origin": row.origin} for row in rows}


def _config_evidence(with_sources: bool = False) -> dict:
    """Report which config file is in effect, resolved the way load_config resolves it.

    Without this, an auth failure can only guess at which layer supplied the
    credential the database rejected.
    """
    config_path = wheeler_config.find_config_file()
    evidence: dict = {
        "config_file": str(config_path) if config_path else None,
        "config_source": (
            f"wheeler.yaml at {config_path}"
            if config_path
            else (
                "no wheeler.yaml found: settings come from NEO4J_* env vars, "
                "the OS keychain, or built-in defaults"
            )
        ),
    }
    if with_sources:
        evidence["neo4j_sources"] = _neo4j_field_sources(config_path)
    return evidence


def _diagnose_auth_failure(evidence: dict) -> dict:
    """Diagnose a rejected credential, naming the layer that actually supplied it."""
    config_file = evidence.get("config_file")
    sources = evidence.get("neo4j_sources") or _neo4j_field_sources(
        Path(config_file) if config_file else None
    )
    password = sources.get("password", {})
    layer = password.get("source", "")
    origin = password.get("origin", "")

    if layer == "env":
        supplied = f"the {origin} environment variable"
        action = (
            f"Check the password exported in {origin}, or unset it so the keychain "
            "and wheeler.yaml take effect."
        )
    elif layer == "keychain":
        supplied = f"the OS keychain ({origin})"
        action = (
            f"Re-store the credential for {origin} with `wheeler login`, or set "
            "neo4j.profile to the slot this project should connect through."
        )
    elif layer == "yaml":
        supplied = f"neo4j.password in {origin}"
        action = (
            f"Check the neo4j.password field in {origin} against the password the "
            "Neo4j database was created with."
        )
    elif layer == "default":
        supplied = "Wheeler's built-in default"
        if config_file:
            action = (
                f"{config_file} does not set neo4j.password, so the built-in default "
                "was used. Set it there, run `wheeler login`, or export NEO4J_PASSWORD."
            )
        else:
            action = (
                "Supply the real password: run `wheeler login`, export NEO4J_PASSWORD, "
                "or start from the project root whose wheeler.yaml sets neo4j.password."
            )
    else:
        supplied = "a layer that could not be determined (source reporting failed)"
        action = (
            "Check NEO4J_PASSWORD, then the credential stored by `wheeler login`, "
            "then neo4j.password in wheeler.yaml."
        )

    if config_file:
        where = f"Resolved config file: {config_file}."
    else:
        where = "No config file was found, so wheeler.yaml supplied nothing on this run."

    cause = f"The Neo4j server answered and rejected the credential. The password came from {supplied}."
    if layer != "yaml":
        cause = f"{cause} {where}"

    return {
        "diagnosis": "Neo4j authentication failed",
        "cause": cause,
        "remediation": f"{action} {_PASSWORD_PRECEDENCE}",
        "fix": [action, _PASSWORD_PRECEDENCE],
    }


def _diagnose_health_error(error_msg: str, evidence: dict | None = None) -> dict:
    """Return structured diagnosis for common Neo4j connection errors.

    Always includes 'remediation' as a string (backward-compatible).
    Adds 'diagnosis', 'cause', and 'fix' fields for richer LLM context.
    """
    msg = error_msg.lower()
    if "unauthorized" in msg or "authentication" in msg:
        return _diagnose_auth_failure(
            evidence if evidence is not None else _config_evidence(with_sources=True)
        )
    if "refused" in msg or "unavailable" in msg or "connection" in msg or "failed to establish" in msg:
        return {
            "diagnosis": "Cannot connect to Neo4j",
            "cause": "Neo4j is not running, or another process is using port 7687.",
            "remediation": (
                "Open Neo4j Desktop and click Start on your database (look for "
                "the green Running indicator), or run: docker start wheeler-neo4j. "
                "Check for port conflicts: lsof -i :7687"
            ),
            "fix": [
                "Open Neo4j Desktop and click Start on your database (look for the green Running indicator).",
                "If using Docker: docker start wheeler-neo4j",
                "If using Homebrew: brew services start neo4j",
                "Check for port conflicts: lsof -i :7687",
            ],
        }
    return {
        "remediation": (
            "Open Neo4j Desktop and start the database, "
            "or run: docker start wheeler-neo4j"
        ),
    }


# --- Graph health & status ---


@mcp.tool()
@_logged
async def graph_health() -> dict:
    """Check Wheeler knowledge graph database connectivity and report diagnostics.

    Returns backend type, connection status, database name, node counts,
    and any errors. Use this to verify the graph is working before
    starting research work that depends on it.
    """
    result: dict = {
        "backend": _config.graph.backend,
        "database": _config.neo4j.database,
        "status": "unknown",
        "node_count": 0,
        "error": None,
    }
    result.update(_config_evidence())
    try:
        counts = await schema.get_status(_config)
        if counts.get("_status") == "offline":
            result["status"] = "offline"
            result["error"] = counts.get("_error", "Unknown error")
            result["blocking"] = True
            evidence = _config_evidence(with_sources=True)
            result.update(evidence)
            result.update(_diagnose_health_error(str(counts.get("_error", "")), evidence))
        else:
            node_counts: dict[str, int] = {
                k: v for k, v in counts.items() if not k.startswith("_")
            }
            total = sum(node_counts.values())
            result["status"] = "connected"
            result["node_count"] = total
            result["node_counts"] = node_counts
    except Exception as exc:
        result["status"] = "offline"
        result["error"] = str(exc)
        result["blocking"] = True
        evidence = _config_evidence(with_sources=True)
        result.update(evidence)
        result.update(_diagnose_health_error(str(exc), evidence))

    # Check knowledge/ directory
    knowledge_path = project_knowledge_dir(_config)
    if knowledge_path.exists():
        json_files = list(knowledge_path.glob("*.json"))
        result["knowledge_files"] = len(json_files)
    else:
        result["knowledge_files"] = 0
        if result["status"] == "connected":
            result["warnings"] = ["knowledge/ directory does not exist -- run /wh:init"]

    # Triple-write drift surfacing: compare graph, JSON, and synthesis
    # inventories so drift is reported at routine health checks instead
    # of only on a manual graph_consistency_check.
    if result["status"] == "connected":
        try:
            from wheeler.consistency import check_consistency, summarize_drift

            drift = summarize_drift(await check_consistency(_config))
            result["drift"] = drift
            if drift["exceeds_threshold"]:
                result.setdefault("warnings", []).append(
                    f"Triple-write drift: {drift['total_divergent']} nodes diverge "
                    "across graph/JSON/synthesis layers "
                    f"(threshold {drift['threshold']}). "
                    "Run graph_consistency_check for details."
                )
        except Exception as exc:
            result["drift"] = {"error": str(exc)}

    return result


@mcp.tool()
@_logged
async def graph_status() -> dict:
    """Return node counts per label in the Wheeler knowledge graph."""
    counts = await schema.get_status(_config)
    if counts.get("_status") == "offline":
        return {
            "status": "offline",
            "error": counts.get("_error", "Unknown error"),
            "blocking": True,
            "remediation": (
                "Open Neo4j Desktop and start the database, "
                "or run: docker start wheeler-neo4j"
            ),
            "node_counts": {k: v for k, v in counts.items()
                           if not k.startswith("_")},
        }
    return counts


@mcp.tool()
@_logged
async def graph_context(topic: str = "") -> str:
    """Fetch size-limited context from the Wheeler knowledge graph (recent findings, open questions, hypotheses).

    When topic is provided, filters results to those matching the topic
    (case-insensitive substring match on descriptions/statements).
    Leave empty to get all recent context.
    """
    return await context.fetch_context(_config, topic=topic)


@mcp.tool()
@_logged
async def graph_gaps(limit: int = 10, offset: int = 0, summary: bool = False) -> dict:
    """Find gaps in the Wheeler knowledge graph: unlinked questions, unsupported hypotheses, stale analyses, near-duplicates.

    The response always includes a counts dict with true per-bucket
    totals; total_gaps is the sum of those totals.

    Args:
        limit: Max items per gap bucket (default 10)
        offset: Items to skip per bucket, for pagination (default 0)
        summary: When true, cap each bucket at 3 items (compact output
                 for large graphs)
    """
    result = await graph_tools.execute_tool(
        "graph_gaps",
        {"limit": limit, "offset": offset, "summary": summary},
        _config,
    )
    gaps = json.loads(result)

    # Enrich with near-duplicate detection from embeddings (if available)
    try:
        store = _get_embedding_store()
        pairs = store.find_similar_pairs(threshold=0.85)
        pair_cap = 3 if summary else 10
        gaps["potential_duplicates"] = [
            {
                "node_a": {"id": a.node_id, "label": a.label, "text": (a.text or "")[:300]},
                "node_b": {"id": b.node_id, "label": b.label, "text": (b.text or "")[:300]},
                "similarity": round(score, 4),
            }
            for a, b, score in pairs[:pair_cap]
        ]
        gaps["total_gaps"] = gaps.get("total_gaps", 0) + len(gaps["potential_duplicates"])
    except (ImportError, Exception):
        # Embeddings not available: skip duplicate detection silently
        pass

    return gaps


# --- Node read (filesystem) ---


@mcp.tool()
@_logged
async def show_node(
    node_id: str = "",
    node_ids: list[str] | None = None,
    fields: str = "",
    include_change_log: bool = False,
    neighbors: bool = False,
    version: int | None = None,
    if_changed_since: str = "",
) -> dict:
    """Read one or many Wheeler knowledge graph nodes with their full content.

    Listings return pointers; this is the deep read. Args:
      node_id: one id (e.g. "F-3a2b"). Or node_ids for several in ONE call;
        the result is then {"nodes": [...], "missing": [...], "count"}.
      fields: comma-separated fields to return ("description,confidence");
        default returns every non-empty field.
      include_change_log: per-field edit history, omitted by default.
      neighbors: also return the ONE-HOP neighbourhood as pointer rows:
        [{id, rel, direction, type, headline, content_version, moved}]. `moved`
        is true when the neighbour's content changed after the edge was made
        (edge pinned version differs from the node's current version).
      version: read an earlier content version (1 = as created). The current
        version is in every result as content_version.
      if_changed_since: a content_hash or "v3" you saw earlier. If the node is
        unchanged you get back only {id, content_version, content_hash,
        changed: false} instead of the content you already have.

    Reads the node's JSON file and falls back to the graph node when the file
    is missing, so a node that exists in Neo4j is never reported as not found.
    """
    ids = [i for i in (node_ids or []) if i] or ([node_id] if node_id else [])
    if not ids:
        return {"error": "Pass node_id or node_ids"}
    wanted = {f.strip() for f in fields.split(",") if f.strip()} if fields else None

    found: list[dict] = []
    missing: list[str] = []
    for nid in ids:
        if version is not None and not node_ids:
            data = _read_node_version(nid, version)
        else:
            data = await _read_node_any_layer(nid)
        if data is None:
            missing.append(nid)
            continue
        if if_changed_since and not node_ids:
            token = if_changed_since.strip().lower()
            cur_hash = str(data.get("content_hash") or "")
            cur_v = int(data.get("content_version") or 1)
            same = (token == cur_hash.lower()) or (token.lstrip("v").isdigit() and int(token.lstrip("v")) == cur_v)
            if same:
                return {"id": nid, "content_version": cur_v, "content_hash": cur_hash, "changed": False}
            data["changed"] = True
        if not include_change_log:
            data.pop("change_log", None)
        data = _strip_empty(data)
        if wanted:
            data = {k: v for k, v in data.items() if k in wanted or k in ("id", "type")}
        if neighbors:
            data["neighbors"] = await _neighbors_of(nid)
        found.append(data)

    if node_ids:
        return {"nodes": found, "missing": missing, "count": len(found)}
    if not found:
        if version is not None:
            return {"error": f"Node {ids[0]} has no version {version}"}
        return {"error": f"Node {ids[0]} not found"}
    return found[0]


def _read_node_version(nid: str, version: int) -> dict | None:
    """A specific content version from knowledge/ (current file or a snapshot)."""
    from wheeler.knowledge import versions as _versions

    try:
        data = _versions.read_version(project_knowledge_dir(_config), nid, version)
    except FileNotFoundError:
        return None
    current = None
    try:
        from wheeler.knowledge import store

        current = store.read_node(project_knowledge_dir(_config), nid).content_version
    except Exception:
        pass
    data["is_current"] = current is not None and current == version
    return data


async def _neighbors_of(nid: str) -> list[dict]:
    """One hop from *nid* as pointer rows, with the edge's pinned version check."""
    from wheeler.mcp_shared import _headline

    tag = _config.neo4j.project_tag
    where = " WHERE n._wheeler_project = $ptag AND m._wheeler_project = $ptag" if tag else ""
    params: dict = {"id": nid}
    if tag:
        params["ptag"] = tag
    try:
        backend = await graph_tools._get_backend(_config)
        rows = await backend.run_cypher(
            "MATCH (n {id: $id})-[r]-(m)" + where + " "
            "RETURN type(r) AS rel, startNode(r).id = $id AS outgoing, m.id AS id, "
            "labels(m)[0] AS type, coalesce(m.title, '') AS title, "
            "coalesce(m.description, m.statement, m.question, m.content, '') AS text, "
            "coalesce(m.content_version, 1) AS content_version, "
            "r.source_version AS source_version, r.target_version AS target_version "
            "ORDER BY rel, m.id LIMIT 200",
            params,
        )
    except Exception as exc:
        return [{"error": f"neighbour query failed: {exc}"}]
    out = []
    for r in rows:
        outgoing = bool(r.get("outgoing"))
        pinned = r.get("target_version") if outgoing else r.get("source_version")
        row: dict = {
            "id": r["id"],
            "rel": r["rel"],
            "direction": "out" if outgoing else "in",
            "type": r.get("type") or "",
            "headline": _headline({"title": r.get("title") or "", "text": r.get("text") or ""}),
            "content_version": r.get("content_version") or 1,
        }
        if pinned is not None and int(pinned) != int(row["content_version"]):
            row["moved"] = True
        out.append(row)
    return out


async def _read_node_any_layer(nid: str) -> dict | None:
    """The node as a dict from its JSON file, else from the graph, else None."""
    from wheeler.portability import is_portable, resolve

    data: dict | None = None
    try:
        from wheeler.knowledge import store

        model = store.read_node(project_knowledge_dir(_config), nid)
        data = model.model_dump()
    except (FileNotFoundError, ImportError):
        data = None
    except Exception:
        data = None

    if data is None:
        # The JSON layer can lag or be missing (a node written on another
        # machine, a repair pending). The graph is the index of record, so read
        # it rather than sending the caller away with "not found".
        label = schema.PREFIX_TO_LABEL.get(nid.split("-", 1)[0])
        if label:
            try:
                backend = await graph_tools._get_backend(_config)
                node = await backend.get_node(label, nid)
            except Exception:
                node = None
            if node:
                data = {k: v for k, v in dict(node).items() if not k.startswith("_")}
                data.setdefault("id", nid)
                data.setdefault("type", label)
                data["source"] = "graph"
        if data is None:
            return None

    stored = data.get("path") or ""
    if stored:
        # `path` is what the caller opens, so it is resolved for this machine;
        # `stored_path` keeps the machine-independent form the node holds. An
        # unresolvable value (a root this computer does not configure) is left
        # portable rather than turned into a local path that points nowhere.
        data["stored_path"] = stored
        if is_portable(stored):
            resolved = resolve(stored, _config.resolved_roots)
            data["path"] = str(resolved) if resolved is not None else stored
            data["path_resolved"] = resolved is not None
    return data


# --- Entity resolution (read-only) ---


@mcp.tool()
@_logged
async def propose_merge(node_id_a: str, node_id_b: str) -> dict:
    """Compare two knowledge graph nodes and propose a merge.

    Returns which node to keep (more relationships), field conflicts,
    and relationships that would be redirected. Read-only, no changes made.
    Use before execute_merge to preview the operation.
    """
    from wheeler.merge import propose_merge as _propose
    return await _propose(_config, node_id_a, node_id_b)


# --- Raw Cypher ---


@mcp.tool()
@_logged
async def run_cypher(query: str, limit: int = 100) -> dict:
    """Run a read-only Cypher query against the Wheeler knowledge graph database.

    Use for ad-hoc research graph exploration: relationship traversal, path queries,
    aggregations, or anything the higher-level tools don't cover.

    Examples:
        "MATCH (f:Finding)-[:SUPPORTS]->(h:Hypothesis) RETURN f.id, h.statement"
        "MATCH p=(a:Analysis)-[:GENERATED]->(f:Finding) RETURN p"
        "MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count ORDER BY count DESC"

    Args:
        query: Cypher query string. Read-only: CREATE, MERGE, DELETE, SET,
            REMOVE, DROP, CALL, FOREACH and LOAD are all refused, matched as
            whole words. CALL is refused even for read-only procedures such as
            fulltext queries, since a procedure name does not reveal whether it
            writes; use search_findings for fulltext. This query is NOT
            project-scoped, unlike every query_* tool.
        limit: maximum rows returned (default 100). When the query yields
            more, the result carries truncated=true and total_rows; add a
            WHERE or LIMIT to the query rather than raising this blindly.
    """
    # Block write operations. One shared rule (graph/cypher_guard.py), also used
    # by the backend to decide replay safety. The previous local copy scanned
    # for keywords with literal trailing spaces, so `CREATE(n:Finding {id:'x'})`
    # and `CALL apoc.*` passed while `MATCH (d:Dataset {name: $n})` was refused
    # ("DATASET " contains "SET "). Do not reintroduce a text scan here.
    if not is_read_only_cypher(query):
        return {
            "error": (
                "Write operations not allowed via run_cypher. Use Wheeler's mutation "
                "tools (add_finding, link_nodes, etc.) instead. Refused keywords: "
                + ", ".join(WRITE_KEYWORDS)
                + ". CALL is refused even for read-only procedures, because a "
                "procedure's name does not reveal whether it writes."
            )
        }

    try:
        backend = await graph_tools._get_backend(_config)
        records = await backend.run_cypher(query)
        total = len(records)
        if limit and total > limit:
            return {
                "results": records[:limit],
                "count": limit,
                "truncated": True,
                "total_rows": total,
            }
        return {"results": records, "count": total}
    except Exception as exc:
        return {"error": str(exc), "results": [], "count": 0}


# --- Schema ---


@mcp.tool()
@_logged
async def init_schema() -> dict:
    """Apply Wheeler knowledge graph constraints and indexes to Neo4j. Returns count of applied statements."""
    applied = await schema.init_schema(_config)
    return {"applied": len(applied)}


# --- Semantic search ---


@mcp.tool()
@_logged
async def search_findings(
    query: str,
    limit: int = 10,
    label: str = "",
    mode: str = "multi",
    full: bool = False,
) -> dict:
    """Search across Wheeler knowledge graph nodes for research context retrieval.

    Combines semantic (embedding similarity), keyword (graph queries),
    temporal (recency), and fulltext (Neo4j index) channels via Reciprocal
    Rank Fusion for better recall than any single channel alone. Use for
    finding related research nodes when linking new entries or exploring
    existing knowledge.

    Args:
        query: Natural language search query
        limit: Maximum results (default 10)
        label: Optional filter by node type (Finding, Hypothesis, OpenQuestion, Paper, Dataset, Document)
        mode: Retrieval mode -- "multi" (default, all channels), "semantic" (embeddings only),
              "keyword" (graph keyword only), "temporal" (most recent only), "fulltext" (Neo4j fulltext index only)
        full: return each hit's complete text instead of the first 240 chars
              (use show_node on the hits you need rather than this)
    """
    try:
        from wheeler.search.retrieval import multi_search

        results = await multi_search(
            query, _config, limit=limit, label=label, mode=mode,
        )
        payload = {
            "results": [
                {
                    "node_id": r.get("id", ""),
                    "label": r.get("type", ""),
                    "text": (_extract_display_text(r) if full else _trim_text(_extract_display_text(r))),
                    "score": r.get("rrf_score", 0.0),
                }
                for r in results
            ],
            "count": len(results),
            "query": query,
            "mode": mode,
        }
        if DISCLOSURE == "pointer" and not full:
            return await _pointerize(payload, _config)
        return payload
    except Exception as exc:
        return {
            "error": f"Search failed: {exc}",
            "results": [],
            "count": 0,
        }


@mcp.tool()
@_logged
async def search_context(
    query: str,
    limit: int = 5,
    hops: int = 2,
    label: str = "",
    max_related: int = 20,
) -> dict:
    """Search the knowledge graph and expand results via graph traversal.

    Returns seed nodes from search plus their graph neighborhood:
    provenance chains (2 hops via USED/WAS_GENERATED_BY/WAS_DERIVED_FROM),
    semantic links (1 hop via SUPPORTS/CONTRADICTS), and other relationships.

    Use this instead of search_findings when you need the full experimental
    context around results, not just the results themselves. Especially
    useful for "why" and "how" questions that need provenance chains.

    Args:
        query: Natural language search query
        limit: Maximum seed results (default 5)
        hops: Maximum provenance chain depth (default 2)
        label: Optional filter by node type
        max_related: cap on related nodes returned (default 20; 0 = no cap).
            When the neighbourhood is larger the result carries
            truncated_related=true and total_related still reports the full
            count; relationships are filtered to the nodes kept.
    """
    from wheeler.search.retrieval import multi_search, expand_search_results

    try:
        seeds = await multi_search(query, _config, limit=limit, label=label)
        expanded = await expand_search_results(
            seeds, _config, max_hops_prov=hops,
        )
        related = expanded.get("related_nodes") or []
        if max_related and len(related) > max_related:
            # One real call returned 94 related nodes (36 KB); the seeds' immediate
            # neighbourhood is what the caller reads, the tail is noise it pays for.
            kept = related[:max_related]
            keep_ids = {n.get("id") for n in kept} | {n.get("id") for n in expanded.get("seed_nodes") or []}
            expanded["related_nodes"] = kept
            expanded["relationships"] = [
                r for r in expanded.get("relationships") or []
                if r.get("source") in keep_ids and r.get("target") in keep_ids
            ]
            expanded["truncated_related"] = True
        if DISCLOSURE == "pointer":
            return await _pointerize(expanded, _config)
        return expanded
    except Exception as exc:
        return {
            "error": f"Search context failed: {exc}",
            "seed_nodes": [],
            "related_nodes": [],
        }


@mcp.tool()
@_logged
async def index_node(node_id: str, label: str, text: str) -> dict:
    """Add or update a Wheeler knowledge graph node's semantic embedding for search.

    Call this after creating or updating a research node to make it searchable.
    The embedding is generated from the text content using a local model.

    Args:
        node_id: The node ID (e.g., F-3a2b)
        label: Node type (Finding, Hypothesis, etc.)
        text: The text content to embed
    """
    try:
        store = _get_embedding_store()
        store.add(node_id, label, text)
        store.save()
        return {"status": "indexed", "node_id": node_id, "label": label}
    except ImportError:
        return {"error": "Semantic search not available. Install with: pip install wheeler[search]"}
    except Exception as exc:
        return {"error": f"Indexing failed: {exc}"}


# --- Act corpus ---
#
# Reads, not mutations, so they do NOT route through execute_tool(): that rule
# exists to keep the triple-write wiring in one place and applies to writes.
# Serving act bodies here is what lets a second host (Codex) run the same acts
# without a second copy of their content.


@mcp.tool()
@_logged
async def list_acts() -> dict:
    """List Wheeler's /wh:* acts: the research workflows this project ships.

    Each entry carries the act's name, short id, one-line description,
    argument hint, enforcement mode (chat / write / execute), and
    orchestration shape (none / skill-dispatch / subagents). Call get_act
    to fetch the full instructions for one of them.
    """
    return {
        "acts": [act.summary() for act in acts_corpus.load_acts()],
        "count": len(acts_corpus.load_acts()),
    }


@mcp.tool()
@_logged
async def get_act(name: str, host: str = "") -> dict:
    """Fetch the full instructions for one Wheeler /wh:* act.

    The body is the act's system prompt, returned verbatim and identical for
    every host. `orchestration_note` is the only host-specific part: it says
    how to achieve this act's orchestration shape on the calling host, and is
    empty for acts that orchestrate nothing. Read it as an appendix to the body.

    Args:
        name: Act name, with or without the prefix ("chat" or "wh:chat")
        host: Calling host, "claude" (default) or "codex"
    """
    act = acts_corpus.find_act(name)
    if act is None:
        return {
            "error": f"Unknown act: {name!r}",
            "known_acts": list(acts_corpus.act_ids()),
        }
    try:
        resolved_host = acts_corpus.normalize_host(host)
    except ValueError as exc:
        return {
            "error": str(exc),
            "supported_hosts": list(acts_corpus.HOSTS),
        }
    return {
        "name": act.name,
        "act_id": act.act_id,
        "description": act.description,
        "argument_hint": act.argument_hint,
        "mode": act.mode,
        "orchestration": act.orchestration,
        "allowed_tools": list(act.allowed_tools),
        "host": resolved_host,
        "body": act.body,
        "orchestration_note": acts_corpus.orchestration_note(act, resolved_host),
    }


# --- Request log ---


@mcp.tool()
@_logged
async def request_log_summary() -> dict:
    """Return summary stats of recent Wheeler MCP tool calls (latency, error rate, call counts)."""
    return _request_logger.summary()


# --- Entry point ---


def main():
    import asyncio

    from wheeler.graph.driver import invalidate_async_driver

    asyncio.run(_verify_backend())
    invalidate_async_driver()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
