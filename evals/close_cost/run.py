#!/usr/bin/env python
"""Experiment harness: what does the mechanical half of a /wh:close cost, and
is it cheaper to hand that half to one subagent?

Two arms, identical work, identical output contract:

  inline   the main session reads the prior-session context, then runs the
           sweep itself
  split    the main session reads the prior-session context, then delegates the
           WHOLE sweep to exactly one subagent and relays its digest

Only the mechanical phases of `/wh:close` are measured: 1.1 (window boundary
plus the malformed-close check), 1.2 (recent entities), 1.3 (orphans), 1.6
(`detect_stale`), 2.1 (per-type inventory), 2.4 (`validate_citations`) and 2.6
(`graph_consistency_check`). The judgment phases (1.3b, 1.3c, orphan grouping,
the synthesis narrative) need the scientist and stay in the main session in
BOTH arms, so they cancel and are deliberately excluded.

Per run:
  1. create ``runs/<UTC ts>-<arm>-<context>/project/``: the fixture files, the
     context filler for the chosen size, a scratch ``wheeler.yaml`` with a
     unique ``neo4j.project_tag`` and a read-only ``.mcp.json`` (core, query
     and ops servers, NO mutations server)
  2. seed the whole fixture graph into that tag through ``execute_tool``
     (``register_batch`` for nodes, artifacts and edges), then stamp the
     designed timestamps and touch the one script that must read as stale
  3. launch ``claude -p`` headlessly on the subscription, parse the
     stream-json transcript, score the DIGEST line against gold
  4. write ``results.json`` and, unless ``--keep``, DETACH DELETE the tag

Runs must be executed ONE AT A TIME. `run_cypher` is not project-scoped, the
database is shared, and a second concurrent run's nodes would land inside the
window of the first. The harness refuses to start while another run's tag is
still in the database or its lock file is held.

Run from the worktree root with the worktree first on PYTHONPATH::

    PYTHONPATH=$PWD .venv/bin/python evals/close_cost/run.py --check-gold
    PYTHONPATH=$PWD .venv/bin/python evals/close_cost/run.py --arm split --context small --plan
    PYTHONPATH=$PWD .venv/bin/python evals/close_cost/run.py --arm inline --context small
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[1]
PYTHON = WORKTREE / ".venv" / "bin" / "python"
FIXTURE = HERE / "fixture"
FILES = FIXTURE / "files"
CONTEXT = FIXTURE / "context"
PROMPTS = HERE / "prompts"
RUNS = HERE / "runs"
LOCK = HERE / ".run.lock"

ARMS = ("inline", "split")
CONTEXT_SIZES = ("small", "large")
TAG_PREFIX = "closecost-"

# Local experiment database. Isolation is by project_tag, never by database.
NEO4J = {
    "uri": "bolt://localhost:7717",
    "username": "neo4j",
    "password": "research-graph",
    "database": "neo4j",
}

SERVERS = ("core", "query", "ops")
TOOL_PREFIXES = tuple(f"mcp__wheeler_{name}__" for name in SERVERS)

# Fraction of the context target below which a run is marked as not having
# achieved its inflation.
CONTEXT_FLOOR = 0.70


# ---------------------------------------------------------------------------
# Paths, config, caches
# ---------------------------------------------------------------------------


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def assert_worktree_import() -> None:
    """Refuse to run if the shared venv's install shadows this worktree."""
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
        "# Scratch project for the /wh:close cost experiment.\n"
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


def server_env() -> dict[str, str]:
    return {
        "PYTHONPATH": str(WORKTREE),
        "WHEELER_DISCLOSURE": "pointer",
        # Belt and braces so a server can never resolve to another graph: the
        # keychain layer outranks wheeler.yaml, and env outranks the keychain.
        "WHEELER_NO_KEYCHAIN": "1",
        "NEO4J_URI": NEO4J["uri"],
        "NEO4J_USERNAME": NEO4J["username"],
        "NEO4J_PASSWORD": NEO4J["password"],
        "NEO4J_DATABASE": NEO4J["database"],
    }


def mcp_json() -> dict:
    """Read-only server set: core, query and ops. No mutations server."""
    env = server_env()
    servers = {
        f"wheeler_{name}": {
            "type": "stdio",
            "command": str(PYTHON),
            "args": ["-m", f"wheeler.mcp_{name}"],
            "env": env,
        }
        for name in SERVERS
    }
    return {"mcpServers": servers}


def subprocess_env(project: Path) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        # Runs use the claude CLI on the subscription: drop any direct API
        # credential the environment happens to carry.
        if not (k.startswith("ANTHROPIC") and k.endswith("_API_KEY"))
    }
    # A claude launched from inside a Claude Code session refuses to start
    # while the parent's marker is present.
    env.pop("CLAUDECODE", None)
    env.update(server_env())
    env["WHEELER_PROJECT_ROOT"] = str(project)
    return env


# ---------------------------------------------------------------------------
# Neo4j helpers
# ---------------------------------------------------------------------------


def _neo4j_session():
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(NEO4J["uri"], auth=(NEO4J["username"], NEO4J["password"]))
    return driver, driver.session(database=NEO4J["database"])


def _rows(session, query: str, **params) -> list[dict]:
    return [dict(r) for r in session.run(query, **params)]


