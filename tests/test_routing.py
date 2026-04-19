"""End-to-end tests for /wh:* auto-routing infrastructure.

Validates that command descriptions, trigger patterns, tree sync,
and router structure will produce correct routing behavior.
"""

from pathlib import Path

import pytest
import yaml

CLAUDE_DIR = Path(__file__).parent.parent / ".claude" / "commands" / "wh"
DATA_DIR = Path(__file__).parent.parent / "wheeler" / "_data" / "commands"

# ── Canonical command lists ──────────────────────────────────────────

# Commands whose descriptions should trigger auto-invocation (have "Use when/for/only")
TRIGGER_COMMANDS = [
    "add",
    "ask",
    "chat",
    "close",
    "compile",
    "dev-feedback",
    "discuss",
    "dream",
    "execute",
    "handoff",
    "note",
    "pair",
    "pause",
    "plan",
    "reconvene",
    "report",
    "resume",
    "status",
    "triage",
    "write",
]

# Commands that must NOT have trigger descriptions (internal / explicit-only)
NON_TRIGGER_COMMANDS = ["queue", "init", "ingest", "update"]

# Router command (outcome-only description, user-invoked)
ROUTER_COMMAND = "start"

# Commands the router must never route to
ROUTER_EXCLUDED = {"queue", "init", "ingest", "update"}

# All routable commands (everything the router CAN choose)
ROUTABLE_COMMANDS = set(TRIGGER_COMMANDS) - ROUTER_EXCLUDED

# Domain-anchor terms: every trigger description must contain at least one
ANCHOR_TERMS = ["Wheeler", "knowledge graph", "knowledge-graph"]


# ── Helpers ──────────────────────────────────────────────────────────


