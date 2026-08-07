"""Act corpus reader: the single reader of Wheeler's `/wh:*` act definitions.

An act is a markdown file with YAML frontmatter, shipped inside the package at
`wheeler/_data/commands/*.md`. Historically each act was consumed only by
Claude Code, which loads those files as slash commands. A second host (OpenAI
Codex) means the content would have to be maintained twice, so the body becomes
MCP-served (`list_acts` / `get_act` in `mcp_core.py`) and per-host artifacts
become thin generated stubs. This module is the one place that reads the corpus.

Two properties hosts need are DERIVED from `allowed-tools` rather than declared
as extra frontmatter keys, so `allowed-tools` stays the single source of truth
and the two can never disagree:

- `mode`: which enforcement tier the act runs at (chat / write / execute).
- `orchestration`: whether the act fans work out (none / skill-dispatch /
  subagents), which is the part a non-Claude host cannot infer on its own.

`orchestration_note()` renders a short host-specific note for that shape. The
body itself is never rewritten per host: it is returned verbatim.
"""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Files in _data/commands/ that are documentation, not acts. CLAUDE.md is the
# act-authoring guide. Counting it as an act is a silent off-by-one, which is
# why the exact act count is asserted in tests/test_acts.py.
NON_ACT_FILES = frozenset({"CLAUDE.md"})

# The complete frontmatter vocabulary across the corpus. Deriving beats adding:
# a new key has to be written into every act and can then contradict the tool
# list, which is what `mode` and `orchestration` avoid.
FRONTMATTER_KEYS = ("name", "description", "argument-hint", "allowed-tools")

# Every act's `name` is namespaced. The short act id drops it.
NAME_PREFIX = "wh:"

# Hosts that get a tailored orchestration note. Same two-way fork as
# `integrations/llmsr/cli.py::_GENERATORS` and the hand-written host branch in
# the llmsr-discover act.
HOSTS = ("claude", "codex")
DEFAULT_HOST = "claude"

MODES = ("chat", "write", "execute")
ORCHESTRATIONS = ("none", "skill-dispatch", "subagents")

_OPS_PREFIX = "mcp__wheeler_ops__"
_MUTATIONS_PREFIX = "mcp__wheeler_mutations__"

# Granting any of these means the act hands work to other agents.
SUBAGENT_TOOLS = frozenset({
    "Agent",
    "Task",
    "TaskCreate",
    "TaskList",
    "TaskUpdate",
    "TaskGet",
    "TeamCreate",
    "TeamDelete",
    "SendMessage",
})
SKILL_TOOL = "Skill"


def derive_mode(allowed_tools: tuple[str, ...] | list[str]) -> str:
    """Return the enforcement mode implied by an act's `allowed-tools`.

    Ops tools (validators, scanners, consistency) are the widest grant, so they
    mark EXECUTE. Mutations without ops is WRITE. Neither is CHAT (read-only
    against the graph).
    """
    if any(t.startswith(_OPS_PREFIX) for t in allowed_tools):
        return "execute"
    if any(t.startswith(_MUTATIONS_PREFIX) for t in allowed_tools):
        return "write"
    return "chat"


def derive_orchestration(allowed_tools: tuple[str, ...] | list[str]) -> str:
    """Return the orchestration shape implied by an act's `allowed-tools`.

    Agent/team/task tools mean the act fans work out to other agents. `Skill`
    alone means it routes to a sibling act in the same conversation.
    """
    granted = set(allowed_tools)
    if granted & SUBAGENT_TOOLS:
        return "subagents"
    if SKILL_TOOL in granted:
        return "skill-dispatch"
    return "none"


@dataclass(frozen=True)
class Act:
    """One parsed act: frontmatter, verbatim body, derived shape."""

    act_id: str
    """Short name with the `wh:` prefix stripped, e.g. `chat`."""

    name: str
    """Namespaced name exactly as the frontmatter declares it, e.g. `wh:chat`."""

    description: str
    argument_hint: str
    allowed_tools: tuple[str, ...]

    body: str
    """The markdown after the frontmatter, verbatim apart from surrounding
    blank lines. This is the system prompt and is never host-adapted."""

    mode: str
    orchestration: str
    filename: str

    def summary(self) -> dict:
        """Return the listing shape (everything but the body)."""
        return {
            "name": self.name,
            "act_id": self.act_id,
            "description": self.description,
            "argument_hint": self.argument_hint,
            "mode": self.mode,
            "orchestration": self.orchestration,
        }


def act_data_dir() -> Path:
    """Return the packaged act directory, `wheeler/_data/commands/`."""
    return Path(str(resources.files("wheeler") / "_data" / "commands"))


