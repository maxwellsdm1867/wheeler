"""Tests for the `wh` plugin generator.

The generated tree is COMMITTED, not gitignored, because both hosts install a
plugin by fetching the repository and reading its manifests
(`claude plugin marketplace add owner/repo`, `codex plugin install <url>`), and
because `claude --plugin-dir <clone>` reads it straight off disk. A gitignored
tree would make a marketplace install, and a fresh clone, find nothing.

Committed generated output can go stale silently, so
`test_committed_tree_matches_generator` is the drift guard, in the same spirit as
`tests/test_installer.py::test_package_data_in_sync` and
`tests/test_routing.py::TestTreeSync`, which pin the existing
`.claude/commands/wh/` <-> `wheeler/_data/commands/` mirror.
"""

from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest
import yaml

from wheeler import build_plugin as bp
from wheeler.acts import load_acts

REPO = bp._repo_root()
SOURCE_COMMANDS = REPO / "wheeler" / "_data" / "commands"

EXPECTED_ACT_COUNT = 39

# Reserved marketplace names the host rejects.
RESERVED_MARKETPLACE_NAMES = {
    "claude-code-marketplace",
    "claude-plugins-official",
    "agent-skills",
}


@pytest.fixture(scope="module")
def files() -> dict[str, str]:
    """The tree the generator would produce, rendered to memory."""
    return bp.build_plugin_files(REPO)


@pytest.fixture(scope="module")
def version() -> str:
    return bp.package_version(REPO)


@pytest.fixture
def scratch_root(tmp_path: Path) -> Path:
    """A root holding only pyproject.toml.

    Acts and subagents are read through the package, so that is the generator's
    only input from the root; everything else it writes.
    """
    shutil.copy2(REPO / "pyproject.toml", tmp_path / "pyproject.toml")
    return tmp_path


def _skill_paths(files: dict[str, str]) -> list[str]:
    return sorted(p for p in files if p.startswith(f"{bp.SKILLS_DIR}/"))


def _split_skill(text: str) -> tuple[dict, str]:
    """Return (frontmatter, body) for a generated SKILL.md."""
    assert text.startswith("---\n"), "frontmatter must open the file"
    _, _, rest = text.partition("---\n")
    fm_text, _, body = rest.partition("\n---")
    return yaml.safe_load(fm_text), body


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


def test_source_tree_is_39_acts_plus_the_authoring_guide():
    """_data/commands/ holds 40 .md files; CLAUDE.md is not an act."""
    names = sorted(p.name for p in SOURCE_COMMANDS.glob("*.md"))
    assert "CLAUDE.md" in names
    assert len(names) == EXPECTED_ACT_COUNT + 1


def test_emits_one_skill_per_act_and_excludes_claude_md(files):
    """39 acts, not 40. `_data/commands/CLAUDE.md` is the authoring guide."""
    skills = sorted(p.split("/")[1] for p in _skill_paths(files))
    assert len(skills) == EXPECTED_ACT_COUNT
    assert "CLAUDE" not in skills and "claude" not in skills
    assert skills == sorted(a.act_id for a in load_acts())


def test_every_skill_is_one_SKILL_md_in_its_own_dir(files):
    for path in _skill_paths(files):
        parts = path.split("/")
        assert len(parts) == 3, path
        assert parts[2] == "SKILL.md", path


def test_skill_dirs_carry_no_wh_prefix(files):
    """Claude Code namespaces plugin skills as /<plugin>:<skill>.

    A skill dir named `wh-plan` or `wh:plan` would yield `/wh:wh-plan`, breaking
    the whole point of naming the plugin `wh`.
    """
    for path in _skill_paths(files):
        name = path.split("/")[1]
        assert not name.startswith("wh-"), name
        assert not name.startswith("wh:"), name
        assert ":" not in name, name


def test_invocation_spelling_is_unchanged(files):
    """The acts users type today must resolve under the same spelling."""
    skills = {p.split("/")[1] for p in _skill_paths(files)}
    for act in ("chat", "plan", "execute", "discuss", "write", "start", "ask"):
        assert act in skills, f"/{bp.PLUGIN_NAME}:{act} would not resolve"