def foreign_tags() -> list[dict]:
    """Tags from earlier close-cost runs still in the shared database."""
    driver, session = _neo4j_session()
    try:
        return _rows(
            session,
            "MATCH (n) WHERE n._wheeler_project STARTS WITH $p "
            "RETURN n._wheeler_project AS tag, count(n) AS nodes ORDER BY tag",
            p=TAG_PREFIX,
        )
    finally:
        session.close()
        driver.close()


def preflight() -> None:
    """Refuse to start while another run is live. Raw Cypher is not scoped."""
    if LOCK.exists():
        sys.exit(
            f"{LOCK} exists: another close-cost run is in flight (or crashed).\n"
            "Runs must be one at a time: raw Cypher is not project-scoped, so a "
            "second run's nodes land inside the first run's window.\n"
            f"If nothing is running, delete {LOCK} and re-check for stray tags."
        )
    stale = foreign_tags()
    if stale:
        listing = ", ".join(f"{r['tag']} ({r['nodes']} nodes)" for r in stale)
        sys.exit(
            f"close-cost tags are still in the database: {listing}.\n"
            "Clean them up before starting, or the window queries will see them:\n"
            "  MATCH (n) WHERE n._wheeler_project = '<tag>' DETACH DELETE n"
        )


def cleanup(tag: str) -> dict:
    driver, session = _neo4j_session()
    try:
        before = session.run(
            "MATCH (n) WHERE n._wheeler_project = $tag RETURN count(n) AS c", tag=tag
        ).single()["c"]
        session.run(
            "MATCH (n) WHERE n._wheeler_project = $tag DETACH DELETE n", tag=tag
        ).consume()
        after = session.run(
            "MATCH (n) WHERE n._wheeler_project = $tag RETURN count(n) AS c", tag=tag
        ).single()["c"]
    finally:
        session.close()
        driver.close()
    return {"deleted": before, "remaining": after}


# ---------------------------------------------------------------------------
# Fixture, project preparation and seeding
# ---------------------------------------------------------------------------


def load_graph() -> dict:
    return json.loads((FIXTURE / "graph.json").read_text())


def load_gold() -> dict:
    return json.loads((FIXTURE / "gold.json").read_text())


def load_context_manifest() -> dict:
    return json.loads((CONTEXT / "manifest.json").read_text())


def context_files(size: str) -> list[str]:
    """Project-relative paths of the filler files for one context size."""
    info = load_context_manifest()["targets"][size]
    return [f"context/{Path(f['path']).name}" for f in info["files"]]


def prepare_project(run_dir: Path, tag: str, size: str) -> Path:
    project = run_dir / "project"
    shutil.copytree(FILES, project)
    (project / "context").mkdir()
    for src in sorted((CONTEXT / size).glob("*.md")):
        shutil.copy2(src, project / "context" / src.name)
    (project / "wheeler.yaml").write_text(wheeler_yaml(tag))
    (project / ".mcp.json").write_text(json.dumps(mcp_json(), indent=2) + "\n")
    return project


class SeedError(RuntimeError):
    pass


def _stamps(graph: dict, start: datetime) -> dict[str, str]:
    """Symbolic key -> ISO timestamp, resolved from the fixture's hour offsets."""
    out: dict[str, str] = {}
    for item in graph["nodes"] + graph["artifacts"]:
        out[item["key"]] = (
            start - timedelta(hours=float(item["hours_ago"]))
        ).isoformat(timespec="seconds")
    draft = graph["draft"]
    out[draft["key"]] = (
        start - timedelta(hours=float(draft["hours_ago"]))
    ).isoformat(timespec="seconds")
    return out


async def _seed(cfg, graph: dict, project: Path) -> dict:
    """Two register_batch calls, then the timestamp stamp, then the stale touch."""
    from wheeler.tools.graph_tools.batch import register_batch

    manifest_a = {
        "nodes": [
            {"alias": f"@{n['key']}", "type": n["type"], **n["fields"]}
            for n in graph["nodes"]
        ],
        "artifacts": [
            {"alias": f"@{a['key']}", "path": a["path"], **a["fields"]}
            for a in graph["artifacts"]
        ],
        "edges": [[f"@{s}", rel, f"@{d}"] for s, rel, d in graph["edges"]],
    }
    report_a = await register_batch(manifest_a, cfg, base_dir=project)
    if report_a["status"] != "ok":
        raise SeedError(f"batch A {report_a['status']}: {json.dumps(report_a)[:1500]}")
    ids: dict[str, str] = {k.lstrip("@"): v for k, v in report_a["ids"].items()}

    # The draft Document cites real node ids, so it can only be written once
    # the ids exist. Render it, then register it in a second batch.
    draft = graph["draft"]
    template = (project / draft["template"]).read_text()
    body = template
    for i, key in enumerate(draft["cites"], start=1):
        body = body.replace("{CITE%d}" % i, ids[key])
    body = body.replace("{FAKE}", draft["fake"])
    (project / draft["out"]).write_text(body)

    manifest_b = {
        "artifacts": [
            {"alias": f"@{draft['key']}", "path": draft["out"], **draft["fields"]}
        ],
    }
    report_b = await register_batch(manifest_b, cfg, base_dir=project)
    if report_b["status"] != "ok":
        raise SeedError(f"batch B {report_b['status']}: {json.dumps(report_b)[:1500]}")
    ids.update({k.lstrip("@"): v for k, v in report_b["ids"].items()})

    return {
        "ids": ids,
        "nodes": len(ids),
        "edges": len(graph["edges"]),
        "draft_path": str(project / draft["out"]),
    }


