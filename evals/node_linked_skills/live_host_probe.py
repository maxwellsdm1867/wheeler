"""Native host -> production Wheeler MCP -> selective file-read smoke probe.

Setup and cleanup touch only fresh uniquely tagged fixture namespaces. Host runs
are explicit, one per invocation, and use subscription authentication with normal
host permissions. No user configuration or installed skill catalog is modified.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import hashlib
import shutil
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.parse import urlparse
from uuid import uuid4

REPO = Path(__file__).resolve().parents[2]
PYTHON = REPO / ".venv/bin/python"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from host_runner import _events, _evidence  # noqa: E402

CASES = ("positive", "same_node_negative", "other_resource", "pagination")


def run_host(host: str, fixture_root: Path, prompt: str, logs: Path,
             mcpconfig: dict, timeout_seconds: int = 180, *,
             plugin_dirs: list[str] | None = None, codex_config: list[str] | None = None,
             use_user_config: bool = False, executable: str | None = None) -> dict:
    """Run one host with an ephemeral Claude-style ``mcpServers`` mapping.

    The mapping supports command, args, env and optional enabled_tools. Codex
    receives equivalent CLI TOML overrides. Claude permits Read, Write and the
    explicitly configured MCP servers, with dontAsk permission mode. Codex keeps
    its workspace-write sandbox. This function does not itself score behavior.
    """
    if host not in {"claude", "codex"}:
        raise ValueError("host must be claude or codex")
    program = executable or host
    fixture_root, logs = fixture_root.resolve(strict=True), logs.resolve()
    logs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in list(env):
        if key.endswith("_API_KEY"):
            env.pop(key, None)
    servers = mcpconfig.get("mcpServers", {})
    if not servers:
        raise ValueError("At least one explicit MCP server is required")
    # Also bind any catalog-provided subprocess to the same isolated project.
    # Server disabling remains explicit; this is an additional scope guard.
    roots = {server.get("env", {}).get("WHEELER_PROJECT_ROOT") for server in servers.values()}
    if len(roots) == 1 and None not in roots:
        first_env = next(iter(servers.values())).get("env", {})
        for key in ("WHEELER_PROJECT_ROOT", "WHEELER_NO_KEYCHAIN", "NEO4J_URI", "NEO4J_USERNAME",
                    "NEO4J_PASSWORD", "NEO4J_DATABASE", "PYTHONPATH"):
            if key in first_env:
                env[key] = str(first_env[key])
    (logs / "prompt.txt").write_text(prompt)
    if host == "claude":
        config_path = logs / "mcp.json"
        # enabled_tools is a Codex-only client filter, not Claude MCP schema.
        config_path.write_text(json.dumps({"mcpServers": {
            key: {k: v for k, v in value.items() if k != "enabled_tools"}
            for key, value in servers.items()}}, indent=2))
        settings = logs / "settings.json"
        settings.write_text(json.dumps({"disableAllHooks": True, "autoMemoryEnabled": False}))
        allowed = ["Read", "Write"] + (["Skill"] if plugin_dirs else [])
        for name, server in servers.items():
            enabled = server.get("enabled_tools")
            allowed.extend(f"mcp__{name}__{tool}" for tool in enabled) if enabled else allowed.append(f"mcp__{name}__*")
        command = [program, "--print", "--output-format", "stream-json", "--verbose",
                   "--tools", "Read,Write,Skill" if plugin_dirs else "Read,Write", "--strict-mcp-config", "--mcp-config", str(config_path),
                   "--setting-sources", "project", "--settings", str(settings),
                   "--no-session-persistence", "--no-chrome", "--permission-mode", "dontAsk",
                   "--allowedTools", *allowed]
        for plugin_dir in plugin_dirs or []:
            command += ["--plugin-dir", plugin_dir]
        command += ["--", prompt]
    else:
        command = [program, "exec", *([] if use_user_config else ["--ignore-user-config"]), "--ephemeral", "--json",
                   "--sandbox", "workspace-write", "--skip-git-repo-check", "--cd", str(fixture_root),
                   "-c", 'approval_policy="never"', "-c", "mcp_servers={}"]
        for name, server in servers.items():
            if not name.replace("_", "").replace("-", "").isalnum():
                raise ValueError("MCP server name must be alphanumeric with underscores/hyphens")
            for key in ("command", "args", "enabled_tools"):
                if key in server:
                    command += ["-c", f"mcp_servers.{name}.{key}={json.dumps(server[key])}"]
            for key, value in server.get("env", {}).items():
                if not key.replace("_", "").isalnum():
                    raise ValueError("MCP environment key is invalid")
                command += ["-c", f"mcp_servers.{name}.env.{key}={json.dumps(str(value))}"]
            command += ["-c", f"mcp_servers.{name}.startup_timeout_sec=60"]
        for override in codex_config or []:
            command += ["-c", override]
        command.append("-")
    (logs / "command.json").write_text(json.dumps(command, indent=2))
    try:
        version = subprocess.run([program, "--version"], capture_output=True, text=True,
                                 env=env, timeout=15, check=False).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        version = "unknown"
    started = time.time()
    status, exit_code, launch_error = "host_error", None, None
    with (logs / "stdout.jsonl").open("w") as stdout, (logs / "stderr.log").open("w") as stderr:
        try:
            process = subprocess.Popen(command, cwd=fixture_root, env=env, stdout=stdout, stderr=stderr,
                                       stdin=subprocess.PIPE, text=True, start_new_session=True)
            try:
                process.communicate(prompt if host == "codex" else None, timeout=timeout_seconds)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                status = "timeout"
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                exit_code = process.returncode
        except OSError as exc:
            status, launch_error = "launch_error", str(exc)
    native_events = _events(logs / "stdout.jsonl")
    evidence = _evidence(host, native_events)
    mcp_calls = [event["item"] for event in native_events
                 if event.get("type") == "item.completed"
                 and event.get("item", {}).get("type") == "mcp_tool_call"]
    for call in mcp_calls:
        if "cancelled" in str(call.get("error", "")).lower():
            evidence["permission_denials"].append({"tool": call.get("tool"), "error": call.get("error")})
    if status not in {"timeout", "launch_error"}:
        status = "completed" if exit_code == 0 and evidence["native_completion_event"] else "host_error"
        if evidence["permission_denials"]:
            status = "permission_denied"
    evidence["model_selection"] = "native host configuration; no model override" if use_user_config else "host default; no model override; user config excluded"
    result = {"host": host, "host_version": version, "executable": program, "status": status,
              "exit_code": exit_code, "launch_error": launch_error,
              "elapsed_seconds": round(time.time() - started, 3),
              "fixture_root": str(fixture_root), "logs": str(logs), "use_user_config": use_user_config, **evidence}
    (logs / "result.json").write_text(json.dumps(result, indent=2))
    return result


def _mcp_config(project: Path, uri: str) -> dict:
    return {"mcpServers": {"wheeler_core": {
        "command": str(PYTHON), "args": ["-m", "wheeler.mcp_core"],
        "enabled_tools": ["show_node"],
        "env": {"WHEELER_PROJECT_ROOT": str(project), "PYTHONPATH": str(REPO),
                "NEO4J_URI": uri, "NEO4J_USERNAME": "neo4j", "NEO4J_PASSWORD": "",
                "NEO4J_DATABASE": "neo4j", "WHEELER_NO_KEYCHAIN": "1"},
    }}}


def _guidance() -> str:
    act = (REPO / "wheeler/_data/commands/ask.md").read_text()
    section = act.split("## Node-linked skills", 1)[1].split("$ARGUMENTS", 1)[0]
    return section.strip()


async def setup(root: Path, uri: str, cases: tuple[str, ...] = CASES) -> dict:
    from wheeler.config import WheelerConfig
    from wheeler.tools.graph_tools import execute_tool

    parsed = urlparse(uri)
    if parsed.scheme not in {"bolt", "neo4j"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("This probe accepts only an explicitly isolated loopback Neo4j URI")
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "private-manifest.json"
    if manifest_path.exists():
        raise ValueError("Use a fresh probe root")
    manifest = {"uri": uri, "kind": "native-live-mcp-probe", "cases": {},
                "guidance": _guidance(), "repo": str(REPO), "fixture_tags": []}
    # Write progress before each graph mutation so cleanup remains possible.
    def persist() -> None:
        manifest_path.write_text(json.dumps(manifest, indent=2))
    persist()
    for host in ("claude", "codex"):
        for case in cases:
            key = f"{host}/{case}"
            project = root / "projects" / host / case
            project.mkdir(parents=True)
            tag = "native-live-probe-" + uuid4().hex
            manifest["fixture_tags"].append({"tag": tag, "project": str(project)})
            persist()
            config = WheelerConfig(project_root=str(project), search={"enabled": False}, synthesis_enabled=False,
                                   neo4j={"uri": uri, "username": "neo4j",
                "database": "neo4j", "project_tag": tag,
                "password": ""})
            # JSON is valid YAML, preserves every explicit isolated setting.
            (project / "wheeler.yaml").write_text(config.model_dump_json(indent=2))
            resources = {}
            for name in ("primary", "other"):
                directory = project / name
                directory.mkdir()
                path = directory / "responses.csv"
                path.write_text("recording_id,value\nr7,14\nr7,26\nr9,53\nz2,70\nz2,90\n")
                node_id = "D-" + uuid4().hex[:8]
                added = json.loads(await execute_tool("add_dataset", {
                    "id": node_id, "path": str(path), "type": "csv",
                    "description": f"{name.title()} response measurements for this analysis",
                }, config))
                if added.get("error"):
                    raise RuntimeError(added)
                resources[name] = {"id": node_id, "path": str(path)}
            skills = []
            count = 21 if case == "pagination" else 1
            for index in range(count):
                label = f"analysis-{index + 1:02d}" if count > 1 else "population-response"
                marker = "response-convention-" + uuid4().hex[:12]
                body = (f"For the {label} report, average values within recording_id first, then average "
                        "the recording means equally. Report population_mean and recording_count. "
                        f"Set the report's convention field to {marker}. Do not use this procedure "
                        "for any other report family or for file metadata inspection.")
                captured = json.loads(await execute_tool("capture_lesson", {
                    "name": label + "-report",
                    "description": f"Prepare the {label} population response report from this resource. "
                                   "Applies only to this named report family, not file metadata or other report families.",
                    "instructions": body, "target_ids": [resources["primary"]["id"]],
                    "source_excerpt": "Unequal repeats require an explicit recording-weighting convention.",
                    "problem_statement": "Prevent unintended weighting of recordings by repeat count.",
                    "benchmark_task": "Use unseen response values; check recording weighting and skip file-only tasks.",
                    "accepted": True, "author_model": "unknown",
                    "author_environment": "Local synthetic native MCP fixture generation",
                }, config))
                if captured.get("error") or captured.get("status") in {None, "incomplete"}:
                    raise RuntimeError(captured)
                skills.append({"id": captured["node_id"], "path": captured["path"],
                               "label": label, "marker": marker})
            ordered = sorted(skills, key=lambda item: item["id"])
            relevant = ordered[-1]
            selected = resources["other" if case == "other_resource" else "primary"]
            if case in {"positive", "pagination"}:
                task = (f"Prepare the {relevant['label']} population response report from this dataset. "
                        "Save the result as report.json in this workspace.")
            else:
                task = "Report this dataset file's basename using its graph metadata. Do not load file contents or produce an analysis."
            prompt = (f"Use Wheeler's live show_node tool to inspect node {selected['id']} for this task:\n{task}\n\n"
                      + manifest["guidance"] + "\n\nUse ordinary native file tools when relevant. Work only in this "
                      "fixture project and with artifacts returned by its graph. Do not inspect evaluator logs, "
                      "other case directories, or the parent manifest. Return a concise final answer.")
            entry = {"project": str(project), "tag": tag, "node_id": selected["id"],
                     "case": case, "host": host, "prompt": prompt, "mcpconfig": _mcp_config(project, uri),
                     "skills": skills, "expected_offered_count": 0 if case == "other_resource" else count,
                     "expected_read_ids": [relevant["id"]] if case in {"positive", "pagination"} else [],
                     "expected_report": {"population_mean": 51, "recording_count": 3,
                                         "convention": relevant["marker"]} if case in {"positive", "pagination"} else None,
                     "target_sort_index": ordered.index(relevant)}
            manifest["cases"][key] = entry
            persist()
    return {"root": str(root), "manifest": str(manifest_path), "cases": list(manifest["cases"])}


async def setup_routing(root: Path, uri: str) -> dict:
    """Prepare a real router + generated ask stub catalog, without inline acts."""
    await setup(root, uri, cases=("positive", "same_node_negative"))
    manifest_path = root / "private-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["cases"].values():
        project = Path(entry["project"])
        plugin = project / "plugins/wh"
        for directory in (".claude-plugin", ".codex-plugin", "skills/ask", "skills/wheeler-voice"):
            (plugin / directory).mkdir(parents=True, exist_ok=True)
        (plugin / ".claude-plugin/plugin.json").write_text(json.dumps({
            "name": "wh", "version": "0.0.0-routing-probe", "description": "Isolated Wheeler routing evaluation"}))
        (plugin / ".codex-plugin/plugin.json").write_text(json.dumps({
            "name": "wh", "version": "0.0.0-routing-probe", "description": "Isolated Wheeler routing evaluation",
            "skills": "./skills/"}))
        files = {
            "ask": REPO / "skills/ask/SKILL.md",
            "wheeler-voice": REPO / "wheeler/_data/plugin_skills/wheeler-voice/SKILL.md",
        }
        entry["catalog_source_hashes"] = {}
        for name, source in files.items():
            destination = plugin / "skills" / name / "SKILL.md"
            shutil.copyfile(source, destination)
            entry["catalog_source_hashes"][name] = hashlib.sha256(source.read_bytes()).hexdigest()
            assert source.read_bytes() == destination.read_bytes()
        marketplace_name = "wheeler-routing-" + uuid4().hex[:8]
        catalog = project / ".agents/plugins/marketplace.json"
        catalog.parent.mkdir(parents=True, exist_ok=True)
        catalog.write_text(json.dumps({"name": marketplace_name, "plugins": [{
            "name": "wh", "source": {"source": "local", "path": "./plugins/wh"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity"}]}, indent=2))
        # Explicit transient source/enable overrides do not edit global config.
        entry["codex_config"] = [
            f'marketplaces.{marketplace_name}.source={json.dumps(str(project))}',
            f'plugins."wh@{marketplace_name}".enabled=true',
        ]
        entry["plugin_dirs"] = [str(plugin)]
        entry["catalog_mode"] = "native-session-plugin" if entry["host"] == "claude" else "native-project-marketplace"
        entry["mcpconfig"]["mcpServers"]["wheeler_core"]["enabled_tools"] = [
            "get_act", "graph_health", "show_node", "run_cypher", "graph_status", "graph_context"]
        task = (f"Check Wheeler: describe the population-response procedure linked to dataset {entry['node_id']}. "
                "I want the saved method, not a new analysis.") if entry["case"] == "positive" else (
                f"Check Wheeler: what is the file basename recorded for dataset {entry['node_id']}? "
                "Only look up its metadata; do not inspect or describe analysis procedures.")
        entry["prompt"] = task
        entry["expected_report"] = None
        entry["expected_chain"] = ["native-router-skill", "native-ask-stub", "get_act:ask", "graph_health", "show_node"]
        entry["routing_probe"] = True
    manifest["routing_probe"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return {"root": str(root), "manifest": str(manifest_path), "cases": list(manifest["cases"]),
            "note": "Native plugin discovery still requires host evidence; no host calls made by setup."}


def score_live(root: Path, logs_subdir: str = "logs", *, chain_mode: str = "router",
               stub_paths: dict[str, str] | None = None) -> dict:
    """Score actual MCP calls, successful learned-body reads and output files."""
    if chain_mode not in {"router", "stub"}:
        raise ValueError("chain_mode must be router or stub")
    manifest = json.loads((root / "private-manifest.json").read_text())
    results = []
    for key, entry in manifest["cases"].items():
        logs = root / logs_subdir / entry["host"] / entry["case"]
        if not (logs / "stdout.jsonl").exists():
            results.append({"case": key, "status": "not_run"})
            continue
        events = _events(logs / "stdout.jsonl")
        native_complete = _evidence(entry["host"], events)["native_completion_event"]
        runtime = json.loads((logs / "result.json").read_text()) if (logs / "result.json").exists() else {}
        calls, outputs, native_skill_calls = [], {}, []
        for index, event in enumerate(events):
            if entry["host"] == "claude":
                for block in event.get("message", {}).get("content", []):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        calls.append({"index": index, "id": block["id"], "name": block["name"],
                                      "arguments": block.get("input", {})})
                        if block["name"] == "Skill":
                            native_skill_calls.append(block.get("input", {}))
                    elif block.get("type") == "tool_result":
                        outputs[block.get("tool_use_id")] = block
            elif event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "mcp_tool_call":
                    calls.append({"index": index, "id": item.get("id"), "name": item.get("tool"),
                                  "arguments": item.get("arguments", {}),
                                  "succeeded": item.get("status") == "completed" and not item.get("error")})
                elif item.get("type") == "command_execution":
                    calls.append({"index": index, "id": item.get("id"), "name": "command_execution",
                                  "arguments": {"command": item.get("command", "")},
                                  "succeeded": item.get("exit_code", 0) == 0 and item.get("status") == "completed",
                                  "output": item.get("aggregated_output", "")})
        if entry["host"] == "claude":
            for call in calls:
                result = outputs.get(call["id"], {})
                call["succeeded"] = bool(result) and not result.get("is_error", False)
                call["output"] = json.dumps(result.get("content", ""))
        body_reads = []
        for skill in entry["skills"]:
            relative_skill_path = str(Path(skill["path"]).relative_to(Path(entry["project"])))
            for call in calls:
                if not call["succeeded"]:
                    continue
                selected = (call["name"] == "Read" and call["arguments"].get("file_path") == skill["path"]) or (
                    call["name"] == "command_execution" and any(
                        path in call["arguments"].get("command", "") for path in (skill["path"], relative_skill_path)))
                if selected and skill["marker"] in call.get("output", ""):
                    body_reads.append({"id": skill["id"], "event_index": call["index"]})
        successful_graph = [call for call in calls if call["succeeded"] and call["name"].endswith("show_node")]
        selected_graph = [call for call in successful_graph if entry["node_id"] in
                          [call["arguments"].get("node_id"), *call["arguments"].get("node_ids", [])]]
        read_ids = {row["id"] for row in body_reads}
        expected = set(entry["expected_read_ids"])
        report_ok = True
        report_path = Path(entry["project"]) / "report.json"
        if entry.get("expected_report"):
            try:
                report = json.loads(report_path.read_text())
                report_ok = all(report.get(k) == v for k, v in entry["expected_report"].items())
            except (OSError, ValueError):
                report_ok = False
        pagination = any(call["arguments"].get("skill_offset", 0) >= 20 for call in selected_graph)
        reasons = []
        if not native_complete:
            reasons.append("host_not_completed")
        if not selected_graph:
            reasons.append("no_successful_live_graph_call")
        if selected_graph and read_ids != expected:
            reasons.append("learned_body_selection_mismatch")
        if not report_ok:
            reasons.append("report_result_mismatch")
        if entry["case"] == "pagination" and not pagination:
            reasons.append("no_successful_pagination")
        if selected_graph and body_reads and min(r["event_index"] for r in body_reads) < selected_graph[0]["index"]:
            reasons.append("body_read_before_graph")
        chain = {}
        if entry.get("routing_probe"):
            def indexes(predicate):
                return [call["index"] for call in calls if call["succeeded"] and predicate(call)]
            if entry["host"] == "claude":
                router = indexes(lambda c: c["name"] == "Skill" and c["arguments"].get("skill", "").endswith("wheeler-voice"))
                stub = indexes(lambda c: c["name"] == "Skill" and c["arguments"].get("skill") == "wh:ask")
            else:
                source_paths = entry.get("ambient_catalog_sources", {})
                router_path = source_paths.get("router", {}).get("path", "wheeler-voice/SKILL.md")
                ask_path = (stub_paths or {}).get(key) or source_paths.get("ask_stub", {}).get("path", "ask/SKILL.md")
                router = indexes(lambda c: c["name"] == "command_execution" and router_path in c["arguments"].get("command", ""))
                stub_relative = str(Path(ask_path).relative_to(Path(entry["project"]))) if str(ask_path).startswith(entry["project"] + "/") else ask_path
                stub = indexes(lambda c: c["name"] == "command_execution" and any(
                    path in c["arguments"].get("command", "") for path in (ask_path, stub_relative)))
            act = indexes(lambda c: c["name"].endswith("get_act") and str(c["arguments"].get("name", "")).removeprefix("wh:") == "ask")
            health = indexes(lambda c: c["name"].endswith("graph_health"))
            graph = [call["index"] for call in selected_graph]
            catalog_mode = entry.get("catalog_mode")
            if chain_mode == "stub":
                catalog_mode = "project .agents/skills; explicit native ask selection; no router claim"
            elif runtime.get("use_user_config"):
                catalog_mode = "existing installed user plugin catalog; invocation-only fixture MCP isolation"
            chain = {"router": router, "ask_stub": stub, "get_act_ask": act, "graph_health": health,
                     "selected_graph": graph, "catalog_mode": catalog_mode, "tested_chain": chain_mode}
            present = all([stub, act, health, graph]) and (bool(router) if chain_mode == "router" else True)
            chain["complete_in_order"] = bool(present and stub[0] < act[0] < health[0] <= graph[0]
                                               and (router[0] <= stub[0] if chain_mode == "router" else True))
            if not chain["complete_in_order"]:
                reasons.append("routing_chain_incomplete_or_out_of_order")
        result = {"case": key, "status": "passed" if not reasons else "blocked" if not selected_graph else "failed",
                  "reasons": reasons, "successful_graph_calls": len(selected_graph),
                  "expected_read_ids": sorted(expected), "actual_read_ids": sorted(read_ids),
                  "body_reads": body_reads, "pagination_observed": pagination,
                  "report_matches": report_ok, "host_completed": native_complete,
                  "host_version": runtime.get("host_version", "unknown"),
                  "actual_model": runtime.get("actual_model", "unknown"),
                  "native_skill_calls": native_skill_calls, "routing_chain": chain,
                  "calls": [{k: v for k, v in call.items() if k != "output"} for call in calls]}
        results.append(result)
    summary = {"cases": results, "passed": sum(r["status"] == "passed" for r in results),
               "failed": sum(r["status"] == "failed" for r in results),
               "blocked": sum(r["status"] == "blocked" for r in results)}
    score_name = "trace-score.json" if logs_subdir == "logs" else "trace-score-" + logs_subdir.replace("/", "-") + ".json"
    (root / score_name).write_text(json.dumps(summary, indent=2))
    return summary


async def cleanup(root: Path) -> dict:
    from wheeler.config import WheelerConfig
    from wheeler.tools.graph_tools import _get_backend

    manifest = json.loads((root / "private-manifest.json").read_text())
    if manifest.get("kind") != "native-live-mcp-probe":
        raise ValueError("Not a fixture manifest")
    removed = []
    for item in manifest["fixture_tags"]:
        if not item["tag"].startswith("native-live-probe-"):
            raise ValueError("Refusing a non-fixture namespace")
        config = WheelerConfig(project_root=item["project"], neo4j={"uri": manifest["uri"],
            "username": "neo4j", "database": "neo4j", "project_tag": item["tag"],
            "password": ""})
        backend = await _get_backend(config)
        await backend.run_cypher("MATCH (n {_wheeler_project: $tag}) DETACH DELETE n", {"tag": item["tag"]})
        removed.append(item["tag"])
    return {"removed_fixture_tags": removed}


async def main() -> None:
    from wheeler.graph.driver import close_async_driver

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup", "setup-routing", "run", "score", "cleanup"])
    parser.add_argument("root", type=Path)
    parser.add_argument("--uri", default="")
    parser.add_argument("--host", choices=["claude", "codex"])
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.action in {"setup", "setup-routing"}:
            if not args.uri:
                parser.error("setup requires explicit --uri for an isolated Neo4j server")
            result = await (setup_routing(root, args.uri) if args.action == "setup-routing" else setup(root, args.uri))
        elif args.action == "score":
            result = score_live(root)
        elif args.action == "cleanup":
            result = await cleanup(root)
        else:
            if not args.host or not args.case:
                parser.error("run requires --host and --case")
            manifest = json.loads((root / "private-manifest.json").read_text())
            entry = manifest["cases"][f"{args.host}/{args.case}"]
            logs = root / "logs" / args.host / args.case
            if (logs / "result.json").exists():
                raise ValueError("A result already exists; preserve prior evidence")
            result = run_host(args.host, Path(entry["project"]), entry["prompt"], logs,
                              entry["mcpconfig"], args.timeout,
                              plugin_dirs=entry.get("plugin_dirs"), codex_config=entry.get("codex_config"))
        print(json.dumps(result, indent=2))
    finally:
        await close_async_driver()


if __name__ == "__main__":
    asyncio.run(main())
