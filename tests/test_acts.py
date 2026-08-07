"""Tests for the act corpus reader and the list_acts / get_act MCP tools.

The corpus is the single source of act content now that a second host (Codex)
consumes it, so the invariants worth holding are: every shipped act is
reachable, the act-authoring guide is not mistaken for an act, the derived
mode and orchestration agree with `allowed-tools`, and the body is byte-for-byte
the same whichever host asks for it.
"""

from pathlib import Path

import pytest
import yaml

from wheeler import acts

DATA_DIR = Path(__file__).parent.parent / "wheeler" / "_data" / "commands"

# `_data/commands/` ships 40 .md files: 39 acts plus CLAUDE.md, the
# act-authoring guide. Off by one here is exactly the failure that would ship
# silently, so it is pinned.
NUM_ACTS = 39


def _frontmatter(path: Path) -> dict:
    """Parse frontmatter independently of wheeler.acts, for cross-checking."""
    return yaml.safe_load(path.read_text().split("---", 2)[1])


class TestCorpusCoverage:
    def test_act_count_is_exact(self):
        assert len(acts.load_acts()) == NUM_ACTS

    def test_data_dir_holds_acts_plus_the_guide(self):
        """Guards the count above against someone adding an act."""
        md_files = sorted(p.name for p in DATA_DIR.glob("*.md"))
        assert "CLAUDE.md" in md_files
        assert len(md_files) == NUM_ACTS + 1

    def test_every_shipped_act_is_reachable(self):
        for path in sorted(DATA_DIR.glob("*.md")):
            if path.name == "CLAUDE.md":
                continue
            assert acts.find_act(path.stem) is not None, f"{path.name} unreachable"

    def test_claude_md_is_not_an_act(self):
        assert "CLAUDE" not in acts.act_ids()
        assert acts.find_act("CLAUDE") is None
        assert acts.find_act("wh:CLAUDE") is None
        assert all(a.filename != "CLAUDE.md" for a in acts.load_acts())

    def test_act_ids_are_unique(self):
        ids = acts.act_ids()
        assert len(set(ids)) == len(ids)

    def test_no_act_declares_an_unknown_frontmatter_key(self):
        """The vocabulary is exactly four keys. Derive, do not declare."""
        for path in sorted(DATA_DIR.glob("*.md")):
            if path.name == "CLAUDE.md":
                continue
            extra = set(_frontmatter(path)) - set(acts.FRONTMATTER_KEYS)
            assert not extra, f"{path.name} has unexpected frontmatter keys: {extra}"


class TestParsing:
    def test_name_prefix_is_stripped_but_kept(self):
        act = acts.find_act("chat")
        assert act is not None
        assert act.act_id == "chat"
        assert act.name == "wh:chat"

    def test_lookup_accepts_either_form(self):
        assert acts.find_act("chat") is acts.find_act("wh:chat")
        assert acts.find_act("/wh:chat") is acts.find_act("chat")

    def test_lookup_of_unknown_name_returns_none(self):
        assert acts.find_act("does-not-exist") is None
        assert acts.find_act("") is None

    def test_every_act_has_description_and_tools(self):
        for act in acts.load_acts():
            assert act.description, f"{act.name} has no description"
            assert act.allowed_tools, f"{act.name} grants no tools"

    def test_body_is_verbatim_from_the_file(self):
        """The body is the file's content, not a rewrite of it."""
        for act in acts.load_acts():
            raw = (DATA_DIR / act.filename).read_text()
            assert act.body, f"{act.name} has an empty body"
            assert act.body in raw, f"{act.name} body is not a substring of its file"

    def test_body_excludes_the_frontmatter(self):
        act = acts.find_act("chat")
        assert act is not None
        assert "allowed-tools" not in act.body.split("\n")[0]
        assert not act.body.startswith("---")

    def test_parse_act_rejects_a_file_with_no_frontmatter(self, tmp_path):
        bogus = tmp_path / "bogus.md"
        bogus.write_text("# just a heading\n")
        with pytest.raises(ValueError):
            acts.parse_act(bogus)