def test_frontmatter_opens_the_file(files):
    """A parser that does not see `---` on line 1 treats the block as prose.

    That would silently drop `description` and `allowed-tools`, and take Claude
    Code's mode enforcement with them. Every SKILL.md installed on a real
    machine opens with `---`; the generated-file banner goes after it.
    """
    for path in _skill_paths(files):
        text = files[path]
        assert text.startswith("---\n"), path
        assert "GENERATED FILE" in text, path
        banner_at = text.index("GENERATED FILE")
        assert banner_at > text.index("\n---", 4), path


def test_skill_frontmatter_matches_source_act(files):
    """description and allowed-tools are carried through verbatim.

    allowed-tools matters most: Claude Code honours it in plugin skills, so it is
    what keeps CHAT/WRITE/EXECUTE mode enforcement working after the move.
    """
    for act in load_acts():
        fm, body = _split_skill(files[f"{bp.SKILLS_DIR}/{act.act_id}/SKILL.md"])

        assert fm["name"] == act.act_id
        assert fm["description"] == act.description
        # Every granted tool survives. The generator may ADD get_act (below),
        # but it may never drop or rewrite a grant.
        emitted = tuple(fm.get("allowed-tools") or ())
        assert set(act.allowed_tools) <= set(emitted), act.act_id
        assert emitted[: len(act.allowed_tools)] == act.allowed_tools, act.act_id
        if act.argument_hint:
            assert fm["argument-hint"] == act.argument_hint
        # The stub must delegate, not inline the act.
        assert "get_act" in body
        assert len(body) < 1200, f"{act.act_id} stub is too long, is the body inlined?"


def test_every_skill_can_actually_call_get_act(files):
    """The gate must permit the one tool the stub is told to call.

    `allowed-tools` is an allowlist. An act granted explicit
    `mcp__wheeler_core__*` tool NAMES but not `get_act` would be told to fetch
    its own instructions through a gate that blocks the fetch, leaving the skill
    inert. Only the wildcard acts are covered without the addition.
    """
    for act in load_acts():
        fm, _ = _split_skill(files[f"{bp.SKILLS_DIR}/{act.act_id}/SKILL.md"])
        tools = fm.get("allowed-tools") or []
        assert bp.GET_ACT_TOOL in tools or bp.CORE_WILDCARD in tools, (
            f"{act.act_id} is told to call get_act but cannot reach it"
        )


def test_get_act_is_not_duplicated_under_a_wildcard():
    act = next(a for a in load_acts() if bp.CORE_WILDCARD in a.allowed_tools)
    tools = bp.skill_allowed_tools(act)
    assert tools.count(bp.CORE_WILDCARD) == 1
    assert bp.GET_ACT_TOOL not in tools
    # The wildcard still gets its plugin-scoped twin.
    assert f"mcp__{bp.PLUGIN_TOOL_NAMESPACE}wheeler_core__*" in tools


def test_get_act_is_appended_when_no_wildcard_covers_it():
    act = next(a for a in load_acts() if bp.CORE_WILDCARD not in a.allowed_tools)
    tools = bp.skill_allowed_tools(act)
    assert bp.GET_ACT_TOOL in tools
    # Source grants come first and in order, so nothing is reordered or dropped.
    assert tools[: len(act.allowed_tools)] == act.allowed_tools


# ---------------------------------------------------------------------------
# Plugin MCP namespacing: the trap that makes every act inert if missed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("server", sorted(bp.SERVER_NAMES))
def test_plugin_scoped_tool_rewrites_the_server_segment(server):
    """Read off the CLI's own init event under `--plugin-dir`:
    `wheeler_core` shipped by plugin `wh` registers as `plugin:wh:wheeler_core`,
    and its tools as `mcp__plugin_wh_wheeler_core__<tool>`."""
    assert bp.plugin_scoped_tool(f"mcp__{server}__thing") == (
        f"mcp__plugin_wh_{server}__thing"
    )
    assert bp.plugin_scoped_tool(f"mcp__{server}__*") == f"mcp__plugin_wh_{server}__*"


