"""Audited, isolated graph-discovery -> agent task execution probe.

Run with the checkout's Python. Setup requires an explicitly isolated Neo4j URI.
Agents get only the CLI action contract, one case ID, and its task. The evaluator
retains the oracle separately. No production project config is loaded here.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wheeler.config import WheelerConfig
from wheeler.graph.driver import close_async_driver
from wheeler.search.retrieval import expand_search_results
from wheeler.tools.graph_tools import _get_backend, execute_tool


CASES = {
    "join": ("D-probe-db", "Return the parasol recording IDs and their measured response values from this database, ordered by recording ID and value."),
    "neighbor": ("D-probe-dataset", "Find this dataset's database and return the midget recording IDs and measured response values, ordered by recording ID and value."),
    "summary": ("D-probe-db", "Compute the population response summary from this database's measurements, following this analysis's conventions."),
    "size": ("D-probe-db", "Report this database file's size in bytes. Do not query its contents."),
    "schema": ("D-probe-db", "List the names of the tables in this database. Do not analyze or join any records."),
    "other": ("D-probe-other", "List the names of the tables in this database. Do not analyze or join any records."),
}


def record(root, case, action, request, response):
    event = {"at": datetime.now(timezone.utc).isoformat(), "action": action,
             "request": request, "response": response}
    with (root / f"{case}.events.jsonl").open("a") as handle:
        handle.write(json.dumps(event, default=str) + "\n")


async def setup(root, uri, variant=""):
    root.mkdir(parents=True, exist_ok=True)
    if (root / "config.json").exists():
        raise ValueError("Use a new probe root")
    config = WheelerConfig(project_root=str(root), neo4j={
        "uri": uri, "username": "neo4j", "password": "", "database": "neo4j",
        "project_tag": "skill-task-probe-" + uuid4().hex,
    })
    (root / "config.json").write_text(config.model_dump_json(indent=2))
    paths = {}
    for name in ("primary", "other"):
        folder = root / name
        folder.mkdir()
        path = folder / "recordings.sqlite"
        with sqlite3.connect(path) as db:
            db.executescript("""
                CREATE TABLE recordings(recording_id TEXT PRIMARY KEY, basename TEXT, cell_type TEXT);
                CREATE TABLE measurements(recording_id TEXT, basename TEXT, value REAL);
                INSERT INTO recordings VALUES
                    ('p1', 'trace.dat', 'parasol'), ('p2', 'other.dat', 'parasol'),
                    ('m1', 'trace.dat', 'midget');
                INSERT INTO measurements VALUES
                    ('p1', 'trace.dat', 10), ('p1', 'trace.dat', 20),
                    ('p2', 'other.dat', 40), ('m1', 'trace.dat', 99), ('m1', 'trace.dat', 101);
            """)
            if variant == "heldout":
                # Keep skill examples unchanged, but vary task data so copying
                # a benchmark answer cannot produce the correct task result.
                db.executescript("""
                    UPDATE measurements SET value = CASE
                        WHEN recording_id = 'p1' AND value = 10 THEN 12
                        WHEN recording_id = 'p1' AND value = 20 THEN 24
                        WHEN recording_id = 'p2' THEN 45
                        WHEN recording_id = 'm1' AND value = 99 THEN 80
                        WHEN recording_id = 'm1' AND value = 101 THEN 100
                    END;
                """)
        paths[name] = path
    (root / "dataset.csv").write_text("cell_type\nmidget\n")
    for node_id, path, desc in (
        ("D-probe-db", paths["primary"], "Recording metadata and measured responses for the primary retinal analysis"),
        ("D-probe-other", paths["other"], "Separate recordings database for another analysis"),
        ("D-probe-dataset", root / "dataset.csv", "Midget dataset linked to its source recordings database"),
    ):
        result = json.loads(await execute_tool("add_dataset", {
            "id": node_id, "path": str(path), "type": path.suffix.lstrip("."), "description": desc,
        }, config))
        assert "error" not in result, result
    await execute_tool("link_nodes", {"source_id": "D-probe-dataset", "target_id": "D-probe-db",
                                      "relationship": "RELEVANT_TO"}, config)
    specs = [
        ("recording-joins", "Join recording metadata to measured responses, including selecting measurements by cell type. Not for file size, schema inspection, or summaries of measurements alone.",
         "When joining recordings and measurements, use recording_id, never basename: filenames repeat across cells. Filter cell type on recordings. Multiple measurements per recording are valid. Verify the joined row count equals the measurement count for the selected recording IDs before interpreting results.",
         "A basename join contaminated parasol results with midget responses.",
         "Select parasol measurements and return p1:10, p1:20, p2:40, without midget values; check cardinality."),
        ("population-response", "Compute the population response summary from the measurements table in this analysis. Applies to aggregation, not metadata joins, individual response retrieval, schema inspection, or file size.",
         "For the population response summary, first average value within each recording_id in measurements. Then average those per-recording means with equal weight per recording. Report per-recording means, recording count, and the equal-weight population mean. Do not average all measurement rows directly; that overweights recordings with more measurements. This operation does not need a recordings metadata join.",
         "Recordings with unequal measurement counts received unequal weight in the population summary.",
         "For p1=[10,20], p2=[40], m1=[99,101], report means 15,40,100 and population mean 155/3 for three recordings."),
    ]
    manifest = []
    for name, description, instructions, problem, benchmark in specs:
        args = {"name": name, "description": description, "instructions": instructions,
                "target_ids": ["D-probe-db"], "source_excerpt": problem,
                "problem_statement": problem, "benchmark_task": benchmark, "accepted": True,
                "author_model": "unknown", "author_environment": "Codex local checkout; synthetic evaluator fixture"}
        result = json.loads(await execute_tool("capture_lesson", args, config))
        assert result.get("status") not in {None, "incomplete"} and "error" not in result, result
        content = Path(result["path"]).read_text()
        manifest.append({"capture": result, "arguments": args, "body": content,
                         "sha256": hashlib.sha256(content.encode()).hexdigest()})
    (root / "fixture-manifest.json").write_text(json.dumps(manifest, indent=2))
    with sqlite3.connect(paths["primary"]) as db:
        wrong_join = db.execute("SELECT r.recording_id,m.value FROM recordings r JOIN measurements m ON r.basename=m.basename WHERE r.cell_type='parasol' ORDER BY r.recording_id,m.value").fetchall()
        wrong_mean = db.execute("SELECT AVG(value) FROM measurements").fetchone()[0]
    (root / "controls.json").write_text(json.dumps({"variant": variant, "wrong_basename_join": wrong_join, "wrong_row_mean": wrong_mean}, indent=2))
    print(json.dumps({"root": str(root), "cases": {k: v[1] for k, v in CASES.items()}}, indent=2))


async def act(root, action, case, argument):
    config = WheelerConfig.model_validate_json((root / "config.json").read_text())
    if action == "cleanup":
        backend = await _get_backend(config)
        await backend.run_cypher("MATCH (n {_wheeler_project: $tag}) DETACH DELETE n",
                                 {"tag": config.neo4j.project_tag})
        return {"cleaned_namespace": config.neo4j.project_tag}
    node_id, task = CASES[case]
    if action == "context":
        # This is the production graph expansion/discovery implementation.
        # Seed selection is fixed to isolate selection from search ranking.
        result = await expand_search_results([{"id": node_id, "type": "Dataset"}], config, max_hops_prov=1)
        (root / f"{case}.context.json").write_text(json.dumps(result, indent=2, default=str))
    elif action == "read":
        context = json.loads((root / f"{case}.context.json").read_text())
        skill = next(s for s in context["linked_skills"] if s["id"] == argument)
        result = {"id": argument, "name": skill["name"], "body": Path(skill["path"]).read_text()}
    elif action in {"sql", "stat"}:
        path = root / ("other" if case == "other" else "primary") / "recordings.sqlite"
        if action == "stat":
            result = {"path": str(path), "size_bytes": path.stat().st_size}
        else:
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
                db.execute("PRAGMA query_only=ON")
                cursor = db.execute(argument)
                result = {"columns": [c[0] for c in cursor.description], "rows": cursor.fetchall()}
    elif action == "finish":
        result = json.loads(argument)
        (root / f"{case}.answer.json").write_text(json.dumps(result, indent=2))
    else:
        raise ValueError(action)
    record(root, case, action, argument, result)
    return result


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("action", choices=["setup", "context", "read", "sql", "stat", "finish", "cleanup"])
    parser.add_argument("case", nargs="?", default="")
    parser.add_argument("argument", nargs="?", default="")
    args = parser.parse_args()
    try:
        if args.action == "setup":
            await setup(args.root.resolve(), args.case, args.argument)
        else:
            result = await act(args.root.resolve(), args.action, args.case, args.argument)
            print(json.dumps(result, default=str))
    finally:
        await close_async_driver()


if __name__ == "__main__":
    asyncio.run(main())