class TestDerivedMode:
    def test_mode_matches_allowed_tools_for_every_act(self):
        """Compute the mode independently and compare, for all 39 acts."""
        for act in acts.load_acts():
            tools = _frontmatter(DATA_DIR / act.filename)["allowed-tools"]
            grants_ops = any(t.startswith("mcp__wheeler_ops__") for t in tools)
            grants_mutations = any(
                t.startswith("mcp__wheeler_mutations__") for t in tools
            )
            expected = (
                "execute" if grants_ops
                else "write" if grants_mutations
                else "chat"
            )
            assert act.mode == expected, (
                f"{act.name}: derived {act.mode}, tools imply {expected}"
            )

    def test_every_mode_is_a_known_value(self):
        assert {a.mode for a in acts.load_acts()} <= set(acts.MODES)

    def test_wildcard_grants_count(self):
        """Acts grant whole servers with `mcp__wheeler_ops__*`, not tool by tool."""
        assert acts.derive_mode(["Read", "mcp__wheeler_ops__*"]) == "execute"
        assert acts.derive_mode(["Read", "mcp__wheeler_mutations__*"]) == "write"

    def test_ops_wins_over_mutations(self):
        both = ["mcp__wheeler_mutations__add_finding", "mcp__wheeler_ops__hash_file"]
        assert acts.derive_mode(both) == "execute"

    def test_read_only_act_is_chat(self):
        assert acts.derive_mode(["Read", "mcp__wheeler_core__*", "mcp__wheeler_query__*"]) == "chat"
        assert acts.derive_mode([]) == "chat"

    def test_known_acts_land_where_expected(self):
        """Spot check the three tiers against acts whose role is unambiguous."""
        assert acts.find_act("execute").mode == "execute"
        assert acts.find_act("note").mode == "write"
        assert acts.find_act("update").mode == "chat"


class TestDerivedOrchestration:
    def test_orchestration_matches_allowed_tools_for_every_act(self):
        subagent_tools = {
            "Agent", "Task", "TaskCreate", "TaskList", "TaskUpdate", "TaskGet",
            "TeamCreate", "TeamDelete", "SendMessage",
        }
        for act in acts.load_acts():
            tools = set(_frontmatter(DATA_DIR / act.filename)["allowed-tools"])
            expected = (
                "subagents" if tools & subagent_tools
                else "skill-dispatch" if "Skill" in tools
                else "none"
            )
            assert act.orchestration == expected, (
                f"{act.name}: derived {act.orchestration}, tools imply {expected}"
            )

    def test_every_orchestration_is_a_known_value(self):
        assert {a.orchestration for a in acts.load_acts()} <= set(acts.ORCHESTRATIONS)

    def test_agent_tool_means_subagents(self):
        assert acts.derive_orchestration(["Read", "Agent"]) == "subagents"
        assert acts.derive_orchestration(["Read", "TeamCreate"]) == "subagents"

    def test_subagents_wins_over_skill(self):
        assert acts.derive_orchestration(["Skill", "Agent"]) == "subagents"

    def test_skill_alone_means_dispatch(self):
        assert acts.derive_orchestration(["Read", "Skill"]) == "skill-dispatch"

    def test_plain_act_orchestrates_nothing(self):
        assert acts.derive_orchestration(["Read", "Write"]) == "none"

    def test_known_acts_land_where_expected(self):
        assert acts.find_act("execute").orchestration == "subagents"
        assert acts.find_act("start").orchestration == "skill-dispatch"
        assert acts.find_act("note").orchestration == "none"


class TestOrchestrationNote:
    def test_default_host_is_claude(self):
        act = acts.find_act("execute")
        assert acts.orchestration_note(act) == acts.orchestration_note(act, "claude")
        assert acts.orchestration_note(act, "") == acts.orchestration_note(act, "claude")

    def test_claude_note_names_claude_tools(self):
        note = acts.orchestration_note(acts.find_act("execute"), "claude")
        assert "Agent" in note
        assert "TeamCreate" in note

    def test_codex_note_names_codex_multi_agent(self):
        note = acts.orchestration_note(acts.find_act("execute"), "codex")
        assert "features.multi_agent" in note
        for call in ("spawn_agent", "send_input", "wait_agent", "close_agent"):
            assert call in note
        assert ".codex/agents" in note

    def test_codex_note_does_not_name_claude_tools(self):
        note = acts.orchestration_note(acts.find_act("execute"), "codex")
        for claude_tool in ("TeamCreate", "TeamDelete", "TaskCreate", "SendMessage"):
            assert claude_tool not in note

    def test_codex_note_falls_back_to_sequential(self):
        note = acts.orchestration_note(acts.find_act("execute"), "codex")
        assert "sequence" in note

    def test_skill_dispatch_note_is_host_specific(self):
        act = acts.find_act("start")
        assert "`Skill` tool" in acts.orchestration_note(act, "claude")
        codex = acts.orchestration_note(act, "codex")
        assert "$<act_id>" in codex
        assert "Skill" not in codex

    def test_no_note_when_nothing_is_orchestrated(self):
        act = acts.find_act("note")
        assert act.orchestration == "none"
        assert acts.orchestration_note(act, "claude") == ""
        assert acts.orchestration_note(act, "codex") == ""

    def test_unknown_host_raises(self):
        with pytest.raises(ValueError):
            acts.orchestration_note(acts.find_act("execute"), "gemini")

    def test_notes_use_no_em_dashes(self):
        for act in acts.load_acts():
            for host in acts.HOSTS:
                assert "—" not in acts.orchestration_note(act, host)


