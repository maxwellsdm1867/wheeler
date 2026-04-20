"""Structured task logging for independent (queue/quick) execution.

Wraps raw claude -p output into a structured log entry with task metadata,
citation validation, and checkpoint detection. Called by bin/wh after
headless runs complete.

Usage: python -m wheeler.task_log <logfile> <task_description> <model> <duration_seconds>
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from wheeler.config import load_config
from wheeler.validation.citations import (
    CitationStatus,
    extract_citations,
    validate_citations,
)
from wheeler.validation.ledger import create_entry, store_entry

# Checkpoint patterns the queue prompt tells the LLM to flag
_CHECKPOINT_PATTERNS = [
    (r"(?i)checkpoint:\s*fork.decision", "fork_decision"),
    (r"(?i)checkpoint:\s*interpretation", "interpretation"),
    (r"(?i)checkpoint:\s*anomaly", "anomaly"),
    (r"(?i)checkpoint:\s*judgment", "judgment"),
    (r"(?i)checkpoint:\s*unexpected", "unexpected"),
    (r"(?i)checkpoint:\s*rabbit.hole", "rabbit_hole"),
]


def generate_task_id() -> str:
    """Generate a task ID like T-20260303-001."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    # Use timestamp-based suffix for uniqueness
    suffix = datetime.now(timezone.utc).strftime("%H%M%S")
    return f"T-{today}-{suffix}"


def detect_checkpoints(text: str) -> list[dict]:
    """Detect checkpoint flags in LLM output text."""
    flags = []
    for pattern, flag_type in _CHECKPOINT_PATTERNS:
        for match in re.finditer(pattern, text):
            # Grab surrounding context (up to 200 chars after the match)
            start = match.start()
            context_end = min(start + 300, len(text))
            # Find the end of the sentence/paragraph
            context = text[start:context_end]
            newline = context.find("\n\n")
            if newline > 0:
                context = context[:newline]
            flags.append({"type": flag_type, "context": context.strip()})
    return flags


def extract_result_text(raw: str) -> str:
    """Extract the text content from claude -p output."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data.get("result", "")
        if isinstance(data, str):
            return data
    except json.JSONDecodeError:
        pass
    return raw


async def build_task_log(
    log_path: str,
    task_description: str,
    model: str,
    duration_seconds: int,
) -> None:
    """Read raw output, wrap in structured log, validate citations, write back."""
    path = Path(log_path)
    if not path.exists():
        return

    config = load_config()
    raw = path.read_text()
    text = extract_result_text(raw)

    if not text:
        return

    task_id = generate_task_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    checkpoint_flags = detect_checkpoints(text)

    # Determine status based on checkpoints
    status = "flagged" if checkpoint_flags else "completed"

    # Citation validation
    citation_validation = None
    cited = extract_citations(text)
    if cited:
        results = await validate_citations(text, config)
        entry = create_entry("independent", text[:200], results)
        await store_entry(entry, config)

        valid = [r for r in results if r.status == CitationStatus.VALID]
        invalid = [r for r in results if r.status == CitationStatus.NOT_FOUND]
        stale = [r for r in results if r.status == CitationStatus.STALE]
        weak = [r for r in results if r.status == CitationStatus.MISSING_PROVENANCE]

        citation_validation = {
            "total": len(results),
            "valid": len(valid),
            "invalid": [r.node_id for r in invalid],
            "stale": [r.node_id for r in stale],
            "missing_provenance": [r.node_id for r in weak],
            "pass_rate": entry.pass_rate,
        }
    elif len(text) > 80:
        entry = create_entry("independent", text[:200], [])
        await store_entry(entry, config)
        citation_validation = {
            "total": 0,
            "valid": 0,
            "ungrounded": True,
            "pass_rate": 0.0,
        }

    # Extract token usage from claude -p JSON output if available
    token_usage = {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # claude -p --output-format json includes usage stats
            if "usage" in data:
                token_usage = data["usage"]
            elif "input_tokens" in data:
                token_usage = {
                    "input": data.get("input_tokens", 0),
                    "output": data.get("output_tokens", 0),
                }
    except (json.JSONDecodeError, TypeError):
        pass

    # Build structured log entry
    log_entry = {
        "task_id": task_id,
        "timestamp": timestamp,
        "task_description": task_description,
        "status": status,
        "model": model,
        "duration_seconds": duration_seconds,
        "checkpoint_flags": checkpoint_flags,
        "result": text,
        "citation_validation": citation_validation,
        "token_usage": token_usage,
    }

    # Write structured log
    path.write_text(json.dumps(log_entry, indent=2))

    # Print summary to terminal
    _print_summary(log_entry, cited, text)


def _print_summary(entry: dict, cited: list, text: str) -> None:
    """Print colored terminal summary."""
    task_id = entry["task_id"]
    status = entry["status"]
    duration = entry["duration_seconds"]

    # Status line
    if status == "flagged":
        status_color = "\033[33m"  # yellow
        status_icon = "!"
    elif status == "completed":
        status_color = "\033[32m"  # green
        status_icon = "✓"
    else:
        status_color = "\033[31m"  # red
        status_icon = "✗"

    print(f"  \033[90m{task_id}\033[0m  {status_color}{status_icon} {status}\033[0m  \033[90m({duration}s)\033[0m")

    # Checkpoint flags
    for flag in entry.get("checkpoint_flags", []):
        print(f"  \033[33m  ⚑ {flag['type']}\033[0m: {flag['context'][:80]}")

    # Citation validation
    validation = entry.get("citation_validation")
    if validation:
        if validation.get("ungrounded"):
            print("  \033[33mcitations: none — ungrounded\033[0m")
        else:
            total = validation.get("total", 0)
            valid = validation.get("valid", 0)
            rate = validation.get("pass_rate", 0)
            color = "\033[32m" if rate >= 0.8 else "\033[33m" if rate >= 0.5 else "\033[31m"
            print(f"  \033[90mcitations\033[0m  {color}{valid}/{total} ({rate:.0%})\033[0m")


def main():
    if len(sys.argv) < 5:
        print(
            "Usage: python -m wheeler.task_log <logfile> <task_description> <model> <duration_seconds>",
            file=sys.stderr,
        )
        sys.exit(1)
    log_path = sys.argv[1]
    task_description = sys.argv[2]
    model = sys.argv[3]
    duration_seconds = int(sys.argv[4])
    asyncio.run(build_task_log(log_path, task_description, model, duration_seconds))


if __name__ == "__main__":
    main()
