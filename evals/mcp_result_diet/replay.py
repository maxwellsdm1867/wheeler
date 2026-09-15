"""Replay recorded MCP results through the new result shaping and count the bytes saved.

Offline, no graph, no model: reads Claude Code transcripts (`*.jsonl`), finds
every tool_result of a Wheeler MCP tool, applies the same shaping the wrappers
now apply by default, and reports bytes before and after per tool. Bytes here
are what the model re-reads on every later turn of the session.

    .venv/bin/python evals/mcp_result_diet/replay.py ~/.claude/projects/<project-dir>
"""

from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict

from wheeler.mcp_shared import _compact_write_result, _strip_empty, _trim_rows, _trim_text

ENSURE_ECHO = ("path", "stored_path", "hash", "previous_hash", "path_upgraded")


def shape(tool: str, payload: dict):
    if tool == "update_node":
        payload.pop("changes", None)
        return payload
    if tool == "ensure_artifact":
        if "error" in payload:
            return payload
        out = {k: v for k, v in payload.items() if k not in ENSURE_ECHO}
        if not out.get("stale_downstream"):
            out.pop("stale_downstream", None)
        return _compact_write_result(out)
    if tool.startswith("add_"):
        return _compact_write_result(payload)
    if tool == "show_node":
        payload.pop("change_log", None)
        return _strip_empty(payload)
    if tool.startswith("query_"):
        return _trim_rows(payload)
    if tool == "search_findings":
        for r in payload.get("results", []):
            if isinstance(r, dict) and "text" in r:
                r["text"] = _trim_text(r["text"])
        return payload
    if tool == "detect_stale":
        rows = payload.get("result", payload) if isinstance(payload, dict) else payload
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict):
                    r.pop("stored_hash", None)
                    r.pop("current_hash", None)
        return payload
    if tool == "validate_citations":
        rows = payload.get("results", [])
        payload["by_status"] = {}
        for r in rows:
            payload["by_status"][r.get("status")] = payload["by_status"].get(r.get("status"), 0) + 1
        payload["results"] = [r for r in rows if r.get("status") != "valid"]
        return payload
    if tool == "search_context":
        related = payload.get("related_nodes") or []
        if len(related) > 20:
            kept = related[:20]
            keep = {n.get("id") for n in kept} | {n.get("id") for n in payload.get("seed_nodes") or []}
            payload["related_nodes"] = kept
            payload["relationships"] = [r for r in payload.get("relationships") or [] if r.get("source") in keep and r.get("target") in keep]
            payload["truncated_related"] = True
        return payload
    if tool == "run_cypher":
        res = payload.get("results")
        if isinstance(res, list) and len(res) > 100:
            payload["results"] = res[:100]
            payload["truncated"] = True
            payload["total_rows"] = len(res)
        return payload
    return payload


def main(d: str) -> None:
    tool_of: dict[str, str] = {}
    before: dict[str, int] = defaultdict(int)
    after: dict[str, int] = defaultdict(int)
    calls: dict[str, int] = defaultdict(int)
    for f in sorted(glob.glob(d + "/*.jsonl")):
        for line in open(f, errors="ignore"):
            try:
                m = json.loads(line)
            except Exception:
                continue
            c = (m.get("message") or {}).get("content")
            if not isinstance(c, list):
                continue
            for b in c:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    tool_of[b["id"]] = b.get("name", "")
                elif b.get("type") == "tool_result":
                    name = tool_of.get(b.get("tool_use_id"), "")
                    if not name.startswith("mcp__wheeler"):
                        continue
                    tool = name.split("__")[-1]
                    cc = b.get("content")
                    text = "".join(x.get("text", "") for x in cc if isinstance(x, dict)) if isinstance(cc, list) else (cc or "")
                    try:
                        payload = json.loads(text)
                    except Exception:
                        continue
                    calls[tool] += 1
                    before[tool] += len(text)
                    # detect_stale is a bare list at the wrapper; keep the shape symmetric
                    shaped = shape(tool, payload if isinstance(payload, dict) else {"result": payload})
                    if not isinstance(payload, dict):
                        shaped = shaped.get("result", shaped)
                    after[tool] += len(json.dumps(shaped, separators=(",", ":")))
    tb = sum(before.values())
    ta = sum(after.values())
    print(f"{'tool':26} {'calls':>6} {'before KB':>10} {'after KB':>9} {'saved':>7}")
    for tool in sorted(before, key=lambda t: -(before[t] - after[t])):
        b, a = before[tool], after[tool]
        if b == 0:
            continue
        print(f"{tool:26} {calls[tool]:6d} {b/1024:10.1f} {a/1024:9.1f} {100*(b-a)/b:6.0f}%")
    print(f"{'TOTAL':26} {sum(calls.values()):6d} {tb/1024:10.1f} {ta/1024:9.1f} {100*(tb-ta)/tb:6.0f}%   (~{(tb-ta)//4} tokens)")


if __name__ == "__main__":
    main(sys.argv[1])