class TestListActsTool:
    @pytest.mark.asyncio
    async def test_returns_every_act(self):
        from wheeler.mcp_core import list_acts

        result = await list_acts()
        assert result["count"] == NUM_ACTS
        assert len(result["acts"]) == NUM_ACTS

    @pytest.mark.asyncio
    async def test_entry_shape(self):
        from wheeler.mcp_core import list_acts

        result = await list_acts()
        entry = next(a for a in result["acts"] if a["act_id"] == "chat")
        assert set(entry) == {
            "name", "act_id", "description", "argument_hint", "mode", "orchestration",
        }
        assert entry["name"] == "wh:chat"

    @pytest.mark.asyncio
    async def test_listing_carries_no_bodies(self):
        """The listing stays small: 39 bodies would be ~389 KB."""
        from wheeler.mcp_core import list_acts

        result = await list_acts()
        assert all("body" not in a for a in result["acts"])

    @pytest.mark.asyncio
    async def test_claude_md_absent_from_listing(self):
        from wheeler.mcp_core import list_acts

        result = await list_acts()
        assert all(a["act_id"] != "CLAUDE" for a in result["acts"])


class TestGetActTool:
    @pytest.mark.asyncio
    async def test_every_act_is_fetchable(self):
        from wheeler.mcp_core import get_act

        for path in sorted(DATA_DIR.glob("*.md")):
            if path.name == "CLAUDE.md":
                continue
            result = await get_act(path.stem)
            assert "error" not in result, f"{path.name}: {result.get('error')}"
            assert result["body"]

    @pytest.mark.asyncio
    async def test_claude_md_is_not_fetchable(self):
        from wheeler.mcp_core import get_act

        for name in ("CLAUDE", "wh:CLAUDE", "CLAUDE.md"):
            result = await get_act(name)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_accepts_prefixed_and_bare_names(self):
        from wheeler.mcp_core import get_act

        assert await get_act("chat") == await get_act("wh:chat")

    @pytest.mark.asyncio
    async def test_unknown_name_returns_error_not_raise(self):
        from wheeler.mcp_core import get_act

        result = await get_act("nonexistent-act")
        assert "error" in result
        assert "nonexistent-act" in result["error"]
        assert "chat" in result["known_acts"]

    @pytest.mark.asyncio
    async def test_body_is_identical_across_hosts_but_note_differs(self):
        from wheeler.mcp_core import get_act

        claude = await get_act("execute", host="claude")
        codex = await get_act("execute", host="codex")
        assert claude["body"] == codex["body"]
        assert claude["orchestration_note"] != codex["orchestration_note"]
        assert "TeamCreate" not in codex["orchestration_note"]
        assert "features.multi_agent" in codex["orchestration_note"]

    @pytest.mark.asyncio
    async def test_host_defaults_to_claude(self):
        from wheeler.mcp_core import get_act

        assert await get_act("execute") == await get_act("execute", host="claude")

    @pytest.mark.asyncio
    async def test_unknown_host_returns_error(self):
        from wheeler.mcp_core import get_act

        result = await get_act("execute", host="gemini")
        assert "error" in result
        assert result["supported_hosts"] == ["claude", "codex"]

    @pytest.mark.asyncio
    async def test_result_carries_mode_and_tools(self):
        from wheeler.mcp_core import get_act

        result = await get_act("execute")
        assert result["mode"] == "execute"
        assert result["orchestration"] == "subagents"
        assert result["host"] == "claude"
        assert "Read" in result["allowed_tools"]