@pytest.mark.parametrize("tool", ["Read", "Bash", "Skill", "mcp__neo4j__read"])
def test_non_wheeler_tools_have_no_plugin_alias(tool):
    """Host built-ins and third-party MCP servers are not namespaced by us."""
    assert bp.plugin_scoped_tool(tool) is None


def test_every_wheeler_grant_is_spelled_both_ways(files):
    """A plugin's MCP tool ids are namespaced, so `allowed-tools` copied through
    verbatim would deny every Wheeler tool once the servers come from the plugin.

    Both spellings are emitted: the bare one matches a server configured outside
    the plugin (user-scope `~/.claude.json`, or the repo's dev `.mcp.json`), the
    namespaced one matches the plugin's own. Verified end to end against the real
    CLI: a skill granted only `mcp__plugin_wh_wheeler_core__graph_status` called
    it successfully with no permission denial.
    """
    for act in load_acts():
        fm, _ = _split_skill(files[f"{bp.SKILLS_DIR}/{act.act_id}/SKILL.md"])
        emitted = set(fm["allowed-tools"])
        for tool in act.allowed_tools:
            alias = bp.plugin_scoped_tool(tool)
            if alias is not None:
                assert alias in emitted, f"{act.act_id} lacks {alias}"


def test_get_act_is_reachable_under_both_spellings(files):
    for act in load_acts():
        fm, _ = _split_skill(files[f"{bp.SKILLS_DIR}/{act.act_id}/SKILL.md"])
        tools = set(fm["allowed-tools"])
        bare = bp.GET_ACT_TOOL in tools or bp.CORE_WILDCARD in tools
        scoped = (
            f"mcp__{bp.PLUGIN_TOOL_NAMESPACE}wheeler_core__get_act" in tools
            or f"mcp__{bp.PLUGIN_TOOL_NAMESPACE}wheeler_core__*" in tools
        )
        assert bare, f"{act.act_id} cannot call get_act on a non-plugin server"
        assert scoped, f"{act.act_id} cannot call get_act on the plugin's server"


def test_aliasing_widens_nothing(files):
    """Each added entry names one specific tool (or mirrors a wildcard the act
    already had), so mode enforcement is unchanged."""
    for act in load_acts():
        fm, _ = _split_skill(files[f"{bp.SKILLS_DIR}/{act.act_id}/SKILL.md"])
        source = set(act.allowed_tools)
        allowed_extras = {bp.GET_ACT_TOOL}
        for tool in source | allowed_extras:
            alias = bp.plugin_scoped_tool(tool)
            if alias:
                allowed_extras.add(alias)
        assert set(fm["allowed-tools"]) <= source | allowed_extras, act.act_id
        # A bare wildcard is never invented for an act that had none.
        if not any(t.endswith("__*") for t in source):
            assert not any(t.endswith("__*") for t in fm["allowed-tools"]), act.act_id


def test_no_duplicate_entries_in_any_skill(files):
    for path in _skill_paths(files):
        fm, _ = _split_skill(files[path])
        tools = fm.get("allowed-tools") or []
        assert len(tools) == len(set(tools)), path


def test_stub_does_not_duplicate_the_act_body(files):
    """The point of the design: exactly one copy of each act body, served over MCP."""
    for act in load_acts():
        stub = files[f"{bp.SKILLS_DIR}/{act.act_id}/SKILL.md"]
        # Compare on a distinctive slice of the real body rather than the whole
        # thing, so this stays robust to whitespace handling.
        marker = act.body.strip().splitlines()[0][:60]
        if len(marker) > 20:
            assert marker not in stub, f"{act.act_id} stub appears to inline the body"