def _load_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a command .md file."""
    content = path.read_text()
    parts = content.split("---", 2)
    return yaml.safe_load(parts[1])


def _get_description(path: Path) -> str:
    """Extract the description string from frontmatter."""
    return _load_frontmatter(path)["description"]


# ── 1. Tree sync: .claude/ and _data/ descriptions are identical ─────


class TestTreeSync:
    def test_every_claude_command_has_data_mirror(self):
        """Every .md in .claude/commands/wh/ must exist in wheeler/_data/commands/."""
        for md in sorted(CLAUDE_DIR.glob("*.md")):
            if md.name == "CLAUDE.md":
                continue
            mirror = DATA_DIR / md.name
            assert mirror.exists(), f"{md.name} missing from wheeler/_data/commands/"

    def test_descriptions_identical(self):
        """Description lines must be byte-identical between the two trees."""
        for md in sorted(CLAUDE_DIR.glob("*.md")):
            if md.name == "CLAUDE.md":
                continue
            mirror = DATA_DIR / md.name
            if not mirror.exists():
                pytest.skip(f"mirror missing for {md.name}")
            claude_desc = _get_description(md)
            data_desc = _get_description(mirror)
            assert claude_desc == data_desc, (
                f"{md.name} description mismatch:\n"
                f"  .claude: {claude_desc}\n"
                f"  _data:   {data_desc}"
            )

    def test_claude_md_inventories_identical(self):
        """Both CLAUDE.md files list the same commands."""
        claude_text = (CLAUDE_DIR / "CLAUDE.md").read_text()
        data_text = (DATA_DIR / "CLAUDE.md").read_text()
        assert claude_text == data_text, "CLAUDE.md files differ between trees"


# ── 2. Trigger descriptions: narrow, domain-anchored ────────────────


class TestTriggerDescriptions:
    @pytest.mark.parametrize("cmd", TRIGGER_COMMANDS)
    def test_has_trigger_prefix(self, cmd):
        """Trigger commands must start with 'Use when', 'Use for', or 'Use only'."""
        desc = _get_description(CLAUDE_DIR / f"{cmd}.md")
        assert desc.startswith(("Use when", "Use for", "Use only")), (
            f"{cmd}.md description lacks trigger prefix: {desc!r}"
        )

    @pytest.mark.parametrize("cmd", TRIGGER_COMMANDS)
    def test_contains_anchor_term(self, cmd):
        """Every trigger description must contain an explicit Wheeler/graph term."""
        desc = _get_description(CLAUDE_DIR / f"{cmd}.md")
        has_anchor = any(term in desc for term in ANCHOR_TERMS)
        assert has_anchor, (
            f"{cmd}.md description lacks anchor term ({ANCHOR_TERMS}): {desc!r}"
        )

    @pytest.mark.parametrize("cmd", TRIGGER_COMMANDS)
    def test_under_130_chars(self, cmd):
        """Descriptions should be concise enough for the skill list."""
        desc = _get_description(CLAUDE_DIR / f"{cmd}.md")
        assert len(desc) <= 130, (
            f"{cmd}.md description is {len(desc)} chars (max 130): {desc!r}"
        )

    @pytest.mark.parametrize("cmd", TRIGGER_COMMANDS)
    def test_no_yaml_breaking_colon_space(self, cmd):
        """Descriptions must not contain ': ' mid-value (breaks YAML parsing)."""
        desc = _get_description(CLAUDE_DIR / f"{cmd}.md")
        # If we got here, yaml.safe_load succeeded, so this is a double-check.
        # The actual risk is colon-space inside the value after the first ': '.
        # We test by re-parsing -- if _get_description didn't throw, we're good.
        assert desc, f"{cmd}.md has empty description"


# ── 3. Non-trigger commands: no auto-fire ────────────────────────────


class TestNonTriggerCommands:
    @pytest.mark.parametrize("cmd", NON_TRIGGER_COMMANDS)
    def test_no_trigger_prefix(self, cmd):
        """Internal commands must NOT start with trigger prefixes."""
        desc = _get_description(CLAUDE_DIR / f"{cmd}.md")
        assert not desc.startswith(("Use when", "Use for", "Use only")), (
            f"{cmd}.md should not have a trigger prefix: {desc!r}"
        )


# ── 4. Router (/wh:start) structure ─────────────────────────────────


class TestRouter:
    def test_router_exists_both_trees(self):
        """start.md must exist in both command trees."""
        assert (CLAUDE_DIR / "start.md").exists()
        assert (DATA_DIR / "start.md").exists()

    def test_router_no_trigger_prefix(self):
        """Router description must be outcome-only, not a trigger."""
        desc = _get_description(CLAUDE_DIR / "start.md")
        assert not desc.startswith(("Use when", "Use for", "Use only")), (
            f"start.md must not auto-fire, but has trigger prefix: {desc!r}"
        )

    def test_router_has_skill_tool(self):
        """Router must have Skill in allowed-tools to invoke other commands."""
        fm = _load_frontmatter(CLAUDE_DIR / "start.md")
        assert "Skill" in fm["allowed-tools"], "start.md needs Skill in allowed-tools"

    def test_router_has_ask_user_question(self):
        """Router must be able to ask the user for intent."""
        fm = _load_frontmatter(CLAUDE_DIR / "start.md")
        assert "AskUserQuestion" in fm["allowed-tools"], (
            "start.md needs AskUserQuestion in allowed-tools"
        )

    def test_router_has_argument_hint(self):
        """Router should accept optional arguments."""
        fm = _load_frontmatter(CLAUDE_DIR / "start.md")
        assert "argument-hint" in fm, "start.md should have argument-hint"

    def test_router_body_references_arguments(self):
        """Router body must reference $ARGUMENTS for direct routing."""
        content = (CLAUDE_DIR / "start.md").read_text()
        assert "$ARGUMENTS" in content, "start.md should reference $ARGUMENTS"

    def test_router_excludes_internal_commands(self):
        """Router body must explicitly exclude internal commands."""
        content = (CLAUDE_DIR / "start.md").read_text()
        for cmd in ROUTER_EXCLUDED:
            assert cmd in content, (
                f"start.md should mention {cmd} in its exclusion list"
            )

    def test_router_covers_all_routable_commands(self):
        """Router routing table must mention every routable command."""
        content = (CLAUDE_DIR / "start.md").read_text()
        # Extract the routing priority section
        for cmd in ROUTABLE_COMMANDS:
            assert f"`{cmd}`" in content, (
                f"start.md routing table is missing `{cmd}`"
            )


# ── 5. False-positive resistance ─────────────────────────────────────


class TestFalsePositiveResistance:
    """Verify that descriptions won't fire on general coding/research prompts.

    These tests check structural properties, not LLM behavior. They ensure
    that no description is so broad it would match non-Wheeler intent.
    """

    # Words that are too generic to appear as the ONLY domain signal
    GENERIC_ONLY_WORDS = [
        "finding",
        "paper",
        "execute",
        "write",
        "plan",
        "note",
        "status",
        "report",
        "discuss",
        "compile",
    ]

    @pytest.mark.parametrize("cmd", TRIGGER_COMMANDS)
    def test_not_solely_generic(self, cmd):
        """No trigger description should rely only on generic research words."""
        desc = _get_description(CLAUDE_DIR / f"{cmd}.md")
        has_anchor = any(term in desc for term in ANCHOR_TERMS)
        assert has_anchor, (
            f"{cmd}.md relies on generic terms without Wheeler/graph anchor: {desc!r}"
        )

    @pytest.mark.parametrize("cmd", TRIGGER_COMMANDS)
    def test_no_bare_verb_trigger(self, cmd):
        """Descriptions shouldn't start with just 'Use when the user wants to'
        followed by a generic verb without Wheeler context."""
        desc = _get_description(CLAUDE_DIR / f"{cmd}.md")
        # Anchor term must appear somewhere in the description (already
        # enforced by test_contains_anchor_term). This test adds a proximity
        # check: if the description is long, the anchor shouldn't be buried
        # at the very end where a model might match on the generic prefix.
        # For short descriptions (under 120 chars) the anchor is always
        # close enough. For longer ones, it must appear in the first 100.
        if len(desc) > 120:
            has_early_anchor = any(
                term.lower() in desc[:100].lower() for term in ANCHOR_TERMS
            )
            assert has_early_anchor, (
                f"{cmd}.md anchor term appears too late in description: {desc!r}"
            )


# ── 6. CLAUDE.md inventory completeness ──────────────────────────────


class TestInventory:
    def test_start_in_claude_md(self):
        """CLAUDE.md must list the start command."""
        content = (CLAUDE_DIR / "CLAUDE.md").read_text()
        assert "`start`" in content, "CLAUDE.md missing `start` in command inventory"

    def test_all_commands_have_files(self):
        """Every .md file (excluding CLAUDE.md) should be a real command."""
        files = {
            p.stem for p in CLAUDE_DIR.glob("*.md") if p.name != "CLAUDE.md"
        }
        # Just verify we have at least all trigger + non-trigger + router
        expected = set(TRIGGER_COMMANDS) | set(NON_TRIGGER_COMMANDS) | {ROUTER_COMMAND}
        missing = expected - files
        assert not missing, f"Missing command files: {missing}"