def stamp_timestamps(tag: str, graph: dict, ids: dict[str, str], stamps: dict[str, str]) -> dict:
    """Write the designed instants straight into Neo4j.

    `update_node` always overwrites `updated` with now, so it cannot express a
    node that is older than this moment. A direct scoped SET is the only way to
    build a window. Only the timestamp fields are touched; the knowledge JSON
    keeps the instant it was written at, which is invisible to
    `graph_consistency_check` (it compares id inventories, not fields).
    """
    execution_keys = {n["key"] for n in graph["nodes"] if n["type"] == "execution"}
    bad = graph["malformed_close_key"]
    driver, session = _neo4j_session()
    touched = 0
    try:
        for key, node_id in ids.items():
            ts = stamps[key]
            session.run(
                "MATCH (n) WHERE n._wheeler_project = $tag AND n.id = $id "
                "SET n.date = $ts, n.updated = $ts",
                tag=tag, id=node_id, ts=ts,
            ).consume()
            if key in execution_keys:
                session.run(
                    "MATCH (n:Execution) WHERE n._wheeler_project = $tag AND n.id = $id "
                    "SET n.started_at = $ts, n.ended_at = $ts",
                    tag=tag, id=node_id, ts=ts,
                ).consume()
            touched += 1
        # The malformed close: no started_at at all.
        #
        # The act's phase 1.1 accepts `IS NULL OR = ""`, but phase 2.1 runs
        # `datetime(x.started_at)` over every Execution in the project and an
        # empty string makes Neo4j raise, which would turn this fixture into a
        # test of error recovery instead of a cost measurement. NULL exercises
        # the same 1.1 branch and leaves 2.1 well defined.
        session.run(
            "MATCH (n:Execution) WHERE n._wheeler_project = $tag AND n.id = $id "
            "REMOVE n.started_at",
            tag=tag, id=ids[bad],
        ).consume()
    finally:
        session.close()
        driver.close()
    return {"stamped": touched, "malformed_close": ids[bad]}


def touch_stale_script(project: Path, graph: dict) -> str:
    path = project / graph["stale"]["path"]
    with path.open("a") as fh:
        fh.write(graph["stale"]["append"])
    return str(path)


def seed_all(cfg, graph: dict, project: Path, tag: str, start: datetime) -> dict:
    reset_wheeler_caches()
    t0 = time.monotonic()
    try:
        out = asyncio.run(_seed(cfg, graph, project))
    finally:
        reset_wheeler_caches()
    stamps = _stamps(graph, start)
    out["stamp"] = stamp_timestamps(tag, graph, out["ids"], stamps)
    out["stale_file"] = touch_stale_script(project, graph)
    out["since"] = (start - timedelta(hours=float(graph["since_hours_ago"]))).isoformat(
        timespec="seconds"
    )
    out["seed_wall_s"] = round(time.monotonic() - t0, 3)
    return out


# ---------------------------------------------------------------------------
# Gold resolution and scoring
# ---------------------------------------------------------------------------


def resolve_gold(gold: dict, ids: dict[str, str], since: str) -> dict:
    return {
        "since": since,
        "malformed_closes": gold["malformed_closes"],
        "window_ids": sorted(ids[k] for k in gold["window_ids"]),
        "orphan_ids": sorted(ids[k] for k in gold["orphan_ids"]),
        "inventory": dict(gold["inventory"]),
        "stale": sorted(ids[k] for k in gold["stale"]),
        "citations": dict(gold["citations"]),
        "consistency_ok": gold["consistency_ok"],
    }


def _norm_ts(value) -> str:
    """Compare timestamps by instant, not by spelling."""
    if not isinstance(value, str) or not value.strip():
        return ""
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc).isoformat()
    except ValueError:
        return text


def _set_scores(got, want: list[str]) -> dict:
    if not isinstance(got, list) or not all(isinstance(x, str) for x in got):
        return {"recall": 0.0, "precision": 0.0, "exact": False, "note": "not a list of ids"}
    g, w = set(got), set(want)
    recall = len(g & w) / len(w) if w else 1.0
    precision = len(g & w) / len(g) if g else 0.0
    return {
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "exact": g == w,
        "missing": sorted(w - g)[:10],
        "extra": sorted(g - w)[:10],
        "note": "",
    }


def score_digest(digest, gold: dict) -> dict:
    if not isinstance(digest, dict):
        return {"ok": False, "error": "no DIGEST json"}
    out: dict = {}
    out["window"] = _set_scores(digest.get("window_ids"), gold["window_ids"])
    out["orphan"] = _set_scores(digest.get("orphan_ids"), gold["orphan_ids"])
    out["stale"] = _set_scores(digest.get("stale"), gold["stale"])

    inv = digest.get("inventory")
    inv_ok = isinstance(inv, dict) and all(
        inv.get(k) == v for k, v in gold["inventory"].items()
    )
    out["inventory"] = {
        "exact": bool(inv_ok),
        "got": inv if isinstance(inv, dict) else None,
        "want": gold["inventory"],
    }

    out["malformed_closes"] = {
        "exact": digest.get("malformed_closes") == gold["malformed_closes"],
        "got": digest.get("malformed_closes"),
        "want": gold["malformed_closes"],
    }
    cit = digest.get("citations")
    out["citations"] = {
        "exact": isinstance(cit, dict)
        and cit.get("total") == gold["citations"]["total"]
        and cit.get("valid") == gold["citations"]["valid"],
        "got": cit,
        "want": gold["citations"],
    }
    out["since"] = {
        "exact": _norm_ts(digest.get("since")) == _norm_ts(gold["since"]),
        "got": digest.get("since"),
        "want": gold["since"],
    }
    out["consistency_ok"] = {
        "exact": digest.get("consistency_ok") == gold["consistency_ok"],
        "got": digest.get("consistency_ok"),
        "want": gold["consistency_ok"],
    }
    out["all_exact"] = bool(
        out["window"]["exact"] and out["orphan"]["exact"] and out["stale"]["exact"]
        and out["inventory"]["exact"] and out["malformed_closes"]["exact"]
        and out["citations"]["exact"] and out["since"]["exact"]
        and out["consistency_ok"]["exact"]
    )
    out["ok"] = True
    return out