def parse_act(path: Path) -> Act:
    """Parse one act markdown file.

    Raises ValueError if the file has no YAML frontmatter block.
    """
    text = path.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3 or parts[0].strip():
        raise ValueError(f"{path.name}: no YAML frontmatter block")
    frontmatter = yaml.safe_load(parts[1]) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError(f"{path.name}: frontmatter is not a mapping")

    name = str(frontmatter.get("name") or f"{NAME_PREFIX}{path.stem}")
    act_id = name[len(NAME_PREFIX):] if name.startswith(NAME_PREFIX) else name
    tools = frontmatter.get("allowed-tools") or []
    if isinstance(tools, str):
        tools = [tools]
    allowed_tools = tuple(str(t) for t in tools)

    return Act(
        act_id=act_id,
        name=name,
        description=str(frontmatter.get("description") or ""),
        argument_hint=str(frontmatter.get("argument-hint") or ""),
        allowed_tools=allowed_tools,
        body=parts[2].strip("\n"),
        mode=derive_mode(allowed_tools),
        orchestration=derive_orchestration(allowed_tools),
        filename=path.name,
    )


@functools.lru_cache(maxsize=1)
def load_acts() -> tuple[Act, ...]:
    """Load every act in the packaged corpus, sorted by act id.

    Cached: the corpus ships inside the package and cannot change under a
    running process. Call `load_acts.cache_clear()` in tests that need a
    re-read.
    """
    directory = act_data_dir()
    acts: list[Act] = []
    for path in sorted(directory.glob("*.md")):
        if path.name in NON_ACT_FILES:
            continue
        try:
            acts.append(parse_act(path))
        except (ValueError, yaml.YAMLError) as exc:
            logger.warning("Skipping unparseable act %s: %s", path.name, exc)
    return tuple(sorted(acts, key=lambda a: a.act_id))


def find_act(name: str) -> Act | None:
    """Look up one act by `chat` or `wh:chat`. Returns None if unknown."""
    wanted = (name or "").strip()
    if not wanted:
        return None
    if wanted.startswith("/"):
        wanted = wanted[1:]
    bare = wanted[len(NAME_PREFIX):] if wanted.startswith(NAME_PREFIX) else wanted
    for act in load_acts():
        if act.act_id == bare or act.name == wanted:
            return act
    return None


def act_ids() -> tuple[str, ...]:
    """Return every known act id, sorted."""
    return tuple(act.act_id for act in load_acts())


# --- Host-adapted orchestration notes ---
#
# The act body is single-source and host-agnostic. What differs per host is the
# machinery for fanning work out, so that is the only thing said here. The note
# is an appendix to the body, not a replacement for any part of it.

_CLAUDE_SUBAGENTS = """\
## Orchestration note (host: claude)

This act hands work to other agents. Spawn one with the `Agent` tool. For a
coordinated group with its own task list, use `TeamCreate` plus `TaskCreate` /
`TaskUpdate` / `TaskGet` / `TaskList`, message members with `SendMessage`, and
`TeamDelete` when the group is finished. Where the body above names one of
those tools, it means exactly that tool."""

_CODEX_SUBAGENTS = """\
## Orchestration note (host: codex)

This act hands work to other agents. Codex exposes them through
`features.multi_agent`: `spawn_agent` starts one, `send_input` gives a running
one more instructions, `wait_agent` collects its result, `close_agent` shuts it
down. Reusable roles are declared as custom agent files under
`.codex/agents/*.toml`. Wherever the body above names a Claude Code agent, team,
or task tool, use these calls instead: they are the same shape of work, not a
different plan. If `features.multi_agent` is not enabled in this environment,
run the fanned-out steps yourself in sequence and say that you did so, rather
than skipping them."""

_CLAUDE_SKILL = """\
## Orchestration note (host: claude)

This act routes to a sibling act rather than doing the work itself. Invoke the
sibling with the `Skill` tool, naming it `wh:<act>` (for example `wh:plan`). Do
not paste the sibling's instructions inline: let it run as its own act so its
tool restrictions apply."""

_CODEX_SKILL = """\
## Orchestration note (host: codex)

This act routes to a sibling act rather than doing the work itself. Invoke the
sibling skill as `$<act_id>` (for example `$plan`). If that skill is not
installed here, call `get_act` over MCP with the sibling's name and follow the
body it returns in this same conversation."""

_NOTES: dict[tuple[str, str], str] = {
    ("subagents", "claude"): _CLAUDE_SUBAGENTS,
    ("subagents", "codex"): _CODEX_SUBAGENTS,
    ("skill-dispatch", "claude"): _CLAUDE_SKILL,
    ("skill-dispatch", "codex"): _CODEX_SKILL,
}


def normalize_host(host: str | None) -> str:
    """Return a supported host name. Empty or None means the default host.

    Raises ValueError for an unrecognized host, so a Codex caller never gets
    Claude Code tool names by accident.
    """
    resolved = (host or DEFAULT_HOST).strip().lower()
    if resolved not in HOSTS:
        raise ValueError(
            f"Unknown host {host!r}. Supported hosts: {', '.join(HOSTS)}"
        )
    return resolved


def orchestration_note(act: Act, host: str | None = None) -> str:
    """Return the host-appropriate orchestration note for an act.

    Empty string when the act orchestrates nothing: there is nothing to say and
    a filler paragraph would only dilute the prompt.
    """
    return _NOTES.get((act.orchestration, normalize_host(host)), "")
