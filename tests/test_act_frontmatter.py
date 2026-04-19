"""Test that act files use split-server MCP globs, not the legacy unprefixed glob.

Adversarial review #11: if any act still lists mcp__wheeler__* (unprefixed),
it will silently lose tool access under the four-server layout.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def _collect_act_files() -> list[Path]:
    """Find all .md act files in both dev and package locations."""
    repo_root = Path(__file__).resolve().parent.parent
    dirs = [
        repo_root / ".claude" / "commands" / "wh",
        repo_root / "wheeler" / "_data" / "commands",
    ]
    files = []
    for d in dirs:
        if d.is_dir():
            files.extend(d.glob("*.md"))
    return files


# Pattern that matches the legacy unprefixed glob: mcp__wheeler__
# Valid patterns use the split prefixes: mcp__wheeler_core__, mcp__wheeler_query__, etc.
_LEGACY_PATTERN = re.compile(r"mcp__wheeler__")


@pytest.mark.parametrize("act_file", _collect_act_files(), ids=lambda p: p.name)
def test_no_legacy_wheeler_glob(act_file: Path):
    """Act file must not use the unprefixed mcp__wheeler__ glob."""
    content = act_file.read_text()
    matches = _LEGACY_PATTERN.findall(content)
    assert not matches, (
        f"{act_file.name} uses legacy unprefixed 'mcp__wheeler__' glob. "
        "Update to mcp__wheeler_core__, mcp__wheeler_query__, "
        "mcp__wheeler_mutations__, or mcp__wheeler_ops__."
    )
