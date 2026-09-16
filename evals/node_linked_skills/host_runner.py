"""Fresh native-host sessions for controlled, oracle-blind skill evaluations.

This runner uses the host's subscription authentication and model defaults. It
never changes HOME/CODEX_HOME, persisted configuration, or authentication files.
Fixture workspaces must contain the audited ``fixture_cli.py``. Claude's shell
allowlist grants only that CLI; Codex uses its normal workspace-write sandbox.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time
from typing import Any


def _events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def _evidence(host: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    models: set[str] = set()
    primary_models: set[str] = set()
    model_evidence = []
    tools: dict[str, dict[str, Any]] = {}
    final = ""
    completed = False
    errors: list[Any] = []
    denials: list[Any] = []
    session_id = None
    for index, event in enumerate(events):
        kind = event.get("type", "")
        if host == "claude":
            if kind == "system" and event.get("subtype") == "init":
                session_id = event.get("session_id")
                model = event.get("model")
                if model:
                    models.add(model)
                    model_evidence.append({"event_index": index, "source": "system.init.model", "model": model})
            if kind == "assistant":
                message = event.get("message", {})
                model = message.get("model")
                if model:
                    models.add(model)
                    primary_models.add(model)
                    model_evidence.append({"event_index": index, "source": "assistant.message.model", "model": model})
                for block in message.get("content", []):
                    if block.get("type") == "tool_use":
                        key = block.get("id", str(index))
                        tools[key] = {"id": key, "name": block.get("name"), "input": block.get("input")}
            if kind == "result":
                completed = event.get("subtype") == "success" and not event.get("is_error", False)
                final = event.get("result", "")
                denials.extend(event.get("permission_denials", []))
                errors.extend(event.get("errors", []))
                for model in event.get("modelUsage", {}):
                    models.add(model)
                    model_evidence.append({"event_index": index, "source": "result.modelUsage", "model": model})
                if not completed:
                    errors.append({"subtype": event.get("subtype"), "result": final})
        else:
            if kind == "thread.started":
                session_id = event.get("thread_id")
            # Only native runtime metadata counts, never model names in text.
            if kind in {"thread.started", "session_meta", "session.started", "turn.started"}:
                metadata = event.get("payload", event)
                model = metadata.get("model")
                if model:
                    models.add(model)
                    primary_models.add(model)
                    model_evidence.append({"event_index": index, "source": kind + ".model", "model": model})
            if kind == "turn.completed":
                completed = True
            if kind in {"error", "turn.failed"}:
                errors.append(event)
            item = event.get("item", {})
            item_type = item.get("type")
            if item_type in {"command_execution", "mcp_tool_call", "web_search", "file_change", "tool_call"}:
                key = item.get("id", str(index))
                tools[key] = {"id": key, "name": item_type, "command": item.get("command"), "status": item.get("status")}
            if kind == "item.completed" and item_type == "agent_message":
                final = item.get("text", "")
    return {
        "session_id": session_id,
        "actual_model": sorted(primary_models)[0] if len(primary_models) == 1 else "unknown",
        "primary_models": sorted(primary_models),
        "actual_models": sorted(models),
        "model_evidence": model_evidence,
        "model_selection": "host default; no model override; user config excluded",
        "final_response": final,
        "native_completion_event": completed,
        "tool_invocation_count": len(tools),
        "tool_invocations": list(tools.values()),
        "errors": errors,
        "permission_denials": denials,
    }


def run_session(
    host: str, cwd: Path, prompt: str, output_dir: Path, timeout_seconds: int = 150,
    allowed_command: str = "/private/tmp/wheeler-main-lessons-20260915/.venv/bin/python fixture_cli.py",
) -> dict[str, Any]:
    """Execute one independent case; infrastructure failure is never a negative.

    ``status`` is completed, host_error, timeout, launch_error, or
    permission_denied. Behavioral scoring belongs to the caller and must
    inspect fixture audit events.
    """
    if host not in {"claude", "codex"}:
        raise ValueError("host must be claude or codex")
    cwd = cwd.resolve(strict=True)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "prompt.txt"
    prompt_path.write_text(prompt)
    stdout_path = output_dir / "stdout.jsonl"
    stderr_path = output_dir / "stderr.log"
    environment = os.environ.copy()
    # These native CLI trials use subscription auth. Drop all provider API
    # keys rather than maintaining a provider-specific credential allowlist.
    for key in tuple(environment):
        if key.endswith("_API_KEY"):
            environment.pop(key)
    try:
        version = subprocess.run(
            [host, "--version"], capture_output=True, text=True,
            env=environment, timeout=15, check=False,
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        version = "unknown"
    if host == "claude":
        mcp = output_dir / "empty-mcp.json"
        mcp.write_text(json.dumps({"mcpServers": {}}))
        settings = output_dir / "settings.json"
        settings.write_text(json.dumps({"disableAllHooks": True, "autoMemoryEnabled": False}))
        command = [
            "claude", "--print", "--output-format", "stream-json", "--verbose",
            "--tools", "Bash", "--strict-mcp-config", "--mcp-config", str(mcp),
            "--setting-sources", "project", "--settings", str(settings),
            "--no-session-persistence", "--no-chrome", "--permission-mode", "dontAsk",
            "--allowedTools", f"Bash({allowed_command} *)", "--", prompt,
        ]
    else:
        command = [
            "codex", "exec", "--ignore-user-config", "--ephemeral", "--json",
            "--sandbox", "workspace-write", "--skip-git-repo-check", "--cd", str(cwd),
            "-c", 'approval_policy="never"', "-",
        ]
    (output_dir / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    started = time.time()
    status = "host_error"
    exit_code = None
    launch_error = None
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        try:
            process = subprocess.Popen(
                command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
                stdin=subprocess.PIPE, text=True, start_new_session=True,
            )
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
            status = "launch_error"
            launch_error = str(exc)
    evidence = _evidence(host, _events(stdout_path))
    outside_contract = []
    for invocation in evidence["tool_invocations"]:
        if host == "claude":
            shell_command = (invocation.get("input") or {}).get("command", "")
        else:
            shell_command = invocation.get("command") or ""
        try:
            parts = shlex.split(shell_command)
            # Codex logs its shell wrapper rather than just the command.
            if len(parts) == 3 and parts[1] in {"-lc", "-c"}:
                shell_command = parts[2]
            lexer = shlex.shlex(shell_command, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            parts = list(lexer)
            expected = shlex.split(allowed_command)
            valid = parts[:len(expected)] == expected and len(parts) in {len(expected) + 1, len(expected) + 2}
            valid = valid and not any(token in {";", "&&", "||", "|", ">", ">>", "<", "&", "(", ")"} for token in parts)
        except ValueError:
            valid = False
        if not valid:
            outside_contract.append(invocation)
    if status not in {"timeout", "launch_error"}:
        status = "completed" if exit_code == 0 and evidence["native_completion_event"] else "host_error"
        if evidence["permission_denials"]:
            status = "permission_denied"
    result = {
        "host": host, "host_version": version, "status": status,
        "exit_code": exit_code, "elapsed_seconds": round(time.time() - started, 3),
        "started_unix": started, "timeout_seconds": timeout_seconds,
        "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path),
        "command_path": str(output_dir / "command.json"), "prompt_path": str(prompt_path),
        "launch_error": launch_error, **evidence,
        "allowed_command": allowed_command,
        "out_of_contract_tool_invocations": outside_contract,
        "tool_contract_valid": not outside_contract,
    }
    (output_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
