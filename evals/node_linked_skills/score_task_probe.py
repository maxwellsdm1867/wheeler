"""Score observed reads and SQLite results, then preserve a self-contained record."""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from task_probe import CASES


def score(root: Path, output: Path, case_names: list[str] | None = None) -> None:
    manifest = json.loads((root / "fixture-manifest.json").read_text())
    controls = json.loads((root / "controls.json").read_text())
    heldout = controls.get("variant") == "heldout"
    skill_ids = {s["arguments"]["name"]: s["capture"]["node_id"] for s in manifest}
    expected_reads = {"join": [skill_ids["recording-joins"]],
                      "neighbor": [skill_ids["recording-joins"]],
                      "summary": [skill_ids["population-response"]],
                      "size": [], "schema": [], "other": []}
    cases = []
    for name, (node_id, task) in CASES.items():
        if case_names and name not in case_names:
            continue
        events = [json.loads(line) for line in (root / f"{name}.events.jsonl").read_text().splitlines()]
        context = json.loads((root / f"{name}.context.json").read_text())
        answer = json.loads((root / f"{name}.answer.json").read_text())
        actual_reads = [e["request"] for e in events if e["action"] == "read"]
        queries = [e for e in events if e["action"] == "sql"]
        rowsets = [e["response"]["rows"] for e in queries]
        discovered = [s["id"] for s in context["linked_skills"]]
        expected_discovered = sorted(skill_ids.values()) if name != "other" else []
        checks = {
            "discovery_scoped_correctly": sorted(discovered) == expected_discovered,
            "discovery_complete": context["linked_skills_status"] == "complete",
            "only_relevant_bodies_read": actual_reads == expected_reads[name],
            "reported_selection_matches_reads": sorted(answer["selected_skill_ids"]) == sorted(actual_reads),
            "full_instructions_not_in_context": all(s["arguments"]["instructions"] not in json.dumps(context) for s in manifest),
        }
        if name in {"join", "neighbor"}:
            expected_rows = [["p1", 10.0], ["p1", 20.0], ["p2", 40.0]] if name == "join" else [["m1", 99.0], ["m1", 101.0]]
            if heldout:
                expected_rows = [["p1", 12.0], ["p1", 24.0], ["p2", 45.0]] if name == "join" else [["m1", 80.0], ["m1", 100.0]]
            checks["executed_result_correct"] = expected_rows in rowsets
            checks["used_stable_join_key"] = any("join" in e["request"].lower() and "recording_id" in e["request"].lower() for e in queries)
            checks["no_basename_join"] = all("basename" not in e["request"].lower() for e in queries if "join" in e["request"].lower())
            if name == "neighbor":
                checks["target_encountered_as_neighbor"] = (
                    [n["id"] for n in context["seed_nodes"]] == ["D-probe-dataset"]
                    and "D-probe-db" in [n["id"] for n in context["related_nodes"]]
                )
        elif name == "summary":
            checks["executed_result_correct"] = any(
                any(isinstance(v, (int, float)) and math.isclose(v, 51 if heldout else 155 / 3) for row in rows for v in row)
                for rows in rowsets
            )
            checks["no_unnecessary_metadata_join"] = all("join" not in e["request"].lower() for e in queries)
            checks["grouped_by_recording"] = any("group by recording_id" in e["request"].lower() for e in queries)
        elif name == "size":
            size = (root / "primary" / "recordings.sqlite").stat().st_size
            checks["executed_result_correct"] = any(e["action"] == "stat" and e["response"]["size_bytes"] == size for e in events)
            checks["no_content_query"] = not queries
        else:
            checks["executed_result_correct"] = any(sorted(rows) == [["measurements"], ["recordings"]] for rows in rowsets)
            checks["schema_queries_only"] = bool(queries) and all("sqlite_master" in e["request"].lower() or "sqlite_schema" in e["request"].lower() for e in queries)
        cases.append({"case": name, "task": task, "seed_id": node_id,
                      "expected_read_ids": expected_reads[name], "observed_read_ids": actual_reads,
                      "checks": checks, "passed": all(checks.values()), "events": events,
                      "answer": answer})
    repo = Path(__file__).resolve().parents[2]
    snapshots = {}
    for relative in ["evals/node_linked_skills/task_probe.py", "evals/node_linked_skills/score_task_probe.py",
                     "wheeler/skill_discovery.py", "wheeler/search/retrieval.py", "wheeler/_data/commands/ask.md"]:
        content = (repo / relative).read_text()
        snapshots[relative] = {"sha256": hashlib.sha256(content.encode()).hexdigest(), "content": content}
    result = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {"host": "Codex local desktop subagents", "python": platform.python_version(),
                    "platform": platform.platform(), "sqlite": sqlite3.sqlite_version,
                    "graph": "Isolated loopback Neo4j; production Wheeler discovery; no research graph"},
        "method": "Fresh-context subagents, one case per agent. Actual isolated Neo4j capture and production discovery, audited skill reads and read-only SQLite execution. Expected choices and numerical results withheld from agent task prompts. Original fixture matches skill benchmark examples; heldout variant changes task data while keeping those examples unchanged.",
        "limitations": "One run per case; synthetic tasks and explicit applicability descriptions. No reliability estimate or model comparison. Seed node supplied to graph expansion, so search ranking and voice routing are not tested. Exact evaluator model IDs unavailable. SQL fixture controls are deterministic wrong implementations, not agent baselines. The CLI audit relies on agents following their tool-use contract; it is not an OS sandbox.",
        "preflight": "Original fixture only: first join context event was evaluator preflight before the agent's own context read. All heldout events are agent actions.",
        "agent_protocol": "Use context first. Compare linked resource, operation and applicability with current intent. Skip clear mismatches without opening bodies; read candidates if uncertainty matters; apply relevant guidance. Use only audited context/read/sql/stat/finish CLI actions. Do not inspect other cases, manifests, evaluator files or repository code. Execute task and record answer, selected/skipped IDs, rationale, exact model ID if exposed and environment.",
        "fixture": manifest, "controls": controls,
        "cases": cases, "passed": sum(c["passed"] for c in cases), "total": len(cases),
        "source_snapshots": snapshots,
    }
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"passed": result["passed"], "total": result["total"],
                      "checks": {c["case"]: c["checks"] for c in cases}}, indent=2))
    if result["passed"] != result["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    score(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:] or None)