DIGEST_RE = re.compile(r"^\s*DIGEST\s+(.*\S)\s*$")


def extract_digest(texts: list[str]) -> tuple[object | None, str | None]:
    """The last parseable 'DIGEST <json>' line across the given texts."""
    for text in reversed(texts):
        for ln in reversed(text.splitlines()):
            m = DIGEST_RE.match(ln)
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


def render_prompt(arm: str, project: Path, size: str, since: str) -> str:
    sweep = (PROMPTS / "_sweep.md").read_text().strip()
    digest = (PROMPTS / "_digest.md").read_text().strip()
    files = context_files(size)
    listing = "\n".join(f"- `{p}`" for p in files)
    body = (PROMPTS / f"{arm}.md").read_text()
    subs = {
        "SWEEP": sweep,
        "DIGEST": digest,
        "PROJECT_DIR": str(project),
        "SINCE": since,
        "N_CONTEXT_FILES": str(len(files)),
        "CONTEXT_FILE_LIST": listing,
    }
    # SWEEP carries {PROJECT_DIR} and {SINCE} of its own, so substitute twice.
    for _ in range(2):
        for key, value in subs.items():
            body = body.replace("{" + key + "}", value)
    return body.strip() + "\n"


def allowed_tools(arm: str) -> list[str]:
    tools = [f"mcp__wheeler_{name}" for name in SERVERS] + ["Read", "Glob", "Grep"]
    if arm == "split":
        tools.append("Agent")
    return tools


def claude_command(prompt: str, model: str, max_turns: int, arm: str) -> list[str]:
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
        *allowed_tools(arm),
    ]


def launch(cmd: list[str], project: Path, out_dir: Path, timeout_s: float) -> dict:
    env = subprocess_env(project)
    t0 = time.monotonic()
    timed_out = False
    with open(out_dir / "transcript.jsonl", "wb") as out, open(out_dir / "stderr.log", "wb") as err:
        proc = subprocess.Popen(
            cmd, cwd=project, env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL
        )
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

USAGE_KEYS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


def _short_tool(name: str) -> str:
    for prefix in TOOL_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _ctx_of(usage: dict) -> int:
    return int(
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
    )


