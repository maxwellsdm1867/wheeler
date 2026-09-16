"""Capture node-linked skills through the ordinary mutation/receipt pipeline.

Files live outside native skill catalogs. Accepted metadata is published last;
discovery additionally verifies graph/file agreement before returning a skill.
Immutable capture IDs make retries and close-session replay idempotent.
"""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
import re
import tempfile

import yaml

from wheeler.config import project_wheeler_dir
from wheeler.models import PREFIX_TO_LABEL


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:24]


@contextmanager
def _lineage_lock(config, name, targets):
    """Nonblocking cross-process lock for local-project skill lifecycle writes."""
    import fcntl

    lock_dir = project_wheeler_dir(config) / "lesson-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / f"{_digest([name, sorted(targets)])}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def _write_once(path: Path, content: str) -> None:
    """Never overwrite a captured version, including a hand-edited version."""
    if path.exists():
        if path.read_text() != content:
            raise ValueError(f"Captured artifact changed on disk: {path}. Restore it or capture a revision.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".capture-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


async def capture_lesson(backend, args: dict) -> str:
    """Composite mutation; every graph/file registration routes via dispatch."""
    config = args["_config"]
    try:
        for field in ("name", "description", "instructions", "source_excerpt", "problem_statement", "benchmark_task"):
            if not isinstance(args.get(field), str) or not args[field].strip():
                raise ValueError(f"{field} must be a non-empty string")
        name = args["name"].strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
            raise ValueError("name must be a lowercase hyphenated skill name, at most 64 characters")
        if len(args["description"]) > 1024:
            raise ValueError("description must be at most 1024 characters for progressive disclosure")
        if len(args["instructions"]) > 100_000 or len(args["source_excerpt"]) > 100_000:
            raise ValueError("Use a concise skill and source excerpt (at most 100000 characters each)")
        if any(len(args[field]) > 10_000 for field in ("problem_statement", "benchmark_task")):
            raise ValueError("Problem and benchmark task must each be at most 10000 characters")
        if not isinstance(args.get("accepted", False), bool):
            raise ValueError("accepted must be a boolean")
        targets = args.get("target_ids")
        sources = args.get("source_ids", [])
        harness = args.get("harness_ids", [])
        benchmarks = args.get("benchmark_result_ids", [])
        for field, ids in (("target_ids", targets), ("source_ids", sources), ("harness_ids", harness), ("benchmark_result_ids", benchmarks)):
            if not isinstance(ids, list) or not all(isinstance(i, str) and i for i in ids):
                raise ValueError(f"{field} must be a list of node IDs")
            if len(ids) > 50:
                raise ValueError(f"{field} is limited to 50 node IDs")
        if not targets:
            raise ValueError("At least one target node is required")
        targets, sources, harness = sorted(set(targets)), sorted(set(sources)), sorted(set(harness))
        benchmarks = sorted(set(benchmarks))
        model_context = {}
        for field in ("author_model", "author_environment", "tested_model", "tested_environment"):
            value = args.get(field, "unknown" if field.startswith("author_") else "")
            maximum = 200 if field.endswith("model") else 2000
            if not isinstance(value, str) or len(value) > maximum:
                raise ValueError(f"{field} must be a string of at most {maximum} characters")
            model_context[field] = value.strip() or ("unknown" if field.startswith("author_") else "")
        if benchmarks or model_context["tested_model"] or model_context["tested_environment"]:
            if not (benchmarks and model_context["tested_model"] and model_context["tested_environment"]):
                raise ValueError("A recorded evaluation requires tested_model, tested_environment, and benchmark_result_ids together")
        supersedes = args.get("supersedes", "")
        if not isinstance(supersedes, str):
            raise ValueError("supersedes must be a Document node ID or an empty string")
        harness_snapshot = {}
        for node_id in set(targets + sources + harness + benchmarks):
            label = PREFIX_TO_LABEL.get(node_id.split("-", 1)[0])
            found = await backend.get_node(label, node_id) if label else None
            if not found:
                raise ValueError(f"Node not found in this project: {node_id}")
            if node_id in harness:
                harness_snapshot[node_id] = {"hash": found.get("hash", ""), "path": found.get("path", "")}
        expected_harness = args.get("_expected_harness_snapshot")
        if expected_harness is not None and expected_harness != harness_snapshot:
            raise ValueError("Harness metadata changed since this candidate was captured; review and benchmark a revision before accepting")
        identity = {
            "name": name, "description": args["description"].strip(),
            "instructions": args["instructions"].strip(),
            "source_excerpt": args["source_excerpt"].strip(),
            "target_ids": targets, "source_ids": sources, "supersedes": supersedes,
            "problem_statement": args["problem_statement"].strip(),
            "benchmark_task": args["benchmark_task"].strip(), "harness_ids": harness,
            "harness_snapshot": harness_snapshot,
            **model_context, "benchmark_result_ids": benchmarks,
        }
        skill_text = _render_skill(identity)
        # Discovery reads at most 256 KiB. Validate the complete rendered UTF-8
        # artifact before acquiring a file lock or writing any capture state;
        # character limits alone do not bound Unicode bytes or added metadata.
        if len(skill_text.encode("utf-8")) > 256 * 1024:
            raise ValueError("Rendered SKILL.md must be at most 256 KiB in UTF-8, including metadata")
        key = _digest(identity)
        # Keep Wheeler's citation-compatible 8-hex IDs. The full capture key
        # below detects a truncated-ID collision instead of reusing it.
        node_id, source_id, execution_id = f"W-{key[:8]}", f"W-{_digest(['source', key])[:8]}", f"X-{key[:8]}"
        # Serialize captures of this local project's skill lineage across MCP
        # processes, without blocking the event loop. A busy caller can retry.
        with _lineage_lock(config, name, targets):
            return await _capture_locked(
                backend, args, identity, node_id, source_id, execution_id, key, skill_text,
            )
    except BlockingIOError:
        return json.dumps({"error": "capture_busy", "message": "This skill is being changed. Retry the same request."})
    except (ValueError, TypeError) as exc:
        return json.dumps({"error": "invalid_lesson", "message": str(exc)})


def _render_skill(identity: dict) -> str:
    """Render the exact bytes that discovery will verify and disclose."""
    return "---\n" + yaml.safe_dump(
        {"name": identity["name"], "description": identity["description"]}, sort_keys=False,
    ) + ("---\n\n" + identity["instructions"]
         + "\n\n## Problem this skill addresses\n\n" + identity["problem_statement"]
         + "\n\n## Benchmark task\n\n" + identity["benchmark_task"]
         + "\n\n## Model and run context\n\n"
         + "Authored with: " + identity["author_model"]
         + "\n\nAuthoring environment: " + identity["author_environment"]
         + "\n\nTested with: " + (identity["tested_model"] or "not recorded")
         + "\n\nTest environment: " + (identity["tested_environment"] or "not recorded")
         + "\n\nBenchmark result nodes: " + (", ".join(identity["benchmark_result_ids"]) or "none recorded")
         + "\n\nThe saved task alone is not evidence of a passing benchmark. "
         "Read the result nodes and this skill's Wheeler Document for source and harness versions. "
         "Results on one model/environment do not establish portability to another.\n")


async def _capture_locked(backend, args, identity, node_id, source_id, execution_id, key, skill_text) -> str:
    from wheeler.tools.graph_tools import execute_tool

    config = args["_config"]
    name, targets, sources = identity["name"], identity["target_ids"], identity["source_ids"]
    supersedes = identity["supersedes"]
    existing = await backend.get_node("Document", node_id)
    if existing and existing.get("skill_capture_key") != key:
        raise ValueError("Capture ID collision; choose a different descriptive skill name")
    if (existing or {}).get("skill_state") == "retracted":
        raise ValueError("This capture was retracted; create a revision instead of reactivating it")
    version = 1
    if supersedes:
        previous = await backend.get_node("Document", supersedes)
        if not previous or previous.get("skill_name") != name:
            raise ValueError("supersedes must identify an existing version of this named skill")
        if sorted(previous.get("skill_target_ids", [])) != targets:
            raise ValueError("A revision must retain the same target nodes; use a new skill name for a different scope")
        version = int(previous.get("skill_version", 0)) + 1

    siblings = await backend.query_nodes("Document", {"skill_name": name}, limit=1000)
    if len(siblings) >= 1000:
        raise ValueError("Too many versions for this name; narrow the skill scope before capture")
    siblings = [s for s in siblings if sorted(s.get("skill_target_ids", [])) == targets]
    if not existing:
        if supersedes:
            if any(s.get("skill_supersedes") == supersedes and s.get("skill_state") in {"accepted", "retracted"} for s in siblings):
                raise ValueError("That version already has an accepted successor; revise the current skill")
        elif siblings:
            return json.dumps({"error": "skill_exists", "message": "Reuse the existing capture or pass supersedes to create a revision.",
                               "existing_ids": [s["id"] for s in siblings]})
    # Promotion of an old candidate must not create a second accepted branch.
    if args.get("accepted") and supersedes and any(
        s["id"] != node_id and s.get("skill_supersedes") == supersedes
        and s.get("skill_state") in {"accepted", "retracted"} for s in siblings
    ):
        raise ValueError("Another revision was accepted; revise that current version instead")

    directory = config.resolved_project_root / ".notes" / "lessons" / name / key
    skill_path, source_path = directory / "SKILL.md", directory / "source.md"
    source_text = "# Lesson source\n\n" + identity["source_excerpt"] + "\n"

    async def call(tool, values):
        result = json.loads(await execute_tool(tool, {
            **values, "session_id": args.get("session_id", ""),
            "_require_complete_write": tool != "link_nodes",
        }, config))
        if result.get("error") or (tool != "link_nodes" and not all(result.get("storage", {}).get(k) for k in ("json", "synthesis"))):
            raise RuntimeError(f"{tool}: {result.get('message') or result.get('error') or 'incomplete file persistence'}")
        return result

    async def ensure(tool, label, values):
        current = await backend.get_node(label, values["id"])
        if current:
            from wheeler.portability import resolve

            if label == "Document":
                stored_path = resolve(current.get("path", ""), config.resolved_roots)
                if current.get("hash") != values["hash"] or stored_path != Path(values["path"]):
                    raise ValueError("Capture source/artifact ID collision or modified graph record")
            elif current.get("description") != values["description"]:
                raise ValueError("Capture Execution ID collision")
            # A CREATE may have committed before the response/files failed.
            # Repair the mirrors from graph state rather than replaying CREATE.
            field = "description" if label == "Execution" else "title"
            return await call("update_node", {
                "node_id": values["id"], field: current.get(field, values[field]),
                "_refresh_files": True,
            })
        return await call(tool, values)

    async def link(source, target, relationship):
        params = {"source_id": source, "target_id": target, "relationship": relationship}
        scope = ""
        if config.neo4j.project_tag:
            params["project_tag"] = config.neo4j.project_tag
            scope = " AND s._wheeler_project = $project_tag AND t._wheeler_project = $project_tag"
        query = (
            "MATCH (s {id: $source_id})-[r]->(t {id: $target_id}) "
            "WHERE type(r) = $relationship" + scope + " RETURN count(r) AS count"
        )
        # link_nodes creates a new edge, so replay must check before writing.
        # Preserve the original edge's version pins and creation timestamp.
        rows = await backend.run_cypher(query, params)
        if rows and rows[0].get("count"):
            return
        await call("link_nodes", {"source_id": source, "target_id": target, "relationship": relationship})
        rows = await backend.run_cypher(query, params)
        if not rows or not rows[0].get("count"):
            raise RuntimeError(f"Required link was not persisted: {source} {relationship} {target}")

    try:
        _write_once(skill_path, skill_text)
        _write_once(source_path, source_text)
        _write_once(directory / "capture.json", json.dumps(identity, sort_keys=True, indent=2) + "\n")
        await ensure("add_document", "Document", {
            "id": source_id, "title": f"Source: {name}", "path": str(source_path),
            "hash": hashlib.sha256(source_text.encode()).hexdigest(), "status": "final",
        })
        await ensure("add_execution", "Execution", {
            "id": execution_id, "kind": "lesson", "description": f"Capture {name} version {version} ({key})",
        })
        await ensure("add_document", "Document", {
            "id": node_id, "title": name, "path": str(skill_path), "status": "final",
            "hash": hashlib.sha256(skill_text.encode()).hexdigest(),
            "skill_name": name, "skill_description": identity["description"],
            "skill_version": version, "skill_state": "incomplete", "skill_supersedes": supersedes,
            "skill_source_ids": [source_id, *sources], "skill_target_ids": targets,
            "skill_capture_key": key,
            "skill_problem": identity["problem_statement"],
            "skill_benchmark_task": identity["benchmark_task"], "skill_harness_ids": identity["harness_ids"],
            "skill_harness_snapshot": json.dumps(identity["harness_snapshot"], sort_keys=True),
            "skill_author_model": identity["author_model"],
            "skill_author_environment": identity["author_environment"],
            "skill_tested_model": identity["tested_model"],
            "skill_tested_environment": identity["tested_environment"],
            "skill_benchmark_result_ids": identity["benchmark_result_ids"],
        })
        await link(node_id, execution_id, "WAS_GENERATED_BY")
        for input_id in sorted(set([source_id, *sources, *identity["harness_ids"], *identity["benchmark_result_ids"]])):
            await link(execution_id, input_id, "USED")
        for target in targets:
            await link(node_id, target, "APPLIES_TO")
        if supersedes:
            await link(node_id, supersedes, "WAS_DERIVED_FROM")
        state = "accepted" if args.get("accepted") or (existing or {}).get("skill_state") == "accepted" else "candidate"
        if (existing or {}).get("skill_state") == "retracted":
            raise ValueError("This capture was retracted; create a revision instead of reactivating it")
        await call("update_node", {"node_id": node_id, "skill_state": state, "_refresh_files": True})
        if state == "accepted":
            # Publication receipt comes after graph, canonical JSON, synthesis,
            # and every required edge have been checked. Accepted graph state
            # alone cannot prove a cross-store write completed.
            _write_once(directory / "capture-complete.json", json.dumps({
                "node_id": node_id, "capture_key": key,
                "hash": hashlib.sha256(skill_text.encode()).hexdigest(),
            }, sort_keys=True) + "\n")
        unchanged = existing and existing.get("skill_state") == state
        return json.dumps({
            "node_id": node_id, "label": "Document", "status": "unchanged" if unchanged else "updated" if existing else "created",
            "skill_state": state, "path": str(skill_path), "version": version,
            "source_id": source_id, "execution_id": execution_id, "target_ids": targets,
        })
    except Exception as exc:
        return json.dumps({
            "error": "incomplete_lesson", "status": "incomplete", "node_id": node_id,
            "message": str(exc), "retry": "Retry the same capture request to repair and finish it.",
        })


async def retire_skill(backend, args: dict) -> str:
    """Withdraw a learned skill from discovery without deleting its provenance."""
    from wheeler.tools.graph_tools import execute_tool

    node_id = args.get("node_id", "")
    reason = args.get("reason", "")
    if not isinstance(reason, str) or not reason.strip():
        return json.dumps({"error": "A retirement reason is required"})
    current = await backend.get_node("Document", node_id)
    if not current or not current.get("skill_name"):
        return json.dumps({"error": "Not a learned skill Document", "node_id": node_id})
    try:
        with _lineage_lock(args["_config"], current["skill_name"], current["skill_target_ids"]):
            result = json.loads(await execute_tool("update_node", {
                "node_id": node_id, "skill_state": "retracted", "skill_retired_reason": reason.strip(),
                "session_id": args.get("session_id", ""), "_refresh_files": True,
                "_require_complete_write": True,
            }, args["_config"]))
            if not result.get("error") and not all(result.get("storage", {}).get(k) for k in ("json", "synthesis")):
                result.update(error="incomplete_retirement", message="Graph retirement saved, file mirrors incomplete. Retry the same retirement.")
            return json.dumps(result)
    except BlockingIOError:
        return json.dumps({"error": "capture_busy", "message": "This skill is being changed. Retry retirement."})


async def accept_skill(backend, args: dict) -> str:
    """Accept a saved candidate by ID without reconstructing its original call."""
    from wheeler.portability import resolve
    from wheeler.tools.graph_tools import execute_tool

    current = await backend.get_node("Document", args.get("node_id", ""))
    if not current or not current.get("skill_name"):
        return json.dumps({"error": "Not a learned skill Document"})
    config = args["_config"]
    try:
        skill_path = resolve(current["path"], config.resolved_roots)
        if skill_path is None or not skill_path.resolve().is_relative_to(config.resolved_project_root / ".notes" / "lessons"):
            raise ValueError("Saved capture is not available in this project's lesson artifacts")
        identity = json.loads(skill_path.with_name("capture.json").read_text())
        if _digest(identity) != current["skill_capture_key"]:
            raise ValueError("Saved capture manifest changed; restore it before accepting")
        return await execute_tool("capture_lesson", {
            **identity, "accepted": True, "session_id": args.get("session_id", ""),
            "_expected_harness_snapshot": identity["harness_snapshot"],
        }, config)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return json.dumps({"error": "invalid_saved_capture", "message": str(exc)})