def test_stub_records_the_derived_mode_and_orchestration(files):
    """Codex cannot infer either from the tool list, so the stub states them."""
    for act in load_acts():
        stub = files[f"{bp.SKILLS_DIR}/{act.act_id}/SKILL.md"]
        assert f"Mode: `{act.mode}`" in stub, act.act_id
        assert f"Orchestration: `{act.orchestration}`" in stub, act.act_id


# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------


def test_all_emitted_json_parses(files):
    for rel, content in files.items():
        if rel.endswith(".json"):
            json.loads(content)


def test_manifest_version_tracks_pyproject(files, version):
    assert f'version = "{version}"' in (REPO / "pyproject.toml").read_text()
    for rel in (bp.CLAUDE_MANIFEST, bp.CODEX_MANIFEST):
        assert json.loads(files[rel])["version"] == version
    mkt = json.loads(files[bp.MARKETPLACE_MANIFEST])
    assert mkt["plugins"][0]["version"] == version
    assert mkt["metadata"]["version"] == version


def test_plugin_is_named_wh(files):
    """Renaming this silently renames every slash command. Pin it."""
    for rel in (bp.CLAUDE_MANIFEST, bp.CODEX_MANIFEST):
        assert json.loads(files[rel])["name"] == "wh"
    assert bp.PLUGIN_NAME == "wh"


def test_marketplace_name_is_not_reserved(files):
    name = json.loads(files[bp.MARKETPLACE_MANIFEST])["name"]
    assert name == bp.MARKETPLACE_NAME == "wheeler"
    assert name not in RESERVED_MARKETPLACE_NAMES
    assert not name.startswith("anthropic-")


def test_marketplace_serves_the_plugin_from_this_same_repo(files):
    data = json.loads(files[bp.MARKETPLACE_MANIFEST])
    assert "owner" in data
    assert len(data["plugins"]) == 1
    entry = data["plugins"][0]
    assert entry["name"] == bp.PLUGIN_NAME
    # Catalog root and plugin root are the same directory.
    assert entry["source"] == "./"
    assert ".." not in entry["source"]


def test_no_bundled_content_variant_key(files):
    """Undocumented and first-party-internal; do not ship it."""
    for rel in (bp.CLAUDE_MANIFEST, bp.CODEX_MANIFEST, bp.MARKETPLACE_MANIFEST):
        assert "bundledContentVariant" not in files[rel], rel


def test_both_manifests_point_at_the_generated_mcp_config(files):
    """Not the conventional `.mcp.json`: that path is the repo's DEV config.

    The root `.mcp.json` launches `.venv/bin/python -m wheeler.mcp_core` against
    a local checkout. Claiming it would break every contributor's editable
    install, so both hosts get an explicit path instead.
    """
    expected = f"./{bp.MCP_JSON_NAME}"
    assert json.loads(files[bp.CLAUDE_MANIFEST])["mcpServers"] == expected
    assert json.loads(files[bp.CODEX_MANIFEST])["mcpServers"] == expected
    assert bp.MCP_JSON_NAME in files
    assert bp.MCP_JSON_NAME != ".mcp.json"
    assert ".mcp.json" not in files


def test_mcp_config_is_zero_install_and_version_pinned(files, version):
    """uvx needs no prior install, and the pin stops plugin/package drift."""
    cfg = json.loads(files[bp.MCP_JSON_NAME])
    assert set(cfg) == set(bp.SERVER_NAMES)
    scripts = {name: script for name, script, _role in bp.MCP_SERVERS}
    for name, entry in cfg.items():
        assert entry["command"] == "uvx", name
        assert entry["args"][:2] == ["--from", f"wheeler>={version}"], name
        assert entry["args"][2] == scripts[name], name