def parse_transcript(path: Path) -> dict:
    """Usage once per assistant message id, split into parent and subagent.

    Claude Code emits one assistant line per content block, all sharing one
    ``message.id`` and repeating the same ``usage``, so usage is taken once per
    id. A line carrying ``parent_tool_use_id`` came from inside an Agent call.

    The final ``result`` line's ``usage`` block is NOT a session total when a
    subagent ran: it carries only the parent's last exchange. ``modelUsage``
    and ``total_cost_usd`` on the same line ARE session totals and include the
    subagent. Both are recorded; the report reads ``modelUsage``.
    """
    out: dict = {
        "transcript_lines": 0,
        "unparseable_lines": 0,
        "assistant_lines": 0,
        "turns": 0,
        "parent_turns": 0,
        "subagent_turns": 0,
        "subagent_assistant_lines": 0,
        "subagent_usage_visible": False,
        "agent_calls": 0,
        "tokens": {k: 0 for k in USAGE_KEYS},
        "parent_tokens": {k: 0 for k in USAGE_KEYS},
        "subagent_tokens": {k: 0 for k in USAGE_KEYS},
        "parent_context_peak_tokens": 0,
        "subagent_context_peak_tokens": 0,
        "context_first_turn_tokens": 0,
        "tool_calls": {},
        "tool_call_sequence": [],
        "sweep_tool_calls": 0,
        "parent_sweep_tool_calls": 0,
        "context_reads": 0,
        "consistency_graph_only": None,
        "result": {},
        "final_text": "",
        "digest": None,
        "digest_line": None,
    }
    if not path.exists():
        return out

    usage_by_msg: dict[str, tuple[dict, bool]] = {}
    seen_tool_ids: set[str] = set()
    tool_seq: list[tuple[str, bool]] = []
    assistant_texts: list[str] = []
    first_turn_ctx: int | None = None
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
            sub = bool(line.get("parent_tool_use_id"))
            if sub:
                out["subagent_assistant_lines"] += 1
            msg = line.get("message") or {}
            mid = msg.get("id")
            if not mid:
                anon += 1
                mid = f"anon-{anon}"
            usage = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
            if mid not in usage_by_msg:
                usage_by_msg[mid] = (usage, sub)
                if not sub and first_turn_ctx is None:
                    first_turn_ctx = _ctx_of(usage)
            for block in msg.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str) and not sub:
                    assistant_texts.append(block["text"])
                if block.get("type") != "tool_use":
                    continue
                bid = block.get("id") or f"anon-tool-{len(seen_tool_ids)}"
                if bid in seen_tool_ids:
                    continue
                seen_tool_ids.add(bid)
                name = str(block.get("name") or "?")
                tool_seq.append((_short_tool(name), sub))
                if name == "Agent" or name == "Task":
                    out["agent_calls"] += 1
                if name.startswith(TOOL_PREFIXES):
                    out["sweep_tool_calls"] += 1
                    if not sub:
                        out["parent_sweep_tool_calls"] += 1
                if name == "Read":
                    target = str((block.get("input") or {}).get("file_path") or "")
                    if "/context/" in target or target.startswith("context/"):
                        out["context_reads"] += 1

        elif ltype == "user":
            # Tool results ride on user lines. graph_consistency_check's
            # graph_only list is an artifact of the shared database; record how
            # big it was so the report can say how much of the sweep payload it
            # accounted for.
            msg = line.get("message") or {}
            for block in msg.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                content = block.get("content")
                text = ""
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                if '"graph_only"' not in text:
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                only = payload.get("graph_only") if isinstance(payload, dict) else None
                if isinstance(only, list):
                    out["consistency_graph_only"] = len(only)
                    out["consistency_result_chars"] = len(text)

        elif ltype == "result":
            res = {}
            for key in ("subtype", "num_turns", "duration_ms", "duration_api_ms",
                        "total_cost_usd", "is_error"):
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

    for usage, sub in usage_by_msg.values():
        bucket = out["subagent_tokens"] if sub else out["parent_tokens"]
        for k in USAGE_KEYS:
            v = usage.get(k)
            if isinstance(v, (int, float)):
                bucket[k] += int(v)
                out["tokens"][k] += int(v)
        ctx = _ctx_of(usage)
        key = "subagent_context_peak_tokens" if sub else "parent_context_peak_tokens"
        out[key] = max(out[key], ctx)
        out["turns"] += 1
        if sub:
            out["subagent_turns"] += 1
        else:
            out["parent_turns"] += 1

    for bucket in ("tokens", "parent_tokens", "subagent_tokens"):
        out[bucket]["total_input_incl_cache"] = (
            out[bucket]["input_tokens"]
            + out[bucket]["cache_creation_input_tokens"]
            + out[bucket]["cache_read_input_tokens"]
        )
    out["context_first_turn_tokens"] = first_turn_ctx or 0
    out["subagent_usage_visible"] = out["subagent_assistant_lines"] > 0
    out["tool_calls"] = dict(Counter(n for n, _ in tool_seq).most_common())
    out["tool_call_sequence"] = [n for n, _ in tool_seq]
    texts = assistant_texts + ([out["final_text"]] if out["final_text"] else [])
    out["digest"], out["digest_line"] = extract_digest(texts)
    return out


def session_totals(parsed: dict) -> dict:
    """Session-wide token and cost totals that include any subagent.

    ``result.usage`` is the parent's final exchange only once an Agent call has
    run, so it undercounts the split arm by orders of magnitude. ``modelUsage``
    aggregates every model the session used, subagent included, and matches the
    per-message sum on runs with no subagent.
    """
    mu = (parsed.get("result") or {}).get("modelUsage") or {}
    totals = {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0}
    for row in mu.values():
        if not isinstance(row, dict):
            continue
        totals["input"] += int(row.get("inputTokens") or 0)
        totals["cache_read"] += int(row.get("cacheReadInputTokens") or 0)
        totals["cache_creation"] += int(row.get("cacheCreationInputTokens") or 0)
        totals["output"] += int(row.get("outputTokens") or 0)
    if not mu:  # no modelUsage: fall back to the per-message sum
        t = parsed["tokens"]
        totals = {
            "input": t["input_tokens"],
            "cache_read": t["cache_read_input_tokens"],
            "cache_creation": t["cache_creation_input_tokens"],
            "output": t["output_tokens"],
        }
        totals["source"] = "per_message_sum"
    else:
        totals["source"] = "modelUsage"
    totals["context_total"] = totals["input"] + totals["cache_read"] + totals["cache_creation"]
    cost = (parsed.get("result") or {}).get("total_cost_usd")
    totals["cost_usd"] = float(cost) if isinstance(cost, (int, float)) else 0.0
    return totals


# ---------------------------------------------------------------------------
# check-gold
# ---------------------------------------------------------------------------

