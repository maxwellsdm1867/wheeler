#!/usr/bin/env python
"""Experiment harness: how much of a node should a listing return by default?

One invocation runs one disclosure level (``full``, ``trimmed`` or ``pointer``)
over the selected tasks. The level is only an environment variable,
``WHEELER_DISCLOSURE``, passed to the MCP servers; the model is never told
which level is active.

Per level run:
  1. create ``runs/<UTC ts>-<level>/project/``: the fixture files, a scratch
     ``wheeler.yaml`` with a unique ``neo4j.project_tag`` and a read-only
     ``.mcp.json`` (core + query servers, no mutations server)
  2. seed the whole fixture graph into that tag through ``execute_tool``
     (nodes, then ``link_nodes`` edges, then a title pass that stamps
     ``updated`` in a designed order), once for all tasks in the run
  3. for each task and repeat: launch ``claude -p`` headlessly on the
     subscription, parse the stream-json transcript, score the ANSWER line
     against the gold resolved to real node ids, write ``t<k>-r<n>/results.json``
  4. write ``level_summary.json`` and, unless ``--keep``, delete every node
     with the tag

Run from the worktree root with the worktree first on PYTHONPATH::

    PYTHONPATH=$PWD .venv/bin/python evals/disclosure/run.py --level pointer --tasks 1 --plan
    PYTHONPATH=$PWD .venv/bin/python evals/disclosure/run.py --check-gold
    PYTHONPATH=$PWD .venv/bin/python evals/disclosure/run.py --level trimmed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[1]
PYTHON = WORKTREE / ".venv" / "bin" / "python"
FIXTURE = HERE / "fixture"
FILES = FIXTURE / "files"
RUNS = HERE / "runs"

LEVELS = ("full", "trimmed", "pointer")
DISCLOSURE_ENV = "WHEELER_DISCLOSURE"

# Local experiment database. Isolation is by project_tag, never by database.
NEO4J = {
    "uri": "bolt://localhost:7717",
    "username": "neo4j",
    "password": "research-graph",
    "database": "neo4j",
}

CORE_PREFIX = "mcp__wheeler_core__"
QUERY_PREFIX = "mcp__wheeler_query__"

PROMPT_HEAD = (
    "You are answering a question about the Wheeler knowledge graph of this project. "
    "Use the Wheeler MCP tools. Prefer the fewest calls that answer correctly; read a "
    "node's full content only when you need it."
)


# ---------------------------------------------------------------------------
# Paths, config, caches
# ---------------------------------------------------------------------------


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def assert_worktree_import() -> None:
    """Refuse to run if the shared venv's editable install shadows this worktree."""
    import wheeler

    got = Path(wheeler.__file__).resolve()
    if WORKTREE not in got.parents:
        sys.exit(
            f"wheeler imports from {got}, not from {WORKTREE}. "
            f"Run with PYTHONPATH={WORKTREE}."
        )


def reset_wheeler_caches() -> None:
    """Drop the module-level backend cache and the async driver.

    Both are process-wide singletons; the async driver is bound to whichever
    event loop created it, and every ``asyncio.run`` here opens a fresh loop.
    """
    import wheeler.tools.graph_tools as gt
    from wheeler.graph.driver import invalidate_async_driver

    if hasattr(gt, "reset_backend_cache"):
        gt.reset_backend_cache()
    else:  # pragma: no cover - older attribute spelling
        for name in ("_backend_cache", "_backend_instance"):
            if hasattr(gt, name):
                setattr(gt, name, {} if name == "_backend_cache" else None)
    invalidate_async_driver()


def build_config(project: Path, tag: str):
    from wheeler.config import Neo4jConfig, SearchConfig, WheelerConfig

    return WheelerConfig(
        neo4j=Neo4jConfig(**NEO4J, project_tag=tag),
        search=SearchConfig(enabled=False),
        project_root=str(project),
    )


def wheeler_yaml(tag: str) -> str:
    return (
        "# Scratch project for the progressive-disclosure experiment.\n"
        "neo4j:\n"
        f"  uri: \"{NEO4J['uri']}\"\n"
        f"  username: \"{NEO4J['username']}\"\n"
        f"  password: \"{NEO4J['password']}\"\n"
        f"  database: \"{NEO4J['database']}\"\n"
        f"  project_tag: \"{tag}\"\n"
        "search:\n"
        "  enabled: false\n"
        "project_root: \".\"\n"
        "knowledge_path: \"knowledge\"\n"
        "synthesis_path: \"synthesis\"\n"
    )