@pytest.mark.asyncio
async def test_pinned_version_must_actually_provide_the_tools_the_stubs_call():
    """The stubs tell the model to call `get_act`. The pinned package must have it.

    This test exists because the real thing shipped broken and looked fine locally.
    The plugin pinned `wheeler==0.13.0`, and PyPI's 0.13.0 predates `wheeler/acts.py`:
    its `mcp_core` serves 12 tools with no `get_act` and no `list_acts`. So every one
    of the 39 skills was inert on a marketplace install, on both hosts, while the
    frontmatter read correctly.

    It passed on a developer machine for a subtle reason worth remembering: `uv`
    resolved `wheeler==<pyproject version>` out of its cache using a locally BUILT
    artifact of this working tree. A dev therefore gets the working tree and every
    real user gets PyPI. Any check that runs `uvx --from wheeler==<version>` on a
    machine that has built this repo is measuring the wrong thing.

    So assert against the LOCAL module surface instead, which is what the next
    release will publish: whatever tool names the generated stubs instruct the model
    to call must exist in the server the manifest points at.

    RELEASE PREREQUISITE: the pinned version has to be published to PyPI before the
    plugin works for anyone else. Bump, publish, then regenerate.
    """
    from wheeler.mcp_core import mcp

    core_tools = {t.name for t in await mcp.list_tools()}

    # Names the stubs actually instruct the model to call.
    required = {"get_act"}
    missing = required - core_tools
    assert not missing, (
        f"generated stubs call {sorted(missing)}, which wheeler.mcp_core does not "
        f"expose. Either the stub body or the server surface is wrong."
    )


def test_pin_equals_pyproject_version(files, version):
    """Plugin and package must move together, or the pin points at a stale surface.

    Paired with the test above: that one proves the tools exist in this tree, this
    one proves the manifest asks for this tree's version rather than an older one.
    """
    import tomllib

    pyproject_version = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]
    assert version == pyproject_version
    cfg = json.loads(files[bp.MCP_JSON_NAME])
    for name, entry in cfg.items():
        assert f"wheeler>={pyproject_version}" in entry["args"], name


def test_codex_component_paths_are_plugin_root_relative(files):
    data = json.loads(files[bp.CODEX_MANIFEST])
    assert data["skills"] == f"./{bp.SKILLS_DIR}/"
    assert data["hooks"] == f"./{bp.HOOKS_CONFIG}"
    for key in ("skills", "mcpServers", "hooks"):
        assert data[key].startswith("./"), key


def test_codex_declares_its_mcp_dependencies(files):
    """Without dependencies.tools, Codex will not auto-wire the servers.

    The user-visible symptom is "The following MCP servers are required by the
    selected skills but are not installed yet."
    """
    data = yaml.safe_load(files[bp.CODEX_AGENT_META])
    declared = {t["value"] for t in data["dependencies"]["tools"]}
    assert declared == set(bp.SERVER_NAMES)
    assert data["policy"]["allow_implicit_invocation"] is True
    for tool in data["dependencies"]["tools"]:
        assert tool["type"] == "mcp"
        assert tool["transport"] == "stdio"
        assert tool["description"]


# ---------------------------------------------------------------------------
# Codex mode profiles
# ---------------------------------------------------------------------------


def test_all_emitted_toml_parses(files):
    for rel, content in files.items():
        if rel.endswith(".toml"):
            tomllib.loads(content)


def test_three_profiles_one_per_mode(files):
    emitted = {p for p in files if p.startswith(f"{bp.PROFILES_DIR}/")}
    assert emitted == {
        f"{bp.PROFILES_DIR}/wheeler-{m}.config.toml" for m in bp.MODE_SERVERS
    }


@pytest.mark.parametrize("mode", sorted(bp.MODE_SERVERS))
def test_profile_disables_every_server_outside_the_mode(files, mode):
    """The merge trap, and the reason this test exists.

    Codex merges a profile RECURSIVELY into the base config, so omitting a server
    does NOT disable it: the base entry survives, and there is no
    `mcp_servers = {}` reset. Each profile must therefore write `enabled = false`
    explicitly for everything outside its mode, or "chat" quietly keeps write
    access.
    """
    rel = f"{bp.PROFILES_DIR}/wheeler-{mode}.config.toml"
    servers = tomllib.loads(files[rel])["mcp_servers"]

    allowed = set(bp.MODE_SERVERS[mode])
    all_names = set(bp.SERVER_NAMES)

    # Every server appears, so nothing can be left to the base config.
    assert set(servers) == all_names
    for name in all_names:
        assert servers[name]["enabled"] is (name in allowed), (
            f"{mode}: {name} enabled={servers[name]['enabled']}, "
            f"expected {name in allowed}"
        )