WINDOW_Q = (
    "MATCH (n) WHERE n._wheeler_project = $tag "
    "AND coalesce(n.updated, n.date) IS NOT NULL "
    "AND datetime(coalesce(n.updated, n.date)) >= datetime($since) "
    "AND NOT n:Execution AND NOT n:Paper RETURN n.id AS id"
)
ORPHAN_Q = (
    "MATCH (n) WHERE n._wheeler_project = $tag "
    "AND (coalesce(n.updated, n.date) IS NULL "
    "     OR datetime(coalesce(n.updated, n.date)) >= datetime($since)) "
    "AND NOT n:Execution AND NOT n:Paper "
    "AND NOT (n)-[:WAS_GENERATED_BY]->(:Execution) RETURN n.id AS id"
)
INVENTORY_Q = {
    "Finding": "MATCH (f:Finding) WHERE f._wheeler_project = $tag AND datetime(f.date) >= datetime($since) RETURN f.id AS id",
    "Hypothesis": "MATCH (h:Hypothesis) WHERE h._wheeler_project = $tag AND datetime(coalesce(h.updated, h.date)) >= datetime($since) RETURN h.id AS id",
    "OpenQuestion": "MATCH (q:OpenQuestion) WHERE q._wheeler_project = $tag AND datetime(coalesce(q.date, q.date_added)) >= datetime($since) RETURN q.id AS id",
    "Plan": "MATCH (pl:Plan) WHERE pl._wheeler_project = $tag AND datetime(pl.updated) >= datetime($since) RETURN pl.id AS id",
    "Execution": "MATCH (x:Execution) WHERE x._wheeler_project = $tag AND datetime(x.started_at) >= datetime($since) RETURN x.id AS id",
    "Document": "MATCH (w:Document) WHERE w._wheeler_project = $tag AND datetime(w.date) >= datetime($since) RETURN w.id AS id",
}


async def _tool_phases(cfg, draft_path: Path) -> dict:
    """Phases 1.6, 2.4 and 2.6 through the same code the MCP servers call."""
    from wheeler.consistency import check_consistency
    from wheeler.graph.provenance import detect_stale_scripts
    from wheeler.validation.citations import CitationStatus, validate_citations

    stale = await detect_stale_scripts(cfg)
    cites = await validate_citations(draft_path.read_text(), cfg)
    report = await check_consistency(cfg)
    return {
        "stale": sorted(s.node_id for s in stale if s.reason == "changed"),
        "stale_all": [{"id": s.node_id, "reason": s.reason} for s in stale],
        "citations": {
            "total": len(cites),
            "valid": sum(1 for c in cites if c.status == CitationStatus.VALID),
            "by_status": dict(Counter(c.status.value for c in cites)),
        },
        "consistency": {
            "json_only": len(report.json_only),
            "synthesis_missing": len(report.synthesis_missing),
            "synthesis_orphaned": len(report.synthesis_orphaned),
            "unreadable": len(report.unreadable),
            "graph_only": len(report.graph_only),
            "total_graph": report.total_graph,
            "total_json": report.total_json,
        },
    }


def check_gold(ns: argparse.Namespace) -> None:
    """Seed, run every gold query against Neo4j, print, clean up."""
    graph = load_graph()
    gold = load_gold()
    ts = _utc_ts()
    tag = f"{TAG_PREFIX}{ts}-checkgold"
    run_dir = RUNS / f"{ts}-checkgold"
    run_dir.mkdir(parents=True, exist_ok=True)
    project = prepare_project(run_dir, tag, "small")
    cfg = build_config(project, tag)
    start = datetime.now(timezone.utc)
    checks: list[dict] = []
    ok_all = False
    try:
        seed = seed_all(cfg, graph, project, tag, start)
        since = seed["since"]
        resolved = resolve_gold(gold, seed["ids"], since)
        (run_dir / "seed_ids.json").write_text(
            json.dumps({k: v for k, v in seed.items()}, indent=2, default=str) + "\n"
        )
        print(f"[{tag}] seeded {seed['nodes']} nodes, {seed['edges']} edges in {seed['seed_wall_s']}s")
        print(f"[{tag}] $since = {since}")

        driver, session = _neo4j_session()
        try:
            total = _rows(session, "MATCH (n) WHERE n._wheeler_project = $tag RETURN count(n) AS c", tag=tag)[0]["c"]
            checks.append({"check": "seeded nodes", "ok": total == len(seed["ids"]),
                           "got": total, "want": len(seed["ids"])})

            boundary = _rows(
                session,
                "MATCH (x:Execution {kind: 'close'}) WHERE x._wheeler_project = $tag "
                "AND x.started_at IS NOT NULL AND x.started_at <> '' "
                "RETURN x.started_at AS last_close ORDER BY x.started_at DESC LIMIT 1",
                tag=tag,
            )
            got_since = boundary[0]["last_close"] if boundary else None
            checks.append({"check": "1.1 window boundary", "ok": _norm_ts(got_since) == _norm_ts(since),
                           "got": got_since, "want": since})

            bad = _rows(
                session,
                "MATCH (x:Execution {kind: 'close'}) WHERE x._wheeler_project = $tag "
                "AND (x.started_at IS NULL OR x.started_at = '') RETURN x.id AS id",
                tag=tag,
            )
            checks.append({"check": "1.1 malformed closes", "ok": len(bad) == resolved["malformed_closes"],
                           "got": len(bad), "want": resolved["malformed_closes"]})

            win = sorted(r["id"] for r in _rows(session, WINDOW_Q, tag=tag, since=since))
            checks.append({"check": "1.2 window ids", "ok": win == resolved["window_ids"],
                           "got": len(win), "want": len(resolved["window_ids"]),
                           "missing": sorted(set(resolved["window_ids"]) - set(win)),
                           "extra": sorted(set(win) - set(resolved["window_ids"]))})

            orph = sorted(r["id"] for r in _rows(session, ORPHAN_Q, tag=tag, since=since))
            checks.append({"check": "1.3 orphan ids", "ok": orph == resolved["orphan_ids"],
                           "got": len(orph), "want": len(resolved["orphan_ids"]),
                           "missing": sorted(set(resolved["orphan_ids"]) - set(orph)),
                           "extra": sorted(set(orph) - set(resolved["orphan_ids"]))})

            inv = {k: len(_rows(session, q, tag=tag, since=since)) for k, q in INVENTORY_Q.items()}
            checks.append({"check": "2.1 inventory", "ok": inv == resolved["inventory"],
                           "got": inv, "want": resolved["inventory"]})
        finally:
            session.close()
            driver.close()

        reset_wheeler_caches()
        try:
            phases = asyncio.run(_tool_phases(cfg, Path(seed["draft_path"])))
        finally:
            reset_wheeler_caches()
        checks.append({"check": "1.6 detect_stale (changed)", "ok": phases["stale"] == resolved["stale"],
                       "got": phases["stale"], "want": resolved["stale"], "all": phases["stale_all"]})
        checks.append({"check": "2.4 validate_citations",
                       "ok": phases["citations"]["total"] == resolved["citations"]["total"]
                       and phases["citations"]["valid"] == resolved["citations"]["valid"],
                       "got": phases["citations"], "want": resolved["citations"]})
        cons = phases["consistency"]
        cons_ok = cons["json_only"] == 0 and cons["synthesis_missing"] == 0 and cons["synthesis_orphaned"] == 0
        checks.append({"check": "2.6 graph_consistency_check (project layers)",
                       "ok": cons_ok == resolved["consistency_ok"], "got": cons,
                       "want": {"json_only": 0, "synthesis_missing": 0, "synthesis_orphaned": 0}})

        (run_dir / "check_gold.json").write_text(
            json.dumps({"tag": tag, "since": since, "gold": resolved, "checks": checks},
                       indent=2, default=str) + "\n"
        )
        ok_all = all(c["ok"] for c in checks)
        for c in checks:
            flag = "ok " if c["ok"] else "BAD"
            extra = ""
            if not c["ok"]:
                extra = "  <- " + json.dumps({k: v for k, v in c.items() if k not in ("check", "ok")}, default=str)[:400]
            print(f"  {flag} {c['check']}: got={json.dumps(c.get('got'), default=str)[:200]} "
                  f"want={json.dumps(c.get('want'), default=str)[:200]}{extra}")
        print(f"  note: graph_only={cons['graph_only']} of {cons['total_graph']} graph ids is the "
              "shared database, not this project; it is excluded from consistency_ok by design")
        files = {
            "knowledge_json": len(list((project / "knowledge").glob("*.json"))),
            "synthesis_md": len(list((project / "synthesis").glob("*.md"))),
        }
        print(f"  files: {files}")
    finally:
        if ns.keep:
            print(f"[{tag}] --keep: graph nodes left in place under tag {tag}")
        else:
            result = cleanup(tag)
            print(f"[{tag}] cleanup: {result}")
            if result["remaining"] != 0:
                print(f"[{tag}] WARNING: {result['remaining']} nodes still tagged")
    print("check-gold:", "PASS" if ok_all else "FAIL")
    if not ok_all:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