def server_env(level: str) -> dict[str, str]:
    return {
        "PYTHONPATH": str(WORKTREE),
        DISCLOSURE_ENV: level,
        # Belt and braces so a server can never resolve to another graph: the
        # keychain layer outranks wheeler.yaml, and env outranks the keychain.
        "WHEELER_NO_KEYCHAIN": "1",
        "NEO4J_URI": NEO4J["uri"],
        "NEO4J_USERNAME": NEO4J["username"],
        "NEO4J_PASSWORD": NEO4J["password"],
        "NEO4J_DATABASE": NEO4J["database"],
    }


def mcp_json(level: str) -> dict:
    """Read-only server set: core (show_node, search, cypher) and query."""
    env = server_env(level)
    servers = {
        f"wheeler_{name}": {
            "type": "stdio",
            "command": str(PYTHON),
            "args": ["-m", f"wheeler.mcp_{name}"],
            "env": env,
        }
        for name in ("core", "query")
    }
    return {"mcpServers": servers}


def subprocess_env(project: Path, level: str) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        # Runs use the claude CLI on the subscription: drop any direct API credential.
        if not (k.startswith("ANTHROPIC") and k.endswith("_API_KEY"))
    }
    # A claude launched from inside a Claude Code session refuses to start
    # while the parent's marker is present.
    env.pop("CLAUDECODE", None)
    env.update(server_env(level))
    env["WHEELER_PROJECT_ROOT"] = str(project)
    return env


# ---------------------------------------------------------------------------
# Fixture, project preparation and seeding
# ---------------------------------------------------------------------------


def load_graph() -> dict:
    return json.loads((FIXTURE / "graph.json").read_text())


def load_tasks() -> dict:
    return json.loads((FIXTURE / "tasks.json").read_text())


def prepare_project(run_dir: Path, tag: str, level: str) -> Path:
    project = run_dir / "project"
    shutil.copytree(FILES, project)
    (project / "wheeler.yaml").write_text(wheeler_yaml(tag))
    (project / ".mcp.json").write_text(json.dumps(mcp_json(level), indent=2) + "\n")
    return project


class SeedError(RuntimeError):
    pass


async def _seed(cfg, graph: dict, project: Path) -> dict:
    """Nodes, then edges, then the title pass. Returns {key: id} plus a log."""
    from wheeler.tools.graph_tools import execute_tool

    ids: dict[str, str] = {}
    errors: list[dict] = []

    for node in graph["nodes"]:
        args = dict(node["args"])
        if "path" in args:
            args["path"] = str(project / args["path"])
        raw = await execute_tool(node["tool"], args, cfg)
        res = json.loads(raw)
        if "error" in res or not res.get("node_id"):
            raise SeedError(f"{node['tool']} for {node['key']} failed: {raw}")
        ids[node["key"]] = res["node_id"]

    linked = 0
    for src, rel, dst in graph["edges"]:
        raw = await execute_tool(
            "link_nodes",
            {"source_id": ids[src], "relationship": rel, "target_id": ids[dst]},
            cfg,
        )
        res = json.loads(raw)
        if res.get("status") != "linked":
            errors.append({"edge": [src, rel, dst], "result": res})
        else:
            linked += 1
    if errors:
        raise SeedError(f"{len(errors)} edges failed: {errors[:3]}")

    # Title pass: update_node stamps ``updated`` on each finding it touches, so
    # this order is what "most recently updated" means for task 9.
    titles = {n["key"]: n.get("title") for n in graph["nodes"] if n.get("title")}
    for key in graph["update_order"]:
        raw = await execute_tool("update_node", {"node_id": ids[key], "title": titles[key]}, cfg)
        res = json.loads(raw)
        if "error" in res:
            raise SeedError(f"update_node for {key} failed: {raw}")

    return {"ids": ids, "nodes": len(ids), "edges": linked, "titled": len(graph["update_order"])}


def seed_graph(cfg, graph: dict, project: Path) -> dict:
    reset_wheeler_caches()
    t0 = time.monotonic()
    try:
        out = asyncio.run(_seed(cfg, graph, project))
    finally:
        reset_wheeler_caches()
    out["seed_wall_s"] = round(time.monotonic() - t0, 3)
    return out


# ---------------------------------------------------------------------------
# Gold resolution and scoring
# ---------------------------------------------------------------------------


def resolve_gold(task: dict, ids: dict[str, str]) -> dict:
    """Map every symbolic key in a task's gold to the created node id."""
    g = task["gold"]
    kind = g["type"]
    if kind == "id":
        return {"type": kind, "value": ids[g["value"]]}
    if kind == "id_set":
        return {"type": kind, "value": sorted(ids[k] for k in g["value"])}
    if kind == "pair_set":
        return {"type": kind, "value": sorted([ids[a], ids[b]] for a, b in g["value"])}
    if kind == "chain_and_set":
        return {"type": kind, "chain": [ids[k] for k in g["chain"]], "set": sorted(ids[k] for k in g["set"])}
    if kind == "count_and_chain":
        return {"type": kind, "count": g["count"], "chain": [ids[k] for k in g["chain"]]}
    if kind == "object":
        return {"type": kind, "value": dict(g["value"]), "finding": ids.get(g.get("finding", ""), "")}
    raise ValueError(f"unknown gold type {kind}")


