"""Post-hoc citation validation for headless (queue/quick) output.

Reads JSON output from claude -p, extracts citations, validates against Neo4j,
appends validation results to the log file. Called by bin/wh after queue/quick runs.

Usage: python -m wheeler.validate_output <logfile>
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from wheeler.config import load_config
from wheeler.validation.citations import (
    CitationStatus,
    extract_citations,
    validate_citations,
)
from wheeler.validation.ledger import create_entry, store_entry


async def validate_log(log_path: str) -> None:
    """Read a log file, validate citations, append results."""
    path = Path(log_path)
    if not path.exists():
        return

    config = load_config()
    raw = path.read_text()

    # Extract text content from the JSON output
    # claude -p --output-format json returns {"result": "...", ...}
    text = ""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            text = data.get("result", "")
        elif isinstance(data, str):
            text = data
    except json.JSONDecodeError:
        # Plain text output
        text = raw

    if not text:
        return

    cited = extract_citations(text)
    if cited:
        results = await validate_citations(text, config)
        entry = create_entry("independent", text[:200], results)
        await store_entry(entry, config)

        # Build validation summary
        valid = [r for r in results if r.status == CitationStatus.VALID]
        invalid = [r for r in results if r.status == CitationStatus.NOT_FOUND]
        stale = [r for r in results if r.status == CitationStatus.STALE]
        weak = [r for r in results if r.status == CitationStatus.MISSING_PROVENANCE]

        validation = {
            "total": len(results),
            "valid": len(valid),
            "invalid": [r.node_id for r in invalid],
            "stale": [r.node_id for r in stale],
            "missing_provenance": [r.node_id for r in weak],
            "pass_rate": entry.pass_rate,
        }
    elif len(text) > 80:
        # Non-trivial output with zero citations
        entry = create_entry("independent", text[:200], [])
        await store_entry(entry, config)
        validation = {
            "total": 0,
            "valid": 0,
            "ungrounded": True,
            "pass_rate": 0.0,
        }
    else:
        return

    # Append validation to the log file
    try:
        existing = json.loads(raw) if raw.strip().startswith("{") else {}
        if isinstance(existing, dict):
            existing["_citation_validation"] = validation
            path.write_text(json.dumps(existing, indent=2))
        else:
            # Can't merge into non-dict, write alongside
            val_path = path.with_suffix(".validation.json")
            val_path.write_text(json.dumps(validation, indent=2))
    except Exception:
        # Fallback: write validation as separate file
        val_path = path.with_suffix(".validation.json")
        val_path.write_text(json.dumps(validation, indent=2))

    # Print summary to terminal
    if validation.get("ungrounded"):
        print(f"  \033[33mcitations: none — ungrounded\033[0m")
    else:
        parts = []
        for r in (results if cited else []):
            if r.status == CitationStatus.VALID:
                parts.append(f"\033[32m{r.node_id}\033[0m")
            elif r.status == CitationStatus.NOT_FOUND:
                parts.append(f"\033[31m{r.node_id}\033[0m")
            elif r.status == CitationStatus.STALE:
                parts.append(f"\033[33m{r.node_id}~\033[0m")
            elif r.status == CitationStatus.MISSING_PROVENANCE:
                parts.append(f"\033[33m{r.node_id}!\033[0m")
        if parts:
            print(f"  \033[90mcitations\033[0m  {' '.join(parts)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m wheeler.validate_output <logfile>", file=sys.stderr)
        sys.exit(1)
    asyncio.run(validate_log(sys.argv[1]))


if __name__ == "__main__":
    main()