def one_run(ns: argparse.Namespace, k: int) -> Path:
    graph = load_graph()
    gold = load_gold()
    manifest = load_context_manifest()["targets"][ns.context]
    ts = _utc_ts()
    tag = f"{TAG_PREFIX}{ts}-{ns.arm}-{ns.context}"
    run_dir = RUNS / f"{ts}-{ns.arm}-{ns.context}-r{k}"
    run_dir.mkdir(parents=True, exist_ok=False)
    project = prepare_project(run_dir, tag, ns.context)
    cfg = build_config(project, tag)
    start = datetime.now(timezone.utc)
    print(f"[{tag}] project at {project}")

    results: dict = {
        "arm": ns.arm,
        "context": ns.context,
        "context_target_tokens": manifest["target_tokens"],
        "context_fixture_tokens": manifest["estimated_tokens"],
        "context_files": manifest["n_files"],
        "model": ns.model,
        "repeat_index": k,
        "run_dir": str(run_dir),
        "project_dir": str(project),
        "project_tag": tag,
        "worktree": str(WORKTREE),
        "started_at": _now_iso(),
    }
    seed: dict = {}
    try:
        seed = seed_all(cfg, graph, project, tag, start)
        since = seed["since"]
        resolved = resolve_gold(gold, seed["ids"], since)
        (run_dir / "seed_ids.json").write_text(json.dumps(seed, indent=2, default=str) + "\n")
        print(f"[{tag}] seeded {seed['nodes']} nodes, {seed['edges']} edges in {seed['seed_wall_s']}s; "
              f"$since={since}")

        prompt = render_prompt(ns.arm, project, ns.context, since)
        (run_dir / "prompt.md").write_text(prompt)
        cmd = claude_command(prompt, ns.model, ns.max_turns, ns.arm)
        (run_dir / "command.txt").write_text(shlex.join(cmd) + "\n")
        results["gold"] = resolved
        results["seed"] = {kk: vv for kk, vv in seed.items() if kk != "ids"}

        print(f"[{tag}] launching claude ({ns.model}, arm={ns.arm}, context={ns.context}, "
              f"max {ns.max_turns} turns)")
        results.update(launch(cmd, project, run_dir, ns.timeout_s))
        results.update(parse_transcript(run_dir / "transcript.jsonl"))
        results["totals"] = session_totals(results)
        results["score"] = score_digest(results["digest"], resolved)

        achieved = max(results["parent_context_peak_tokens"], results["context_first_turn_tokens"])
        results["context_achieved_tokens"] = achieved
        results["context_target_missed"] = achieved < CONTEXT_FLOOR * manifest["target_tokens"]
        results["finished_at"] = _now_iso()
    finally:
        if ns.keep:
            results["cleanup"] = {"skipped": True, "tag": tag}
            print(f"[{tag}] --keep: graph nodes left in place under tag {tag}")
        elif seed:
            results["cleanup"] = cleanup(tag)
            print(f"[{tag}] cleanup: {results['cleanup']}")
            if results["cleanup"]["remaining"] != 0:
                print(f"[{tag}] WARNING: {results['cleanup']['remaining']} nodes still tagged")
        else:
            results["cleanup"] = cleanup(tag)
            print(f"[{tag}] seeding failed; cleanup: {results['cleanup']}")
        (run_dir / "results.json").write_text(json.dumps(results, indent=2, default=str) + "\n")

    score = results.get("score") or {}
    tot = results.get("totals") or {}
    print(
        f"[{tag}] rc={results.get('returncode')} {results.get('wall_clock_s')}s "
        f"turns={results.get('turns')} (parent {results.get('parent_turns')}, "
        f"subagent {results.get('subagent_turns')}) "
        f"context={tot.get('context_total')} cost=${tot.get('cost_usd')} "
        f"agent_calls={results.get('agent_calls')} "
        f"subagent_usage_visible={results.get('subagent_usage_visible')}"
    )
    print(
        f"[{tag}] score: all_exact={score.get('all_exact')} "
        f"window r/p={(score.get('window') or {}).get('recall')}/"
        f"{(score.get('window') or {}).get('precision')} "
        f"orphan r/p={(score.get('orphan') or {}).get('recall')}/"
        f"{(score.get('orphan') or {}).get('precision')} "
        f"inventory={(score.get('inventory') or {}).get('exact')}"
    )
    if results.get("context_target_missed"):
        print(
            f"[{tag}] CONTEXT TARGET MISSED: achieved {results['context_achieved_tokens']} tokens, "
            f"target {manifest['target_tokens']} (floor {int(CONTEXT_FLOOR * 100)} percent). "
            "Treat this run's comparison as unusable."
        )
    if results.get("agent_calls") and not results.get("subagent_usage_visible"):
        print(
            f"[{tag}] WARNING: an Agent call ran but no subagent assistant line appeared in the "
            "parent stream. This arm's token total is UNDERCOUNTED."
        )
    return run_dir