@pytest.mark.parametrize("mode", sorted(bp.MODE_SERVERS))
def test_enabled_servers_are_fully_declared(files, mode):
    """A profile must stand alone: a user with no base declaration still gets
    working servers, not bare `enabled = true` against nothing."""
    rel = f"{bp.PROFILES_DIR}/wheeler-{mode}.config.toml"
    servers = tomllib.loads(files[rel])["mcp_servers"]
    scripts = {name: script for name, script, _role in bp.MCP_SERVERS}
    for name in bp.MODE_SERVERS[mode]:
        assert servers[name]["command"] == "uvx", (mode, name)
        assert servers[name]["args"][-1] == scripts[name], (mode, name)


@pytest.mark.parametrize("mode", sorted(bp.MODE_SERVERS))
def test_profile_pins_the_package_version(files, version, mode):
    rel = f"{bp.PROFILES_DIR}/wheeler-{mode}.config.toml"
    servers = tomllib.loads(files[rel])["mcp_servers"]
    for name in bp.MODE_SERVERS[mode]:
        assert servers[name]["args"][1] == f"wheeler>={version}", (mode, name)


def test_chat_mode_cannot_reach_mutations(files):
    """The single most important property of the mode split."""
    servers = tomllib.loads(
        files[f"{bp.PROFILES_DIR}/wheeler-chat.config.toml"]
    )["mcp_servers"]
    assert servers["wheeler_mutations"]["enabled"] is False
    assert servers["wheeler_ops"]["enabled"] is False
    # A disabled server carries no launch command at all.
    assert "command" not in servers["wheeler_mutations"]


def test_profiles_avoid_the_dead_legacy_shape(files):
    """`[profiles.<name>]` and a `profile = "..."` selector are both dead as of
    Codex 0.134.0. Top-level keys only."""
    for mode in bp.MODE_SERVERS:
        text = files[f"{bp.PROFILES_DIR}/wheeler-{mode}.config.toml"]
        assert "[profiles." not in text, mode
        assert "[profiles]" not in text, mode
        data = tomllib.loads(text)
        assert "profiles" not in data, mode
        assert "profile" not in data, mode
        assert "mcp_servers" in data, mode


def test_modes_are_strictly_nested():
    chat, write, execute = (
        set(bp.MODE_SERVERS[m]) for m in ("chat", "write", "execute")
    )
    assert chat < write < execute
    assert execute == set(bp.SERVER_NAMES)


# ---------------------------------------------------------------------------
# Hooks, subagents, install doc
# ---------------------------------------------------------------------------


def test_hooks_config_references_an_emitted_script(files):
    data = json.loads(files[bp.HOOKS_CONFIG])
    commands = [
        h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]
    ]
    assert any(bp.SHADOW_HOOK in c for c in commands)
    assert any("${CLAUDE_PLUGIN_ROOT}" in c for c in commands)
    assert bp.SHADOW_HOOK in files


def test_shadow_hook_is_silent_on_a_clean_machine(files):
    """It must not narrate on the overwhelmingly common case of no legacy install."""
    script = files[bp.SHADOW_HOOK]
    assert "process.exit(0)" in script
    assert "migrate-to-plugin" in script


def test_subagents_ship_verbatim(files):
    for name in ("wheeler-researcher.md", "wheeler-worker.md"):
        rel = f"{bp.AGENTS_DIR}/{name}"
        assert rel in files
        assert files[rel] == (bp.agent_data_dir() / name).read_text(), rel


def test_subagent_frontmatter_still_parses(files):
    for rel, content in files.items():
        if rel.startswith(f"{bp.AGENTS_DIR}/") and rel.endswith(".md"):
            fm = yaml.safe_load(content.split("---", 2)[1])
            assert fm["name"]
            assert fm["description"]