def _as_str_list(value) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return value
    return None


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def _prefix_match(got: list, gold: list) -> float:
    n = 0
    for g, w in zip(got, gold):
        if g != w:
            break
        n += 1
    return n / len(gold) if gold else 1.0


def _num_eq(a, b, tol: float = 1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def score_answer(answer, gold: dict) -> dict:
    """Exact match on ids; Jaccard for sets, prefix for chains, per-field for objects."""
    kind = gold["type"]
    score = 0.0
    note = ""
    if answer is None:
        return {"score": 0.0, "verdict": "wrong", "note": "no ANSWER line"}

    if kind == "id":
        score = 1.0 if answer == gold["value"] else 0.0
    elif kind == "id_set":
        got = _as_str_list(answer)
        if got is None:
            note = "expected a list of ids"
        else:
            score = _jaccard(set(got), set(gold["value"]))
    elif kind == "pair_set":
        if isinstance(answer, list) and all(isinstance(p, list) and len(p) == 2 for p in answer):
            score = _jaccard({tuple(p) for p in answer}, {tuple(p) for p in gold["value"]})
        else:
            note = "expected a list of [finding_id, hypothesis_id] pairs"
    elif kind == "chain_and_set":
        if isinstance(answer, dict):
            chain = _as_str_list(answer.get("chain")) or []
            scripts = _as_str_list(answer.get("scripts")) or []
            score = 0.7 * _prefix_match(chain, gold["chain"]) + 0.3 * _jaccard(set(scripts), set(gold["set"]))
        else:
            note = "expected an object with chain and scripts"
    elif kind == "count_and_chain":
        if isinstance(answer, dict):
            count_ok = _num_eq(answer.get("count"), gold["count"])
            top = _as_str_list(answer.get("top3")) or []
            score = 0.5 * float(count_ok) + 0.5 * _prefix_match(top, gold["chain"])
        else:
            note = "expected an object with count and top3"
    elif kind == "object":
        if isinstance(answer, dict):
            fields = gold["value"]
            hits = sum(1 for k, v in fields.items() if _num_eq(answer.get(k), v))
            score = hits / len(fields)
        else:
            note = "expected an object"
    score = round(score, 4)
    verdict = "correct" if score >= 0.9999 else ("partial" if score > 0 else "wrong")
    return {"score": score, "verdict": verdict, "note": note}


ANSWER_RE = re.compile(r"^\s*ANSWER\s+(.*\S)\s*$")


def extract_answer(texts: list[str]) -> tuple[object | None, str | None]:
    """The last parseable 'ANSWER <json>' line across the given texts."""
    for text in reversed(texts):
        for ln in reversed(text.splitlines()):
            m = ANSWER_RE.match(ln)
            if not m:
                continue
            payload = m.group(1).strip()
            if payload.startswith("`") and payload.endswith("`"):
                payload = payload.strip("`").strip()
            try:
                return json.loads(payload), ln.strip()
            except json.JSONDecodeError:
                return None, ln.strip()
    return None, None


# ---------------------------------------------------------------------------
# Prompt and command
# ---------------------------------------------------------------------------


def render_prompt(task: dict, answer_line: str) -> str:
    return (
        f"{PROMPT_HEAD}\n\n"
        f"Question: {task['prompt']}\n\n"
        f"Answer shape: {task['shape']}.\n\n"
        f"{answer_line}"
    )


def allowed_tools() -> list[str]:
    return ["mcp__wheeler_query", "mcp__wheeler_core", "Read", "Glob", "Grep"]


def claude_command(prompt: str, model: str, max_turns: int) -> list[str]:
    return [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--verbose",
        "--max-turns",
        str(max_turns),
        "--mcp-config",
        ".mcp.json",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--allowedTools",
        *allowed_tools(),
    ]


def launch(cmd: list[str], project: Path, out_dir: Path, level: str, timeout_s: float) -> dict:
    env = subprocess_env(project, level)
    t0 = time.monotonic()
    timed_out = False
    with open(out_dir / "transcript.jsonl", "wb") as out, open(out_dir / "stderr.log", "wb") as err:
        proc = subprocess.Popen(cmd, cwd=project, env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL)
        try:
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            rc = proc.wait()
    return {"wall_clock_s": round(time.monotonic() - t0, 3), "returncode": rc, "timed_out": timed_out}


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


def _short_tool(name: str) -> str:
    for prefix in (CORE_PREFIX, QUERY_PREFIX):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def parse_transcript(path: Path) -> dict:
    """Usage once per assistant message id, turns, tool histogram, ANSWER line.

    Claude Code may emit one assistant line per content block, all sharing one
    ``message.id`` and repeating the same ``usage``; usage is taken once per id.
    The ``result`` line's usage block is the authoritative session total when
    present; the per-message sum is kept as a cross-check.
    """
    out: dict = {
        "transcript_lines": 0,
        "unparseable_lines": 0,
        "turns": 0,
        "tokens": {k: 0 for k in USAGE_KEYS},
        "tool_calls": {},
        "tool_call_sequence": [],
        "show_node": {"calls": 0, "with_neighbors": 0, "with_fields": 0, "with_node_ids": 0, "ids_requested": 0},
        "listing_calls": 0,
        "search_calls": 0,
        "hop_calls": 0,
        "cypher_calls": 0,
        "result": {},
        "final_text": "",
        "answer": None,
        "answer_line": None,
    }
    if not path.exists():
        return out

    usage_by_msg: dict[str, dict] = {}
    seen_tool_ids: set[str] = set()
    tool_seq: list[str] = []
    assistant_texts: list[str] = []
    anon = 0

    for raw in path.read_text(errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        out["transcript_lines"] += 1
        try:
            line = json.loads(raw)
        except json.JSONDecodeError:
            out["unparseable_lines"] += 1
            continue
        if not isinstance(line, dict):
            continue
        ltype = line.get("type")

        if ltype == "assistant":
            msg = line.get("message") or {}
            mid = msg.get("id")
            if not mid:
                anon += 1
                mid = f"anon-{anon}"
            usage = msg.get("usage")
            if isinstance(usage, dict):
                usage_by_msg[mid] = usage
            else:
                usage_by_msg.setdefault(mid, {})
            for block in msg.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    assistant_texts.append(block["text"])
                if block.get("type") != "tool_use":
                    continue
                bid = block.get("id") or f"anon-tool-{len(seen_tool_ids)}"
                if bid in seen_tool_ids:
                    continue
                seen_tool_ids.add(bid)
                name = _short_tool(str(block.get("name") or "?"))
                tool_seq.append(name)
                inp = block.get("input") or {}
                if not isinstance(inp, dict):
                    inp = {}
                if name == "show_node":
                    sn = out["show_node"]
                    sn["calls"] += 1
                    if inp.get("neighbors"):
                        sn["with_neighbors"] += 1
                        out["hop_calls"] += 1
                    if inp.get("fields"):
                        sn["with_fields"] += 1
                    node_ids = inp.get("node_ids")
                    if isinstance(node_ids, list) and node_ids:
                        sn["with_node_ids"] += 1
                        sn["ids_requested"] += len(node_ids)
                    elif inp.get("node_id"):
                        sn["ids_requested"] += 1
                elif name.startswith("query_"):
                    out["listing_calls"] += 1
                elif name in ("search_findings", "search_context", "graph_context"):
                    out["search_calls"] += 1
                    if name == "search_context":
                        out["hop_calls"] += 1
                elif name == "run_cypher":
                    out["cypher_calls"] += 1

        elif ltype == "result":
            res = {}
            for key in ("subtype", "num_turns", "duration_ms", "duration_api_ms", "total_cost_usd", "is_error"):
                if key in line:
                    res[key] = line[key]
            if isinstance(line.get("usage"), dict):
                res["usage"] = line["usage"]
            if isinstance(line.get("modelUsage"), dict):
                res["modelUsage"] = line["modelUsage"]
            out["result"] = res
            text = line.get("result")
            if isinstance(text, str):
                out["final_text"] = text

    for usage in usage_by_msg.values():
        for k in USAGE_KEYS:
            v = usage.get(k)
            if isinstance(v, (int, float)):
                out["tokens"][k] += int(v)
    out["tokens"]["total_input_incl_cache"] = (
        out["tokens"]["input_tokens"]
        + out["tokens"]["cache_creation_input_tokens"]
        + out["tokens"]["cache_read_input_tokens"]
    )
    out["turns"] = len(usage_by_msg)
    out["tool_calls"] = dict(Counter(tool_seq).most_common())
    out["tool_call_sequence"] = tool_seq
    texts = assistant_texts + ([out["final_text"]] if out["final_text"] else [])
    out["answer"], out["answer_line"] = extract_answer(texts)
    return out


# ---------------------------------------------------------------------------
# Neo4j helpers: gold verification and cleanup
# ---------------------------------------------------------------------------


def _neo4j_session():
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(NEO4J["uri"], auth=(NEO4J["username"], NEO4J["password"]))
    return driver, driver.session(database=NEO4J["database"])


def _rows(session, query: str, **params) -> list[dict]:
    return [dict(r) for r in session.run(query, **params)]


def verify_gold(tag: str, tasks: list[dict], ids: dict[str, str], graph: dict) -> list[dict]:
    """Check that every task's gold is what the seeded graph actually says."""
    T = "n._wheeler_project = $tag"
    driver, session = _neo4j_session()
    report: list[dict] = []
    try:
        count = _rows(session, f"MATCH (n) WHERE {T} RETURN count(n) AS c", tag=tag)[0]["c"]
        edges = _rows(
            session,
            "MATCH (a)-[r]->(b) WHERE a._wheeler_project = $tag AND b._wheeler_project = $tag RETURN count(r) AS c",
            tag=tag,
        )[0]["c"]
        report.append({"check": "graph", "ok": count == len(ids) and edges == len(graph["edges"]),
                       "nodes": count, "edges": edges, "expected": [len(ids), len(graph["edges"])]})

        for task in tasks:
            gold = resolve_gold(task, ids)
            tid = task["id"]
            entry: dict = {"task": tid, "kind": task["kind"], "gold": gold}
            if tid == 1:
                got = _rows(session,
                            "MATCH (f:Finding {id: $fig})-[:WAS_GENERATED_BY]->(x:Execution)-[:USED]->(s:Script) "
                            "WHERE f._wheeler_project = $tag RETURN s.id AS id",
                            fig=ids["fig03"], tag=tag)
                entry["graph"] = sorted(r["id"] for r in got)
                entry["ok"] = entry["graph"] == [gold["value"]]
            elif tid == 2:
                got = _rows(session,
                            "MATCH (f:Finding)-[:SUPPORTS]->(h:Hypothesis {id: $h}) WHERE f._wheeler_project = $tag "
                            "RETURN f.id AS id", h=ids["H2"], tag=tag)
                entry["graph"] = sorted(r["id"] for r in got)
                entry["ok"] = entry["graph"] == gold["value"]
            elif tid == 3:
                got = _rows(session,
                            "MATCH (f:Finding {id: $fig})-[:WAS_GENERATED_BY]->(x:Execution)-[:USED]->(d:Dataset) "
                            "WHERE f._wheeler_project = $tag RETURN d.id AS id", fig=ids["fig05"], tag=tag)
                entry["graph"] = sorted(r["id"] for r in got)
                entry["ok"] = entry["graph"] == gold["value"]
            elif tid == 4:
                chain = gold["chain"]
                ok = True
                for i in range(len(chain) - 1):
                    rel = "WAS_GENERATED_BY" if i % 2 == 0 else "USED"
                    hit = _rows(session,
                                f"MATCH (a {{id: $a}})-[:{rel}]->(b {{id: $b}}) WHERE a._wheeler_project = $tag "
                                "RETURN count(*) AS c", a=chain[i], b=chain[i + 1], tag=tag)[0]["c"]
                    ok = ok and hit == 1
                execs = [chain[i] for i in range(1, len(chain), 2)]
                scripts = _rows(session,
                                "MATCH (x:Execution)-[:USED]->(s:Script) WHERE x.id IN $xs AND x._wheeler_project = $tag "
                                "RETURN DISTINCT s.id AS id", xs=execs, tag=tag)
                entry["graph"] = {"chain_edges_ok": ok, "scripts": sorted(r["id"] for r in scripts)}
                # A figure has exactly one generating execution, and the raw dataset none.
                raw_gen = _rows(session,
                                "MATCH (d {id: $d})-[:WAS_GENERATED_BY]->() WHERE d._wheeler_project = $tag RETURN count(*) AS c",
                                d=chain[-1], tag=tag)[0]["c"]
                entry["ok"] = ok and entry["graph"]["scripts"] == gold["set"] and raw_gen == 0
            elif tid == 5:
                node = _rows(session,
                             "MATCH (f:Finding {id: $id}) WHERE f._wheeler_project = $tag "
                             "RETURN f.confidence AS conf, f.description AS d", id=gold["finding"], tag=tag)[0]
                number = str(gold["value"]["peak_latency_ms"])
                others = _rows(session,
                               "MATCH (n) WHERE n._wheeler_project = $tag AND n.id <> $id AND "
                               "(coalesce(n.description, '') CONTAINS $num OR coalesce(n.title, '') CONTAINS $num "
                               "OR coalesce(n.statement, '') CONTAINS $num) RETURN n.id AS id",
                               id=gold["finding"], num=number, tag=tag)
                pos = node["d"].find(number)
                entry["graph"] = {"confidence": node["conf"], "number_at_char": pos, "other_nodes_with_number": len(others)}
                entry["ok"] = _num_eq(node["conf"], gold["value"]["confidence"]) and pos >= 240 and not others
            elif tid == 6:
                phrase = task["prompt"].split("mentions ", 1)[1].split("?", 1)[0]
                got = _rows(session,
                            "MATCH (n) WHERE n._wheeler_project = $tag AND toLower(coalesce(n.description, '')) CONTAINS toLower($p) "
                            "RETURN n.id AS id, n.description AS d", p=phrase, tag=tag)
                entry["graph"] = {"ids": sorted(r["id"] for r in got),
                                  "phrase_at_char": [r["d"].lower().find(phrase.lower()) for r in got]}
                entry["ok"] = entry["graph"]["ids"] == [gold["value"]] and all(p >= 400 for p in entry["graph"]["phrase_at_char"])
            elif tid == 7:
                got = _rows(session,
                            "MATCH (f:Finding)-[:CONTRADICTS]->(h:Hypothesis) WHERE f._wheeler_project = $tag "
                            "RETURN f.id AS f, h.id AS h", tag=tag)
                entry["graph"] = sorted([r["f"], r["h"]] for r in got)
                entry["ok"] = entry["graph"] == gold["value"]
            elif tid == 8:
                got = _rows(session,
                            "MATCH (f:Finding {artifact_type: 'figure'})-[:WAS_GENERATED_BY|USED*1..8]->(s:Script {id: $s}) "
                            "WHERE f._wheeler_project = $tag RETURN DISTINCT f.id AS id", s=ids["S3"], tag=tag)
                entry["graph"] = sorted(r["id"] for r in got)
                entry["ok"] = entry["graph"] == gold["value"]
            elif tid == 9:
                got = _rows(session,
                            "MATCH (f:Finding)-[:RELEVANT_TO]->(q:OpenQuestion {id: $q}) WHERE f._wheeler_project = $tag "
                            "RETURN f.id AS id, f.updated AS updated ORDER BY f.updated DESC", q=ids["Q1"], tag=tag)
                entry["graph"] = {"count": len(got), "top3": [r["id"] for r in got[:3]],
                                  "all_have_updated": all(r["updated"] for r in got)}
                entry["ok"] = (entry["graph"]["count"] == gold["count"] and entry["graph"]["top3"] == gold["chain"]
                               and entry["graph"]["all_have_updated"])
            elif tid == 10:
                got = _rows(session,
                            "MATCH (w:Document {id: $w})-[:CITES]->(p:Paper) WHERE w._wheeler_project = $tag RETURN p.id AS id",
                            w=ids["W1"], tag=tag)
                entry["graph"] = sorted(r["id"] for r in got)
                entry["ok"] = entry["graph"] == gold["value"]
            else:
                entry["ok"] = False
                entry["graph"] = "no verifier for this task"
            report.append(entry)
    finally:
        session.close()
        driver.close()
    return report


def cleanup(tag: str) -> dict:
    driver, session = _neo4j_session()
    try:
        before = session.run("MATCH (n) WHERE n._wheeler_project = $tag RETURN count(n) AS c", tag=tag).single()["c"]
        session.run("MATCH (n) WHERE n._wheeler_project = $tag DETACH DELETE n", tag=tag).consume()
        after = session.run("MATCH (n) WHERE n._wheeler_project = $tag RETURN count(n) AS c", tag=tag).single()["c"]
    finally:
        session.close()
        driver.close()
    return {"deleted": before, "remaining": after}


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


def parse_task_selection(spec: str | None, tasks: list[dict]) -> list[dict]:
    if not spec:
        return tasks
    wanted = {int(x) for x in spec.split(",") if x.strip()}
    known = {t["id"] for t in tasks}
    unknown = wanted - known
    if unknown:
        sys.exit(f"unknown task ids {sorted(unknown)}; have {sorted(known)}")
    return [t for t in tasks if t["id"] in wanted]


def one_task(ns: argparse.Namespace, run_dir: Path, project: Path, tag: str, task: dict,
             ids: dict[str, str], answer_line: str, k: int) -> dict:
    out_dir = run_dir / f"t{task['id']}-r{k}"
    out_dir.mkdir(parents=True, exist_ok=False)
    prompt = render_prompt(task, answer_line)
    (out_dir / "prompt.md").write_text(prompt)
    cmd = claude_command(prompt, ns.model, ns.max_turns)
    (out_dir / "command.txt").write_text(shlex.join(cmd) + "\n")
    gold = resolve_gold(task, ids)

    results: dict = {
        "level": ns.level,
        "task": task["id"],
        "kind": task["kind"],
        "may_need_body": task["may_need_body"],
        "model": ns.model,
        "repeat_index": k,
        "run_dir": str(run_dir),
        "out_dir": str(out_dir),
        "project_dir": str(project),
        "project_tag": tag,
        "started_at": _now_iso(),
        "worktree": str(WORKTREE),
        "gold": gold,
    }
    print(f"[{tag}] task {task['id']} r{k}: launching claude ({ns.model}, max {ns.max_turns} turns)")
    results.update(launch(cmd, project, out_dir, ns.level, ns.timeout_s))
    results.update(parse_transcript(out_dir / "transcript.jsonl"))
    results["score"] = score_answer(results["answer"], gold)
    results["finished_at"] = _now_iso()
    (out_dir / "results.json").write_text(json.dumps(results, indent=2, default=str) + "\n")
    s = results["score"]
    print(
        f"[{tag}] task {task['id']} r{k}: {s['verdict']} (score {s['score']}), rc={results['returncode']}, "
        f"{results['wall_clock_s']}s, {results['turns']} turns, show_node x{results['show_node']['calls']}, "
        f"cypher x{results['cypher_calls']}; answer={results['answer_line']!r}"
    )
    return results


def level_summary(ns: argparse.Namespace, run_dir: Path, tag: str, seed: dict, rows: list[dict]) -> dict:
    def _ctx(r: dict) -> int:
        u = (r.get("result") or {}).get("usage") or r.get("tokens") or {}
        return int(u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0))

    def _mean(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    body = [r for r in rows if r["may_need_body"]]
    rest = [r for r in rows if not r["may_need_body"]]
    return {
        "level": ns.level,
        "model": ns.model,
        "run_dir": str(run_dir),
        "project_tag": tag,
        "seed": {k: v for k, v in seed.items() if k != "ids"},
        "n_runs": len(rows),
        "mean_score": _mean([r["score"]["score"] for r in rows]),
        "accuracy": _mean([1.0 if r["score"]["verdict"] == "correct" else 0.0 for r in rows]),
        "mean_turns": _mean([r["turns"] for r in rows]),
        "mean_context_tokens": _mean([_ctx(r) for r in rows]),
        "mean_output_tokens": _mean([((r.get("result") or {}).get("usage") or r["tokens"]).get("output_tokens", 0) for r in rows]),
        "mean_wall_s": _mean([r["wall_clock_s"] for r in rows]),
        "mean_show_node_calls": _mean([r["show_node"]["calls"] for r in rows]),
        "mean_cypher_calls": _mean([r["cypher_calls"] for r in rows]),
        "may_need_body": {
            "n": len(body),
            "accuracy": _mean([1.0 if r["score"]["verdict"] == "correct" else 0.0 for r in body]),
            "mean_score": _mean([r["score"]["score"] for r in body]),
        },
        "no_body_needed": {
            "n": len(rest),
            "accuracy": _mean([1.0 if r["score"]["verdict"] == "correct" else 0.0 for r in rest]),
            "mean_score": _mean([r["score"]["score"] for r in rest]),
        },
        "per_task": [
            {"task": r["task"], "repeat": r["repeat_index"], "verdict": r["score"]["verdict"],
             "score": r["score"]["score"], "turns": r["turns"], "context_tokens": _ctx(r)}
            for r in rows
        ],
    }


def run_level(ns: argparse.Namespace) -> Path:
    graph = load_graph()
    tasks_doc = load_tasks()
    tasks = parse_task_selection(ns.tasks, tasks_doc["tasks"])
    ts = _utc_ts()
    tag = f"disclosure-{ts}-{ns.level}"
    run_dir = RUNS / f"{ts}-{ns.level}"
    run_dir.mkdir(parents=True, exist_ok=False)
    project = prepare_project(run_dir, tag, ns.level)
    cfg = build_config(project, tag)
    print(f"[{tag}] project at {project}")

    rows: list[dict] = []
    seed: dict = {}
    try:
        seed = seed_graph(cfg, graph, project)
        (run_dir / "seed_ids.json").write_text(json.dumps(seed, indent=2) + "\n")
        print(f"[{tag}] seeded {seed['nodes']} nodes, {seed['edges']} edges in {seed['seed_wall_s']}s")
        for task in tasks:
            for k in range(1, ns.repeat + 1):
                rows.append(one_task(ns, run_dir, project, tag, task, seed["ids"], tasks_doc["answer_line"], k))
    finally:
        summary = level_summary(ns, run_dir, tag, seed, rows) if seed else {"error": "seeding failed"}
        if ns.keep:
            summary["cleanup"] = {"skipped": True, "tag": tag}
            print(f"[{tag}] --keep: graph nodes left in place under tag {tag}")
        else:
            summary["cleanup"] = cleanup(tag)
            print(f"[{tag}] cleanup: {summary['cleanup']}")
        (run_dir / "level_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
        print(f"[{tag}] wrote {run_dir / 'level_summary.json'}")
    return run_dir


def check_gold(ns: argparse.Namespace) -> None:
    """Seed, resolve every gold to ids, verify each against Neo4j, clean up."""
    graph = load_graph()
    tasks = load_tasks()["tasks"]
    ts = _utc_ts()
    tag = f"disclosure-{ts}-checkgold"
    run_dir = RUNS / f"{ts}-checkgold"
    run_dir.mkdir(parents=True, exist_ok=False)
    project = prepare_project(run_dir, tag, "full")
    cfg = build_config(project, tag)
    ok_all = False
    try:
        seed = seed_graph(cfg, graph, project)
        (run_dir / "seed_ids.json").write_text(json.dumps(seed, indent=2) + "\n")
        print(f"[{tag}] seeded {seed['nodes']} nodes, {seed['edges']} edges in {seed['seed_wall_s']}s")
        report = verify_gold(tag, tasks, seed["ids"], graph)
        (run_dir / "check_gold.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
        ok_all = all(e["ok"] for e in report)
        for e in report:
            flag = "ok " if e["ok"] else "BAD"
            if e.get("check") == "graph":
                print(f"  {flag} graph: {e['nodes']} nodes, {e['edges']} edges (expected {e['expected']})")
                continue
            print(f"  {flag} task {e['task']:>2} ({e['kind']}): gold={json.dumps(e['gold'])}")
            if not e["ok"]:
                print(f"      graph says: {json.dumps(e['graph'])}")
        files = {
            "knowledge_json": len(list((project / "knowledge").glob("*.json"))),
            "synthesis_md": len(list((project / "synthesis").glob("*.md"))),
        }
        print(f"  files: {files}")
    finally:
        if ns.keep:
            print(f"[{tag}] --keep: graph nodes left in place under tag {tag}")
        else:
            print(f"[{tag}] cleanup: {cleanup(tag)}")
    print("check-gold:", "PASS" if ok_all else "FAIL")
    if not ok_all:
        sys.exit(1)


def plan(ns: argparse.Namespace) -> None:
    tasks_doc = load_tasks()
    tasks = parse_task_selection(ns.tasks, tasks_doc["tasks"])
    project = RUNS / f"<ts>-{ns.level}" / "project"
    print("# cwd:", project)
    print("# env: os.environ minus the direct API credential and CLAUDECODE, plus")
    print(f"#      PYTHONPATH={WORKTREE} {DISCLOSURE_ENV}={ns.level} WHEELER_NO_KEYCHAIN=1 "
          "WHEELER_PROJECT_ROOT=<project> NEO4J_*=<scratch>")
    print("# .mcp.json:")
    print(json.dumps(mcp_json(ns.level), indent=2))
    for task in tasks:
        prompt = render_prompt(task, tasks_doc["answer_line"])
        cmd = claude_command(prompt, ns.model, ns.max_turns)
        print()
        print(f"# task {task['id']} ({task['kind']}, may_need_body={task['may_need_body']}) command:")
        print(shlex.join(cmd[:2]), shlex.quote("<prompt below>"), shlex.join(cmd[3:]))
        print()
        print("# prompt:")
        print(prompt)
        print()
        print("# gold (symbolic keys, resolved to ids after seeding):", json.dumps(task["gold"]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", choices=LEVELS, help="disclosure level passed to the servers")
    ap.add_argument("--tasks", help="comma-separated task ids, default all 10")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--keep", action="store_true", help="leave the tagged nodes in Neo4j afterwards")
    ap.add_argument("--plan", action="store_true", help="print the command and prompt, run nothing")
    ap.add_argument("--check-gold", action="store_true",
                    help="seed, verify every gold answer against Neo4j, clean up, exit")
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--timeout-s", type=float, default=1800, help="kill claude after this many seconds")
    ns = ap.parse_args()

    if not FIXTURE.exists() or not (FIXTURE / "graph.json").exists():
        sys.exit(f"fixture missing at {FIXTURE}: run make_fixture.py first")
    if ns.plan:
        if not ns.level:
            sys.exit("--plan needs --level")
        plan(ns)
        return
    assert_worktree_import()
    if ns.check_gold:
        check_gold(ns)
        return
    if not ns.level:
        sys.exit("--level is required (or --check-gold / --plan)")
    if shutil.which("claude") is None:
        sys.exit("claude CLI not found on PATH")
    run_level(ns)


if __name__ == "__main__":
    main()