def plan(ns: argparse.Namespace) -> None:
    manifest = load_context_manifest()["targets"][ns.context]
    project = RUNS / f"<ts>-{ns.arm}-{ns.context}-r1" / "project"
    since = "<boundary close started_at, run start minus "
    since += f"{load_graph()['since_hours_ago']} hours>"
    prompt = render_prompt(ns.arm, project, ns.context, since)
    cmd = claude_command(prompt, ns.model, ns.max_turns, ns.arm)
    print("# cwd:", project)
    print("# env: os.environ minus the direct API credential and CLAUDECODE, plus")
    print(f"#      PYTHONPATH={WORKTREE} WHEELER_DISCLOSURE=pointer WHEELER_NO_KEYCHAIN=1 "
          "WHEELER_PROJECT_ROOT=<project> NEO4J_*=<scratch>")
    print(f"# project tag: {TAG_PREFIX}<ts>-{ns.arm}-{ns.context}")
    print(f"# context: {ns.context}, {manifest['n_files']} files, "
          f"{manifest['estimated_tokens']} estimated tokens (target {manifest['target_tokens']})")
    print("# .mcp.json:")
    print(json.dumps(mcp_json(), indent=2))
    print()
    print("# command:")
    print(shlex.join(cmd[:2]), shlex.quote("<prompt below>"), shlex.join(cmd[3:]))
    print()
    print("# prompt:")
    print(prompt)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", choices=ARMS, help="inline sweep, or delegated to one subagent")
    ap.add_argument("--context", choices=CONTEXT_SIZES, help="how much prior-session filler to load")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--keep", action="store_true", help="leave the tagged nodes in Neo4j afterwards")
    ap.add_argument("--plan", action="store_true", help="print the command and prompt, seed nothing")
    ap.add_argument("--check-gold", action="store_true",
                    help="seed, verify every gold set against Neo4j, clean up, exit")
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--timeout-s", type=float, default=3600, help="kill claude after this many seconds")
    ns = ap.parse_args()

    if not (FIXTURE / "graph.json").exists() or not (CONTEXT / "manifest.json").exists():
        sys.exit(f"fixture missing at {FIXTURE}: run make_fixture.py first")

    if ns.plan:
        if not (ns.arm and ns.context):
            sys.exit("--plan needs --arm and --context")
        plan(ns)
        return

    assert_worktree_import()
    preflight()
    LOCK.write_text(f"{os.getpid()} {_now_iso()}\n")
    try:
        if ns.check_gold:
            check_gold(ns)
            return
        if not (ns.arm and ns.context):
            sys.exit("--arm and --context are required (or --check-gold / --plan)")
        if shutil.which("claude") is None:
            sys.exit("claude CLI not found on PATH")
        for k in range(1, ns.repeat + 1):
            one_run(ns, k)
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
