#!/usr/bin/env python
"""Experiment harness for issue #117: cost of bulk provenance registration.

One invocation runs one strategy ``--repeat`` times. Each run gets its own
scratch project under ``runs/<UTC ts>-s<N>-r<k>/project/`` with its own
``wheeler.yaml`` (unique ``neo4j.project_tag``) so the local Neo4j, which holds
thousands of unrelated test nodes, is never touched outside that tag.

Per run:
  1. copy the fixture into a scratch project, write wheeler.yaml and .mcp.json
  2. seed the two pre-existing nodes (question, dataset) and render BRIEF.md
  3. launch ``claude -p`` headlessly on the subscription (strategies 1-5), or
     call ``register_batch`` directly from gold (strategy 0, the oracle)
  4. parse the stream-json transcript for tokens, turns and tool calls
  5. score the tagged subgraph against ``fixture/gold.json``
  6. write ``results.json`` and, unless ``--keep``, delete every node with the tag

Run from the worktree root with the worktree first on PYTHONPATH::

    PYTHONPATH=$PWD .venv/bin/python evals/batch_registration/run.py --strategy 0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
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
RUNS = HERE / "runs"
PROMPTS = HERE / "prompts"

# Local experiment database. Isolation is by project_tag, never by database.
NEO4J = {
    "uri": "bolt://localhost:7717",
    "username": "neo4j",
    "password": "research-graph",
    "database": "neo4j",
}

# Files in the fixture that the model must never see inside its project.
FIXTURE_EXCLUDE = {"BRIEF.md.template", "gold.json"}

STRATEGY_NAMES = {
    0: "oracle (register_batch from gold, no model)",
    1: "status quo: one MCP call per node and per edge",
    2: "batch MCP: register_batch / ensure_artifacts + link_nodes_batch",
    3: "manifest: Write provenance.yaml, one CLI register call",
    4: "manifest + validate: --dry-run first, then register",
    5: "subagent: delegate the status-quo method to one Agent",
    6: "batch MCP, split form: ensure_artifacts + add_* + link_nodes_batch (id round trip)",
}

MUTATION_PREFIX = "mcp__wheeler_mutations__"
CLI_REGISTER = "wheeler.tools.cli integrate register"


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

    Both are process-wide singletons. The backend cache is keyed on the config
    (uri, db, tag, project root) so a new tag would miss it anyway, but the
    async driver is bound to whichever event loop created it, and every
    ``asyncio.run`` here opens a fresh loop.
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
        "# Scratch project for the #117 batch-registration experiment.\n"
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


def mcp_json(strategy: int) -> dict:
    env = {
        "PYTHONPATH": str(WORKTREE),
        "WHEELER_BATCH_TOOLS": "1" if strategy in (2, 6) else "0",
        # Belt and braces so a server can never resolve to another graph: the
        # keychain layer outranks wheeler.yaml, and env outranks the keychain.
        "WHEELER_NO_KEYCHAIN": "1",
        "NEO4J_URI": NEO4J["uri"],
        "NEO4J_USERNAME": NEO4J["username"],
        "NEO4J_PASSWORD": NEO4J["password"],
        "NEO4J_DATABASE": NEO4J["database"],
    }
    servers = {}
    for name in ("core", "query", "mutations"):
        servers[f"wheeler_{name}"] = {
            "type": "stdio",
            "command": str(PYTHON),
            "args": ["-m", f"wheeler.mcp_{name}"],
            "env": env,
        }
    return {"mcpServers": servers}


def subprocess_env(project: Path) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        # Runs use the claude CLI on the subscription: drop any direct API credential.
        if not (k.startswith("ANTHROPIC") and k.endswith("_API_KEY"))
    }
    # A claude launched from inside a Claude Code session refuses to start
    # while the parent's marker is present.
    env.pop("CLAUDECODE", None)
    env["PYTHONPATH"] = str(WORKTREE)
    env["WHEELER_NO_KEYCHAIN"] = "1"
    env["WHEELER_PROJECT_ROOT"] = str(project)
    env["NEO4J_URI"] = NEO4J["uri"]
    env["NEO4J_USERNAME"] = NEO4J["username"]
    env["NEO4J_PASSWORD"] = NEO4J["password"]
    env["NEO4J_DATABASE"] = NEO4J["database"]
    return env


# ---------------------------------------------------------------------------
# Project preparation and seeding
# ---------------------------------------------------------------------------


def load_gold() -> dict:
    return json.loads((FIXTURE / "gold.json").read_text())


def prepare_project(run_dir: Path, tag: str, strategy: int) -> Path:
    project = run_dir / "project"
    shutil.copytree(
        FIXTURE, project, ignore=lambda _d, names: [n for n in names if n in FIXTURE_EXCLUDE]
    )
    gold = load_gold()
    raw = project / gold["seed_dataset"]["path"]
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(
        "epoch,spike_time_ms\n"
        + "\n".join(f"1,{12.5 + 37.25 * i:.2f}" for i in range(12))
        + "\n"
    )
    (project / "wheeler.yaml").write_text(wheeler_yaml(tag))
    (project / ".mcp.json").write_text(json.dumps(mcp_json(strategy), indent=2) + "\n")
    return project


async def _seed(cfg, gold: dict, project: Path) -> dict[str, str]:
    from wheeler.tools.graph_tools import execute_tool

    q = json.loads(
        await execute_tool("add_question", {"question": gold["seed_question"], "priority": 4}, cfg)
    )
    if "error" in q:
        raise RuntimeError(f"add_question failed: {q}")
    ds = gold["seed_dataset"]
    d = json.loads(
        await execute_tool(
            "add_dataset",
            {
                "path": str(project / ds["path"]),
                "type": ds["type"],
                "description": ds["description"],
                "tier": "reference",
            },
            cfg,
        )
    )
    if "error" in d:
        raise RuntimeError(f"add_dataset failed: {d}")
    return {"QUESTION_ID": q["node_id"], "DATASET_ID": d["node_id"]}


def seed_graph(cfg, gold: dict, project: Path) -> dict[str, str]:
    reset_wheeler_caches()
    try:
        return asyncio.run(_seed(cfg, gold, project))
    finally:
        reset_wheeler_caches()


def render_brief(project: Path, seeds: dict[str, str]) -> None:
    text = (FIXTURE / "BRIEF.md.template").read_text()
    for key, value in seeds.items():
        text = text.replace("{" + key + "}", value)
    (project / "BRIEF.md").write_text(text)


# ---------------------------------------------------------------------------
# Prompt and command
# ---------------------------------------------------------------------------


def render_prompt(strategy: int, project: Path, seeds: dict[str, str]) -> str:
    body = (PROMPTS / f"s{strategy}.md").read_text()
    body = body.replace("{COMMON_HEAD}", (PROMPTS / "_common_head.md").read_text())
    body = body.replace("{COMMON_TAIL}", (PROMPTS / "_common_tail.md").read_text())
    subs = {
        "PROJECT_DIR": str(project),
        "PYTHON": str(PYTHON),
        "WORKTREE": str(WORKTREE),
        **seeds,
    }
    for key, value in subs.items():
        body = body.replace("{" + key + "}", value)
    return body


def allowed_tools(strategy: int) -> list[str]:
    tools = [
        "mcp__wheeler_mutations",
        "mcp__wheeler_query",
        "mcp__wheeler_core",
        "Read",
        "Glob",
        "Grep",
        "Write",
    ]
    if strategy in (3, 4):
        tools.append(f"Bash({PYTHON} -m {CLI_REGISTER}*)")
    if strategy == 5:
        tools.append("Agent")
    return tools


def claude_command(prompt: str, model: str, max_turns: int, strategy: int) -> list[str]:
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
        *allowed_tools(strategy),
    ]


def launch(cmd: list[str], project: Path, run_dir: Path, timeout_s: float) -> dict:
    env = subprocess_env(project)
    t0 = time.monotonic()
    timed_out = False
    with open(run_dir / "transcript.jsonl", "wb") as out, open(run_dir / "stderr.log", "wb") as err:
        proc = subprocess.Popen(cmd, cwd=project, env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL)
        try:
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            rc = proc.wait()
    return {
        "wall_clock_s": round(time.monotonic() - t0, 3),
        "returncode": rc,
        "timed_out": timed_out,
    }


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


def _max_consecutive(seq: list[str]) -> tuple[str, int]:
    best_name, best_run = "", 0
    cur_name, cur_run = None, 0
    for name in seq:
        if name == cur_name:
            cur_run += 1
        else:
            cur_name, cur_run = name, 1
        if cur_run > best_run:
            best_name, best_run = name, cur_run
    return best_name, best_run


def parse_transcript(path: Path) -> dict:
    """Sum usage over assistant messages, count turns and tool calls.

    Claude Code may emit one assistant line per content block, all sharing one
    ``message.id`` and repeating the same ``usage``. Usage is therefore taken
    once per message id (last seen), and turns are distinct message ids.
    """
    out: dict = {
        "transcript_lines": 0,
        "unparseable_lines": 0,
        "assistant_lines": 0,
        "turns": 0,
        "tokens": {k: 0 for k in USAGE_KEYS},
        "tool_calls": {},
        "tool_call_sequence": [],
        "max_consecutive_tool": {"tool": "", "run": 0},
        "mutation_calls": 0,
        "cli_register_calls": 0,
        "cli_dry_run_calls": 0,
        "subagent_assistant_lines": 0,
        "subagent_usage_visible": False,
        "result": {},
        "final_text": "",
        "done_line": None,
    }
    if not path.exists():
        return out

    usage_by_msg: dict[str, dict] = {}
    seen_tool_ids: set[str] = set()
    tool_seq: list[str] = []
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
            out["assistant_lines"] += 1
            msg = line.get("message") or {}
            if line.get("parent_tool_use_id"):
                out["subagent_assistant_lines"] += 1
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
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                bid = block.get("id") or f"anon-tool-{len(seen_tool_ids)}"
                if bid in seen_tool_ids:
                    continue
                seen_tool_ids.add(bid)
                name = str(block.get("name") or "?")
                tool_seq.append(name)
                if name.startswith(MUTATION_PREFIX):
                    out["mutation_calls"] += 1
                if name == "Bash":
                    cmd = str((block.get("input") or {}).get("command") or "")
                    if CLI_REGISTER in cmd:
                        if "--dry-run" in cmd:
                            out["cli_dry_run_calls"] += 1
                        else:
                            out["cli_register_calls"] += 1
                            out["mutation_calls"] += 1

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
    name, run = _max_consecutive(tool_seq)
    out["max_consecutive_tool"] = {"tool": name, "run": run}
    out["subagent_usage_visible"] = out["subagent_assistant_lines"] > 0

    for ln in reversed(out["final_text"].splitlines()):
        parts = ln.strip().split()
        if len(parts) == 3 and parts[0] == "DONE":
            try:
                out["done_line"] = {"nodes": int(parts[1]), "edges": int(parts[2])}
            except ValueError:
                out["done_line"] = {"raw": ln.strip()}
            break
    return out


# ---------------------------------------------------------------------------
# Scoring against gold
# ---------------------------------------------------------------------------


def _neo4j_session():
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(NEO4J["uri"], auth=(NEO4J["username"], NEO4J["password"]))
    return driver, driver.session(database=NEO4J["database"])


def fetch_tagged(tag: str) -> tuple[list[dict], list[dict], int]:
    driver, session = _neo4j_session()
    try:
        nodes = [
            dict(r)
            for r in session.run(
                "MATCH (n) WHERE n._wheeler_project = $tag "
                "RETURN labels(n) AS labels, n.id AS id, n.path AS path, "
                "n.description AS description, n.title AS title, n.kind AS kind, "
                "n.question AS question",
                tag=tag,
            )
        ]
        edges = [
            dict(r)
            for r in session.run(
                "MATCH (a)-[r]->(b) WHERE a._wheeler_project = $tag AND b._wheeler_project = $tag "
                "RETURN a.id AS src, type(r) AS rel, b.id AS dst",
                tag=tag,
            )
        ]
        crossing = session.run(
            "MATCH (a)-[r]-(b) WHERE a._wheeler_project = $tag "
            "AND coalesce(b._wheeler_project, '') <> $tag RETURN count(r) AS c",
            tag=tag,
        ).single()["c"]
    finally:
        session.close()
        driver.close()
    return nodes, edges, crossing


def _basename(path: str | None) -> str:
    if not path:
        return ""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def score(tag: str, gold: dict, seeds: dict[str, str]) -> dict:
    nodes, edges, crossing = fetch_tagged(tag)
    seed_ids = set(seeds.values())
    by_id = {n["id"]: n for n in nodes if n.get("id")}
    created = [n for n in nodes if n.get("id") not in seed_ids]

    resolved: dict[str, str] = {"QUESTION_ID": seeds["QUESTION_ID"], "DATASET_ID": seeds["DATASET_ID"]}
    notes: list[str] = []
    matched_ids: set[str] = set()

    # Execution
    execs = [n for n in created if "Execution" in (n.get("labels") or [])]
    if len(execs) > 1:
        notes.append(f"{len(execs)} Execution nodes created; expected 1")
        execs.sort(key=lambda n: (n.get("kind") != gold["nodes"]["execution"]["kind"], n["id"]))
    if execs:
        resolved["exec"] = execs[0]["id"]
        matched_ids.add(execs[0]["id"])

    # Artifacts by basename, label must match
    unmatched_artifacts: list[dict] = []
    label_mismatches: list[dict] = []
    for rel, spec in gold["nodes"]["artifacts"].items():
        base = _basename(rel)
        cands = [n for n in created if _basename(n.get("path")) == base]
        good = [n for n in cands if spec["label"] in (n.get("labels") or [])]
        if good:
            if len(good) > 1:
                notes.append(f"{rel}: {len(good)} nodes share this basename; using {good[0]['id']}")
            resolved[rel] = good[0]["id"]
            matched_ids.add(good[0]["id"])
        elif cands:
            label_mismatches.append(
                {"path": rel, "expected": spec["label"], "got": [c.get("labels") for c in cands]}
            )
            unmatched_artifacts.append({"path": rel, "reason": "label_mismatch"})
        else:
            unmatched_artifacts.append({"path": rel, "reason": "not_found"})

    # Findings by key substring in description, case-insensitive
    unmatched_findings: list[str] = []
    shared_nodes: list[dict] = []
    findings = [n for n in created if "Finding" in (n.get("labels") or [])]
    for key in gold["nodes"]["findings"]:
        hits = [n for n in findings if key.lower() in str(n.get("description") or "").lower()]
        fresh = [n for n in hits if n["id"] not in matched_ids]
        pick = (fresh or hits)[:1]
        if not pick:
            unmatched_findings.append(key)
            continue
        node = pick[0]
        if len(hits) > 1:
            notes.append(f"finding {key!r}: {len(hits)} candidate nodes; using {node['id']}")
        if node["id"] in matched_ids and not fresh:
            shared_nodes.append({"finding": key, "node_id": node["id"]})
        resolved[f"finding:{key}"] = node["id"]
        matched_ids.add(node["id"])

    # Edges
    gold_triples: list[tuple[str, str, str] | None] = []
    missed_edges: list[dict] = []
    for src, rel, dst in gold["edges"]:
        s, d = resolved.get(src), resolved.get(dst)
        gold_triples.append((s, rel, d) if s and d else None)
    graph_counter = Counter((e["src"], e["rel"], e["dst"]) for e in edges)
    gold_set = {t for t in gold_triples if t}
    matched_edges = 0
    for (src, rel, dst), triple in zip(gold["edges"], gold_triples):
        if triple and graph_counter.get(triple, 0) > 0:
            matched_edges += 1
        else:
            missed_edges.append(
                {"source": src, "relationship": rel, "target": dst,
                 "reason": "endpoint_unresolved" if triple is None else "edge_absent"}
            )

    def _describe(node_id: str) -> str:
        n = by_id.get(node_id)
        if not n:
            return node_id
        lbl = (n.get("labels") or ["?"])[0]
        hint = _basename(n.get("path")) or str(n.get("description") or n.get("question") or "")[:50]
        return f"{node_id} ({lbl}: {hint})"

    extra_edges = []
    for triple, count in graph_counter.items():
        extra = count - (1 if triple in gold_set else 0)
        for _ in range(extra):
            extra_edges.append(
                {"source": _describe(triple[0]), "relationship": triple[1], "target": _describe(triple[2]),
                 "duplicate": triple in gold_set}
            )
    extra_nodes = [
        {"id": n["id"], "labels": n.get("labels"), "path": n.get("path"),
         "description": str(n.get("description") or n.get("question") or "")[:120]}
        for n in created
        if n["id"] not in matched_ids
    ]

    n_gold_nodes = 1 + len(gold["nodes"]["artifacts"]) + len(gold["nodes"]["findings"])
    n_gold_edges = len(gold["edges"])
    matched_nodes = len(matched_ids)
    total_edges = sum(graph_counter.values())
    return {
        "nodes_created": len(created),
        "nodes_matched": matched_nodes,
        "nodes_expected": n_gold_nodes,
        "node_recall": round(matched_nodes / n_gold_nodes, 4),
        "node_precision": round(matched_nodes / len(created), 4) if created else 0.0,
        "edges_created": total_edges,
        "edges_matched": matched_edges,
        "edges_expected": n_gold_edges,
        "edge_recall": round(matched_edges / n_gold_edges, 4),
        "edge_precision": round(matched_edges / total_edges, 4) if total_edges else 0.0,
        "execution_found": "exec" in resolved,
        "execution_count": len(execs),
        "edges_crossing_tag": crossing,
        "seeds_intact": all(s in by_id for s in seed_ids),
        "unmatched_artifacts": unmatched_artifacts,
        "label_mismatches": label_mismatches,
        "unmatched_findings": unmatched_findings,
        "missed_edges": missed_edges,
        "extra_edges": extra_edges,
        "extra_nodes": extra_nodes,
        "shared_nodes": shared_nodes,
        "notes": notes,
        "resolved_ids": resolved,
    }


def file_layer_counts(project: Path) -> dict:
    return {
        "knowledge_json": len(list((project / "knowledge").glob("*.json"))) if (project / "knowledge").exists() else 0,
        "synthesis_md": len(list((project / "synthesis").glob("*.md"))) if (project / "synthesis").exists() else 0,
        "repair_queue_lines": (
            sum(1 for _ in open(project / ".wheeler" / "repair_queue.jsonl"))
            if (project / ".wheeler" / "repair_queue.jsonl").exists()
            else 0
        ),
    }


def cleanup(tag: str) -> dict:
    driver, session = _neo4j_session()
    try:
        before = session.run(
            "MATCH (n) WHERE n._wheeler_project = $tag RETURN count(n) AS c", tag=tag
        ).single()["c"]
        session.run("MATCH (n) WHERE n._wheeler_project = $tag DETACH DELETE n", tag=tag).consume()
        after = session.run(
            "MATCH (n) WHERE n._wheeler_project = $tag RETURN count(n) AS c", tag=tag
        ).single()["c"]
    finally:
        session.close()
        driver.close()
    return {"deleted": before, "remaining": after}


# ---------------------------------------------------------------------------
# Strategy 0: oracle
# ---------------------------------------------------------------------------


def gold_manifest(gold: dict, project: Path, seeds: dict[str, str]) -> dict:
    alias: dict[str, str] = {"exec": "@exec", **{k: v for k, v in seeds.items()}}
    ex = gold["nodes"]["execution"]
    nodes = [{"alias": "@exec", "type": "execution", "kind": ex["kind"],
              "description": ex["description"], "status": "completed"}]
    for i, (key, f) in enumerate(gold["nodes"]["findings"].items(), 1):
        alias[f"finding:{key}"] = f"@f{i}"
        nodes.append({"alias": f"@f{i}", "type": "finding",
                      "description": f["text"], "confidence": f["confidence"]})
    artifacts = []
    for i, (rel, spec) in enumerate(gold["nodes"]["artifacts"].items(), 1):
        alias[rel] = f"@a{i}"
        artifacts.append({"alias": f"@a{i}", "path": rel,
                          "title": spec["title"], "description": spec["description"]})
    edges = [[alias[s], r, alias[d]] for s, r, d in gold["edges"]]
    return {"nodes": nodes, "artifacts": artifacts, "edges": edges}


def run_oracle(cfg, gold: dict, project: Path, seeds: dict[str, str]) -> dict:
    from wheeler.tools.graph_tools.batch import register_batch

    manifest = gold_manifest(gold, project, seeds)
    (project / "provenance.oracle.yaml").write_text(json.dumps(manifest, indent=2) + "\n")
    reset_wheeler_caches()
    t0 = time.monotonic()
    try:
        report = asyncio.run(register_batch(manifest, cfg, base_dir=project))
    finally:
        reset_wheeler_caches()
    wall = round(time.monotonic() - t0, 3)
    summary = {
        "status": report.get("status"),
        "counts": report.get("counts"),
        "failures": report.get("failures"),
        "item_errors": [
            r for sec in ("nodes", "artifacts", "edges")
            for r in (report.get(sec) or []) if r.get("status") not in ("created", "linked", "unchanged", "updated")
        ],
    }
    if report.get("errors"):
        summary["errors"] = report["errors"]
    return {"wall_clock_s": wall, "oracle_report": summary}


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------


def one_run(ns: argparse.Namespace, k: int) -> Path:
    ts = _utc_ts()
    tag = f"batchreg-{ts}-s{ns.strategy}-r{k}"
    run_dir = RUNS / f"{ts}-s{ns.strategy}-r{k}"
    run_dir.mkdir(parents=True, exist_ok=False)
    gold = load_gold()
    project = prepare_project(run_dir, tag, ns.strategy)
    cfg = build_config(project, tag)

    results: dict = {
        "strategy": ns.strategy,
        "strategy_name": STRATEGY_NAMES[ns.strategy],
        "model": None if ns.strategy == 0 else ns.model,
        "repeat_index": k,
        "run_dir": str(run_dir),
        "project_dir": str(project),
        "project_tag": tag,
        "started_at": _now_iso(),
        "worktree": str(WORKTREE),
    }
    print(f"[{tag}] project at {project}")

    seeds: dict[str, str] = {}
    try:
        seeds = seed_graph(cfg, gold, project)
        results["seeds"] = seeds
        render_brief(project, seeds)
        print(f"[{tag}] seeded {seeds}")

        if ns.strategy == 0:
            results.update(run_oracle(cfg, gold, project, seeds))
            results["turns"] = 0
            results["tokens"] = {k_: 0 for k_ in USAGE_KEYS} | {"total_input_incl_cache": 0}
            results["tool_calls"] = {}
            results["mutation_calls"] = 1
            results["returncode"] = 0
            print(f"[{tag}] oracle: {results['oracle_report']['status']} in {results['wall_clock_s']}s")
        else:
            prompt = render_prompt(ns.strategy, project, seeds)
            (run_dir / "prompt.md").write_text(prompt)
            cmd = claude_command(prompt, ns.model, ns.max_turns, ns.strategy)
            (run_dir / "command.txt").write_text(shlex.join(cmd) + "\n")
            print(f"[{tag}] launching claude ({ns.model}, max {ns.max_turns} turns)")
            results.update(launch(cmd, project, run_dir, ns.timeout_s))
            results.update(parse_transcript(run_dir / "transcript.jsonl"))
            print(
                f"[{tag}] claude exited rc={results['returncode']} in {results['wall_clock_s']}s, "
                f"{results['turns']} turns, {results['tokens']['output_tokens']} output tokens"
            )
    finally:
        results["finished_at"] = _now_iso()
        if seeds:
            results["score"] = score(tag, gold, seeds)
            s = results["score"]
            print(
                f"[{tag}] score: nodes {s['nodes_matched']}/{s['nodes_expected']} "
                f"edges {s['edges_matched']}/{s['edges_expected']} "
                f"(recall {s['edge_recall']}, precision {s['edge_precision']}, "
                f"{s['edges_created']} edges, {s['nodes_created']} nodes created)"
            )
        else:
            results["score"] = {"error": "seeding failed, nothing to score"}
        results["files"] = file_layer_counts(project)
        if ns.keep:
            results["cleanup"] = {"skipped": True, "tag": tag}
            print(f"[{tag}] --keep: graph nodes left in place under tag {tag}")
        else:
            results["cleanup"] = cleanup(tag)
            print(f"[{tag}] cleanup: {results['cleanup']}")
        (run_dir / "results.json").write_text(json.dumps(results, indent=2, default=str) + "\n")
        print(f"[{tag}] wrote {run_dir / 'results.json'}")
    return run_dir


def plan(ns: argparse.Namespace) -> None:
    project = RUNS / f"<ts>-s{ns.strategy}-r1" / "project"
    seeds = {"QUESTION_ID": "Q-plan0000", "DATASET_ID": "D-plan0000"}
    prompt = render_prompt(ns.strategy, project, seeds)
    cmd = claude_command(prompt, ns.model, ns.max_turns, ns.strategy)
    print("# cwd:", project)
    print("# env: os.environ minus the direct API credential and CLAUDECODE, plus")
    print(f"#      PYTHONPATH={WORKTREE} WHEELER_NO_KEYCHAIN=1 WHEELER_PROJECT_ROOT=<project> NEO4J_*=<scratch>")
    print("# command:")
    print(shlex.join(cmd[:2]), shlex.quote("<prompt below>"), shlex.join(cmd[3:]))
    print()
    print("# .mcp.json:")
    print(json.dumps(mcp_json(ns.strategy), indent=2))
    print()
    print("# prompt:")
    print(prompt)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strategy", type=int, required=True, choices=sorted(STRATEGY_NAMES))
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--keep", action="store_true", help="leave the tagged nodes in Neo4j after scoring")
    ap.add_argument("--plan", action="store_true", help="print the command and prompt, run nothing")
    ap.add_argument("--max-turns", type=int, default=250)
    ap.add_argument("--timeout-s", type=float, default=3 * 3600, help="kill claude after this many seconds")
    ns = ap.parse_args()

    if ns.plan:
        plan(ns)
        return
    assert_worktree_import()
    if not FIXTURE.exists():
        sys.exit(f"fixture missing at {FIXTURE}: run make_fixture.py first")
    if ns.strategy != 0 and shutil.which("claude") is None:
        sys.exit("claude CLI not found on PATH")
    for k in range(1, ns.repeat + 1):
        one_run(ns, k)


if __name__ == "__main__":
    main()
