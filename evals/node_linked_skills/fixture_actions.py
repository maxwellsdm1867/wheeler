"""Audited public actions for native-host node-linked-skill evaluations.

The runner supplies public.json and isolated artifacts. This module never loads
an oracle. The action contract is an audit boundary, not an operating-system
sandbox: native hosts can have additional tools, which the evaluator must audit.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import html
import json
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _json_arg(value: str) -> dict[str, Any]:
    parsed = json.loads(value or "{}")
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def _resource(public: dict, name: str | None = None) -> tuple[str, Path]:
    resources = public.get("resources", {})
    name = name or public.get("default_resource")
    if name in resources:
        return str(name), Path(resources[name]).resolve()
    # A runner may identify the default artifact by its already registered path.
    matches = [(key, value) for key, value in resources.items() if str(value) == str(name)]
    if len(matches) == 1:
        key, value = matches[0]
        return key, Path(value).resolve()
    raise ValueError(f"Unknown resource: {name!r}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _csv_rows(path: Path) -> list[dict]:
    def number(value: str) -> Any:
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    with path.open(newline="") as handle:
        return [{key: value if key in {"cell", "cell_id", "recording_id"} else number(value)
                 for key, value in row.items()} for row in csv.DictReader(handle)]


def _readonly_sql(path: Path, query: str) -> dict:
    def authorize(action: int, _arg1: str | None, _arg2: str | None,
                  _db: str | None, _source: str | None) -> int:
        denied = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}
        return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only = ON")
        connection.set_authorizer(authorize)
        cursor = connection.execute(query)
        columns = [column[0] for column in cursor.description or []]
        rows = [list(row) for row in cursor.fetchall()]
    return {"columns": columns, "rows": rows, "row_count": len(rows)}


def _inspect(root: Path, public: dict, request: dict) -> dict:
    name, path = _resource(public, request.get("resource"))
    kind = request.get("kind", "stat")
    if kind == "stat":
        stat = path.stat()
        return {"resource": name, "path": str(path), "filename": path.name,
                "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                "mtime": stat.st_mtime, "is_directory": path.is_dir()}
    if kind == "schema":
        result = _readonly_sql(path, "SELECT name FROM sqlite_master "
                              "WHERE type='table' ORDER BY name")
        return {"tables": [row[0] for row in result["rows"]]}
    if kind == "imports":
        parsed = ast.parse(path.read_text())
        imports = set()
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add("." * node.level + (node.module or ""))
        return {"imports": sorted(imports)}
    if kind == "data":
        return {"resource": name, "rows": _csv_rows(path)}
    if kind == "list":
        return {"filenames": sorted(item.name for item in path.iterdir())}
    if kind == "copy":
        archive = root / "archive"
        archive.mkdir(exist_ok=True)
        destination = archive / path.name
        with destination.open("xb") as handle:
            handle.write(path.read_bytes())
        return {"source": str(path), "destination": str(destination),
                "source_sha256": _sha(path), "destination_sha256": _sha(destination),
                "hash_matches": _sha(path) == _sha(destination)}
    raise ValueError(f"Unsupported inspection kind: {kind}")


def _fit(public: dict, request: dict) -> dict:
    import numpy as np

    _, path = _resource(public, request.get("resource", "fit_data"))
    rows = _csv_rows(path)
    group_by = request.get("group_by")
    if group_by not in {None, "cell"}:
        raise ValueError("group_by must be cell or null")
    intercept = request.get("intercept", True)
    if not isinstance(intercept, bool):
        raise ValueError("intercept must be a boolean")
    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        groups[str(row["cell"]) if group_by else "pooled"].append(row)
    fits = {}
    for key, values in sorted(groups.items()):
        x = np.asarray([row["x"] for row in values], dtype=float)
        y = np.asarray([row["y"] for row in values], dtype=float)
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("Fit data must be finite")
        design = np.column_stack((np.ones(len(x)), x)) if intercept else x[:, None]
        coefficients, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
        if rank < design.shape[1]:
            raise ValueError(f"Fit group {key} is rank deficient")
        fits[key] = {"intercept": float(coefficients[0]) if intercept else 0.0,
                     "slope": float(coefficients[-1]), "n": len(values)}
    return {"group_by": group_by, "intercept": intercept, "fits": fits}


def _plot(root: Path, public: dict, request: dict) -> dict:
    _, path = _resource(public, request.get("resource", "plot_dataset"))
    rows = _csv_rows(path)
    group_by = request.get("group_by")
    if group_by not in {None, "cell"}:
        raise ValueError("group_by must be cell or null")
    buckets: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        x, y = float(row["x"]), float(row["y"])
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("Plot data must be finite")
        buckets[(x, row["cell"] if group_by else None)].append(y)
    points: dict[float, list[float]] = defaultdict(list)
    for (x, _cell), values in buckets.items():
        points[x].append(sum(values) / len(values))
    xs = sorted(points)
    ys = [sum(points[x]) / len(points[x]) for x in xs]
    if not xs:
        raise ValueError("No plot data")
    xscale, yscale = request.get("xscale", "linear"), request.get("yscale", "linear")
    if xscale not in {"linear", "log"} or yscale not in {"linear", "log"}:
        raise ValueError("Scale must be linear or log")
    def transform(values: list[float], scale: str) -> list[float]:
        if scale == "log":
            if min(values) <= 0:
                raise ValueError("Log axis requires positive values")
            return [math.log10(value) for value in values]
        return values
    tx, ty = transform(xs, xscale), transform(ys, yscale)
    def norm(value: float, values: list[float]) -> float:
        span = max(values) - min(values)
        return (value - min(values)) / span if span else 0.5
    coords = [(60 + 500 * norm(x, tx), 340 - 280 * norm(y, ty)) for x, y in zip(tx, ty)]
    xlabel, ylabel = str(request.get("xlabel", "x")), str(request.get("ylabel", "y"))
    points_text = " ".join(f"{x:.3f},{y:.3f}" for x, y in coords)
    ticks = "".join(f'<text x="{px:.3f}" y="360" text-anchor="middle">{x:g}</text>'
                    for x, (px, _py) in zip(xs, coords))
    circles = "".join(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="4"/>' for px, py in coords)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" '
           f'data-xscale="{xscale}" data-yscale="{yscale}">'
           '<rect width="640" height="420" fill="white"/>'
           '<path d="M60 60V340H560" fill="none" stroke="black"/>'
           f'<polyline points="{points_text}" fill="none" stroke="blue"/>{circles}{ticks}'
           f'<text x="310" y="400" text-anchor="middle">{html.escape(xlabel)}</text>'
           f'<text x="20" y="200" transform="rotate(-90 20 200)" '
           f'text-anchor="middle">{html.escape(ylabel)}</text></svg>')
    svg_path, json_path = root / "plot.svg", root / "plot.json"
    result = {"x": xs, "y": ys, "xscale": xscale, "yscale": yscale,
              "xlabel": xlabel, "ylabel": ylabel, "group_by": group_by,
              "svg_path": str(svg_path), "json_path": str(json_path)}
    svg_path.write_text(svg)
    json_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def _export(public: dict, request: dict) -> dict:
    _, directory = _resource(public, "export_directory")
    filename = request.get("filename")
    if not isinstance(filename, str) or not filename or filename in {".", ".."} or Path(filename).name != filename:
        raise ValueError("filename must be a single nonempty basename")
    content = request.get("content", public.get("export_parameters", {}).get("content"))
    path = directory / filename
    data = (json.dumps(content, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(data)
    return {"path": str(path), "filename": filename, "bytes": len(data), "sha256": _sha(path)}


def _perform(root: Path, public: dict, action: str, argument: str, phase: int) -> Any:
    if action == "context":
        return {"context": public.get("context", {}),
                "resources": public.get("resources", {}),
                "default_resource": public.get("default_resource"),
                "export_parameters": public.get("export_parameters", {})}
    if action == "read":
        offered = {skill["id"] for skill in public.get("context", {}).get("linked_skills", [])}
        if argument not in offered or argument not in public.get("skill_paths", {}):
            raise ValueError("Skill ID was not offered by this graph response")
        return {"id": argument, "body": Path(public["skill_paths"][argument]).read_text()}
    if action == "sql":
        request = _json_arg(argument) if argument.lstrip().startswith("{") else {"query": argument}
        _, path = _resource(public, request.get("resource"))
        return _readonly_sql(path, request["query"])
    request = _json_arg(argument)
    if action == "inspect":
        return _inspect(root, public, request)
    if action == "fit":
        return _fit(public, request)
    if action == "plot":
        return _plot(root, public, request)
    if action == "export":
        return _export(public, request)
    if action == "finish":
        (root / f"answer-phase{phase}.json").write_text(json.dumps(request, indent=2) + "\n")
        if phase == 1 and public.get("followup_task"):
            (root / ".phase.json").write_text(json.dumps({"phase": 2}) + "\n")
            return {"status": "recorded", "next_task": public["followup_task"], "phase": 2}
        (root / "answer.json").write_text(json.dumps(request, indent=2) + "\n")
        return {"status": "recorded", "complete": True, "phase": phase}
    raise ValueError(f"Unknown action: {action}")


def run_cli(root: Path) -> None:
    """Handle sys.argv[1:] and always print an auditable JSON response."""
    root = root.resolve()
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    argument = " ".join(sys.argv[2:])
    phase = 1
    started = datetime.now(timezone.utc).isoformat()
    try:
        public = json.loads((root / "public.json").read_text())
        if (root / ".phase.json").exists():
            phase = int(json.loads((root / ".phase.json").read_text())["phase"])
        result = _perform(root, public, action, argument, phase)
        error = False
    except Exception as exc:
        result = {"error": str(exc), "error_type": type(exc).__name__}
        error = True
    event = {"at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
             "phase": phase, "action": action, "argument": argument,
             "request": argument, "result": result, "response": result, "error": error}
    with (root / "events.jsonl").open("a") as handle:
        handle.write(json.dumps(event, default=str) + "\n")
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    run_cli(Path.cwd())