def test_install_doc_states_the_prerequisites(files):
    doc = files[bp.INSTALL_DOC]
    assert "uvx" in doc and "Neo4j" in doc
    assert "shadow" in doc.lower()
    assert "wheeler migrate-to-plugin" in doc
    for mode in bp.MODE_SERVERS:
        assert f"wheeler-{mode}" in doc, mode


# ---------------------------------------------------------------------------
# Committed tree matches the generator
# ---------------------------------------------------------------------------


def test_committed_tree_matches_generator():
    """Fail if the committed plugin tree drifts from the generator.

    The tree is committed on purpose (a clone must be installable), so this test
    is the only thing standing between that and silently stale output.
    """
    problems = bp.check_plugin(REPO)
    assert not problems, (
        "committed plugin tree is out of date:\n  "
        + "\n  ".join(problems)
        + f"\n\nRegenerate with: {bp.REGEN_CMD}"
    )


def test_every_generated_path_is_committed(files):
    for rel in files:
        assert (REPO / rel).is_file(), f"{rel} was generated but is not on disk"


# ---------------------------------------------------------------------------
# Generator mechanics
# ---------------------------------------------------------------------------


def test_writes_a_clean_tree_that_then_checks_out(scratch_root):
    written, pruned = bp.write_plugin(scratch_root)
    assert written
    assert not pruned
    assert bp.check_plugin(scratch_root) == []


def test_second_run_is_a_no_op(scratch_root):
    bp.write_plugin(scratch_root)
    assert bp.write_plugin(scratch_root) == ([], [])


def test_check_reports_a_hand_edited_file(scratch_root):
    bp.write_plugin(scratch_root)
    (scratch_root / bp.SKILLS_DIR / "chat" / "SKILL.md").write_text("edited\n")
    problems = bp.check_plugin(scratch_root)
    assert any("stale" in p and "chat" in p for p in problems)


def test_check_reports_a_missing_file(scratch_root):
    bp.write_plugin(scratch_root)
    (scratch_root / bp.CLAUDE_MANIFEST).unlink()
    assert any("missing" in p for p in bp.check_plugin(scratch_root))


def test_a_stale_skill_dir_is_reported_then_pruned(scratch_root):
    """A renamed or removed act must not leave a directory a host would load."""
    bp.write_plugin(scratch_root)
    orphan = scratch_root / bp.SKILLS_DIR / "zz-removed-act"
    orphan.mkdir()
    (orphan / "SKILL.md").write_text("---\nname: zz-removed-act\n---\n")

    assert any("leftover" in p for p in bp.check_plugin(scratch_root))

    _written, pruned = bp.write_plugin(scratch_root)
    assert f"{bp.SKILLS_DIR}/zz-removed-act/SKILL.md" in pruned
    assert not orphan.exists(), "emptied skill dir should be removed too"
    assert bp.check_plugin(scratch_root) == []


def test_cli_check_exits_nonzero_on_drift(scratch_root, capsys):
    bp.write_plugin(scratch_root)
    assert bp.main(["--check", "--root", str(scratch_root)]) == 0

    (scratch_root / bp.MCP_JSON_NAME).unlink()
    assert bp.main(["--check", "--root", str(scratch_root)]) == 1
    assert "out of date" in capsys.readouterr().out


def test_yaml_scalar_quotes_what_would_misparse():
    assert bp._yaml_scalar("plain text") == "plain text"
    assert bp._yaml_scalar("") == '""'
    # A colon is the case that actually occurs in act descriptions.
    assert bp._yaml_scalar("Use when: now").startswith('"')
    assert bp._yaml_scalar('say "hi"') == '"say \\"hi\\""'


def test_every_act_description_survives_a_yaml_round_trip(files):
    """The emitted frontmatter must parse back to the exact source description."""
    for act in load_acts():
        fm, _ = _split_skill(files[f"{bp.SKILLS_DIR}/{act.act_id}/SKILL.md"])
        assert fm["description"] == act.description, act.act_id
